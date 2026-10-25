"""工作区（Workspace）管理 API。

支持多 SQLite 库隔离，每个工作区拥有独立的数据库、上传资源和配置。
"""

from __future__ import annotations

import base64
import binascii
import json
import secrets
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core import bank as core_bank
from app.core import bank_provider, host_restart, workspace_removal
from app.core.config import (
    default_database_path,
    root_data_dir,
    settings,
    switch_workspace,
    workspace_storage_dir,
)
from app.core.db import init_db
from app.core.security import require_write_token
from app.core.workspace_bootstrap import ensure_workspace_layout
router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

DEFAULT_WORKSPACE_ID = "default"
DEFAULT_WORKSPACE_NAME = "默认工作区"
def _provider_id() -> str:
    # 工作区下拉里「当前题库」显示的是**活跃 provider** 的题目数（PLUGIN_SPEC §2.6.1）。
    # 这里不写死官方 core-bank 的 id——第三方题库被选为 provider 后，
    # 计数、建库、挂载都跟着走同一个解析结果。
    return bank_provider.resolve()["plugin_id"]


def _bank_db_for(workspace_id: str | None) -> Path:
    """按工作区推导活跃题库的物理库路径，不改全局 settings，供只读计数。"""
    base = root_data_dir()
    data_dir = base / "workspaces" / workspace_id if workspace_id else base
    return data_dir / "banks" / f"{_provider_id()}.db"


def _bank_question_count(workspace_id: str | None) -> int:
    """只读统计某工作区题库的题目数；库还不存在（没打开过）算 0，绝不为计数去建库。

    升级过渡（军令 #20）：引擎库还没生成、但该区只有旧 core-bank 库时，
    按旧库计数——否则工作区下拉会把老师攒的题显示成 0（库里其实一题没少）。
    """
    path = _bank_db_for(workspace_id)
    if not path.is_file():
        base = root_data_dir()
        data_dir = base / "workspaces" / workspace_id if workspace_id else base
        for legacy_id in bank_provider.LEGACY_PROVIDER_IDS:
            candidate = data_dir / "banks" / f"{legacy_id}.db"
            if candidate.is_file():
                path = candidate
                break
    if not path.is_file():
        return 0
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return 0
    try:
        return int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
    except sqlite3.Error:
        return 0
    finally:
        con.close()


def active_textbook_id(plugin_id: str) -> str:
    """当前工作区生效的教材版本：工作区偏好优先，失效或未选时回落默认版本。

    大纲树按这个 ID 只展示对应版本的目录节点；考向并集不受影响。
    老库没有 textbooks 表时如实回空串，让调用方按「不过滤」处理。
    """
    workspaces = _load_workspaces()
    current_id = settings.workspace_id or DEFAULT_WORKSPACE_ID
    entry = next((item for item in workspaces if item.get("id") == current_id), None)
    chosen = str((entry or {}).get("textbook_id") or "").strip()
    items = core_bank.textbooks(plugin_id)
    known = {str(item["id"]) for item in items}
    if chosen and chosen in known:
        return chosen
    return next((str(item["id"]) for item in items if item.get("is_default")), "")


def _request_port(request: Request) -> int:
    """重启脚本要绑回用户当前访问的端口，不能盲信默认 8000。"""
    port = request.url.port
    if isinstance(port, int) and 0 < port < 65536:
        return port
    return int(settings.port)


def _provision_core_bank() -> int:
    """切/建工作区后立即落地该区的题库物理库，并回其题目数。

    新工作区（非 default）走 ensure_bank 的 schema 兜底 → 空库；default 若有本机种子则复制、
    否则同样建空；从旧 core-bank 升级过来的工作区由 ensure_bank 一次性复制旧库。
    任何建库异常都不该让切换/新建整条失败——题目读不到时前端会再触发。
    """
    try:
        core_bank.ensure_bank(_provider_id())
    except Exception:  # noqa: BLE001 - 兜底：建库失败不阻断工作区操作，交由后续懒加载重试
        pass
    return _bank_question_count(settings.workspace_id)


class WorkspaceCreateRequest(BaseModel):
    """创建工作区请求体。

    ``textbook_id`` 随新建一并登记：切库要重启进程，再补一刀 ``/textbook``
    极可能撞在进程退出的当口，偏好就悄悄丢了。
    """
    name: str = Field(..., min_length=1, description="工作区名称")
    textbook_id: str = Field("", max_length=32, description="教材版本ID，tb_ 前缀；空串=跟随默认")


