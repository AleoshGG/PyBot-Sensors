import cv2
import requests
import os
import threading
import time
from queue import Queue
import logging

logger = logging.getLogger("CameraReader")

class CameraReader:
    def __init__(self, waste_handler):
        self.handler = waste_handler
        self.prototype_id = os.getenv("ID_PROTOTYPE", "b036dbb930264780847bfd19")
        self.api_url = "https://pybot.aleosh.online/detections/api/v1/detect"
        
        # ✅ USAR NOMBRE FIJO DE LA CÁMARA
        self.camera_device = "/dev/videoPyBot"
        self.frame_queue = Queue(maxsize=3)
        self.is_running = True
        self.session = requests.Session()
        
        self.stats = {
            'frames_captured': 0,
            'frames_processed': 0,
            'requests_failed': 0,
            'last_stats_time': time.time()
        }
        
        # Verificar que la cámara esté disponible
        if not self._verify_camera():
            logger.error("❌ Cámara no disponible")
            self.is_running = False
            return
            
        logger.info(f"✅ Cámara inicializada en {self.camera_device}")

    def _verify_camera(self):
        """Verifica que la cámara esté disponible"""
        try:
            cap = cv2.VideoCapture(self.camera_device)
            if not cap.isOpened():
                logger.error(f"No se pudo abrir {self.camera_device}")
                # Intentar fallback a dispositivos tradicionales
                fallback_devices = ['/dev/video0', '/dev/video1']
                for device in fallback_devices:
                    cap = cv2.VideoCapture(device)
                    if cap.isOpened():
                        self.camera_device = device
                        logger.info(f"✅ Usando cámara fallback: {device}")
                        cap.release()
                        return True
                    cap.release()
                return False
            
            # Probar leer un frame
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                logger.error("Cámara no puede leer frames")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error verificando cámara: {e}")
            return False

    def capture_thread(self):
        """Hilo de captura usando dispositivo fijo"""
        logger.info(f"🎥 Iniciando captura en {self.camera_device}")
        
        cap = None
        try:
            cap = cv2.VideoCapture(self.camera_device)
            
            if not cap.isOpened():
                logger.error(f"❌ No se pudo abrir {self.camera_device}")
                return

            # Configuración óptima para Raspberry Pi
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            cap.set(cv2.CAP_PROP_FPS, 10)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            
            logger.info("✅ Cámara configurada - 320x240 @ 10FPS")
            
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("❌ Error leyendo frame")
                    time.sleep(0.1)
                    continue
                
                # Manejar cola de frames
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()  # Descarta frame viejo
                    except:
                        pass
                
                self.frame_queue.put(frame)
                self.stats['frames_captured'] += 1
                
        except Exception as e:
            logger.error(f"❌ Error en captura: {e}")
        finally:
            if cap:
                cap.release()
            logger.info("🔌 Cámara liberada")

    def processing_thread(self):
        """Hilo de procesamiento de frames"""
        logger.info("🔄 Iniciando procesamiento")
        
        while self.is_running:
            try:
                # Obtener frame con timeout
                frame = self.frame_queue.get(timeout=1.0)
                self._process_frame(frame)
                self.stats['frames_processed'] += 1
                
            except:
                continue  # Timeout normal

    def _process_frame(self, frame):
        """Procesa un frame individual"""
        try:
            # Redimensionar para inferencia
            small = cv2.resize(frame, (256, 256))
            
            # Codificar imagen
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 75]
            success, buffer = cv2.imencode('.jpg', small, encode_params)
            
            if not success:
                return
                
            image_bytes = buffer.tobytes()
            
            # Enviar al servicio de detección
            files = {'image': ('frame.jpg', image_bytes, 'image/jpeg')}
            data = {
                'prototype_id': self.prototype_id,
                'timestamp': str(time.time())
            }
            
            response = self.session.post(
                self.api_url,
                files=files,
                data=data,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                detections = result.get('detections', [])
                
                if detections:
                    logger.info(f"🎯 Detectados {len(detections)} objetos")
                    self.handler.process_detections(detections)
                # else: No hay detecciones, es normal
                    
            else:
                self.stats['requests_failed'] += 1
                logger.error(f"❌ Error HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.stats['requests_failed'] += 1
            logger.error("⏰ Timeout en detección")
        except Exception as e:
            self.stats['requests_failed'] += 1
            logger.error(f"❌ Error procesando frame: {e}")

    def get_stats(self):
        """Obtener estadísticas"""
        current_time = time.time()
        elapsed = current_time - self.stats['last_stats_time']
        
        if elapsed >= 1.0:
            fps_capture = self.stats['frames_captured'] / elapsed
            fps_processed = self.stats['frames_processed'] / elapsed
            
            self.stats['frames_captured'] = 0
            self.stats['frames_processed'] = 0
            self.stats['last_stats_time'] = current_time
            
            return {
                'fps_capture': round(fps_capture, 1),
                'fps_processed': round(fps_processed, 1),
                'requests_failed': self.stats['requests_failed'],
                'queue_size': self.frame_queue.qsize()
            }
        else:
            return {
                'fps_capture': 0.0,
                'fps_processed': 0.0,
                'requests_failed': self.stats['requests_failed'],
                'queue_size': self.frame_queue.qsize()
            }

    def start(self):
        """Iniciar todos los hilos"""
        if not self.is_running:
            return
            
        logger.info("🚀 Iniciando sistema de cámara")
        
        # Hilos
        self.capture_thread = threading.Thread(target=self.capture_thread, daemon=True)
        self.processing_thread = threading.Thread(target=self.processing_thread, daemon=True)
        self.monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        
        self.capture_thread.start()
        self.processing_thread.start()
        self.monitoring_thread.start()
        
        # Bucle principal
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def monitoring_loop(self):
        """Monitoreo de estadísticas"""
        while self.is_running:
            stats = self.get_stats()
            print(f"\r[Camera] Captura: {stats['fps_capture']} FPS | "
                  f"Procesados: {stats['fps_processed']} FPS | "
                  f"Fallos: {stats['requests_failed']} | "
                  f"Cola: {stats['queue_size']}", end="", flush=True)
            time.sleep(1)

    def stop(self):
        """Detener sistema"""
        logger.info("🛑 Deteniendo cámara")
        self.is_running = False
        time.sleep(1)
        self.session.close()