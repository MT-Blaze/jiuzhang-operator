# -*- coding: utf-8 -*-
"""审核重认（T6 §4）：老师点选席位→同张题图裁块/整题→原位替换，失败显性。

覆盖：席位未知/未就绪/已停用/无图各有人话错误码／整题重认各通道
（云 VLM/本地 VLM/MinerU 云/本地/PP-M 专科拒整题）／公式块重认（无坐标/序号越界/
原位替换/定位不到不裸拼）／失败挂批次失败清单 retryable／回填来源
review.reidentify＋待核旗清除／list_spans 只读／HTTP 口子形状校验。
外部引擎与池子全 mock，绝不触真服务真库。
运行：``.venv/Scripts/python.exe -m unittest tests.test_reidentify``
"""

from __future__ import annotations

import unittest
from contextlib import ExitStack
from unittest import mock

from fastapi import HTTPException

from app.api import pending_reidentify as api
from app.core.ingest import registry
from app.core.ingest.recognize import reidentify
from app.core.pending import service as pending_service
from app.core.pending.batch import batches
from app.core.pending.db import PendingNotFound

PID = "p_test0001"


def _item(stem: str = "已知 x+1=2，求值。", pending: bool = False) -> dict:
    document: dict = {"type": "solution", "stem": stem,
                      "source": {"question_no": "1"},
                      "images": [{"id": "img1", "role": "stem",
                                  "uri": "/static/pending/%s.png" % PID}]}
    if pending:
        document["extensions"] = {"org.jiuzhang.editor": {"formula_pending": True}}
    return {"id": PID, "batch_id": "B-001", "page_no": 1,
            "question": document, "assets": [{"name": PID + ".png"}]}


def _entry(step: str, state: str = "ready", enabled: bool = True) -> dict:
    return {"id": "seat_x", "name": "测试席", "state": state, "enabled": enabled,
            "detail": "" if state == "ready" else "未安装",
            "plan_recognize": [step] if step else []}


def _question(stem: str = "求 $x+1=2$ 的解。") -> dict:
    return {"type": "solution", "stem": stem, "options": [], "answer": "x=1",
            "solution": "移项得 $x=1$。", "question_no": "1", "difficulty": "L2"}


class CoreTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.item = _item()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(
            batches, "get_pending", side_effect=lambda pid: self.item))
        self.stack.enter_context(mock.patch.object(
            reidentify.recognize_shared, "item_image_bytes", return_value=b"png"))
        self.ledger: list[dict] = []
        self.stack.enter_context(mock.patch.object(
            pending_service, "read_batch_route", return_value={"failures": []}))
        self.stack.enter_context(mock.patch.object(
            pending_service, "set_batch_route",
            side_effect=lambda batch_id, route: self.ledger.append(route)))

    def _seat(self, entry: dict | None) -> None:
        self.stack.enter_context(mock.patch.object(
            registry, "entry_state", return_value=entry))

    def _save(self, ok: bool = True) -> mock.Mock:
        return self.stack.enter_context(mock.patch.object(
            reidentify.recognize_shared, "save_back", return_value=ok))

    async def test_unknown_seat_is_explicit(self) -> None:
        self._seat(None)
        result = await reidentify.reidentify(PID, "乱填")
        self.assertEqual(result["code"], "SEAT_UNKNOWN")

    async def test_unready_or_disabled_seat_is_explicit(self) -> None:
        for entry in (_entry("ai", state="degraded"),
                      _entry("ai", enabled=False)):
            with self.subTest(entry=entry):
                self._seat(entry)
                result = await reidentify.reidentify(PID, "seat_x")
                self.assertEqual(result["code"], "SEAT_NOT_READY")
                self.assertIn("未就绪", result["detail"])

    async def test_missing_image_is_explicit(self) -> None:
        self._seat(_entry("ai"))
        with mock.patch.object(reidentify.recognize_shared, "item_image_bytes",
                               return_value=b""):
            result = await reidentify.reidentify(PID, "seat_x")
        self.assertEqual(result["code"], "NO_IMAGE")

    async def test_cloud_whole_question_backfills_with_review_origin(self) -> None:
        self._seat(_entry("ai"))
        save_back = self._save()
        recognize = mock.AsyncMock(return_value={"ok": True, "question": _question()})
        with mock.patch.object(reidentify.ai_center, "resolve_task",
                               return_value=mock.Mock(is_configured=True)), \
                mock.patch.object(reidentify.ai_recognize, "recognize", recognize):
            result = await reidentify.reidentify(PID, "seat_x")
        self.assertTrue(result["ok"])
        self.assertEqual(result["seat"], "seat_x")
        self.assertEqual(result["target"], "question")
        self.assertEqual(save_back.call_args.args[3], "review.reidentify")
        document = save_back.call_args.args[1]
        self.assertEqual(document["stem"], "求 $x+1=2$ 的解。")
        self.assertEqual(document["images"], self.item["question"]["images"])
        self.assertEqual(recognize.await_args.kwargs["task"], "ocr")

    async def test_cloud_without_assignment_fails_into_ledger(self) -> None:
        self._seat(_entry("ai"))
        with mock.patch.object(reidentify.ai_center, "resolve_task",
                               return_value=mock.Mock(is_configured=False)):
            result = await reidentify.reidentify(PID, "seat_x")
        self.assertEqual(result["code"], "RECOGNIZE_FAILED")
        self.assertIn("还没指派", result["detail"])
        failure = self.ledger[-1]["failures"][-1]
        self.assertEqual(failure["step"], "审核·重认·%s" % PID)
        self.assertTrue(failure["retryable"])
        self.assertIn("还没指派", failure["reason"])

    async def test_local_vlm_whole_question(self) -> None:
        self._seat(_entry("vlm_local"))
        self._save()
        ready = {"ok": True, "base_url": "http://127.0.0.1:43210", "token": "tok"}
        with mock.patch.object(reidentify.vlm_service, "ensure_ready",
                               return_value=ready), \
                mock.patch.object(reidentify.vlm_local, "recognize_image",
                                  return_value={"ok": True, "question": _question()}) as recognize:
            result = await reidentify.reidentify(PID, "seat_x")
        self.assertTrue(result["ok"])
        self.assertEqual(recognize.call_args.kwargs["kind"], "question")

    async def test_mineru_local_whole_question_parses_markdown(self) -> None:
        self._seat(_entry("mineru_local"))
        save_back = self._save()
        ready = {"ok": True, "base_url": "http://127.0.0.1:43211", "token": "tok"}
        with mock.patch.object(reidentify.mineru_service, "ensure_ready",
                               return_value=ready), \
                mock.patch.object(reidentify.mineru_local, "parse_image",
                                  return_value={"ok": True,
                                                "markdown": "1. 求 $x+1=2$ 的解。"}):
            result = await reidentify.reidentify(PID, "seat_x")
        self.assertTrue(result["ok"])
        self.assertIn("求 $x+1=2$ 的解。", save_back.call_args.args[1]["stem"])

    async def test_mineru_cloud_without_account_is_explicit(self) -> None:
        self._seat(_entry("mineru"))
        with mock.patch.object(reidentify.ai_center, "find_mineru", return_value=None):
            result = await reidentify.reidentify(PID, "seat_x")
        self.assertEqual(result["code"], "RECOGNIZE_FAILED")
        self.assertIn("没有可用的账号", result["detail"])

    async def test_specialty_seat_says_next_card(self) -> None:
        self._seat(_entry(""))
        result = await reidentify.reidentify(PID, "seat_x")
        self.assertEqual(result["code"], "RECOGNIZE_FAILED")
        self.assertIn("下一卡开", result["detail"])

    async def test_combo_chain_refused_for_whole_question(self) -> None:
        self._seat(_entry("combo"))
        result = await reidentify.reidentify(PID, "seat_x")
        self.assertEqual(result["code"], "RECOGNIZE_FAILED")
        self.assertIn("不支持单题重认", result["detail"])

    async def test_pp_m_whole_question_refused_with_seat_guide(self) -> None:
        self._seat(_entry("formula_pp_m"))
        result = await reidentify.reidentify(PID, "seat_x")
        self.assertEqual(result["code"], "RECOGNIZE_FAILED")
        self.assertIn("公式专科座", result["detail"])
        self.assertIn("整题座", result["detail"])

    async def test_pp_l_whole_question_refused_with_seat_guide(self) -> None:
        self._seat(_entry("formula_pp_l"))
        result = await reidentify.reidentify(PID, "seat_x")
        self.assertEqual(result["code"], "RECOGNIZE_FAILED")
        self.assertIn("公式专科座", result["detail"])
        self.assertIn("整题座", result["detail"])

    async def test_pp_m_formula_block_replaces_in_place(self) -> None:
        self._seat(_entry("formula_pp_m"))
        save_back = self._save()
        span = {"bbox": [10, 10, 40, 20], "text": "x+1=2", "latex": "",
                "origin": "textlayer"}
        recognize = mock.Mock(return_value={"ok": True, "latex": "x^3",
                                            "detail": "PP-FormulaNet·M 公式已转写"})
        with mock.patch.object(reidentify.recognize_formula, "batch_context",
                               return_value=([], b"")), \
                mock.patch.object(reidentify.recognize_formula, "discover_spans",
                                  return_value=[span]), \
                mock.patch.object(reidentify.recognize_formula, "crop_png",
                                  return_value=b"crop"), \
                mock.patch.object(reidentify.recognize_formula.formula_pp_m,
                                  "recognize", recognize):
            result = await reidentify.reidentify(PID, "seat_x", target="formula")
        self.assertTrue(result["ok"])
        self.assertEqual(save_back.call_args.args[1]["stem"], "已知 $x^3$，求值。")
        recognize.assert_called_once_with(b"crop")

    async def test_pp_m_uninstalled_seat_not_ready_guides_install(self) -> None:
        self._seat(_entry("formula_pp_m", state="degraded"))
        result = await reidentify.reidentify(PID, "seat_x", target="formula")
        self.assertEqual(result["code"], "SEAT_NOT_READY")
        self.assertIn("未就绪", result["detail"])

    async def test_combo_chain_refused_for_formula_block(self) -> None:
        result = await reidentify.recognize_formula.dispatch(
            _entry("combo"), b"png", self.item)
        self.assertFalse(result["ok"])
        self.assertIn("不支持单块公式重认", result["detail"])

    async def test_formula_without_coords_points_to_whole_question(self) -> None:
        self._seat(_entry("ai"))
        with mock.patch.object(reidentify.recognize_formula, "batch_context",
                               return_value=([], b"")), \
                mock.patch.object(reidentify.recognize_formula, "discover_spans",
                                  return_value=[]):
            result = await reidentify.reidentify(PID, "seat_x", target="formula")
        self.assertEqual(result["code"], "NO_COORDS")
        self.assertIn("整题重认", result["detail"])

    async def test_formula_span_index_out_of_range(self) -> None:
        self._seat(_entry("ai"))
        span = {"bbox": [10, 10, 40, 20], "text": "x+1=2", "latex": "",
                "origin": "textlayer"}
        with mock.patch.object(reidentify.recognize_formula, "batch_context",
                               return_value=([], b"")), \
                mock.patch.object(reidentify.recognize_formula, "discover_spans",
                                  return_value=[span]):
            result = await reidentify.reidentify(PID, "seat_x", target="formula",
                                                 span_index=5)
        self.assertEqual(result["code"], "BAD_SPAN")

    async def test_formula_success_replaces_only_the_fragment(self) -> None:
        self._seat(_entry("ai"))
        save_back = self._save()
        span = {"bbox": [10, 10, 40, 20], "text": "x+1=2", "latex": "",
                "origin": "textlayer"}
        with mock.patch.object(reidentify.recognize_formula, "batch_context",
                               return_value=([], b"")), \
                mock.patch.object(reidentify.recognize_formula, "discover_spans",
                                  return_value=[span]), \
                mock.patch.object(reidentify.recognize_formula, "crop_png",
                                  return_value=b"crop") as crop, \
                mock.patch.object(reidentify.recognize_formula, "dispatch",
                                  mock.AsyncMock(return_value={"ok": True, "latex": "x^3"})):
            result = await reidentify.reidentify(PID, "seat_x", target="formula")
        self.assertTrue(result["ok"])
        crop.assert_called_once_with(b"png", span["bbox"])
        self.assertEqual(save_back.call_args.args[1]["stem"], "已知 $x^3$，求值。")

    async def test_formula_locate_failure_never_blind_concat(self) -> None:
        self.item = _item(stem="已知 $y$，求值。")
        self._seat(_entry("ai"))
        span = {"bbox": [10, 10, 40, 20], "text": "x+1=2", "latex": "",
                "origin": "textlayer"}
        with mock.patch.object(reidentify.recognize_formula, "batch_context",
                               return_value=([], b"")), \
                mock.patch.object(reidentify.recognize_formula, "discover_spans",
                                  return_value=[span]), \
                mock.patch.object(reidentify.recognize_formula, "crop_png",
                                  return_value=b"crop"), \
                mock.patch.object(reidentify.recognize_formula, "dispatch",
                                  mock.AsyncMock(return_value={"ok": True, "latex": "x^3"})):
            result = await reidentify.reidentify(PID, "seat_x", target="formula")
        self.assertEqual(result["code"], "REPLACE_FAILED")
        self.assertIn("不裸拼", result["detail"])
        self.assertTrue(self.ledger)

    async def test_save_rejected_is_explicit(self) -> None:
        self._seat(_entry("ai"))
        self._save(ok=False)
        with mock.patch.object(reidentify.ai_center, "resolve_task",
                               return_value=mock.Mock(is_configured=True)), \
                mock.patch.object(reidentify.ai_recognize, "recognize",
                                  mock.AsyncMock(return_value={"ok": True,
                                                               "question": _question()})):
            result = await reidentify.reidentify(PID, "seat_x")
        self.assertEqual(result["code"], "SAVE_FAILED")
        self.assertTrue(self.ledger)

    async def test_success_clears_formula_pending_flag(self) -> None:
        self.item = _item(pending=True)
        self._seat(_entry("ai"))
        save_back = self._save()
        with mock.patch.object(reidentify.ai_center, "resolve_task",
                               return_value=mock.Mock(is_configured=True)), \
                mock.patch.object(reidentify.ai_recognize, "recognize",
                                  mock.AsyncMock(return_value={"ok": True,
                                                               "question": _question()})):
            result = await reidentify.reidentify(PID, "seat_x")
        self.assertTrue(result["ok"])
        editor = save_back.call_args.args[1].get("extensions", {}).get(
            "org.jiuzhang.editor", {})
        self.assertFalse(editor.get("formula_pending"))

    async def test_list_spans_is_readonly_preview(self) -> None:
        spans = [{"bbox": [0, 0, 10, 10], "text": "x" * 120, "latex": "",
                  "origin": "textlayer"},
                 {"bbox": [0, 0, 10, 10], "text": "", "latex": "x^2",
                  "origin": "mineru"}]
        with mock.patch.object(reidentify.recognize_formula, "batch_context",
                               return_value=([], b"")), \
                mock.patch.object(reidentify.recognize_formula, "discover_spans",
                                  return_value=spans):
            result = await reidentify.list_spans(PID)
        self.assertTrue(result["ok"])
        self.assertEqual([row["index"] for row in result["spans"]], [0, 1])
        self.assertEqual(result["spans"][0]["origin"], "textlayer")
        self.assertEqual(len(result["spans"][0]["preview"]), 80)
        self.assertEqual(result["spans"][1]["preview"], "x^2")


