"""AI 副驾改写端点（/api/agent/refine）契约：v0.7.1 任务 2.4，纯函数 + 打桩，不触网不起服务。

钉三件事：
1. build_refine_user_message 只把题目可见字段喂给模型，extensions / 令牌一类绝不进 prompt；
2. parse_refine_reply 认得裸 JSON 与 ```json 围栏、认 field/value/text 三种键，取不到非空文本就抛错；
3. /refine 路由的三条腿：真实模型产出改写、缺密钥 Mock 原样回显、异常回落 fallback——
   三条都必须把「原题干」之外的东西如实交代，绝不把空串当改写结果回填进老师表单。

运行：``.venv/Scripts/python.exe -m unittest tests.test_refine_agent``
"""

from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from app.api import agents
from app.api.agents import (
    REFINE_SYSTEM_PROMPT,
    RefineRequest,
    agent_refine,
    build_refine_user_message,
    parse_refine_reply,
)


class RefinePromptTest(unittest.TestCase):
    def test_leaks_no_extensions_or_tokens(self) -> None:
        question = {
            "type": "single_choice", "stem": "旧题干 $x^2$", "solution": "旧解析",
            "options": [{"key": "A", "content": "$1$"}],
            "extensions": {"org.jiuzhang.core-bank.migration": {"flags": ["answer_absent"]}},
            "answer": {"kind": "choice", "choice_keys": ["A"]},
        }
        msg = build_refine_user_message(question, "把题干改短", "stem", "旧题干 $x^2$")
        self.assertIn("旧题干 $x^2$", msg)
        self.assertIn("把题干改短", msg)
        self.assertNotIn("extensions", msg, "extensions 不得进模型")
        self.assertNotIn("migration", msg, "审核标记不得进模型")

    def test_prompt_declares_json_contract(self) -> None:
        self.assertIn("裸 JSON", REFINE_SYSTEM_PROMPT)
        self.assertIn("不得改错", REFINE_SYSTEM_PROMPT)


class RefineParseTest(unittest.TestCase):
    def test_reads_named_field(self) -> None:
        parsed = parse_refine_reply('```json\n{"stem": "新题干", "note": "更简洁"}\n```', "stem")
        self.assertEqual(parsed, {"value": "新题干", "note": "更简洁"})

    def test_falls_back_to_value_or_text(self) -> None:
        self.assertEqual(parse_refine_reply('{"value": "甲"}', "solution")["value"], "甲")
        self.assertEqual(parse_refine_reply('{"text": "乙"}', "stem")["value"], "乙")

    def test_rejects_non_json_and_empty(self) -> None:
        for bad in ("not json", "{}", '{"stem":"   "}', "[]"):
            with self.assertRaises(ValueError):
                parse_refine_reply(bad, "stem")


def _fake_completion(content: str, mock_flag: bool):
    async def _call(*args, **kwargs):
        return {
            "content": content,
            "tool_calls": [],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            "model": "stub",
            "mock": mock_flag,
        }
    return _call


class RefineRouteTest(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def test_real_model_returns_rewrite(self) -> None:
        body = RefineRequest(
            question={"type": "fill_blank", "stem": "旧题干"},
            instruction="更简洁", field="stem",
        )
        with mock.patch.object(agents.ai_client, "chat_completion",
                               _fake_completion('{"stem": "新题干", "note": "精简"}', False)):
            response = self._run(agent_refine(body))
        self.assertEqual(response["type"], "complete")
        self.assertFalse(response["mock"])
        self.assertEqual(response["data"]["value"], "新题干")

    def test_mock_echoes_original_never_fabricates(self) -> None:
        body = RefineRequest(
            question={"type": "fill_blank", "stem": "旧题干 $x$"},
            instruction="改短", field="stem",
        )
        with mock.patch.object(agents.ai_client, "chat_completion",
                               _fake_completion("whatever mock says", True)):
            response = self._run(agent_refine(body))
        self.assertTrue(response["mock"])
        # Mock 模式必须原样回显原题干，绝不把假数据当真改写
        self.assertEqual(response["data"]["value"], "旧题干 $x$")
        self.assertIn("未配置模型", response["data"]["note"])

    def test_model_exception_falls_back_to_original(self) -> None:
        async def _boom(*args, **kwargs):
            raise RuntimeError("provider down")
        body = RefineRequest(
            question={"stem": "原始题干", "solution": "原始解析"},
            instruction="改解析", field="solution",
        )
        with mock.patch.object(agents.ai_client, "chat_completion", _boom):
            response = self._run(agent_refine(body))
        self.assertEqual(response["type"], "error")
        self.assertEqual(response["fallback"]["value"], "原始解析")

    def test_field_is_whitelisted_to_stem_or_solution(self) -> None:
        body = RefineRequest(
            question={"stem": "s", "answer": {"kind": "text", "content": "a"}},
            instruction="改答案", field="answer",
        )
        with mock.patch.object(agents.ai_client, "chat_completion",
                               _fake_completion('{"stem": "s2"}', False)):
            response = self._run(agent_refine(body))
        # 越界字段被夹回 stem，绝不允许改写 answer 这类非白名单字段
        self.assertEqual(response["data"]["field"], "stem")

    def test_route_registered(self) -> None:
        self.assertIn("/api/agent/refine", [route.path for route in agents.router.routes])


if __name__ == "__main__":
    unittest.main()
