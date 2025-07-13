import requests

class WorkPeriodService:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8080/workPeriods"
        self.session = requests.Session()

    def getLastHourPeriod(self) -> requests.Response:
        try:
            resp = self.session.get(self.base_url + "/")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[FetchAPI] Error listando datos: {e}")
            return None
        
    def getDistanceAndWeight(self, id) -> requests.Response:
        try:
            resp = self.session.get(self.base_url + "/readingsGlobal?id=" + id)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[FetchAPI] Error listando datos: {e}")
            return None
        
    def createNewPeriod(self, payload: dict) -> requests.Response:
        try:
            resp = self.session.post(self.base_url + "/", json = payload)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[FetchAPI] Error creando recurso: {e}")
            return resp.json()
        
    def createNewReading(self, payload: dict) -> requests.Response:
        try:
            resp = self.session.post(self.base_url + "/readings", json = payload)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[FetchAPI] Error creando recurso: {e}")
            return resp.json()
    
    def updateLastPeriod(self, endHour, id) -> requests.Response:
        try:
            resp = self.session.patch(self.base_url + "/?endHour=" + endHour + "&id=" + id)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[FetchAPI] Error actualizando id={id}: {e}")
            return False
    
    def updateLastReadig(self, payload: dict) -> requests.Response:
        try:
            resp = self.session.put(self.base_url + "/", json = payload)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[FetchAPI] Error actualizando id={id}: {e}")
            return False