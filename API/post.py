import requests

API_URL = "https://tu-api.com/data"
TIMEOUT = 5

class FetchAPI:
    @staticmethod
    def send(payload: dict) -> bool:
        try:
            resp = requests.post(API_URL, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[FetchAPI] Error enviando datos: {e}")
            return False