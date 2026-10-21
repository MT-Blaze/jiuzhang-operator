"""OpenAI 兼容的大模型客户端（Provider 实现）。

从环境变量读取 API Key 与 Base URL；缺失时自动降级为 Mock 实现，保证前端不挂。
遵循 STACK §1.4 缓存友好原则：系统提示词固定前置，可变内容仅追加尾部。

使用标准库 urllib 实现 HTTP 请求，不引入额外依赖。
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any

from app.core.provider import AIProvider


# --- Configuration ---
AI_API_KEY = os.environ.get("JZO_AI_API_KEY", "").strip()
AI_BASE_URL = os.environ.get("JZO_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
AI_MODEL = os.environ.get("JZO_AI_MODEL", "gpt-3.5-turbo")
AI_TIMEOUT = int(os.environ.get("JZO_AI_TIMEOUT_SECONDS", "30"))


class OpenAICompatibleProvider(AIProvider):
    """OpenAI 兼容格式的 Provider 实现。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: int | None = None,
    ):
        self._api_key = api_key or AI_API_KEY
        self._base_url = (base_url or AI_BASE_URL).rstrip("/")
        self._default_model = default_model or AI_MODEL
        self._timeout = timeout or AI_TIMEOUT
        self._mock_mode = not bool(self._api_key)

    @property
    def provider_name(self) -> str:
        return "openai-compatible" if not self._mock_mode else "mock"

    @property
    def is_mock(self) -> bool:
        return self._mock_mode

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """调用大模型完成对话。

        Args:
            system_prompt: 固定系统提示词（缓存友好前缀）。
            user_message: 用户输入或上下文变量部分。
            model: 可选覆盖模型名，默认取配置值。
            temperature: 采样温度，0-2。
            max_tokens: 最大输出 token 数。
            stream: 是否流式响应（当前版本不支持，保留接口）。

        Returns:
            {
                "content": "<模型输出文本>",
                "usage": {"prompt_tokens": N, "completion_tokens": M},
                "model": "<实际使用模型>",
                "mock": true|false
            }

        Raises:
            urllib.error.HTTPError: 当非 Mock 模式且请求失败时。
        """
        if self._mock_mode:
            return _mock_chat(system_prompt, user_message)

        target_model = model or self._default_model
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if stream:
            payload["stream"] = True

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                body = response.read().decode("utf-8")
                result = json.loads(body)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"AI API error {exc.code}: {error_body}") from exc

        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = result.get("usage", {})

        return {
            "content": message.get("content", ""),
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
            "model": result.get("model", target_model),
            "mock": False,
        }


# --- Module-level singleton for backward compatibility ---
_default_provider = OpenAICompatibleProvider()


async def chat_completion(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    """向后兼容的模块级函数，委托给默认 Provider。"""
    return await _default_provider.chat_completion(
        system_prompt, user_message, model, temperature, max_tokens, stream
    )


def _mock_chat(system_prompt: str, user_message: str) -> dict[str, Any]:
    """Mock 实现：返回预设假数据，保持接口签名一致。"""
    lower_msg = user_message.lower()

    # Split agent: return question list directly
    if "拆题专家" in system_prompt or "split" in system_prompt.lower():
        content = json.dumps(
            [
                {
                    "id": "q1",
                    "type": "single_choice",
                    "stem": "已知集合 $A=\\{x \\mid x^2 - 3x + 2 = 0\\}$，则 $A$ 的元素个数为（  ）",
                    "options": {"A": "$0$", "B": "$1$", "C": "$2$", "D": "$3$"},
                    "answer": "C",
                    "difficulty": "basic",
                },
                {
                    "id": "q2",
                    "type": "fill_blank",
                    "stem": "若函数 $f(x) = \\ln(x+1)$，则 $f'(0) = $ ______。",
                    "answer": "$1$",
                    "difficulty": "medium",
                },
            ],
            ensure_ascii=False,
        )
    # Review agent: return quality checks
    elif "审题质检" in system_prompt or "review" in system_prompt.lower():
        content = json.dumps(
            {
                "checks": [
                    {"field": "answer", "status": "pass"},
                    {"field": "solution", "status": "warning", "detail": "解析略简"},
                ],
                "overall_score": 4,
                "note": "[Mock] 模拟审题质检",
            },
            ensure_ascii=False,
        )
    # Chat agent: return action based on keywords
    elif "拆分" in user_message or "split" in lower_msg:
        content = json.dumps(
            {
                "action": "split_paper",
                "page_range": [3, 5],
                "note": "[Mock] 模拟拆题指令解析",
            },
            ensure_ascii=False,
        )
    elif "审题" in user_message or "review" in lower_msg:
        content = json.dumps(
            {
                "checks": [
                    {"field": "answer", "status": "pass"},
                    {"field": "solution", "status": "warning", "detail": "解析略简"},
                ],
                "overall_score": 4,
                "note": "[Mock] 模拟审题质检",
            },
            ensure_ascii=False,
        )
    else:
        content = json.dumps(
            {
                "action": "clarify",
                "question": "请明确您的具体需求？",
                "note": "[Mock] 未识别到明确指令",
            },
            ensure_ascii=False,
        )

    return {
        "content": content,
        "usage": {"prompt_tokens": len(system_prompt) // 4, "completion_tokens": len(content) // 4},
        "model": "mock-agent-v1",
        "mock": True,
    }
