# -*- coding: utf-8 -*-
"""双引擎路由、五特征坏题体检与分诊统计契约（T6 分流语义）。

钉住六件事：
1. 版面/识别两套引擎的白名单单源在插件 catalog；老四通道名仍能映射；
   识别自动＝按卷型分流（不再是步骤队列），具体档选谁只走谁；
2. 五特征（连续空选项 / 掉变量句式 / 内联小图多但无公式 / 长文无符号 / 公式图未补）各报各的；
3. 每次解析静默打一行 ``[STAT] 本次解析总题数: X, 坏题数: Y, 坏题率: Z%``；
4. 坏题率只供统计口径：自动＋文字卷走组合路，坏题/无坐标走整题兜底，
   不再按 30% 阈值切换全量 OCR（T6 拍板）；
5. MinerU 引擎整批一次发送单题截图（绝不发整卷 PDF），轮询进度逐轮写回路由；
6. 双下拉框带原生 title，只影响下一次解析，且单文件不超过 400 行。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ingest_triage``
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from app.core.ingest import route as ingest_route
from app.core.pending import service
from app.core.ai.platform import center as ai_center
from app.core.ingest.quality import question_reasons, triage_documents
from app.core.ingest.layout import router as layout_router
from app.core.ingest.recognize import (ai as recognize_ai, mineru as recognize_mineru, router as recognize_router)
from tests.catalog_fixture import CatalogIsolated

ROOT = Path(__file__).resolve().parents[1]
from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
PLUGIN_DIR = PLUGIN_SOURCE_DIR / "org.jiuzhang.editor"
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
    if kind == "formula_image":
        return {"type": "solution", "stem": "已知 $x+1=2$，求 [公式图:1] 的值。"}
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


class EngineConstantTest(CatalogIsolated):
    """引擎名单单源在插件 catalog（配置归插件卡）；自动＝分流，步骤实现名归底座。"""

    def test_01_layout_matrix_auto_waterfall_specific_single(self) -> None:
        self.assertEqual(layout_router.plan("auto"), ("python", "yolo", "cloud"))
        self.assertEqual(layout_router.plan("rapidocr_fast"), ("ocr",))
        self.assertEqual(layout_router.plan("yolo"), ("yolo",))
        self.assertEqual(layout_router.plan("cloud_vision"), ("cloud",))
        self.assertEqual(layout_router.normalize_engine("乱填"), layout_router.LAYOUT_AUTO)
        self.assertEqual(layout_router.normalize_engine(None), layout_router.LAYOUT_AUTO)

    def test_02_recognize_matrix_auto_splits_specific_single(self) -> None:
        # T6：自动不再是步骤队列，按卷型分流（纯图→整题座；文字→组合路）。
        self.assertEqual(recognize_router.plan("auto"), ())
        self.assertEqual(recognize_router.plan("cloud_vision"), ("ai",))
        self.assertEqual(recognize_router.plan("mineru"), ("mineru",))
        self.assertEqual(recognize_router.plan("mineru_local"), ("mineru_local",))
        self.assertEqual(recognize_router.BAD_RATE_THRESHOLD, 0.30)
        self.assertEqual(ingest_route.INGEST_BAD_RATE_THRESHOLD, 0.30)

    def test_03_legacy_channels_still_map(self) -> None:
        self.assertEqual(recognize_router.from_legacy_channel("local_ai"), "auto")
        self.assertEqual(recognize_router.from_legacy_channel("full_ocr"), "cloud_vision")
        self.assertEqual(recognize_router.from_legacy_channel("mineru"), "mineru")
        self.assertEqual(recognize_router.from_legacy_channel("乱填"), "auto")
        self.assertEqual(layout_router.normalize_engine("cloud"), "cloud_vision")
        self.assertEqual(layout_router.normalize_engine("ocr"), "rapidocr_fast")

    def test_04_engine_modules_stay_under_four_hundred_lines(self) -> None:
        modules = [
            ROOT / "app" / "core" / "ingest" / "layout" / name
            for name in ("router.py", "python.py", "yolo.py", "cloud.py")
        ] + [
            ROOT / "app" / "core" / "ingest" / "recognize" / name
            for name in ("router.py", "local.py", "ai.py", "mineru.py",
                         "shared.py")
        ] + [
            ROOT / "app" / "core" / "ingest" / name
            for name in ("service.py", "intake/text.py", "intake/media.py",
                         "route.py")
        ]
        for path in modules:
            with self.subTest(module=path.name):
                self.assertLessEqual(
                    len(path.read_text(encoding="utf-8").splitlines()), 400,
                    f"{path.name} 超过 400 行")


class BadFeatureTest(unittest.TestCase):
    def test_01_each_feature_is_reported(self) -> None:
        self.assertIn("连续空选项", question_reasons(broken_doc("empty_options")))
        self.assertIn("掉变量句式", question_reasons(broken_doc("dropped_var")))
        self.assertIn("内联小图多但无公式", question_reasons(broken_doc("images_no_formula")))
        self.assertIn("长文无符号", question_reasons(broken_doc("long_no_symbol")))
        self.assertIn("公式图未补", question_reasons(broken_doc("formula_image")))

    def test_05_formula_image_mark_has_no_dollar_precondition(self) -> None:
        """既有 OMML 公式（含 ``$``）又有图片公式时，仍必须判「公式图未补」。"""
        document = {"type": "solution",
                    "stem": "计算 $x^2$ 后看图 [公式图:2]，写出结果。"}
        self.assertTrue(question_reasons(document))
        self.assertIn("公式图未补", question_reasons(document))

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
        with self.assertLogs("app.core.ingest.route", level="INFO") as captured:
            ingest_route.log_documents(docs)
        self.assertEqual(len(captured.records), 1)
        self.assertIn(
            "[STAT] 本次解析总题数: 10, 坏题数: 2, 坏题率: 20.0%",
            captured.output[0],
        )


class TriagePolicyTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    async def _run(self, documents: list[dict],
                   engine: str = recognize_router.RECOGNIZE_AUTO) -> dict:
        items = [item("p_test%02d" % index, document) for index, document in enumerate(documents)]
        saved: list[dict] = []

        def capture(rows, **_kwargs):
            saved.extend(rows)
            return {"saved_ids": [row.get("pending_id") for row in rows]}

        with mock.patch.object(service, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(service, "save_draft", side_effect=capture), \
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

    async def _run_split(self, documents: list[dict]) -> dict:
        """自动＋文字卷：走真实组合路接线，外部座全 mock（绝不触真引擎）。"""
        from app.core.ingest import registry

        items = [item("p_test%02d" % index, document) for index, document in enumerate(documents)]
        saved: list[dict] = []

        def capture(rows, **_kwargs):
            saved.extend(rows)
            return {"saved_ids": [row.get("pending_id") for row in rows]}

        def fake_local_run(batch_id, rows, pending, ready, route, on_progress):
            capture([{"pending_id": rows[index]["id"]} for index in pending])
            return {"ok": True, "attempted": len(pending), "filled": len(pending),
                    "filled_indexes": list(pending), "detail": ""}

        async def fake_combo(batch_id, rows, good, seat, route, on_progress,
                             page_images, pdf_bytes):
            return {"ok": True, "attempted": len(good), "filled": 0,
                    "filled_indexes": [], "no_coord_indexes": [],
                    "pending_marks": len(good), "seat_ready": False,
                    "seat_reason": "专科推理通道下一卡开（D 卡）", "detail": ""}

        combo = mock.AsyncMock(side_effect=fake_combo)
        local = mock.AsyncMock(side_effect=fake_local_run)
        ready = {"ok": True, "base_url": "http://127.0.0.1:43210", "token": "tok",
                 "detail": "本地 MinerU 服务已就绪"}
        with mock.patch.object(service, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(service, "save_draft", side_effect=capture), \
                mock.patch.object(registry, "auto_seats", return_value={
                    "auto_image_seat": "mineru_local",
                    "auto_text_formula_seat": "formula_pp_m"}), \
                mock.patch.object(registry, "entry_state", return_value={
                    "id": "mineru_local", "name": "MinerU·本地",
                    "state": "ready", "enabled": True}), \
                mock.patch.object(recognize_router.recognize_formula, "batch_context",
                                  return_value=([], None)), \
                mock.patch.object(recognize_router.recognize_formula, "run_combo", combo), \
                mock.patch.object(recognize_router.mineru_service, "ensure_ready",
                                  return_value=ready), \
                mock.patch.object(recognize_router.recognize_mineru_local, "run", local), \
                mock.patch.object(recognize_ai.ai_recognize, "recognize") as recognize:
            route = await ingest_route.fill_scan_batch(
                "B-001", recognize_router.RECOGNIZE_AUTO,
                {"has_text_layer": True, "garbled": False})
        return {"route": route, "saved": saved, "combo": combo,
                "local": local, "recognize": recognize}

    async def test_auto_text_combo_fallback_only_bad_questions(self) -> None:
        docs = [clean_doc(index) for index in range(8)] + [
            broken_doc("empty_options"), broken_doc("dropped_var")]
        with self.assertLogs("app.core.ingest.route", level="INFO") as captured:
            outcome = await self._run_split(docs)
        route = outcome["route"]
        self.assertIn("坏题率: 20.0%", captured.output[0])
        self.assertEqual(route["stats"]["bad"], 2)
        self.assertEqual(outcome["combo"].await_args.args[2], list(range(8)),
                         "好题保留文字直取，只把公式送座")
        self.assertEqual(outcome["local"].await_args.args[2], [8, 9],
                         "只有坏题走整题兜底")
        self.assertEqual([row["pending_id"] for row in outcome["saved"]],
                         ["p_test08", "p_test09"])
        self.assertEqual(route["mode"], "auto_combo")
        self.assertIn("组合路", route["note"])
        self.assertIn("整题兜底", route["note"])
        self.assertIn("待核", route["note"])
        outcome["recognize"].assert_not_called()
        self.assertEqual(route["layout_engine"], "auto")
        self.assertEqual(route["recognize_engine"], "auto")

    async def test_at_threshold_still_combo_not_full_ocr(self) -> None:
        docs = [clean_doc(index) for index in range(7)] + [
            broken_doc("empty_options"), broken_doc("dropped_var"),
            broken_doc("long_no_symbol")]
        outcome = await self._run_split(docs)
        route = outcome["route"]
        self.assertEqual(route["stats"]["rate"], 30.0)
        self.assertEqual(route["mode"], "auto_combo",
                         "坏题率只供统计：达到 30% 也不再切换全量 OCR（T6）")
        self.assertNotIn("并发全量 OCR", route["note"])
        self.assertEqual(outcome["local"].await_args.args[2], [7, 8, 9])

    async def test_cloud_vision_engine_ignores_threshold(self) -> None:
        docs = [clean_doc(index) for index in range(10)]
        outcome = await self._run(docs, engine="cloud_vision")
        self.assertEqual(outcome["recognize"].await_count, 10)
        self.assertEqual(outcome["route"]["mode"], "cloud_vision")

    async def test_clean_batch_combo_without_whole_question_fallback(self) -> None:
        outcome = await self._run_split([clean_doc(index) for index in range(5)])
        route = outcome["route"]
        self.assertEqual(route["mode"], "auto_combo")
        self.assertIn("文字直取正文", route["note"])
        outcome["local"].assert_not_called()
        outcome["recognize"].assert_not_called()
        self.assertEqual(outcome["saved"], [])

    async def test_mineru_engine_skips_ai(self) -> None:
        items = [item("p_mine%02d" % index, clean_doc(index)) for index in range(2)]
        with mock.patch.object(service, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(recognize_ai.ai_recognize, "recognize") as recognize, \
                mock.patch.object(recognize_mineru.recognize_shared, "item_image_bytes",
                                  return_value=b""):
            route = await ingest_route.fill_scan_batch(
                "B-003", "mineru",
                {"has_text_layer": False, "garbled": False})
        recognize.assert_not_called()
        self.assertEqual(route["recognize_engine"], "mineru")

    async def test_missing_mineru_account_is_reported(self) -> None:
        items = [item("p_none%02d" % index, clean_doc(index)) for index in range(2)]
        with mock.patch.object(service, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(ai_center, "find_mineru", return_value=None):
            route = await ingest_route.fill_scan_batch(
                "B-004", "mineru",
                {"has_text_layer": False, "garbled": False})
        self.assertIn("MinerU 没有可用的账号", route["note"])


class MineruPerQuestionTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    """提速①整批化后的现实：单题截图一次整批发送，逐题独立回填，轮询逐轮写路由。"""

    async def test_single_question_screenshots_not_the_whole_pdf(self) -> None:
        items = [item("p_mineru%02d" % index, broken_doc("dropped_var"))
                 for index in range(3)]
        saved: list[dict] = []
        seen_files: list[tuple[str, bytes]] = []
        seen_wait: list[float] = []
        route_notes: list[str] = []

        def fake_extract_batch(files, base_url, token, **kwargs):
            seen_files.extend(files)
            seen_wait.append(kwargs.get("wait"))
            kwargs["on_progress"](1, 3)
            kwargs["on_progress"](3, 3)
            return [{"ok": True, "markdown": "1. 求 $x+1=2$ 的解。", "detail": "ok"}
                    for _ in files]

        def capture_route(_service, _batch_id, snapshot):
            route_notes.append(str(snapshot.get("note") or ""))

        with mock.patch.object(service, "list_batch_questions",
                               return_value={"items": items}), \
                mock.patch.object(service, "save_draft",
                                  side_effect=lambda rows, **kwargs: saved.extend(rows)), \
                mock.patch.object(recognize_mineru.recognize_shared, "item_image_bytes",
                                  side_effect=lambda _item: b"\x89PNG-question"), \
                mock.patch.object(ai_center, "find_mineru",
                                  return_value=binding("mineru")), \
                mock.patch.object(recognize_mineru.mineru_extract, "extract_batch",
                                  side_effect=fake_extract_batch) as extract_batch, \
                mock.patch.object(recognize_mineru.mineru_extract, "extract") as extract, \
                mock.patch.object(ingest_route, "save_route",
                                  side_effect=capture_route) as save_route:
            with self.assertLogs("app.core.ingest.recognize.mineru",
                                 level="INFO") as captured:
                route = await ingest_route.fill_scan_batch(
                    "B-002", "mineru",
                    {"has_text_layer": False, "garbled": False})

        extract_batch.assert_called_once()
        extract.assert_not_called()
        self.assertEqual(seen_files, [
            ("第1题.png", b"\x89PNG-question"),
            ("第2题.png", b"\x89PNG-question"),
            ("第3题.png", b"\x89PNG-question"),
        ], "发的是单题截图且一次整批，绝不是整卷 PDF")
        self.assertEqual(seen_wait, [900.0],
                         "MinerU 等待时限必须放宽到 900 秒")
        self.assertEqual(len(saved), 3, "每道题独立回填，互不干扰")
        self.assertEqual([row["pending_id"] for row in saved],
                         ["p_mineru00", "p_mineru01", "p_mineru02"])
        for row in saved:
            self.assertIn("求 $x+1=2$ 的解。", row["question"]["stem"],
                          "云端正文字段替换本地坏题干")
            self.assertEqual(row["question"]["images"][0]["uri"],
                             "/static/pending/" + row["pending_id"] + ".png",
                             "题图仍认本地这一道，不许串题")
        self.assertEqual(save_route.call_count, 3,
                         "整批发送 1 次＋两轮轮询各 1 次写回批次路由")
        self.assertIn("整批发送", route_notes[0])
        self.assertIn("已回 1/3 题", route_notes[1])
        self.assertIn("已回 3/3 题", route_notes[2])
        self.assertFalse(any("没成功" in note for note in route_notes),
                         "全部成功时不留失败 note")
        batch_lines = [line for line in captured.output if "整批发送" in line]
        self.assertEqual(len(batch_lines), 1)
        self.assertIn("已将 3 题单题截图整批发送至 MinerU 云端解析...", batch_lines[0])
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
        self.assertEqual(col.count("<option"), 2,
                         "静态只留「自动」；就绪条目由宿主 registry 动态注入")
        self.assertIn('<option value="auto"', col)
        self.assertGreaterEqual(col.count("title="), 2,
                                "每个下拉选项都要有原生 title 提示")
        # 单源 registry：配置页取清单灌下拉，ui_intake 不再硬编码引擎名单。
        config_js = (PLUGIN_DIR / "dist" / "ui_model_config.js").read_text(encoding="utf-8")
        self.assertIn('hostCall("models.registry_status"', config_js)
        self.assertIn("applyEngines(entries, defaults)", config_js)
        self.assertIn("function applyRegistry(", INTAKE_JS)
        self.assertIn('entry.state !== "ready"', INTAKE_JS)
        self.assertIn("entry.enabled === false", INTAKE_JS)
        # 四合一：一键装＋勾选代笔＋大白话说明都走宿主 relay，插件不自落状态。
        # 2.20.0 卡§1 拆兄弟模块：安装链住 ui_model_install.js（kind 泛化），
        # 大白话说明住 ui_model_table.js；契约意图不变，只认调用形状。
        install_js = (PLUGIN_DIR / "dist" / "ui_model_install.js").read_text(encoding="utf-8")
        table_js = (PLUGIN_DIR / "dist" / "ui_model_table.js").read_text(encoding="utf-8")
        self.assertIn('hostCall("models." + kind + "_install"', install_js)
        self.assertIn('hostCall("models.prefs_save"', config_js)
        self.assertIn("summary_usage", table_js)
        self.assertIn("defs.layout", INTAKE_JS)
        self.assertNotIn("LAYOUT_ENGINES", INTAKE_JS)
        self.assertNotIn("RECOGNIZE_ENGINES", INTAKE_JS)
        # 可整块下架：模块不在时 plugin.js 落 null，不许写死 create。
        plugin_js = (PLUGIN_DIR / "dist" / "plugin.js").read_text(encoding="utf-8")
        self.assertIn("window.JzoEditorModelConfig ?", plugin_js)
        # 宿主两道转发（relay＋intake）也不许二次白名单：名单单源后端 normalize_engine，
        # 否则新引擎名（rapidocr_fast/cloud_vision）会被半路碾回 auto（2026-11-18 实测踩坑）。
        for name in ("stage_relay_bank.js", "intake.js"):
            host_js = (ROOT / "static" / "js" / name).read_text(encoding="utf-8")
            self.assertNotIn('"auto", "yolo", "cloud"', host_js, name)
            self.assertNotIn('"auto", "full_ocr", "mineru"', host_js, name)

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
