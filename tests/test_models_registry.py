"""模型注册表（配置归插件卡）：插件目录×通用规则解释器×运行时三态、闸口、只读 API。

目录是插件财产：夹具造一个声明 models.catalog 的最小 headless 插件，
catalog.toml 从插件源码仓原样拷来（tests/catalog_fixture.py）。底座只认
七个规则名，不认任何模型 id；未知规则＝blocked＋提示更新底座，绝不静默。

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
from app.core.ingest import formula_setup, ocr_setup, registry
from tests.catalog_fixture import CATALOG_CAPABILITY, EDITOR, CatalogIsolated

_HW_16G = {"vram_gb": 16.0, "vram_label": "16.0G", "gpu_name": "测试卡",
           "vram_source": "nvidia-smi", "detail": ""}
_HW_LOW = {"vram_gb": 4.0, "vram_label": "4.0G", "gpu_name": "",
           "vram_source": "wmi", "detail": ""}
_HEALTH_MISSING = {"ok": False, "state": "missing", "version": "",
                   "message": "本地 MinerU 未安装。"}
_VLM_HEALTH_MISSING = {"ok": False, "state": "missing", "version": "",
                       "message": "本地 VLM 未安装。"}
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
             prefs: dict | None = None,
             vlm_health: dict | None = None,
             vlm_install: dict | None = None,
             vlm_weights: bool = False,
             ocr_weights: bool = False,
             ocr_install: dict | None = None,
             formula_weights: bool = False,
             formula_l_weights: bool = False,
             formula_p2t_weights: bool = False,
             formula_install: dict | None = None):
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
            mock.patch.object(registry.vlm_setup, "health",
                              return_value=vlm_health if vlm_health is not None else dict(_VLM_HEALTH_MISSING)), \
            mock.patch.object(registry.vlm_setup, "status",
                              return_value=vlm_install if vlm_install is not None else {"state": "idle"}), \
            mock.patch.object(registry.vlm_setup, "weights_ready", return_value=vlm_weights), \
            mock.patch.object(ocr_setup, "weights_ready", return_value=ocr_weights), \
            mock.patch.object(ocr_setup, "status",
                              return_value=ocr_install if ocr_install is not None else {"state": "idle"}), \
            mock.patch.object(formula_setup, "weights_ready",
                              side_effect=lambda variant="m": (
                                  {"l": formula_l_weights,
                                   "p2t": formula_p2t_weights}.get(variant, formula_weights))), \
            mock.patch.object(formula_setup, "status",
                              return_value=formula_install if formula_install is not None else {"state": "idle"}), \
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
        self.assertEqual(entries["rapidocr_accurate"]["state"], "degraded")
        self.assertIn("权重未下载", entries["rapidocr_accurate"]["detail"])
        self.assertEqual(entries["rapidocr_accurate"]["action"], "install_ocr")

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

    def test_accurate_unlocks_real_install_and_ready(self) -> None:
        """2.20.0 卡§6：准档 blocked→weight_present，权重在＝就绪、不在＝真安装动作。"""
        with _runtime(ocr_weights=True):
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["rapidocr_accurate"]["state"], "ready")
        self.assertEqual(entries["rapidocr_accurate"]["action"], "")
        self.assertIn("medium 权重已落地", entries["rapidocr_accurate"]["detail"])
        with _runtime():
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["rapidocr_accurate"]["state"], "degraded")
        self.assertEqual(entries["rapidocr_accurate"]["action"], "install_ocr")

    def test_accurate_install_error_is_blocked_with_retry(self) -> None:
        with _runtime(ocr_install={"state": "error", "message": "权重源全不通"}):
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["rapidocr_accurate"]["state"], "blocked")
        self.assertIn("权重源全不通", entries["rapidocr_accurate"]["detail"])
        self.assertEqual(entries["rapidocr_accurate"]["action"], "install_ocr")

    def test_accurate_ready_pick_runs_only_ocr_medium(self) -> None:
        from app.core.ingest.layout import router as layout_router

        with _runtime(ocr_weights=True):
            self.assertEqual(registry.gate_layout("rapidocr_accurate"),
                             ("rapidocr_accurate", ""))
            self.assertEqual(layout_router.plan("rapidocr_accurate"), ("ocr_medium",))
        self.assertIn("ocr_medium", layout_router.default_providers())

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
        """2.20.0 卡§6：六→三，留千问/面壁/书生；安装接线卡座5/6 三座全接线。"""
        vlms = [item for item in registry.catalog() if item.get("family") == "vlm"]
        self.assertEqual(sorted(item["id"] for item in vlms),
                         ["vlm_intern", "vlm_minicpm", "vlm_qwen"])
        for item in vlms:
            self.assertGreaterEqual(int(item["min_vram"]), 6)
            self.assertTrue(item["can_cpu"])
            self.assertEqual(item["rule"], "vlm_local")
            self.assertEqual(item["plan_recognize"], ["vlm_local"])

    def test_formula_four_registered(self) -> None:
        formulas = [item["id"] for item in registry.catalog()
                    if item.get("family") == "formula"]
        self.assertEqual(sorted(formulas),
                         ["formula_p2t", "formula_pp_l", "formula_pp_m", "formula_texify"])

    def test_p2t_renamed_to_pix2text(self) -> None:
        """卡§6：pix2tex 与 Pix2Text 是两家，全族文案改 Pix2Text·MFR。"""
        entry = next(item for item in registry.catalog() if item["id"] == "formula_p2t")
        self.assertEqual(entry["name"], "Pix2Text·MFR（公式专科）")
        self.assertIn("Pix2Text", entry["summary"])
        for item in registry.catalog():
            self.assertNotIn("pix2tex", str(item.get("name", "")) + str(item.get("summary", "")))

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

    def test_seven_rules_are_the_whole_contract(self) -> None:
        self.assertEqual(sorted(registry.RULES),
                         sorted(["import_probe", "weight_present", "task_assign",
                                 "mineru_local", "vlm_local", "vram_gate", "blocked"]))


class MissingCatalogTest(CatalogIsolated):
    """无提供者/目录损坏＝空目录：下拉只剩 auto，闸口不静默也不崩。"""

    def test_no_provider_means_empty_catalog_and_auto_defaults(self) -> None:
        shutil.rmtree(self.plugin)
        with _runtime():
            payload = registry.status()
        self.assertEqual(payload["entries"], [])
        self.assertEqual(payload["defaults"],
                         {"layout": "auto", "recognize": "auto",
                          "auto_image_seat": "auto", "auto_text_formula_seat": "auto"})
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
    def test_low_vram_installed_is_ready_with_cpu_fallback(self) -> None:
        vlm_ok = {"ok": True, "state": "ready", "version": "0.2.3",
                  "engine": "vulkan", "message": ""}
        with _runtime(hw=_HW_LOW, vlm_health=vlm_ok, vlm_weights=True):
            entries = _states(registry.status()["entries"])
        entry = entries["vlm_qwen"]
        self.assertEqual(entry["state"], "ready")
        self.assertIn("CPU 慢兜底", entry["detail"])
        self.assertIn("4.0G", entry["detail"])
        self.assertIn("6G", entry["detail"])

    def test_low_vram_not_installed_still_offers_install(self) -> None:
        with _runtime(hw=_HW_LOW):
            entry = _states(registry.status()["entries"])["vlm_qwen"]
        self.assertEqual(entry["state"], "degraded")
        self.assertEqual(entry["action"], "install_vlm")

    def test_vlm_intern_minicpm_wired_with_per_seat_install_actions(self) -> None:
        """安装接线卡座5/6：书生/面壁不再 vram_gate 登记，走 vlm_local 三态＋按座安装动作。"""
        with _runtime(hw=_HW_16G):
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["vlm_intern"]["state"], "degraded")
        self.assertEqual(entries["vlm_intern"]["action"], "install_vlm_intern")
        self.assertEqual(entries["vlm_minicpm"]["state"], "degraded")
        self.assertEqual(entries["vlm_minicpm"]["action"], "install_vlm_minicpm")
        self.assertIn("1.74GB", entries["vlm_intern"]["detail"])
        self.assertIn("4.85GB", entries["vlm_minicpm"]["detail"])
        ready_health = {"ok": True, "state": "ready", "version": "0.2.3",
                        "engine": "vulkan", "message": ""}
        with _runtime(hw=_HW_16G, vlm_health=ready_health, vlm_weights=True):
            entries = _states(registry.status()["entries"])
        for seat in ("vlm_qwen", "vlm_intern", "vlm_minicpm"):
            self.assertEqual(entries[seat]["state"], "ready")

    def test_formula_entries_blocked_pending_d_card(self) -> None:
        with _runtime():
            entries = _states(registry.status()["entries"])
        # texify 侦查门判跳过（官方无 ONNX、底座零 torch）：blocked 文案改实。
        self.assertEqual(entries["formula_texify"]["state"], "blocked")
        self.assertIn("登记跳过", entries["formula_texify"]["detail"])
        self.assertEqual(entries["formula_texify"]["capability"], "formula")
        # PP-M/L＋p2t 已接线：权重三态，未装引导安装，不再 blocked。
        self.assertEqual(entries["formula_pp_m"]["state"], "degraded")
        self.assertEqual(entries["formula_pp_m"]["action"], "install_formula")
        self.assertEqual(entries["formula_pp_l"]["state"], "degraded")
        self.assertEqual(entries["formula_pp_l"]["action"], "install_formula_l")
        self.assertEqual(entries["formula_p2t"]["state"], "degraded")
        self.assertEqual(entries["formula_p2t"]["action"], "install_formula_p2t")

    def test_formula_pp_m_ready_when_weights_present(self) -> None:
        with _runtime(formula_weights=True):
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["formula_pp_m"]["state"], "ready")
        self.assertEqual(entries["formula_pp_m"]["capability"], "formula")
        self.assertEqual(entries["formula_pp_l"]["state"], "degraded")

    def test_formula_pp_l_ready_when_weights_present(self) -> None:
        with _runtime(formula_l_weights=True):
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["formula_pp_l"]["state"], "ready")
        self.assertEqual(entries["formula_pp_l"]["capability"], "formula")
        self.assertEqual(entries["formula_pp_m"]["state"], "degraded")

    def test_formula_p2t_ready_when_weights_present(self) -> None:
        with _runtime(formula_p2t_weights=True):
            entries = _states(registry.status()["entries"])
        self.assertEqual(entries["formula_p2t"]["state"], "ready")
        self.assertEqual(entries["formula_p2t"]["capability"], "formula")
        self.assertEqual(entries["formula_pp_m"]["state"], "degraded")
        self.assertEqual(entries["formula_pp_l"]["state"], "degraded")

    def test_status_carries_hardware_and_tiers(self) -> None:
        with _runtime(hw=_HW_16G):
            payload = registry.status()
        self.assertEqual(payload["hardware"]["vram_gb"], 16.0)
        self.assertEqual(len(payload["vram_tiers"]), 7)
        self.assertIn("约", payload["vram_note"])


class VlmLocalRuleTest(CatalogIsolated):
    """本地 VLM 座（2.20.0 卡§4/§5）：安装体检＋权重＋显存门；不够不灰死安装。"""

    VLM_OK = {"ok": True, "state": "ready", "version": "0.2.3",
              "engine": "vulkan", "message": ""}

    def test_not_installed_is_degraded_with_install_action(self) -> None:
        with _runtime():
            entry = _states(registry.status()["entries"])["vlm_qwen"]
        self.assertEqual(entry["state"], "degraded")
        self.assertEqual(entry["action"], "install_vlm")
        self.assertIn("安装本地 VLM", entry["detail"])

    def test_weights_missing_is_degraded_even_if_env_ok(self) -> None:
        with _runtime(vlm_health=self.VLM_OK, vlm_weights=False):
            entry = _states(registry.status()["entries"])["vlm_qwen"]
        self.assertEqual(entry["state"], "degraded")
        self.assertEqual(entry["action"], "install_vlm")

    def test_installed_with_weights_and_vram_is_ready(self) -> None:
        with _runtime(vlm_health=self.VLM_OK, vlm_weights=True):
            entry = _states(registry.status()["entries"])["vlm_qwen"]
        self.assertEqual(entry["state"], "ready")
        self.assertIn("0.2.3", entry["detail"])
        self.assertEqual(entry["action"], "")
        self.assertEqual(entry["badge"], "已安装·就绪（Vulkan）")

    def test_badge_and_brief_are_live_per_vram(self) -> None:
        with _runtime(hw=_HW_LOW, vlm_health=self.VLM_OK, vlm_weights=True):
            low = _states(registry.status()["entries"])["vlm_qwen"]
        self.assertEqual(low["badge"], "已安装·本机显存不足·CPU 慢兜底")
        self.assertIn("4.0G", low["brief"])
        self.assertIn("CPU 慢兜底", low["brief"])
        with _runtime(hw=_HW_LOW):
            missing = _states(registry.status()["entries"])["vlm_qwen"]
        self.assertEqual(missing["badge"], "未安装")
        self.assertIn("4.0G", missing["brief"])
        with _runtime(vlm_health=self.VLM_OK, vlm_weights=True):
            ok = _states(registry.status()["entries"])["vlm_qwen"]
        self.assertIn("Vulkan", ok["brief"])

    def test_boot_refresh_reuses_snapshot_without_probing(self) -> None:
        with _runtime():
            with mock.patch.object(registry.hardware, "snapshot",
                                   return_value=dict(_HW_LOW)) as snap:
                payload = registry.status(probe_hardware=False)
                registry.hardware.probe.assert_not_called()
        snap.assert_called_once()
        self.assertEqual(payload["hardware"]["vram_label"], "4.0G")

    def test_install_failure_is_blocked_with_reason_and_retry(self) -> None:
        install = {"state": "error", "step": "预取权重",
                   "message": "权重校验和不符，已丢弃"}
        with _runtime(vlm_install=install):
            entry = _states(registry.status()["entries"])["vlm_qwen"]
        self.assertEqual(entry["state"], "blocked")
        self.assertIn("权重校验和不符", entry["detail"])
        self.assertEqual(entry["action"], "install_vlm")

    def test_broken_env_is_blocked(self) -> None:
        broken = {"ok": False, "state": "error", "version": "",
                  "message": "llama-cpp 环境在但体检失败：dll load failed"}
        with _runtime(vlm_health=broken):
            entry = _states(registry.status()["entries"])["vlm_qwen"]
        self.assertEqual(entry["state"], "blocked")
        self.assertIn("dll load failed", entry["detail"])
        self.assertEqual(entry["action"], "install_vlm")

    def test_wired_entry_declares_plan(self) -> None:
        entry = next(item for item in registry.catalog() if item["id"] == "vlm_qwen")
        self.assertEqual(entry.get("plan_recognize"), ["vlm_local"])

    def test_auto_seats_come_from_catalog_and_prefs_override(self) -> None:
        with _runtime():
            seats = registry.auto_seats()
        self.assertEqual(seats["auto_image_seat"], "mineru_local")
        self.assertEqual(seats["auto_text_formula_seat"], "formula_pp_m")
        prefs = dict(_PREFS_EMPTY, auto_image_seat="cloud_vision",
                     auto_text_formula_seat="auto")
        with _runtime(prefs=prefs, vision=_vision()):
            seats = registry.auto_seats()
        self.assertEqual(seats["auto_image_seat"], "cloud_vision")
        self.assertEqual(seats["auto_text_formula_seat"], "formula_pp_m")


class ComboChainTest(CatalogIsolated):
    """组合路三链（2.20.0 卡§2）：复用既有七规则，不造第八规则；链路不是模型。"""

    VLM_OK = {"ok": True, "state": "ready", "version": "0.2.3",
              "engine": "vulkan", "message": ""}

    def test_five_combos_declare_plan_and_seat(self) -> None:
        catalog = {entry["id"]: entry for entry in registry.catalog()}
        expected = {"combo_cloud": "cloud_vision", "combo_vlm": "vlm_qwen",
                    "combo_pp_m": "formula_pp_m", "combo_pp_l": "formula_pp_l",
                    "combo_p2t": "formula_p2t"}
        for combo_id, seat in expected.items():
            with self.subTest(combo=combo_id):
                entry = catalog[combo_id]
                self.assertEqual(entry["capability"], "recognize")
                self.assertEqual(entry["plan_recognize"], ["combo"])
                self.assertEqual(entry["combo_seat"], seat)
                self.assertIn("文字层取", entry["summary_usage"])
                self.assertIn("纯图卷", entry["summary_usage"])

    def test_formula_combos_use_weight_rule_matching_seat(self) -> None:
        """全组合（记上次卡）：PP-L/p2t 组合用 weight_present＋store 与公式座同档，
        就绪完全随座（零 registry/router 代码改）；不照抄 combo_pp_m 的 import_probe
        （那会与权重无关，违背「按就绪公式座枚举」）。"""
        catalog = {entry["id"]: entry for entry in registry.catalog()}
        for combo_id, seat_id, store in (("combo_pp_l", "formula_pp_l", "formula_l"),
                                         ("combo_p2t", "formula_p2t", "formula_p2t")):
            with self.subTest(combo=combo_id):
                self.assertEqual(catalog[combo_id]["rule"], "weight_present")
                self.assertEqual(catalog[combo_id]["store"], store)
                self.assertEqual(catalog[combo_id]["store"], catalog[seat_id]["store"])

    def test_combo_pp_l_follows_formula_l_weights(self) -> None:
        with _runtime():
            entries = _states(registry.status()["entries"])
            self.assertEqual(entries["combo_pp_l"]["state"], "degraded")
            self.assertEqual(entries["combo_pp_l"]["state"], entries["formula_pp_l"]["state"])
            self.assertEqual(entries["combo_pp_l"]["action"], "install_formula_l")
        with _runtime(formula_l_weights=True):
            entries = _states(registry.status()["entries"])
            self.assertEqual(entries["combo_pp_l"]["state"], "ready")
            self.assertEqual(entries["combo_pp_l"]["state"], entries["formula_pp_l"]["state"])
            self.assertIn("组合路就绪", entries["combo_pp_l"]["detail"])

    def test_combo_p2t_follows_formula_p2t_weights(self) -> None:
        with _runtime():
            entries = _states(registry.status()["entries"])
            self.assertEqual(entries["combo_p2t"]["state"], "degraded")
            self.assertEqual(entries["combo_p2t"]["state"], entries["formula_p2t"]["state"])
            self.assertEqual(entries["combo_p2t"]["action"], "install_formula_p2t")
        with _runtime(formula_p2t_weights=True):
            entries = _states(registry.status()["entries"])
            self.assertEqual(entries["combo_p2t"]["state"], "ready")
            self.assertEqual(entries["combo_p2t"]["state"], entries["formula_p2t"]["state"])
            self.assertIn("组合路就绪", entries["combo_p2t"]["detail"])

    def test_formula_combo_ready_only_when_its_own_seat_ready(self) -> None:
        """装 L 不连带 p2t：各组合只随各自公式座，互不串。"""
        with _runtime(formula_l_weights=True):
            entries = _states(registry.status()["entries"])
            self.assertEqual(entries["combo_pp_l"]["state"], "ready")
            self.assertEqual(entries["combo_p2t"]["state"], "degraded")
        with _runtime(formula_p2t_weights=True):
            entries = _states(registry.status()["entries"])
            self.assertEqual(entries["combo_p2t"]["state"], "ready")
            self.assertEqual(entries["combo_pp_l"]["state"], "degraded")

    def test_combo_cloud_follows_vision_assignment(self) -> None:
        with _runtime():
            entry = _states(registry.status()["entries"])["combo_cloud"]
        self.assertEqual(entry["state"], "degraded")
        self.assertEqual(entry["action"], "assign")
        with _runtime(vision=_vision()):
            entry = _states(registry.status()["entries"])["combo_cloud"]
        self.assertEqual(entry["state"], "ready")
        self.assertIn("视觉一号", entry["detail"])
        self.assertIn("组合路就绪", entry["detail"])

    def test_combo_vlm_follows_local_vlm_health(self) -> None:
        with _runtime():
            entry = _states(registry.status()["entries"])["combo_vlm"]
        self.assertEqual(entry["state"], "degraded")
        self.assertEqual(entry["action"], "install_vlm")
        with _runtime(vlm_health=self.VLM_OK, vlm_weights=True):
            entry = _states(registry.status()["entries"])["combo_vlm"]
        self.assertEqual(entry["state"], "ready")
        self.assertIn("组合路就绪", entry["detail"])

    def test_combo_pp_m_ready_and_discloses_uninstalled_weights(self) -> None:
        with _runtime():
            entry = _states(registry.status()["entries"])["combo_pp_m"]
        self.assertEqual(entry["state"], "ready")
        self.assertIn("PP-FormulaNet·M", entry["detail"])
        self.assertIn("待核", entry["detail"])

    def test_combo_gate_passes_ready_and_falls_auto_degraded(self) -> None:
        with _runtime(vision=_vision()):
            picked, note = registry.gate_recognize("combo_cloud")
        self.assertEqual(picked, "combo_cloud")
        self.assertEqual(note, "")
        with _runtime():
            picked, note = registry.gate_recognize("combo_cloud")
        self.assertEqual(picked, "auto")
        self.assertIn("未就绪", note)

    def test_auto_defaults_stay_single_seats_not_combos(self) -> None:
        with _runtime():
            seats = registry.auto_seats()
        self.assertNotIn("combo", seats["auto_image_seat"])
        self.assertNotIn("combo", seats["auto_text_formula_seat"])


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
                         {"layout": "yolo", "recognize": "mineru",
                          "auto_image_seat": "auto", "auto_text_formula_seat": "auto"})


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
        self.assertIn("/api/models/vlm/install", paths)
        self.assertIn("/api/models/vlm/status", paths)
        self.assertIn("/api/models/vlm/uninstall", paths)
        self.assertIn("/api/models/vlm_intern/install", paths)
        self.assertIn("/api/models/vlm_intern/status", paths)
        self.assertIn("/api/models/vlm_intern/uninstall", paths)
        self.assertIn("/api/models/vlm_minicpm/install", paths)
        self.assertIn("/api/models/vlm_minicpm/status", paths)
        self.assertIn("/api/models/vlm_minicpm/uninstall", paths)
        self.assertIn("/api/models/mineru/uninstall", paths)
        self.assertIn("/api/models/ocr/install", paths)
        self.assertIn("/api/models/ocr/status", paths)
        self.assertIn("/api/models/ocr/uninstall", paths)
        self.assertIn("/api/models/formula/install", paths)
        self.assertIn("/api/models/formula/status", paths)
        self.assertIn("/api/models/formula/uninstall", paths)
        self.assertIn("/api/models/formula_l/install", paths)
        self.assertIn("/api/models/formula_l/status", paths)
        self.assertIn("/api/models/formula_l/uninstall", paths)
        self.assertIn("/api/models/formula_p2t/install", paths)
        self.assertIn("/api/models/formula_p2t/status", paths)
        self.assertIn("/api/models/formula_p2t/uninstall", paths)
        self.assertIn("/api/pending/reidentify", paths)
        self.assertIn("/api/pending/reidentify/spans", paths)
        self.assertIn("/api/pending/return_batch", paths)

    def test_write_routes_declare_write_token(self) -> None:
        from app.core.security import require_write_token
        writes = [route for route in models_api.router.routes
                  if getattr(route, "methods", set()) & {"POST"}]
        self.assertEqual(len(writes), 17)
        for route in writes:
            self.assertIn(require_write_token,
                          [dep.dependency for dep in route.dependencies])

    def test_formula_l_endpoints_pass_variant_through(self) -> None:
        with mock.patch.object(formula_setup, "status",
                               return_value={"state": "idle"}) as status, \
                mock.patch.object(formula_setup, "start_install",
                                  return_value={"state": "installing"}) as install, \
                mock.patch.object(formula_setup, "uninstall",
                                  return_value={"ok": True}) as uninstall:
            models_api.formula_l_status()
            models_api.formula_l_install()
            models_api.formula_l_uninstall()
        status.assert_called_once_with("l")
        install.assert_called_once_with("l")
        uninstall.assert_called_once_with("l")

    def test_formula_p2t_endpoints_pass_variant_through(self) -> None:
        with mock.patch.object(formula_setup, "status",
                               return_value={"state": "idle"}) as status, \
                mock.patch.object(formula_setup, "start_install",
                                  return_value={"state": "installing"}) as install, \
                mock.patch.object(formula_setup, "uninstall",
                                  return_value={"ok": True}) as uninstall:
            models_api.formula_p2t_status()
            models_api.formula_p2t_install()
            models_api.formula_p2t_uninstall()
        status.assert_called_once_with("p2t")
        install.assert_called_once_with("p2t")
        uninstall.assert_called_once_with("p2t")

    def test_vlm_uninstall_stops_service_only_when_this_seat_active(self) -> None:
        from app.core.ingest import vlm_setup
        calls = []
        with mock.patch("app.core.ingest.recognize.vlm_service.active_seat",
                        return_value="qwen"), \
                mock.patch("app.core.ingest.recognize.vlm_service.stop",
                           side_effect=lambda: calls.append("stop")), \
                mock.patch.object(vlm_setup, "uninstall",
                                  side_effect=lambda seat="qwen": calls.append("uninstall")
                                  or {"ok": True, "message": "已卸载"}):
            result = models_api.vlm_uninstall()
        self.assertEqual(calls, ["stop", "uninstall"])
        self.assertTrue(result["ok"])
        calls.clear()
        with mock.patch("app.core.ingest.recognize.vlm_service.active_seat",
                        return_value="intern"), \
                mock.patch("app.core.ingest.recognize.vlm_service.stop",
                           side_effect=lambda: calls.append("stop")), \
                mock.patch.object(vlm_setup, "uninstall",
                                  side_effect=lambda seat="qwen": calls.append("uninstall")
                                  or {"ok": True, "message": "已卸载"}):
            models_api.vlm_uninstall()
        self.assertEqual(calls, ["uninstall"], "别座在跑不停服，只删本座权重")

    def test_vlm_intern_minicpm_endpoints_pass_seat_through(self) -> None:
        from app.core.ingest import vlm_setup
        for seat, status_fn, install_fn, uninstall_fn in (
                ("intern", models_api.vlm_intern_status,
                 models_api.vlm_intern_install, models_api.vlm_intern_uninstall),
                ("minicpm", models_api.vlm_minicpm_status,
                 models_api.vlm_minicpm_install, models_api.vlm_minicpm_uninstall)):
            with mock.patch.object(vlm_setup, "status",
                                   return_value={"state": "idle"}) as status, \
                    mock.patch.object(vlm_setup, "start_install",
                                      return_value={"state": "installing"}) as install, \
                    mock.patch.object(vlm_setup, "uninstall",
                                      return_value={"ok": True}) as uninstall, \
                    mock.patch("app.core.ingest.recognize.vlm_service.active_seat",
                               return_value=""):
                status_fn()
                install_fn()
                uninstall_fn()
            status.assert_called_once_with(seat)
            install.assert_called_once_with(seat)
            uninstall.assert_called_once_with(seat)

    def test_mineru_uninstall_refusal_is_400(self) -> None:
        from fastapi import HTTPException
        from app.core.ingest import mineru_setup
        with mock.patch("app.core.ingest.recognize.mineru_service.stop"), \
                mock.patch.object(mineru_setup, "uninstall",
                                  side_effect=mineru_setup.MineruSetupError("安装中，不能卸载")):
            with self.assertRaises(HTTPException) as caught:
                models_api.mineru_uninstall()
        self.assertEqual(caught.exception.status_code, 400)
        self.assertIn("安装中", caught.exception.detail)

    def test_ocr_uninstall_delegates_and_refusal_is_400(self) -> None:
        from fastapi import HTTPException
        with mock.patch.object(ocr_setup, "uninstall",
                               return_value={"ok": True, "message": "已卸载"}):
            self.assertTrue(models_api.ocr_uninstall()["ok"])
        with mock.patch.object(ocr_setup, "uninstall",
                               side_effect=ocr_setup.OcrSetupError("安装中，不能卸载")):
            with self.assertRaises(HTTPException) as caught:
                models_api.ocr_uninstall()
        self.assertEqual(caught.exception.status_code, 400)

    def test_ocr_install_refusal_is_400(self) -> None:
        from fastapi import HTTPException
        with mock.patch.object(ocr_setup, "start_install",
                               side_effect=ocr_setup.OcrSetupError("权重源全不通")):
            with self.assertRaises(HTTPException) as caught:
                models_api.ocr_install()
        self.assertEqual(caught.exception.status_code, 400)
        self.assertIn("权重源全不通", caught.exception.detail)

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