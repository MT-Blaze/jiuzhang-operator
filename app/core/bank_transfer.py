"""题库批量导入导出：``.json`` / ``.zip`` 题目包 ⇄ 题目标准结构。

这一层只管「包长什么样」：怎么把文件拆成题目、怎么把题目打包成文件。
校验与落库由 ``app/core/bank.py`` 统一负责——校验口径只有一份
（``schemas/question.json``），两处各写一套必然对不上。
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from app.core.contract import CONTRACT_VERSION

BUNDLE_FORMAT = "jiuzhang.question.bundle"
BUNDLE_FORMAT_VERSION = "1.0"

MAX_BUNDLE_BYTES = 32 * 1024 * 1024
MAX_BUNDLE_QUESTIONS = 5000
MAX_ZIP_MEMBERS = 512
MAX_ZIP_MEMBER_BYTES = 16 * 1024 * 1024
ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


class TransferError(Exception):
    """题目包本身不合法：坏 JSON、坏 zip、空包或超限。"""


def looks_like_zip(raw: bytes) -> bool:
    """按魔数判 zip：不信文件后缀，老师改个名也不该把底座带沟里。"""
    return raw[:4] in ZIP_MAGICS


def parse_bundle(raw: bytes, filename: str = "") -> list[dict[str, Any]]:
    """把一个题目包拆成题目标准结构列表。

    支持三种包型（都是「符合 question.json 的批量」）：
    - 单个题目对象；
    - 题目数组；
    - 带 ``questions`` 字段的交换包（底座导出用的就是这一型）。

    ``.zip`` 里每个 ``.json`` 成员都按同一口径解析，其余成员忽略。
    """
    if not raw:
        raise TransferError("题目包是空的")
    if len(raw) > MAX_BUNDLE_BYTES:
        raise TransferError(
            f"题目包超过 {MAX_BUNDLE_BYTES // (1024 * 1024)} MB 上限"
        )
    members = _read_zip_members(raw) if looks_like_zip(raw) else [
        (filename or "题目包.json", raw)
    ]
    documents: list[dict[str, Any]] = []
    for name, blob in members:
        try:
            payload = json.loads(blob.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise TransferError(f"{name} 不是 UTF-8 文本") from exc
        except json.JSONDecodeError as exc:
            raise TransferError(f"{name} 不是合法的 JSON：{exc}") from exc
        documents.extend(_extract_documents(payload, name))
    if not documents:
        raise TransferError("题目包里没有题目")
    if len(documents) > MAX_BUNDLE_QUESTIONS:
        raise TransferError(
            f"题目数 {len(documents)} 超过一次导入 {MAX_BUNDLE_QUESTIONS} 题的上限"
        )
    return documents


def build_bundle(plugin_id: str, documents: list[dict[str, Any]], exported_at: str) -> dict[str, Any]:
    """把题目打包成交换包：导出的文件能原样再导入回来。"""
    return {
        "format": BUNDLE_FORMAT,
        "format_version": BUNDLE_FORMAT_VERSION,
        "schema_version": CONTRACT_VERSION,
        "exported_at": exported_at,
        "plugin_id": plugin_id,
        "count": len(documents),
        "questions": documents,
    }


def _read_zip_members(raw: bytes) -> list[tuple[str, bytes]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise TransferError("压缩包损坏，无法读取") from exc
    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > MAX_ZIP_MEMBERS:
            raise TransferError(f"压缩包内文件过多（{len(infos)} 个）")
        members: list[tuple[str, bytes]] = []
        for info in infos:
            if not info.filename.lower().endswith(".json"):
                continue
            # 逐个限量读：压缩包头里的体积可以撒谎，实际解压量必须由我们自己卡住
            with archive.open(info) as stream:
                blob = stream.read(MAX_ZIP_MEMBER_BYTES + 1)
            if len(blob) > MAX_ZIP_MEMBER_BYTES:
                raise TransferError(f"{info.filename} 解压后超过单文件上限")
            members.append((info.filename, blob))
    if not members:
        raise TransferError("压缩包里没有 .json 题目文件")
    return members


def _extract_documents(payload: Any, name: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("questions"), list):
            items = payload["questions"]
        elif "stem" in payload:
            items = [payload]
        else:
            raise TransferError(f"{name} 既不是题目对象，也没有 questions 数组")
    else:
        raise TransferError(f"{name} 的顶层结构必须是题目对象或题目数组")
    documents: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise TransferError(f"{name} 第 {index} 项不是题目对象")
        documents.append(item)
    return documents
