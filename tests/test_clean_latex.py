"""脏 LaTeX 清洗端点与宿主通道契约：军令 #21 任务四。

钉三件事：
1. ``/api/agent/clean_latex`` 是确定性规则：同一段输入永远得到同一段输出，不碰模型；
2. 宿主 ``text.clean_latex`` 通道不截断长文本（半截文本回填比失败更糟），
   也不是 AI 专属方法——录题插件不需要声明 ai:invoke 就能用；
3. 录题端的【AI 清洗公式】按钮必须真的走这条通道，而不是再抄一份规则。

运行：``.venv/Scripts/python.exe -m unittest tests.test_clean_latex``
"""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.api.agents import CleanLatexRequest, agent_clean_latex

ROOT = Path(__file__).resolve().parents[1]
STAGE_JS = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
EDITOR_DIR = ROOT / "plugins" / "org.jiuzhang.editor"
EDITOR_JS = (EDITOR_DIR / "dist" / "plugin.js").read_text(encoding="utf-8")
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
    """军令 #23 阶段 3：【AI 清洗公式】搬到辅助栏，走宿主 text.clean_latex 回填画布。

    钉四件事：按钮在辅助栏（不在画布）、真的调宿主通道而不是再抄一份规则、
    题干段与解析段全成功才回填、请求中按钮标 aria-busy（AGENTS §6）。
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

    def test_02_apply_happens_only_after_every_call_succeeds(self) -> None:
        block = self.cleaner_block()
        self.assertIn("Promise.all(", block, "必须全部成功后再回填")
        self.assertIn('"stem", "solution"', block, "两段一起清洗，不逐段边洗边写")
        self.assertIn("panel.ai.busy = false", block)
        self.assertIn("editor.apply_patch", block, "回填一律经宿主通知画布")
        self.assertIn("源码保持原样", block, "任一失败要如实说不许动")
        self.assertNotIn("fetch(", block)
        self.assertNotIn("/api/", block)

    def test_03_busy_state_marks_the_buttons(self) -> None:
        """清洗/改写进行中：三个动作按钮必须同步 aria-busy，不许只靠变灰的颜色传达。"""
        block = EDITOR_JS.split("function renderAi() {", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn('node.setAttribute("aria-busy", "true")', block)
        self.assertIn('node.removeAttribute("aria-busy")', block)
        self.assertIn("panelAiSendEl, panelAiCleanEl, panelAiApplyEl", block)

    def test_04_manifest_and_index_agree(self) -> None:
        """清单与官方索引的版本号、描述必须逐字相同——不写死数字，插件一升号就假红。"""
        manifest = json.loads((EDITOR_DIR / "plugin.json").read_text(encoding="utf-8"))
        index = json.loads((ROOT / "plugins.json").read_text(encoding="utf-8"))
        entries = [item for item in index["entries"] if item["id"] == "org.jiuzhang.editor"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["version"], manifest["version"])
        self.assertEqual(entries[0]["description"], manifest["description"])


if __name__ == "__main__":
    unittest.main()
