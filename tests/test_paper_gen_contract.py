"""组卷排版插件（org.jiuzhang.paper-gen）契约测试：v0.6.0 第三战役。

真机排版由 ``tools/paper_probe.py`` 取证；这里守的是可静态判定的底线：

- 清单能过宿主校验，舞台声明、能力、权限不多要；
- A4 几何在 CSS 与 JS 里只有一份真相（794×1123、正文 925）；
- 探针依赖的 ``data-*`` 指标必须真的写出来，否则压测会静默失去证据；
- 插件只吃宿主总线与本地资源：不联网、不用后行断言、不夹带密钥；
- 打包器产出的 zip 顶层就是插件 id，且不含临时文件。

运行：``.venv/Scripts/python.exe -m unittest tests.test_paper_gen_contract``
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
PLUGIN_DIR = ROOT / "plugins" / "org.jiuzhang.paper-gen"
DIST = PLUGIN_DIR / "dist"


def read(name: str) -> str:
    return (DIST / name).read_text(encoding="utf-8")


class PaperGenManifestTest(unittest.TestCase):
    def test_01_manifest_passes_host_validation(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        info = validate_plugin(PLUGIN_DIR, manifest)
        self.assertEqual(info["id"], "org.jiuzhang.paper-gen")
        self.assertIn("stage.center", info["slots"])
        self.assertTrue(info["entry_url"].startswith("/plugin-assets/"))

    def test_02_stage_is_high_priority_and_single_instance(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        stage = manifest["stage"]
        self.assertEqual(stage["region"], "center")
        self.assertEqual(stage["mode"], "takeover")
        self.assertEqual(stage["priority"], 70)
        self.assertIs(stage["singleton"], True)
        self.assertLessEqual(len(stage["title"]), 24, "舞台页签标题不得超过 24 字")

    def test_03_permissions_are_read_only(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["permissions"], ["questions:read"])
        self.assertIn("paper.generate", manifest["capabilities"])

    def test_04_ui_controls_match_plugin_state(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        controls = {item["key"]: item for item in manifest["ui"]["controls"]}
        self.assertEqual(controls["answers"]["default"], "隐藏")
        self.assertEqual(controls["density"]["default"], "标准")
        source = read("plugin.js")
        self.assertIn('showAnswers: false', source)
        self.assertIn('density: "normal"', source)

    def test_05_bus_only_takes_what_it_needs(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        # 组卷是输出端：订阅回流刷新，发布只多一个「去编辑」跳转
        self.assertEqual(sorted(manifest["bus"]["subscribe"]),
                         ["basket.changed", "stage.tab.activated", "system.question_updated",
                          "ui.params.changed"])
        self.assertEqual(sorted(manifest["bus"]["publish"]), ["region.dock", "system.open_editor"])


class PaperGenLayoutContractTest(unittest.TestCase):
    def test_01_a4_geometry_has_one_truth(self) -> None:
        css = read("plugin.css")
        js = read("plugin.js")
        self.assertIn("--pg-page-w: 794px", css)
        self.assertIn("--pg-page-h: 1123px", css)
        self.assertIn("--pg-body-h: 925px", css)
        self.assertRegex(js, r"var PAGE_W = 794;")
        self.assertRegex(js, r"var PAGE_H = 1123;")
        fill = int(re.search(r"var PAGE_FILL_H = (\d+);", js).group(1))
        self.assertLessEqual(fill, 925, "填充高度不能超过正文高度")
        self.assertGreaterEqual(fill, 860, "留白过大等于白扔纸面")

    def test_02_probe_metrics_are_emitted(self) -> None:
        js = read("plugin.js")
        for attribute in (
            "data-render-ms",
            "data-pages",
            "data-questions",
            "data-overflow",
            "data-reflow",
            "data-t-build",
            "data-t-measure-blocks",
            "data-t-place",
            "data-t-settle",
        ):
            self.assertIn('setAttribute("' + attribute + '"', js)

    def test_03_basket_and_param_events_drive_reflow(self) -> None:
        js = read("plugin.js")
        self.assertIn("basket.changed", js)
        self.assertIn("ui.params.changed", js)
        self.assertIn("function loadBasket", js)
        self.assertIn("function reflow", js)

    def test_04_index_exposes_measure_column_and_metrics(self) -> None:
        html = read("index.html")
        self.assertIn('id="pgMeasure"', html)
        self.assertIn('id="pgPages"', html)
        self.assertIn('id="pgMetrics"', html)

    def test_05_no_remote_assets(self) -> None:
        for name in ("index.html", "plugin.css", "plugin.js"):
            source = read(name)
            self.assertNotIn("http://", source, f"{name} 不得引用远程资源")
            self.assertNotIn("https://", source, f"{name} 不得引用远程资源")
            self.assertNotIn("@import", source, f"{name} 不得远程导入样式")

    def test_06_no_regex_lookbehind(self) -> None:
        source = read("plugin.js")
        self.assertNotIn("(?<", source, "旧浏览器会直接语法失败")

    def test_07_no_secrets_or_checkout(self) -> None:
        source = read("plugin.js")
        for needle in ("X-JZO-Token", "local_token", "api_key", "sk-"):
            self.assertNotIn(needle, source, f"插件不得接触宿主凭据：{needle}")
        self.assertNotIn("localStorage", source, "沙箱 iframe 没有可用的持久存储")

    def test_08_messy_legacy_latex_is_normalized(self) -> None:
        """真题原文混用 \\(...\\)、\\textbf{}、\\fillin、tabular，必须在纸面转义。"""
        source = read("plugin.js")
        for token in ("\\\\textbf", "\\\\textit", "\\\\fillin", "\\\\begin\\{tabular\\}"):
            self.assertIn(token, source)
        self.assertIn("pg-blank", read("plugin.css"))
        self.assertIn("pg-table", read("plugin.css"))
        self.assertIn("solutionBody", source, "解析里重复的【答案】段应被剥离")


class PaperGenPackageTest(unittest.TestCase):
    def test_01_zip_top_level_is_plugin_id_and_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = build_plugin(PLUGIN_DIR, Path(tmp))
            self.assertTrue(target.is_file())
            with zipfile.ZipFile(target) as bundle:
                names = bundle.namelist()
        self.assertTrue(names)
        for name in names:
            parts = name.split("/")
            self.assertEqual(parts[0], "org.jiuzhang.paper-gen", name)
            self.assertNotIn(".env", parts, name)
            self.assertNotIn("__pycache__", parts, name)
        joined = "\n".join(names)
        self.assertIn("org.jiuzhang.paper-gen/plugin.json", joined)
        self.assertIn("org.jiuzhang.paper-gen/dist/index.html", joined)
        self.assertIn("org.jiuzhang.paper-gen/LICENSE", joined)
        self.assertFalse(any(name.endswith((".pyc", ".log", ".tmp", ".zip")) for name in names))


if __name__ == "__main__":
    unittest.main()
