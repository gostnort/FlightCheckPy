#!/usr/bin/env python3
import json
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

    def _post(self, path: str, payload: dict):
        """Helper method to send a POST request with a JSON payload."""
        data = json.dumps(payload).encode("utf-8")
        req = Request(self.base + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path: str):
        """Helper method to send a GET request."""
        req = Request(self.base + path, method="GET")
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def health(self):
        """Checks the health of the database server."""
        return self._get("/health")

    def list_databases(self):
        """Retrieves a list of available database files from the server."""
        return self._get("/databases/list").get("files", [])

    def load_database(self, path: str):
        """Requests the server to load a database file into memory."""
        return self._post("/database/load", {"path": path})

    def backup(self):
        """Requests the server to create a backup of the current in-memory database."""
        return self._post("/database/backup", {})

    def save(self):
        """Requests the server to save the in-memory database to its source file."""
        return self._post("/database/save", {})

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


