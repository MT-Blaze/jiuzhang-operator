"""重题池（军令 #32 · 第四步）：跨批次存活的重题候选，与四个裁决动作。

这张池子**独立于待审池与批次**（主公口径，032.md 第二节）：

- 每条自带完整题目文档与自己裁下来的成品图，来源批次号与原文件名只是**溯源字段**，
  不作外键——批次消失之后，池里这条照常可读（判据 4.2）；
- 图跟题走：抽走那一刻就把待审池的 ``pimg_`` **复制**成本条目自己的 ``pool_assets/cimg_``
  文件，题面里的地址同步改写。两个目录互不相干——批次审完清残留切图清不到池里这份，
  池内删除也删不到批次那份（判据 4.2／4.7）；
- **整页底图不进池子**：比的是渲染，底图切完就没用（判据 4.3）；
- **一条一题**：一条进来题只占一条（``item_id`` 唯一），配一条最像的主库原题，
  不分组、不折叠（判据 4.1）；
- 四个动作只有 ``merge_metadata`` / ``add_solution`` / ``keep_separate`` / ``delete``，
  【覆盖】与【放弃】都按退役处理，别在这里长出第五个。

裁决完这条就从池里退场，退场时在 ``pool_actions`` 留一行——那一行既是**最小审计**
（时间、动作、来源批次、主库题 id），也是**已裁决标记**：拖档重扫再命中同一条，
:func:`admit_from_scan` 照它挡住复活（判据 4.9 与第五步的 5.3 在数据层的这一半）。

终局闸门不在这里：`pending_bank.approve` 里的精确判重一个字不动，
``keep_separate`` 走的是**本模块的显式动作**，不是「把闸门拆了」。
"""

from __future__ import annotations

import copy
from typing import Any

from app.core import bank, bank_dedupe, pending_assets, pending_batches, wire
from app.core import pending_dedupe, questions
from app.core.pending_db import (
    PENDING_ASSET_URI_PREFIX,
    POOL_ID_RE,
    PendingConflict,
    PendingError,
    PendingNotFound,
    connect,
    new_pool_action_id,
    new_pool_id,
)
from app.core.pending_meta import contract_probe
from app.core.pool_meta import (
    FIELD_LABELS as META_FIELD_LABELS,
    REQUIRED_UNIQUE_FIELDS,
    SOURCE_TITLE_FIELD,
    TYPE_LABELS,
    meta_diff as _meta_diff,
    meta_value as _unique_values,
    resolutions as _resolutions,
)
# 源码回写拆在独立舱位（单文件 800 行红线），对外仍从 pending_pool 取。
from app.core.pool_source import update_document  # noqa: F401

ACTIONS = ("merge_metadata", "add_solution", "keep_separate", "delete")

# 答案明确不同时锁死的那两个动作（判据 4.8）；另两个照走，不拦。
ANSWER_GATED = ("merge_metadata", "add_solution")


class PoolActionRefused(PendingError):
    """动作被规则锁死（当前只有「答案明确不同」），带机读码给前端上锁用。"""

    def __init__(self, message: str, *, code: str, action: str, **detail: Any) -> None:
        super().__init__(message)
        self.code = code
        self.action = action
        self.detail = detail


# ---------------------------------------------------------------- 读


def _label(level: str) -> str:
    return pending_dedupe.LEVEL_LABELS_TEXT.get(str(level or ""), "")


