"""中转站的公共元数据规则：标准名拼接、场景与学校 ID、以及向题目文档的同步。

四条口径（主公 2026-11-01 裁定）：
- **学校只存 ID**：题目文档里写 ``school_id`` / ``school_ids``，校名一个字节都不进；
- **标准名是算出来的**：``年份-地区-主体-场景-类型-学科``，空段不占位；老师手改后
  暂停拼接，任何一项元数据再改，自动拼接立刻恢复；
- **场景交叉标签带权重**：外国题优先 AMC / A-Level / IB，校考题优先 9月月考 / 一模；
- **同步不硬塞**：同步不上的题一条也不动，如实报出原因，绝不为了「同步成功」改坏
  老师已经录好的题。

契约校验用的「影子文档」构造（``contract_probe``）也在这里：暂存文档与契约只有两处
刻意不同（``p_`` 号段、``pending_assets/`` 图路），影子只换回这两处，
于是「池子里不合规」与「入库时不合规」是同一把尺子量出来的。
"""

from __future__ import annotations

import copy
import re
import secrets
import sqlite3
from typing import Any

from app.core import bank, questions, wire
from app.core.exam_name import compose_exam_name
from app.core.pending_db import (
    GROUP_ITEM_SEP,
    GROUP_SEP,
    HIDDEN_TAG_PREFIX,
    META_NAME_LIMIT,
    META_SCHOOL_LIMIT,
    PendingError,
    UPLOAD_ASSET_URI_PREFIX,
    connect,
)
from app.core.pending_batches import (
    batch_row,
    read_approved,
)

def contract_probe(document: dict[str, Any]) -> dict[str, Any]:
    """把暂存文档投影成「契约形状」的影子，用它跑真正的 Schema 校验。

    暂存文档有两处刻意与契约不同：id 走 ``p_`` 号段，配图 uri 指向
    ``pending_assets/``。影子只把这两处换回契约认可的形状，其余字段一字不改——
    这样「暂存时不合规」与「入库时不合规」是同一把尺子量出来的，
    不会出现「池子里躺着、审核时才发现是废题」。
    """
    probe = copy.deepcopy(document)
    probe["id"] = "q_" + secrets.token_hex(12)
    probe["schema_version"] = "2.1"
    images = probe.get("images")
    if isinstance(images, list):
        for image in images:
            if isinstance(image, dict):
                image["uri"] = UPLOAD_ASSET_URI_PREFIX + "_probe.png"
    return probe
def clean_text(value: Any, limit: int) -> str:
    """去首尾空白、压掉中间空白；超长截断。"""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def build_standard_name(meta: dict[str, Any]) -> str:
    """标准名：按考试类型规则动态拼装，空段不占位。

    月考带月份、模拟考带轮次、期中/期末带学期，其余类型只到类型名；
    只有老师手动改过标准名且元数据没再动时，才保留手改值
    （见 ``normalize_batch_meta``）。
    """
    exam_type = str(meta.get("exam_type") or meta.get("scene_type") or "")
    return compose_exam_name(
        year=meta.get("year"),
        exam_type=exam_type,
        exam_org_name=str(meta.get("body") or ""),
        grade_name=str(meta.get("grade") or ""),
        month=meta.get("month"),
        mock_round=meta.get("mock_round"),
        semester=meta.get("semester"),
        subject_name=str(meta.get("subject") or ""),
    )[:META_NAME_LIMIT]


