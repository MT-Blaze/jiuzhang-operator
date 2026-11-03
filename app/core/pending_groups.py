"""批次查重清单的归并与剔除计划（军令 #32 · S5b 拆出）。

**来源**：整块搬自 ``app/core/pending_dedupe.py``，纯 extract-module，判据口径逐字未改；
``pending_dedupe`` 原位 re-export 本模块全部名字。

**边界**：输入是**已经取好的行**（中转站行 + 主库快照行），输出是「哪些算重复、按指纹该剔谁」
——组与计划都是纯结构计算，不读库、不写库、不碰扫描缓存。
取主库快照的 ``bank_rows_snapshot`` 留在 ``pending_dedupe``（后台初查链与测试都在那儿打桩），
读它之后再把行交给本模块。指纹与置信度口径来自 ``pending_compare``／``dedupe_signature``。

**禁区**：
- 「一键剔除」只出**计划**，实际删除仍由 ``pending_dedupe.batch_duplicate_groups`` 与批次清退走写库；
- 组内保留谁、剔谁按指纹与题号定序，别处不许另立一套成序规则。
"""

from __future__ import annotations

import json
from typing import Any

from app.core.pending_compare import (
    _bank_image_hashes,
    _fingerprint,
    _pending_image_hashes,
    _text_key,
)

def bank_fingerprint_map(main_rows: list[Any],
                         text_keys: set[tuple[str, str, tuple[str, ...]]]) -> dict[str, list[str]]:
    """主库侧指纹表 ``{指纹: [题号升序]}``，只算**文字键命中池内题**的那些行。

    两阶段筛选，与 :func:`find_duplicate` 的既有做法同源：先比文字键，文字键不同的行
    连图都不用算；只有键相等才去算配图内容哈希。同指纹多行全部保留 id 并升序排，
    调用方取 ``[0]`` 就是清单里那个 ``existing_id``。
    """
    mapping: dict[str, list[str]] = {}
    for row in main_rows:
        row_key = _text_key(row["type"], row["stem"], row["options"])
        if row_key not in text_keys:
            continue
        fingerprint = _fingerprint(row_key, _bank_image_hashes(row["extensions"]))
        mapping.setdefault(fingerprint, []).append(str(row["id"]))
    return {fingerprint: sorted(ids) for fingerprint, ids in mapping.items()}


def _pool_entry(row: Any) -> dict[str, Any]:
    """池内一行算成「id + 录入次序 + 文字键 + 指纹」。"""
    document = json.loads(row["doc_json"] or "{}")
    assets = json.loads(row["assets_json"] or "[]") if row["assets_json"] else []
    text_key = _text_key(document.get("type"), document.get("stem"), document.get("options"))
    return {
        "id": str(row["id"]),
        "seq": int(row["seq"] or 0),
        "text_key": text_key,
        "fingerprint": _fingerprint(text_key, _pending_image_hashes(document, assets)),
    }


def group_duplicates(pool_rows: list[Any], main_rows: list[Any]) -> dict[str, Any]:
    """纯计算：池内行 + 主库行快照 → 重复组。**dry-run 与执行口共用这一份逻辑。**

    出参：

    - ``groups``：先 ``batch`` 组（按 keep 的 ``seq_keep`` 升序），再 ``bank`` 组
      （按 ``drop`` 里的编号升序）；
    - ``drop_ids``：``batch`` 组 ``drop`` 的并集、升序，即前端默认勾选集；
    - ``recompute``：两组 ``drop`` 的并集、升序，**不含任何 keep**（保留者不可能成为剔除项）；
    - ``keep_ids``：``batch`` 组的保留者，执行口据此拦「勾了保留者」；
    - ``redundant`` / ``scanned``：重复全集条数 / 池内行数。

    一条 ``p_`` 只进一个组：批内重复已经成组的那几条（keep 与 drop 都算）不再按主库
    命中单列。落选者已被批内去重覆盖；keep 是「要留的那条」，若再列成删除项，老师
    勾不动它、不勾它又会永久计入 ``new_redundant``。批内去重后仍与主库重复的 keep，
    交给入库时的终局闸门处理，不在本清单重复报。
    """
    pool = [_pool_entry(row) for row in pool_rows]
    by_fingerprint: dict[str, list[dict[str, Any]]] = {}
    for entry in pool:
        by_fingerprint.setdefault(entry["fingerprint"], []).append(entry)

    batch_groups: list[dict[str, Any]] = []
    covered: set[str] = set()
    for fingerprint, entries in by_fingerprint.items():
        if len(entries) < 2:
            continue
        ordered = sorted(entries, key=lambda item: (item["seq"], item["id"]))
        keep = ordered[0]
        batch_groups.append({
            "reason": "batch",
            "keep": keep["id"],
            "drop": [item["id"] for item in ordered[1:]],
            "fingerprint": fingerprint,
            "seq_keep": keep["seq"],
        })
        covered.update(item["id"] for item in ordered)
    batch_groups.sort(key=lambda group: (group["seq_keep"], group["keep"]))

    main_map = bank_fingerprint_map(main_rows, {entry["text_key"] for entry in pool})

    bank_groups: list[dict[str, Any]] = []
    for entry in pool:
        if entry["id"] in covered:
            continue
        existing = main_map.get(entry["fingerprint"])
        if not existing:
            continue
        bank_groups.append({
            "reason": "bank",
            "keep": "",
            "drop": [entry["id"]],
            "fingerprint": entry["fingerprint"],
            "existing_id": existing[0],
        })
    bank_groups.sort(key=lambda group: group["drop"][0])

    batch_drop = sorted({item_id for group in batch_groups for item_id in group["drop"]})
    recompute = sorted(set(batch_drop)
                       | {item_id for group in bank_groups for item_id in group["drop"]})
    return {
        "groups": batch_groups + bank_groups,
        "drop_ids": batch_drop,
        "recompute": recompute,
        "keep_ids": sorted(group["keep"] for group in batch_groups),
        "redundant": len(recompute),
        "scanned": len(pool),
        # 每个 drop 的**匹配指纹**：批内组就是那枚共用的指纹；主库组按同一口径现算
        # 一次（``groups`` 里那枚 ``fingerprint`` 是候选层唯一能拿到的等号来源）。
        "drop_fingerprints": drop_fingerprints(batch_groups, bank_groups, pool),
    }


def drop_fingerprints(batch_groups: list[dict[str, Any]],
                      bank_groups: list[dict[str, Any]],
                      pool: list[dict[str, Any]]) -> dict[str, str]:
    """``{池内题号: 匹配上的那枚指纹}``，只给已经成组的剔除项。

    批内组直接取分组时那枚共用指纹；主库组的 ``groups`` 里只记了 ``existing_id``，
    指纹取池内条目算好的同一个值——**不重算、不另立口径**，dry-run 与候选清单两个
    入口于是拿到同一份数字。
    """
    marks: dict[str, str] = {}
    for group in batch_groups:
        for item_id in group["drop"]:
            marks[str(item_id)] = str(group.get("fingerprint") or "")
    by_id = {str(entry["id"]): str(entry["fingerprint"]) for entry in pool}
    for group in bank_groups:
        for item_id in group["drop"]:
            marks[str(item_id)] = by_id.get(str(item_id), "")
    return marks
