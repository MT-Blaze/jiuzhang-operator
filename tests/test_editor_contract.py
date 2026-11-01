"""录题工作台 v2（org.jiuzhang.editor，军令 #23 阶段 1–2）契约测试。

真机三栏与 KaTeX 渲染由 ``tools/editor_probe.py`` 取证；这里钉住可静态判定的部分：

- 清单只申请画布舞台 + 右栏辅助栏插槽，写库经宿主、令牌永不进插件；
- 画布内只有三栏（左原图 | 中 exam-zh 源码 | 右渲染），**没有任何表单控件**；
- 辅助栏（``#epRoot``）只有元数据表单 + 审核动作 + 格式切换，**不放源码、不放预览**；
- 源码只用 exam-zh 标准环境（question/choices/problem/solution），填空用 ``\\fillin``；
- 解析器 / 重组器 / 本地清洗三件套的口径（阶段 2 复用同一份实现，不许另写）；
- 假数据 ``dev/fixtures.json`` 是单一事实来源：过 Schema 2.0、按《格式宪法》写源码、
  与 plugin.js 内嵌块逐字一致，且**绝不进发行包**；
- 沙箱红线：无 fetch / parent.document / 浏览器本地存储 / 远程资源 / 后行断言。

已知偏离（详见 docs/editor-v2-progress.md）：v1 的 A4 固定页几何（794×1123）随「渲染不固定
A4、按内容实际高度」这条已定决策一并撤除，因此不再保留 A4 尺寸判据。

运行：``.venv/Scripts/python.exe -m unittest tests.test_editor_contract``
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.core.plugins import validate_plugin
from tools.build_plugin import build_plugin

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "org.jiuzhang.editor"
DIST = PLUGIN_DIR / "dist"
FIXTURES = PLUGIN_DIR / "dev" / "fixtures.json"
BEGIN = "  //# FIXTURES-BEGIN"
END = "  //# FIXTURES-END"

# 军令 #23：只许 exam-zh 标准环境，禁止自定义任何 LaTeX 环境。
ALLOWED_ENVS = {"question", "choices", "problem", "solution"}


def read(name: str) -> str:
    return (DIST / name).read_text(encoding="utf-8")


def manifest() -> dict:
    return json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))


def css_rule(css: str, selector: str) -> str:
    at = css.index(selector + " {")
    return css[at:css.index("}", at)]


def canvas_only(html: str) -> str:
    """画布实例那段 DOM——右栏辅助栏根节点之后的内容不属于画布。"""
    return html[html.index('id="edRoot"'):html.index('id="epRoot"')]


def panel_only(html: str) -> str:
    """辅助栏实例那段 DOM——截到页面脚本之前，KaTeX 是宿主给画布渲染公式用的。"""
    start = html.index('id="epRoot"')
    return html[start:html.index("<script", start)]


def rule_body(css: str, selector: str) -> str:
    """取 selector 所在规则的正文（分组选择器 .a, .b {} 也能命中）。"""
    at = css.index(selector)
    start = css.index("{", at) + 1
    return css[start:css.index("}", start)]


def fn_body(js: str, name: str) -> str:
    """取 ``  function name(`` 到下一个同级函数声明之间的源码。"""
    start = js.index("  function " + name + "(")
    nxt = js.find("\n  function ", start + 10)
    section = js.find("\n  // ----------", start + 10)
    ends = [pos for pos in (nxt, section) if pos != -1]
    return js[start:min(ends) if ends else len(js)]


class EditorManifestTest(unittest.TestCase):
    def test_01_manifest_passes_host_validation(self) -> None:
        info = validate_plugin(PLUGIN_DIR, manifest())
        self.assertEqual(info["id"], "org.jiuzhang.editor")
        self.assertIn("stage.center", info["slots"])
        self.assertIn("sidebar.right", info["slots"])
        self.assertIn("question.edit", info["capabilities"])
        self.assertEqual(sorted(info["permissions"]),
                         ["ai:invoke", "assets:read", "assets:write",
                          "questions:read", "questions:write"])

    def test_02_stage_is_singleton_with_priority(self) -> None:
        stage = manifest()["stage"]
        self.assertEqual(stage["region"], "center")
        self.assertEqual(stage["mode"], "takeover")
        self.assertEqual(stage["priority"], 65)
        self.assertIs(stage["singleton"], True)
        self.assertLessEqual(len(stage["title"]), 24)

    def test_03_ai_invoke_is_claimed_for_the_params_channel(self) -> None:
        """阶段 2：辅助栏→画布的唯一合法通道是 ui.params.set，而它是 AI_ONLY 方法。

        清单没写 ai:invoke，宿主只会回 PERMISSION_DENIED——面板的格式切换按钮当场失效。
        """
        self.assertEqual(manifest()["slots"], ["stage.center", "sidebar.right"])
        self.assertIn("ai:invoke", manifest()["permissions"])

    def test_04_bus_subscriptions_match_delivery(self) -> None:
        bus = manifest()["bus"]
        self.assertEqual(sorted(bus["subscribe"]),
                         ["editor.apply_patch", "stage.selection", "system.open_editor",
                          "system.pending_updated", "system.question_updated",
                          "ui.params.changed"])
        self.assertEqual(sorted(bus["publish"]),
                         ["region.dock", "stage.selection", "system.editor_close",
                          "system.return_from_editor"])

    def test_05_commands_keep_the_ai_surface(self) -> None:
        """军令 #20 定下的四条命令 id 与 requires_user 不许被界面改造带偏。"""
        commands = manifest()["contributes"]["commands"]
        self.assertEqual([item["id"] for item in commands], [
            "org.jiuzhang.action.input.open_question",
            "org.jiuzhang.action.process.clean_latex",
            "org.jiuzhang.action.input.save_question",
            "org.jiuzhang.action.process.create_variant",
        ])
        self.assertEqual(sorted(item["id"] for item in commands if item.get("requires_user")),
                         ["org.jiuzhang.action.input.save_question",
                          "org.jiuzhang.action.process.clean_latex",
                          "org.jiuzhang.action.process.create_variant"])

    def test_06_view_selects_are_declared(self) -> None:
        """宿主 applyUiParams 只认清单 ui.controls 里的 select 键，没声明的键直接丢弃。"""
        ui = manifest()["ui"]
        self.assertNotIn("panel", ui,
                         "录题辅助栏不再用 ui.panel=false 表达「别画一遍快捷区」："
                         "那个开关字面上像「关掉辅助栏」，被误读过。宿主改按插件自己"
                         "声明了 sidebar.right 来判断。")
        controls = ui["controls"]
        fmt = [item for item in controls if item.get("key") == "format"]
        self.assertEqual(len(fmt), 1, controls)
        self.assertEqual(fmt[0]["type"], "select")
        self.assertEqual([option["value"] for option in fmt[0]["options"]], ["latex", "boxed"])
        self.assertEqual(fmt[0]["default"], "latex")
        swap = [item for item in controls if item.get("key") == "swap"]
        self.assertEqual(len(swap), 1, controls)
        self.assertEqual([option["value"] for option in swap[0]["options"]], ["false", "true"])
        self.assertEqual(swap[0]["default"], "false")


class EditorThreePaneLayoutTest(unittest.TestCase):
    """军令 #23 阶段 1 的验收面：画布里只有三栏，一道假数据能渲染。"""

    def test_01_canvas_has_exactly_three_panes_and_two_splits(self) -> None:
        canvas = canvas_only(read("index.html"))
        self.assertEqual(canvas.count('class="ed-col '), 3, canvas)
        self.assertEqual(canvas.count('class="ed-split"'), 2, canvas)
        for node_id in ("edCols", "edImageBody", "edSourceBody", "edRenderBody",
                        "edSplitImage", "edSplitSource"):
            self.assertIn(f'id="{node_id}"', canvas, f"缺少三栏节点 {node_id}")

    def test_02_pane_order_is_image_source_render(self) -> None:
        canvas = canvas_only(read("index.html"))
        self.assertLess(canvas.index('id="edPaneImage"'), canvas.index('id="edPaneSource"'),
                        "左栏必须是原图")
        self.assertLess(canvas.index('id="edPaneSource"'), canvas.index('id="edPaneRender"'),
                        "中栏必须是源码、右栏才是渲染")

    def test_03_canvas_carries_no_form_controls(self) -> None:
        """题型 / 难度 / 年级是辅助栏的活；画布内出现下拉框或输入框即判不合格。"""
        canvas = canvas_only(read("index.html"))
        self.assertNotIn("<select", canvas, "画布内禁止出现下拉框")
        self.assertNotIn("<input", canvas, "画布内禁止出现输入框")
        for legacy in ("edType", "edDifficulty", "edGrade", "edAnswer", "edTags", "edSolution",
                       "edOptions", "edStem", "edSave", "edPreview", "edPage", "edSourceCanvas",
                       "edCropBox", "edAiClean", "edClean"):
            self.assertNotIn(f'id="{legacy}"', read("index.html"),
                             f"旧表单 / 旧 A4 节点 {legacy} 已随 v2 撤除")

    def test_04_middle_pane_is_full_source_not_a_slice(self) -> None:
        """中栏是一整个 question…solution 环境块，不是「单栏题干源码」那种局部框。"""
        html = read("index.html")
        js = read("plugin.js")
        self.assertIn('aria-label="LaTeX 源码"', html)
        self.assertNotIn("题干源码", html, "旧版只给题干一栏，v2 中栏必须是全量源码")
        self.assertIn("exam-zh 全量源码", js)
        self.assertIn("area.value = item.source;", js)
        self.assertIn("var parsed = parseExamSource(item.source);", js)

    def test_05_grid_uses_three_columns_with_draggable_widths(self) -> None:
        css = read("plugin.css")
        self.assertIn(
            "max(var(--pane-min), var(--w-image)) var(--split-w) minmax(0, 1fr)", css,
            "中右两栏合并成一只整体容器后，网格只该有三条轨道")
        self.assertIn("--split-w: 6px", css)
        self.assertIn("--pane-min: 28px", css, "拖到极窄缝也不能归零")
        self.assertIn("--void: #fafafa", css, "短栏留白的极淡底色")
        self.assertIn("cursor: col-resize", css)

    def test_05b_widths_are_ratios_so_three_columns_scale_together(self) -> None:
        """画布一窄，三栏必须等比例缩放：像素记账只会把弹性那一栏（渲染）挤没。"""
        css = read("plugin.css")
        self.assertIn("--w-image: 20%", css, "原图栏按比例占画布")
        self.assertIn("--w-source: 34%", css, "源码栏按比例占中右两栏")
        self.assertIn("--pane-render-min: 160px", css, "渲染栏要有防挤压下限")
        self.assertIn("flex: 0 0 max(var(--pane-min), var(--w-source));", css)
        self.assertIn("flex: 1 1 0;", css, "弹性栏必须按 0 基准增长，不许按内容撑")
        self.assertIn("min-width: var(--pane-render-min);", css)
        js = read("plugin.js")
        self.assertIn("var DEFAULT_IMAGE_RATIO = 0.2;", js)
        self.assertIn("var DEFAULT_SOURCE_RATIO = 0.34;", js)
        self.assertIn("function clampRatio(value, fallback)", js)
        apply = fn_body(js, "applyWidths")
        self.assertIn('colsEl.style.setProperty("--w-image", (state.widths.image * 100).toFixed(3) + "%");',
                      apply, "比例要写成百分比，网格才会跟着画布宽度一起缩放")
        self.assertIn('colsEl.style.setProperty("--w-source", (state.widths.source * 100).toFixed(3) + "%");',
                      apply)
        drag = fn_body(js, "bindSplit")
        self.assertIn("delta / metrics.total", drag, "像素位移必须当场换算成比例位移")
        self.assertIn("delta / metrics.workbench", drag)

    def test_06_drag_is_clamped_and_keyboard_usable(self) -> None:
        js = read("plugin.js")
        self.assertIn("var PANE_MIN = 28", js)
        self.assertIn("var SPLIT_W = 6", js)
        self.assertIn("function clampValue(value, min, max)", js)
        self.assertIn("state.widths.image = clampRatio(state.widths.image, DEFAULT_IMAGE_RATIO);", js)
        self.assertIn("state.widths.source = clampRatio(state.widths.source, DEFAULT_SOURCE_RATIO);", js)
        self.assertIn('event.key !== "ArrowLeft" && event.key !== "ArrowRight"', js)
        canvas = canvas_only(read("index.html"))
        self.assertIn('role="separator"', canvas)
        self.assertIn('aria-orientation="vertical"', canvas)

    def test_07_shared_scroll_and_row_alignment(self) -> None:
        js = read("plugin.js")
        self.assertIn("function syncScroll(from)", js)
        self.assertIn("function alignRows()", js)
        self.assertIn('cell.style.minHeight = rowH + "px"', js)
        self.assertIn('node.addEventListener("scroll", function () { syncScroll(node); })', js)
        self.assertIn("if (scrollLock) return;", js, "三栏互相同步，不能再滚出回路")
        # 行高必须量小数：offsetHeight 会把 300.4 截成 300，框框视图里内容高常带小数，
        # 截整之后每一行的源码格都高出一丝，虚线一行一行往下飘（点格式二就歪的真相）。
        self.assertIn("cell.getBoundingClientRect().height", js,
                      "行高要按小数高度量，截整会让三栏虚线逐行错位")
        self.assertNotIn("cell.offsetHeight > rowH", js, "不许再拿截整的 offsetHeight 量行高")

    def test_08_middle_pane_grows_instead_of_scrolling(self) -> None:
        css = read("plugin.css")
        area = css_rule(css, ".ed-src-area")
        self.assertIn("resize: none", area)
        self.assertIn("overflow: hidden", area, "源码区不许出现内部滚动条")
        js = read("plugin.js")
        self.assertIn("function growTextarea(node)", js)
        self.assertIn('node.style.height = Math.max(node.scrollHeight, 60) + "px"', js)

    def test_09_render_pane_follows_content_height(self) -> None:
        """已定决策：渲染不固定 A4。旧几何必须消失，高度只由内容撑出来。"""
        self.assertNotIn("794", read("plugin.css"), "A4 固定页宽已随 v2 撤除")
        self.assertNotIn("1123", read("plugin.css"), "A4 固定页高已随 v2 撤除")
        js = read("plugin.js")
        self.assertNotIn("PAGE_W", js)
        self.assertNotIn("PAGE_H", js)
        self.assertIn("<em>按内容实际高度</em>", read("index.html"))

    def test_10_progress_and_metrics_are_probe_visible(self) -> None:
        js = read("plugin.js")
        for attr in ("data-render-ms", "data-katex", "data-blocks", "data-errors",
                     "data-question-id", "data-row-h", "data-pane-w"):
            self.assertIn(f'"{attr}"', js, f"探针判据缺少度量属性 {attr}")
        self.assertIn('var progressText = "第 " + (state.active + 1) + " / " '
                      '+ state.items.length + " 题"', js)


class EditorTopBarAndAlignmentTest(unittest.TestCase):
    """紧急 UI 回炉（2026-10-31）：顶栏去冗余、三栏顶线齐、中右底边平、左右可互换。"""

    def test_01_no_internal_title_or_status_strip(self) -> None:
        canvas = canvas_only(read("index.html"))
        self.assertNotIn("<h1", canvas, "外层页签已报题名，画布内不许再写一遍大标题")
        self.assertNotIn("ed-bar-brand", canvas)
        self.assertNotIn("ed-status", canvas)
        self.assertNotIn("ed-legend", canvas)

    def test_02_canvas_has_no_toolbar_or_status_strip_at_all(self) -> None:
        """顶栏与底栏整体撤除：画布从上到下只有题目内容，不再有任何工具条。"""
        canvas = canvas_only(read("index.html"))
        self.assertNotIn('class="ed-bar"', canvas, "画布内不许再有顶栏")
        self.assertNotIn("<header", canvas, "画布内不许再有头部容器")
        for gone in ("edFmtLatex", "edFmtBoxed", "edSwapMode", "edSwapInline"):
            self.assertNotIn(f'id="{gone}"', canvas, f"{gone} 已搬进辅助栏，画布内不许留")
        # 状态位仍在，但只给探针与读屏看，视觉上不占像素
        for node_id in ("edProgress", "edFormat", "edDirty", "edSaved", "edMetrics"):
            at = canvas.index(f'id="{node_id}"')
            self.assertIn('class="ed-sr"', canvas[max(0, at - 60):at], f"{node_id} 必须 sr-only")
        # 底栏撤除后，画布内只许剩【← 批次列表】这一枚：它是二屏回首屏的唯一出口，
        # 其余动作全在辅助栏，画布内不许再有第二枚按钮。
        self.assertEqual(canvas.count("<button"), 1, "画布内只许剩【← 批次列表】一枚按钮")
        at = canvas.index("<button")
        self.assertIn('id="edBackList"', canvas[at:at + 160])

    def test_03_three_heads_share_one_pixel_line(self) -> None:
        css = read("plugin.css")
        head = rule_body(css, ".ed-pane-head")
        self.assertIn("height: 32px", head, "三栏头部必须是同一固定高度")
        self.assertIn("flex: 0 0 32px", head)
        self.assertIn("align-items: center", head)
        for selector in (".ed-col-image {", ".ed-workbench {"):
            self.assertIn("border-top: 1px solid var(--line-strong)",
                          rule_body(css, selector), f"{selector.strip()} 缺顶框线")
        self.assertTrue(all("border-top" not in body for body in
                            re.findall(r"\.ed-workbench-panes > \.ed-col\w*\s*\{([^}]*)\}", css)),
                        "中右两栏自己再画顶线就会与整体容器的线错开 1px")

    def test_04_source_and_render_share_one_bottom_border(self) -> None:
        canvas = canvas_only(read("index.html"))
        self.assertIn('id="edWorkbench"', canvas)
        self.assertLess(canvas.index('id="edWorkbench"'), canvas.index('id="edPaneSource"'))
        self.assertLess(canvas.index('id="edPaneSource"'), canvas.index('id="edPaneRender"'))
        css = read("plugin.css")
        bench = rule_body(css, ".ed-workbench {")
        self.assertIn("border-bottom: 1px solid var(--line-strong)", bench,
                      "中右两栏的底框线只能由整体容器画一条")
        self.assertIn("flex: 1 1 0", rule_body(css, ".ed-workbench-panes > .ed-col {"))
        for selector in (".ed-col-source", ".ed-col-render"):
            rules = re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)
            self.assertTrue(rules, f"缺少 {selector} 规则")
            self.assertTrue(all("border-bottom" not in body for body in rules),
                            f"{selector} 自己又画底边，两条线迟早错位")

    def test_05_swap_is_visual_only(self) -> None:
        css = read("plugin.css")
        js = read("plugin.js")
        for marker in ('.ed-cols[data-swap="true"] .ed-workbench-panes > .ed-col-render',
                       '.ed-cols[data-swap="true"] .ed-workbench-panes > .ed-col-source'):
            self.assertIn(marker, css, "互换必须靠 flex order，不许搬 DOM")
        self.assertIn("function applySwap(next, persist)", js)
        self.assertIn("function toggleSwap()", js)
        self.assertIn('colsEl.setAttribute("data-swap"', js)
        self.assertIn("state.swap = Boolean(next);", js)
        # 互换不许重建源码或渲染，值和滚动进度必须留在原节点
        swap = fn_body(js, "toggleSwap")
        self.assertNotIn("renderAll();", swap)
        self.assertNotIn("innerHTML", swap)
        self.assertIn("node.scrollTop = scrolls[position];", swap)
        self.assertIn("focus.setSelectionRange(caret[0], caret[1]);", swap)

    def test_06_swap_state_is_persisted_with_the_layout(self) -> None:
        js = read("plugin.js")
        self.assertIn("swap: state.swap", fn_body(js, "saveLayout"))
        activate = js[js.index('if (message.method === "plugin.activate")'):
                      js.index('if (message.method === "plugin.deactivate")')]
        self.assertIn("applySwap(value.swap, false);", activate)

    def test_07_view_buttons_in_the_panel_are_44px_hit_targets(self) -> None:
        css = read("plugin.css")
        self.assertIn("min-height: 44px", rule_body(css, ".ep-seg-btn {"),
                      "格式一/二搬进辅助栏后仍是 44px 触控面")
        self.assertIn("min-height: 44px", rule_body(css, ".ep-btn {"),
                      "⇄ 互换按钮必须与辅助栏其它按钮同高")
        # 画布旧顶栏的按钮样式必须彻底退场，别留死规则
        for gone in (".ed-seg-btn", ".ed-swap-btn", ".ed-swap-inline"):
            self.assertNotIn(gone, css, f"{gone} 已随顶栏撤除")

    def test_08_split_has_no_button_guard_left(self) -> None:
        js = read("plugin.js")
        bind = fn_body(js, "bindSplit")
        self.assertNotIn(".ed-swap-inline", bind, "画布里的互换钮已撤，拖手不再需要让位逻辑")
        self.assertIn("if (event.target !== node) return;", bind, "按钮上的方向键不许变成拖栏")

    def test_09_panes_lock_height_and_footer_never_wraps(self) -> None:
        """「一会对齐一会不对齐」的根因：批量条换行 + 滚动条出现改变了栅格行高。

        2026-10-31 起批量条整条搬进辅助栏，画布底栏不再存在：
        中右两栏的高度改由父容器钉死（height / max-height / overflow: hidden），
        话术再长也只许在辅助栏里省略，绝不再回来推走中栏的底边。
        """
        css = read("plugin.css")
        col = rule_body(css, ".ed-col {")
        self.assertIn("overflow: hidden", col, "栏本身不许被内容撑高")
        bench = rule_body(css, ".ed-workbench {")
        for required in ("height: 100%", "overflow: hidden", "border-bottom"):
            self.assertIn(required, bench, f".ed-workbench 缺 {required}，中右底边会跳")
        panes = rule_body(css, ".ed-workbench-panes {")
        for required in ("height: 100%", "min-height: 0", "overflow: hidden"):
            self.assertIn(required, panes, f".ed-workbench-panes 缺 {required}")
        body = rule_body(css, ".ed-pane-body {")
        for required in ("scrollbar-gutter: stable", "overflow-y: auto", "min-height: 0"):
            self.assertIn(required, body, f".ed-pane-body 缺 {required}")
        # 画布底栏已整条删除：样式与规则都不许留半截
        for gone in (".ed-foot {", ".ed-batch {", ".ed-pool {", ".ed-foot-actions {"):
            self.assertNotIn(gone, css, f"{gone} 已随画布底栏退场")
        batch = rule_body(css, ".ep-batch {")
        for required in ("white-space: nowrap", "text-overflow: ellipsis", "overflow: hidden"):
            self.assertIn(required, batch, "批量话术只许省略，不许换行")
        # 锁死高度是这次整改的正题：三层的父容器都得写死
        for selector in (".ed-root {", ".ed-cols {", ".ed-workbench {", ".ed-workbench-panes {"):
            block = rule_body(css, selector)
            self.assertIn("height: 100%", block, f"{selector} 没锁死高度，中右两栏会被内容撑歪")
            self.assertIn("overflow: hidden", block, f"{selector} 没有独立滚动区")

    def test_10_ghost_scrollbars_stay_transparent_until_needed(self) -> None:
        css = read("plugin.css")
        # 幽灵样式块追加在文件末尾，用最后一次出现定位，别误读前面同名的布局规则
        for selector in (".ed-pane-body,", ".ep-root,", ".ep-tree {"):
            at = css.rindex(selector)
            block = css[at:css.index("}", at)]
            self.assertIn("scrollbar-color: transparent transparent", block, selector)
        self.assertIn(".ed-pane-body::-webkit-scrollbar-thumb", css)
        self.assertIn("transition: background-color", css, "幽灵滚动条要用过渡淡入淡出")
        self.assertIn(".ed-pane-body.is-scrolling::-webkit-scrollbar-thumb", css,
                      "滚动时滑块才浮出来，靠 .is-scrolling 驱动")
        js = read("plugin.js")
        ghost = fn_body(js, "wireGhost")
        self.assertIn('node.classList.add("is-scrolling")', ghost)
        self.assertIn('node.classList.remove("is-scrolling")', ghost)
        self.assertIn("GHOST_SCROLL_MS", ghost)


