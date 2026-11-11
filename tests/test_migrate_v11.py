"""v10 → v11 迁移契约：教研字典改同学科联合唯一，脏名称洗回裸名。

运行：``.venv/Scripts/python.exe -m unittest tests.test_migrate_v11 -v``
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.bank_engine import builder, migrate_v11

SCHEMA = Path(__file__).resolve().parents[1] / (
    "plugins/org.jiuzhang.bank-engine/bank/schema.sql"
)


class MigrateV11Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="migrate-v11-"))
        self.db_path = self.tmp / "engine.db"
        builder.build_engine(db_path=self.db_path, schema=SCHEMA)
        self.conn = sqlite3.connect(self.db_path)
        self.addCleanup(self._cleanup)

    def _cleanup(self) -> None:
        self.conn.close()
        shutil.rmtree(self.tmp, True)

    def _collapse_to_v11_rows(self) -> None:
        """v11 的唯一口径容不下逐学段同名行：先收成每学科每名一行，模拟真实 v11 库。"""
        for table in ("dict_subject_thoughts", "dict_solution_methods",
                      "dict_core_competencies"):
            self.conn.execute(
                "DELETE FROM " + table + " WHERE id NOT IN "
                "(SELECT MIN(id) FROM " + table + " GROUP BY subject_id, name)"
            )
        self.conn.commit()

    def test_roundtrip_relaxes_unique_and_cleans_names(self) -> None:
        self._collapse_to_v11_rows()
        migrate_v11.rollback(self.conn)
        self.assertEqual(self.conn.execute("PRAGMA user_version").fetchone()[0], 10)
        legacy = self.conn.execute(
            "SELECT name FROM dict_core_competencies "
            "WHERE subject_id = 6 AND name LIKE '%（生物）'"
        ).fetchall()
        self.assertTrue(legacy, "回滚后跨学科重名应重新带上学科括注")
        self.conn.execute(
            "UPDATE dict_solution_methods SET stage = '初中' "
            "WHERE code = 'math_completing_square'"
        )
        self.conn.commit()

        migrate_v11.upgrade(self.conn)

        self.assertEqual(self.conn.execute("PRAGMA user_version").fetchone()[0], 11)
        self.assertEqual(
            self.conn.execute("PRAGMA foreign_key_check").fetchall(), []
        )
        dirty = self.conn.execute(
            "SELECT COUNT(*) FROM dict_core_competencies "
            "WHERE name LIKE '%（生物）' OR name LIKE '%（科学）' OR name LIKE '%（美术）'"
        ).fetchone()[0]
        self.assertEqual(dirty, 0)
        method = self.conn.execute(
            "SELECT stage FROM dict_solution_methods WHERE code = 'math_completing_square'"
        ).fetchone()
        self.assertEqual(method[0], "全学段")

        self.conn.execute(
            "INSERT INTO dict_core_competencies "
            "(name, code, sort_order, subject_id, stage) "
            "VALUES ('科学思维', 'zz_core_dup_ok', 99, 1, '全学段')"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO dict_core_competencies "
                "(name, code, sort_order, subject_id, stage) "
                "VALUES ('科学思维', 'zz_core_dup_bad', 99, 4, '全学段')"
            )
        self.conn.rollback()


if __name__ == "__main__":
    unittest.main()
