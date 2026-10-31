"""录题工作台 v2（org.jiuzhang.editor，军令 #23 阶段 1）契约测试。

真机三栏与 KaTeX 渲染由 ``tools/editor_probe.py`` 取证；这里钉住可静态判定的部分：

- 清单只申请画布舞台与题库读写，阶段 1 不抢右栏插槽、不要 AI 权限；
- 画布内只有三栏（左原图 | 中全量 exam-zh 源码 | 右渲染），**没有任何表单控件**；
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


class EditorManifestTest(unittest.TestCase):
    def test_01_manifest_passes_host_validation(self) -> None:
        info = validate_plugin(PLUGIN_DIR, manifest())
        self.assertEqual(info["id"], "org.jiuzhang.editor")
        self.assertIn("stage.center", info["slots"])
        self.assertIn("question.edit", info["capabilities"])
        self.assertEqual(sorted(info["permissions"]),
                         ["assets:write", "questions:read", "questions:write"])

    def test_02_stage_is_singleton_with_priority(self) -> None:
        stage = manifest()["stage"]
        self.assertEqual(stage["region"], "center")
        self.assertEqual(stage["mode"], "takeover")
        self.assertEqual(stage["priority"], 65)
        self.assertIs(stage["singleton"], True)
        self.assertLessEqual(len(stage["title"]), 24)

    def test_03_sidebar_slot_is_not_claimed_yet(self) -> None:
        """阶段 1 只搭画布骨架：右栏辅助面板连同 ai:invoke 一起留到阶段 2/3。"""
        self.assertEqual(manifest()["slots"], ["stage.center"])
        self.assertNotIn("ai:invoke", manifest()["permissions"])

    def test_04_bus_subscriptions_match_delivery(self) -> None:
        bus = manifest()["bus"]
        self.assertEqual(sorted(bus["subscribe"]),
                         ["editor.apply_patch", "system.open_editor", "ui.params.changed"])
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
            "var(--w-image) var(--split-w) var(--w-source) var(--split-w) minmax(0, 1fr)", css)
        self.assertIn("--split-w: 6px", css)
        self.assertIn("--pane-min: 28px", css, "拖到极窄缝也不能归零")
        self.assertIn("--void: #fafafa", css, "短栏留白的极淡底色")
        self.assertIn("cursor: col-resize", css)

    def test_06_drag_is_clamped_and_keyboard_usable(self) -> None:
        js = read("plugin.js")
        self.assertIn("var PANE_MIN = 28", js)
        self.assertIn("var SPLIT_W = 6", js)
        self.assertIn("function clampValue(value, min, max)", js)
        self.assertIn("image = clampValue(state.widths.image, PANE_MIN", js)
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
        cleaner = js[js.index("function cleanExamSource("):js.index("// ---------- 假数据")]
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

    def test_02_stage_one_never_writes_to_the_bank(self) -> None:
        """阶段 1 只做骨架：写库通道整体缺席，保存命令要显式回绝而不是偷偷落库。"""
        js = read("plugin.js")
        for forbidden in ("bank.create", "bank.update", "bank.delete", "asset.upload"):
            self.assertNotIn(forbidden, js, f"阶段 1 不得接入 {forbidden}")
        self.assertIn("保存入库在阶段 2 接入", js)

    def test_03_request_ids_are_host_safe(self) -> None:
        """宿主 BAD_REQUEST_ID 只认 ^[A-Za-z0-9_-]{1,80}$，带点号必被拒发。"""
        js = read("plugin.js")
        lines = [each.strip() for each in js.splitlines() if 'var id = "edv2"' in each]
        self.assertEqual(len(lines), 1, lines)
        self.assertEqual(lines[0], 'var id = "edv2" + requestSeq + "-" + Date.now().toString(36);')
        # Date.now().toString(36) 只产出 [0-9a-z]，拼出来的 id 不含点号
        self.assertRegex("edv21-" + format(1730000000000, "x"), r"^[A-Za-z0-9_-]{1,80}$")

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
            self.assertIn("\\begin{question}", source)
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
