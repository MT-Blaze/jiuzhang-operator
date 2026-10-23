"""题库浏览插件（org.jiuzhang.bank-browser）契约测试：军令 #13 任务 8。

真机浏览、筛选、入篮与跳转由 ``tools/bank_browser_probe.py`` 取证；这里守静态底线：

- 清单能过宿主校验，只占中栏舞台，权限只读，发布面只开 dock 与编辑跳转；
- 左树、全局搜索、分页、加入题篮、去编辑在 HTML 与 JS 里都有真实落点；
- 浏览型插件只走 ``bank.active_*`` / ``basket.active_add``（活跃题库同源），
  不许拿自己的页签 id 去猜库；
- 插件不碰 localStorage / fetch / 宿主 DOM，公式只喂 KaTeX 且 trust=false；
- 宿主转发通道确实认得这两条 active 方法；zip 顶层就是插件 id。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_browser_plugin``
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.core import plugin_update
from app.core.plugins import validate_plugin
from tools.build_plugin import build_plugin

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "org.jiuzhang.bank-browser"
PLUGIN_DIR = ROOT / "plugins" / PLUGIN_ID
DIST = PLUGIN_DIR / "dist"


def read(name: str) -> str:
    return (DIST / name).read_text(encoding="utf-8")


def manifest() -> dict:
    return json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))


class BankBrowserManifestTest(unittest.TestCase):
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
        self.assertEqual(manifest()["capabilities"], ["question.render"])

    def test_04_bus_follows_basket_and_edit_channel(self) -> None:
        bus = manifest()["bus"]
        self.assertIn("basket.changed", bus["subscribe"])
        self.assertIn("question.updated", bus["subscribe"])
        self.assertEqual(bus["publish"], ["region.dock", "system.open_editor"])

    def test_05_min_host_version_matches_current_host(self) -> None:
        declared = manifest()["min_host_version"]
        self.assertEqual(declared, "0.8.2")
        self.assertTrue(plugin_update.host_satisfies(declared))

    def test_06_license_ships_full_apache_text(self) -> None:
        text = (PLUGIN_DIR / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License", text)
        self.assertGreater(len(text), 10000)

    def test_07_no_backend_entry(self) -> None:
        self.assertNotIn("backend", manifest())
        self.assertFalse((PLUGIN_DIR / "backend").exists())


class BankBrowserStructureTest(unittest.TestCase):
    def test_01_left_tree_global_search_and_pager_exist(self) -> None:
        html = read("index.html")
        for element_id in ("bbTree", "bbSearch", "bbSearchBtn", "bbList", "bbPager", "bbEmpty"):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn('role="tree"', html)
        self.assertIn('role="search"', html)

    def test_02_cards_offer_basket_and_edit(self) -> None:
        js = read("plugin.js")
        self.assertIn('el("button", "bb-add", "加入题篮")', js)
        self.assertIn('el("button", "bb-edit", "去编辑")', js)
        self.assertIn('addEventListener("click", function () { addToBasket(question, addBtn); })', js)
        self.assertIn('addEventListener("click", function () { openEditor(question); })', js)

    def test_03_browse_channels_are_active_provider_scoped(self) -> None:
        source = read("plugin.js")
        self.assertIn('hostCall("bank.active_list"', source)
        self.assertIn('hostCall("bank.active_stats"', source)
        self.assertIn('hostCall("basket.active_add"', source)
        self.assertNotIn('hostCall("bank.list"', source)
        self.assertNotIn('hostCall("bank.stats"', source)
        self.assertNotIn('hostCall("basket.add"', source)

    def test_04_tree_is_lazy_and_filters_by_topic(self) -> None:
        source = read("plugin.js")
        self.assertIn('hostCall("bank.topics", { parent_id: key })', source)
        self.assertIn("node.has_children", source)
        self.assertIn('payload.topic = state.topicId', source)
        self.assertIn("function renderLevel(items, host)", source)

    def test_05_global_search_clears_tree_scope(self) -> None:
        source = read("plugin.js")
        self.assertIn("state.q = keyword", source)
        self.assertIn('state.topicId = ""', source)
        self.assertIn("SEARCH_MAX", source)
        self.assertIn('maxlength="100"', read("index.html"))

    def test_05b_search_does_not_rely_on_form_submit(self) -> None:
        # 沙箱 iframe 只开 allow-scripts，没有 allow-forms：表单提交会被浏览器拦下。
        self.assertNotIn("<form", read("index.html"))
        source = read("plugin.js")
        self.assertIn('searchBtn.addEventListener("click", submitSearch);', source)
        self.assertIn('event.key === "Enter"', source)

    def test_06_pagination_is_bounded(self) -> None:
        source = read("plugin.js")
        self.assertIn("var PAGE_SIZE = 12;", source)
        self.assertIn("state.totalPages", source)
        self.assertIn("prevBtn.disabled", source)
        self.assertIn("nextBtn.disabled", source)

    def test_07_basket_membership_comes_from_host(self) -> None:
        source = read("plugin.js")
        self.assertIn('hostCall("basket.list", { expand: false })', source)
        self.assertIn('message.event === "basket.changed"', source)
        self.assertIn("已在题篮", source)

    def test_08_edit_jump_is_a_notification(self) -> None:
        source = read("plugin.js")
        self.assertIn('notifyHost("system.open_editor", { question_id: question.id })', source)
        self.assertNotIn("openEditor(", read("index.html"))


class BankBrowserRuntimeTest(unittest.TestCase):
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
        self.assertIn('var id = "b" + requestSeq + "_" + Date.now().toString(36);', source)
        self.assertRegex("b7_k2m9", r"^[A-Za-z0-9_-]{1,80}$")
        self.assertNotIn('"b" + requestSeq + "."', source)

    def test_05_katex_is_trust_free(self) -> None:
        source = read("plugin.js")
        self.assertIn("window.katex.renderToString", source)
        self.assertIn("trust: false", source)
        self.assertIn('strict: "ignore"', source)
        self.assertEqual(source.count("innerHTML"), 1, "innerHTML 只许喂 KaTeX 输出")

    def test_06_text_goes_through_text_content(self) -> None:
        source = read("plugin.js")
        self.assertIn("document.createTextNode", source)
        self.assertIn('if (text != null) node.textContent = text;', source)

    def test_07_no_regex_lookbehind(self) -> None:
        for name in ("plugin.js", "plugin.css", "index.html"):
            self.assertNotRegex(read(name), r"\(\?<[=!]", f"{name} 含有后行断言")

    def test_08_plugin_id_matches_directory(self) -> None:
        self.assertEqual(PLUGIN_DIR.name, manifest()["id"])


class BankBrowserHostContractTest(unittest.TestCase):
    def test_01_host_relays_active_bank_methods(self) -> None:
        source = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        self.assertIn('"bank.active_list", "bank.active_stats"', source)
        self.assertIn('"basket.active_add"', source)
        self.assertIn('method === "bank.active_list" ? sharedBase : base', source)
        self.assertIn('method === "bank.active_stats" ? sharedBase : base', source)
        self.assertIn('if (method === "basket.active_add") basketOwner = bankProviderId;', source)

    def test_02_plugin_spec_documents_the_channels(self) -> None:
        spec = (ROOT / "PLUGIN_SPEC.md").read_text(encoding="utf-8")
        for method in ("bank.active_list", "bank.active_stats", "basket.active_add"):
            self.assertIn(f"`{method}`", spec)


class BankBrowserPackageTest(unittest.TestCase):
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
