"""
Lark Drive API Client
Handles: authentication, file listing, folder traversal, native file export
Dùng user_access_token (OAuth) để truy cập personal Drive của user.
"""

import time
import requests
from typing import Optional

# Import user token manager
from .lark_auth import get_valid_access_token

# Lark file type → export extension mapping
LARK_EXPORT_MAP = {
    "docx":      "docx",    # Lark Doc       → Word
    "doc":       "docx",    # Lark Doc (old) → Word
    "sheet":     "xlsx",    # Lark Sheet     → Excel
    "bitable":   "xlsx",    # Lark Base      → Excel
    "mindnote":  "pdf",     # MindNote       → PDF
    "slides":    "pptx",    # Lark Slides    → PowerPoint
}

# Lark native types (cần export, không thể download trực tiếp)
LARK_NATIVE_TYPES = set(LARK_EXPORT_MAP.keys())

LARK_BASE_URL = "https://open.larksuite.com/open-apis"


class LarkClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret

    # ------------------------------------------------------------------
    # Authentication — dùng user_access_token
    # ------------------------------------------------------------------

    def get_access_token(self) -> str:
        """Lấy user_access_token hợp lệ (tự refresh nếu cần)."""
        return get_valid_access_token()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.get_access_token()}"}

    # ------------------------------------------------------------------
    # File / Folder listing
    # ------------------------------------------------------------------

    def list_folder(self, folder_token: str = "") -> list[dict]:
        """
        Liệt kê toàn bộ file và folder trong một folder.
        folder_token = "" → root của Lark Drive.
        Trả về list các item dict.
        """
        items = []
        page_token = None

        while True:
            params = {"page_size": 200}
            if folder_token:
                params["folder_token"] = folder_token
            if page_token:
                params["page_token"] = page_token

            resp = requests.get(
                f"{LARK_BASE_URL}/drive/v1/files",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(f"Lark list_folder failed: {data}")

            result = data.get("data", {})
            items.extend(result.get("files", []))

            if not result.get("has_more"):
                break
            page_token = result.get("next_page_token")

        return items

    def traverse(self, folder_token: str = "", path: str = "/") -> list[dict]:
        """
        Traverse đệ quy toàn bộ Lark Drive.
        Trả về flat list các item với thêm field 'path' và 'parent_token'.
        """
        results = []
        items = self.list_folder(folder_token)

        for item in items:
            item["path"] = f"{path}{item['name']}/"
            item["parent_token"] = folder_token

            if item["type"] == "folder":
                results.append(item)
                results.extend(
                    self.traverse(item["token"], item["path"])
                )
            else:
                item["path"] = f"{path}{item['name']}"
                results.append(item)

        return results

    # ------------------------------------------------------------------
    # File export (Lark native formats)
    # ------------------------------------------------------------------

    def export_native_file(self, file_token: str, file_type: str) -> bytes:
        """
        Export Lark native file (Doc, Sheet, Slides...) sang binary.
        Trả về bytes của file đã export.
        """
        ext = LARK_EXPORT_MAP.get(file_type)
        if not ext:
            raise ValueError(f"Unsupported Lark native type: {file_type}")

        # Bước 1: Tạo export task
        resp = requests.post(
            f"{LARK_BASE_URL}/drive/v1/export_tasks",
            headers=self._headers(),
            json={
                "file_extension": ext,
                "token": file_token,
                "type": file_type,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Lark export task create failed: {data}")

        ticket = data["data"]["ticket"]

        # Bước 2: Poll export task cho đến khi done
        export_file_token = self._poll_export_task(ticket, file_token)

        # Bước 3: Download file đã export
        return self._download_export(export_file_token)

    def _poll_export_task(self, ticket: str, file_token: str, timeout: int = 120) -> str:
        """Poll export task, trả về export_file_token khi done."""
        deadline = time.time() + timeout
        interval = 2

        while time.time() < deadline:
            resp = requests.get(
                f"{LARK_BASE_URL}/drive/v1/export_tasks/{ticket}",
                headers=self._headers(),
                params={"token": file_token},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Lark export task poll failed: {data}")

            result = data["data"]["result"]
            job_status = result.get("job_status")

            if job_status == 0:  # Done
                return result["file_token"]
            elif job_status in (1, 2):  # In progress
                time.sleep(interval)
                interval = min(interval * 1.5, 10)
            else:
                raise RuntimeError(f"Lark export task failed with status {job_status}: {result}")

        raise TimeoutError(f"Export task {ticket} timed out after {timeout}s")

    def _download_export(self, export_file_token: str) -> bytes:
        """Download file đã export từ Lark."""
        resp = requests.get(
            f"{LARK_BASE_URL}/drive/v1/export_tasks/file/{export_file_token}/download",
            headers=self._headers(),
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()
        return resp.content

    # ------------------------------------------------------------------
    # Regular file download
    # ------------------------------------------------------------------

    def download_file(self, file_token: str) -> bytes:
        """Download file thông thường (không phải Lark native)."""
        resp = requests.get(
            f"{LARK_BASE_URL}/drive/v1/files/{file_token}/download",
            headers=self._headers(),
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()
        return resp.content
