"""专题讲义插件（org.jiuzhang.lecture）契约测试：军令 #13 任务 7。

真机编辑与草稿恢复由 ``tools/lecture_probe.py`` 取证；这里守的是可静态判定的底线：

- 清单能过宿主校验，只占中栏舞台，权限只读；
- 三块（知识点 / 方法 / 易错点）在 HTML 与 JS 里同名同序，骨架按 taxonomy 归堆；
- 正文是原生渲染：标题/列表/段落是真 DOM，公式走 KaTeX，正文不 innerHTML 回显；
- 草稿只走宿主 draft.save / draft.load，插件不碰 localStorage、不联网、不读宿主 DOM；
- 打印只出正文（编辑控件隐藏），且 zip 顶层就是插件 id。

运行：``.venv/Scripts/python.exe -m unittest tests.test_lecture_plugin``
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
PLUGIN_ID = "org.jiuzhang.lecture"
PLUGIN_DIR = ROOT / "plugins" / PLUGIN_ID
DIST = PLUGIN_DIR / "dist"


def read(name: str) -> str:
    return (DIST / name).read_text(encoding="utf-8")


def manifest() -> dict:
    return json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))


class LectureManifestTest(unittest.TestCase):
    def test_01_manifest_passes_host_validation(self) -> None:
        info = validate_plugin(PLUGIN_DIR, manifest())
        self.assertEqual(info["id"], PLUGIN_ID)
        self.assertEqual(info["slots"], ["stage.center"])
        self.assertTrue(info["entry_url"].startswith("/plugin-assets/"))

    def test_02_stage_is_takeover_and_singleton(self) -> None:
        stage = manifest()["stage"]
        self.assertEqual(stage["region"], "center")
        self.assertEqual(stage["mode"], "takeover")
        self.assertIs(stage["singleton"], True)
        self.assertLessEqual(len(stage["title"]), 24)

    def test_03_permissions_are_read_only(self) -> None:
        self.assertEqual(manifest()["permissions"], ["questions:read"])
        self.assertEqual(manifest()["capabilities"], ["handout.render"])

    def test_04_bus_only_follows_basket(self) -> None:
        bus = manifest()["bus"]
        self.assertEqual(bus["subscribe"], ["basket.changed"])
        self.assertEqual(bus["publish"], ["region.dock"])

    def test_05_license_ships_full_apache_text(self) -> None:
        text = (PLUGIN_DIR / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License", text)
        self.assertGreater(len(text), 10000)

    def test_06_no_backend_entry(self) -> None:
        self.assertNotIn("backend", manifest())
        self.assertFalse((PLUGIN_DIR / "backend").exists())


class LectureStructureTest(unittest.TestCase):
    def test_01_three_blocks_match_in_html_and_js(self) -> None:
        html = read("index.html")
        js = read("plugin.js")
        for key, label in (("knowledge", "知识点"), ("methods", "方法"), ("pitfalls", "易错点")):
            self.assertIn(f'data-block="{key}"', html)
            self.assertIn(f'data-entries="{key}"', html)
            self.assertIn(f'key: "{key}"', js)
            self.assertIn(f'label: "{label}"', js)

    def test_02_skeleton_groups_by_taxonomy(self) -> None:
        js = read("plugin.js")
        self.assertIn("taxonomy.topic", js)
        self.assertIn("taxonomy.section", js)
        self.assertIn("taxonomy.chapter", js)
        self.assertIn("TOPIC_LIMIT", js)
        self.assertIn("function buildSkeleton()", js)
        self.assertIn("state.blocks.knowledge.push", js)
        self.assertIn("state.blocks.methods.push", js)
        self.assertIn("state.blocks.pitfalls.push", js)

    def test_03_rebuild_requires_second_click(self) -> None:
        js = read("plugin.js")
        self.assertIn("REBUILD_WINDOW_MS", js)
        self.assertIn("再点一次", js)
        self.assertIn("rebuildAt", js)

    def test_04_entries_are_editable_and_removable(self) -> None:
        js = read("plugin.js")
        self.assertIn('document.createElement("textarea")', js)
        self.assertIn('addEventListener("input"', js)
        self.assertIn("state.blocks[key].splice(index, 1)", js)
        self.assertIn(".lc-remove", read("plugin.css"))

    def test_05_preview_is_native_dom(self) -> None:
        js = read("plugin.js")
        self.assertIn("function renderRich(target, source)", js)
        self.assertIn('heading = line.match(/^(#{1,3})\\s+(.*)$/)', js)
        self.assertIn("lc-list", js)
        self.assertIn("document.createTextNode", js)
        self.assertEqual(js.count("innerHTML"), 1, "innerHTML 只许喂 KaTeX 输出")

    def test_06_print_only_prints_the_body(self) -> None:
        css = read("plugin.css")
        self.assertIn("@page", css)
        self.assertIn("size: A4", css)
        printed = css.split("@media print")[1]
        for selector in (".lc-top", ".lc-sources", ".lc-entry textarea", ".lc-empty-hint"):
            self.assertIn(selector, printed)
        self.assertIn("break-inside: avoid", printed)
        self.assertIn("beforeprint", read("plugin.js"))

    def test_07_empty_basket_still_usable(self) -> None:
        html = read("index.html")
        js = read("plugin.js")
        self.assertIn('id="lcSourceEmpty"', html)
        self.assertIn("题篮为空", js)
        self.assertIn("题篮是空的，先加几道同类题再生成骨架", js)


class LectureRuntimeTest(unittest.TestCase):
    def test_01_no_inline_scripts(self) -> None:
        inline = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", read("index.html"), re.IGNORECASE)
        self.assertEqual(inline, [])

    def test_02_assets_are_local(self) -> None:
        html = read("index.html")
        self.assertNotRegex(html, r'(?:src|href)="https?://')
        self.assertIn("/static/vendor/katex/katex.min.js", html)
        self.assertIn('src="plugin.js"', html)

    def test_03_three_greps_are_zero(self) -> None:
        source = read("plugin.js")
        for token in ("fetch(", "parent.document", "localStorage", "indexedDB", "document.cookie"):
            self.assertNotIn(token, source)

    def test_04_request_ids_are_host_compatible(self) -> None:
        source = read("plugin.js")
        self.assertIn('var id = "l" + requestSeq + "_" + Date.now().toString(36);', source)
        self.assertRegex("l12_m3n4", r"^[A-Za-z0-9_-]{1,80}$")

    def test_05_katex_is_trust_free(self) -> None:
        source = read("plugin.js")
        self.assertIn("window.katex.renderToString", source)
        self.assertIn("trust: false", source)
        self.assertIn('strict: "ignore"', source)

    def test_06_draft_goes_through_host(self) -> None:
        source = read("plugin.js")
        self.assertIn('hostCall("draft.save", { key: DRAFT_KEY, value: snapshot() })', source)
        self.assertIn('hostCall("draft.load", { key: DRAFT_KEY })', source)
        self.assertIn('var DRAFT_KEY = "lecture";', source)
        self.assertIn("function scheduleSave()", source)

    def test_07_basket_read_uses_expand(self) -> None:
        source = read("plugin.js")
        self.assertIn('hostCall("basket.list", { expand: true })', source)
        self.assertIn('message.event === "basket.changed"', source)

    def test_08_no_regex_lookbehind(self) -> None:
        for name in ("plugin.js", "plugin.css", "index.html"):
            self.assertNotRegex(read(name), r"\(\?<[=!]", f"{name} 含有后行断言")

    def test_09_content_is_bounded(self) -> None:
        source = read("plugin.js")
        self.assertIn("ENTRY_MAX_CHARS", source)
        self.assertIn("slice(0, ENTRY_MAX_CHARS)", source)
        self.assertIn("maxlength=\"48\"", read("index.html"))

    def test_10_plugin_id_matches_directory(self) -> None:
        self.assertEqual(PLUGIN_DIR.name, manifest()["id"])


class LecturePackageTest(unittest.TestCase):
    def test_01_zip_top_level_is_plugin_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = build_plugin(PLUGIN_DIR, Path(tmp))
            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
        self.assertTrue(all(name.startswith(PLUGIN_ID + "/") for name in names), names[:5])
        for expected in ("plugin.json", "LICENSE", "dist/index.html", "dist/plugin.js", "dist/plugin.css"):
            self.assertIn(f"{PLUGIN_ID}/{expected}", names)
        self.assertFalse([name for name in names if name.endswith((".pyc", ".part", ".bak"))])


if __name__ == "__main__":
    unittest.main()
