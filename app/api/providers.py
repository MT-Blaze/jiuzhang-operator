"""AI Provider 端点：列出注册表、切换活跃配置档、面板保存配置与连通性测试。

切换、保存与测试都是写操作，必须过 ``X-JZO-Token``（STACK §0）。密钥永不下发，
前端只看到「是否已配置」与接口主机名。面板填入的密钥写回本机 .env 并直写
环境变量，热生效、不重启（AGENTS §5：密钥只走环境变量 / 本机 .env）。
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.core import providers
from app.core.ai_client import get_client
from app.core.provider_config import (
    ProviderConfigError,
    save_profile_config,
    test_connectivity,
)
from app.core.security import require_write_token

router = APIRouter(prefix="/api/providers", tags=["providers"])


class ProviderSummary(BaseModel):
    name: str
    label: str
    model: str
    host: str
    configured: bool
    mock: bool
    active: bool


class ProviderListResponse(BaseModel):
    active: str
    providers: list[ProviderSummary]


class ProviderSwitchRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="目标 Provider 名称")


class ProviderSwitchResponse(BaseModel):
    active: str
    model: str
    mock: bool


class ProviderConfigRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="目标 Provider 名称")
    api_key: str | None = Field(default=None, max_length=512, description="API Key，写入本机 .env，不回显")
    base_url: str | None = Field(default=None, max_length=512, description="OpenAI 兼容接口地址")
    model: str | None = Field(default=None, max_length=128, description="模型名")


class ProviderTestRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="目标 Provider 名称")


class ProviderTestResponse(BaseModel):
    ok: bool
    name: str
    host: str
    status_code: int | None = None
    detail: str


def _summary(profile: providers.ProviderProfile, active: str) -> ProviderSummary:
    client = get_client(profile.name)
    return ProviderSummary(
        name=profile.name,
        label=profile.label,
        model=profile.model,
        host=urlparse(profile.base_url).netloc if profile.base_url else "",
        configured=profile.is_configured,
        mock=client.is_mock,
        active=profile.name == active,
    )


@router.get("", response_model=ProviderListResponse, summary="列出 Provider 配置档")
def list_providers() -> ProviderListResponse:
    active = providers.active_name()
    return ProviderListResponse(
        active=active,
        providers=[_summary(profile, active) for profile in providers.registry().values()],
    )


@router.post(
    "/active",
    response_model=ProviderSwitchResponse,
    summary="切换活跃 Provider",
    dependencies=[Depends(require_write_token)],
)
def switch_provider(body: ProviderSwitchRequest = Body(...)) -> ProviderSwitchResponse:
    profile = _registered_or_404(body.name)
    providers.set_active_name(profile.name)
    client = get_client(profile.name)
    return ProviderSwitchResponse(
        active=profile.name, model=profile.model, mock=client.is_mock
    )


def _registered_or_404(name: str) -> providers.ProviderProfile:
    profile = providers.registry().get(name)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"未注册的 Provider：{name}")
    return profile


@router.post(
    "/config",
    response_model=ProviderSummary,
    summary="保存面板填入的 API Key / Base URL / 模型名（写本机 .env，热生效）",
    dependencies=[Depends(require_write_token)],
)
def save_config(body: ProviderConfigRequest = Body(...)) -> ProviderSummary:
    """密钥只落本机 .env 与环境变量，响应里永不回显（STACK §1.6）。"""
    profile = _registered_or_404(body.name)
    try:
        updated = save_profile_config(
            profile, api_key=body.api_key, base_url=body.base_url, model=body.model
        )
    except ProviderConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _summary(updated, providers.active_name())


@router.post(
    "/test",
    response_model=ProviderTestResponse,
    summary="对指定 Provider 发一次只读连通性测试（GET /models）",
    dependencies=[Depends(require_write_token)],
)
async def test_provider(body: ProviderTestRequest = Body(...)) -> ProviderTestResponse:
    """带令牌不是因为改数据，而是因为这是底座替用户出网的口子（同索引拉取口径）。

    同步 urllib 调用放线程池执行，避免阻塞事件循环。
    """
    profile = _registered_or_404(body.name)
    result = await run_in_threadpool(test_connectivity, profile)
    return ProviderTestResponse(name=profile.name, **result)  # type: ignore[arg-type]