def _school_ids_from_payload(payload: dict[str, Any]) -> list[str]:
    """明细学校一律落字典 ID；老客户端送校名时按名字找档（找不到就建档）。"""
    from app.core import meta_dict

    ids: list[str] = []
    raw_ids = payload.get("school_ids")
    if isinstance(raw_ids, list):
        for item in raw_ids:
            school_id = clean_text(item, 40)
            if school_id and school_id not in ids:
                ids.append(school_id)
    if not ids:
        raw_names = payload.get("schools")
        if isinstance(raw_names, list):
            for item in raw_names:
                name = clean_text(item, 120)
                if not name:
                    continue
                try:
                    record = meta_dict.find_or_create_by_name(name)
                except meta_dict.MetaDictError as exc:
                    raise PendingError(str(exc)) from exc
                if record["id"] not in ids:
                    ids.append(record["id"])
    if len(ids) > META_SCHOOL_LIMIT:
        raise PendingError(f"明细学校最多 {META_SCHOOL_LIMIT} 所")
    if ids:
        try:
            meta_dict.get_schools(ids)
        except meta_dict.MetaDictError as exc:
            raise PendingError(str(exc)) from exc
    return ids


def _meta_fingerprint(meta: dict[str, Any]) -> tuple[Any, ...]:
    """判断「元数据有没有被改过」的比对键：标准名与手动模式不算元数据。"""
    return (
        meta.get("year"), meta.get("region"), meta.get("grade"), meta.get("body"),
        meta.get("exam_type"), meta.get("subject"), meta.get("scene_type"),
        meta.get("month"), meta.get("mock_round"), meta.get("semester"),
        tuple(meta.get("school_ids") or []),
    )


def normalize_batch_meta(payload: Any, previous: Any = None) -> dict[str, Any]:
    """把老师填的公共字段规整成底座口径。

    - 明细学校只收字典 ID；老客户端送校名时先建档再换成 ID。
    - 场景只收 11 个主场景之一。
    - 标准名默认由底座重算；``name_mode=manual`` 且元数据没再变时保留手改值，
      之后任何一项元数据再改，自动拼接立刻恢复（主公 2026-11-01 双向联动）。
    """
    from app.core import meta_dict

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise PendingError("公共元数据必须是对象")

    # PATCH 语义：没带来的字段沿用上一版；带来的空串才是「真的清空」。
    # 双向联动全靠这一步——老师只改标准名时，其余元数据原样不动，
    # 指纹才不会误判成「元数据改了」，手改名也才留得住。
    prior = previous if isinstance(previous, dict) else None
    merged = dict(prior) if prior else {}
    if "school_ids" in payload or "schools" in payload:
        merged.pop("school_ids", None)
        merged.pop("schools", None)
    merged.update(payload)

    year: int | None = None
    raw_year = str(merged.get("year") or "").strip()
    if raw_year:
        if not raw_year.isdigit():
            raise PendingError("年份只能填数字")
        year = int(raw_year)
        if not 1900 <= year <= 2100:
            raise PendingError("年份要在 1900–2100 之间")

    month: int | None = None
    raw_month = str(merged.get("month") or "").strip()
    if raw_month:
        if not raw_month.isdigit():
            raise PendingError("月份只能填数字")
        month = int(raw_month)
        if not 1 <= month <= 12:
            raise PendingError("月份要在 1–12 之间")

    mock_round: int | None = None
    raw_round = str(merged.get("mock_round") or "").strip()
    if raw_round:
        if not raw_round.isdigit():
            raise PendingError("模考轮次只能填数字")
        mock_round = int(raw_round)
        if not 1 <= mock_round <= 10:
            raise PendingError("模考轮次要在 1–10 之间")

    semester = clean_text(merged.get("semester"), 8)
    if semester and semester not in ("上学期", "下学期"):
        raise PendingError("学期只能是上学期或下学期")

    try:
        scene_type = meta_dict.normalize_scene(merged.get("scene_type"))
    except meta_dict.MetaDictError as exc:
        raise PendingError(str(exc)) from exc

    meta = {
        "year": year,
        "region": clean_text(merged.get("region"), 64),
        # 年级是契约的根字段（maxLength 20，落库在 sources.grade），跟着批次走。
        "grade": clean_text(merged.get("grade"), 20),
        "body": clean_text(merged.get("body"), 64),
        "exam_type": clean_text(merged.get("exam_type"), 64),
        "month": month,
        "mock_round": mock_round,
        "semester": semester,
        "subject": clean_text(merged.get("subject"), 64),
        "scene_type": scene_type,
        "school_ids": _school_ids_from_payload(merged),
    }

    changed = prior is not None and _meta_fingerprint(prior) != _meta_fingerprint(meta)
    manual = str(payload.get("name_mode") or "").strip() == "manual"
    if manual and not changed:
        name = clean_text(payload.get("standard_name"), META_NAME_LIMIT)
        if not name and prior is not None:
            name = str(prior.get("standard_name") or "")
        meta["name_mode"] = "manual"
        meta["standard_name"] = name or build_standard_name(meta)
    else:
        meta["name_mode"] = "auto"
        meta["standard_name"] = build_standard_name(meta)
    return meta


