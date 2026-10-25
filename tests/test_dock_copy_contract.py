"""底栏「报错诊断」双击静默复制契约（军令 #21 任务五）。

三条不可回退的口径：
  1. 双击整行即复制，复制源是行上的完整 ``data-copy``（时间 + 主题 + 正文）；
  2. 反馈只许原位换成「已复制」并闪绿底，严禁弹 Toast；
  3. 严禁抢焦点、严禁把整行文字刷蓝——隐藏 textarea 的老办法也要把焦点还回去。

浏览器行为证据由 ``tools/workspace_ui_probe.py`` 出（含剪贴板内容、焦点、
选区与截图像素）；这里只把实现的结构性约束钉死，防止后续重构悄悄退化。

运行：``.venv/Scripts/python.exe -m unittest tests.test_dock_copy_contract``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "static" / "css" / "workspace.css").read_text(encoding="utf-8")
JS = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")

COPY_START = JS.index("  function copyPlainText(value)")
COPY_END = JS.index("\n  if (dockTabs) {", COPY_START)
COPY_BLOCK = JS[COPY_START:COPY_END]
FALLBACK_BLOCK = JS[JS.index("  function fallbackCopy(text)"):JS.index("  function entryVisible(entry)")]


def rule_body(selector: str) -> str:
    pattern = re.escape(selector) + r"\s*\{([^}]*)\}"
    match = re.search(pattern, CSS)
    assert match, f"workspace.css 缺少规则：{selector}"
    return match.group(1)


class SilentCopyTest(unittest.TestCase):
    def test_01_copy_returns_boolean_not_silent_void(self) -> None:
        """成功与否要能回传，否则「已复制」会在复制失败时撒谎。"""
        self.assertIn("return navigator.clipboard.writeText(text).then(function () {", COPY_BLOCK)
        self.assertIn("return fallbackCopy(text);", COPY_BLOCK)
        self.assertIn("return Promise.resolve(fallbackCopy(text));", COPY_BLOCK)

    def test_02_fallback_restores_focus_without_scrolling(self) -> None:
        """textarea.select() 必然抢焦点，复制完必须还给用户原来所在的元素。"""
        self.assertIn("var active = document.activeElement;", FALLBACK_BLOCK)
        self.assertIn("active.focus({ preventScroll: true })", FALLBACK_BLOCK)
        self.assertLess(
            FALLBACK_BLOCK.index("document.body.removeChild(area)"),
            FALLBACK_BLOCK.index("active.focus({ preventScroll: true })"),
            "必须先摘掉隐藏 textarea 再还焦点",
        )

    def test_03_fallback_is_offscreen_and_returns_exec_result(self) -> None:
        self.assertIn('area.style.position = "fixed"', FALLBACK_BLOCK)
        self.assertIn("ok = document.execCommand(\"copy\")", FALLBACK_BLOCK)
        self.assertIn("return ok;", FALLBACK_BLOCK)

    def test_04_no_toast_in_copy_path(self) -> None:
        """军令逐字要求：严禁 Toast。注释可以写「不弹 Toast」，代码里不许有调用。"""
        code = re.sub(r"//[^\n]*", "", COPY_BLOCK)
        self.assertNotRegex(code, r"[Tt]oast")
        self.assertNotIn("alert(", code)


class ErrorViewSelectionTest(unittest.TestCase):
    def test_01_first_mousedown_is_cancelled(self) -> None:
        """第一下就要 preventDefault：等第二下再拦，焦点早已丢给 body。"""
        mouse_block = COPY_BLOCK[
            COPY_BLOCK.index('addEventListener("mousedown"'):COPY_BLOCK.index('addEventListener("selectstart"')
        ]
        self.assertIn('dockView !== "error"', mouse_block)
        self.assertIn("event.preventDefault();", mouse_block)
        self.assertNotIn("event.detail", mouse_block)

    def test_02_selectstart_is_blocked_only_in_error_view(self) -> None:
        self.assertRegex(COPY_BLOCK, r'addEventListener\("selectstart"')
        select_block = COPY_BLOCK[
            COPY_BLOCK.index('addEventListener("selectstart"'):COPY_BLOCK.index("addEventListener(\"dblclick\"")
        ]
        self.assertIn('dockView !== "error"', select_block)

    def test_03_error_rows_opt_out_of_text_selection(self) -> None:
        body = rule_body('.ws-dock-log[data-view="error"] .ws-dock-item')
        self.assertIn("user-select: none", body)
        self.assertIn("-webkit-user-select: none", body)

    def test_04_dblclick_clears_any_live_selection(self) -> None:
        self.assertIn("selection.removeAllRanges()", COPY_BLOCK)


class InPlaceFeedbackTest(unittest.TestCase):
    def test_01_flash_only_swaps_hint_and_class(self) -> None:
        self.assertIn('flash(ok ? "已复制" : "复制失败")', COPY_BLOCK)
        start = COPY_BLOCK.index("var flash = function")
        flash_block = COPY_BLOCK[start:COPY_BLOCK.index("copyPlainText(item.getAttribute", start)]
        self.assertIn('item.classList.add("is-copied")', flash_block)
        self.assertIn('hint.textContent = label', flash_block)
        self.assertIn('hint.textContent = "双击复制"', flash_block)

    def test_02_flash_is_cleared_after_a_while(self) -> None:
        self.assertIn("}, 1200);", COPY_BLOCK)
        self.assertIn('item.classList.remove("is-copied")', COPY_BLOCK)

    def test_03_copy_source_is_the_full_line(self) -> None:
        self.assertIn('item.setAttribute("data-copy", entry.line);', JS)
        self.assertIn('copyPlainText(item.getAttribute("data-copy") || "")', COPY_BLOCK)
        # 行文本由时间 + 主题 + 正文拼成，复制内容必须整行可 grep
        self.assertIn('line: at + (name ? " [" + name + "] " : " ") + body,', JS)

    def test_04_hint_is_decorative(self) -> None:
        """提示只是视觉反馈，读屏不应把它当成正文念两遍。"""
        self.assertIn('hint.setAttribute("aria-hidden", "true")', JS)

    def test_05_no_regex_lookbehind(self) -> None:
        self.assertIsNone(re.search(r"\(\?<[=!]", JS), "workspace.js 含后行断言（AGENTS §6）")


if __name__ == "__main__":
    unittest.main()
