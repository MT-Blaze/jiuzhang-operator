"""工作台左栏契约（v0.5.4 + 军令 #15）：底座零业务入口，插件区动态渲染。

军令口径：
1. 删除写死的「拆分试卷 / 校对解析 / 组卷导出」；军令 #15 再删最后一条内置入口
   「自由对话」——找插件、找题目一律对右栏助手说；
2. 插件区按 ``/api/plugins`` 的发现结果渲染，空态显示「暂无插件」；
3. 点插件只注入工作模式上下文并更新右栏「当前任务」，不得跳转页面；
4. 左栏只剩折叠、插件列表与栏底控制台入口；安装/索引/About 全进 ``/settings``。

本测试只钉结构，不启浏览器；真机与像素证据由 ``.system_generated`` 下的探针产出。

运行：``.venv/Scripts/python.exe -m unittest tests.test_workspace_sidebar``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
HTML = (STATIC / "workspace.html").read_text(encoding="utf-8")
JS = (STATIC / "js" / "workspace.js").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "workspace.css").read_text(encoding="utf-8")
CHAT_JS = (ROOT / "plugins" / "org.jiuzhang.chat" / "dist" / "plugin.js").read_text(
    encoding="utf-8"
)


class SidebarStructureTest(unittest.TestCase):
    def test_01_business_tasks_are_gone(self) -> None:
        for label in ("拆分试卷", "校对解析", "组卷导出"):
            self.assertNotIn(label, HTML, f"左栏仍写死业务入口：{label}")
            self.assertNotIn(label, JS)

    def test_02_left_column_has_no_hardcoded_entry(self) -> None:
        """军令 #15 任务 2：撤掉最后一条内置入口，AI 助手只是清单里的一个普通插件行。

        口径说明：军令原文点的是「搜索框」，它在 v0.5.4 已退役；同区里当时唯一残留的
        硬编码入口是「自由对话」，本轮按同一意图清掉。
        """
        self.assertNotIn('class="ws-entry-item"', HTML)
        self.assertNotIn('id="wsChatEntry"', HTML, "左栏不许再留底座内置的对话入口")
        self.assertNotIn('data-key="chat"', HTML)
        self.assertNotIn("chatEntry", JS)
        self.assertIn('var ASSISTANT_PLUGIN_ID = "org.jiuzhang.chat"', JS)

    def test_03_plugin_area_has_empty_state(self) -> None:
        self.assertIn('id="wsPluginList"', HTML)
        self.assertIn('class="ws-plugin-empty"', HTML)
        self.assertIn("暂无插件", HTML)

    def test_04_plugin_entries_are_not_navigation_links(self) -> None:
        block = re.search(r'<ul class="ws-plugin-list".*?</ul>', HTML, re.S)
        self.assertIsNotNone(block)
        self.assertNotIn("<a ", block.group(0), "插件条目不许用链接跳转")
        self.assertNotIn("href=", block.group(0))

    def test_05_plugin_item_hit_area_is_44px(self) -> None:
        block = re.search(r"\.ws-plugin-item\s*\{([^}]*)\}", CSS)
        self.assertIsNotNone(block, "插件条目没有命中区规则")
        self.assertRegex(block.group(1), r"min-height:\s*44px")
        self.assertIn(".ws-plugin-empty", CSS)

    def test_06_low_frequency_entries_moved_to_settings(self) -> None:
        """v0.5.4：安装按钮、拖拽提示、插件索引、About 链接都不许留在左栏。"""
        self.assertNotIn("wsPluginInstallBtn", HTML)
        self.assertNotIn("wsPluginFile", HTML)
        self.assertNotIn("安装插件 zip 包", HTML)
        self.assertNotIn("ws-plugin-drop-hint", HTML)
        self.assertNotIn("ws-plugin-links", HTML)
        self.assertNotIn('href="/plugins"', HTML)
        self.assertNotIn('href="/about"', HTML)
        # 工作台脚本也不再引用已删除的安装按钮
        self.assertNotIn("wsPluginInstallBtn", JS)

    def test_07_console_entry_is_44px_and_not_a_gear_link(self) -> None:
        """v0.8.2 定调：左下角不再有固定齿轮，也不再跳独立页。"""
        self.assertNotIn('id="wsSettingsLink"', HTML, "齿轮链接应已被控制台入口取代")
        self.assertIn('id="wsConsoleBtn"', HTML)
        self.assertIn('aria-label="打开设置与控制台"', HTML)
        self.assertIn('JzoStage.activate("console")', JS, "入口应开画布页签而不是跳页")
        block = re.search(r"\.ws-console-entry\s*\{([^}]*)\}", CSS)
        self.assertIsNotNone(block, "缺少控制台入口样式")
        self.assertRegex(block.group(1), r"width:\s*100%", "管理入口必须占满栏底")
        self.assertRegex(block.group(1), r"height:\s*44px")
        self.assertNotIn(".ws-settings-link", CSS, "旧齿轮样式已零引用，该删干净")
        foot = re.search(r'<footer class="ws-sidebar-foot">(.*?)</footer>', HTML, re.S)
        self.assertIn('id="wsConsoleBtn"', foot.group(1), "管理入口必须死锁在左栏最底部")
        self.assertNotIn('id="wsResetLayout"', foot.group(1), "悬浮小图标已按定调令移除")


class SidebarBehaviourTest(unittest.TestCase):
    def test_01_plugins_rendered_from_discovery_api(self) -> None:
        self.assertIn('fetch("/api/plugins"', JS)
        self.assertRegex(JS, r'pluginListEl\.textContent = ""')
        self.assertIn('empty.textContent = "暂无插件"', JS)
        # 插件名是不可信清单内容，只能 textContent 落 DOM
        # （军令 #16 之后显示的是「昵称优先」，但仍经由同一个 textContent 出口）
        self.assertIn("name.textContent = rowTitle(plugin)", JS)
        self.assertIn("window.JzoPrefs.displayName(plugin)", JS)

    def test_02_assistant_row_only_reclaims_the_right_slot(self) -> None:
        """军令 #15 任务 4：点助手那一行不开画布页，只把右栏主权收回来。"""
        self.assertNotIn("function enterChatMode()", JS, "底座不再有内置对话模式")
        body = re.search(
            r"function enterPluginMode\(plugin, item\)\s*\{(.*?)\n  \}", JS, re.S
        )
        self.assertIsNotNone(body)
        block = body.group(1)
        self.assertIn("plugin.id === ASSISTANT_PLUGIN_ID", block)
        self.assertIn("window.JzoContextPanel.reclaim()", block)

    def test_03_plugin_entry_switches_working_mode(self) -> None:
        body = re.search(r"function enterPluginMode\(plugin, item\)\s*\{(.*?)\n  \}", JS, re.S)
        self.assertIsNotNone(body)
        block = body.group(1)
        self.assertIn("activePlugin = plugin", block)
        self.assertIn("setStage(name)", block)
        self.assertIn("initUiState(plugin)", block)
        # 「现在处于插件…」这类话只能由助手插件说：宿主壳已经没有对话流了
        self.assertNotIn("现在处于插件", block)
        self.assertIn("工作模式", CHAT_JS)
        self.assertNotIn("location", block)
        self.assertNotIn("window.open", block)

    def test_04_context_carries_plugin_and_working_mode(self) -> None:
        """上下文由助手插件组装，但它看得见的世界只有宿主给的快照。"""
        body = re.search(r"function gatherContext\(\)\s*\{(.*?)\n  \}", CHAT_JS, re.S)
        self.assertIsNotNone(body, "对话上下文应在助手插件里组装")
        block = body.group(1)
        self.assertIn("context.working_mode", block)
        self.assertIn("context.plugin =", block)
        self.assertIn("capabilities", block)
        self.assertIn("hostCall(\"workspace.state\"", CHAT_JS, "只能向底座要快照")
        snap = re.search(r"function stateSnapshot\(\)\s*\{(.*?)\n  \}", JS, re.S)
        self.assertIsNotNone(snap)
        self.assertIn("right_slot", snap.group(1))
        self.assertIn("capabilities", snap.group(1))

    def test_05_initial_mode_is_the_neutral_workbench(self) -> None:
        """军令 #15：默认不再叫「自由对话」——中栏停在引导页，右栏住助手。"""
        self.assertIn('setStage("工作台")', JS)
        self.assertIn("markActiveEntry(null)", JS)
        self.assertNotIn("markActiveEntry(chatEntry)", JS)

    def test_06_install_refreshes_plugin_list(self) -> None:
        self.assertRegex(JS, r"return loadPlugins\(\)\.catch")

    def test_07_no_page_navigation_in_workspace_script(self) -> None:
        for token in ("location.href", "location.assign", "window.open"):
            self.assertNotIn(token, JS, f"工作台脚本出现跳转：{token}")

    def test_08_global_drag_install_still_works(self) -> None:
        """删掉左栏安装按钮后，整页拖拽兜底必须还在（军令 2.4）。"""
        self.assertIn('window.addEventListener("drop"', JS)
        self.assertIn("installPluginZip(file, false)", JS)
        self.assertIn('fetch("/api/plugins/install"', JS)
        self.assertIn('id="wsDropOverlay"', HTML)


if __name__ == "__main__":
    unittest.main()
