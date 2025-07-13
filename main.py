import threading
from Sensors.Camera import CameraReader
from Sensors.GPS import GPSReader
from Sensors.HX711 import HX711Reader
from dotenv import load_dotenv
from API.registerPeriods import RegisterPeriods
# from Sensors.camera import CameraReader

if __name__ == '__main__':
    # Cargar las variables de enorno
    load_dotenv()
    r = RegisterPeriods()
    
    firstPeriod = r.statusPeriod()

    if firstPeriod:
        r.createNewPeriod()
        r.createVoidReading()
    else: 
        print("Calcula lo anterior")
        r.completeLastPeriod()

    # Instanciar lectores
    gps = GPSReader(serviceRegister=r)
    hx = HX711Reader(serviceRegister=r)
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