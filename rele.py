import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

RELE1 = 17
RELE2 = 27

GPIO.setup(RELE1, GPIO.OUT)
GPIO.setup(RELE2, GPIO.OUT)
print("Hola")
time.sleep(2)
# Apagar ambos relés
GPIO.output(RELE1, GPIO.HIGH)
GPIO.output(RELE2, GPIO.HIGH)
print("Puto")
time.sleep(2)
# Encender relé 1
GPIO.output(RELE1, GPIO.LOW)
print("Pinche limberg nalgona")
time.sleep(2)

# Encender relé 2
GPIO.output(RELE2, GPIO.LOW)
print("Andre mamponote superr pro")
time.sleep(2)

# Apagar ambos
GPIO.output(RELE1, GPIO.HIGH)
GPIO.output(RELE2, GPIO.HIGH)

GPIO.cleanup()