class EditorSourceContractTest(unittest.TestCase):
    """《格式宪法》与解析 / 重组口径（阶段 2 复用同一份实现）。"""

    def test_01_only_standard_exam_zh_environments(self) -> None:
        js = read("plugin.js")
        literals = set(re.findall(r"begin\{([a-z]+)\}", js))
        lookup = set(re.findall(r'matchEnv\([A-Za-z]+, "([a-z]+)"\)', js))
        used = literals | lookup
        self.assertTrue(used, "解析器一个环境都不认，判据就空了")
        self.assertTrue(used.issubset(ALLOWED_ENVS),
                        f"出现白名单外的自定义环境：{sorted(used - ALLOWED_ENVS)}")

    def test_02_choice_question_serialization(self) -> None:
        js = read("plugin.js")
        self.assertIn(r'out += "\\begin{question}', js)
        self.assertIn(r'"\\begin{choices}', js)
        self.assertIn(r'"  \\item "', js, "选项行必须是两空格缩进的 \\item")
        self.assertIn(r'\n\\end{choices}\n\\end{question}\n\n"', js,
                      "题干环境与 solution 之间空一行")
        self.assertIn(r'return out + "\\begin{solution}', js)
        self.assertIn(r'"\n\\end{solution}\n"', js)
        self.assertIn('text += "（  ）"', js, "选择题题干末尾要补括号")
        self.assertIn('var head = "答案：" + answerLetters(question)', js)

    def test_03_multi_choice_hint_and_fillin(self) -> None:
        js = read("plugin.js")
        self.assertIn('if (multi && text.indexOf("（多选）") < 0) text += "（多选）"', js)
        self.assertIn('} else if (type === "fill_blank") {', js)
        self.assertIn(r'if (/\\fillin\s*\[[^\]]*\]/.test(result.stem)) {', js)
        self.assertIn('parent.appendChild(el("span", "ed-fillin", hint ? hint[1] : ""))', js)

    def test_04_type_detection_rules(self) -> None:
        js = read("plugin.js")
        detect = js[js.index("function detectType("):js.index("function parseExamSource(")]
        self.assertIn('if (parsed.hasChoices) return parsed.multi ? "multiple_choice" : "single_choice"',
                      detect)
        self.assertIn('if (parsed.hasFillin) return "fill_blank"', detect)
        self.assertIn('return "solution"', detect)
        self.assertIn('result.env = question ? "question" : (problem ? "problem" : "")', js)
        self.assertIn(r'out += "\\begin{problem}', js, "解答题用 problem 环境")

    def test_05_errors_are_reported_not_swallowed(self) -> None:
        js = read("plugin.js")
        for message in ("question 与 problem 环境只能二选一",
                        r'缺少 \\begin{question} 或 \\begin{problem}',
                        "题干为空", "选项不足两项",
                        "solution 开头缺「答案：」", r'缺少 \\begin{solution}',
                        "solution 不应嵌在题干环境内"):
            self.assertIn(message, js, f"解析器缺少可读报错：{message}")
        self.assertIn('block.setAttribute("data-errors", String(parsed.errors.length))', js)

    def test_06_local_cleaner_touches_delimiters_only(self) -> None:
        js = read("plugin.js")
        cleaner = fn_body(js, "cleanExamSource")
        self.assertIn(r"/\\\[([\s\S]*?)\\\]/g", cleaner)
        self.assertIn(r"/\\\(([\s\S]*?)\\\)/g", cleaner)
        self.assertIn('return "$$" + inner.trim() + "$$";', cleaner)
        self.assertIn('return "$" + inner.trim() + "$";', cleaner)
        self.assertIn(r'next.replace(/\r\n/g, "\n")', cleaner)
        # 只动定界符：环境骨架、\fillin 一律不碰，也不联网、不调模型
        for forbidden in ("begin", "fillin", "text.clean_latex", "agent.refine", "hostCall"):
            self.assertNotIn(forbidden, cleaner, f"本地清洗越界动了：{forbidden}")

    def test_07_no_lookbehind_regex(self) -> None:
        """AGENTS §6：后行断言会让旧浏览器整份脚本报语法错。"""
        self.assertNotIn("(?<", read("plugin.js"))


