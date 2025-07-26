import threading
import time
import serial
import os
from dotenv import load_dotenv
import RPi.GPIO as GPIO

from Sensors.Camera import CameraReader
from Sensors.GPS import GPSReader
from Sensors.HX711 import HX711Reader
from Sensors.WasteHandler import WasteHandler
from API.backup import Backup

class RelayManager:
    """
    Gestiona la activación de un relé en un pin GPIO durante un tiempo dado.
    Mientras haya objetos detectados, mantiene el relé encendido.
    """
    def __init__(self, pin: int, duration: float):
        self.pin = pin
        self.duration = duration
        self.is_active = False
        self.last_trigger_time = 0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.monitor_thread = None
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = relé apagado
        print(f"[RELAY] Inicializado en pin {pin}, duración {duration}s")
        
        # Iniciar hilo monitor que verifica constantemente si debe apagar
        self._start_monitor()

    def trigger(self):
        """
        Activa el relé o extiende su tiempo de activación si ya está encendido.
        """
        with self.lock:
            current_time = time.time()
            self.last_trigger_time = current_time
            
            if not self.is_active:
                # Relé apagado, encenderlo
                self._turn_on()
            else:
                # Relé ya encendido, solo actualizar el tiempo
                print(f"[RELAY] Tiempo extendido - último trigger: {current_time}")

    def _turn_on(self):
        """Enciende el relé físicamente."""
        GPIO.output(self.pin, GPIO.LOW)  # LOW = relé encendido
        self.is_active = True
        print("[RELAY] Encendido")

    def _turn_off(self):
        """Apaga el relé físicamente."""
        GPIO.output(self.pin, GPIO.HIGH)  # HIGH = relé apagado
        self.is_active = False
        print("[RELAY] Apagado")

    def _start_monitor(self):
        """Inicia el hilo monitor que verifica periódicamente si debe apagar el relé."""
        self.monitor_thread = threading.Thread(target=self._monitor_relay, daemon=True)
        self.monitor_thread.start()

    def _monitor_relay(self):
        """
        Hilo que verifica cada 0.5 segundos si debe apagar el relé.
        """
        while not self.stop_event.is_set():
            time.sleep(0.5)  # Verificar cada 500ms
            
            with self.lock:
                if self.is_active:
                    current_time = time.time()
                    time_since_last_trigger = current_time - self.last_trigger_time
                    
                    if time_since_last_trigger >= self.duration:
                        print(f"[RELAY] Sin actividad por {time_since_last_trigger:.1f}s - Apagando")
                        self._turn_off()

    def force_off(self):
        """Fuerza el apagado del relé (útil para limpieza)."""
        with self.lock:
            if self.is_active:
                self._turn_off()
    
    def cleanup(self):
        """Limpia los recursos del relé."""
        print("[RELAY] Iniciando limpieza...")
        self.stop_event.set()
        self.force_off()
        
        # Esperar a que termine el monitor
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
        
        # Limpiar el pin específico
        GPIO.setup(self.pin, GPIO.IN)  # Configurar como entrada antes de limpiar
        print(f"[RELAY] Pin {self.pin} limpiado")

class RaspberryController:
    """
    Orquesta la lectura de sensores, manejo de periodos, backup, comunicación con ESP32 y relé.
    """
    def __init__(self, service_periods):
        # Cargar configuración
        load_dotenv()
        self.register_service = service_periods  # instancia de RegisterPeriods

        # Parámetros ESP32
        self.ESP32_PORT = os.getenv('ESP32_PORT', '/dev/ttyUSB0')
        self.ESP32_BAUDRATE = int(os.getenv('ESP32_BAUDRATE', '9600'))
        self.OBJECT_COMMAND = os.getenv('OBJECT_COMMAND', 'OBJETO_ENFRENTE')

        # Parámetros relé
        relay_pin = int(os.getenv('RELAY_PIN', '17'))
        relay_duration = float(os.getenv('RELAY_DURATION', '6'))
        self.relay = RelayManager(relay_pin, relay_duration)

        # Umbral detección
        self.CAM_CONF_THRESHOLD = float(os.getenv('CAM_CONF_THRESHOLD', '0.8'))

        # Evento de paro y cola de comandos
        self.stop_event = threading.Event()
        from queue import Queue
        self.cmd_queue = Queue()

        # Inicializar handler y sensores
        self.handler = WasteHandler(service_register=self.register_service)
        self._hook_detections()

        self.gps = GPSReader(serviceRegister=self.register_service)
        self.hx = HX711Reader(serviceRegister=self.register_service, h=self.handler)
        self.cam = CameraReader(h=self.handler)
        #self.backup = Backup()

    def _hook_detections(self):
        """Envuelve process_detections para enviar comando y disparar relé."""
        original = self.handler.process_detections
        def hooked(detections):
            original(detections)
            
            # Verificar si hay detecciones válidas
            valid_detection = False
            for det in detections:
                if det.get('conf', 0) >= self.CAM_CONF_THRESHOLD:
                    valid_detection = True
                    break
            
            # Solo activar relé y enviar comando si hay detección válida
            if valid_detection:
                self.cmd_queue.put(self.OBJECT_COMMAND)
                self.relay.trigger()
                
        self.handler.process_detections = hooked

    def _esp32_comm(self):
        """Hilo que envía comandos al ESP32 via serial."""
        try:
            ser = serial.Serial(self.ESP32_PORT, self.ESP32_BAUDRATE, timeout=1)
            print(f"[ESP32] Conectado a {self.ESP32_PORT}@{self.ESP32_BAUDRATE}")
        except Exception as e:
            print(f"[ESP32] Error abriendo serial: {e}")
            return

        while not self.stop_event.is_set():
            try:
                cmd = self.cmd_queue.get(timeout=0.5)
                ser.write((cmd + '\n').encode())
                print(f"[ESP32] Enviado: {cmd}")
            except Exception:
                continue

        ser.close()
        print("[ESP32] Comunicación finalizada")

    def start(self):
        """Arranca todos los hilos necesarios y maneja KeyboardInterrupt."""
        # Inicializar período
        if self.register_service.statusPeriod():
            self.register_service.createNewPeriod()
            self.register_service.createVoidReading()
        else:
            self.register_service.completeLastPeriod()

        # Crear hilos
        threads = [
            threading.Thread(target=self._esp32_comm, name='ESP32_Comm', daemon=True),
            threading.Thread(target=self.gps.start,     name='GPS',       daemon=True),
            threading.Thread(target=self.hx.start,      name='HX711',     daemon=True),
            threading.Thread(target=self.cam.start,     name='Camera',    daemon=True),
            #threading.Thread(target=self.backup.start,  name='Backup',    daemon=True),
        ]
        for t in threads:
            t.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[MAIN] Detención solicitada")
            self.stop_event.set()
            
            # Limpiar el relé específicamente
            self.relay.cleanup()
            time.sleep(0.5)
            
            # Limpiar todos los pines GPIO
            GPIO.cleanup()
            print("[MAIN] Recursos liberados. Saliendo.")