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

class ESP32Communicator:
    """
    Maneja la comunicación con la ESP32 usando el puerto fijo
    """
    def __init__(self):
        # ✅ USAR PUERTO FIJO DEFINIDO POR UDEV
        self.port = "/dev/ttyESP32"
        self.baudrate = 115200
        self.ser = None
        self.is_running = True
        self._connect()

    def _connect(self):
        """Conecta a la ESP32 con reintentos automáticos"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"[ESP32] 🔌 Intentando conectar a {self.port} (intento {attempt + 1}/{max_retries})...")
                
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=1,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
                
                # Pequeña prueba de conexión
                time.sleep(2)  # Esperar inicialización de la ESP32
                
                if self._test_connection():
                    print(f"[ESP32] ✅ Conectado exitosamente a {self.port}")
                    return True
                else:
                    self.ser.close()
                    self.ser = None
                    
            except serial.SerialException as e:
                print(f"[ESP32] ❌ Error de conexión (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    print(f"[ESP32] 🔄 Reintentando en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                else:
                    print("[ESP32] ❌ Todos los intentos de conexión fallaron")
        
        return False

    def _test_connection(self):
        """Prueba la conexión con la ESP32"""
        try:
            if self.ser and self.ser.is_open:
                # Enviar comando de prueba
                self.ser.write(b'PING\n')
                time.sleep(0.1)
                
                # Leer respuesta (si la ESP32 responde)
                if self.ser.in_waiting > 0:
                    response = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    print(f"[ESP32] 🔄 Respuesta de prueba: {response}")
                
                return True
        except Exception as e:
            print(f"[ESP32] ❌ Error en prueba de conexión: {e}")
        
        return False

    def send_command(self, command):
        """Envía un comando a la ESP32"""
        if not self.ser or not self.ser.is_open:
            print("[ESP32] ❌ No hay conexión con la ESP32")
            return False
            
        try:
            # Asegurarse de que el comando termine con newline
            if not command.endswith('\n'):
                command += '\n'
                
            self.ser.write(command.encode('utf-8'))
            print(f"[ESP32] 📤 Enviado: {command.strip()}")
            return True
            
        except Exception as e:
            print(f"[ESP32] ❌ Error enviando comando: {e}")
            # Intentar reconectar
            self._connect()
            return False

    def read_data(self):
        """Lee datos de la ESP32 si están disponibles"""
        if not self.ser or not self.ser.is_open:
            return None
            
        try:
            if self.ser.in_waiting > 0:
                data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if data:
                    print(f"[ESP32] 📥 Recibido: {data}")
                    return data
        except Exception as e:
            print(f"[ESP32] ❌ Error leyendo datos: {e}")
            
        return None

    def close(self):
        """Cierra la conexión con la ESP32"""
        self.is_running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[ESP32] 🔌 Conexión cerrada")

class RaspberryController:
    """
    Orquesta la lectura de sensores, manejo de periodos, backup, comunicación con ESP32 y relé.
    """
    def __init__(self, service_periods):
        # Cargar configuración
        load_dotenv()
        self.register_service = service_periods  # instancia de RegisterPeriods

        # ✅ USAR COMUNICADOR MEJORADO CON PUERTO FIJO
        self.esp32 = ESP32Communicator()
        
        # Parámetros ESP32
        self.OBJECT_COMMAND = os.getenv('OBJECT_COMMAND', 'OBJETO_ENFRENTE')

        # Parámetros relé
        relay_pin = int(os.getenv('RELAY_PIN', '17'))
        relay_duration = float(os.getenv('RELAY_DURATION', '3'))
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
        self.backup = Backup()

        # Hilo para lectura continua de la ESP32
        self.esp32_read_thread = None

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
                print(f"[CONTROLLER] 🎯 Detección válida - Activando relé y enviando comando a ESP32")
                self.cmd_queue.put(self.OBJECT_COMMAND)
                self.relay.trigger()
            else:
                print(f"[CONTROLLER] 👀 Sin detecciones válidas")
                
        self.handler.process_detections = hooked

    def _esp32_comm_loop(self):
        """Hilo que envía comandos al ESP32 y lee respuestas."""
        print("[ESP32] 🔄 Iniciando loop de comunicación")
        
        while not self.stop_event.is_set():
            try:
                # 1. Enviar comandos pendientes
                try:
                    cmd = self.cmd_queue.get(timeout=0.5)
                    self.esp32.send_command(cmd)
                except:
                    pass  # Timeout normal, no hay comandos
                
                # 2. Leer datos de la ESP32
                self.esp32.read_data()
                
            except Exception as e:
                print(f"[ESP32] ❌ Error en loop de comunicación: {e}")
                time.sleep(1)

    def _esp32_read_loop(self):
        """Hilo separado para lectura continua de la ESP32"""
        print("[ESP32] 👂 Iniciando loop de lectura")
        
        while not self.stop_event.is_set():
            try:
                data = self.esp32.read_data()
                if data:
                    # Procesar datos recibidos de la ESP32
                    self._process_esp32_data(data)
            except Exception as e:
                print(f"[ESP32] ❌ Error en loop de lectura: {e}")
            
            time.sleep(0.1)  # Pequeña pausa

    def _process_esp32_data(self, data):
        """Procesa los datos recibidos de la ESP32"""
        try:
            # Aquí puedes procesar los datos que envía la ESP32
            # Por ejemplo: estados de sensores, confirmaciones, etc.
            if "CONFIRMACION" in data:
                print(f"[ESP32] ✅ Confirmación recibida: {data}")
            elif "ERROR" in data:
                print(f"[ESP32] ❌ Error reportado: {data}")
            else:
                print(f"[ESP32] 📝 Datos: {data}")
                
        except Exception as e:
            print(f"[ESP32] ❌ Error procesando datos: {e}")

    def start(self):
        """Arranca todos los hilos necesarios y maneja KeyboardInterrupt."""
        print("[CONTROLLER] 🚀 Iniciando sistema PyBot...")

        # Verificar que la ESP32 esté conectada
        if not self.esp32.ser:
            print("[CONTROLLER] ⚠️  ESP32 no disponible - continuando sin ella")

        # Crear hilos
        threads = [
            threading.Thread(target=self._esp32_comm_loop, name='ESP32_Comm', daemon=True),
            threading.Thread(target=self._esp32_read_loop, name='ESP32_Read', daemon=True),
            threading.Thread(target=self.gps.start, name='GPS', daemon=True),
            threading.Thread(target=self.hx.start, name='HX711', daemon=True),
            threading.Thread(target=self.cam.start, name='Camera', daemon=True),
            threading.Thread(target=self.backup.start, name='Backup', daemon=True),
        ]
        
        for t in threads:
            t.start()
            print(f"[CONTROLLER] ✅ Hilo {t.name} iniciado")

        print("[CONTROLLER] ✅ Todos los hilos iniciados")
        print("[CONTROLLER] 📊 Sistema operativo - Esperando detecciones...")

        try:
            while True:
                # Mostrar estado del sistema cada 30 segundos
                time.sleep(30)
                print("[CONTROLLER] 💓 Sistema activo - Esperando detecciones...")
                
        except KeyboardInterrupt:
            print("\n[CONTROLLER] 🛑 Detención solicitada por usuario")
            self.stop()

    def stop(self):
        """Detiene todos los componentes de manera segura."""
        print("[CONTROLLER] 🧹 Iniciando limpieza de recursos...")
        self.stop_event.set()
        
        # Limpiar componentes en orden
        components = [
            ("Relé", self.relay.cleanup),
            ("ESP32", self.esp32.close),
            ("Cámara", getattr(self.cam, 'stop', lambda: None)),
            ("GPS", getattr(self.gps, 'stop', lambda: None)),
            ("HX711", getattr(self.hx, 'stop', lambda: None)),
            ("Backup", getattr(self.backup, 'stop', lambda: None)),
        ]
        
        for name, stop_func in components:
            try:
                print(f"[CONTROLLER] 🔌 Deteniendo {name}...")
                stop_func()
                time.sleep(0.2)
            except Exception as e:
                print(f"[CONTROLLER] ❌ Error deteniendo {name}: {e}")
        
        # Limpiar GPIO
        try:
            GPIO.cleanup()
            print("[CONTROLLER] ✅ GPIO limpiado")
        except Exception as e:
            print(f"[CONTROLLER] ❌ Error limpiando GPIO: {e}")
        
        print("[CONTROLLER] ✅ Recursos liberados. Saliendo.")

# Uso en tu main.py
if __name__ == "__main__":
    # Ejemplo de uso
    from API.register_periods import RegisterPeriods  # Ajusta según tu estructura
    
    try:
        service_periods = RegisterPeriods()  # Tu servicio de periodos
        controller = RaspberryController(service_periods)
        controller.start()
    except Exception as e:
        print(f"❌ Error iniciando aplicación: {e}")
        GPIO.cleanup()  # Limpiar GPIO en caso de error