def _row_view(row: Any) -> dict[str, Any]:
    """列表视图：一条一题，带档位标签与可解释数字，不带两侧文档（详情接口才给）。"""
    level = str(row["level"] or "")
    return {
        "pool_id": str(row["pool_id"]),
        "item_id": str(row["item_id"]),
        "batch_id": str(row["batch_id"] or ""),
        "source_name": str(row["source_name"] or ""),
        "provider_id": str(row["provider_id"] or ""),
        "main_id": str(row["main_id"] or ""),
        "level": level,
        "label": _label(level),
        "percent": int(row["percent"] or 0),
        "similarity": float(row["similarity"] or 0.0),
        "signals": _json_list(row["signals_json"]),
        "asset_count": len(_json_list(row["assets_json"])),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _json_list(raw: Any) -> list[Any]:
    try:
        value = wire.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def _json_object(raw: Any) -> dict[str, Any]:
    try:
        value = wire.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _pool_row(pool_id: str) -> Any:
    if not POOL_ID_RE.match(str(pool_id or "")):
        raise PendingNotFound("重题池编号不合法")
    con = connect()
    try:
        row = con.execute("SELECT * FROM duplicate_pool WHERE pool_id = ?",
                          (str(pool_id),)).fetchone()
    finally:
        con.close()
    if row is None:
        raise PendingNotFound("重题池里没有这一条")
    return row


def list_pool(*, tier: Any = None) -> dict[str, Any]:
    """池子列表：默认按「像的程度」降序（判据 5.2 的排序口径由数据层给足）。

    ``tier`` 只是**读侧过滤**（按档位取候选，判据 4.3）：档位不落盘，
    每次请求现算，严档只看「确定＋很像」，宽档全给。
    """
    limit = bank_dedupe.normalize_tier(tier) if tier else None
    con = connect()
    try:
        rows = con.execute(
            "SELECT * FROM duplicate_pool ORDER BY percent DESC, item_id ASC"
        ).fetchall()
    finally:
        con.close()
    items = [_row_view(row) for row in rows]
    if limit is not None:
        items = [item for item in items if bank_dedupe.accepts(item["level"], limit)]
    return {"items": items, "total": len(items), "tier": limit or "",
            "default_tier": bank_dedupe.DEFAULT_TIER}


def get_entry(pool_id: str, *, tier: Any = None) -> dict[str, Any]:
    """一条详情：左右两侧**完整文档**（供纯渲染对比）＋置信度明细＋当前档位。"""
    row = _pool_row(pool_id)
    entry = _row_view(row)
    entry["incoming"] = _json_object(row["doc_json"])
    entry["assets"] = _json_list(row["assets_json"])
    existing: dict[str, Any] = {}
    main_id = entry["main_id"]
    if main_id:
        try:
            existing = bank.get_question(entry["provider_id"], main_id)
        except bank.BankError:
            # 主库那道刚被别处删掉：详情照发，只如实标没有可对比的原文。
            entry["existing_missing"] = True
    entry["existing"] = existing
    # 裁判台只看差异：多选属性给并集，唯一属性冲突点名并要求二选一（军令·查重三栏）。
    entry["meta_diff"] = _meta_diff(existing, entry["incoming"])
    answer_state = pending_dedupe.answer_mismatch(existing.get("answer"),
                                                 entry["incoming"].get("answer"))
    entry["answer"] = {
        "same": None if answer_state is None else not answer_state,
        "mismatch": answer_state is True,
        "main": pending_dedupe.answer_key(existing.get("answer")),
        "incoming": pending_dedupe.answer_key(entry["incoming"].get("answer")),
    }
    # 锁前两项这件事只有一条出处：答案明确不同就是锁，不给界面自己判。
    entry["locked_actions"] = [action for action in ANSWER_GATED if answer_state is True]
    entry["tier"] = bank_dedupe.normalize_tier(tier) if tier else bank_dedupe.DEFAULT_TIER
    # 本函数顶上那句「＋置信度明细」得有实物。档位／标签／百分比／信号全部回读池行里
    # 存的那一份——尺子只有 ``bank_dedupe.confidence`` 一把（判据 2.6），这里不重算、
    # 不另立第二把；界面拿 ``confidence`` 一个键就能把「像在哪、不像在哪」说明白。
    entry["confidence"] = {
        "level": entry["level"],
        "label": entry["label"],
        "percent": entry["percent"],
        "similarity": entry["similarity"],
        "signals": entry["signals"],
        "tier": entry["tier"],
        "accepted": bool(entry["level"]) and bank_dedupe.accepts(entry["level"],
                                                                 entry["tier"]),
    }
    return entry


# ---------------------------------------------------------------- 进池（一条一题）


def _adjudicated_item_ids(con: Any) -> set[str]:
    """已裁决的进来题号：``pool_actions`` 里有过任何动作就永久占坑，不许复活。"""
    return {str(row["item_id"]) for row in con.execute(
        "SELECT DISTINCT item_id FROM pool_actions WHERE item_id <> ''")}


def _source_name(con: Any, batch_id: str) -> str:
    row = con.execute("SELECT source_name FROM batches WHERE batch_id = ?",
                      (batch_id,)).fetchone()
    return str(row["source_name"] or "") if row is not None else ""


_PENDING_COLUMNS = ("id, batch_id, doc_json, assets_json, origin,"
                   " created_at, updated_at, seq")


def _copy_row_assets(assets: list[Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """把这一条的成品图逐份复制进 ``pool_assets/``，返回（池内资产清单，旧 uri → 新 uri）。

    任一份图文件不在就抛：调用方按「这一条整条不搬」处理——池里宁可没有这条，
    也不能有一条点开是死链的题（判据 3.6 的「图文件缺失」一路）。
    """
    copied: list[dict[str, Any]] = []
    mapping: dict[str, str] = {}
    for asset in assets:
        if not isinstance(asset, dict) or not str(asset.get("name") or ""):
            continue
        old_name = str(asset["name"])
        entry = pending_assets.copy_pending_asset_to_pool(asset)
        copied.append(entry)
        mapping[PENDING_ASSET_URI_PREFIX + old_name] = str(entry["uri"])
    return copied, mapping


def _swap_doc_uris(document_text: str, mapping: dict[str, str]) -> str:
    """把已序列化的题目文档里的池内图地址换成重题池的那一份。

    整串替换而不是只改 ``images`` 数组：解析正文里也可能内嵌同一张图的地址，
    只改数组会漏掉正文那一处。文件名是底座生成的 16 位随机十六进制，
    在别处撞上的概率当作零。
    """
    text = document_text
    for old_uri, new_uri in mapping.items():
        text = text.replace(old_uri, new_uri)
    return text


def admit_from_scan(batch_id: str, *, provider_id: Any = None, tier: Any = None,
                    state: dict[str, Any] | None = None) -> dict[str, Any]:
    """**抽走**：一条事务里把初查命中的题从待审池搬进重题池（判据 3.5／3.6／4.1／4.2）。

    只搬 ``reason="bank"`` 且带主库原题的那些——批内互重走「一键剔除」那条既有通道，
    不进重题池；重题池的每条都必须配一道主库原题。

    一行的搬法是「复制成品图 → 写池行（含完整文档与池内图引用）→ 删待审行」，
    三步同生共死：

    - **写库报错**（任何一条 INSERT/DELETE 失败）→ 整批事务回滚，池里一条不多、
      待审一条不少，连这次复制出去的池内图片也一并删干净，磁盘不留孤儿；
    - **图文件缺失** → 只有这一条整条不搬（它既没进池也没被删），其余照常抽走，
      缺图的那些记在 ``missing_asset_item_ids`` 里如实报数；
    - 绝不会留下「池里有了、批次里还留着」，也不会留下反过来的一半。

    另三件事照旧定死：一条一题（``item_id`` 唯一）、已裁决不复活（审计表挡）、
    本函数不判重（尺子只在 ``pending_dedupe`` 那一把）。批次未审数在同一事务里
    ``refresh_batch`` 重算，抽完账就对得上（判据 5.4）。**初查结论 ``done`` 也在
    同一条事务里落库**（S6 缺陷 2）：读的人一旦看见 ``done``，池表、待审行与批次
    账目必然已经是抽完的样子，回投里 ``scan_persisted`` 如实报这件事做没做。

    ``state`` 是后台链刚算好、**还没对外发布**的那一份初查结论（军令 #32 · S6：
    抽走必须排在 ``done`` 可读之前，所以这里不能回头去读 ``scan_state``）。
    不传就照旧读已落盘／已缓存的结论——同步入口 ``POST /api/pending/pool/collect``
    与测试都走这一条。
    """
    state = pending_dedupe.scan_state(batch_id) if state is None else dict(state)
    if str(state.get("status") or "") != "done":
        return {
            "batch_id": str(batch_id),
            "admitted": 0,
            "evicted": 0,
            "skipped_adjudicated": 0,
            "status": str(state.get("status") or "pending"),
            "code": str(state.get("code") or ""),
            "message": str(state.get("message") or "本批还没有可用的初查结论"),
            "pool_id": "",
        }
    limit = bank_dedupe.normalize_tier(tier if tier else state.get("tier"))
    resolved_provider = str(provider_id or state.get("provider_id") or "")
    candidates = [
        item for item in (state.get("candidates") or [])
        if str(item.get("reason") or "") == "bank"
        and str(item.get("existing_id") or "")
        and bank_dedupe.accepts(str(item.get("level") or ""), limit)
    ]
    con = connect()
    admitted: list[str] = []
    skipped_adjudicated = 0
    skipped: dict[str, list[str]] = {"missing_pending": [], "missing_asset": [],
                                     "already_in_pool": []}
    created_assets: list[dict[str, Any]] = []
    touched_batches: set[str] = set()
    try:
        con.execute("BEGIN IMMEDIATE")
        adjudicated = _adjudicated_item_ids(con)
        now = questions.now_iso()
        for candidate in candidates:
            item_id = str(candidate.get("item_id") or "")
            if not item_id or item_id in adjudicated:
                skipped_adjudicated += 1
                continue
            row = con.execute(
                f"SELECT {_PENDING_COLUMNS} FROM pending_questions WHERE id = ?",
                (item_id,),
            ).fetchone()
            if row is None:
                skipped["missing_pending"].append(item_id)
                continue
            if con.execute("SELECT 1 FROM duplicate_pool WHERE item_id = ?",
                           (item_id,)).fetchone() is not None:
                skipped["already_in_pool"].append(item_id)
                continue
            item_batch = str(row["batch_id"] or batch_id)
            try:
                pool_assets, mapping = _copy_row_assets(_json_list(row["assets_json"]))
            except PendingError:
                # 这一条的图没了：整条不搬——它一行 SQL 都没执行，不需要回滚。
                skipped["missing_asset"].append(item_id)
                continue
            created_assets.extend(pool_assets)
            doc_text = _swap_doc_uris(
                wire.dumps(_json_object(row["doc_json"]), ensure_ascii=False), mapping)
            con.execute(
                "INSERT OR IGNORE INTO duplicate_pool (pool_id, item_id, batch_id,"
                " source_name, provider_id, main_id, level, percent, similarity,"
                " signals_json, doc_json, assets_json, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    new_pool_id(), item_id, item_batch, _source_name(con, item_batch),
                    resolved_provider, str(candidate.get("existing_id") or ""),
                    str(candidate.get("level") or ""), int(candidate.get("percent") or 0),
                    float(candidate.get("similarity") or 0.0),
                    wire.dumps(candidate.get("signals") or [], ensure_ascii=False),
                    doc_text,
                    wire.dumps(pool_assets, ensure_ascii=False),
                    now, now,
                ),
            )
            if not con.execute("SELECT changes()").fetchone()[0]:
                continue                      # 唯一索引挡住的那次不算搬走，也不许删待审行
            cursor = con.execute("DELETE FROM pending_questions WHERE id = ?", (item_id,))
            if cursor.rowcount != 1:
                raise PendingConflict(
                    f"抽走失败：{item_id} 已进重题池，但待审池里那条没能删掉，整批回滚。")
            touched_batches.add(item_batch)
            admitted.append(item_id)
        for moved_batch in sorted(touched_batches):
            pending_batches.refresh_batch(con, moved_batch)
        # 落 ``done`` 挤进同一条事务（军令 #32 · S6 缺陷 2 的收口）：池行、待审删除、
        # 批次账目、初查结论四件事一起提交，一起被外面读到。分成两步就必然存在
        # 「池里已经有题、卡片还说全在待审」或者反过来的一拍，靠轮询多等一刻遮不住。
        scan_persisted = bool(pending_dedupe.persist_scan_in_txn(con, batch_id, state))
        con.commit()
    except BaseException:
        con.rollback()
        pending_assets.drop_pool_assets(created_assets)
        raise
    finally:
        con.close()
    return {
        "batch_id": str(batch_id),
        "admitted": len(admitted),
        "admitted_item_ids": admitted,
        # 抽走＝进池与删待审同时成立，两个数是同一批条数，分开报是给界面把话说明白。
        "evicted": len(admitted),
        "evicted_item_ids": admitted,
        "scan_persisted": scan_persisted,
        "skipped_adjudicated": skipped_adjudicated,
        "skipped_missing_pending": skipped["missing_pending"],
        "skipped_missing_asset": skipped["missing_asset"],
        "already_in_pool": skipped["already_in_pool"],
        "batches": _batch_cards(touched_batches),
        "status": "done",
        "tier": limit,
        "total": len(list_pool()["items"]),
    }


def _batch_cards(batch_ids: set[str]) -> list[dict[str, Any]]:
    """抽完之后把动过的批次卡片读回来（另起只读连接，事务已经提交了）。

    G6：卡片在**这条连接的同一条读事务**里就构造完——以前只把 ``(row, live)`` 递出去，
    由调用方另开连接数池内条数、回读初查结论，两次读之间正好能跨过下一次抽走的提交，
    读出「待审 2 ＋ 池内 2，总数才 2」那种混代帧（G5 同一条根）。
    """
    if not batch_ids:
        return []
    con = connect()
    try:
        con.execute("BEGIN")  # 只读事务：本连接一行都不写
        try:
            pooled = pending_dedupe.pooled_counts(con)
            cards: list[dict[str, Any]] = []
            for text in sorted(batch_ids):
                row = pending_batches.batch_row(con, text)
                if row is None:
                    continue
                live = int(con.execute(
                    "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (text,)
                ).fetchone()[0])
                cards.append(pending_batches.batch_card(row, live,
                                                        pooled=pooled.get(text, 0), con=con))
            return cards
        finally:
            con.rollback()
    finally:
        con.close()


# ---------------------------------------------------------------- 公共小件


def _answer_gate(row: Any, main: dict[str, Any], action: str) -> None:
    """答案明确不同 → 合并元数据与新增解析一起锁死（判据 4.8）。"""
    incoming = _json_object(row["doc_json"])
    if pending_dedupe.answer_mismatch(main.get("answer"), incoming.get("answer")) is not True:
        return
    raise PoolActionRefused(
        "这一条与主库那道题的答案明确不同：合并会把两套互相矛盾的解法并到一道题上。"
        "请改走「不重复（分开存）」或删除。",
        code="answer_mismatch",
        action=action,
        main_answer=pending_dedupe.answer_key(main.get("answer")),
        incoming_answer=pending_dedupe.answer_key(incoming.get("answer")),
    )


def _source_entry(document: dict[str, Any]) -> dict[str, Any] | None:
    """池内这条的来源卷（只留契约认识的字段），没有原卷标题就当没有来源。"""
    raw = document.get("source")
    if not isinstance(raw, dict) or not str(raw.get(SOURCE_TITLE_FIELD) or "").strip():
        return None
    allowed = set(bank.SOURCE_FIELDS)
    entry = {key: value for key, value in raw.items() if key in allowed}
    return entry or None


def _extra_sources(provider_id: str, main: dict[str, Any],
                   extra: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    """主库已挂的原卷整组读回来，加上池里这一条，按「同卷同题号只记一次」去重。

    ``bank.update_question(sources=...)`` 是**整组重挂**，所以这里必须把已有的
    一起递回去——只递新的会把老挂载删掉，那是覆盖来源，不是追加。
    """
    primary = main.get("source") if isinstance(main.get("source"), dict) else {}
    primary_key = (str(primary.get(SOURCE_TITLE_FIELD) or ""),
                   str(primary.get("question_no") or ""))
    allowed = set(bank.SOURCE_FIELDS)
    try:
        mounted = bank.question_sources(provider_id, str(main.get("id") or ""))["items"]
    except bank.BankError:
        mounted = []
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in mounted:
        entry = {key: value for key, value in item.items() if key in allowed}
        key = (str(entry.get(SOURCE_TITLE_FIELD) or ""), str(entry.get("question_no") or ""))
        if key == primary_key or key in seen:
            continue
        seen.add(key)
        merged.append(entry)
    if extra is not None:
        key = (str(extra.get(SOURCE_TITLE_FIELD) or ""), str(extra.get("question_no") or ""))
        if key != primary_key and key not in seen:
            merged.append(extra)
    return merged or None


# ---------------------------------------------------------------- 四个动作


def merge_metadata(pool_id: str, *, resolutions: Any = None) -> dict[str, Any]:
    """只并元数据：来源追加、标签并集、考向并集（主考向仍用主库原题的）。

    题干、选项、答案、解析、配图**一个字不动**（判据 4.4）。唯一属性（题型 / 难度）
    两侧都有且不同时，必须由老师用 ``resolutions``（``main`` / ``incoming``）二选一；
    没选就拒绝合并——界面锁按钮只是提示，真正的闸门在这里。
    """
    row = _pool_row(pool_id)
    main = _require_main(row)
    _answer_gate(row, main, "merge_metadata")
    incoming = _json_object(row["doc_json"])
    diff = _meta_diff(main, incoming)
    chosen = _resolutions(resolutions)
    missing = [field for field in diff["requires_resolution"] if field not in chosen]
    if missing:
        raise PoolActionRefused(
            "题型或难度两边不同，必须先决定保留哪一边再合并。",
            code="meta_conflict",
            action="merge_metadata",
            conflicts=[item for item in diff["conflicts"] if item["field"] in missing],
            requires_resolution=diff["requires_resolution"],
        )

    patch: dict[str, Any] = {}
    changed: dict[str, Any] = {}
    conflicts: list[dict[str, Any]] = []

    main_tags = [t for t in (main.get("tags") or []) if isinstance(t, str)]
    tags = list(dict.fromkeys([*main_tags, *[t for t in (incoming.get("tags") or [])
                                                 if isinstance(t, str)]]))
    if tags != main_tags:
        patch["tags"] = tags
        changed["tags"] = tags

    main_tax = dict(main.get("taxonomy") or {})
    main_ids = [t for t in (main_tax.get("topic_ids") or []) if isinstance(t, str)]
    incoming_ids = [t for t in ((incoming.get("taxonomy") or {}).get("topic_ids") or [])
                    if isinstance(t, str)]
    merged_ids = list(dict.fromkeys([*main_ids, *incoming_ids]))
    if merged_ids != main_ids:
        # 层名一律留主库原题的：主考向不许被池里这条顶掉。
        main_tax["topic_ids"] = merged_ids
        patch["taxonomy"] = main_tax
        changed["taxonomy"] = main_tax

    for field in REQUIRED_UNIQUE_FIELDS:
        main_value = _unique_values(main, field)
        incoming_value = _unique_values(incoming, field)
        if main_value == incoming_value:
            continue
        if chosen.get(field) == "incoming":
            patch[field] = incoming_value
            changed[field] = incoming_value
        elif not main_value and incoming_value:
            patch[field] = incoming_value
            changed[field] = incoming_value
        # 选 main（或两边都有冲突已裁决保留主库）就一个字不改。
    # 年级不在唯一属性二选一里：冲突只报不改，沿用旧口径。
    main_grade = str(main.get("grade") or "").strip()
    incoming_grade = str(incoming.get("grade") or "").strip()
    if main_grade and incoming_grade and main_grade != incoming_grade:
        conflicts.append({"field": "grade", "main": main_grade, "incoming": incoming_grade})
    elif not main_grade and incoming_grade:
        patch["grade"] = incoming_grade
        changed["grade"] = incoming_grade

    extra = _source_entry(incoming)
    sources = _extra_sources(row["provider_id"], main, extra)
    merged_source = extra is not None and sources is not None
    if merged_source:
        changed["source_appended"] = extra

    if patch or sources is not None:
        bank.update_question(str(row["provider_id"]), str(row["main_id"]),
                             patch or {}, sources=sources)
    return _finish(row, "merge_metadata", {
        "main_id": str(row["main_id"]),
        "changed": changed,
        "conflicts": conflicts,
        "question": bank.get_question(str(row["provider_id"]), str(row["main_id"])),
        "message": "已并入元数据，题面与答案未动。" if changed else "没有可并的元数据。",
    })


def add_solution(pool_id: str) -> dict[str, Any]:
    """把池里这条的解析接成主库那道题的下一个解法，并追加来源（判据 4.5）。

    写法复用底座查重引擎的 :func:`bank_dedupe.append_solution`——「解法二」那段
    措辞全仓只有一处，``pending_bank._merge_solution`` 用的也是它。
    """
    row = _pool_row(pool_id)
    main = _require_main(row)
    _answer_gate(row, main, "add_solution")
    incoming = _json_object(row["doc_json"])
    body = str(incoming.get("solution") or "").strip()
    if not body:
        raise PendingError("这一条没有解析，没有能并成新解法的内容")

    base = str(main.get("solution") or "")
    ordinal = base.count("**解法") + 1
    # 解析正文里引用的图是池内那一份（``pool_assets/``）：给主库**复制**成 uploads
    # 里的长期件再改 URI，池里那份等这条裁决退场时由 ``_finish`` 收掉。
    mapping = pending_assets.copy_pool_assets_to_uploads(_json_list(row["assets_json"]))
    merged = bank_dedupe.append_solution(
        base, pending_assets.rewrite_uri_text(body, mapping), ordinal)
    extra = _source_entry(incoming)
    sources = _extra_sources(row["provider_id"], main, extra)
    try:
        question = bank.update_question(str(row["provider_id"]), str(row["main_id"]),
                                        {"solution": merged}, sources=sources)
    except BaseException:
        pending_assets.remove_uploaded_copies(mapping)
        raise
    return _finish(row, "add_solution", {
        "main_id": str(row["main_id"]),
        "solution_ordinal": ordinal,
        "source_appended": extra if sources is not None and extra else None,
        "question": question,
        "message": f"已并为主库那道题的{bank_dedupe.solution_label(ordinal)}。",
    })


def keep_separate(pool_id: str) -> dict[str, Any]:
    """当一道独立新题写进主库：主库原题不动，闸门照走**显式动作**（判据 4.6/5.5）。

    校验与审核画布入库同一套：答案、占位符、考向三项先点名，再整体过契约
    （``questions.validate_question(contract_probe(...))``，与 ``pending_bank`` 暂存时
    同一句）。**不过就不写库**，条目留在池里，把缺项原样回给老师。
    """
    row = _pool_row(pool_id)
    document = copy.deepcopy(_json_object(row["doc_json"]))
    document.pop("id", None)
    missing = _missing_required(document)
    if missing:
        return {
            "ok": False,
            "action": "keep_separate",
            "pool_id": str(row["pool_id"]),
            "item_id": str(row["item_id"]),
            "main_id": str(row["main_id"] or ""),
            "written": False,
            "kept_in_pool": True,
            "missing": missing,
            "message": "这一条缺项，未写入主库：" + "、".join(missing) + "。请补齐后再裁决。",
        }

    assets = _json_list(row["assets_json"])
    mapping = pending_assets.copy_pool_assets_to_uploads(assets)
    pending_assets.rewrite_asset_uris(document, mapping)
    try:
        questions.validate_question(contract_probe(document))
        question = bank.create_question(str(row["provider_id"]), document)
    except questions.QuestionValidationError as error:
        pending_assets.remove_uploaded_copies(mapping)
        return {
            "ok": False,
            "action": "keep_separate",
            "pool_id": str(row["pool_id"]),
            "item_id": str(row["item_id"]),
            "main_id": str(row["main_id"] or ""),
            "written": False,
            "kept_in_pool": True,
            "missing": [str(text) for text in (error.errors or [])],
            "message": "这一条不符合契约，未写入主库，仍留在池里。",
        }
    except BaseException:
        pending_assets.remove_uploaded_copies(mapping)
        raise
    return _finish(row, "keep_separate", {
        "main_id": str(row["main_id"] or ""),
        "created_id": str(question.get("id") or ""),
        "question": question,
        "message": "已作为独立新题存入主库，主库原题未动。",
    })


def delete_entry(pool_id: str) -> dict[str, Any]:
    """只删池内这条与它在 ``pool_assets/`` 里的成品图；主库与批次一个字节都不动（判据 4.7）。"""
    row = _pool_row(pool_id)
    result = _finish(row, "delete", {
        "main_id": str(row["main_id"] or ""),
        "message": "已从池里删除，主库原题未动。",
    })
    return result


_ACTS = {
    "merge_metadata": merge_metadata,
    "add_solution": add_solution,
    "keep_separate": keep_separate,
    "delete": delete_entry,
}


def act(pool_id: str, action: Any, *, resolutions: Any = None) -> dict[str, Any]:
    """四个动作的唯一入口：动作名不认就是不认，不做「猜一个最像的」。

    ``resolutions`` 只服务合并元数据时的题型/难度二选一，其余动作传了也不认。
    """
    choice = str(action or "").strip()
    if choice not in _ACTS:
        raise PendingError(f"不认识的池内动作：{action}（只收 {'、'.join(ACTIONS)}）")
    if choice == "merge_metadata":
        return merge_metadata(pool_id, resolutions=resolutions)
    return _ACTS[choice](pool_id)


# ---------------------------------------------------------------- 收尾与内部件


def _require_main(row: Any) -> dict[str, Any]:
    main_id = str(row["main_id"] or "")
    if not main_id:
        raise PendingError("这一条没有配主库原题，不能并进主库")
    return bank.get_question(str(row["provider_id"]), main_id)


def _missing_required(document: dict[str, Any]) -> list[str]:
    """入库三项先点名（答案、占位符、考向），剩下的交给契约整体校验。"""
    missing: list[str] = []
    answer = document.get("answer")
    if answer is None or (isinstance(answer, str) and not answer.strip()):
        missing.append("答案")
    if _placeholder_hits(document):
        missing.append("占位符未清")
    taxonomy = document.get("taxonomy")
    if not isinstance(taxonomy, dict) or not (taxonomy.get("topic_ids") or []):
        missing.append("考向")
    return missing


_PLACEHOLDER_MARKS = ("（待识别", "(待识别", "待补", "【待", "___")


def _placeholder_hits(document: dict[str, Any]) -> list[str]:
    """题面里还留着识别占位文就是没审完——这三处都是正文，藏不住。"""
    haystack = [str(document.get("stem") or ""), str(document.get("solution") or "")]
    for option in (document.get("options") or []):
        body = option.get("content") if isinstance(option, dict) else option
        haystack.append(str(body or ""))
    return [mark for mark in _PLACEHOLDER_MARKS if any(mark in text for text in haystack)]


def _drop_unreferenced_assets(row: Any) -> int:
    """裁决退场时收掉这条在 ``pool_assets/`` 里的成品图（判据 4.7 的最终形态）。

    S4 留的那条过渡规则是「回查 ``pending_questions`` 谁还引用这个名字」——那时池与
    待审还共图，不查就会误删批次还在用的图。抽走之后图跟题走：池内这条的图是它
    自己的 ``cimg_`` 文件，跟 ``pending_assets/`` 里的 ``pimg_`` 不重名、不同目录，
    物理上删不到批次那一份，回查这一趟可以撤掉。

    四个动作退场都要收：并元数据不动图（池内那份从此没人引）、并解法与分开存的
    图已经复制进 ``uploads/``（主库读那份）、删除本就冲着它来。失败没退场的路径
    （缺项、被锁、校验不过）不会走到这里，图原样留着等老师补齐再裁。
    """
    return pending_assets.drop_pool_assets(_json_list(row["assets_json"]))


def _finish(row: Any, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    """一条事务里做两件事：写裁决记录（审计＋防复活）与让条目退场（判据 4.9）。

    事务提交成功之后才收池内的成品图：收图是清理，不能反过来把裁决本身搭进去。
    """
    record = {key: value for key, value in payload.items() if key != "question"}
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT INTO pool_actions (action_id, pool_id, item_id, batch_id, main_id,"
            " action, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_pool_action_id(), str(row["pool_id"]), str(row["item_id"]),
                str(row["batch_id"] or ""), str(row["main_id"] or ""), action,
                wire.dumps(record, ensure_ascii=False), questions.now_iso(),
            ),
        )
        cursor = con.execute("DELETE FROM duplicate_pool WHERE pool_id = ?",
                             (str(row["pool_id"]),))
        if cursor.rowcount == 0:
            raise PendingConflict("这一条已经被处理过了")
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return {
        "ok": True,
        "action": action,
        "pool_id": str(row["pool_id"]),
        "item_id": str(row["item_id"]),
        "batch_id": str(row["batch_id"] or ""),
        "main_id": str(row["main_id"] or ""),
        "written": action in ("merge_metadata", "add_solution", "keep_separate"),
        "removed_from_pool": True,
        "deleted_assets": _drop_unreferenced_assets(row),
        **payload,
    }
