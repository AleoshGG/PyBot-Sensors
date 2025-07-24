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
    """
    def __init__(self, pin: int, duration: float):
        self.pin = pin
        self.duration = duration
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = relé apagado

    def trigger(self):
        """Enciende el relé durante self.duration segundos en un hilo separado."""
        threading.Thread(target=self._cycle, daemon=True).start()

    def _cycle(self):
        GPIO.output(self.pin, GPIO.LOW)   # LOW = relé encendido
        time.sleep(self.duration)
        GPIO.output(self.pin, GPIO.HIGH)  # HIGH = relé apagado

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
        relay_duration = float(os.getenv('RELAY_DURATION', '12'))
        self.relay = RelayManager(relay_pin, relay_duration)

        # Umbral detección
        self.CAM_CONF_THRESHOLD = float(os.getenv('CAM_CONF_THRESHOLD', '0.5'))

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

    def _hook_detections(self):
        """Envuelve process_detections para enviar comando y disparar relé."""
        original = self.handler.process_detections
        def hooked(detections):
            original(detections)
            for det in detections:
                if det.get('conf', 0) >= self.CAM_CONF_THRESHOLD:
                    self.cmd_queue.put(self.OBJECT_COMMAND)
                    self.relay.trigger()
                    break
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
            threading.Thread(target=self.backup.start,  name='Backup',    daemon=True),
        ]
        for t in threads:
            t.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[MAIN] Detención solicitada")
            self.stop_event.set()
            time.sleep(0.5)
            GPIO.cleanup()
            print("[MAIN] Recursos liberados. Saliendo.")
