"""当前工作区恢复：校验、覆盖前备份与可回滚落盘。

边界（军令 #17 第四步）：
- 只恢复当前工作区的数据文件；包内清单之外的文件一律不写，也不碰 plugins/；
- 先校验包哈希、逐文件哈希与逐题哈希，任何一项不过就拒绝，不落任何数据；
- 覆盖前为当前库、边车与将被覆盖的文件生成 ``.pre-restore.bak``，只留最近 1 份；
- 落盘用「先移到回滚区、再原子替换」的可回滚流程，失败整批还原，不留半恢复状态。

本模块不碰 HTTP；下载、勾选与二次确认由 API 层负责。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from compression import zstd

from app.core import backup
from app.core.config import root_data_dir

REQUIRED_CATEGORIES = {"bank", "uploads"}
CATEGORIES = {"bank", "uploads", "other"}
CONFIRM_TEXT = "确认恢复"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SIDECAR_SUFFIXES = backup.SIDECAR_SUFFIXES


class RestoreError(Exception):
    """恢复前置校验或落盘失败；message 可直接回给前端。"""


def safe_rel(value: Any) -> str:
    """把清单里的相对路径收紧成安全的 POSIX 相对路径。"""
    if not isinstance(value, str):
        raise RestoreError("文件路径非法")
    raw = value.strip()
    if (
        not raw
        or len(raw) > 500
        or "\\" in raw
        or "\x00" in raw
        or ":" in raw
        or raw.startswith("/")
    ):
        raise RestoreError("文件路径非法")
    parts = raw.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise RestoreError("文件路径越界")
    if raw.endswith(".pre-restore.bak") or raw.endswith(".tmp"):
        raise RestoreError("备份中出现了工具临时文件")
    if raw.startswith(".restore-"):
        raise RestoreError("备份中出现了工具回滚目录")
    return raw


def is_required(item: dict[str, Any]) -> bool:
    return bool(item.get("required")) or item.get("category") in REQUIRED_CATEGORIES


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RestoreError(message)


def validate_manifest(manifest: Any, workspace_id: str) -> None:
    """manifest 自述字段必须齐全且自洽；不通过就拒绝整个恢复。"""
    _require(isinstance(manifest, dict), "manifest 不是 JSON 对象")
    _require(
        int(manifest.get("manifest_version") or 0) == backup.MANIFEST_VERSION,
        "manifest 版本不受支持",
    )
    _require(manifest.get("workspace_id") == workspace_id, "备份不属于当前工作区，已拒绝")

    files = manifest.get("files")
    _require(isinstance(files, list) and bool(files), "备份清单为空")
    seen: set[str] = set()
    for item in files:
        _require(isinstance(item, dict), "备份清单条目非法")
        rel = safe_rel(item.get("path"))
        _require(rel not in seen, f"备份清单有重复路径：{rel}")
        seen.add(rel)
        size = item.get("size")
        _require(isinstance(size, int) and size >= 0, f"文件大小非法：{rel}")
        _require(SHA256_RE.fullmatch(str(item.get("sha256") or "")), f"文件哈希非法：{rel}")
        _require(item.get("category") in CATEGORIES, f"文件分组非法：{rel}")

    package = manifest.get("package")
    _require(isinstance(package, dict), "manifest 缺少包信息")
    _require(
        bool(backup.BACKUP_FILE_RE.fullmatch(str(package.get("filename") or ""))),
        "包文件名非法",
    )
    _require(SHA256_RE.fullmatch(str(package.get("sha256") or "")), "包哈希缺失")
    _require(isinstance(package.get("size"), int) and package["size"] > 0, "包大小非法")

    count = manifest.get("question_count")
    _require(isinstance(count, int) and count >= 0, "题目数非法")
    hashes = manifest.get("question_hashes")
    _require(isinstance(hashes, dict), "缺少逐题哈希")
    _require(len(hashes) == count, "逐题哈希数量与题目数不符")
    _require(all(SHA256_RE.fullmatch(str(value)) for value in hashes.values()), "逐题哈希非法")

    if count:
        library = manifest.get("library")
        _require(isinstance(library, dict), "缺少库标识")
        lib_path = safe_rel(library.get("path"))
        _require(lib_path in seen, "库文件不在备份清单中")
        item = next(entry for entry in files if entry["path"] == lib_path)
        _require(item["category"] == "bank", "库文件分组不是 bank")
        _require(
            not library.get("sha256") or library.get("sha256") == item["sha256"],
            "库哈希与文件清单不一致",
        )


def verify_package(package: str | Path, manifest: dict[str, Any]) -> None:
    """先验包：文件名、大小与整体 SHA-256 全部对上才允许拆包。"""
    path = Path(package)
    _require(path.is_file(), "备份包不存在")
    expected = manifest["package"]
    _require(path.name == expected["filename"], "备份包文件名与 manifest 不符")
    _require(path.stat().st_size == expected["size"], "备份包大小与 manifest 不符")
    _require(backup.sha256_file(path) == expected["sha256"], "备份包哈希不符，已拒绝恢复")


def extract_package(package: str | Path, stage_dir: str | Path) -> None:
    """只解普通文件；拒绝目录、链接与任何越界路径。"""
    stage = Path(stage_dir)
    stage.mkdir(parents=True, exist_ok=True)
    written: set[str] = set()
    with zstd.ZstdFile(package, "rb") as compressed:
        with tarfile.open(fileobj=compressed, mode="r") as archive:
            for member in archive.getmembers():
                _require(member.isfile(), f"备份包含非普通文件：{member.name}")
                rel = safe_rel(member.name)
                _require(rel not in written, f"备份包含重复文件：{rel}")
                written.add(rel)
                target = stage / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                _require(source is not None, f"备份文件读取失败：{rel}")
                with source, target.open("xb") as handle:
                    shutil.copyfileobj(source, handle)


def verify_stage(stage_dir: str | Path, manifest: dict[str, Any]) -> None:
    """拆包后逐文件复核大小与哈希，再复算逐题哈希与图片摘要。"""
    stage = Path(stage_dir)
    expected = {item["path"]: item for item in manifest["files"]}
    actual = {
        path.relative_to(stage).as_posix(): path
        for path in stage.rglob("*")
        if path.is_file()
    }
    for rel in expected:
        _require(rel in actual, f"备份缺少文件：{rel}")
    for rel in actual:
        _require(rel in expected, f"备份包含清单外文件：{rel}")
    for rel, item in expected.items():
        path = actual[rel]
        _require(path.stat().st_size == item["size"], f"文件大小不符：{rel}")
        _require(backup.sha256_file(path) == item["sha256"], f"文件哈希不符：{rel}")

    images = [
        {"path": item["path"], "size": item["size"], "sha256": item["sha256"]}
        for item in manifest["files"]
        if item["category"] == "uploads"
    ]
    digest = hashlib.sha256(
        json.dumps(images, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _require(digest == manifest.get("images_hash"), "图片清单摘要不符")

    if int(manifest.get("question_count") or 0):
        library = manifest["library"]
        db_path = stage / library["path"]
        count, hashes, user_version = backup.question_hashes(db_path)
        _require(count == manifest["question_count"], "逐题哈希复算：题目数不符")
        _require(hashes == manifest["question_hashes"], "逐题哈希复算不符")
        _require(user_version == int(library.get("user_version") or 0), "库结构版本不符")


def normalize_selection(manifest: dict[str, Any], files: Any) -> list[str]:
    """题库与图片资产强制包含；其余按前端勾选，缺省视为全选。"""
    known = {item["path"]: item for item in manifest["files"]}
    if files is None:
        selected = set(known)
    else:
        _require(isinstance(files, list), "勾选清单必须是数组")
        selected = set()
        for value in files:
            rel = safe_rel(value)
            _require(rel in known, f"勾选项不在备份清单里：{rel}")
            selected.add(rel)
    selected |= {rel for rel, item in known.items() if is_required(item)}
    _require(bool(selected), "没有勾选任何可恢复文件")
    return sorted(selected)


def preview_view(manifest: dict[str, Any]) -> dict[str, Any]:
    """给前端的预览：摘要 + 分组清单，不带逐题哈希。"""
    files = [
        {
            "path": item["path"],
            "size": item["size"],
            "category": item["category"],
            "required": is_required(item),
        }
        for item in manifest["files"]
    ]
    groups: dict[str, list[str]] = {"bank": [], "uploads": [], "other": []}
    for item in files:
        groups[item["category"]].append(item["path"])
    package = manifest.get("package") or {}
    library = manifest.get("library") or {}
    return {
        "workspace_id": manifest.get("workspace_id"),
        "schema_version": manifest.get("schema_version", library.get("user_version", 0)),
        "question_count": manifest.get("question_count", 0),
        "generated_at": manifest.get("generated_at", ""),
        "package_sha256": package.get("sha256", ""),
        "package_size": package.get("size", 0),
        "file_count": len(files),
        "image_count": len(groups["uploads"]),
        "library_plugin_id": library.get("plugin_id", ""),
        "files": files,
        "groups": groups,
        "required": [item["path"] for item in files if item["required"]],
    }


def prepare_restore(
    package: str | Path,
    manifest: Any,
    files: Any,
    workspace_id: str,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    """完整前置校验并解包到临时区；失败时清掉临时区，绝不触碰工作区。"""
    work = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="jzo-restore-"))
    stage = work / "stage"
    try:
        validate_manifest(manifest, workspace_id)
        verify_package(package, manifest)
        extract_package(package, stage)
        verify_stage(stage, manifest)
        selected = normalize_selection(manifest, files)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    return {
        "package": str(Path(package)),
        "stage": str(stage),
        "work_dir": str(work),
        "manifest": manifest,
        "selected": selected,
        "workspace_id": workspace_id,
    }


def prepare_local_restore(
    stem: str,
    files: Any,
    workspace_id: str,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    manifest, package = backup.load_local_backup_manifest(stem, None, workspace_id)
    return prepare_restore(package, manifest, files, workspace_id, work_dir)


def _bak_path(path: Path) -> Path:
    return Path(str(path) + ".pre-restore.bak")


def _atomic_copy(source: Path, target: Path) -> None:
    temp = target.with_name("." + target.name + ".restore-new")
    try:
        shutil.copy2(source, temp)
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def create_pre_restore_backup(workspace_id: str, selected: list[str]) -> list[str]:
    """当前库 + 边车 + 将被覆盖的文件各留一份 ``.pre-restore.bak``，只留最近 1 份。"""
    root = backup.workspace_dir(workspace_id)
    selected_set = set(selected)
    plans: list[tuple[str, Path]] = []
    for path in backup.iter_workspace_files(workspace_id):
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".db":
            plans.append(("sqlite" if backup._is_sqlite(path) else "copy", path))
        elif rel in selected_set:
            plans.append(("copy", path))

    generated: set[Path] = set()
    produced: list[str] = []
    for kind, source in plans:
        target = _bak_path(source)
        temp = Path(str(target) + ".tmp")
        try:
            if kind == "sqlite":
                backup.sqlite_snapshot(source, temp)
            else:
                shutil.copy2(source, temp)
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
        generated.add(target.resolve())
        produced.append(target.relative_to(root).as_posix())
        if source.suffix.lower() == ".db":
            for suffix in SIDECAR_SUFFIXES:
                sidecar = Path(str(source) + suffix)
                if not sidecar.is_file():
                    continue
                sidecar_bak = _bak_path(sidecar)
                sidecar_temp = Path(str(sidecar_bak) + ".tmp")
                try:
                    shutil.copy2(sidecar, sidecar_temp)
                    os.replace(sidecar_temp, sidecar_bak)
                finally:
                    sidecar_temp.unlink(missing_ok=True)
                generated.add(sidecar_bak.resolve())
                produced.append(sidecar_bak.relative_to(root).as_posix())

    # 上一轮可能覆盖过别的文件：只保留本轮这一套，其余旧副本删掉。
    # default 工作区的根是 data/，必须绕开别的工作区与备份目录。
    root_is_default = root == root_data_dir().resolve()
    skip_dirs = set(backup.DEFAULT_ROOT_SKIP_DIRS) if root_is_default else set()
    for base, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in skip_dirs and not name.startswith(".")]
        for name in names:
            if not name.endswith(".pre-restore.bak"):
                continue
            stale = Path(base) / name
            if stale.resolve() in generated:
                continue
            try:
                stale.unlink()
            except OSError:
                continue
    return produced


def _rollback(applied: list[tuple[Path, bool, Path | None]]) -> None:
    for target, had_original, saved in reversed(applied):
        try:
            if had_original and saved is not None and saved.exists():
                os.replace(saved, target)
            elif not had_original:
                target.unlink(missing_ok=True)
        except OSError:
            continue


def apply_restore(
    workspace_id: str,
    stage_dir: str | Path,
    selected: list[str],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """按勾选覆盖；任一步失败就把整批文件还原到恢复前。"""
    root = backup.workspace_dir(workspace_id).resolve()
    stage = Path(stage_dir)
    expected = {item["path"]: item for item in manifest["files"]}
    rollback = root / (".restore-rollback-" + secrets.token_hex(6))
    rollback.mkdir(parents=True, exist_ok=False)
    applied: list[tuple[Path, bool, Path | None]] = []
    restored: list[str] = []
    try:
        for rel in selected:
            item = expected.get(rel)
            _require(item is not None, f"勾选项不在备份清单里：{rel}")
            source = stage / rel
            _require(source.is_file(), f"临时区缺少文件：{rel}")
            _require(backup.sha256_file(source) == item["sha256"], f"待恢复文件哈希不符：{rel}")
            target = (root / rel).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise RestoreError(f"恢复目标越界：{rel}") from exc
            target.parent.mkdir(parents=True, exist_ok=True)

            if rel.endswith(".db"):
                for suffix in SIDECAR_SUFFIXES:
                    sidecar = Path(str(target) + suffix)
                    if sidecar.exists():
                        saved = rollback / (rel + suffix)
                        saved.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(sidecar, saved)
                        applied.append((sidecar, True, saved))

            saved_target = rollback / rel
            had_original = target.exists()
            if had_original:
                saved_target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, saved_target)
            applied.append((target, had_original, saved_target if had_original else None))
            if Path(rel).suffix.lower() == ".db":
                # 旧边车已移走；新库不配旧边车，避免 WAL 串库。
                for suffix in SIDECAR_SUFFIXES:
                    Path(str(target) + suffix).unlink(missing_ok=True)
            _atomic_copy(source, target)
            _require(backup.sha256_file(target) == item["sha256"], f"写回校验失败：{rel}")
            restored.append(rel)
    except BaseException:
        _rollback(applied)
        shutil.rmtree(rollback, ignore_errors=True)
        raise
    shutil.rmtree(rollback, ignore_errors=True)
    return {"restored": restored, "reload_required": True}


def execute_restore(workspace_id: str, plan: dict[str, Any]) -> dict[str, Any]:
    """二次确认后的执行：复核包与临时区，再备份、落盘、回报。"""
    manifest = plan["manifest"]
    selected = list(plan["selected"])
    verify_package(plan["package"], manifest)
    verify_stage(plan["stage"], manifest)
    pre_restore = create_pre_restore_backup(workspace_id, selected)
    result = apply_restore(workspace_id, plan["stage"], selected, manifest)
    result["pre_restore"] = pre_restore
    return result


def cleanup_plan(plan: dict[str, Any]) -> None:
    work = plan.get("work_dir")
    if work:
        shutil.rmtree(work, ignore_errors=True)