class WorkspaceTextbookRequest(BaseModel):
    """为工作区选定教材版本；传空串表示「跟随默认版本」。"""
    workspace_id: str = Field(..., min_length=1, description="目标工作区ID")
    textbook_id: str = Field("", max_length=32, description="教材版本ID，tb_ 前缀；空串=跟随默认")


class WorkspaceSwitchRequest(BaseModel):
    """切换工作区请求体。"""
    workspace_id: str = Field(..., min_length=1, description="目标工作区ID")


class WorkspaceDeleteRequest(BaseModel):
    """删除工作区请求体：必须逐字输入确认语，服务端再校验一次。"""
    confirm: str = Field("", description="必须为「确认删除」")


class WorkspaceImportRequest(BaseModel):
    """导入本地题库：把一个 .db 挂载成一个新的独立工作区。

    不用 multipart（底座不引 python-multipart，STACK §0）：前端把文件读成 base64 传上来。
    """
    name: str = Field(..., min_length=1, description="新工作区名称")
    db_base64: str = Field(..., min_length=1, description="题库 .db 文件内容的 base64")


IMPORT_MAX_DB_BYTES = 64 * 1024 * 1024          # 单个导入库上限 64 MB
_SQLITE_MAGIC = b"SQLite format 3\x00"
# 七张业务表齐全才认作 core-bank 库（bank/schema.sql 冻结口径）；缺表即拒，不静默建空。
_REQUIRED_TABLES = {
    "questions", "topics", "sources", "schools",
    "question_topics", "question_sources", "topic_notes",
}


def _workspace_config_path() -> Path:
    """工作区登记表永远住在根 data 目录，不随当前工作区漂移。"""
    return root_data_dir() / "workspaces.json"


def _load_workspaces() -> list[dict[str, Any]]:
    """Load workspace registry from disk.

    ``workspaces.json`` 是人可以直接改的文件。``id`` 是工作区的身份：没有它，条目既切不过去、
    删不掉，也会在左栏下拉里挂成一行选不动的假工作区（计数还会错算成默认区的），
    所以读的时候按「是不是一个工作区」判掉；``name`` 之类展示字段缺失由调用方 ``.get()`` 兜。
    """
    path = _workspace_config_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [
        item
        for item in data
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]
    ]


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
    has_default = any(w.get("id") == DEFAULT_WORKSPACE_ID for w in workspaces)
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
        entry["question_count"] = _bank_question_count(
            None if entry.get("id") == DEFAULT_WORKSPACE_ID else entry.get("id")
        )

    return {
        "workspaces": workspaces,
        "current": current_id,
    }


@router.post("/switch", summary="切换工作区")
async def switch_workspace_endpoint(
    payload: WorkspaceSwitchRequest, request: Request,
) -> dict[str, Any]:
    """切换到指定工作区，然后**重启底座**加载该区的插件与配置。

    工作区的插件目录、plugin_state、.env 都是目录级隔离的；只切指针不重启，
    界面会拿旧区的插件去读新区的库。所以这里写完指针就调度一次性重启脚本，
    回包带 ``restarting`` 与当前 ``boot_id``，前端据此轮询新进程。
    ``JZO_RESTART_DISABLED=1``（单测/受控环境）下退回旧的活切换语义。
    """
    workspace_id = payload.workspace_id
    workspaces = _load_workspaces()

    if workspace_id == "default":
        target = None
    else:
        # Verify workspace exists
        workspace_ids = [w.get("id") for w in workspaces]
        if workspace_id not in workspace_ids:
            raise HTTPException(status_code=404, detail=f"工作区 {workspace_id} 不存在")
        target = workspace_id

    # 先准备脚本再写指针：脚本生成失败时指针不动，不出现「切了库却没重启」的半截状态。
    prepared = host_restart.prepare_restart(port=_request_port(request))
    switch_workspace(target)

    # Reinitialize database for new workspace（新进程启动时也会做一次，这里同步建好）
    init_db()
    question_count = _provision_core_bank()
    if prepared is not None:
        host_restart.launch_restart(prepared)

    resolved_id = workspace_id or "default"
    # 名字读不到就退回 id：此时库已经切完、重启已经发起，不能再用 KeyError 把回包炸掉。
    resolved_name = next(
        (w.get("name") or resolved_id for w in workspaces if w.get("id") == resolved_id),
        DEFAULT_WORKSPACE_NAME if resolved_id == DEFAULT_WORKSPACE_ID else resolved_id,
    )

    return {
        "workspace_id": resolved_id,
        "name": resolved_name,
        "database": str(settings.database_path),
        "question_count": question_count,
        "is_active": True,
        "restarting": prepared is not None,
        "boot_id": host_restart.boot_id(),
    }


