"""AI Provider 注册表：扫描本目录模块收集配置档，活跃项只由环境变量决定。

见 PLUGIN_SPEC §2.1：新增 Provider 只需在本目录放一个导出 ``profiles()`` 的模块，
无需改动底座。密钥与模型名一律来自环境变量（本机 ``.env``），禁止硬编码，
也不提供任何 UI 切换或落盘入口。
"""

from __future__ import annotations

import importlib
import os
import pkgutil
from dataclasses import dataclass
from typing import Callable

FALLBACK_NAME = "openai-compatible"


@dataclass(frozen=True)
class ProviderProfile:
    """一个可选的模型供应商配置档。

    ``env_prefix`` 是该档环境变量名前缀（如 ``JZO_BAILIAN_``），供配置面板
    把用户亲手填入的 Key / Base URL / 模型名写回本机 .env 时定位变量名；
    密钥仍然只存在环境变量与本机 .env，永不入库、永不下发前端。
    """

    name: str
    label: str
    base_url: str
    api_key: str
    model: str
    env_prefix: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key) and bool(self.base_url)


def env_value(name: str) -> str:
    return os.environ.get(name, "").strip()


def registry() -> dict[str, ProviderProfile]:
    """扫描本目录模块，返回 名称 -> 配置档。每次调用都重读环境变量。"""
    profiles: dict[str, ProviderProfile] = {}
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        exporter: Callable[[], list[ProviderProfile]] | None = getattr(module, "profiles", None)
        for profile in exporter() if callable(exporter) else ():
            if profile.name in profiles:
                raise ValueError(f"Provider 名称冲突：{profile.name}")
            profiles[profile.name] = profile
    return profiles


def active_name() -> str:
    """环境变量 ``JZO_AI_PROVIDER`` 决定活跃档；缺省取默认档，默认档缺席取首个注册档。"""
    profiles = registry()
    from_env = env_value("JZO_AI_PROVIDER")
    if from_env in profiles:
        return from_env
    if FALLBACK_NAME in profiles:
        return FALLBACK_NAME
    return next(iter(profiles), "")


def active_profile() -> ProviderProfile:
    profiles = registry()
    return profiles[active_name()]
