"""对话引擎调优契约（10.24 军令 P0）：纯函数单测，不触网、不起服务。

覆盖三件事：
1. strip_code_fences 剥掉模型爱套的 ```json 围栏（拦截动作裸奔的后端半边）。
2. build_chat_system_prompt 把右栏结构化上下文追加到 System 尾部（上下文注入）。
3. build_user_message_with_history 把此前对话折叠进本轮 user 消息（延续前文）。
另附 ChatRequest 契约字段的宽松校验。

运行：``.venv/Scripts/python.exe -m unittest tests.test_agent_chat_tuning``
"""

from __future__ import annotations

import unittest

from app.api.agents import (
    CHAT_SYSTEM_PROMPT,
    ChatRequest,
    build_chat_system_prompt,
    build_user_message_with_history,
    strip_code_fences,
)


class StripCodeFencesTest(unittest.TestCase):
    def test_strips_json_fence(self) -> None:
        raw = '```json\n{"action": "clarify"}\n```'
        self.assertEqual(strip_code_fences(raw), '{"action": "clarify"}')

    def test_strips_bare_fence_without_lang(self) -> None:
        raw = '```\n{"action": "split_paper"}\n```'
        self.assertEqual(strip_code_fences(raw), '{"action": "split_paper"}')

    def test_strips_fence_with_surrounding_whitespace(self) -> None:
        raw = '  ```json\r\n{"a": 1}\r\n```  '
        self.assertEqual(strip_code_fences(raw), '{"a": 1}')

    def test_plain_text_untouched(self) -> None:
        self.assertEqual(strip_code_fences("拆分第 1-2 页"), "拆分第 1-2 页")

    def test_empty_and_none_safe(self) -> None:
        self.assertEqual(strip_code_fences(""), "")
        self.assertIsNone(strip_code_fences(None))

    def test_inner_fence_not_over_stripped(self) -> None:
        # 只剥最外层一对围栏，正文里的反引号应原样保留
        raw = '```json\n{"note": "用 ``` 包裹"}\n```'
        self.assertEqual(strip_code_fences(raw), '{"note": "用 ``` 包裹"}')


class BuildSystemPromptTest(unittest.TestCase):
    def test_no_context_returns_fixed_prefix(self) -> None:
        self.assertEqual(build_chat_system_prompt(None), CHAT_SYSTEM_PROMPT)
        self.assertEqual(build_chat_system_prompt({}), CHAT_SYSTEM_PROMPT)

    def test_context_appended_at_tail(self) -> None:
        ctx = {"current_task": "拆题", "textbook": "人教A版必修一"}
        prompt = build_chat_system_prompt(ctx)
        # 固定前缀必须原样在最前（缓存友好），上下文追加在尾部
        self.assertTrue(prompt.startswith(CHAT_SYSTEM_PROMPT))
        self.assertIn("当前工作台上下文", prompt)
        self.assertIn("人教A版必修一", prompt)
        self.assertLess(prompt.index(CHAT_SYSTEM_PROMPT[:10]), prompt.index("人教A版必修一"))

    def test_context_is_json_serialized(self) -> None:
        prompt = build_chat_system_prompt({"mock": True, "model": "qwen"})
        self.assertIn('"mock": true', prompt)
        self.assertIn('"model": "qwen"', prompt)


class BuildUserMessageTest(unittest.TestCase):
    def test_no_history_returns_input(self) -> None:
        self.assertEqual(build_user_message_with_history(None, "拆分第 3 页"), "拆分第 3 页")
        self.assertEqual(build_user_message_with_history([], "拆分第 3 页"), "拆分第 3 页")

    def test_history_folded_before_input(self) -> None:
        history = [
            {"role": "user", "content": "拆分第 1-2 页"},
            {"role": "assistant", "content": "已识别拆题指令：第 1-2 页"},
        ]
        msg = build_user_message_with_history(history, "改成第 3-4 页")
        self.assertIn("此前对话记录", msg)
        self.assertIn("用户：拆分第 1-2 页", msg)
        self.assertIn("助手：已识别拆题指令：第 1-2 页", msg)
        self.assertIn("本轮指令", msg)
        self.assertIn("改成第 3-4 页", msg)
        # 本轮指令必须在历史记录之后
        self.assertLess(msg.index("此前对话记录"), msg.index("本轮指令"))

    def test_malformed_turns_skipped(self) -> None:
        history = [
            "not-a-dict",
            {"role": "system", "content": "越权角色"},
            {"role": "user", "content": "   "},
            {"role": "user", "content": "有效指令"},
        ]
        msg = build_user_message_with_history(history, "本轮")
        self.assertIn("有效指令", msg)
        self.assertNotIn("越权角色", msg)

    def test_all_invalid_falls_back_to_input(self) -> None:
        history = [{"role": "system", "content": "x"}]
        self.assertEqual(build_user_message_with_history(history, "本轮"), "本轮")


class ChatRequestContractTest(unittest.TestCase):
    def test_context_and_history_optional(self) -> None:
        req = ChatRequest(user_input="拆分")
        self.assertIsNone(req.context)
        self.assertIsNone(req.history)

    def test_full_payload_accepted(self) -> None:
        req = ChatRequest(
            user_input="改成第 3-4 页",
            task_id="ws_1",
            context={"current_task": "拆题"},
            history=[{"role": "user", "content": "拆分第 1-2 页"}],
        )
        self.assertEqual(req.context["current_task"], "拆题")
        self.assertEqual(req.history[0]["role"], "user")


if __name__ == "__main__":
    unittest.main()