class EditorHostCallTest(unittest.TestCase):
    def test_01_reads_and_layout_drafts_go_through_host(self) -> None:
        js = read("plugin.js")
        self.assertIn('hostCall("bank.get"', js)
        self.assertIn('hostCall("draft.save"', js)
        self.assertIn('hostCall("draft.load"', js)
        self.assertIn('var DRAFT_LAYOUT_KEY = "editor:v2:layout"', js)

    def test_02_writes_go_through_the_host_and_only_two_methods(self) -> None:
        """阶段 2 接写库：题面只许 bank.create / bank.update，删题仍缺席。

        写令牌永远在宿主侧；插件连 bank.delete 都不声明，误删真题就没有通道。
        （asset.upload 是另一条二进制通道：军令 #26 的切图用它落盘配图，
        题面本身仍只走 bank.create / bank.update —— 见 EditorCropMagnifierTest。）
        """
        js = read("plugin.js")
        self.assertIn('var method = updating ? "bank.update" : "bank.create";', js)
        for forbidden in ("bank.delete", "bank.review"):
            self.assertNotIn(forbidden, js, f"本期不得接入 {forbidden}")
        self.assertNotIn("保存入库在阶段 2 接入", js, "阶段 1 的占位拒绝必须退场")

    def test_02b_save_payload_never_carries_id_or_meta_override(self) -> None:
        """id / meta 由底座签发：插件只交正文与元数据，撞到 409 也要如实报给老师。"""
        js = read("plugin.js")
        save = js[js.index("function saveItem("):js.index("  /** 入库后的回显")]
        self.assertIn("payload = { question: doc }", save)
        self.assertIn("if (updating) payload.id = item.savedId;", save)
        self.assertNotIn("payload.sources", save, "带 sources 会把一题多卷的原卷清单整组覆盖掉")
        self.assertIn("LOCAL_INVALID", save, "保存前必须先过最小校验，脏题不许写库")
        self.assertIn('panelMetricsEl.setAttribute("data-variant-id", id || "");', save,
                      "派生变式的新题号要留在状态位上，话术区会被画布回投的选区盖掉")

    def test_03_request_ids_are_host_safe(self) -> None:
        """宿主 BAD_REQUEST_ID 只认 ^[A-Za-z0-9_-]{1,80}$，带点号必被拒发。"""
        js = read("plugin.js")
        lines = [each.strip() for each in js.splitlines() if 'var id = "edv2"' in each]
        self.assertEqual(len(lines), 1, lines)
        self.assertEqual(lines[0], 'var id = "edv2" + requestSeq + "-" + Date.now().toString(36);')
        # Date.now().toString(36) 只产出 [0-9a-z]，拼出来的 id 不含点号
        self.assertRegex("edv21-" + format(1730000000000, "x"), r"^[A-Za-z0-9_-]{1,80}$")

    def test_03b_grade_is_written_twice_because_create_reads_extensions(self) -> None:
        """契约根字段 grade 在底座 create 通道里没人读（bank.py 的 _grade_of 只看 extensions），
        只交根字段会让老师填的年级静默丢失；沿用 v1 的 org.jiuzhang.editor 键双写。"""
        js = read("plugin.js")
        cell = fn_body(js, "questionFromParsed")
        self.assertIn('if (meta.grade) doc.grade = String(meta.grade).trim().slice(0, 20);', cell)
        self.assertIn('extras["org.jiuzhang.editor"] = editorExt;', cell)
        self.assertIn("editorExt.grade = doc.grade;", cell)

    def test_04_plugin_never_touches_token_or_database(self) -> None:
        js = read("plugin.js")
        for needle in ("X-JZO-Token", "local_token", "/api/", "fetch(", "localStorage",
                       "api_key", "sk-", "sessionStorage", "indexedDB", "parent.document"):
            self.assertNotIn(needle, js, f"录题插件不得直接接触：{needle}")

    def test_05_activation_branches_on_slot(self) -> None:
        """同一份 plugin.js 会被画布帧与右栏帧各加载一次，必须按插槽分支。"""
        js = read("plugin.js")
        self.assertIn('state.slot = (message.payload && message.payload.slot) || "stage.center"', js)
        self.assertIn('if (state.slot !== "stage.center")', js)
        self.assertIn("root.hidden = false;", js)
        self.assertIn('id="epRoot"', read("index.html"), "右栏实例需要自己的根节点")

    def test_06_offline_and_no_remote_assets(self) -> None:
        for name in ("index.html", "plugin.css", "plugin.js"):
            source = read(name)
            self.assertNotIn("http://", source, f"{name} 不得引用远程资源")
            self.assertNotIn("https://", source, f"{name} 不得引用远程资源")
            self.assertNotIn("@import", source, f"{name} 不得远程导入样式")
        self.assertIn("/static/vendor/katex/katex.min.js", read("index.html"), "公式只走本地 KaTeX")

    def test_07_image_refs_stay_on_host_paths(self) -> None:
        js = read("plugin.js")
        self.assertIn("function safeAssetUri", js)
        for allowed in ('uri.indexOf("/static/uploads/") === 0', 'uri.indexOf("asset://") === 0'):
            self.assertIn(allowed, js)
        self.assertNotIn("data:image", js[:js.index("function safeAssetUri")])
        # 认不出的地址只当普通文本，绝不变成 <img src>
        self.assertIn("if (!path) {", js)
        self.assertIn("document.createTextNode(raw", js)


