"""工作区删除兜底：整目录进系统回收站，并写审计日志（军令 #17 第五步）。

删除只认 ``data/workspaces/<ws_id>/`` 这一层：id 先过格式校验，路径
``resolve()`` 后必须落在 ``root_data_dir()/workspaces/`` 内，绝不外溢到
default 根目录、别的数据目录或 ``plugins/``。

底层一律走系统回收站（Windows 用 ``SHFileOperationW`` + ``FOF_ALLOWUNDO``），
禁止 ``unlink`` / ``rmtree``——老师删错库还能从回收站捞回来。

审计只记操作事实（时间、工作区 id、原路径、结果），不写题目、不写凭据。
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import root_data_dir

AUDIT_FILENAME = "deletion_audit.json"
CONFIRM_TEXT = "确认删除"
AUDIT_MAX_RECORDS = 500

_WORKSPACE_ID_RE = re.compile(r"^ws_[a-f0-9]{8,32}$")
_audit_lock = threading.Lock()
_LOCAL_TZ = timezone(timedelta(hours=8))


class WorkspaceRemovalError(Exception):
    """删除被拒或回收站调用失败。"""


class WorkspaceNotFound(WorkspaceRemovalError):
    pass


def now_iso() -> str:
    return datetime.now(_LOCAL_TZ).isoformat(timespec="seconds")


def workspace_path(workspace_id: str) -> Path:
    """解析并校验待删除目录；任何越界都抛 ``WorkspaceRemovalError``。"""
    if not isinstance(workspace_id, str) or not _WORKSPACE_ID_RE.fullmatch(workspace_id):
        raise WorkspaceRemovalError("工作区 id 非法")
    root = root_data_dir().resolve()
    base = (root / "workspaces").resolve()
    target = (base / workspace_id).resolve()
    if target == base or target.parent != base:
        raise WorkspaceRemovalError("删除路径越界，已拒绝")
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise WorkspaceRemovalError("删除路径越界，已拒绝") from exc
    if target.is_symlink():
        raise WorkspaceRemovalError("工作区目录是符号链接/联接点，已拒绝")
    if not target.is_dir():
        raise WorkspaceNotFound(f"工作区目录不存在：{workspace_id}")
    return target


def _shell_recycle(path: Path) -> None:
    """Windows：把单个目录整体移入系统回收站。"""
    if os.name != "nt":
        raise WorkspaceRemovalError("当前平台未提供系统回收站实现")
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    FO_DELETE = 3
    FOF_SILENT = 0x0004
    FOF_NOCONFIRMATION = 0x0010
    FOF_ALLOWUNDO = 0x0040
    FOF_NOERRORUI = 0x0400

    operation = SHFILEOPSTRUCTW()
    operation.hwnd = None
    operation.wFunc = FO_DELETE
    operation.pFrom = str(path) + "\0\0"
    operation.pTo = None
    operation.fFlags = FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI
    code = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    if code != 0:
        raise WorkspaceRemovalError(f"系统回收站调用失败（代码 {code}）")
    if operation.fAnyOperationsAborted:
        raise WorkspaceRemovalError("回收站操作被中止")
    if path.exists():
        raise WorkspaceRemovalError("回收站未移除工作区目录")


def send_to_recycle_bin(path: Path) -> None:
    """删除底层唯一出口；单测与探针都从这里观察/替换。"""
    _shell_recycle(Path(path))


def audit_path() -> Path:
    return root_data_dir() / AUDIT_FILENAME


def append_audit(record: dict[str, Any]) -> Path:
    """追加一条审计记录；文件只保留最近 ``AUDIT_MAX_RECORDS`` 条。"""
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _audit_lock:
        records: list[Any] = []
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    records = loaded
            except (OSError, ValueError):
                records = []
        records.append(record)
        if len(records) > AUDIT_MAX_RECORDS:
            records = records[-AUDIT_MAX_RECORDS:]
        fd, temp_name = tempfile.mkstemp(prefix=".deletion_audit-", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(records, handle, ensure_ascii=False, indent=2)
            os.replace(temp_name, path)
        except BaseException:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
    return path


def recycle_workspace(workspace_id: str) -> dict[str, Any]:
    """把工作区目录整体移入回收站，并记录审计结果。"""
    target = workspace_path(workspace_id)
    try:
        send_to_recycle_bin(target)
    except WorkspaceRemovalError as exc:
        append_audit({
            "time": now_iso(),
            "workspace_id": workspace_id,
            "path": str(target),
            "result": "failed",
            "detail": str(exc),
        })
        raise
    except OSError as exc:
        append_audit({
            "time": now_iso(),
            "workspace_id": workspace_id,
            "path": str(target),
            "result": "failed",
            "detail": str(exc),
        })
        raise WorkspaceRemovalError(f"删除失败：{exc}") from exc

    audit = append_audit({
        "time": now_iso(),
        "workspace_id": workspace_id,
        "path": str(target),
        "result": "success",
    })
    return {"workspace_id": workspace_id, "path": str(target), "audit": str(audit)}
