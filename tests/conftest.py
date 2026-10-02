"""
Test setup: every test runs against a throw-away data folder and a headless Qt.
LARKSYNC_HOME must be set before any LarkSync module is imported (paths are
resolved at import time).
"""
import os
import sys
import tempfile
from pathlib import Path

_HOME = tempfile.mkdtemp(prefix="larksync-test-")
os.environ["LARKSYNC_HOME"] = _HOME
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402


def _close_log_handlers():
    """SyncThread installs a RotatingFileHandler on the root logger; Windows refuses to
    delete a file that is still open, so release it before the folder is emptied."""
    import logging
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "baseFilename", "").startswith(_HOME):
            handler.close()
            root.removeHandler(handler)


@pytest.fixture(autouse=True)
def clean_data_dir():
    """Empty the data folder between tests."""
    import shutil
    _close_log_handlers()
    for child in Path(_HOME).iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    yield
    _close_log_handlers()


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
