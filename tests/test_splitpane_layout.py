"""四区拖拽调尺寸（SplitPane）契约：v0.6.0 军令任务 1 与任务 2。

钉死五件事：
1. 三条边界各有一枚手柄，键盘可达（AGENTS §6）；
2. 拖拽只写 CSS 变量，绝不往元素上补 width/height 内联样式（两本账是 v0.4.2 死锁温床）；
3. 拖拽期间 iframe 必须 pointer-events:none —— 否则鼠标滑进插件文档就被吞掉，
   mousemove 断流，手柄卡死在半路（纯原生拖拽最经典的暗坑）；
4. 尺寸落 localStorage、刷新恢复、左下角一键回默认；
5. 零第三方拖拽库，零 innerHTML。

像素与真机证据由 tools/split_probe.py（Playwright）产出。

运行：``.venv/Scripts/python.exe -m unittest tests.test_splitpane_layout``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
HTML = (STATIC / "workspace.html").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "workspace.css").read_text(encoding="utf-8")
JS = (STATIC / "js" / "splitpane.js").read_text(encoding="utf-8")
BUS = (STATIC / "js" / "bus.js").read_text(encoding="utf-8")

PANES = ("side", "context", "dock")
VARIABLES = {
    "side": "--sidebar-width",
    "context": "--context-width",
    "dock": "--dock-height",
}


def rule_bodies(selector: str) -> list[str]:
    return [
        body
        for group, body in re.findall(r"([^{}]+)\{([^{}]*)\}", CSS)
        if selector in group
    ]


class HandleMarkupTest(unittest.TestCase):
    def test_01_three_handles_exist(self) -> None:
        for pane in PANES:
            self.assertIn(f'data-resize="{pane}"', HTML, f"缺少 {pane} 边界的手柄")

    def test_02_handles_are_keyboard_reachable_separators(self) -> None:
        for pane in PANES:
            tag = re.search(r"<div[^>]*data-resize=\"" + pane + r"\"[^>]*>", HTML)
            self.assertIsNotNone(tag, f"找不到 {pane} 手柄标签")
            markup = tag.group(0)
            self.assertIn('role="separator"', markup)
            self.assertIn('tabindex="0"', markup, "手柄必须能进 tab 序列")
            self.assertIn("aria-label=", markup)
            orientation = "horizontal" if pane == "dock" else "vertical"
            self.assertIn(f'aria-orientation="{orientation}"', markup)

    def test_03_console_entry_is_locked_in_sidebar_foot(self) -> None:
        """v0.8.4：悬浮小图标（恢复布局）退役，栏底只留死锁的【设置与控制台】。"""
        foot = re.search(r'<footer class="ws-sidebar-foot">(.*?)</footer>', HTML, re.S)
        self.assertIsNotNone(foot, "左栏栏底不见了")
        self.assertIn('id="wsConsoleBtn"', foot.group(1), "管理入口必须固定在左下角")
        self.assertIn("设置与控制台", foot.group(1))
        self.assertNotIn('id="wsResetLayout"', foot.group(1), "悬浮小图标应已移除")
        bodies = rule_bodies(".ws-console-entry")
        self.assertTrue(bodies, "缺少管理入口样式")
        joined = "\n".join(bodies)
        self.assertRegex(joined, r"height:\s*44px")
        self.assertRegex(joined, r"width:\s*100%")


class DragSafetyTest(unittest.TestCase):
    """暗坑防线：拖拽时 iframe 必须让出指针事件。"""

    def test_01_iframe_goes_click_through_while_resizing(self) -> None:
        bodies = rule_bodies(".ws-page[data-resizing] iframe")
        self.assertTrue(bodies, "缺少「拖拽中 iframe 让出指针事件」的规则")
        self.assertRegex("\n".join(bodies), r"pointer-events:\s*none")

    def test_02_script_flips_the_resizing_flag(self) -> None:
        self.assertIn('page.setAttribute("data-resizing"', JS)
        self.assertIn('page.removeAttribute("data-resizing")', JS)
        # 旗标必须在挂监听之前升起，否则第一帧就可能把鼠标送进 iframe
        self.assertLess(
            JS.index('page.setAttribute("data-resizing"'),
            JS.index('window.addEventListener("mousemove"'),
            "data-resizing 必须在绑定 mousemove 之前挂上",
        )

    def test_03_listeners_are_captured_and_released(self) -> None:
        for event in ("mousedown", "mousemove", "mouseup"):
            self.assertIn(f'"{event}"', JS, f"缺少 {event} 监听")
        self.assertEqual(
            JS.count('window.removeEventListener("mousemove"'),
            JS.count('window.addEventListener("mousemove"'),
            "mousemove 监听没有成对摘除，会越拖越卡",
        )
        self.assertIn('window.addEventListener("blur", cancelDrag', JS, "窗口失焦必须中断拖拽")

    def test_04_moves_are_coalesced_into_frames(self) -> None:
        self.assertIn("requestAnimationFrame", JS, "mousemove 频率高于刷新率时必须合帧")

    def test_05_handles_grab_extra_hit_area(self) -> None:
        self.assertIn("touch-action: none", "\n".join(rule_bodies(".ws-resizer")))
        self.assertRegex(CSS, r"\.ws-resizer-v\s*\{\s*cursor:\s*col-resize")
        self.assertRegex(CSS, r"\.ws-resizer-h\s*\{\s*cursor:\s*row-resize")
        self.assertTrue(
            any("cursor: inherit" in body for body in rule_bodies("html.ws-dragging *")),
            "拖拽全程光标必须统一，否则滑过按钮时会闪成 pointer",
        )


class VariableOnlyTest(unittest.TestCase):
    def test_01_only_css_variables_are_written(self) -> None:
        for pane, variable in VARIABLES.items():
            self.assertIn(f'"{variable}"', JS, f"{pane} 没有对应的 CSS 变量")
        self.assertIn("style.setProperty", JS)
        # 直接写宽高就是第二本账：属性说 240、内联说 300，折叠与拖拽互相打脸
        self.assertNotRegex(JS, r"style\.(width|height|flexBasis)\s*=")

    def test_02_sizes_are_clamped(self) -> None:
        self.assertIn("function clamp(pane, value)", JS)
        for pane in PANES:
            block = re.search(
                r"^\s{4}" + pane + r":\s*\{(.*?)\n    \}", JS, re.S | re.M
            )
            self.assertIsNotNone(block, f"splitpane.js 缺少 {pane} 的配置")
            self.assertRegex(block.group(1), r"min:\s*\d+")
            self.assertRegex(block.group(1), r"max:\s*\d+")
            self.assertRegex(block.group(1), r"fallback:\s*\d+")

    def test_03_dock_cannot_eat_the_canvas(self) -> None:
        self.assertIn("page.clientHeight", JS, "底栏上限必须按视口实时算")


class PersistenceTest(unittest.TestCase):
    def test_01_layout_is_saved_after_drag(self) -> None:
        self.assertIn("localStorage.setItem(STORAGE_KEY", JS)
        self.assertIn("JSON.stringify", JS)
        self.assertRegex(JS, r'var STORAGE_KEY = "jzo\.workspace\.layout\.v1"')

    def test_02_layout_is_restored_on_load(self) -> None:
        self.assertIn("localStorage.getItem(STORAGE_KEY)", JS)
        self.assertIn("function restore()", JS)
        self.assertRegex(JS, r"\n  restore\(\);", "初始化时必须恢复上次布局")

    def test_03_corrupt_storage_cannot_break_the_page(self) -> None:
        """localStorage 里塞了垃圾也只能回默认，不许抛到调用点。"""
        restore_block = JS[JS.index("function load()"): JS.index("function restore()")]
        self.assertIn("try {", restore_block)
        self.assertIn("catch", restore_block)
        self.assertIn("return null", restore_block)

    def test_04_double_click_restores_that_pane(self) -> None:
        """悬浮复位图标早已退役（test_01 钉死页面里没有它），回默认只剩「双击分隔条」这一条活路。"""
        start = JS.index('addEventListener("dblclick"')
        block = JS[start:JS.index("syncAria(paneKey", start)]
        self.assertIn("PANES[paneKey].fallback", block, "双击要把这一区弹回默认宽")
        self.assertIn("persist: true", block, "双击的结果得写进记忆，刷新后不许弹回去")
        self.assertIn('by: "dblclick"', block, "总线要认得出是双击，别和拖拽混成一类")
        self.assertNotIn("wsResetLayout", JS, "退役的复位按钮不许再回宿主代码")

    def test_05_keyboard_and_double_click_adjust(self) -> None:
        self.assertIn("ArrowRight", JS)
        self.assertIn("ArrowLeft", JS)
        self.assertIn('"dblclick"', JS)
        self.assertIn("event.shiftKey", JS, "Shift 加速必须有，键盘调尺寸才够用")


class EventBusContractTest(unittest.TestCase):
    def test_01_layout_changes_are_announced(self) -> None:
        self.assertIn('"layout.changed"', JS)
        self.assertIn('"region.dock"', JS)

    def test_02_bus_is_dependency_free_and_safe(self) -> None:
        for name, source in (("bus.js", BUS), ("splitpane.js", JS)):
            self.assertNotIn("require(", source, f"{name} 引入了模块依赖")
            self.assertNotRegex(source, r"^\s*import\s", f"{name} 引入了打包器语法")
            self.assertNotIn("innerHTML", source, f"{name} 用了 innerHTML")
            self.assertIsNone(re.search(r"\(\?<[=!]", source), f"{name} 含后行断言")

    def test_03_subscriber_failure_cannot_break_the_bus(self) -> None:
        block = BUS[BUS.index("function emit("): BUS.index("function history(")]
        self.assertIn("try {", block)
        self.assertIn("catch", block)

    def test_04_workspace_wires_the_dock(self) -> None:
        workspace = (STATIC / "js" / "workspace.js").read_text(encoding="utf-8")
        self.assertIn("wireDock()", workspace)
        self.assertIn('window.JzoBus.on("region.dock"', workspace)
        self.assertIn("textContent", workspace[workspace.index("function dockLine("):])


class ScriptOrderTest(unittest.TestCase):
    def test_01_modules_load_before_workspace(self) -> None:
        order = [
            HTML.index("/static/js/bus.js"),
            HTML.index("/static/js/splitpane.js"),
            HTML.index("/static/js/stage.js"),
            HTML.index("/static/js/workspace.js"),
        ]
        self.assertEqual(order, sorted(order), "脚本顺序错了：总线与舞台必须先于工作台加载")


if __name__ == "__main__":
    unittest.main()
