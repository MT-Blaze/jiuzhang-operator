# -*- coding: utf-8 -*-
"""终极军令 任务一/任务三的前端契约：配置中心、单题/批量识别与人机共驾的边界。

这批判据钉四件事：
1. 入口与弹窗住在对的那一帧：双栏配置窗必须回画布（辅助栏只有 300px 宽），
   辅助栏只放【API 配置】与【✨ 批量 AI 识别全卷】两颗入口；
2. Key 只进不出：回读一律 api_key_masked，插件不碰 localStorage、不直连 fetch；
3. 方案 A：AI 只回结构化正文 + 底座套好的源码，插件整题换 source，不自己拼环境；
4. 覆盖机制：有人工修改先问，批量识别经既有 editor.batch_review 主题发令，
   失败只亮红点 + 报错诊断，绝不弹窗打断。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ai_copilot_contract``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.core import manifests
from tests.core_sources import plugin_bundle, stage_source

ROOT = Path(__file__).resolve().parents[1]
from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
PLUGIN_DIR = PLUGIN_SOURCE_DIR / "org.jiuzhang.editor"
HTML = (PLUGIN_DIR / "dist" / "index.html").read_text(encoding="utf-8")
JS = plugin_bundle("org.jiuzhang.editor")
CSS = plugin_bundle("org.jiuzhang.editor", "link")
STAGE_JS = stage_source()


def canvas_only(html: str) -> str:
    return html[html.index('id="edRoot"'):html.index('id="epRoot"')]


def panel_only(html: str) -> str:
    start = html.index('id="epRoot"')
    return html[start:html.index("<script", start)]


def manifest() -> dict:
    return manifests.load_manifest(PLUGIN_DIR)


class HostRelayTest(unittest.TestCase):
    """六条 ai.* 方法必须在白名单里，且写操作全由宿主代持令牌。"""

    METHODS = (
        "ai.center", "ai.account_save", "ai.account_delete",
        "ai.assign", "ai.models", "ai.recognize",
    )

    def test_01_every_method_is_whitelisted(self) -> None:
        block = re.search(r"var RELAY_METHODS = \[(.*?)\];", STAGE_JS, re.S).group(1)
        listed = set(re.findall(r'"([^"]+)"', block))
        for method in self.METHODS:
            self.assertIn(method, listed, f"{method} 不在宿主白名单里，插件一调就被拒")

    def test_02_every_method_has_a_branch(self) -> None:
        for method in self.METHODS:
            self.assertIn(f'if (method === "{method}")', STAGE_JS,
                          f"{method} 没写分支，请求会掉到末尾的 UNSUPPORTED_METHOD")

    def test_03_urls_and_write_token(self) -> None:
        for url in ("/api/ai-center", "/api/ai-center/accounts",
                    "/api/ai-center/assign", "/api/ai-center/models",
                    "/api/ai-center/recognize"):
            self.assertIn(url, STAGE_JS)
        start = STAGE_JS.index('if (method === "ai.center")')
        block = STAGE_JS[start:]
        # 五个写/出网口子全走宿主代取的一次性令牌；读口子不必带。
        self.assertGreaterEqual(block.count("withWriteToken("), 5,
                                "保存账号、删除、指派、拉模型、识别都要宿主代持写令牌")

    def test_04_recognize_waits_longer_than_the_base_budget(self) -> None:
        self.assertIn("AI_RECOGNIZE_TIMEOUT_MS = 125000", STAGE_JS,
                      "视觉模型一轮可能几十秒，别按 20 秒的默认预算截断")

    def test_05_solve_does_not_require_an_image(self) -> None:
        self.assertIn('=== "solve" ? "solve" : "ocr"', STAGE_JS)
        self.assertIn('if (aiTask === "ocr" && !images.length)', STAGE_JS,
                      "只有 ocr 强制题图；解析走题干，不该被题图卡住")
        self.assertIn("task: aiTask", STAGE_JS)


class ConfigCenterMarkupTest(unittest.TestCase):
    """双栏配置窗住画布，辅助栏只留两颗入口。"""

    def test_01_dual_column_modal_lives_in_the_canvas(self) -> None:
        canvas = canvas_only(HTML)
        self.assertIn('id="epAiConfigModal"', canvas, "双栏窗必须住画布：辅助栏只有 300px")
        self.assertNotIn('id="epAiConfigModal"', panel_only(HTML))
        self.assertIn('class="ep-ai-cols"', canvas)
        self.assertIn('class="ep-ai-col"', canvas)
        for node_id in ("epAiPoolList", "epAiAssignList", "epAiName", "epAiBase", "epAiKey"):
            self.assertIn(f'id="{node_id}"', canvas, f"配置窗缺节点 {node_id}")

    def test_02_panel_keeps_only_the_two_entry_buttons(self) -> None:
        panel = panel_only(HTML)
        self.assertIn('id="epAiConfig"', panel)
        self.assertIn('id="epAiBatch"', panel)
        self.assertIn("✨ 批量 AI 识别全卷", panel)
        self.assertIn('id="epAiBatchNote"', panel, "批量识别的进度只在辅助栏这一行报")
        self.assertIn('id="epHeadTools"', panel[:panel.index('id="epAiConfig"')])

    def test_02b_batch_list_has_its_own_config_entry(self) -> None:
        """任务二的入口在批次列表右上角：一进画布就能配，不必先开一道题。"""
        canvas = canvas_only(HTML)
        head = canvas[canvas.index('class="ed-batches-head"'):]
        head = head[:head.index("</div>", head.index("</button>"))]
        self.assertIn('id="epAiConfigList"', head)
        self.assertIn("API 配置", head)
        js = (PLUGIN_DIR / "dist" / "ui_ai_copilot.js").read_text(encoding="utf-8")
        self.assertIn('getElementById("epAiConfigList")', js)

    def test_03_overwrite_modal_is_in_the_canvas_and_registered(self) -> None:
        self.assertIn('id="epAiOverwriteModal"', canvas_only(HTML))
        self.assertNotIn('id="epAiOverwriteModal"', panel_only(HTML))
        modal = (PLUGIN_DIR / "dist" / "ui_modal.js").read_text(encoding="utf-8")
        for name in ("aiConfigModalEl", "aiOverwriteModalEl"):
            self.assertIn(name, modal, f"{name} 没进焦点圈/ Esc 收口名单")

    def test_04_dual_columns_are_real_grid_columns(self) -> None:
        self.assertIn(".ep-ai-cols", CSS)
        block = CSS[CSS.index(".ep-ai-cols"):]
        self.assertIn("grid-template-columns", block[:block.index("}")])
        self.assertIn("minmax(0, 1fr) minmax(0, 1.1fr)", block[:block.index("}")])

    def test_05_account_form_starts_collapsed(self) -> None:
        """新增表单默认收起：点【+ 新增接口】才铺开，存完自动清空收起。"""
        canvas = canvas_only(HTML)
        self.assertIn('id="epAiNewAccount"', canvas)
        self.assertIn('aria-controls="epAiAccountForm"', canvas)
        form = canvas[canvas.index('id="epAiAccountForm"'):]
        self.assertIn("hidden", form[:form.index(">")], "表单必须默认 hidden")
        self.assertIn(".ep-ai-form[hidden]", CSS, "display:flex 会压过 [hidden]，得显式收口")
        self.assertIn("function setAccountFormOpen(", JS)
        self.assertIn('bindSwitcher("epAiAccountForm", "epAiNewAccount"', JS)
        start = JS.index("function saveAccount(")
        block = JS[start:JS.index("function openConfig(", start)]
        self.assertIn("resetAccountForm(true)", block, "保存成功后要清空并收起表单")
        pool = CSS[CSS.index(".ep-ai-pool,"):]
        pool = pool[:pool.index("}")]
        self.assertNotIn("overflow-y", pool, "密钥池内层不再套滚动条")
        self.assertNotIn("max-height", pool)
        self.assertIn("width: min(900px, 100%)", CSS)


class MaskAndSandboxTest(unittest.TestCase):
    """Key 只进不出：回读只有掩码，插件不碰存储、不直连网络。"""

    def test_01_keys_are_never_rendered_raw(self) -> None:
        # 密钥池改成单行列表后只显示名称，连掩码都不再上屏。
        self.assertNotIn("api_key_masked", JS, "密钥池只显示名称，掩码也不上屏")
        # 老师刚敲进框里的 Key 只能随着保存请求一次性交给宿主，读回来的对象永远只有掩码。
        for line in JS.splitlines():
            if re.search(r"\.api_key(?!_masked)[\s,;)\]]", line):
                self.assertIn("payload.api_key", line, f"Key 只许上行、不许回读：{line.strip()}")
        self.assertIn('type="password"', canvas_only(HTML), "输入 Key 时也不该明文铺在屏上")

    def test_02_no_storage_or_direct_network(self) -> None:
        for token in ("localStorage", "sessionStorage", "XMLHttpRequest"):
            self.assertNotIn(token, JS, f"沙箱插件不许碰 {token}")
        self.assertNotIn("fetch(", JS, "插件只能经宿主 Host API 出网")

    def test_03_no_lookbehind_regex(self) -> None:
        self.assertIsNone(re.search(r"\(\?<[=!]", JS), "AGENTS §6：后行断言会打挂旧浏览器")

    def test_04_plugin_keeps_the_ai_grant(self) -> None:
        self.assertIn("ai:invoke", manifest()["permissions"])


class PoolRowContractTest(unittest.TestCase):
    """密钥池 = 单行列表：名称占左，三颗图标钮贴右，连通性原地走状态机。"""

    def test_01_row_hides_base_url_and_key(self) -> None:
        for legacy in ("ep-ai-acc-meta", "ep-ai-acc-key", "ep-ai-acc-head"):
            self.assertNotIn(legacy, JS, f"单行列表不该再渲染 {legacy}")

    def test_02_row_is_one_flex_line(self) -> None:
        block = CSS[CSS.index(".ep-ai-acc {"):]
        block = block[:block.index("}")]
        self.assertIn("display: flex", block)
        self.assertIn("align-items: center", block)
        self.assertNotIn("flex-direction: column", block)

    def test_03_test_icon_has_four_states(self) -> None:
        self.assertIn("function paintTestButton(", JS)
        for state in ('"idle"', '"busy"', '"ok"', '"fail"'):
            self.assertIn(state, JS[JS.index("function paintTestButton("):], f"缺状态 {state}")
        self.assertIn('"连接正常"', JS, "成功态必须带连接正常提示")
        self.assertIn('"连接失败："', JS, "失败态悬停要能看原因")
        self.assertIn(".ep-ai-test[data-state=\"busy\"]", CSS, "测试中要有旋转动画")
        self.assertIn("@keyframes ep-ai-spin", CSS)

    def test_04_saving_auto_tests_the_row(self) -> None:
        start = JS.index("function saveAccount(")
        block = JS[start:JS.index("function openConfig(", start)]
        self.assertIn("testAccount(savedId)", block, "保存后要立刻在原行验证连通性")


class SchemeATest(unittest.TestCase):
    """方案 A：底座套环境，插件只负责整题换上。"""

    def test_01_result_source_is_applied_verbatim(self) -> None:
        start = JS.index("function applyResult(index, result)")
        block = JS[start: start + 900]
        self.assertIn("result && result.source", block)
        self.assertIn("item.aiSource = source;", block)
        self.assertNotIn("\\begin{question}", block, "插件不许自己拼环境骨架")

    def test_02_human_edits_are_detected(self) -> None:
        start = JS.index("function hasHumanEdits(item)")
        block = JS[start: start + 400]
        self.assertIn("item.source !== item.aiSource", block)
        self.assertIn("item.dirty === true", block)

    def test_03_single_buttons_sit_at_the_meta_strip(self) -> None:
        strip = (PLUGIN_DIR / "dist" / "ui_meta_strip.js").read_text(encoding="utf-8")
        self.assertIn('"AI识题"', strip)
        self.assertIn('"AI解析"', strip, "任务三要求识别与解析两颗单题钮")
        self.assertNotIn("✨", strip, "两颗钮不再带图标，文案精简到四字")
        self.assertIn('"ocr"', strip)
        self.assertIn('"solve"', strip)
        self.assertIn("data-mode", strip)
        self.assertIn("onAiIdentify", strip)
        self.assertIn("metaStrip.render", JS, "只读条仍是渲染入口")

    def test_04_batch_and_config_ride_the_existing_topic(self) -> None:
        protocol = (PLUGIN_DIR / "dist" / "core_protocol.js").read_text(encoding="utf-8")
        self.assertIn('reviewPayload.action === "ai_config"', protocol)
        self.assertIn('reviewPayload.action === "ai_batch"', protocol)
        self.assertIn('reviewPayload.action === "ai_batch_solve"', protocol,
                      "批量解析要有自己的发令分支")
        bus = manifest()["bus"]
        self.assertIn("editor.batch_review", bus["publish"])
        self.assertIn("editor.batch_review", bus["subscribe"])

    def test_05_both_batch_buttons_live_in_the_panel(self) -> None:
        panel = panel_only(HTML)
        self.assertIn('id="epAiBatch"', panel)
        self.assertIn('id="epAiBatchSolve"', panel)
        self.assertIn("✨ 批量 AI 识别全卷", panel)
        self.assertIn("✨ 批量解析全卷", panel)
        self.assertIn("runBatchSolve", JS)


class SilentSaveTest(unittest.TestCase):
    """识别/解析成功后直接静默存入待审池，不让老师再点一次【存为待审】。"""

    def test_01_success_writes_pending_pool(self) -> None:
        self.assertIn("function stashQuietly(index)", JS)
        self.assertIn('hostCall("pending.save_draft"', JS)
        self.assertIn("documentFor(item, metaFor(item))", JS)

    def test_02_no_manual_step_left_in_the_success_path(self) -> None:
        start = JS.index("function runSingle(")
        block = JS[start:start + 1800]
        self.assertIn("return stashQuietly(index)", block)
        self.assertIn("已存入待审", block)

    def test_03_batch_also_stashes_each_item(self) -> None:
        start = JS.index("function startBatch(")
        block = JS[start:start + 2200]
        self.assertIn("return stashQuietly(index)", block)
        self.assertIn("批量 AI ", block, "批量完成只弹总气泡")


class ToastContractTest(unittest.TestCase):
    """右下角气泡：成功 3s、失败 8s、悬停暂停、不可点击。"""

    def test_01_durations(self) -> None:
        host = (PLUGIN_DIR / "dist" / "core_host.js").read_text(encoding="utf-8")
        self.assertIn("TOAST_OK_MS = 3000", host)
        self.assertIn("TOAST_ERROR_MS = 8000", host)
        self.assertIn('toastEl.addEventListener("mouseenter"', host)
        self.assertIn('toastEl.addEventListener("mouseleave"', host)

    def test_02_bottom_right_and_not_clickable(self) -> None:
        css = CSS
        block = css[css.index(".ed-toast {"):]
        block = block[:block.index("}")]
        self.assertIn("right: 22px", block)
        self.assertIn("bottom: 22px", block)
        self.assertNotIn("left: 50%", block)
        html = canvas_only(HTML)
        start = html.index('id="edToast"')
        tag = html[html.rindex("<", 0, start):html.index(">", start)]
        self.assertNotIn("onclick", tag)
        self.assertNotIn("<a ", tag)

    def test_03_batch_fires_exactly_one_total_toast(self) -> None:
        start = JS.index("function startBatch(")
        block = JS[start:JS.index("function runBatch(", start)]
        self.assertEqual(block.count("toast("), 1, "批量只许弹一枚总气泡")


class FailurePolicyTest(unittest.TestCase):
    """API 报错只亮红点 + 报错诊断，绝不弹窗打断。"""

    def test_01_error_marks_the_button_instead_of_dialog(self) -> None:
        self.assertIn('button.setAttribute("data-error", "true")', JS)
        self.assertIn("dockWarn(", JS)
        self.assertIn('data-error="true"]::after', CSS, "红点必须是纯样式，不靠额外浮层")

    def test_02_batch_progress_is_reported_back_to_the_panel(self) -> None:
        self.assertIn("onBatchReport", JS)
        self.assertIn('phase: "progress"', JS)
        self.assertIn('phase: "done"', JS)
        self.assertIn("payload.applied", JS)

    def test_03_route_hint_from_the_base_is_surfaced(self) -> None:
        batches = (PLUGIN_DIR / "dist" / "ui_batches.js").read_text(encoding="utf-8")
        self.assertIn("state.route = (result && result.route", batches)
        self.assertIn("解析路由：", batches, "乱码/扫描件提示要照实转达，绝不自动调 AI")


if __name__ == "__main__":
    unittest.main()
