"""中转站的查重口径：与 core-bank 指纹引擎同源，但配图按**内容哈希**比。

池子里的图叫 ``pimg_x.png``、主库里的图叫 ``img_x.png``——同一个文件两个名字，
按文件名比永远比不上，按内容哈希比才是真的同一张图。

判据四要素：题型、归一题干、归一选项、配图内容全一致。先比文字键再比图：
文字键不同的题连图都不用算，几百道题扫一遍也只是几次字符串归一。
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.core import bank, bank_dedupe
from app.core.bank_codec import answer_from_storage
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


# ------------------------------------------------------------ 高度相似（软查重）

# 「高度相似」的分数线：归一题干逐字比对后的相似比。0.92 意味着一句 30 字的题干
# 只允许错三几个字——错别字、多一个「的」、单位写法不同都会落进来，而「已知 A 求 B」
# 改成「已知 B 求 A」这种换了问法的题不会被误判成同一道。
HIGH_SIMILARITY = 0.92
# 题干长度比低于这个值直接不比：长短差一倍的题干不可能是同一道题的誊抄误差。
LENGTH_FLOOR = 0.5
# 一次最多逐字比多少行：老师的库上万行时，宁可报「扫到上限」也不许把请求拖死。
MAX_COMPARE = 4000

LEVEL_IDENTICAL = "identical"
LEVEL_HIGH = "high"
LEVEL_NONE = "none"


def _answer_object(raw: Any) -> dict[str, Any]:
    """答案既能是对象（插件递进来的文档），也能是库里的 JSON 文本，两种都收。"""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def answer_key(raw: Any) -> str:
    """答案的可比口径：选择题按标号集合，其余按归一后的答案正文。

    ``raw`` 必须是**契约答案对象**；库里那一列存的是纯文本（选择题存 ``A,C``），
    读出来先过 ``bank_codec.answer_from_storage`` 再由本函数归一。认不出的形状
    一律回空串——空串表示「这道题没表态」，调用方据此把判断降级成「无法比较」，
    绝不当成「答案不同」去拦老师。
    """
    answer = _answer_object(raw)
    if not answer:
        return ""
    keys = answer.get("choice_keys")
    if isinstance(keys, list):
        picked = [str(key).strip().upper() for key in keys if str(key).strip()]
        if picked:
            return "choice:" + ",".join(sorted(set(picked)))
    kind = str(answer.get("kind") or "").strip() or "text"
    body = bank_dedupe.normalize_text(answer.get("content"))
    if body:
        return f"{kind}:{body}"
    final = bank_dedupe.normalize_text(answer.get("final"))
    if final:
        return f"{kind}:{final}"
    return ""


def answer_mismatch(existing_raw: Any, incoming_raw: Any) -> bool | None:
    """两边答案是否**确定不同**。任一边没表态就回 ``None``（无法比较）。"""
    left, right = answer_key(existing_raw), answer_key(incoming_raw)
    if not left or not right:
        return None
    return left != right


def answers_agree(existing_raw: Any, incoming_raw: Any) -> bool | None:
    """两边答案是否**确定相同**。任一边没表态就回 ``None``（无法比较）。

    与 :func:`answer_mismatch` 是同一把尺子的正反两说：报告里那个 ``same`` 字段
    直接就是本函数的返回值，界面据 ``same is False`` 判「红字拦截」。
    """
    verdict = answer_mismatch(existing_raw, incoming_raw)
    return None if verdict is None else (not verdict)


def similarity(left: str, right: str) -> float:
    """归一题干之间的相似比（0~1）。长度差太大直接归零，省掉一次逐字比对。"""
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    shorter, longer = sorted((len(left), len(right)))
    if not longer or shorter / longer < LENGTH_FLOOR:
        return 0.0
    return difflib.SequenceMatcher(None, left, right).ratio()


def similarity_report(provider_id: str, document: dict[str, Any],
                      assets: list[dict[str, Any]], *,
                      threshold: float = HIGH_SIMILARITY) -> dict[str, Any]:
    """在主库里找**同题或高度相似题**，回一张可供老师裁决的报告。

    与 :func:`find_duplicate` 的分工：那个函数只认指纹全等，是入库闸门；
    这个函数多给一档「高度相似」，用于入库前的后台预检——老师看一眼就该知道
    「这道题主库里已经有了，只是标点写法不同」。

    出参：``level`` 为 ``identical`` / ``high`` / ``none``；``similarity`` 是相似比；
    ``answer`` 三个字段说明答案比不比得上（``same`` 为 ``None`` 表示有一边没表态）；
    ``truncated`` 为真表示库太大、只比到 ``MAX_COMPARE`` 行。
    """
    text_key = _text_key(document.get("type"), document.get("stem"), document.get("options"))
    target = _fingerprint(text_key, _pending_image_hashes(document, assets))
    report: dict[str, Any] = {
        "hit": False,
        "level": LEVEL_NONE,
        "similarity": 0.0,
        "existing_id": "",
        "scanned": 0,
        "truncated": False,
        "answer": {"same": None, "existing": "", "incoming": answer_key(document.get("answer"))},
    }
    try:
        con = bank.connect(provider_id)
    except bank.BankError:
        return report
    try:
        rows = con.execute(
            "SELECT id, type, stem, options, extensions, answer FROM questions"
        ).fetchall()
    finally:
        con.close()

    report["scanned"] = len(rows)
    compared = 0
    best_score = 0.0
    best_row: Any = None
    for row in rows:
        # 题型不同的一律跳过：选择题与填空题就算题干一字不差也是两种用法。
        if str(row["type"] or "") != text_key[0]:
            continue
        row_key = _text_key(row["type"], row["stem"], row["options"])
        if row_key == text_key and _fingerprint(
                row_key, _bank_image_hashes(row["extensions"])) == target:
            # 指纹全等：这就是同一道题，不必再比相似度，直接收工。
            existing_answer = answer_from_storage(row["answer"], row["type"])
            report.update({"hit": True, "level": LEVEL_IDENTICAL, "similarity": 1.0,
                           "existing_id": str(row["id"])})
            report["answer"]["existing"] = answer_key(existing_answer)
            report["answer"]["same"] = answers_agree(existing_answer, document.get("answer"))
            return report
        if compared >= MAX_COMPARE:
            report["truncated"] = True
            break
        compared += 1
        score = similarity(text_key[1], row_key[1])
        if score > best_score:
            best_score, best_row = score, row
    if best_row is not None and best_score >= threshold:
        existing_answer = answer_from_storage(best_row["answer"], best_row["type"])
        report.update({"hit": True, "level": LEVEL_HIGH, "similarity": round(best_score, 4),
                       "existing_id": str(best_row["id"])})
        report["answer"]["existing"] = answer_key(existing_answer)
        report["answer"]["same"] = answers_agree(existing_answer, document.get("answer"))
    return report
