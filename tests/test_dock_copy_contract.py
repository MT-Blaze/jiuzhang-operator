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
from tests.core_sources import workspace_css, workspace_source  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
JS_DIR = ROOT / "static" / "js"
CSS = workspace_css()
JS = workspace_source()

COPY_START = JS.index("  function copyPlainText(value)")
COPY_END = JS.index("\n  if (dockTabs) {", COPY_START)
COPY_BLOCK = JS[COPY_START:COPY_END]


def function_body(source: str, header: str) -> str:
    """按花括号配平取一个函数体：拆模块后不能再靠「下一个函数」定位。"""
    start = source.index(header)
    depth = 0
    for index in range(source.index("{", start), len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"未闭合的函数：{header}")


FALLBACK_BLOCK = function_body(JS, "  function fallbackCopy(text)")


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
        # 军令 #28：报错诊断复制的是完整现场，没有现场才退回那一行摘要。
        self.assertIn('item.setAttribute("data-copy", entry.detail || entry.line);', JS)
        self.assertIn('copyPlainText(item.getAttribute("data-copy") || "")', COPY_BLOCK)
        # 行文本由时间 + 主题 + 正文拼成，复制内容必须整行可 grep
        self.assertIn('at + (name ? " [" + name + "] " : " ") + body', JS,
                      "普通行的复制内容必须整行可 grep")
        # 「记一笔」只留一行灰字：`[15:30] 正文`——不带主题名，不带秒
        self.assertIn('kind === "note"', JS)
        self.assertIn('"[" + at.slice(0, 5) + "] " + body', JS)

    def test_04_hint_is_decorative(self) -> None:
        """提示只是视觉反馈，读屏不应把它当成正文念两遍。"""
        self.assertIn('hint.setAttribute("aria-hidden", "true")', JS)

    def test_05_no_regex_lookbehind(self) -> None:
        self.assertIsNone(re.search(r"\(\?<[=!]", JS), "workspace.js 含后行断言（AGENTS §6）")


class DockRoutingTest(unittest.TestCase):
    """底栏分流契约：系统底座事件只进【系统终端】，业务操作只进【运行日志】。"""

    def test_01_error_view_takes_warn_and_error(self) -> None:
        block = function_body(JS, "  function entryVisible(entry)")
        self.assertIn('if (dockView === "error") return entry.level === "error" || entry.level === "warn";',
                      block)
        self.assertIn('if (dockView === "terminal") return entry.scope === "system";', block)
        self.assertIn('return entry.scope === "runtime";', block,
                      "运行日志必须彻底屏蔽系统底座事件")

    def test_02_system_topics_are_the_base_families(self) -> None:
        block = JS[JS.index("  var SYSTEM_TOPIC_RE"):JS.index("  function isSystemTopic")]
        for prefix in ("stage", "region", "layout", "plugin", "system", "workspace", "provider"):
            self.assertIn(prefix, block, f"系统终端口径漏了 {prefix}.*")
        self.assertIn('wsState.sysEntries', JS)
        self.assertIn('wsState.runtimeEntries', JS)

    def test_03_plugin_business_logs_stay_in_runtime(self) -> None:
        """插件经宿主桥投来的 region.dock 带 pluginId：那是业务日志，不许被传输主题拖进终端。"""
        start = JS.index('window.JzoBus.on("region.dock"')
        block = JS[start:JS.index('window.JzoBus.on("layout.changed"', start)]
        self.assertIn("var fromPlugin = Boolean(payload.pluginId);", block)
        self.assertIn('fromPlugin ? "runtime"', block)
        self.assertIn('"layout.changed", "", "", "system"', JS,
                      "布局调整是底座事件，只进系统终端")

    def test_04_views_read_separate_ledgers(self) -> None:
        block = function_body(JS, "  function entriesForView()")
        self.assertIn('if (view === "terminal") return wsState.sysEntries;', block)
        self.assertIn("return wsState.runtimeEntries;", block)
        self.assertIn("if (view === \"error\") return allEntries();", block)
        merged = function_body(JS, "  function allEntries()")
        self.assertIn("wsState.sysEntries.concat(wsState.runtimeEntries)", merged,
                      "报错诊断要把两本账里的告警合起来")

    def test_05_dict_business_ops_reach_the_runtime_log(self) -> None:
        """字典控制台在 iframe 里：写操作成功/失败必须经 postMessage 递给宿主。"""
        console = ROOT / "static" / "js" / "dict_console"
        ops = (console / "ops_log.js").read_text(encoding="utf-8")
        self.assertIn('data.jzo !== "dict.ops"', (JS_DIR / "stage_dict_view.js").read_text(encoding="utf-8"))
        self.assertIn('var FLAG = "dict.ops";', ops)
        client = (console / "client.js").read_text(encoding="utf-8")
        self.assertIn("window.DcOpsLog.ok(", client)
        self.assertIn("window.DcOpsLog.fail(", client)
        html = (ROOT / "static" / "dict_console.html").read_text(encoding="utf-8")
        self.assertIn("dict_console/ops_log.js", html)

    def test_06_bare_not_found_is_recognised_as_error(self) -> None:
        start = JS.index("  function dockLevel(topic, text)")
        block = JS[start:JS.index("  function stamp()", start)]
        self.assertIn("not found", block, "英文 HTTP 原话（如 Not Found）必须判进报错诊断")
        self.assertIn("失败|错误|异常|超时|冲突", block)

    def test_07_detail_is_kept_whole_and_summarised_separately(self) -> None:
        start = JS.index("  function dockLine(")
        block = JS[start:JS.index("  function wireDock()", start)]
        self.assertIn("detailText", block)
        self.assertIn("slice(0, 20000)", block, "现场最多留 20KB，不许截成一句")
        self.assertIn('if (!detailText && (kind === "error" || kind === "warn")) detailText = full.slice(0, 20000);',
                      block, "没有额外现场时，至少把整句话原样留下")
        self.assertIn("detail: detailText", block)

    def test_08_error_view_renders_the_raw_detail(self) -> None:
        block = function_body(JS, "  function renderDock()")
        self.assertIn('detail.className = "ws-dock-detail";', block)
        self.assertIn('detail.textContent = entry.detail;', block)
        self.assertIn('dockView === "error"', block)
        body = rule_body(".ws-dock-detail")
        self.assertIn("white-space: pre-wrap", body, "堆栈与 Response 原文必须按原样折行")
        self.assertIn("overflow: auto", body)

    def test_09_bus_accepts_tone_and_level(self) -> None:
        start = JS.index("  function wireDock()")
        block = JS[start:start + 3600]
        self.assertIn('payload.level || payload.tone', block)
        self.assertIn("payload.detail_text", block, "老口径 detail_text 也要收")
        self.assertIn("dockLine(payload.text", block)


if __name__ == "__main__":
    unittest.main()
