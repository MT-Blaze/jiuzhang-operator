# -*- coding: utf-8 -*-
"""双引擎路由、四特征坏题体检与 30% 分诊契约。

钉住六件事：
1. 版面/识别两套引擎的白名单与瀑布顺序是单源；老四通道名仍能映射；
2. 四特征（连续空选项 / 掉变量句式 / 内联小图多但无公式 / 长文无符号）各报各的；
3. 每次解析静默打一行 ``[STAT] 本次解析总题数: X, 坏题数: Y, 坏题率: Z%``；
4. 坏题率低于阈值只补坏题，达到阈值自动改走并发全量 OCR；
5. MinerU 引擎逐题发送单题截图（绝不发整卷 PDF），进度逐题写进路由；
6. 双下拉框带原生 title，只影响下一次解析，且单文件不超过 400 行。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ingest_triage``
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from app.core import ai_center, ingest_route, pending_bank
from app.core.ingest_quality import question_reasons, triage_documents
from app.core.layout import layout_router
from app.core.recognize import (recognize_ai, recognize_mineru, recognize_router)

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "org.jiuzhang.editor"
HTML = (PLUGIN_DIR / "dist" / "index.html").read_text(encoding="utf-8")
INTAKE_JS = (PLUGIN_DIR / "dist" / "ui_intake.js").read_text(encoding="utf-8")


def clean_doc(number: int = 1) -> dict:
    return {
        "type": "solution",
        "stem": "求 $x+1=2$ 的解。",
        "difficulty": "L2",
        "source": {"question_no": str(number)},
    }


def broken_doc(kind: str) -> dict:
    if kind == "empty_options":
        return {
            "type": "single_choice",
            "stem": "下列结论正确的是（ ）",
            "options": [{"key": "A", "content": ""}, {"key": "B", "content": ""},
                        {"key": "C", "content": "3"}],
        }
    if kind == "dropped_var":
        return {"type": "solution", "stem": "已知，求的值。"}
    if kind == "images_no_formula":
        return {"type": "solution",
                "stem": "\\includegraphics{a.png} 与 \\includegraphics{b.png} 的关系是"}
    if kind == "long_no_symbol":
        return {"type": "solution", "stem": "题干" * 80}
    raise AssertionError(kind)


def item(pending_id: str, document: dict, page_no: int = 1) -> dict:
    return {
        "id": pending_id,
        "page_no": page_no,
        "question": {
            **document,
            "images": [{"id": "img_" + pending_id, "role": "stem",
                        "uri": "/static/pending/" + pending_id + ".png"}],
        },
        "assets": [{"name": pending_id + ".png"}],
    }


def binding(task: str = "ocr") -> ai_center.TaskBinding:
    return ai_center.TaskBinding(task=task, account_id="acc_0000000001", name="测试",
                                 base_url="https://api.test/v1", api_key="fixture",
                                 model="vision")


class EngineConstantTest(unittest.TestCase):
    def test_01_layout_waterfall_matrix(self) -> None:
        self.assertEqual(layout_router.plan("auto"), ("python", "yolo", "cloud"))
        self.assertEqual(layout_router.plan("yolo"), ("python", "yolo", "cloud"))
        self.assertEqual(layout_router.plan("cloud"), ("python", "cloud"))
        for engine in ("auto", "yolo", "cloud"):
            self.assertEqual(layout_router.plan(engine)[0], "python",
                             "纯 Python 探路必须永远排第一")
        self.assertEqual(layout_router.normalize_engine("乱填"), layout_router.LAYOUT_AUTO)
        self.assertEqual(layout_router.normalize_engine(None), layout_router.LAYOUT_AUTO)

    def test_02_recognize_waterfall_matrix(self) -> None:
        self.assertEqual(recognize_router.plan("auto"), ("local", "ai", "mineru"))
        self.assertEqual(recognize_router.plan("full_ocr"), ("local", "ai", "mineru"))
        self.assertEqual(recognize_router.plan("mineru"), ("local", "mineru"))
        self.assertEqual(recognize_router.BAD_RATE_THRESHOLD, 0.30)
        self.assertEqual(ingest_route.INGEST_BAD_RATE_THRESHOLD, 0.30)

    def test_03_legacy_channels_still_map(self) -> None:
        self.assertEqual(recognize_router.from_legacy_channel("local_ai"), "auto")
        self.assertEqual(recognize_router.from_legacy_channel("full_ocr"), "full_ocr")
        self.assertEqual(recognize_router.from_legacy_channel("mineru"), "mineru")
        self.assertEqual(recognize_router.from_legacy_channel("乱填"), "auto")

    def test_04_engine_modules_stay_under_four_hundred_lines(self) -> None:
        modules = [
            ROOT / "app" / "core" / "layout" / name
            for name in ("layout_router.py", "layout_python.py",
                         "layout_yolo.py", "layout_cloud.py")
        ] + [
            ROOT / "app" / "core" / "recognize" / name
            for name in ("recognize_router.py", "recognize_local.py",
                         "recognize_ai.py", "recognize_mineru.py",
                         "recognize_shared.py")
        ] + [
            ROOT / "app" / "core" / name
            for name in ("ingest.py", "ingest_text.py", "ingest_media.py",
                         "ingest_route.py")
        ]
        for path in modules:
            with self.subTest(module=path.name):
                self.assertLessEqual(
                    len(path.read_text(encoding="utf-8").splitlines()), 400,
                    f"{path.name} 超过 400 行")


class FourFeatureTest(unittest.TestCase):
    def test_01_each_feature_is_reported(self) -> None:
        self.assertIn("连续空选项", question_reasons(broken_doc("empty_options")))
        self.assertIn("掉变量句式", question_reasons(broken_doc("dropped_var")))
        self.assertIn("内联小图多但无公式", question_reasons(broken_doc("images_no_formula")))
        self.assertIn("长文无符号", question_reasons(broken_doc("long_no_symbol")))

    def test_02_clean_question_is_not_flagged(self) -> None:
        self.assertEqual(question_reasons(clean_doc()), [])

    def test_03_placeholder_is_a_bad_question(self) -> None:
        self.assertIn("空题干", question_reasons(
            {"type": "solution", "stem": "（自动切题：原卷第 1 页第 ? 题，请对照题图录入）"}))

    def test_04_rate_and_indexes(self) -> None:
        docs = [clean_doc(index) for index in range(8)] + [
            broken_doc("empty_options"), broken_doc("dropped_var")]
        report = triage_documents(docs)
        self.assertEqual(report["total"], 10)
        self.assertEqual(report["bad"], 2)
        self.assertAlmostEqual(report["rate"], 0.2)
        self.assertEqual(report["bad_indexes"], [8, 9])


class StatLogTest(unittest.TestCase):
    def test_stat_line_is_exactly_one_silent_line(self) -> None:
        docs = [clean_doc(index) for index in range(8)] + [
            broken_doc("empty_options"), broken_doc("dropped_var")]
        with self.assertLogs("app.core.ingest_route", level="INFO") as captured:
            ingest_route.log_documents(docs)
        self.assertEqual(len(captured.records), 1)
        self.assertIn(
            "[STAT] 本次解析总题数: 10, 坏题数: 2, 坏题率: 20.0%",
            captured.output[0],
        )


class TriagePolicyTest(unittest.IsolatedAsyncioTestCase):
    async def _run(self, documents: list[dict],
                   engine: str = recognize_router.RECOGNIZE_AUTO) -> dict:
        items = [item("p_test%02d" % index, document) for index, document in enumerate(documents)]
        saved: list[dict] = []

        def capture(rows, **_kwargs):
            saved.extend(rows)
            return {"saved_ids": [row.get("pending_id") for row in rows]}

        with mock.patch.object(pending_bank, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(pending_bank, "save_draft", side_effect=capture), \
                mock.patch.object(recognize_ai.ai_center, "resolve_task",
                                  return_value=binding()), \
                mock.patch.object(recognize_ai.ai_recognize, "recognize",
                                  new=mock.AsyncMock(return_value={
                                      "ok": True,
                                      "question": {
                                          "type": "solution", "stem": "求 $x+1=2$ 的解。",
                                          "options": [], "answer": "x=1",
                                          "solution": "移项得 $x=1$。",
                                          "question_no": "1", "difficulty": "L2",
                                      },
                                  })) as recognize:
            route = await ingest_route.fill_scan_batch(
                "B-001", engine, {"has_text_layer": True, "garbled": False})
        return {"route": route, "saved": saved, "recognize": recognize}

    async def test_below_threshold_patches_only_bad_questions(self) -> None:
        docs = [clean_doc(index) for index in range(8)] + [
            broken_doc("empty_options"), broken_doc("dropped_var")]
        with self.assertLogs("app.core.ingest_route", level="INFO") as captured:
            outcome = await self._run(docs)
        self.assertEqual(outcome["recognize"].await_count, 2, "低坏题率只补坏题")
        self.assertEqual(len(outcome["saved"]), 2)
        self.assertEqual([row["pending_id"] for row in outcome["saved"]],
                         ["p_test08", "p_test09"])
        self.assertIn("局部修补", outcome["route"]["note"])
        self.assertFalse(outcome["route"].get("mode") == "full_ocr")
        self.assertIn("坏题率: 20.0%", captured.output[0])
        self.assertEqual(outcome["route"]["layout_engine"], "auto")
        self.assertEqual(outcome["route"]["recognize_engine"], "auto")

    async def test_at_threshold_switches_to_full_ocr(self) -> None:
        docs = [clean_doc(index) for index in range(7)] + [
            broken_doc("empty_options"), broken_doc("dropped_var"),
            broken_doc("long_no_symbol")]
        outcome = await self._run(docs)
        self.assertEqual(outcome["recognize"].await_count, 10,
                         "坏题率达到 30% 就整批改走并发全量 OCR")
        self.assertEqual(outcome["route"]["mode"], "full_ocr")
        self.assertIn("并发全量 OCR", outcome["route"]["note"])

    async def test_full_ocr_engine_ignores_threshold(self) -> None:
        docs = [clean_doc(index) for index in range(10)]
        outcome = await self._run(docs, engine=recognize_router.RECOGNIZE_FULL_OCR)
        self.assertEqual(outcome["recognize"].await_count, 10)
        self.assertEqual(outcome["route"]["mode"], "full_ocr")

    async def test_clean_batch_does_not_call_ai(self) -> None:
        outcome = await self._run([clean_doc(index) for index in range(5)])
        self.assertEqual(outcome["recognize"].await_count, 0)
        self.assertIn("未发现坏题", outcome["route"]["note"])

    async def test_mineru_engine_skips_ai(self) -> None:
        items = [item("p_mine%02d" % index, clean_doc(index)) for index in range(2)]
        with mock.patch.object(pending_bank, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(recognize_ai.ai_recognize, "recognize") as recognize, \
                mock.patch.object(recognize_mineru.recognize_shared, "item_image_bytes",
                                  return_value=b""):
            route = await ingest_route.fill_scan_batch(
                "B-003", recognize_router.RECOGNIZE_MINERU,
                {"has_text_layer": False, "garbled": False})
        recognize.assert_not_called()
        self.assertEqual(route["recognize_engine"], "mineru")

    async def test_missing_mineru_account_is_reported(self) -> None:
        items = [item("p_none%02d" % index, clean_doc(index)) for index in range(2)]
        with mock.patch.object(pending_bank, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(ai_center, "find_mineru", return_value=None):
            route = await ingest_route.fill_scan_batch(
                "B-004", recognize_router.RECOGNIZE_MINERU,
                {"has_text_layer": False, "garbled": False})
        self.assertIn("MinerU 没有可用的账号", route["note"])


class MineruPerQuestionTest(unittest.IsolatedAsyncioTestCase):
    async def test_single_question_screenshots_not_the_whole_pdf(self) -> None:
        items = [item("p_mineru%02d" % index, broken_doc("dropped_var"))
                 for index in range(3)]
        saved: list[dict] = []
        seen_names: list[str] = []
        seen_bytes: list[bytes] = []

        def fake_extract(name, data, base_url, token, **kwargs):
            seen_names.append(name)
            seen_bytes.append(data)
            self.assertEqual(kwargs.get("wait"), 900.0,
                             "MinerU 等待时限必须放宽到 900 秒")
            return {"ok": True, "markdown": "1. 求 $x+1=2$ 的解。", "detail": "ok"}

        with mock.patch.object(pending_bank, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(pending_bank, "save_draft",
                                  side_effect=lambda rows, **kwargs: saved.extend(rows)), \
                mock.patch.object(recognize_mineru.recognize_shared, "item_image_bytes",
                                  side_effect=lambda _item: b"\x89PNG-question"), \
                mock.patch.object(ai_center, "find_mineru",
                                  return_value=binding("mineru")), \
                mock.patch.object(recognize_mineru.mineru_extract, "extract",
                                  side_effect=fake_extract), \
                mock.patch.object(ingest_route, "save_route") as save_route:
            with self.assertLogs("app.core.recognize.recognize_mineru",
                                 level="INFO") as captured:
                route = await ingest_route.fill_scan_batch(
                    "B-002", recognize_router.RECOGNIZE_MINERU,
                    {"has_text_layer": False, "garbled": False})

        self.assertEqual(seen_names, ["第1题.png", "第2题.png", "第3题.png"])
        self.assertEqual(seen_bytes, [b"\x89PNG-question"] * 3)
        self.assertEqual(len(saved), 3, "每道题独立回填，互不干扰")
        progress = [line for line in captured.output
                    if "正在将第" in line and "MinerU 云端解析" in line]
        self.assertEqual(len(progress), 3)
        self.assertIn("正在将第 1 题发送至 MinerU 云端解析...", progress[0])
        self.assertEqual(save_route.call_count, 3, "进度要逐题写回批次路由")
        self.assertIn("3/3", route["note"])


class EngineUiContractTest(unittest.TestCase):
    def test_01_two_selects_sit_above_the_basket(self) -> None:
        col = HTML[HTML.index('class="ed-basket-col"'):]
        col = col[:col.index('class="ed-basket"')]
        self.assertIn('id="edLayoutEngine"', col)
        self.assertIn('id="edRecognizeEngine"', col)
        self.assertLess(col.index('id="edLayoutEngine"'),
                        col.index('id="edRecognizeEngine"'),
                        "左版面、右识别")
        for value in ("auto", "yolo", "cloud"):
            self.assertIn('<option value="%s"' % value, col)
        for value in ("auto", "full_ocr", "mineru"):
            self.assertIn('<option value="%s"' % value, col)
        self.assertGreaterEqual(col.count("title="), 6,
                                "每个下拉选项都要有原生 title 提示")

    def test_02_selection_rides_the_next_ingest_only(self) -> None:
        self.assertIn('hostCall("ingest.files"', INTAKE_JS)
        self.assertIn("state.ingestLayoutEngine", INTAKE_JS)
        self.assertIn("state.ingestRecognizeEngine", INTAKE_JS)
        self.assertIn("layout_engine: pickedLayout", INTAKE_JS)
        self.assertIn("recognize_engine: pickedRecognize", INTAKE_JS)
        go = INTAKE_JS[INTAKE_JS.index("function basketGo("):]
        go = go[:go.index("function collectToCanvas(")]
        self.assertIn("var pickedLayout = currentLayoutEngine();", go)
        self.assertIn("var pickedRecognize = currentRecognizeEngine();", go)
        self.assertNotIn("refreshBatches();", go[:go.index("pickedLayout")],
                         "选引擎不许顺手重跑任何旧批次")

    def test_03_no_storage_or_direct_network_in_engine_code(self) -> None:
        for token in ("localStorage", "sessionStorage", "XMLHttpRequest", "fetch("):
            self.assertNotIn(token, INTAKE_JS)

    def test_04_plugin_readme_documents_both_engines(self) -> None:
        readme = (PLUGIN_DIR / "README.md").read_text(encoding="utf-8")
        for token in ("版面引擎", "识别引擎", "YOLO", "MinerU", "全量OCR",
                      "JZO_YOLO_LAYOUT_URL", "Apache-2.0"):
            self.assertIn(token, readme)


if __name__ == "__main__":
    unittest.main()
