import threading
import time
import serial
import pynmea2
import os
from MQTT.connection import RabbitMQPublisher
from API.registerPeriods import RegisterPeriods
# from FetchAPI.fetchAPI import FetchAPI

class GPSReader:
    def __init__(self, serviceRegister: RegisterPeriods):
        self.register = serviceRegister
        self.mqtt = RabbitMQPublisher()
        self.prototype_id = os.getenv("ID_PROTOTYPE")

    @staticmethod
    def knots_to_kmph(knots: float) -> float:
        return knots * 1.852    

    def start(self):
        try:
            ser = serial.Serial("/dev/serial0", 9600, timeout=1)
        except Exception as e:
            print(f"[GPS] No se pudo abrir puerto: {e}")
            return

        last_data = {}

        while True:
            try:
                line = ser.readline().decode('ascii', errors='replace')

                if line.startswith('$GPRMC'):
                    msg = pynmea2.parse(line)
                    last_data['prototype_id'] = self.prototype_id
                    last_data['lat'] = msg.latitude
                    last_data['lon'] = msg.longitude
                    speed_knots = msg.spd_over_grnd or 0.0
                    last_data['spd'] = round(self.knots_to_kmph(speed_knots), 2)
                    last_data['date'] = msg.datestamp.strftime('%Y-%m-%d') if msg.datestamp else None
                    last_data['UTC'] = msg.timestamp.strftime('%H:%M:%S') if msg.timestamp else None

                elif line.startswith('$GPGGA'):
                    msg = pynmea2.parse(line)
                    last_data['alt'] = msg.altitude
                    # asegurarse de que sea entero
                    try:
                        last_data['sats'] = int(msg.num_sats)
                    except ValueError:
                        last_data['sats'] = None

                # Mostrar y enviar datos solo si tenemos coordenadas
                if 'lat' in last_data and 'lon' in last_data:
                    print(f"[GPS] {last_data}")

                    self.mqtt.send(payload=last_data, routing_key="neo")
                    self.register.registerGPS(last_data)
                
                time.sleep(5)
            except Exception as e:
                print(f"[GPS] Error: {e}")
                time.sleep(1)