"""工作台折叠状态机契约：v0.4.2 内测「折叠后展不开」死锁的锁死测试。

根因（2026-10-24 军令，Playwright + Chromium 实测复现 5/5）：
桌面收起左栏靠的是 ``display: none``，会把该元素摘出网格。三栏原本全靠自动定位，
于是一摘走中栏与右栏就顺位前移——中栏挤进 ``0px`` 轨道（实测宽度 0）、
右栏涨到 1140px 盖住舞台头，「任务」展开钮被 ``#ctxTask`` 截获指针事件，
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
    """三栏必须各钉一条轨道：这是死锁的根治。"""

    def test_01_base_grid_has_three_tracks(self) -> None:
        body = rule_body(".ws-page")
        self.assertRegex(body, r"grid-template-columns:\s*240px\s+minmax\(0,\s*1fr\)\s+300px")
        # 显式一行，供 grid-row: 1 有个真实落点
        self.assertIn("grid-template-rows", body)

    def test_02_each_pane_pins_its_track(self) -> None:
        for selector, column in ((".ws-sidebar", 1), (".ws-center", 2), (".ws-context", 3)):
            body = rule_body(selector)
            self.assertIn(
                f"grid-column: {column}",
                body,
                f"{selector} 必须显式钉在第 {column} 轨：自动定位会在 display:none 时让余栏顺位前移",
            )
            self.assertIn("grid-row: 1", body)

    def test_03_pinned_middle_track_still_flexes(self) -> None:
        """钉轨不许把中栏写死：它必须仍是 minmax(0, 1fr) 才吃得下折叠让出的宽度。"""
        for selector in (
            '.ws-page[data-side="hidden"]',
            '.ws-page[data-ctx="hidden"]',
            '.ws-page[data-side="hidden"][data-ctx="hidden"]',
        ):
            self.assertIn(
                "minmax(0, 1fr)",
                rule_body(selector),
                f"{selector} 的中栏轨道退化成固定宽度，折叠让出的空间吃不进去",
            )

    def test_04_hidden_side_collapses_only_first_track(self) -> None:
        body = rule_body('.ws-page[data-side="hidden"]')
        self.assertRegex(body, r"grid-template-columns:\s*0\s+minmax\(0,\s*1fr\)\s+300px")

    def test_05_both_hidden_leaves_center_full(self) -> None:
        body = rule_body('.ws-page[data-side="hidden"][data-ctx="hidden"]')
        self.assertRegex(body, r"grid-template-columns:\s*0\s+minmax\(0,\s*1fr\)\s+0")


class ReopenEntryTest(unittest.TestCase):
    """展开入口：任何折叠态下都必须出现、常驻、且压得过栏内容。"""

    def test_01_entry_exists_in_stage_head(self) -> None:
        self.assertIn('id="wsOpenSidebar"', HTML)
        tools = re.search(r'class="ws-stage-tools">(.*?)</div>', HTML, re.S)
        self.assertIsNotNone(tools, "舞台头按钮组不见了")
        self.assertIn("wsOpenSidebar", tools.group(1), "「任务」入口必须留在舞台头按钮组里")

    def test_02_entry_appears_when_side_hidden(self) -> None:
        self.assertEqual(rule_body(".ws-drawer-btn").count("display: none"), 1)
        self.assertRegex(
            rule_body('.ws-page[data-side="hidden"] .ws-drawer-btn'),
            r"display:\s*inline-flex",
        )

    def test_03_entry_layering_is_pinned_above_panels(self) -> None:
        """层级加固：按钮组与入口钮都要 position 定位 + z-index，且不许被 flex 挤掉。"""
        for selector in (".ws-stage-tools", ".ws-drawer-btn"):
            body = rule_body(selector)
            self.assertRegex(body, r"position:\s*relative", f"{selector} 缺 position，z-index 不生效")
            self.assertRegex(body, r"z-index:\s*\d+", f"{selector} 缺 z-index")
        self.assertRegex(rule_body(".ws-drawer-btn"), r"flex:\s*none", "入口钮会被挤压缩窄")

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

    def test_02_stage_title_yields_to_buttons(self) -> None:
        body = rule_body(".ws-stage-title")
        self.assertRegex(body, r"min-width:\s*0")
        self.assertRegex(body, r"overflow:\s*hidden")

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
        block = re.search(r"\.ws-btn,\s*\.ws-btn-sm,\s*\.ws-chip\s*\{([^}]*)\}", body)
        self.assertIsNotNone(block)
        self.assertRegex(block.group(1), r"min-height:\s*44px")

    def test_06_stage_title_survives_the_button_row(self) -> None:
        """窄屏舞台头三枚按钮吃掉大半行：标题若仍按内容挤位会被压成一列竖字
        （v0.4.2 遗留观感缺陷，360px 实测截图为证）。必须单行 + 省略号。"""
        body = media_body_max(768)
        block = re.search(r"\.ws-stage-title h1\s*\{([^}]*)\}", body)
        self.assertIsNotNone(block, "窄屏没给标题单行省略号的处理")
        self.assertRegex(block.group(1), r"white-space:\s*nowrap")
        self.assertRegex(block.group(1), r"text-overflow:\s*ellipsis")
        self.assertRegex(block.group(1), r"overflow:\s*hidden")
        self.assertRegex(
            re.search(r"\.ws-stage-kicker\s*\{([^}]*)\}", body).group(1),
            r"display:\s*none",
            "装饰性 kicker 在窄屏该让位给按钮行",
        )


class StateMachineTest(unittest.TestCase):
    """脚本侧：data 属性是唯一事实来源，不再往元素上补内联样式。"""

    def test_01_data_attribute_is_the_only_source(self) -> None:
        self.assertIn("function sideOpen()", JS)
        self.assertIn('wsPage.getAttribute("data-side") === "open"', JS)
        # 折叠相关代码不许写 style（两本账是死锁的温床）
        fold_block = JS[JS.index("var wsPage ="): JS.index("if (promptInput)")]
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
