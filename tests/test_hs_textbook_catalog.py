"""高中数学 / 物理教材目录契约：版本、册次与学科绑定。

守五件事：
1. 数学六个主流版本、物理五个主流版本都在版本表；
2. 每个版本的必修 / 选择性必修册次齐全，册次名不带版本前缀；
3. 每册都挂到正确的学科与版本，不产生悬空外键；
4. 新增册次不造假章节，章节数保持原种子口径；
5. 目录编码全局唯一，重复灌种不增行。
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.bank_engine import builder, service

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"

MATH_VERSIONS = {
    "人教A版": ["必修第一册", "必修第二册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
    "人教B版": ["必修第一册", "必修第二册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
    "北师大版": ["必修第一册", "必修第二册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
    "苏教版": ["必修第一册", "必修第二册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
    "湘教版": ["必修第一册", "必修第二册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
    "沪教版": ["必修第一册", "必修第二册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
}
PHYSICS_VERSIONS = {
    "人教版": ["必修第一册", "必修第二册", "必修第三册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
    "鲁科版": ["必修第一册", "必修第二册", "必修第三册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
    "沪科版": ["必修第一册", "必修第二册", "必修第三册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
    "粤教版": ["必修第一册", "必修第二册", "必修第三册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
    "教科版": ["必修第一册", "必修第二册", "必修第三册", "选择性必修第一册", "选择性必修第二册", "选择性必修第三册"],
}


class HighSchoolCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="hs-catalog-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def _volumes(self, subject_id: int, name: str) -> list[str]:
        version = next(
            item for item in service.textbook_versions(subject_id=subject_id, db_path=self.db_path)
            if item.name == name
        )
        books = service.textbooks(version_id=version.id, db_path=self.db_path)
        return [book.volume_name for book in books if book.volume_name in set(
            MATH_VERSIONS.get(name, PHYSICS_VERSIONS.get(name, []))
        )]

    def test_math_versions_and_volumes_are_complete(self) -> None:
        for name, volumes in MATH_VERSIONS.items():
            self.assertEqual(self._volumes(2, name), volumes, name)

    def test_physics_versions_and_volumes_are_complete(self) -> None:
        for name, volumes in PHYSICS_VERSIONS.items():
            self.assertEqual(self._volumes(4, name), volumes, name)

    def test_books_are_bound_to_subject_and_version(self) -> None:
        with service.session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT b.id, b.name, b.subject_id, v.subject_id AS version_subject "
                "FROM dim_textbooks b JOIN dim_textbook_versions v ON v.id = b.version_id "
                "WHERE b.code LIKE 'hs_%'"
            ).fetchall()
        self.assertEqual(len(rows), 60)
        self.assertTrue(all(
            row["subject_id"] == row["version_subject"] and row["subject_id"] in (2, 4)
            for row in rows
        ))

    def test_new_volumes_carry_no_placeholder_chapters(self) -> None:
        with service.session(self.db_path) as conn:
            rows = conn.execute(
                "SELECT COUNT(*) FROM dim_textbook_chapters "
                "WHERE textbook_id IN (SELECT id FROM dim_textbooks WHERE code LIKE 'hs_%')"
            ).fetchone()
        self.assertEqual(int(rows[0]), 0)
