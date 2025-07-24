from dotenv import load_dotenv
from API.registerPeriods import RegisterPeriods
from raspberry_controller import RaspberryController

if __name__ == '__main__':
    # Cargar variables de entorno
    load_dotenv()

    # Inicializar servicio de periodos
    r = RegisterPeriods()
    first_period = r.statusPeriod()

    if first_period:
        r.createNewPeriod()
        r.createVoidReading()
    else:
        r.completeLastPeriod()

    # Inicializar controlador que maneja ESP32 y relé, sensores y backup
    controller = RaspberryController(service_periods=r)
    controller.start()  # lanza internamente lectura de GPS, HX711, Cámara y Backup, además de la comunicación con ESP32 y relé
