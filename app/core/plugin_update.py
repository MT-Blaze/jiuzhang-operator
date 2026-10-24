"""双轨更新（PLUGIN_SPEC §1.7 / ADR-006）：插件热更新 + 底座自更新。

三条铁律写死在本模块里，任何调用方都绕不过：

1. **不主动出网**：本模块自己一个请求都不发。只有 API 层在用户当场点击
   【检查更新】/【更新】/【一键更新全部插件】/【更新并重启】之后，把已经
   取回的索引条目递进来，才会去下载那一个 zip（AGENTS §2 出网铁律、裁决 1/2）。
2. **写范围只有代码目录**：插件更新只覆盖 ``plugins/<id>/``；底座更新由一次性
   ``update.bat`` 用 robocopy 覆盖程序文件，逐条排除 ``data/``、``plugins/``、
   ``.venv/``、``.git/``、``dist/``、``__pycache__/``、``.system_generated/``。
3. **本机文件必保**：官方 core-bank 的种子题库（``bank/bank.db``）、``.bak``
   备份、灌库报告与 ``bank/assets/`` 下几十张题目配图就住在插件目录里，
   ``rmtree`` 一把梭等于删老师的财产。插件更新按**合并**语义落地：新包没有的
   文件一律原地保住；新包带了同名的数据文件（库/备份/报告）则以旧的为准
   （:func:`_preserve_local_files`）。分不清「新版本删掉的旧代码」与「老师的
   数据」时一律按数据办——留着一个没人引用的旧 js 无害，丢掉题库不可逆。

底座自更新的「覆盖 + 重启」这一棒在开发机上不可真机验证（它会覆盖正在运行的
工作树），本模块只保证：下载与校验、脚本内容（排除清单逐条可断言）、
状态机读写与重启续更。真实替换要在装好的发行包上手工跑一次才算证据。
"""

from __future__ import annotations

import io
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from app import __version__
from app.core.config import root_data_dir, settings
from app.core.plugin_download import download_plugin_zip_sources
from app.core.plugin_install import (
    MAX_ENTRIES,
    PluginInstallError,
    _check_entry,
    staged_plugin_from_zip,
)

LOCAL_TZ = timezone(timedelta(hours=8))

# 底座包比插件包大得多（含 static/vendor 的 KaTeX），但仍要有上限
HOST_MAX_ZIP_BYTES = 200 * 1024 * 1024
HOST_MAX_UNCOMPRESSED_BYTES = 600 * 1024 * 1024

# update.bat 的 robocopy 排除清单（ADR-006 死命令 1，逐条入律）
# ``plugins`` 也在清单里：发行包内自带插件目录（core-bank 的**空壳**种子库），
# 底座自更新一旦覆盖它，等于拿空库换掉老师的真题库。插件版本由双轨更新的
# 插件热更通道负责（那边按合并语义落地并保住本机数据文件），底座自更新
# 只管程序文件，绝不碰插件目录。
HOST_EXCLUDED_DIRS = ("data", "plugins", ".venv", ".git", "dist", "__pycache__",
                      ".system_generated")
HOST_EXCLUDED_FILES = ("*.pyc", "*.pyo")

# 插件目录里属于「老师财产」的文件：更新覆盖时必须原样保住
DATA_SUFFIXES = (".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".bak", ".part")
DATA_FILENAMES = ("migration_report.json",)

PENDING_FILENAME = "update_state.json"
STAGE_DIR_NAME = "jzo-update-stage"

# 底座 zip 解压后必须能认出来是底座（防拿插件包/任意包冒充底座覆盖程序文件）
HOST_REQUIRED_FILES = ("app/main.py", "static/workspace.html", "LICENSE")

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")
_lock = threading.Lock()

# 本次进程最近一次「重启续更」的结果，供前端如实播报一次（进程内，不落盘）
_LAST_RESUME: dict[str, Any] = {"ran": False, "resumed": [], "failed": [],
                                "had_pending": False, "at": ""}


class UpdateRejected(Exception):
    """更新被拒绝：不兼容、包不合格、或环境不允许（如开发工作树）。"""

    def __init__(self, message: str, code: str = "rejected") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


# ------------------------------------------------------------------ 版本比较

def parse_version(value: Any) -> tuple[int, int, int, str] | None:
    """把 ``主.次.修订[-预发布]`` 拆成可比较的元组；写坏返回 None。"""
    match = _VERSION_RE.match(str(value or "").strip())
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), match.group(4) or ""


