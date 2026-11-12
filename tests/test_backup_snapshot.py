"""军令 #17 第一步 + #34 契约：当前工作区一致性快照与 manifest。

钉六件事：
1. 有 WAL 且连接仍开着时，快照仍可读、题目数与活库一致，且不把边车原样装包；
2. manifest 字段齐全（工作区、schema 版本、库标识、题目数、逐题哈希、
   图片哈希、文件清单、生成时间、待回填的 Zstd 包哈希）；
3. 逐题哈希能按快照库原样复算；
4. default 工作区不把其他工作区、宿主状态与凭据文件卷进来；
5. **本区配置（``plugin_state.toml`` 等）进包，插件代码一概不进**——插件代码全机一份；
6. 旧包里的插件目录摘要仍可由文件清单复算并校验，篡改或漏文件即被拒绝。

运行：``.venv/Scripts/python.exe -m unittest tests.test_backup_snapshot``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))


import copy
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core import backup, backup_manifest, restore
from app.core.config import settings

PROVIDER = "org.jiuzhang.bank-engine"
WS_ID = "ws_0123456789abcdef"


def _make_bank(path: Path, rows: int) -> sqlite3.Connection:
    """建一个带 questions 表的最小库并保持 WAL 连接打开。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA user_version=7")
    con.execute(
        "CREATE TABLE questions ("
        " id TEXT PRIMARY KEY, stem TEXT NOT NULL, difficulty TEXT, "
        " images_json TEXT, updated_at TEXT)"
    )
    for index in range(rows):
        con.execute(
            "INSERT INTO questions (id, stem, difficulty, images_json, updated_at)"
            " VALUES (?, ?, 'L2', '[]', ?)",
            (f"q_{index:03d}", f"题干 {index}", "2026-10-24T20:00:00+08:00"),
        )
    con.commit()
    return con


class SnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir(parents=True)
        self.ws_dir = self.data / "workspaces" / WS_ID
        self.ws_dir.mkdir(parents=True)
        self._saved_data = os.environ.get("JZO_DATA_DIR")
        self._saved_ws = settings.workspace_id
        os.environ["JZO_DATA_DIR"] = str(self.data)
        settings.workspace_id = WS_ID
        self.conn = _make_bank(self.ws_dir / "banks" / f"{PROVIDER}.db", 5)
        (self.ws_dir / "uploads").mkdir()
        (self.ws_dir / "uploads" / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\nDATA")
        (self.ws_dir / "config.toml").write_text('provider = "x"\n', encoding="utf-8")
        (self.ws_dir / "backup.toml").write_text('password = "secret"\n', encoding="utf-8")
        (self.ws_dir / ".local_token").write_text("token", encoding="utf-8")

    def tearDown(self) -> None:
        self.conn.close()
        settings.workspace_id = self._saved_ws
        if self._saved_data is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = self._saved_data
        self.tmp.cleanup()

    def _snapshot(self):
        # 库发现必须真的跑过：manifest 里的题目数与逐题哈希全靠它挑中题仓库。
        with mock.patch.object(
            backup_manifest, "select_bank_db", wraps=backup_manifest.select_bank_db
        ) as spy:
            stage, manifest = backup.snapshot_workspace(WS_ID)
        spy.assert_called_once()
        return stage, manifest

    def test_01_wal_snapshot_is_consistent_and_self_contained(self) -> None:
        wal = Path(str(self.ws_dir / "banks" / f"{PROVIDER}.db") + "-wal")
        self.assertTrue(wal.exists(), "测试前置：WAL 边车必须已经产生")
        stage, manifest = self._snapshot()
        try:
            snap_db = stage / "banks" / f"{PROVIDER}.db"
            con = sqlite3.connect(snap_db)
            try:
                self.assertEqual(5, con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
                self.assertEqual(7, con.execute("PRAGMA user_version").fetchone()[0])
            finally:
                con.close()
            self.assertFalse((stage / "banks" / f"{PROVIDER}.db-wal").exists())
            self.assertEqual(5, manifest["question_count"])
            self.assertEqual(7, manifest["schema_version"])
            self.assertEqual(PROVIDER, manifest["library"]["plugin_id"])
            self.assertEqual(5, len(manifest["question_hashes"]))
        finally:
            import shutil

            shutil.rmtree(stage, ignore_errors=True)

    def test_02_manifest_fields_are_complete(self) -> None:
        stage, manifest = self._snapshot()
        try:
            for key in (
                "workspace_id", "schema_version", "library", "question_count",
                "question_hashes", "images", "images_hash", "files",
                "generated_at", "package",
            ):
                self.assertIn(key, manifest)
            self.assertEqual(WS_ID, manifest["workspace_id"])
            self.assertEqual("", manifest["package"]["sha256"])
            self.assertIn("filename", manifest["package"])
            self.assertEqual(1, len(manifest["images"]))
            self.assertIn("sha256", manifest["images"][0])
            categories = {item["path"]: item["category"] for item in manifest["files"]}
            self.assertEqual("bank", categories[f"banks/{PROVIDER}.db"])
            self.assertEqual("uploads", categories["uploads/pic.png"])
            self.assertEqual("other", categories["config.toml"])
            required = {item["path"]: item["required"] for item in manifest["files"]}
            self.assertTrue(required[f"banks/{PROVIDER}.db"])
            self.assertTrue(required["uploads/pic.png"])
            self.assertNotIn("backup.toml", categories)
            self.assertNotIn(".local_token", categories)
        finally:
            import shutil

            shutil.rmtree(stage, ignore_errors=True)

    def test_03_question_hashes_can_be_recomputed(self) -> None:
        stage, manifest = self._snapshot()
        try:
            snap_db = stage / "banks" / f"{PROVIDER}.db"
            count, hashes, _ = backup.question_hashes(snap_db)
            self.assertEqual(manifest["question_count"], count)
            self.assertEqual(manifest["question_hashes"], hashes)
            self.assertFalse(backup.verify_manifest_hashes(manifest, stage))
            self.assertTrue(backup.manifest_question_hashes_ok(manifest, snap_db))
            # 改动一题后逐题哈希必须失配
            con = sqlite3.connect(snap_db)
            con.execute("UPDATE questions SET stem='改了' WHERE id='q_000'")
            con.commit()
            con.close()
            self.assertFalse(backup.manifest_question_hashes_ok(manifest, snap_db))
        finally:
            import shutil

            shutil.rmtree(stage, ignore_errors=True)

    def test_04_default_workspace_leaves_other_workspaces_out(self) -> None:
        other = self.data / "workspaces" / "ws_ffffffffffffffff"
        other.mkdir(parents=True)
        (other / "banks").mkdir()
        (other / "banks" / "foreign.db").write_bytes(b"not ours")
        (other / "plugins").mkdir()
        (other / "plugins" / "org.jiuzhang.foreign").mkdir()
        (other / "plugins" / "org.jiuzhang.foreign" / "plugin.toml").write_text(
            'id = "org.jiuzhang.foreign"\n', encoding="utf-8"
        )
        (self.data / "plugin_state.toml").write_text("", encoding="utf-8")
        (self.data / "workspaces.toml").write_text("workspaces = []\n", encoding="utf-8")
        settings.workspace_id = None
        stage, manifest = backup.snapshot_workspace("default")
        try:
            paths = {item["path"] for item in manifest["files"]}
            self.assertFalse(any(path.startswith("workspaces/") for path in paths))
            self.assertNotIn("plugin_state.toml", paths)
            self.assertNotIn("workspaces.toml", paths)
            self.assertFalse(
                any(path.startswith("ws/") for path in paths),
                "default 区自己没配覆盖层时，不许把别区的 plugins/ 当成 ws/ 卷进来",
            )
            self.assertEqual([], manifest["plugins"])
        finally:
            import shutil

            shutil.rmtree(stage, ignore_errors=True)


class OverlaySnapshotTest(unittest.TestCase):
    """军令 #34：本区配置进包；插件代码全局一份，工作区新旧副本一概不进。"""

    PLUGIN = "org.jiuzhang.demo"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.ws_dir = self.data / "workspaces" / WS_ID
        (self.ws_dir / "banks").mkdir(parents=True)
        self.plugins = self.root / "plugins"
        self._saved_data = os.environ.get("JZO_DATA_DIR")
        self._saved_plugins = os.environ.get("JZO_PLUGINS_DIR")
        self._saved_ws = settings.workspace_id
        os.environ["JZO_DATA_DIR"] = str(self.data)
        os.environ["JZO_PLUGINS_DIR"] = str(self.plugins)
        settings.workspace_id = WS_ID
        self.conn = _make_bank(self.ws_dir / "banks" / f"{PROVIDER}.db", 2)
        (self.ws_dir / "plugin_state.toml").write_text(
            'enabled = "demo"\n', encoding="utf-8"
        )
        (self.ws_dir / "startup.toml").write_text('page = "workspace"\n', encoding="utf-8")
        (self.ws_dir / ".env").write_text("SECRET=1", encoding="utf-8")
        (self.ws_dir / "backup.toml").write_text('password = "secret"\n', encoding="utf-8")
        # 全局插件代码：备份必须视而不见。
        code = self.plugins / self.PLUGIN
        (code / "dist").mkdir(parents=True)
        (code / "plugin.toml").write_text('id = "%s"\n' % self.PLUGIN, encoding="utf-8")
        (code / "dist" / "plugin.js").write_text("console.log(1)", encoding="utf-8")
        # 历史残留的工作区插件副本（旧版会复制进区）：也应整目录跳过。
        legacy = self.ws_dir / "plugins" / self.PLUGIN
        legacy.mkdir(parents=True)
        (legacy / "plugin.toml").write_text('id = "%s"\n' % self.PLUGIN, encoding="utf-8")
        foreign = self.data / "workspaces" / "ws_ffffffffffffffff" / "plugins" / "org.jiuzhang.foreign"
        foreign.mkdir(parents=True)
        (foreign / "plugin.toml").write_text('id = "org.jiuzhang.foreign"\n', encoding="utf-8")

    def tearDown(self) -> None:
        self.conn.close()
        settings.workspace_id = self._saved_ws
        for key, value in (("JZO_DATA_DIR", self._saved_data), ("JZO_PLUGINS_DIR", self._saved_plugins)):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def _manifest(self) -> tuple[Path, dict]:
        return backup.snapshot_workspace(WS_ID)

    def test_05_state_files_are_packed_but_no_plugin_code_at_all(self) -> None:
        stage, manifest = self._manifest()
        try:
            categories = {item["path"]: item["category"] for item in manifest["files"]}
            required = {item["path"]: item["required"] for item in manifest["files"]}
            self.assertEqual("other", categories["ws/plugin_state.toml"])
            self.assertEqual("other", categories["ws/startup.toml"])
            self.assertFalse(required["ws/plugin_state.toml"], "配置可勾掉")
            for leaked in (
                f"ws/plugins/{self.PLUGIN}/plugin.toml",
                f"plugins/{self.PLUGIN}/plugin.toml",
                "ws/.env", "ws/backup.toml",
                "ws/plugins/org.jiuzhang.foreign/plugin.toml",
            ):
                self.assertNotIn(leaked, categories, f"{leaked} 不该进包")
            self.assertFalse([rel for rel, kind in categories.items() if kind == "plugins"],
                             "插件代码已全局化，包里不许再出现 plugins 分组")
            self.assertFalse((stage / "ws" / "plugins").exists())
            self.assertTrue((stage / "ws" / "plugin_state.toml").is_file())
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def test_06_manifest_has_no_plugin_inventory_for_new_packages(self) -> None:
        stage, manifest = self._manifest()
        try:
            self.assertEqual([], manifest["plugins"])
            self.assertEqual([], [item for item in manifest["files"]
                                  if item["category"] == "plugins"])
            restore.validate_manifest({**manifest, "package": {
                "filename": "backup_20260101_010101_001.zst",
                "sha256": "0" * 64, "size": 1}}, WS_ID)
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def test_07_old_package_plugin_digest_is_still_checked(self) -> None:
        """旧包（含 ws/plugins 条目）仍要验摘要；篡改或漏文件当场拒。"""
        stage, manifest = self._manifest()
        try:
            package = {
                "filename": "backup_20260101_010101_001.zst",
                "sha256": "0" * 64, "size": 1,
            }
            old = copy.deepcopy(manifest)
            old["files"].append({
                "path": f"ws/plugins/{self.PLUGIN}/plugin.toml", "size": 3,
                "sha256": "a" * 64, "category": "plugins", "required": False,
            })
            old["plugins"] = backup.plugins_inventory(old["files"])
            base = {**old, "package": package}
            restore.validate_manifest(base, WS_ID)
            tampered = copy.deepcopy(base)
            tampered["plugins"][0]["sha256"] = "f" * 64
            with self.assertRaises(restore.RestoreError) as caught:
                restore.validate_manifest(tampered, WS_ID)
            self.assertIn("摘要", str(caught.exception))
            dropped = copy.deepcopy(base)
            dropped["files"] = [item for item in dropped["files"]
                                if item["category"] != "plugins"]
            with self.assertRaises(restore.RestoreError):
                restore.validate_manifest(dropped, WS_ID)
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def test_08_workspace_plugin_dirs_are_skipped_entirely(self) -> None:
        evil = self.ws_dir / "plugins" / "Evil"
        evil.mkdir()
        (evil / "x.js").write_text("x", encoding="utf-8")
        stage, manifest = self._manifest()
        try:
            paths = {item["path"] for item in manifest["files"]}
            self.assertFalse([rel for rel in paths if rel.startswith("ws/plugins/")])
            self.assertFalse((stage / "ws" / "plugins").exists())
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def test_09_host_only_bookkeeping_files_never_enter_the_package(self) -> None:
        # 真机取证踩出来的坑：data/current_workspace 曾被当普通数据文件扫进包，
        # 而恢复校验又拦住宿主级文件——两头不一致会让整包判废，一份都恢复不了。
        for name in ("current_workspace", "workspaces.toml", "deletion_audit.toml", ".local_token"):
            (self.ws_dir / name).write_text("host", encoding="utf-8")
        stage, manifest = self._manifest()
        try:
            paths = {item["path"] for item in manifest["files"]}
            for name in backup.HOST_ONLY_FILES:
                self.assertNotIn(name, paths, f"{name} 是宿主级账本/凭据，不该进包")
            self.assertIn(f"banks/{PROVIDER}.db", paths, "跳过宿主文件后业务数据仍要照常进包")
            self.assertIn("ws/plugin_state.toml", paths)
        finally:
            shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
