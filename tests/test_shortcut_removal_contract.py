"""军令 #18 第二步反向契约：全局快捷键仲裁层已彻底蒸发。

这一层不是「关掉」而是「拆掉」，所以断言的方向与旧契约相反——任何一处复活都会让本模块变红：

1. 前端模块 `static/js/shortcuts.js` 不存在，两份宿主页也不许再引它；
2. 宿主脚本里不许出现 `JzoKeys`、`shortcut.invoke` / `shortcut.press` / `shortcut.conflict`；
3. 后端不许再有 `/api/plugins/shortcuts` 端点、清单 `shortcuts` 解析与状态层键位读写；
4. OpenAPI 与插件清单契约里都不再暴露该字段；
5. 契约文档明写「底座永不提供快捷键注册 API」。

运行：``.venv/Scripts/python.exe -m unittest tests.test_shortcut_removal_contract``
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
HTML_FILES = (STATIC / "workspace.html", STATIC / "settings.html")
HOST_SCRIPTS = tuple((STATIC / "js").glob("*.js"))
BACKEND_SOURCES = tuple((ROOT / "app").rglob("*.py"))

BANNED_FRONTEND = ("JzoKeys", "shortcut.invoke", "shortcut.press", "shortcut.conflict",
                   "/api/plugins/shortcuts")
BANNED_BACKEND = ("set_shortcut", "normalize_shortcuts", "canonical_combo",
                  "/api/plugins/shortcuts")


class ShortcutModuleGoneTest(unittest.TestCase):
    def test_01_module_file_is_deleted(self) -> None:
        self.assertFalse((STATIC / "js" / "shortcuts.js").exists(),
                         "快捷键模块文件必须物理删除，不能留空壳")

    def test_02_no_host_page_loads_it(self) -> None:
        for page in HTML_FILES:
            with self.subTest(page=page.name):
                self.assertNotIn("shortcuts.js", page.read_text(encoding="utf-8"))

    def test_03_settings_ui_is_gone(self) -> None:
        html = (STATIC / "settings.html").read_text(encoding="utf-8")
        for token in ("keyList", "keyStatus", "keyReloadBtn", "全局快捷键"):
            self.assertNotIn(token, html, f"设置页仍残留 {token}")
        css = (STATIC / "css" / "settings.css").read_text(encoding="utf-8")
        for selector in (".key-list", ".key-row", ".key-input", ".key-note"):
            self.assertNotIn(selector, css, f"快捷键样式仍残留 {selector}")


class FrontendEvaporatedTest(unittest.TestCase):
    def test_01_no_host_script_mentions_the_arbiter(self) -> None:
        for script in HOST_SCRIPTS:
            source = script.read_text(encoding="utf-8")
            for token in BANNED_FRONTEND:
                with self.subTest(script=script.name, token=token):
                    self.assertNotIn(token, source)

    def test_02_prefs_no_longer_normalizes_combos(self) -> None:
        source = (STATIC / "js" / "prefs.js").read_text(encoding="utf-8")
        for token in ("canonicalCombo", "comboFromEvent", "MODIFIER_ORDER"):
            self.assertNotIn(token, source)

    def test_03_stage_does_not_relay_shortcut_requests(self) -> None:
        source = (STATIC / "js" / "stage.js").read_text(encoding="utf-8")
        self.assertNotIn("shortcut", source)

    def test_04_chat_plugin_no_longer_asks_the_host(self) -> None:
        source = (ROOT / "plugins" / "org.jiuzhang.chat" / "dist" / "plugin.js").read_text(
            encoding="utf-8"
        )
        for token in ("shortcut.invoke", "shortcut.press", "MY_KEYS"):
            self.assertNotIn(token, source)


class BackendEvaporatedTest(unittest.TestCase):
    def test_01_no_source_defines_the_removed_api(self) -> None:
        for source in BACKEND_SOURCES:
            text = source.read_text(encoding="utf-8")
            for token in BANNED_BACKEND:
                with self.subTest(source=str(source.relative_to(ROOT)), token=token):
                    self.assertNotIn(token, text)

    def test_02_openapi_has_no_shortcut_route(self) -> None:
        from app.main import app

        paths = app.openapi().get("paths", {})
        self.assertNotIn("/api/plugins/shortcuts", paths)

    def test_03_listing_schema_has_no_shortcuts_field(self) -> None:
        from app.main import app

        schema = app.openapi()["components"]["schemas"]["InstalledPlugin"]["properties"]
        self.assertNotIn("shortcuts", schema, "清单模型不许再声明快捷键字段")

    def test_04_state_view_has_no_shortcuts_key(self) -> None:
        from app.core import plugin_state

        self.assertNotIn("shortcuts", plugin_state.state())


class SpecPromiseTest(unittest.TestCase):
    def test_01_spec_declares_the_permanent_promise(self) -> None:
        spec = (ROOT / "docs" / "PLUGIN_SPEC.md").read_text(encoding="utf-8")
        self.assertIn("底座永不提供快捷键注册 API", spec)
        for token in ("`shortcuts`", "`shortcut.invoke`", "`shortcut.press`",
                      "`/api/plugins/shortcuts`"):
            # 允许出现在「已删除」的说明句里，但那种句子必须与删除口径同段
            if token in spec:
                self.assertIn("已整层删除", spec)


if __name__ == "__main__":
    unittest.main()
