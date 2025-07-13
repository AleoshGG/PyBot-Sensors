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