@router.post("", summary="创建工作区")
async def create_workspace(payload: WorkspaceCreateRequest, request: Request) -> dict[str, Any]:
    """创建新工作区并切换过去（同样需要重启以装配该区插件）。"""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="工作区名称不能为空")

    textbook_id = (payload.textbook_id or "").strip()
    if textbook_id and core_bank.TEXTBOOK_ID_RE.fullmatch(textbook_id) is None:
        raise HTTPException(status_code=400, detail="教材版本 ID 不合法")
    if textbook_id:
        # 版本清单来自**切换前**的当前库（下拉就是它喂的）；
        # 库还没落地（空环境/新装）时没有并集登记表可查，不拦。
        try:
            known = {str(item["id"]) for item in core_bank.textbooks(_provider_id())}
        except (core_bank.BankError, sqlite3.Error):
            known = set()
        if known and textbook_id not in known:
            raise HTTPException(status_code=400, detail="该教材版本不在当前题库的并集登记表里")

    # Generate unique ID
    workspace_id = f"ws_{secrets.token_hex(8)}"
    
    # Create workspace directory structure. 必须按根 data 解析，
    # 不能拼在当前工作区目录下（否则会生成 workspaces/<旧区>/workspaces/<新区>）。
    ensure_workspace_layout(workspace_id)

    prepared = host_restart.prepare_restart(port=_request_port(request))

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
    entry = {
        "id": workspace_id,
        "name": name,
        "created_at": "auto",  # Would use datetime in production
        "database": str(settings.database_path),
    }
    if textbook_id:
        entry["textbook_id"] = textbook_id
    workspaces.append(entry)
    _save_workspaces(workspaces)

    # 新工作区立刻落地一个空的 core-bank 库（非 default 走 schema 兜底，不复制 default 真题）
    question_count = _provision_core_bank()
    if prepared is not None:
        host_restart.launch_restart(prepared)

    return {
        "id": workspace_id,
        "name": name,
        "question_count": question_count,
        "switched": True,
        "restarting": prepared is not None,
        "boot_id": host_restart.boot_id(),
    }


@router.post("/import", summary="导入本地 .db 为一个新工作区（数据备份/恢复入口）")
async def import_workspace(payload: WorkspaceImportRequest, request: Request) -> dict[str, Any]:
    """把老师选择的一个本地 .db 挂载成独立工作区，并切换过去。

    校验顺序：base64 解码 → 体积上限 → SQLite 魔数 → 七表齐全。任一不过即 400 且不留半成品文件。
    落位到 ``data/workspaces/<wsid>/banks/<活跃 provider>.db``，与 v0.7.2 的工作区物理隔离口径一致。
    """
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="工作区名称不能为空")
    try:
        raw = base64.b64decode(payload.db_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="题库数据不是合法的 base64") from exc
    if not raw:
        raise HTTPException(status_code=400, detail="题库文件为空")
    if len(raw) > IMPORT_MAX_DB_BYTES:
        raise HTTPException(status_code=413, detail="题库文件超过 64 MB 上限")
    if not raw.startswith(_SQLITE_MAGIC):
        raise HTTPException(status_code=400, detail="所选文件不是有效的 SQLite 数据库")

    workspace_id = f"ws_{secrets.token_hex(8)}"
    workspace_dir = workspace_storage_dir(workspace_id) / "banks"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    # 落成的文件名跟活跃 provider 一致：工作区「当前题库」读的就是这个路径。
    # 导入接口本身按 core-bank 七表校验，所以只有官方库当 provider 时它才有意义
    # （第三方 provider 接的是自己的存储，见 PLUGIN_SPEC §2.6.1 的当前边界）。
    db_path = workspace_dir / f"{_provider_id()}.db"
    db_path.write_bytes(raw)

    try:
        con = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        db_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="数据库无法打开") from exc
    try:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = _REQUIRED_TABLES - tables
        if missing:
            raise HTTPException(
                status_code=400,
                detail="所选库缺少 core-bank 业务表：" + "、".join(sorted(missing)) + "，导入被拒绝",
            )
        try:
            question_count = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        except sqlite3.Error:
            question_count = 0
    except HTTPException:
        try:
            con.close()
        except sqlite3.Error:
            pass
        try:
            db_path.unlink()
        except OSError:
            pass
        # 回收半成品工作区：先删 banks 子目录再删其父，且都容错（可能已被占/已空）
        for leftover in (workspace_dir, workspace_dir.parent):
            try:
                leftover.rmdir()
            except OSError:
                pass
        raise
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass

    # 库校验全部通过后才生成该区的插件目录与空状态，失败路径不留半成品。
    ensure_workspace_layout(workspace_id)
    prepared = host_restart.prepare_restart(port=_request_port(request))
    switch_workspace(workspace_id)
    init_db()
    workspaces = _load_workspaces()
    workspaces.append({
        "id": workspace_id,
        "name": name,
        "created_at": "import",
        "database": str(settings.database_path),
    })
    _save_workspaces(workspaces)
    if prepared is not None:
        host_restart.launch_restart(prepared)

    return {
        "id": workspace_id,
        "name": name,
        "question_count": question_count,
        "switched": True,
        "restarting": prepared is not None,
        "boot_id": host_restart.boot_id(),
    }


