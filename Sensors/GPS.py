import threading
import serial
import pynmea2
from MQTT.toServerMQTT import MQTTClient
from FetchAPI.fetchAPI import FetchAPI

class GPSReader:
    def __init__(self):
        self.mqtt = MQTTClient()

    def start(self):
        try:
            ser = serial.Serial("/dev/serial0", 9600, timeout=1)
        except Exception as e:
            print(f"[GPS] No se pudo abrir puerto: {e}")
            return

        while True:
            try:
                line = ser.readline().decode('ascii', errors='replace')
                if line.startswith('$GPGGA'):
                    msg = pynmea2.parse(line)
                    data = {
                        'lat': msg.latitude,
                        'lon': msg.longitude,
                        'alt': msg.altitude
                    }
                    print(f"[GPS] {data}")
                    self.mqtt.send(data)
                    FetchAPI.send(data)
            except Exception as e:
                print(f"[GPS] Error: {e}")