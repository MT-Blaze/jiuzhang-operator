"""数据字典控制台 · 二级标签契约：八表全开放 + 前端静态装配。

钉住四件事：
1. 二级标签里出现的每张表都有 dao_console 规格，且返回真实 Dataclass 行；
2. 八张原先只读的字典全部开放新增 / 改名 / 删除，删除仍保留外键引用防呆；
3. subtabs.js / chapters.js / chapter_ops.js / dict_console_subtabs.css 真被页面加载；
4. 分类面板只挂 DcSubTabs，不再把多张表纵向堆叠，也不再出现只读角标。

运行：``.venv/Scripts/python.exe -m unittest tests.test_dict_console_subtabs``
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bank_engine import builder, dao_console, seeding, service  # noqa: E402
from app.bank_engine.models import (  # noqa: E402
    Chapter,
    CoreCompetency,
    Difficulty,
    Quality,
    QuestionType,
    SolutionMethod,
    SubjectThought,
    TextbookVersion,
)

SCHEMA = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"
CONSOLE_DIR = ROOT / "static" / "js" / "dict_console"

DICT_TABLES = {
    "dict_question_types": (QuestionType, 3),
    "dict_difficulties": (Difficulty, 5),
    "dict_question_qualities": (Quality, 3),
    "dim_textbook_versions": (
        TextbookVersion, seeding.EXPECTED_COUNTS["dim_textbook_versions"]
    ),
    "dim_textbook_chapters": (Chapter, 3519),
    "dict_subject_thoughts": (SubjectThought, 22),
    "dict_solution_methods": (SolutionMethod, 34),
    "dict_core_competencies": (CoreCompetency, 47),
}


class WritableDictSpecTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="dict-subtabs-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def test_every_subtable_is_registered_and_seeded(self) -> None:
        for table, (model, expected) in DICT_TABLES.items():
            self.assertIn(table, dao_console.SPECS)
            items, total = service.console_list(table, limit=200, db_path=self.db_path)
            self.assertEqual(total, expected, table)
            self.assertTrue(items, table)
            self.assertTrue(all(isinstance(item, model) for item in items), table)

    def test_all_eight_dicts_expose_editable_fields(self) -> None:
        for table in DICT_TABLES:
            fields = dao_console.fields_meta(dao_console.get_spec(table))
            self.assertTrue(fields)
            editable = [field["key"] for field in fields if field["editable"]]
            self.assertTrue(editable, table)
            self.assertIn("name", editable, table)
            self.assertIn("code", editable, table)

    def test_insert_update_delete_every_dict(self) -> None:
        with service.session(self.db_path) as conn:
            book_id = int(conn.execute("SELECT id FROM dim_textbooks LIMIT 1").fetchone()["id"])
        cases = {
            "dict_question_types": {"name": "验收题型", "code": "zz_t_type"},
            "dict_question_qualities": {"name": "验收质量", "code": "zz_t_quality"},
            "dim_textbook_versions": {
                "name": "验收版本", "code": "zz_t_version", "subject_id": 1
            },
            "dim_textbook_chapters": {
                "name": "验收章节", "code": "zz_t_chapter", "textbook_id": book_id
            },
            "dict_subject_thoughts": {
                "name": "验收思想", "code": "zz_t_thought", "subject_id": 1
            },
            "dict_solution_methods": {
                "name": "验收方法", "code": "zz_t_method", "subject_id": 1
            },
            "dict_core_competencies": {
                "name": "验收素养", "code": "zz_t_competency", "subject_id": 1
            },
        }
        for table, payload in cases.items():
            with self.subTest(table=table):
                row = service.console_insert(table, payload, db_path=self.db_path)
                self.addCleanup(self._drop, table, row.id)
                changed = service.console_update(
                    table, row.id, {"name": payload["name"] + "改"}, db_path=self.db_path
                )
                self.assertEqual(changed.name, payload["name"] + "改")
                service.console_delete(table, row.id, db_path=self.db_path)
                with self.assertRaises(dao_console.ConsoleLookupError):
                    service.console_row(table, row.id, db_path=self.db_path)

    def test_difficulty_update_keeps_domain_check(self) -> None:
        fields = dao_console.fields_meta(dao_console.get_spec("dict_difficulties"))
        self.assertIn("level", [field["key"] for field in fields if field["editable"]])
        changed = service.console_update(
            "dict_difficulties", 1, {"description": "验收说明"}, db_path=self.db_path
        )
        self.assertEqual(changed.description, "验收说明")
        with self.assertRaises(dao_console.ConflictError):
            service.console_insert(
                "dict_difficulties", {"name": "越界难度", "code": "zz_t_l6", "level": 6},
                db_path=self.db_path,
            )

    def test_delete_still_guards_references(self) -> None:
        items, _ = service.console_list("dim_textbook_versions", limit=1, db_path=self.db_path)
        with self.assertRaises(dao_console.ReferencedError) as ctx:
            service.console_delete("dim_textbook_versions", items[0].id, db_path=self.db_path)
        self.assertTrue(ctx.exception.hits)

    def test_keyword_search_works_on_dict_table(self) -> None:
        items, total = service.console_list(
            "dict_question_types", keyword="choice", db_path=self.db_path
        )
        self.assertEqual(total, 1)
        self.assertEqual(items[0].code, "choice")

    def test_global_subject_filter_on_versions(self) -> None:
        items, total = service.console_list(
            "dim_textbook_versions", filters={"subject_id": 1}, limit=200,
            db_path=self.db_path,
        )
        self.assertGreater(total, 0)
        self.assertTrue(all(item.subject_id == 1 for item in items))

    def test_chapter_pagination_is_stable(self) -> None:
        first, total = service.console_list(
            "dim_textbook_chapters", limit=50, offset=0, db_path=self.db_path
        )
        second, _ = service.console_list(
            "dim_textbook_chapters", limit=50, offset=50, db_path=self.db_path
        )
        self.assertEqual(len(first), 50)
        self.assertEqual(len(second), 50)
        self.assertNotEqual({row.id for row in first}, {row.id for row in second})
        self.assertGreater(total, 50)

    def test_textbook_volume_lifecycle(self) -> None:
        versions, _ = service.console_list(
            "dim_textbook_versions", filters={"subject_id": 1}, limit=200,
            db_path=self.db_path,
        )
        row = service.console_insert(
            "dim_textbooks",
            {
                "name": "验收册次", "code": "zz_t_volume", "sort_order": 99,
                "subject_id": 1, "version_id": versions[0].id, "volume_name": "验收上册",
            },
            db_path=self.db_path,
        )
        self.addCleanup(self._drop, "dim_textbooks", row.id)
        changed = service.console_update(
            "dim_textbooks", row.id, {"volume_name": "验收下册"}, db_path=self.db_path
        )
        self.assertEqual(changed.volume_name, "验收下册")
        service.console_delete("dim_textbooks", row.id, db_path=self.db_path)
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.console_row("dim_textbooks", row.id, db_path=self.db_path)

    def test_volume_with_chapters_cannot_be_deleted(self) -> None:
        with service.session(self.db_path) as conn:
            row = conn.execute(
                "SELECT textbook_id FROM dim_textbook_chapters "
                "WHERE textbook_id IS NOT NULL LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(row)
        with self.assertRaises(dao_console.ReferencedError) as ctx:
            service.console_delete(
                "dim_textbooks", int(row["textbook_id"]), db_path=self.db_path
            )
        self.assertIn("dim_textbook_chapters", {hit.table for hit in ctx.exception.hits})

    def _drop(self, table: str, row_id: int) -> None:
        try:
            service.console_delete(table, row_id, db_path=self.db_path)
        except (dao_console.ReferencedError, dao_console.ConsoleLookupError):
            pass


class SubTabsWiringTest(unittest.TestCase):
    def test_new_assets_exist_and_are_loaded(self) -> None:
        html = (ROOT / "static" / "dict_console.html").read_text(encoding="utf-8")
        for ref in (
            "/static/css/dict_console_subtabs.css",
            "/static/css/dict_console_entities.css",
            "/static/js/dict_console/subtabs.js",
            "/static/js/dict_console/chapter_ops.js",
            "/static/js/dict_console/entity_shared.js",
            "/static/js/dict_console/entity_schools.js",
            "/static/js/dict_console/textbook_stage_tree.js",
            "/static/js/dict_console/entity_textbooks.js",
        ):
            self.assertIn(ref, html)
            self.assertTrue((ROOT / ref.lstrip("/")).is_file(), ref)

    def test_new_assets_stay_under_500_lines(self) -> None:
        for name in (
            "subtabs.js", "chapters.js", "chapter_ops.js", "row_ops.js",
            "entity_shared.js", "entity_schools.js", "textbook_stage_tree.js",
            "entity_textbooks.js",
        ):
            path = CONSOLE_DIR / name
            self.assertLess(len(path.read_text(encoding="utf-8").splitlines()), 500, name)
        for css_name in ("dict_console_subtabs.css", "dict_console_entities.css"):
            css = ROOT / "static" / "css" / css_name
            self.assertLess(len(css.read_text(encoding="utf-8").splitlines()), 500, css_name)

    def test_subtabs_js_never_uses_innerhtml_or_eval(self) -> None:
        for name in (
            "subtabs.js", "chapters.js", "chapter_ops.js",
            "entity_shared.js", "entity_schools.js", "textbook_stage_tree.js",
            "entity_textbooks.js",
        ):
            text = (CONSOLE_DIR / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\.innerHTML\s*=", name)
            self.assertNotRegex(text, r"\beval\s*\(", name)

    def test_catalog_declares_required_subtabs(self) -> None:
        catalog = (CONSOLE_DIR / "catalog.js").read_text(encoding="utf-8")
        for label in (
            "学科", "年级", "题型", "难度", "题目质量", "考试类型",
            "行政区划与学校", "教材与章节",
            "知识点与考向", "学科思想", "解题方法", "核心素养",
        ):
            self.assertIn('label: "' + label + '"', catalog)
        self.assertIn('mode: "linkage"', catalog)
        self.assertIn('mode: "regions-schools"', catalog)
        self.assertIn('mode: "textbooks-chapters"', catalog)
        self.assertNotIn('mode: "chapters"', catalog)

    def test_category_panel_uses_subtabs_only(self) -> None:
        panels = (CONSOLE_DIR / "panels.js").read_text(encoding="utf-8")
        self.assertIn("DcSubTabs.mount", panels)
        self.assertIn("DcEntitySchools.mount", panels)
        self.assertIn("DcEntityTextbooks.mount", panels)
        self.assertNotIn("待交付字典", panels)
        self.assertNotIn("readOnly", panels)

    def test_no_readonly_badge_or_gate_left(self) -> None:
        table = (CONSOLE_DIR / "table.js").read_text(encoding="utf-8")
        self.assertNotIn("readOnly", table)
        self.assertNotIn("dc-table-readonly", table)
        self.assertIn("DcRowOps.addRow", table)
        self.assertIn("DcRowOps.deleteRow", table)
        css = (ROOT / "static" / "css" / "dict_console_subtabs.css").read_text(encoding="utf-8")
        self.assertNotIn("dc-table-readonly", css)
        catalog = (CONSOLE_DIR / "catalog.js").read_text(encoding="utf-8")
        self.assertNotIn("editable", catalog)

    def test_state_memory_wired_in_main_and_subtabs(self) -> None:
        main = (CONSOLE_DIR / "main.js").read_text(encoding="utf-8")
        self.assertIn("jzo.dictConsole.subtabs.v1", main)
        self.assertIn("replaceState", main)
        subtabs = (CONSOLE_DIR / "subtabs.js").read_text(encoding="utf-8")
        self.assertIn('pane.style.display = on ? "block" : "none"', subtabs)
        table = (CONSOLE_DIR / "table.js").read_text(encoding="utf-8")
        self.assertNotIn("readOnly", table)
        self.assertNotRegex(table, r"\.innerHTML\s*=")


if __name__ == "__main__":
    unittest.main()
