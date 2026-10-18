"""TOPDIM serveri bilan ishlovchi HTTP mijoz.

Faqat Python'ning standart kutubxonasi (urllib) ishlatiladi — telefonda
ortiqcha paket kerak bo'lmaydi. urllib sinxron ishlaydi, shuning uchun har
bir so'rov ``asyncio.to_thread`` orqali alohida oqimda bajariladi: so'rov
ketayotganda ilova oynasi "qotib" qolmaydi.
"""

import asyncio
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

TIMEOUT_SECONDS = 15


class ApiError(Exception):
    """Server yoki tarmoq xatosi. ``message`` foydalanuvchiga ko'rsatiladi."""

    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def normalize_server_url(text: str) -> str:
    """"192.168.1.5:8080/" -> "http://192.168.1.5:8080"."""
    url = text.strip().rstrip("/")
    if url and "://" not in url:
        url = "http://" + url
    return url


def _ssl_context() -> ssl.SSLContext:
    """HTTPS uchun sertifikatlar. Android'da tizim sertifikatlari Python'ga
    ko'rinmaydi, shuning uchun ``certifi`` paketidagilari ishlatiladi."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


class TopdimApi:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = normalize_server_url(base_url)
        self.token = token

    # ------------------------------------------------------------------
    # Past darajadagi so'rov
    # ------------------------------------------------------------------
    def _request_sync(
        self, method: str, path: str, params: dict | None, body: dict | None, raw: bool
    ) -> Any:
        url = self.base_url + path
        if params:
            clean = {k: v for k, v in params.items() if v not in (None, "")}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)

        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=_ssl_context()) as response:
                payload = response.read()
                status = response.status
        except urllib.error.HTTPError as error:
            # Server xato qaytardi: matnini {"error": "..."} dan olamiz
            try:
                message = json.loads(error.read()).get("error") or f"Xato {error.code}"
            except ValueError:
                message = f"Server xatosi ({error.code})"
            raise ApiError(message, error.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ApiError(
                "Serverga ulanib bo'lmadi. Internetni va server manzilini tekshiring."
            ) from None

        if raw:
            return payload
        result = json.loads(payload) if payload else {}
        if isinstance(result, dict):
            result["_status"] = status
        return result

    async def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        body: dict | None = None,
        raw: bool = False,
    ) -> Any:
        return await asyncio.to_thread(self._request_sync, method, path, params, body, raw)

    # ------------------------------------------------------------------
    # API metodlari (serverdagi topdim/api/server.py bilan mos)
    # ------------------------------------------------------------------
    async def health(self) -> dict:
        return await self._request("GET", "/api/health")

    async def meta(self) -> dict:
        return await self._request("GET", "/api/meta")

    async def auth_start(self) -> dict:
        """{"code", "url", "expires_in"} qaytaradi."""
        return await self._request("POST", "/api/auth/start", body={})

    async def auth_check(self, code: str) -> str | None:
        """Token tayyor bo'lsa token, hali tasdiqlanmagan bo'lsa None."""
        result = await self._request("POST", "/api/auth/check", body={"code": code})
        return result.get("token") if result["_status"] == 200 else None

    async def logout(self) -> None:
        await self._request("POST", "/api/auth/logout", body={})

    async def items(self, query: str = "", category: str | None = None, page: int = 1) -> dict:
        return await self._request(
            "GET", "/api/items", params={"q": query, "category": category, "page": page}
        )

    async def item(self, item_id: int) -> dict:
        return await self._request("GET", f"/api/items/{item_id}")

    async def photo(self, item_id: int) -> bytes:
        return await self._request("GET", f"/api/items/{item_id}/photo", raw=True)

    async def create_item(self, payload: dict) -> dict:
        return await self._request("POST", "/api/items", body=payload)

    async def my_items(self, page: int = 1) -> dict:
        return await self._request("GET", "/api/my/items", params={"page": page})

    async def set_status(self, item_id: int, status: str) -> dict:
        return await self._request("POST", f"/api/items/{item_id}/status", body={"status": status})
