"""模型注册表（配置归插件卡）：插件目录×通用规则解释器×运行时三态、闸口、只读 API。

目录是插件财产：夹具造一个声明 models.catalog 的最小 headless 插件，
catalog.toml 从插件源码仓原样拷来（tests/catalog_fixture.py）。底座只认
六个规则名，不认任何模型 id；未知规则＝blocked＋提示更新底座，绝不静默。

运行：``.venv/Scripts/python.exe -m unittest tests.test_models_registry``
"""

from __future__ import annotations

import asyncio
import shutil
import unittest
from contextlib import contextmanager
from unittest import mock

from app.api import models as models_api
from app.core.ai.platform import center as ai_center
from app.core.ingest import registry
from tests.catalog_fixture import CATALOG_CAPABILITY, EDITOR, CatalogIsolated

_HW_16G = {"vram_gb": 16.0, "vram_label": "16.0G", "gpu_name": "测试卡",
           "vram_source": "nvidia-smi", "detail": ""}
_HW_LOW = {"vram_gb": 4.0, "vram_label": "4.0G", "gpu_name": "",
           "vram_source": "wmi", "detail": ""}
_HEALTH_MISSING = {"ok": False, "state": "missing", "version": "",
                   "message": "本地 MinerU 未安装。"}
_PREFS_EMPTY = {"disabled": [], "default_layout": "auto", "default_recognize": "auto"}


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
             mineru: ai_center.TaskBinding | None = None,
             hw: dict | None = None,
             health: dict | None = None,
             install: dict | None = None,
             prefs: dict | None = None):
    with mock.patch.object(registry, "_import_ok", return_value=ocr), \
            mock.patch.object(registry.model_store, "present", return_value=yolo), \
            mock.patch.object(registry.ai_center, "resolve_task",
                              return_value=vision if vision is not None else _vision(False)), \
            mock.patch.object(registry.ai_center, "find_mineru", return_value=mineru), \
            mock.patch.object(registry.hardware, "probe",
                              return_value=hw if hw is not None else _HW_16G), \
            mock.patch.object(registry.mineru_setup, "health",
                              return_value=health if health is not None else _HEALTH_MISSING), \
            mock.patch.object(registry.mineru_setup, "status",
                              return_value=install if install is not None else {"state": "idle"}), \
            mock.patch.object(registry.model_prefs, "load",
                              return_value=prefs if prefs is not None else dict(_PREFS_EMPTY)):
        yield


def _states(entries: list[dict]) -> dict[str, dict]:
    return {entry["id"]: entry for entry in entries}


class RegistryStatusTest(CatalogIsolated):
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
        with _runtime(yolo=False), \
                mock.patch.object(registry.model_store, "present",
                                  side_effect=[False, True]):
            first = _states(registry.status()["entries"])["yolo"]["state"]
            second = _states(registry.status()["entries"])["yolo"]["state"]
        self.assertEqual((first, second), ("degraded", "ready"))


class RegistryGateTest(CatalogIsolated):
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


