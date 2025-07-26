#!/usr/bin/env python3
"""
Programa de prueba para el RelayManager
Permite probar manualmente el encendido/apagado del relé
"""

import threading
import time
import RPi.GPIO as GPIO
import os
from dotenv import load_dotenv

class RelayManager:
    """
    Gestiona la activación de un relé en un pin GPIO durante un tiempo dado.
    """
    def __init__(self, pin: int, duration: float):
        self.pin = pin
        self.duration = duration
        self.is_active = False
        self.last_trigger_time = 0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.monitor_thread = None
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = relé apagado
        print(f"[RELAY] Inicializado en pin {pin}, duración {duration}s")
        
        # Iniciar hilo monitor
        self._start_monitor()

    def trigger(self):
        """Activa el relé o extiende su tiempo de activación."""
        with self.lock:
            current_time = time.time()
            self.last_trigger_time = current_time
            
            if not self.is_active:
                self._turn_on()
            else:
                print(f"[RELAY] Tiempo extendido - último trigger: {current_time:.2f}")

    def _turn_on(self):
        """Enciende el relé físicamente."""
        GPIO.output(self.pin, GPIO.LOW)  # LOW = relé encendido
        self.is_active = True
        print("[RELAY] ✅ ENCENDIDO")

    def _turn_off(self):
        """Apaga el relé físicamente."""
        GPIO.output(self.pin, GPIO.HIGH)  # HIGH = relé apagado
        self.is_active = False
        print("[RELAY] ❌ APAGADO")

    def _start_monitor(self):
        """Inicia el hilo monitor."""
        self.monitor_thread = threading.Thread(target=self._monitor_relay, daemon=True)
        self.monitor_thread.start()

    def _monitor_relay(self):
        """Hilo que verifica periódicamente si debe apagar el relé."""
        while not self.stop_event.is_set():
            time.sleep(0.5)
            
            with self.lock:
                if self.is_active:
                    current_time = time.time()
                    time_since_last_trigger = current_time - self.last_trigger_time
                    
                    if time_since_last_trigger >= self.duration:
                        print(f"[RELAY] Sin actividad por {time_since_last_trigger:.1f}s - Apagando")
                        self._turn_off()

    def manual_on(self):
        """Enciende el relé manualmente (sin timer)."""
        with self.lock:
            GPIO.output(self.pin, GPIO.LOW)
            self.is_active = True
            print("[RELAY] 🔧 ENCENDIDO MANUAL")

    def manual_off(self):
        """Apaga el relé manualmente."""
        with self.lock:
            GPIO.output(self.pin, GPIO.HIGH)
            self.is_active = False
            self.last_trigger_time = 0  # Reset timer
            print("[RELAY] 🔧 APAGADO MANUAL")

    def get_status(self):
        """Retorna el estado actual del relé."""
        return "ENCENDIDO" if self.is_active else "APAGADO"

    def cleanup(self):
        """Limpia los recursos del relé."""
        print("[RELAY] Iniciando limpieza...")
        self.stop_event.set()
        
        with self.lock:
            if self.is_active:
                GPIO.output(self.pin, GPIO.HIGH)
                self.is_active = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
        
        GPIO.setup(self.pin, GPIO.IN)
        print(f"[RELAY] Pin {self.pin} limpiado")

def print_menu():
    """Muestra el menú de opciones."""
    print("\n" + "="*50)
    print("🔌 PROGRAMA DE PRUEBA DE RELÉ")
    print("="*50)
    print("1. Activar relé (con timer automático)")
    print("2. Encender relé manual")
    print("3. Apagar relé manual")
    print("4. Ver estado del relé")
    print("5. Prueba automática (encender 5s)")
    print("6. Prueba de detección continua")
    print("0. Salir")
    print("-"*50)

def automatic_test(relay, duration=5):
    """Prueba automática: enciende por X segundos y se apaga solo."""
    print(f"\n🤖 PRUEBA AUTOMÁTICA: Encendiendo por {duration} segundos...")
    
    # Crear una instancia temporal con duración específica
    test_relay = RelayManager(relay.pin, duration)
    test_relay.trigger()
    
    print(f"⏱️  Esperando {duration} segundos...")
    time.sleep(duration + 1)  # Esperar un poco más para ver el apagado
    
    test_relay.cleanup()
    print("✅ Prueba automática completada")

def continuous_detection_test(relay):
    """Simula detecciones continuas durante 10 segundos."""
    print("\n🔄 PRUEBA DE DETECCIÓN CONTINUA:")
    print("Simulando detecciones cada 2 segundos durante 10 segundos...")
    print("El relé debería mantenerse encendido y apagarse 12s después de la última detección")
    
    start_time = time.time()
    detection_interval = 2
    test_duration = 10
    
    while time.time() - start_time < test_duration:
        relay.trigger()
        print(f"🎯 Detección simulada - Estado: {relay.get_status()}")
        time.sleep(detection_interval)
    
    print(f"🏁 Detecciones terminadas. El relé debería apagarse en ~12 segundos...")
    print("Esperando para verificar apagado automático...")

def main():
    # Cargar configuración
    load_dotenv()
    
    # Configuración del relé
    relay_pin = int(os.getenv('RELAY_PIN', '17'))
    relay_duration = float(os.getenv('RELAY_DURATION', '12'))
    
    print(f"🚀 Iniciando programa de prueba...")
    print(f"📍 Pin GPIO: {relay_pin}")
    print(f"⏰ Duración automática: {relay_duration}s")
    
    # Crear instancia del relé
    relay = RelayManager(relay_pin, relay_duration)
    
    try:
        while True:
            print_menu()
            choice = input("Selecciona una opción: ").strip()
            
            if choice == '1':
                print(f"\n🔥 Activando relé con timer de {relay_duration}s...")
                relay.trigger()
                print(f"⏱️  El relé se apagará automáticamente en {relay_duration}s si no hay más activaciones")
                
            elif choice == '2':
                print("\n🔧 Encendiendo relé manualmente (sin timer)...")
                relay.manual_on()
                
            elif choice == '3':
                print("\n🔧 Apagando relé manualmente...")
                relay.manual_off()
                
            elif choice == '4':
                status = relay.get_status()
                print(f"\n📊 Estado actual del relé: {status}")
                if relay.is_active and relay.last_trigger_time > 0:
                    time_remaining = relay.duration - (time.time() - relay.last_trigger_time)
                    if time_remaining > 0:
                        print(f"⏰ Tiempo restante: {time_remaining:.1f}s")
                    else:
                        print("⏰ Debería apagarse pronto...")
                
            elif choice == '5':
                automatic_test(relay)
                
            elif choice == '6':
                continuous_detection_test(relay)
                
            elif choice == '0':
                break
                
            else:
                print("❌ Opción inválida")
                
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupción detectada...")
        
    finally:
        print("\n🧹 Limpiando recursos...")
        relay.cleanup()
        GPIO.cleanup()
        print("✅ Programa terminado correctamente")

if __name__ == "__main__":
    main()