class EditorPanelTest(unittest.TestCase):
    """军令 #23 阶段 2–3 的验收面：辅助栏只有元数据表单 + AI 帮改 + 审核动作。"""

    def test_01_panel_carries_view_controls_status_metadata_and_actions(self) -> None:
        panel = panel_only(read("index.html"))
        for node_id in ("epFmtLatex", "epFmtBoxed", "epSwap", "epViewNote",
                        "epProgress", "epStatus", "epConfidence",
                        "epType", "epDifficulty", "epGrade",
                        "epPaper", "epQuestionNo", "epYear", "epExamType", "epTags",
                        "epMounted", "epTopicTree",
                        "epAiField", "epAiAsk", "epAiSend", "epAiClean",
                        "epAiState", "epAiNote", "epAiPreview", "epAiApply", "epAiDiscard",
                        "epApprove", "epStash", "epDelete",
                        "epDupModal", "epDupBack", "epDupForce",
                        "epDelModal", "epDelCancel", "epDelOk",
                        "epMessage", "epMetrics"):
            self.assertIn(f'id="{node_id}"', panel, f"辅助栏缺少 {node_id}")
        canvas = canvas_only(read("index.html"))
        self.assertNotIn("epFmtLatex", canvas, "视图切换只活在辅助栏，画布内不许重开一套")

    def test_02_panel_never_carries_source_or_preview(self) -> None:
        """铁律：源码只在中栏、渲染只在中栏右邻。辅助栏唯一的 textarea 是给 AI 写指令的。"""
        panel = panel_only(read("index.html"))
        self.assertEqual(panel.count("<textarea"), 1, "辅助栏只许出现指令框这一个 textarea")
        at = panel.index("<textarea")
        tag = panel[at:panel.index(">", at)]
        self.assertIn('id="epAiAsk"', tag, "唯一的 textarea 必须是 AI 指令框")
        for forbidden in ("edSourceBody", "edRenderBody", "edQBlock", "katex",
                          "ed-src-area", "ed-box-area"):
            self.assertNotIn(forbidden, panel, f"辅助栏越界放了 {forbidden}")

    def test_03_review_actions_are_the_three_real_buttons(self) -> None:
        """军令 #24：审核动作真接上中转站了——就三颗钮，且都必须真的绑上点击。"""
        panel = panel_only(read("index.html"))
        for node_id in ("epApprove", "epStash", "epDelete"):
            self.assertIn(f'id="{node_id}"', panel, f"缺少审核动作 {node_id}")
        for legacy in ("epSave", "epVariant", "epPass", "epReject", "epSkip"):
            self.assertNotIn(f'id="{legacy}"', panel,
                             f"{legacy} 已随审核台接管退场")
        js = read("plugin.js")
        activation = fn_body(js, "activatePanel")
        for bound in ('panelApproveEl.addEventListener("click"',
                      'panelStashEl.addEventListener("click", onStash)',
                      'panelDeleteEl.addEventListener("click", onDelete)'):
            self.assertIn(bound, activation, f"辅助栏没绑上 {bound}")

    def test_04_confidence_is_marked_as_placeholder(self) -> None:
        """置信度来自识别引擎，本期只有假数据：文案必须自己承认是占位。"""
        panel = panel_only(read("index.html"))
        self.assertIn("置信度 —（假数据占位）", panel)
        self.assertIn('data-confidence=""', panel)

    def test_05_metadata_is_ai_prefilled_but_the_human_wins(self) -> None:
        js = read("plugin.js")
        note = js[js.index("function renderTypeNote("):js.index("  function applySelection(")]
        self.assertIn('panelTypeNoteEl.setAttribute("data-from", "ai")', note)
        self.assertIn('panelTypeNoteEl.setAttribute("data-from", "manual")', note)
        self.assertIn("保存以你的选择为准", note, "AI 预填的题型必须让人工改动压过它")
        self.assertIn('panel.selection.dirty = true;', js[js.index("function onFormChange("):
                                                              js.index("  function renderTypeNote(")])

    def test_06_view_controls_live_in_the_panel_and_sync_the_params_channel(self) -> None:
        """面板拿不到画布 DOM：格式与互换只经宿主 ui.params.set → ui.params.changed 对账。"""
        js = read("plugin.js")
        choose = js[js.index("  function chooseFormatFromPanel("):
                    js.index("  // ---------- 源码 / 渲染左右互换")]
        self.assertIn("setFormatButtons(next);", choose)
        self.assertIn('hostCall("ui.params.set"', choose)
        self.assertIn("params: { format: next }", choose)
        self.assertIn("plugin_id: PLUGIN_ID", choose)
        swap = js[js.index("  function toggleSwapFromPanel("):js.index("  /**\n   * 互换的只有视觉位置")]
        self.assertIn('params: { swap: next ? "true" : "false" }', swap)
        self.assertIn("setSwapButton(next);", swap)
        # 画布收到广播才真正切视图/换位
        params = fn_body(js, "onUiParams")
        self.assertIn("setFormat(values.format)", params)
        self.assertIn("applySwap(wantSwap, true)", params)
        self.assertIn("publishSelection();", params)
        # 面板帧只翻按钮，不直接改画布
        self.assertIn("setSwapButton(values.swap === true", params)
        # 旧的面板帧切换通道已退场，不许留两套事实来源
        self.assertNotIn("function switchFormat(", js)
        activate = js[js.index("  function activatePanel("):js.index("  // ---------- 协议 ----------")]
        self.assertIn('chooseFormatFromPanel(node.getAttribute("data-format"))', activate)
        self.assertIn('panelSwapEl.addEventListener("click", toggleSwapFromPanel)', activate)

    def test_07_touch_targets_meet_the_a11y_floor(self) -> None:
        """AGENTS §6：触控目标不小于 44px；树行与小圆钮（热区补齐）都得达标。"""
        css = read("plugin.css")
        for selector in (".ep-input", ".ep-select", ".ep-topic-expander"):
            self.assertIn("min-height: 44px", rule_body(css, selector),
                          f"{selector} 没有 44px 触控高度")
        chip_x = rule_body(css, ".ep-chip-x")
        self.assertIn("position: relative", chip_x)
        self.assertIn(".ep-chip-x::after", css, "小圆钮要用伪元素把热区补到 44px")
        self.assertIn("inset: -6px -8px", rule_body(css, ".ep-chip-x::after"))

    def test_08_save_is_locally_validated_before_the_bank_sees_it(self) -> None:
        """保存前的最小校验要在插件里做完：脏源码不配去敲宿主的写库通道。"""
        js = read("plugin.js")
        check = js[js.index("function validateForSave("):js.index("  function saveItem(")]
        for required in ("parsed.errors", "doc.stem", "choice_keys", "STEM_MAX",
                         "meta.year", "TOPIC_LIMIT"):
            self.assertIn(required, check, f"保存前校验缺少 {required}")
        self.assertIn("单选题答案只能有一个字母", check)
        self.assertIn("多选题答案至少两个字母", check)
        self.assertIn("return problems", check)

    def test_09_topics_are_loaded_lazily_and_mount_is_capped(self) -> None:
        js = read("plugin.js")
        self.assertIn('hostCall("bank.topics", { parent_id: node.id })', js)
        self.assertIn('hostCall("bank.topics", {})', js)
        self.assertIn("var TOPIC_LIMIT = 8", js)
        node = js[js.index("  function topicNode("):js.index("  function loadChildren(")]
        self.assertIn("if (!open && !kids.childNodes.length) loadChildren(node, kids, depth + 1);",
                      node, "展开节点才取下一层，别一上来把整棵大纲拖进右栏")
        self.assertIn("if (!node.has_children) expander.disabled = true;", node,
                      "没有下级的节点不该给假展开箭头")

    def test_10_meta_and_receipts_are_host_held_drafts(self) -> None:
        """插件侧绝不出现浏览器存储：元数据草稿与入库回执都交宿主代持。"""
        js = read("plugin.js")
        self.assertIn('var DRAFT_META_KEY = "editor:v2:meta"', js)
        self.assertIn('var DRAFT_RECEIPT_KEY = "editor:v2:receipts"', js)
        self.assertIn('hostCall("draft.save", { key: DRAFT_META_KEY, value: panel.meta })', js)
        self.assertIn('hostCall("draft.load", { key: DRAFT_RECEIPT_KEY })', js)
        self.assertNotIn("localStorage", js)


    def test_11_panel_rebuilds_the_form_from_the_shared_draft(self) -> None:
        """画布帧与面板帧同时挂载时，stage.selection 可能早于面板就绪——不能把右栏晾成空壳。"""
        js = read("plugin.js")
        self.assertIn("  function applyDraftSelection(value) {", js)
        self.assertIn("if (panel.selection) return;", fn_body(js, "applyDraftSelection"),
                      "已经收到活选区后，不许用旧草稿把它盖回去")
        worklist = fn_body(js, "worklistValue")
        self.assertIn("defaults: defaultsOf(item)", worklist, "草稿要带上元数据默认值")
        self.assertIn("confidence:", worklist)
        self.assertIn("var PANEL_DRAFT_RETRY_MS = 900;", js)
        activate = js[js.index('if (message.method === "plugin.activate")'):
                      js.index('if (message.method === "plugin.deactivate")')]
        self.assertIn("saveWorklist();\n        publishSelection();", activate,
                      "画布挂载后立刻回写草稿，面板才可能读到")

    def test_12_draft_keys_are_literal_and_host_held(self) -> None:
        """草稿键必须是写死的字符串：宿主按 plugin.id + key 分箱，拼错了就是另一只箱子。"""
        js = read("plugin.js")
        for key in ("editor:v2:layout", "editor:v2:worklist", "editor:v2:meta",
                    "editor:v2:receipts"):
            self.assertIn(f'"{key}"', js, f"缺少宿主代持草稿键 {key}")

    def test_13_canvas_echoes_the_id_from_the_claimed_receipt(self) -> None:
        """画布与面板是两只帧：面板那句「已入库」画布收不到，认领回执后必须由画布自己回显；
        而宿主先广播事件、后把应答送回面板，回执晚一跳，读不到就得重试。"""
        js = read("plugin.js")
        cell = fn_body(js, "consumeReceipts")
        self.assertIn("showSaved(id, matched.action === \"update\");", cell,
                      "画布顶栏的已入库标记只能来自回执认领，不然老师看不到题号")
        self.assertIn("setTimeout(function () { consumeReceipts(payload, tries + 1); }", cell)
        self.assertIn("var RECEIPT_RETRY_MS = 350;", js)
        self.assertIn("var RECEIPT_RETRY_MAX = 4;", js)


