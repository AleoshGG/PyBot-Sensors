import threading
import serial
import pynmea2
import time
import RPi.GPIO as GPIO
from hx711 import HX711

# Configuration
GPS_PORT = "/dev/serial0"
GPS_BAUDRATE = 9600
GPS_TIMEOUT = 1

DOUT_PIN = 20  # HX711 DT
SCK_PIN = 21   # HX711 SCK
CALIBRATION_FACTOR = 7050.0
READINGS = 10

# Event to signal threads to stop
stop_event = threading.Event()


def read_gps():
    try:
        gps_serial = serial.Serial(GPS_PORT, baudrate=GPS_BAUDRATE, timeout=GPS_TIMEOUT)
    except serial.SerialException as e:
        print(f"[GPS] Error opening serial port: {e}")
        return

    while not stop_event.is_set():
        try:
            line = gps_serial.readline().decode("ascii", errors="replace")
            if line.startswith("$GPGGA"):
                msg = pynmea2.parse(line)
                print(f"[GPS] Latitude: {msg.latitude}, Longitude: {msg.longitude}")
                print(f"[GPS] Altitude: {msg.altitude} {msg.altitude_units}")
        except pynmea2.ParseError as e:
            print(f"[GPS] Parse error: {e}")
        except Exception as e:
            print(f"[GPS] Unexpected error: {e}")
            time.sleep(1)

    print("[GPS] Thread stopped")
    gps_serial.close()


def setup_hx711():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    hx = HX711(DOUT_PIN, SCK_PIN)
    hx.reset()
    time.sleep(0.1)

    print("[HX711] Calculating tare offset...")
    raw_list = hx.get_raw_data(times=READINGS)
    if raw_list is None:
        print("[HX711] Error obtaining offset, defaulting to 0")
        raw_offset = 0.0
    else:
        raw_offset = float(sum(raw_list) / len(raw_list))
    print(f"[HX711] Offset = {raw_offset}")
    return hx, raw_offset


def read_hx711():
    try:
        hx, offset = setup_hx711()
    except Exception as e:
        print(f"[HX711] Setup error: {e}")
        return

    while not stop_event.is_set():
        try:
            raw_list = hx.get_raw_data(times=READINGS)
            if raw_list is None:
                print("[HX711] Read error")
                continue
            raw = float(sum(raw_list) / len(raw_list))
            net = raw - offset
            weight = net / CALIBRATION_FACTOR
            print(f"[HX711] Raw: {raw:.2f} | Net: {net:.2f} | Weight: {weight:.2f} g")

            hx.power_down()
            hx.power_up()
            time.sleep(1.0)
        except Exception as e:
            print(f"[HX711] Unexpected error: {e}")
            time.sleep(1)

    print("[HX711] Thread stopped")
    GPIO.cleanup()


def main():
    # Create threads for each sensor
    gps_thread = threading.Thread(target=read_gps, name="GPS_Thread")
    hx_thread = threading.Thread(target=read_hx711, name="HX711_Thread")

    # Start threads
    gps_thread.start()
    hx_thread.start()

    try:
        # Keep main thread alive until interrupted
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[MAIN] KeyboardInterrupt received. Stopping threads...")
        stop_event.set()

    # Wait for threads to finish
    gps_thread.join()
    hx_thread.join()
    print("[MAIN] All threads stopped. Exiting.")


if __name__ == "__main__":
    main()