@router.post("/textbook", summary="为某个工作区选定教材版本")
async def set_workspace_textbook(payload: WorkspaceTextbookRequest) -> dict[str, Any]:
    """把用户选的教材版本登记进工作区档案（v0.8.2 多版本地基的控制台入口）。

    与 switch/create 同口径：本机单用户开放，不占一次性写令牌那套轮换经济
    （令牌留给题目增删改）。这里只改工作区档案里的一个偏好字段，
    不碰任何题库数据；大纲树按所选版本过滤是下一棒的活。
    """
    workspaces = _load_workspaces()
    entry = next((w for w in workspaces if w.get("id") == payload.workspace_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="工作区不存在")
    textbook_id = (payload.textbook_id or "").strip()
    if textbook_id and core_bank.TEXTBOOK_ID_RE.fullmatch(textbook_id) is None:
        raise HTTPException(status_code=400, detail="教材版本 ID 不合法")
    if textbook_id:
        try:
            known = {item["id"] for item in core_bank.textbooks(_provider_id())}
        except core_bank.BankError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if textbook_id not in known:
            raise HTTPException(status_code=400, detail="该教材版本不在当前题库的并集登记表里")
    entry["textbook_id"] = textbook_id
    _save_workspaces(workspaces)
    return {"workspace_id": payload.workspace_id, "textbook_id": textbook_id}


@router.delete(
    "/{workspace_id}",
    summary="删除工作区（整目录进系统回收站，并写审计）",
    dependencies=[Depends(require_write_token)],
)
async def delete_workspace(
    workspace_id: str,
    payload: WorkspaceDeleteRequest = Body(...),
) -> dict[str, Any]:
    """删除指定工作区及其所有数据。

    删除是最后一道兜底：用户必须在弹窗里逐字输入「确认删除」，服务端再验一次；
    工作区目录整体进系统回收站，绝不 ``unlink`` / ``rmtree``。
    """
    if payload.confirm != workspace_removal.CONFIRM_TEXT:
        raise HTTPException(status_code=400, detail="请输入「确认删除」后再执行")
    if workspace_id == "default":
        raise HTTPException(status_code=400, detail="不能删除默认工作区")
    if settings.workspace_id == workspace_id:
        raise HTTPException(status_code=400, detail="不能删除当前活跃工作区，请先切换到其他工作区")

    try:
        result = workspace_removal.recycle_workspace(workspace_id)
    except workspace_removal.WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except workspace_removal.WorkspaceRemovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    workspaces = _load_workspaces()
    remaining = [w for w in workspaces if w.get("id") != workspace_id]
    if len(remaining) != len(workspaces):
        _save_workspaces(remaining)

    return {"deleted": workspace_id, **result}

