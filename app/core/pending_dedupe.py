"""中转站的查重口径：与 core-bank 指纹引擎同源，但配图按**内容哈希**比。

池子里的图叫 ``pimg_x.png``、主库里的图叫 ``img_x.png``——同一个文件两个名字，
按文件名比永远比不上，按内容哈希比才是真的同一张图。

判据四要素：题型、归一题干、归一选项、配图内容全一致。先比文字键再比图：
文字键不同的题连图都不用算，几百道题扫一遍也只是几次字符串归一。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from app.core import bank, bank_dedupe
from app.core.config import settings
from app.core.pending_db import PENDING_ASSET_URI_PREFIX, UPLOAD_ASSET_URI_PREFIX

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_key(question_type: Any, stem: Any, options: Any) -> tuple[str, str, tuple[str, ...]]:
    """题面文字键：题型 + 归一题干 + 归一选项（按内容排序）。

    与 ``bank_dedupe`` 同一把尺子：LaTeX 归一、排版标点剔除、全角转半角、
    去空白，但**绝不去括号与 ASCII 标点**——``!`` 是阶乘、``:`` 是比。
    """
    return (
        str(question_type or ""),
        bank_dedupe.normalize_text(stem),
        tuple(bank_dedupe.normalized_options(options)),
    )


def _fingerprint(text_key: tuple[str, str, tuple[str, ...]], image_hashes: list[str]) -> str:
    """题面指纹：文字键 + 配图内容哈希。配图按内容算，跨库同名不同名不影响判定。"""
    parts = [
        text_key[0],
        text_key[1],
        "\x1e".join(text_key[2]),
        "\x1e".join(sorted(image_hashes)),
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _upload_asset_path(uri: str) -> Path | None:
    """``/static/uploads/x.png`` → 真实文件；不合规一律回空（不拼路径）。"""
    text = str(uri or "")
    if not text.startswith(UPLOAD_ASSET_URI_PREFIX):
        return None
    name = text[len(UPLOAD_ASSET_URI_PREFIX):]
    if not re.match(r"^[A-Za-z0-9_.-]{1,120}$", name) or ".." in name:
        return None
    root = Path(settings.uploads_dir).resolve()
    target = root / name
    try:
        target.resolve().relative_to(root)
    except ValueError:
        return None
    return target


def _bank_image_hashes(extensions_raw: Any) -> list[str]:
    """主库题的配图内容哈希。文件不在了就用「缺失」占位——它与任何一张图都不相等。"""
    entry = bank.extensions_to_object(extensions_raw).get(bank.EXT_IMAGES_KEY)
    images = entry.get("images") if isinstance(entry, dict) else None
    if not isinstance(images, list):
        return []
    hashes: list[str] = []
    for image in images:
        uri = str(image.get("uri") or "") if isinstance(image, dict) else str(image or "")
        path = _upload_asset_path(uri)
        if path is None or not path.is_file():
            hashes.append("missing:" + bank_dedupe.normalize_text(uri))
            continue
        try:
            hashes.append(_sha256_file(path))
        except OSError:
            hashes.append("missing:" + bank_dedupe.normalize_text(uri))
    return hashes


def _pending_image_hashes(document: dict[str, Any], assets: list[dict[str, Any]]) -> list[str]:
    """池中题的配图内容哈希：池子里的图用暂存时记下的 sha256，其余按磁盘上的算。"""
    by_name = {str(item.get("name") or ""): str(item.get("sha256") or "") for item in assets}
    images = document.get("images")
    if not isinstance(images, list):
        return []
    hashes: list[str] = []
    for image in images:
        uri = str(image.get("uri") or "") if isinstance(image, dict) else str(image or "")
        if uri.startswith(PENDING_ASSET_URI_PREFIX):
            name = uri[len(PENDING_ASSET_URI_PREFIX):]
            digest = by_name.get(name, "")
            hashes.append(digest or "missing:" + bank_dedupe.normalize_text(uri))
            continue
        path = _upload_asset_path(uri)
        if path is None or not path.is_file():
            hashes.append("missing:" + bank_dedupe.normalize_text(uri))
            continue
        try:
            hashes.append(_sha256_file(path))
        except OSError:
            hashes.append("missing:" + bank_dedupe.normalize_text(uri))
    return hashes


def find_duplicate(provider_id: str, document: dict[str, Any],
                   assets: list[dict[str, Any]]) -> str:
    """在主库里找同题，返回那道题的 id；没有就回空串。

    两道题「同题」的判据与 core-bank 查重引擎同源：题型、归一题干、归一选项、
    配图内容全一致。**先比文字键再比图**：文字键不同的题连图都不用算，
    几百道题的库扫一遍也只是几次字符串归一。
    """
    text_key = _text_key(document.get("type"), document.get("stem"), document.get("options"))
    target = _fingerprint(text_key, _pending_image_hashes(document, assets))
    try:
        con = bank.connect(provider_id)
    except bank.BankError:
        return ""
    try:
        rows = con.execute(
            "SELECT id, type, stem, options, extensions FROM questions"
        ).fetchall()
    finally:
        con.close()
    for row in rows:
        row_key = _text_key(row["type"], row["stem"], row["options"])
        if row_key != text_key:
            continue
        if _fingerprint(row_key, _bank_image_hashes(row["extensions"])) == target:
            return str(row["id"])
    return ""