def apply_meta_to_document(document: dict[str, Any], meta: dict[str, Any]) -> tuple[bool, str, list[str]]:
    """把公共元数据写进一道题的 ``source``、根字段 ``grade`` 与 ``tags``。

    学校只写 ``school_id`` / ``school_ids``，校名一个字节都不进题目文档；
    老版本留下的隐藏校名标签在这里一并清掉。

    返回 (是否写成功, 失败原因, 提示)。写不成的题**原样留着**并如实上报，
    绝不为了「同步成功」去改坏老师已经录好的题。
    """
    notes: list[str] = []
    source = document.get("source")
    updated = dict(source) if isinstance(source, dict) else {}
    updated.pop("school", None)
    if meta.get("year"):
        updated["year"] = int(meta["year"])
    if meta.get("region"):
        updated["region"] = str(meta["region"])
    for field in ("body", "scene_type", "exam_type"):
        value = str(meta.get(field) or "")
        if value:
            updated[field] = value
        else:
            updated.pop(field, None)
    org = str(meta.get("body") or "")
    if org:
        updated["exam_org_name"] = org
    else:
        updated.pop("exam_org_name", None)
    exam_type = str(meta.get("exam_type") or "")
    for field, relevant in (
        ("month", exam_type == "月考"),
        ("mock_round", exam_type in ("模考", "模拟考")),
        ("semester", exam_type in ("期中", "期末")),
    ):
        value = meta.get(field)
        if relevant and value not in (None, ""):
            updated[field] = value
        else:
            updated.pop(field, None)
    school_ids = [str(item) for item in (meta.get("school_ids") or []) if str(item)]
    if school_ids:
        updated["school_ids"] = school_ids
        updated["school_id"] = school_ids[0]
    else:
        updated.pop("school_ids", None)
        updated.pop("school_id", None)
    standard = str(meta.get("standard_name") or "")
    if standard:
        # 标准名就是这一批的原卷名：它落进 sources.paper_name，是这一批题在主库里的出处。
        updated["paper_title"] = standard
    grade = str(meta.get("grade") or "")
    if grade:
        # 年级是契约的**根字段**（不在 source 里），存储层再落进 sources.grade。
        # 批次没填年级时一个字都不动：不许把老师逐题手写过的年级抹平。
        document["grade"] = grade
    document["source"] = updated

    # 老版本的明细学校曾是「#哈三中」隐藏标签；2.1 起题目只存 school_id，
    # 这些遗留标签在同步时清掉，老师的可见标签原样保留。
    raw_tags = [tag for tag in (document.get("tags") or []) if isinstance(tag, str) and tag]
    document["tags"] = list(dict.fromkeys(
        tag for tag in raw_tags if not tag.startswith(HIDDEN_TAG_PREFIX)
    ))

    try:
        questions.validate_question(contract_probe(document))
    except questions.QuestionValidationError as exc:
        return False, f"同步后不合契约：{exc.errors[0] if exc.errors else '未知'}", notes
    return True, "", notes


