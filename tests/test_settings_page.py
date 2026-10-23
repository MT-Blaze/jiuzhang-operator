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
STAGE_JS = (STATIC / "js" / "stage.js").read_text(encoding="utf-8")


class SettingsRouteTest(unittest.TestCase):
    def test_01_route_serves_settings_page(self) -> None:
        from app.main import app

        endpoints = {getattr(route, "path", None): getattr(route, "endpoint", None) for route in app.routes}
        endpoint = endpoints.get("/settings")
        self.assertIsNotNone(endpoint, "缺少 /settings 路由")
        response = asyncio.run(endpoint())
        self.assertEqual(Path(response.path), STATIC / "settings.html")

    def test_02_console_tab_embeds_this_page_and_route_stays_alive(self) -> None:
        """画布页签内嵌的是本页；同时 /settings 独立路由必须仍然可直达（防变砖）。"""
        self.assertIn('id="wsConsoleBtn"', WORKSPACE_HTML)
        self.assertIn('id="wsConsoleFrame"', WORKSPACE_HTML)
        self.assertIn('/settings?embedded=1', STAGE_JS, "控制台页签没内嵌设置页")
        self.assertIn('id="wsPanelConsole"', WORKSPACE_HTML)


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


class ConsoleSubTabsTest(unittest.TestCase):
    """插件分区是「左菜单 → 右二级菜单」：四个页签，不做弹窗、不竖着堆长页。"""

    def test_01_four_subtabs_and_panels_are_wired(self) -> None:
        self.assertIn('id="stPluginTabs"', HTML)
        self.assertIn('role="tablist"', HTML)
        labels = re.findall(r'class="st-subnav-item[^"]*"[^>]*>([^<]+)</button>', HTML)
        self.assertEqual([item.strip() for item in labels], ["管理", "检查更新", "在线索引", "手动安装"])
        for suffix in ("Manage", "Update", "Index", "Install"):
            self.assertIn(f'id="stPluginTab{suffix}"', HTML)
            self.assertIn(f'id="stPluginPanel{suffix}"', HTML)
        for panel_id in ("stPluginPanelUpdate", "stPluginPanelIndex", "stPluginPanelInstall"):
            block = re.search(rf'<section class="st-subpanel" id="{panel_id}"[^>]*>', HTML)
            self.assertIsNotNone(block)
            self.assertIn("hidden", block.group(0), f"{panel_id} 初始应收起")

    def test_02_secondary_tabs_keep_keyboard_navigation(self) -> None:
        self.assertIn("selectPluginTab", JS)
        self.assertIn("PLUGIN_TABS", JS)
        self.assertIn('event.key === "ArrowRight"', JS)
        self.assertIn('event.key === "Home"', JS)
        self.assertIn("console.panel", JS)
        self.assertIn("data.tab", JS)

    def test_03_subtabs_are_44px_targets(self) -> None:
        self.assertRegex(CSS, r"\.st-subnav-item\s*\{[^}]*min-height:\s*44px")

    def test_04_no_modal_for_plugin_management(self) -> None:
        self.assertNotIn("mg-modal-overlay", HTML.split("stPluginTabs", 1)[1].split("模型配置", 1)[0])


class WorkspaceTextbookSwitchTest(unittest.TestCase):
    def test_01_existing_workspace_has_inline_textbook_picker(self) -> None:
        self.assertIn("st-ws-textbook-inline", JS)
        self.assertIn("setWorkspaceTextbook", JS)
        self.assertIn("/api/workspaces/textbook", JS)
        self.assertIn("active_textbook_id", JS)
        self.assertRegex(CSS, r"\.st-ws-textbook-inline\s*\{[^}]*min-height:\s*44px")


class UpdateNoticeAndProgressTest(unittest.TestCase):
    def test_01_progressbar_is_aria_described_and_motion_safe(self) -> None:
        block = re.search(r'<div class="up-progress" id="upProgress"[^>]*>', HTML)
        self.assertIsNotNone(block)
        self.assertIn('role="progressbar"', block.group(0))
        self.assertIn('aria-valuetext="空闲"', block.group(0))
        self.assertIn("upProgressSet", JS)
        self.assertIn("prefers-reduced-motion: reduce", CSS)

    def test_02_notice_is_text_plus_color_and_persisted_locally(self) -> None:
        self.assertIn('id="wsConsoleDot"', WORKSPACE_HTML)
        self.assertIn("有 ", WORKSPACE_HTML + JS)
        self.assertIn("updates.available", JS)
        self.assertIn("jzo.updateNotice", JS)
        self.assertIn("renderUpdateNotice", (STATIC / "js" / "workspace.js").read_text(encoding="utf-8"))
        workspace_css = (STATIC / "css" / "workspace.css").read_text(encoding="utf-8")
        self.assertRegex(workspace_css, r"\.ws-console-badge\s*\{[^}]*background:")

    def test_03_notice_jumps_into_plugin_update_tab(self) -> None:
        workspace_js = (STATIC / "js" / "workspace.js").read_text(encoding="utf-8")
        self.assertIn('openConsoleTab("plugin", "update")', workspace_js)
        self.assertIn("tab=", workspace_js)
        self.assertIn("&tab=", workspace_js)
        self.assertIn("[?&]tab=", JS)


if __name__ == "__main__":
    unittest.main()
