from dotenv import load_dotenv
import pika
import json
import os

load_dotenv()

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
EXCHANGE_NAME = 'amq.topic'
EXCHANGE_TYPE = 'topic'
DEFAULT_ROUTING_KEY = os.getenv('MQTT_TOPIC', 'sensors.info')

class RabbitMQPublisher:
    def __init__(self):
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            self.channel = self.connection.channel()
            self.channel.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type=EXCHANGE_TYPE,
                durable=True
            )
            print("[RabbitMQ] Conectado y exchange declarado")
        except Exception as e:
            print(f"[RabbitMQ] Error al conectar o declarar exchange: {e}")
            self.connection = None

    def send(self, payload: dict, routing_key: str = DEFAULT_ROUTING_KEY):
        if not self.connection or self.connection.is_closed:
            print("[RabbitMQ] Conexión no disponible")
            return
        try:
            message = json.dumps(payload)
            self.channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=message
            )
            print(f"[RabbitMQ] Enviado {routing_key}:{message}")
        except Exception as e:
            print(f"[RabbitMQ] Error publicando mensaje: {e}")

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("[RabbitMQ] Conexión cerrada")
