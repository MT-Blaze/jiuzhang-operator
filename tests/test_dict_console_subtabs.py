"""数据字典控制台 · 二级标签契约：只读字典规格 + 前端静态装配。

钉住四件事：
1. 二级标签里出现的每张表都有 dao_console 规格，且返回真实 Dataclass 行；
2. 补齐的字典全部只读（fields_meta 无 editable 列），前端不出现增删入口；
3. subtabs.js / chapters.js / dict_console_subtabs.css 真被页面加载；
4. 分类面板只挂 DcSubTabs，不再把多张表纵向堆叠。

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

from app.bank_engine import builder, dao_console, service  # noqa: E402
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

READ_ONLY = {
    "dict_question_types": (QuestionType, 3),
    "dict_difficulties": (Difficulty, 5),
    "dict_question_qualities": (Quality, 3),
    "dim_textbook_versions": (TextbookVersion, 19),
    "dim_textbook_chapters": (Chapter, 3519),
    "dict_subject_thoughts": (SubjectThought, 22),
    "dict_solution_methods": (SolutionMethod, 34),
    "dict_core_competencies": (CoreCompetency, 47),
}


class ReadOnlyDictSpecTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="dict-subtabs-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def test_every_subtable_is_registered_and_seeded(self) -> None:
        for table, (model, expected) in READ_ONLY.items():
            self.assertIn(table, dao_console.SPECS)
            items, total = service.console_list(table, limit=200, db_path=self.db_path)
            self.assertEqual(total, expected, table)
            self.assertTrue(items, table)
            self.assertTrue(all(isinstance(item, model) for item in items), table)

    def test_read_only_specs_expose_no_editable_field(self) -> None:
        for table in READ_ONLY:
            fields = dao_console.fields_meta(dao_console.get_spec(table))
            self.assertTrue(fields)
            self.assertFalse(
                any(field["editable"] for field in fields), table
            )

    def test_keyword_search_works_on_read_only_table(self) -> None:
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


class SubTabsWiringTest(unittest.TestCase):
    def test_new_assets_exist_and_are_loaded(self) -> None:
        html = (ROOT / "static" / "dict_console.html").read_text(encoding="utf-8")
        for ref in (
            "/static/css/dict_console_subtabs.css",
            "/static/js/dict_console/subtabs.js",
            "/static/js/dict_console/chapters.js",
        ):
            self.assertIn(ref, html)
            self.assertTrue((ROOT / ref.lstrip("/")).is_file(), ref)

    def test_new_assets_stay_under_500_lines(self) -> None:
        for name in ("subtabs.js", "chapters.js"):
            path = CONSOLE_DIR / name
            self.assertLess(len(path.read_text(encoding="utf-8").splitlines()), 500, name)
        css = ROOT / "static" / "css" / "dict_console_subtabs.css"
        self.assertLess(len(css.read_text(encoding="utf-8").splitlines()), 500)

    def test_subtabs_js_never_uses_innerhtml_or_eval(self) -> None:
        for name in ("subtabs.js", "chapters.js"):
            text = (CONSOLE_DIR / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\.innerHTML\s*=", name)
            self.assertNotRegex(text, r"\beval\s*\(", name)

    def test_catalog_declares_required_subtabs(self) -> None:
        catalog = (CONSOLE_DIR / "catalog.js").read_text(encoding="utf-8")
        for label in (
            "学科", "年级", "题型", "难度", "题目质量", "考试类型",
            "教材版本", "学校", "教材章节", "行政区划",
            "知识点与考向", "学科思想", "解题方法", "核心素养",
        ):
            self.assertIn('label: "' + label + '"', catalog)
        self.assertIn('mode: "linkage"', catalog)
        self.assertIn('mode: "chapters"', catalog)

    def test_category_panel_uses_subtabs_only(self) -> None:
        panels = (CONSOLE_DIR / "panels.js").read_text(encoding="utf-8")
        self.assertIn("DcSubTabs.mount", panels)
        self.assertNotIn("待交付字典", panels)
        self.assertIn("readOnly", panels)

    def test_state_memory_wired_in_main_and_subtabs(self) -> None:
        main = (CONSOLE_DIR / "main.js").read_text(encoding="utf-8")
        self.assertIn("jzo.dictConsole.subtabs.v1", main)
        self.assertIn("replaceState", main)
        subtabs = (CONSOLE_DIR / "subtabs.js").read_text(encoding="utf-8")
        self.assertIn('pane.style.display = on ? "block" : "none"', subtabs)
        table = (CONSOLE_DIR / "table.js").read_text(encoding="utf-8")
        self.assertIn("readOnly", table)
        self.assertNotRegex(table, r"\.innerHTML\s*=")


if __name__ == "__main__":
    unittest.main()
