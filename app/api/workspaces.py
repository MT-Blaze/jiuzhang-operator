"""工作区（Workspace）管理 API。

支持多 SQLite 库隔离，每个工作区拥有独立的数据库、上传资源和配置。
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import default_database_path, settings, switch_workspace
from app.core.db import init_db

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

DEFAULT_WORKSPACE_ID = "default"
DEFAULT_WORKSPACE_NAME = "默认工作区"


class WorkspaceCreateRequest(BaseModel):
    """创建工作区请求体。"""
    name: str = Field(..., min_length=1, description="工作区名称")


class WorkspaceSwitchRequest(BaseModel):
    """切换工作区请求体。"""
    workspace_id: str = Field(..., min_length=1, description="目标工作区ID")


def _workspace_config_path() -> Path:
    """Return path to workspace registry file (always in root data dir)."""
    # Use PROJECT_ROOT/data as the base, not affected by workspace switching
    from app.core.config import PROJECT_ROOT
    base = Path(os.environ.get("JZO_DATA_DIR", str(PROJECT_ROOT / "data")))
    return base / "workspaces.json"


def _load_workspaces() -> list[dict[str, Any]]:
    """Load workspace registry from disk."""
    path = _workspace_config_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_workspaces(workspaces: list[dict[str, Any]]) -> None:
    """Save workspace registry to disk."""
    path = _workspace_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(workspaces, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("", summary="列出所有工作区")
async def list_workspaces() -> dict[str, Any]:
    """返回所有已注册的工作区列表及当前活跃工作区。"""
    workspaces = _load_workspaces()
    
    # Ensure default workspace exists
    has_default = any(w["id"] == DEFAULT_WORKSPACE_ID for w in workspaces)
    if not has_default:
        workspaces.insert(0, {
            "id": DEFAULT_WORKSPACE_ID,
            "name": DEFAULT_WORKSPACE_NAME,
            "created_at": "system",
            "database": str(default_database_path()),
        })
        _save_workspaces(workspaces)
    
    current_id = settings.workspace_id or DEFAULT_WORKSPACE_ID

    # is_active 是前端下拉框选中当前工作区的唯一依据；此前后端只回顶层 current，
    # 前端却逐项查 ws.is_active，导致选择器永远显示不出真正活跃的库。这里补齐。
    for entry in workspaces:
        if entry.get("id") == DEFAULT_WORKSPACE_ID:
            # default 的库路径按当前 config 现算，纠正历史登记里写错的 questions.db。
            entry["database"] = str(default_database_path())
        entry["is_active"] = entry.get("id") == current_id

    return {
        "workspaces": workspaces,
        "current": current_id,
    }


@router.post("/switch", summary="切换工作区")
async def switch_workspace_endpoint(payload: WorkspaceSwitchRequest) -> dict[str, Any]:
    """切换到指定工作区。"""
    workspace_id = payload.workspace_id
    workspaces = _load_workspaces()

    if workspace_id == "default":
        switch_workspace(None)
    else:
        # Verify workspace exists
        workspace_ids = [w["id"] for w in workspaces]
        if workspace_id not in workspace_ids:
            raise HTTPException(status_code=404, detail=f"工作区 {workspace_id} 不存在")

        switch_workspace(workspace_id)

    # Reinitialize database for new workspace
    init_db()

    resolved_id = workspace_id or "default"
    resolved_name = next(
        (w["name"] for w in workspaces if w["id"] == resolved_id),
        DEFAULT_WORKSPACE_NAME if resolved_id == DEFAULT_WORKSPACE_ID else resolved_id,
    )

    return {
        "workspace_id": resolved_id,
        "name": resolved_name,
        "database": str(settings.database_path),
        "is_active": True,
    }


@router.post("", summary="创建工作区")
async def create_workspace(payload: WorkspaceCreateRequest) -> dict[str, Any]:
    """创建新工作区并切换到该工作区。"""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="工作区名称不能为空")
    
    # Generate unique ID
    workspace_id = f"ws_{secrets.token_hex(8)}"
    
    # Create workspace directory structure
    workspace_dir = Path(settings.data_dir) / "workspaces" / workspace_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize database for new workspace
    old_workspace = settings.workspace_id
    try:
        switch_workspace(workspace_id)
        init_db()
    except Exception as exc:
        switch_workspace(old_workspace)
        raise HTTPException(status_code=500, detail=f"工作区初始化失败: {exc}") from exc
    
    # Register workspace
    workspaces = _load_workspaces()
    workspaces.append({
        "id": workspace_id,
        "name": name,
        "created_at": "auto",  # Would use datetime in production
        "database": str(settings.database_path),
    })
    _save_workspaces(workspaces)
    
    return {
        "id": workspace_id,
        "name": name,
        "switched": True,
    }


@router.delete("/{workspace_id}", summary="删除工作区")
async def delete_workspace(workspace_id: str) -> dict[str, Any]:
    """删除指定工作区及其所有数据。"""
    if workspace_id == "default":
        raise HTTPException(status_code=400, detail="不能删除默认工作区")
    
    # Check if trying to delete current workspace
    if settings.workspace_id == workspace_id:
        raise HTTPException(status_code=400, detail="不能删除当前活跃工作区，请先切换到其他工作区")
    
    # Remove from registry
    workspaces = _load_workspaces()
    workspaces = [w for w in workspaces if w["id"] != workspace_id]
    _save_workspaces(workspaces)
    
    # Delete workspace directory
    workspace_dir = Path(settings.data_dir) / "workspaces" / workspace_id
    if workspace_dir.exists():
        import shutil
        shutil.rmtree(workspace_dir)
    
    return {"deleted": workspace_id}
