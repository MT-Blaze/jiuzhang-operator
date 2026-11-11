"""数据字典控制台 · 阶段一契约：教材版本接口、/dict 路由与静态骨架红线。

钉住四件事：
1. 教材版本清单按学科 / 年级单表过滤，Dataclass 出口，行数与种子一致；
2. /dict 页面路由与 /api/bank/engine/textbooks 都注册进底座；
3. 控制台骨架引用的静态资源全部真实存在，新文件单文件不超 500 行；
4. 控制台 JS 不拼 innerHTML、目录里不落任何 .json 文件（绝对纯净红线）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_dict_console``
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bank_engine import builder, service  # noqa: E402
from app.bank_engine.models import Textbook  # noqa: E402
from app.core import manifests  # noqa: E402

SCHEMA = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"
CONSOLE_DIR = ROOT / "static" / "js" / "dict_console"
NEW_FILES = [
    ROOT / "static" / "dict_console.html",
    ROOT / "static" / "css" / "dict_console.css",
    *sorted(CONSOLE_DIR.glob("*.js")),
]


class TextbooksServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="dict-console-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def test_full_list_matches_seed_count(self) -> None:
        items = service.textbooks(db_path=self.db_path)
        self.assertEqual(len(items), 128)
        self.assertTrue(all(isinstance(item, Textbook) for item in items))

    def test_subject_filter_is_single_table(self) -> None:
        items = service.textbooks(subject_id=2, db_path=self.db_path)
        self.assertTrue(items)
        self.assertTrue(all(item.subject_id == 2 for item in items))
        self.assertLess(len(items), 128)

    def test_grade_filter_narrows_further(self) -> None:
        items = service.textbooks(subject_id=1, grade_id=10, db_path=self.db_path)
        self.assertTrue(items)
        self.assertTrue(all(item.subject_id == 1 and item.grade_id == 10 for item in items))


class TextbooksRouteTest(unittest.TestCase):
    def test_route_passes_filters_and_returns_plain_objects(self) -> None:
        from app.api import bank_engine

        canned = (Textbook(id=1, name="人教A版必修一", code="t1", sort_order=1,
                           publisher="人民教育出版社", subject_id=2, grade_id=10),)
        with mock.patch.object(bank_engine.service, "textbooks", return_value=canned) as call:
            body = bank_engine.engine_textbooks(subject_id=2, grade_id=10, version_id=None)
        call.assert_called_once_with(subject_id=2, grade_id=10, version_id=None)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["name"], "人教A版必修一")
        self.assertEqual(body["items"][0]["subject_id"], 2)

    def test_routes_registered_in_host(self) -> None:
        from app.main import create_app

        def walk(routes):
            for route in routes:
                if hasattr(route, "path"):
                    yield route.path
                original = getattr(route, "original_router", None)
                if original is not None:
                    yield from walk(original.routes)

        paths = set(walk(create_app().routes))
        self.assertIn("/dict", paths)
        self.assertIn("/api/bank/engine/textbooks", paths)


class ConsoleSkeletonTest(unittest.TestCase):
    def test_new_files_stay_under_500_lines(self) -> None:
        self.assertTrue(NEW_FILES)
        for path in NEW_FILES:
            lines = len(path.read_text(encoding="utf-8").splitlines())
            self.assertLess(lines, 500, f"{path.name} 超过 500 行红线：{lines}")

    def test_html_references_all_resolve(self) -> None:
        html = (ROOT / "static" / "dict_console.html").read_text(encoding="utf-8")
        refs = re.findall(r'(?:src|href)="(/static/[^"]+)"', html)
        self.assertTrue(refs)
        for ref in refs:
            # 引用带 ?v= 缓存版本号，落盘检查只认路径部分
            path = ref.split("?", 1)[0].split("#", 1)[0].lstrip("/")
            self.assertTrue((ROOT / path).is_file(), f"引用的资源不存在：{ref}")

    def test_console_js_never_uses_innerhtml(self) -> None:
        for path in CONSOLE_DIR.glob("*.js"):
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"\.innerHTML\s*=", path.name)

    def test_no_json_files_in_console_tree(self) -> None:
        self.assertEqual(list(CONSOLE_DIR.rglob("*.json")), [])
        self.assertFalse((ROOT / "static" / "dict_console.json").exists())

    def test_workspace_has_no_standalone_dict_entry(self) -> None:
        html = (ROOT / "static" / "workspace.html").read_text(encoding="utf-8")
        self.assertNotIn('href="/dict"', html)
        self.assertNotIn("ws-dict-entry", html)

    def test_workspace_rail_is_a_pure_container(self) -> None:
        """2026-11-11 架构纠偏：右栏归底座当容器，字典导航不许再写死在全局壳里。"""
        html = (ROOT / "static" / "workspace.html").read_text(encoding="utf-8")
        self.assertNotIn('id="wsDictNav"', html)
        self.assertNotIn("字典维护导航", html)
        self.assertNotIn("/static/js/ws_dict_nav.js", html)
        self.assertFalse((ROOT / "static" / "js" / "ws_dict_nav.js").exists())
        css = (ROOT / "static" / "css" / "workspace_canvas.css").read_text(encoding="utf-8")
        self.assertNotIn(".ws-dict-nav", css)

    def test_dashboard_plugin_owns_dict_navigation(self) -> None:
        """字典导航是数据看板插件自己的 sidebar.right 面板，只在看板页签激活时入住。"""
        manifest = manifests.load_manifest(ROOT / "plugins" / "org.jiuzhang.dashboard")
        self.assertIn("sidebar.right", manifest["slots"])
        plugin_dir = ROOT / "plugins" / "org.jiuzhang.dashboard" / "dist"
        source = ((plugin_dir / "plugin.js").read_text(encoding="utf-8")
                  + (plugin_dir / "rail.js").read_text(encoding="utf-8"))
        self.assertIn("字典分类", source)
        self.assertIn('call("dict.catalog")', source)
        self.assertIn('call("dict.open"', source)
        stage_dict = (ROOT / "static" / "js" / "stage_dict.js").read_text(encoding="utf-8")
        self.assertIn("DcCatalog", stage_dict)
        self.assertIn("/dict?embedded=1&cat=", stage_dict)

    def test_dashboard_rail_is_three_categories_and_globals(self) -> None:
        """2026-11-11 极简令：右栏与字典控制台同构——全局设置 + 三大主分类。"""
        plugin_dir = ROOT / "plugins" / "org.jiuzhang.dashboard" / "dist"
        source = ((plugin_dir / "plugin.js").read_text(encoding="utf-8")
                  + (plugin_dir / "rail.js").read_text(encoding="utf-8"))
        css = (plugin_dir / "plugin.css").read_text(encoding="utf-8")
        self.assertIn("DbRail.mount", source)
        self.assertIn("dict.globals_get", source)
        self.assertIn("dict.globals_save", source)
        self.assertIn("db-cat-btn", source)
        self.assertIn("aria-pressed", source)
        for dead in ("db-chip-group", "db-chip-row", "db-chip", "db-dict-body"):
            self.assertNotIn(dead, source, f"旧小标签残留：{dead}")
            self.assertNotIn(dead, css, f"旧小标签样式残留：{dead}")
        self.assertIn(".db-cat-btn {", css)
        self.assertIn("min-height: 56px", css)
        self.assertIn(".db-globals-toggle {", css)


if __name__ == "__main__":
    unittest.main()