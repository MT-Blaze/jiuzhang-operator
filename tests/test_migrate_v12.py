"""v11 → v12 迁移契约：教研字典唯一键补上学段维度。

判定四件事：
1. v12 允许同学科同名不同学段并存（物理观念 初中 / 高中）；
2. 同学科同学段同名仍被唯一约束拦住；
3. 回滚到 v11 时为撞名行补「（学段）」后缀，行数与 id 不丢；
4. 再升级回 v12 时后缀洗掉，结构、外键与行数全部复原。

运行：``.venv/Scripts/python.exe -m unittest tests.test_migrate_v12 -v``
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.bank_engine import builder, migrate_v12, migrate_v13
from app.core.config import plugin_source_root

SCHEMA = (plugin_source_root() or (Path(__file__).resolve().parents[1] / "plugins")) / (
    "org.jiuzhang.bank-engine/bank/schema.sql"
)


class MigrateV12Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="migrate-v12-"))
        self.db_path = self.tmp / "engine.db"
        builder.build_engine(db_path=self.db_path, schema=SCHEMA)
        self.conn = sqlite3.connect(self.db_path)
        # 本文件只考 v11 ↔ v12：先把最新库降回 v12，断言才有意义。
        migrate_v13.rollback(self.conn)
        self.addCleanup(self._cleanup)

    def _cleanup(self) -> None:
        self.conn.close()
        shutil.rmtree(self.tmp, True)

    def _version(self) -> int:
        return int(self.conn.execute("PRAGMA user_version").fetchone()[0])

    def _counts(self) -> dict[str, int]:
        return {
            table: int(self.conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
            for table in migrate_v12.TABLES
        }

    def test_v12_allows_same_name_per_stage(self) -> None:
        self.assertEqual(self._version(), 12)
        stages = {
            row[0]
            for row in self.conn.execute(
                "SELECT stage FROM dict_core_competencies "
                "WHERE subject_id = 4 AND name = '物理观念' ORDER BY stage"
            )
        }
        self.assertEqual(stages, {"初中", "高中"})
        self.conn.execute(
            "INSERT INTO dict_core_competencies "
            "(name, code, sort_order, subject_id, stage) "
            "VALUES ('验收素养', 'zz_v12_stage_a', 99, 1, '小学')"
        )
        self.conn.execute(
            "INSERT INTO dict_core_competencies "
            "(name, code, sort_order, subject_id, stage) "
            "VALUES ('验收素养', 'zz_v12_stage_b', 99, 1, '初中')"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO dict_core_competencies "
                "(name, code, sort_order, subject_id, stage) "
                "VALUES ('验收素养', 'zz_v12_stage_c', 99, 1, '小学')"
            )
        self.conn.rollback()

    def test_rollback_then_upgrade_roundtrip(self) -> None:
        before = self._counts()
        migrate_v12.rollback(self.conn)

        self.assertEqual(self._version(), 11)
        self.assertEqual(self._counts(), before)
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        suffixed = self.conn.execute(
            "SELECT name, stage FROM dict_core_competencies "
            "WHERE subject_id = 4 AND name LIKE '物理观念%' ORDER BY stage"
        ).fetchall()
        self.assertEqual(
            suffixed, [("物理观念", "初中"), ("物理观念（高中）", "高中")]
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO dict_core_competencies "
                "(name, code, sort_order, subject_id, stage) "
                "VALUES ('物理观念', 'zz_v11_dup', 99, 4, '高中')"
            )
        self.conn.rollback()

        migrate_v12.upgrade(self.conn)

        self.assertEqual(self._version(), 12)
        self.assertEqual(self._counts(), before)
        dirty = self.conn.execute(
            "SELECT COUNT(*) FROM dict_core_competencies "
            "WHERE name LIKE '%（小学）' OR name LIKE '%（初中）' OR name LIKE '%（高中）'"
        ).fetchone()[0]
        self.assertEqual(dirty, 0)
        stages = [
            row[0]
            for row in self.conn.execute(
                "SELECT stage FROM dict_core_competencies "
                "WHERE subject_id = 4 AND name = '物理观念' ORDER BY stage"
            )
        ]
        self.assertEqual(stages, ["初中", "高中"])


if __name__ == "__main__":
    unittest.main()