class CatalogDataTest(CatalogIsolated):
    """目录数据驱动：toml 单源住插件目录，加条目不改底座代码。"""

    def test_catalog_comes_from_plugin_dir_and_keeps_original_five(self) -> None:
        provider = registry.catalog_provider()
        self.assertIsNotNone(provider)
        self.assertEqual(provider["id"], EDITOR)
        self.assertIn(CATALOG_CAPABILITY, provider["capabilities"])
        self.assertTrue((self.plugin / registry.CATALOG_FILENAME).is_file())
        ids = [item["id"] for item in registry.catalog()]
        for original in ("rapidocr_fast", "rapidocr_accurate", "yolo",
                         "cloud_vision", "mineru"):
            self.assertIn(original, ids)
        self.assertIn("mineru_local", ids)

    def test_every_entry_has_plain_usage(self) -> None:
        for item in registry.catalog():
            self.assertTrue(str(item.get("summary_usage") or "").strip(),
                            "%s 缺大白话使用说明" % item["id"])
            self.assertIn("min_vram", item)
            self.assertIn("can_cpu", item)

    def test_every_entry_declares_a_known_rule(self) -> None:
        for item in registry.catalog():
            self.assertIn(str(item.get("rule")), registry.RULES,
                          "%s 的 rule 不在通用契约里" % item["id"])

    def test_vlm_families_registered_with_six_g_floor(self) -> None:
        vlms = [item for item in registry.catalog() if item.get("family") == "vlm"]
        self.assertEqual(len(vlms), 6)
        for item in vlms:
            self.assertGreaterEqual(int(item["min_vram"]), 6)
            self.assertFalse(item["can_cpu"])

    def test_formula_four_registered(self) -> None:
        formulas = [item["id"] for item in registry.catalog()
                    if item.get("family") == "formula"]
        self.assertEqual(sorted(formulas),
                         ["formula_p2t", "formula_pp_l", "formula_pp_m", "formula_texify"])

    def test_tier_table_starts_at_six_g_no_four_g(self) -> None:
        tiers = registry.vram_tiers()
        self.assertEqual([int(t["min_gb"]) for t in tiers],
                         [6, 8, 10, 16, 20, 32, 48])
        self.assertNotIn(4, [int(t["min_gb"]) for t in tiers])


class GenericRuleTest(CatalogIsolated):
    """解释器只认规则名：未知规则＝blocked＋人话提示更新底座，绝不静默。"""

    def _rewrite_catalog(self, text: str) -> None:
        (self.plugin / registry.CATALOG_FILENAME).write_text(text, encoding="utf-8")

    def test_unknown_rule_is_blocked_with_update_hint(self) -> None:
        self._rewrite_catalog(
            '[[entry]]\nid = "future_model"\nname = "未来模型"\n'
            'capability = "layout"\nrule = "quantum_probe"\n')
        with _runtime():
            entry = _states(registry.status()["entries"])["future_model"]
        self.assertEqual(entry["state"], "blocked")
        self.assertIn("底座不认识这条规则", entry["detail"])
        self.assertIn("quantum_probe", entry["detail"])
        self.assertIn("更新底座", entry["detail"])

    def test_missing_rule_is_blocked_not_silent(self) -> None:
        self._rewrite_catalog(
            '[[entry]]\nid = "ruleless"\nname = "没写规则"\ncapability = "layout"\n')
        with _runtime():
            entry = _states(registry.status()["entries"])["ruleless"]
        self.assertEqual(entry["state"], "blocked")
        self.assertIn("缺 rule 声明", entry["detail"])

    def test_six_rules_are_the_whole_contract(self) -> None:
        self.assertEqual(sorted(registry.RULES),
                         sorted(["import_probe", "weight_present", "task_assign",
                                 "mineru_local", "vram_gate", "blocked"]))


class MissingCatalogTest(CatalogIsolated):
    """无提供者/目录损坏＝空目录：下拉只剩 auto，闸口不静默也不崩。"""

    def test_no_provider_means_empty_catalog_and_auto_defaults(self) -> None:
        shutil.rmtree(self.plugin)
        with _runtime():
            payload = registry.status()
        self.assertEqual(payload["entries"], [])
        self.assertEqual(payload["defaults"],
                         {"layout": "auto", "recognize": "auto"})
        self.assertEqual(registry.catalog(), ())
        self.assertEqual(registry.gate_layout("yolo"), ("auto", ""))

    def test_corrupt_catalog_degrades_to_empty(self) -> None:
        (self.plugin / registry.CATALOG_FILENAME).write_text(
            "这不是 toml = = =", encoding="utf-8")
        with _runtime():
            payload = registry.status()
        self.assertEqual(payload["entries"], [])
        self.assertEqual(registry.gate_recognize("mineru"), ("auto", ""))

    def test_undeclared_plugin_is_not_a_provider(self) -> None:
        from app.core import toml_io
        manifest = self.plugin / "plugin.toml"
        data = toml_io.load(manifest, {})
        data["capabilities"] = ["question.edit"]
        toml_io.write(manifest, data)
        self.assertIsNone(registry.catalog_provider())
        self.assertEqual(registry.catalog(), ())