class ApiShapeTest(unittest.IsolatedAsyncioTestCase):
    """HTTP 口子只做鉴权与形状校验；写令牌依赖由探针真服务器覆盖。"""

    async def test_bad_shapes_are_400(self) -> None:
        cases = [{"pending_id": "bad", "seat": "x"},
                 {"pending_id": PID, "seat": ""},
                 {"pending_id": PID, "seat": "x", "target": "乱填"},
                 {"pending_id": PID, "seat": "x", "span_index": "abc"},
                 {"pending_id": PID, "seat": "x", "span_index": 32}]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(HTTPException) as caught:
                    await api.pending_reidentify(payload)
                self.assertEqual(caught.exception.status_code, 400)

    async def test_valid_payload_reaches_core_with_defaults(self) -> None:
        core = mock.AsyncMock(return_value={"ok": True})
        with mock.patch.object(api.recognize_reidentify, "reidentify", core):
            result = await api.pending_reidentify({"pending_id": PID, "seat": "seat_x"})
        self.assertTrue(result["ok"])
        core.assert_awaited_once_with(PID, "seat_x", "question", 0)

    async def test_missing_pending_is_404(self) -> None:
        with mock.patch.object(api.recognize_reidentify, "reidentify",
                               mock.AsyncMock(side_effect=PendingNotFound("没有这一条"))):
            with self.assertRaises(HTTPException) as caught:
                await api.pending_reidentify({"pending_id": PID, "seat": "seat_x"})
        self.assertEqual(caught.exception.status_code, 404)

    async def test_spans_endpoint_validates_pid(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await api.reidentify_spans("bad")
        self.assertEqual(caught.exception.status_code, 400)
        spans = mock.AsyncMock(return_value={"ok": True, "spans": []})
        with mock.patch.object(api.recognize_reidentify, "list_spans", spans):
            result = await api.reidentify_spans(PID)
        self.assertTrue(result["ok"])
        spans.assert_awaited_once_with(PID)


if __name__ == "__main__":
    unittest.main()