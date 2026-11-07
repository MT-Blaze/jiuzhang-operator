"""备份子系统的本机配置：开关、本地目录、WebDAV 凭据。

三条铁律写死在这里：
- 凭据只落 ``data/workspaces/<id>/backup.toml``，**绝不进备份包**（包里没有钥匙）；
- 给前端的视图里密码只报「有没有」，绝不回明文；
- 网盘备份依赖本地备份：用户亲手关掉本地时，网盘必须一起关，绝不允许
  「无本地文件可传」的空转开关。

路径口径与「哪些文件不许进包」见 backup_files.py。
"""

from __future__ import annotations

from typing import Any

from app.core import state_store
from app.core.backup_files import (
    backup_settings_path,
    current_workspace_id,
    default_local_dir,
    validate_local_dir,
)


def default_backup_settings(workspace_id: str | None = None) -> dict[str, Any]:
    ws_id = workspace_id or current_workspace_id()
    return {
        "local_enabled": False,
        "webdav_enabled": False,
        "local_dir": str(default_local_dir(ws_id)),
        "url": "",
        "username": "",
        "password": "",
        "remote_dir": "jiuzhang-backups",
        "last_upload": {},
    }


def load_backup_settings(workspace_id: str | None = None) -> dict[str, Any]:
    ws_id = workspace_id or current_workspace_id()
    defaults = default_backup_settings(ws_id)
    raw = state_store.load_table(backup_settings_path(ws_id))
    for key in ("url", "username", "password", "remote_dir", "local_dir"):
        if isinstance(raw.get(key), str):
            defaults[key] = raw[key].strip() if key != "password" else raw[key]
    defaults["local_enabled"] = bool(raw.get("local_enabled"))
    defaults["webdav_enabled"] = bool(raw.get("webdav_enabled")) and defaults["local_enabled"]
    if isinstance(raw.get("last_upload"), dict):
        defaults["last_upload"] = raw["last_upload"]
    if not defaults["local_dir"]:
        defaults["local_dir"] = str(default_local_dir(ws_id))
    return defaults


def save_backup_settings(values: dict[str, Any], workspace_id: str | None = None) -> dict[str, Any]:
    ws_id = workspace_id or current_workspace_id()
    current = load_backup_settings(ws_id)
    if isinstance(values.get("last_upload"), dict):
        current["last_upload"] = values["last_upload"]
    for key in ("url", "username", "remote_dir", "local_dir"):
        if key in values and isinstance(values[key], str):
            current[key] = values[key].strip()
    if isinstance(values.get("password"), str) and values["password"] != "••••••••":
        current["password"] = values["password"]
    if "local_dir" in values:
        current["local_dir"] = str(validate_local_dir(values.get("local_dir"), ws_id))
    local_off = "local_enabled" in values and not bool(values["local_enabled"])
    if "local_enabled" in values:
        current["local_enabled"] = bool(values["local_enabled"])
    if "webdav_enabled" in values:
        current["webdav_enabled"] = bool(values["webdav_enabled"])
    if local_off:
        # 用户亲手关掉本地备份：网盘一起关，绝不允许「无本地文件可传」的空转开关。
        current["webdav_enabled"] = False
    else:
        current = normalize_toggles(current)
    _write_settings(current, ws_id)
    return current


def record_upload_result(result: dict[str, Any], workspace_id: str | None = None) -> dict[str, Any]:
    ws_id = workspace_id or current_workspace_id()
    current = load_backup_settings(ws_id)
    current["last_upload"] = dict(result)
    _write_settings(current, ws_id)
    return current


def _write_settings(values: dict[str, Any], ws_id: str) -> None:
    state_store.save(backup_settings_path(ws_id), values)


def normalize_toggles(values: dict[str, Any]) -> dict[str, Any]:
    """网盘备份依赖本地备份；关掉本地时网盘必须一起关。"""
    result = dict(values)
    result["local_enabled"] = bool(result.get("local_enabled"))
    result["webdav_enabled"] = bool(result.get("webdav_enabled"))
    if result["webdav_enabled"]:
        result["local_enabled"] = True
    if not result["local_enabled"]:
        result["webdav_enabled"] = False
    return result


def public_backup_settings(values: dict[str, Any]) -> dict[str, Any]:
    """给前端的视图：密码只报「有没有」，绝不回明文。"""
    out = dict(values)
    password = str(out.pop("password", "") or "")
    out["password_set"] = bool(password)
    out["password_masked"] = "••••••••" if password else ""
    out.pop("last_upload", None)
    return out
