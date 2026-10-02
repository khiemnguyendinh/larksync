"""
Google Drive API Client
Handles: OAuth2 auth, folder creation, file upload (create + overwrite), Google format import

v1.1 changes: token stored as JSON (the old pickle is migrated automatically and
removed), expired authorization is reported as GoogleAuthRequired instead of an
obscure crash, the browser flow only runs when the caller allows it (never
inside a background sync), Shared Drives are supported, overwrite falls back to
create when the Drive file was deleted, and a blank destination now means "My
Drive root" instead of "any folder with that name anywhere in the Drive".
"""

import io
import logging
from pathlib import Path
from typing import Optional

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from .paths import write_private

logger = logging.getLogger(__name__)

# Scopes cần thiết
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Map extension → MIME type nguồn (khi upload)
SOURCE_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf":  "application/pdf",
}

# Map extension → Google native MIME type (để import sang Google format)
GOOGLE_NATIVE_MIME = {
    "docx": "application/vnd.google-apps.document",
    "xlsx": "application/vnd.google-apps.spreadsheet",
    "pptx": "application/vnd.google-apps.presentation",
}

FOLDER_MIME = "application/vnd.google-apps.folder"

_RESUMABLE_THRESHOLD = 5 * 1024 * 1024     # smaller uploads go in a single request
_RETRIES = 3                               # transient 429/5xx handled by googleapiclient


class GoogleAuthRequired(RuntimeError):
    """The user has to (re-)authorize Google from Settings."""