class HardwareGateTest(CatalogIsolated):
    def test_low_vram_says_unsupported_and_points_to_cloud(self) -> None:
        with _runtime(hw=_HW_LOW):
            entries = _states(registry.status()["entries"])
        entry = entries["vlm_qwen"]
        self.assertEqual(entry["state"], "blocked")
        self.assertIn("电脑硬件不支持", entry["detail"])
        self.assertIn("6G", entry["detail"])
        self.assertEqual(entry["action"], "assign")

    def test_enough_vram_still_blocked_pending_t6_with_tier(self) -> None:
        with _runtime(hw=_HW_16G):
            entries = _states(registry.status()["entries"])
        entry = entries["vlm_minicpm"]
        self.assertEqual(entry["state"], "blocked")
        self.assertIn("待 T6", entry["detail"])
        self.assertIn("7B fp16 / 26B int4", entry["detail"])
        self.assertEqual(entry["action"], "")

    def test_formula_entries_blocked_pending_t6(self) -> None:
        with _runtime():
            entries = _states(registry.status()["entries"])
        for entry_id in ("formula_pp_m", "formula_pp_l", "formula_p2t", "formula_texify"):
            self.assertEqual(entries[entry_id]["state"], "blocked")
            self.assertIn("待 T6", entries[entry_id]["detail"])

    def test_status_carries_hardware_and_tiers(self) -> None:
        with _runtime(hw=_HW_16G):
            payload = registry.status()
        self.assertEqual(payload["hardware"]["vram_gb"], 16.0)
        self.assertEqual(len(payload["vram_tiers"]), 7)
        self.assertIn("约", payload["vram_note"])


class MineruLocalTest(CatalogIsolated):
    def test_not_installed_is_degraded_with_install_action(self) -> None:
        with _runtime():
            entry = _states(registry.status()["entries"])["mineru_local"]
        self.assertEqual(entry["state"], "degraded")
        self.assertEqual(entry["action"], "install")

    def test_installed_is_ready(self) -> None:
        health = {"ok": True, "state": "ready", "version": "4.2.3", "message": ""}
        with _runtime(health=health):
            entry = _states(registry.status()["entries"])["mineru_local"]
        self.assertEqual(entry["state"], "ready")
        self.assertIn("4.2.3", entry["detail"])
        self.assertEqual(entry["action"], "")

    def test_install_failure_is_blocked_with_reason_and_retry(self) -> None:
        install = {"state": "error", "step": "安装依赖",
                   "message": "全部镜像失败：网络或镜像不通"}
        with _runtime(install=install):
            entry = _states(registry.status()["entries"])["mineru_local"]
        self.assertEqual(entry["state"], "blocked")
        self.assertIn("网络或镜像不通", entry["detail"])
        self.assertEqual(entry["action"], "install")

    def test_broken_env_is_blocked(self) -> None:
        health = {"ok": False, "state": "error", "version": "",
                  "message": "MinerU 环境在但体检失败：dll load failed"}
        with _runtime(health=health):
            entry = _states(registry.status()["entries"])["mineru_local"]
        self.assertEqual(entry["state"], "blocked")
        self.assertEqual(entry["action"], "install")

    def test_gate_not_ready_falls_auto_ready_passes_through(self) -> None:
        with _runtime():
            picked, note = registry.gate_recognize("mineru_local")
        self.assertEqual(picked, "auto")
        self.assertIn("MinerU·本地", note)
        self.assertIn("未就绪", note)
        health = {"ok": True, "state": "ready", "version": "4.2.3", "message": ""}
        with _runtime(health=health):
            picked, note = registry.gate_recognize("mineru_local")
        self.assertEqual(picked, "mineru_local")
        self.assertEqual(note, "")

    def test_wired_entry_declares_plan_and_no_gate_note(self) -> None:
        entry = next(item for item in registry.catalog() if item["id"] == "mineru_local")
        self.assertEqual(entry.get("plan_recognize"), ["mineru_local"])
        self.assertFalse(str(entry.get("gate_note") or ""))


