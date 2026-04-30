"""
Sync Engine
Logic chính: traverse Lark Drive → mirror sang Google Drive
- Mirror cấu trúc folder
- Export Lark native files sang Google native format
- Download regular files và upload
- Overwrite nếu đã tồn tại (dựa trên state file)
"""

import json
import logging
import os
from typing import Optional

from .lark_client import LarkClient, LARK_EXPORT_MAP, LARK_NATIVE_TYPES
from .google_client import GoogleDriveClient

logger = logging.getLogger(__name__)


class SyncEngine:
    def __init__(
        self,
        lark: LarkClient,
        gdrive: GoogleDriveClient,
        state_path: str,
        gdrive_root_folder_id: Optional[str] = None,
        progress_cb=None,
        cancel_fn=None,
        max_file_mb: int = 0,
    ):
        self.lark = lark
        self.gdrive = gdrive
        self.state_path = state_path
        self.gdrive_root_folder_id = gdrive_root_folder_id
        self.progress_cb  = progress_cb   # callable(msg, completed, total)
        self.cancel_fn    = cancel_fn     # callable() → bool
        self.max_file_mb  = max_file_mb   # 0 = no limit

        # State structure:
        # {
        #   "folders": { "lark_folder_token": "gdrive_folder_id", ... },
        #   "files":   { "lark_file_token":   "gdrive_file_id",   ... }
        # }
        self.state = self._load_state()

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _load_state(self) -> dict:
        if os.path.exists(self.state_path):
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"folders": {}, "files": {}}

    def _save_state(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Main sync entry
    # ------------------------------------------------------------------

    def run(self):
        """Run the full sync job."""
        logger.info("=== START SYNC: Lark Drive → Google Drive ===")

        stats = {"folders": 0, "files_synced": 0, "files_skipped": 0, "errors": 0}

        if self.progress_cb:
            self.progress_cb("Traversing Lark Drive…", 0, 0)

        all_items = self.lark.traverse(folder_token="", path="/")
        total = len(all_items)
        logger.info(f"Found {total} items")

        for idx, item in enumerate(all_items):
            if self.cancel_fn and self.cancel_fn():
                logger.info("Sync cancelled by user.")
                break

            try:
                if item["type"] == "folder":
                    self._sync_folder(item)
                    stats["folders"] += 1
                else:
                    synced = self._sync_file(item)
                    if synced:
                        stats["files_synced"] += 1
                    else:
                        stats["files_skipped"] += 1
            except Exception as e:
                logger.error(f"Error syncing '{item.get('name')}' ({item.get('token')}): {e}")
                stats["errors"] += 1

            if self.progress_cb:
                self.progress_cb(
                    f"[{idx + 1}/{total}] {item.get('name', '')}",
                    idx + 1,
                    total,
                )

        self._save_state()

        logger.info(
            f"=== SYNC COMPLETE ===\n"
            f"  Folders: {stats['folders']}\n"
            f"  Files synced: {stats['files_synced']}\n"
            f"  Files skipped: {stats['files_skipped']}\n"
            f"  Errors: {stats['errors']}"
        )
        return stats

    # ------------------------------------------------------------------
    # Folder sync
    # ------------------------------------------------------------------

    def _sync_folder(self, item: dict):
        """Tạo folder tương ứng trên GDrive nếu chưa có."""
        token = item["token"]
        name = item["name"]
        parent_token = item.get("parent_token", "")

        # Xác định parent GDrive folder ID
        if parent_token == "":
            parent_gdrive_id = self.gdrive_root_folder_id
        else:
            parent_gdrive_id = self.state["folders"].get(parent_token)
            if not parent_gdrive_id:
                logger.warning(f"Parent folder chưa được sync: {parent_token}, skip '{name}'")
                return

        if token not in self.state["folders"]:
            gdrive_id = self.gdrive.get_or_create_folder(name, parent_gdrive_id)
            self.state["folders"][token] = gdrive_id
            logger.info(f"[FOLDER] Tạo: {item['path']} → {gdrive_id}")
        else:
            logger.debug(f"[FOLDER] Đã có: {item['path']}")

    # ------------------------------------------------------------------
    # File sync
    # ------------------------------------------------------------------

    def _sync_file(self, item: dict) -> bool:
        """
        Sync một file: export/download từ Lark rồi upload lên GDrive.
        Trả về True nếu sync thành công, False nếu skip.
        """
        token = item["token"]
        name = item["name"]
        file_type = item["type"]
        parent_token = item.get("parent_token", "")

        # Xác định parent GDrive folder ID
        if parent_token == "":
            parent_gdrive_id = self.gdrive_root_folder_id
        else:
            parent_gdrive_id = self.state["folders"].get(parent_token)
            if not parent_gdrive_id:
                logger.warning(f"Parent folder chưa sync: {parent_token}, skip file '{name}'")
                return False

        # Skip files that exceed the size limit (size field may not always be present)
        if self.max_file_mb > 0:
            size_bytes = item.get("size", 0)
            if size_bytes and size_bytes > self.max_file_mb * 1024 * 1024:
                logger.warning(
                    f"Skipping large file '{name}' "
                    f"({size_bytes / 1024 / 1024:.1f} MB > {self.max_file_mb} MB limit)"
                )
                return False

        # Kiểm tra existing GDrive file ID (để overwrite)
        existing_gdrive_id = self.state["files"].get(token)

        # Xác định extension và tên file đích
        if file_type in LARK_NATIVE_TYPES:
            ext = LARK_EXPORT_MAP[file_type]
            # Tên file đích: dùng tên gốc, đối với Google native không cần ext
            display_name = name
        else:
            # Regular file: giữ tên gốc
            ext = self._get_ext(name)
            display_name = name

        logger.info(f"[FILE] Syncing: {item['path']} (type={file_type})")

        # Download / Export từ Lark
        if file_type in LARK_NATIVE_TYPES:
            content = self.lark.export_native_file(token, file_type)
        else:
            content = self.lark.download_file(token)

            # .url shortcut files: parse URL → resolve to a real Lark doc token and export
            if name.lower().endswith(".url") or (content and content[:4] == b"[Int"):
                resolved = self._resolve_url_file(content, name)
                if resolved:
                    real_token, real_type = resolved
                    logger.info(f"[FILE] .url resolved → type={real_type}, token={real_token}")
                    try:
                        content      = self.lark.export_native_file(real_token, real_type)
                        ext          = LARK_EXPORT_MAP[real_type]
                        display_name = name.removesuffix(".url").removesuffix(".URL")
                    except Exception as e:
                        logger.warning(f"[FILE] .url export failed: {e} — uploading as-is")
                else:
                    logger.warning(f"[FILE] .url could not resolve Lark token: '{name}' — skip")
                    return False

        # Upload / Overwrite lên GDrive
        gdrive_id = self.gdrive.upload_file(
            content=content,
            filename=display_name,
            ext=ext,
            parent_id=parent_gdrive_id,
            existing_file_id=existing_gdrive_id,
        )

        self.state["files"][token] = gdrive_id
        action = "Overwrite" if existing_gdrive_id else "Upload mới"
        logger.info(f"[FILE] {action}: '{name}' → GDrive ID: {gdrive_id}")
        return True

    # ------------------------------------------------------------------
    # .url file resolver
    # ------------------------------------------------------------------

    _URL_TYPE_MAP = {
        "/docx/":   "docx",
        "/docs/":   "docx",
        "/wiki/":   "docx",
        "/sheets/": "sheet",
        "/sheet/":  "sheet",
        "/slides/": "slides",
        "/base/":   "bitable",
    }

    def _resolve_url_file(self, content: bytes, name: str) -> tuple[str, str] | None:
        """
        Parse a Windows .url shortcut file, extract a Lark doc token and type.
        Returns (doc_token, lark_type) or None if the URL is not a recognisable Lark doc.
        """
        import re
        import urllib.parse
        try:
            text  = content.decode("utf-8", errors="ignore")
            match = re.search(r"URL=(.+)", text)
            if not match:
                return None
            url = match.group(1).strip()
        except Exception:
            return None

        lark_type = None
        for fragment, ltype in self._URL_TYPE_MAP.items():
            if fragment in url:
                lark_type = ltype
                break

        if not lark_type:
            logger.warning(f"[FILE] .url points to non-Lark URL, skipping: {url[:80]}")
            return None

        try:
            path  = urllib.parse.urlparse(url).path
            token = path.rstrip("/").split("/")[-1]
            if len(token) < 8:
                return None
            return token, lark_type
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_ext(filename: str) -> str:
        """Lấy extension (không có dấu chấm) từ tên file."""
        if "." in filename:
            return filename.rsplit(".", 1)[-1].lower()
        return ""
