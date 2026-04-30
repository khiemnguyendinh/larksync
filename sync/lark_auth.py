"""
Lark User OAuth
Handles the OAuth flow to obtain a user_access_token.
App credentials (app_id / app_secret) are read from the saved config file.
"""

import json
import os
import time
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode
import requests

LARK_BASE_URL = "https://open.larksuite.com/open-apis"
REDIRECT_URI  = "http://localhost:8080/callback"
SCOPES        = "drive:drive:readonly"

# Paths — mirror what config_manager.py defines as APP_DIR
_APP_DIR     = Path.home() / "Documents" / "lark_gdrive_sync"
_TOKEN_FILE  = _APP_DIR / "lark_token.json"
_CONFIG_FILE = _APP_DIR / "app_config.json"


def _get_app_credentials():  # -> Tuple[str, str]
    """Read Lark app_id / app_secret from the saved app_config.json."""
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("lark_app_id", ""), cfg.get("lark_app_secret", "")
    return "", ""


# ------------------------------------------------------------------
# Local callback server để nhận code từ Lark OAuth
# ------------------------------------------------------------------

class _CallbackHandler(BaseHTTPRequestHandler):
    code = None
    error = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            _CallbackHandler.code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family:sans-serif;padding:40px">
                <h2 style="color:green">Xac thuc Lark thanh cong!</h2>
                <p>Ban co the dong tab nay va quay lai Terminal.</p>
                </body></html>
            """)
        elif "error" in params:
            _CallbackHandler.error = params.get("error_description", ["Unknown error"])[0]
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<html><body>Loi xac thuc. Quay lai Terminal.</body></html>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Tắt log của HTTPServer


def _run_server(server: HTTPServer):
    server.handle_request()


# ------------------------------------------------------------------
# OAuth flow
# ------------------------------------------------------------------

def authorize() -> dict:
    """
    Open browser for Lark login, receive the code, exchange for tokens.
    Saves the token to disk and returns the token dict.
    """
    # Reset class-level state so repeated calls work correctly
    _CallbackHandler.code  = None
    _CallbackHandler.error = None

    app_id, _ = _get_app_credentials()
    params = {
        "app_id":       app_id,
        "redirect_uri": REDIRECT_URI,
        "scope":        SCOPES,
        "state":        "lark_sync",
    }
    auth_url = f"{LARK_BASE_URL}/authen/v1/authorize?{urlencode(params)}"

    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    server_thread = threading.Thread(target=_run_server, args=(server,), daemon=True)
    server_thread.start()

    webbrowser.open(auth_url)
    server_thread.join(timeout=120)

    if _CallbackHandler.error:
        raise RuntimeError(f"Lark OAuth error: {_CallbackHandler.error}")
    if not _CallbackHandler.code:
        raise TimeoutError("No authorization code received within 120 seconds.")

    tokens = _exchange_code(_CallbackHandler.code)
    save_token(tokens)
    return tokens


def authorize_async(on_success=None, on_error=None):
    """
    Run the OAuth flow in a background thread.
    on_success() and on_error(msg) are scheduled on the Qt main thread
    via QTimer.singleShot so it is safe to update UI from these callbacks.
    """
    def _run():
        try:
            authorize()
            if on_success is not None:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, on_success)
        except Exception as exc:
            if on_error is not None:
                msg = str(exc)
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: on_error(msg))

    threading.Thread(target=_run, daemon=True).start()


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
    _APP_DIR.mkdir(parents=True, exist_ok=True)
    with open(_TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2)


def load_token():  # -> Optional[dict]
    if _TOKEN_FILE.exists():
        with open(_TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def get_valid_access_token() -> str:
    """
    Return a valid user_access_token, auto-refreshing if near expiry.
    Raises RuntimeError if no token exists yet.
    """
    token_data = load_token()
    if not token_data:
        raise RuntimeError(
            "No Lark user token found. Complete the Setup Wizard to authorize."
        )

    obtained_at = token_data.get("obtained_at", 0)
    expire_in   = token_data.get("expire_in", 7200)
    now         = time.time()

    if now >= obtained_at + expire_in - 300:
        token_data = _refresh_token(token_data["refresh_token"])
        save_token(token_data)

    return token_data["access_token"]
