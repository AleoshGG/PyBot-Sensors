# MQTT/toServerMQTT.py
import paho.mqtt.client as mqtt
import json



class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(USERNAME, PASSWORD)
        try:
            self.client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            self.client.loop_start()
            print("[MQTT] Conectado al broker")
        except Exception as e:
            print(f"[MQTT] Error conectando al broker: {e}")

    def send(self, payload: dict) -> None:
        try:
            message = json.dumps(payload)
            self.client.publish(TOPIC, message)
            print(f"[MQTT] Publicado en {TOPIC}: {message}")
        except Exception as e:
            print(f"[MQTT] Error publicando: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("[MQTT] Desconectado")
