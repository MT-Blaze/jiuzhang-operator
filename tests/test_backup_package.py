"""军令 #17 第二步 + #34 契约：压缩打包、本地保留 3 份、路径校验与开关联动。

钉两条：插件代码全机一份（军令 #34），**不进工作区备份包**；工作区配置照常进包，
包体积与哈希如实。包内成员必须**恰好等于**清单——读 WAL 库顺手落下的 ``-wal``/``-shm``
边车一旦混进包，恢复侧「清单外文件」门禁会把整包判废。

运行：``.venv/Scripts/python.exe -m unittest tests.test_backup_package``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))


import os
import shutil
import sqlite3
import tarfile
import tempfile
import unittest
from pathlib import Path

from app.core import backup, restore, toml_io, wire
from app.core.backup_codec import open_package
from app.core.config import settings

PROVIDER = "org.jiuzhang.bank-engine"
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
            os.environ.get("JZO_PLUGINS_DIR"),
            settings.workspace_id,
        )
        os.environ["JZO_DATA_DIR"] = str(self.data)
        os.environ["JZO_PLUGINS_DIR"] = str(self.plugins)
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
        for key, value in (("JZO_DATA_DIR", data), ("JZO_PLUGINS_DIR", plugins)):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
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
        manifest = toml_io.load(manifest_path)
        self.assertEqual(backup.sha256_file(package), manifest["package"]["sha256"])
        self.assertEqual(package.stat().st_size, manifest["package"]["size"])
        self.assertEqual(result["package_sha256"], manifest["package"]["sha256"])
        with open_package(package, "rb") as compressed:
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
            (folder / f"manifest_{stamp}.toml").write_text("files = []", encoding="utf-8")
        (folder / "notes.txt").write_text("keep me", encoding="utf-8")
        deleted = backup.prune_local_backups(folder, keep=3)
        remaining = sorted(path.name for path in folder.iterdir())
        self.assertEqual(7, len(remaining))
        for stamp in ("20260103_010101_001", "20260104_010101_001", "20260105_010101_001"):
            self.assertIn(f"backup_{stamp}.zst", remaining)
            self.assertIn(f"manifest_{stamp}.toml", remaining)
        self.assertNotIn("backup_20260101_010101_001.zst", remaining)
        self.assertNotIn("manifest_20260101_010101_001.toml", remaining)
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

    def test_05_plugin_code_never_enters_the_package(self) -> None:
        first = backup.create_local_backup(WS_ID, local_dir=self.out)
        first_size = Path(first["package"]).stat().st_size

        code = self.plugins / "org.jiuzhang.demo"
        (code / "dist").mkdir(parents=True)
        (code / "plugin.toml").write_text('id = "org.jiuzhang.demo"\n', encoding="utf-8", newline="\n")
        (code / "dist" / "plugin.js").write_text("console.log(1)", encoding="utf-8")
        (code / "__pycache__").mkdir()
        (code / "__pycache__" / "junk.pyc").write_bytes(b"\x00" * 4096)
        (code / ".git").mkdir()
        (code / ".git" / "config").write_text("[core]", encoding="utf-8")
        (self.ws_dir / "plugin_state.toml").write_text("enabled = true\n", encoding="utf-8")
        # 历史残留：旧版曾把插件代码复制进工作区，也必须整目录跳过。
        legacy = self.ws_dir / "plugins" / "org.jiuzhang.demo"
        legacy.mkdir(parents=True)
        (legacy / "plugin.toml").write_text('id = "org.jiuzhang.demo"\n', encoding="utf-8")

        result = backup.create_local_backup(WS_ID, local_dir=self.out)
        package = Path(result["package"])
        manifest = toml_io.load(Path(result["manifest"]))
        self.assertEqual(package.stat().st_size, manifest["package"]["size"], "包体积必须如实")
        self.assertEqual(backup.sha256_file(package), manifest["package"]["sha256"])

        with open_package(package, "rb") as compressed:
            with tarfile.open(fileobj=compressed, mode="r") as archive:
                names = set(archive.getnames())
        self.assertIn("ws/plugin_state.toml", names)
        self.assertFalse([name for name in names if "plugins/" in name],
                         "插件代码全机一份，工作区备份里不许出现")
        self.assertFalse([name for name in names if "__pycache__" in name or "/.git/" in name],
                         "缓存与版本库不许进包")

        self.assertEqual([], manifest["plugins"])
        self.assertFalse([item for item in manifest["files"] if item["category"] == "plugins"])
        self.assertGreaterEqual(manifest["package"]["size"], first_size, "包体积仍须如实")
        self.assertTrue(all(row["plugin_count"] == 0
                            for row in backup.list_local_backups(self.out, WS_ID)))

    def test_06_plugin_dirs_from_any_root_are_never_packed(self) -> None:
        """全局 plugins/ 与工作区 plugins/ 都不属于工作区备份的数据面。"""
        code = self.plugins / "org.jiuzhang.override-check"
        code.mkdir(parents=True)
        (code / "plugin.toml").write_text('id = "org.jiuzhang.override-check"\n', encoding="utf-8")
        (self.ws_dir / "plugins").mkdir(parents=True)
        in_ws = self.ws_dir / "plugins" / "org.jiuzhang.in-workspace"
        in_ws.mkdir()
        (in_ws / "plugin.toml").write_text(
            'id = "org.jiuzhang.in-workspace"\n', encoding="utf-8"
        )
        (self.ws_dir / "plugin_state.toml").write_text("enabled = true\n", encoding="utf-8")
        manifest = toml_io.load(
            Path(backup.create_local_backup(WS_ID, local_dir=self.out)["manifest"])
        )
        self.assertEqual([], manifest["plugins"])
        paths = {item["path"] for item in manifest["files"]}
        self.assertIn("ws/plugin_state.toml", paths)
        self.assertFalse([rel for rel in paths if "plugins/" in rel])

    def test_07_wal_sidecars_never_smuggle_into_the_package(self) -> None:
        db = self.ws_dir / "banks" / f"{PROVIDER}.db"
        con = sqlite3.connect(db)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("INSERT INTO questions VALUES ('q_2', '题干二')")
        con.commit()
        con.close()

        result = backup.create_local_backup(WS_ID, local_dir=self.out, keep=3)
        package = Path(result["package"])
        manifest = toml_io.load(Path(result["manifest"]))
        with open_package(package, "rb") as compressed:
            with tarfile.open(fileobj=compressed, mode="r") as archive:
                names = sorted(archive.getnames())
        self.assertEqual(sorted(str(item["path"]) for item in manifest["files"]), names,
                         "包成员必须恰好等于清单，多一个边车都会让整包判废")
        self.assertFalse([name for name in names if name.endswith(backup.SIDECAR_SUFFIXES)])

        plan = restore.prepare_restore(
            package, manifest, [item["path"] for item in manifest["files"]],
            WS_ID, self.root / "work",
        )
        self.assertEqual(names, sorted(plan["selected"]))
        restore.cleanup_plan(plan)

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
