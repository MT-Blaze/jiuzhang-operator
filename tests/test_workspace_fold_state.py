"""工作台折叠状态机契约：v0.4.2 内测「折叠后展不开」死锁的锁死测试。

根因（2026-10-24 军令，Playwright + Chromium 实测复现 5/5）：
桌面收起左栏靠的是 ``display: none``，会把该元素摘出网格。三栏原本全靠自动定位，
于是一摘走中栏与右栏就顺位前移——中栏挤进 ``0px`` 轨道（实测宽度 0）、
右栏涨到 1140px 盖住舞台头，「任务」展开钮被右栏内容截获指针事件，
用户看到的是「错乱 + 按钮点不动 + 再也展不开」。
修法：三栏各自显式钉轨（grid-column），display:none 便不再影响余下两栏的落位。

本测试不依赖浏览器与网络，只把 CSS/JS/HTML 三处的结构性约束钉死；
像素与命中证据由 ``tools/fold_probe.py``（Playwright）出图，
``tools/pixel_scan.py`` 负责按调色板归类截图行像素。

运行：``.venv/Scripts/python.exe -m unittest tests.test_workspace_fold_state``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "static" / "css" / "workspace.css").read_text(encoding="utf-8")
JS = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")
HTML = (ROOT / "static" / "workspace.html").read_text(encoding="utf-8")


def rule_body(selector: str) -> str:
    """取某条规则的声明块；选择器按字面匹配，找不到即失败。"""
    pattern = re.escape(selector) + r"\s*\{([^}]*)\}"
    match = re.search(pattern, CSS)
    assert match, f"workspace.css 缺少规则：{selector}"
    return match.group(1)


def rule_bodies(selector: str) -> str:
    """同一选择器可能被拆成多块（钉轨一块、外观一块），取全部声明合读。"""
    blocks = re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert blocks, f"workspace.css 缺少规则：{selector}"
    return "\n".join(blocks)


def media_body(min_width: int) -> str:
    """取某条 @media (min-width: N) 断点规则的整段正文（含嵌套块）。"""
    marker = f"@media (min-width: {min_width}px)"
    start = CSS.index(marker)
    depth, i = 0, CSS.index("{", start)
    for j in range(i, len(CSS)):
        if CSS[j] == "{":
            depth += 1
        elif CSS[j] == "}":
            depth -= 1
            if depth == 0:
                return CSS[i:j + 1]
    raise AssertionError(f"{marker} 括号未闭合")


def media_body_max(max_width: int) -> str:
    marker = f"@media (max-width: {max_width}px)"
    start = CSS.index(marker)
    depth, i = 0, CSS.index("{", start)
    for j in range(i, len(CSS)):
        if CSS[j] == "{":
            depth += 1
        elif CSS[j] == "}":
            depth -= 1
            if depth == 0:
                return CSS[i:j + 1]
    raise AssertionError(f"{marker} 括号未闭合")


class PaneTrackPinningTest(unittest.TestCase):
    """四区各钉一条轨道，且尺寸只由 CSS 变量决定：这是死锁的根治，也是拖拽的前提。"""

    def test_01_base_grid_has_five_tracks_and_three_rows(self) -> None:
        body = rule_body(".ws-page")
        self.assertRegex(
            body,
            r"grid-template-columns:\s*var\(--sidebar-width\)\s+var\(--gutter-side\)\s+"
            r"minmax\(0,\s*1fr\)\s+var\(--gutter-ctx\)\s+var\(--context-width\)",
        )
        self.assertRegex(
            body,
            r"grid-template-rows:\s*minmax\(0,\s*1fr\)\s+var\(--gutter-dock\)\s+var\(--dock-height\)",
        )
        # 默认尺寸写死在唯一的基础规则里，拖拽脚本只改这三枚变量
        for declaration in ("--sidebar-width: 240px", "--context-width: 300px", "--dock-height: 190px"):
            self.assertIn(declaration, body, f"缺少默认尺寸声明：{declaration}")

    def test_02_each_pane_pins_its_track(self) -> None:
        for selector, column in ((".ws-sidebar", 1), (".ws-center", 3), (".ws-context", 5)):
            body = rule_body(selector)
            self.assertIn(
                f"grid-column: {column}",
                body,
                f"{selector} 必须显式钉在第 {column} 轨：自动定位会在 display:none 时让余区顺位前移",
            )
            self.assertIn("grid-row: 1", body)
        # 四区通高几何（定调令）：输出日志区只吃中列，宽度严格等于画布宽度，
        # 绝不再横跨左右两栏——否则左右通高会被从底下凿穿。
        dock = rule_body(".ws-dock")
        self.assertIn("grid-column: 3", dock, "输出日志区必须只占中列")
        self.assertIn("grid-row: 3", dock)
        # 左右两栏与两条竖向手柄都要上下通高
        for selector in (".ws-sidebar", ".ws-context",
                         '.ws-resizer-v[data-resize="side"]', '.ws-resizer-v[data-resize="context"]'):
            self.assertIn("grid-row: 1 / -1", rule_body(selector),
                          f"{selector} 必须上下通高（1 / -1）")

    def test_03_resizers_own_the_gutter_tracks(self) -> None:
        """手柄各占一条 gutter 轨：不与任何区抢格子，收为 0 时自然消失。"""
        for selector, column, row in (
            ('.ws-resizer-v[data-resize="side"]', "2", "1"),
            ('.ws-resizer-v[data-resize="context"]', "4", "1"),
            ('.ws-resizer-h[data-resize="dock"]', "3", "2"),
        ):
            body = rule_body(selector)
            self.assertIn(f"grid-column: {column}", body, f"{selector} 没钉在 gutter 轨上")
            self.assertIn(f"grid-row: {row}", body)

    def test_04_fold_states_only_touch_variables(self) -> None:
        """折叠态只改尺寸变量，绝不重述 grid-template-columns。

        两本账（属性说收起、轨道说展开）正是 v0.4.2 死锁的温床；
        四区改造后轨道表达式只存在于基础规则一处，结构上无法再跑偏。
        """
        for selector, variable in (
            ('.ws-page[data-side="hidden"]', "--sidebar-width"),
            ('.ws-page[data-ctx="hidden"]', "--context-width"),
            ('.ws-page[data-dock="hidden"]', "--dock-height"),
        ):
            body = rule_body(selector)
            self.assertNotIn("grid-template-columns", body, f"{selector} 又重述了轨道表达式")
            self.assertRegex(body, re.escape(variable) + r":\s*0px")
        self.assertIn("minmax(0, 1fr)", rule_body(".ws-page"), "中栏轨道必须恒为 minmax(0, 1fr)")

    def test_05_collapsed_pane_removes_its_handle(self) -> None:
        """收起的那条边界不许再拖：0 宽轨道里的手柄既拖不动也点不着。

        三条手柄规则合并写在一个选择器组里，所以这里按「选择器组包含该选择器」
        匹配，而不是要求它独占一条规则。
        """
        rules = re.findall(r"([^{}]+)\{([^{}]*)\}", CSS)
        for selector in (
            '.ws-page[data-side="hidden"] .ws-resizer-v[data-resize="side"]',
            '.ws-page[data-ctx="hidden"] .ws-resizer-v[data-resize="context"]',
            '.ws-page[data-dock="hidden"] .ws-resizer-h[data-resize="dock"]',
        ):
            bodies = [body for group, body in rules if selector in group]
            self.assertTrue(bodies, f"找不到手柄规则：{selector}")
            self.assertTrue(
                any("display: none" in body for body in bodies),
                f"{selector} 收起后仍可命中",
            )


class ReopenEntryTest(unittest.TestCase):
    """展开入口：任何折叠态下都必须出现、常驻、且压得过栏内容。"""

    def test_01_entry_lives_in_tab_bar(self) -> None:
        """v0.8.4 定调：舞台头已删除，展开入口并入贴顶的页签栏。"""
        self.assertIn('id="wsOpenSidebar"', HTML)
        wrap = re.search(r'class="ws-tabs-wrap">(.*?)</div>', HTML, re.S)
        self.assertIsNotNone(wrap, "页签栏容器不见了")
        self.assertIn("wsOpenSidebar", wrap.group(1), "展开入口必须留在页签栏里")

    def test_02_entry_appears_when_side_hidden(self) -> None:
        self.assertEqual(rule_body(".ws-drawer-btn").count("display: none"), 1)
        self.assertRegex(
            rule_body('.ws-page[data-side="hidden"] .ws-drawer-btn'),
            r"display:\s*inline-flex",
        )

    def test_03_entry_layering_is_pinned_above_panels(self) -> None:
        """层级加固：入口钮要 position 定位 + z-index，且不许被 flex 挤掉。"""
        body = rule_body(".ws-drawer-btn")
        self.assertRegex(body, r"position:\s*relative", "入口钮缺 position，z-index 不生效")
        self.assertRegex(body, r"z-index:\s*\d+", "入口钮缺 z-index")
        self.assertRegex(body, r"flex:\s*none", "入口钮会被挤压缩窄")

    def test_04_entry_toggle_text_stays_in_sync(self) -> None:
        """折叠钮文案只能由状态机写入，且两态各有说法。"""
        body = re.search(r"function setSide\(open\).*?\n  \}", JS, re.S).group(0)
        self.assertIn('setAttribute("data-side"', body)
        self.assertIn('open ? "折叠" : "展开"', body)
        self.assertIn('aria-expanded', body)


class ClippingTest(unittest.TestCase):
    """隐藏时不许有内容溢到主对话区（军令任务 2.3）。"""

    def test_01_panels_clip_their_own_content(self) -> None:
        for selector in (".ws-sidebar", ".ws-context"):
            body = rule_bodies(selector)
            self.assertRegex(
                body,
                r"overflow:\s*hidden",
                f"{selector} 未裁剪：轨道收为 0 时长文本与按钮会溢出到主区",
            )
            self.assertRegex(body, r"min-width:\s*0")

    def test_02_tab_strip_clips_its_overflow(self) -> None:
        """页签栏贴顶后，长标题不再挤按钮：页签自己横向滚动，绝不许撑破中栏。"""
        body = rule_body(".ws-tabs")
        self.assertRegex(body, r"min-width:\s*0")
        self.assertRegex(body, r"overflow-x:\s*auto")

    def test_03_root_still_clips_the_canvas(self) -> None:
        self.assertRegex(rule_body(".ws-page"), r"overflow:\s*hidden")


class DesktopHideRuleTest(unittest.TestCase):
    """桌面（≥769px）仍用 display:none 收起；钉轨声明让这一步不再牵连余下两栏。"""

    def test_01_display_none_scoped_to_desktop_only(self) -> None:
        body = media_body(769)
        self.assertIn("display: none", body)
        self.assertIn('.ws-page[data-side="hidden"] .ws-sidebar', body)
        # 必须限定在 ≥769：窄屏对抽屉用 display:none 会让它「凭空消失」而非滑出，
        # 还会把元素摘出网格——那正是本次死锁的机制。
        self.assertIn("@media (min-width: 769px)", CSS)
        mobile = media_body_max(768)
        for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", mobile):
            if "display: none" in decl:
                self.assertNotRegex(
                    sel, r"ws-(sidebar|context|center)",
                    f"窄屏对 {sel.strip()} 使了 display:none，抽屉必须靠 transform 滑出",
                )


class MobileDrawerTest(unittest.TestCase):
    """窄屏（≤768px）抽屉逻辑：单列压轨、抽屉落位回退、收起后不可命中。"""

    def test_01_single_column_overrides_all_fold_states(self) -> None:
        body = media_body_max(768)
        block = re.search(
            r"\.ws-page,\s*\.ws-page\[data-side=\"hidden\"\],\s*"
            r"\.ws-page\[data-ctx=\"hidden\"\],\s*\.ws-page\[data-side=\"hidden\"\]\[data-ctx=\"hidden\"\]"
            r"\s*\{([^}]*)\}",
            body,
        )
        self.assertIsNotNone(block, "窄屏没有把四种栅格状态一起压成单列")
        self.assertRegex(block.group(1), r"grid-template-columns:\s*minmax\(0,\s*1fr\)")

    def test_02_drawer_panes_release_their_pins(self) -> None:
        """抽屉脱离网格流，桌面的第 1/3 轨钉位必须回退成 auto，否则凭空多出隐式轨道。"""
        body = media_body_max(768)
        block = re.search(r"\.ws-sidebar,\s*\.ws-context\s*\{([^}]*)\}", body)
        self.assertIsNotNone(block)
        self.assertRegex(block.group(1), r"grid-column:\s*auto")
        self.assertRegex(block.group(1), r"grid-row:\s*auto")
        self.assertRegex(block.group(1), r"position:\s*fixed")

    def test_03_center_pinned_to_first_track_on_mobile(self) -> None:
        body = media_body_max(768)
        block = re.search(r"\.ws-center\s*\{([^}]*)\}", body)
        self.assertIsNotNone(block, "窄屏没把中栏钉回第 1 轨")
        self.assertRegex(block.group(1), r"grid-column:\s*1")

    def test_04_closed_drawer_is_unreachable(self) -> None:
        """收起 = 滑出画布 + 滑完隐身：既留住动画，又不让看不见的按钮留在 tab 序列。"""
        body = media_body_max(768)
        block = re.search(
            r"\.ws-page\[data-side=\"hidden\"\] \.ws-sidebar,\s*\.ws-page\[data-ctx=\"hidden\"\] \.ws-context"
            r"\s*\{([^}]*)\}",
            body,
        )
        self.assertIsNotNone(block, "窄屏收起态规则被改写，检查抽屉是否又变成可命中的透明层")
        decl = block.group(1)
        self.assertIn("visibility: hidden", decl)
        self.assertRegex(decl, r"translateX\(-100%\)")

    def test_05_touch_targets_stay_44px(self) -> None:
        body = media_body_max(768)
        block = re.search(r"\.ws-btn,\s*\.ws-btn-sm\s*\{([^}]*)\}", body)
        self.assertIsNotNone(block)
        self.assertRegex(block.group(1), r"min-height:\s*44px")

    def test_06_tab_strip_survives_narrow_screens(self) -> None:
        """窄屏没有舞台头可挤：页签栏只许横向滚动，不许把抽屉入口推出屏外。"""
        body = media_body_max(768)
        self.assertIn("overflow-x: auto", rule_body(".ws-tabs"))
        self.assertIn("flex: none", rule_body(".ws-drawer-btn"))
        self.assertNotIn("ws-stage-head", body, "窄屏仍在给已删除的舞台头写样式")


class StateMachineTest(unittest.TestCase):
    """脚本侧：data 属性是唯一事实来源，不再往元素上补内联样式。"""

    def test_01_data_attribute_is_the_only_source(self) -> None:
        self.assertIn("function sideOpen()", JS)
        self.assertIn('wsPage.getAttribute("data-side") === "open"', JS)
        # 折叠相关代码不许写 style（两本账是死锁的温床）
        fold_block = JS[JS.index("var wsPage ="): JS.index("// 跨断点时必须重算")]
        self.assertNotIn(".style.", fold_block)

    def test_02_breakpoint_crossing_resyncs(self) -> None:
        """跨断点必须重算默认态：窄屏收起的抽屉拖宽会错位，反之会糊住对话流。"""
        self.assertIn("function onBreakpoint(matched)", JS)
        self.assertRegex(JS, r"mqMobile\.addEventListener\(\"change\"")
        self.assertRegex(JS, r"mqMobile\.addListener\(")  # 老内核兜底

    def test_03_no_regex_lookbehind(self) -> None:
        """AGENTS §6：不许用后行断言，旧浏览器直接语法失败。"""
        for src, name in ((JS, "workspace.js"), (CSS, "workspace.css")):
            self.assertIsNone(re.search(r"\(\?<[=!]", src), f"{name} 含后行断言")


if __name__ == "__main__":
    unittest.main()
