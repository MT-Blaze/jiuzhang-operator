"""中转站的比对口径：四要素指纹、单条命中与软查重置信度（军令 #32 · S5b 拆出）。

**来源**：整块搬自 ``app/core/pending_dedupe.py``（原 1065 行撞破 800 行上限）——
纯 extract-module，函数体、常量值、注释与判据口径逐字未改。``pending_dedupe`` 原位
re-export 本模块全部名字，调用点（``api/pending.py``、``pending_pool.py``、
``pending_bank.py``、``pending_batches.py``、``tools/editor_probe.py``、``tests/*``）
用法一字不改；``pending_dedupe`` 里留下的扫描缓存／初查链／抽走进池照旧按模块全局取用，
测试 monkeypatch ``pending_dedupe.bank_rows_snapshot`` 的口径不受影响（该函数仍在 ``pending_dedupe``）。

**边界**：这里只做**读库比对**——把中转站待审题与主库存量题摆一起判「像不像」，
不碰进程内缓存、不写 ``dedupe_scans`` / ``dedupe_findings``、不入池。
主库侧的骨架／签名／置信度口径住 ``dedupe_signature``（同源，本文件不另立一套）。

**禁区**：
- 配图按**内容哈希**比：池子里叫 ``pimg_x.png``、主库里叫 ``img_x.png``，按文件名比永远比不上；
- 文字键不同的题连图都不用算；宁可漏报不可误报——误报的下一站是删数据；
- 百分比只是档位内排序的刻度，措辞只说「很像」，不说「98% 是同一道题」（台账第 52 条）。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.core import bank, bank_dedupe
from app.core.bank_codec import answer_from_storage
from app.core.config import settings
from app.core.pending_db import (
    PENDING_ASSET_URI_PREFIX,
    UPLOAD_ASSET_URI_PREFIX,
)

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

# 「高度相似」的分数线——军令 #32 · S2 判据 2.6：这把尺子已并进底座查重引擎的
# 档位表（``bank_dedupe.SKELETON_LEVELS``），这里只留一个**别名**给老调用方与老
# 测试用，值必须仍是 0.92（＝新档位的「很像」门槛）。**不许在这里另设阈值**，
# 否则同一件事又长出第二把尺子。
HIGH_SIMILARITY = bank_dedupe.SKELETON_LEVELS["very_similar"]
# 一次最多逐字比多少行：老师的库上万行时，宁可报「扫到上限」也不许把请求拖死。
MAX_COMPARE = 4000

LEVEL_IDENTICAL = "identical"
LEVEL_HIGH = "high"
LEVEL_NONE = "none"
# 「很像」及以上（含「确定」）在旧三态里的落点——新档位与旧 ``level`` 键的桥。
LEVELS_HIGH_OR_ABOVE = (LEVEL_IDENTICAL, LEVEL_HIGH)
# 档位标签的唯一来源是底座查重引擎（判据 2.6：一把尺子，措辞也只有一处定义）。
LEVEL_LABELS_TEXT = bank_dedupe.LEVEL_LABELS


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
    """归一题干之间的相似比（0~1）。

    军令 #32 · S2：逐字比对的实现搬到底座查重引擎（``bank_dedupe.text_similarity``），
    本函数只保留**原有调用口径**——入参仍是 ``normalize_text`` 归一后的题干，长度
    差一倍以上直接归零。别再在这里抄一份 SequenceMatcher，两把尺子迟早岔开。
    """
    return bank_dedupe.text_similarity(left, right)


def confidence_of(document: dict[str, Any], row: Any, *,
                  mark_equal: bool = False, tier: str | None = None) -> dict[str, Any]:
    """一条池内题面 vs 一行主库记录的置信度（判据 2.5 的唯一出口）。

    ``row`` 用 ``bank_rows_snapshot`` / ``similarity_report`` 那种带 ``stem``、
    ``options``、``answer`` 的行；答案只作信号、不作判据——两边都没表态时
    传 ``None``，绝不折成「答案不同」。
    """
    verdict = bank_dedupe.confidence(
        bank_dedupe.surface_text(document.get("stem"), document.get("options")),
        bank_dedupe.surface_text(row["stem"], row["options"]),
        mark_equal=mark_equal,
        answer_state=answers_agree(answer_from_storage(row["answer"], row["type"]),
                                   document.get("answer")))
    verdict["tier"] = str(tier or bank_dedupe.DEFAULT_TIER)
    verdict["accepted"] = bool(verdict["level"]) and bank_dedupe.accepts(verdict["level"], tier)
    return verdict


def _pair_confidence(left: dict[str, Any], right: dict[str, Any], *,
                     answer_state: Any = None) -> dict[str, Any]:
    """两条候选行 → 置信度 dict（含 label），判据 2.5 的唯一出口。"""
    verdict = bank_dedupe.confidence(left["surface"], right["surface"],
                                     answer_state=answer_state)
    verdict["label"] = LEVEL_LABELS_TEXT.get(verdict["level"], "")
    return verdict


def _better(verdict: dict[str, Any], current: dict[str, Any] | None,
            tier: str) -> bool:
    """新的一对是否比已选的那对更像；档位不达门槛直接不算。"""
    level = verdict["level"]
    if not level or not bank_dedupe.accepts(level, tier):
        return False
    if current is None:
        return True
    return bank_dedupe.level_rank(level) < bank_dedupe.level_rank(current["level"])


def _candidate_entry(row: Any) -> dict[str, Any]:
    """池内一行 → 候选比对行（题面文本 + 题型 + **契约答案对象**）。"""
    document = json.loads(row["doc_json"] or "{}")
    return {
        "id": str(row["id"]),
        "seq": int(row["seq"] or 0),
        "type": str(document.get("type") or ""),
        "surface": bank_dedupe.surface_text(document.get("stem"), document.get("options")),
        "answer": document.get("answer"),
    }


def _bank_entry(row: Any) -> dict[str, Any]:
    """主库一行 → 候选比对行。答案列存的是纯文本，先过 ``answer_from_storage`` 再比。"""
    answer = row["answer"] if "answer" in row.keys() else ""
    return {
        "id": str(row["id"]),
        "type": str(row["type"] or ""),
        "surface": bank_dedupe.surface_text(row["stem"], row["options"]),
        "answer": answer_from_storage(answer, row["type"]),
    }


def similarity_report(provider_id: str, document: dict[str, Any],
                      assets: list[dict[str, Any]], *,
                      threshold: float = HIGH_SIMILARITY,
                      tier: str | None = None) -> dict[str, Any]:
    """在主库里找**同题或高度相似题**，回一张可供老师裁决的报告。

    与 :func:`find_duplicate` 的分工：那个函数只认指纹全等，是入库闸门；
    这个函数多给一档「高度相似」，用于入库前的后台预检——老师看一眼就该知道
    「这道题主库里已经有了，只是标点写法不同」。

    军令 #32 · S2 起的口径（判据 2.5／2.6，**只有一把尺子**）：档位与百分比由
    ``bank_dedupe.confidence`` 算——正文骨架负责召回、公式签名负责判重，旧的
    0.92 逐字比门槛就是这里的「很像」门槛，不再是另一套阈值。
    ``threshold`` 形参保留只为兼容旧调用方（前端还没换尺子），新代码请传 ``tier``。

    出参**形状与旧版逐字兼容**（前端 ``ui_approve.js`` 还在读这六个键，改形状是
    第四棒的活）：``level`` 为 ``identical`` / ``high`` / ``none``——「确定」映射成
    ``identical``，「很像」及以上映射成 ``high``；``similarity`` 仍是 0~1 的相似比。
    新增键是**纯增量**：``confidence``（档位/标签/百分比/信号明细）、``tier``。
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
        "confidence": {"level": "", "label": "", "percent": 0, "signals": []},
        "tier": str(tier or bank_dedupe.DEFAULT_TIER),
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
    surface = bank_dedupe.surface_text(document.get("stem"), document.get("options"))
    compared = 0
    best: tuple[Any, dict[str, Any]] | None = None
    for row in rows:
        # 题型不同的一律跳过：选择题与填空题就算题干一字不差也是两种用法。
        if str(row["type"] or "") != text_key[0]:
            continue
        row_key = _text_key(row["type"], row["stem"], row["options"])
        if row_key == text_key and _fingerprint(
                row_key, _bank_image_hashes(row["extensions"])) == target:
            # 指纹全等：这就是同一道题，不必再比相似度，直接收工。
            existing_answer = answer_from_storage(row["answer"], row["type"])
            verdict = confidence_of(document, row, mark_equal=True, tier=tier)
            report.update({"hit": True, "level": LEVEL_IDENTICAL, "similarity": 1.0,
                           "existing_id": str(row["id"]), "confidence": verdict})
            report["answer"]["existing"] = answer_key(existing_answer)
            report["answer"]["same"] = answers_agree(existing_answer, document.get("answer"))
            return report
        if compared >= MAX_COMPARE:
            report["truncated"] = True
            break
        compared += 1
        verdict = confidence_of(document, row, tier=tier)
        if best is None or verdict["percent"] > best[1]["percent"]:
            best = (row, verdict)
    if best is not None:
        row, verdict = best
        # `similarity` 沿用旧键名与旧值域（0~1），但尺子换成新档位的骨架相似度——
        # 题干逐字比已被「数学段挖掉再比」取代：题干里那几个字符恰恰是最会打的字。
        # 判据 2.6 要的是「一把尺子」，不是「新旧各跑一遍」。
        legacy_score = verdict["similarity"]
        hit = verdict["level"] == "certain" or bool(
            verdict["level"] and legacy_score >= threshold
            and bank_dedupe.accepts(verdict["level"], tier))
        if hit:
            existing_answer = answer_from_storage(row["answer"], row["type"])
            report.update({"hit": True, "level": LEVEL_HIGH,
                           "similarity": round(legacy_score, 4),
                           "existing_id": str(row["id"]), "confidence": verdict})
            report["answer"]["existing"] = answer_key(existing_answer)
            report["answer"]["same"] = answers_agree(existing_answer, document.get("answer"))
        else:
            report["similarity"] = round(legacy_score, 4)
    return report
