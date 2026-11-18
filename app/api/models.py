"""模型注册表的 HTTP 口子：只读聚合＋MinerU 一键装＋配置勾选代笔。

注册表状态每次现算（目录 × 运行时体检），不出网、不碰库；下载与指派
动作走既有的 layout.model_download 与 API 配置中心。新增两条写口都带
写令牌：MinerU 安装只由老师点击发起（国内镜像）；启用/停用＋默认选择
代笔进插件目录 model_prefs.toml，绝不落宿主 data/。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.ingest import mineru_setup, model_prefs, registry
from app.core.security import require_write_token

router = APIRouter(tags=["models"])


@router.get("/api/models/registry", summary="模型目录 × 运行时三态（ready/degraded/blocked）")
def models_registry() -> dict[str, Any]:
    return registry.status()


@router.get("/api/models/mineru/status", summary="本地 MinerU 安装进度（只读）")
def mineru_status() -> dict[str, Any]:
    return mineru_setup.status()


@router.post(
    "/api/models/mineru/install",
    status_code=202,
    summary="一键安装本地 MinerU（engines/mineru/ 隔离环境，国内镜像）",
    dependencies=[Depends(require_write_token)],
)
def mineru_install() -> dict[str, Any]:
    try:
        return mineru_setup.start_install()
    except mineru_setup.MineruSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/models/prefs",
    summary="启用/停用＋默认选择（代笔进插件目录，不落 data/）",
    dependencies=[Depends(require_write_token)],
)
def models_prefs(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return model_prefs.save(payload, [item["id"] for item in registry.catalog()])
    except model_prefs.PrefsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc