"""中转站的查重口径：与 core-bank 指纹引擎同源，但配图按**内容哈希**比。

池子里的图叫 ``pimg_x.png``、主库里的图叫 ``img_x.png``——同一个文件两个名字，
按文件名比永远比不上，按内容哈希比才是真的同一张图。

判据四要素：题型、归一题干、归一选项、配图内容全一致。先比文字键再比图：
文字键不同的题连图都不用算，几百道题扫一遍也只是几次字符串归一。

**军令 #32 · S5b**：本文件原 1065 行撞破 800 行上限，比对层整块搬到 ``pending_compare``、
批次归并层搬到 ``pending_groups``，名字在下方原位 re-export，外部用法一字不改；
留下的只有扫描缓存、扫描持久化、后台初查链与抽走进池。
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any

from app.core import bank, bank_dedupe, questions
from app.core.pending_batches import batch_row
from app.core.pending_db import connect



# 军令 #32 · S5b：比对层与批次归并层已拆出（本文件原 1065 行撞破 800 行上限）。
# 原位 re-export：外部照旧用 pending_dedupe.<名字>；本文件后半段的初查链也照旧按模块全局名
# 取用，测试里 monkeypatch pending_dedupe.bank_rows_snapshot / _scan_seq / admit_into_pool 不受影响。
from app.core.pending_compare import (  # noqa: F401
    _sha256_file,
    _text_key,
    _fingerprint,
    _upload_asset_path,
    _bank_image_hashes,
    _pending_image_hashes,
    find_duplicate,
    HIGH_SIMILARITY,
    MAX_COMPARE,
    LEVEL_IDENTICAL,
    LEVEL_HIGH,
    LEVEL_NONE,
    LEVELS_HIGH_OR_ABOVE,
    LEVEL_LABELS_TEXT,
    _answer_object,
    answer_key,
    answer_mismatch,
    answers_agree,
    similarity,
    confidence_of,
    similarity_report,
    # 军令 #32 · G7：候选层的四个纯函数整体搬到比对层（本文件曾 816 行撞破 800 上限）。
    # 它们只被 ``collect_candidates`` 内部调用，测试既不 patch 也不直接引用，
    # 外部按 ``pending_dedupe.<名字>`` 的取法一字不变。
    _pair_confidence,
    _better,
    _candidate_entry,
    _bank_entry,
)
from app.core.pending_groups import (  # noqa: F401
    bank_fingerprint_map,
    _pool_entry,
    group_duplicates,
    drop_fingerprints,
)

# ------------------------------------------------------------ 批次查重清单（一键剔除）

# 剔除器只认这两类口径：``batch`` 是「批内互相重复」，``bank`` 是「与主库命中」。
# API 与前端一律按枚举值分支，不认识具体判定——将来加第三类口径只改枚举与分支。
DUPLICATE_REASONS = ("batch", "bank")


def bank_rows_snapshot(provider_id: str) -> list[Any]:
    """主库行快照：一次全表读，只回行，不读图也不算指纹。

    ``answer`` 列一并读出（军令 #32 · S3）：候选层的「答案一致」信号要用它。多读
    一列不改变本函数的任何判据——指纹那套仍然只认题型/题干/选项/配图四要素。

    **连接异常原样往上抛**（``bank.BankNotFound`` / ``bank.BankError``），一条都不吞：
    吞掉会让清单假装「本批没有与主库重复的题」，老师按清单执行就漏剔了。
    这与 :func:`find_duplicate` 的单条实时判定口径不同——那边吞异常只是「这次没比出同题」，
    这边吞异常是「清单少了一整类」，性质不同。
    """
    con = bank.connect(provider_id)
    try:
        rows = con.execute(
            "SELECT id, type, stem, options, extensions, answer FROM questions"
        ).fetchall()
    finally:
        con.close()
    return list(rows)


def batch_duplicate_groups(batch_id: str, provider_id: str, *,
                           main_rows: list[Any] | None = None) -> dict[str, Any]:
    """一键剔除前的清单（dry-run）：**只读不写**，池内行数与批次账目一个字都不动。

    ``redundant`` 是两组 ``drop`` 的并集条数，``drop_ids`` 只是默认勾选集（``batch``
    组的 ``drop`` 并集），``live_after`` 与 ``will_empty`` 都按默认勾选集算——老师改勾选
    后由前端按 ``scanned - 勾选数`` 实时重算，服务端不猜。

    ``main_snapshot_at`` 如实暴露主库快照时刻：两段竞态窗口（``[dry-run, 执行 S0]``
    与毫秒级残窗）都以它为起点，最坏结果只影响池内副本的取舍，不碰主库一行。

    ``main_rows`` 是**初查链的复用挂点**（G4）：一次初查只许读主库一次，``_run_scan``
    自己取好快照再递进来，``main_scanned`` 与候选层因此同一代。传 ``None`` 时本函数照旧
    自读一次——同步入口（``app/api/pending.py:254`` 的 dry-run）与一键剔除写链不动。
    该参数**只进不出**：返回 dict 里不带 ``main_rows``，它就是 HTTP 响应体，行对象进
    JSON 会炸；``dedupe_scans``／``dedupe_findings`` 的列与口径更不因此改变。
    外部传入快照时 ``main_snapshot_at`` 是本函数的取时刻，真实快照更早（同一轮调用内，
    毫秒级），竞态窗口口径因此**偏小不偏大**——如实登记，不假装它等于快照时刻。
    """
    if main_rows is None:
        main_rows = bank_rows_snapshot(provider_id)
    snapshot_at = questions.now_iso()
    con = connect()
    try:
        if batch_row(con, batch_id) is None:
            raise PendingNotFound("中转站里没有这个批次")
        rows = con.execute(
            "SELECT id, doc_json, assets_json, seq FROM pending_questions"
            " WHERE batch_id = ? ORDER BY seq ASC, id ASC",
            (batch_id,),
        ).fetchall()
    finally:
        con.close()
    planned = group_duplicates(rows, main_rows)
    scanned = len(rows)
    live_after = scanned - len(planned["drop_ids"])
    fingerprints = planned["drop_fingerprints"]
    return {
        "batch_id": batch_id,
        "provider_id": provider_id,
        "scanned": scanned,
        "redundant": planned["redundant"],
        "drop_fingerprints": fingerprints,
        "live_after": live_after,
        "will_empty": live_after == 0,
        "main_snapshot_at": snapshot_at,
        "main_scanned": len(main_rows),
        "groups": planned["groups"],
        "drop_ids": planned["drop_ids"],
    }


# ---------- 整批自动初查（军令 #31 · 3.1a → 军令 #32 · S3） ----------
# 进程内缓存仍是「这一次会话里的快取」，但结论**必须跨过重启可读**（判据 3.3）：
# 底座一开，缓存空了不等于「这批没有重复」，报「还没扫」就是把已做过的初查抹掉。
# 所以 warm_batch_scan 同时写 ``dedupe_scans``（账目/状态）与 ``dedupe_findings``
# （每条候选一行）；scan_state 在缓存未命中时回读库。两张表只存结论、不存题目，
# 池内容永远是事实来源——重算一遍自然覆盖。
# 写法对齐既有先例 ``app/core/basket.py:23``、``app/core/plugin_state.py:20``：
# 模块级 ``threading.Lock`` + 进程内状态。
_scan_lock = threading.Lock()
_scan_cache: dict[str, dict[str, Any]] = {}
# 发起世代号（[DESIGN-2 勘误·二] ②）：只允许世代更大者覆盖缓存，与 status 无关。
# 只在 ``_scan_lock`` 内读写；落库时也带上，让重启后的新一代不会用旧结论盖新结论。
_scan_seq = 0
# 候选上限：一批最多回投这么多条（按「越像越前」截断），``truncated`` 如实报截了多少。
MAX_CANDIDATES = 200


def _group_counts(groups: Any) -> tuple[int, int]:
    """按 ``reason`` 拆出「批内重复」与「主库已有」的条数（只数 drop，不数保留者）。"""
    batch_count = 0
    bank_count = 0
    for group in groups or []:
        drops = group.get("drop") or []
        if str(group.get("reason") or "") == "batch":
            batch_count += len(drops)
        else:
            bank_count += len(drops)
    return batch_count, bank_count


def _scan_view(stored: dict[str, Any], *, strip_generation: bool) -> dict[str, Any]:
    """缓存行 / 库行 → 对外注解：剥掉内部键，failed 一律如实带 code + retryable。"""
    out = dict(stored)
    if strip_generation:
        out.pop("seq", None)
    out.setdefault("candidates", [])
    out.setdefault("truncated", False)
    out.setdefault("tier", bank_dedupe.DEFAULT_TIER)
    return out


def collect_candidates(pool_rows: list[Any], main_rows: list[Any], *,
                       tier: str | None = None,
                       fingerprints: dict[str, str] | None = None) -> dict[str, Any]:
    """整批初查的**候选清单**（判据 3.1）：在既有判重口径之上产出「重题候选」。

    不新写第二个引擎：批内分组完全复用 :func:`group_duplicates`（指纹全等那套），
    本函数只在它之外补一层**骨架召回**——把「指纹不等但题面像」的配对也找出来，
    每对给一个 ``bank_dedupe.confidence`` 的档位，再按档位门槛（判据 3.2 默认「宽」）
    筛掉不够格的。

    出参 ``candidates`` 每条是「一条池内题 + 它像谁」：

    - ``item_id``：池内题号；``level``/``label``/``percent``：置信度；
    - ``reason``：``batch``＝本批另一条像它（``keep_id`` 是那条），
      ``bank``＝主库里有像它的（``existing_id`` 是那条）；
    - ``fingerprint``：**指纹全等**那一条的指纹；只在 ``level=="certain"`` 时有值，
      其余档位是「像但不是同一枚指纹」，留空串——伪造一个等号是判据 2.6 不允许的；
    - ``signals``：可展开的命中/未命中明细，原样来自 ``confidence``，前端不动口径。

    排序按题号（与 ``groups``/``drop_ids`` 同一序），同一条题只留最强的一对（老师看
    一次就够）；超过 ``MAX_CANDIDATES`` 截断并置 ``truncated``——**如实报截了多少**，
    不假装扫全；逐字比对的代价上限沿用既有 ``MAX_COMPARE``，撞到它同样如实报。
    """
    limit = str(tier or bank_dedupe.DEFAULT_TIER)
    exact = group_duplicates(pool_rows, main_rows)
    # 批内成组的那几条到底有没有主库原题，得单独问一次指纹。``group_duplicates``
    # 的「一条 p_ 只进一个组」让批内组把成员全吃掉（军令 #31 为「一键剔除」定的口径），
    # 主库命中于是从**候选清单**里消失；而抽走只认 ``reason="bank"``——四道同题面命中
    # 就只搬走一道，剩下三道挂在待审里等一个已经不在待审的「保留者」（S6 缺陷 1）。
    # 这里按**同一枚指纹**把主库那一侧补回来：成员全部改报主库命中，配同一道原题。
    # ``groups``／``drop_ids`` 一个字没动，一键剔除那套照旧。
    main_hits = bank_fingerprint_map(main_rows,
                                     {_pool_entry(row)["text_key"] for row in pool_rows})
    pooled: dict[str, dict[str, Any]] = {}
    for group in exact["groups"]:
        fingerprint = str(group.get("fingerprint") or "")
        bank_hit = str((main_hits.get(fingerprint) or [""])[0]) if group["reason"] == "batch" else ""
        existing_id = str(group.get("existing_id") or "") or bank_hit
        reason = "bank" if existing_id else "batch"
        # 批内组一旦配上主库原题，连「要留的那条」也是原题的重题，不再 exempt。
        members = ([group["keep"], *group["drop"]]
                   if (bank_hit and group.get("keep")) else list(group["drop"]))
        for item_id in members:
            pooled[item_id] = {
                "item_id": item_id,
                "reason": reason,
                "keep_id": str(group.get("keep") or "") if reason == "batch" else "",
                "existing_id": existing_id,
                "level": "certain",
                "label": LEVEL_LABELS_TEXT["certain"],
                "percent": 100,
                "fingerprint": fingerprint,
                "similarity": 1.0,
                "signals": [],
            }

    # 骨架召回：指纹没全等的题才走这一步，比对代价全在这里。
    entries = [_candidate_entry(row) for row in pool_rows]
    bank_entries = [_bank_entry(row) for row in main_rows]
    compared = 0
    truncated = False
    for entry in entries:
        if entry["id"] in pooled or not entry["surface"]:
            continue
        best: dict[str, Any] | None = None
        for peer in entries:
            if peer is entry or peer["id"] in pooled:
                continue
            if compared >= MAX_COMPARE:
                truncated = True
                break
            compared += 1
            if peer["type"] != entry["type"]:
                continue
            verdict = _pair_confidence(entry, peer)
            if not _better(verdict, best, limit):
                continue
            best = {**verdict, "item_id": entry["id"], "reason": "batch",
                    "keep_id": peer["id"], "existing_id": "", "fingerprint": ""}
        # 命中比对上限（MAX_COMPARE）从批内这一圈退出时，**不许把已经找到的 best 丢掉**：
        # 外圈循环照旧停，但这一条题的最优命中要先进候选账（S2／G2）。
        # 主库那一圈进不去时第一步就撞上同一上限并立刻 break，不会多比一次。
        for peer in bank_entries:
            if compared >= MAX_COMPARE:
                truncated = True
                break
            compared += 1
            if peer["type"] != entry["type"]:
                continue
            verdict = _pair_confidence(entry, peer,
                                       answer_state=answers_agree(peer["answer"], entry["answer"]))
            if not _better(verdict, best, limit):
                continue
            best = {**verdict, "item_id": entry["id"], "reason": "bank", "keep_id": "",
                    "existing_id": peer["id"], "fingerprint": ""}
        if best is not None:
            pooled[best["item_id"]] = best
        if truncated:
            break

    ranked = sorted(pooled.values(),
                    key=lambda item: (item["item_id"], bank_dedupe.level_rank(item["level"])))
    for item in ranked:
        # 「确定」档才有匹配指纹：主库命中那一侧的指纹不在 dry-run 清单里，由调用方
        # （``warm_batch_scan``）按同一口径算好递进来；算不到就留空串，不编一个等号。
        # 批内组升级成主库命中的那些，指纹已经在组里算好了（``drop_fingerprints``
        # 只覆盖剔除项，覆盖不到「要留的那条」），递不进来就别把它抹成空串。
        if item["level"] == "certain":
            item["fingerprint"] = ((fingerprints or {}).get(item["item_id"])
                                   or item.get("fingerprint") or "")
    kept = ranked[:MAX_CANDIDATES]
    dropped = max(0, len(ranked) - len(kept))
    return {
        "candidates": kept,
        "truncated": bool(truncated or dropped),
        "dropped": dropped,
        "compared": compared,
        "tier": limit,
        # 排序键是「题号 + 档位」的字典序，直接用 group_duplicates 排好的 ``groups``
        # 回填指纹——候选行成序与它一致，按位对齐比按 id 再匹配一次更稳。
        "fingerprints": {drop: str(group.get("fingerprint") or "")
                         for group in exact["groups"] for drop in group["drop"]},
        "groups": exact["groups"],
        "drop_ids": exact["drop_ids"],
        "recompute": exact["recompute"],
        "keep_ids": exact["keep_ids"],
        "redundant": exact["redundant"],
        "scanned": exact["scanned"],
    }


def _write_scan_rows(con: Any, batch_id: str, state: dict[str, Any],
                     candidates: list[dict[str, Any]]) -> bool:
    """在**给定连接**里落初查结论：不 commit、不 close——调用方说了算。

    这是抽走事务要用的那一半（军令 #32 · S6 缺陷 2 收口）：「写池行＋删待审行＋
    刷新批次账目＋落 ``done``」必须一次提交同时对外可见，所以这几条 SQL 得跟着
    ``pending_pool.admit_from_scan`` 那把 ``BEGIN IMMEDIATE`` 走，而不是等它提交完
    再另起连接补写——那正是「池里已经有题、卡片还说全在待审」这一拍的来源。

    回 ``True`` 表示真的写了这一代；被世代号挡下（库里已有更晚发起的结论）回 ``False``。
    """
    stored = con.execute("SELECT generation FROM dedupe_scans WHERE batch_id = ?",
                         (batch_id,)).fetchone()
    if stored is not None and int(stored["generation"] or 0) > int(state.get("seq") or 0):
        return False
    con.execute(
        "INSERT OR REPLACE INTO dedupe_scans (batch_id, provider_id, status, scanned,"
        " redundant, batch_redundant, bank_redundant, main_scanned, tier, truncated,"
        " code, retryable, message, finished_at, generation)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (batch_id, str(state.get("provider_id") or ""), str(state["status"]),
         int(state.get("scanned") or 0), int(state.get("redundant") or 0),
         int(state.get("batch_redundant") or 0), int(state.get("bank_redundant") or 0),
         int(state.get("main_scanned") or 0), str(state.get("tier") or bank_dedupe.DEFAULT_TIER),
         1 if state.get("truncated") else 0, str(state.get("code") or ""),
         1 if state.get("retryable") else 0, str(state.get("message") or ""),
         str(state.get("at") or questions.now_iso()),
         int(state.get("seq") or 0)))
    # 抹账只发生在「这一代要重写 findings」的时候（G2·S1）：``failed`` 态不动旧行——
    # 一次重扫失败就把上一轮已存的 findings 抹平，卡片与琥珀灯会同时断账（判据 3.3/3.4）。
    # 幂等口径定死为：**同一批的 findings 只由最新一代 done 拥有**，done 重扫整批替换、
    # 连扫两次同一数据行数不翻倍；failed／非 done 只更新 ``dedupe_scans`` 那一行。
    if state["status"] != "done":
        return True
    con.execute("DELETE FROM dedupe_findings WHERE batch_id = ?", (batch_id,))
    for item in candidates:
        con.execute(
            "INSERT OR REPLACE INTO dedupe_findings (batch_id, item_id, reason,"
            " keep_id, existing_id, level, percent, similarity, fingerprint,"
            " signals_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (batch_id, str(item["item_id"]), str(item["reason"]),
             str(item.get("keep_id") or ""), str(item.get("existing_id") or ""),
             str(item["level"]), int(item.get("percent") or 0),
             float(item.get("similarity") or 0.0),
             str(item.get("fingerprint") or ""),
             json.dumps(item.get("signals") or [], ensure_ascii=False),
             str(state.get("at") or questions.now_iso())))
    return True


def persist_scan_in_txn(con: Any, batch_id: str, state: dict[str, Any]) -> bool:
    """给抽走事务用的挂点：把本轮结论写进调用方那条事务里（判据 3.3／3.5）。

    只在结论是 ``done``／``failed`` 时写；写了回 ``True``，让 ``_publish_scan``
    知道库里已经有这一代、不必再补一次（补了就是把同一份账写两遍，还多出一次可见翻转）。
    """
    if not isinstance(state, dict) or str(state.get("status") or "") not in ("done", "failed"):
        return False
    return _write_scan_rows(con, str(batch_id or ""), state,
                            list(state.get("candidates") or []))


def _persist_scan(batch_id: str, state: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
    """把一次初查的结论写进 ``dedupe_scans`` + ``dedupe_findings``（判据 3.3）。

    世代号比库里那条大才写：两个后台线程同时在扫（重启后立刻又入题）时，
    落库顺序可能和发起顺序相反，旧代不能盖新代——与进程内缓存同一规矩。
    写失败只记日志、不改内存结论：初查是显形增强，绝不让它把导入牵连坏。

    同步入口（``admit=False``）走这一条自开连接；后台抽走链的结论由
    :func:`persist_scan_in_txn` 随池行一并提交，不再经过这里。
    """
    con = connect()
    try:
        _write_scan_rows(con, batch_id, state, candidates)
        con.commit()
    finally:
        con.close()


def _load_scan(batch_id: str, con: Any = None) -> dict[str, Any] | None:
    """重启后回读初查结论；库里没有这一批就是真没扫过（``None`` → ``pending``）。

    ``con`` 传入时**只用这条连接**、既不自开也不关（G5）：批次卡片要在同一条读事务里
    把「结论＋待审数＋池内数」一次读齐，结论另开一条连接就会读到比计数更新的一代。
    """
    own = con is None
    if own:
        con = connect()
    try:
        row = con.execute("SELECT * FROM dedupe_scans WHERE batch_id = ?",
                          (batch_id,)).fetchone()
        if row is None:
            return None
        state: dict[str, Any] = {
            "status": str(row["status"]),
            "provider_id": str(row["provider_id"]),
            "tier": str(row["tier"] or bank_dedupe.DEFAULT_TIER),
            "truncated": bool(row["truncated"]),
            "at": str(row["finished_at"]),
            "seq": int(row["generation"] or 0),
        }
        if state["status"] != "done":
            # 失败态只回失败态该有的键：把「0 条重复」的账目一起带回去，
            # 读的人就分不清「扫过没重复」和「压根没扫成」（判据 3.4）。
            if row["code"]:
                state["code"] = str(row["code"])
                state["retryable"] = bool(row["retryable"])
            if row["message"]:
                state["message"] = str(row["message"])
            state["candidates"] = []
            return state
        state.update({
            "scanned": int(row["scanned"] or 0),
            "redundant": int(row["redundant"] or 0),
            "batch_redundant": int(row["batch_redundant"] or 0),
            "bank_redundant": int(row["bank_redundant"] or 0),
            "main_scanned": int(row["main_scanned"] or 0),
        })
        candidates: list[dict[str, Any]] = []
        for found in con.execute(
                "SELECT item_id, reason, keep_id, existing_id, level, percent,"
                " fingerprint, similarity, signals_json FROM dedupe_findings"
                " WHERE batch_id = ? ORDER BY item_id ASC", (batch_id,)):
            candidates.append({
                "item_id": str(found["item_id"]),
                "reason": str(found["reason"]),
                "keep_id": str(found["keep_id"] or ""),
                "existing_id": str(found["existing_id"] or ""),
                "level": str(found["level"]),
                "label": LEVEL_LABELS_TEXT.get(str(found["level"]), ""),
                "percent": int(found["percent"] or 0),
                "fingerprint": str(found["fingerprint"] or ""),
                "similarity": float(found["similarity"] or 0.0),
                "signals": json.loads(found["signals_json"] or "[]"),
            })
        # 与 ``collect_candidates`` 的成序**完全一致**（题号优先，再按档位）：
        # 重启前后是同一份账，差别只在内存里还是库里。
        candidates.sort(key=lambda item: (item["item_id"],
                                          bank_dedupe.level_rank(item["level"])))
        state["candidates"] = candidates
        state["candidate_count"] = len(candidates)
        return state
    finally:
        if own:
            con.close()


def _take_scan_seq() -> int:
    """取世代号：按「读取发起时刻」排序，取号必须早于真正开扫。"""
    global _scan_seq
    with _scan_lock:
        _scan_seq += 1
        return _scan_seq


def _run_scan(key: str, provider_id: str, seq: int) -> dict[str, Any]:
    """跑一整轮初查，**只算不发布**：回 ``done``／``failed`` 两种内存结论之一。

    发布（写缓存＋落库）一律交给 :func:`_publish_scan`——判据 3.5 要的是「读到
    ``done`` 的那一刻抽走已经落地」，所以「算完」和「让人看见」必须是两步，
    中间才能插进抽走与抽完后的重算。
    """
    try:
        # **一次初查只读一次主库**（G4）。旧实现读两把不同代的快照：``batch_duplicate_groups``
        # 里一把（``main_scanned`` 与 ``groups`` 出自它），候选层这里又一把。建批后台线程与
        # 紧随的 ``approve`` 竞态时，快照 1 为空、快照 2 已含刚入库那行，落盘后跨重启可读，
        # 同一代结论就自相矛盾：``main_scanned=0 / redundant=0`` 却挂着一条 certain 自匹配，
        # ``existing_id`` 指向**这条待审自己刚变成的那个 q_**（判据 3.3 的反方向：多报一条
        # 永不消失的自匹配，不是漏报）。快照在这里取一次，同时喂分组与候选层。
        main_rows = bank_rows_snapshot(provider_id)
        result = batch_duplicate_groups(key, str(provider_id or ""), main_rows=main_rows)
    except Exception as error:  # 展示层初查：任何异常都只落缓存与一条日志，不冒回调用方
        logging.getLogger("uvicorn.error").warning(
            "待审批次初查失败 batch=%s err=%r", key, error)
        state = {
            "status": "failed",
            "code": "dedupe_scan_bank_unavailable",
            "retryable": True,
            "message": "初查失败、可重试：主库读不通，本批结论未出。",
            "at": questions.now_iso(),
            "seq": seq,
            "provider_id": str(provider_id or ""),
            "tier": bank_dedupe.DEFAULT_TIER,
            "candidates": [],
        }
        return state
    batch_count, bank_count = _group_counts(result.get("groups"))
    # **重复条数只有一把尺子**（G2·C2）：批内／主库两个分区都来自 ``groups`` 的 drop，
    # ``redundant`` 就取这两个分区之和，与 ``app/api/pending.py:233``「redundant 是两组
    # drop 的并集条数」以及批次卡片「疑似重复 N（批内 X ／ 主库 Y）」三数相加同源。
    # ``pending_groups`` 的 ``recompute``／``drop_ids`` 仍是默认勾选集与重算集，
    # 但它们不再充当「重复条数」——两套口径并存时卡片迟早对不平（判据 5.4）。
    redundant_total = batch_count + bank_count
    try:
        # 候选层**复用上面那一份快照**（G4 顺带修掉这里的假注释：原话写「主库行只读一次」，
        # 实现却在候选层这一行又读了一次）。读不通时不再影响账目——上面只读过一次，这里只算候选。
        found = collect_candidates(_pool_rows_for_scan(key), main_rows,
                                   fingerprints=result.get("drop_fingerprints") or {})
    except Exception as error:  # 候选层出错不影响已算出的账目：照旧报数，候选留空
        logging.getLogger("uvicorn.error").warning(
            "待审批次候选清单生成失败 batch=%s err=%r", key, error)
        found = {"candidates": [], "truncated": False, "tier": bank_dedupe.DEFAULT_TIER}
    candidates = found["candidates"]
    state = {
        "status": "done",
        "scanned": int(result.get("scanned") or 0),
        "redundant": redundant_total,
        "batch_redundant": batch_count,
        "bank_redundant": bank_count,
        "main_scanned": int(result.get("main_scanned") or 0),
        "candidate_count": len(candidates),
        "truncated": bool(found.get("truncated")),
        "tier": str(found.get("tier") or bank_dedupe.DEFAULT_TIER),
        "at": questions.now_iso(),
        "seq": seq,
        "provider_id": str(provider_id or ""),
        "candidates": candidates,
    }
    return state


def _publish_scan(key: str, state: dict[str, Any], *, persist: bool = True) -> None:
    """把这一轮结论**一次**公开：先写进程内缓存，再落库（判据 3.3 的两级回读）。

    ``persist=False`` 用于后台抽走链：结论已经由 :func:`persist_scan_in_txn` 随池行
    一并提交了，这里只补内存缓存；再写一遍就是把同一代账目翻转两次。
    """
    seq = int(state.get("seq") or 0)
    with _scan_lock:
        old = _scan_cache.get(key)
        if old is not None and int(old.get("seq") or 0) > seq:
            return  # 更晚发起的读取已写过：过期世代不覆盖
        _scan_cache[key] = state
    if persist:
        _safe_persist(key, state, state.get("candidates") or [])


def warm_batch_scan(batch_id: str, provider_id: str, *, admit: bool = False) -> None:
    """后台初查一个批次：判重仍走既有只读引擎，只把「只报数」换成「出候选」。

    成功写 ``done``（批内 / 主库两组条数 + 候选清单 + 档位），主库读不通等一切异常
    写 ``failed`` 并就地接住——初查只是显形增强，绝不让导入请求替它背错误。
    **两条路都落库**（判据 3.3／3.4）：重启后 ``failed`` 仍然读得到「初查失败、可重试」，
    绝不会被读成「0 条重复」。

    ``admit=True`` 是判据 3.5 的时序收口（军令 #32 · S6 缺陷 2 的最终形态）：结论
    **不落库**、只交给抽走那一步，由 ``admit_from_scan`` 把「写池行＋删待审行＋刷新
    批次账目＋落 ``done``」放进同一条事务一次提交——对外根本不存在「done 已可读但
    卡片还说全在待审」的那一拍，也不存在反过来「先抽走再说扫完了」的空窗。
    抽走完成后这里只补内存缓存（``persist=False``），不再重扫一遍改账：重扫会把
    ``scanned`` 从整批的 5 改成抽剩的 1，同一代账目翻两次，正是要消掉的东西。
    默认 ``False`` 给同步入口与测试用：它们只要结论，不代替后台链去动待审行。
    """
    key = str(batch_id or "")
    if not key:
        return
    seq = _take_scan_seq()
    state = _run_scan(key, provider_id, seq)
    persisted = False
    if admit and state.get("status") == "done":
        outcome = admit_into_pool(key, provider_id, state=state)
        persisted = bool(isinstance(outcome, dict) and outcome.get("scan_persisted"))
    _publish_scan(key, state, persist=not persisted)


def _safe_persist(batch_id: str, state: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
    """落库失败只记日志：内存里的这一轮结论照样可用。"""
    try:
        _persist_scan(batch_id, state, candidates)
    except Exception as error:  # 中转站被别人的写锁占住时不能让初查把导入带崩
        logging.getLogger("uvicorn.error").warning(
            "待审批次初查落库失败 batch=%s err=%r", batch_id, error)


def _pool_rows_for_scan(batch_id: str) -> list[Any]:
    """本批池内行（候选层用的列），与 dry-run 同一份读法。"""
    con = connect()
    try:
        return con.execute(
            "SELECT id, doc_json, assets_json, seq FROM pending_questions"
            " WHERE batch_id = ? ORDER BY seq ASC, id ASC",
            (batch_id,),
        ).fetchall()
    finally:
        con.close()


def bank_rows_for_candidates(provider_id: str) -> list[Any]:
    """候选层要读主库答案列，快照少一列就会在这里静默漏报——单独一条读法。

    连接异常**原样往上抛**（与 :func:`bank_rows_snapshot` 同一纪律）：主库读不通
    时调用方要落 ``failed``「初查失败、可重试」，绝不能把它当成「主库没有重复」。
    """
    con = bank.connect(provider_id)
    try:
        return con.execute(
            "SELECT id, type, stem, options, extensions, answer FROM questions"
        ).fetchall()
    finally:
        con.close()


def pooled_counts(con: Any = None) -> dict[str, int]:
    """按批次统计「已抽进重题池」的条数（判据 5.4 的账：未审数＋池内数对得上总数）。

    ``con`` 传进来时**只用这条连接**：不自开、不提交、不回滚——调用方那条读事务就是
    这批数的快照（G5）。批次卡片一次要读 N 张卡，逐卡自开连接就会跨过抽走事务的
    提交点，读出「待审 2 ＋ 池内 2 ＝ 总数 2」这种重复计数的帧。
    表还没迁出来（老工作区）或读不通时回空字典，卡片按 0 处理，绝不整批失败。
    """
    own = con is None
    try:
        if own:
            con = connect()
        try:
            return {str(row["batch_id"]): int(row["n"]) for row in con.execute(
                "SELECT batch_id, COUNT(*) AS n FROM duplicate_pool GROUP BY batch_id")}
        finally:
            if own:
                con.close()
    except Exception as error:  # 读不到就报 0，但不能让批次卡片整体失败
        logging.getLogger("uvicorn.error").warning(
            "重题池条数回读失败 err=%r", error)
        return {}


def _pooled_count(batch_id: str) -> int:
    """单批的池内条数：``pooled_counts`` 的便捷壳（卡片之外的调用点仍走这一条）。"""
    if not batch_id:
        return 0
    return int(pooled_counts().get(batch_id, 0))


def scan_state(batch_id: str, *, pooled: int | None = None,
               con: Any = None) -> dict[str, Any]:
    """批次卡片上的初查注解，外加「这一批已抽走几条」（``pooled``）。

    ``pooled`` **任何状态都给**（G2·C1，判据 5.4）：它是 ``duplicate_pool`` 的实时行数，
    与初查结论出不出无关。以前只在 ``done`` 时给，扫描进行中／失败态的卡片就拿不到池内数，
    前端 ``gone = total - pending - pooled - stored`` 会把已抽走的题折进「已裁删」——
    老师的题在账上凭空变成被删掉的。口径与 ``done`` 态一致：同一张池表数同一批。

    ``pooled``／``con`` 由调用方给定时（``batch_list`` 的同一快照批量数，G5）就**不再自开
    连接**，结论也改从那条读事务里回读；两个都不传仍是原样——各开各的缓存与实时行数，
    ``pending_pool`` 那类单点调用与其他测试的行为一字不变。
    """
    view = _scan_state_body(batch_id, con)
    view["pooled"] = (int(pooled) if pooled is not None
                      else _pooled_count(str(batch_id or "")))
    return view


def _scan_state_body(batch_id: str, con: Any = None) -> dict[str, Any]:
    """批次卡片上的初查注解：**先看进程内缓存，未命中回读库**（判据 3.3）。

    两边都没有才回 ``pending``——「还没扫」与「扫过且没重复」是两件事，
    重启不能把后者降级成前者。``seq`` 是内部世代键，回投前剥掉。

    ``con``（G5）＝调用方那条读事务：给了就**只走库、不碰缓存也不回填**，因为缓存记的是
    「发布那一刻」的结论，抽走事务提交之后才写它；跟读事务混用就会读出「计数是旧一代、
    状态是新一代」那帧（``done`` 配 ``pooled=0``）。
    """
    key = str(batch_id or "")
    if con is not None:
        try:
            pinned = _load_scan(key, con)
        except Exception as error:
            logging.getLogger("uvicorn.error").warning(
                "待审批次初查回读失败 batch=%s err=%r", key, error)
            pinned = None
        if pinned is None:
            return {"status": "pending"}
        return _scan_view(pinned, strip_generation=True)
    with _scan_lock:
        cached = _scan_cache.get(key)
    if cached is not None:
        return _scan_view(cached, strip_generation=True)
    try:
        stored = _load_scan(key)
    except Exception as error:  # 库读不通就照实说没扫过，不编一个结论出来
        logging.getLogger("uvicorn.error").warning(
            "待审批次初查回读失败 batch=%s err=%r", key, error)
        stored = None
    if stored is None:
        return {"status": "pending"}
    with _scan_lock:
        cached = _scan_cache.get(key)
        if cached is None or int(cached.get("seq") or 0) <= int(stored.get("seq") or 0):
            _scan_cache[key] = stored      # 回填缓存：一次回读，之后都走内存
            return _scan_view(stored, strip_generation=True)
        return _scan_view(cached, strip_generation=True)


def warm_dedupe_scan(batch_id: str) -> None:
    """后台初查任务体：线程内自行取活跃 provider（core→core 同层，零出网零写库）。

    provider 拿不到不另造第二套状态：带着空 id 交给 ``warm_batch_scan``，主库连不通
    自然落进它那条 ``failed`` 分支与日志——暂存本身早已提交成功，绝不被初查牵连。

    ``admit=True``：抽走由 ``warm_batch_scan`` 排在 ``done`` 发布**之前**，
    本线程体不再自己追一步（军令 #32 · S6 缺陷 2 的旧空窗就是这么来的）。
    """
    provider_id = ""
    try:
        from app.core import bank_provider

        provider_id = str(bank_provider.resolve().get("plugin_id") or "")
    except Exception as error:  # 只作降级：取不到题库就把空 id 交给下游的 failed 分支
        logging.getLogger("uvicorn.error").warning(
            "待审批次初查取题库失败 batch=%s err=%r", batch_id, error)
    warm_batch_scan(batch_id, provider_id, admit=True)


def admit_into_pool(batch_id: str, provider_id: str, *,
                    state: dict[str, Any] | None = None) -> dict[str, Any]:
    """把初查判出的主库命中**抽走**（判据 3.5）：只搬、不发布，结论归调用方。

    抽走发生在数据落库阶段，而且**结论 ``done`` 就写在这同一条事务里**——
    ``pending_pool.admit_from_scan`` 提交后回投 ``scan_persisted=True``，
    ``warm_batch_scan`` 于是只补内存缓存、不再另起连接补写库：库里根本不存在
    「池行已提交、done 还没落」或反过来的一拍（S6 缺陷 2 的最终形态）。
    失败只记日志：待审行原样留着、初查结论原样摆着，审核照旧一张一张能过，
    后台增强不许把导入或审核牵连坏。

    ``state`` 是本轮刚算好的初查结论（``admit_from_scan`` 自己去读 ``scan_state``
    时读不到——那时候 ``done`` 还没发布）。同步入口与测试不传，照旧回读已落盘的结论。

    ``JZO_POOL_ADMIT_DISABLED=1`` 只服务既有测试：#24/#25 那批用例的前提是
    「判出的重复题仍留在待审批次里」，与判据 3.5 直接冲突，先按用例隔离关掉，
    抽走本身由 ``tests/test_pending_pool.py`` 的 ``PoolEvictionTest`` 六条盯死。
    生产路径不看这个变量（默认就是抽）。

    **保留理由与量化代价（G2·S4，主公已裁：留接缝，不摘）**：四支既有测试仍在设它——
    ``tests/test_pending_api.py:88``、``tests/test_pending_meta.py:111``、
    ``tests/test_pending_dedupe_scan.py:129-130``、``tests/test_pending_purge.py:83-84``。
    用临时夹具把开关节掉、仓库零改的实测代价是 **红 15 条**：api 5／meta 7／
    dedupe_scan 1（``test_07b`` 3≠0）／purge 2（``test_01`` 0≠2、``test_17`` BatchPurgeError），
    失败形态一律是「命中题已被抽走 → 待审侧 404／少一行」；``test_pending_pool`` 32/32 不受影响。
    这些用例的前提（#24/#25 时代「重复题仍留在待审里」）与判据 3.5 结构性相冲，
    摘接缝等于一次跨四个模块的题意重写——本轮不做，HTTP 端到端由探针补位。
    """
    disabled = {"admitted": 0, "evicted": 0, "status": "admit_disabled"}
    if str(os.environ.get("JZO_POOL_ADMIT_DISABLED") or "") == "1":
        return disabled
    try:
        # 延迟导入：``pending_pool`` 顶层就 import 本模块，放到函数里断开循环。
        from app.core import pending_pool

        result = pending_pool.admit_from_scan(batch_id, provider_id=provider_id,
                                             state=state)
    except Exception as error:  # 抽走是增强，任何异常都只落一条日志
        logging.getLogger("uvicorn.error").warning(
            "重题池抽走失败 batch=%s err=%r", batch_id, error)
        return {"admitted": 0, "evicted": 0, "status": "error"}
    if result.get("admitted"):
        logging.getLogger("uvicorn.error").info(
            "重题池抽走 batch=%s admitted=%s evicted=%s",
            batch_id, result.get("admitted"), result.get("evicted"))
    return result
