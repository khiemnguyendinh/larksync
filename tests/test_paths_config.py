import json
import os
import stat
import sys

import pytest

from sync import paths
from sync.paths import migrate_legacy_data, write_private


def test_write_private_is_atomic_and_owner_only(tmp_path):
    target = tmp_path / "secret.json"
    write_private(target, '{"a": 1}')
    write_private(target, '{"a": 2}')                  # overwrite
    assert json.loads(target.read_text()) == {"a": 2}
    assert not [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(target).st_mode) == 0o600


def test_write_private_binary_and_unicode(tmp_path):
    write_private(tmp_path / "b.bin", b"\x00\x01")
    assert (tmp_path / "b.bin").read_bytes() == b"\x00\x01"
    write_private(tmp_path / "u.txt", "Đồng bộ")
    assert (tmp_path / "u.txt").read_text(encoding="utf-8") == "Đồng bộ"


def test_migrate_legacy_copies_once_and_keeps_source(tmp_path):
    src, dst = tmp_path / "old", tmp_path / "new"
    src.mkdir()
    (src / "app_config.json").write_text('{"lark_app_id": "cli_x"}')
    (src / "lark_token.json").write_text('{"access_token": "t"}')
    (src / "google_token.pkl").write_bytes(b"pkl")
    (src / "unrelated.py").write_text("print('original CLI script')")

    copied = migrate_legacy_data(src, dst)

    assert set(copied) == {"app_config.json", "lark_token.json", "google_token.pkl"}
    assert (src / "app_config.json").exists()          # never deletes the old folder
    assert not (dst / "unrelated.py").exists()          # only files LarkSync wrote
    assert migrate_legacy_data(src, dst) == []          # second run is a no-op


def test_migrate_does_not_overwrite_new_install(tmp_path):
    src, dst = tmp_path / "old", tmp_path / "new"
    src.mkdir(); dst.mkdir()
    (src / "app_config.json").write_text('{"lark_app_id": "old"}')
    (dst / "app_config.json").write_text('{"lark_app_id": "new"}')
    assert migrate_legacy_data(src, dst) == []
    assert json.loads((dst / "app_config.json").read_text())["lark_app_id"] == "new"


def test_migrate_with_nothing_to_migrate(tmp_path):
    assert migrate_legacy_data(tmp_path / "missing", tmp_path / "new") == []


@pytest.mark.parametrize("platform,expected", [
    ("darwin", ("Library", "Application Support", "LarkSync")),
    ("linux", ("LarkSync",)),
])
def test_default_data_dir_per_platform(monkeypatch, tmp_path, platform, expected):
    monkeypatch.delenv("LARKSYNC_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(paths.sys, "platform", platform)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    resolved = paths._resolve_app_dir()
    assert resolved.parts[-len(expected):] == expected
    assert "Documents" not in resolved.parts            # the whole point of the move


def test_default_data_dir_windows_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.delenv("LARKSYNC_HOME", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setattr(paths.sys, "platform", "win32")
    assert paths._resolve_app_dir() == tmp_path / "Roaming" / "LarkSync"


def test_config_roundtrip_and_corruption(monkeypatch):
    from app.config_manager import ConfigManager, CONFIG_FILE
    c = ConfigManager()
    c.update({"schedule": "daily", "lark_app_secret": "s3cret"})
    assert ConfigManager().get("schedule") == "daily"

    CONFIG_FILE.write_text("{ not json")
    fresh = ConfigManager()                             # must not crash
    assert fresh.get("schedule") == "weekly"
    assert CONFIG_FILE.with_suffix(".json.bak").exists()   # user's data is kept


def test_config_non_dict_root_is_treated_as_corrupt():
    from app.config_manager import ConfigManager, CONFIG_FILE
    ConfigManager()
    CONFIG_FILE.write_text("[1, 2, 3]")
    assert ConfigManager().get("sync_mode") == "incremental"
