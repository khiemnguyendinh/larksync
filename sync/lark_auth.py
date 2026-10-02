"""
Lark User OAuth
Handles the OAuth flow to obtain a user_access_token.
App credentials (app_id / app_secret) are read from the saved config file.

v1.1 changes: the loopback server is always closed (the old one kept port 8080
bound after a timeout, so every retry failed), the OAuth `state` is verified,
the flow can be cancelled and no longer touches Qt (the UI runs it on a worker
thread — see app/oauth_worker.py).
"""

import html
import json
import secrets
import sys
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import requests

from .paths import CONFIG_FILE, LARK_TOKEN, write_private

LARK_BASE_URL = "https://open.larksuite.com/open-apis"
CALLBACK_PORT = 8080
REDIRECT_URI  = f"http://localhost:{CALLBACK_PORT}/callback"
SCOPES        = "drive:drive:readonly"


class LarkAuthError(RuntimeError):
    pass


class LarkAuthRequired(LarkAuthError):
    """The user has to (re-)authorize Lark from Settings."""


def _get_app_credentials():  # -> Tuple[str, str]
    """Read Lark app_id / app_secret from the saved app_config.json."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("lark_app_id", ""), cfg.get("lark_app_secret", "")
    return "", ""


# ------------------------------------------------------------------
# Local callback server để nhận code từ Lark OAuth
# ------------------------------------------------------------------

_PAGE = """<html><head><meta charset="utf-8"><title>LarkSync</title></head>
<body style="font-family:-apple-system,Segoe UI,sans-serif;padding:40px">
<h2 style="color:{color}">{title}</h2><p>{body}</p></body></html>"""


class _LoopbackServer(HTTPServer):
    # On Windows SO_REUSEADDR lets a second program bind a port that is already
    # listening, which would hide a real "port in use" conflict (and lets another
    # process share the callback port). Elsewhere it only avoids TIME_WAIT delays.
    allow_reuse_address = sys.platform != "win32"


def _make_handler(expected_state: str, result: dict):
    """Build a request handler bound to this attempt's state (no class-level globals)."""

    class _CallbackHandler(BaseHTTPRequestHandler):
        def _reply(self, status: int, color: str, title: str, body: str):
            page = _PAGE.format(color=color, title=html.escape(title), body=html.escape(body))
            data = page.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != "/callback":          # favicon.ico etc. — ignore, keep waiting
                self.send_response(404)
                self.end_headers()
                return

            params = parse_qs(parsed.query)
            if params.get("state", [""])[0] != expected_state:
                self._reply(400, "#c0392b", "Authorization rejected",
                            "The response did not match this sign-in attempt. "
                            "Go back to LarkSync and click Authorize again.")
                return

            if "code" in params:
                result["code"] = params["code"][0]
                self._reply(200, "#27ae60", "Lark authorization successful",
                            "You can close this tab and return to LarkSync.")
            elif "error" in params:
                result["error"] = params.get("error_description", params["error"])[0]
                self._reply(400, "#c0392b", "Authorization failed",
                            "Return to LarkSync for details.")
            else:
                self._reply(400, "#c0392b", "Authorization failed", "No code was returned.")

        def log_message(self, format, *args):
            pass  # keep the app log clean

    return _CallbackHandler


# ------------------------------------------------------------------
# OAuth flow
# ------------------------------------------------------------------

