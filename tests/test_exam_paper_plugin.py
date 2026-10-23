"""试卷排版插件（org.jiuzhang.exam-paper）契约测试：军令 #13 任务 6。

真机排版由 ``tools/exam_paper_probe.py`` 取证；这里守的是可静态判定的底线：

- 清单能过宿主校验，只声明 stage.center + question.card，权限只读；
- A4 度量、大题标号、涂卡区、密封线四件套在 CSS/JS 里真的落到代码上；
- 「日常小练 / 标准答题卡」两种模板可切换，且标准卡不泄露题干（答题卡只给作答位）；
- 插件只吃宿主总线与本地资源：不联网、不碰宿主 DOM、不写 localStorage、不夹带内联脚本；
- 打包器产出的 zip 顶层就是插件 id。

运行：``.venv/Scripts/python.exe -m unittest tests.test_exam_paper_plugin``
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
PLUGIN_ID = "org.jiuzhang.exam-paper"
PLUGIN_DIR = ROOT / "plugins" / PLUGIN_ID
DIST = PLUGIN_DIR / "dist"


def read(name: str) -> str:
    return (DIST / name).read_text(encoding="utf-8")


def manifest() -> dict:
    return json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))


class ExamPaperManifestTest(unittest.TestCase):
    def test_01_manifest_passes_host_validation(self) -> None:
        info = validate_plugin(PLUGIN_DIR, manifest())
        self.assertEqual(info["id"], PLUGIN_ID)
        self.assertIn("stage.center", info["slots"])
        self.assertIn("question.card", info["slots"])
        self.assertTrue(info["entry_url"].startswith("/plugin-assets/"))

    def test_02_stage_is_single_takeover_tab(self) -> None:
        stage = manifest()["stage"]
        self.assertEqual(stage["region"], "center")
        self.assertEqual(stage["mode"], "takeover")
        self.assertIs(stage["singleton"], True)
        self.assertLessEqual(len(stage["title"]), 24, "舞台页签标题不得超过 24 字")

    def test_03_permissions_are_read_only(self) -> None:
        self.assertEqual(manifest()["permissions"], ["questions:read"])
        self.assertIn("paper.generate", manifest()["capabilities"])

    def test_04_bus_only_subscribes_basket_refresh(self) -> None:
        bus = manifest()["bus"]
        self.assertEqual(sorted(bus["subscribe"]), ["basket.changed", "stage.tab.activated"])
        self.assertEqual(bus["publish"], ["region.dock"])

    def test_05_license_ships_full_apache_text(self) -> None:
        text = (PLUGIN_DIR / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License", text)
        self.assertIn("Version 2.0, January 2004", text)
        self.assertGreater(len(text), 10000, "LICENSE 必须是 Apache-2.0 全文，不是一句声明")

    def test_06_no_backend_entry(self) -> None:
        self.assertNotIn("backend", manifest())
        self.assertFalse((PLUGIN_DIR / "backend").exists())


class ExamPaperLayoutContractTest(unittest.TestCase):
    def test_01_a4_geometry_is_in_mm(self) -> None:
        css = read("plugin.css")
        js = read("plugin.js")
        self.assertIn("--ep-page-w: 210mm", css)
        self.assertIn("--ep-page-h: 297mm", css)
        self.assertIn("@page", css)
        self.assertIn("size: A4", css)
        self.assertIn("var PAGE_W = 210 * MM;", js)
        self.assertIn("var PAGE_H = 297 * MM;", js)

    def test_02_four_sections_and_major_numbering(self) -> None:
        js = read("plugin.js")
        for title in ("一、选择题", "二、填空题", "三、解答题", "四、其他题目"):
            self.assertIn(title, js)
        self.assertIn("entry.no + \".\"", js, "题号必须连续落到每道题前面")

    def test_03_pagination_moves_overflow_to_next_sheet(self) -> None:
        js = read("plugin.js")
        self.assertIn("function overflows(inner)", js)
        self.assertIn("CONTENT_H", js)
        self.assertIn("sectionEl.removeChild(node)", js, "超页的题必须整题挪走，不许拦腰切断")
        self.assertIn('newSheet("practice", false', js)
        self.assertIn('newSheet("card", false', js)

    def test_04_practice_mode_has_choice_columns_and_answer_space(self) -> None:
        css = read("plugin.css")
        js = read("plugin.js")
        self.assertIn("grid-template-columns: 1fr 1fr", css)
        self.assertIn(".ep-options", css)
        self.assertIn(".ep-line", css)
        self.assertIn(".ep-work", css)
        self.assertIn('entry.group === "blank"', js)
        self.assertIn('entry.group === "solution"', js)

    def test_05_omr_bubbles_and_answer_boxes(self) -> None:
        css = read("plugin.css")
        js = read("plugin.js")
        self.assertIn(".ep-bubble", css)
        self.assertIn("border-radius: 50%", css)
        self.assertIn("function omrRow(entry)", js)
        self.assertIn("function answerBox(entry)", js)
        self.assertIn(".ep-answer-box-area", css)

    def test_06_seal_line_is_vertical_dashed(self) -> None:
        css = read("plugin.css")
        js = read("plugin.js")
        self.assertIn(".ep-seal", css)
        self.assertIn("writing-mode: vertical-rl", css)
        self.assertIn("密封线内不得答题", js)
        self.assertIn("border-left: 1px dashed", css)

    def test_07_card_mode_never_prints_stems(self) -> None:
        js = read("plugin.js")
        card = js.split("function buildCard(entries)")[1].split("// ---------- 渲染与缩放")[0]
        self.assertNotIn("appendRich", card, "答题卡只给作答位，不回抄题干")
        self.assertNotIn("question.stem", card)

    def test_08_two_templates_switch_with_aria_pressed(self) -> None:
        html = read("index.html")
        js = read("plugin.js")
        self.assertIn('data-mode="practice"', html)
        self.assertIn('data-mode="card"', html)
        self.assertIn('aria-pressed="true"', html)
        self.assertIn("function setMode(mode)", js)
        self.assertIn("aria-pressed", js)
        self.assertIn('state.mode === "card" ? buildCard(entries) : buildPractice(entries)', js)

    def test_09_print_hides_toolbar_and_breaks_pages(self) -> None:
        css = read("plugin.css")
        js = read("plugin.js")
        self.assertIn("break-after: page", css)
        self.assertIn(".ep-top", css.split("@media print")[1], "打印时工具条必须整块隐藏")
        self.assertIn('window.addEventListener("beforeprint"', js)

    def test_10_empty_basket_has_a_way_out(self) -> None:
        html = read("index.html")
        js = read("plugin.js")
        self.assertIn('id="epEmpty"', html)
        self.assertIn("题篮是空的", html)
        self.assertIn("emptyEl.hidden = entries.length > 0", js)


class ExamPaperRuntimeContractTest(unittest.TestCase):
    def test_01_no_inline_scripts_in_shell(self) -> None:
        html = read("index.html")
        inline = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html, re.IGNORECASE)
        self.assertEqual(inline, [], "宿主 CSP 是 script-src 'self'，内联脚本会被拦掉")

    def test_02_external_assets_are_local(self) -> None:
        html = read("index.html")
        self.assertNotRegex(html, r"(?:src|href)=\"https?://")
        self.assertIn("/static/vendor/katex/katex.min.js", html)
        self.assertIn('src="plugin.js"', html)

    def test_03_three_greps_are_zero(self) -> None:
        source = read("plugin.js")
        self.assertNotIn("fetch(", source)
        self.assertNotIn("parent.document", source)
        self.assertNotIn("localStorage", source)
        self.assertNotIn("indexedDB", source)
        self.assertNotIn("document.cookie", source)

    def test_04_request_ids_are_host_compatible(self) -> None:
        source = read("plugin.js")
        self.assertIn('var id = "e" + requestSeq + "_" + Date.now().toString(36);', source)
        self.assertNotIn("id: id + \".\"", source)
        self.assertRegex("e1_m1x2y3", r"^[A-Za-z0-9_-]{1,80}$")

    def test_05_katex_is_rendered_without_trust(self) -> None:
        source = read("plugin.js")
        self.assertIn("window.katex.renderToString", source)
        self.assertIn("trust: false", source)
        self.assertIn('strict: "ignore"', source)
        self.assertEqual(source.count("innerHTML"), 1, "innerHTML 只许喂 KaTeX 的可信输出")

    def test_06_content_is_inserted_as_text(self) -> None:
        source = read("plugin.js")
        self.assertNotIn("insertAdjacentHTML", source)
        self.assertIn("document.createTextNode", source)
        self.assertIn("textContent", source)

    def test_07_follows_basket_changes(self) -> None:
        source = read("plugin.js")
        self.assertIn('message.event === "basket.changed"', source)
        self.assertIn("function scheduleReload()", source)
        self.assertIn('hostCall("basket.list", { expand: true })', source)

    def test_08_no_regex_lookbehind(self) -> None:
        for name in ("plugin.js", "plugin.css", "index.html"):
            self.assertNotRegex(read(name), r"\(\?<[=!]", f"{name} 含有后行断言")

    def test_09_plugin_id_matches_directory(self) -> None:
        self.assertEqual(PLUGIN_DIR.name, manifest()["id"])


class ExamPaperPackageTest(unittest.TestCase):
    def test_01_zip_top_level_is_plugin_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = build_plugin(PLUGIN_DIR, Path(tmp))
            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
        self.assertTrue(names, "打包不能产出空 zip")
        self.assertTrue(all(name.startswith(PLUGIN_ID + "/") for name in names), names[:5])
        self.assertIn(f"{PLUGIN_ID}/plugin.json", names)
        self.assertIn(f"{PLUGIN_ID}/dist/index.html", names)
        self.assertIn(f"{PLUGIN_ID}/dist/plugin.js", names)
        self.assertIn(f"{PLUGIN_ID}/dist/plugin.css", names)
        self.assertFalse([name for name in names if name.endswith((".pyc", ".part", ".bak"))])


if __name__ == "__main__":
    unittest.main()
