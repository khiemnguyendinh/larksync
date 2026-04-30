"""
Google Drive API Client
Handles: OAuth2 auth, folder creation, file upload (create + overwrite), Google format import
"""

import io
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

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


class GoogleDriveClient:
    def __init__(self, credentials_path: str, token_path: str):
        """
        credentials_path: path đến file credentials.json tải từ Google Cloud Console
        token_path: path để lưu token OAuth (tự động tạo sau lần auth đầu)
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self._service = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _get_credentials(self) -> Credentials:
        import os
        import pickle

        creds = None

        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_path, "wb") as f:
                pickle.dump(creds, f)

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
            .create(body=metadata, fields="id")
            .execute()
        )
        return folder["id"]

    def find_item(self, name: str, parent_id: Optional[str] = None, is_folder: bool = False) -> Optional[str]:
        """
        Tìm file/folder theo tên trong parent.
        Trả về ID nếu tìm thấy, None nếu không.
        """
        # Google Drive API dùng \' để escape dấu nháy đơn trong query
        escaped_name = name.replace("\\", "\\\\").replace("'", "\\'")
        q = f"name = '{escaped_name}' and trashed = false"
        if parent_id:
            q += f" and '{parent_id}' in parents"
        if is_folder:
            q += f" and mimeType = '{FOLDER_MIME}'"

        results = (
            self.get_service()
            .files()
            .list(q=q, fields="files(id)", pageSize=1)
            .execute()
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
        Trả về Google Drive file ID.
        """
        source_mime = SOURCE_MIME.get(ext, "application/octet-stream")
        target_mime = GOOGLE_NATIVE_MIME.get(ext)  # None nếu không convert

        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=source_mime, resumable=True)

        if existing_file_id:
            # Overwrite: chỉ update content (không đổi tên/vị trí)
            file = (
                self.get_service()
                .files()
                .update(
                    fileId=existing_file_id,
                    media_body=media,
                    fields="id",
                )
                .execute()
            )
            return file["id"]
        else:
            # Create mới
            metadata = {"name": filename}
            if parent_id:
                metadata["parents"] = [parent_id]
            if target_mime:
                metadata["mimeType"] = target_mime

            file = (
                self.get_service()
                .files()
                .create(
                    body=metadata,
                    media_body=media,
                    fields="id",
                )
                .execute()
            )
            return file["id"]
