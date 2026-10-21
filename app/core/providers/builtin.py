"""内置 Provider 配置档。

密钥与模型名只从环境变量读取（由 ``app/__init__._load_local_env`` 从仓库根 ``.env``
装载），本文件禁止出现任何密钥明文，也禁止硬编码模型版本号（STACK §1.4）。
"""

from __future__ import annotations

from app.core.providers import ProviderProfile, env_value

OPENAI_COMPATIBLE = "openai-compatible"
BAILIAN = "bailian"
SILICONFLOW = "siliconflow"


def profiles() -> list[ProviderProfile]:
    return [
        ProviderProfile(
            name=OPENAI_COMPATIBLE,
            label="OpenAI 兼容（默认）",
            base_url=env_value("JZO_AI_BASE_URL"),
            api_key=env_value("JZO_AI_API_KEY"),
            model=env_value("JZO_AI_MODEL"),
        ),
        ProviderProfile(
            name=BAILIAN,
            label="阿里百炼兼容接口",
            base_url=env_value("JZO_BAILIAN_BASE_URL"),
            api_key=env_value("JZO_BAILIAN_API_KEY"),
            model=env_value("JZO_BAILIAN_MODEL"),
        ),
        ProviderProfile(
            name=SILICONFLOW,
            label="硅基流动",
            base_url=env_value("JZO_SILICONFLOW_BASE_URL"),
            api_key=env_value("JZO_SILICONFLOW_API_KEY"),
            model=env_value("JZO_SILICONFLOW_MODEL"),
        ),
    ]