class EditorAiAssistTest(unittest.TestCase):
    """军令 #23 阶段 3（AI 帮改档 1）：预览归面板，替换归老师那一下点击。

    钉五条：可改字段只有题干段/解析段、采用门只认 ready、目标题靠 id 里的键回认、
    空值/失败一律不许动源码、上下文不外泄私有数据与令牌。
    """

    def test_01_apply_ships_disabled_and_gated_on_ready(self) -> None:
        panel = panel_only(read("index.html"))
        at = panel.index('id="epAiApply"')
        tag = panel[at - 200:at + 200]
        self.assertIn("disabled", tag, "【采用】出厂必须按不动")
        self.assertIn('aria-disabled="true"', tag)
        js = read("plugin.js")
        self.assertIn('setEpEnabled(panelAiApplyEl, panel.ai.state === "ready"',
                      fn_body(js, "renderAi"),
                      "只有「待老师裁决」才允许采用")

    def test_02_only_stem_and_solution_are_editable(self) -> None:
        """选项与「答案：」行由格式宪法锁死：光标落在这两处，AI 就不许有目标字段。"""
        js = read("plugin.js")
        ranges = fn_body(js, "fieldRanges")
        self.assertIn('envSpan(text, "choices", stem.bodyAt)', ranges, "题干段止于 choices")
        self.assertIn("/^[ \\t]*答案\\s*[:：][^\\n]*\\n?/", ranges, "解析段跳过「答案：」首行")
        caret = fn_body(js, "fieldAtOffset")
        self.assertIn('return "";', caret, "段外一律判不出字段，不许fallback 到整题")
        send = fn_body(js, "onAiSend")
        self.assertIn("!caret.field", send, "没定位到可改字段就不许发请求")

    def test_03_the_target_question_travels_inside_the_patch_id(self) -> None:
        """宿主只把 {id, field, value} 广播给各帧，目标题只能编进 id 里回认。"""
        js = read("plugin.js")
        self.assertIn('("ai1-" + String(key == null ? "" : key).replace(/[^A-Za-z0-9_-]/g, "-")).slice(0, 80)',
                      fn_body(js, "patchIdFor"), "id 必须宿主安全（不含点号）且不超 80")
        canvas = fn_body(js, "applyAiPatch")
        self.assertIn("AI 回填的目标不是当前题，源码没动", canvas)
        panel_send = fn_body(js, "onAiApply")
        self.assertIn("item.key !== panel.ai.key", panel_send,
                      "面板换题后不许把上一题的改写发出去")

    def test_04_empty_or_failed_replies_never_touch_the_source(self) -> None:
        js = read("plugin.js")
        send = fn_body(js, "onAiSend")
        self.assertIn("!value", send, "模型回空串要判失败")
        self.assertIn("画布源码没动", send)
        self.assertIn("多半是回显", send, "宿主摊平时丢了 mock 标记：逐字相同要照实说是回显")
        canvas = fn_body(js, "applyAiPatch")
        self.assertIn("AI 回填缺字段或内容为空，源码没动", canvas)
        self.assertIn("return false", canvas)

    def test_05_the_model_gets_the_visible_fields_only(self) -> None:
        """上桥的只有 type/difficulty/stem/options/answer/solution——与底座 build_refine_user_message 同口径。"""
        js = read("plugin.js")
        ctx = fn_body(js, "refineContext")
        for key in ('type:', 'difficulty:', 'stem:', 'answer:', 'solution:', 'options:'):
            self.assertIn(key, ctx, f"上下文缺 {key}")
        for forbidden in ("extensions", "saved_id", "question_id", "token", "paper_title"):
            self.assertNotIn(forbidden, ctx, f"{forbidden} 不许进模型上下文")
        self.assertNotIn("innerHTML", fn_body(js, "renderAi"), "预览只走 textContent")

    def test_06_slow_models_get_the_hosts_budget_not_twenty_seconds(self) -> None:
        """宿主给模型 60s（stage.js 的 AGENT_TIMEOUT_MS）；插件按 20s 等会把慢回答误报成失败。"""
        js = read("plugin.js")
        self.assertIn("var AI_REQUEST_TIMEOUT_MS = 65000;", js)
        self.assertIn("}, AI_REQUEST_TIMEOUT_MS).then(function (result) {", fn_body(js, "onAiSend"))
        relay = js[js.index("function cleanViaHost"):]
        self.assertNotIn("AI_REQUEST_TIMEOUT_MS", relay.split("\n  }\n")[0],
                         "规则清洗不经过模型，按普通额度等就够")
        stage = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        self.assertIn("var AGENT_TIMEOUT_MS = 60000;", stage)

    def test_07_the_panel_never_renders_the_patch_itself(self) -> None:
        """回填只有画布执行：面板收到自己发出的广播必须静默，否则一次采用改两遍。"""
        js = read("plugin.js")
        at = js.index('if (message.event === "editor.apply_patch") {')
        block = js[at:js.index("return;", at) + len("return;")]
        self.assertIn('state.slot === "stage.center"', block)

    def test_08_ai_buttons_are_bound_and_the_caret_publishes(self) -> None:
        js = read("plugin.js")
        activation = fn_body(js, "activatePanel")
        for bound in ('panelAiSendEl.addEventListener("click", onAiSend)',
                      'panelAiCleanEl.addEventListener("click", cleanViaHost)',
                      'panelAiApplyEl.addEventListener("click", onAiApply)',
                      'panelAiAskEl.addEventListener("input", renderAi)'):
            self.assertIn(bound, activation, f"辅助栏没绑上 {bound}")
        cells = js[js.index("  function renderSourceCell("):js.index("  function renderBoxedCell(")]
        self.assertEqual(cells.count('publishSelectionSoon'), 2,
                         "格式一的源码框与格式二的题干/解析框都要把光标上桥，面板才知道改哪段")


class EditorBoxedFormatTest(unittest.TestCase):
    """格式二（框框视图）：只能改内容改不到环境，改完必须自动重组格式一。"""

    def test_01_environment_names_are_locked_text(self) -> None:
        js = read("plugin.js")
        cell = js[js.index("  function boxFieldCell("):js.index("  function renderBoxedCell(")]
        self.assertIn('head.appendChild(el("span", "ed-box-env", envName));', cell,
                      "环境名必须是纯文本标签，一旦做成输入框就等于允许自定义环境")
        self.assertIn("只能改内容", cell)
        self.assertNotIn('data-field="env"', js, "格式二不得暴露可编辑的环境字段")

    def test_02_box_edit_rebuilds_format_one(self) -> None:
        box = fn_body(read("plugin.js"), "onBoxInput")
        for field in ("stem", "choice", "answer", "analysis"):
            self.assertIn(f'field === "{field}"', box, f"框框视图缺少 {field} 的写回分支")
        self.assertIn("buildExamSource(boxesToQuestion(", box,
                      "改完框必须重组整段格式一源码，两栏不能各写各的")

    def test_03_unboxable_source_is_refused_with_reasons(self) -> None:
        js = read("plugin.js")
        reason = js[js.index("  function boxedBlockReason("):js.index("  function boxFieldCell(")]
        for text in ("环境外的内容", "拆不出框", "答案与解析没有归属", "选项不足两项"):
            self.assertIn(text, reason, f"拆框拒绝话术缺少 {text}")
        self.assertIn('return "";', reason)

    def test_04_both_formats_share_one_source_of_truth(self) -> None:
        """两种视图只是同一份 item.source 的两种编辑面，切格式不许改内容。"""
        js = read("plugin.js")
        self.assertIn('node.setAttribute("data-field", field);', js)
        self.assertIn("item.source = next;", fn_body(js, "onBoxInput"),
                      "框框视图的产物必须回写同一份整段源码")
        set_format = fn_body(js, "setFormat")
        self.assertIn("renderAll();", set_format)
        self.assertNotIn("item.source =", set_format, "切换格式不许动源码内容")


