# -*- coding: utf-8 -*-
"""默认引擎记上次＋识别下拉分组＋全组合（记上次卡）的插件 JS 结构契约。

本模块按仓库既有「JS 单测」口径＝读插件源码钉结构契约（同 test_ingest_triage
EngineUiContractTest / test_editor_contract）；行为的真证由 Playwright 隔离副本
探针 tools/last_used_engine_probe.py 走真人路径给出（§4 八项）。这里钉的是产生
那些行为的代码形状，逐条对应卡 §3：

1. 配置页：②手动默认行整砍（renderDefaults 函数＋调用点＋「默认引擎」标签串都不在）；
   ①保留并改名「自动设置（…括号解释保留…）」；置顶组 class 不动（探针置顶判据依赖）。
2. 记上次回写：只在 bindSelect 的显式 change 里走 models.prefs_save 回写
   default_layout/default_recognize（复用既有键，不新增键）；失败显性 dockWarn 不阻塞；
   加载期 applyRegistry 兜底归 auto **不回写**（卸座不擦记忆）。
3. 读口不动：applyRegistry 仍按 defs.layout/defs.recognize 注入初值、未就绪归 auto。
4. 识别下拉自动单独置顶，其余按禁用表头「—— 整题OCR ——／—— 文字直取＋公式 ——」
   全平铺（不建 optgroup）；版面下拉保持扁平；纯图卷筐 combo 置灰＋人话保留；
   某组为空＝不出该表头行。
5. 全组合：catalog 增 combo_pp_l/combo_p2t，weight_present＋store 与公式座同档
   （就绪随座，零 registry/router 代码改），combo_seat/plan_recognize/capability 齐；
   本地 VLM 组合拆三条（千问/书生/面壁），各自随本座就绪。

运行：``.venv/Scripts/python.exe -m unittest tests.test_last_used_engine``
"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.core.config import plugin_source_root

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
PLUGIN_DIR = PLUGIN_SOURCE_DIR / "org.jiuzhang.editor"
INTAKE_JS = (PLUGIN_DIR / "dist" / "ui_intake.js").read_text(encoding="utf-8")
CONFIG_JS = (PLUGIN_DIR / "dist" / "ui_model_config.js").read_text(encoding="utf-8")
HTML = (PLUGIN_DIR / "dist" / "index.html").read_text(encoding="utf-8")
CATALOG = (PLUGIN_DIR / "catalog.toml").read_text(encoding="utf-8")


def region(text: str, start: str, end: str) -> str:
    """取 [start, end) 之间的源码段；找不到端点直接判失败，不静默吞。"""
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[i:j]


class ConfigPageDefaultsTest(unittest.TestCase):
    """②手动默认行整砍、①改名自动设置（卡 §2.2/§2.3）。"""

    def test_manual_default_row_is_gone(self) -> None:
        self.assertNotIn("function renderDefaults(", CONFIG_JS)
        self.assertNotIn("renderDefaults()", CONFIG_JS)
        self.assertNotIn("默认引擎", CONFIG_JS)
        self.assertNotIn("default_layout", CONFIG_JS,
                         "配置页不再手设 default_layout（改由画布记上次回写）")
        self.assertNotIn("default_recognize", CONFIG_JS)

    def test_auto_seats_renamed_and_kept(self) -> None:
        self.assertIn("function renderAutoSeats(", CONFIG_JS)
        self.assertIn("自动设置（按卷型分流走哪座；默认座未就绪会显性提示，不偷换）", CONFIG_JS)
        self.assertNotIn("自动分流默认（", CONFIG_JS)
        # 置顶组 class 不动：model_table_probe 的置顶判据靠它定位。
        self.assertIn("ep-model-config-auto-seats", CONFIG_JS)
        self.assertIn('hostCall("models.prefs_save"', CONFIG_JS)
        self.assertIn("auto_image_seat", CONFIG_JS)
        self.assertIn("auto_text_formula_seat", CONFIG_JS)

    def test_render_no_longer_appends_defaults(self) -> None:
        render = region(CONFIG_JS, "function render()", "function refresh(")
        self.assertIn("renderAutoSeats()", render)
        self.assertNotIn("renderDefaults", render)


class LastUsedWriteBackTest(unittest.TestCase):
    """记上次：显式 change 回写 default_*；加载期不回写（卡 §2.1）。"""

    def test_change_handler_writes_prefs(self) -> None:
        wire = region(INTAKE_JS, "function wireEngineSelects()", "function hasFiles(")
        self.assertIn('hostCall("models.prefs_save"', wire)
        self.assertIn('kind === "layout" ? "default_layout" : "default_recognize"', wire)
        # 失败显性 dock，不静默不阻塞解析。
        self.assertIn("dockWarn(", wire)
        self.assertIn("记上次没存住", wire)

    def test_apply_registry_does_not_write_prefs(self) -> None:
        apply_reg = region(INTAKE_JS, "function applyRegistry(", "function fileEntry(")
        self.assertNotIn("prefs_save", apply_reg,
                         "加载期兜底归 auto 绝不回写（卸座不擦记忆）")
        self.assertNotIn("hostCall(", apply_reg)

    def test_read_port_unchanged(self) -> None:
        apply_reg = region(INTAKE_JS, "function applyRegistry(", "function fileEntry(")
        # 初值仍来自 registry defaults（＝上次值），仅 state 未设且在 allowed 才采纳。
        self.assertIn("defs.layout", apply_reg)
        self.assertIn("defs.recognize", apply_reg)
        self.assertIn("!state.ingestLayoutEngine", apply_reg)
        self.assertIn("!state.ingestRecognizeEngine", apply_reg)
        # 未就绪/停用残留值当场归 auto（读口 normalization 不动）。
        self.assertIn('state.ingestLayoutEngine = "auto"', apply_reg)
        self.assertIn('state.ingestRecognizeEngine = "auto"', apply_reg)
        self.assertIn('entry.state !== "ready"', apply_reg)
        self.assertIn("entry.enabled === false", apply_reg)


class RecognizeGroupingTest(unittest.TestCase):
    """自动置顶＋两条禁用表头＋全平铺；版面扁平；纯图卷 combo 灰保留（卡 §2.4）。"""

    def test_flat_with_disabled_headers(self) -> None:
        paint = region(INTAKE_JS, "function paintEngineOptions()", "function applyRegistry(")
        # 识别分支不再建 optgroup，改用禁用 option 当表头。
        self.assertNotIn('document.createElement("optgroup")', paint)
        self.assertIn('groupHead("—— 整题OCR ——")', paint)
        self.assertIn('groupHead("—— 文字直取＋公式 ——")', paint)
        self.assertIn("option.disabled = true", INTAKE_JS)
        # auto 是自动分流，单独置顶，必须排在两条表头之前。
        self.assertLess(paint.index('engineOption("auto", spec[0])'),
                        paint.index('groupHead("—— 整题OCR ——")'))
        self.assertLess(paint.index('engineOption("auto", spec[0])'),
                        paint.index('groupHead("—— 文字直取＋公式 ——")'))
        # 归属仍按 comboIds；auto 显式排除在两组之外。
        self.assertIn('id !== "auto"', paint)
        self.assertIn("comboIds.indexOf(id) >= 0", paint)

    def test_layout_dropdown_stays_flat(self) -> None:
        paint = region(INTAKE_JS, "function paintEngineOptions()", "function applyRegistry(")
        # 分组只发生在 edRecognizeEngine 分支；版面走 else 扁平 append。
        self.assertIn('if (spec[0] === "edRecognizeEngine")', paint)
        self.assertIn("select.appendChild(engineOption(id, spec[0]))", paint)

    def test_empty_group_header_hidden(self) -> None:
        paint = region(INTAKE_JS, "function paintEngineOptions()", "function applyRegistry(")
        self.assertIn("if (whole.length)", paint)
        self.assertIn("if (combos.length)", paint)
        self.assertNotIn("childNodes.length", paint)

    def test_pure_image_combo_disable_preserved(self) -> None:
        helper = region(INTAKE_JS, "function engineOption(", "function paintEngineOptions(")
        self.assertIn("option.disabled = true", helper)
        self.assertIn("只支持文字卷", helper)
        self.assertIn("jzoPureImage", helper)
        paint = region(INTAKE_JS, "function paintEngineOptions()", "function applyRegistry(")
        self.assertIn("识别已回到自动分流", paint)

    def test_static_selects_still_auto_only(self) -> None:
        col = HTML[HTML.index('class="ed-basket-col"'):]
        col = col[:col.index('class="ed-basket"')]
        self.assertIn('id="edLayoutEngine"', col)
        self.assertIn('id="edRecognizeEngine"', col)
        self.assertEqual(col.count("<option"), 2,
                         "静态只留自动；分组与就绪条目由 paintEngineOptions 动态注入")


class FullComboCatalogTest(unittest.TestCase):
    """全组合：combo_pp_l/combo_p2t 随公式座就绪（卡 §2.5，weight_present 偏离登记）。"""

    def test_two_new_combos_present_with_seat(self) -> None:
        for combo_id, seat, store in (("combo_pp_l", "formula_pp_l", "formula_l"),
                                      ("combo_p2t", "formula_p2t", "formula_p2t")):
            with self.subTest(combo=combo_id):
                block = region(CATALOG, 'id = "%s"' % combo_id, "[[entry]]")
                self.assertIn('capability = "recognize"', block)
                self.assertIn('plan_recognize = ["combo"]', block)
                self.assertIn('combo_seat = "%s"' % seat, block)
                self.assertIn('rule = "weight_present"', block)
                self.assertIn('store = "%s"' % store, block)

    def test_new_combo_names_follow_card(self) -> None:
        for name in ("PP-FormulaNet·M", "PP-FormulaNet·L", "Pix2Text·MFR", "Texify"):
            with self.subTest(name=name):
                self.assertIn('name = "%s"' % name, CATALOG)
        self.assertIn('name = "云端 AI OCR"', CATALOG)

    def test_vlm_combo_split_into_three_seats(self) -> None:
        self.assertNotIn('id = "combo_vlm"', CATALOG,
                         "旧的合体 combo_vlm 已拆三座，不得残留")
        for combo_id, seat, name in (
                ("combo_vlm_qwen", "vlm_qwen", "千问 Qwen2.5-VL（本地）"),
                ("combo_vlm_intern", "vlm_intern", "书生 InternVL3-2B（本地）"),
                ("combo_vlm_minicpm", "vlm_minicpm", "面壁 MiniCPM-V-2.6（本地）")):
            with self.subTest(combo=combo_id):
                block = region(CATALOG, 'id = "%s"' % combo_id, "[[entry]]")
                self.assertNotIn("name =", block,
                                 "组合条目名字由座继承（MODEL-NAME-INHERIT-01）")
                seat_block = region(CATALOG, 'id = "%s"' % seat, "[[entry]]")
                self.assertIn('name = "%s"' % name, seat_block)
                self.assertIn('rule = "vlm_local"', block)
                self.assertIn('combo_seat = "%s"' % seat, block)
                self.assertIn('plan_recognize = ["combo"]', block)
                self.assertIn("文字层取", block)
                self.assertIn("纯图卷", block)

    def test_combo_pp_m_untouched(self) -> None:
        # 转正（COMBO-PPM-READY-01）：import_probe「能导入就恒绿」已修，
        # combo_pp_m 与公式座 PP-M 同口径，就绪真跟权重走。
        block = region(CATALOG, 'id = "combo_pp_m"', 'id = "combo_pp_l"')
        self.assertIn('rule = "weight_present"', block)
        self.assertIn('store = "formula"', block)
        self.assertNotIn("probe =", block)
        self.assertIn('combo_seat = "formula_pp_m"', block)

    def test_texify_combo_prebuilt_with_seat(self) -> None:
        # 旧「不预建」已被卡④（editor 2.25.0）真值取代，随插件仓转正。
        block = region(CATALOG, 'id = "combo_texify"', "[[entry]]")
        self.assertIn('rule = "weight_present"', block)
        self.assertIn('store = "formula_texify"', block)
        self.assertIn('combo_seat = "formula_texify"', block)


if __name__ == "__main__":
    unittest.main()