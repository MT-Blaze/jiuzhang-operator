"""当前工作区备份的数据层：一致性快照与 manifest。

边界（军令 #17）：
- 只认「当前工作区」；不自动备份、不联网、不碰插件代码目录；
- SQLite 一律走 backup API 生成自包含快照，绝不直接复制 .db 主文件，
  也不把 -wal / -shm 边车原样装包（边车语义已经并入快照）；
- manifest 只描述快照里的数据文件，供恢复页做勾选，不含凭据文件。

本模块不碰 HTTP、不做压缩、不写 UI；打包与上传见同目录其它模块。
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tarfile
import tempfile
from compression import zstd
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from app.core.config import root_data_dir, settings

MANIFEST_VERSION = 1
SQLITE_MAGIC = b"SQLite format 3\x00"
WORKSPACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")

BACKUP_STEM_RE = re.compile(r"^(\d{8}_\d{6}_\d{3})$")
BACKUP_FILE_RE = re.compile(r"^backup_(\d{8}_\d{6}_\d{3})\.zst$")
MANIFEST_FILE_RE = re.compile(r"^manifest_(\d{8}_\d{6}_\d{3})\.json$")

# 不属于「当前工作区数据」的宿主级文件：备份既不打包它们，恢复也不碰。
GLOBAL_FILES = {
    ".local_token",
    "workspaces.json",
    "plugin_state.json",
    "plugin_index_cache.json",
    "startup.json",
    "bank_provider.json",
    "backup_settings.json",
}
# 凭据文件可以备份到本机以外？不。它只属于本机配置，绝不进包。
SECRET_FILES = {"backup.json"}
# default 工作区的 data 根目录里还住着别的工作区与备份产物，必须整目录跳过。
DEFAULT_ROOT_SKIP_DIRS = {"workspaces", "backups", "audit"}
SIDECAR_SUFFIXES = (".db-wal", ".db-shm", ".db-journal")


class BackupError(Exception):
    """备份/快照失败；message 可直接回给前端。"""


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def stamp_now() -> str:
    current = datetime.now()
    return current.strftime("%Y%m%d_%H%M%S_") + f"{current.microsecond // 1000:03d}"


def current_workspace_id() -> str:
    return settings.workspace_id or "default"


def workspace_dir(workspace_id: str | None = None) -> Path:
    """工作区数据根；default 就是 root data 目录。"""
    ws_id = workspace_id or current_workspace_id()
    if not WORKSPACE_ID_RE.fullmatch(ws_id):
        raise BackupError("工作区 ID 非法")
    root = root_data_dir().resolve()
    target = root if ws_id == "default" else root / "workspaces" / ws_id
    resolved = target.resolve()
    if resolved != root and root not in resolved.parents:
        raise BackupError("工作区路径越界")
    return resolved


def backup_settings_path(workspace_id: str | None = None) -> Path:
    """凭据与开关落点：data/workspaces/<ws_id>/backup.json（含 default）。"""
    ws_id = workspace_id or current_workspace_id()
    if not WORKSPACE_ID_RE.fullmatch(ws_id):
        raise BackupError("工作区 ID 非法")
    root = root_data_dir().resolve()
    path = (root / "workspaces" / ws_id / "backup.json").resolve()
    if root not in path.parents:
        raise BackupError("备份配置路径越界")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sqlite(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(len(SQLITE_MAGIC)) == SQLITE_MAGIC
    except OSError:
        return False


def _skip_name(name: str) -> bool:
    lower = name.lower()
    if lower in GLOBAL_FILES or lower in SECRET_FILES:
        return True
    if lower.endswith(".pre-restore.bak") or lower.endswith(".tmp"):
        return True
    if BACKUP_FILE_RE.match(name) or MANIFEST_FILE_RE.match(name):
        return True
    return False


def iter_workspace_files(workspace_id: str | None = None) -> list[Path]:
    """扫描当前工作区的数据文件（绝对路径，已按相对路径排序）。

    跳过：宿主级状态文件、凭据文件、备份产物自身、SQLite 边车、
    default 根下的 workspaces/backups/audit 与 plugins 等代码目录。
    """
    root = workspace_dir(workspace_id)
    if not root.is_dir():
        return []
    skip_dirs = set(DEFAULT_ROOT_SKIP_DIRS) if root == root_data_dir().resolve() else set()
    found: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(
            name for name in dirs
            if name not in skip_dirs and not name.startswith(".")
        )
        for name in sorted(files):
            if _skip_name(name):
                continue
            if name.endswith(SIDECAR_SUFFIXES):
                continue
            path = Path(base) / name
            try:
                resolved = path.resolve()
                resolved.relative_to(root)
            except (OSError, ValueError):
                continue
            if resolved.is_file():
                found.append(resolved)
    return found


def _relative(path: Path, workspace_id: str | None = None) -> str:
    return path.relative_to(workspace_dir(workspace_id)).as_posix()


def category_of(relative: str) -> tuple[str, bool]:
    """返回 (分组, 是否必选)。题库与图片资产必选，其他文件默认勾选但可取消。"""
    if relative.endswith(".db"):
        return "bank", True
    if relative == "uploads" or relative.startswith("uploads/"):
        return "uploads", True
    return "other", False


def _jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes__": base64.b64encode(value).decode("ascii")}
    return value


def sqlite_snapshot(source: Path, target: Path) -> None:
    """用 SQLite backup API 落一份自包含快照（自动带上 WAL 里已提交的内容）。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True, timeout=15.0)
    try:
        dst = sqlite3.connect(target, timeout=15.0)
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()


