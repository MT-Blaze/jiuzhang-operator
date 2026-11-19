"""识别调度矩阵（T6 拍板）：自动＝按卷类型分流，具体档只走选中通道。

自动不再走瀑布：纯图卷→默认整题座直转；文字卷→组合路（详见 tests.test_auto_split）。
具体档队列与旧通道名兼容全由插件 catalog 数据声明（配置归插件卡）：
夹具见 tests/catalog_fixture.py；目录缺失时具体档一律归自动。

运行：``.venv/Scripts/python.exe -m unittest tests.test_recognize_router``
"""

from __future__ import annotations

import shutil
import unittest
from unittest import mock

from app.core.ai.platform import center as ai_center
from app.core.ingest.recognize import router as recognize_router
from tests.catalog_fixture import CatalogIsolated

ITEMS = [{"id": "p%d" % index, "page_no": 1,
          "question": {"stem": "题干", "images": [
              {"uri": "/static/pending/p%d.png" % index}]}}
         for index in range(3)]


def report(rate: float = 0.0, bad: list[int] | None = None) -> dict:
    return {"total": len(ITEMS), "bad": len(bad or []), "rate": rate,
            "bad_indexes": list(bad or [])}


def binding() -> ai_center.TaskBinding:
    return ai_center.TaskBinding(task="text", account_id="acc_0000000001", name="MinerU",
                                 base_url="https://mineru.test", api_key="fixture",
                                 model="mineru")


class RecognizePlanTest(CatalogIsolated):
    def test_matrix(self) -> None:
        self.assertEqual(recognize_router.plan("auto"), ())
        self.assertEqual(recognize_router.plan("cloud_vision"), ("ai",))
        self.assertEqual(recognize_router.plan("mineru"), ("mineru",))

    def test_legacy_channels_stay_compatible(self) -> None:
        self.assertEqual(recognize_router.normalize_engine("local_ai"), "auto")
        self.assertEqual(recognize_router.normalize_engine("full_ocr"), "cloud_vision")
        self.assertEqual(recognize_router.plan("full_ocr"), ("ai",))
        self.assertEqual(recognize_router.from_legacy_channel("minerU"), "mineru")

    def test_unknown_engine_falls_back_to_auto(self) -> None:
        self.assertEqual(recognize_router.normalize_engine("乱填"), "auto")


class RecognizeFillTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    async def _run(self, engine: str, policy: dict,
                   ai_result: dict | None = None,
                   mineru_result: dict | None = None,
                   mineru_binding=True,
                   ai_error: Exception | None = None,
                   on_progress=None) -> dict:
        route: dict = {}
        ai_mock = mock.AsyncMock(return_value=ai_result or {
            "ok": True, "attempted": 1, "filled": 1,
            "filled_indexes": list(policy["bad_indexes"]), "detail": "",
        })
        if ai_error is not None:
            ai_mock.side_effect = ai_error
        mineru_mock = mock.AsyncMock(return_value=mineru_result or {
            "ok": True, "attempted": len(policy["bad_indexes"]),
            "filled": len(policy["bad_indexes"]),
            "filled_indexes": list(policy["bad_indexes"]), "detail": "",
        })
        with mock.patch.object(recognize_router.recognize_local, "probe",
                               return_value={"ok": not policy["bad_indexes"],
                                             "bad_indexes": policy["bad_indexes"]}), \
                mock.patch.object(recognize_router.recognize_ai, "run", ai_mock), \
                mock.patch.object(recognize_router.recognize_mineru, "run", mineru_mock), \
                mock.patch.object(recognize_router.ai_center, "find_mineru",
                                  return_value=binding() if mineru_binding else None):
            result = await recognize_router.fill_batch(
                "B-001", ITEMS, engine, report(policy["rate"], policy["bad_indexes"]),
                route, on_progress)
        return {"route": result, "ai": ai_mock, "mineru": mineru_mock}

    async def test_auto_image_routes_to_default_seat(self) -> None:
        from app.core.ingest import registry
        route: dict = {}
        ready = {"ok": True, "base_url": "http://127.0.0.1:43210", "token": "tok",
                 "detail": "本地 MinerU 服务已就绪"}
        local_mock = mock.AsyncMock(return_value={
            "ok": True, "attempted": 3, "filled": 3,
            "filled_indexes": [0, 1, 2], "detail": ""})
        with mock.patch.object(registry, "auto_seats", return_value={
                "auto_image_seat": "mineru_local", "auto_text_formula_seat": "formula_pp_m"}), \
                mock.patch.object(registry, "entry_state", return_value={
                    "id": "mineru_local", "name": "MinerU·本地",
                    "state": "ready", "enabled": True}), \
                mock.patch.object(recognize_router.mineru_service, "ensure_ready",
                                  return_value=ready), \
                mock.patch.object(recognize_router.recognize_mineru_local, "run", local_mock):
            result = await recognize_router.fill_batch(
                "B-001", ITEMS, "auto", report(0.0, []), route)
        local_mock.assert_awaited_once()
        self.assertEqual(result["mode"], "mineru_local")
        self.assertIn("自动分流（纯图卷）→默认座", result["note"])

    async def test_auto_image_unready_seat_is_explicit_no_swap(self) -> None:
        from app.core.ingest import registry
        route: dict = {}
        ai_mock = mock.AsyncMock()
        mineru_mock = mock.AsyncMock()
        with mock.patch.object(registry, "auto_seats", return_value={
                "auto_image_seat": "mineru_local", "auto_text_formula_seat": ""}), \
                mock.patch.object(registry, "entry_state", return_value={
                    "id": "mineru_local", "name": "MinerU·本地",
                    "state": "degraded", "enabled": True, "detail": "未安装"}), \
                mock.patch.object(recognize_router.recognize_ai, "run", ai_mock), \
                mock.patch.object(recognize_router.recognize_mineru, "run", mineru_mock):
            result = await recognize_router.fill_batch(
                "B-001", ITEMS, "auto", report(0.0, []), route)
        ai_mock.assert_not_called()
        mineru_mock.assert_not_called()
        self.assertIn("未就绪", result["note"])
        self.assertIn("不偷换", result["note"])
        steps = [entry["step"] for entry in result.get("failures") or []]
        self.assertIn("识别·自动分流", steps)
        self.assertTrue(result["done"])

    async def test_auto_text_layer_delegates_to_combo(self) -> None:
        from app.core.ingest import registry
        route: dict = {"text_layer": True}
        combo_mock = mock.AsyncMock(return_value={
            "ok": True, "attempted": 3, "filled": 3, "filled_indexes": [0, 1, 2],
            "no_coord_indexes": [], "pending_marks": 0, "seat_ready": True,
            "seat_reason": "", "detail": ""})
        with mock.patch.object(registry, "auto_seats", return_value={
                "auto_image_seat": "mineru_local", "auto_text_formula_seat": "formula_pp_m"}), \
                mock.patch.object(recognize_router.recognize_local, "probe",
                                  return_value={"ok": True, "bad_indexes": []}), \
                mock.patch.object(recognize_router.recognize_formula, "batch_context",
                                  return_value=([], None)), \
                mock.patch.object(recognize_router.recognize_formula, "run_combo", combo_mock):
            result = await recognize_router.fill_batch(
                "B-001", ITEMS, "auto", report(0.0, []), route)
        combo_mock.assert_awaited_once()
        self.assertEqual(result["mode"], "auto_combo")
        self.assertIn("组合路", result["note"])

    async def test_cloud_vision_sends_whole_batch_even_if_clean(self) -> None:
        outcome = await self._run(
            "full_ocr", {"rate": 0.0, "bad_indexes": []},
            ai_result={"ok": True, "attempted": 3, "filled": 3,
                       "filled_indexes": [0, 1, 2], "detail": ""})
        outcome["ai"].assert_awaited_once()
        self.assertEqual(outcome["ai"].call_args.args[2], "all")
        outcome["mineru"].assert_not_called()
        self.assertEqual(outcome["route"]["mode"], "cloud_vision")
        self.assertIn("3/3", outcome["route"]["note"])

    async def test_cloud_failure_does_not_switch_to_mineru(self) -> None:
        outcome = await self._run(
            "cloud_vision", {"rate": 0.0, "bad_indexes": []},
            ai_result={"ok": False, "attempted": 3, "filled": 0,
                       "filled_indexes": [], "detail": "视觉模型超时"})
        outcome["mineru"].assert_not_called()
        route = outcome["route"]
        self.assertIn("不降级", route["note"])
        steps = [entry["step"] for entry in route.get("failures") or []]
        self.assertIn("识别·云端视觉", steps)
        self.assertTrue(route["failures"][0]["retryable"])

    async def test_mineru_engine_skips_ai(self) -> None:
        outcome = await self._run(
            "mineru", {"rate": 0.0, "bad_indexes": []},
            mineru_result={"ok": True, "attempted": 3, "filled": 3,
                           "filled_indexes": [0, 1, 2], "detail": ""})
        outcome["ai"].assert_not_called()
        outcome["mineru"].assert_awaited_once()
        self.assertEqual(outcome["route"]["mode"], "mineru")
        self.assertIn("3/3", outcome["route"]["note"])

    async def test_mineru_without_account_is_reported(self) -> None:
        outcome = await self._run("mineru", {"rate": 0.0, "bad_indexes": []},
                                  mineru_binding=False)
        outcome["mineru"].assert_not_called()
        outcome["ai"].assert_not_called()
        self.assertIn("MinerU 没有可用的账号", outcome["route"]["note"])
        steps = [entry["step"] for entry in outcome["route"].get("failures") or []]
        self.assertIn("识别·MinerU", steps)

    async def test_mineru_failure_surfaces_without_fallback(self) -> None:
        outcome = await self._run(
            "mineru", {"rate": 0.0, "bad_indexes": []},
            mineru_result={"ok": False, "attempted": 3, "filled": 1,
                           "filled_indexes": [0], "detail": "解析服务限流"})
        outcome["ai"].assert_not_called()
        route = outcome["route"]
        self.assertIn("不降级", route["note"])
        self.assertIn("2 道保持本地切图", route["note"])
        steps = [entry["step"] for entry in route.get("failures") or []]
        self.assertIn("识别·MinerU", steps)

    async def test_progress_callback_reaches_mineru(self) -> None:
        sentinel = lambda snapshot: None  # noqa: E731
        outcome = await self._run(
            "mineru", {"rate": 0.0, "bad_indexes": []},
            mineru_result={"ok": True, "attempted": 3, "filled": 3,
                           "filled_indexes": [0, 1, 2], "detail": ""},
            on_progress=sentinel)
        self.assertIs(outcome["mineru"].call_args.args[5], sentinel)


class RecognizeComboPickTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    """老师点选组合路（2.20.0 卡§2）：纯图卷显性拒绝，文字卷只走声明的公式座。"""

    COMBO_OK = {"ok": True, "attempted": 3, "filled": 3, "filled_indexes": [0, 1, 2],
                "no_coord_indexes": [], "pending_marks": 0, "seat_ready": True,
                "seat_reason": "", "detail": ""}

    async def _run(self, engine: str, route: dict) -> dict:
        combo_mock = mock.AsyncMock(return_value=dict(self.COMBO_OK))
        ai_mock = mock.AsyncMock()
        mineru_mock = mock.AsyncMock()
        with mock.patch.object(recognize_router.recognize_local, "probe",
                               return_value={"ok": True, "bad_indexes": []}), \
                mock.patch.object(recognize_router.recognize_formula, "batch_context",
                                  return_value=([], None)), \
                mock.patch.object(recognize_router.recognize_formula, "run_combo",
                                  combo_mock), \
                mock.patch.object(recognize_router.recognize_ai, "run", ai_mock), \
                mock.patch.object(recognize_router.recognize_mineru, "run", mineru_mock):
            result = await recognize_router.fill_batch(
                "B-001", ITEMS, engine, report(0.0, []), route)
        return {"route": result, "combo": combo_mock, "ai": ai_mock,
                "mineru": mineru_mock}

    def test_combo_plan_comes_from_catalog(self) -> None:
        for engine in ("combo_cloud", "combo_vlm", "combo_pp_m"):
            with self.subTest(engine=engine):
                self.assertEqual(recognize_router.normalize_engine(engine), engine)
                self.assertEqual(recognize_router.plan(engine), ("combo",))

    async def test_pure_image_pick_is_explicit_no_engine_runs(self) -> None:
        outcome = await self._run("combo_cloud", {"text_layer": False})
        outcome["combo"].assert_not_called()
        outcome["ai"].assert_not_called()
        outcome["mineru"].assert_not_called()
        route = outcome["route"]
        self.assertEqual(route["mode"], "combo_cloud")
        self.assertIn("纯图卷", route["note"])
        self.assertIn("不偷换", route["note"])
        self.assertTrue(route["done"])
        steps = [entry["step"] for entry in route.get("failures") or []]
        self.assertIn("识别·组合路", steps)

    async def test_untriaged_route_also_refuses_combo(self) -> None:
        outcome = await self._run("combo_vlm", {})
        outcome["combo"].assert_not_called()
        self.assertIn("纯图卷", outcome["route"]["note"])

    async def test_text_layer_pick_runs_declared_seat_only(self) -> None:
        for engine, seat in (("combo_cloud", "cloud_vision"),
                             ("combo_vlm", "vlm_qwen"),
                             ("combo_pp_m", "formula_pp_m")):
            with self.subTest(engine=engine):
                outcome = await self._run(engine, {"text_layer": True})
                outcome["combo"].assert_awaited_once()
                self.assertEqual(outcome["combo"].call_args.args[3], seat)
                outcome["ai"].assert_not_called()
                outcome["mineru"].assert_not_called()
                route = outcome["route"]
                self.assertEqual(route["mode"], engine)
                self.assertIn("组合路", route["note"])
                self.assertIn(seat, route["note"])
                self.assertTrue(route["done"])


class RecognizeNoCatalogTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    """目录缺失/未接线通道：归自动或诚实失败，底座不猜模型。"""

    def test_missing_catalog_normalizes_specific_pick_to_auto(self) -> None:
        shutil.rmtree(self.plugin)
        self.assertEqual(recognize_router.normalize_engine("mineru"), "auto")
        self.assertEqual(recognize_router.from_legacy_channel("full_ocr"), "auto")
        self.assertEqual(recognize_router.plan("auto"), ())

    async def test_unwired_plan_surfaces_failure_without_fallback(self) -> None:
        (self.plugin / "catalog.toml").write_text(
            '[[entry]]\nid = "unwired"\nname = "未接线"\n'
            'capability = "recognize"\nrule = "blocked"\nplan_recognize = ["local"]\n',
            encoding="utf-8")
        route: dict = {}
        result = await recognize_router.fill_batch(
            "B-001", ITEMS, "unwired", report(0.0, []), route)
        self.assertTrue(result["done"])
        self.assertEqual(result["mode"], "unwired")
        self.assertIn("尚未接线", result["note"])
        steps = [entry["step"] for entry in result.get("failures") or []]
        self.assertIn("识别·选中引擎", steps)


class RecognizeMineruLocalTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    """MinerU·本地具体档：只走本地服务，失败显性不降级（任务卡 §4）。"""

    READY = {"ok": True, "base_url": "http://127.0.0.1:43210", "token": "tok",
             "detail": "本地 MinerU 服务已就绪"}

    async def _run(self, ready: dict, local_result: dict | None = None,
                   on_progress=None) -> dict:
        route: dict = {}
        local_mock = mock.AsyncMock(return_value=local_result or {
            "ok": True, "attempted": 3, "filled": 3,
            "filled_indexes": [0, 1, 2], "detail": "",
        })
        ai_mock = mock.AsyncMock()
        mineru_mock = mock.AsyncMock()
        with mock.patch.object(recognize_router.mineru_service, "ensure_ready",
                               return_value=ready), \
                mock.patch.object(recognize_router.recognize_mineru_local, "run",
                                  local_mock), \
                mock.patch.object(recognize_router.recognize_ai, "run", ai_mock), \
                mock.patch.object(recognize_router.recognize_mineru, "run", mineru_mock):
            result = await recognize_router.fill_batch(
                "B-001", ITEMS, "mineru_local", report(0.0, []), route, on_progress)
        return {"route": result, "local": local_mock, "ai": ai_mock,
                "mineru": mineru_mock}

    def test_plan_comes_from_catalog(self) -> None:
        self.assertEqual(recognize_router.normalize_engine("mineru_local"),
                         "mineru_local")
        self.assertEqual(recognize_router.plan("mineru_local"), ("mineru_local",))
        self.assertEqual(recognize_router.plan("auto"), ())

    async def test_local_engine_skips_cloud_channels(self) -> None:
        outcome = await self._run(self.READY)
        outcome["ai"].assert_not_called()
        outcome["mineru"].assert_not_called()
        outcome["local"].assert_awaited_once()
        self.assertEqual(outcome["route"]["mode"], "mineru_local")
        self.assertIn("3/3", outcome["route"]["note"])
        self.assertIn("本地", outcome["route"]["note"])
        self.assertEqual(outcome["local"].call_args.args[3], self.READY)

    async def test_service_unavailable_surfaces_failure_without_fallback(self) -> None:
        outcome = await self._run({"ok": False, "detail": "本地 MinerU 未就绪（未安装）。"})
        outcome["local"].assert_not_called()
        outcome["ai"].assert_not_called()
        outcome["mineru"].assert_not_called()
        route = outcome["route"]
        self.assertIn("不降级", route["note"])
        self.assertIn("未就绪", route["note"])
        steps = [entry["step"] for entry in route.get("failures") or []]
        self.assertIn("识别·MinerU本地", steps)
        self.assertTrue(route["failures"][0]["retryable"])

    async def test_partial_failure_keeps_local_cuts_without_fallback(self) -> None:
        outcome = await self._run(self.READY, {
            "ok": True, "attempted": 3, "filled": 1,
            "filled_indexes": [0], "detail": "只有 1/3 道回来了"})
        outcome["ai"].assert_not_called()
        outcome["mineru"].assert_not_called()
        route = outcome["route"]
        self.assertIn("不降级", route["note"])
        self.assertIn("2 道保持本地切图", route["note"])
        steps = [entry["step"] for entry in route.get("failures") or []]
        self.assertIn("识别·MinerU本地", steps)

    async def test_all_failure_is_explicit(self) -> None:
        outcome = await self._run(self.READY, {
            "ok": False, "attempted": 3, "filled": 0,
            "filled_indexes": [], "detail": "只有 0/3 道回来了"})
        route = outcome["route"]
        self.assertIn("不降级", route["note"])
        self.assertIn("3 道保持本地切图", route["note"])
        steps = [entry["step"] for entry in route.get("failures") or []]
        self.assertIn("识别·MinerU本地", steps)

    async def test_progress_callback_reaches_local(self) -> None:
        sentinel = lambda snapshot: None  # noqa: E731
        outcome = await self._run(self.READY, on_progress=sentinel)
        self.assertIs(outcome["local"].call_args.args[5], sentinel)


class RecognizeVlmMultiSeatTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    """本地 VLM 三座具体档（安装接线卡座5/6）：按选中座传 seat 起服，失败显性不降级。"""

    async def _run(self, picked: str, ready: dict) -> dict:
        route: dict = {}
        local_mock = mock.AsyncMock(return_value={
            "ok": True, "attempted": 3, "filled": 3,
            "filled_indexes": [0, 1, 2], "detail": ""})
        ready_mock = mock.Mock(return_value=ready)
        with mock.patch.object(recognize_router.vlm_service, "ensure_ready", ready_mock), \
                mock.patch.object(recognize_router.recognize_vlm_local, "run", local_mock):
            result = await recognize_router.fill_batch(
                "B-001", ITEMS, picked, report(0.0, []), route)
        return {"route": result, "local": local_mock, "ready": ready_mock}

    async def test_each_seat_passes_its_key_to_ensure_ready(self) -> None:
        ready = {"ok": True, "base_url": "http://127.0.0.1:43210", "token": "tok",
                 "seat": "intern", "seat_label": "书生 InternVL3-2B", "detail": "就绪"}
        for picked, seat in (("vlm_qwen", "qwen"), ("vlm_intern", "intern"),
                             ("vlm_minicpm", "minicpm")):
            with self.subTest(picked=picked):
                outcome = await self._run(picked, ready)
                outcome["ready"].assert_called_once_with(seat)
                outcome["local"].assert_awaited_once()
                self.assertEqual(outcome["route"]["mode"], picked)

    async def test_seat_unavailable_surfaces_failure_without_fallback(self) -> None:
        outcome = await self._run("vlm_intern", {"ok": False, "detail": "书生权重不在本机。"})
        outcome["local"].assert_not_called()
        route = outcome["route"]
        self.assertIn("不降级", route["note"])
        steps = [entry["step"] for entry in route.get("failures") or []]
        self.assertIn("识别·本地VLM", steps)


if __name__ == "__main__":
    unittest.main()