class EditorBatchTest(unittest.TestCase):
    """军令 #24 审核台：首屏批次列表 + 二屏三栏审核。

    2026-10-31 整改：批量条整条从画布底部搬进右侧辅助栏的元数据操作区。
    画布底栏（.ed-foot）一换行就把中右两栏的底边挤歪，还占着老师最宝贵的屏幕下沿。

    2026-11-01 再整改：待入库池换成「中转站待审核池」，批量提交整体退场——
    审核动作改成【存入主库】【存为待办】【彻底删除】三颗钮，住在辅助栏；
    画布首屏改成批次列表，二屏抬头才写当前批次号。
    """

    def test_01_batch_bar_lives_in_the_canvas_and_the_ledger_in_the_panel(self) -> None:
        canvas = canvas_only(read("index.html"))
        panel = panel_only(read("index.html"))
        for node_id in ("edBatches", "edBatchList", "edBatchBar", "edBatchNo",
                        "edBatchStat", "edBackList"):
            self.assertIn(f'id="{node_id}"', canvas, f"画布首屏缺少 {node_id}")
        for node_id in ("edPool", "edBatchNote"):
            self.assertIn(f'id="{node_id}"', panel, f"辅助栏台账缺少 {node_id}")
            self.assertNotIn(f'id="{node_id}"', canvas, f"{node_id} 属于辅助栏，不许留在画布")
        # 画布底栏连同它的容器一起删干净（注释里可以留说明，不许留元素）
        self.assertNotIn('class="ed-foot"', canvas, "画布底栏已整条删除")
        # 批量条不许把表单控件带进画布（<button> 不算表单输入控件）
        self.assertNotIn("<select", canvas)
        self.assertNotIn("<input", canvas)
        # 批量提交整体退场：三颗审核钮才是唯一出口
        for gone in ("edSaveAll", "edPoolStash"):
            self.assertNotIn(f'id="{gone}"', read("index.html"),
                             f"{gone} 已随批量提交退场")

    def test_02_the_three_review_buttons_are_the_only_write_paths(self) -> None:
        """审核台只有三条出路：存主库、存待办、彻底删除。批量提交的口径整体撤除。"""
        js = read("plugin.js")
        for gone in ("saveAllDirty", "panelSaveAllDirty", "panelWorklistItems",
                     "patchPanelPool", "dirtyList"):
            self.assertNotIn("function " + gone + "(", js, f"{gone} 已随批量提交退场")
        self.assertIn('hostCall("pending.approve"', js)
        self.assertIn('hostCall("pending.save_draft"', js)
        self.assertIn('hostCall("pending.delete"', js)

    def test_02b_stash_updates_the_same_pending_row_in_place(self) -> None:
        """存为待办带 pending_id：池子里不许多出一道重影，题号也不会飘。"""
        js = read("plugin.js")
        stash = fn_body(js, "stashOne")
        self.assertIn("pending_id: item.pendingId || \"\"", stash)
        self.assertIn('hostCall("pending.save_draft", payload)', stash)
        self.assertIn("if (!item.pendingId && result", stash,
                      "只有新题才认回池子编号")

    def test_02c_stash_keeps_images_extensions_and_origin(self) -> None:
        """面板侧重建题目时，图片、扩展与原卷字段一件都不许丢——更新一题就抹掉一样等于毁题。"""
        js = read("plugin.js")
        worklist = fn_body(js, "worklistValue")
        for field in ("images", "extensions", "origin"):
            self.assertIn(field, worklist, f"画布写草稿时必须带 {field}")
        self.assertIn("var SOURCE_MAX = 60000;", js,
                      "源码不许在两帧之间被砍到 20000 字，长解析的尾巴会丢")
        selection = fn_body(js, "selectionPayload")
        for field in ("images", "extensions", "origin"):
            self.assertIn(field, selection, f"选区必须带 {field}")

    def test_03_review_writes_are_issued_one_at_a_time(self) -> None:
        """宿主对写库有频率闸门：审核动作必须串行，不许并发。"""
        js = read("plugin.js")
        for name in ("onApprove", "onStash", "onDeleteConfirm"):
            body = fn_body(js, name)
            self.assertNotIn("Promise.all(", body, f"{name} 不许并发写库")
        self.assertIn("if (panel.saving) return;", fn_body(js, "onApprove"),
                      "重复点击不许并发二轮")

    def test_04_review_reuses_the_same_bank_write_methods(self) -> None:
        js = read("plugin.js")
        self.assertEqual(js.count('var method = updating ? "bank.update" : "bank.create";'), 1,
                         "另开写库通道就是第二套事实来源")
        for forbidden in ("bank.delete", "bank.review"):
            self.assertNotIn(forbidden, js)

    def test_05_scroll_follows_the_row_at_the_top(self) -> None:
        js = read("plugin.js")
        self.assertIn("function activeFromScroll(top)", js)
        self.assertIn("function followActive(from)", js)
        follow = fn_body(js, "followActive")
        self.assertIn("if (!state.items.length || editingRowIndex() >= 0) return;", follow,
                      "老师的手还停在某题的框里，滚动就不许把当前题抢走")
        self.assertIn("if (next === state.active) return;", follow)
        self.assertIn("publishSelectionSoon();", follow, "跟题必须把选区一起推给辅助栏")
        self.assertIn("followActive(from);", fn_body(js, "syncScroll"))

    def test_06_active_row_is_shown_by_more_than_color(self) -> None:
        js = read("plugin.js")
        css = read("plugin.css")
        self.assertIn('cell.classList.toggle("is-active", index === state.active);',
                      fn_body(js, "markActiveRow"))
        self.assertIn('node.setAttribute("aria-current", on ? "true" : "false");',
                      fn_body(js, "markActiveRow"))
        self.assertIn("box-shadow: inset 3px 0 0 var(--accent)",
                      css_rule(css, ".ed-q-block.is-active"))

    def test_07_sync_active_bits_does_not_fake_render_metrics(self) -> None:
        """滚动换题时不许把上一次的 render-ms 冒充成新渲染，也不许写 0。"""
        bits = fn_body(read("plugin.js"), "syncActiveBits")
        self.assertIn('var elapsed = Number(metricsEl && metricsEl.getAttribute("data-render-ms"));', bits)
        self.assertIn("updateStatusbar(isNaN(elapsed) ? 0 : elapsed, isNaN(rowH) ? 0 : rowH);", bits)

    def test_08_left_column_jumps_are_keyboard_reachable(self) -> None:
        js = read("plugin.js")
        cell = fn_body(js, "renderImageCell")
        self.assertIn('var jump = el("button", "ed-img-jump"', cell)
        self.assertIn('jump.type = "button";', cell)
        self.assertIn('jump.addEventListener("click", function () { jumpTo(index); });', cell)
        self.assertIn('jump.setAttribute("aria-label", "跳到第 "', cell)
        self.assertIn("min-height: 44px", css_rule(read("plugin.css"), ".ed-img-jump"))
        jump = fn_body(js, "jumpTo")
        self.assertIn("body.scrollTop = Math.max(cell.offsetTop - 12, 0);", jump, "跳转要把三栏一起滚过去")
        self.assertIn("clampValue(Number(index) || 0, 0, Math.max(state.items.length - 1, 0))", jump)

    def test_09_the_pool_ledger_is_read_only_now(self) -> None:
        """池子那一行只报数：审核动作在上面那三颗钮里，台账不许自己发令。"""
        js = read("plugin.js")
        html = read("index.html")
        render = fn_body(js, "renderPool")
        for attr in ("data-new", "data-stored", "data-dirty", "data-errored"):
            self.assertIn(f'poolEl.setAttribute("{attr}"', render)
        self.assertNotIn("bank.create", render, "台账不许碰写库通道")
        self.assertNotIn("pending.", render, "台账不许碰中转站通道")
        self.assertIn('id="edPool"', html)

    def test_10_review_buttons_keep_the_a11y_floor(self) -> None:
        js = fn_body(read("plugin.js"), "approveBusy")
        self.assertIn("panelApproveEl.disabled = busy;", js)
        self.assertIn('panelApproveEl.setAttribute("aria-busy", busy ? "true" : "false");', js)
        self.assertIn('panelApproveEl.setAttribute("aria-disabled", busy ? "true" : "false");', js)
        css = read("plugin.css")
        self.assertIn("min-height: 44px", css_rule(css, ".ep-btn"))
        self.assertIn('.ep-batch[data-batch="partial"]', css)
        self.assertIn(".ep-btn[disabled]", css)
        note = fn_body(read("plugin.js"), "batchNote")
        self.assertIn("batchNoteEl.textContent = text;", note, "话术只走 textContent，不许拼 DOM")

    def test_11_pool_refreshes_with_every_render(self) -> None:
        js = read("plugin.js")
        status = fn_body(js, "updateStatusbar")
        self.assertIn("markActiveRow();", status)
        self.assertIn("renderPool();", status)

    def test_12_rebuild_keeps_the_reading_position(self) -> None:
        """批量界面靠滚动定位：整屏重建不许把老师的阅读位置抹回顶部。"""
        js = read("plugin.js")
        render = fn_body(js, "renderAll")
        self.assertIn("var scrolls = [imageBodyEl, sourceBodyEl, renderBodyEl].map", render)
        self.assertLess(render.index("var scrolls ="), render.index("imageBodyEl.textContent = \"\";"),
                        "清空之前必须先把三条滚动线抄下来")
        self.assertIn("node.scrollTop = scrolls[position] || 0;", render)
        self.assertIn("if (scrollRestore) return;", fn_body(js, "syncScroll"),
                      "回填滚动时不许再触发一次跟题")

    def test_13_selection_echo_does_not_clobber_the_ai_note(self) -> None:
        """采用后的「保存才入库」不能被选区回显盖掉，否则老师会以为已经入库了。"""
        js = read("plugin.js")
        apply = fn_body(js, "applySelection")
        self.assertIn('} else if (panel.ai.state === "ready" && panel.ai.key === sel.key) {', apply)
        self.assertLess(apply.index('panel.ai.state === "ready" && panel.ai.key === sel.key'),
                        apply.index('panelSay("当前第 "'),
                        "回显话术必须排在 AI 让位分支之后")

    def test_14_three_panes_are_real_scrollers(self) -> None:
        """三栏得自己带滚动条：iframe 被内容撑高的话，跳转与跟题全是死代码（探针 jump_geo 全 0 那次）。"""
        css = read("plugin.css")
        cols = css_rule(css, ".ed-cols")
        self.assertIn("grid-template-rows: minmax(0, 1fr)", cols,
                      "网格行不锁高度的话会被最高的那栏撑到几千像素")
        body = css_rule(css, ".ed-pane-body")
        self.assertIn("position: relative", body, "不站住定位父，cell.offsetTop 就是整篇文档的坐标")
        self.assertIn("min-height: 0", body)
        self.assertIn("overflow-y: auto", body)

    def test_15_batch_chain_hands_the_ledger_to_the_next_leg(self) -> None:
        """串行链每一棒都要把台账交回去，不然第二题起 acc 是 undefined，整批提交假死。"""
        js = read("plugin.js")
        leave = fn_body(js, "stashBeforeLeave")
        self.assertIn("return targets.reduce(function (chain, target) {", leave)
        self.assertNotIn("Promise.all(", leave)


