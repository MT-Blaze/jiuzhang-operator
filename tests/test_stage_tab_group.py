"""军令 #16 模块三：画布页签的沉浸全屏、溢出横滚、分组合并与休眠分层。

钉死六件事：
1. 双击才沉浸、单击照常切页；沉浸走真 Fullscreen API（地址栏退场），但只翻
   ``data-immersive`` / ``data-immersive-rail`` —— 绝不动 ``data-side`` / ``data-ctx``，
   老师的折叠偏好是另一本账；
2. 退沉浸三条通道只允许一条落地（``exitImmersive`` 幂等），宿主弹窗在场时底座不抢 ``Esc``；
3. 超过 10 个插件页签固定 120px + 左右小箭头 + 滚轮横滑；``scroll`` / ``resize`` 回调不带参数时
   要自己把页签数数回来，否则一滚就摘掉挤爆态、箭头跟着消失（run5 真机抓出来的坑）；
4. 分组合并只在挤爆时启用、组内凑满 2 页才收下拉；组名只认左栏那棵树；下拉用 fixed 定位逃出横滚裁剪；
5. 浅休眠只作用于 ``stage.weight = "light"``（``plugin.suspend`` / ``plugin.resume`` 成对），
   深休眠 LRU 名额只数 heavy；
6. 契约与实现对齐：PLUGIN_SPEC §2.13 与 §2.3.3 的 suspend/resume 行必须在册。

运行：``.venv/Scripts/python.exe -m unittest tests.test_stage_tab_group``
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
STAGE = (STATIC / "js" / "stage.js").read_text(encoding="utf-8")
WORKSPACE = (STATIC / "js" / "workspace.js").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "workspace.css").read_text(encoding="utf-8")
SPEC = (ROOT / "PLUGIN_SPEC.md").read_text(encoding="utf-8")
FIXTURE = ROOT / "examples" / "stage_weight_probe_plugin"


def block(source: str, start: str, end: str) -> str:
    """取源码里 [start, end) 这一段——契约测试只对可执行代码生效，注释另说。"""
    head = source.index(start)
    return source[head:source.index(end, head)]


def code_only(source: str) -> str:
    """剥掉注释再查禁词：说明性注释里写着「不许用 innerHTML」不算违规。"""
    body = re.sub(r"/\*.*?\*/", " ", source, flags=re.S)
    body = re.sub(r"//[^\n]*", " ", body)
    return re.sub(r"<!--.*?-->", " ", body, flags=re.S)


class ImmersiveTest(unittest.TestCase):
    def test_01_double_click_is_the_only_immersive_gesture(self) -> None:
        tap = block(STAGE, 'button.addEventListener("click"', "tab.button = button;")
        self.assertIn("activate(tab.key)", tap, "单击仍要照常切页，不许被双击手势吃掉")
        dbl = block(STAGE, 'button.addEventListener("dblclick"', "tab.button = button;")
        self.assertIn("toggleImmersive(tab.key)", dbl)
        self.assertIn(".ws-tab-close", dbl, "点关闭钮的那一下不许顺手把整屏拉起来")
        self.assertIn("event.preventDefault()", dbl)

    def test_02_immersive_asks_the_browser_for_real_fullscreen(self) -> None:
        body = block(STAGE, "function toggleImmersive(key) {", "function weightOf(tab) {")
        self.assertIn("requestFullscreen", body)
        self.assertIn("exitFullscreen", body)
        self.assertIn('setAttribute("data-immersive", "on")', body)
        self.assertIn('removeAttribute("data-immersive")', body)
        self.assertIn('removeAttribute("data-immersive-rail")', body,
                      "上一回呼出的浮层不许在下一张独占卷面时自己冒回来")
        self.assertIn("asking.catch", body, "Promise 没人接就是 unhandled rejection")
        self.assertIn("function applyFullscreen(tab)", STAGE, "stage.mode 全屏与沉浸是两本账，都要在")

    def test_03_fold_preferences_are_never_touched(self) -> None:
        body = block(STAGE, "function toggleImmersive(key) {", "function weightOf(tab) {")
        for pref in ("data-side", "data-ctx", "data-dock"):
            self.assertNotIn(pref, body, f"沉浸只压尺寸，不许改用户的 {pref} 偏好")

    def test_04_exit_is_idempotent_and_esc_yields_to_dialogs(self) -> None:
        body = block(STAGE, "function exitImmersive(via) {", "function weightOf(tab) {")
        self.assertIn('if (!immersiveKey) return;', body, "三条退出通道只许一条落地，否则底栏刷屏")
        self.assertIn('document.addEventListener("fullscreenchange"', body)
        self.assertIn('document.addEventListener("keydown"', body)
        self.assertIn('event.key !== "Escape"', body)
        self.assertIn(".ws-dialog-backdrop", body, "弹窗还要用 Esc 关掉，底座那一下不许抢")

    def test_05_the_rail_really_leaves_the_grid(self) -> None:
        """0 宽轨道拦不住内容的 min-content：沉浸中左栏必须真 display:none（run2 的 320px 僵尸栏）。"""
        hidden = re.findall(r'\.ws-page\[data-immersive="on"\] \.ws-sidebar\s*\{([^}]*)\}', CSS)
        self.assertTrue(any("display: none" in rule for rule in hidden),
                        "沉浸中左栏只压变量会留下一条拦不住的僵尸栏")
        overlay = re.findall(
            r'\.ws-page\[data-immersive="on"\]\[data-immersive-rail="on"\] \.ws-sidebar\s*\{([^}]*)\}', CSS
        )
        self.assertTrue(overlay, "沉浸中呼出的左栏浮层没有规则可循")
        self.assertIn("position: fixed", overlay[0])
        self.assertRegex(overlay[0], r"z-index:\s*\d+")

    def test_06_ctrl_b_raises_the_overlay_without_rewriting_preferences(self) -> None:
        body = block(WORKSPACE, "function toggleRail() {", "function setCtx(open) {")
        self.assertIn("immersiveOn()", body)
        self.assertIn('setAttribute("data-immersive-rail", "on")', body)
        self.assertIn('removeAttribute("data-immersive-rail")', body)
        self.assertIn("setSide(!sideOpen())", body, "非沉浸态还得是原来那本折叠账")
        self.assertNotIn('setAttribute("data-immersive"', WORKSPACE,
                         "data-immersive 是画布的手势，只有 stage.js 能写")
        self.assertGreaterEqual(WORKSPACE.count("toggleRail()"), 3,
                                "两枚左栏按钮共用同一个开关，不许两份实现")


class OverflowTest(unittest.TestCase):
    def test_01_threshold_and_fixed_width(self) -> None:
        self.assertRegex(STAGE, r"var TAB_OVERFLOW = 10;")
        rule = re.findall(r"\.ws-page\.ws-tabs-many \.ws-tab\s*\{([^}]*)\}", CSS)
        self.assertTrue(rule)
        self.assertIn("flex: 0 0 120px", rule[0])
        self.assertIn("width: 120px", rule[0])

    def test_02_arrows_appear_only_when_it_really_overflows(self) -> None:
        body = block(STAGE, "function paintOverflowBar(many) {", "function renderTabBar(")
        self.assertIn("typeof many === \"boolean\"", body,
                      "scroll/resize 回调不带参数进来，读 undefined 会把挤爆态一滚就摘掉")
        self.assertIn('tabs.filter(function (tab) { return tab.kind === "plugin"; }).length > TAB_OVERFLOW',
                      body, "自己数回来的必须还是插件页签数")
        self.assertIn("scrollWidth > tabsEl.clientWidth", body)
        self.assertEqual(body.count("hidden = !needs"), 2, "左右两枚箭头要一起亮、一起收")

    def test_03_wheel_takes_over_only_while_the_arrows_are_up(self) -> None:
        body = block(STAGE, "function ensureScrollButtons() {", "function paintOverflowBar(")
        self.assertIn("scrollBtns.right.hidden) return;", body, "箭头收着时不许抢纵向滚动的地盘")
        self.assertIn("event.preventDefault()", body)
        self.assertIn("passive: false", body, "不写 passive:false，preventDefault 会被浏览器忽略")
        self.assertIn("tabsEl.scrollLeft += delta", body)
        self.assertIn('setAttribute("aria-label", aria)', body)
        slide = block(STAGE, "function slideTabs(step) {", "function ensureScrollButtons()")
        self.assertIn("scrollBy(", slide)
        self.assertIn("prefers-reduced-motion", slide)


class GroupMergeTest(unittest.TestCase):
    def test_01_membership_and_names_come_from_the_rail_tree(self) -> None:
        self.assertIn('var UNGROUPED_KEY = "ungrouped";', STAGE)
        body = block(STAGE, "function groupKeyOf(tab) {", "function groupHolder(")
        self.assertIn("tab.plugin.folder_id", body, "分组归属只认后端反查出来的 folder_id")
        self.assertIn("return folder || UNGROUPED_KEY", body)
        self.assertIn('if (key === UNGROUPED_KEY) return "未分组"', body)
        self.assertIn('node.kind === "folder" && node.id === key', body, "组名只能从左栏树取")
        self.assertIn("groupTree = Array.isArray(tree) ? tree : []", body)
        self.assertIn("orderPluginTabs()", body, "树一改页签栏就得重涂")
        self.assertIn("setSidebarTree: setSidebarTree,", STAGE, "workspace 要能把这棵树交给画布")
        self.assertIn("window.JzoStage.setSidebarTree(sidebarTree)", WORKSPACE)

    def test_02_merge_needs_overflow_and_at_least_two_members(self) -> None:
        self.assertRegex(STAGE, r"var TAB_GROUP_MIN = 2;")
        body = block(STAGE, "function renderTabBar(orderedPluginTabs, many) {",
                     "function paintGroupStates() {")
        self.assertIn('many ? groupKeyOf(tab) : ""', body, "没挤爆就维持一插件一页")
        self.assertIn("bucket.members.length < TAB_GROUP_MIN", body)
        self.assertIn('tab.button.classList.remove("ws-tab-in-group")', body,
                      "平铺回去时要洗掉在组里的标记，否则样式跟着骗人")
        self.assertIn('tab.button.classList.add("ws-tab-in-group")', body)
        self.assertIn("if (alive[key]) return;", body, "组散伙了要把空壳页签摘掉")

    def test_03_dropdown_escapes_the_horizontal_scroll_clip(self) -> None:
        holder = block(STAGE, "function groupHolder(key) {", "function collapse(key) {")
        self.assertIn('list.setAttribute("data-group", key)', holder,
                      "从下拉里点开一页时要凭列表反查组，收摊才找得到人")
        self.assertIn('btn.setAttribute("aria-expanded", "false")', holder)
        toggle = block(STAGE, "function toggleGroup(key) {", "function placeGroupList(holder) {")
        self.assertIn('collapse(other)', toggle, "同一时刻只摊开一个")
        self.assertIn('setAttribute("aria-expanded", "true")', toggle)
        self.assertIn("first.focus()", toggle, "摊开即落焦点，键盘才走得住")
        place = block(STAGE, "function placeGroupList(holder) {", "function dismissGroup(tab) {")
        self.assertIn("getBoundingClientRect()", place)
        self.assertIn("window.innerWidth", place, "下拉不许伸出视口外")
        rule = re.findall(r"\.ws-tab-group-list\s*\{([^}]*)\}", CSS)
        self.assertTrue(rule)
        self.assertIn("position: fixed", rule[0], "跟着页签栏一起裁剪就等于点开看不见")

    def test_04_picking_a_child_tab_collapses_the_menu(self) -> None:
        dismiss = block(STAGE, "function dismissGroup(tab) {", "function barItems() {")
        self.assertIn("ws-tab-group-list", dismiss)
        self.assertIn('collapse(parent.getAttribute("data-group")', dismiss)
        activate = block(STAGE, "function activate(key)", "function applyFullscreen(")
        self.assertIn("dismissGroup(tab)", activate)
        self.assertIn("paintGroupStates()", activate)
        paint = block(STAGE, "function paintGroupStates() {", "function toggleImmersive(")
        self.assertIn("is-active", paint)
        self.assertNotIn("appendChild", paint, "切页只补涂标记；重排 DOM 会打断焦点")

    def test_05_outside_click_shuts_the_menu(self) -> None:
        body = block(STAGE, "// 摊开的下拉是「临时态」", "function dismissGroup(tab) {")
        self.assertIn("holder.chip.contains(event.target)", body)
        self.assertIn("collapse(expandedKey)", body)


class SleepPolicyTest(unittest.TestCase):
    def test_01_light_tabs_suspend_instead_of_unmounting(self) -> None:
        body = block(STAGE, "function applySleepPolicy() {", "function pushParams(tab) {")
        self.assertIn('weightOf(tab) !== "light"', body, "浅休眠的地盘只在 light，heavy 走 LRU 那本账")
        self.assertIn('notify(tab, "plugin.suspend", { reason: "background" })', body)
        self.assertIn('notify(tab, "plugin.resume", { reason: "foreground" })', body)
        self.assertIn("if (tab.kind !== \"plugin\" || tab.state !== \"live\"", body)
        self.assertIn("tab.suspended = true", body)
        self.assertIn("tab.suspended = false", body, "唤醒标记要跟着落，否则重复发通知")

    def test_02_lru_budget_counts_only_heavy_frames(self) -> None:
        lru = block(STAGE, "function enforceLru() {", "function request(")
        self.assertIn("var live = heavyLiveFrames();", lru)
        self.assertIn("while (live.length > MAX_LIVE_FRAMES)", lru)
        filter_body = block(STAGE, "function heavyLiveFrames() {", "function applySleepPolicy() {")
        self.assertIn('weightOf(tab) === "heavy"', filter_body)
        weight = block(STAGE, "function weightOf(tab) {", "function heavyLiveFrames() {")
        self.assertIn('stage.weight === "light" ? "light" : "heavy"', weight,
                      "缺省与非法值都算 heavy：不许因为漏声明就多开名额")

    def test_03_tab_snapshot_exposes_weight_and_sleep_marks(self) -> None:
        body = block(STAGE, "tabs: function () {", "request: function (key,")
        self.assertIn('weight: tab.kind === "plugin" ? weightOf(tab) : "native"', body)
        self.assertIn("suspended: tab.kind === \"plugin\" ? tab.suspended === true : false", body)
        self.assertIn("group: tab.kind === \"plugin\" ? groupKeyOf(tab)", body)


class ContractAndFixtureTest(unittest.TestCase):
    def test_01_spec_records_the_suspend_round_trip_and_module_three(self) -> None:
        self.assertIn("### 2.13", SPEC)
        self.assertIn("`plugin.suspend`", SPEC)
        self.assertIn("`plugin.resume`", SPEC)
        self.assertIn("同时存活的重型 iframe 最多 3 个", SPEC, "LRU 名额只数 heavy 得写进契约")
        self.assertIn("浅休眠 | `stage.weight = \"light\"`", SPEC, "生命周期表也要有浅休眠那一行")

    def test_02_probe_fixture_declares_light_and_is_not_a_singleton(self) -> None:
        manifest = json.loads((FIXTURE / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["stage"]["weight"], "light")
        self.assertIs(manifest["stage"]["singleton"], False)
        self.assertEqual(manifest["bus"]["publish"], ["region.dock"])

    def test_03_probe_fixture_passes_the_three_greps(self) -> None:
        """AGENTS §7.1 三查：插件侧 fetch / parent.document / localStorage 必须零命中。"""
        for name in ("dist/plugin.js", "dist/index.html"):
            source = code_only((FIXTURE / name).read_text(encoding="utf-8"))
            self.assertNotIn("fetch(", source, f"{name} 里插件自己出网了")
            self.assertNotIn("parent.document", source, f"{name} 里碰了宿主 DOM")
            self.assertNotIn("localStorage", source, f"{name} 里绕过宿主存了偏好")
            self.assertIsNone(re.search(r"\(\?<[=!]", source), f"{name} 含后行断言")

    def test_04_probe_fixture_echoes_the_notifications_it_is_judged_on(self) -> None:
        raw = (FIXTURE / "dist" / "plugin.js").read_text(encoding="utf-8")
        source = code_only(raw)
        self.assertIn('message.event === "plugin.suspend"', source)
        self.assertIn('message.event === "plugin.resume"', source)
        self.assertIn('event: "region.dock"', source, "收到通知要让老师看得见，否则等于没取证")
        self.assertNotIn("innerHTML", source, "回显走 textContent，注释里提它不算")


if __name__ == "__main__":
    unittest.main()
