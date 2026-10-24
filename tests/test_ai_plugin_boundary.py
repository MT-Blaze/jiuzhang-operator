"""军令 #15 边界契约：AI 助手降级成普通插件，特权一律收归底座代执行。

四件事分开钉，缺一件就说明「插件化」只是换了个地方写死：
1. 清单侧：``org.jiuzhang.chat`` 过 ``validate_plugin``，能力/插槽/权限/总线主题全命中白名单；
2. 沙箱侧：插件脚本零 ``fetch(`` / 零 ``parent.document`` / 零 ``localStorage``，
   请求 id 合规、无后行断言，且它开口要的每一个 Host API 方法都在宿主白名单里；
3. 宿主侧：智能体方法表只对清单声明 ``ai:invoke`` 的插件开放，题库跳转通知只在
   iframe 真的活着之后才投递（早发等于丢）；
4. 后端侧：题库检索工具由底座统计与跳转——AI 只说「去哪、带什么词」，开门的是底座。

纯函数 + 源码不变量，不触网、不起服务；真机证据由 ``.system_generated`` 下的探针产出。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ai_plugin_boundary``
"""

from __future__ import annotations

import asyncio
import json
import re
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CHAT_DIR = ROOT / "plugins" / "org.jiuzhang.chat"
CHAT_JS = (CHAT_DIR / "dist" / "plugin.js").read_text(encoding="utf-8")
CHAT_HTML = (CHAT_DIR / "dist" / "index.html").read_text(encoding="utf-8")
STAGE_JS = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
WORKSPACE_JS = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")
CORE_BANK_JS = (ROOT / "plugins" / "org.jiuzhang.core-bank" / "dist" / "plugin.js").read_text(
    encoding="utf-8"
)

