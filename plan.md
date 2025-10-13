# Simplified Username-Only Login/Logout Plan

### Goals

- Remove old IP-based session interfaces entirely
- No tokens, no IP binding, no timeouts; username-only “logged-in once” acknowledgment
- Support both localhost and LAN
- Start server at first app boot (when possible) and control lifecycle from `ui/login_page.py`

### Changes Overview

- Server: replace `/session/*` with minimal username login state; do not guard DB endpoints
- Client/UI: remove session checks; on login, start server (if needed) and call one-time username login; add restart/shutdown controls
- Docs: update technical docs to reflect simplified flow

### Server (`remote_db/memdb_port_server.py`)

1) Remove legacy endpoints and state

- Delete: `_active_sessions`, `_session_lock`, `SESSION_TIMEOUT`, `_cleanup_expired_sessions`, `_register_session`, `_check_session`, `_logout_session`
- Remove handling for `/session/register`, `/session/check`, `/session/logout`, `/session/active_ips`

2) Add minimal username login state

- Globals: `_current_username: Optional[str] = None`, `_login_time: float = 0.0`
- Endpoints:
  - `POST /auth/login {"username": "..."}` → set `_current_username` and `_login_time`; idempotent
  - `POST /auth/logout` → clear `_current_username`
  - `GET /auth/status` → `{logged_in: bool, username, login_time}`
- Do NOT require username on subsequent requests; DB endpoints remain open on LAN/localhost

3) LAN support

- Keep `--host` option; document `0.0.0.0` for LAN
- Keep `/health`, `/database/*`, `/query`, `/exec` behavior unchanged

Minimal server snippet (illustrative):

```python
_current_username = None
_login_time = 0.0

# in do_POST
if path == "/auth/login":
    username = (body or {}).get("username")
    if not username:
        return self._send(400, {"error": "missing_username"})
    global _current_username, _login_time
    _current_username, _login_time = username, time.time()
    return self._send(200, {"ok": True, "username": username})

if path == "/auth/logout":
    global _current_username
    _current_username = None
    return self._send(200, {"ok": True})
```

### Client Library (`remote_db/db_port_client.py`)

- Remove `register_session`, `check_session`, `logout_session`, `get_active_ips`
- Add:
  - `login_username(username: str)` → POST `/auth/login`
  - `logout_username()` → POST `/auth/logout`
  - `auth_status()` → GET `/auth/status`

### UI Integration

1) `ui/common.py`

- `ensure_memdb_server(username)`:
  - If not running → spawn server
  - Call `client.login_username(username)`; return `(ok, port, msg)`
  - Remove active IP checks and session restoration logic
- `logout_current_user()` → `client.logout_username()`; clear local state

2) `ui/login_page.py`

- On first render, attempt server auto-start once if a `last_username` exists; otherwise show controls
- Add lifecycle controls:
  - Start (spawn if not running), Restart (shutdown then start), Shutdown
- Login flow:
  - Validate username → call `ensure_memdb_server(username)` → success sets `last_username`, `authenticated`, host/port
  - Replace “Clear Session” with “Logout (this user)” that calls `logout_current_user()`
- Auto-login:
  - If `last_username` exists and `auth_status().logged_in` is true → restore UI session

3) `ui/main.py`

- On app boot, optionally try to auto-start server once if `last_username` is present (config flag `AUTO_START_ON_BOOT=True`)
- Otherwise defer to login page controls

### Documentation (`resources/technical_api_documentation.md`)

- Replace IP session section with simple username login section
- Update endpoint list and UI flow diagrams (login once → use system; logout optional)

### Notes

- Code comments in Chinese per project preference
- No backward compatibility retained; old endpoints removed

### Implementation To-d