class EditorReviewDeskTest(unittest.TestCase):
    """军令 #24 审核台：首屏批次列表、二屏三栏审核、防呆自动存回与查重弹窗。

    真机流程由 ``tools/editor_probe.py`` 取证；这里钉住可静态判定的部分。
    """

    def test_01_first_screen_is_the_batch_list(self) -> None:
        """首屏铺满画布就是批次列表：三栏在列表模式下必须收起。"""
        js = read("plugin.js")
        self.assertIn('mode: "list",', js)
        set_mode = fn_body(js, "setMode")
        self.assertIn('if (batchesEl) batchesEl.hidden = state.mode !== "list";', set_mode)
        self.assertIn('if (batchBarEl) batchBarEl.hidden = state.mode !== "review";', set_mode)
        self.assertIn('if (colsEl) colsEl.hidden = state.mode !== "review";', set_mode)
        activate = js[js.index('if (message.method === "plugin.activate")'):
                      js.index('if (message.method === "plugin.deactivate")')]
        self.assertIn('setMode("list");', activate, "画布挂载后先落在批次列表上")

    def test_02_batch_row_format_matches_the_order(self) -> None:
        """左「2024-10-31-星期四-15:30-批次编号 #B-001」，右「未审：n / N」数字绿色。"""
        js = read("plugin.js")
        stamp = fn_body(js, "batchStamp")
        self.assertIn('var WEEKDAYS = "日一二三四五六";', js)
        self.assertIn('"-星期" + WEEKDAYS.charAt(day.getDay())', stamp)
        rows = fn_body(js, "renderBatchList")
        self.assertIn('batchStamp(card.created_at) + "-批次编号 #" + card.batch_id', rows)
        self.assertIn('el("span", "ed-batch-label", "未审：")', rows)
        self.assertIn('el("span", "ed-batch-num", String(pending))', rows)
        self.assertIn('el("span", "ed-batch-num", String(total))', rows)
        css = read("plugin.css")
        self.assertIn("color: var(--accent)", rule_body(css, ".ed-batch-num"),
                      "未审数字必须是绿色")
        self.assertIn("justify-content: space-between", rule_body(css, ".ed-batch-row"),
                      "两端对齐：左边时间、右边计数")
        self.assertIn("text-align: left", rule_body(css, ".ed-batch-row"))

    def test_03_a_finished_batch_is_grey_sunk_and_unclickable(self) -> None:
        """未审归零的批次：变灰、沉到最底、不可点——只能看。"""
        js = read("plugin.js")
        rows = fn_body(js, "renderBatchList")
        self.assertIn("var leftDone = Number(left.pending_count) === 0 ? 1 : 0;", rows)
        self.assertIn("if (leftDone !== rightDone) return leftDone - rightDone;", rows,
                      "审完的批次必须沉到列表最底")
        self.assertIn("row.disabled = true;", rows)
        self.assertIn('row.setAttribute("aria-disabled", "true");', rows)
        self.assertIn('row.setAttribute("data-done", done ? "true" : "false");', rows)
        # 未审为 0 的行不许挂点击
        self.assertIn('row.addEventListener("click", function () { openBatch(card.batch_id); });', rows)
        css = read("plugin.css")
        done = rule_body(css, '.ed-batch-row[data-done="true"]')
        self.assertIn("opacity:", done)
        self.assertIn("cursor: default", done)

    def test_04_the_batch_bar_names_the_current_batch(self) -> None:
        js = read("plugin.js")
        bar = fn_body(js, "renderBatchBar")
        self.assertIn('batchNoEl.textContent = "批次 #" + (state.batchId || "—");', bar)
        self.assertIn("未审 ", bar)
        html = read("index.html")
        self.assertIn('id="edBatchNo"', html)

    def test_05_clicking_a_row_opens_the_three_pane_review(self) -> None:
        js = read("plugin.js")
        open_batch = fn_body(js, "openBatch")
        self.assertIn('hostCall("pending.list", { batch_id: id })', open_batch)
        self.assertIn('item.pendingId = String((row && row.id) || "");', open_batch)
        self.assertIn('setMode("review");', open_batch)
        self.assertIn("publishSelection();", open_batch)

    def test_06_idle_three_minutes_stashes_silently_into_the_pool(self) -> None:
        """三分钟没人碰 → 静默存回待审核池，只在底部日志留一行灰字，绝不弹窗。"""
        js = read("plugin.js")
        self.assertIn("var IDLE_MS = 3 * 60 * 1000;", js)
        watch = fn_body(js, "startIdleWatch")
        self.assertIn("window.setInterval(function () {", watch,
                      "用轮询盯表：假时钟拨不动 setTimeout 链")
        self.assertIn("if (Date.now() - lastActivityAt < IDLE_MS) return;", watch)
        auto = fn_body(js, "autoSaveIdle")
        self.assertIn('dock("检测到长时间无操作，已自动存入待审核池。", "note");', auto)
        self.assertNotIn("toast(", auto, "自动存回不许弹窗抢老师")
        self.assertNotIn("panelSay(", auto)

    def test_07_unload_also_stashes(self) -> None:
        js = read("plugin.js")
        self.assertIn("stashOnUnload();", fn_body(js, "bind"))
        unload = fn_body(js, "stashOnUnload")
        self.assertIn('hostCall("pending.save_draft", payload)', unload)

    def test_08_background_ocr_errors_never_pop_a_red_window(self) -> None:
        """后台切题：识别错得再离谱也照切不误，只留一行警告。"""
        js = read("plugin.js")
        open_batch = fn_body(js, "openBatch")
        self.assertIn("dockWarn(", open_batch)
        self.assertNotIn("toast(", open_batch)
        warn = fn_body(js, "dockWarn")
        self.assertIn('dock("⚠ "', warn)
        self.assertIn('"warn"', warn)

    def test_09_duplicate_hit_offers_two_choices(self) -> None:
        """查重命中弹窗给【返回修改】与【强行覆盖】两颗钮，Esc 可关，焦点圈住。"""
        html = read("index.html")
        for node_id in ("epDupModal", "epDupBack", "epDupForce"):
            self.assertIn(f'id="{node_id}"', html)
        js = read("plugin.js")
        approve = fn_body(js, "onApprove")
        self.assertIn("if (error && error.duplicate) {", approve)
        self.assertIn("openDupModal(item, error);", approve)
        self.assertIn('hostCall("pending.approve", { pending_id: item.pendingId, force: force === true })',
                      approve)
        modal = fn_body(js, "openDupModal")
        self.assertIn("existingId", modal)
        keys = js[js.index('document.addEventListener("keydown"'):]
        self.assertIn('if (event.key === "Escape")', keys)
        self.assertIn('if (event.key !== "Tab") return;', keys, "Tab 必须被圈在弹窗里")

    def test_10_only_approve_and_delete_pull_questions_off_the_canvas(self) -> None:
        """暂存只是改内容，不许把题从画布上撤下来。"""
        js = read("plugin.js")
        handler = fn_body(js, "onPendingUpdated")
        self.assertIn('action === "approve" || action === "delete"', handler)
        self.assertIn("refreshBatches();", handler)
        self.assertIn('if (message.event === "system.pending_updated")', js)

    def test_11_deleting_a_question_asks_first(self) -> None:
        js = read("plugin.js")
        delete = fn_body(js, "onDelete")
        self.assertIn("openModal(delModalEl);", delete)
        confirm = fn_body(js, "onDeleteConfirm")
        self.assertIn('hostCall("pending.delete", { pending_id: item.pendingId })', confirm)

    def test_12_the_host_dock_renders_a_note_as_a_grey_line(self) -> None:
        """「记一笔」级别在底栏只留一行灰字：`[15:30] 正文`。"""
        workspace = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")
        dock_line = workspace[workspace.index("function dockLine("):]
        dock_line = dock_line[:dock_line.index("\n  }")]
        self.assertIn('kind === "note"', dock_line)
        self.assertIn('at.slice(0, 5)', dock_line)
        stage = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        self.assertIn('"note", "error", "info", "system", "warn"', stage,
                      "插件自报的 warn 级别必须在宿主白名单里")


