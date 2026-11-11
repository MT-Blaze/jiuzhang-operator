"""中栏画布（Tabs + 沙箱 iframe + LRU 休眠）与事件总线契约：v0.6.0 军令任务 3。

钉死六件事：
1. 中栏只是舞台：Tabs 容器由底座渲染，业务画面在插件自己的 iframe 文档里；
2. 「设置与控制台」是唯一的原生页签且可关闭；关到画布空时不回补任何兜底页，中栏留白；
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
from tests.core_sources import stage_source, workspace_css, workspace_source  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
HTML = (STATIC / "workspace.html").read_text(encoding="utf-8")
CSS = workspace_css()
STAGE = stage_source()
WORKSPACE = workspace_source()


class CanvasMarkupTest(unittest.TestCase):
    def test_01_center_is_a_tabbed_canvas(self) -> None:
        self.assertIn('id="wsTabs"', HTML)
        self.assertIn('role="tablist"', HTML)
        self.assertIn('id="wsCanvasBody"', HTML)

    def test_02_no_fallback_panel_and_no_host_chat(self) -> None:
        """2026-10-31 军令：画布不设兜底页，关完所有页签就留白；
        2026-11-05：宿主壳与对话插件一并下架，宿主里不再有第二条对话通道。"""
        self.assertNotIn("wsPanelHome", HTML, "引导页签的面板必须彻底删除")
        self.assertNotIn("引导", HTML, "宿主壳里不许再出现「引导」二字")
        self.assertNotIn("暂无打开页签", HTML, "画布不塞占位文案")
        self.assertNotIn(".ws-home", CSS, "引导页的样式必须彻底删除")
        self.assertNotIn("ws-home", HTML)
        # 宿主壳里不许再留一份对话流：那等于给 AI 开一条绕过 Host API 的后门
        self.assertNotIn('id="wsThread"', HTML)
        self.assertNotIn('id="wsChatForm"', HTML)
        self.assertNotIn('id="wsPanelChat"', HTML)
        self.assertFalse(
            (ROOT / "plugins" / "org.jiuzhang.chat").exists(),
            "AI 助手插件已整块下架，不许悄悄回装",
        )

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

    def test_05_bar_buttons_share_the_tab_shape(self) -> None:
        """页签栏里的「入口 / 辅助栏」是按钮：与页签同背景、同圆角、同内边距、同字号同高，但没有叉。"""
        drawer = re.search(r'<button class="[^"]*ws-drawer-btn"[^>]*>(.*?)</button>', HTML, re.S)
        self.assertIsNotNone(drawer, "页签栏左端的「入口」钮不见了")
        self.assertIn("入口", drawer.group(1))
        self.assertNotIn("ws-tab-close", drawer.group(1), "按钮不是页签，不许长关闭叉")
        rule = re.search(
            r"\.ws-tabs-wrap \.ws-drawer-btn,\s*\n\.ws-tabs-wrap \.ws-ctx-btn \{([^}]*)\}", CSS
        )
        self.assertIsNotNone(rule, "页签栏按钮要有与页签同形的样式块")
        body = rule.group(1)
        for token in (
            "min-height: 36px",
            # 零外边距：入口钮紧贴第一枚页签，辅助栏钮紧贴最后一枚页签（2026-10-31 焊死）
            "margin: 6px 0 0 0",
            "padding: 6px 10px 6px 12px",
            "border-radius: 8px 8px 0 0",
            "background: var(--paper-deep)",
            "font-size: 0.8rem",
            # 底端对齐：三枚按钮与页签必须贴在同一根底线上
            "align-self: flex-end",
        ):
            self.assertIn(token, body, f"与页签同形缺了 {token}")

    def test_06_native_tabs_carry_close_buttons(self) -> None:
        """设置与控制台渲染关闭叉；原生页签的面板关掉后留在文档里供重建。"""
        self.assertIn("if (tab.closable) {", STAGE)
        self.assertIn("close.setAttribute(\"aria-label\", \"关闭\" + tab.title)", STAGE)
        self.assertIn("if (tab.kind === \"native\") tab.panel.hidden = true;", STAGE)


class SandboxTest(unittest.TestCase):
    def test_01_iframe_has_no_same_origin(self) -> None:
        self.assertIn('frame.setAttribute("sandbox", SANDBOX)', STAGE)
        sandbox = re.search(r'var SANDBOX = "([^"]+)"', STAGE).group(1)
        self.assertEqual(sandbox, "allow-scripts allow-modals")
        self.assertNotIn("allow-same-origin", sandbox, "给了同源就等于把底座 DOM 与令牌交出去")
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
        # 牺牲者的「跳过当前页」口径住在 core_tabs.js，组合根只负责递给它。
        self.assertIn("tabsCore.lruVictim(live, stageState.activeKey)", block)
        self.assertIn("if (!oldest) break", block, "全是活动页时不许硬摘")
        self.assertIn("if (tab.key === activeKey) return;", STAGE,
                      "core_tabs.lruVictim 必须跳过当前页")

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

    def test_07_bad_request_id_is_rejected_loudly(self) -> None:
        """入口守卫拒发不合法 id 时必须当场回包 + 底栏记账，不许静默丢弃（军令 #07 批复 2）。"""
        start = STAGE.index('if (message.kind === "request")')
        block = STAGE[start:start + 1600]
        self.assertIn("BAD_REQUEST_ID", block, "要回可读错误码，不能让插件干等到超时")
        self.assertIn("dock(", block, "拒发要在底栏「输出日志区」记一笔，开发者才不抓瞎")
        self.assertNotIn("!ID_RE.test(message.id)) return;", block, "守卫处不许裸 return")
        self.assertIn("^[A-Za-z0-9_-]{1,80}$", block, "回执与记账都要写出正确形状，便于自查")
        self.assertNotIn("data-ctx", block)


