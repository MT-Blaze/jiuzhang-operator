"""工作台左栏契约（v0.5.4 + 军令 #15）：底座零业务入口，插件区动态渲染。

军令口径：
1. 删除写死的「拆分试卷 / 校对解析 / 组卷导出」与常驻对话入口（2026-11-05）；
2. 插件区按 ``/api/plugins`` 的发现结果渲染，空态显示「暂无插件」；
3. 点插件只注入工作模式上下文并更新舞台标题，不得跳转页面；
4. 左栏 = 切换用户卡片 + 插件列表 + 栏底控制台入口。

本测试只钉结构，不启浏览器；真机与像素证据由 ``.system_generated`` 下的探针产出。

运行：``.venv/Scripts/python.exe -m unittest tests.test_workspace_sidebar``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from app.core import manifests  # noqa: E402
from tests.core_sources import workspace_css, workspace_source  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
HTML = (STATIC / "workspace.html").read_text(encoding="utf-8")
JS = workspace_source()
CSS = workspace_css()


def rule_body(css: str, selector: str) -> str:
    """取 selector 所在规则的正文。"""
    at = css.index(selector)
    start = css.index("{", at) + 1
    return css[start:css.index("}", start)]


class SidebarStructureTest(unittest.TestCase):
    def test_01_business_tasks_are_gone(self) -> None:
        for label in ("拆分试卷", "校对解析", "组卷导出"):
            self.assertNotIn(label, HTML, f"左栏仍写死业务入口：{label}")
            self.assertNotIn(label, JS)

    def test_02_left_column_starts_with_the_user_switch(self) -> None:
        """2026-11-05：左栏首块是「切换用户」，底座不再有内置对话入口。"""
        self.assertNotIn('class="ws-entry-item"', HTML)
        self.assertNotIn('id="wsChatEntry"', HTML)
        self.assertNotIn('data-key="chat"', HTML)
        self.assertNotIn("chatEntry", JS)
        self.assertIn('id="wsUserSwitchBtn"', HTML)
        self.assertIn("当前用户", HTML)
        self.assertIn('id="wsUserModal"', HTML)
        self.assertIn("ws_users.js", HTML)

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

    def test_08_right_context_keeps_only_the_assistant_and_fills_the_column(self) -> None:
        """军令 #18 第一步：右栏只留 AI 助手，三个占位区与历史链删干净。

        2026-10-31 整改：右栏顶部那块「模型：OpenAI 兼容…」也删了——
        它既不提供任何操作，又占着辅助栏最宝贵的上沿；高度整块让给插件。
        """
        for token in ("ctxHistory", "ctxTask", "logHistory"):
            self.assertNotIn(token, HTML)
            self.assertNotIn(token, JS)
        for label in ("最近操作", "教材大纲"):
            self.assertNotIn(label, HTML)
        self.assertNotIn(">当前任务<", HTML)
        self.assertNotIn(".ws-history", CSS)
        self.assertNotIn(".ws-placeholder", CSS)
        # 模型展示块：宿主壳里一处都不许剩
        self.assertNotIn('id="ctxModel"', HTML, "右栏顶部的模型展示块已删")
        self.assertNotIn("renderModelChip", JS, "渲染它的脚本也要一起删干净")
        self.assertNotIn(".ws-context-value", CSS, "只服务于那块模型展示的样式一并退场")
        # 辅助栏要 100% 铺满画布：插槽自己吃掉剩余高度，内部滚动
        slot = rule_body(CSS, ".ws-context-slot-body {")
        for required in ("flex: 1 1 auto", "min-height: 0", "overflow: hidden"):
            self.assertIn(required, slot, f"右栏插槽缺 {required}，插件面板撑不满辅助栏")
        self.assertNotIn("height: 52vh", CSS, "插槽不许再写死视口高度")
        # 插槽下面不许再留分节的空白：插件面板该贴到栏底
        slot_rule = rule_body(CSS, ".ws-section.ws-context-slot {")
        self.assertIn("margin-bottom: 0", slot_rule,
                      "插槽下方那 20px 分节留白是死空间，插件面板会悬在半空")
        body_rule = rule_body(CSS, ".ws-context-body {")
        self.assertIn("overflow: hidden", body_rule, "辅助栏本体不滚，滚的是面板内部")

    def test_09_host_skips_its_duplicate_panel_for_slot_owners(self) -> None:
        """宿主那层「人机共设」快捷区：插件自带整块右栏面板时不再画一遍。

        判据只认插槽本身（插件声明了 sidebar.right），不认清单里的 ui.panel 开关——
        panel=false 字面上像「关掉辅助栏」，早年被误读成它能决定插件住不住。
        常驻助手已下架，判据只剩「插件自己声明了 sidebar.right」这一条。
        """
        self.assertIn("function ownsOwnRightPanel(plugin)", JS)
        helper = JS[JS.index("function ownsOwnRightPanel(plugin)"):]
        helper = helper[:helper.index("\n  }")]
        self.assertIn('plugin.slots.indexOf("sidebar.right")', helper)
        self.assertNotIn("assistantId", helper, "常驻助手已下架，判据不许再给它开后门")
        self.assertIn("ui.panel === false || ownsOwnRightPanel(plugin)", JS,
                      "宿主必须同时认结构性判据与显式开关")
        editor = manifests.load_manifest(ROOT / "plugins" / "org.jiuzhang.editor")
        self.assertNotIn("panel", editor.get("ui", {}),
                         "录题清单里不许再留 ui.panel=false")
        self.assertIn("sidebar.right", editor["slots"],
                      "录题声明了 sidebar.right，宿主据此判定它自带整块面板")


class SidebarBehaviourTest(unittest.TestCase):
    def test_01_plugins_rendered_from_discovery_api(self) -> None:
        self.assertIn('fetch("/api/plugins"', JS)
        self.assertRegex(JS, r'pluginListEl\.textContent = ""')
        self.assertIn('empty.textContent = "暂无插件"', JS)
        # 插件名是不可信清单内容，只能 textContent 落 DOM
        # （军令 #16 之后显示的是「昵称优先」，但仍经由同一个 textContent 出口）
        self.assertIn("name.textContent = rowTitle(plugin)", JS)
        self.assertIn("window.JzoPrefs.displayName(plugin)", JS)

    def test_02_plugin_row_has_no_assistant_special_case(self) -> None:
        """AI 助手整块下架后，点插件那一行只剩「切模式 + 按需开画布」。"""
        self.assertNotIn("function enterChatMode()", JS, "底座不再有内置对话模式")
        self.assertNotIn("ASSISTANT_PLUGIN_ID", JS, "宿主壳不许再认领某个助手插件")
        body = re.search(
            r"function enterPluginMode\(plugin, item\)\s*\{(.*?)\n  \}", JS, re.S
        )
        self.assertIsNotNone(body)
        block = body.group(1)
        self.assertNotIn("JzoContextPanel.reclaim()", block, "右栏主权不再由宿主点名归还")
        self.assertIn("window.JzoStage.openPlugin(plugin)", block)

    def test_03_plugin_entry_switches_working_mode(self) -> None:
        body = re.search(r"function enterPluginMode\(plugin, item\)\s*\{(.*?)\n  \}", JS, re.S)
        self.assertIsNotNone(body)
        block = body.group(1)
        self.assertIn("activePlugin = plugin", block)
        self.assertIn("setStage(name)", block)
        self.assertIn("initUiState(plugin)", block)
        # 「现在处于插件…」这类话没有发送方了：宿主壳已经没有对话流。
        self.assertNotIn("现在处于插件", block)
        self.assertNotIn("location", block)
        self.assertNotIn("window.open", block)

    def test_04_snapshot_still_exposes_right_slot_and_capabilities(self) -> None:
        """对话没了，但插件看得见的世界仍然只有宿主快照这一扇窗。"""
        snap = re.search(r"function stateSnapshot\(\)\s*\{(.*?)\n  \}", JS, re.S)
        self.assertIsNotNone(snap)
        block = snap.group(1)
        self.assertIn("right_slot", block)
        self.assertIn("capabilities", block)
        self.assertIn("tabs:", block)

    def test_05_initial_mode_is_the_neutral_workbench(self) -> None:
        """默认不叫「自由对话」——中栏留白，右栏默认收起。"""
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
