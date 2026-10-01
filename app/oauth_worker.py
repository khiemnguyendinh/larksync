"""
Background OAuth workers.

Both OAuth flows block until the user finishes in the browser (up to ~3 min).
v1.0.x ran them on the UI thread (Google, and Lark from Settings), freezing the
window — the macOS beachball — and used QTimer.singleShot from a plain Python
thread (Lark/Wizard), whose callback never ran. These QThread workers deliver
the result back through signals instead.
"""

import threading

from PyQt6.QtCore import QThread, pyqtSignal

# Keep a strong reference until the thread ends, even if the dialog that started
# it is closed first (destroying a running QThread aborts the process).
_ACTIVE: set = set()


class _OAuthWorker(QThread):
    succeeded = pyqtSignal()
    failed    = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._cancel_event = threading.Event()
        _ACTIVE.add(self)
        self.finished.connect(self._cleanup)

    def cancel(self):
        self._cancel_event.set()

    def _cleanup(self):
        _ACTIVE.discard(self)
        self.deleteLater()

    def _authorize(self):                     # pragma: no cover - overridden
        raise NotImplementedError

    def run(self):
        try:
            self._authorize()
        except Exception as exc:              # surface every failure in the UI
            self.failed.emit(str(exc) or exc.__class__.__name__)
        else:
            self.succeeded.emit()


class LarkAuthWorker(_OAuthWorker):
    def _authorize(self):
        from sync import lark_auth
        lark_auth.authorize(cancel_event=self._cancel_event)


class GoogleAuthWorker(_OAuthWorker):
    def __init__(self, credentials_path: str, token_path: str):
        super().__init__()
        self._credentials_path = credentials_path
        self._token_path = token_path

    def _authorize(self):
        from sync.google_client import GoogleDriveClient
        GoogleDriveClient(self._credentials_path, self._token_path, interactive=True).get_service()