from app import __version__ as HOST_VERSION  # noqa: E402
from app.api import agents  # noqa: E402
from app.core import plugin_tools  # noqa: E402
from app.core.plugins import (  # noqa: E402
    _BUS_SUBSCRIBE,
    _CAPABILITIES,
    validate_plugin,
)

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def _version_tuple(raw: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", str(raw))[:3])


def _relay_methods() -> set[str]:
    block = re.search(r"var RELAY_METHODS = \[(.*?)\];", STAGE_JS, re.S)
    assert block, "stage.js 里找不到 Host API 白名单数组"
    return set(re.findall(r'"([^"]+)"', block.group(1)))


class ManifestContractTest(unittest.TestCase):
    """助手插件必须和第三方插件吃同一套校验，一票都不能多。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((CHAT_DIR / "plugin.json").read_text(encoding="utf-8"))
        cls.info = validate_plugin(CHAT_DIR, dict(cls.manifest))

    def test_01_shipped_manifest_passes(self) -> None:
        self.assertEqual(self.info["id"], "org.jiuzhang.chat")
        self.assertEqual(self.info["slots"], ["sidebar.right"])
        self.assertEqual(self.info["capabilities"], ["assistant.chat"])
        self.assertEqual(self.info["permissions"], ["ai:invoke"])
        self.assertTrue(self.info["entry_url"], "入口必须能被发现接口下发")

    def test_02_no_privileged_fields(self) -> None:
        # 后端插件字段与题库读权限都是「底层特权」，AI 一样不许碰
        self.assertNotIn("backend", self.manifest)
        self.assertNotIn("questions:read", self.manifest["permissions"])
        self.assertNotIn("database", json.dumps(self.manifest))

    def test_03_new_tokens_are_whitelisted(self) -> None:
        self.assertIn("assistant.chat", _CAPABILITIES)
        for topic in ("panel.button.click", "stage.selection"):
            self.assertIn(topic, _BUS_SUBSCRIBE)
        for topic in self.manifest["bus"]["subscribe"]:
            self.assertIn(topic, _BUS_SUBSCRIBE, f"清单订阅了白名单外的主题：{topic}")

    def test_04_min_host_version_is_not_in_the_future(self) -> None:
        self.assertLessEqual(_version_tuple(self.manifest["min_host_version"]), _version_tuple(HOST_VERSION))
        self.assertTrue((CHAT_DIR / "LICENSE").is_file(), "插件包必须自带 Apache-2.0 许可")

    def test_05_ui_controls_within_host_limit(self) -> None:
        controls = (self.info.get("ui") or {}).get("controls") or []
        self.assertLessEqual(len(controls), 8, "面板控件超上限必被宿主截断")
        for control in controls:
            self.assertTrue(REQUEST_ID_RE.match(control["id"]), control["id"])


class PluginSandboxTest(unittest.TestCase):
    """三查落进单测：命中数必须为 0，而不是靠人肉 grep。"""

    def test_01_no_direct_network_access(self) -> None:
        self.assertNotIn("fetch(", CHAT_JS)
        self.assertNotIn("XMLHttpRequest", CHAT_JS)

    def test_02_no_host_dom(self) -> None:
        self.assertNotIn("parent.document", CHAT_JS)
        self.assertNotIn("contentDocument", CHAT_JS)

    def test_03_no_local_storage(self) -> None:
        # 沙箱是不透明源，插件自己碰存储会抛 SecurityError；记忆一律走宿主代持的 draft.*
        for token in ("window.localStorage", "localStorage.getItem", "localStorage.setItem"):
            self.assertNotIn(token, CHAT_JS, "对话记忆只能请宿主代持（draft.*）：" + token)
        self.assertIn('hostCall("draft.save"', CHAT_JS)

    def test_04_request_ids_are_host_shaped(self) -> None:
        sample = "c12_" + format(1_700_000_000_000, "x")
        self.assertTrue(REQUEST_ID_RE.match(sample))
        self.assertIn('var id = "c" + requestSeq + "_" + Date.now().toString(36);', CHAT_JS)

    def test_05_no_lookbehind_regex(self) -> None:
        self.assertIsNone(re.search(r"\(\?<[=!]", CHAT_JS), "AGENTS §6：后行断言会打挂旧浏览器")

    def test_06_no_physical_input_simulation(self) -> None:
        """军令 #15 任务 2：AI 不接管鼠标键盘——不构造输入事件，也不碰宿主窗口。"""
        for token in ("new KeyboardEvent", "new MouseEvent", "new PointerEvent", ".click()"):
            self.assertNotIn(token, CHAT_JS, f"插件不得模拟输入事件：{token}")
        # 对父窗口唯一的动作就是 postMessage；读宿主 DOM 的门从头到尾没开过
        self.assertEqual(CHAT_JS.count("window.parent."), CHAT_JS.count("window.parent.postMessage"))
        # 插件只给自己的输入框聚焦
        self.assertIn("promptInput.focus()", CHAT_JS)

    def test_07_every_requested_method_is_on_the_host_whitelist(self) -> None:
        methods = set(re.findall(r'hostCall\("([^"]+)"', CHAT_JS))
        self.assertTrue(methods, "插件一个 Host API 都没调，说明这条测失效了")
        relay = _relay_methods()
        for method in sorted(methods):
            self.assertIn(method, relay, f"插件调了白名单外的方法 {method}，必被宿主拒发")
        # 跳转方法是变量分派的，单独钉它在白名单里
        for method in ("stage.open_bank", "stage.open_editor"):
            self.assertIn(method, relay)

    def test_08_composer_never_relies_on_native_form_submit(self) -> None:
        """真机踩出来的坑：沙箱 iframe 没开 allow-forms，浏览器在派发 submit 之前就掐掉原生提交。

        写成 `<form>` + `type="submit"` 时点【发送】石沉大海（连事件都不发），只能等超时。
        发送必须走显式的按钮点击与回车键，不许再借表单原生行为。
        """
        self.assertNotIn("<form", CHAT_HTML, "输入区不得用表单承载——沙箱里提交必被拦截")
        self.assertNotIn('type="submit"', CHAT_HTML)
        self.assertNotIn('addEventListener("submit"', CHAT_JS)
        self.assertNotIn('new Event("submit"', CHAT_JS)
        self.assertIn('sendBtn.addEventListener("click", submitFromComposer)', CHAT_JS)
        self.assertIn("submitFromComposer();", CHAT_JS, "回车发送要直接走同一个出口")


class HostGuardTest(unittest.TestCase):
    """宿主侧：智能体通道只对声明了 ai:invoke 的清单开放。"""

    def test_01_ai_only_methods_are_listed(self) -> None:
        block = re.search(r"var AI_ONLY_METHODS = \[(.*?)\];", STAGE_JS, re.S)
        self.assertIsNotNone(block)
        methods = set(re.findall(r'"([^"]+)"', block.group(1)))
        self.assertEqual(
            methods,
            {
                "agent.chat",
                "agent.refine",
                "plugin.install_url",
                "ui.params.set",
                "editor.apply_patch",
                "stage.open_bank",
                "stage.open_editor",
            },
        )

    def test_02_permission_comes_from_the_manifest_not_the_payload(self) -> None:
        self.assertIn('var AI_INVOKE_PERMISSION = "ai:invoke"', STAGE_JS)
        start = STAGE_JS.index("function hasAiGrant(tab)")
        block = STAGE_JS[start: start + 300]
        self.assertIn("tab.plugin && tab.plugin.permissions", block)
        self.assertNotIn("payload.permissions", STAGE_JS, "插件自报权限一律不认")

    def test_03_guard_replies_before_relaying(self) -> None:
        guard_at = STAGE_JS.index('if (AI_ONLY_METHODS.indexOf(method) >= 0 && !hasAiGrant(tab))')
        relay_at = STAGE_JS.index("relayAgent(method, payload, done, fail, failWith);")
        self.assertLess(guard_at, relay_at, "先守卫再代发，顺序反了等于敞开大门")
        self.assertIn('code: "PERMISSION_DENIED"', STAGE_JS)

    def test_04_write_token_stays_host_side(self) -> None:
        start = STAGE_JS.index("function relayAgent(")
        block = STAGE_JS[start: STAGE_JS.index('if (method === "asset.upload")')]
        self.assertIn("withWriteToken(", block, "装机必须由宿主代持写令牌")
        self.assertNotIn("localStorage", block, "令牌与草稿都不落在智能体通道里")
        self.assertNotIn("window.localStorage", CHAT_JS)

    def test_05_broadcast_reaches_the_right_slot(self) -> None:
        self.assertIn(
            "var targets = liveFrames().concat(panels.filter(function (panel) { return panel.frame; }));",
            STAGE_JS,
            "面板按钮的指令要能广播到右栏助手",
        )

    def test_06_host_shell_no_longer_calls_the_agent_api(self) -> None:
        self.assertNotIn('fetch("/api/agent/chat"', WORKSPACE_JS)
        self.assertNotIn('fetch("/api/agent/refine"', WORKSPACE_JS)

    def test_07_every_agent_branch_is_dispatched(self) -> None:
        """relayAgent 里写了分支的方法，必须真的被分发过去（真机踩过的坑）。

        `plugins.list` / `workspace.state` 不在 AI_ONLY_METHODS 里（任何插件都能读清单），
        一旦分发口只认 AI_ONLY_METHODS，这两个请求就会一路掉到 relay 末尾——
        曾经末尾的默认动作是清空题篮，读一次快照就把老师的题篮清了。
        """
        start = STAGE_JS.index("function relayAgent(")
        body = STAGE_JS[start: STAGE_JS.index("  function relay(tab, message)")]
        handled = set(re.findall(r'if \(method === "([^"]+)"', body))
        self.assertTrue(handled, "relayAgent 一条分支都没有，这条测失效了")
        ai_only = set(re.findall(
            r'"([^"]+)"', re.search(r"var AI_ONLY_METHODS = \[(.*?)\];", STAGE_JS, re.S).group(1)))
        agent_read = set(re.findall(
            r'"([^"]+)"', re.search(r"var AGENT_READ_METHODS = \[(.*?)\];", STAGE_JS, re.S).group(1)))
        self.assertEqual(handled - ai_only - agent_read, set(),
                         "这些方法写在 relayAgent 里却没人分发过去")
        self.assertIn('AGENT_READ_METHODS.indexOf(method) >= 0', STAGE_JS)

    def test_08_relay_rejects_unknown_method_instead_of_defaulting(self) -> None:
        """relay 的末尾必须是「明确拒回」，不许留任何默认动作。"""
        relay_body = STAGE_JS[STAGE_JS.index("  function relay(tab, message)"):]
        relay_body = relay_body[: relay_body.index("\n  /** 题篮变动记一笔")]
        self.assertIn('if (method === "basket.clear") {', relay_body,
                      "清题篮必须是显式分支，不许当兜底")
        self.assertIn('failWith("UNSUPPORTED_METHOD"', relay_body)
        self.assertLess(
            relay_body.index('if (method === "basket.clear")'),
            relay_body.index('failWith("UNSUPPORTED_METHOD"'),
            "未知方法只能在所有分支之后被拒掉")


class BankQueryDeliveryTest(unittest.TestCase):
    """军令 #15 任务 3 的落点：检索词只在 iframe 活着之后才交出去。"""

    def test_01_open_bank_captures_the_query(self) -> None:
        self.assertIn("var pendingBankQuery = null;", STAGE_JS)
        self.assertIn("pendingBankQuery = { query: query, question_id: questionId };", STAGE_JS)
        self.assertIn('notify(tab, "system.bank_query"', STAGE_JS)

    def test_02_delivery_waits_for_a_live_tab(self) -> None:
        deliver = STAGE_JS[STAGE_JS.index("function deliverBankQuery(tab)"):]
        deliver = deliver[: deliver.index("\n  }")]
        self.assertIn('tab.state !== "live"', deliver, "早发的 postMessage 会被浏览器丢掉")
        mount_at = STAGE_JS.index("deliverBankQuery(tab);", STAGE_JS.index("frame.addEventListener(\"load\""))
        self.assertGreater(mount_at, 0, "挂载成功后要补发一次检索意图")

    def test_03_core_bank_handles_the_notification(self) -> None:
        self.assertIn('message.event === "system.bank_query"', CORE_BANK_JS, "core-bank 没接住跳转")
        self.assertIn("state.search = query", CORE_BANK_JS)

    def test_04_query_is_clamped_host_side(self) -> None:
        self.assertRegex(STAGE_JS, r"var OPEN_BANK_QUERY_MAX = \d+;")
        self.assertIn("raw.query.trim().slice(0, OPEN_BANK_QUERY_MAX)", STAGE_JS)


class BankToolContractTest(unittest.TestCase):
    """题库检索工具：数量与命中都由底座统计，AI 拿不到连接。"""

    def test_01_tool_shape(self) -> None:
        tool = plugin_tools.build_bank_tool()
        self.assertEqual(tool["type"], "function")
        function = tool["function"]
        self.assertEqual(function["name"], plugin_tools.HOST_BANK_TOOL)
        self.assertEqual(function["parameters"]["properties"]["query"]["maxLength"], plugin_tools.BANK_MAX_QUERY)
        self.assertNotIn("required", function["parameters"], "留空即统计全库，不该强制关键词")

    def test_02_jump_declares_intent_only(self) -> None:
        jump = plugin_tools._bank_jump("导数", {"plugin_id": "org.jiuzhang.core-bank"})
        self.assertEqual(jump["type"], "open_bank")
        self.assertEqual(jump["label"], "前往题库并搜索")
        self.assertEqual(jump["query"], "导数")
        self.assertEqual(plugin_tools._bank_jump("", {})["label"], "前往题库")

    def test_03_bad_arguments_degrade_readably(self) -> None:
        result = plugin_tools.execute_bank_tool("{not json")
        self.assertFalse(result["ok"])
        self.assertTrue(result["host_tool"])
        self.assertEqual(result["action"], plugin_tools.HOST_BANK_TOOL)
        self.assertIn("题库检索失败", result["summary"])

    def test_04_count_comes_from_the_store(self) -> None:
        item = {"id": "q_1", "type": "single_choice", "stem": "求函数 $f(x)=x^2$ 的导数", "difficulty": "L2"}
        with mock.patch.object(plugin_tools.bank_provider, "resolve", return_value={
            "plugin_id": "org.jiuzhang.core-bank", "name": "真题题库"
        }), mock.patch.object(plugin_tools.bank_store, "list_questions", return_value=([item], 48)), \
                mock.patch.object(plugin_tools.bank_store, "stats", return_value={"total": 456}):
            result = plugin_tools.execute_bank_tool({"query": "导数"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["total"], 456)
        self.assertEqual(result["data"]["matched"], 48)
        self.assertIn("456", result["summary"])
        self.assertIn("48", result["summary"])
        self.assertEqual(result["jump"]["query"], "导数")
        self.assertEqual(result["jump"]["plugin_id"], "org.jiuzhang.core-bank")

    def test_05_empty_query_counts_the_whole_bank(self) -> None:
        with mock.patch.object(plugin_tools.bank_provider, "resolve", return_value={
            "plugin_id": "org.jiuzhang.core-bank", "name": "真题题库"
        }), mock.patch.object(plugin_tools.bank_store, "list_questions", return_value=([], 0)), \
                mock.patch.object(plugin_tools.bank_store, "stats", return_value={"total": 0}):
            result = plugin_tools.execute_bank_tool({"query": ""})
        self.assertIn("共 0 题", result["summary"])
        self.assertEqual(result["jump"]["label"], "前往题库")

    def test_06_intent_matcher(self) -> None:
        intent = plugin_tools.match_bank_intent("查一下题库里有多少道导数题")
        self.assertIsNotNone(intent)
        self.assertEqual(intent["tool"], plugin_tools.HOST_BANK_TOOL)
        self.assertEqual(intent["arguments"]["query"], "导数")
        self.assertIsNone(plugin_tools.match_bank_intent("拆分第一题"), "拆题是插件工具的活")
        self.assertIsNone(plugin_tools.match_bank_intent("今天天气不错"))

    def test_07_store_failure_is_reported_not_raised(self) -> None:
        with mock.patch.object(plugin_tools.bank_provider, "resolve", return_value={
            "plugin_id": "org.jiuzhang.core-bank", "name": "真题题库"
        }), mock.patch.object(
            plugin_tools.bank_store, "list_questions", side_effect=plugin_tools.bank_store.BankError("库锁死")
        ):
            result = plugin_tools.execute_bank_tool({"query": "导数"})
        self.assertFalse(result["ok"])
        self.assertIn("读取题库", result["summary"])


class JumpActionAssemblyTest(unittest.TestCase):
    def _call(self, jump: dict) -> dict:
        return {"tool": "t", "jump": jump, "ok": True, "summary": "", "cards": []}

    def test_01_only_allowed_types_survive(self) -> None:
        actions = agents._jump_actions([
            self._call({"type": "open_bank", "label": "前往题库并搜索", "query": "导数", "plugin_id": "a"}),
            self._call({"type": "rm_rf", "label": "删库", "query": "", "plugin_id": ""}),
            self._call({"type": "trigger_button", "label": "替你点按钮", "query": "", "plugin_id": ""}),
        ])
        self.assertEqual([item["type"] for item in actions], ["open_bank"])
        self.assertEqual(actions[0]["query"], "导数")

    def test_02_deduped_and_capped(self) -> None:
        calls = [
            self._call({"type": "open_bank", "label": "前往题库并搜索", "query": "导数", "plugin_id": "a"})
            for _ in range(2)
        ] + [
            self._call({"type": "open_editor", "label": "去编辑", "query": "", "plugin_id": "b%d" % index})
            for index in range(5)
        ]
        actions = agents._jump_actions(calls)
        self.assertLessEqual(len(actions), 3)
        self.assertEqual(len({(a["type"], a["query"], a["plugin_id"]) for a in actions}), len(actions))

    def test_03_missing_jump_is_tolerated(self) -> None:
        self.assertEqual(agents._jump_actions([{"tool": "t", "jump": None}]), [])


class ChatEndpointTest(unittest.TestCase):
    """整条链：无 tool_calls 时宿主按句式兜底，动作随回复一起回。"""

    def _run(self, user_input: str) -> dict:
        async def fake_completion(**_kwargs):
            return {
                "content": "好的",
                "tool_calls": [],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                "model": "mock/test",
                "mock": True,
            }

        item = {"id": "q_9", "type": "fill_blank", "stem": "数列 $a_n$ 的导数…", "difficulty": "L3"}
        with mock.patch.object(agents.ai_client, "chat_completion", fake_completion), \
                mock.patch.object(plugin_tools, "build_tools", return_value=[]), \
                mock.patch.object(plugin_tools.bank_provider, "resolve", return_value={
                    "plugin_id": "org.jiuzhang.core-bank", "name": "真题题库"
                }), \
                mock.patch.object(plugin_tools.bank_store, "list_questions", return_value=([item], 48)), \
                mock.patch.object(plugin_tools.bank_store, "stats", return_value={"total": 456}):
            return asyncio.run(
                agents.agent_chat(agents.ChatRequest(user_input=user_input, task_id="t-15"))
            )

    def test_01_bank_question_routes_host_and_carries_action(self) -> None:
        body = self._run("查一下题库里有多少道导数题")
        self.assertEqual(body["route"], "host")
        data = body["data"]
        self.assertEqual(data["plugin_calls"][0]["tool"], plugin_tools.HOST_BANK_TOOL)
        actions = data["actions"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "open_bank")
        self.assertEqual(actions[0]["label"], "前往题库并搜索")
        self.assertEqual(actions[0]["query"], "导数")
        self.assertIn("456", data["content"])

    def test_02_no_button_action_is_ever_emitted(self) -> None:
        """任务 2 的后端半边：响应里不得再出现「替你点按钮」这类动作。"""
        body = self._run("题库里一共有多少道题")
        self.assertTrue(body["data"]["actions"])
        for action in body["data"]["actions"]:
            self.assertIn(action["type"], {"open_bank", "open_editor"})
        self.assertNotIn("trigger_button", json.dumps(body))


if __name__ == "__main__":
    unittest.main()
