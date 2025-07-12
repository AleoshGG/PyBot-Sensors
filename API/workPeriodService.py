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
        
    def createNewPeriod(self, payload: dict) -> requests.Response:
        try:
            resp = self.session.post(self.base_url + "/", json = payload)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[FetchAPI] Error creando recurso: {e}")
            return resp.json()
    
    """ 
    

    def update(self, id: int, payload: dict) -> bool:
        PUT /resource/{id}
        try:
            resp = self.session.put(self._url(str(id)), json=payload)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[FetchAPI] Error actualizando id={id}: {e}")
            return False

    def delete(self, id: int) -> bool:
        DELETE /resource/{id}
        try:
            resp = self.session.delete(self._url(str(id)))
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[FetchAPI] Error eliminando id={id}: {e}")
            return False """
           
if __name__ == "__main__":
    serviceAPI = WorkPeriodService()
    print(serviceAPI.getLastHourPeriod())