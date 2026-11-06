"""录题工作台 v2（org.jiuzhang.editor，军令 #23 阶段 1–2）契约测试。

真机三栏与 MathJax 渲染由 ``tools/editor_probe.py`` 取证；这里钉住可静态判定的部分：

- 清单只申请画布舞台 + 右栏辅助栏插槽，写库经宿主、令牌永不进插件；
- 画布内只有三栏（左原图 | 中 exam-zh 源码 | 右渲染），**没有任何表单控件**；
- 辅助栏（``#epRoot``）只有元数据表单 + 审核动作 + 格式切换，**不放源码、不放预览**；
- 源码只用 exam-zh 标准环境（question/choices/problem/solution），填空用 ``\\fillin``；
- 解析器 / 重组器 / 本地清洗三件套的口径（阶段 2 复用同一份实现，不许另写）；
- 假数据 ``dev/fixtures.json`` 是单一事实来源：过 Schema 2.0、按《格式宪法》写源码、
  与 plugin.js 内嵌块逐字一致，且**绝不进发行包**；
- 沙箱红线：无 fetch / parent.document / 浏览器本地存储 / 远程资源 / 后行断言。

已知偏离（详见 .qoder/records/biz/2026-10/20261031_editor-v2-progress.md）：v1 的 A4 固定页几何（794×1123）随「渲染不固定
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
from tests.core_sources import stage_source, workspace_source  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "org.jiuzhang.editor"
DIST = PLUGIN_DIR / "dist"
FIXTURES = PLUGIN_DIR / "dev" / "fixtures.json"
BEGIN = "  //# FIXTURES-BEGIN"
END = "  //# FIXTURES-END"

# 军令 #23：只许 exam-zh 标准环境，禁止自定义任何 LaTeX 环境。
# center 不是自定义环境：任务四的配图按格式宪法必须落在 \begin{center} 里，
# 它是 LaTeX 内核自带的标准居中环境，不参与题目结构。
ALLOWED_ENVS = {"question", "choices", "problem", "solution", "center"}


def read(name: str) -> str:
    """读插件资源。``plugin.js`` / ``plugin.css`` 是**整包**：按 index.html 的加载次序拼起来。

    军令 #30 把插件拆成 ui_reactive / ui_breath / ui_capsule / plugin 几个小文件，
    契约判据仍然按「整包源码」看，不因文件拆分漏判。
    """
    if name == "plugin.js":
        return _bundle("script", "src")
    if name == "plugin.css":
        return _bundle("link", "href")
    return (DIST / name).read_text(encoding="utf-8")


def _bundle(tag: str, attr: str) -> str:
    html = (DIST / "index.html").read_text(encoding="utf-8")
    parts = []
    for value in re.findall(r"<%s[^>]*%s=\"([^\"]+)\"" % (tag, attr), html):
        if value.startswith("/static/"):
            continue
        path = DIST / value
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def manifest() -> dict:
    return json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))


def css_rule(css: str, selector: str) -> str:
    """取行首起算的那条规则：``.ep-head-tools .ep-btn {`` 不能冒充 ``.ep-btn {``。"""
    at = css.index("\n" + selector + " {") + 1
    return css[at:css.index("}", at)]


def canvas_only(html: str) -> str:
    """画布实例那段 DOM——右栏辅助栏根节点之后的内容不属于画布。"""
    return html[html.index('id="edRoot"'):html.index('id="epRoot"')]


def panel_only(html: str) -> str:
    """辅助栏实例那段 DOM——截到页面脚本之前，MathJax 是宿主给画布渲染公式用的。"""
    start = html.index('id="epRoot"')
    return html[start:html.index("<script", start)]


def rule_body(css: str, selector: str) -> str:
    """取 selector 所在规则的正文（分组选择器 .a, .b {} 也能命中）。"""
    at = css.index(selector)
    start = css.index("{", at) + 1
    return css[start:css.index("}", start)]


def _px(rule: str, prop: str) -> float:
    """把规则里某个 px 属性读成数字，用来比较两行字谁大谁小。"""
    hit = re.search(r"(?:^|[;{\s])" + re.escape(prop) + r":\s*([0-9.]+)px", rule)
    if hit is None:
        raise AssertionError("%s 必须是 px 数值" % prop)
    return float(hit.group(1))


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
        """清单声明的总线主题必须与投递一致（军令 #32 · 第五步新增两条）。

        `editor.pool_review`／`editor.batch_review` 各承担一类「辅助栏↔画布」双向指令：
        前者开关重题池那一屏，后者画琥珀灯与跑【全部入库】。主题名靠 `from` 分头，
        不再为「画布回执」另立第三条——新增总线主题的实数就是这两条。
        """
        bus = manifest()["bus"]
        self.assertEqual(sorted(bus["subscribe"]),
                         ["editor.apply_patch", "editor.batch_review", "editor.canvas_state",
                          "editor.clean_review",
                          "editor.clean_review_state", "editor.collect_files",
                          "editor.dup_compare", "editor.dup_review", "editor.pool_review",
                          "stage.selection",
                          "system.open_editor", "system.pending_updated",
                          "system.question_updated", "ui.params.changed"])
        self.assertEqual(sorted(bus["publish"]),
                         ["editor.batch_review", "editor.canvas_state", "editor.clean_review",
                          "editor.clean_review_state", "editor.collect_files",
                          "editor.dup_compare", "editor.dup_review", "editor.pool_review",
                          "region.dock",
                          "stage.selection",
                          "system.editor_close", "system.return_from_editor"])

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
        view = [item for item in controls if item.get("key") == "view"]
        self.assertEqual(len(view), 1, controls)
        self.assertEqual(view[0]["type"], "select")
        self.assertEqual([option["value"] for option in view[0]["options"]], ["review", "list"])
        self.assertEqual(view[0]["default"], "review",
                         "默认停在审核三栏；只有辅助栏点【返回列表】才发 list")


class EditorThreePaneLayoutTest(unittest.TestCase):
    """军令 #23 阶段 1 的验收面：画布里只有三栏，一道假数据能渲染。"""

    def test_01_canvas_has_exactly_three_panes_and_two_splits(self) -> None:
        canvas = canvas_only(read("index.html"))
        # 查重三栏（军令·查重三栏）：审核三栏之外多一只「原题渲染」栏，
        # 平时 hidden，只在 compare 模式从右侧滑出——静态节点实数因此是 4。
        self.assertEqual(canvas.count('class="ed-col '), 4, canvas)
        self.assertEqual(canvas.count('class="ed-split"'), 2, canvas)
        self.assertIn('id="edPaneOriginal"', canvas, "缺少查重对比的原题渲染栏")
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
        """题型 / 难度 / 年级是辅助栏的活；画布内容区不许出现题型表单。

        军令 #27 例外：画布右栏那只收集筐要能点开系统选文件框，
        所以画布里只许有**一只隐藏的** ``<input type="file">``，不许有第二个。
        双引擎例外：收集筐上方只许有版面 / 识别两个下拉框，其余下拉一律判不合格。
        """
        canvas = canvas_only(read("index.html"))
        # 双栏 API 配置弹窗必须住在画布：辅助栏整宽只有 300px，塞两栏就成了两根压扁的柴。
        # 它平时 hidden、只在老师点【API 配置】时出现，与剔除重复弹窗同一个口径——
        # 不在「画布内容区不许有表单控件」这条禁令的射程内。
        plain = canvas[:canvas.index('id="epAiConfigModal"')] + canvas[canvas.index('id="edToast"'):]
        self.assertEqual(plain.count("<select"), 2, "画布内只许有版面 / 识别两个下拉框")
        self.assertIn('id="edLayoutEngine"', plain)
        self.assertIn('id="edRecognizeEngine"', plain)
        self.assertEqual(plain.count("<input"), 1, "画布内只许剩收集筐那一只隐藏的选文件 input")
        at = plain.index("<input")
        tag = plain[at:plain.index(">", at)]
        self.assertIn('type="file"', tag, "画布内唯一的 input 必须是选文件用的")
        self.assertIn('id="edBasketFile"', tag)
        self.assertIn("aria-hidden=\"true\"", tag, "选文件 input 必须藏起来，不占版面")
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
        self.assertNotIn("exam-zh 全量源码", js, "源码栏不再挂每题冗言，只留可编辑整段源码")
        self.assertIn('class="ed-pane-head ed-src-tools"', html,
                      "源码栏头部是左对齐工具条，后续按钮往右追加")
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
        self.assertIn('node.addEventListener("scroll", function () {', js)
        self.assertIn("syncScroll(node);", js)
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
        for attr in ("data-render-ms", "data-math", "data-blocks", "data-errors",
                     "data-question-id", "data-row-h", "data-pane-w"):
            self.assertIn(f'"{attr}"', js, f"探针判据缺少度量属性 {attr}")
        self.assertIn("var progressText = state.scanBatch", js,
                      "扫描卷的进度条要同时报原卷页数")
        self.assertIn('"第 " + (state.active + 1) + " / " + state.items.length + " 题"', js)
        self.assertIn('" 题 · 原卷 " + pageTotal + " 页"', js)
        self.assertIn('"待框选 · 原卷 " + pageTotal + " 页"', js)


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
        # 画布上方一根毛的按钮都不留：返回列表已搬进辅助栏顶部死锁区。
        # 画布内只许剩收集筐的【🚀 开始解析】、批次列表右上角的【API 配置】、
        # 源码栏头部的【添加配图】与【重新切题】——各是建批次、任务配置、
        # 插配图、重切原卷的唯一入口。
        # 一键剔除弹窗的按钮不算工具条：它平时 hidden，只在老师点「剔除重复」后出现。
        plain_canvas = (canvas[:canvas.index('id="epBatchPurgeModal"')]
                        + canvas[canvas.index('id="edToast"'):])
        self.assertEqual(plain_canvas.count("<button"), 4,
                         "画布内只许剩【API 配置】【开始解析】【添加配图】【重新切题】")
        self.assertIn('id="edLayoutEngine"', plain_canvas)
        self.assertIn('id="edRecognizeEngine"', plain_canvas)
        self.assertNotIn('id="edRouteChannels"', canvas, "四通道按钮已换双下拉框")
        self.assertIn('id="epAiConfigList"', plain_canvas)
        self.assertIn('id="edAddIllustration"', plain_canvas)
        self.assertNotIn('id="edBackList"', canvas, "返回列表已搬进辅助栏")
        self.assertNotIn('id="edBatchBar"', canvas, "二屏抬头大横条已彻底删除")
        self.assertIn('id="edBasketGo"', canvas)

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
        """军令 #29：底段按钮视觉上要极矮，但 AGENTS §6 的 44px 触控面不许丢——
        靠伪元素把热区往外补一圈：视觉不破、命中区达标。"""
        css = read("plugin.css")

        def body_of(selector: str) -> str:
            # 从行首找起：`.ep-foot-actions .ep-mini-btn` 这种带前缀的规则不算数。
            at = css.index("\n" + selector + " {")
            start = css.index("{", at) + 1
            return css[start:css.index("}", start)]

        self.assertIn("min-height: 44px", body_of(".ep-btn"),
                      "【布局】钮必须与辅助栏其它按钮同高")
        for selector in (".ep-mini-btn", ".ep-head-tools .ep-seg-btn"):
            body = body_of(selector)
            self.assertIn("min-height: 24px", body, f"{selector} 的视觉高度必须极矮")
            self.assertIn("position: relative", body, f"{selector} 缺定位，热区补不上")
            after = body_of(selector + "::after")
            self.assertIn("inset: -10px 0", after,
                          f"{selector} 的 44px 热区没补上")
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
        for selector in (".ed-pane-body,", ".ep-root,", ".ep-scroll {"):
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
        # 原卷自带作答括号时不许再补：只看「题干里有没有空括号」，不猜缩进/全半角。
        self.assertIn('if (!EMPTY_BRACKET.test(text)) text += "（  ）"', js,
                      "选择题题干只有在没有空括号时才补括号")
        self.assertIn("text = text.replace(DUP_BRACKET, \"$1\")", js,
                      "旧路径留下的连体空括号要并成一个")
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

    def test_06_cleaning_rules_live_only_in_the_base(self) -> None:
        """军令 #32 · 判据 1.6：清洗规则表只准有一处，就是底座的 latex_style_dict。

        插件从前自带一份「定界符归一 + CRLF」的正则表，与底座那张并行——两套规则迟早分叉。
        现在整批清洗逐题发 `hostCall("text.clean_latex", {mode: "exam_source"})`，
        由 `question_parser.clean_exam_source` 洗；插件侧一张表都不留。
        """
        js = read("plugin.js")
        self.assertNotIn("function cleanExamSource", js, "插件又长出第二份清洗规则了")
        for forbidden in (r"/\\\[([\s\S]*?)\\\]/g", r"/\\\(([\s\S]*?)\\\)/g",
                          r'next.replace(/\r\n/g, "\n")'):
            self.assertNotIn(forbidden, js, f"本地清洗规则没拆干净：{forbidden}")
        commands = fn_body(js, "handleCommandExecute")
        self.assertIn('commandId === "org.jiuzhang.action.process.clean_latex"', commands)
        self.assertIn('hostCall("text.clean_latex", { text: text, mode: "exam_source" })', commands)
        self.assertNotIn("cleanExamSource(", commands, "内部命令不许再调本地规则表")

    def test_07_no_lookbehind_regex(self) -> None:
        """AGENTS §6：后行断言会让旧浏览器整份脚本报语法错。"""
        self.assertNotIn("(?<", read("plugin.js"))


class EditorMetaStripContractTest(unittest.TestCase):
    """渲染栏每道题顶部的只读信息条：待审进度 / 原卷题号 / 题型 / 分值 / 难度。"""

    def test_01_strip_is_read_only_and_carries_four_facts(self) -> None:
        html = read("index.html")
        self.assertIn('<script src="ui_meta_strip.js"></script>', html)
        js = read("plugin.js")
        self.assertIn("metaStrip: uiMetaStrip", js, "只读条没接进三栏渲染模块")
        block = fn_body(js, "renderQuestionBlock")
        self.assertIn(
            "block.appendChild(\n      metaStrip.render(item, index, parsed, meta, state.items.length))",
            block, "只读条必须排在每一题最上方，并带上本批总数")
        strip = read("ui_meta_strip.js")
        self.assertNotIn("addEventListener", strip, "只读卡片不许挂任何点击/键盘事件")
        self.assertIn('(index + 1) + " / "', strip, "第一格要报池内进度")
        self.assertIn('" (原卷第" + no + "题)"', strip, "原卷题号只从私有元数据读")
        self.assertIn("TYPE_LABELS[type]", strip)
        self.assertIn("scoreText(data.score)", strip)
        self.assertIn("DIFFICULTY_LABELS[difficulty]", strip)
        self.assertIn('strip.setAttribute("role", "note")', strip)

    def test_04_render_has_no_self_invented_numbering(self) -> None:
        """题号完全以原卷为准：渲染区不许再按数组下标补 ``1. 2. 3.``。"""
        js = read("plugin.js")
        self.assertNotIn('el("span", "ed-num"', js, "渲染区不许自增序号")
        self.assertNotIn(".ed-q-stem .ed-num", read("plugin.css"), "自增序号的样式一并下架")

    def test_02_strip_stays_visually_subordinate(self) -> None:
        css = read("plugin.css")
        strip = css_rule(css, ".ed-q-meta")
        self.assertLessEqual(_px(strip, "font-size"), 12, "元数据条字号必须小于正文")
        self.assertIn("var(--ink-soft)", strip, "元数据条要用弱化字色")
        self.assertIn("background: #f1f0ec", strip, "元数据条要浅灰底")
        self.assertLess(_px(strip, "font-size"), _px(css_rule(css, ".ed-q-stem"), "font-size"))
        self.assertIn(".ed-q-meta-item + .ed-q-meta-item::before", css,
                      "多项之间要有轻分隔")

    def test_03_meta_edits_repaint_the_strip(self) -> None:
        js = read("plugin.js")
        self.assertIn("paintMetaStrip: uiColumns.refreshMetaStrip", js)
        panel = read("ui_panel.js")
        self.assertIn("paintMetaStrip(Number(panel.selection.index) || 0)", panel,
                      "辅助栏改分值/难度后只读条要跟着换字")


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
        """年级在插件侧双写：契约根字段 + 插件自己的扩展键。

        2026-11-02 起底座写路径根字段优先（``_grade_of`` 先读 grade 再退扩展字段），
        根字段单独交过去也不再丢；扩展键继续留着，是给只把年级塞在 extensions
        里的旧库兜底，两条通道值一致时行为不变。
        """
        js = read("plugin.js")
        cell = fn_body(js, "questionFromParsed")
        self.assertIn('if (meta.grade) doc.grade = String(meta.grade).trim().slice(0, 20);', cell)
        self.assertIn('extras["org.jiuzhang.editor"] = editorExt;', cell)
        self.assertIn("editorExt.grade = doc.grade;", cell)

    def test_04_plugin_never_touches_token_or_database(self) -> None:
        js = read("plugin.js")
        # ``api_key`` 自终极军令任务一起是老师手填的厂商密钥：插件只能随保存请求
        # 上行一次，读回来永远只有 ``api_key_masked``（见 test_ai_copilot_contract）。
        # 这里继续钉死宿主令牌、直连网络与浏览器存储。
        for needle in ("X-JZO-Token", "local_token", "/api/", "fetch(", "localStorage",
                       "sk-", "sessionStorage", "indexedDB", "parent.document"):
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
        self.assertIn("/static/vendor/mathjax/tex-svg-full.js", read("index.html"), "公式只走本地 MathJax")

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
                        "epType", "epDifficulty",
                        "epQuestionNo", "epTags", "epMounted",
                        "epAiField", "epAiAsk", "epAiSend", "epAiClean",
                        "epAiState", "epAiNote", "epAiPreview", "epAiApply", "epAiDiscard",
                        "epApprove", "epStash", "epDelete",
                        "epDupWarn", "epDupInspect", "epDupOverwrite",
                        "epDupMerge", "epDupAbandon",
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
        for forbidden in ("edSourceBody", "edRenderBody", "edQBlock", "mathjax",
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

    def test_03b_single_approve_button_is_named_single(self) -> None:
        """底栏四颗钮分工不变：【单题入库】与【全部入库】成对，旧名【存入主库】只许留在回执话术里。"""
        panel = panel_only(read("index.html"))
        self.assertIn('id="epApprove">单题入库</button>', panel)
        self.assertNotIn('id="epApprove">存入主库</button>', panel,
                         "按钮文案已统一为【单题入库】，不许新旧两名并存")

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
                    js.index("  // ---------- 布局：源码 / 渲染左右互换")]
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
        # 【返回列表】也只在辅助栏里（瘦身令后不带箭头图标），且同样经宿主参数通道广播回画布
        back = fn_body(js, "backToListFromPanel")
        self.assertIn('hostCall("ui.params.set"', back)
        self.assertIn('params: { view: "list" }', back)
        self.assertIn("plugin_id: PLUGIN_ID", back)
        self.assertIn('panelBackListEl.addEventListener("click", backToListFromPanel)', activate)
        self.assertIn('values.view === "list"', params,
                      "画布收到广播才真回列表，且只认 review → list 这一跳")
        self.assertIn('backToList("已回到批次列表。", true)', params,
                      "画布不许把刚收到的 list 再回发一遍")

    def test_07_touch_targets_meet_the_a11y_floor(self) -> None:
        """AGENTS §6：触控目标不小于 44px；树行与小圆钮（热区补齐）都得达标。"""
        css = read("plugin.css")
        for selector in (".ep-input", ".ep-select"):
            self.assertIn("min-height: 44px", rule_body(css, selector),
                          f"{selector} 没有 44px 触控高度")
        chip_x = rule_body(css, ".ep-chip-x")
        self.assertIn("position: relative", chip_x)
        self.assertIn(".ep-chip-x::after", css, "小圆钮要用伪元素把热区补到 44px")
        self.assertIn("inset: -14px -8px", rule_body(css, ".ep-chip-x::after"))

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
        """考向大纲树已下线（UI 极致瘦身令 2026-11-02）：懒加载只剩幽灵胶囊这一条路。"""
        js = read("plugin.js")
        html = read("index.html")
        for gone in ("function topicNode(", "function loadChildren(",
                     "function loadTopicRoots(", 'id="epTopicTree"', ".ep-tree",
                     ".ep-topic-expander"):
            self.assertNotIn(gone, js + html, f"{gone} 已随考向大纲树退场")
        self.assertIn('ctx.hostCall("bank.topics", key ? { parent_id: key } : {})', js,
                      "路径解析按层懒取：只问祖先那一层，别一上来把整棵大纲拖进右栏")
        self.assertIn('ctx.hostCall("bank.topics", { q: query })', js,
                      "候选来自拼音模糊搜索，与大纲共用同一条只读通道")
        self.assertIn("var TOPIC_LIMIT = 8", js)
        toggle = fn_body(js, "toggleTopic")
        self.assertIn("ids.length >= TOPIC_LIMIT", toggle, "挂载数量必须有上限")
        self.assertIn("先摘掉一个。", toggle)

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
        self.assertIn('if (panel.selection || panel.view === "list") return;',
                      fn_body(js, "applyDraftSelection"),
                      "已经收到活选区、或已明确回到批次列表后，不许用旧草稿把它盖回去")
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
        stage = stage_source()
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
    审核动作改成【存入主库】【存为待审】【彻底删除】三颗钮，住在辅助栏；
    画布首屏改成批次列表，二屏抬头才写当前批次号。
    """

    def test_01_back_to_list_lives_in_the_panel_head(self) -> None:
        canvas = canvas_only(read("index.html"))
        panel = panel_only(read("index.html"))
        for node_id in ("edBatches", "edBatchList", "edBatchNo", "edBatchStat"):
            self.assertIn(f'id="{node_id}"', canvas, f"画布首屏缺少 {node_id}")
        # 批次号只留读屏与探针，视觉上不占像素
        for node_id in ("edBatchNo", "edBatchStat"):
            at = canvas.index(f'id="{node_id}"')
            self.assertIn('class="ed-sr"', canvas[max(0, at - 60):at],
                          f"{node_id} 必须 sr-only")
        # 画布抬头大横条与它那颗回列表的钮一起撤干净
        for gone in ("edBatchBar", "edBackList"):
            self.assertNotIn(f'id="{gone}"', canvas, f"{gone} 已随画布抬头撤除")
        # 返回列表与源码/卡片/互换同住辅助栏顶部死锁区，挤在同一行
        head = panel[panel.index('id="epHead"'):panel.index('id="epScroll"')]
        for node_id in ("epHeadTools", "epBackList", "epFmtLatex", "epFmtBoxed", "epSwap"):
            self.assertIn(f'id="{node_id}"', head, f"辅助栏死锁区缺少 {node_id}")
        foot = panel[panel.index('id="epDock"'):]
        self.assertNotIn('id="epFmtLatex"', foot, "视图切换已搬进头部，脚部不许留双份")
        self.assertNotIn('id="epSwap"', foot)
        for node_id in ("edPool", "edBatchNote"):
            self.assertIn(f'id="{node_id}"', panel, f"辅助栏台账缺少 {node_id}")
            self.assertNotIn(f'id="{node_id}"', canvas, f"{node_id} 属于辅助栏，不许留在画布")
        # 画布底栏连同它的容器一起删干净（注释里可以留说明，不许留元素）
        self.assertNotIn('class="ed-foot"', canvas, "画布底栏已整条删除")
        # 批量条不许把表单控件带进画布（<button> 不算表单输入控件；
        # 收集筐那只隐藏的选文件 input 是军令 #27 唯一例外）。
        # 双栏 API 配置窗与剔除重复弹窗一样平时 hidden、点按钮才出现，不算画布内容区。
        # 收集筐上方那两只引擎下拉是本轮唯一的例外：版面引擎 + 识别引擎，一左一右。
        plain = canvas[:canvas.index('id="epAiConfigModal"')] + canvas[canvas.index('id="edToast"'):]
        self.assertEqual(plain.count("<select"), 2, "画布内只许有版面 / 识别两个下拉框")
        self.assertIn('id="edLayoutEngine"', plain)
        self.assertIn('id="edRecognizeEngine"', plain)
        self.assertEqual(plain.count("<input"), 1)
        # 批量提交整体退场：三颗审核钮才是唯一出口
        for gone in ("edSaveAll", "edPoolStash"):
            self.assertNotIn(f'id="{gone}"', read("index.html"),
                             f"{gone} 已随批量提交退场")

    def test_02_the_three_review_buttons_are_the_only_write_paths(self) -> None:
        """审核台只有三条出路：存主库、存待审、彻底删除。批量提交的口径整体撤除。"""
        js = read("plugin.js")
        for gone in ("saveAllDirty", "panelSaveAllDirty", "panelWorklistItems",
                     "patchPanelPool", "dirtyList"):
            self.assertNotIn("function " + gone + "(", js, f"{gone} 已随批量提交退场")
        self.assertIn('hostCall("pending.approve"', js)
        self.assertIn('hostCall("pending.save_draft"', js)
        self.assertIn('hostCall("pending.delete"', js)

    def test_02b_stash_updates_the_same_pending_row_in_place(self) -> None:
        """存为待审带 pending_id：池子里不许多出一道重影，题号也不会飘。"""
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
        bundle = read("plugin.js")
        js = fn_body(bundle, "approveBusy")
        self.assertIn('panelApproveEl.setAttribute("aria-busy", busy ? "true" : "false");', js)
        self.assertIn("syncSchoolLock();", js,
                      "忙态一律交回统一禁用逻辑，别处不许再手写一份 disabled")
        lock = fn_body(bundle, "syncSchoolLock")
        self.assertIn("panelApproveEl.disabled = !canApprove;", lock)
        self.assertIn('panelApproveEl.setAttribute("aria-disabled", canApprove ? "false" : "true");', lock)
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

    def test_16_purge_modal_lives_in_the_canvas_root(self) -> None:
        """「剔除重复」按钮在画布批次列表里，弹窗必须同住 #edRoot。

        2026-11-02 真机探针抓到的坑：弹窗留在 #epRoot 下，可画布帧里那半棵树是
        hidden 的——openModal 把 hidden 抹了，布局框仍是 0×0，老师什么都看不见。
        """
        html = read("index.html")
        self.assertIn('id="epBatchPurgeModal"', canvas_only(html),
                      "一键剔除弹窗必须挂在画布根下；留在辅助栏根下，画布帧里就是 0×0")
        self.assertNotIn('id="epBatchPurgeModal"', panel_only(html))
        js = read("ui_batches.js")
        self.assertIn('el("button", "ed-batch-purge", "剔除重复")', js)
        self.assertIn('hostCall("pending.batch_duplicates"', js)
        self.assertIn('hostCall("pending.purge_duplicates"', js)

    def test_17_g2_c1_ledger_never_folds_pooled_into_deleted(self) -> None:
        """军令 #32 · G2 · C1（前端那一半）：批次台账里「池内」是一条**独立**的账。

        底座现在任何状态都给 ``dedupe.pooled``（后端四条读拍由
        ``tests/test_pending_dedupe_scan.py::test_12`` 与
        ``tests/test_pending_pool.py::test_49`` 钉，HTTP 端到端由
        ``tests/test_pending_api.py::PoolEvictionHttpTest`` 钉）。这里钉住画布侧的
        换算口径：「已裁删」＝``total - pending - pooled - stored``，
        ``pooled`` **必须在减数里**——漏掉它，抽进重题池的题就在账上变成老师删掉的题。
        负向对照同条给出：旧的换算式（不含 ``pooled``）不许以任何写法回到现场。
        """
        js = read("ui_batches.js")
        self.assertIn("var gone = pooledKnown ? total - pending - pooled - stored : 0;", js,
                      "已裁删的算式必须把池内单独减掉；老底座不给 pooled 时整条不报")
        self.assertIn("var pooledKnown = Boolean(dedupe) && dedupe.pooled !== undefined"
                      " && dedupe.pooled !== null;", js)
        self.assertIn("池内 = 已抽进重题池的条数", js, "台账注释得说清这一栏是什么")
        self.assertNotIn("total - pending - stored", js,
                         "旧算式（把池内折进已裁删）不许回来")


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
        self.assertIn('if (colsEl) colsEl.hidden = state.mode !== "review" && state.mode !== "compare";',
                      set_mode)
        self.assertNotIn("batchBarEl", set_mode, "画布抬头已撤，模式切换不再管横条")
        activate = js[js.index('if (message.method === "plugin.activate")'):
                      js.index('if (message.method === "plugin.deactivate")')]
        self.assertIn('setMode("list");', activate, "画布挂载后先落在批次列表上")

    def test_01b_back_to_list_clears_the_previous_question(self) -> None:
        """返回批次列表：右栏不许再挂着上一题的表单与动作按钮。"""
        js = read("plugin.js")
        back = fn_body(js, "backToList")
        self.assertIn("publishSelection();", back,
                      "回列表时立刻发 list 选区，右栏不必等 batch_list 往返才清")
        list_sel = fn_body(js, "applyListSelection")
        self.assertIn("clearQuestionState();", list_sel)
        clear = fn_body(js, "clearQuestionState")
        for cleared in ('panelHeadNoEl.textContent = "批次概览"',
                        'panelQuestionNoEl.value = "";',
                        'panelScoreEl.value = "";',
                        'panelTagsEl.value = "";',
                        "setActionsEnabled(false);"):
            self.assertIn(cleared, clear, f"回列表没清掉 {cleared}")
        self.assertIn("setActionsEnabled(true);", fn_body(js, "applySelection"),
                      "重新进批次时必须把动作按钮解锁")
        # 面板开机时会挂一次 900ms 的草稿补读：它若在【返回列表】之后才回来，
        # 会把旧题回灌到已经清空的右栏。面板必须记住「已明确回到列表」这个空状态。
        self.assertIn('panel.view = "list";', list_sel,
                      "回列表要先记下视图，selection 为空才不会被当成「还没载入」")
        self.assertIn('panel.view = "review";', fn_body(js, "applySelection"))
        draft = fn_body(js, "applyDraftSelection")
        self.assertIn('if (panel.selection || panel.view === "list") return;', draft,
                      "迟到的草稿只许补「还没载入」，不许覆盖已回到列表的清空态")

    def test_02_batch_row_format_matches_the_order(self) -> None:
        """第一行是原文件名（加大加粗），第二行灰字「11-05 12:19 | 批次 #B-001」，右「待审 n / N」数字绿色。"""
        js = read("plugin.js")
        stamp = fn_body(js, "shortBatchStamp")
        self.assertIn('" " + hit[4] + ":" + hit[5]', stamp,
                      "第二行只报月日与时刻，年份和星期都省给文件名")
        self.assertNotIn("星期", stamp)
        rows = fn_body(js, "renderBatchList")
        self.assertIn('var title = String(card.source_name || card.label || ("批次 #" + card.batch_id));',
                      rows, "卡片第一行必须是原始文件名，老批次才退到批次标签")
        self.assertIn('el("span", "ed-batch-name", title)', rows)
        self.assertIn('shortBatchStamp(card.created_at) + " | 批次 #" + card.batch_id', rows)
        self.assertIn('el("span", "ed-batch-label", "待审 ")', rows)
        self.assertIn('el("span", "ed-batch-num", String(pending))', rows)
        self.assertIn('el("span", "ed-batch-num ed-batch-total", String(total))', rows)
        css = read("plugin.css")
        self.assertIn("color: var(--accent)", rule_body(css, ".ed-batch-num"),
                      "待审数字必须是绿色")
        name = rule_body(css, ".ed-batch-name")
        self.assertIn("font-weight: 700", name)
        self.assertGreaterEqual(_px(name, "font-size"), 15, "卷名是全卡最大的一行")
        self.assertIn("color: var(--ink-soft)", rule_body(css, ".ed-batch-meta"),
                      "时间与编号退成灰字")
        self.assertLess(_px(rule_body(css, ".ed-batch-meta"), "font-size"),
                        _px(name, "font-size"))
        # 两端对齐住在主按钮里：行本身还要在右端挂【剔除重复】，不能自己 space-between
        open_rule = rule_body(css, ".ed-batch-open")
        self.assertIn("justify-content: space-between", open_rule,
                      "两端对齐：左边卷名、右边计数")
        self.assertIn("text-align: left", open_rule)
        self.assertIn("flex: 1 1 auto", open_rule, "主按钮吃满整行，剔除钮才贴得住右端")
        purge = css_rule(css, ".ed-batch-purge")
        self.assertIn("flex: none", purge, "剔除钮不许被长批次号挤扁")
        self.assertIn("border: 1px dashed", purge, "剔除是次要动作，虚线弱化")
        self.assertIn("color: var(--ink-soft)", purge, "剔除按钮不许抢视觉重心")

    def test_03_a_finished_batch_is_grey_sunk_and_unclickable(self) -> None:
        """未审归零的批次：变灰、沉到最底、不可点——只能看。"""
        js = read("plugin.js")
        rows = fn_body(js, "renderBatchList")
        self.assertIn("var leftDone = Number(left.pending_count) === 0 && !left.page_only ? 1 : 0;",
                      rows)
        self.assertIn("var rightDone = Number(right.pending_count) === 0 && !right.page_only ? 1 : 0;",
                      rows)
        self.assertIn("if (leftDone !== rightDone) return leftDone - rightDone;", rows,
                      "审完的批次必须沉到列表最底；纯图卷还没框选，不许沉")
        self.assertIn("row.setAttribute(\"data-done\", done ? \"true\" : \"false\");", rows)
        # 行本身是容器，不可点的是里面那颗主按钮
        self.assertIn("open.disabled = true;", rows)
        self.assertIn('open.setAttribute("aria-disabled", "true");', rows)
        # 未审为 0 的行不许挂点击：绑定只住在 else 分支里
        self.assertIn('open.addEventListener("click", function () { openBatch(card.batch_id); });', rows)
        self.assertLess(rows.index("if (done) {"),
                        rows.index('open.addEventListener("click"'),
                        "点开的绑定必须在 else 分支：审完的批次只许看")
        css = read("plugin.css")
        done = rule_body(css, '.ed-batch-row[data-done="true"]')
        self.assertIn("opacity:", done)
        self.assertIn("cursor: default", done)

    def test_04_the_batch_bar_names_the_current_batch(self) -> None:
        js = read("plugin.js")
        bar = fn_body(js, "renderBatchBar")
        self.assertIn('batchNoEl.textContent = "批次 #" + (state.batchId || "—");', bar)
        # 「未审 X ＋ 池内 Y ＝ 总数」这本账只有一处算法（军令 #32 · 判据 5.1 的账目对平）：
        # 批次卡片与二屏抬头都走 ledgerText，不许两处各写一份文案。
        self.assertIn("ledgerText(ledger)", bar)
        self.assertIn("未审 ", fn_body(js, "ledgerText"))
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

    def test_09_duplicate_hit_offers_three_choices(self) -> None:
        """查重命中（军令 #31）：画布出**渲染**对比浮层，辅助栏出红字与三个裁决动作。

        画布里一颗按钮都不许有（军令 #23：画布里只许有题目内容），所以「覆盖 /
        放弃 / 合并为解析二」住在辅助栏的段三；画布只负责把两侧渲染摆出来。
        """
        html = read("index.html")
        canvas = canvas_only(html)
        for node_id in ("edDupModal", "edDupMineBody", "edDupTheirBody",
                        "edDupNote", "edDupBlock"):
            self.assertIn(f'id="{node_id}"', canvas, f"画布缺少对比浮层的 {node_id}")
        # 对比浮层这一段一颗按钮都不许有（裁决只住辅助栏）；
        # 整幅画布的静态按钮另有收集筐与剔除弹窗，不能混进来算。
        dup_block = canvas[canvas.index('id="edDupModal"'):canvas.index('id="edCleanModal"')]
        self.assertEqual(dup_block.count("<button"), 0,
                         "对比浮层不许在画布里放按钮：裁决动作只住辅助栏")
        panel = panel_only(html)
        for node_id in ("epDupWarn", "epDupInspect", "epDupOverwrite",
                        "epDupMerge", "epDupAbandon"):
            self.assertIn(f'id="{node_id}"', panel, f"辅助栏缺少查重控件 {node_id}")
        self.assertIn("主库已存在高度相似题目", panel, "红字必须与军令逐字一致")

        js = read("plugin.js")
        approve = fn_body(js, "onApprove")
        self.assertIn("inspectDup();", approve)
        self.assertIn("precheck(item).then(function (report) {", approve,
                      "入库前必须先查重，命中就不许直接写库")
        # 真写库那一步被后端 409 拦下时，补一次查重把完整报告取回来再让老师裁决。
        write = fn_body(js, "approveNow")
        self.assertIn("if (error && error.duplicate) {", write)
        self.assertIn("precheck(item).then(function (report) {", write)

        action = fn_body(js, "doDupAction")
        self.assertIn('hostCall("pending.approve", { pending_id: item.pendingId, action: action })',
                      action)
        self.assertIn('action === "merge_solution"', action)
        self.assertIn('action === "abandon"', action)

        # 答案不同则红字拦截：【覆盖】【合并为解析二】两颗钮锁死，只留【放弃】。
        sync = fn_body(js, "syncDupActions")
        self.assertIn("node.disabled = blocked || busy;", sync)
        self.assertIn("dupAbandonEl.disabled = false", sync)

        # 对比的是**渲染**，不是源码：两侧都走 appendBody / appendRich。
        dup = read("ui_dup.js")
        self.assertIn("appendBody(target, stem);", dup, "题干必须走渲染")
        self.assertIn("appendRich(line,", dup, "选项必须走渲染")
        self.assertNotIn("textContent = String(body.source", dup, "绝不许拿源码当对比")

        # 浮层的开合由辅助栏经宿主投递，两帧不直连。
        self.assertIn("showDupReview(dupPayload)", read("core_protocol.js"))
        self.assertIn("clearDupReview()", read("core_protocol.js"))

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
        workspace = workspace_source()
        dock_line = workspace[workspace.index("function dockLine("):]
        dock_line = dock_line[:dock_line.index("\n  }")]
        self.assertIn('kind === "note"', dock_line)
        self.assertIn('at.slice(0, 5)', dock_line)
        stage = stage_source()
        self.assertIn('"note", "error", "info", "system", "warn"', stage,
                      "插件自报的 warn 级别必须在宿主白名单里")


class EditorFileBasketTest(unittest.TestCase):
    """军令 #27：右栏文件收集筐——首屏黄金分割、圆角虚线筐、垂直单列文件行、【开始解析】才建批次。

    真机流程由 ``tools/editor_probe.py`` 取证；这里钉住可静态判定的部分。
    """

    def test_01_the_first_screen_splits_in_two_halves(self) -> None:
        """左栏历史批次列表、右栏收集筐，黄金分割 1.618 : 1（左宽右窄）。"""
        css = read("plugin.css")
        body = css_rule(css, ".ed-batches-body")
        self.assertIn("display: grid", body)
        self.assertIn("grid-template-columns: 1.618fr 1fr", body,
                      "首屏必须是黄金分割栅格，左侧批次列表宽于右侧收集筐")
        html = read("index.html")
        self.assertIn('class="ed-batch-col"', html, "左栏是批次列表")
        self.assertIn('class="ed-basket-col"', html, "右栏是收集筐")
        self.assertLess(html.index('class="ed-batch-col"'), html.index('class="ed-basket-col"'),
                        "批次列表在左，收集筐在右")

    def test_02_the_basket_is_one_big_rounded_dashed_box(self) -> None:
        """右栏整块是一只巨大的圆角虚线框，但里面改成了垂直单列列表。"""
        css = read("plugin.css")
        basket = css_rule(css, ".ed-basket")
        self.assertIn("border: 2px dashed", basket, "虚线框是收集筐的招牌")
        self.assertIn("border-radius: 20px", basket, "圆角要够大，才像一只筐")
        self.assertIn("flex-direction: column", basket, "文件列表竖着排，底部才留得住【开始解析】")
        self.assertIn("align-items: stretch", basket)
        self.assertIn("text-align: left", basket, "列表行左对齐，不再是居中文案")
        col = css_rule(css, ".ed-basket-col")
        self.assertIn("flex-direction: column", col, "引擎下拉在上、筐在下，竖着摞")
        self.assertIn("align-items: stretch", col, "筐要横向铺满右栏")
        self.assertIn("justify-content: center", col)
        listing = css_rule(css, ".ed-basket-list")
        self.assertIn("flex-direction: column", listing, "一行一个文件，垂直单列")
        self.assertIn("overflow-y: auto", listing, "列表在虚线框内独立滚动")

    def test_03_each_row_has_an_icon_a_name_and_a_remove_button(self) -> None:
        """每行一个文件：左图标（图片小缩略图 / 文档图标）、中间文件名省略、右侧红 ×。

        缩略图画在 canvas 上：插件沙箱的 CSP 是 ``img-src 'self' <底座源>``，
        blob: 与 data: 的 ``<img>`` 全被拦掉——屏幕上只会剩一只空框。
        """
        css = read("plugin.css")
        row = css_rule(css, ".ed-basket-item")
        self.assertIn("display: flex", row)
        self.assertIn("align-items: center", row)
        self.assertIn("min-height: 56px", row)
        thumb = css_rule(css, ".ed-basket-thumb")
        self.assertIn("width: 44px", thumb, "图片缩略图收到 44px 小方图")
        self.assertIn("height: 44px", thumb)
        icon = css_rule(css, ".ed-basket-icon")
        self.assertIn("width: 44px", icon, "文档图标和缩略图同宽，行首才对齐")
        self.assertIn("height: 44px", icon)
        name = css_rule(css, ".ed-basket-name")
        self.assertIn("text-overflow: ellipsis", name, "文件名太长自动省略")
        self.assertIn("white-space: nowrap", name)
        self.assertIn("flex: 1 1 auto", name, "文件名吃掉中间的余量")
        js = read("plugin.js")
        render = fn_body(js, "renderBasket")
        self.assertIn('var item = el("li", "ed-basket-item");', render)
        self.assertIn('thumb.className = "ed-basket-thumb";', render)
        self.assertIn('document.createElement("canvas")', render)
        self.assertIn('var icon = el("span", "ed-basket-icon");', render)
        self.assertIn('var nameEl = el("span", "ed-basket-name", entry.name);', render)
        self.assertIn("nameEl.title = entry.name;", render, "悬停看全名")
        self.assertIn("var THUMB_SIDE = 44;", js)
        self.assertIn("window.createImageBitmap(entry.file)", js,
                      "缩略图得用插件自己解出的位图，沙箱的 CSP 拦不住它")
        self.assertNotIn("URL.createObjectURL", js, "blob: 的 <img> 会被 CSP 挡成空框")
        self.assertNotIn("URL.revokeObjectURL", js)
        self.assertIn("entry.bitmap.close()", fn_body(js, "basketRemove"),
                      "移除条目要把位图还回去")

    def test_04_every_item_has_a_remove_button(self) -> None:
        css = read("plugin.css")
        cross = css_rule(css, ".ed-basket-x")
        self.assertIn("width: 44px", cross, "移除钮的触控面按 AGENTS §6 不得小于 44px")
        self.assertIn("height: 44px", cross)
        js = read("plugin.js")
        render = fn_body(js, "renderBasket")
        self.assertIn('el("button", "ed-basket-x", "×")', render)
        self.assertIn("basketRemove(entry.id);", render)

    def test_05_only_the_go_button_creates_a_batch(self) -> None:
        """建批次只能由【开始解析】发起：拖入与粘贴都只往筐里放。"""
        js = read("plugin.js")
        go = fn_body(js, "basketGo")
        self.assertIn("ingestEntries(", go, "【开始解析】才把筐里的东西交给宿主")
        self.assertIn('hostCall("ingest.files"', js)
        add = fn_body(js, "basketAdd")
        self.assertNotIn("ingest", add.lower(), "拖入/粘贴不许顺手建批次")
        drop = js[js.index('root.addEventListener("drop"'):]
        drop = drop[:drop.index("});")]
        self.assertIn("basketAdd(files);", drop, "拖到画布任何位置都算落进筐里")
        self.assertNotIn("ingest", drop.lower())
        self.assertNotIn("function ingestFiles(", js,
                         "旧口径「拖进来就自动建批次」必须退场")

    def test_06_the_go_button_is_visible_only_when_there_are_files(self) -> None:
        js = read("plugin.js")
        render = fn_body(js, "renderBasket")
        self.assertIn("if (basketFootEl) basketFootEl.hidden = state.basket.length === 0;", render)
        self.assertIn('basketGoEl.textContent = "🚀 开始解析 (" + state.basket.length + " 个文件)";',
                      render)
        html = read("index.html")
        self.assertIn('id="edBasketGo"', html)
        self.assertIn('id="edBasketFoot" hidden', html)

    def test_07_the_panel_instance_never_creates_a_batch_by_itself(self) -> None:
        """辅助栏那张 iframe 收到文件只转交宿主；建批次的事归画布的筐。"""
        js = read("plugin.js")
        collect = fn_body(js, "collectToCanvas")
        self.assertIn('publish("editor.collect_files", { files: list });', collect)
        self.assertNotIn("ingest", collect.lower())
        # 画布只收画布那份：辅助栏再收一遍就成了两份
        handler = js[js.index('if (message.event === "editor.collect_files") {'):]
        handler = handler[:handler.index("return;\n      }")]
        self.assertIn('if (state.slot !== "stage.center") return;', handler)
        self.assertIn("basketAdd(incoming);", handler)

    def test_08_the_host_owns_the_relay_and_never_loses_the_files(self) -> None:
        """宿主是中间人：白名单放行、只转给录题画布，画布不在就退回直接入库。"""
        stage = stage_source()
        self.assertIn('"editor.collect_files"', stage, "宿主白名单必须放行这个事件")
        relay = stage[stage.index('bus.on("editor.collect_files"'):]
        relay = relay[:relay.index("\n      });")]
        self.assertIn("payload.pluginId !== EDITOR_PLUGIN_ID", relay,
                      "别的插件想往筐里塞东西，门都不给")
        self.assertIn('notify(editorTab, "editor.collect_files", { files: files });', relay)
        self.assertIn("window.JzoIntake.ingestFiles(files, { source: \"panel\" });", relay,
                      "画布没开时文件不许凭空消失")
        intake = (ROOT / "static" / "js" / "intake.js").read_text(encoding="utf-8")
        self.assertIn("function collectIntoEditor(files)", intake)
        self.assertIn("window.JzoStage.notifyCanvas(editorId, \"editor.collect_files\"", intake)


class EditorCropMagnifierTest(unittest.TestCase):
    """军令 #26 纠偏：砍掉截屏，放大镜搬进左栏「重新框选」。

    钉住五件事：
    - 宿主只多开一个读口子（asset.read），权限按 assets:read 判定；
    - 插件侧画布必须干净（宿主读来的字节 → Blob → ImageBitmap），不许 fetch；
    - 放大镜小而清楚：直径 120px、1.2 倍、开平滑、镜心一根红十字；
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
        stage = stage_source()
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

    def test_04_the_magnifier_is_small_and_clear(self) -> None:
        """镜窗直径 120px、源像素 1.2 倍、1px 细边：小而清楚，绝不挡住正在看的字。"""
        js = read("plugin.js")
        self.assertIn("var CROP_RADIUS = 60;", js, "半径 60 = 直径 120px")
        self.assertIn("var CROP_ZOOM = 1.2;", js)
        lens = fn_body(js, "drawLens")
        self.assertIn("ctx.imageSmoothingEnabled = true;", lens,
                      "镜内必须开平滑，小倍率也要看得清")
        self.assertIn('ctx.strokeStyle = "rgba(255, 96, 96, 0.95)";', lens,
                      "镜心准星必须是那根红十字")
        self.assertIn("ctx.arc(mx, my, radius, 0, Math.PI * 2);", lens)
        self.assertIn("ctx.lineWidth = 1;", lens, "镜圈收成 1px 细边")
        self.assertIn("px + radius + 18", lens, "镜子永远偏在指针一侧，不压住光标下的字")
        self.assertIn("if (px < box.left || px > box.right || py < box.top || py > box.bottom) return;",
                      lens, "指针离开画布就把镜子收掉")

    def test_05_the_crop_surface_and_the_lens_are_styled(self) -> None:
        css = read("plugin.css")
        self.assertIn("cursor: crosshair", rule_body(css, ".ed-crop-canvas"),
                      "切图台上鼠标必须是十字")
        lens = rule_body(css, ".ed-crop-lens")
        self.assertIn("position: fixed", lens, "放大镜层要盖住整屏")
        self.assertIn("pointer-events: none", lens, "镜子不能挡住鼠标")
        self.assertIn("inset: 0", lens)
        self.assertIn(".ed-img-crop-btn", css)

    def test_06_releasing_the_button_offers_the_crop_actions(self) -> None:
        """纯图片卷松开即切；普通题松开仍弹动作选项（配图 / 切分新题 / 取消）。

        扫描卷每一页都是原卷，框完就是一道新题，不让老师再点第二次；
        普通题框的可能是配图，必须先问这一块算哪一类。
        """
        js = read("plugin.js")
        up = fn_body(js, "onCropUp")
        self.assertIn("if (!rect || rect.w < CROP_MIN_SIDE || rect.h < CROP_MIN_SIDE)", up)
        self.assertIn("if (session.autoSplit) {", up, "扫描卷松开鼠标即切")
        self.assertIn('finishCrop(session, "split");', up)
        self.assertLess(up.index("if (session.autoSplit) {"), up.index("showCropActions(session);"),
                        "自动切题的判断必须排在弹动作条之前")
        self.assertIn("showCropActions(session);", up,
                      "普通题松开鼠标仍要选动作，不能直接吞框")
        self.assertNotIn("finishCrop(session);", up)
        bar = fn_body(js, "showCropActions")
        self.assertIn('actionButton("提取为本题配图"', bar)
        self.assertIn('actionButton("切分新题"', bar)
        self.assertIn('actionButton("取消"', bar)
        self.assertIn("canSplitItem(session.item)", bar,
                      "「切分新题」只许出现在中转站里的题上")
        self.assertIn("(item.pendingId || item.galleryPage)", fn_body(js, "canSplitItem"),
                      "原卷页框出来的格子还没有 pendingId，也要能切题")
        close = fn_body(js, "closeCrop")
        self.assertIn("lensCanvas.parentNode.removeChild(lensCanvas);", close,
                      "左键松开后放大镜必须消失")
        self.assertIn('window.removeEventListener("mouseup", onCropUp, true);', close)

    def test_07_the_cropped_bytes_land_in_the_pending_pool_first(self) -> None:
        """中转站里的题：配图字节随草稿一起进 pending_assets/，主库一个字节都不碰。"""
        js = read("plugin.js")
        finish = fn_body(js, "finishCrop")
        self.assertIn("item.cropAsset = { id: assetId, data_url: dataUrl };", finish)
        self.assertIn("stashOne(item, metaFor(item, {}), false, true)", finish,
                      "只补配图、不改题干：缺答案也不能拦住配图入池")
        self.assertIn('if (mode === "split")', finish)
        self.assertIn("splitFromCrop(item, dataUrl,", finish)
        self.assertIn("item.cropAsset = null;", finish,
                      "存过之后必须清掉，否则下一次保存又写一份重复配图")
        stash = fn_body(js, "stashOne")
        self.assertIn("payload.questions[0].assets = [", stash)
        self.assertIn("data_url: String(item.cropAsset.data_url || \"\")", stash)

    def test_10_split_from_crop_makes_a_real_pending_question(self) -> None:
        """「切分新题」必须真的落一道待审题（带原卷页号），而不是只在界面上多一格。"""
        split = read("ui_split.js")
        call = fn_body(split, "splitFromCrop")
        self.assertIn('hostCall("pending.save_draft"', call)
        self.assertIn("batch_id: item.batchId", call)
        self.assertIn("page_no: pageNo", call)
        self.assertIn('origin: "editor.split"', call)
        self.assertIn('position: "top"', call, "新题必须置顶，老师马上能补录题干")
        placeholder = fn_body(split, "placeholderDoc")
        self.assertIn("框选切题", placeholder)
        self.assertIn("已从原卷第 ", placeholder)
        # 插件分包后仍要挂进整包：index.html 先加载它，plugin.js 再接线。
        html = read("index.html")
        self.assertIn('<script src="ui_split.js"></script>', html)
        self.assertIn(
            "splitFromCrop: uiSplit.splitFromCrop",
            read("plugin.js"),
            "plugin.js 没把切题通道交给切图台",
        )

    def test_08_the_global_paste_stays_out_of_the_way_while_cropping(self) -> None:
        """切图台开着的时候，全局粘贴不许把这张图当成新卷子吞进批次。

        接收区自己排在切图台之前建块，问「开着没」只能走 plugin.js 交进来的迟到取用
        ``cropOpen``，不能按值抓 uiCrop 那个还没诞生的对象。
        """
        js = read("plugin.js")
        wiring = js[js.index("var uiIntake = window.JzoEditorIntake.create({"):]
        wiring = wiring[:wiring.index("  });")]
        self.assertIn("cropOpen: function () { return uiCrop.isOpen(); },", wiring,
                      "plugin.js 没把切图台的开关迟到交给接收区")
        paste = js[js.index('window.addEventListener("paste", function (event)'):]
        paste = paste[:paste.index("});")]
        self.assertIn("if (cropOpen()) return;", paste)
        drop = js[js.index('root.addEventListener("drop"'):]
        drop = drop[:drop.index("});")]
        self.assertIn("if (cropOpen()) return;", drop)

    def test_09_the_pending_bank_echoes_the_real_asset_address(self) -> None:
        """插件切完图要知道底座把字节写到哪去了：题面里的 uri 得跟着换。"""
        bank = (ROOT / "app" / "core" / "pending_bank.py").read_text(encoding="utf-8")
        self.assertIn('"saved_assets":', bank)
        self.assertIn("PENDING_ASSET_URI_PREFIX", bank)


class EditorSplitBoardContractTest(unittest.TestCase):
    """悬浮切题画板：入口、遮罩与滚动锁、Ctrl+滚轮缩放、确认/放弃两条路。"""

    def test_01_the_board_is_loaded_wired_and_old_boxes_are_gone(self) -> None:
        html = read("index.html")
        self.assertIn('<link rel="stylesheet" href="split_board.css">', html)
        self.assertIn('<script src="ui_split_board.js"></script>', html)
        self.assertIn('id="edSplitBoardBtn"', html)
        self.assertLess(html.index("ui_crop.js"), html.index("ui_split_board.js"),
                        "画板要用切图台的裁像素通道，必须排在它后面")
        self.assertLess(html.index("ui_split_board.js"), html.index("ui_columns_scan.js"),
                        "画板模块必须先于纯图片卷左栏加载")
        self.assertLess(html.index('id="edAddIllustration"'), html.index('id="edSplitBoardBtn"'),
                        "【重新切题】排在【添加配图】右边，工具条一律靠左追加")
        # 纸带坐标、骨架 DOM、缩放记忆三块拆出去，且都要先于画板加载。
        for module in ("split_board_geom.js", "split_board_dom.js", "split_board_zoom.js"):
            self.assertIn('<script src="%s"></script>' % module, html)
            self.assertLess(html.index(module), html.index("ui_split_board.js"),
                            module + " 必须在画板之前加载")
            self.assertTrue((DIST / module).is_file(), module + " 必须真的发货")
        # 原「左栏直接拖绿框」整块撤除，不许留下半截。
        self.assertNotIn("ui_page_boxes.js", html)
        self.assertNotIn("layout_boxes.css", html)
        self.assertFalse((DIST / "ui_page_boxes.js").exists())
        self.assertFalse((DIST / "layout_boxes.css").exists())
        js = read("plugin.js")
        self.assertIn("var uiSplitBoard = window.JzoEditorSplitBoard.create({", js)
        self.assertIn(
            "splitPageRegion: function () { return uiCrop.splitPageRegion.apply(uiCrop, arguments); },",
            js)
        self.assertIn(
            "splitSpanRegion: function () { return uiCrop.splitSpanRegion.apply(uiCrop, arguments); },",
            js)
        self.assertIn(
            "updatePageRegion: function () { return uiCrop.updatePageRegion.apply(uiCrop, arguments); },",
            js)
        self.assertIn(
            "updateSpanRegion: function () { return uiCrop.updateSpanRegion.apply(uiCrop, arguments); },",
            js)
        self.assertNotIn("JzoEditorPageBoxes", js)
        self.assertNotIn("renderPageBoxes", read("ui_columns_scan.js"))
        self.assertIn("splitBoardBtnEl: splitBoardBtnEl,", read("ui_dom.js"))

    def test_02_the_board_fills_the_viewport_and_locks_page_scroll(self) -> None:
        css = read("plugin.css")
        mask = rule_body(css, ".ed-sb-mask")
        self.assertIn("position: fixed", mask)
        self.assertIn("inset: 0", mask)
        board = rule_body(css, ".ed-sb-board")
        self.assertIn("position: absolute", board)
        self.assertIn("inset: 0", board, "画板自己就是屏幕，不再是一只居中弹窗")
        self.assertNotIn("width: min(68vw", board)
        self.assertNotIn("display: flex", board,
                        "上下控制栏不再占版面，画板不必再纵向分栏")
        # 2026-11-06 全屏沉浸：画板没有白底、圆角、边框、阴影。
        self.assertNotIn("border", board)
        self.assertNotIn("border-radius", board)
        self.assertNotIn("box-shadow", board)
        self.assertIn("background: transparent", board)
        scroll = rule_body(css, ".ed-sb-scroll")
        self.assertIn("position: absolute", scroll)
        self.assertIn("inset: 0", scroll, "纸带从屏幕顶端铺到底端")
        self.assertIn("overflow: auto", scroll)
        self.assertIn("background: transparent", scroll)
        self.assertIn("overscroll-behavior: contain", scroll)
        pages = rule_body(css, ".ed-sb-pages")
        self.assertIn("padding: 0", pages)
        self.assertIn("margin: 0 auto", pages)
        self.assertIn("background: rgba(18, 22, 28, 0.56)", mask)
        layer = rule_body(css, ".ed-sb-layer")
        self.assertIn("position: absolute", layer)
        self.assertIn("inset: 0", layer)
        self.assertIn("pointer-events: auto", layer)
        # 页缝只画虚线提示，不再给页面加边框，否则页与页之间会出现断口。
        page = rule_body(css, ".ed-sb-page {")
        self.assertNotIn("overflow", page, "单页容器不许裁剪，跨页框要能横穿")
        self.assertNotIn("border", page)
        self.assertIn("border-top: 1px dashed", rule_body(css, ".ed-sb-page + .ed-sb-page::before"))
        box = rule_body(css, ".ed-sb-box")
        self.assertIn("position: absolute", box)
        self.assertIn("pointer-events: auto", box)
        self.assertIn("touch-action: none", box)
        self.assertIn("border-style: dashed", rule_body(css, ".ed-sb-box.is-new"))
        for key in ("nw", "n", "ne", "e", "se", "s", "sw", "w"):
            rule_body(css, '.ed-sb-handle[data-handle="%s"]' % key)
        # 控制条透明、零内边距，子元素绝对悬浮在四角。
        head = rule_body(css, ".ed-sb-head,")
        self.assertIn("background: transparent", head)
        self.assertIn("padding: 0", head)
        self.assertIn("border: 0", head)
        self.assertIn("pointer-events: none", head)
        self.assertIn("position: absolute", head)
        module = read("ui_split_board.js")
        for needle in ("Ctrl", "wheel", "Escape", "Enter", "Delete", "Backspace",
                       'body.classList.add("ed-sb-locked")'):
            self.assertIn(needle, module)
        floating = rule_body(css, ".ed-sb-title,")
        self.assertIn("position: absolute", floating,
                      "标题、缩放比例、操作按钮全部绝对悬浮在四角")
        self.assertIn(".ed-sb-actions {\n  right: 16px;", css,
                      "操作按钮悬浮在右下角")

    def test_03_zoom_is_cursor_anchored_smoothed_and_remembered(self) -> None:
        module = read("ui_split_board.js")
        self.assertIn("event.ctrlKey || event.metaKey", module)
        self.assertIn("Math.exp(-event.deltaY * 0.0015)", module)
        self.assertIn("getBoundingClientRect()", module)
        self.assertIn("requestAnimationFrame(step)", module)
        self.assertIn("scroll.scrollLeft += after.left + pointX * next - clientX", module)
        self.assertIn("scroll.scrollTop += after.top + pointY * next - clientY", module)
        # 跨批次记忆：比例只许走宿主数据舱，插件侧绝不碰 localStorage。
        self.assertNotIn("localStorage", module)
        self.assertIn("split_board_zoom.js", read("index.html"))
        zoom = read("split_board_zoom.js")
        self.assertIn('hostCall("draft.save"', zoom)
        self.assertIn('hostCall("draft.load"', zoom)
        self.assertIn('key: key', zoom)
        self.assertIn("catch (error)", zoom)
        self.assertNotIn("localStorage", zoom)

    def test_04_confirm_reuses_pending_and_discard_never_writes(self) -> None:
        module = read("ui_split_board.js")
        self.assertIn('hostCall("pending.set_pages"', module)
        self.assertIn('hostCall("pending.delete"', module)
        self.assertIn("splitPageRegion(pseudo, pieces[0].region", module)
        self.assertIn("updatePageRegion(item, pieces[0].region", module)
        self.assertIn("splitSpanRegion(pseudo, pieces", module)
        self.assertIn("updateSpanRegion(item, pieces", module)
        # 跨页框落库：按页拆块，但同一 pending_id 的块仍是同一道题。
        self.assertIn("geom.piecesOf(rec.rect", module)
        self.assertIn("region.pending_id = rec.pending_id", module)
        # 放弃路径只拆 DOM，绝不碰任何后端写接口。
        discard = module[module.index("    function discard("):]
        discard = discard[:discard.index("    function close(")]
        self.assertNotIn("hostCall(", discard)
        self.assertIn("close()", discard)
        self.assertIn("原卷一个字节都没动", discard)

    def test_05_geometry_keeps_one_coordinate_system_for_the_whole_strip(self) -> None:
        geom = read("split_board_geom.js")
        self.assertIn("function piecesOf(", geom)
        self.assertIn("function rectOfPieces(", geom)
        self.assertIn("function rectBetween(", geom)
        self.assertIn("function clampRect(", geom)
        self.assertIn("function layout(", geom)
        # 拆分只按页界线机械切，不改框形状：同一矩形拆出的块上下沿应当对齐。
        self.assertIn("rect.y + rect.h", geom)


class EditorLeftPaperStripContractTest(unittest.TestCase):
    """左栏整卷纸带（2026-11-06 阶段一）：无缝拼接、只读绿框、提示块撤除。"""

    def test_01_the_gray_caption_block_is_gone(self) -> None:
        module = read("ui_columns_scan.js")
        self.assertNotIn("ed-img-caption", module, "左栏页底提示文字块必须整块撤除")
        self.assertNotIn("已自动切出", module)
        self.assertNotIn("pooledCount", module)
        self.assertNotIn("pooledCount", read("plugin.js"))

    def test_02_pages_join_into_one_strip(self) -> None:
        module = read("ui_columns_scan.js")
        self.assertIn('"ed-page-sep"', module)
        self.assertIn('"原卷第 " + pageNo + " 页"', module)
        css = read("plugin.css")
        cell = rule_body(css, ".ed-img-cell.ed-page-cell {")
        self.assertIn("padding: 0", cell, "页面不再留内衬，纸带要无缝相接")
        self.assertIn("border-bottom: 0", cell)
        self.assertIn("border-top: 1px dashed", rule_body(css, ".ed-page-sep::before"))
        self.assertIn("position: absolute", rule_body(css, ".ed-img-cell.ed-page-cell .ed-img-tools"))

    def test_03_green_boxes_are_read_only(self) -> None:
        module = read("ui_columns_scan.js")
        self.assertIn('"ed-green-layer"', module)
        self.assertIn('"ed-green-box"', module)
        self.assertIn('"data-pending-id"', module)
        self.assertIn("ed-green-box", read("ui_columns.js"),
                      "当前题对应的绿框要能加深，但只改 class")
        css = read("plugin.css")
        self.assertIn("pointer-events: none", rule_body(css, ".ed-green-layer"))
        box = rule_body(css, ".ed-green-box {")
        self.assertIn("pointer-events: none", box)
        self.assertIn("position: absolute", box)
        self.assertIn("border: 2px solid #2f9e5a", box)
        self.assertNotIn("cursor: move", box)


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
            self.assertEqual(item["schema_version"], "2.1")

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
        js = read("dev_fixtures.js")
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


class EditorThreeSegmentPanelTest(unittest.TestCase):
    """军令 #29：辅助栏三段式排版 + 双侧呼吸灯 + 幽灵胶囊。"""

    def test_01_the_panel_is_three_fixed_segments(self) -> None:
        """段一顶部固定（当前题与私有元数据）、段二自己滚、段三底部固定。"""
        panel = panel_only(read("index.html"))
        for node_id in ("epHead", "epHeadNo", "epScore", "epMetaSec", "epMetaFold",
                        "epMetaSummary", "epDock", "epViewNote"):
            self.assertIn(f'id="{node_id}"', panel, f"辅助栏缺少 {node_id}")
        # 三段的先后顺序不能乱：头 → 滚动区 → 脚
        self.assertLess(panel.index('id="epHead"'), panel.index('id="epScroll"'))
        self.assertLess(panel.index('id="epScroll"'), panel.index('id="epDock"'))
        css = read("plugin.css")
        self.assertIn("flex-direction: column", rule_body(css, ".ep-root"))
        self.assertIn("overflow-y: auto", rule_body(css, ".ep-scroll"))

    def test_01b_the_head_tools_share_one_row(self) -> None:
        """军令 #30 + 瘦身令：返回列表 + 源码/卡片 + 布局必须挤在段一同一行，按钮不带图标。"""
        panel = panel_only(read("index.html"))
        tools = panel[panel.index('id="epHeadTools"'):]
        tools = tools[:tools.index("</div>", tools.index('id="epSwap"'))]
        for node_id in ("epBackList", "epFmtLatex", "epFmtBoxed", "epSwap"):
            self.assertIn(f'id="{node_id}"', tools, f"死锁区同一行缺少 {node_id}")
        self.assertIn(">源码<", panel, "格式一必须改名叫【源码】")
        self.assertIn(">卡片<", panel, "格式二必须改名叫【卡片】")
        self.assertNotIn("格式一", read("index.html"))
        self.assertNotIn("格式二", read("index.html"))
        css = read("plugin.css")
        row = rule_body(css, ".ep-head-tools")
        self.assertIn("display: flex", row)
        self.assertIn("gap: 4px", row)
        self.assertIn("flex: 0 0 auto", rule_body(css, ".ep-head-tools .ep-btn"),
                      "三只控件按文字宽度排，不许被 flex 拉满整行")

    def test_01c_the_clean_button_is_named_for_the_current_question(self) -> None:
        """清洗按钮的改名护栏：只清当前题、只规范化 LaTeX，文案就得把这两件事说清。

        旧名【AI 清洗公式】已经复发过一次——它既不是模型决定改什么，也不止管公式，
        会让人以为点了就送去问 AI。所以护栏钉四层：辅助栏文案、整页无旧名、
        清单命令标题、契约文档命令表标题列。
        """
        panel = panel_only(read("index.html"))
        self.assertIn('id="epAiClean"', panel, "按钮 id 是既有回填通道的锚点，不许跟着文案改")
        self.assertIn(">清洗当前题 LaTeX<", panel, "清洗按钮必须叫【清洗当前题 LaTeX】")
        html = read("index.html")
        self.assertNotIn("AI 清洗公式", html, "整页不许再留旧名【AI 清洗公式】")
        commands = {item["id"]: item for item in manifest()["contributes"]["commands"]}
        self.assertEqual(commands["org.jiuzhang.action.process.clean_latex"]["title"],
                         "清洗当前题 LaTeX", "清单里这条命令的标题要与按钮文案一致")
        spec = (ROOT / "docs" / "PLUGIN_SPEC.md").read_text(encoding="utf-8")
        rows = [line for line in spec.splitlines()
                if line.startswith("| `org.jiuzhang.action.process.clean_latex`")]
        self.assertEqual(len(rows), 1, f"命令表里该命令应当只有一行：{rows}")
        cells = [cell.strip() for cell in rows[0].strip().strip("|").split("|")]
        self.assertEqual(cells[1], "清洗当前题 LaTeX", "契约文档命令表的标题列要同步改名")
        self.assertNotIn("AI 清洗公式", spec, "契约文档全文不许再留旧名【AI 清洗公式】")

    def test_02_the_private_metadata_lives_in_the_head(self) -> None:
        """段一只放单题私有的六项：题号、题型、难度、分值、考向、标签。"""
        head = read("index.html")
        head = head[head.index('id="epHead"'):head.index('id="epScroll"')]
        for node_id in ("epQuestionNo", "epType", "epDifficulty", "epScore",
                        "epTagList", "epMounted"):
            self.assertIn(f'id="{node_id}"', head, f"段一缺少 {node_id}")
        # 段二不许再放单题私有的分值
        tail = read("index.html")
        tail = tail[tail.index('id="epScroll"'):]
        self.assertNotIn('id="epScore"', tail, "分值属于单题私有，不许落进批次段")

    def test_03_the_batch_section_folds_on_canvas_scroll(self) -> None:
        """画布一滚动就收成一行矮标题；鼠标停在标题上才展开，移开不收。"""
        js = read("plugin.js")
        self.assertIn('panelMetaSecEl.setAttribute("data-fold", "closed")', js)
        self.assertIn('panelMetaSecEl.setAttribute("data-fold", "open")', js)
        self.assertIn('panelMetaFoldEl.addEventListener("mouseenter", expandMetaSection)', js)
        # 移开鼠标不许收起：mouseleave 上不许挂收起动作
        self.assertNotIn('panelMetaFoldEl.addEventListener("mouseleave"', js,
                         "移开鼠标不许把老师正在填的批次字段收走")
        self.assertIn('if (raw.scroll) collapseMetaSection();', js)
        css = read("plugin.css")
        self.assertIn('[data-fold="closed"] .ep-fold-body', css, "折叠只由通用规则管，段二不再专属")

    def test_04_the_lamp_breathes_on_both_sides(self) -> None:
        """悬停 200ms：画布那道题与辅助栏边缘同时亮莫兰迪冷蓝的呼吸灯。"""
        js = read("plugin.js")
        self.assertIn("var LAMP_DELAY_MS = 200;", js)
        self.assertIn("var lampTimer = 0;", js)
        self.assertIn('publish("editor.canvas_state", { hover: index });', js)
        self.assertIn('publish("editor.canvas_state", { hover: -1 });', js)
        css = read("plugin.css")
        self.assertIn("@keyframes ep-lamp-breathe", css)
        self.assertIn("0%, 100% { opacity: 0.1; }", css)
        self.assertIn("50% { opacity: 0.4; }", css)
        self.assertIn("2s ease-in-out infinite", css)
        for selector in ('.ed-img-cell[data-lamp="on"]::after',
                         '.ed-src-cell[data-lamp="on"]::after',
                         '.ed-q-block[data-lamp="on"]::after',
                         '.ep-root[data-lamp="on"]::after'):
            self.assertIn(selector, css, f"{selector} 缺呼吸灯")
        # 减少动效时灯改成常亮，不许一呼一吸
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertIn("animation: none !important;", css)

    def test_05_the_ghost_capsule_takes_focus_without_a_click(self) -> None:
        """幽灵胶囊：虚线空壳 → 悬停 150ms 自己活过来接光标 → 打字出候选 → 回车上屏。"""
        js = read("plugin.js")
        self.assertIn("var GHOST_DELAY_MS = 150;", js)
        self.assertIn("var GHOST_TEXT = \"+ 请添加…\";", js)
        self.assertIn("rec.timer = window.setTimeout(function () { activateGhost(kind); }, GHOST_DELAY_MS);",
                      js)
        self.assertIn("rec.input.focus();", js)
        # 回车取第一条（候选与高亮都在响应式状态里）
        self.assertIn("if (ui[kind].items.length) {", js)
        self.assertIn("pickGhostItem(kind, ui[kind].active >= 0 ? ui[kind].active : 0);", js)
        # 候选菜单带路径：条目要走 resolveTopicPath，路径用「 › 」拼。
        self.assertIn("hostCall(\"bank.topics\", { q: query })", js)
        self.assertIn("resolveTopicPath(item.value && item.value.path, item.name)", js)
        self.assertIn(".join(\" › \")", js)
        # 宿主每 10 秒最多放 80 个请求：候选条数有上限，路径解析按层缓存。
        self.assertIn("var GHOST_TOPIC_LIMIT = 8;", js)
        self.assertIn("rows.slice(0, GHOST_TOPIC_LIMIT)", js)
        self.assertIn("function fetchTopicChildren(parentId)", js)
        # 打字别一口一个请求：等手停下来再查。
        self.assertIn("var GHOST_SEARCH_DELAY_MS = 180;", js)
        # UI 极致瘦身令（2026-11-02）：空胶囊是唯一的「这里能点」提示，移出鼠标只许睡回去
        self.assertNotIn("ui[kind].hidden", js, "显隐位已废：幽灵胶囊常驻，不再忽隐忽现")
        self.assertIn('ui[kind].state = "idle";', js)

    def test_06_the_score_goes_into_the_plugin_extension(self) -> None:
        """契约里没有分值字段：只进 extensions["org.jiuzhang.editor"].score。"""
        js = read("plugin.js")
        cell = fn_body(js, "questionFromParsed")
        self.assertIn("editorExt.score = scoreText;", cell)
        self.assertNotIn("doc.score", cell, "分值没有契约字段，不许往题目根字段塞")
        self.assertIn("if (panelScoreEl) entry.score = panelScoreEl.value;", js)
        self.assertIn("score: trunc(editorExt.score, 8),", js)

    def test_07_the_ledger_line_reports_two_numbers(self) -> None:
        """底段最下一行灰字：待入库：N · 已入库：M。"""
        js = read("plugin.js")
        pool = fn_body(js, "renderPool")
        self.assertIn('"待入库：" + counts.fresh', pool)
        self.assertIn('"已入库：" + counts.stored', pool)
        self.assertIn('poolEl.textContent = parts.join(" · ");', pool)

    def test_08_the_ghost_channel_is_declared_and_delivered(self) -> None:
        """跨帧联动只能走宿主总线：清单声明、宿主白名单、宿主投递三处都要有。"""
        self.assertIn("editor.canvas_state", manifest()["bus"]["subscribe"])
        self.assertIn("editor.canvas_state", manifest()["bus"]["publish"])
        host = stage_source()
        self.assertIn('"editor.canvas_state"', host, "宿主白名单里没有这条主题")
        self.assertIn('notify(panel, "editor.canvas_state"', host, "宿主没有把它投给右栏面板")
        whitelist = (ROOT / "app" / "core" / "plugins.py").read_text(encoding="utf-8")
        self.assertIn('"editor.canvas_state"', whitelist, "底座白名单里没有这条主题")

    def test_09_no_duplicate_ids_in_the_panel(self) -> None:
        """id 撞车会让 getElementById 取错节点：折叠层曾把「主体」输入框顶掉。

        判据取全页：画布与辅助栏是同一份 index.html 的两段 DOM，撞车一样要命。
        """
        html = read("index.html")
        found = re.findall(r'\bid="([^"]+)"', html)
        duplicates = sorted({node for node in found if found.count(node) > 1})
        self.assertEqual(duplicates, [], f"index.html 里有重号的 id：{duplicates}")
        # 折叠层与「主体」输入框必须各有一个自己的 id
        self.assertIn('id="epMetaFoldBody"', html)
        self.assertIn('id="epMetaBody"', html)
        self.assertNotIn('id="epMetaBody" class="ep-fold-body"', html)

    def test_10_the_intake_box_is_retired_and_only_the_basket_remains(self) -> None:
        """UI 极致瘦身令（2026-11-02）：辅助栏那只虚线接收框彻底下线，收件只有画布的收集筐。

        面板帧的全局 Ctrl+V 仍在——粘贴的截图经宿主中转入筐，与那只框无关；
        框本身既不许留 DOM，也不许留样式或拖拽监听。
        """
        html = read("index.html")
        js = read("plugin.js")
        css = read("plugin.css")
        for gone in ('id="epIntake"', "ep-intake", "panelIntakeEl"):
            self.assertNotIn(gone, html + js + css, f"{gone} 已随辅助栏接收区退场")
        self.assertIn('id="edBasket"', html, "画布右侧的文件收集筐是唯一收件处")
        self.assertIn("function collectToCanvas(", js, "面板帧的粘贴仍要经宿主转交进筐")
        self.assertIn('[data-fold="closed"] .ep-fold-body { display: none; }', css,
                      "折叠规则已通用化：带 data-fold 的段（批次元数据 / AI 帮改）共用一条")

    def test_11_a_late_receipt_never_erases_what_the_teacher_just_added(self) -> None:
        """回执晚到不许抹掉老师刚建档的学校：本地新增与本地摘掉分开记账。"""
        js = read("plugin.js")
        self.assertIn("function mergeSchools(details)", js)
        merge = fn_body(js, "mergeSchools")
        self.assertIn("panel.schoolAdded[id]", merge, "本地新增的学校必须被回执合并回来")
        self.assertIn("panel.schoolDropped[id]", merge, "老师摘掉的学校不许被旧回执请回来")
        self.assertIn("panel.schoolAdded[id] = true;", js)
        self.assertIn("panel.schoolDropped[String(record.id || \"\")] = true;", js)
        # 两处回执都走同一套合并
        self.assertIn("panel.schools = mergeSchools(details);", js)
        self.assertIn("panel.schools = mergeSchools(meta.school_details);", js)

    def test_12_a_stale_menu_reply_never_overwrites_a_fresh_one(self) -> None:
        """晚到的旧回执不许盖掉刚画出来的候选菜单：每份回执带序号。"""
        js = read("plugin.js")
        self.assertIn("var tagMenuSeq = 0;", js)
        tags = fn_body(js, "loadTags")
        self.assertIn("if (seq !== tagMenuSeq) return [];", tags)
        self.assertIn("ghostState.tag.seq !== seq", js)
        self.assertIn("ghostState.topic.seq !== seq", js)

    def test_13_the_machine_only_text_does_not_take_up_the_dock(self) -> None:
        """置信度占位与指标挂载点只给机器看：不许占段三的高度。"""
        css = read("plugin.css")
        self.assertIn(".ep-sr {", css)
        body = css[css.index(".ep-sr {"):css.index(".ep-sr {") + 320]
        self.assertIn("position: absolute;", body)
        self.assertIn("clip: rect(0, 0, 0, 0);", body)


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
        """军令 #23：假数据不进发行包——对外只有真实题库，运行期靠 dist/dev_fixtures.js 的内嵌块。"""
        names = self._names()
        offenders = [each for each in names if "/dev/" in each or each.endswith("fixtures.json")]
        self.assertEqual(offenders, [], f"发行包混进开发期文件：{offenders}")
        self.assertIn("org.jiuzhang.editor/dist/plugin.js", names)
        self.assertIn("org.jiuzhang.editor/dist/dev_fixtures.js", names)


class EditorDuplicatePoolScreenTest(unittest.TestCase):
    """军令 #32 · 第五步（S5）：重题池画布与交互的界面契约。

    契约测试读的是**整包源码**（index.html 按加载次序拼起来），钉的是「这一屏长什么样、
    谁能动、话怎么说」；真浏览器点击与像素描边归测试工程师的探针。
    """

    def test_01_pool_canvas_has_zero_buttons_and_no_source_pane(self) -> None:
        """判据 5.1：池子有自己的画布屏，左右都是渲染；这一屏一颗按钮都不许有（军令 #23 铁律）。"""
        html = read("index.html")
        pool = html[html.index('id="edPoolCanvas"'):html.index("批量条原是画布底下一条横条")]
        self.assertIn('id="edPoolMainBody"', pool, "左栏必须是主库原题的渲染容器")
        self.assertIn('id="edPoolIncomingBody"', pool, "右栏必须是池内这条的渲染容器")
        self.assertNotIn("<button", pool, "重题池画布里一颗按钮都不许有")
        self.assertNotIn("SourceBody", pool, "池画布不比源码：不许出现源码栏容器")
        self.assertIn('aria-label="重题池对比"', pool)

    def test_02_four_actions_live_in_the_panel_and_two_are_retired(self) -> None:
        """判据 5.1/5.4：辅助栏四颗动作；【覆盖】【放弃】一律不做，界面不许留入口。"""
        html = read("index.html")
        panel = panel_only(html)
        pool = html[html.index('id="epPoolSec"'):html.index('id="epPoolBack"')]
        for label in ("合并元数据", "新增解析", "不重复", "删除"):
            self.assertIn(">" + label + "<", pool, f"辅助栏缺池内动作【{label}】")
        js = read("plugin.js")
        self.assertNotIn('runAction("overwrite")', js, "【覆盖】已退役，不许复活")
        self.assertNotIn('runAction("abandon")', js, "【放弃】已退役，不许复活")
        self.assertIn('id="epPoolDelModal"', panel, "【删除】必须走二次确认")
        self.assertIn('class="ep-btn ep-btn-danger" id="epPoolDelOk"', panel,
                      "确认那颗复用 #46 红按钮的样式，不再长第二套确认")

    def test_03_red_lamp_retired_from_review_and_amber_is_new(self) -> None:
        """判据 5.2：红色呼吸灯退出审核画布（只在池画布）；琥珀灯是新造的，常驻呼吸且减动效退静态。"""
        css = read("plugin.css")
        self.assertIn('.ed-root[data-mode="pool"][data-dup="on"]::after', css,
                      "红灯必须收口到池画布那一屏")
        self.assertNotIn('\n.ed-root[data-dup="on"]', css,
                         "不带 data-mode 的红灯选择器会让审核画布重新亮红")
        self.assertIn("--amber: #c08a2e;", css, "琥珀色必须是新令牌 #c08a2e")
        self.assertIn('.ed-q-block[data-amber="on"]::before', css, "题卡琥珀灯（与青黛 ::after 分轴共存）")
        self.assertIn('.ep-root[data-amber="on"]::before', css, "辅助栏边缘琥珀灯：与题卡同时亮")
        self.assertIn("prefers-reduced-motion", css)

    def test_04_tiers_are_session_only_and_empty_pool_stays_blank(self) -> None:
        """判据 5.3：三档默认宽、切档即时带 ?tier= 重取、档位只在内存；已裁决条目不复活；空池留白。"""
        js = read("plugin.js")
        self.assertIn('var tier = "loose";', js, "默认档位必须是宽")
        self.assertIn('hostCall("pending.pool_list", { tier: tier })', js, "每次现传档位")
        self.assertIn('hostCall("pending.pool_get", { pool_id: poolId, tier: tier })', js)
        self.assertIn('if (["strict", "standard", "loose"].indexOf(value) < 0 || value === tier) return;',
                      js, "只认三档名，同档不重取")
        # P0 新义：**有货默认就展开、空池仍隐藏、入口钮只在已收起时出现**。
        # 收起只剩一把锁（池里没货）；入口钮那段判断照留，作为「以后有收起路径」的备用通路。
        self.assertIn("sectionEl.hidden = !selectedEntry && !(revealed && entries.length);", js,
                      "空池整段收起：不许写占位文案（这条锁不许因为默认展开而拆掉）")
        self.assertIn("entryEl.hidden = !(entries.length && !revealed && !selectedEntry);", js,
                      "【重题池 N 条】只在已收起时挂着：默认展开后它不该出现在有货的池子上")
        self.assertIn('entryEl.textContent = "重题池 " + entries.length + " 条";', js,
                      "入口钮要带条数，老师才知道有多少待裁决")
        self.assertIn('if (entryEl) entryEl.addEventListener("click", reveal);', js,
                      "入口钮必须真绑了点击，不是画一颗死按钮")
        # 默认态本身也得钉住：初值回退成 false 就是「要点一下才看得见」，P0 直接失守。
        self.assertIn("var revealed = true;", js, "池子段默认展开：revealed 初值必须是 true")
        self.assertNotIn("var revealed = false;", js,
                         "回退警报：revealed 初值又变回 false，池子成了点了才展开")
        # 契约：ui_dom.js 里取的每个 epPool* 节点都必须在 index.html 里真存在；
        # 且「入口钮 → 条目 → 画布 show」这条链必须是真人可点的（静态可校）。
        html = read("index.html")
        dom_js = read("ui_dom.js")
        claimed = set(re.findall(r'getElementById\("(epPool[A-Za-z]*)"\)', dom_js))
        self.assertTrue(claimed, "ui_dom.js 一个 epPool* 节点都没取，扫描器无账可校")
        missing = sorted(i for i in claimed if f'id="{i}"' not in html)
        self.assertEqual(missing, [], f"这些 epPool* 节点在 index.html 里不存在：{missing}")
        # 负向对照：检测本身不许是瞎子——凭空捏一个 id 必须被判成缺失。
        self.assertEqual([i for i in ("epPoolNoSuchNode",) if f'id="{i}"' not in html],
                         ["epPoolNoSuchNode"], "缺失检测失能：假 id 没被抓出来")
        self.assertIn('id="epPoolEntry" hidden', html, "辅助栏那颗入口钮必须在 HTML 里")
        self.assertIn('aria-controls="epPoolSec"', html, "入口钮要指到它展开的那一段")
        self.assertIn('notifyCanvas("open", detail)', js, "点条目必须把详情递给画布")
        self.assertIn("showPoolReview", js, "画布那一屏的渲染入口必须存在")
        # 空池不许有占位文案：只看池子那一屏真会上屏的字（注释里提一句「不写暂无重题」不算违规；
        # 「本批没有重复题」是 #31 批次清退的账目文案，不住在池子这一屏）。
        pool_js = read("ui_pool_panel.js")
        for text in re.findall(r'textContent\s*=\s*"([^"]*)"', pool_js):
            for placeholder in ("暂无重题", "池子是空的", "没有重复"):
                self.assertNotIn(placeholder, text, "空池只能留白，不许写占位文案")
        self.assertNotIn('class="ep-pool-empty"', read("index.html"), "不许长出一块空态占位 DOM")
        html = read("index.html")
        self.assertIn('class="ep-seg-btn is-on" data-tier="loose"', html)

    def test_05_approve_all_scans_the_lamp_first(self) -> None:
        """判据 43：【全部入库】先整批扫琥珀灯，有未清项一题都不存并跳到最上面那道；池内题不再特判扣数。"""
        js = read("plugin.js")
        run = fn_body(js, "runApproveAll")
        self.assertIn("var found = scan();", run)
        self.assertLess(run.index("var found = scan();"), run.index("pending.approve"),
                        "必须先扫灯再入库")
        self.assertIn("if (jumpTo) jumpTo(found.top);", run, "有未清项要跳到最上面那道")
        self.assertIn("blocked: true", run)
        self.assertLess(run.index("blocked: true"), run.index("pending.approve"),
                        "拦下来时一题都不许存")
        self.assertNotIn("pooled", run, "池内题已由后端从待审清单摘走，前端不许再特判扣一遍数")
        targets = fn_body(js, "approveTargets")
        self.assertIn('item.pendingId && item.status !== "stored"', targets,
                      "只处理未入库的题（§2 第 46 条）")

    def test_06_the_panel_and_canvas_split_by_from(self) -> None:
        """两帧只经宿主总线对话：同一主题靠 from 分头，新增主题实数就是两条。"""
        bus = manifest()["bus"]
        self.assertEqual(len(set(bus["subscribe"]) | set(bus["publish"])), 17,
                         "订 14 ∪ 发 12 = 17 个主题名；查重三栏新增 editor.dup_compare")
        for topic in ("editor.pool_review", "editor.batch_review", "editor.dup_compare"):
            self.assertIn(topic, bus["subscribe"])
            self.assertIn(topic, bus["publish"])
        protocol = read("core_protocol.js")
        self.assertIn('if (poolFrom === "canvas" && poolPayload.phase === "closed") onPoolCanvasClosed();',
                      protocol, "画布按 Esc 自己退池，辅助栏的选中要跟着放开")
        self.assertIn('onDupCompareClosed()', protocol,
                      "画布按 Esc 退查重三栏，辅助栏的裁判台要跟着收起")
        stage = stage_source()
        self.assertIn('notify(tab, "editor.pool_review", pair.payload)', stage)
        self.assertIn('notify(panel, "editor.batch_review", pair.payload)', stage)
        self.assertIn('notify(tab, "editor.dup_compare", pair.payload)', stage)
        self.assertIn('notify(panel, "editor.dup_compare", pair.payload)', stage)


class EditorExportIntegrityTest(unittest.TestCase):
    """军令 #32 · S5c：导出对象里不许挂「函数已删、名字还在」的悬挂标识符。

    ``node --check`` 只看语法、开机链之外的分支只在调用时抛，所以这条判据按**声明现场**判：
    ``create()`` 的 ``return { key: value }`` 里那个 ``value``，必须能在同一支文件里找到它的
    函数声明 / 变量声明 / 形参位置。扫描器自带负向对照，防止「扫不到」被当成「没问题」。
    """

    ENTRY = re.compile(r"^\s{2,}([A-Za-z_$][\w$]*)\s*:\s*([A-Za-z_$][\w$]*)\s*,?\s*$", re.M)
    LITERALS = {"function", "false", "true", "null", "undefined", "this",
                "arguments", "global", "window"}

    def _declared(self, src: str, name: str) -> bool:
        patterns = [rf"function\s+{name}\s*\(",
                    rf"\b(?:var|let|const)\b[^\n]*\b{name}\b\s*(?:=|,|\)|;)",
                    rf"[(,]\s*{name}\s*(?:[,)]|\s*=>)",
                    rf"\b{name}\s*=>",
                    rf"\b{name}\s*=\s*deps\."]
        return any(re.search(p, src) for p in patterns)

    def _dangling(self, src: str) -> list[tuple[str, str]]:
        return [(m.group(1), m.group(2)) for m in self.ENTRY.finditer(src)
                if m.group(2) not in self.LITERALS and not self._declared(src, m.group(2))]

    def test_01_scanner_is_not_vacuous(self) -> None:
        """负向对照：导出名没有声明现场时，扫描器必须点名。"""
        probe = ('(function (global) {\n  function create() {\n    function keep(a) { return a; }\n'
                 '    return {\n      keep: keep,\n      gone: gone,\n    };\n  }\n})(window);\n')
        self.assertEqual(self._dangling(probe), [("gone", "gone")])

    def test_02_no_dangling_export_in_dist(self) -> None:
        """dist 每一支 JS 的导出项都要有声明现场——录题工作台的开机链靠这个才跑得完。"""
        offenders = []
        files = sorted(DIST.glob("*.js"))
        self.assertTrue(files, "dist/ 下必须扫到 JS")
        for path in files:
            for key, value in self._dangling(path.read_text(encoding="utf-8")):
                offenders.append(f"{path.name}:{key}: {value}")
        self.assertEqual(offenders, [], "这些导出名在所属文件里没有声明现场（函数删了、名字还挂着）")

    def test_03_clean_exam_source_is_gone_for_good(self) -> None:
        """判据 1.6 的收口形状：本地清洗器整体退场，名字一处都不留（含导出位）。"""
        bundle = read("plugin.js")
        self.assertNotIn("cleanExamSource", bundle,
                         "清洗规则已归底座，插件里不许再留这个名字（尤其不许只留导出位）")


if __name__ == "__main__":
    unittest.main()
