#!/usr/bin/env python3
import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


class DbPortClient:
    """
    A minimal HTTP client for communicating with the MemDbPortServer.
    This class abstracts the HTTP requests to the server's endpoints,
    making it easy to interact with the remote in-memory database from other
    parts of the application. Each method corresponds to an endpoint on the server.
    """
    def __init__(self, host: str, port: int):
        self.base = f"http://{host}:{port}"

    def _decode(self, resp):
        return json.loads(resp.read().decode("utf-8"))

    def _request(self, req: Request):
        try:
            with urlopen(req, timeout=30) as resp:
                return self._decode(resp)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(detail or str(exc.reason)) from exc

    def _post(self, path: str, payload: dict):
        """Helper method to send a POST request with a JSON payload."""
        data = json.dumps(payload).encode("utf-8")
        req = Request(self.base + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
        return self._request(req)

    def _get(self, path: str):
        """Helper method to send a GET request."""
        req = Request(self.base + path, method="GET")
        return self._request(req)

    def health(self):
        """Checks the health of the database server."""
        return self._get("/health")

    def _database_list_payload(self, directory=None):
        path = "/databases/list"
        if directory:
            path += f"?directory={quote(directory)}"
        return self._get(path)

    def list_databases(self, directory=None):
        """Retrieves a list of available database files from the server."""
        return self._database_list_payload(directory).get("files", [])

    def list_database_status(self, directory=None):
        """List databases, including which ones are already in memory."""
        payload = self._database_list_payload(directory)
        details = payload.get("databases")
        if details:
            return details
        return [
            {"path": path, "valid": True, "resident": False, "active": False}
            for path in payload.get("files", [])
        ]

    def load_database(self, path: str):
        """Requests the server to load a database file into memory."""
        return self._post("/database/load", {"path": path})

    def preload_databases(self, paths, activate: str):
        """Queue background loads. activate is the database that should open."""
        return self._post("/database/preload", {"paths": list(paths), "activate": activate})

    def validate_database_schema(self, path: str):
        """Validates that a database file has the expected schema."""
        try:
            return self._post("/database/validate", {"path": path})
        except Exception:
            return {"valid": False, "error": "Failed to validate database"}

    def backup(self):
        """Requests the server to create a backup of the current in-memory database."""
        return self._post("/database/backup", {})

    def save(self):
        """Requests the server to save the in-memory database to its source file."""
        return self._post("/database/save", {})

    def reload_database(self):
        """Requests the server to reload the current database from disk."""
        return self._post("/database/reload", {})

    def query(self, sql: str, params=None):
        """
        Sends a read-only SQL query to the server.
        :param sql: The SQL SELECT statement.
        :param params: A list of parameters for the SQL query.
        :return: A dictionary with 'columns' and 'rows'.
        """
        return self._post("/query", {"sql": sql, "params": params or []})

    def exec(self, sql: str, params=None):
        """
        Sends a write (INSERT, UPDATE, DELETE) SQL statement to the server.
        :param sql: The SQL statement to execute.
        :param params: A list of parameters for the SQL statement.
        :return: A dictionary with 'rowcount'.
        """
        return self._post("/exec", {"sql": sql, "params": params or []})


    def shutdown(self):
        """
        Requests the server to save the database and shutdown gracefully.
        """
        try:
            return self._get("/shutdown")
        except Exception:
            # Server might close connection before responding, which is expected
            return {"ok": True}

    def login_username(self, username: str):
        """
        登录用户名（简化认证，无IP绑定）
        :param username: 用户名
        :return: 服务器响应字典，包含ok, username, login_time
        """
        return self._post("/auth/login", {"username": username})

    def logout_username(self):
        """
        登出当前用户
        :return: 包含ok布尔值的字典
        """
        return self._post("/auth/logout", {})

    def auth_status(self):
        """
        获取当前认证状态
        :return: 包含logged_in, username, login_time的字典
        """
        return self._get("/auth/status")


