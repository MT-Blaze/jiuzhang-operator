"""备份子系统的一致性快照与 manifest。

SQLite 一律走 backup API 生成自包含快照，绝不直接复制 .db 主文件，
也不把 -wal / -shm 边车原样装包（边车语义已经并入快照）；manifest 描述快照里的
全部文件，供恢复页做勾选。

「逐题哈希」是这一层的核心承诺：行哈希按 PRAGMA table_info 的列序取全字段，
JSON 键排序后求 SHA-256，任何一次复算都必须得到同一串——不依赖 SELECT * 的偶然列序。
恢复侧靠它判定「题真的没少、也没被悄悄改过」。

文件清单与路径规则见 backup_files.py；打包与保留见 backup_package.py。
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.core.backup_files import (
    PLUGIN_ID_RE,
    SIDECAR_SUFFIXES,
    BackupError,
    backup_file_plan,
    category_of,
    current_workspace_id,
    is_sqlite,
    now_iso,
    sha256_file,
    workspace_dir,
)

MANIFEST_VERSION = 1


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
    for rel, source in backup_file_plan(ws_id):
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() == ".db" and is_sqlite(source):
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


def select_bank_db(stage: Path) -> Path | None:
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


def _digest_rows(rows: list[dict[str, Any]]) -> str:
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def plugins_inventory(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按插件目录汇总：id、文件数、字节数与目录摘要。

    目录摘要是对 ``[{path, sha256}]`` 排序后再求 SHA-256——任何一个文件动过，串必变；
    恢复时拿它复核整目录，比逐文件比对照多一道「清单没被篡改」的门禁。
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in files:
        if item.get("category") != "plugins":
            continue
        parts = str(item["path"]).split("/")
        if len(parts) < 4 or parts[0] != "ws" or parts[1] != "plugins":
            raise BackupError(f"插件条目路径非法：{item['path']}")
        groups.setdefault(parts[2], []).append(item)
    out: list[dict[str, Any]] = []
    for plugin_id, items in sorted(groups.items()):
        if not PLUGIN_ID_RE.fullmatch(plugin_id):
            raise BackupError(f"插件目录名非法：{plugin_id}")
        out.append({
            "id": plugin_id,
            "files": len(items),
            "bytes": sum(int(item["size"]) for item in items),
            "sha256": _digest_rows(
                [{"path": item["path"], "sha256": item["sha256"]} for item in items]
            ),
        })
    return out


def build_manifest(workspace_id: str, stage_dir: Path) -> dict[str, Any]:
    """从快照目录生成 manifest（package 哈希留空，等打包后回填）。

    ``manifest_version`` 仍是 1：阶段二只往 ``files`` 里**新增** ``ws/`` 条目与 ``plugins`` 汇总，
    旧包在新底座照样能验能恢复，不需要破坏性的版本号跳变。
    """
    stage = Path(stage_dir)
    files: list[dict[str, Any]] = []
    for path in sorted(stage.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(stage).as_posix()
        if path.name.endswith(SIDECAR_SUFFIXES):
            continue
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
    images_digest = _digest_rows(images)

    bank = select_bank_db(stage)
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
        "plugins": plugins_inventory(files),
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
    """按 manifest 复核目录里的文件；返回不匹配的清单（空表示全过）。

    ``root`` 是快照/解包临时区：那里 ``ws/`` 就是真子目录，不映射到本机工作区。
    """
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