class EditorCropMagnifierTest(unittest.TestCase):
    """军令 #26 纠偏：砍掉截屏，放大镜搬进左栏「重新框选」。

    钉住五件事：
    - 宿主只多开一个读口子（asset.read），权限按 assets:read 判定；
    - 插件侧画布必须干净（宿主读来的字节 → Blob → ImageBitmap），不许 fetch；
    - 放大镜是原样搬过来的：半径 104、8 倍、关平滑、镜心一根红十字；
    - 左键松开切完就走：镜子撤掉，字节落进中转站，主库一个字节都不碰；
    - 切图台开着的时候，全局粘贴不许把这张图当成新卷子吞掉。
    """

    def test_01_the_capture_feature_is_gone_for_good(self) -> None:
        """截屏那套东西必须连根拔掉：快捷键、按钮、宿主壳的遮罩与画布。"""
        for name in ("static/js/stage.js", "static/js/intake.js", "static/workspace.html"):
            path = ROOT / name
            if not path.is_file():
                continue
            source = path.read_text(encoding="utf-8")
            for gone in ("jzo-cap-layer", "jzo-cap-canvas", "jzo-cap-hint",
                         "captureScreen", "Alt+S", "getDisplayMedia("):
                self.assertNotIn(gone, source, f"{name} 仍残留截屏代码 {gone}")
        js = read("plugin.js")
        self.assertNotIn("Alt+S", js)
        self.assertNotIn("epCapture", read("index.html"))

    def test_02_the_host_opens_exactly_one_read_channel(self) -> None:
        stage = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        self.assertIn('"asset.read"', stage, "切图要读托管配图，宿主必须开这个口子")
        self.assertIn('assetReadPermissions.indexOf("assets:read") < 0', stage,
                      "读口子的权限必须按清单判定，不能谁都能调")
        self.assertIn('code: "FORBIDDEN"', stage)
        # 只许读底座自己托管的地址
        self.assertIn("/static\\/(pending|uploads|icons|assets)\\/", stage)

    def test_03_the_plugin_reads_pixels_without_fetch(self) -> None:
        """插件侧禁用 fetch（契约红线）：data URL → Blob 只能靠 atob 造字节。"""
        js = read("plugin.js")
        self.assertIn("function dataUrlToBlob(", js)
        blob = fn_body(js, "dataUrlToBlob")
        self.assertIn("window.atob(payload)", blob)
        self.assertNotIn("fetch(", blob)
        self.assertIn("new Blob([bytes], { type: mime || \"image/png\" })", blob)
        self.assertIn('hostCall("asset.read", { uri: picture.uri })', js)
        self.assertIn("window.createImageBitmap(blob)", js)

    def test_04_the_magnifier_is_the_ported_one(self) -> None:
        """几何与观感必须与被砍掉的那套一模一样，否则老师会觉得换了个人切图。"""
        js = read("plugin.js")
        self.assertIn("var CROP_RADIUS = 104;", js)
        self.assertIn("var CROP_ZOOM = 8;", js)
        lens = fn_body(js, "drawLens")
        self.assertIn("ctx.imageSmoothingEnabled = false;", lens, "放大镜必须关平滑看像素")
        self.assertIn('ctx.strokeStyle = "rgba(255, 96, 96, 0.95)";', lens,
                      "镜心准星必须是那根红十字")
        self.assertIn("ctx.arc(mx, my, radius, 0, Math.PI * 2);", lens)
        self.assertIn("ctx.lineWidth = 2;", lens, "镜圈是 2px 白边")

    def test_05_the_crop_surface_and_the_lens_are_styled(self) -> None:
        css = read("plugin.css")
        self.assertIn("cursor: crosshair", rule_body(css, ".ed-crop-canvas"),
                      "切图台上鼠标必须是十字")
        lens = rule_body(css, ".ed-crop-lens")
        self.assertIn("position: fixed", lens, "放大镜层要盖住整屏")
        self.assertIn("pointer-events: none", lens, "镜子不能挡住鼠标")
        self.assertIn("inset: 0", lens)
        self.assertIn(".ed-img-crop-btn", css)

    def test_06_releasing_the_button_finishes_the_crop(self) -> None:
        js = read("plugin.js")
        up = fn_body(js, "onCropUp")
        self.assertIn("if (!rect || rect.w < CROP_MIN_SIDE || rect.h < CROP_MIN_SIDE)", up)
        self.assertIn("finishCrop(session);", up)
        close = fn_body(js, "closeCrop")
        self.assertIn("lensCanvas.parentNode.removeChild(lensCanvas);", close,
                      "左键松开后放大镜必须消失")
        self.assertIn('window.removeEventListener("mouseup", onCropUp, true);', close)

    def test_07_the_cropped_bytes_land_in_the_pending_pool_first(self) -> None:
        """中转站里的题：配图字节随草稿一起进 pending_assets/，主库一个字节都不碰。"""
        js = read("plugin.js")
        finish = fn_body(js, "finishCrop")
        self.assertIn("item.cropAsset = { id: assetId, data_url: dataUrl };", finish)
        self.assertIn("stashOne(item, metaFor(item, {}), false)", finish)
        self.assertIn("item.cropAsset = null;", finish,
                      "存过之后必须清掉，否则下一次保存又写一份重复配图")
        stash = fn_body(js, "stashOne")
        self.assertIn("payload.questions[0].assets = [", stash)
        self.assertIn("data_url: String(item.cropAsset.data_url || \"\")", stash)

    def test_08_the_global_paste_stays_out_of_the_way_while_cropping(self) -> None:
        """切图台开着的时候，全局粘贴不许把这张图当成新卷子吞进批次。"""
        js = read("plugin.js")
        paste = js[js.index('window.addEventListener("paste"'):]
        paste = paste[:paste.index("});")]
        self.assertIn("if (crop) return;", paste)
        drop = js[js.index('root.addEventListener("drop"'):]
        drop = drop[:drop.index("});")]
        self.assertIn("if (crop) return;", drop)

    def test_09_the_pending_bank_echoes_the_real_asset_address(self) -> None:
        """插件切完图要知道底座把字节写到哪去了：题面里的 uri 得跟着换。"""
        bank = (ROOT / "app" / "core" / "pending_bank.py").read_text(encoding="utf-8")
        self.assertIn('"saved_assets":', bank)
        self.assertIn("PENDING_ASSET_URI_PREFIX", bank)


class EditorFixtureContractTest(unittest.TestCase):
    """假数据：每道题都是一份合法的 question.json 2.0，dev/ 只在本机存在。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.items = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def test_01_fixtures_are_valid_questions(self) -> None:
        from jsonschema import Draft202012Validator

        schema = json.loads((ROOT / "schemas" / "question.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        self.assertTrue(self.items, "假数据不能是空数组")
        for item in self.items:
            errors = list(validator.iter_errors(item))
            self.assertEqual(errors, [], f"假数据 {item.get('id')} 不合规：{errors}")
            self.assertEqual(item["schema_version"], "2.0")

    def test_02_dev_block_carries_source_and_stage_hints(self) -> None:
        for item in self.items:
            block = item["extensions"]["org.jiuzhang.editor.dev"]
            source = block["source_latex"]
            # 阶段 4 的假数据横跨四类题型：解答题按《格式宪法》用 problem 环境
            self.assertTrue("\\begin{question}" in source or "\\begin{problem}" in source,
                            f"{item['id']} 题干环境只能是 question 或 problem")
            self.assertFalse("\\begin{question}" in source and "\\begin{problem}" in source,
                             f"{item['id']} 两个题干环境不能同时出现")
            self.assertIn("\\begin{solution}", source)
            self.assertIn("答案：", source)
            self.assertIsInstance(block["confidence"], (int, float))
            self.assertIsInstance(block["cross_page"], bool)
            self.assertTrue(block["image_uri"].startswith("/static/"), "原图只能是底座托管路径")

    def test_03_choice_fixture_follows_the_format_constitution(self) -> None:
        choice = [item for item in self.items if item["type"].endswith("_choice")]
        self.assertTrue(choice, "阶段 1 建议题必须是选择题")
        for item in choice:
            source = item["extensions"]["org.jiuzhang.editor.dev"]["source_latex"]
            self.assertIn("（  ）", item["stem"], "选择题题干末尾要留括号")
            self.assertEqual(source.count("\\item "), len(item["options"]))
            self.assertIn("\\end{choices}\n\\end{question}\n\n\\begin{solution}", source)
            self.assertIn("答案：" + "".join(item["answer"]["choice_keys"]), source)
            self.assertTrue(item["solution"].startswith("解析"),
                            "宪法要求「答案：X」在 solution 首行，解析另起一行")

    def test_04_inline_block_equals_the_file(self) -> None:
        js = read("plugin.js")
        block = js[js.index(BEGIN) + len(BEGIN):js.index(END)]
        inline = json.loads(block.strip()[len("var DEV_FIXTURES = "):].rstrip(";"))
        self.assertEqual(inline, self.items,
                         "内嵌假数据与 dev/fixtures.json 漂移，先跑 tools/sync_editor_fixtures.py")

    def test_05_sync_tool_owns_the_marker_block(self) -> None:
        tool = (ROOT / "tools" / "sync_editor_fixtures.py").read_text(encoding="utf-8")
        self.assertIn(BEGIN.strip(), tool)
        self.assertIn("var DEV_FIXTURES = ", tool)

    def test_06_batch_fixtures_cover_the_four_types(self) -> None:
        """阶段 4 的批量界面要有四类题各一道，且全部按《格式宪法》落环境。"""
        by_type = {item["type"] for item in self.items}
        self.assertEqual(by_type, {"single_choice", "multiple_choice", "fill_blank", "solution"})
        for item in self.items:
            source = item["extensions"]["org.jiuzhang.editor.dev"]["source_latex"]
            stem_env = "\\begin{problem}" if item["type"] == "solution" else "\\begin{question}"
            self.assertTrue(source.startswith(stem_env), f"{item['id']} 题干了环境用错")
            if item["type"] == "multiple_choice":
                self.assertIn("（多选）", item["stem"])
                self.assertGreaterEqual(len(item["answer"]["choice_keys"]), 2)
            if item["type"] == "fill_blank":
                self.assertIn("\\fillin", source)
                # 方括号只当提示、不带答案：假数据一律用裸 \fillin
                self.assertNotIn("\\fillin[", source)
                self.assertEqual(item["answer"]["kind"], "expression")
        ids = [item["id"] for item in self.items]
        self.assertEqual(len(ids), len(set(ids)), "假数据题号不许重复")


class EditorPackageTest(unittest.TestCase):
    def _names(self) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            target = build_plugin(PLUGIN_DIR, Path(tmp))
            self.assertTrue(target.is_file())
            with zipfile.ZipFile(target) as bundle:
                return bundle.namelist()

    def test_01_zip_top_level_is_plugin_id_and_clean(self) -> None:
        names = self._names()
        self.assertTrue(names)
        for name in names:
            self.assertEqual(name.split("/")[0], "org.jiuzhang.editor", name)
            self.assertNotIn(".env", name.split("/"))
            self.assertNotIn("__pycache__", name.split("/"))
        joined = "\n".join(names)
        self.assertIn("org.jiuzhang.editor/plugin.json", joined)
        self.assertIn("org.jiuzhang.editor/dist/index.html", joined)
        self.assertIn("org.jiuzhang.editor/LICENSE", joined)
        self.assertFalse(any(name.endswith((".pyc", ".log", ".tmp", ".zip")) for name in names))

    def test_02_dev_fixtures_never_ship(self) -> None:
        """军令 #23：假数据不进发行包——对外只有真实题库，运行期靠 plugin.js 内嵌块。"""
        names = self._names()
        offenders = [each for each in names if "/dev/" in each or each.endswith("fixtures.json")]
        self.assertEqual(offenders, [], f"发行包混进开发期文件：{offenders}")
        self.assertIn("org.jiuzhang.editor/dist/plugin.js", names)


if __name__ == "__main__":
    unittest.main()
