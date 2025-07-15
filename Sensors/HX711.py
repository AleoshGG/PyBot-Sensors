import os
import time
from hx711 import HX711
from MQTT.connection import RabbitMQPublisher
from API.registerPeriods import RegisterPeriods
from Sensors.WasteHandler import WasteHandler

class HX711Reader:
    def __init__(self, serviceRegister: RegisterPeriods, h: WasteHandler):
        self.prototype_id = os.getenv("ID_PROTOTYPE")
        self.mqtt = RabbitMQPublisher()
        self.hx = HX711(20, 21)
        self.serviceRegister = serviceRegister
        self.handler = h
        # self.hx.reset()
        # time.sleep(0.1)
        # raw = self.hx.get_raw_data(times=10)
        self.offset = -356380.04# sum(raw)/len(raw) if raw else 0
        self.scale = 101.6037

    def start(self):
        while True:
            try:
                raws = self.hx.get_raw_data(times=20)
                raw_avg = sum(raws) /len(raws)
                diff = raw_avg - self.offset
                weight = diff / self.scale
                data = {'prototype_id': self.prototype_id,'weight_g': weight}
                print(f"[HX711] {data}")
                self.mqtt.send(data, routing_key="hx")
                
                if weight >= 0:
                    self.serviceRegister.registerWeigh(weight)
                    self.handler.process_weight(weight)

                self.hx.power_down()          
                time.sleep(5)      
                self.hx.power_up()
            except Exception as e:
                print(f"[HX711] Error: {e}")
                time.sleep(1)