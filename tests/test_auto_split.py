# -*- coding: utf-8 -*-
"""自动分流（T6 §1）：按卷类型分流，不挨个试；默认座未就绪显性失败绝不偷换。

覆盖：卷型旗标（triage text_layer）决定分支／prefs 改座真生效（真实
catalog＋model_prefs 落盘）／默认座缺失/未就绪/已停用都显性引导／
文字卷兜底＝坏题∪无坐标并集走整题座／具体档不受分流影响选谁只走谁。
外部引擎全 mock，绝不触真服务。
运行：``.venv/Scripts/python.exe -m unittest tests.test_auto_split``
"""

from __future__ import annotations

import unittest
from unittest import mock

from app.core.ingest import model_prefs, registry
from app.core.ingest.recognize import router as recognize_router
from tests.catalog_fixture import EDITOR, CatalogIsolated

READY = {"ok": True, "base_url": "http://127.0.0.1:43210", "token": "tok",
         "detail": "本地 MinerU 服务已就绪"}
SEATS = {"auto_image_seat": "mineru_local", "auto_text_formula_seat": "formula_pp_m"}


def _items(count: int = 3) -> list[dict]:
    return [{"id": "p_test%02d" % index, "page_no": 1,
             "question": {"type": "solution", "stem": "求 $x+1=2$ 的解。",
                          "source": {"question_no": str(index + 1)},
                          "images": [{"id": "img%d" % index, "role": "stem",
                                      "uri": "/static/pending/p_test%02d.png" % index}]},
             "assets": [{"name": "p_test%02d.png" % index}]}
            for index in range(count)]


def _report(bad: list[int], total: int = 3) -> dict:
    return {"total": total, "bad": len(bad),
            "rate": len(bad) / total if total else 0.0, "bad_indexes": bad}


def _seat_entry(state: str = "ready", enabled: bool = True) -> dict:
    return {"id": "mineru_local", "name": "MinerU·本地", "state": state,
            "enabled": enabled, "detail": "" if state == "ready" else "未安装"}


class SplitDecisionTest(unittest.IsolatedAsyncioTestCase):
    async def test_text_layer_flag_decides_the_branch(self) -> None:
        combo = mock.AsyncMock(return_value={
            "ok": True, "attempted": 3, "filled": 3, "filled_indexes": [0, 1, 2],
            "no_coord_indexes": [], "pending_marks": 0, "seat_ready": True,
            "seat_reason": "", "detail": ""})
        local = mock.AsyncMock(return_value={
            "ok": True, "attempted": 3, "filled": 3,
            "filled_indexes": [0, 1, 2], "detail": ""})
        with mock.patch.object(registry, "auto_seats", return_value=dict(SEATS)), \
                mock.patch.object(registry, "entry_state",
                                  return_value=_seat_entry()), \
                mock.patch.object(recognize_router.recognize_formula, "batch_context",
                                  return_value=([], b"")), \
                mock.patch.object(recognize_router.recognize_formula, "run_combo", combo), \
                mock.patch.object(recognize_router.mineru_service, "ensure_ready",
                                  return_value=READY), \
                mock.patch.object(recognize_router.recognize_mineru_local, "run", local):
            text_route = await recognize_router.fill_batch(
                "B-001", _items(), "auto", _report([]), {"text_layer": True})
            self.assertEqual(text_route["mode"], "auto_combo")
            combo.assert_awaited_once()
            local.assert_not_awaited()
            image_route = await recognize_router.fill_batch(
                "B-001", _items(), "auto", _report([]), {})
        self.assertEqual(image_route["mode"], "mineru_local")
        self.assertIn("纯图卷", image_route["note"])
        local.assert_awaited_once()

    async def test_missing_default_seat_is_explicit_failure(self) -> None:
        empty = {"auto_image_seat": "", "auto_text_formula_seat": ""}
        ai = mock.AsyncMock()
        with mock.patch.object(registry, "auto_seats", return_value=empty), \
                mock.patch.object(recognize_router.recognize_ai, "run", ai):
            route = await recognize_router.fill_batch(
                "B-001", _items(), "auto", _report([]), {})
        self.assertIn("缺失", route["note"])
        self.assertIn("模型配置", route["note"])
        self.assertEqual(route["failures"][0]["step"], "识别·自动分流")
        ai.assert_not_called()

    async def test_unready_default_seat_never_swaps_engine(self) -> None:
        ai = mock.AsyncMock()
        mineru = mock.AsyncMock()
        with mock.patch.object(registry, "auto_seats", return_value=dict(SEATS)), \
                mock.patch.object(registry, "entry_state",
                                  return_value=_seat_entry("degraded")), \
                mock.patch.object(recognize_router.recognize_ai, "run", ai), \
                mock.patch.object(recognize_router.recognize_mineru, "run", mineru):
            route = await recognize_router.fill_batch(
                "B-001", _items(), "auto", _report([]), {})
        self.assertIn("未就绪", route["note"])
        self.assertIn("不偷换", route["note"])
        ai.assert_not_called()
        mineru.assert_not_called()

    async def test_disabled_default_seat_is_explicit_too(self) -> None:
        local = mock.AsyncMock()
        with mock.patch.object(registry, "auto_seats", return_value=dict(SEATS)), \
                mock.patch.object(registry, "entry_state",
                                  return_value=_seat_entry("ready", enabled=False)), \
                mock.patch.object(recognize_router.mineru_service, "ensure_ready",
                                  return_value=READY), \
                mock.patch.object(recognize_router.recognize_mineru_local, "run", local):
            route = await recognize_router.fill_batch(
                "B-001", _items(), "auto", _report([]), {})
        self.assertIn("不偷换", route["note"])
        local.assert_not_called()

    async def test_fallback_is_union_of_bad_and_no_coord(self) -> None:
        combo = mock.AsyncMock(return_value={
            "ok": False, "attempted": 1, "filled": 0, "filled_indexes": [],
            "no_coord_indexes": [1], "pending_marks": 1, "seat_ready": False,
            "seat_reason": "公式座未就绪", "detail": ""})
        local = mock.AsyncMock(return_value={
            "ok": True, "attempted": 2, "filled": 2,
            "filled_indexes": [1, 2], "detail": ""})
        with mock.patch.object(registry, "auto_seats", return_value=dict(SEATS)), \
                mock.patch.object(registry, "entry_state",
                                  return_value=_seat_entry()), \
                mock.patch.object(recognize_router.recognize_formula, "batch_context",
                                  return_value=([], b"")), \
                mock.patch.object(recognize_router.recognize_formula, "run_combo", combo), \
                mock.patch.object(recognize_router.mineru_service, "ensure_ready",
                                  return_value=READY), \
                mock.patch.object(recognize_router.recognize_mineru_local, "run", local):
            route = await recognize_router.fill_batch(
                "B-001", _items(), "auto", _report([2]), {"text_layer": True})
        self.assertEqual(route["mode"], "auto_combo")
        self.assertEqual(local.await_args.args[2], [1, 2],
                         "兜底＝坏题∪无坐标并集，按序不重复")
        self.assertIn("2 道无公式坐标或坏题", route["note"])
        self.assertIn("整题兜底", route["note"])
        self.assertIn("待核", route["note"])

    async def test_concrete_engine_ignores_the_split(self) -> None:
        ai = mock.AsyncMock(return_value={
            "ok": True, "attempted": 3, "filled": 3,
            "filled_indexes": [0, 1, 2], "detail": ""})
        with mock.patch.object(recognize_router.recognize_ai, "run", ai), \
                mock.patch.object(recognize_router.recognize_formula, "batch_context") as context:
            route = await recognize_router.fill_batch(
                "B-001", _items(), "cloud_vision", _report([]), {"text_layer": True})
        self.assertEqual(route["mode"], "cloud_vision")
        ai.assert_awaited_once()
        context.assert_not_called()


class PrefsOverrideTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    """真实 catalog＋prefs 落盘：改座真生效，未就绪照念不偷换。"""

    def setUp(self) -> None:
        super().setUp()
        # 体检与硬件全 mock：本测只钉 prefs→目录→分流的接线，不触真引擎。
        missing = {"ok": False, "state": "missing", "version": "", "message": "未安装"}
        for patcher in (
            mock.patch.object(registry.hardware, "probe",
                              return_value={"vram_gb": 16.0, "vram_label": "16G",
                                            "detail": ""}),
            mock.patch.object(registry.mineru_setup, "status",
                              return_value={"state": "idle"}),
            mock.patch.object(registry.mineru_setup, "health",
                              return_value=dict(missing)),
            mock.patch.object(registry.vlm_setup, "status",
                              return_value={"state": "idle"}),
            mock.patch.object(registry.vlm_setup, "health",
                              return_value=dict(missing)),
            mock.patch.object(registry.vlm_setup, "weights_ready",
                              return_value=False),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _ids(self) -> list[str]:
        return [str(item["id"]) for item in registry.catalog()]

    async def test_catalog_defaults_then_prefs_override_image_seat(self) -> None:
        self.assertEqual(registry.auto_seats(), SEATS)
        model_prefs.save({"auto_image_seat": "cloud_vision"}, self._ids(), EDITOR)
        self.assertEqual(registry.auto_seats()["auto_image_seat"], "cloud_vision")
        ai = mock.AsyncMock()
        with mock.patch.object(recognize_router.recognize_ai, "run", ai):
            route = await recognize_router.fill_batch(
                "B-001", _items(), "auto", _report([]), {})
        # 本机没有云账号：cloud_vision 三态未就绪 → 显性失败，绝不偷换回 MinerU。
        self.assertEqual(route["auto_image_seat"], "cloud_vision")
        self.assertIn("未就绪", route["note"])
        self.assertIn("不偷换", route["note"])
        ai.assert_not_called()

    async def test_prefs_override_formula_seat_reaches_combo(self) -> None:
        model_prefs.save({"auto_text_formula_seat": "cloud_vision"},
                         self._ids(), EDITOR)
        combo = mock.AsyncMock(return_value={
            "ok": True, "attempted": 0, "filled": 0, "filled_indexes": [],
            "no_coord_indexes": [], "pending_marks": 0, "seat_ready": False,
            "seat_reason": "", "detail": ""})
        with mock.patch.object(recognize_router.recognize_formula, "batch_context",
                               return_value=([], b"")), \
                mock.patch.object(recognize_router.recognize_formula, "run_combo", combo):
            await recognize_router.fill_batch(
                "B-001", _items(), "auto", _report([]), {"text_layer": True})
        self.assertEqual(combo.await_args.args[3], "cloud_vision")

    async def test_override_back_to_auto_restores_catalog_default(self) -> None:
        model_prefs.save({"auto_image_seat": "cloud_vision"}, self._ids(), EDITOR)
        model_prefs.save({"auto_image_seat": "auto"}, self._ids(), EDITOR)
        self.assertEqual(registry.auto_seats()["auto_image_seat"], "mineru_local")


if __name__ == "__main__":
    unittest.main()