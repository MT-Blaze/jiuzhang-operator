"""录题工作台（org.jiuzhang.editor）契约测试：v0.6.2。

真机录题由 ``tools/editor_probe.py`` 取证；这里钉住可静态判定的部分：

- 清单只申请中栏舞台与题库读写权限，不越权；
- 表单覆盖题干/动态选项/答案/解析/难度/知识点标签；
- 输入防抖后经宿主 ``bank.create`` 写入，插件自身不碰令牌与数据库；
- 一键清洗只走本地规则，覆盖 \\(...\\)、\\[...\\]、\\textbf、\\fillin 与 choices；
- A4 几何与组卷/讲义同口径，预览可缩放且不横溢；
- 离线、无凭据、无后行断言、zip 顶层为插件 id 且无临时文件。

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


def read(name: str) -> str:
    return (DIST / name).read_text(encoding="utf-8")


class EditorManifestTest(unittest.TestCase):
    def test_01_manifest_passes_host_validation(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        info = validate_plugin(PLUGIN_DIR, manifest)
        self.assertEqual(info["id"], "org.jiuzhang.editor")
        self.assertIn("stage.center", info["slots"])
        self.assertIn("question.edit", info["capabilities"])
        self.assertEqual(sorted(info["permissions"]), ["questions:read", "questions:write"])

    def test_02_stage_is_singleton_with_priority(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        stage = manifest["stage"]
        self.assertEqual(stage["region"], "center")
        self.assertEqual(stage["mode"], "takeover")
        self.assertEqual(stage["priority"], 65)
        self.assertIs(stage["singleton"], True)
        self.assertLessEqual(len(stage["title"]), 24)

    def test_03_bus_is_minimal(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        # 三端分离：录题是唯一输入端。v0.7.1 再要两件事——
        # 订阅一条「AI 副驾回填」下行通知，发布一条「保存后自动收页」信号。
        self.assertEqual(sorted(manifest["bus"]["subscribe"]),
                         ["editor.apply_patch", "system.open_editor", "ui.params.changed"])
        self.assertEqual(sorted(manifest["bus"]["publish"]),
                         ["region.dock", "stage.selection", "system.editor_close",
                          "system.return_from_editor"])


class EditorFormContractTest(unittest.TestCase):
    def test_01_required_fields_exist(self) -> None:
        html = read("index.html")
        for node_id in (
            "edType", "edDifficulty", "edGrade", "edStem", "edOptions",
            "edAddOption", "edAnswer", "edSolution", "edTags", "edSave", "edClean",
        ):
            self.assertIn(f'id="{node_id}"', html, f"缺少表单节点 {node_id}")
        self.assertIn('placeholder="例：已知函数', html)

    def test_02_options_are_dynamic_with_bounded_keys(self) -> None:
        js = read("plugin.js")
        self.assertIn("function addOption", js)
        self.assertIn("function renderOptions", js)
        self.assertIn("OPTION_KEYS", js)
        self.assertIn("state.options.length >= OPTION_KEYS.length", js)
        self.assertIn("state.options.length <= 2", js, "选择题至少保留两项")
        self.assertIn('remove.setAttribute("aria-label"', js)

    def test_03_answer_and_solution_are_required_for_save(self) -> None:
        js = read("plugin.js")
        self.assertIn("题干不能为空", js)
        self.assertIn("请填写答案", js)
        self.assertIn("单选题答案只能有一个字母", js)
        self.assertIn("多选题答案至少两个字母", js)

    def test_04_preview_is_debounced_and_local(self) -> None:
        js = read("plugin.js")
        self.assertIn("PREVIEW_DEBOUNCE_MS = 140", js)
        self.assertIn("schedulePreview", js)
        self.assertIn('addEventListener("input"', js)
        self.assertIn("katex.renderToString", js)
        self.assertIn('event: "stage.selection"', js, "草稿需经事件总线上桥")

    def test_05_a4_geometry_matches_other_printers(self) -> None:
        css = read("plugin.css")
        js = read("plugin.js")
        self.assertIn("width: 794px", css)
        self.assertIn("height: 1123px", css)
        self.assertIn("var PAGE_W = 794", js)
        self.assertIn("var PAGE_H = 1123", js)
        self.assertIn("function fitPreview", js)
        self.assertIn("ResizeObserver", js)


class EditorWriteContractTest(unittest.TestCase):
    def test_01_save_goes_through_host_bank_create(self) -> None:
        js = read("plugin.js")
        # 新增走 bank.create，改题走 bank.update——两条都只能经宿主，插件不碰令牌与接口
        self.assertIn('"bank.create"', js)
        self.assertIn('"bank.update"', js)
        self.assertIn("hostCall(updating ? ", js)
        self.assertIn('schema_version: "1.0"', js)
        self.assertIn('meta: { status: "published"', js)
        self.assertIn('"org.jiuzhang.editor": { grade:', js)

    def test_02_plugin_never_touches_token_or_database(self) -> None:
        js = read("plugin.js")
        for needle in ("X-JZO-Token", "local_token", "/api/", "fetch(", "localStorage", "api_key", "sk-"):
            self.assertNotIn(needle, js, f"录题插件不得直接接触：{needle}")

    def test_03_cleaner_is_local_and_covers_dirty_latex(self) -> None:
        js = read("plugin.js")
        self.assertIn("\\\\\\[([\\s\\S]*?)\\\\\\]", js, "必须归一 \\[...\\]")
        self.assertIn("\\\\\\(([\\s\\S]*?)\\\\\\)", js, "必须归一 \\(...\\)")
        self.assertIn("\\\\textbf", js)
        self.assertIn("\\\\fillin", js)
        self.assertIn("\\\\begin\\{choices\\}", js)
        self.assertIn("function cleanText", js)
        self.assertIn("function cleanAll", js)
        # 本地规则清洗：不出现网络调用或模型端点
        self.assertNotIn("http", js.lower().replace("http-equiv", ""))

    def test_04_no_remote_assets_or_credentials(self) -> None:
        for name in ("index.html", "plugin.css", "plugin.js"):
            source = read(name)
            self.assertNotIn("http://", source, f"{name} 不得引用远程资源")
            self.assertNotIn("https://", source, f"{name} 不得引用远程资源")
            self.assertNotIn("@import", source, f"{name} 不得远程导入样式")
        self.assertNotIn("(?<", read("plugin.js"), "旧浏览器会直接语法失败")

    def test_05_saved_state_is_visible_to_probe(self) -> None:
        js = read("plugin.js")
        self.assertIn('savedEl.setAttribute("data-id", id || "")', js)
        self.assertIn('metricsEl.setAttribute("data-saved-id", id || "")', js)
        self.assertIn("data-render-ms", js)
        self.assertIn("data-katex", js)
        self.assertIn("data-overflow", js)


class EditorV071FeatureTest(unittest.TestCase):
    """v0.7.1 极致好用与进阶：删题、派生变式、草稿托管、选项配图、AI 回填。"""

    def test_01_delete_question_with_confirm(self) -> None:
        html = read("index.html")
        js = read("plugin.js")
        self.assertIn('id="edDelete"', html, "缺【删除本题】按钮")
        self.assertIn('id="edModal"', html, "缺二次确认弹窗容器")
        self.assertIn('"bank.delete"', js, "删题必须经宿主转发")
        self.assertIn("function requestDelete", js)
        self.assertIn("function openConfirm", js)
        self.assertIn("不可撤销", js, "删除必须二次确认并说清不可逆")
        self.assertIn('keyEvent.key === "Escape"', js, "弹窗要能用 Esc 关闭（AGENTS §6）")

    def test_02_save_as_derived_variant(self) -> None:
        html = read("index.html")
        js = read("plugin.js")
        self.assertIn('id="edVariant"', html, "缺【另存为新题（派生变式）】按钮")
        self.assertIn("function saveAsVariant", js)
        self.assertIn("派生变式", js)
        # 派生变式一定是新题：去掉 id 走 create，绝不回写原题
        self.assertIn("delete question.id", js)
        self.assertIn('hostCall("bank.create"', js)

    def test_03_option_image_ids_round_trip(self) -> None:
        js = read("plugin.js")
        # 回填：从出参读入 image_ids；保存：写回 option.image_ids；配图资产随题保留
        self.assertIn("option.image_ids", js, "载入时必须读回选项配图")
        self.assertIn("entry.image_ids = option.imageIds", js, "保存时必须带上选项配图")
        self.assertIn("state.images", js, "配图资产数组需整体保留")
        self.assertIn("imageIds", js)

    def test_04_draft_is_hosted_never_localstorage(self) -> None:
        js = read("plugin.js")
        self.assertIn('"draft.save"', js, "草稿必须经宿主 RPC 托管")
        self.assertIn('"draft.load"', js)
        self.assertIn("function getFormState", js)
        self.assertIn("function applyFormState", js)
        self.assertIn("function maybeRestoreDraft", js)
        self.assertIn("addEventListener(\"beforeunload\", flushDraft)", js)
        # 关键红线：沙箱不透明源里 localStorage 会抛异常，插件绝不能用它
        self.assertNotIn("localStorage", js)

    def test_05_auto_close_and_ai_backfill(self) -> None:
        js = read("plugin.js")
        self.assertIn("AUTO_CLOSE_MS = 1000", js, "保存后 1 秒自动收页")
        self.assertIn('"system.editor_close"', js)
        self.assertIn('message.event === "editor.apply_patch"', js, "必须接收 AI 副驾回填通知")
        # 回填只进表单，不自动落库：保存权仍在老师手里
        self.assertIn("请核对后保存", js)

    def test_06_a4_geometry_still_single_truth(self) -> None:
        # 上一版守住的红线不许被本轮改动带偏
        css = read("plugin.css")
        self.assertIn("width: 794px", css)
        self.assertIn("height: 1123px", css)


class EditorPackageTest(unittest.TestCase):
    def test_01_zip_top_level_is_plugin_id_and_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = build_plugin(PLUGIN_DIR, Path(tmp))
            self.assertTrue(target.is_file())
            with zipfile.ZipFile(target) as bundle:
                names = bundle.namelist()
        self.assertTrue(names)
        for name in names:
            parts = name.split("/")
            self.assertEqual(parts[0], "org.jiuzhang.editor", name)
            self.assertNotIn(".env", parts)
            self.assertNotIn("__pycache__", parts)
        joined = "\n".join(names)
        self.assertIn("org.jiuzhang.editor/plugin.json", joined)
        self.assertIn("org.jiuzhang.editor/dist/index.html", joined)
        self.assertIn("org.jiuzhang.editor/LICENSE", joined)
        self.assertFalse(any(name.endswith((".pyc", ".log", ".tmp", ".zip")) for name in names))


if __name__ == "__main__":
    unittest.main()
