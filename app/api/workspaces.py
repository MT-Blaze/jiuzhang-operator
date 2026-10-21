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

from app.core.config import settings, switch_workspace
from app.core.db import init_db

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def _workspace_config_path() -> Path:
    """Return path to workspace registry file."""
    return Path(settings.data_dir) / "workspaces.json"


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
    has_default = any(w["id"] == "default" for w in workspaces)
    if not has_default:
        workspaces.insert(0, {
            "id": "default",
            "name": "默认工作区",
            "created_at": "system",
            "database": str(settings.database_path),
        })
        _save_workspaces(workspaces)
    
    current_id = settings.workspace_id or "default"
    
    return {
        "workspaces": workspaces,
        "current": current_id,
    }


@router.post("/switch", summary="切换工作区")
async def switch_workspace_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """切换到指定工作区。"""
    workspace_id = payload.get("workspace_id")
    
    if workspace_id == "default":
        switch_workspace(None)
    else:
        # Verify workspace exists
        workspaces = _load_workspaces()
        workspace_ids = [w["id"] for w in workspaces]
        if workspace_id not in workspace_ids:
            raise HTTPException(status_code=404, detail=f"工作区 {workspace_id} 不存在")
        
        switch_workspace(workspace_id)
    
    # Reinitialize database for new workspace
    init_db()
    
    return {
        "workspace_id": workspace_id or "default",
        "database": str(settings.database_path),
    }


@router.post("", summary="创建工作区")
async def create_workspace(payload: dict[str, Any]) -> dict[str, Any]:
    """创建新工作区并切换到该工作区。"""
    name = payload.get("name", "").strip()
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
