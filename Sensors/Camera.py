import base64
import os
import threading, cv2, torch
import time
from ultralytics import YOLO

from MQTT.connection import RabbitMQPublisher

class CameraReader:
    def __init__(self):
        self.mqtt = RabbitMQPublisher()
        self.prototype_id = os.getenv("ID_PROTOTYPE")
        self.model  = YOLO("models/YOLOv11.pt")  # o donde tengas tu modelo entrenado
        self.model.fuse()  # optimización opcional
        self.frame_lock = threading.Lock()
        self.latest_frame = None

    def capture_thread(self):
        try: 
            cap = cv2.VideoCapture(0)
            cap.set(3,320); cap.set(4,240)
            while True:
                ret, f = cap.read()
                if not ret: break
                with self.frame_lock:
                    self.latest_frame = f
        except Exception as e:
            print(f"[Camera] Error en la captura: {e}")
            time.sleep(1)

    def encode_image(self, frame):
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            return jpg_as_text
        except Exception as e:
            print(f"[Camera] Error codificando imagen: {e}")

    def start(self):
        try:
            t = threading.Thread(target=self.capture_thread, daemon=True)
            t.start()

            while True:
                with self.frame_lock:
                    f = self.latest_frame.copy() if self.latest_frame is not None else None
                if f is None: continue

                # reescala e infiere
                small = cv2.resize(f, (256,256))
                results = self.model(small)  # batch de 1
                
                detections = []
                for box in results[0].boxes:
                    detections.append({
                        "cls": int(box.cls[0]),
                        "conf": float(box.conf[0])
                    })
                print(f"[Camera] Detecciones: {detections}")

                ann = results[0].plot()
                img = cv2.resize(ann, (320,240))
                encoded_img = self.encode_image(img)

                if encoded_img: 
                    payload = {
                        "prototype_id": self.prototype_id,
                        "detections": detections,
                        "image": encoded_img
                    }
                    self.mqtt.send(payload, routing_key='cam')

                #cv2.imshow("Async Fast YOLOv11", img)
                #if cv2.waitKey(1)==27: break
        except Exception as e:
            print(f"[Camera] Error: {e}")
            time.sleep(1)
        
