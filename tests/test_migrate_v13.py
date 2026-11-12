"""v12 → v13 迁移契约：考试类型字典「模考」更名为「模拟考」。

判定三件事：
1. 新库（v13）字典里只有「模拟考」，id 与 code 不动；
2. 回滚到 v12 时名字退回「模考」，再升级又变回「模拟考」；
3. 升级幂等，重复执行不报错、不多改行。

运行：``.venv/Scripts/python.exe -m unittest tests.test_migrate_v13 -v``
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.bank_engine import builder, migrate_v13

SCHEMA = Path(__file__).resolve().parents[1] / (
    "plugins/org.jiuzhang.bank-engine/bank/schema.sql"
)


class MigrateV13Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="migrate-v13-"))
        self.db_path = self.tmp / "engine.db"
        builder.build_engine(db_path=self.db_path, schema=SCHEMA)
        self.conn = sqlite3.connect(self.db_path)
        self.addCleanup(self._cleanup)

    def _cleanup(self) -> None:
        self.conn.close()
        shutil.rmtree(self.tmp, True)

    def _version(self) -> int:
        return int(self.conn.execute("PRAGMA user_version").fetchone()[0])

    def _mock_row(self) -> tuple:
        return tuple(self.conn.execute(
            "SELECT id, name, code FROM dict_exam_types WHERE code = 'mock'"
        ).fetchone())

    def test_fresh_build_uses_new_name(self) -> None:
        self.assertEqual(self._version(), 13)
        self.assertEqual(self._mock_row(), (3, "模拟考", "mock"))
        names = [
            row[0]
            for row in self.conn.execute("SELECT name FROM dict_exam_types ORDER BY id")
        ]
        self.assertNotIn("模考", names)

    def test_rollback_then_upgrade_roundtrip(self) -> None:
        migrate_v13.rollback(self.conn)
        self.assertEqual(self._version(), 12)
        self.assertEqual(self._mock_row(), (3, "模考", "mock"))

        migrate_v13.upgrade(self.conn)
        self.assertEqual(self._version(), 13)
        self.assertEqual(self._mock_row(), (3, "模拟考", "mock"))

        # 幂等：升级跑第二遍不报错，行不变。
        migrate_v13.upgrade(self.conn)
        self.assertEqual(self._version(), 13)
        self.assertEqual(self._mock_row(), (3, "模拟考", "mock"))


if __name__ == "__main__":
    unittest.main()