class GoogleDriveClient:
    def __init__(self, credentials_path: str, token_path: str, interactive: bool = True):
        """
        credentials_path: path đến file credentials.json tải từ Google Cloud Console
        token_path: path để lưu token OAuth (tự động tạo sau lần auth đầu)
        interactive: allow opening the browser for sign-in. Background syncs pass
                     False and get GoogleAuthRequired instead.
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.interactive = interactive
        self._service = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _load_saved_credentials(self) -> Optional[Credentials]:
        token = Path(self.token_path)
        if token.exists():
            try:
                return Credentials.from_authorized_user_file(str(token), SCOPES)
            except (ValueError, OSError, KeyError):
                logger.warning("Saved Google token is unreadable — will re-authorize.")
                return None

        # v1.0.x stored a pickle next to it; read it once, the caller re-saves as JSON.
        legacy = token.with_suffix(".pkl")
        if legacy.exists():
            import pickle
            try:
                with open(legacy, "rb") as f:
                    creds = pickle.load(f)             # our own file, written by v1.0.x
                if isinstance(creds, Credentials):
                    return creds
            except Exception:
                logger.warning("Legacy Google token could not be read.")
        return None

    def _save_credentials(self, creds: Credentials) -> None:
        write_private(self.token_path, creds.to_json())
        Path(self.token_path).with_suffix(".pkl").unlink(missing_ok=True)

    def _get_credentials(self) -> Credentials:
        creds = self._load_saved_credentials()

        if creds and creds.valid:
            if not Path(self.token_path).exists():
                self._save_credentials(creds)          # finish pickle → JSON migration
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds)
                return creds
            except RefreshError as exc:
                # Typical when the OAuth consent screen is in "Testing" (7-day tokens)
                # or access was revoked.
                logger.warning("Google refresh failed: %s", exc)
                if not self.interactive:
                    raise GoogleAuthRequired(
                        "Google authorization expired. "
                        "Open Settings → Google Drive → Re-authorize Google."
                    ) from exc

        if not self.interactive:
            raise GoogleAuthRequired(
                "Google is not authorized. Open Settings → Google Drive → Re-authorize Google."
            )

        flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
        creds = flow.run_local_server(
            port=0, timeout_seconds=180, prompt="consent",
            authorization_prompt_message="",
            success_message="LarkSync is connected to Google Drive. You can close this tab.",
        )
        self._save_credentials(creds)
        return creds

    def get_service(self):
        if not self._service:
            creds = self._get_credentials()
            self._service = build("drive", "v3", credentials=creds,
                                  cache_discovery=False)
        return self._service

    # ------------------------------------------------------------------
    # Folder operations
    # ------------------------------------------------------------------

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Tạo folder, trả về folder ID."""
        metadata = {
            "name": name,
            "mimeType": FOLDER_MIME,
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        folder = (
            self.get_service()
            .files()
            .create(body=metadata, fields="id", supportsAllDrives=True)
            .execute(num_retries=_RETRIES)
        )
        return folder["id"]

    def find_item(self, name: str, parent_id: Optional[str] = None, is_folder: bool = False) -> Optional[str]:
        """
        Tìm file/folder theo tên trong parent (None → root của My Drive).
        Trả về ID nếu tìm thấy, None nếu không.
        """
        # Google Drive API dùng \' để escape dấu nháy đơn trong query
        escaped_name = name.replace("\\", "\\\\").replace("'", "\\'")
        q = f"name = '{escaped_name}' and trashed = false"
        # Without a parent the old query matched a same-named folder anywhere in
        # the Drive; anchor it to the root instead.
        q += f" and '{parent_id or 'root'}' in parents"
        if is_folder:
            q += f" and mimeType = '{FOLDER_MIME}'"

        results = (
            self.get_service()
            .files()
            .list(q=q, fields="files(id)", pageSize=1,
                  supportsAllDrives=True, includeItemsFromAllDrives=True)
            .execute(num_retries=_RETRIES)
        )
        files = results.get("files", [])
        return files[0]["id"] if files else None

    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Lấy folder ID nếu đã tồn tại, ngược lại tạo mới."""
        existing = self.find_item(name, parent_id, is_folder=True)
        if existing:
            return existing
        return self.create_folder(name, parent_id)

    # ------------------------------------------------------------------
    # File upload / overwrite
    # ------------------------------------------------------------------

    def upload_file(
        self,
        content: bytes,
        filename: str,
        ext: str,
        parent_id: Optional[str] = None,
        existing_file_id: Optional[str] = None,
    ) -> str:
        """
        Upload hoặc overwrite file lên Google Drive.
        - Nếu ext là docx/xlsx/pptx → import sang Google native format.
        - existing_file_id: nếu có → update (overwrite), ngược lại → create.
          If that file no longer exists (deleted/trashed in Drive) a new one is created.
        Trả về Google Drive file ID.
        """
        source_mime = SOURCE_MIME.get(ext, "application/octet-stream")
        target_mime = GOOGLE_NATIVE_MIME.get(ext)  # None nếu không convert
        resumable   = len(content) > _RESUMABLE_THRESHOLD

        def _media():
            return MediaIoBaseUpload(io.BytesIO(content), mimetype=source_mime, resumable=resumable)

        service = self.get_service()

        if existing_file_id:
            # Overwrite: chỉ update content (không đổi tên/vị trí)
            try:
                file = (
                    service.files()
                    .update(fileId=existing_file_id, media_body=_media(),
                            fields="id, trashed", supportsAllDrives=True)
                    .execute(num_retries=_RETRIES)
                )
                if not file.get("trashed"):
                    return file["id"]
                logger.info("Drive file %s is in the trash — creating a new copy.", existing_file_id)
            except HttpError as exc:
                if getattr(exc.resp, "status", None) != 404:
                    raise
                logger.info("Drive file %s no longer exists — creating a new copy.", existing_file_id)

        # Create mới
        metadata = {"name": filename}
        if parent_id:
            metadata["parents"] = [parent_id]
        if target_mime:
            metadata["mimeType"] = target_mime

        file = (
            service.files()
            .create(body=metadata, media_body=_media(), fields="id", supportsAllDrives=True)
            .execute(num_retries=_RETRIES)
        )
        return file["id"]
