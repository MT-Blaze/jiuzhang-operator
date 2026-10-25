"""讲义排版插件（org.jiuzhang.handout）契约测试：v0.6.1 第四战役。

真机排版由 ``tools/handout_probe.py`` 取证；这里钉住可静态判定的部分：

- 清单能过宿主校验：只要中栏舞台、零权限，不碰题库与文件系统；
- A4 几何与组卷插件同口径（794×1123 / 正文 925），测量列必须存在；
- Markdown 子集覆盖标题、列表、表格、引用、代码块与三种公式定界符；
- 改字即重排（防抖）、探针指标真实写出；
- 离线、无凭据、无后行断言、zip 顶层为插件 id 且无临时文件。

运行：``.venv/Scripts/python.exe -m unittest tests.test_handout_contract``
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
PLUGIN_DIR = ROOT / "plugins" / "org.jiuzhang.handout"
DIST = PLUGIN_DIR / "dist"


def read(name: str) -> str:
    return (DIST / name).read_text(encoding="utf-8")


class HandoutManifestTest(unittest.TestCase):
    def test_01_manifest_passes_host_validation(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        info = validate_plugin(PLUGIN_DIR, manifest)
        self.assertEqual(info["id"], "org.jiuzhang.handout")
        self.assertIn("stage.center", info["slots"])
        self.assertIn("handout.render", info["capabilities"])
        self.assertEqual(info["permissions"], [], "讲义插件不需要任何宿主数据权限")

    def test_02_stage_is_singleton_with_priority(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        stage = manifest["stage"]
        self.assertEqual(stage["region"], "center")
        self.assertEqual(stage["mode"], "takeover")
        self.assertEqual(stage["priority"], 60)
        self.assertIs(stage["singleton"], True)
        self.assertLessEqual(len(stage["title"]), 24)

    def test_03_ui_size_control_matches_state(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        controls = {item["key"]: item for item in manifest["ui"]["controls"]}
        self.assertEqual(controls["size"]["default"], "标准")
        self.assertIn("大字", [item["value"] for item in controls["size"]["options"]])
        self.assertIn('size: "normal"', read("plugin.js"))

    def test_04_bus_is_minimal(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        # 讲义是输出端：只订阅「题目已更新」（新名 + 老插件别名两条）用来标脏，不申请任何写通道。
        # 这条清单必须与 plugin.js 里真的按 event 分支处理的主题逐字全等——由
        # tests.test_plugin_bus_parity 统一守，这里只钉住「没有多要写通道」。
        self.assertEqual(manifest["bus"]["subscribe"],
                         ["ui.params.changed", "system.question_updated", "question.updated"])
        self.assertEqual(manifest["bus"]["publish"], ["region.dock"])


class HandoutLayoutContractTest(unittest.TestCase):
    def test_01_a4_geometry_matches_paper(self) -> None:
        css = read("plugin.css")
        js = read("plugin.js")
        self.assertIn("--hp-page-w: 794px", css)
        self.assertIn("--hp-page-h: 1123px", css)
        self.assertIn("--hp-body-h: 925px", css)
        self.assertRegex(js, r"var PAGE_W = 794;")
        self.assertRegex(js, r"var PAGE_H = 1123;")
        fill = int(re.search(r"var PAGE_FILL_H = (\d+);", js).group(1))
        self.assertLessEqual(fill, 925)
        self.assertGreaterEqual(fill, 860)

    def test_02_measure_column_and_metrics_exist(self) -> None:
        html = read("index.html")
        self.assertIn('id="hpMeasure"', html)
        self.assertIn('id="hpMetrics"', html)
        self.assertIn('id="hpPages"', html)
        js = read("plugin.js")
        for attribute in (
            "data-render-ms",
            "data-pages",
            "data-blocks",
            "data-chars",
            "data-overflow",
            "data-reflow",
        ):
            self.assertIn('setAttribute("' + attribute + '"', js)

    def test_03_markdown_subset_is_covered(self) -> None:
        js = read("plugin.js")
        # 标题、列表、表格分隔行、引用、代码块、三种公式定界符
        self.assertIn("#{1,4}", js)
        self.assertIn("blockquote", js)
        self.assertIn('createElement("table")', js)
        self.assertIn("pre", js)
        self.assertIn("\\\\[", js, "必须支持 \\[...\\] 公式")
        self.assertIn("\\\\(", js, "必须支持 \\(...\\) 公式")
        self.assertIn("isTableStart", js)
        self.assertIn("parseMarkdown", js)

    def test_04_typing_triggers_debounced_reflow(self) -> None:
        js = read("plugin.js")
        self.assertIn('addEventListener("input"', js)
        self.assertIn("DEBOUNCE_MS = 160", js)
        self.assertIn("scheduleReflow", js)

    def test_05_no_remote_assets_or_credentials(self) -> None:
        for name in ("index.html", "plugin.css", "plugin.js"):
            source = read(name)
            self.assertNotIn("http://", source, f"{name} 不得引用远程资源")
            self.assertNotIn("https://", source, f"{name} 不得引用远程资源")
            self.assertNotIn("@import", source, f"{name} 不得远程导入样式")
        source = read("plugin.js")
        for needle in ("X-JZO-Token", "local_token", "api_key", "sk-", "localStorage"):
            self.assertNotIn(needle, source, f"讲义插件不得接触：{needle}")
        self.assertNotIn("(?<", source, "旧浏览器会直接语法失败")

    def test_06_print_styles_are_present(self) -> None:
        css = read("plugin.css")
        printed = css.split("@media print")[1]
        self.assertIn("@media print", css)
        self.assertIn("break-after: page", css)
        self.assertIn("transform: none", css)
        # A4 纸面必须显式声明纸张，并留出 1px 余量免得挤出空白尾页。
        self.assertIn("size: A4", printed)
        self.assertIn("height: 1122px", printed)
        self.assertIn("overflow: hidden", printed)
        self.assertIn("window.print()", read("plugin.js"))


class HandoutPackageTest(unittest.TestCase):
    def test_01_zip_top_level_is_plugin_id_and_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = build_plugin(PLUGIN_DIR, Path(tmp))
            self.assertTrue(target.is_file())
            with zipfile.ZipFile(target) as bundle:
                names = bundle.namelist()
        self.assertTrue(names)
        for name in names:
            parts = name.split("/")
            self.assertEqual(parts[0], "org.jiuzhang.handout", name)
            self.assertNotIn(".env", parts)
            self.assertNotIn("__pycache__", parts)
        joined = "\n".join(names)
        self.assertIn("org.jiuzhang.handout/plugin.json", joined)
        self.assertIn("org.jiuzhang.handout/dist/index.html", joined)
        self.assertIn("org.jiuzhang.handout/LICENSE", joined)
        self.assertFalse(any(name.endswith((".pyc", ".log", ".tmp", ".zip")) for name in names))


if __name__ == "__main__":
    unittest.main()
