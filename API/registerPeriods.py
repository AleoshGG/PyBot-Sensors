from API.workPeriodService import WorkPeriodService
from API.sensorRegister import SensorRegisterService
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

class RegisterPeriods:
    def __init__(self):
        load_dotenv()
        self.serviceWorkPeriods = WorkPeriodService()
        self.serciceSensors = SensorRegisterService()
        self.prototype_id = os.getenv("ID_PROTOTYPE")
        self.actual_period_id = 0
        self.last_period_id = 0
        self.last_hour_period = ''
        self.w_id_CANS = 0
        self.w_id_PET = 0
    
    def statusPeriod(self) -> bool: 
        res = self.serviceWorkPeriods.getLastHourPeriod()

        if res.get('last_period').get('period_id') == 0:
            return True
        
        self.last_period_id = res.get('last_period').get('period_id')
        self.last_hour_period = res.get('last_period').get('last_hour')
        return False
    
    def createNewPeriod(self): 
        # Crear parámetros necesarios
        start_hour = datetime.now(timezone.utc)
        end_hour = ''
        day_work = start_hour.strftime('%a')
        
        d_body = {
            "period_id": 0,
            "start_hour": start_hour.isoformat(),
            "end_hour": end_hour,
            "day_work": day_work,
            "prototype_id": self.prototype_id
        }
        
        res = self.serviceWorkPeriods.createNewPeriod(d_body)
        id = res.get('data').get('work_periods_id')

        if  id != 0:
            self.actual_period_id = id
        else:
            print("Ocurrio un error al crear el periodo")
    
    def registerWeigh(self, weight: float):
        # Crear parámetros necesarios
        hour_period = datetime.now(timezone.utc).isoformat()
        weight = round(weight, 4)
        
        d_body = {
            "weight_data_id": 0,
            "period_id": self.actual_period_id,
            "Hour_period": hour_period,
            "Weight": weight,
        }

        self.serciceSensors.registerWeightData(d_body)

    def registerGPS(self, data: dict):
    
        
        d_body = {
            "gps_data_id": 0,
            "period_id": self.actual_period_id or 0,
            "latitude": data.get("lat") or 0.0,
            "longitude": data.get("lon") or 0.0,
            "altitude": data.get("alt") or 0.0,
            "speed": data.get("spd") or 0.0,
            "date_gps": data.get("date") or '2015-07-13',
            "hour_UTC": data.get("date") + "T" + data.get('UTC')+"+00:00" or '2025-07-12T20:14:07.057608+00:00'
        }

        self.serciceSensors.registerGPSData(d_body)

    
    def createVoidReading(self):
        d_body = {
            "period_id": self.actual_period_id,
            "distance_traveled": 0.0,
            "weight_waste": 0.0,
        }
        self.serviceWorkPeriods.createNewReading(d_body)

    def completeLastPeriod(self):
        id =  str(self.last_period_id)
        res = self.serviceWorkPeriods.getDistanceAndWeight(id)
        print(res)

        res1 = self.serviceWorkPeriods.updateLastPeriod(
            self.last_hour_period,
            id=str(self.last_period_id))
        print(res1)

        d_body = {
            "period_id": self.last_period_id,
            "distance_traveled": res.get('last_reading').get('distance_traveled'),
            "weight_waste": res.get('last_reading').get('weight_waste'),
        }

        res = self.serviceWorkPeriods.updateLastReadig(d_body)
        print(res)
        self.createNewPeriod()
        self.createVoidReading()

    def createWasteCollection(self, waste_id):
        d_body = {
            "waste_collection_id": 0,
            "period_id": self.actual_period_id,
            "amount": 0,
            "waste_id": waste_id
        }

        res = self.serciceSensors.registerWasteCollection(d_body)
        if waste_id == 1:
            self.w_id_PET = res.get('data').get('waste_collection_id')
        else:
            self.w_id_CANS = res.get('data').get('waste_collection_id')
    
    def updateWasteCollection(self, waste_collection_id: int):
        res = self.serciceSensors.updateWasteCollection(waste_collection_id)
        print(res)

    def getIdWasteCollectionPET(self):
        return self.w_id_PET
    
    def getIdWasteCollectionCANS(self):
        return self.w_id_CANS


"""
if __name__ == "__main__":
    r = RegisterPeriods()

    if r.statusPeriod():
        print("Hacer el primer periodo")
        r.createNewPeriod()
        r.createVoidReading()
    else:
        print("Proceder a calcular el ultimo periodo")
        r.completeLastPeriod()"""