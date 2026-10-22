"""AI Provider 抽象接口规范。

所有模型供应商（OpenAI、百炼、硅基流动等）必须实现此接口，
确保插件化替换与多工作区隔离。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """AI 模型提供者抽象基类。

    子类必须实现 chat_completion 方法，支持同步/异步调用。
    """

    @abstractmethod
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
        """执行对话补全。

        Args:
            system_prompt: 系统提示词（固定前缀，缓存友好）。
            user_message: 用户消息或上下文变量部分。
            model: 可选覆盖模型名。
            temperature: 采样温度，0-2。
            max_tokens: 最大输出 token 数。
            stream: 是否流式响应。

        Returns:
            {
                "content": "<模型输出文本>",
                "usage": {"prompt_tokens": N, "completion_tokens": M},
                "model": "<实际使用模型>",
                "mock": true|false
            }
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回提供者名称，用于日志与诊断。"""
        ...

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """返回是否处于 Mock 降级模式。"""
        ...
