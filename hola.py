import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)

while True:
    if ser.in_waiting:
        data = ser.readline().decode().strip()
        print("Datoss: ", data)

        if data == "OBJETO_ENFRENTE": 
            ser.write(b"Espera basura\n")
    time.sleep(0.1)