class WorkspaceWiringTest(unittest.TestCase):
    ENTER_START = "function enterPluginMode(plugin, item)"
    ENTER_END = "function applyStartupBehavior(plugins)"

    def enter_block(self) -> str:
        return WORKSPACE[WORKSPACE.index(self.ENTER_START):WORKSPACE.index(self.ENTER_END)]

    def test_01_only_declaring_plugins_get_a_canvas_tab(self) -> None:
        block = self.enter_block()
        self.assertIn("plugin.stage", block)
        self.assertIn("window.JzoStage.openPlugin(plugin)", block)

    def test_02_plugin_row_opens_canvas_without_assistant_branch(self) -> None:
        """AI 助手下架后，点插件行只剩「声明了 stage 才开画布」，没有特例分支。"""
        block = self.enter_block()
        self.assertNotIn("ASSISTANT_PLUGIN_ID", WORKSPACE)
        self.assertNotIn("JzoContextPanel.reclaim()", block)
        # 2026-10-31 军令：引导页彻底删除；原生页签只剩设置与控制台，且必须有叉
        self.assertNotIn('registerNative({ key: "home"', STAGE, "引导页签必须彻底移除")
        self.assertNotIn('activate("home")', STAGE)
        self.assertNotIn("引导", STAGE, "stage.js 里不许再出现「引导」")
        self.assertIn('key: "console", title: "设置与控制台"', STAGE)
        self.assertIn('panelId: "wsPanelConsole", lazy: true', STAGE,
                      "控制台只登记定义、懒加载，不许启动就建页签")
        self.assertIn("closable: options.closable !== false", STAGE)
        self.assertIn("function ensureNative(", STAGE, "关掉的控制台要能按登记表重建")
        # 关完所有页签：不回补兜底页、不写占位字，画布留白
        self.assertNotIn('ensureNative("home")', STAGE)
        self.assertIn("activeKey = null", STAGE)
        self.assertNotIn("暂无打开页签", STAGE)

    def test_03_param_changes_are_published_on_the_bus(self) -> None:
        self.assertIn("function publishUiParams(source, changedKey)", WORKSPACE)
        self.assertNotIn('publishUiParams("human", control.key)', WORKSPACE,
                         "右栏快捷操作面板已下架，参数只在插件自带面板里改")
        self.assertIn('publishUiParams("ai", null)', WORKSPACE, "插件经宿主改参数也要广播")
        self.assertIn("window.JzoUiState", WORKSPACE)

    def test_04_no_third_party_drag_or_ui_library(self) -> None:
        for source, name in ((STAGE, "stage.js"), (WORKSPACE, "workspace.js")):
            self.assertNotRegex(source, r"^\s*import\s", f"{name} 引入了打包器语法")
            self.assertIsNone(re.search(r"\(\?<[=!]", source), f"{name} 含后行断言")