def _compare_prerelease(left: str, right: str) -> int:
    """语义化版本的预发布段：数字标识符按数值比且低于非数字，段数少的更低。"""
    if left == right:
        return 0
    if not left:
        return 1  # 正式版高于任何预发布
    if not right:
        return -1
    left_parts, right_parts = left.split("."), right.split(".")
    for index in range(max(len(left_parts), len(right_parts))):
        if index >= len(left_parts):
            return -1
        if index >= len(right_parts):
            return 1
        a, b = left_parts[index], right_parts[index]
        a_num, b_num = a.isdigit(), b.isdigit()
        if a_num and b_num:
            if int(a) != int(b):
                return -1 if int(a) < int(b) else 1
        elif a_num != b_num:
            return -1 if a_num else 1
        elif a != b:
            return -1 if a < b else 1
    return 0


def compare_versions(left: Any, right: Any) -> int | None:
    """``left`` 与 ``right`` 谁大：1 / -1 / 0；**任一版本号写坏返回 None**。

    返回 None 而不是 0 是刻意的：版本写坏的条目必须自己出局并在界面列出原因，
    不能被当成「一样新」静默跳过（PLUGIN_SPEC §1.7）。
    """
    a, b = parse_version(left), parse_version(right)
    if a is None or b is None:
        return None
    for x, y in zip(a[:3], b[:3]):
        if x != y:
            return -1 if x < y else 1
    return _compare_prerelease(a[3], b[3])


def host_version() -> str:
    """底座版本：兼容校验的唯一比对基准（ADR-006 死命令 2）。"""
    return str(__version__)


def host_satisfies(min_host_version: Any) -> bool:
    """底座版本是否满足 ``min_host_version``；缺省视为不设限，写坏视为不满足。"""
    declared = str(min_host_version or "").strip()
    if not declared:
        return True
    verdict = compare_versions(host_version(), declared)
    return verdict is not None and verdict >= 0


def manifest_min_host(manifest: dict[str, Any]) -> str:
    """清单里两处兼容声明取更严的那个：``min_host_version`` 与 ``engine.host_version``。"""
    engine = manifest.get("engine") if isinstance(manifest.get("engine"), dict) else {}
    candidates = [str(manifest.get("min_host_version") or "").strip(),
                  str(engine.get("host_version") or "").strip()]
    usable = [item for item in candidates if parse_version(item) is not None]
    if not usable:
        return ""
    return sorted(usable, key=lambda item: parse_version(item) or (0, 0, 0, ""))[-1]


# ------------------------------------------------------------------ 检查更新

