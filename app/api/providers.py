"""AI Provider 端点：列出注册表、切换活跃配置档。

切换是写操作，必须过 ``X-JZO-Token``（STACK §0）。密钥永不下发，前端只看到
「是否已配置」与接口主机名。
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core import providers
from app.core.ai_client import get_client
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
    profile = providers.registry().get(body.name)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"未注册的 Provider：{body.name}")
    providers.set_active_name(profile.name)
    client = get_client(profile.name)
    return ProviderSwitchResponse(
        active=profile.name, model=profile.model, mock=client.is_mock
    )
