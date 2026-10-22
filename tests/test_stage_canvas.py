"""中栏画布（Tabs + 沙箱 iframe + LRU 休眠）与事件总线契约：v0.6.0 军令任务 3。

钉死六件事：
1. 中栏只是舞台：Tabs 容器由底座渲染，业务画面在插件自己的 iframe 文档里；
2. 对话页是原生页签且不可关闭 —— 插件全崩也还有地方说话（AGENTS §2 兜底）；
3. iframe 沙箱不给 allow-same-origin，插件碰不到宿主 DOM 与令牌（PLUGIN_SPEC §2.3.4）；
4. 同时存活的插件页有上限，最久未用的发 plugin.deactivate 后摘掉文档（LRU 休眠）；
5. 宿主对插件请求 30 秒超时（PLUGIN_SPEC §5.1），发信人必须核验；
6. 插件能发的事件主题受白名单限制：不许发 ui.params.* / layout.*，防插件反向操控面板。

运行：``.venv/Scripts/python.exe -m unittest tests.test_stage_canvas``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
HTML = (STATIC / "workspace.html").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "workspace.css").read_text(encoding="utf-8")
STAGE = (STATIC / "js" / "stage.js").read_text(encoding="utf-8")
WORKSPACE = (STATIC / "js" / "workspace.js").read_text(encoding="utf-8")


class CanvasMarkupTest(unittest.TestCase):
    def test_01_center_is_a_tabbed_canvas(self) -> None:
        self.assertIn('id="wsTabs"', HTML)
        self.assertIn('role="tablist"', HTML)
        self.assertIn('id="wsCanvasBody"', HTML)

    def test_02_native_chat_panel_holds_thread_and_composer(self) -> None:
        panel = re.search(
            r'<section class="ws-tab-panel" id="wsPanelChat".*?</section>', HTML, re.S
        )
        self.assertIsNotNone(panel, "对话页签的面板不见了")
        self.assertIn('id="wsThread"', panel.group(0))
        self.assertIn('id="wsChatForm"', panel.group(0))
        self.assertIn('role="tabpanel"', panel.group(0))

    def test_03_panels_stack_inside_a_relative_body(self) -> None:
        body = re.findall(r"\.ws-canvas-body\s*\{([^}]*)\}", CSS)
        self.assertTrue(body)
        self.assertRegex(body[0], r"position:\s*relative")
        panel = re.findall(r"\.ws-tab-panel\s*\{([^}]*)\}", CSS)
        self.assertTrue(panel)
        self.assertRegex(panel[0], r"position:\s*absolute")
        self.assertIn("inset: 0", panel[0])

    def test_04_dock_is_host_owned(self) -> None:
        self.assertIn('id="wsDock"', HTML)
        self.assertIn('id="wsDockLog"', HTML)
        self.assertIn('id="wsToggleDock"', HTML)


class SandboxTest(unittest.TestCase):
    def test_01_iframe_has_no_same_origin(self) -> None:
        self.assertIn('frame.setAttribute("sandbox", SANDBOX)', STAGE)
        self.assertRegex(STAGE, r'var SANDBOX = "allow-scripts"')
        self.assertNotIn("allow-same-origin", STAGE, "给了同源就等于把底座 DOM 与令牌交出去")
        self.assertNotIn("allow-top-navigation", STAGE)

    def test_02_sender_is_verified_before_trusting_a_message(self) -> None:
        block = STAGE[STAGE.index('window.addEventListener("message"'):]
        self.assertIn("frame.contentWindow === event.source", block)
        self.assertIn("if (!tab) return", block, "不认识的发信人必须直接丢弃")
        self.assertIn('message.protocol !== PROTOCOL', block)

    def test_03_plugin_text_never_goes_through_innerhtml(self) -> None:
        self.assertNotIn("innerHTML", STAGE)
        self.assertIn("label.textContent = tab.title", STAGE)


class LruHibernationTest(unittest.TestCase):
    def test_01_live_frames_are_capped(self) -> None:
        self.assertRegex(STAGE, r"var MAX_LIVE_FRAMES = \d+;")
        cap = int(re.search(r"var MAX_LIVE_FRAMES = (\d+);", STAGE).group(1))
        self.assertGreaterEqual(cap, 1)
        self.assertLessEqual(cap, 4, "存活上限太大就失去休眠意义")
        self.assertIn("function enforceLru()", STAGE)

    def test_02_hibernation_deactivates_then_drops_the_document(self) -> None:
        block = STAGE[STAGE.index("function hibernate("): STAGE.index("function enforceLru(")]
        self.assertIn('notify(tab, "plugin.deactivate"', block)
        self.assertIn("removeChild(tab.frame)", block)
        self.assertIn('tab.state = "sleep"', block)
        self.assertIn("tab.pending.clear()", block, "休眠时必须清掉在飞的请求，否则回调永远等不到")

    def test_03_the_active_tab_is_never_hibernated(self) -> None:
        block = STAGE[STAGE.index("function enforceLru("): STAGE.index("function request(")]
        self.assertIn("tab.key === activeKey", block)
        self.assertIn("if (!oldest) break", block, "全是活动页时不许硬摘")

    def test_04_waking_a_sleeping_tab_remounts_it(self) -> None:
        block = STAGE[STAGE.index("function activate(key)"): STAGE.index("function applyFullscreen(")]
        self.assertIn('tab.state !== "live"', block)
        self.assertIn("mountFrame(tab)", block)


class ProtocolTest(unittest.TestCase):
    def test_01_request_response_carries_an_id(self) -> None:
        block = STAGE[STAGE.index("function request(tab"): STAGE.index("function notify(tab")]
        self.assertIn('kind: "request"', block)
        self.assertIn("protocol: PROTOCOL", block)
        self.assertRegex(STAGE, r'var PROTOCOL = "jzo-plugin/1"')

    def test_02_requests_time_out_at_thirty_seconds(self) -> None:
        self.assertRegex(STAGE, r"var REQUEST_TIMEOUT_MS = 30000;")
        self.assertIn("插件响应超时", STAGE)

    def test_03_notifications_are_one_way(self) -> None:
        block = STAGE[STAGE.index("function notify(tab"): STAGE.index("function broadcast(")]
        self.assertIn('kind: "notification"', block)
        self.assertNotIn("pending", block, "单向通知不许登记等待者")

    def test_04_publish_whitelist_blocks_panel_and_layout(self) -> None:
        allow = re.search(r"var PUBLISH_ALLOW = \[(.*?)\];", STAGE, re.S)
        self.assertIsNotNone(allow)
        topics = allow.group(1)
        self.assertIn("region.dock", topics)
        self.assertNotIn("ui.params", topics, "插件不许反向操控右侧面板")
        self.assertNotIn("layout.", topics, "插件不许改用户的布局")
        self.assertIn("PUBLISH_ALLOW.indexOf(topic) < 0", STAGE)

    def test_05_param_changes_reach_the_canvas(self) -> None:
        self.assertIn('bus.on("ui.params.changed"', STAGE)
        self.assertIn('broadcast("ui.params.changed"', STAGE)
        self.assertIn("function pushParams(tab)", STAGE, "挂载后要补发一次当前参数")

    def test_06_fullscreen_does_not_touch_user_fold_prefs(self) -> None:
        block = STAGE[STAGE.index("function applyFullscreen("): STAGE.index("function closeTab(")]
        self.assertIn('data-fullscreen', block)
        self.assertNotIn("data-side", block, "全屏只能压变量，不许改用户的折叠偏好")
        self.assertNotIn("data-ctx", block)


class WorkspaceWiringTest(unittest.TestCase):
    def test_01_only_declaring_plugins_get_a_canvas_tab(self) -> None:
        block = WORKSPACE[
            WORKSPACE.index("function enterPluginMode(plugin, item)"):
            WORKSPACE.index('if (chatEntry) chatEntry.addEventListener')
        ]
        self.assertIn("plugin.stage", block)
        self.assertIn("window.JzoStage.openPlugin(plugin)", block)

    def test_02_chat_entry_returns_to_the_native_tab(self) -> None:
        block = WORKSPACE[
            WORKSPACE.index("function enterChatMode()"): WORKSPACE.index("function enterPluginMode(")
        ]
        self.assertIn('window.JzoStage.activate("chat")', block)

    def test_03_param_changes_are_published_on_the_bus(self) -> None:
        self.assertIn("function publishUiParams(source, changedKey)", WORKSPACE)
        self.assertIn('publishUiParams("human", control.key)', WORKSPACE)
        self.assertIn('publishUiParams("ai", null)', WORKSPACE, "AI 代人改参数也要广播")
        self.assertIn("window.JzoUiState", WORKSPACE)

    def test_04_no_third_party_drag_or_ui_library(self) -> None:
        for source, name in ((STAGE, "stage.js"), (WORKSPACE, "workspace.js")):
            self.assertNotRegex(source, r"^\s*import\s", f"{name} 引入了打包器语法")
            self.assertIsNone(re.search(r"\(\?<[=!]", source), f"{name} 含后行断言")


if __name__ == "__main__":
    unittest.main()
