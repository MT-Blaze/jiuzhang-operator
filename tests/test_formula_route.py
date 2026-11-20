# -*- coding: utf-8 -*-
"""公式裁图通道（T6 §2 组合路＋§4 重认裁块）：坐标→同张题图裁块→送席→原位替换。

覆盖：裁块像素边界（太小/越界/坏图不编图）／MinerU 归一化 bbox→像素／
无坐标＝空交整题兜底／席位按 catalog 步骤名分派（云 VLM/本地 VLM/MinerU/
PP-M 专科真跑＋未装引导，其余专科 blocked 显性）／原位替换两条匹配／
组合路：公式座未就绪→标待核＋失败清单，正文不动不整题降级。
运行：``.venv/Scripts/python.exe -m unittest tests.test_formula_route``
"""

from __future__ import annotations

import io
import unittest
from unittest import mock

from PIL import Image

from app.core.ai.platform import center as ai_center
from app.core.ingest import registry
from app.core.ingest.recognize import formula


def _png(width: int = 100, height: int = 80) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(out, "PNG")
    return out.getvalue()


def _item(stem: str = "已知 x+1=2，求值。", boxes: list | None = None,
          pending: bool = False) -> dict:
    editor: dict = {}
    if boxes is not None:
        editor["formula_boxes"] = boxes
    if pending:
        editor["formula_pending"] = True
    document: dict = {"type": "solution", "stem": stem,
                      "source": {"question_no": "1"},
                      "images": [{"id": "img1", "role": "stem",
                                  "uri": "/static/pending/p_test0001.png"}]}
    if editor:
        document["extensions"] = {formula.EDITOR_NS: editor}
    return {"id": "p_test0001", "batch_id": "B-001", "page_no": 1,
            "question": document, "assets": [{"name": "p_test0001.png"}]}


def _binding(configured: bool = True) -> ai_center.TaskBinding:
    return ai_center.TaskBinding(
        task="ocr", account_id="acc_0000000001" if configured else "",
        name="测试" if configured else "",
        base_url="https://api.test/v1" if configured else "",
        api_key="fixture" if configured else "",
        model="vision" if configured else "")


class CropTest(unittest.TestCase):
    def test_crop_returns_exact_pixel_block(self) -> None:
        out = formula.crop_png(_png(), [10, 10, 40, 30])
        with Image.open(io.BytesIO(out)) as image:
            self.assertEqual(image.size, (40, 30))

    def test_tiny_or_garbage_crop_is_empty_never_fabricated(self) -> None:
        self.assertEqual(formula.crop_png(_png(), [10, 10, 4, 4]), b"")
        self.assertEqual(formula.crop_png(b"not a png", [0, 0, 50, 50]), b"")

    def test_out_of_bounds_bbox_is_clamped(self) -> None:
        out = formula.crop_png(_png(), [90, 70, 500, 500])
        with Image.open(io.BytesIO(out)) as image:
            self.assertEqual(image.size, (10, 10))


