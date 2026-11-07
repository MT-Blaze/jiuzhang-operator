"""脏 LaTeX 清洗端点与宿主通道契约：军令 #21 任务四。

钉三件事：
1. ``/api/agent/clean_latex`` 是确定性规则：同一段输入永远得到同一段输出，不碰模型；
2. 宿主 ``text.clean_latex`` 通道不截断长文本（半截文本回填比失败更糟），
   也不是 AI 专属方法——录题插件不需要声明 ai:invoke 就能用；
3. 录题端的【清洗当前题 LaTeX】按钮必须真的走这条通道，而不是再抄一份规则；
   军令 #31 · 4.3 起再加一条：清洗只出**预览**，老师逐段点【采用替换】才允许回填，
   两条新通道（``editor.clean_review`` / ``editor.clean_review_state``）必须在
   宿主两张白名单与 ``core_bus`` 里同时活着——清单写了、通道没建等于没声明。

运行：``.venv/Scripts/python.exe -m unittest tests.test_clean_latex``
"""

from __future__ import annotations

import asyncio
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.api.agents import CleanLatexRequest, agent_clean_latex
from app.core import manifests, plugins, toml_io
from tests.core_sources import plugin_bundle, stage_source  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STAGE_JS = stage_source()
EDITOR_DIR = ROOT / "plugins" / "org.jiuzhang.editor"
EDITOR_JS = plugin_bundle("org.jiuzhang.editor")
EDITOR_HTML = (EDITOR_DIR / "dist" / "index.html").read_text(encoding="utf-8")


class CleanLatexRouteTest(unittest.TestCase):
    def test_01_returns_cleaned_text_and_rules(self) -> None:
        result = asyncio.run(agent_clean_latex(CleanLatexRequest(
            text=r"求 \(x\)，并化简 \[y=\dfrac{1}{2}\]，填 \fillin", task_id="t1"
        )))
        self.assertEqual(result["type"], "complete")
        self.assertEqual(result["task_id"], "t1")
        self.assertFalse(result["mock"])
        self.assertEqual(result["data"]["text"], r"求 $x$，并化简 $$y=\frac{1}{2}$$，填 ＿＿＿＿")
        self.assertTrue(result["data"]["changed"])
        self.assertIn("delimiters", result["data"]["rules"])

    def test_02_choices_come_back_as_structured_options(self) -> None:
        result = asyncio.run(agent_clean_latex(CleanLatexRequest(
            text="选一个\n\\begin{choices}\n\\item $(1)$\n\\item 2\n\\end{choices}"
        )))
        self.assertEqual(result["data"]["text"], "选一个")
        self.assertEqual(
            result["data"]["options"],
            [{"key": "A", "content": "$(1)$"}, {"key": "B", "content": "2"}],
        )

    def test_03_is_deterministic_and_does_not_touch_models(self) -> None:
        body = CleanLatexRequest(text=r"\textbf{甲} \(x\)")
        first = asyncio.run(agent_clean_latex(body))["data"]
        second = asyncio.run(agent_clean_latex(body))["data"]
        self.assertEqual(first, second)
        self.assertEqual(first["text"], "**甲** $x$")

    def test_04_rejects_absurdly_long_text(self) -> None:
        with self.assertRaises(ValidationError):
            CleanLatexRequest(text="x" * 20001)


class CleanLatexRelayContractTest(unittest.TestCase):
    def test_01_relay_method_is_open_to_all_plugins(self) -> None:
        self.assertIn('"text.clean_latex"', STAGE_JS, "宿主未开放 text.clean_latex")
        allowed = STAGE_JS.split("var RELAY_METHODS = [", 1)[1].split("];", 1)[0]
        self.assertIn('"text.clean_latex"', allowed, "必须进方法白名单")
        ai_only = STAGE_JS.split("var AI_ONLY_METHODS = [", 1)[1].split("];", 1)[0]
        self.assertNotIn("text.clean_latex", ai_only, "规则清洗不是 AI 专属能力")

    def test_02_relay_posts_to_the_endpoint_and_rejects_oversize(self) -> None:
        block = STAGE_JS.split('if (method === "text.clean_latex") {', 1)[1].split("\n    }", 1)[0]
        self.assertIn('fetchJson("/api/agent/clean_latex"', block)
        self.assertIn("CLEAN_TEXT_MAX", block)
        self.assertIn("文本过长", block)
        self.assertNotIn("dirtyText.slice", block, "超长必须拒，绝不能截断后回填")
        self.assertIn("typeof data.text !== \"string\"", block)