def check_updates(index: dict[str, Any], installed: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """把「已装插件」与「用户当场拉回的索引」对账，产出一张可执行的状态表。

    本函数**不出网**：``index`` 必须来自用户点【检查更新】后 API 层拉回的结果。
    单条对不上（索引里没有、版本写坏、不兼容）只让它自己出局并带上原因，
    不牵连其他插件，也不影响底座自己的更新判定。
    """
    from app.core.plugins import discover_plugins  # 局部导入：避免与插件发现互相持有

    if installed is None:
        discovered = discover_plugins()
        installed = [item for item in (discovered.get("plugins") or []) if isinstance(item, dict)]

    entries = {str(item.get("id")): item for item in (index.get("entries") or [])
               if isinstance(item, dict) and item.get("id")}
    plugins: list[dict[str, Any]] = []
    for plugin in installed:
        plugin_id = str(plugin.get("id") or "")
        local_version = str(plugin.get("version") or "")
        entry = entries.get(plugin_id)
        row: dict[str, Any] = {
            "id": plugin_id,
            "name": plugin.get("name") or plugin_id,
            "local_version": local_version,
            "remote_version": "",
            "min_host_version": "",
            "compatible": True,
            "state": "not_in_index",
            "reason": "",
            "zip_url": "",
            "mirrors": [],
        }
        if entry is None:
            row["reason"] = "索引里没有这个插件（本地装的，或索引未收录）"
            plugins.append(row)
            continue

        remote_version = str(entry.get("version") or "")
        row["remote_version"] = remote_version
        row["min_host_version"] = str(entry.get("min_host_version") or "")
        row["zip_url"] = str(entry.get("zip_url") or "")
        row["mirrors"] = list(entry.get("mirrors") or [])

        verdict = compare_versions(remote_version, local_version)
        if verdict is None:
            row["state"] = "bad_entry"
            row["reason"] = (f"版本号写坏，无法比较：本地 {local_version or "缺"} / 远端 "
                             f"{remote_version or "缺"}")
        elif verdict <= 0:
            row["state"] = "up_to_date"
            row["reason"] = "已是最新" if verdict == 0 else "本地版本比索引更新，不降级"
        elif not host_satisfies(row["min_host_version"]):
            row["state"] = "incompatible"
            row["compatible"] = False
            row["reason"] = (f"需先更新底座：该版本要求 ≥ {row['min_host_version']}，"
                             f"当前底座 {host_version()}")
        else:
            row["state"] = "update_available"
            row["reason"] = f"{local_version} → {remote_version}"
        plugins.append(row)

    host_block = index.get("host") if isinstance(index.get("host"), dict) else None
    host_row: dict[str, Any] = {
        "current": host_version(),
        "available": "",
        "update_available": False,
        "notes": "",
        "reason": "索引未声明底座版本（host 块缺失或不合格）",
    }
    if host_block:
        available = str(host_block.get("version") or "")
        verdict = compare_versions(available, host_version())
        host_row["available"] = available
        host_row["notes"] = str(host_block.get("notes") or "")
        if verdict is None:
            host_row["reason"] = f"底座版本号写坏，无法比较：{available or "缺"}"
        elif verdict > 0:
            host_row["update_available"] = True
            host_row["reason"] = f"{host_version()} → {available}"
        else:
            host_row["reason"] = "底座已是最新" if verdict == 0 else "本地底座比索引更新，不降级"

    summary = {
        "checked": len(plugins),
        "update_available": sum(1 for row in plugins if row["state"] == "update_available"),
        "incompatible": sum(1 for row in plugins if row["state"] == "incompatible"),
        "up_to_date": sum(1 for row in plugins if row["state"] == "up_to_date"),
        "not_in_index": sum(1 for row in plugins if row["state"] == "not_in_index"),
        "bad_entry": sum(1 for row in plugins if row["state"] == "bad_entry"),
    }
    return {"host": host_row, "plugins": plugins, "summary": summary,
            "index_name": index.get("index_name") or "", "updated_at": index.get("updated_at") or ""}


# ------------------------------------------------------------- 数据文件保护

def _is_data_file(path: Path) -> bool:
    return path.suffix.lower() in DATA_SUFFIXES or path.name in DATA_FILENAMES


def _local_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(item for item in root.rglob("*") if item.is_file())


def _preserve_local_files(destination: Path, staged_root: Path) -> dict[str, list[str]]:
    """把旧插件目录里的本机文件并进待落地的新包，返回两类保住的路径清单。

    更新 = **合并**，不是「删掉整个目录再解压」：

    - 新包里没有的文件一律原地保住（``carried``）。官方 core-bank 的题库
      （``bank/bank.db``）、``.bak`` 备份、灌库报告与 ``bank/assets/`` 里几十张
      题目配图都住在插件目录里，``rmtree`` 一把梭等于删老师的财产。分不清
      「新版本删掉的旧代码」与「老师的数据」时，一律按数据办——留着一个没人
      引用的旧 js 是无害的，丢掉题库是不可逆的。
    - 新包里带了同名文件、而它属于数据白名单（``DATA_SUFFIXES`` /
      ``DATA_FILENAMES``）时，**以旧的为准**（``data_overridden``）：官方包里的
      空壳种子库覆盖上来，等于拿空库换掉真题库。
    """
    carried: list[str] = []
    data_overridden: list[str] = []
    for source in _local_files(destination):
        relative = source.relative_to(destination)
        target = staged_root / relative
        if target.exists():
            if _is_data_file(source):
                shutil.copy2(source, target)
                data_overridden.append(relative.as_posix())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        carried.append(relative.as_posix())
    return {"carried": carried, "data_overridden": data_overridden}


# --------------------------------------------------------------- 插件热更新

def apply_plugin_update(entry: dict[str, Any], *, local_version: str = "",
                        data: bytes | None = None) -> dict[str, Any]:
    """更新一个插件：下载（若未给字节）→ 同款暂存校验 → 并回本机文件 → 落地。

    双重兼容闸门：索引条目的 ``min_host_version`` 先拦一次；解压后再按新包
    清单里的 ``min_host_version`` / ``engine.host_version`` 拦一次。任何一道
    不过都**直接丢弃、绝不覆盖本地代码**（ADR-006 死命令 2）。
    """
    plugin_id = str(entry.get("id") or "")
    if not plugin_id:
        raise UpdateRejected("条目缺少 id，无法更新")
    if not host_satisfies(entry.get("min_host_version")):
        raise UpdateRejected(
            f"需先更新底座：{plugin_id} 要求 ≥ {entry.get('min_host_version')}，"
            f"当前底座 {host_version()}", code="incompatible")

    if data is None:
        zip_url = str(entry.get("zip_url") or "")
        if not zip_url:
            raise UpdateRejected(f"{plugin_id} 的条目没有 zip_url，无从下载")
        data, _used = download_plugin_zip_sources(zip_url, list(entry.get("mirrors") or []))

    with staged_plugin_from_zip(data) as (staged_root, info):
        if info.get("id") != plugin_id:
            raise UpdateRejected(f"包里的 id 与条目不符：{info.get('id')} ≠ {plugin_id}",
                                 code="id_mismatch")
        try:
            manifest = json.loads((staged_root / "plugin.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise UpdateRejected(f"新包 plugin.json 无法解析：{exc}") from exc
        required = manifest_min_host(manifest if isinstance(manifest, dict) else {})
        if not host_satisfies(required):
            raise UpdateRejected(
                f"需先更新底座：新包要求 ≥ {required}，当前底座 {host_version()}",
                code="incompatible")

        plugins_dir = Path(settings.plugins_dir)
        destination = plugins_dir / plugin_id
        if destination.exists() and (destination.is_symlink() or not destination.is_dir()):
            raise UpdateRejected(f"plugins/{plugin_id} 不是目录，拒绝覆盖")

        kept = _preserve_local_files(destination, staged_root) if destination.is_dir() else {
            "carried": [], "data_overridden": []}
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_root), str(destination))

    return {
        "id": plugin_id,
        "from": local_version or "",
        "to": str(info.get("version") or ""),
        "preserved": kept["carried"] + kept["data_overridden"],
        "data_overridden": kept["data_overridden"],
        "min_host_version": required,
    }


def apply_updates(rows: list[dict[str, Any]], *, allow_download: bool = True) -> dict[str, Any]:
    """串行执行一批更新（一次点击 = 一次批量任务，跑完即止，不排队不重试）。

    只吃 ``state == "update_available"`` 的行——不兼容与版本写坏的一律跳过并
    如实列进 ``skipped``，绝不覆盖本地代码。失败逐条记原因，不牵连其他条目。
    """
    updated: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if row.get("state") != "update_available":
            skipped.append({"id": row.get("id"), "state": row.get("state"),
                            "reason": row.get("reason") or "不在本次更新范围"})
            continue
        if not allow_download:
            skipped.append({"id": row.get("id"), "state": "blocked",
                            "reason": "本次调用不允许出网（续更只消费本机已下载的包）"})
            continue
        try:
            result = apply_plugin_update(row, local_version=str(row.get("local_version") or ""))
        except (UpdateRejected, PluginInstallError, OSError, ValueError) as exc:
            message = getattr(exc, "message", None) or str(exc)
            failed.append({"id": row.get("id"), "reason": message})
            continue
        updated.append(result)
    return {"updated": updated, "failed": failed, "skipped": skipped}


# ----------------------------------------------------------------- 续更状态

def pending_path() -> Path:
    """``data/update_state.json``：更新唯一允许写进 ``data/`` 的痕迹。"""
    return root_data_dir() / PENDING_FILENAME


def _now() -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def read_pending() -> dict[str, Any]:
    """读续更状态；缺失或损坏一律当作「没有待办」，绝不挡启动。"""
    path = pending_path()
    if not path.is_file():
        return {"host_version": "", "pending": [], "written_at": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"host_version": "", "pending": [], "written_at": ""}
    if not isinstance(data, dict):
        return {"host_version": "", "pending": [], "written_at": ""}
    rows = data.get("pending")
    pending = [row for row in rows if isinstance(row, dict) and row.get("id")] if isinstance(rows, list) else []
    return {
        "host_version": str(data.get("host_version") or ""),
        "pending": pending,
        "written_at": str(data.get("written_at") or ""),
    }


def write_pending(host_version_target: str = "", pending: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """写续更状态。只存版本号、待办 id 与本机临时包路径——**不含任何题目数据**。"""
    payload = {
        "host_version": str(host_version_target or ""),
        "pending": [
            {"id": str(row.get("id")), "from": str(row.get("from") or ""),
             "to": str(row.get("to") or ""), "zip_path": str(row.get("zip_path") or "")}
            for row in (pending or []) if isinstance(row, dict) and row.get("id")
        ],
        "written_at": _now(),
    }
    with _lock:
        path = pending_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    return payload


def clear_pending() -> dict[str, Any]:
    """清掉续更状态（补齐跑完、或用户明确要求作废）。文件不存在也算成功。"""
    with _lock:
        path = pending_path()
        if path.is_file():
            path.unlink()
    return read_pending()


def resume_pending() -> dict[str, Any]:
    """重启后接着补齐上一轮没更完的插件。

    **只消费本机状态文件里用户上一轮亲手点选的清单与已下载的包，不出网**
    （AGENTS §2 出网铁律的续更例外）。包不在了就如实记失败，等用户再点一次。
    结果同时记进 :func:`last_resume`，供前端在底部日志区如实播报一次。
    """
    state = read_pending()
    rows = state.get("pending") or []
    installed: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for row in rows:
        zip_path = Path(str(row.get("zip_path") or ""))
        if not zip_path.is_file():
            failed.append({"id": row.get("id"), "reason": f"本机更新包已不在：{zip_path}"})
            continue
        try:
            data = zip_path.read_bytes()
            result = apply_plugin_update({"id": row.get("id")}, local_version=str(row.get("from") or ""),
                                         data=data)
        except (UpdateRejected, PluginInstallError, OSError, ValueError) as exc:
            failed.append({"id": row.get("id"), "reason": getattr(exc, "message", None) or str(exc)})
            continue
        installed.append(result)
        try:
            zip_path.unlink()
        except OSError:
            pass
    if installed or failed:
        clear_pending()
    outcome = {"ran": True, "resumed": installed, "failed": failed,
               "had_pending": bool(rows), "at": _now()}
    _record_resume(outcome)
    return outcome


def _record_resume(outcome: dict[str, Any]) -> None:
    global _LAST_RESUME
    with _lock:
        _LAST_RESUME = dict(outcome)


def last_resume() -> dict[str, Any]:
    """本次进程最近一次续更的结果（没跑过则 ``ran=False``）。"""
    with _lock:
        return dict(_LAST_RESUME)


# --------------------------------------------------------------- 底座自更新

def _extract_host_zip(data: bytes, target: Path) -> Path:
    """把底座 zip 解到临时目录并验明正身（必须有 app/main.py、workspace.html、LICENSE）。

    条目安全检查直接复用安装链那一套（``_check_entry``）：加密条目、符号链接、
    绝对路径、``..`` 穿越、嵌套 zip 一律拒——安全逻辑只允许有一份。
    """
    if not data:
        raise UpdateRejected("下载内容为空")
    if len(data) > HOST_MAX_ZIP_BYTES:
        raise UpdateRejected("底座包超过 200 MB 上限")
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise UpdateRejected("不是有效的 zip 文件")

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        infos = zf.infolist()
        if not infos:
            raise UpdateRejected("zip 包是空的")
        if len(infos) > MAX_ENTRIES * 4:
            raise UpdateRejected("底座包条目数异常（>8000），拒绝解压")
        entries = [_check_entry(info) for info in infos]
        total = 0
        prefix = _host_root(entries)
        for info, relative in zip(infos, entries):
            total += info.file_size
            if total > HOST_MAX_UNCOMPRESSED_BYTES:
                raise UpdateRejected("解压总量超过 600 MB 上限，疑似 zip 炸弹")
            if info.is_dir():
                continue
            stripped = relative.relative_to(*prefix) if prefix else relative
            destination = target / Path(*stripped.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(destination, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 256)

    for required in HOST_REQUIRED_FILES:
        if not (target / required).is_file():
            raise UpdateRejected(f"包里没有 {required}，不像底座发行包，拒绝覆盖程序文件")
    return target


def _host_root(entries: list[PurePosixPath]) -> tuple[str, ...]:
    """找包内顶层目录（发行包通常裹一层 ``jiuzhang-operator-x.y.z/``）。"""
    tops = {part for part in (entry.parts[0] for entry in entries if entry.parts)}
    if len(tops) == 1:
        only = next(iter(tops))
        if all(len(entry.parts) > 1 for entry in entries if entry.parts):
            return (only,)
    return ()


def build_update_script(*, root: Path, staged: Path, pid: int, port: int) -> str:
    """生成一次性 ``update.bat`` 的内容（纯字符串，便于逐条断言排除清单）。

    四步：等父进程退出 → robocopy 覆盖程序文件（排除 ``data/`` 等七项）→
    重新拉起底座 → 删暂存与自身。

    等待循环用 ``for /f`` 读 tasklist 的 CSV 输出，**不碰 ``find``**：
    Git Bash 的 ``usr/bin/find.exe`` 在 PATH 里排在 System32 的 ``find.exe``
    前面，``tasklist | find`` 那行会让整篇批处理直接终止（沙箱真跑实测：
    脚本停在该行，底座永不重启，覆盖也没发生）。``timeout`` 在没有控制台的
    DETACHED_PROCESS 里同样不可靠，睡眠改用 ``ping -n 2 127.0.0.1``。
    ``tasklist``/``ping`` 一律写绝对路径，躲开 PATH 抢占。

    ``/XD`` 只写**目录名**，不写目标绝对路径：军令 #13 任务 10 的沙箱真跑抓出
    绝对路径在这个方向（阶段→根）不生效，源包里的 ``data/``、``.git/``、``dist/``
    会照原样覆盖过去——那就等于把老师的题库交出去了。裸名会让 robocopy 在整棵树
    里跳过同名的目录，两侧都保护；代价是发行包里任何同名目录也不会被复制，
    这正是 ADR-006 要的结果。

    ``plugins`` 同样在清单里：发行包内自带插件目录（core-bank 的空壳种子库），
    覆盖它等于拿空库换掉老师的真题库。插件版本归双轨更新的插件热更通道管。
    """
    excludes = " ".join(f'"{name}"' for name in HOST_EXCLUDED_DIRS)
    file_excludes = " ".join(f'"{pattern}"' for pattern in HOST_EXCLUDED_FILES)
    protect_hint = " ".join(name + "\\" for name in HOST_EXCLUDED_DIRS)
    python_exe = root / ".venv" / "Scripts" / "python.exe"
    lines = [
        "@echo off",
        "rem 九章算子底座自更新（一次性脚本，跑完自删；由用户在界面上点【更新并重启】生成）",
        "setlocal",
        f'set "JZO_ROOT={root}"',
        f'set "JZO_STAGE={staged}"',
        f'set "JZO_PID={pid}"',
        "echo [1/4] 等待底座进程退出...",
        ":wait_exit",
        'set "JZO_ALIVE=0"',
        r'for /f "usebackq tokens=2 delims=," %%p in (`""%SystemRoot%\System32\tasklist.exe" /FI "PID eq %JZO_PID%" /NH /FO CSV"`) do if "%%~p"=="%JZO_PID%" set "JZO_ALIVE=1"',
        'if "%JZO_ALIVE%"=="1" (',
        r'  "%SystemRoot%\System32\ping.exe" -n 2 127.0.0.1 >nul',
        "  goto wait_exit",
        ")",
        f"echo [2/4] 覆盖程序文件（保护 {protect_hint}）",
        f'robocopy "%JZO_STAGE%" "%JZO_ROOT%" /E /XD {excludes} /XF {file_excludes} /R:2 /W:2 /NFL /NDL /NJH',
        "if errorlevel 8 (",
        "  echo robocopy 失败（退出码 %errorlevel%），保留原文件不动，请手工检查",
        "  goto :eof",
        ")",
        "echo [3/4] 重新拉起底座",
        'cd /d "%JZO_ROOT%"',
        f'start "" "{python_exe}" -m uvicorn app.main:app --host 127.0.0.1 --port {port}',
        "echo [4/4] 清理临时文件",
        'rmdir /S /Q "%JZO_STAGE%"',
        'del "%~f0"',
        "endlocal",
        "",
    ]
    return "\r\n".join(lines)


def _batch_encoding() -> str:
    """批处理文件的编码：cmd 按控制台 ANSI 码页读 ``.bat``。

    UTF-8 无 BOM 的 ``.bat`` 里，中文会被 cp936 误解成乱码；乱码中冒出的
    引号与管道符足以让整篇脚本语法崩掉（沙箱真跑实测：``rem`` 后半句被
    当成命令执行）。所以这里优先用 ANSI 码页实在编码不出中文时才退 UTF-8。
    """
    for candidate in ("mbcs", locale.getpreferredencoding(False), "utf-8"):
        if not candidate:
            continue
        try:
            "九章算子".encode(candidate)
        except (LookupError, UnicodeEncodeError):
            continue
        return candidate
    return "utf-8"


def _write_batch_script(path: Path, script: str) -> None:
    """把一次性 ``.bat`` 落盘：ANSI 码页编码，行尾只有一层 CRLF。

    ``Path.write_text`` 会再做一次 newline 转换：脚本本身已是 CRLF，
    再转换就成 ``\\r\\r\\n``，cmd 会把多出来的 ``\\r`` 当成命令的一部分。
    """
    encoding = _batch_encoding()
    try:
        payload = script.encode(encoding)
    except UnicodeEncodeError:
        payload = script.encode(encoding, errors="replace")
    path.write_bytes(payload)


def prepare_host_update(host_block: dict[str, Any], *, port: int | None = None,
                        data: bytes | None = None) -> dict[str, Any]:
    """下载并校验底座新版本，生成一次性脚本、写续更状态。**不自杀、不覆盖**。

    真正的「结束自身 → 覆盖 → 重启」由 :func:`launch_host_update` 干，且必须
    由用户当场点【更新并重启】触发；开发工作树（存在 ``.git``）直接拒绝执行，
    免得一把 robocopy 把没提交的活儿抹掉。
    """
    if not isinstance(host_block, dict) or not host_block.get("zip_url"):
        raise UpdateRejected("索引没有可用的底座更新信息（host 块缺失或没有 zip_url）")
    available = str(host_block.get("version") or "")
    verdict = compare_versions(available, host_version())
    if verdict is None:
        raise UpdateRejected(f"底座版本号写坏，无法比较：{available or "缺"}")
    if verdict <= 0:
        raise UpdateRejected(f"当前底座 {host_version()} 不需要更新到 {available}")

    if data is None:
        data, _used = download_plugin_zip_sources(str(host_block["zip_url"]),
                                                 list(host_block.get("mirrors") or []))

    stage = Path(tempfile.gettempdir()) / f"jzo_host_update_{os.getpid()}"
    if stage.exists():
        shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True, exist_ok=True)
    _extract_host_zip(data, stage)

    script_path = Path(tempfile.gettempdir()) / f"jzo_update_{os.getpid()}.bat"
    script = build_update_script(root=Path(settings.project_root), staged=stage,
                                pid=os.getpid(), port=int(port or settings.port))
    _write_batch_script(script_path, script)

    state = read_pending()
    write_pending(host_version_target=available, pending=state.get("pending") or [])

    return {
        "version": available,
        "current": host_version(),
        "notes": str(host_block.get("notes") or ""),
        "script_path": str(script_path),
        "staged_at": str(stage),
        "excluded_dirs": list(HOST_EXCLUDED_DIRS),
        "launchable": not (Path(settings.project_root) / ".git").exists(),
        "pending_plugins": [row["id"] for row in (state.get("pending") or [])],
    }


def launch_host_update(script_path: str) -> dict[str, Any]:
    """启动一次性脚本并结束自身进程（用户点【更新并重启】才会走到这里）。

    开发工作树上直接拒绝：robocopy 覆盖正在运行的工作树会抹掉未提交的改动，
    这种「不可逆 + 影响面大」的事必须由人在装好的发行包上亲手做。

    脚本的 stdout/stderr 一律接**日志文件**，绝不接控制台：底座可能压根没有
    控制台（双击图标、用 pythonw 起服务、或由别的进程拉起），此时 cmd 的
    ``echo`` 写控制台会失败，**整篇批处理当场终止**——脚本停在第一行，
    覆盖与重启都没发生（沙箱真机压测实测）。改接文件后 ``echo`` 只是写文件，
    脚本一路跑完；日志同时留下失败原因，便于事后追查。
    """
    path = Path(script_path)
    if not path.is_file():
        raise UpdateRejected(f"更新脚本不存在：{script_path}")
    if (Path(settings.project_root) / ".git").exists():
        raise UpdateRejected("当前是开发工作树（存在 .git），拒绝自动覆盖重启；"
                             "请在装好的发行包上执行该脚本", code="dev_worktree")
    log_path = path.with_name(path.stem + ".log")
    handle = open(log_path, "ab")
    try:
        subprocess.Popen(
            ["cmd.exe", "/c", str(path)], cwd=str(Path(settings.project_root)),
            stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    finally:
        handle.close()
    return {"launched": True, "script_path": str(path), "log_path": str(log_path)}


def stage_plugin_zip(entry: dict[str, Any]) -> dict[str, Any]:
    """把一个条目的 zip 下载到本机临时目录，供「重启续更」离线补齐用。

    只在用户当场点击的批量任务里调用；下载失败如实抛出，由上层记进失败清单。
    """
    zip_url = str(entry.get("zip_url") or "")
    if not zip_url:
        raise UpdateRejected(f"{entry.get('id')} 没有 zip_url")
    data, used = download_plugin_zip_sources(zip_url, list(entry.get("mirrors") or []))
    stage_dir = Path(tempfile.gettempdir()) / STAGE_DIR_NAME
    stage_dir.mkdir(parents=True, exist_ok=True)
    version = str(entry.get("version") or "")
    if parse_version(version) is None:
        version = "unversioned"
    target = stage_dir / f"{entry.get('id')}_{version}.zip"
    target.write_bytes(data)
    return {"id": entry.get("id"), "to": version if version != "unversioned" else "",
            "zip_path": str(target), "source": used, "bytes": len(data)}


def terminate_self() -> None:  # pragma: no cover - 只在真机重启路径上执行
    """结束底座自身进程（交给 update.bat 接管）。测试里绝不调用。"""
    sys.stdout.flush()
    os._exit(0)