def sync_batch_sources(con: sqlite3.Connection, batch_id: str,
                        meta: dict[str, Any]) -> tuple[int, int, list[str]]:
    """把公共元数据同步给这一批**池子里**的所有题。

    返回 (同步成功数, 跳过数, 提示)。跳过的题一条也不动。
    """
    rows = con.execute(
        "SELECT id, doc_json FROM pending_questions WHERE batch_id = ?"
        " ORDER BY seq ASC, id ASC",
        (batch_id,),
    ).fetchall()
    synced = 0
    skipped = 0
    warnings: list[str] = []
    for row in rows:
        try:
            document = wire.loads(row["doc_json"])
        except (TypeError, ValueError):
            skipped += 1
            warnings.append(f"{row['id']}：文档损坏，未同步")
            continue
        ok, reason, notes = apply_meta_to_document(document, meta)
        if not ok:
            skipped += 1
            warnings.append(f"{row['id']}：{reason}")
            continue
        con.execute(
            "UPDATE pending_questions SET doc_json = ?, updated_at = ? WHERE id = ?",
            (wire.dumps(document, ensure_ascii=False, separators=(",", ":")),
             questions.now_iso(), row["id"]),
        )
        synced += 1
        warnings.extend(f"{row['id']}：{note}" for note in notes)
    return synced, skipped, warnings


def sync_approved_sources(batch_id: str, meta: dict[str, Any]) -> tuple[int, list[str]]:
    """公共元数据后改时，补写这一批**已经进主库**的那些题。

    这一步是尽力而为：主库写不进去时如实报出来，绝不假装同步成功，
    也绝不因为主库暂时不可用就把池子里的同步一起回滚。
    """
    from app.core import bank_provider

    con = connect()
    try:
        row = batch_row(con, batch_id)
        if row is None:
            return 0, []
        approved = read_approved(row)
    finally:
        con.close()
    if not approved:
        return 0, []

    warnings: list[str] = []
    patched = 0
    try:
        plugin_id = bank_provider.resolve()["plugin_id"]
    except Exception as exc:  # noqa: BLE001 — 题库不可用不该打断池子里的同步
        return 0, [f"已入库的题没补写：题库不可用（{exc}）"]

    for item in approved:
        question_id = str(item.get("question_id") or "")
        if not question_id:
            continue
        try:
            current = bank.get_question(plugin_id, question_id)
        except Exception as exc:  # noqa: BLE001 — 单题失败不牵连别的题
            warnings.append(f"{question_id}：已入库的题没补写（{exc}）")
            continue
        document = dict(current)
        ok, reason, notes = apply_meta_to_document(document, meta)
        if not ok:
            warnings.append(f"{question_id}：{reason}")
            continue
        patch = {
            key: document[key]
            for key in ("source", "tags", "grade")
            if key in document
        }
        try:
            sync_dictionary_schools(plugin_id, document)
            bank.update_question(plugin_id, question_id, patch)
        except Exception as exc:  # noqa: BLE001 — 同上
            warnings.append(f"{question_id}：已入库的题没补写（{exc}）")
            continue
        patched += 1
        warnings.extend(f"{question_id}：{note}" for note in notes)
    return patched, warnings


