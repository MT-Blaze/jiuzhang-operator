"""模型注册表（2026-11-18 拍板）：目录×运行时三态、闸口残留值、只读 API。

运行：``.venv/Scripts/python.exe -m unittest tests.test_models_registry``
"""

from __future__ import annotations

import asyncio
import unittest
from contextlib import contextmanager
from unittest import mock

from app.api import models as models_api
from app.core.ai.platform import center as ai_center
from app.core.ingest import registry


def _vision(configured: bool = True) -> ai_center.TaskBinding:
    return ai_center.TaskBinding(
        task="ocr", account_id="acc_0000000001", name="视觉一号",
        base_url="https://vision.test" if configured else "",
        api_key="fixture" if configured else "",
        model="vision-x" if configured else "")


def _mineru() -> ai_center.TaskBinding:
    return ai_center.TaskBinding(
        task="mineru", account_id="acc_0000000002", name="MinerU 云端",
        base_url="https://mineru.test", api_key="fixture", model="mineru")


@contextmanager
def _runtime(ocr: bool = True, yolo: bool = False,
             vision: ai_center.TaskBinding | None = None,
             mineru: ai_center.TaskBinding | None = None):
    with mock.patch.object(registry, "_rapidocr_installed", return_value=ocr), \
            mock.patch.object(registry.model_store, "present", return_value=yolo), \
            mock.patch.object(registry.ai_center, "resolve_task",
                              return_value=vision if vision is not None else _vision(False)), \
            mock.patch.object(registry.ai_center, "find_mineru", return_value=mineru):
        yield


def _states(entries: list[dict]) -> dict[str, dict]:
    return {entry["id"]: entry for entry in entries}


class RegistryStatusTest(unittest.TestCase):
    def test_all_ready_catalog_has_three_states_and_names(self) -> None:
        with _runtime(yolo=True, vision=_vision(), mineru=_mineru()):
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["rapidocr_fast"]["state"], "ready")
        self.assertEqual(entries["yolo"]["state"], "ready")
        self.assertEqual(entries["cloud_vision"]["state"], "ready")
        self.assertEqual(entries["cloud_vision"]["assigned"], "视觉一号")
        self.assertEqual(entries["mineru"]["state"], "ready")
        self.assertEqual(entries["rapidocr_accurate"]["state"], "blocked")
        self.assertIn("模型未核实、暂不开下载", entries["rapidocr_accurate"]["detail"])

    def test_unconfigured_entries_are_degraded_with_real_actions(self) -> None:
        with _runtime():
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["rapidocr_fast"]["state"], "ready")
        self.assertEqual(entries["yolo"]["state"], "degraded")
        self.assertEqual(entries["yolo"]["action"], "download")
        self.assertEqual(entries["cloud_vision"]["state"], "degraded")
        self.assertEqual(entries["cloud_vision"]["action"], "assign")
        self.assertEqual(entries["mineru"]["state"], "degraded")
        self.assertEqual(entries["mineru"]["action"], "assign")

    def test_missing_rapidocr_is_degraded(self) -> None:
        with _runtime(ocr=False):
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["rapidocr_fast"]["state"], "degraded")

    def test_accurate_never_offers_a_fake_download(self) -> None:
        with _runtime(yolo=True, vision=_vision(), mineru=_mineru()):
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["rapidocr_accurate"]["action"], "")

    def test_status_is_recomputed_every_call(self) -> None:
        with mock.patch.object(registry, "_rapidocr_installed", return_value=True), \
                mock.patch.object(registry.model_store, "present",
                                  side_effect=[False, True]), \
                mock.patch.object(registry.ai_center, "resolve_task",
                                  return_value=_vision(False)), \
                mock.patch.object(registry.ai_center, "find_mineru", return_value=None):
            first = _states(registry.status()["entries"])["yolo"]["state"]
            second = _states(registry.status()["entries"])["yolo"]["state"]
        self.assertEqual((first, second), ("degraded", "ready"))


class RegistryGateTest(unittest.TestCase):
    def test_ready_pick_passes_without_note(self) -> None:
        with _runtime(yolo=True):
            self.assertEqual(registry.gate_layout("yolo"), ("yolo", ""))

    def test_degraded_pick_returns_auto_with_reason(self) -> None:
        with _runtime():
            picked, note = registry.gate_layout("yolo")
        self.assertEqual(picked, "auto")
        self.assertIn("YOLO·版面", note)
        self.assertIn("未就绪", note)
        self.assertIn("权重未下载", note)

    def test_auto_and_junk_values_carry_no_note(self) -> None:
        with _runtime():
            self.assertEqual(registry.gate_layout("auto"), ("auto", ""))
            self.assertEqual(registry.gate_layout("乱填"), ("auto", ""))

    def test_legacy_alias_gates_by_new_entry(self) -> None:
        with _runtime(vision=_vision()):
            self.assertEqual(registry.gate_layout("cloud"), ("cloud_vision", ""))
        with _runtime():
            picked, note = registry.gate_layout("cloud")
        self.assertEqual(picked, "auto")
        self.assertIn("云端视觉", note)

    def test_recognize_mineru_unassigned_returns_auto_with_reason(self) -> None:
        with _runtime():
            picked, note = registry.gate_recognize("mineru")
        self.assertEqual(picked, "auto")
        self.assertIn("MinerU", note)
        with _runtime(mineru=_mineru()):
            self.assertEqual(registry.gate_recognize("mineru"), ("mineru", ""))

    def test_gate_note_survives_recognize_summary_overwrite(self) -> None:
        """成功路识别汇总会盖掉 note（既有行为）：闸口归一原因必须补回末尾。"""
        from app.core.ingest import route as ingest_route

        async def fake_fill(batch_id, items, engine, report, route, progress):
            route["note"] = "本地提取 1 题未发现坏题，无需调用 AI。"
            return route

        batch = {"items": [{"question": {"stem": "计算 1+1", "type": "解答题"}}]}
        with mock.patch("app.core.pending.service.list_batch_questions", return_value=batch), \
                mock.patch.object(ingest_route.recognize_router, "fill_batch",
                                  side_effect=fake_fill):
            route = asyncio.run(ingest_route.fill_scan_batch(
                "B-TEST", "auto", None, "auto", None,
                "版面：YOLO·版面未就绪，已归一回自动。"))
        self.assertIn("本地提取 1 题", route["note"])
        self.assertIn("YOLO·版面未就绪", route["note"])


class RegistryApiTest(unittest.TestCase):
    def test_endpoint_returns_registry_payload(self) -> None:
        payload = {"ok": True, "entries": [{"id": "yolo", "state": "ready"}]}
        with mock.patch.object(registry, "status", return_value=payload):
            self.assertEqual(models_api.models_registry(), payload)

    def test_main_app_mounts_the_route(self) -> None:
        from app.main import create_app
        # FastAPI 0.141 把 include_router 包成 _IncludedRouter，以 OpenAPI paths 为准。
        paths = create_app().openapi().get("paths", {})
        self.assertIn("/api/models/registry", paths)


if __name__ == "__main__":
    unittest.main()