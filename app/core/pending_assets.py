"""中转站的物理文件层：暂存配图、原文件只读副本与入库时的搬迁。

三条硬规矩：
- 图片只认魔数，解码后硬上限 8 MiB，文件名一律底座生成——请求自报的 MIME 不作数；
- 池子里的题在审核期间，配图只落 ``pending_assets/``，被否决的题连一张图都不许留在
  主库资源目录里；未审数归零时原文件副本与残留切图**物理删除**，磁盘不养废纸；
- 入库那一刻才把 ``pimg_x`` 搬进 ``uploads/`` 并改名 ``img_x``；写主库失败就原样搬回，
  绝不出现「图进了主库、题没进」的半截状态。

号段/路径常量与错误类型见 pending_db.py。
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.core import bank, wire
from app.core.config import settings
from app.core.pending_db import (
    DATA_URL_RE,
    EXTENSIONS,
    MAX_ASSET_BYTES,
    MAX_DATA_URL_CHARS,
    PENDING_ASSET_PREFIX,
    PENDING_ASSET_RE,
    PENDING_ASSET_URI_PREFIX,
    POOL_ASSET_PREFIX,
    POOL_ASSET_RE,
    POOL_ASSET_URI_PREFIX,
    PendingError,
    UPLOAD_ASSET_PREFIX,
    UPLOAD_ASSET_URI_PREFIX,
    pending_assets_dir,
    pool_assets_dir,
)

def _sniff_mime(data: bytes) -> str:
    """按魔数认图；不认识就回空串（绝不信请求自报的 MIME）。"""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return ""


def decode_data_url(data_url: Any) -> tuple[str, bytes]:
    """data URL → (MIME, 字节)。不合规就抛，绝不猜。"""
    if not isinstance(data_url, str) or not data_url:
        raise PendingError("配图缺少 data_url")
    if len(data_url) > MAX_DATA_URL_CHARS:
        raise PendingError("图片过大（解码后上限 8 MiB）")
    matched = DATA_URL_RE.match(data_url)
    if matched is None:
        raise PendingError("只接受 PNG / JPEG / WebP 的 base64 data URL")
    declared, payload = matched.group(1), matched.group(2)
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PendingError("图片 base64 内容不合法") from exc
    if not raw:
        raise PendingError("图片内容为空")
    if len(raw) > MAX_ASSET_BYTES:
        raise PendingError("图片过大（解码后上限 8 MiB）")
    actual = _sniff_mime(raw)
    if not actual:
        raise PendingError("不是可识别的 PNG / JPEG / WebP 图片")
    if actual != declared:
        raise PendingError("图片魔数与声明的格式不一致")
    return actual, raw


def write_pending_asset(raw: bytes, mime: str) -> str:
    """配图落进 ``pending_assets/``：文件名底座生成，先写临时文件再原子改名。"""
    root = pending_assets_dir()
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(5):
        name = PENDING_ASSET_PREFIX + secrets.token_hex(8) + EXTENSIONS[mime]
        target = root / name
        if target.exists():
            continue
        temp = root / (".pending-" + secrets.token_hex(8) + ".tmp")
        try:
            temp.write_bytes(raw)
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
        return name
    raise PendingError("生成配图文件名失败，请重试")


_SVG_FORBIDDEN = ("<script", "<foreignobject", "javascript:", " onload=", " onerror=")


def write_generated_asset(raw: bytes, mime: str) -> str:
    """底座自己渲染出来的页面图落盘（原卷页）。

    与 :func:`write_pending_asset` 的区别只在入口：这条只收底座生成的内容，
    不接受任何请求载荷。SVG 是文本页面的还原图，落盘前要过一遍禁用标签检查，
    保证它能当 ``<img>`` 读、当不了脚本容器。
    """
    if mime not in EXTENSIONS:
        raise PendingError("页面图格式不支持")
    if not raw:
        raise PendingError("页面图内容为空")
    if len(raw) > MAX_ASSET_BYTES:
        raise PendingError("页面图过大（上限 8 MiB）")
    if mime == "image/svg+xml":
        text = raw.decode("utf-8", errors="replace").lower()
        if "<svg" not in text:
            raise PendingError("页面图不是 SVG")
        if any(token in text for token in _SVG_FORBIDDEN):
            raise PendingError("页面图含不允许的内容")
    else:
        actual = _sniff_mime(raw)
        if actual != mime:
            raise PendingError("页面图魔数与声明格式不一致")
    return write_pending_asset(raw, mime)


def asset_path(name: str) -> Path:
    """把池子里记的文件名解析成真实路径；名字不合规一律拒绝，绝不拼路径。"""
    if not PENDING_ASSET_RE.match(str(name or "")):
        raise PendingError("配图文件名不合法")
    root = pending_assets_dir()
    target = root / name
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise PendingError("配图路径越界") from exc
    return target


def pool_asset_path(name: str) -> Path:
    """重题池成品图的真实路径：只认 ``cimg_`` 号段，越界一律拒绝。"""
    if not POOL_ASSET_RE.match(str(name or "")):
        raise PendingError("重题池配图文件名不合法")
    root = pool_assets_dir()
    target = root / name
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise PendingError("重题池配图路径越界") from exc
    return target


def rewrite_asset_uris(document: dict[str, Any], mapping: dict[str, str]) -> None:
    """把文档里的配图 uri 换一批：``mapping`` 是「旧 uri → 新 uri」。"""
    images = document.get("images")
    if not isinstance(images, list):
        return
    for image in images:
        if isinstance(image, dict):
            new_uri = mapping.get(str(image.get("uri") or ""))
            if new_uri:
                image["uri"] = new_uri


def drop_assets(assets: Iterable[dict[str, Any]]) -> None:
    """把配图从 ``pending_assets/`` 里删掉（否决与入库失败都要走这条）。"""
    for item in assets or []:
        name = str(item.get("name") or "")
        if not PENDING_ASSET_RE.match(name):
            continue
        path = pending_assets_dir() / name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            # 删不掉的残留文件不该让整次操作失败：它只是垃圾，不是数据。
            pass


def backup_path(source_backup: str) -> Path | None:
    """原文件副本的路径：只许工作区 ``data/`` 里的相对路径，越界一律拒绝。"""
    text = str(source_backup or "").strip()
    if not text:
        return None
    if text.startswith("/") or "\\" in text:
        raise PendingError("原文件副本路径必须是工作区内的相对路径")
    parts = [part for part in text.split("/") if part]
    if not parts or any(part in (".", "..") for part in parts):
        raise PendingError("原文件副本路径非法")
    root = Path(settings.data_dir).resolve()
    target = root.joinpath(*parts)
    try:
        target.resolve().relative_to(root)
    except ValueError as exc:
        raise PendingError("原文件副本路径越界") from exc
    return target


def backup_paths(source_backup: str) -> list[Path]:
    """一批可能有多份原文件副本（一次拖入好几个文件）。

    存法有两种：单个副本是普通相对路径；多个副本是 JSON 数组。
    两种都只许落在工作区 ``data/`` 里，越界一律拒绝。
    """
    text = str(source_backup or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            items = wire.loads(text)
        except (TypeError, ValueError) as exc:
            raise PendingError("原文件副本清单损坏") from exc
        if not isinstance(items, list):
            raise PendingError("原文件副本清单损坏")
    else:
        items = [text]
    paths: list[Path] = []
    for item in items:
        path = backup_path(str(item))
        if path is not None:
            paths.append(path)
    return paths


PENDING_SOURCES_DIRNAME = "pending_sources"


def store_source_backup(filename: str, data: bytes) -> str:
    """把拖进来的原文件在工作区 ``data/`` 下留一份**只读副本**，返回相对路径。

    副本是给这一批兜底用的：批次未审数归零时底座会物理删掉它，磁盘不养废纸。
    老师盘上的原件底座一个字节都不碰——这里只写副本。
    """
    raw = str(filename or "").strip()
    safe = re.sub(r"[^\w.\-]+", "_", raw, flags=re.UNICODE).strip("._") or "source"
    safe = safe[:80]
    folder = Path(settings.data_dir) / PENDING_SOURCES_DIRNAME
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(bank.LOCAL_TZ).strftime("%Y%m%d-%H%M%S")
    target = folder / f"{stamp}_{secrets.token_hex(3)}_{safe}"
    target.write_bytes(data)
    return f"{PENDING_SOURCES_DIRNAME}/{target.name}"
def move_assets_to_uploads(assets: list[dict[str, Any]]) -> dict[str, str]:
    """把配图从 ``pending_assets/`` 搬进 ``uploads/``，返回「旧 uri → 新 uri」。

    文件名也跟着换：池子里叫 ``pimg_x.png``，进主库后叫 ``img_x.png``——
    两套目录的名字空间本来就该分开，不然主库里会出现一堆 ``pimg_`` 开头的文件。
    """
    mapping: dict[str, str] = {}
    uploads_root = Path(settings.uploads_dir)
    uploads_root.mkdir(parents=True, exist_ok=True)
    for asset in assets:
        name = str(asset.get("name") or "")
        if not PENDING_ASSET_RE.match(name):
            continue
        source = asset_path(name)
        if not source.is_file():
            continue
        target_name = UPLOAD_ASSET_PREFIX + name[len(PENDING_ASSET_PREFIX):]
        target = uploads_root / target_name
        shutil.move(str(source), str(target))
        mapping[PENDING_ASSET_URI_PREFIX + name] = UPLOAD_ASSET_URI_PREFIX + target_name
    return mapping

def copy_pool_assets_to_uploads(assets: Iterable[dict[str, Any]]) -> dict[str, str]:
    """把**重题池**的成品图复制进 ``uploads/``，返回「旧 uri → 新 uri」。

    重题池并解法、分开存的时候，主库那份要能长期读，所以必须落 ``uploads/``；
    而 ``pool_assets/`` 那一份是这条池内条目自己的，裁决退场时由 :func:`drop_pool_assets`
    收干净。号段照旧：``cimg_x.png`` 进主库改名 ``img_x.png``。
    """
    mapping: dict[str, str] = {}
    uploads_root = Path(settings.uploads_dir)
    uploads_root.mkdir(parents=True, exist_ok=True)
    for asset in assets or []:
        name = str((asset or {}).get("name") or "") if isinstance(asset, dict) else ""
        if not POOL_ASSET_RE.match(name):
            continue
        source = pool_asset_path(name)
        if not source.is_file():
            continue
        target_name = UPLOAD_ASSET_PREFIX + name[len(POOL_ASSET_PREFIX):]
        target = uploads_root / target_name
        if not target.is_file():
            shutil.copyfile(str(source), str(target))
        mapping[POOL_ASSET_URI_PREFIX + name] = UPLOAD_ASSET_URI_PREFIX + target_name
    return mapping


def copy_pending_asset_to_pool(asset: Any) -> dict[str, Any]:
    """把待审池那一份成品图**复制**进 ``pool_assets/``，返回池内资产条目。

    是复制不是搬：待审行在同一条事务里才被删掉，文件先搬走的话事务一旦回滚
    就再也拼不回来——「池里有了、批次里还留着」可以是半态，「图没了、题也没了」
    是真丢数据。批次 ``assets_json`` 仍记着 ``pimg_`` 那一份，未审数归零时由
    ``pending_bank._settle_batch`` 统一清，与本目录互不相干。

    源文件不在就是失败（原判据 3.6 的「图文件缺失」一路）：宁可整条不搬，
    也不让池里躺着一条点开是死链的题。
    """
    name = str((asset or {}).get("name") or "") if isinstance(asset, dict) else ""
    if not PENDING_ASSET_RE.match(name):
        raise PendingError("配图文件名不合法")
    source = asset_path(name)
    if not source.is_file():
        raise PendingError("配图文件已不在中转站目录里，无法搬进重题池")
    raw = source.read_bytes()
    target_name = POOL_ASSET_PREFIX + name[len(PENDING_ASSET_PREFIX):]
    root = pool_assets_dir()
    root.mkdir(parents=True, exist_ok=True)
    target = root / target_name
    if not target.is_file():
        temp = root / (".pool-" + secrets.token_hex(8) + ".tmp")
        try:
            temp.write_bytes(raw)
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
    entry = {key: value for key, value in (asset or {}).items() if key != "name"}
    entry["name"] = target_name
    entry["uri"] = POOL_ASSET_URI_PREFIX + target_name
    entry["bytes"] = len(raw)
    entry["sha256"] = hashlib.sha256(raw).hexdigest()
    return entry


def drop_pool_assets(assets: Iterable[dict[str, Any]]) -> int:
    """只删 ``pool_assets/`` 里的那几份；``pending_assets/`` 与 ``uploads/`` 一个字节不碰。

    目录分开之后，「池里 delete 删到批次还在用的图」这件事在物理上就不成立了，
    不需要再回查别的表引用（S4 留的那条过渡规则到此收口）。
    """
    deleted = 0
    for item in assets or []:
        name = str((item or {}).get("name") or "") if isinstance(item, dict) else ""
        if not POOL_ASSET_RE.match(name):
            continue
        path = pool_assets_dir() / name
        try:
            if path.is_file():
                path.unlink()
                deleted += 1
        except OSError:
            # 删不掉的残留文件只是垃圾，不该让已经成功的裁决动作报失败。
            pass
    return deleted


def remove_uploaded_copies(mapping: dict[str, str]) -> None:
    """写库没过：把刚复制进 ``uploads/`` 的那几份删掉。

    只删本次复制的产物（:func:`copy_pool_assets_to_uploads` 的输出），绝不动
    ``pending_assets/`` 与 ``pool_assets/`` 里的原件；删不掉就当垃圾留着，
    不让收尾的清理把已经发生的业务失败盖住。
    """
    for _old_uri, new_uri in (mapping or {}).items():
        name = str(new_uri or "")[len(UPLOAD_ASSET_URI_PREFIX):]
        if not name.startswith(UPLOAD_ASSET_PREFIX):
            continue
        try:
            path = Path(settings.uploads_dir) / name
            if path.is_file():
                path.unlink()
        except OSError:
            pass


def rewrite_uri_text(text: str, mapping: dict[str, str]) -> str:
    """把正文（解析、题干）里出现的旧 uri 换成新 uri。

    :func:`rewrite_asset_uris` 只改 ``images`` 数组；解析正文是 Markdown 文本，
    图引用就写在里面，「新增解析」并进去的那段必须换一遍，不然主库解法里的图
    指向的还是池子目录。
    """
    body = str(text or "")
    for old_uri, new_uri in (mapping or {}).items():
        body = body.replace(old_uri, new_uri)
    return body


def restore_assets(mapping: dict[str, str]) -> None:
    """写库没过：把已经搬进主库资源目录的配图搬回池子。"""
    for old_uri, new_uri in mapping.items():
        name = old_uri[len(PENDING_ASSET_URI_PREFIX):]
        target_name = new_uri[len(UPLOAD_ASSET_URI_PREFIX):]
        try:
            shutil.move(str(Path(settings.uploads_dir) / target_name),
                        str(asset_path(name)))
        except (OSError, PendingError):
            pass
