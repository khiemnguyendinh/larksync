import json
import pickle

import pytest
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from sync import google_client
from sync.google_client import GoogleDriveClient, GoogleAuthRequired


class Req:
    def __init__(self, fn): self.fn = fn
    def execute(self, num_retries=0): return self.fn()


class FakeFiles:
    def __init__(self, update_exc=None, update_result=None):
        self.created, self.updated, self.listed = [], [], []
        self.update_exc, self.update_result = update_exc, update_result or {"id": "upd"}

    def create(self, body=None, media_body=None, fields=None, supportsAllDrives=None):
        self.created.append(body)
        return Req(lambda: {"id": "new-id"})

    def update(self, fileId=None, media_body=None, fields=None, supportsAllDrives=None):
        self.updated.append(fileId)
        def run():
            if self.update_exc: raise self.update_exc
            return self.update_result
        return Req(run)

    def list(self, q=None, **kw):
        self.listed.append(q)
        return Req(lambda: {"files": []})


class FakeService:
    def __init__(self, files): self._files = files
    def files(self): return self._files


def client_with(files):
    c = GoogleDriveClient("c.json", "t.json", interactive=False)
    c._service = FakeService(files)
    return c


def http_error(status):
    class R: pass
    r = R(); r.status = status; r.reason = "x"
    return HttpError(r, b"{}")


def test_overwrite_falls_back_to_create_when_drive_file_was_deleted():
    files = FakeFiles(update_exc=http_error(404))
    gid = client_with(files).upload_file(b"x", "a.pdf", "pdf", parent_id="P", existing_file_id="gone")
    assert gid == "new-id"
    assert files.created[0]["parents"] == ["P"]


def test_overwrite_falls_back_to_create_when_file_is_in_trash():
    files = FakeFiles(update_result={"id": "t", "trashed": True})
    assert client_with(files).upload_file(b"x", "a.pdf", "pdf", "P", "trashed-id") == "new-id"


def test_overwrite_other_errors_propagate():
    files = FakeFiles(update_exc=http_error(403))
    with pytest.raises(HttpError):
        client_with(files).upload_file(b"x", "a.pdf", "pdf", "P", "id")


def test_overwrite_success_returns_same_id():
    assert client_with(FakeFiles()).upload_file(b"x", "a.pdf", "pdf", "P", "id") == "upd"


def test_docx_is_imported_as_google_doc():
    files = FakeFiles()
    client_with(files).upload_file(b"x", "Plan", "docx", "P")
    assert files.created[0]["mimeType"] == "application/vnd.google-apps.document"


def test_blank_destination_is_anchored_to_my_drive_root():
    """Without a parent the old query matched a same-named folder anywhere in the Drive."""
    files = FakeFiles()
    client_with(files).find_item("Reports", None, is_folder=True)
    assert "'root' in parents" in files.listed[0]
    client_with(files).find_item("It's", "PARENT")
    assert "'PARENT' in parents" in files.listed[1] and "It\\'s" in files.listed[1]


# ── credentials handling ──────────────────────────────────────────────

def _creds(**kw):
    return Credentials(token=kw.get("token", "tok"), refresh_token="r", client_id="cid",
                       client_secret="cs", token_uri="https://oauth2.googleapis.com/token",
                       scopes=google_client.SCOPES)


def test_json_token_roundtrip(tmp_path):
    c = GoogleDriveClient("c.json", str(tmp_path / "t.json"), interactive=False)
    c._save_credentials(_creds())
    loaded = c._load_saved_credentials()
    assert loaded.refresh_token == "r" and loaded.client_id == "cid"
    import sys, os, stat
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(tmp_path / "t.json").st_mode) == 0o600


def test_legacy_pickle_is_migrated_to_json(tmp_path):
    token = tmp_path / "google_token.json"
    (tmp_path / "google_token.pkl").write_bytes(pickle.dumps(_creds()))
    c = GoogleDriveClient("c.json", str(token), interactive=False)
    # not expired + valid -> returned and re-saved as JSON, pickle removed
    creds = c._get_credentials()
    assert creds.refresh_token == "r"
    assert token.exists() and json.loads(token.read_text())["refresh_token"] == "r"
    assert not (tmp_path / "google_token.pkl").exists()


def test_corrupt_token_file_requires_reauth_in_background(tmp_path):
    token = tmp_path / "t.json"; token.write_text("{nope")
    with pytest.raises(GoogleAuthRequired):
        GoogleDriveClient("c.json", str(token), interactive=False)._get_credentials()


def test_expired_refresh_token_is_a_clear_error_not_a_crash(tmp_path, monkeypatch):
    """OAuth apps in 'Testing' mode lose refresh tokens after 7 days."""
    token = tmp_path / "t.json"
    creds = _creds(); creds.expiry = None
    token.write_text(creds.to_json())
    def refuse(self, request): raise RefreshError("invalid_grant")
    monkeypatch.setattr(Credentials, "refresh", refuse)
    monkeypatch.setattr(Credentials, "valid", property(lambda self: False))
    monkeypatch.setattr(Credentials, "expired", property(lambda self: True))
    with pytest.raises(GoogleAuthRequired, match="Re-authorize"):
        GoogleDriveClient("c.json", str(token), interactive=False)._get_credentials()


def test_background_sync_never_opens_a_browser(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(google_client.InstalledAppFlow, "from_client_secrets_file",
                        lambda *a, **k: called.append(1))
    with pytest.raises(GoogleAuthRequired):
        GoogleDriveClient("c.json", str(tmp_path / "missing.json"), interactive=False)._get_credentials()
    assert called == []
