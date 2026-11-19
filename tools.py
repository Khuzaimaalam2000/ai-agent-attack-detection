"""HTTP tools the agent can call against the Juice Shop target."""
import requests
from langchain_core.tools import tool

BASE_URL = "http://localhost:3000"
TIMEOUT = 10


def _headers(auth_token: str | None) -> dict:
    return {"Authorization": f"Bearer {auth_token}"} if auth_token else {}


@tool
def http_get(path: str, params: dict | None = None, auth_token: str | None = None) -> str:
    """GET request. Pass auth_token (the JWT from login) to access authenticated endpoints."""
    resp = requests.get(f"{BASE_URL}{path}", params=params or {}, headers=_headers(auth_token), timeout=TIMEOUT)
    return f"status={resp.status_code}\n{resp.text[:2000]}"


@tool
def http_post(path: str, json_body: dict | None = None, auth_token: str | None = None) -> str:
    """POST request. Pass auth_token (the JWT from login) to access authenticated endpoints."""
    resp = requests.post(f"{BASE_URL}{path}", json=json_body or {}, headers=_headers(auth_token), timeout=TIMEOUT)
    return f"status={resp.status_code}\n{resp.text[:2000]}"


@tool
def http_put(path: str, json_body: dict | None = None, auth_token: str | None = None) -> str:
    """PUT request. Pass auth_token (the JWT from login) to access authenticated endpoints."""
    resp = requests.put(f"{BASE_URL}{path}", json=json_body or {}, headers=_headers(auth_token), timeout=TIMEOUT)
    return f"status={resp.status_code}\n{resp.text[:2000]}"


@tool
def http_delete(path: str, auth_token: str | None = None) -> str:
    """DELETE request. Pass auth_token (the JWT from login) to access authenticated endpoints."""
    resp = requests.delete(f"{BASE_URL}{path}", headers=_headers(auth_token), timeout=TIMEOUT)
    return f"status={resp.status_code}\n{resp.text[:2000]}"


ALL_TOOLS = [http_get, http_post, http_put, http_delete]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}