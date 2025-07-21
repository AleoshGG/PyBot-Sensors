import socket
import requests

class Backup:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8080/backup"
        self.session = requests.Session()

    def check_internet_conection(self, host="8.8.8.8", port=53, timeout=3):
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            return False
    
    def start(self):
        connection = self.check_internet_conection()

        if connection:
            print("Se hace el backup")
            try:
                resp = self.session.get(self.base_url + "/")
                resp.raise_for_status()
                print(resp.json())
            except requests.RequestException as e:
                print(f"[FetchAPI] Error al hacer el backup: {e}")
                print(resp.json())
        else:
            print("Baackup no disponible")