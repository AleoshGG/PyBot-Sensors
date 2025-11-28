from dotenv import load_dotenv
import pika
import json
import os

load_dotenv()

# Configuración cargada una sola vez
RABBITMQ_URL = os.getenv('RABBITMQ_URL')
EXCHANGE_NAME = 'amq.topic'
DEFAULT_ROUTING_KEY = os.getenv('MQTT_TOPIC', 'sensors.info')

class RabbitMQPublisher:
    def __init__(self):
        # Conexión directa sin try/except redundante
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            # No declarar exchange en cada conexión (asumimos que existe)
        except:
            self.connection = None

    def send(self, payload: dict, routing_key: str = DEFAULT_ROUTING_KEY):
        # Verificación ultra mínima
        if not self.connection:
            return False
            
        try:
            self.channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=json.dumps(payload)
            )
            return True
        except:
            return False

    def close(self):
        if self.connection:
            self.connection.close()