"""模型注册表的 HTTP 口子：只读聚合，供插件配置页与引擎下拉取单源清单。

状态每次现算（目录 × 运行时体检），不出网、不碰库、不写盘；
下载与指派动作走既有的 layout.model_download 与 API 配置中心，这里不开新通道。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.ingest import registry

router = APIRouter(tags=["models"])


@router.get("/api/models/registry", summary="模型目录 × 运行时三态（ready/degraded/blocked）")
def models_registry() -> dict[str, Any]:
    return registry.status()