"""备份子系统的成品层：Zstd 打包、本地保留策略与清单读取。

打包只装 manifest 点名的文件——读一份 WAL 库会在同目录落下 ``-wal``/``-shm`` 边车，
早先「整目录 rglob」的写法会把边车一起装进包，而 manifest 里没有它们，
恢复侧的「清单外文件」门禁当场判废，整个包一份都恢复不出来。

写成品一律「临时文件 + 原子替换」：中途崩溃不会留下半份包或半份 manifest。
本地保留只删本工具命名的 ``backup_*.zst`` / ``manifest_*.json``，别的文件一个都不碰。

快照与 manifest 的生成见 backup_manifest.py；路径与禁令见 backup_files.py；配置见 backup_settings.py。
"""

from __future__ import annotations

import json
import os
import tarfile
from pathlib import Path
from typing import Any

from compression import zstd

from app.core.backup_files import (
    BACKUP_FILE_RE,
    BACKUP_STEM_RE,
    MANIFEST_FILE_RE,
    BackupError,
    current_workspace_id,
    default_local_dir,
    sha256_file,
    stamp_now,
    validate_local_dir,
)
from app.core.backup_manifest import workspace_snapshot
from app.core.backup_settings import load_backup_settings


def package_snapshot(
    stage_dir: Path,
    manifest: dict[str, Any],
    out_dir: Path,
    stamp: str | None = None,
) -> dict[str, Any]:
    """把快照目录打成 ``backup_<stamp>.zst``（tar 流经 zstd 压缩）并写同名 manifest。

    **只装 manifest 点名的文件**：边车不进包，清单外不许有文件，缺一多一都当场拒。
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = stamp or stamp_now()
    if not BACKUP_STEM_RE.fullmatch(stamp):
        raise BackupError("备份时间戳格式非法")
    stage = Path(stage_dir).resolve()
    listed = [str(item["path"]) for item in (manifest.get("files") or [])]
    if not listed:
        raise BackupError("清单里没有任何文件，已拒绝打包")
    for rel in sorted(listed):
        path = (stage / rel).resolve()
        try:
            path.relative_to(stage)
        except ValueError as exc:
            raise BackupError(f"清单路径越界：{rel}") from exc
        if not path.is_file():
            raise BackupError(f"快照缺少文件：{rel}")
    package_path = out / f"backup_{stamp}.zst"
    manifest_path = out / f"manifest_{stamp}.json"
    temp_path = out / f".backup_{stamp}.part"
    try:
        with zstd.ZstdFile(temp_path, "wb", level=10) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for rel in sorted(listed):
                    archive.add(
                        stage / rel,
                        arcname=rel,
                        recursive=False,
                    )
        temp_path.replace(package_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        package_path.unlink(missing_ok=True)
        raise
    manifest = dict(manifest)
    manifest["package"] = {
        "filename": package_path.name,
        "sha256": sha256_file(package_path),
        "size": package_path.stat().st_size,
    }
    temp_manifest = out / f".manifest_{stamp}.part"
    temp_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp_manifest.replace(manifest_path)
    return {"package": package_path, "manifest_path": manifest_path, "manifest": manifest}


def create_local_backup(
    workspace_id: str | None = None,
    local_dir: str | os.PathLike[str] | None = None,
    keep: int = 3,
) -> dict[str, Any]:
    """生成一次本地备份，并按保留策略清理旧份。返回给前端的结果不含凭据。"""
    ws_id = workspace_id or current_workspace_id()
    out = validate_local_dir(local_dir, ws_id) if local_dir else validate_local_dir(
        load_backup_settings(ws_id).get("local_dir"), ws_id
    )
    with workspace_snapshot(ws_id) as (stage, manifest):
        result = package_snapshot(stage, manifest, out)
    deleted = prune_local_backups(out, keep=keep)
    return {
        "ok": True,
        "workspace_id": ws_id,
        "local_dir": str(out),
        "package": str(result["package"]),
        "package_name": result["package"].name,
        "manifest": str(result["manifest_path"]),
        "package_sha256": result["manifest"]["package"]["sha256"],
        "package_size": result["manifest"]["package"]["size"],
        "question_count": result["manifest"]["question_count"],
        "generated_at": result["manifest"]["generated_at"],
        "pruned": [path.name for path in deleted],
    }


def prune_local_backups(directory: str | os.PathLike[str], keep: int = 3) -> list[Path]:
    """只删本工具命名的 backup_*.zst / manifest_*.json，保留最近 keep 份。"""
    folder = Path(directory)
    if not folder.is_dir():
        return []
    keep = max(1, int(keep))
    backups = sorted(
        (path for path in folder.iterdir() if path.is_file() and BACKUP_FILE_RE.match(path.name)),
        key=lambda path: path.name,
        reverse=True,
    )
    kept_stems = {BACKUP_FILE_RE.match(path.name).group(1) for path in backups[:keep]}
    deleted: list[Path] = []
    for path in backups[keep:]:
        try:
            path.unlink()
            deleted.append(path)
        except OSError:
            continue
    for path in folder.iterdir():
        if not path.is_file():
            continue
        match = MANIFEST_FILE_RE.match(path.name)
        if match and match.group(1) not in kept_stems:
            try:
                path.unlink()
                deleted.append(path)
            except OSError:
                continue
    return deleted


def list_local_backups(
    directory: str | os.PathLike[str] | None = None,
    workspace_id: str | None = None,
) -> list[dict[str, Any]]:
    """列出本地备份（按时间倒序），只读 manifest，不拆包。"""
    ws_id = workspace_id or current_workspace_id()
    folder = Path(directory) if directory else Path(
        load_backup_settings(ws_id).get("local_dir") or default_local_dir(ws_id)
    )
    if not folder.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for package in sorted(folder.iterdir(), key=lambda path: path.name, reverse=True):
        match = BACKUP_FILE_RE.match(package.name) if package.is_file() else None
        if not match:
            continue
        stem = match.group(1)
        manifest_path = folder / f"manifest_{stem}.json"
        entry: dict[str, Any] = {
            "stem": stem,
            "package": package.name,
            "package_size": package.stat().st_size,
            "manifest": manifest_path.name,
            "ok": False,
            "error": "",
        }
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry["ok"] = True
            entry["workspace_id"] = manifest.get("workspace_id", "")
            entry["question_count"] = manifest.get("question_count", 0)
            entry["generated_at"] = manifest.get("generated_at", "")
            entry["package_sha256"] = (manifest.get("package") or {}).get("sha256", "")
            entry["file_count"] = len(manifest.get("files") or [])
            entry["image_count"] = len(manifest.get("images") or [])
            entry["plugin_count"] = len(manifest.get("plugins") or [])
        except (OSError, ValueError) as exc:
            entry["error"] = str(exc)
        entries.append(entry)
    return entries


def load_local_backup_manifest(
    stem: str,
    directory: str | os.PathLike[str] | None = None,
    workspace_id: str | None = None,
) -> tuple[dict[str, Any], Path]:
    """按 stem 读取本地 manifest 与包路径；stem 先过白名单，防路径拼接。"""
    if not isinstance(stem, str) or not BACKUP_STEM_RE.fullmatch(stem):
        raise BackupError("备份标识非法")
    ws_id = workspace_id or current_workspace_id()
    folder = Path(directory) if directory else Path(
        load_backup_settings(ws_id).get("local_dir") or default_local_dir(ws_id)
    )
    manifest_path = folder / f"manifest_{stem}.json"
    package_path = folder / f"backup_{stem}.zst"
    if not manifest_path.is_file() or not package_path.is_file():
        raise BackupError("该备份不存在或缺少包文件")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BackupError(f"manifest 无法读取：{exc}") from exc
    return manifest, package_path
