import serial
import pynmea2

def read_gps():
    # Open serial connection to GPS module
    gps_serial = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)

    while True:
        try:
            line = gps_serial.readline().decode("ascii", errors="replace")
            if line.startswith("$GPGGA"):
                msg = pynmea2.parse(line)
                print(f"Latitude: {msg.latitude}, Longitude: {msg.longitude}")
                print(f"Altitude: {msg.altitude} {msg.altitude_units}")
        except pynmea2.ParseError as e:
            print(f"Parse error: {e}")
        except KeyboardInterrupt:
            print("Exiting...")
            break

if __name__ == "__main__":
    read_gps()
