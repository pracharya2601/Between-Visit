import asyncio
import os

import requests

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "between-visit"
_storage_key = None


def _init_storage(force: bool = False) -> str:
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _request(method: str, path: str, **kwargs) -> requests.Response:
    for attempt in range(2):
        headers = {"X-Storage-Key": _init_storage(force=attempt == 1), **kwargs.pop("headers", {})}
        resp = requests.request(method, f"{STORAGE_URL}/objects/{path}", headers=headers, **kwargs)
        if resp.status_code != 404 or attempt == 1 or method == "GET":
            resp.raise_for_status()
            return resp
    return resp


def _put(path: str, data: bytes, content_type: str) -> dict:
    return _request("PUT", path, data=data, headers={"Content-Type": content_type}, timeout=120).json()


def _get(path: str) -> bytes:
    return _request("GET", path, timeout=60).content


async def put_object(path: str, data: bytes, content_type: str) -> dict:
    return await asyncio.to_thread(_put, f"{APP_NAME}/{path}", data, content_type)


async def get_object(storage_path: str) -> bytes:
    return await asyncio.to_thread(_get, storage_path)
