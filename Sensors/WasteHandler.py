import threading
import time
from datetime import datetime, timedelta
from API.registerPeriods import RegisterPeriods

class WasteHandler:
    def __init__(self, service_register: RegisterPeriods, weight_threshold=30.0, expire_seconds=15):
        """
        service_register: instancia de RegisterPeriods
        weight_threshold: mínimo aumento de peso (g) para contar un objeto
        expire_seconds: tiempo tras detección para caducar flags
        """
        self.service = service_register
        self.service.createWasteCollection(1) # PET
        self.id_PET = self.service.getIdWasteCollectionPET()
        self.service.createWasteCollection(2) # CANS
        self.id_CANS = self.service.getIdWasteCollectionCANS()

        self.weight_threshold = weight_threshold
        self.expire_delta = timedelta(seconds=expire_seconds)

        self.lock = threading.Lock()
        self.is_can = False
        self.is_pet = False
        self.detect_time = None

        self.last_weight = 0.0

    def process_detections(self, detections: list[dict]):
        """Llamar desde CameraReader tras cada inferencia."""
        now = datetime.utcnow()
        with self.lock:
            # Reset flags si han caducado
            if self.detect_time and now - self.detect_time > self.expire_delta:
                self.is_can = False
                self.is_pet = False

            # Si detecta varios tipos, damos por hecho ambos
            cls_list = [d["cls"] for d in detections]
            if len(detections) > 2:
                self.is_can = True
                self.is_pet = True
            elif cls_list and cls_list[0] == 0:
                # suponiendo 0 = PET
                self.is_pet = True
            else:
                # cualquier otro = can
                self.is_can = True

            self.detect_time = now
            # Debug
            print(f"[Handler] Detección -> is_pet={self.is_pet}, is_can={self.is_can} at {self.detect_time.isoformat()}")

    def process_weight(self, weight: float):
        """Llamar desde HX711Reader tras cada lectura de peso."""
        now = datetime.utcnow()
        with self.lock:
            delta = weight - self.last_weight
            # Solo consideramos aumentos positivos
            if delta >= self.weight_threshold and self.detect_time:
                elapsed = now - self.detect_time
                if elapsed <= self.expire_delta:
                    # Se concreta un residuo
                    if self.is_pet:
                        print(f"[Handler] +1 PET (Δweight={delta:.2f}g)")
                        self.service.updateWasteCollection(self.id_PET)   # método que insertaría PET
                        self.is_pet = False
                    if self.is_can:
                        print(f"[Handler] +1 Can (Δweight={delta:.2f}g)")
                        self.service.updateWasteCollection(self.id_CANS)    # método que insertaría Can
                        self.is_can = False

                    # Tras concreción, borramos también detect_time para esperar nueva detección
                    self.detect_time = None

            # Caducado sin concreción
            if self.detect_time and now - self.detect_time > self.expire_delta:
                print("[Handler] Detección caducada sin peso, reseteando flags")
                self.is_can = False
                self.is_pet = False
                self.detect_time = None

            self.last_weight = weight

# -------------------------
# Ejemplo de integración:
# Suponiendo que en main.py crees:
#
# handler = WasteHandler(service_register=r)
#
# Y luego en cada lector:
#   CameraReader:
#       handler.process_detections(detections)
#
#   HX711Reader:
#       handler.process_weight(weight)
#
# Donde `r.registerWeighPET()` y `r.registerWeighCan()` encapsulan la lógica de inserción en BD.
