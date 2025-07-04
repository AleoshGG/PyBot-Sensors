import os
import time
from hx711 import HX711
from MQTT.connection import RabbitMQPublisher
# from FetchAPI.fetchAPI import FetchAPI

class HX711Reader:
    def __init__(self):
        self.prototype_id = os.getenv("ID_PROTOTYPE")
        self.mqtt = RabbitMQPublisher()
        self.hx = HX711(20, 21)
        self.hx.reset()
        time.sleep(0.1)
        raw = self.hx.get_raw_data(times=10)
        self.offset = sum(raw)/len(raw) if raw else 0

    def start(self):
        while True:
            try:
                raw = sum(self.hx.get_raw_data(times=10))/10
                weight = (raw - self.offset)/7050.0
                data = {'prototype_id': self.prototype_id,'weight_g': weight}
                print(f"[HX711] {data}")
                self.mqtt.send(data, routing_key="hx")
                #FetchAPI.send(data)
                self.hx.power_down()
                self.hx.power_up()
                time.sleep(1)
            except Exception as e:
                print(f"[HX711] Error: {e}")
                time.sleep(1)