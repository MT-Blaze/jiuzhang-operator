"""AI Provider 注册表：扫描本目录模块收集配置档，并按工作区持久化活跃项。

见 PLUGIN_SPEC §2.1：新增 Provider 只需在本目录放一个导出 ``profiles()`` 的模块，
无需改动底座与前端。密钥与模型名一律来自环境变量，禁止在本目录硬编码。
"""

from __future__ import annotations

import importlib
import json
import os
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.core.config import settings

CONFIG_KEY = "provider"
FALLBACK_NAME = "openai-compatible"


@dataclass(frozen=True)
class ProviderProfile:
    """一个可选的模型供应商配置档。"""

    name: str
    label: str
    base_url: str
    api_key: str
    model: str

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


def _config_path() -> Path:
    return settings.config_path


def _read_config() -> dict[str, object]:
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_config(patch: dict[str, str]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    document = _read_config()
    document.update(patch)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def active_name() -> str:
    """环境变量 > 工作区配置 > 默认档；默认档缺席时取首个已注册档。"""
    profiles = registry()
    from_env = env_value("JZO_AI_PROVIDER")
    if from_env in profiles:
        return from_env
    stored = _read_config().get(CONFIG_KEY)
    if isinstance(stored, str) and stored in profiles:
        return stored
    if FALLBACK_NAME in profiles:
        return FALLBACK_NAME
    return next(iter(profiles), "")


def set_active_name(name: str) -> None:
    """把活跃档写入当前工作区配置；名称未注册时拒绝。"""
    if name not in registry():
        raise KeyError(f"未注册的 Provider：{name}")
    _write_config({CONFIG_KEY: name})


def active_profile() -> ProviderProfile:
    profiles = registry()
    return profiles[active_name()]
