"""军令 #17 第二步契约：Zstd 打包、本地保留 3 份、路径校验与开关联动。

运行：``.venv/Scripts/python.exe -m unittest tests.test_backup_package``
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
import unittest
from compression import zstd
from pathlib import Path

from app.core import backup
from app.core.config import settings

PROVIDER = "org.jiuzhang.core-bank"
WS_ID = "ws_abcdef0123456789"


class PackageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.plugins = self.root / "plugins"
        self.plugins.mkdir(parents=True)
        self.ws_dir = self.data / "workspaces" / WS_ID
        (self.ws_dir / "banks").mkdir(parents=True)
        self._saved = (
            os.environ.get("JZO_DATA_DIR"),
            settings.plugins_dir,
            settings.workspace_id,
        )
        os.environ["JZO_DATA_DIR"] = str(self.data)
        settings.plugins_dir = self.plugins
        settings.workspace_id = WS_ID
        con = sqlite3.connect(self.ws_dir / "banks" / f"{PROVIDER}.db")
        con.execute("CREATE TABLE questions (id TEXT PRIMARY KEY, stem TEXT)")
        con.execute("INSERT INTO questions VALUES ('q_1', '题干')")
        con.commit()
        con.close()
        (self.ws_dir / "uploads").mkdir()
        (self.ws_dir / "uploads" / "a.png").write_bytes(b"PNG")
        self.out = self.root / "backups"

    def tearDown(self) -> None:
        data, plugins, ws = self._saved
        if data is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = data
        settings.plugins_dir = plugins
        settings.workspace_id = ws
        self.tmp.cleanup()

    def test_01_package_is_readable_and_hash_is_filled(self) -> None:
        result = backup.create_local_backup(WS_ID, local_dir=self.out, keep=3)
        package = Path(result["package"])
        manifest_path = Path(result["manifest"])
        self.assertTrue(package.is_file())
        self.assertTrue(package.name.startswith("backup_"))
        self.assertTrue(package.name.endswith(".zst"))
        self.assertTrue(manifest_path.is_file())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(backup.sha256_file(package), manifest["package"]["sha256"])
        self.assertEqual(package.stat().st_size, manifest["package"]["size"])
        self.assertEqual(result["package_sha256"], manifest["package"]["sha256"])
        with zstd.ZstdFile(package, "rb") as compressed:
            with tarfile.open(fileobj=compressed, mode="r") as archive:
                names = set(archive.getnames())
        self.assertIn(f"banks/{PROVIDER}.db", names)
        self.assertIn("uploads/a.png", names)
        self.assertNotIn(f"banks/{PROVIDER}.db-wal", names)

    def test_02_retention_keeps_latest_three_and_leaves_foreign_files(self) -> None:
        folder = self.root / "retention"
        folder.mkdir()
        for stamp in (
            "20260101_010101_001", "20260102_010101_001", "20260103_010101_001",
            "20260104_010101_001", "20260105_010101_001",
        ):
            (folder / f"backup_{stamp}.zst").write_bytes(b"z")
            (folder / f"manifest_{stamp}.json").write_text("{}", encoding="utf-8")
        (folder / "notes.txt").write_text("keep me", encoding="utf-8")
        deleted = backup.prune_local_backups(folder, keep=3)
        remaining = sorted(path.name for path in folder.iterdir())
        self.assertEqual(7, len(remaining))
        for stamp in ("20260103_010101_001", "20260104_010101_001", "20260105_010101_001"):
            self.assertIn(f"backup_{stamp}.zst", remaining)
            self.assertIn(f"manifest_{stamp}.json", remaining)
        self.assertNotIn("backup_20260101_010101_001.zst", remaining)
        self.assertNotIn("manifest_20260101_010101_001.json", remaining)
        self.assertIn("notes.txt", remaining)
        self.assertEqual(4, len(deleted))

    def test_03_local_dir_validation(self) -> None:
        with self.assertRaises(backup.BackupError):
            backup.validate_local_dir("relative/path")
        with self.assertRaises(backup.BackupError):
            backup.validate_local_dir(self.plugins / "inside")
        accepted = backup.validate_local_dir(self.root / "ok")
        self.assertTrue(accepted.is_dir())
        self.assertTrue(accepted.is_absolute())

    def test_04_toggle_linkage(self) -> None:
        both = backup.normalize_toggles({"local_enabled": True, "webdav_enabled": True})
        self.assertTrue(both["local_enabled"] and both["webdav_enabled"])
        webdav_only = backup.normalize_toggles(
            {"local_enabled": False, "webdav_enabled": True}
        )
        self.assertTrue(webdav_only["local_enabled"])
        self.assertTrue(webdav_only["webdav_enabled"])
        local_off = backup.normalize_toggles(
            {"local_enabled": False, "webdav_enabled": False}
        )
        self.assertFalse(local_off["local_enabled"] or local_off["webdav_enabled"])

        saved = backup.save_backup_settings(
            {
                "webdav_enabled": True,
                "local_dir": str(self.out),
                "url": "https://dav.example.com",
                "username": "teacher",
                "password": "plain-secret",
            },
            WS_ID,
        )
        self.assertTrue(saved["local_enabled"])
        self.assertTrue(saved["webdav_enabled"])
        loaded = backup.load_backup_settings(WS_ID)
        self.assertEqual("plain-secret", loaded["password"])
        public = backup.public_backup_settings(loaded)
        self.assertNotIn("password", public)
        self.assertEqual("••••••••", public["password_masked"])
        self.assertTrue(public["password_set"])

        turned_off = backup.save_backup_settings(
            {"local_enabled": False, "webdav_enabled": True}, WS_ID
        )
        self.assertFalse(turned_off["local_enabled"])
        self.assertFalse(turned_off["webdav_enabled"])
        self.assertFalse(backup.load_backup_settings(WS_ID)["webdav_enabled"])


if __name__ == "__main__":
    unittest.main()
