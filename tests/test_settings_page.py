"""设置与控制页契约（v0.5.4）：低频操作统一收口，工作台左栏保持极简。

军令口径：
1. 左栏删除安装按钮、拖拽提示、插件索引与 About 链接，只留折叠、自由对话、
   插件列表与栏底齿轮；
2. 齿轮进入 ``/settings``：在线索引拉取、手动安装 zip（文件选择 + 拖拽区）、
   关于底座三段齐全；
3. 手动安装守同一套边界：只收 zip、50 MB 上限、令牌写接口、409 显式确认覆盖；
4. 工作台全局拖拽安装仍然生效（由 ``test_workspace_sidebar`` 另外钉住）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_settings_page``
"""

from __future__ import annotations

import asyncio
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
HTML = (STATIC / "settings.html").read_text(encoding="utf-8")
JS = (STATIC / "js" / "settings.js").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "settings.css").read_text(encoding="utf-8")
WORKSPACE_HTML = (STATIC / "workspace.html").read_text(encoding="utf-8")


class SettingsRouteTest(unittest.TestCase):
    def test_01_route_serves_settings_page(self) -> None:
        from app.main import app

        endpoints = {getattr(route, "path", None): getattr(route, "endpoint", None) for route in app.routes}
        endpoint = endpoints.get("/settings")
        self.assertIsNotNone(endpoint, "缺少 /settings 路由")
        response = asyncio.run(endpoint())
        self.assertEqual(Path(response.path), STATIC / "settings.html")

    def test_02_workspace_link_points_here(self) -> None:
        self.assertIn('id="wsSettingsLink"', WORKSPACE_HTML)
        self.assertIn('href="/settings"', WORKSPACE_HTML)


class IndexSectionTest(unittest.TestCase):
    def test_01_reuses_plugin_index_implementation(self) -> None:
        for element_id in ("plIndexForm", "plIndexUrl", "plFetchBtn", "plStatus", "plResults", "plRejected"):
            self.assertIn(f'id="{element_id}"', HTML, f"索引区缺少 {element_id}，无法复用 plugins.js")
        self.assertIn('/static/js/plugins.js', HTML)

    def test_02_default_index_is_official_mirror(self) -> None:
        self.assertIn("MT-Blaze/jiuzhang-plugins/main/plugins.json", HTML)
        self.assertIn("gh-proxy.com", HTML)

    def test_03_no_automatic_index_pull_on_load(self) -> None:
        """索引只在用户点【拉取清单】时请求；设置页脚本不主动拉清单。"""
        self.assertNotIn("/api/plugins/index", JS)


class ManualInstallSectionTest(unittest.TestCase):
    def test_01_drop_zone_and_file_picker_present(self) -> None:
        self.assertIn('id="stDropZone"', HTML)
        self.assertIn('role="button"', HTML)
        self.assertIn('tabindex="0"', HTML)
        self.assertIn('id="stPickZip"', HTML)
        file_input = re.search(r'<input type="file" id="stZipFile"[^>]*>', HTML)
        self.assertIsNotNone(file_input)
        self.assertIn('accept=".zip,application/zip"', file_input.group(0))

    def test_02_install_uses_write_token_and_install_endpoint(self) -> None:
        self.assertIn('fetch("/api/settings"', JS)
        self.assertIn('fetch("/api/plugins/install"', JS)
        self.assertIn('"X-JZO-Token": token', JS)

    def test_03_bounds_match_installer(self) -> None:
        self.assertIn("/\\.zip$/i", JS)
        self.assertIn("50 * 1024 * 1024", JS)
        self.assertIn("response.status === 409", JS)
        self.assertIn("replace=true", JS)
        self.assertIn("window.confirm", JS)

    def test_04_status_is_text_only(self) -> None:
        self.assertNotIn("innerHTML", JS)
        self.assertIn("statusBox.textContent", JS)

    def test_05_drop_zone_is_keyboard_operable(self) -> None:
        self.assertIn('event.key === "Enter"', JS)
        self.assertIn('event.key === " "', JS)

    def test_06_hit_areas(self) -> None:
        self.assertRegex(CSS, r"\.st-drop\s*\{[^}]*min-height:\s*132px")
        self.assertRegex(CSS, r"\.st-install-actions \.q-button\s*\{[^}]*min-height:\s*44px")
        self.assertRegex(CSS, r"\.st-about-links a\s*\{[^}]*min-height:\s*44px")


class AboutSectionTest(unittest.TestCase):
    def test_01_about_information_present(self) -> None:
        self.assertIn('id="st-about-title"', HTML)
        self.assertIn("关于底座", HTML)
        self.assertIn("Apache License 2.0", HTML)
        self.assertIn('href="/about"', HTML)
        self.assertIn("（About）", HTML)


if __name__ == "__main__":
    unittest.main()
