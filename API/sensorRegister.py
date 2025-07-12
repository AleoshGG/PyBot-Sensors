import requests

class SensorRegisterService:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8080/sensors"
        self.session = requests.Session()
    
    def registerWeightData(self, payload: dict) -> requests.Response:
        try:
            resp = self.session.post(self.base_url + "/weight", json = payload)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[FetchAPI] Error creando recurso: {e}")
            return resp.json()