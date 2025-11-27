import base64
import requests
import os
import threading, cv2
import time
from Sensors.WasteHandler import WasteHandler

class CameraReader:
    def __init__(self, h: WasteHandler):
        self.handler = h
        self.prototype_id = os.getenv("ID_PROTOTYPE")
        self.api_url = "https://pybot.aleosh.online/detections/api/v1/detect"

        self.frame_queue = threading.Queue(maxsize=3)
        self.is_running = True

        # Session HTTP
        self.session = requests.Session()
        
        # Estadísticas
        self.stats = {
            'frames_captured': 0,
            'frames_processed': 0,
            'requests_failed': 0,
            'last_stats_time': time.time()
        }


    def capture_thread(self):
        """Hilo dedicado a captura de frames"""
        try: 
            cap = cv2.VideoCapture(0)
            cap.set(3, 320)
            cap.set(4, 240)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Buffer mínimo para baja latencia
            cap.set(cv2.CAP_PROP_FPS, 10)  # Limitar a 10 FPS
            
            print("[Camera] Cámara optimizada inicializada")
            
            while self.is_running:
                ret, frame = cap.read()
                if not ret: 
                    time.sleep(0.01)
                    continue
                
                # Mantener solo el frame más reciente
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                
                self.frame_queue.put(frame)
                self.stats['frames_captured'] += 1
                
        except Exception as e:
            print(f"[Camera] Error en captura: {e}")
            time.sleep(1)
        finally:
            if 'cap' in locals():
                cap.release()

    def processing_thread(self):
        """Hilo dedicado a procesamiento de frames"""
        while self.is_running:
            try:
                # Obtener frame de la cola
                frame = self.frame_queue.get(timeout=0.1)
                
                # Redimensionar
                small = cv2.resize(frame, (256, 256))
                
                # Enviar al servicio
                self.send_to_detection_service(small, frame)
                
                self.stats['frames_processed'] += 1
                
            except Exception:
                # Timeout de cola vacía
                continue

    def send_to_detection_service(self, processing_frame, original_frame):
        """Envía frame al servicio de detección"""
        try:
            # Codificar imagen
            _, buffer = cv2.imencode('.jpg', processing_frame)
            image_bytes = buffer.tobytes()
            
            # Preparar solicitud
            files = {'image': ('frame.jpg', image_bytes, 'image/jpeg')}
            data = {
                'prototype_id': self.prototype_id,
                'timestamp': str(time.time())
            }
            
            # Enviar al servicio
            response = self.session.post(
                self.api_url,
                files=files,
                data=data,
                timeout=2.0
            )
            
            if response.status_code == 200:
                result = response.json()
                detections = result['detections']
                
                # Procesar detecciones
                self.handler.process_detections(detections)
            else:
                self.stats['requests_failed'] += 1
                print(f"[Camera] Error HTTP: {response.status_code}")
                
        except Exception as e:
            self.stats['requests_failed'] += 1
            print(f"[Camera] Error procesando frame: {e}")

    def encode_image(self, frame):
        """Codificar imagen para MQTT"""
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"[Camera] Error codificando imagen: {e}")
            return None

    def get_stats(self):
        """Obtener estadísticas"""
        current_time = time.time()
        elapsed = current_time - self.stats['last_stats_time']
        
        fps_capture = self.stats['frames_captured'] / elapsed if elapsed > 0 else 0
        fps_processed = self.stats['frames_processed'] / elapsed if elapsed > 0 else 0
        
        # Resetear contadores
        self.stats['frames_captured'] = 0
        self.stats['frames_processed'] = 0
        self.stats['last_stats_time'] = current_time
        
        return {
            'fps_capture': round(fps_capture, 1),
            'fps_processed': round(fps_processed, 1),
            'requests_failed': self.stats['requests_failed'],
            'queue_size': self.frame_queue.qsize()
        }

    def start(self):
        """Iniciar todos los hilos"""
        print("[Camera] Iniciando cámara optimizada...")
        
        # Hilo de captura
        capture_thread = threading.Thread(target=self.capture_thread, daemon=True)
        capture_thread.start()
        
        # Hilo de procesamiento
        processing_thread = threading.Thread(target=self.processing_thread, daemon=True)
        processing_thread.start()
        
        # Hilo de monitoreo
        monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        monitoring_thread.start()
        
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def monitoring_loop(self):
        """Bucle de monitoreo de estadísticas"""
        while self.is_running:
            stats = self.get_stats()
            print(f"\r[Camera] Captura: {stats['fps_capture']} FPS | "
                  f"Procesados: {stats['fps_processed']} FPS | "
                  f"Fallos: {stats['requests_failed']} | "
                  f"Cola: {stats['queue_size']}", end="", flush=True)
            time.sleep(1)

    def stop(self):
        """Detener todos los hilos"""
        self.is_running = False
        self.session.close()
        print("\n[Camera] Cámara optimizada detenida")
        
