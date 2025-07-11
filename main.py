import threading
from Sensors.Camera import CameraReader
from Sensors.GPS import GPSReader
from Sensors.HX711 import HX711Reader
from dotenv import load_dotenv
# from Sensors.camera import CameraReader

if __name__ == '__main__':
    # Cargar las variables de enorno
    load_dotenv()
    # Instanciar lectores
    # gps = GPSReader()
    hx = HX711Reader()
    # cam = CameraReader()

    # Crear hilos
    threads = [
      #  threading.Thread(target=gps.start, name='GPS'),
        threading.Thread(target=hx.start, name='HX711'),
       # threading.Thread(target=cam.start, name='Camera'),
    ]

    # Iniciar hilos
    for t in threads:
        t.daemon = True  # Permite que el programa termine aunque queden hilos activos
        t.start()

    try:
        while True:
            pass  # Otras tareas de supervisión
    except KeyboardInterrupt:
        print("[MAIN] Saliendo...")