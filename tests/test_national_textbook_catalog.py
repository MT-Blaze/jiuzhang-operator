"""全国教材版本目录契约：版本全量、每版每学段有真实册次锚点、绝不造章节。

运行：``.venv/Scripts/python.exe -m unittest tests.test_national_textbook_catalog -v``
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bank_engine import builder, dao_dimensions, seeding  # noqa: E402
from app.bank_engine.seeds import national_catalog  # noqa: E402

SCHEMA = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"

NON_MAINSTREAM = {
    ("mathematics", "冀教版"),
    ("science", "大象版"),
    ("english", "湘少版"),
    ("physics", "沪粤版"),
    ("art", "赣美版"),
    ("chinese", "鲁人版"),
    ("information_technology", "桂科版"),
    ("labor", "东北师大版"),
}


class NationalCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="national-catalog-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        self.addCleanup(conn.close)
        return conn

    def test_specs_are_unique_and_well_formed(self) -> None:
        keys = [(national_catalog.SUBJECT_IDS[code], name) for code, name, *_ in national_catalog.SPECS]
        self.assertEqual(len(keys), len(set(keys)))
        for subject_code, name, publisher, slug, stages in national_catalog.SPECS:
            self.assertIn(subject_code, national_catalog.SUBJECT_IDS, name)
            self.assertTrue(publisher, name)
            self.assertTrue(slug, name)
            self.assertTrue(stages, name)
            self.assertTrue(set(stages) <= {"P", "J", "S"}, name)

    def test_versions_and_anchor_books_match_seed_counts(self) -> None:
        conn = self._conn()
        versions = int(conn.execute("SELECT COUNT(*) FROM dim_textbook_versions").fetchone()[0])
        books = int(conn.execute("SELECT COUNT(*) FROM dim_textbooks").fetchone()[0])
        self.assertEqual(versions, seeding.EXPECTED_COUNTS["dim_textbook_versions"])
        self.assertEqual(books, seeding.EXPECTED_COUNTS["dim_textbooks"])
        self.assertGreaterEqual(versions, 190)

    def test_every_spec_is_bound_to_each_declared_stage(self) -> None:
        conn = self._conn()
        codes = {name: code for code, name in national_catalog.STAGE_NAMES.items()}
        stages = {
            int(row["id"]): codes.get(str(row["stage"]), "")
            for row in conn.execute("SELECT id, stage FROM dict_grades")
        }
        versions = {
            (int(row["subject_id"]), str(row["name"])): int(row["id"])
            for row in conn.execute("SELECT id, subject_id, name FROM dim_textbook_versions")
        }
        covered: dict[int, set[str]] = {}
        for row in conn.execute("SELECT version_id, grade_id FROM dim_textbooks"):
            stage = stages.get(int(row["grade_id"]))
            if stage:
                covered.setdefault(int(row["version_id"]), set()).add(stage)
        labels = national_catalog.STAGE_NAMES
        for subject_code, name, _publisher, _slug, spec_stages in national_catalog.SPECS:
            version_id = versions.get((national_catalog.SUBJECT_IDS[subject_code], name))
            self.assertIsNotNone(version_id, f"{subject_code}/{name} 未落库")
            for code in spec_stages:
                self.assertIn(code, covered.get(version_id, set()),
                              f"{name} 缺 {labels[code]} 册次锚点")

    def test_non_mainstream_versions_exist(self) -> None:
        conn = self._conn()
        versions = {
            (int(row["subject_id"]), str(row["name"]))
            for row in conn.execute("SELECT subject_id, name FROM dim_textbook_versions")
        }
        for subject_code, name in NON_MAINSTREAM:
            self.assertIn((national_catalog.SUBJECT_IDS[subject_code], name), versions)

    def test_anchor_books_never_carry_chapters(self) -> None:
        conn = self._conn()
        total = int(conn.execute("SELECT COUNT(*) FROM dim_textbook_chapters").fetchone()[0])
        self.assertEqual(total, 3519)
        anchored = int(conn.execute(
            "SELECT COUNT(*) FROM dim_textbook_chapters WHERE textbook_id IN "
            "(SELECT id FROM dim_textbooks WHERE code LIKE 'nc_%')"
        ).fetchone()[0])
        self.assertEqual(anchored, 0)

    def test_book_subject_matches_version_subject(self) -> None:
        conn = self._conn()
        mismatched = int(conn.execute(
            "SELECT COUNT(*) FROM dim_textbooks b JOIN dim_textbook_versions v "
            "ON v.id = b.version_id WHERE b.subject_id <> v.subject_id"
        ).fetchone()[0])
        self.assertEqual(mismatched, 0)
        bad_codes = int(conn.execute(
            "SELECT COUNT(*) FROM dim_textbooks b JOIN dim_textbook_versions v "
            "ON v.id = b.version_id WHERE b.code LIKE 'nc_%' AND b.name NOT LIKE v.name || '%'"
        ).fetchone()[0])
        self.assertEqual(bad_codes, 0)

    def test_stage_filter_exposes_junior_physics_versions(self) -> None:
        conn = self._conn()
        names = {
            item.name for item in dao_dimensions.list_textbook_versions(
                conn, subject_id=4, stage="初中"
            )
        }
        for expected in ("沪科版", "沪粤版", "教科版", "苏科版", "北师大版"):
            self.assertIn(expected, names)

    def test_rebuild_plan_is_empty_after_seeding(self) -> None:
        conn = self._conn()
        existing = {
            (int(row["subject_id"]), str(row["name"])): int(row["id"])
            for row in conn.execute("SELECT id, name, subject_id FROM dim_textbook_versions")
        }
        codes = {name: code for code, name in national_catalog.STAGE_NAMES.items()}
        stages = {
            int(row["id"]): codes.get(str(row["stage"]), "")
            for row in conn.execute("SELECT id, stage FROM dict_grades")
        }
        covered: dict[int, set[str]] = {}
        for row in conn.execute(
            "SELECT version_id, grade_id FROM dim_textbooks WHERE version_id IS NOT NULL"
        ):
            stage = stages.get(int(row["grade_id"]))
            if stage:
                covered.setdefault(int(row["version_id"]), set()).add(stage)
        versions, books = national_catalog.build(existing, covered)
        self.assertEqual((len(versions), len(books)), (0, 0))


if __name__ == "__main__":
    unittest.main()
