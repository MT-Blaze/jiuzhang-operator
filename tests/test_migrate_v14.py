"""v13 → v14 迁移契约：考试层级 / 考试主体落地与两条历史脏数据定点清洗。

判定四件事：
1. 升级后 user_version=14，``exams`` 三外键齐全，``PRAGMA foreign_key_check`` 为空；
2. id=1 的「数学」是学科误填，org 清空；
3. id=4 的「哈尔滨」按跨地市联考落黑龙江、层级 cross_city，学校关系保留；
4. 重复升级幂等，不重复建字典行。

运行：``.venv/Scripts/python.exe -m unittest tests.test_migrate_v14 -v``
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.bank_engine import builder, migrate_v14

SCHEMA = Path(__file__).resolve().parents[1] / (
    "plugins/org.jiuzhang.bank-engine/bank/schema.sql"
)


class MigrateV14Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="migrate-v14-"))
        self.db_path = self.tmp / "engine.db"
        builder.build_engine(db_path=self.db_path, schema=SCHEMA)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        migrate_v14.rollback(self.conn)
        self.addCleanup(self._cleanup)
        self._seed_dirty_rows()

    def _cleanup(self) -> None:
        self.conn.close()
        shutil.rmtree(self.tmp, True)

    def _seed_dirty_rows(self) -> None:
        # 出厂种子带示例卷 id=4；这里清空后按历史脏数据重放。
        self.conn.execute("DELETE FROM question_exams")
        self.conn.execute("DELETE FROM exam_school_map")
        self.conn.execute("DELETE FROM exams")
        self.conn.execute("DELETE FROM dict_exam_orgs")
        rows = (
            (1, 2024, "数学", None, 12, 2),
            (4, 2025, "哈尔滨", 1, 12, 2),
        )
        self.conn.executemany(
            "INSERT INTO exams (id, year, exam_org_name, school_id, month, "
            "exam_type_id, mock_round, grade_id, semester, subject_id) "
            "VALUES (?, ?, ?, ?, NULL, 3, NULL, ?, NULL, ?)",
            rows,
        )
        self.conn.commit()

    def _exam(self, exam_id: int) -> sqlite3.Row:
        return self.conn.execute(
            "SELECT e.region_id, e.exam_org_id, e.exam_level_id, o.name AS org_name, "
            "o.org_type, l.code AS level_code, r.code AS region_code "
            "FROM exams e LEFT JOIN dict_exam_orgs o ON o.id = e.exam_org_id "
            "LEFT JOIN dict_exam_levels l ON l.id = e.exam_level_id "
            "LEFT JOIN dim_regions r ON r.id = e.region_id WHERE e.id = ?",
            (exam_id,),
        ).fetchone()

    def test_upgrade_lands_v14_with_clean_foreign_keys(self) -> None:
        migrate_v14.upgrade(self.conn)
        self.assertEqual(
            int(self.conn.execute("PRAGMA user_version").fetchone()[0]), 14
        )
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        columns = {
            row["name"] for row in self.conn.execute("PRAGMA table_info(exams)")
        }
        self.assertTrue({"region_id", "exam_org_id", "exam_level_id"} <= columns)
        self.assertNotIn("exam_org_name", columns)
        self.assertNotIn("school_id", columns)

    def test_subject_name_dirty_row_clears_org(self) -> None:
        migrate_v14.upgrade(self.conn)
        exam = self._exam(1)
        self.assertIsNone(exam["exam_org_id"])
        self.assertIsNone(exam["org_name"])

    def test_harbin_dirty_row_maps_to_heilongjiang_cross_city(self) -> None:
        migrate_v14.upgrade(self.conn)
        exam = self._exam(4)
        self.assertEqual(exam["region_code"], "230000")
        self.assertEqual(exam["level_code"], "cross_city")
        self.assertEqual(exam["org_name"], "哈尔滨")
        link = self.conn.execute(
            "SELECT school_id FROM exam_school_map WHERE exam_id = 4"
        ).fetchone()
        self.assertEqual(int(link["school_id"]), 1)

    def test_legacy_exam_type_names_are_realigned(self) -> None:
        self.conn.execute(
            "UPDATE dict_exam_types SET name = '结业考试' WHERE code = 'academic_proficiency'"
        )
        self.conn.execute(
            "UPDATE dict_exam_types SET name = '小考' WHERE code = 'weekly_test'"
        )
        self.conn.commit()
        migrate_v14.upgrade(self.conn)
        names = dict(
            self.conn.execute("SELECT code, name FROM dict_exam_types")
        )
        self.assertEqual(names["academic_proficiency"], "学业水平")
        self.assertEqual(names["weekly_test"], "周测")

    def test_sample_org_is_seeded_for_cross_province_exams(self) -> None:
        migrate_v14.upgrade(self.conn)
        row = self.conn.execute(
            "SELECT org_type FROM dict_exam_orgs WHERE name = 'T8联盟'"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["org_type"], "联考联盟")

    def test_upgrade_is_idempotent(self) -> None:
        migrate_v14.upgrade(self.conn)
        migrate_v14.upgrade(self.conn)
        self.assertEqual(
            int(self.conn.execute("PRAGMA user_version").fetchone()[0]), 14
        )
        self.assertEqual(
            int(
                self.conn.execute(
                    "SELECT COUNT(*) FROM dict_exam_levels"
                ).fetchone()[0]
            ),
            7,
        )
        self.assertEqual(
            int(
                self.conn.execute(
                    "SELECT COUNT(*) FROM dict_exam_orgs WHERE name = '哈尔滨'"
                ).fetchone()[0]
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
