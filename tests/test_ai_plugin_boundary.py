"""插件调 AI 的边界契约：常驻对话助手下架后，只剩改写/配置中心这条通道。

钉四件事：
1. 宿主方法表里不再有 ``agent.chat``，写进 relayAgent 的每条分支都真的被分发；
2. ``ai:invoke`` 权限来自清单而非请求载荷，守卫必须先于代发；
3. 写令牌与密钥只在宿主侧，插件拿不到；
4. relay 的末尾是明确拒回，绝不留默认动作。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ai_plugin_boundary``
"""

from __future__ import annotations

import re
import unittest

from tests.core_sources import stage_source, workspace_source  # noqa: E402

STAGE_JS = stage_source()
WORKSPACE_JS = workspace_source()


def _array(name: str) -> set[str]:
    match = re.search(r"var " + name + r" = \[(.*?)\];", STAGE_JS, re.S)
    assert match, f"stage.js 里找不到 {name}"
    return set(re.findall(r'"([^"]+)"', match.group(1)))


class HostGuardTest(unittest.TestCase):
    """AI 方法表与守卫顺序。"""

    def test_01_chat_method_is_gone(self) -> None:
        self.assertNotIn("agent.chat", _array("RELAY_METHODS"))
        self.assertNotIn("agent.chat", _array("AI_ONLY_METHODS"))
        self.assertNotIn("/api/agent/chat", STAGE_JS)

    def test_02_ai_only_methods_are_listed(self) -> None:
        ai_only = _array("AI_ONLY_METHODS")
        self.assertIn("agent.refine", ai_only)
        self.assertIn("ai.recognize", ai_only)
        self.assertTrue(ai_only <= _array("RELAY_METHODS"), "AI 方法必须在总白名单里")

    def test_03_permission_comes_from_the_manifest_not_the_payload(self) -> None:
        self.assertIn('var AI_INVOKE_PERMISSION = "ai:invoke"', STAGE_JS)
        start = STAGE_JS.index("function hasAiGrant(tab)")
        block = STAGE_JS[start: start + 300]
        self.assertIn("tab.plugin && tab.plugin.permissions", block)
        self.assertNotIn("payload.permissions", STAGE_JS, "插件自报权限一律不认")

    def test_04_guard_replies_before_relaying(self) -> None:
        guard_at = STAGE_JS.index('if (AI_ONLY_METHODS.indexOf(method) >= 0 && !hasAiGrant(tab))')
        relay_at = STAGE_JS.index("relayAgent(method, payload, done, fail, failWith);")
        self.assertLess(guard_at, relay_at, "先守卫再代发，顺序反了等于敞开大门")
        self.assertIn('code: "PERMISSION_DENIED"', STAGE_JS)

    def test_05_write_token_stays_host_side(self) -> None:
        start = STAGE_JS.index("function relayAgent(")
        block = STAGE_JS[start: STAGE_JS.index("\n    return {\n", start)]
        self.assertIn("withWriteToken(", block, "写操作必须由宿主代持写令牌")
        self.assertNotIn("localStorage", block, "令牌与草稿都不落在智能体通道里")

    def test_06_host_shell_does_not_call_the_agent_api_directly(self) -> None:
        self.assertNotIn('fetch("/api/agent/chat"', WORKSPACE_JS)
        self.assertNotIn('fetch("/api/agent/refine"', WORKSPACE_JS)

    def test_07_every_agent_branch_is_dispatched(self) -> None:
        start = STAGE_JS.index("function relayAgent(")
        body = STAGE_JS[start: STAGE_JS.index("  function relay(tab, message)")]
        handled = set(re.findall(r'if \(method === "([^"]+)"', body))
        self.assertTrue(handled, "relayAgent 一条分支都没有，这条测失效了")
        ai_only = _array("AI_ONLY_METHODS")
        agent_read = _array("AGENT_READ_METHODS")
        self.assertEqual(handled - ai_only - agent_read, set(),
                         "这些方法写在 relayAgent 里却没人分发过去")
        self.assertIn('AGENT_READ_METHODS.indexOf(method) >= 0', STAGE_JS)

    def test_08_relay_rejects_unknown_method_instead_of_defaulting(self) -> None:
        relay_body = STAGE_JS[STAGE_JS.index("  function relay(tab, message)"):]
        relay_body = relay_body[: relay_body.index("\n  /** 题篮变动记一笔")]
        self.assertIn("if (families[f](ctx)) return;", relay_body,
                      "六条族函数挨个问过了才许拒，绝不许在族里偷偷兜底")
        self.assertIn('failWith("UNSUPPORTED_METHOD"', relay_body)


if __name__ == "__main__":
    unittest.main()
