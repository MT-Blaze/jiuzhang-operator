"""字典页「原地切换 + 点两下回归」契约（2026-11-11 交互重构）。

钉住五件事：
1. 新开字典画布页签的旧通道彻底拆除（stage_frame_open.js 与 openFrame 全库无残留）；
2. 原地层只翻 hidden，绝不碰页签账本——右栏主权对账因此不触发，辅助栏不重挂；
3. 回归身份认「分类 + 表」，区划与学校共用一棵树也不会被误判成「再点一次」；
4. 宿主壳按正确次序装载新模块与新样式，插件帧的 [hidden] 能让位；
5. 内嵌控制台交出 DcEmbedded.go，同分类换表不重载文档。

运行：``.venv/Scripts/python.exe -m unittest tests.test_dict_inplace``
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VIEW = ROOT / "static" / "js" / "stage_dict_view.js"
DICT = ROOT / "static" / "js" / "stage_dict.js"
STAGE = ROOT / "static" / "js" / "stage.js"
SHELL = ROOT / "static" / "workspace.html"
CSS = ROOT / "static" / "css" / "workspace_dict_inplace.css"
CONSOLE_MAIN = ROOT / "static" / "js" / "dict_console" / "main.js"
CONSOLE_PANELS = ROOT / "static" / "js" / "dict_console" / "panels.js"


class OldTabChannelRemovedTest(unittest.TestCase):
    def test_frame_open_module_is_gone(self) -> None:
        self.assertFalse((ROOT / "static" / "js" / "stage_frame_open.js").exists())

    def test_no_open_frame_references_left(self) -> None:
        for path in (ROOT / "static").rglob("*.js"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("openFrame", source, f"{path.name} 仍在开新页签")
            self.assertNotIn("JzoStageFrameOpen", source, f"{path.name} 仍引用旧模块")
        self.assertNotIn("stage_frame_open.js", SHELL.read_text(encoding="utf-8"))

    def test_dict_never_creates_dict_tabs(self) -> None:
        for path in (VIEW, DICT):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("addTab", source, f"{path.name} 不许动页签账本")
            self.assertNotIn("stage.tab.activated", source, f"{path.name} 不许触发右栏主权对账")
            self.assertNotRegex(source, r"\bactivate\s*\(", f"{path.name} 不许切页签")


class InPlaceLayerTest(unittest.TestCase):
    def test_toggle_flips_hidden_only(self) -> None:
        source = VIEW.read_text(encoding="utf-8")
        self.assertIn("function toggle(tab, target)", source)
        self.assertIn("view.layer.hidden = !on", source)
        self.assertIn("tab.frame.hidden = on", source)

    def test_second_click_on_same_chip_returns_to_dashboard(self) -> None:
        source = VIEW.read_text(encoding="utf-8")
        self.assertIn("view.token === target.token", source)
        self.assertIn("return { active: false", source)

    def test_identity_is_category_plus_table(self) -> None:
        """区划与学校映射到同一棵树的二级标签，身份必须按表分，否则换表会被当成收页。"""
        source = DICT.read_text(encoding="utf-8")
        self.assertIn('token: category.key + "|" + (table || sub.key)', source)

    def test_stale_layer_after_hibernate_is_dropped(self) -> None:
        source = VIEW.read_text(encoding="utf-8")
        self.assertIn("view.layer.parentNode === tab.panel", source)
        self.assertIn("tab.dictView = null", source)

    def test_same_category_switch_reuses_document(self) -> None:
        source = VIEW.read_text(encoding="utf-8")
        self.assertIn("DcEmbedded", source)
        self.assertIn("api.go(target.cat, target.sub)", source)

    def test_unknown_category_and_table_are_rejected(self) -> None:
        source = DICT.read_text(encoding="utf-8")
        self.assertEqual(source.count('"BAD_REQUEST"'), 4)
        self.assertIn("未知的字典表", source)

    def test_layer_goes_to_canvas_tab_not_the_rail_handle(self) -> None:
        """右栏句柄只有 frame 没有 panel：铺错地方会抛异常，回执还得走发请求那一帧。"""
        source = DICT.read_text(encoding="utf-8")
        self.assertIn("var canvas = canvasTab()", source)
        self.assertIn("dictView.toggle(canvas, {", source)
        self.assertIn("replyHost(tab, message, true, {", source)
        self.assertIn("canvasTab: function () { return findTab(stageState.activeKey); }",
                      STAGE.read_text(encoding="utf-8"))


class ShellWiringTest(unittest.TestCase):
    def test_view_module_loads_before_stage(self) -> None:
        html = SHELL.read_text(encoding="utf-8")
        view_at = html.find("/static/js/stage_dict_view.js")
        stage_at = html.find("/static/js/stage.js")
        self.assertGreater(view_at, 0, "宿主壳没装载原地层模块")
        self.assertGreater(stage_at, view_at, "原地层必须早于 stage.js")

    def test_stylesheet_is_linked(self) -> None:
        self.assertIn("/static/css/workspace_dict_inplace.css", SHELL.read_text(encoding="utf-8"))

    def test_plugin_frame_yields_to_hidden(self) -> None:
        """.ws-plugin-frame 自带 display:block，会盖掉 [hidden] 的 UA 样式。"""
        css = CSS.read_text(encoding="utf-8")
        self.assertRegex(css, r"\.ws-plugin-frame\[hidden\]\s*\{\s*display:\s*none;")
        self.assertRegex(css, r"\.ws-dict-inplace\[hidden\]\s*\{\s*display:\s*none;")

    def test_new_files_stay_under_500_lines(self) -> None:
        for path in (VIEW, DICT, CSS, CONSOLE_MAIN, CONSOLE_PANELS):
            lines = len(path.read_text(encoding="utf-8").splitlines())
            self.assertLess(lines, 500, f"{path.name} 超过 500 行红线：{lines}")

    def test_no_regex_lookbehind(self) -> None:
        for path in (VIEW, DICT, CONSOLE_MAIN, CONSOLE_PANELS):
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"\(\?<[!=]")


class EmbeddedRouteTest(unittest.TestCase):
    def test_go_exposed_only_when_embedded(self) -> None:
        source = CONSOLE_MAIN.read_text(encoding="utf-8")
        block = re.search(r"if \(embedded\) \{\s*window\.DcEmbedded = \{.*?\n    \}", source, re.S)
        self.assertIsNotNone(block, "内嵌模式没交出 DcEmbedded")
        self.assertIn("ctx.openCategory(categoryKey)", block.group(0))
        self.assertIn("subTabs[categoryKey].activate(subKey)", block.group(0))

    def test_category_panel_hands_back_subtab_handle(self) -> None:
        source = CONSOLE_PANELS.read_text(encoding="utf-8")
        self.assertIn("ctx.registerSubTabs(category.key, handle)", source)
        self.assertIn("var handle = window.DcSubTabs.mount", source)


if __name__ == "__main__":
    unittest.main()