class PrefsGateTest(CatalogIsolated):
    def test_disabled_entry_hidden_from_ready_and_gated_with_reason(self) -> None:
        prefs = {"disabled": ["yolo"], "default_layout": "auto",
                 "default_recognize": "auto"}
        with _runtime(yolo=True, prefs=prefs):
            entries = _states(registry.status()["entries"])
            picked, note = registry.gate_layout("yolo")
        self.assertFalse(entries["yolo"]["enabled"])
        self.assertEqual(entries["yolo"]["state"], "ready")
        self.assertEqual(picked, "auto")
        self.assertIn("已停用", note)

    def test_enabled_by_default_and_defaults_surface(self) -> None:
        prefs = {"disabled": [], "default_layout": "yolo",
                 "default_recognize": "mineru"}
        with _runtime(yolo=True, mineru=_mineru(), prefs=prefs):
            payload = registry.status()
        self.assertTrue(all(entry["enabled"] for entry in payload["entries"]))
        self.assertEqual(payload["defaults"],
                         {"layout": "yolo", "recognize": "mineru"})


class RegistryApiTest(CatalogIsolated):
    def test_endpoint_returns_registry_payload(self) -> None:
        payload = {"ok": True, "entries": [{"id": "yolo", "state": "ready"}]}
        with mock.patch.object(registry, "status", return_value=payload):
            self.assertEqual(models_api.models_registry(), payload)

    def test_main_app_mounts_the_route(self) -> None:
        from app.main import create_app
        # FastAPI 0.141 把 include_router 包成 _IncludedRouter，以 OpenAPI paths 为准。
        paths = create_app().openapi().get("paths", {})
        self.assertIn("/api/models/registry", paths)
        self.assertIn("/api/models/mineru/install", paths)
        self.assertIn("/api/models/mineru/status", paths)
        self.assertIn("/api/models/prefs", paths)

    def test_write_routes_declare_write_token(self) -> None:
        from app.core.security import require_write_token
        writes = [route for route in models_api.router.routes
                  if getattr(route, "methods", set()) & {"POST"}]
        self.assertEqual(len(writes), 2)
        for route in writes:
            self.assertIn(require_write_token,
                          [dep.dependency for dep in route.dependencies])

    def test_prefs_endpoint_rejects_unknown_id(self) -> None:
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            models_api.models_prefs({"disabled": ["不存在的引擎"]}, plugin_id=EDITOR)
        self.assertEqual(caught.exception.status_code, 400)

    def test_prefs_endpoint_writes_only_requesting_plugin_dir(self) -> None:
        saved = models_api.models_prefs({"disabled": ["yolo"]}, plugin_id=EDITOR)
        self.assertEqual(saved["disabled"], ["yolo"])
        self.assertTrue((self.plugin / "model_prefs.toml").is_file())

    def test_prefs_endpoint_forbids_undeclared_plugin(self) -> None:
        from fastapi import HTTPException
        from app.core import toml_io
        manifest = self.plugin / "plugin.toml"
        data = toml_io.load(manifest, {})
        data["capabilities"] = ["question.edit"]
        toml_io.write(manifest, data)
        with self.assertRaises(HTTPException) as caught:
            models_api.models_prefs({"disabled": []}, plugin_id=EDITOR)
        self.assertEqual(caught.exception.status_code, 403)
        self.assertIn("models.catalog", caught.exception.detail)

    def test_prefs_endpoint_forbids_absent_plugin(self) -> None:
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            models_api.models_prefs({"disabled": []}, plugin_id="org.example.ghost")
        self.assertEqual(caught.exception.status_code, 403)

    def test_install_endpoint_translates_setup_error(self) -> None:
        from fastapi import HTTPException
        with mock.patch.object(models_api.mineru_setup, "start_install",
                               side_effect=models_api.mineru_setup.MineruSetupError("Python 太旧")):
            with self.assertRaises(HTTPException) as caught:
                models_api.mineru_install()
        self.assertEqual(caught.exception.status_code, 400)
        self.assertIn("Python 太旧", caught.exception.detail)


if __name__ == "__main__":
    unittest.main()