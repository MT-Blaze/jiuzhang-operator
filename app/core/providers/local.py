"""本地模型 Provider 配置档（Ollama 等，预留位）。

Ollama 自带 OpenAI 兼容接口（默认 ``http://127.0.0.1:11434/v1``），
不需要真密钥：API Key 一栏随手填个占位（如 ``ollama``）即可点亮。
密钥与地址仍只从环境变量 / 本机 .env 读取，本文件禁止硬编码。
"""

from __future__ import annotations

from app.core.providers import ProviderProfile, env_value

OLLAMA = "ollama"


def profiles() -> list[ProviderProfile]:
    return [
        ProviderProfile(
            name=OLLAMA,
            label="Ollama 本地模型",
            base_url=env_value("JZO_OLLAMA_BASE_URL"),
            api_key=env_value("JZO_OLLAMA_API_KEY"),
            model=env_value("JZO_OLLAMA_MODEL"),
            env_prefix="JZO_OLLAMA_",
        ),
    ]
