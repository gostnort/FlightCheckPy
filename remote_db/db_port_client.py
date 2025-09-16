#!/usr/bin/env python3
import json
from urllib.request import Request, urlopen


class DbPortClient:
    """Minimal HTTP client for the per-port in-memory DB server."""
    def __init__(self, host: str, port: int):
        self.base = f"http://{host}:{port}"

    def _post(self, path: str, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        req = Request(self.base + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path: str):
        req = Request(self.base + path, method="GET")
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def health(self):
        return self._get("/health")

    def list_databases(self):
        return self._get("/databases/list").get("files", [])

    def load_database(self, path: str):
        return self._post("/database/load", {"path": path})

    def backup(self):
        return self._post("/database/backup", {})

    def save(self):
        return self._post("/database/save", {})

    def query(self, sql: str, params=None):
        return self._post("/query", {"sql": sql, "params": params or []})

    def exec(self, sql: str, params=None):
        return self._post("/exec", {"sql": sql, "params": params or []})