def authorize(timeout: float = 180, cancel_event=None) -> dict:
    """
    Open the browser for Lark login, receive the code, exchange it for tokens.
    Saves the token to disk and returns the token dict.
    Blocking — call it from a worker thread. `cancel_event` is a threading.Event.
    """
    app_id, _ = _get_app_credentials()
    if not app_id:
        raise LarkAuthError("Enter the Lark App ID and App Secret first.")

    state  = secrets.token_urlsafe(16)
    result: dict = {}
    auth_url = f"{LARK_BASE_URL}/authen/v1/authorize?" + urlencode({
        "app_id":       app_id,
        "redirect_uri": REDIRECT_URI,
        "scope":        SCOPES,
        "state":        state,
    })

    try:
        server = _LoopbackServer(("127.0.0.1", CALLBACK_PORT), _make_handler(state, result))
    except OSError as exc:
        raise LarkAuthError(
            f"Port {CALLBACK_PORT} is in use by another program ({exc.strerror or exc}). "
            f"Close it and try again."
        ) from exc

    try:
        server.timeout = 0.5
        webbrowser.open(auth_url)
        deadline = time.monotonic() + timeout
        while not result and time.monotonic() < deadline:
            if cancel_event is not None and cancel_event.is_set():
                raise LarkAuthError("Authorization cancelled.")
            server.handle_request()
    finally:
        server.server_close()

    if result.get("error"):
        raise LarkAuthError(f"Lark OAuth error: {result['error']}")
    if not result.get("code"):
        raise TimeoutError(f"No authorization code received within {int(timeout)} seconds.")

    tokens = _exchange_code(result["code"])
    save_token(tokens)
    return tokens


def get_app_access_token() -> str:
    """Public alias — used by LarkNotifier to send bot messages."""
    return _get_app_access_token()


def _get_app_access_token() -> str:
    app_id, app_secret = _get_app_credentials()
    resp = requests.post(
        f"{LARK_BASE_URL}/auth/v3/app_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"App access token failed: {data}")
    return data["app_access_token"]


def _exchange_code(code: str) -> dict:
    """Exchange authorization code lấy access_token + refresh_token."""
    app_token = _get_app_access_token()
    resp = requests.post(
        f"{LARK_BASE_URL}/authen/v1/oidc/access_token",
        json={
            "grant_type": "authorization_code",
            "code": code,
        },
        headers={
            "Authorization": f"Bearer {app_token}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Token exchange failed: {data}")

    token_data = data["data"]
    token_data["obtained_at"] = time.time()
    return token_data


def _refresh_token(refresh_token: str) -> dict:
    """Dùng refresh_token để lấy access_token mới."""
    app_token = _get_app_access_token()
    resp = requests.post(
        f"{LARK_BASE_URL}/authen/v1/oidc/refresh_access_token",
        json={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={
            "Authorization": f"Bearer {app_token}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Token refresh failed: {data}")

    token_data = data["data"]
    token_data["obtained_at"] = time.time()
    return token_data


# ------------------------------------------------------------------
# Token persistence
# ------------------------------------------------------------------

def save_token(token_data: dict):
    write_private(LARK_TOKEN, json.dumps(token_data, indent=2))


def load_token():  # -> Optional[dict]
    if LARK_TOKEN.exists():
        try:
            with open(LARK_TOKEN, "r", encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError):
            return None
    return None


def get_valid_access_token() -> str:
    """
    Return a valid user_access_token, auto-refreshing if near expiry.
    Raises LarkAuthRequired if there is no usable token (user must re-authorize).
    """
    token_data = load_token()
    if not token_data or not token_data.get("access_token"):
        raise LarkAuthRequired(
            "No Lark authorization found. Open Settings → Larksuite → Re-authorize Lark."
        )

    obtained_at = token_data.get("obtained_at", 0)
    expire_in   = token_data.get("expire_in", 7200)
    now         = time.time()

    if now >= obtained_at + expire_in - 300:
        refresh = token_data.get("refresh_token")
        if not refresh:
            raise LarkAuthRequired(
                "Lark authorization expired. Open Settings → Larksuite → Re-authorize Lark."
            )
        try:
            token_data = _refresh_token(refresh)
        except RuntimeError as exc:
            # Lark answered "code != 0": refresh tokens are single-use and expire,
            # so a rejection means the user must re-authorize.
            raise LarkAuthRequired(
                "Lark authorization expired. Open Settings → Larksuite → Re-authorize Lark."
            ) from exc
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", 500)
            if status < 500:
                raise LarkAuthRequired(
                    "Lark authorization expired. Open Settings → Larksuite → Re-authorize Lark."
                ) from exc
            raise                                   # Lark outage → plain error, retry later
        save_token(token_data)

    return token_data["access_token"]
