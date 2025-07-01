import paho.mqtt.client as mqtt

BROKER = "mqtt.broker.local"
PORT = 1883
TOPIC = "sensors/data"

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        try:
            self.client.connect(BROKER, PORT)
        except Exception as e:
            print(f"[MQTT] Error conectando: {e}")

    def send(self, payload: dict) -> None:
        try:
            self.client.publish(TOPIC, payload=str(payload))
        except Exception as e:
            print(f"[MQTT] Error publicando: {e}")