"""工作区重命名端点（2026-11-13）。

名称只是 ``workspaces.toml`` 里的展示字段：目录、数据库、插件状态都以 ``id`` 为身份，
所以重命名不重启底座、不碰任何数据目录。写操作照旧挂一次性令牌。
从 ``workspaces.py`` 拆出来只为守住单文件 500 行红线。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.workspaces import (
    DEFAULT_WORKSPACE_ID,
    _load_workspaces,
    _save_workspaces,
)
from app.core.config import settings
from app.core.security import require_write_token

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class WorkspaceRenameRequest(BaseModel):
    """重命名工作区：只改登记表里的展示名，不动目录、题库与当前指针。"""
    workspace_id: str = Field(..., min_length=1, description="目标工作区ID")
    name: str = Field(..., min_length=1, max_length=40, description="新名称")


@router.post(
    "/rename",
    summary="重命名工作区（只改展示名）",
    dependencies=[Depends(require_write_token)],
)
async def rename_workspace(payload: WorkspaceRenameRequest) -> dict[str, Any]:
    """改工作区在登记表里的名称；空名与超长名在模型层已拦，这里再挡纯空白。"""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="工作区名称不能为空")
    if len(name) > 40:
        raise HTTPException(status_code=400, detail="工作区名称不能超过 40 个字")

    workspaces = _load_workspaces()
    entry = next((w for w in workspaces if w.get("id") == payload.workspace_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="工作区不存在")
    entry["name"] = name
    _save_workspaces(workspaces)

    current_id = settings.workspace_id or DEFAULT_WORKSPACE_ID
    return {
        "workspace_id": payload.workspace_id,
        "name": name,
        "is_active": payload.workspace_id == current_id,
    }