def snapshot_workspace(workspace_id: str | None = None, stage_dir: Path | None = None) -> tuple[Path, dict[str, Any]]:
    """生成一致快照与 manifest；调用方负责 stage_dir 的生命周期。

    返回 ``(stage_dir, manifest)``。manifest 的 ``package.sha256`` 此时为空，
    由打包模块在写完成品后回填。
    """
    ws_id = workspace_id or current_workspace_id()
    root = workspace_dir(ws_id)
    if not root.is_dir():
        raise BackupError("当前工作区目录不存在")
    stage = Path(stage_dir) if stage_dir else Path(tempfile.mkdtemp(prefix="jzo-backup-"))
    stage.mkdir(parents=True, exist_ok=True)
    for source in iter_workspace_files(ws_id):
        rel = _relative(source, ws_id)
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() == ".db" and _is_sqlite(source):
            sqlite_snapshot(source, target)
        else:
            shutil.copy2(source, target)
    manifest = build_manifest(ws_id, stage)
    return stage, manifest


@contextmanager
def workspace_snapshot(workspace_id: str | None = None) -> Iterator[tuple[Path, dict[str, Any]]]:
    stage, manifest = snapshot_workspace(workspace_id)
    try:
        yield stage, manifest
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _select_bank_db(stage: Path) -> Path | None:
    """挑出当前工作区的题库库：活跃 provider 优先，其次任意 banks/*.db。"""
    wanted = ""
    try:
        from app.core import bank_provider

        wanted = bank_provider.resolve().get("plugin_id") or ""
    except Exception:  # noqa: BLE001 - 发现层异常不该阻断备份
        wanted = ""
    if wanted:
        candidate = stage / "banks" / f"{wanted}.db"
        if candidate.is_file():
            return candidate
    for candidate in sorted((stage / "banks").glob("*.db")):
        if candidate.is_file():
            return candidate
    host_db = stage / "jiuzhang.db"
    if host_db.is_file():
        return host_db
    return None


def _has_questions(path: Path) -> bool:
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10.0)
    except sqlite3.Error:
        return False
    try:
        row = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='questions'"
        ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False
    finally:
        con.close()


def question_hashes(db_path: Path) -> tuple[int, dict[str, str], int]:
    """返回 (题目数, {题目 id: 规范化行哈希}, user_version)。

    行哈希按 PRAGMA table_info 的列序取全字段，JSON 键排序后求 SHA-256，
    任何一次复算都必须得到同一串；不依赖 SELECT * 的偶然列序。
    """
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=10.0)
    try:
        user_version = int(con.execute("PRAGMA user_version").fetchone()[0])
        if not _has_table(con, "questions"):
            return 0, {}, user_version
        columns = [row[1] for row in con.execute("PRAGMA table_info(questions)")]
        rows = con.execute("SELECT * FROM questions ORDER BY id").fetchall()
        hashes: dict[str, str] = {}
        for row in rows:
            payload = {column: _jsonable(row[index]) for index, column in enumerate(columns)}
            canonical = json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            hashes[str(row[columns.index("id")])] = hashlib.sha256(canonical).hexdigest()
        return len(rows), hashes, user_version
    finally:
        con.close()


