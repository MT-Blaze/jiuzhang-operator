"""军令 #17 第一步契约：当前工作区一致性快照与 manifest。

钉四件事：
1. 有 WAL 且连接仍开着时，快照仍可读、题目数与活库一致，且不把边车原样装包；
2. manifest 字段齐全（工作区、schema 版本、库标识、题目数、逐题哈希、
   图片哈希、文件清单、生成时间、待回填的 Zstd 包哈希）；
3. 逐题哈希能按快照库原样复算；
4. default 工作区不把其他工作区、宿主状态与凭据文件卷进来。

运行：``.venv/Scripts/python.exe -m unittest tests.test_backup_snapshot``
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core import backup
from app.core.config import settings

PROVIDER = "org.jiuzhang.core-bank"
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
        (self.ws_dir / "config.json").write_text('{"provider":"x"}', encoding="utf-8")
        (self.ws_dir / "backup.json").write_text('{"password":"secret"}', encoding="utf-8")
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
        with mock.patch.object(
            backup, "_select_bank_db", wraps=backup._select_bank_db
        ):
            return backup.snapshot_workspace(WS_ID)

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
            self.assertEqual("other", categories["config.json"])
            required = {item["path"]: item["required"] for item in manifest["files"]}
            self.assertTrue(required[f"banks/{PROVIDER}.db"])
            self.assertTrue(required["uploads/pic.png"])
            self.assertNotIn("backup.json", categories)
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
        (self.data / "plugin_state.json").write_text("{}", encoding="utf-8")
        (self.data / "workspaces.json").write_text("[]", encoding="utf-8")
        settings.workspace_id = None
        stage, manifest = backup.snapshot_workspace("default")
        try:
            paths = {item["path"] for item in manifest["files"]}
            self.assertFalse(any(path.startswith("workspaces/") for path in paths))
            self.assertNotIn("plugin_state.json", paths)
            self.assertNotIn("workspaces.json", paths)
        finally:
            import shutil

            shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
