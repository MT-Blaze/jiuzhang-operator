"""识别调度矩阵（2026-11-18 拍板）：自动走瀑布，具体档只走选中通道。

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
        self.assertEqual(recognize_router.plan("auto"), ("local", "ai", "mineru"))
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

    async def test_clean_auto_stops_at_local(self) -> None:
        outcome = await self._run("auto", {"rate": 0.0, "bad_indexes": []})
        outcome["ai"].assert_not_called()
        outcome["mineru"].assert_not_called()
        self.assertEqual(outcome["route"]["mode"], "local")
        self.assertTrue(outcome["route"]["done"])
        self.assertIn("未发现坏题", outcome["route"]["note"])

    async def test_below_threshold_patches_only_bad(self) -> None:
        outcome = await self._run("auto", {"rate": 0.2, "bad_indexes": [1]})
        outcome["ai"].assert_awaited_once()
        self.assertEqual(outcome["ai"].call_args.args[2], "bad")
        outcome["mineru"].assert_not_called()
        self.assertEqual(outcome["route"]["mode"], "partial_ai")
        self.assertIn("局部修补", outcome["route"]["note"])

    async def test_threshold_switches_to_full_ocr(self) -> None:
        outcome = await self._run(
            "auto", {"rate": 0.3, "bad_indexes": [0, 1, 2]},
            ai_result={"ok": True, "attempted": 3, "filled": 3,
                       "filled_indexes": [0, 1, 2], "detail": ""})
        self.assertEqual(outcome["ai"].call_args.args[2], "all")
        self.assertEqual(outcome["route"]["mode"], "full_ocr")
        self.assertIn("并发全量 OCR", outcome["route"]["note"])

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

    async def test_ai_failure_falls_back_to_mineru(self) -> None:
        outcome = await self._run(
            "auto", {"rate": 0.2, "bad_indexes": [0]},
            ai_result={"ok": False, "attempted": 1, "filled": 0,
                       "filled_indexes": [], "detail": "模型超时"},
            mineru_result={"ok": True, "attempted": 1, "filled": 1,
                           "filled_indexes": [0], "detail": ""})
        outcome["mineru"].assert_awaited_once()
        self.assertIn("已改用 MinerU", outcome["route"]["note"])

    async def test_ai_exception_degrades_without_crash(self) -> None:
        outcome = await self._run(
            "auto", {"rate": 0.2, "bad_indexes": [0]},
            ai_error=RuntimeError("网络断了"), mineru_binding=False)
        self.assertTrue(outcome["route"]["done"])
        self.assertIn("AI 未成功", outcome["route"]["note"])
        self.assertIn("识别引擎异常", outcome["route"]["note"])

    async def test_progress_callback_reaches_mineru(self) -> None:
        sentinel = lambda snapshot: None  # noqa: E731
        outcome = await self._run(
            "mineru", {"rate": 0.0, "bad_indexes": []},
            mineru_result={"ok": True, "attempted": 3, "filled": 3,
                           "filled_indexes": [0, 1, 2], "detail": ""},
            on_progress=sentinel)
        self.assertIs(outcome["mineru"].call_args.args[5], sentinel)

    async def test_ai_filling_all_bad_skips_mineru(self) -> None:
        outcome = await self._run(
            "auto", {"rate": 0.2, "bad_indexes": [0]},
            ai_result={"ok": True, "attempted": 1, "filled": 1,
                       "filled_indexes": [0], "detail": ""})
        outcome["mineru"].assert_not_called()


class RecognizeNoCatalogTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    """目录缺失/未接线通道：归自动或诚实失败，底座不猜模型。"""

    def test_missing_catalog_normalizes_specific_pick_to_auto(self) -> None:
        shutil.rmtree(self.plugin)
        self.assertEqual(recognize_router.normalize_engine("mineru"), "auto")
        self.assertEqual(recognize_router.from_legacy_channel("full_ocr"), "auto")
        self.assertEqual(recognize_router.plan("auto"), ("local", "ai", "mineru"))

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


if __name__ == "__main__":
    unittest.main()