def _has_table(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def build_manifest(workspace_id: str, stage_dir: Path) -> dict[str, Any]:
    """从快照目录生成 manifest（package 哈希留空，等打包后回填）。"""
    stage = Path(stage_dir)
    files: list[dict[str, Any]] = []
    for path in sorted(stage.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(stage).as_posix()
        category, required = category_of(rel)
        files.append({
            "path": rel,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "category": category,
            "required": required,
        })
    images = [
        {"path": item["path"], "size": item["size"], "sha256": item["sha256"]}
        for item in files if item["category"] == "uploads"
    ]
    images_digest = hashlib.sha256(
        json.dumps(images, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    bank = _select_bank_db(stage)
    question_count = 0
    hashes: dict[str, str] = {}
    user_version = 0
    library: dict[str, Any] = {"plugin_id": "", "path": "", "sha256": "", "user_version": 0}
    if bank is not None and _has_questions(bank):
        question_count, hashes, user_version = question_hashes(bank)
        rel_bank = bank.relative_to(stage).as_posix()
        library = {
            "plugin_id": bank.stem,
            "path": rel_bank,
            "sha256": sha256_file(bank),
            "user_version": user_version,
        }

    return {
        "manifest_version": MANIFEST_VERSION,
        "workspace_id": workspace_id,
        "schema_version": user_version,
        "library": library,
        "question_count": question_count,
        "question_hashes": hashes,
        "images": images,
        "images_hash": images_digest,
        "files": files,
        "generated_at": now_iso(),
        "host_version": _host_version(),
        "package": {
            "filename": "",
            "sha256": "",
            "size": 0,
        },
    }


def _host_version() -> str:
    try:
        from app import __version__

        return str(__version__)
    except Exception:  # noqa: BLE001 - 版本号只作附注
        return ""


def verify_manifest_hashes(manifest: dict[str, Any], root: Path) -> list[str]:
    """按 manifest 复核目录里的文件；返回不匹配的清单（空表示全过）。"""
    problems: list[str] = []
    for item in manifest.get("files") or []:
        path = (Path(root) / str(item.get("path") or "")).resolve()
        try:
            path.relative_to(Path(root).resolve())
        except ValueError:
            problems.append(f"{item.get('path')}: 路径越界")
            continue
        if not path.is_file():
            problems.append(f"{item.get('path')}: 文件缺失")
            continue
        if path.stat().st_size != int(item.get("size") or 0):
            problems.append(f"{item.get('path')}: 大小不符")
            continue
        if sha256_file(path) != item.get("sha256"):
            problems.append(f"{item.get('path')}: 哈希不符")
            continue
    return problems


def manifest_question_hashes_ok(manifest: dict[str, Any], db_path: Path) -> bool:
    """逐题哈希可复算：给定库重算后必须与 manifest 完全一致。"""
    count, hashes, _ = question_hashes(db_path)
    return count == int(manifest.get("question_count") or 0) and hashes == (
        manifest.get("question_hashes") or {}
    )


# ---------- Zstd 打包与本地备份 ----------

def default_local_dir(workspace_id: str | None = None) -> Path:
    return root_data_dir().resolve() / "backups" / (workspace_id or current_workspace_id())


def validate_local_dir(value: str | os.PathLike[str] | None, workspace_id: str | None = None) -> Path:
    """校验并准备本地备份目录：必须是绝对路径、可写，且不得落在 plugins/ 内。"""
    raw = str(value or "").strip()
    target = Path(os.path.expandvars(os.path.expanduser(raw))) if raw else default_local_dir(workspace_id)
    if not target.is_absolute():
        raise BackupError("本地备份地址必须是绝对路径")
    try:
        resolved = target.resolve()
    except OSError as exc:
        raise BackupError(f"本地备份地址无法解析：{exc}") from exc
    plugins_root = Path(settings.plugins_dir).resolve()
    if resolved == plugins_root or plugins_root in resolved.parents:
        raise BackupError("本地备份地址不得落在 plugins/ 目录内")
    try:
        resolved.mkdir(parents=True, exist_ok=True)
        probe = resolved / ".jzo-write-probe"
        probe.write_bytes(b"ok")
        probe.unlink()
    except OSError as exc:
        raise BackupError(f"本地备份目录不可写：{exc}") from exc
    return resolved


def package_snapshot(
    stage_dir: Path,
    manifest: dict[str, Any],
    out_dir: Path,
    stamp: str | None = None,
) -> dict[str, Any]:
    """把快照目录打成 ``backup_<stamp>.zst``（tar 流经 zstd 压缩）并写同名 manifest。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = stamp or stamp_now()
    if not BACKUP_STEM_RE.fullmatch(stamp):
        raise BackupError("备份时间戳格式非法")
    package_path = out / f"backup_{stamp}.zst"
    manifest_path = out / f"manifest_{stamp}.json"
    temp_path = out / f".backup_{stamp}.part"
    try:
        with zstd.ZstdFile(temp_path, "wb", level=10) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in sorted(Path(stage_dir).rglob("*")):
                    if not path.is_file():
                        continue
                    archive.add(
                        path,
                        arcname=path.relative_to(stage_dir).as_posix(),
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


# ---------- 本机备份配置（开关、路径、WebDAV 凭据） ----------

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
    path = backup_settings_path(ws_id)
    if not path.is_file():
        return defaults
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaults
    if not isinstance(raw, dict):
        return defaults
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
    path = backup_settings_path(ws_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
    return current


def record_upload_result(result: dict[str, Any], workspace_id: str | None = None) -> dict[str, Any]:
    ws_id = workspace_id or current_workspace_id()
    current = load_backup_settings(ws_id)
    current["last_upload"] = dict(result)
    path = backup_settings_path(ws_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
    return current


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
