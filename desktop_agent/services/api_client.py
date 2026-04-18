import logging
import httpx
from utils.secure_store import SecureStore

logger = logging.getLogger(__name__)

BASE_URL = "https://mdm-api.yourcompany.com/api/v1"


class ApiClient:
    def __init__(self):
        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=15.0,
            verify=True,  # enforce HTTPS cert validation
        )

    def _headers(self) -> dict:
        token = SecureStore.get("device_token")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def post(self, path: str, data: dict) -> dict | None:
        try:
            resp = self._client.post(path, json=data, headers=self._headers())
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                SecureStore.delete("device_token")
            logger.warning(f"POST {path} failed: {e.response.status_code}")
        except Exception as e:
            logger.debug(f"POST {path} offline/error: {e}")
        return None

    def get(self, path: str, params: dict | None = None) -> dict | None:
        try:
            resp = self._client.get(path, params=params, headers=self._headers())
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.debug(f"GET {path} error: {e}")
        return None

    def close(self):
        self._client.close()
