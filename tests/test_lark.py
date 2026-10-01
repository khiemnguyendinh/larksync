import json
import socket
import sys
import threading
import urllib.request

import pytest
import requests

from sync import lark_auth, lark_client
from sync.lark_client import LarkClient, FileTooLarge


class Resp:
    def __init__(self, status=200, payload=None, headers=None, content=b""):
        self.status_code, self._payload = status, payload or {}
        self.headers, self.content = headers or {}, content

    def json(self): return self._payload
    def close(self): pass

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(lark_client, "get_valid_access_token", lambda: "tok")
    monkeypatch.setattr(lark_client.time, "sleep", lambda s: None)
    return LarkClient("id", "secret")


def test_retries_429_then_succeeds(client, monkeypatch):
    seq = [Resp(429, headers={"Retry-After": "1"}), Resp(503), Resp(200, {"code": 0, "data": {"files": [], "has_more": False}})]
    monkeypatch.setattr(lark_client.requests, "request", lambda *a, **k: seq.pop(0))
    assert client.list_folder() == []
    assert seq == []


def test_retries_connection_errors_then_gives_up(client, monkeypatch):
    calls = []
    def boom(*a, **k):
        calls.append(1); raise requests.ConnectionError("down")
    monkeypatch.setattr(lark_client.requests, "request", boom)
    with pytest.raises(requests.ConnectionError):
        client.list_folder()
    assert len(calls) == 4                                      # 1 try + 3 retries


def test_client_error_is_not_retried(client, monkeypatch):
    calls = []
    def r(*a, **k):
        calls.append(1); return Resp(404)
    monkeypatch.setattr(lark_client.requests, "request", r)
    with pytest.raises(requests.HTTPError):
        client.list_folder()
    assert len(calls) == 1


def test_pagination_and_traverse(client, monkeypatch):
    pages = {
        None: {"files": [{"name": "A", "type": "folder", "token": "fa"}], "has_more": True, "next_page_token": "p2"},
        "p2": {"files": [{"name": "b.txt", "type": "file", "token": "fb"}], "has_more": False},
    }
    inside = {"files": [{"name": "c.txt", "type": "file", "token": "fc"}], "has_more": False}

    def fake(method, url, headers=None, params=None, **k):
        if params.get("folder_token") == "fa":
            return Resp(200, {"code": 0, "data": inside})
        return Resp(200, {"code": 0, "data": pages[params.get("page_token")]})
    monkeypatch.setattr(lark_client.requests, "request", fake)

    items = client.traverse()
    assert [i["path"] for i in items] == ["/A/", "/A/c.txt", "/b.txt"]
    assert items[1]["parent_token"] == "fa"


def test_traverse_can_be_cancelled(client, monkeypatch):
    monkeypatch.setattr(client, "list_folder", lambda t="": [{"name": "x", "type": "file", "token": "1"}])
    assert client.traverse(cancel_fn=lambda: True) == []


def test_download_enforces_size_limit_from_content_length(client, monkeypatch):
    monkeypatch.setattr(lark_client.requests, "request",
                        lambda *a, **k: Resp(200, headers={"Content-Length": str(5 * 1024 * 1024)}, content=b"x"))
    with pytest.raises(FileTooLarge):
        client.download_file("t", max_bytes=1024 * 1024)
    assert client.download_file("t", max_bytes=10 * 1024 * 1024) == b"x"
    assert client.download_file("t") == b"x"                    # 0 = unlimited


# ── OAuth loopback flow ───────────────────────────────────────────────

@pytest.fixture
def oauth(monkeypatch):
    lark_auth.CONFIG_FILE.write_text(json.dumps({"lark_app_id": "cli_test", "lark_app_secret": "s"}))
    monkeypatch.setattr(lark_auth, "_exchange_code", lambda code: {"access_token": f"at-{code}", "obtained_at": 1})
    return monkeypatch


def _port_free():
    s = socket.socket()
    if sys.platform != "win32":
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # ignore TIME_WAIT like the server does
    try:
        s.bind(("127.0.0.1", lark_auth.CALLBACK_PORT))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _browser_that_calls_back(monkeypatch, make_query):
    """Replace webbrowser.open with a fake browser that hits the loopback callback."""
    def open_(url):
        from urllib.parse import urlparse, parse_qs
        state = parse_qs(urlparse(url).query)["state"][0]
        def go():
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{lark_auth.CALLBACK_PORT}/callback?{make_query(state)}", timeout=5)
            except Exception:
                pass
        threading.Thread(target=go, daemon=True).start()
    monkeypatch.setattr(lark_auth.webbrowser, "open", open_)


def test_authorize_success_saves_token_and_closes_port(oauth):
    _browser_that_calls_back(oauth, lambda state: f"code=abc&state={state}")
    tokens = lark_auth.authorize(timeout=10)
    assert tokens["access_token"] == "at-abc"
    assert json.loads(lark_auth.LARK_TOKEN.read_text())["access_token"] == "at-abc"
    assert _port_free()                                         # v1.0.x left 8080 bound after a timeout


def test_authorize_rejects_wrong_state(oauth):
    _browser_that_calls_back(oauth, lambda state: "code=evil&state=forged")
    with pytest.raises(TimeoutError):
        lark_auth.authorize(timeout=2)
    assert not lark_auth.LARK_TOKEN.exists()
    assert _port_free()


def test_authorize_times_out_and_frees_port(oauth):
    oauth.setattr(lark_auth.webbrowser, "open", lambda url: None)
    with pytest.raises(TimeoutError):
        lark_auth.authorize(timeout=1)
    assert _port_free()


def test_authorize_can_be_cancelled(oauth):
    oauth.setattr(lark_auth.webbrowser, "open", lambda url: None)
    ev = threading.Event(); ev.set()
    with pytest.raises(lark_auth.LarkAuthError, match="cancelled"):
        lark_auth.authorize(timeout=30, cancel_event=ev)
    assert _port_free()


def test_authorize_reports_port_in_use(oauth):
    blocker = socket.socket()
    if sys.platform != "win32":
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", lark_auth.CALLBACK_PORT)); blocker.listen(1)
    try:
        with pytest.raises(lark_auth.LarkAuthError, match="in use"):
            lark_auth.authorize(timeout=1)
    finally:
        blocker.close()


def test_authorize_requires_app_id():
    with pytest.raises(lark_auth.LarkAuthError):
        lark_auth.authorize(timeout=1)


def test_expired_token_without_refresh_asks_to_reauthorize():
    lark_auth.save_token({"access_token": "a", "obtained_at": 0, "expire_in": 10})
    with pytest.raises(lark_auth.LarkAuthRequired):
        lark_auth.get_valid_access_token()


def test_rejected_refresh_asks_to_reauthorize(monkeypatch):
    lark_auth.save_token({"access_token": "a", "refresh_token": "r", "obtained_at": 0, "expire_in": 10})
    def reject(_):
        raise RuntimeError("Token refresh failed: {'code': 20037}")
    monkeypatch.setattr(lark_auth, "_refresh_token", reject)
    with pytest.raises(lark_auth.LarkAuthRequired):
        lark_auth.get_valid_access_token()


def test_missing_token_asks_to_authorize():
    with pytest.raises(lark_auth.LarkAuthRequired):
        lark_auth.get_valid_access_token()