class SpanTest(unittest.TestCase):
    def test_mineru_normalized_bbox_becomes_question_pixels(self) -> None:
        item = _item(boxes=[{"bbox": [0.1, 0.2, 0.5, 0.4], "latex": "x^2"}])
        with mock.patch.object(formula.recognize_shared, "item_image_bytes",
                               return_value=_png()):
            spans = formula.discover_spans(item)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["origin"], "mineru")
        self.assertEqual(spans[0]["bbox"], [10.0, 16.0, 40.0, 16.0])
        self.assertEqual(spans[0]["latex"], "x^2")

    def test_mineru_boxes_win_over_textlayer(self) -> None:
        item = _item(boxes=[{"bbox": [0.1, 0.2, 0.5, 0.4]}])
        with mock.patch.object(formula.recognize_shared, "item_image_bytes",
                               return_value=_png()), \
                mock.patch.object(formula, "_textlayer_spans") as textlayer:
            spans = formula.discover_spans(item, [{"page": 1}], b"%PDF-fake")
        self.assertEqual(spans[0]["origin"], "mineru")
        textlayer.assert_not_called()

    def test_no_coords_means_empty_for_whole_question_fallback(self) -> None:
        with mock.patch.object(formula.recognize_shared, "item_image_bytes",
                               return_value=_png()):
            self.assertEqual(formula.discover_spans(_item()), [])
            self.assertEqual(formula.discover_spans(_item(), [], b""), [])

    def test_no_image_means_no_spans(self) -> None:
        with mock.patch.object(formula.recognize_shared, "item_image_bytes",
                               return_value=b""):
            self.assertEqual(formula.discover_spans(_item()), [])

    def test_span_count_is_capped(self) -> None:
        boxes = [{"bbox": [0.1, 0.1, 0.3, 0.3]} for _ in range(40)]
        with mock.patch.object(formula.recognize_shared, "item_image_bytes",
                               return_value=_png()):
            spans = formula.discover_spans(_item(boxes=boxes))
        self.assertEqual(len(spans), formula.MAX_SPANS)


class DispatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_empty_crop_is_explicit_failure(self) -> None:
        outcome = await formula.dispatch({"plan_recognize": ["ai"]}, b"", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("裁不出来", outcome["detail"])

    async def test_specialty_seat_says_next_card_not_fake_button(self) -> None:
        entry = {"plan_recognize": ["pp_formulanet"],
                 "detail": "专科推理通道下一卡开（D 卡：安装＋推理＋擂台同在）。"}
        outcome = await formula.dispatch(entry, b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("下一卡开", outcome["detail"])
        bare = await formula.dispatch({}, b"png", _item())
        self.assertIn("下一卡开", bare["detail"])

    async def test_cloud_vlm_without_assignment_is_explicit(self) -> None:
        with mock.patch.object(formula.ai_center, "resolve_task",
                               return_value=_binding(False)):
            outcome = await formula.dispatch({"plan_recognize": ["ai"]}, b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("还没指派", outcome["detail"])

    async def test_cloud_vlm_success_strips_dollars(self) -> None:
        recognize = mock.AsyncMock(return_value={
            "ok": True, "question": {"stem": "$$x^2$$"}})
        with mock.patch.object(formula.ai_center, "resolve_task",
                               return_value=_binding()), \
                mock.patch.object(formula.ai_recognize, "recognize", recognize):
            outcome = await formula.dispatch({"plan_recognize": ["ai"]}, b"png", _item())
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["latex"], "x^2")
        self.assertEqual(recognize.await_args.kwargs["task"], "ocr")

    async def test_cloud_vlm_exception_is_explicit(self) -> None:
        with mock.patch.object(formula.ai_center, "resolve_task",
                               return_value=_binding()), \
                mock.patch.object(formula.ai_recognize, "recognize",
                                  mock.AsyncMock(side_effect=RuntimeError("出网断了"))):
            outcome = await formula.dispatch({"plan_recognize": ["ai"]}, b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("云端视觉公式识别失败", outcome["detail"])

    async def test_local_vlm_seat_reuses_single_image_ability(self) -> None:
        ready = {"ok": True, "base_url": "http://127.0.0.1:43210", "token": "tok"}
        with mock.patch.object(formula.vlm_service, "ensure_ready",
                               return_value=ready), \
                mock.patch.object(formula.vlm_local, "recognize_image",
                                  return_value={"ok": True, "latex": "x^3"}) as recognize:
            outcome = await formula.dispatch({"plan_recognize": ["vlm_local"]},
                                             b"png", _item())
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["latex"], "x^3")
        self.assertEqual(recognize.call_args.kwargs["kind"], "formula")

    async def test_local_vlm_unready_is_explicit(self) -> None:
        with mock.patch.object(formula.vlm_service, "ensure_ready",
                               return_value={"ok": False, "detail": "未安装，请点安装"}):
            outcome = await formula.dispatch({"plan_recognize": ["vlm_local"]},
                                             b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("请点安装", outcome["detail"])

    async def test_mineru_cloud_without_account_is_explicit(self) -> None:
        with mock.patch.object(formula.ai_center, "find_mineru", return_value=None):
            outcome = await formula.dispatch({"plan_recognize": ["mineru"]},
                                             b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("没有可用的账号", outcome["detail"])

    async def test_mineru_local_success_strips_dollars(self) -> None:
        ready = {"ok": True, "base_url": "http://127.0.0.1:43211", "token": "tok"}
        with mock.patch.object(formula.mineru_service, "ensure_ready",
                               return_value=ready), \
                mock.patch.object(formula.mineru_local, "parse_image",
                                  return_value={"ok": True, "markdown": "$x^2$"}):
            outcome = await formula.dispatch({"plan_recognize": ["mineru_local"]},
                                             b"png", _item())
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["latex"], "x^2")

    async def test_pp_m_success_passes_engine_contract_through(self) -> None:
        recognize = mock.Mock(return_value={"ok": True, "latex": r"\frac{1}{2}",
                                            "detail": "PP-FormulaNet·M 公式已转写"})
        with mock.patch.object(formula.formula_pp_m, "recognize", recognize):
            outcome = await formula.dispatch({"plan_recognize": ["formula_pp_m"]},
                                             b"png", _item())
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["latex"], r"\frac{1}{2}")
        self.assertEqual(outcome["detail"], "PP-FormulaNet·M 公式已转写")
        recognize.assert_called_once_with(b"png")

    async def test_pp_m_uninstalled_guides_to_install_button(self) -> None:
        formula.formula_pp_m.reset()
        with mock.patch.object(formula.formula_pp_m.formula_setup, "weights_ready",
                               return_value=False):
            outcome = await formula.dispatch({"plan_recognize": ["formula_pp_m"]},
                                             b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("权重未安装", outcome["detail"])
        self.assertIn("安装", outcome["detail"])

    async def test_pp_m_engine_failure_is_explicit(self) -> None:
        with mock.patch.object(formula.formula_pp_m, "recognize",
                               return_value={"ok": False, "latex": "",
                                             "detail": "PP-FormulaNet·M 推理失败：会话崩了"}):
            outcome = await formula.dispatch({"plan_recognize": ["formula_pp_m"]},
                                             b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("推理失败", outcome["detail"])

    async def test_pp_l_success_passes_engine_contract_through(self) -> None:
        recognize = mock.Mock(return_value={"ok": True, "latex": r"\frac{1}{2}",
                                            "detail": "PP-FormulaNet·L 公式已转写"})
        with mock.patch.object(formula.formula_pp_l, "recognize", recognize):
            outcome = await formula.dispatch({"plan_recognize": ["formula_pp_l"]},
                                             b"png", _item())
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["latex"], r"\frac{1}{2}")
        self.assertEqual(outcome["detail"], "PP-FormulaNet·L 公式已转写")
        recognize.assert_called_once_with(b"png")

    async def test_pp_l_uninstalled_guides_to_install_button(self) -> None:
        formula.formula_pp_l.reset()
        with mock.patch.object(formula.formula_pp_l.formula_setup, "weights_ready",
                               return_value=False):
            outcome = await formula.dispatch({"plan_recognize": ["formula_pp_l"]},
                                             b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("权重未安装", outcome["detail"])
        self.assertIn("安装", outcome["detail"])

    async def test_p2t_success_passes_engine_contract_through(self) -> None:
        recognize = mock.Mock(return_value={"ok": True, "latex": r"\frac{1}{2}",
                                            "detail": "Pix2Text·MFR 公式已转写"})
        with mock.patch.object(formula.formula_p2t, "recognize", recognize):
            outcome = await formula.dispatch({"plan_recognize": ["formula_p2t"]},
                                             b"png", _item())
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["latex"], r"\frac{1}{2}")
        self.assertEqual(outcome["detail"], "Pix2Text·MFR 公式已转写")
        recognize.assert_called_once_with(b"png")

    async def test_p2t_uninstalled_guides_to_install_button(self) -> None:
        formula.formula_p2t.reset()
        with mock.patch.object(formula.formula_p2t.formula_setup, "weights_ready",
                               return_value=False):
            outcome = await formula.dispatch({"plan_recognize": ["formula_p2t"]},
                                             b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("权重未安装", outcome["detail"])
        self.assertIn("安装", outcome["detail"])

    async def test_texify_success_passes_engine_contract_through(self) -> None:
        recognize = mock.Mock(return_value={"ok": True, "latex": r"\frac{1}{2}",
                                            "detail": "Texify 公式已转写"})
        with mock.patch.object(formula.formula_texify, "recognize", recognize):
            outcome = await formula.dispatch({"plan_recognize": ["formula_texify"]},
                                             b"png", _item())
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["latex"], r"\frac{1}{2}")
        self.assertEqual(outcome["detail"], "Texify 公式已转写")
        recognize.assert_called_once_with(b"png")

    async def test_texify_uninstalled_guides_to_install_button(self) -> None:
        formula.formula_texify.reset()
        with mock.patch.object(formula.formula_texify.formula_setup, "weights_ready",
                               return_value=False):
            outcome = await formula.dispatch({"plan_recognize": ["formula_texify"]},
                                             b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("权重未安装", outcome["detail"])
        self.assertIn("安装", outcome["detail"])

    async def test_texify_engine_failure_is_explicit(self) -> None:
        with mock.patch.object(formula.formula_texify, "recognize",
                               return_value={"ok": False, "latex": "",
                                             "detail": "Texify 推理失败：会话崩了"}):
            outcome = await formula.dispatch({"plan_recognize": ["formula_texify"]},
                                             b"png", _item())
        self.assertFalse(outcome["ok"])
        self.assertIn("推理失败", outcome["detail"])


class ReplaceTest(unittest.TestCase):
    def test_textlayer_replaces_original_run_in_place(self) -> None:
        span = {"text": "x+1=2", "latex": "", "origin": "textlayer"}
        out = formula.replace_fragment("已知 x+1=2，求值。", span, "x^3")
        self.assertEqual(out, "已知 $x^3$，求值。")

    def test_mineru_matches_known_latex_ignoring_spaces(self) -> None:
        span = {"text": "", "latex": "x^2", "origin": "mineru"}
        out = formula.replace_fragment("已知 $ x^2 $，求值。", span, "x^3")
        self.assertEqual(out, "已知 $x^3$，求值。")

    def test_no_match_returns_none_never_blind_concat(self) -> None:
        span = {"text": "y+2", "latex": "y^2", "origin": "mineru"}
        self.assertIsNone(formula.replace_fragment("已知 $x^2$，求值。", span, "x^3"))

    def test_textlayer_normalized_stem_matches_derived_known(self) -> None:
        # 文字直取已把强数学串归一包 $...$：原串不在题面里，按同规则推已知片段匹配。
        span = {"text": " x > 0", "latex": "", "origin": "textlayer"}
        out = formula.replace_fragment("已知 $x > 0$，求值。", span, "x^3")
        self.assertEqual(out, "已知 $x^3$，求值。")

    def test_textlayer_roundtrip_with_scan_text_normalization(self) -> None:
        from app.core.content import scan_text
        stem = scan_text.text_to_latex("已知 x∈R，求值。")
        span = {"text": "x∈R", "latex": "", "origin": "textlayer"}
        out = formula.replace_fragment(stem, span, "x^3")
        self.assertEqual(out, "已知 $x^3$，求值。")

    def test_textlayer_mismatch_still_returns_none(self) -> None:
        span = {"text": "y+2", "latex": "", "origin": "textlayer"}
        self.assertIsNone(formula.replace_fragment("已知 $x^2$，求值。", span, "x^3"))


class ComboTest(unittest.IsolatedAsyncioTestCase):
    async def test_unready_seat_marks_pending_and_surfaces_failure(self) -> None:
        item = _item(pending=False)
        entry = {"id": "formula_pp_m", "name": "PP-FormulaNet·M",
                 "state": "blocked", "enabled": True,
                 "detail": "专科推理通道下一卡开（D 卡）。"}
        span = {"bbox": [10, 10, 40, 20], "text": "x+1=2", "latex": "",
                "origin": "textlayer"}
        with mock.patch.object(registry, "entry_state", return_value=entry), \
                mock.patch.object(formula.recognize_shared, "item_image_bytes",
                                  return_value=_png()), \
                mock.patch.object(formula, "discover_spans",
                                  side_effect=[[span], []]), \
                mock.patch.object(formula.recognize_shared, "save_back",
                                  return_value=True) as save_back:
            route: dict = {}
            result = await formula.run_combo(
                "B-001", [item, _item()], [0, 1], "formula_pp_m", route, None, [], b"")
        self.assertFalse(result["seat_ready"])
        self.assertIn("未就绪", result["seat_reason"])
        self.assertEqual(result["attempted"], 1)
        self.assertEqual(result["no_coord_indexes"], [1])
        self.assertEqual(result["pending_marks"], 1)
        self.assertEqual(save_back.call_args.args[3], "ingest.combo_formula")
        marked = save_back.call_args.args[1]
        self.assertTrue(marked["extensions"][formula.EDITOR_NS]["formula_pending"])
        self.assertEqual(marked["stem"], item["question"]["stem"],
                         "正文保留文字直取，不整题降级")
        failures = route["failures"]
        self.assertEqual(failures[0]["step"], "识别·公式裁图")
        self.assertTrue(failures[0]["retryable"])

    async def test_missing_seat_says_go_pick_another(self) -> None:
        with mock.patch.object(registry, "entry_state", return_value=None), \
                mock.patch.object(formula.recognize_shared, "item_image_bytes",
                                  return_value=_png()), \
                mock.patch.object(formula, "discover_spans", return_value=[]):
            result = await formula.run_combo(
                "B-001", [_item()], [0], "", {}, None, [], b"")
        self.assertIn("不在模型目录", result["seat_reason"])
        self.assertEqual(result["no_coord_indexes"], [0])

    async def test_ready_seat_replaces_in_place_and_clears_pending(self) -> None:
        item = _item(pending=True)
        entry = {"id": "cloud_vision", "name": "云端 AI OCR", "state": "ready",
                 "enabled": True, "plan_recognize": ["ai"]}
        span = {"bbox": [10, 10, 40, 20], "text": "x+1=2", "latex": "",
                "origin": "textlayer"}
        with mock.patch.object(registry, "entry_state", return_value=entry), \
                mock.patch.object(formula.recognize_shared, "item_image_bytes",
                                  return_value=_png()), \
                mock.patch.object(formula, "discover_spans", return_value=[span]), \
                mock.patch.object(formula, "dispatch",
                                  mock.AsyncMock(return_value={"ok": True, "latex": "x^3"})), \
                mock.patch.object(formula.recognize_shared, "save_back",
                                  return_value=True) as save_back:
            route: dict = {}
            result = await formula.run_combo(
                "B-001", [item], [0], "cloud_vision", route, None, [], b"")
        self.assertEqual(result["filled_indexes"], [0])
        self.assertEqual(result["pending_marks"], 0)
        document = save_back.call_args.args[1]
        self.assertEqual(document["stem"], "已知 $x^3$，求值。")
        editor = document["extensions"][formula.EDITOR_NS]
        self.assertFalse(editor.get("formula_pending"))
        self.assertNotIn("failures", route)

    async def test_dispatch_failure_marks_pending_not_whole_downgrade(self) -> None:
        item = _item()
        entry = {"id": "cloud_vision", "name": "云端 AI OCR", "state": "ready",
                 "enabled": True, "plan_recognize": ["ai"]}
        span = {"bbox": [10, 10, 40, 20], "text": "x+1=2", "latex": "",
                "origin": "textlayer"}
        with mock.patch.object(registry, "entry_state", return_value=entry), \
                mock.patch.object(formula.recognize_shared, "item_image_bytes",
                                  return_value=_png()), \
                mock.patch.object(formula, "discover_spans", return_value=[span]), \
                mock.patch.object(formula, "dispatch",
                                  mock.AsyncMock(return_value={"ok": False, "detail": "超时"})), \
                mock.patch.object(formula.recognize_shared, "save_back",
                                  return_value=True) as save_back:
            route: dict = {}
            result = await formula.run_combo(
                "B-001", [item], [0], "cloud_vision", route, None, [], b"")
        self.assertEqual(result["filled_indexes"], [])
        self.assertEqual(result["pending_marks"], 1)
        self.assertEqual(save_back.call_args.args[1]["stem"], item["question"]["stem"])
        self.assertIn("超时", route["failures"][0]["reason"])

    async def test_pp_m_seat_ready_runs_real_dispatch_and_replaces(self) -> None:
        item = _item(pending=True)
        entry = {"id": "formula_pp_m", "name": "PP-FormulaNet·M", "state": "ready",
                 "enabled": True, "plan_recognize": ["formula_pp_m"]}
        span = {"bbox": [10, 10, 40, 20], "text": "x+1=2", "latex": "",
                "origin": "textlayer"}
        recognize = mock.Mock(return_value={"ok": True, "latex": "x^3",
                                            "detail": "PP-FormulaNet·M 公式已转写"})
        with mock.patch.object(registry, "entry_state", return_value=entry), \
                mock.patch.object(formula.recognize_shared, "item_image_bytes",
                                  return_value=_png()), \
                mock.patch.object(formula, "discover_spans", return_value=[span]), \
                mock.patch.object(formula.formula_pp_m, "recognize", recognize), \
                mock.patch.object(formula.recognize_shared, "save_back",
                                  return_value=True) as save_back:
            route: dict = {}
            result = await formula.run_combo(
                "B-001", [item], [0], "formula_pp_m", route, None, [], b"")
        self.assertTrue(result["seat_ready"])
        self.assertEqual(result["filled_indexes"], [0])
        self.assertEqual(result["pending_marks"], 0)
        recognize.assert_called_once()
        document = save_back.call_args.args[1]
        self.assertEqual(document["stem"], "已知 $x^3$，求值。")
        self.assertFalse(document["extensions"][formula.EDITOR_NS].get("formula_pending"))
        self.assertNotIn("failures", route)

    async def test_pp_m_seat_uninstalled_marks_pending_with_install_guide(self) -> None:
        item = _item()
        entry = {"id": "formula_pp_m", "name": "PP-FormulaNet·M", "state": "degraded",
                 "enabled": True,
                 "detail": "权重未安装（约 596MB，国内镜像），点【安装】一键下。"}
        span = {"bbox": [10, 10, 40, 20], "text": "x+1=2", "latex": "",
                "origin": "textlayer"}
        with mock.patch.object(registry, "entry_state", return_value=entry), \
                mock.patch.object(formula.recognize_shared, "item_image_bytes",
                                  return_value=_png()), \
                mock.patch.object(formula, "discover_spans", return_value=[span]), \
                mock.patch.object(formula.recognize_shared, "save_back",
                                  return_value=True) as save_back:
            route: dict = {}
            result = await formula.run_combo(
                "B-001", [item], [0], "formula_pp_m", route, None, [], b"")
        self.assertFalse(result["seat_ready"])
        self.assertIn("权重未安装", result["seat_reason"])
        self.assertEqual(result["pending_marks"], 1)
        self.assertEqual(save_back.call_args.args[1]["stem"], item["question"]["stem"],
                         "正文保留文字直取，不整题降级")
        self.assertIn("权重未安装", route["failures"][0]["reason"])


if __name__ == "__main__":
    unittest.main()