class HostRelayV071Test(unittest.TestCase):
    """v0.7.1 宿主数据通道新增：删题转发、草稿托管、保存后自动收页。

    军令 #15 之后「AI 副驾」不再是底座托管区：它随助手插件住进右栏，
    读选区靠宿主转发的 notification，改写与回填一律走 Host API。
    """

    def test_01_bank_delete_is_relayed_with_write_permission(self) -> None:
        self.assertIn('"bank.delete"', STAGE, "宿主未开放 bank.delete")
        block = STAGE[STAGE.index('if (method === "bank.delete")'):STAGE.index('if (method === "bank.review")')]
        self.assertIn("questions:write", block, "删题必须先声明写权限")
        self.assertIn('method: "DELETE"', block)
        self.assertIn("bankProviderBase()", block, "删题只能作用于当前活跃的公共题库 provider")
        self.assertIn('action: "delete"', block, "删库成功要广播回流刷新")

    def test_02_draft_is_hosted_locally_never_fetched(self) -> None:
        # 草稿走宿主本地 localStorage，插件侧不碰；宿主先分好区再答复，仍不发题库请求
        self.assertIn('"draft.save", "draft.load"', STAGE)
        block = STAGE[STAGE.index('if (method === "draft.save"'):STAGE.index('var base = "/api/bank/plugins/')]
        self.assertIn("saveDraft(pluginId", block)
        self.assertIn("return;", block, "草稿答复必须短路，不发后端请求")
        self.assertIn("window.localStorage", STAGE, "草稿由同源宿主代持")
        self.assertIn("draftPrefix(draftWorkspace) + pluginId", STAGE,
                      "草稿按「工作区 + 插件」两级命名空间隔离，防串库")

    def test_03_editor_close_closes_tab_and_returns(self) -> None:
        self.assertIn('"system.editor_close"', STAGE, "system.editor_close 未进发布白名单")
        handler = STAGE[STAGE.index('bus.on("system.editor_close"'):STAGE.index('bus.on("stage.broadcast"')]
        self.assertIn("findPluginTab(EDITOR_PLUGIN_ID)", handler)
        self.assertIn("closeTab(editor.key)", handler, "保存后要真正关掉编辑页签")
        self.assertIn("activate(target.key)", handler, "关掉后切回发起端")

    def test_04_copilot_is_gone_and_ai_goes_through_host_relay(self) -> None:
        """副驾不是底座私产：宿主只转发选区与回填，AI 一句 DOM 都不碰。"""
        self.assertNotIn('id="wsCopilot"', HTML, "宿主自带副驾已随对话一起下架")
        self.assertNotIn('id="cpBackfill"', HTML)
        self.assertNotIn("/api/agent/refine", WORKSPACE, "宿主壳不得替 AI 直接调后端")
        editor_js = (ROOT / "plugins" / "org.jiuzhang.editor" / "dist" / "ui_ai.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('hostCall("agent.refine"', editor_js, "改写只能请求底座代调")
        self.assertIn('hostCall("editor.apply_patch"', editor_js, "回填只能请求底座代广播")
        self.assertIn('bus.on("stage.selection"', STAGE, "选区要转发给右栏面板")
        self.assertIn('broadcast("editor.apply_patch"', STAGE)

    def test_05_dedupe_channels_are_retired(self) -> None:
        """3.6 下架全库查重清洗：relay 分支与命令声明都不许回来。"""
        self.assertNotIn('"bank.dedupe_scan"', STAGE)
        self.assertNotIn('"bank.dedupe_merge"', STAGE)
        self.assertNotIn('method === "bank.dedupe_scan"', STAGE)
        # 不得退化成 assertNotIn("/duplicates", STAGE)：3.5 的 pending.batch_duplicates 合法使用该路径。

    def test_06_clean_review_falls_back_when_canvas_not_live(self) -> None:
        """4.3 降级分支：正文对照只进 live 的画布帧，画布不在场就回投 tab_not_live。

        Eval-06 补项 B——这条分支此前零覆盖。断言逐个钉住「条件 + 回投载荷」：
        去掉 ``cleanTab.state === "live"``（改成休眠帧也收对照）要红；
        删掉整段回投（辅助栏只能干等插件侧 2 秒超时）要红；
        回投不带 ``return;``（对照已进画布还追加降级通知）也要红。
        """
        start = STAGE.index('bus.on("editor.clean_review"')
        block = STAGE[start:STAGE.index('bus.on("editor.clean_review_state"')]
        self.assertIn('cleanTab && cleanTab.frame && cleanTab.state === "live"', block,
                      "对照只许投 state 为 live 且有文档的画布帧")
        self.assertRegex(block,
                         r'notify\(cleanTab, "editor\.clean_review", payload\);\s*return;',
                         "投进画布后必须当场短路，不许再向辅助栏补发降级"
                         "（钉的是 notify 之后紧接 return; 的先后关系，不钉缩进与换行：\n"
                         "        删掉 return; 或在两者之间插任何语句都要红）")
        self.assertIn('notify(panel, "editor.clean_review_state"', block,
                      "画布不在场时必须向辅助栏回投，不能让插件干等超时")
        self.assertIn('phase: "tab_not_live", reason: "canvas_not_live"', block)
        self.assertIn('key: String(cleanRaw.key || "")', block,
                      "回投必须带本次预览的 key，辅助栏按 key 对号、错号不许降级")


if __name__ == "__main__":
    unittest.main()
