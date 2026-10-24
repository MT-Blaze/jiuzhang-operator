"""系统设置类端点：目前只有「启动行为」（打开软件先落在哪个界面）。

读写分开是刻意的：GET 供工作台启动路径调用，落在启动链上，绝不带写令牌、
绝不抛错；POST 是老师在设置页当场点【保存】，带本机写令牌，目标不合格
（形状非法 / 插件没装 / 已停用）直接 400，不落一个下次启动会静默回退的配置。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core import backup as backup_core
from app.core.startup_prefs import StartupRejected, resolve, set_target
from app.core.security import require_write_token

router = APIRouter(tags=["system"])


@router.get("/api/startup", summary="读取启动行为（含失效回退原因与候选插件清单）")
async def read_startup() -> dict[str, Any]:
    return resolve()


@router.post(
    "/api/startup",
    summary="保存启动行为（老师当场点保存才落盘）",
    dependencies=[Depends(require_write_token)],
)
def write_startup(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """同步函数不是省事：校验要扫 ``plugins/`` 目录、落盘要写文件，都是阻塞 IO，
    FastAPI 会把它放进线程池执行（与 ``/api/plugins/index`` 同款口径）。"""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    try:
        set_target(payload.get("target"))
    except StartupRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return resolve()


# ---------- 备份与恢复：设置页的宿主自有面板（军令 #17） ----------

ALLOWED_BACKUP_KEYS = {
    "local_enabled", "webdav_enabled", "local_dir",
    "url", "username", "password", "remote_dir",
}


def _backup_view() -> dict[str, Any]:
    ws_id = backup_core.current_workspace_id()
    config = backup_core.load_backup_settings(ws_id)
    view = backup_core.public_backup_settings(config)
    view["workspace_id"] = ws_id
    view["default_local_dir"] = str(backup_core.default_local_dir(ws_id))
    view["last_upload"] = config.get("last_upload") or {}
    view["local_backups"] = backup_core.list_local_backups(
        config.get("local_dir"), ws_id
    )
    return view


@router.get("/api/settings/backup", summary="读取当前工作区的备份面板")
async def read_backup() -> dict[str, Any]:
    return _backup_view()


@router.post(
    "/api/settings/backup/config",
    summary="保存本地/网盘开关与地址（凭据只落本机）",
    dependencies=[Depends(require_write_token)],
)
def write_backup_config(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    unknown = set(payload) - ALLOWED_BACKUP_KEYS
    if unknown:
        raise HTTPException(
            status_code=400, detail="不认识的备份字段：" + "、".join(sorted(unknown))
        )
    try:
        backup_core.save_backup_settings(payload)
    except backup_core.BackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _backup_view()


@router.post(
    "/api/settings/backup/run",
    summary="立即备份（先本地；网盘开关开启时上传同一份文件）",
    dependencies=[Depends(require_write_token)],
)
def run_backup() -> dict[str, Any]:
    ws_id = backup_core.current_workspace_id()
    config = backup_core.load_backup_settings(ws_id)
    if not config.get("local_enabled"):
        raise HTTPException(status_code=400, detail="请先开启【本地备份】")
    try:
        result = backup_core.create_local_backup(ws_id, config.get("local_dir"))
    except backup_core.BackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    upload: dict[str, Any] = {"ok": False, "skipped": True}
    if config.get("webdav_enabled"):
        try:
            from app.core import webdav

            upload = webdav.upload_backup(
                config, result["package"], result["manifest"]
            )
        except Exception as exc:  # noqa: BLE001 - 上传失败不吞本地备份，如实回报
            upload = {"ok": False, "error": str(exc)}
        upload["at"] = backup_core.now_iso()
        backup_core.record_upload_result(upload, ws_id)
    return {"ok": True, "local": result, "upload": upload, "backup": _backup_view()}


@router.get(
    "/api/settings/backup/local/{stem}",
    summary="读取某份本地备份的 manifest（恢复预览用）",
)
async def read_local_backup_manifest(stem: str) -> dict[str, Any]:
    try:
        manifest, package = backup_core.load_local_backup_manifest(stem)
    except backup_core.BackupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "source": "local",
        "stem": stem,
        "package": package.name,
        "manifest": manifest,
    }