class EditorAiCleanerTest(unittest.TestCase):
    """军令 #23 阶段 3 + 军令 #31 · 4.3：【清洗当前题 LaTeX】住辅助栏，走宿主 text.clean_latex。

    钉四件事：按钮在辅助栏（不在画布）、真的调宿主通道而不是再抄一份规则、
    题干段与解析段**全部成功才出预览**（4.3：预览不等于回填）、
    请求中按钮标 aria-busy（AGENTS §6）。
    """

    @staticmethod
    def cleaner_block() -> str:
        return EDITOR_JS.split("function cleanViaHost() {", 1)[1].split("\n  }\n", 1)[0]

    def test_01_button_lives_in_the_panel_and_uses_the_host_channel(self) -> None:
        panel_html = EDITOR_HTML.split('id="epRoot"', 1)[1]
        self.assertIn('id="epAiClean"', panel_html, "清洗按钮必须在辅助栏")
        self.assertNotIn('id="edAiClean"', EDITOR_HTML, "画布不再放 AI 清洗按钮")
        self.assertIn('getElementById("epAiClean")', EDITOR_JS)
        self.assertIn('hostCall("text.clean_latex"', EDITOR_JS)
        self.assertIn("function cleanViaHost", EDITOR_JS)
        self.assertIn('panelAiCleanEl.addEventListener("click", cleanViaHost)', EDITOR_JS)

    def test_02_cleaning_stops_at_the_preview_and_never_self_applies(self) -> None:
        """4.3 防呆：清洗只出预览。老师没点【采用替换】，中栏源码一个字节都不许动。"""
        block = self.cleaner_block()
        self.assertIn("Promise.all(", block, "必须全部成功后才出预览")
        self.assertIn('"stem", "solution"', block, "两段一起清洗，不逐段边洗边写")
        self.assertIn("panel.ai.busy = false", block)
        self.assertNotIn("editor.apply_patch", block,
                         "预览阶段不许回填——这条断言就是 4.3 的全部意义")
        self.assertIn("publishClean(true)", block, "对照只经 editor.clean_review 投给画布")
        self.assertIn("源码保持原样", block, "任一失败要如实说不许动")
        self.assertNotIn("fetch(", block)
        self.assertNotIn("/api/", block)

    def test_02b_apply_patch_only_lives_in_the_adopt_handler(self) -> None:
        """回填的唯一出口是「采用替换」；「放弃」只改本地态，一颗补丁都不发。"""
        def body(name: str) -> str:
            start = EDITOR_JS.index("function %s(" % name)
            return EDITOR_JS[start:EDITOR_JS.index("\n  function ", start + 1)]

        self.assertIn('hostCall("editor.apply_patch"', body("onCleanApply"))
        self.assertNotIn("editor.apply_patch", body("onCleanDrop"),
                         "放弃只撤预览，不许发补丁")

    def test_03_busy_state_marks_the_buttons(self) -> None:
        """清洗/改写进行中：三个动作按钮必须同步 aria-busy，不许只靠变灰的颜色传达。"""
        block = EDITOR_JS.split("function renderAi() {", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn('node.setAttribute("aria-busy", "true")', block)
        self.assertIn('node.removeAttribute("aria-busy")', block)
        self.assertIn("panelAiSendEl, panelAiCleanEl, panelAiApplyEl", block)

    def test_04_manifest_and_index_agree(self) -> None:
        """清单与官方索引的版本号、描述必须逐字相同——不写死数字，插件一升号就假红。"""
        manifest = manifests.load_manifest(EDITOR_DIR)
        index = toml_io.load(ROOT / "plugins.toml", {})
        entries = [item for item in index["entries"] if item["id"] == "org.jiuzhang.editor"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["version"], manifest["version"])
        self.assertEqual(entries[0]["description"], manifest["description"])

    def test_05_host_grants_both_clean_review_channels(self) -> None:
        """清单声明了就得真通：Python 白名单与 core_bus 发布白名单都要认这两条。

        2026-11-02 实跑抓到的漏：插件清单与 dist 代码都写好了 editor.clean_review，
        但 ``app/core/plugins.py`` 的两张白名单没加——``_normalize_bus`` 会静默丢弃，
        「清单写着、通道不存在」正是 bus_parity 判据要拦的那类暗通道。
        """
        core_bus = (ROOT / "static" / "js" / "core_bus.js").read_text(encoding="utf-8")
        manifest = manifests.load_manifest(EDITOR_DIR)
        declared = manifest["bus"]["subscribe"]
        for topic in ("editor.clean_review", "editor.clean_review_state"):
            self.assertIn(topic, declared, "清单没声明订阅，宿主不会投递")
            self.assertIn(topic, plugins._BUS_SUBSCRIBE, "Python 侧入站白名单缺这条")
            self.assertIn(topic, plugins._BUS_PUBLISH, "Python 侧出站白名单缺这条")
            self.assertIn('"%s"' % topic, core_bus, "core_bus 发布白名单缺这条")
        info = plugins._normalize_bus({"subscribe": declared, "publish": ["region.dock"]})
        self.assertEqual(sorted(info["subscribe"]), sorted(declared), "有订阅被静默丢弃")
        self.assertLessEqual(len(declared), plugins._BUS_MAX_TOPICS,
                             "订阅数顶到上限会被截断，上限该跟着真需求一起抬")

    def test_06_absent_canvas_degrades_clean_review_and_locks_adopt(self) -> None:
        """4.3 降级契约（Eval-06 补项 B）：画布不在场时两条路都降级，四个按钮全锁死。

        防的真实回归：删掉 ``armCleanTimeout`` 的超时兜底（画布永远不回执时按钮悬空可点）、
        删掉 ``onCleanState`` 的 ``tab_not_live`` 分支（收到宿主降级信号却仍保持可替换）、
        或把 ``degraded`` 从按钮涂装 / 【采用】入口 / 摘要文案里摘掉（降级只停留在变量上，
        老师仍按得到必然落空的按钮）——这些改动都必须把本用例打红。
        """
        def body(name: str) -> str:
            start = EDITOR_JS.index("function %s(" % name)
            return EDITOR_JS[start:EDITOR_JS.index("\n  function ", start + 1)]

        self.assertRegex(EDITOR_JS, r"var CLEAN_OPEN_TIMEOUT_MS = \d+;",
                         "阈值只能是具名常量：改名、删声明或把数字写死回调用点都红")
        arm = body("armCleanTimeout")
        self.assertRegex(arm, r"setTimeout\([\s\S]{0,800}?CLEAN_OPEN_TIMEOUT_MS\s*\);",
                         "超时降级靠这个定时器引用这个常量：删定时器、断开引用或\n"
                         "        换成写死数字都要红（阈值数值本身不再钉死，口径同 test_04）")
        self.assertIn("panel.clean.degraded = true", arm)
        self.assertIn('panelSay("画布未打开，无法替换：已降级为纯摘要。", "warn", "clean_degraded")', arm)

        not_live = body("onCleanState")
        not_live = not_live[not_live.index('phase === "tab_not_live"'):]
        self.assertIn("clearCleanTimer()", not_live, "收到回投就当场降级，不再干等定时器")
        self.assertIn("clean.degraded = true", not_live)
        self.assertIn('clean.reason = "tab_not_live"', not_live)
        self.assertIn('panelSay("画布未打开，无法替换：已降级为纯摘要。", "warn", "clean_degraded")', not_live)

        paint = body("paintCleanButtons")
        self.assertIn("var locked = Boolean(clean && clean.degraded);", paint)
        self.assertIn("applyEl.disabled = !visible || locked || hasOptions;", paint)
        self.assertIn("dropEl.disabled = !visible || locked;", paint, "降级时【放弃】也不许按")

        self.assertIn("clean.degraded) return Promise.resolve(null)", body("onCleanApply"),
                      "降级态哪怕被点到也不许发 editor.apply_patch 补丁")
        self.assertIn('if (clean.degraded) lines.push("画布未打开，无法替换：只保留摘要，四个按钮已锁定。")',
                      body("renderClean"), "摘要必须如实说明降级原因，不能只灰按钮不吭声")


if __name__ == "__main__":
    unittest.main()
