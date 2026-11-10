"""题库引擎 v2 契约测试：35 表结构、全量种子、自动建库与无 JSON 的 DAO。

守的底线：
1. 自动建库后计数与沙盒验收库一致，integrity / foreign_key 双绿；
2. 按考向、按知识点查题只走「单驱动表 + 分片回表」，能完整装配整题；
3. 新代码无 ``import json``，单文件不超过 500 行。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_engine_v2``
"""

from __future__ import annotations

import re
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.bank_engine import builder, service
from app.bank_engine import paths as engine_paths
from app.bank_engine.seeding import EXPECTED_COUNTS
from app.bank_engine.writer import EntryRejected

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"
ENGINE_DIR = ROOT / "app" / "bank_engine"
BUILD_SCRIPT = ROOT / "scripts" / "build_bank_engine.py"
SAMPLE_QUESTION = "q_test0001"
SAMPLE_DIRECTION = 1
SAMPLE_POINT = 9001


def _insert_sample(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO questions (id, stem, subject_id, question_type_id, difficulty_id, quality_id) "
        "VALUES (?, ?, 2, 1, 2, 2)",
        (SAMPLE_QUESTION, "已知集合 $A=\\{1,2\\}$，判断 1 与 A 的关系。"),
    )
    conn.executemany(
        "INSERT INTO question_options (question_id, option_label, content, is_correct) "
        "VALUES (?, ?, ?, ?)",
        [
            (SAMPLE_QUESTION, "A", "$1\\in A$", 1),
            (SAMPLE_QUESTION, "B", "$1\\notin A$", 0),
        ],
    )
    conn.execute(
        "INSERT INTO question_answers (question_id, answer_content, is_primary) VALUES (?, ?, 1)",
        (SAMPLE_QUESTION, "A"),
    )
    conn.execute(
        "INSERT INTO question_solutions (question_id, content, is_primary) VALUES (?, ?, 1)",
        (SAMPLE_QUESTION, "由集合列举法直接读出。"),
    )
    conn.execute(
        "INSERT INTO question_remarks (question_id, remark) VALUES (?, ?)",
        (SAMPLE_QUESTION, "概念辨析题"),
    )
    conn.execute(
        "INSERT INTO question_supplements (question_id, namespace, field_key, field_value) "
        "VALUES (?, '思路', '主线', '先看元素是否在列举集合中')",
        (SAMPLE_QUESTION,),
    )
    conn.execute(
        "INSERT INTO exams "
        "(id, code, year, month, subject_id, grade_id, exam_type_id, exam_subject) "
        "VALUES (9001, 'exm_test0001', 2026, 9, 2, 12, 16, '沙盒联调卷')"
    )
    conn.executemany(
        "INSERT INTO exam_school_map (exam_id, school_id) VALUES (9001, ?)",
        [(1,), (2,)],
    )
    conn.execute(
        "INSERT INTO question_exams (question_id, exam_id, question_no, score) "
        "VALUES (?, 9001, '1', 5.0)",
        (SAMPLE_QUESTION,),
    )
    conn.execute(
        "INSERT INTO question_exam_map (question_id, exam_direction_id) VALUES (?, ?)",
        (SAMPLE_QUESTION, SAMPLE_DIRECTION),
    )
    conn.execute(
        "INSERT INTO question_knowledge_map (question_id, knowledge_point_id) VALUES (?, ?)",
        (SAMPLE_QUESTION, SAMPLE_POINT),
    )
    conn.commit()


class EngineBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="engine-v2-"))
        cls.db_path = cls.tmp / "nested" / "engine.v2.db"
        cls.report = builder.build_engine(db_path=cls.db_path, schema=SCHEMA)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def test_build_reports_all_expected_counts(self) -> None:
        self.assertTrue(self.report.created)
        self.assertEqual(self.report.counts, EXPECTED_COUNTS)
        self.assertEqual(self.report.counts["dim_knowledge_points"], 11388)
        self.assertEqual(self.report.counts["dim_textbook_chapters"], 3519)
        self.assertEqual(self.report.counts["dim_schools"], 347)
        self.assertEqual(self.report.counts["dim_regions"], 367)
        self.assertEqual(self.report.counts["dim_exam_directions"], 567)
        self.assertEqual(self.report.counts["knowledge_exam_map"], 200)
        self.assertEqual(self.report.counts["chapter_knowledge_map"], 74)
        self.assertEqual(self.report.counts["dict_exam_types"], 16)
        self.assertEqual(self.report.counts["exams"], 4)
        self.assertEqual(self.report.counts["exam_school_map"], 9)

    def test_regions_are_two_levels_and_schools_are_linked(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            levels = dict(
                conn.execute(
                    "SELECT level, COUNT(*) FROM dim_regions GROUP BY level"
                ).fetchall()
            )
            self.assertEqual(levels, {1: 34, 2: 333})
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM dim_schools WHERE region_id IS NULL"
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM dim_schools s JOIN dim_regions r "
                    "ON r.id = s.region_id WHERE s.region = '黑龙江哈尔滨' "
                    "AND r.name = '哈尔滨' AND r.level = 2"
                ).fetchone()[0],
                22,
            )
        finally:
            conn.close()

    def test_existing_database_is_reused(self) -> None:
        again = builder.build_engine(db_path=self.db_path, schema=SCHEMA)
        self.assertFalse(again.created)
        self.assertEqual(again.counts, EXPECTED_COUNTS)

    def test_status_reports_integrity_and_foreign_keys(self) -> None:
        report = service.status(self.db_path)
        self.assertEqual(report.schema_version, engine_paths.SCHEMA_VERSION)
        self.assertEqual(report.integrity, "ok")
        self.assertEqual(report.foreign_key_violations, 0)
        self.assertGreaterEqual(report.table_count, 35)

    def test_missing_database_is_built_on_demand(self) -> None:
        fresh = self.tmp / "on-demand.v2.db"
        report = service.status(fresh)
        self.assertTrue(fresh.is_file())
        self.assertEqual(report.schema_version, engine_paths.SCHEMA_VERSION)
        self.assertEqual(report.counts["dim_knowledge_points"], 11388)


class EngineDaoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="engine-dao-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)
        conn = sqlite3.connect(cls.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            _insert_sample(conn)
        finally:
            conn.close()

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def test_exam_directions_list_and_count(self) -> None:
        items, total = service.exam_directions(subject_id=2, limit=5, db_path=self.db_path)
        self.assertEqual(total, 503)
        self.assertEqual(len(items), 5)
        self.assertTrue(all(item.subject_id == 2 for item in items))

    def test_questions_by_exam_direction(self) -> None:
        page = service.questions_of_direction(
            SAMPLE_DIRECTION, limit=10, db_path=self.db_path
        )
        self.assertEqual(page.total, 1)
        summary = page.items[0]
        self.assertEqual(summary.id, SAMPLE_QUESTION)
        self.assertEqual(summary.question_type, "choice")
        self.assertEqual(summary.difficulty, "L2")
        self.assertEqual(summary.quality, "NORMAL")

    def test_questions_by_knowledge_point(self) -> None:
        page = service.questions_of_point(SAMPLE_POINT, db_path=self.db_path)
        self.assertEqual(page.total, 1)
        self.assertEqual(page.items[0].id, SAMPLE_QUESTION)

    def test_question_assembly_is_complete(self) -> None:
        record = service.question(SAMPLE_QUESTION, db_path=self.db_path)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(len(record.options), 2)
        self.assertTrue(record.options[0].is_correct)
        self.assertEqual(record.answers[0].content, "A")
        self.assertEqual(record.solutions[0].content, "由集合列举法直接读出。")
        self.assertEqual(record.remarks, ("概念辨析题",))
        self.assertEqual(record.supplements[0].namespace, "思路")
        self.assertEqual(record.exams[0].exam_subject, "沙盒联调卷")
        self.assertEqual(record.exams[0].exam_type, "自编题")
        self.assertEqual(record.exams[0].school_ids, (1, 2))
        self.assertEqual(record.exams[0].school_names[0], "黑山县第二高级中学")
        self.assertEqual(record.exams[0].score, 5.0)
        self.assertEqual(record.exam_directions[0].id, SAMPLE_DIRECTION)
        self.assertEqual(record.knowledge_points[0].id, SAMPLE_POINT)

    def test_missing_question_returns_none(self) -> None:
        self.assertIsNone(service.question("q_missing", db_path=self.db_path))

    def test_pagination_bounds_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            service.questions_of_direction(SAMPLE_DIRECTION, limit=0, db_path=self.db_path)
        with self.assertRaises(ValueError):
            service.questions_of_point(SAMPLE_POINT, offset=-1, db_path=self.db_path)

    def test_knowledge_tree_keeps_hierarchy(self) -> None:
        roots = service.knowledge_tree(2, db_path=self.db_path)
        self.assertEqual(len(roots), 268)
        self.assertEqual(roots[0].point.name, "函数")
        self.assertGreater(len(roots[0].children), 0)

    def test_required1_bridge_walks_direction_to_chapter(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            direction = conn.execute(
                "SELECT id, name FROM dim_exam_directions WHERE code = 'ED_MATH_H_001'"
            ).fetchone()
            self.assertIsNotNone(direction)
            point_ids = tuple(
                int(row[0]) for row in conn.execute(
                    "SELECT knowledge_point_id FROM knowledge_exam_map "
                    "WHERE exam_direction_id = ?", (direction["id"],)
                )
            )
            self.assertEqual(len(point_ids), 1)
            point = conn.execute(
                "SELECT id, name, code FROM dim_knowledge_points WHERE id = ?",
                (point_ids[0],),
            ).fetchone()
            self.assertEqual((point["name"], point["code"]), ("集合的含义", "KP_MATH_H_001"))
            chapter_ids = tuple(
                int(row[0]) for row in conn.execute(
                    "SELECT chapter_id FROM chapter_knowledge_map "
                    "WHERE knowledge_point_id = ?", (point["id"],)
                )
            )
            self.assertEqual(len(chapter_ids), 1)
            chapter = conn.execute(
                "SELECT name, textbook_id FROM dim_textbook_chapters WHERE id = ?",
                (chapter_ids[0],),
            ).fetchone()
            self.assertEqual(chapter["textbook_id"], 9101)
            self.assertIn("集合的概念", chapter["name"])

    def test_required1_knowledge_names_carry_no_chapter_titles(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            names = [
                str(row[0]) for row in conn.execute(
                    "SELECT name FROM dim_knowledge_points WHERE code LIKE 'KP_MATH_H_%'"
                )
            ]
        self.assertEqual(len(names), 70)
        self.assertEqual(
            [name for name in names if re.match(r"^(第[一二三四五六七八九十]+[章节]|\d)", name)],
            [],
        )

    def test_textbooks_and_chapters(self) -> None:
        books = service.textbooks(subject_id=2, grade_id=10, db_path=self.db_path)
        self.assertTrue(books)
        chapters = service.chapters(books[0].id, db_path=self.db_path)
        self.assertTrue(chapters)
        self.assertTrue(all(chapter.parent_id is None for chapter in chapters))


class EngineEntryWriteTest(unittest.TestCase):
    """录题落库：表单只交名字/编码，主表与从表分步写入，绝不整包塞进 JSON 列。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="engine-entry-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def _document(self) -> dict:
        return {
            "type": "choice",
            "stem": "已知集合 $A=\\{1,2\\}$，判断 $1$ 与 $A$ 的关系。",
            "difficulty": "L2",
            "quality": "NORMAL",
            "subject": "数学",
            "grade": "高一",
            "options": [
                {"key": "A", "content": "$1\\in A$"},
                {"key": "B", "content": "$1\\notin A$"},
            ],
            "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
            "solution": "由列举法直接读出元素属于集合。",
            "exam_direction_ids": ["tp_kx9b03d9eb"],
            "knowledge_point_ids": ["math_function"],
            "tags": ["集合"],
            "source": {
                "paper_title": "沙盒联调卷",
                "exam_type": "自编题",
                "year": 2026,
                "question_no": "1",
                "score": 5,
                "school_ids": [258, 19],
            },
        }

    def test_create_question_splits_into_child_tables(self) -> None:
        created = service.create_question(self._document(), db_path=self.db_path)
        self.assertTrue(created.created)
        self.assertRegex(created.id, r"^q_[0-9a-f]{12}$")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            question = conn.execute(
                "SELECT subject_id, question_type_id, difficulty_id, quality_id "
                "FROM questions WHERE id = ?", (created.id,)
            ).fetchone()
            self.assertIsNotNone(question)
            self.assertEqual(question["subject_id"], 2)
            self.assertEqual(question["difficulty_id"], 2)

            options = conn.execute(
                "SELECT option_label, is_correct FROM question_options "
                "WHERE question_id = ? ORDER BY option_label", (created.id,)
            ).fetchall()
            self.assertEqual([(row["option_label"], row["is_correct"]) for row in options],
                             [("A", 1), ("B", 0)])

            answer = conn.execute(
                "SELECT answer_content FROM question_answers WHERE question_id = ?",
                (created.id,)
            ).fetchone()
            self.assertEqual(answer["answer_content"], "A")

            solution = conn.execute(
                "SELECT content FROM question_solutions WHERE question_id = ?",
                (created.id,)
            ).fetchone()
            self.assertIn("列举法", solution["content"])

            direction = conn.execute(
                "SELECT e.code FROM question_exam_map m "
                "JOIN dim_exam_directions e ON e.id = m.exam_direction_id "
                "WHERE m.question_id = ?", (created.id,)
            ).fetchone()
            self.assertEqual(direction["code"], "tp_kx9b03d9eb")

            point = conn.execute(
                "SELECT k.code FROM question_knowledge_map m "
                "JOIN dim_knowledge_points k ON k.id = m.knowledge_point_id "
                "WHERE m.question_id = ?", (created.id,)
            ).fetchone()
            self.assertEqual(point["code"], "math_function")

            exam = conn.execute(
                "SELECT e.exam_subject, e.year, m.question_no, m.score FROM question_exams m "
                "JOIN exams e ON e.id = m.exam_id WHERE m.question_id = ?",
                (created.id,)
            ).fetchone()
            self.assertEqual(exam["exam_subject"], "沙盒联调卷")
            self.assertEqual(exam["year"], 2026)
            self.assertEqual(exam["score"], 5.0)

            schools = conn.execute(
                "SELECT school_id FROM exam_school_map WHERE exam_id = "
                "(SELECT exam_id FROM question_exams WHERE question_id = ?) "
                "ORDER BY school_id",
                (created.id,)
            ).fetchall()
            self.assertEqual([row["school_id"] for row in schools], [19, 258])

            tag = conn.execute(
                "SELECT namespace, field_value FROM question_supplements "
                "WHERE question_id = ?", (created.id,)
            ).fetchone()
            self.assertEqual((tag["namespace"], tag["field_value"]), ("标签", "集合"))

    def test_unknown_dimension_code_is_rejected_before_any_write(self) -> None:
        document = self._document()
        document["exam_direction_ids"] = ["tp_kxffffffff"]
        with sqlite3.connect(self.db_path) as conn:
            before = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        with self.assertRaises(EntryRejected):
            service.create_question(document, db_path=self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            after = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        self.assertEqual(before, after, "解析失败必须一题不落")


class EngineSourceHygieneTest(unittest.TestCase):
    def test_no_json_import_in_new_engine_code(self) -> None:
        pattern = re.compile(r"^\s*(?:import\s+json|from\s+json\s+import)", re.MULTILINE)
        offenders = [
            path.name
            for path in ENGINE_DIR.rglob("*.py")
            if pattern.search(path.read_text(encoding="utf-8"))
        ]
        if pattern.search(BUILD_SCRIPT.read_text(encoding="utf-8")):
            offenders.append(BUILD_SCRIPT.name)
        self.assertEqual(offenders, [])

    def test_no_json_files_in_engine_tree(self) -> None:
        self.assertEqual(list(ENGINE_DIR.rglob("*.json")), [])
        self.assertEqual(list((ROOT / "plugins" / "org.jiuzhang.bank-engine").rglob("*.json")), [])

    def test_engine_files_stay_under_500_lines(self) -> None:
        oversized = {
            path.relative_to(ROOT).as_posix(): len(path.read_text(encoding="utf-8").splitlines())
            for path in [*ENGINE_DIR.rglob("*.py"), BUILD_SCRIPT]
            if len(path.read_text(encoding="utf-8").splitlines()) > 500
        }
        self.assertEqual(oversized, {})

    def test_schema_is_the_36_table_contract(self) -> None:
        body = SCHEMA.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"CREATE TABLE", body)), 36)
        self.assertEqual(len(builder.BASE_TABLES), 36)
        self.assertEqual(engine_paths.SCHEMA_VERSION, 9)
        self.assertIn("dim_textbook_versions", body)
        self.assertNotIn("dim_sources", body)
        self.assertIn("tikz_code", body)
        self.assertNotIn("question_source_map", body)
        self.assertIn("exam_school_map", builder.BASE_TABLES)

    def test_dictionaries_carry_stage_instead_of_grade(self) -> None:
        body = SCHEMA.read_text(encoding="utf-8")

        def ddl(table: str) -> str:
            block = re.search(
                r"CREATE TABLE " + table + r" \((.*?)\n\);", body, re.DOTALL
            )
            self.assertIsNotNone(block, table)
            assert block is not None
            return block.group(1)

        for table in (
            "dim_knowledge_points",
            "dim_exam_directions",
            "dict_subject_thoughts",
            "dict_solution_methods",
            "dict_core_competencies",
        ):
            self.assertNotIn("grade_id", ddl(table), table)
        for table in ("dict_subject_thoughts", "dict_solution_methods", "dict_core_competencies"):
            self.assertIn("stage      TEXT", ddl(table), table)
            self.assertIn(f"ix_{table}_stage", body)


if __name__ == "__main__":
    unittest.main()
