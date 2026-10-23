"""OpenAI 兼容的大模型客户端（Provider 实现）。

配置一律来自 ``app.core.providers`` 的注册表（密钥只走环境变量 / 仓库根 .env）；
配置档缺席密钥时自动降级为 Mock 实现，保证前端不挂。
遵循 STACK §1.4 缓存友好原则：系统提示词固定前置，可变内容仅追加尾部。

使用标准库 urllib 实现 HTTP 请求，不引入额外依赖。
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from typing import Any

from app.core import providers
from app.core.provider import AIProvider

DEFAULT_BASE_URL = "https://api.openai.com/v1"
AI_TIMEOUT = int(os.environ.get("JZO_AI_TIMEOUT_SECONDS", "30"))


class OpenAICompatibleProvider(AIProvider):
    """OpenAI 兼容格式的 Provider 实现。"""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        default_model: str = "",
        timeout: int | None = None,
        label: str = "openai-compatible",
    ):
        self._api_key = (api_key or "").strip()
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._default_model = default_model
        self._label = label
        self._timeout = timeout or AI_TIMEOUT
        self._mock_mode = not bool(self._api_key)

    @property
    def provider_name(self) -> str:
        return self._label if not self._mock_mode else "mock"

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
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """调用大模型完成对话。

        Args:
            system_prompt: 固定系统提示词（缓存友好前缀）。
            user_message: 用户输入或上下文变量部分。
            model: 可选覆盖模型名，默认取配置值。
            temperature: 采样温度，0-2。
            max_tokens: 最大输出 token 数。
            stream: 是否流式响应（当前版本不支持，保留接口）。
            tools: OpenAI Function Calling 工具定义数组。
            tool_choice: ``"auto"`` / ``"none"`` 或指定函数。

        Returns:
            {
                "content": "<模型输出文本>",
                "tool_calls": [{"id", "type", "function": {"name", "arguments"}}],
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
        if not target_model:
            raise ValueError(f"Provider「{self._label}」未配置模型名（检查对应 *_MODEL 环境变量）。")
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
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"

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

        tool_calls: list[dict[str, Any]] = []
        for call in message.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            function = call.get("function") or {}
            if not isinstance(function, dict) or not function.get("name"):
                continue
            tool_calls.append(
                {
                    "id": str(call.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(function.get("name")),
                        "arguments": function.get("arguments") or "{}",
                    },
                }
            )

        return {
            "content": message.get("content") or "",
            "tool_calls": tool_calls,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
            "model": result.get("model", target_model),
            "mock": False,
        }


# --- Provider resolution (active profile wins at call time) ---
def get_client(name: str | None = None) -> OpenAICompatibleProvider:
    """按注册表配置档构造客户端；``name`` 为 None 时取当前活跃档。"""
    if name is None:
        profile = providers.active_profile()
    else:
        profile = providers.registry()[name]
    configured = profile.is_configured
    return OpenAICompatibleProvider(
        api_key=profile.api_key if configured else "",
        base_url=profile.base_url or DEFAULT_BASE_URL,
        default_model=profile.model,
        label=profile.name,
    )


async def chat_completion(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    stream: bool = False,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """向后兼容的模块级函数，委托给当前活跃 Provider。"""
    return await get_client().chat_completion(
        system_prompt,
        user_message,
        model,
        temperature,
        max_tokens,
        stream,
        tools=tools,
        tool_choice=tool_choice,
    )


_PANEL_ROW_RE = re.compile(
    r"^- ([a-z][a-z0-9_]{0,15})（([^）]{1,24})）：可选 ([^；]+)；", re.M
)
_PANEL_CHANGE_RE = re.compile(r"(改成|改为|调成|换成|切到|换到|调整为)")
_PANEL_GRADE_RE = re.compile(r"(高一|高二|高三)")


def _mock_panel_params(system_prompt: str, user_message: str) -> dict[str, Any] | None:
    """Mock 也认右侧面板：用户点名面板里的可选值时，返回 update_params。

    双向操控不能只在真实模型下可验——缺密钥降级时链路必须照样走得通。
    """
    if "## 右侧插件面板" not in system_prompt:
        return None
    if not _PANEL_CHANGE_RE.search(user_message):
        return None
    if not _PANEL_GRADE_RE.search(user_message) and not re.search(
        r"(基础|中档|压轴|新定义|全部)", user_message
    ):
        return None
    labels: dict[str, str] = {}
    params: dict[str, str] = {}
    for row in _PANEL_ROW_RE.finditer(system_prompt):
        key, label, options_text = row.group(1), row.group(2), row.group(3)
        labels[key] = label
        for option in [item.strip() for item in options_text.split("/") if item.strip()]:
            if option != "全部" and option in user_message:
                params[key] = option
    if not params:
        return None
    described = "、".join(
        "%s「%s」" % (labels.get(key, key), value) for key, value in sorted(params.items())
    )
    return {
        "action": "update_params",
        "params": params,
        "message": "[Mock] 好，右侧面板已切到：" + described + "。",
    }


def _mock_chat(system_prompt: str, user_message: str) -> dict[str, Any]:
    """Mock 实现：返回预设假数据，保持接口签名一致。"""
    lower_msg = user_message.lower()

    # Split agent: return question list directly。
    # 只认拆题 Agent 的专属前缀：对话提示词里含 "split_paper" 动作名，
    # 用 "split" 子串判断会把普通对话误当成拆题。
    if "拆题专家" in system_prompt:
        content = json.dumps(
            [
                {
                    "id": "q1",
                    "type": "single_choice",
                    "stem": "已知集合 $A=\\{x \\mid x^2 - 3x + 2 = 0\\}$，则 $A$ 的元素个数为（  ）",
                    "options": {"A": "$0$", "B": "$1$", "C": "$2$", "D": "$3$"},
                    "answer": "C",
                    "difficulty": "L1",
                },
                {
                    "id": "q2",
                    "type": "fill_blank",
                    "stem": "若函数 $f(x) = \\ln(x+1)$，则 $f'(0) = $ ______。",
                    "answer": "$1$",
                    "difficulty": "L2",
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
    elif (panel_params := _mock_panel_params(system_prompt, user_message)) is not None:
        content = json.dumps(panel_params, ensure_ascii=False)
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
        "tool_calls": [],
        "usage": {"prompt_tokens": len(system_prompt) // 4, "completion_tokens": len(content) // 4},
        "model": "mock-agent-v1",
        "mock": True,
    }