def remember_meta(con: sqlite3.Connection, meta: dict[str, Any]) -> None:
    """记住这次用过的公共字段、明细学校与交叉标签：下次自动带出。"""
    now = questions.now_iso()
    pairs: list[tuple[str, str]] = [
        ("region", str(meta.get("region") or "")),
        ("body", str(meta.get("body") or "")),
        ("exam_type", str(meta.get("exam_type") or "")),
        ("subject", str(meta.get("subject") or "")),
        ("scene_type", str(meta.get("scene_type") or "")),
    ]
    school_ids = [str(item) for item in (meta.get("school_ids") or []) if str(item)]
    schools: list[str] = []
    if school_ids:
        placeholders = ",".join("?" for _ in school_ids)
        rows = con.execute(
            f"SELECT id, short_name FROM schools WHERE id IN ({placeholders})", school_ids
        ).fetchall()
        # 名单顺序照老师挑选的先后排：IN (...) 的返回次序由数据库自定，不能拿来当顺序。
        by_id = {str(row["id"]): str(row["short_name"]) for row in rows}
        schools = [by_id[school_id] for school_id in school_ids if school_id in by_id]
    pairs.extend(("school", name) for name in schools)
    # 交叉标签的权重记忆：老师每次选用/手打一个标签，就在这个场景里 +1。
    scene = str(meta.get("scene_type") or "")
    exam_type = str(meta.get("exam_type") or "").strip()[:32]
    if exam_type:
        con.execute(
            "INSERT INTO exam_types (name, scene, weight, updated_at) VALUES (?, ?, 1, ?)"
            " ON CONFLICT(name, scene) DO UPDATE SET"
            " weight = weight + 1, updated_at = excluded.updated_at",
            (exam_type, scene, now),
        )
    body = str(meta.get("body") or "").strip()
    if body and schools:
        # 主体 → 明细名单的对应关系：下次填同一主体时自动把名单带出来。
        # 同一个主体只留**最新**那一份名单：名单改了就把旧的抹掉，
        # 否则历史里会躺着几套同主体不同名单的记录，带出来的是哪套说不准。
        stale = [
            str(row["value"])
            for row in con.execute(
                "SELECT value FROM meta_history WHERE kind = 'group'"
            ).fetchall()
            if str(row["value"]).partition(GROUP_SEP)[0] == body
        ]
        for value in stale:
            con.execute(
                "DELETE FROM meta_history WHERE kind = 'group' AND value = ?", (value,)
            )
        pairs.append(("group", body + GROUP_SEP + GROUP_ITEM_SEP.join(schools)))
    for kind, value in pairs:
        text = value.strip()
        if not text:
            continue
        con.execute(
            "INSERT INTO meta_history (kind, value, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(kind, value) DO UPDATE SET updated_at = excluded.updated_at",
            (kind, text, now),
        )

def meta_history(limit: int = 12) -> dict[str, Any]:
    """公共字段的历史值：最近用过的排前面，供下次开批次时自动带出。"""
    count = max(1, min(int(limit or 12), 50))
    con = connect()
    try:
        rows = con.execute(
            "SELECT kind, value FROM meta_history ORDER BY updated_at DESC, value ASC"
        ).fetchall()
    finally:
        con.close()
    history: dict[str, list[str]] = {}
    groups: dict[str, list[str]] = {}
    for row in rows:
        kind = str(row["kind"] or "")
        value = str(row["value"] or "")
        if not kind or not value:
            continue
        if kind == "group":
            body, _, raw = value.partition(GROUP_SEP)
            names = [name for name in raw.split(GROUP_ITEM_SEP) if name]
            if body and names and body not in groups and len(groups) < count:
                groups[body] = names
            continue
        items = history.setdefault(kind, [])
        if value not in items and len(items) < count:
            items.append(value)
    return {"history": history, "groups": groups}
def sync_dictionary_schools(provider_id: str, document: dict[str, Any]) -> None:
    """入库前把题目用到的学校登记进题库，ID 原样沿用。

    题目里只有 ``school_id``；题库的 ``sources.school_id`` 要指向一张真实存在的
    ``schools`` 行，否则来源表挂空、按学校名搜也搜不到。字典是权威，题库是副本。
    """
    from app.core import meta_dict

    source = document.get("source")
    if not isinstance(source, dict):
        return
    ids = [str(item) for item in (source.get("school_ids") or []) if str(item)]
    primary = str(source.get("school_id") or "")
    if primary and primary not in ids:
        ids.insert(0, primary)
    if not ids:
        return
    schools = meta_dict.get_schools(ids, strict=False)
    for school in schools:
        bank.upsert_school(provider_id, school, str(source.get("region") or ""))
