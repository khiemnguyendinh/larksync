"""
Lark Notifier
Gửi interactive card message vào group chat Lark sau mỗi sync job.
Dùng chung App credentials với lark_client.py (không cần app mới).

Yêu cầu:
- Bot phải được thêm vào group "Kstudy Điều Hành"
- LARK_NOTIFY_CHAT_ID phải được điền trong config.py
"""

import logging
from datetime import datetime
from typing import Optional

import requests

logger = logging.getLogger(__name__)

LARK_BASE_URL = "https://open.larksuite.com/open-apis"


class LarkNotifier:
    def __init__(self, access_token_fn, chat_id: str):
        """
        access_token_fn: callable trả về tenant_access_token (dùng lại từ LarkClient)
        chat_id: ID của group chat "Kstudy Điều Hành"
        """
        self._get_token = access_token_fn
        self.chat_id = chat_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def notify_success(self, stats: dict, duration_seconds: float):
        """Gửi card thông báo sync thành công."""
        card = self._build_success_card(stats, duration_seconds)
        self._send_card(card)

    def notify_error(self, stats: dict, duration_seconds: float, error_msg: Optional[str] = None):
        """Gửi card thông báo sync có lỗi."""
        card = self._build_error_card(stats, duration_seconds, error_msg)
        self._send_card(card)

    # ------------------------------------------------------------------
    # Card builders
    # ------------------------------------------------------------------

    def _build_success_card(self, stats: dict, duration_seconds: float) -> dict:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        duration = self._format_duration(duration_seconds)

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "Sync Drive Hoàn Tất"
                },
                "template": "green"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**Lark Drive → Google Drive** sync thành công."
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**Folders đồng bộ**\n{stats.get('folders', 0)}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**Files đồng bộ**\n{stats.get('files_synced', 0)}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**Files bỏ qua**\n{stats.get('files_skipped', 0)}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**Thời gian chạy**\n{duration}"
                            }
                        }
                    ]
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"Hoàn tất lúc {now} — Lỗi: 0"
                        }
                    ]
                }
            ]
        }

    def _build_error_card(self, stats: dict, duration_seconds: float, error_msg: Optional[str]) -> dict:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        duration = self._format_duration(duration_seconds)
        error_count = stats.get("errors", 0)

        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**Lark Drive → Google Drive** sync kết thúc với **{error_count} lỗi**. Kiểm tra `sync.log` để xem chi tiết."
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Folders đồng bộ**\n{stats.get('folders', 0)}"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Files đồng bộ**\n{stats.get('files_synced', 0)}"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Lỗi**\n{error_count}"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Thời gian chạy**\n{duration}"
                        }
                    }
                ]
            },
        ]

        # Thêm error detail nếu có
        if error_msg:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**Chi tiết lỗi cuối:**\n```\n{error_msg[:500]}\n```"
                }
            })

        elements.append({"tag": "hr"})
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"Kết thúc lúc {now} — Cần kiểm tra thủ công"
                }
            ]
        })

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"Sync Drive Có Lỗi ({error_count})"
                },
                "template": "red"
            },
            "elements": elements
        }

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    def _send_card(self, card: dict):
        """Gửi interactive card vào group chat."""
        import json

        payload = {
            "receive_id": self.chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card),
        }

        try:
            resp = requests.post(
                f"{LARK_BASE_URL}/im/v1/messages",
                headers=self._headers(),
                params={"receive_id_type": "chat_id"},
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                logger.error(f"Lark notify failed: {data}")
            else:
                logger.info("Lark notification gửi thành công.")
        except Exception as e:
            # Notification failure không được làm crash sync job
            logger.error(f"Lark notify exception: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_duration(seconds: float) -> str:
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        m, s = divmod(seconds, 60)
        if m < 60:
            return f"{m}m {s}s"
        h, m = divmod(m, 60)
        return f"{h}h {m}m {s}s"
