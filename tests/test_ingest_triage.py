# -*- coding: utf-8 -*-
"""解析通道、四特征坏题体检与 30% 分诊契约。

钉住五件事：
1. 四个通道的白名单与 ``INGEST_BAD_RATE_THRESHOLD = 0.30`` 是单源；
2. 四特征（连续空选项 / 掉变量句式 / 内联小图多但无公式 / 长文无符号）各报各的；
3. 每次解析静默打一行 ``[STAT] 本次解析总题数: X, 坏题数: Y, 坏题率: Z%``；
4. 坏题率低于阈值只补坏题，达到阈值自动改走并发全量 OCR；
5. MinerU 通道逐题发送单题截图（绝不发整卷 PDF），进度逐题写进日志与路由。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ingest_triage``
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from app.core import ai_center, ingest_route, pending_bank
from app.core.ingest_quality import question_reasons, triage_documents
from app.core.ingest_route import (
    CHANNEL_AUTO,
    CHANNEL_FULL_OCR,
    CHANNEL_LOCAL_AI,
    CHANNEL_MINERU,
    INGEST_BAD_RATE_THRESHOLD,
    normalize_channel,
)

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


class ChannelConstantTest(unittest.TestCase):
    def test_01_four_channels_and_threshold(self) -> None:
        self.assertEqual(INGEST_BAD_RATE_THRESHOLD, 0.30)
        for key in ("auto", "local_ai", "full_ocr", "mineru"):
            self.assertIn(key, ingest_route.CHANNELS)
        self.assertEqual(normalize_channel("MINERU"), CHANNEL_MINERU)
        self.assertEqual(normalize_channel("乱填"), CHANNEL_AUTO)
        self.assertEqual(normalize_channel(None), CHANNEL_AUTO)

    def test_02_old_whole_pdf_route_is_no_longer_wired_into_ingest(self) -> None:
        from app.core import ingest

        self.assertNotIn("route_scan_pdf", ingest.__dict__,
                         "整卷 PDF 直送 MinerU 的老口子必须从解析主流程退场")


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
    async def _run(self, documents: list[dict], channel: str = CHANNEL_AUTO) -> dict:
        items = [item("p_test%02d" % index, document) for index, document in enumerate(documents)]
        saved: list[dict] = []

        def capture(rows, **_kwargs):
            saved.extend(rows)
            return {"saved_ids": [row.get("pending_id") for row in rows]}

        with mock.patch.object(pending_bank, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(pending_bank, "save_draft", side_effect=capture), \
                mock.patch.object(ingest_route.ai_center, "resolve_task",
                                  return_value=binding()), \
                mock.patch.object(ingest_route.ai_recognize, "recognize",
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
                "B-001", channel, {"has_text_layer": True, "garbled": False})
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

    async def test_local_ai_channel_still_patches_bad_questions(self) -> None:
        docs = [clean_doc(index) for index in range(8)] + [
            broken_doc("empty_options"), broken_doc("dropped_var")]
        outcome = await self._run(docs, channel=CHANNEL_LOCAL_AI)
        self.assertEqual(outcome["recognize"].await_count, 2,
                         "本地+AI 通道低坏题率同样只补坏题")
        self.assertIn("局部修补", outcome["route"]["note"])

    async def test_at_threshold_switches_to_full_ocr(self) -> None:
        docs = [clean_doc(index) for index in range(7)] + [
            broken_doc("empty_options"), broken_doc("dropped_var"),
            broken_doc("long_no_symbol")]
        outcome = await self._run(docs)
        self.assertEqual(outcome["recognize"].await_count, 10,
                         "坏题率达到 30% 就整批改走并发全量 OCR")
        self.assertEqual(outcome["route"]["mode"], "full_ocr")
        self.assertIn("并发全量 OCR", outcome["route"]["note"])

    async def test_full_ocr_channel_ignores_threshold(self) -> None:
        docs = [clean_doc(index) for index in range(10)]
        outcome = await self._run(docs, channel=CHANNEL_FULL_OCR)
        self.assertEqual(outcome["recognize"].await_count, 10)
        self.assertEqual(outcome["route"]["mode"], "full_ocr")

    async def test_clean_batch_does_not_call_ai(self) -> None:
        outcome = await self._run([clean_doc(index) for index in range(5)])
        self.assertEqual(outcome["recognize"].await_count, 0)
        self.assertIn("未发现坏题", outcome["route"]["note"])


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
                mock.patch.object(ingest_route, "_item_image_bytes",
                                  side_effect=lambda _item: b"\x89PNG-question"), \
                mock.patch.object(ingest_route.ai_center, "find_mineru",
                                  return_value=binding("mineru")), \
                mock.patch.object(ingest_route.mineru_extract, "extract",
                                  side_effect=fake_extract), \
                mock.patch.object(ingest_route, "save_route") as save_route:
            with self.assertLogs("app.core.ingest_route", level="INFO") as captured:
                route = await ingest_route.fill_scan_batch(
                    "B-002", CHANNEL_MINERU, {"has_text_layer": False, "garbled": False})

        self.assertEqual(seen_names, ["第1题.png", "第2题.png", "第3题.png"])
        self.assertEqual(seen_bytes, [b"\x89PNG-question"] * 3)
        self.assertEqual(len(saved), 3, "每道题独立回填，互不干扰")
        progress = [line for line in captured.output
                    if "正在将第" in line and "MinerU 云端解析" in line]
        self.assertEqual(len(progress), 3)
        self.assertIn("正在将第 1 题发送至 MinerU 云端解析...", progress[0])
        self.assertEqual(save_route.call_count, 3, "进度要逐题写回批次路由")
        self.assertIn("3/3", route["note"])


class ChannelUiContractTest(unittest.TestCase):
    def test_01_four_buttons_sit_left_of_api_config(self) -> None:
        head = HTML[HTML.index('class="ed-batches-head"'):]
        head = head[:head.index("</div>", head.index('id="epAiConfigList"'))]
        self.assertIn('id="edRouteChannels"', head)
        self.assertLess(head.index('id="edRouteChannels"'),
                        head.index('id="epAiConfigList"'))
        for channel in ("auto", "local_ai", "full_ocr", "mineru"):
            self.assertIn('data-channel="%s"' % channel, head)
        self.assertIn('aria-pressed="true"', head, "自动通道默认选中")

    def test_02_selection_rides_the_next_ingest_only(self) -> None:
        self.assertIn('hostCall("ingest.files"', INTAKE_JS)
        self.assertIn("state.ingestChannel", INTAKE_JS)
        self.assertIn("channel: channel || currentChannel()", INTAKE_JS)
        go = INTAKE_JS[INTAKE_JS.index("function basketGo("):]
        go = go[:go.index("function collectToCanvas(")]
        self.assertIn("var pickedChannel = currentChannel();", go)
        self.assertNotIn("refreshBatches();", go[:go.index("pickedChannel")],
                         "选通道不许顺手重跑任何旧批次")

    def test_03_no_storage_or_direct_network_in_channel_code(self) -> None:
        for token in ("localStorage", "sessionStorage", "XMLHttpRequest", "fetch("):
            self.assertNotIn(token, INTAKE_JS)


if __name__ == "__main__":
    unittest.main()
