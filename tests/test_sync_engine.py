import json

import pytest

from sync.lark_client import FileTooLarge
from sync.sync_engine import SyncEngine


class FakeLark:
    def __init__(self, items):
        self.items = items
        self.downloaded, self.exported = [], []
        self.fail_tokens, self.too_large = set(), set()
        self.max_bytes_seen = None

    def traverse(self, folder_token="", path="/", cancel_fn=None):
        return [dict(i) for i in self.items]

    def download_file(self, token, max_bytes=0):
        self.max_bytes_seen = max_bytes
        if token in self.too_large:
            raise FileTooLarge("big")
        if token in self.fail_tokens:
            raise RuntimeError("boom")
        self.downloaded.append(token)
        return b"data-" + token.encode()

    def export_native_file(self, token, file_type):
        self.exported.append((token, file_type))
        return b"doc-" + token.encode()


class FakeDrive:
    def __init__(self):
        self.uploads, self.folders = [], {}

    def get_or_create_folder(self, name, parent_id=None):
        return self.folders.setdefault((name, parent_id), f"gf-{name}")

    def upload_file(self, content, filename, ext, parent_id=None, existing_file_id=None):
        self.uploads.append(dict(filename=filename, ext=ext, parent=parent_id, existing=existing_file_id))
        return existing_file_id or f"g-{filename}"


def item(token, name, type_="file", parent="", **extra):
    return {"token": token, "name": name, "type": type_, "parent_token": parent,
            "path": f"/{name}", **extra}


def engine(tmp_path, items, **kw):
    lark, drive = FakeLark(items), FakeDrive()
    eng = SyncEngine(lark=lark, gdrive=drive, state_path=str(tmp_path / "state.json"), **kw)
    return eng, lark, drive


def test_basic_run_mirrors_folders_and_files(tmp_path):
    eng, lark, drive = engine(tmp_path, [
        item("fld1", "Reports", "folder"),
        item("a1", "a.pdf", parent="fld1"),
        item("d1", "Plan", "docx", parent="fld1"),
    ], gdrive_root_folder_id="ROOT")
    stats = eng.run()
    assert (stats["folders"], stats["files_synced"], stats["errors"]) == (1, 2, 0)
    assert stats["cancelled"] is False
    assert drive.uploads[0]["parent"] == "gf-Reports"
    assert drive.folders[("Reports", "ROOT")]
    assert json.loads((tmp_path / "state.json").read_text())["files"]["a1"] == "g-a.pdf"


def test_conflict_skip_keeps_existing_files(tmp_path):
    """The 'Skip (keep existing)' option was shown in the UI but ignored by the engine."""
    items = [item("a1", "a.pdf")]
    (tmp_path / "state.json").write_text(json.dumps({"folders": {}, "files": {"a1": "g-old"}}))
    eng, lark, drive = engine(tmp_path, items, conflict="skip")
    stats = eng.run()
    assert stats["files_synced"] == 0 and stats["files_skipped"] == 1
    assert lark.downloaded == [] and drive.uploads == []      # not even downloaded


def test_conflict_overwrite_updates_in_place(tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"folders": {}, "files": {"a1": "g-old"}}))
    eng, _, drive = engine(tmp_path, [item("a1", "a.pdf")], conflict="overwrite")
    eng.run()
    assert drive.uploads[0]["existing"] == "g-old"


def test_incremental_skips_unmodified_files(tmp_path):
    eng, lark, _ = engine(tmp_path, [
        item("old", "old.txt", modified_time="1000"),
        item("new", "new.txt", modified_time="3000"),
        item("nots", "nots.txt"),                              # no timestamp -> sync to be safe
    ], sync_mode="incremental", last_sync_ts=2000.0)
    stats = eng.run()
    assert sorted(lark.downloaded) == ["new", "nots"]
    assert stats["files_skipped"] == 1


def test_one_failing_file_does_not_stop_the_run(tmp_path):
    eng, lark, _ = engine(tmp_path, [item("bad", "bad.pdf"), item("ok", "ok.pdf")])
    lark.fail_tokens = {"bad"}
    stats = eng.run()
    assert stats["errors"] == 1 and stats["files_synced"] == 1
    assert "bad.pdf" in stats["last_error"]


def test_too_large_is_skipped_not_an_error(tmp_path):
    eng, lark, _ = engine(tmp_path, [item("big", "big.zip")], max_file_mb=1)
    lark.too_large = {"big"}
    stats = eng.run()
    assert stats["errors"] == 0 and stats["files_skipped"] == 1
    assert lark.max_bytes_seen == 1024 * 1024                  # limit is passed down to the download


def test_shortcuts_are_skipped_without_error(tmp_path):
    eng, lark, drive = engine(tmp_path, [item("s1", "link", "shortcut")])
    stats = eng.run()
    assert stats["errors"] == 0 and drive.uploads == [] and lark.downloaded == []


def test_cancel_saves_state_and_reports_cancelled(tmp_path):
    eng, lark, _ = engine(tmp_path, [item(f"t{i}", f"f{i}.txt") for i in range(5)])
    seen = []
    eng.progress_cb = lambda msg, done=0, total=0: seen.append(done)
    eng.cancel_fn = lambda: len(lark.downloaded) >= 2
    stats = eng.run()
    assert stats["cancelled"] is True and stats["files_synced"] == 2
    saved = json.loads((tmp_path / "state.json").read_text())
    assert set(saved["files"]) == {"t0", "t1"}                 # nothing done so far is lost


def test_state_saved_even_if_traverse_fails(tmp_path):
    eng, lark, _ = engine(tmp_path, [])
    def boom(*a, **k): raise ConnectionError("offline")
    lark.traverse = boom
    with pytest.raises(ConnectionError):
        eng.run()
    assert (tmp_path / "state.json").exists()


def test_corrupt_state_is_backed_up_not_fatal(tmp_path):
    (tmp_path / "state.json").write_text("{broken")
    eng, _, _ = engine(tmp_path, [])
    assert eng.state == {"folders": {}, "files": {}}
    assert (tmp_path / "state.json.bak").exists()


def test_url_shortcut_file_is_resolved_and_exported(tmp_path):
    eng, lark, drive = engine(tmp_path, [item("u1", "Plan.url")])
    lark.download_file = lambda token, max_bytes=0: b"[InternetShortcut]\nURL=https://x.larksuite.com/docx/AbCdEfGh12345\n"
    eng.run()
    assert lark.exported == [("AbCdEfGh12345", "docx")]
    assert drive.uploads[0]["filename"] == "Plan" and drive.uploads[0]["ext"] == "docx"
