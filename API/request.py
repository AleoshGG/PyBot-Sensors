import os
from dotenv import load_dotenv
import requests

load_dotenv()

class FetchAPI:
    """
    Cliente genérico para interactuar con endpoints CRUD de un recurso.

    Ejemplo de uso:
        api = FetchAPI(resource="users")
        users = api.list(params={"page": 2})
        user = api.retrieve(id=1)
        created = api.create(payload={"name": "Leonel"})
        updated = api.update(id=1, payload={"name": "Nuevo Nombre"})
        deleted = api.delete(id=1)
    """

    def __init__(self, resource: str):
        base = os.getenv("API_BASE_URL", "http://127.0.0.1:8080/")
        self.base_url = base.rstrip("/")
        self.resource = resource.strip("/")
        self.session = requests.Session()

    def _url(self, uri: str = "") -> str:
        """Construye URL completa para el recurso y ruta adicional"""
        parts = [self.base_url, self.resource]
        if uri:
            parts.append(uri.strip("/"))
        return "/".join(parts)

    def list(self, params: dict = None) -> requests.Response:
        """GET /resource?params"""
        try:
            resp = self.session.get(self._url(), params=params)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[FetchAPI] Error listando datos: {e}")
            return None

    def retrieve(self, id: int, params: dict = None) -> requests.Response:
        """GET /resource/{id}?params"""
        try:
            resp = self.session.get(self._url(str(id)), params=params)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[FetchAPI] Error recuperando id={id}: {e}")
            return None

    def create(self, payload: dict) -> bool:
        """POST /resource"""
        try:
            resp = self.session.post(self._url(), json=payload)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[FetchAPI] Error creando recurso: {e}")
            return False

    def update(self, id: int, payload: dict) -> bool:
        """PUT /resource/{id}"""
        try:
            resp = self.session.put(self._url(str(id)), json=payload)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[FetchAPI] Error actualizando id={id}: {e}")
            return False

    def delete(self, id: int) -> bool:
        """DELETE /resource/{id}"""
        try:
            resp = self.session.delete(self._url(str(id)))
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[FetchAPI] Error eliminando id={id}: {e}")
            return False
