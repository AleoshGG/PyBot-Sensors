#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
from hx711 import HX711

# Pines BCM donde conectaste DT y SCK
DOUT_PIN = 20   # DT (DOUT) del HX711
SCK_PIN  = 21   # SCK del HX711

# Factor de calibración (ajústalo con un peso conocido)
CALIBRATION_FACTOR = 7050.0
# Número de lecturas para promediar
default_readings = 10

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Inicializa HX711
    hx = HX711(DOUT_PIN, SCK_PIN)
    hx.reset()
    time.sleep(0.1)

    # Calcula offset de tara (sin carga)
    print("Calculando offset de tara...")
    raw_list = hx.get_raw_data(times=default_readings)
    if raw_list is None:
        print("Error al obtener offset, usando 0")
        raw_offset = 0
    else:
        # Si devuelve lista de canales, calculamos promedio
        if isinstance(raw_list, list):
            raw_offset = sum(raw_list) / len(raw_list)
        else:
            raw_offset = raw_list
    raw_offset = float(raw_offset)
    print(f"Offset (media raw) = {raw_offset}")
    return hx, raw_offset

def loop(hx, raw_offset):
    try:
        while True:
            # Lectura cruda promedio
            raw_list = hx.get_raw_data(times=default_readings)
            if raw_list is None:
                print("Error al leer raw data")
                continue
            # convierte raw_list a scalar promedio
            if isinstance(raw_list, list):
                raw = sum(raw_list) / len(raw_list)
            else:
                raw = raw_list

            # Calcula peso neto
            net = raw - raw_offset
            weight = net / CALIBRATION_FACTOR

            print(f"Raw: {raw:>8.2f} | Neto: {net:>8.2f} | Peso: {weight:0.2f} g")

            hx.power_down()
            hx.power_up()
            time.sleep(1.0)

    except (KeyboardInterrupt, SystemExit):
        print("\nTerminando y limpiando GPIO...")
        GPIO.cleanup()

if __name__ == "__main__":
    hx711, offset = setup()
    loop(hx711, offset)
