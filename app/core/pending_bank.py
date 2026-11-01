"""中转站（待审核池）：录题端与主库之间的**批次制**物理隔离暂存。

老师录完的题不再直接砸进主库，而是先落进「中转站」，他看过、点头了才转成
正式题目入库。这一层存在的全部理由就是**隔离**，所以四件事必须各归各位：

1. **库文件独立**：``<工作区>/pending.db``，与主库 ``banks/<题库插件>.db``
   不是一个文件。中转站炸了，主库照常读写。
2. **配图独立**：``<工作区>/pending_assets/``。题目在池子里期间，配图不进
   ``uploads/``——被否决的题连一张图都不会留在主库的资源目录里。
3. **号段独立**：池子里的题目 id 一律 ``p_`` 前缀，绝不占用主库的 ``q_`` 号段。
   被否决的题连号都不占，将来入库的正式题号也就不会被它顶掉。
4. **批次独立**：一批来自同一份原卷的题挂在同一个 ``batch_id``（``B-001`` 起）
   下。批次表另记三样东西：录入时间、**原文件只读副本**的路径、批次总题数与
   未审数。未审数归零时，原文件副本与本批切图**物理删除**——磁盘不养废纸。

入库那一刻只做一件事：把暂存文档里的 ``p_`` 换成底座新签发的 ``q_``，把配图
从 ``pending_assets/`` 搬进 ``uploads/``，然后把这一条从 ``pending.db`` 里删掉。
**题库主权始终在底座**（AGENTS §3）：id 与时间戳由底座签发，插件给什么都不作数。

查重口径与 core-bank 的指纹引擎同源（``bank_dedupe``），但配图这一维按**内容
哈希**计：池子里的图叫 ``pimg_x.png``、主库里的图叫 ``img_x.png``，同一个文件
两个名字，按文件名比永远比不上，按内容哈希比才是真的同一张图。

四块实现在同目录（PLUGIN_SPEC §2.8 的单文件上限口径，Python 侧同理）：

- ``pending_db.py``       —— 库文件、号段、结构版本迁移与字典基线；
- ``pending_batches.py``  —— 批次与条目的读写（``batches`` / ``pending_questions``）；
- ``pending_assets.py``   —— 暂存配图与原文件只读副本的落盘、入库时的搬迁；
- ``pending_dedupe.py``   —— 与 core-bank 同源的查重口径（配图按内容哈希比）；
- ``pending_meta.py``     —— 公共元数据规则与向题目文档的同步。

本文件留「审核动作」这一层：暂存（save_draft）、改公共元数据（set_batch_meta）、
存入主库（approve）、彻底删除（delete_pending），以及批次收口时的物理清理。
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from app.core import bank, questions
from app.core.config import settings
from app.core.pending_assets import (
    asset_path,
    backup_path,
    backup_paths,
    decode_data_url,
    drop_assets,
    move_assets_to_uploads,
    rewrite_asset_uris,
    store_source_backup,
    write_pending_asset,
)
from app.core.pending_batches import (
    batch_card,
    batch_list,
    batch_row,
    get_pending,
    list_batch_questions,
    next_seq,
    read_meta,
    refresh_batch,
    remember_approved,
)
from app.core.pending_db import (
    BATCH_ID_RE,
    MAX_BATCH_QUESTIONS,
    PENDING_ASSET_URI_PREFIX,
    PENDING_ID_RE,
    PendingConflict,
    PendingDuplicate,
    PendingError,
    PendingNotFound,
    UPLOAD_ASSET_URI_PREFIX,
    batch_label,
    connect,
    local_now,
    new_pending_id,
    next_batch_id,
)
from app.core.pending_dedupe import find_duplicate
from app.core.pending_meta import (
    apply_meta_to_document,
    clean_text,
    contract_probe,
    meta_history,
    normalize_batch_meta,
    remember_meta,
    sync_approved_sources,
    sync_batch_sources,
    sync_dictionary_schools,
)

def _item_parts(item: Any) -> tuple[dict[str, Any], Any, str]:
    """把一条待暂存内容拆成「题目文档 + 配图清单 + 要更新的中转站号」。

    两种形状都收：``{"question": {...}, "assets": [...]}``（信封）与裸题目文档。
    信封里还可以带 ``pending_id``：带了就表示**就地更新**池子里那一条，而不是
    再塞一条新的进去——老师改完点【存为待办】，池子里不该多出一道重影。
    """
    if not isinstance(item, dict):
        raise PendingError("每一条待暂存内容都必须是对象")
    pending_id = str(item.get("pending_id") or "").strip()
    if pending_id and not PENDING_ID_RE.match(pending_id):
        raise PendingError("中转站编号不合法")
    if isinstance(item.get("question"), dict):
        return item["question"], item.get("assets"), pending_id
    return item, None, pending_id


def save_draft(items: Any, *, batch_id: Any = None, source_backup: Any = "",
               source_name: Any = "", origin: Any = "") -> dict[str, Any]:
    """把一道题或一批题存进中转站（**存为待办**）。

    - ``batch_id`` 给了就并进那一批；没给就新开一批（``B-001`` 起）。
    - ``source_backup`` 是原文件只读副本在工作区 ``data/`` 里的相对路径；
      批次未审数归零时底座会**物理删掉**它，磁盘不留废纸。
    - ``source_name`` 是原文件名（老师拖进来的那份），只作展示，不参与解析。
    - 返回批次卡片与新题 id，前端据此刷新列表。

    一条都不写是失败：宁可报错，也不让老师以为存进去了。
    """
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or not items:
        raise PendingError("没有要暂存的题目")
    if len(items) > MAX_BATCH_QUESTIONS:
        raise PendingError(f"一次最多暂存 {MAX_BATCH_QUESTIONS} 道题")
    backup_text = str(source_backup or "").strip()
    backup = backup_path(backup_text)
    name_text = clean_text(source_name, 120)

    prepared: list[tuple[dict[str, Any], list[dict[str, Any]], str]] = []
    for item in items:
        payload, assets, pending_id = _item_parts(item)
        document, stored = _prepare_document(payload, assets, pending_id or None)
        prepared.append((document, stored, pending_id))

    now = questions.now_iso()
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        target_batch = str(batch_id or "").strip()
        if target_batch:
            if not BATCH_ID_RE.match(target_batch):
                raise PendingError("批次编号不合法")
            if batch_row(con, target_batch) is None:
                raise PendingNotFound("中转站里没有这个批次")
        else:
            target_batch = next_batch_id(con)
            con.execute(
                "INSERT INTO batches"
                " (batch_id, label, created_at, updated_at, source_backup, source_name,"
                "  total, pending_count, assets_json)"
                " VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)",
                (target_batch, batch_label(local_now()), now, now, backup_text, name_text, "[]"),
            )
        current = batch_row(con, target_batch)
        # 公共元数据是这一批的「共同出处」：每次暂存都按批次上的那一份重写，
        # 插件只报自己看得见的字段也抹不掉场景、学校 ID 与标准名。
        batch_meta = read_meta(current) if current is not None else {}
        if batch_meta:
            for document, _stored, _pending_id in prepared:
                ok, reason, _notes = apply_meta_to_document(document, batch_meta)
                if not ok:
                    raise PendingError("这一批的公共元数据与题目对不上：" + reason)
        if backup_text and not str((current or {"source_backup": ""})["source_backup"] or ""):
            con.execute(
                "UPDATE batches SET source_backup = ? WHERE batch_id = ?",
                (backup_text, target_batch),
            )
        if name_text and not str((current or {"source_name": ""})["source_name"] or ""):
            con.execute(
                "UPDATE batches SET source_name = ? WHERE batch_id = ?",
                (name_text, target_batch),
            )
        names: list[str] = []
        inserted = 0
        seq = next_seq(con, target_batch)
        for document, stored, pending_id in prepared:
            if pending_id:
                # 就地更新：号、批次与未审数都不动，只换内容。次序号也不动——
                # 老师改的是这一道题，它在批次里的位置还是原来那个位置。
                names.extend(str(item.get("name") or "") for item in _replace_pending(
                    con, pending_id, document, stored))
                continue
            con.execute(
                "INSERT INTO pending_questions"
                " (id, batch_id, doc_json, assets_json, origin, created_at, updated_at, seq)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document["id"], target_batch,
                    json.dumps(document, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(stored, ensure_ascii=False, separators=(",", ":")),
                    str(origin or "")[:64], now, now, seq,
                ),
            )
            seq += 1
            inserted += 1
            names.extend(str(item.get("name") or "") for item in stored)
        row = batch_row(con, target_batch)
        merged = list(json.loads(row["assets_json"] or "[]"))
        merged.extend(name for name in names if name)
        con.execute(
            "UPDATE batches SET total = total + ?, assets_json = ?, updated_at = ?"
            " WHERE batch_id = ?",
            (inserted, json.dumps(merged, ensure_ascii=False, separators=(",", ":")),
             now, target_batch),
        )
        refresh_batch(con, target_batch)
        live = int(con.execute(
            "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (target_batch,)
        ).fetchone()[0])
        card = batch_card(batch_row(con, target_batch), live)
        con.commit()
    except BaseException:
        con.rollback()
        for _document, stored, _pending_id in prepared:
            drop_assets(stored)
        raise
    finally:
        con.close()
    return {
        "batch_id": target_batch,
        "batch": card,
        "saved_ids": [document["id"] for document, _stored, _pending_id in prepared],
        # 新落盘的配图清单：插件切完图要知道底座把字节写到哪个地址去了，
        # 题面里的 uri 得跟着换成真实的那一个，不然题里挂着一张取不到的图。
        "saved_assets": [
            {
                "pending_id": pending_id or document["id"],
                "assets": [
                    {
                        "id": str(asset.get("image_id") or ""),
                        "name": str(asset.get("name") or ""),
                        "uri": PENDING_ASSET_URI_PREFIX + str(asset.get("name") or ""),
                        "mime": str(asset.get("mime") or ""),
                        "bytes": int(asset.get("bytes") or 0),
                    }
                    for asset in stored
                ],
            }
            for document, stored, pending_id in prepared
        ],
    }


def _replace_pending(con: sqlite3.Connection, pending_id: str, document: dict[str, Any],
                     stored_assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """就地更新池子里那一条：号、批次与未审数都不动，只换内容。

    旧配图一律留着：题面里的 uri 还指着它，删了就成死链。等这一批审完，
    ``_settle_batch`` 会把本批残留切图一次性清干净。
    """
    row = con.execute(
        "SELECT id, assets_json FROM pending_questions WHERE id = ?", (pending_id,)
    ).fetchone()
    if row is None:
        raise PendingNotFound("中转站里没有这一条")
    merged = list(json.loads(row["assets_json"] or "[]"))
    known = {str(item.get("name") or "") for item in merged}
    for item in stored_assets:
        name = str(item.get("name") or "")
        if name and name not in known:
            known.add(name)
            merged.append(item)
    document["id"] = pending_id
    con.execute(
        "UPDATE pending_questions SET doc_json = ?, assets_json = ?, updated_at = ?"
        " WHERE id = ?",
        (json.dumps(document, ensure_ascii=False, separators=(",", ":")),
         json.dumps(merged, ensure_ascii=False, separators=(",", ":")),
         questions.now_iso(), pending_id),
    )
    return merged


def _prepare_document(payload: Any, assets: Any,
                      pending_id: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """把一条内容备成「带 ``p_`` 号的暂存文档 + 落盘的配图清单」。"""
    if not isinstance(payload, dict):
        raise PendingError("缺少待暂存的 question 对象")
    body = {key: value for key, value in payload.items() if key not in ("id", "meta", "pending_id")}
    body["id"] = pending_id or new_pending_id()
    document = questions.prepare_new_question(body)

    stored_assets: list[dict[str, Any]] = []
    if assets is not None:
        if not isinstance(assets, list):
            raise PendingError("assets 必须是数组")
        for entry in assets:
            if not isinstance(entry, dict):
                raise PendingError("assets 的每一项都必须是对象")
            image_id = str(entry.get("id") or "").strip()
            if not image_id:
                raise PendingError("配图缺少 id")
            mime, raw = decode_data_url(entry.get("data_url"))
            name = write_pending_asset(raw, mime)
            stored_assets.append({
                "image_id": image_id,
                "name": name,
                "mime": mime,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })

    images = document.get("images")
    if isinstance(images, list):
        by_id = {item["image_id"]: item["name"] for item in stored_assets}
        for image in images:
            if isinstance(image, dict):
                name = by_id.get(str(image.get("id") or ""))
                if name:
                    image["uri"] = PENDING_ASSET_URI_PREFIX + name

    try:
        questions.validate_question(contract_probe(document))
    except questions.QuestionValidationError:
        drop_assets(stored_assets)
        raise
    return document, stored_assets
def set_batch_meta(batch_id: str, payload: Any) -> dict[str, Any]:
    """改一批的公共元数据，这一批的题**立刻**同步。

    同步两处：池子里的待审题（``source`` 与学校 ID），
    以及这一批已经进主库的题（补写主库的 ``sources``）。
    同步不上的题一条也不动，并如实报出原因。
    """
    from app.core import meta_dict

    if not BATCH_ID_RE.match(str(batch_id or "")):
        raise PendingNotFound("批次编号不合法")
    # 先读旧 meta 再规整：老客户端送校名时要先建档，建档会另开连接写字典；
    # 把这一步挪到事务外，避免与本地写锁互相顶住。
    con = connect()
    try:
        row = batch_row(con, batch_id)
        if row is None:
            raise PendingNotFound("中转站里没有这个批次")
        previous = read_meta(row)
    finally:
        con.close()
    meta = normalize_batch_meta(payload, previous)

    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        if batch_row(con, batch_id) is None:
            raise PendingNotFound("中转站里没有这个批次")
        con.execute(
            "UPDATE batches SET meta_json = ?, updated_at = ? WHERE batch_id = ?",
            (json.dumps(meta, ensure_ascii=False, separators=(",", ":")),
             questions.now_iso(), batch_id),
        )
        synced, skipped, warnings = sync_batch_sources(con, batch_id, meta)
        remember_meta(con, meta)
        refresh_batch(con, batch_id)
        live = int(con.execute(
            "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (batch_id,)
        ).fetchone()[0])
        card = batch_card(batch_row(con, batch_id), live)
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()

    patched, bank_warnings = sync_approved_sources(batch_id, meta)
    warnings.extend(bank_warnings)
    return {
        "batch_id": batch_id,
        "batch": card,
        "meta": meta_dict.decorate_meta(meta),
        "synced": synced,
        "skipped": skipped,
        "patched": patched,
        "warnings": warnings,
    }
def approve(pending_id: str, provider_id: str, *, force: bool = False) -> dict[str, Any]:
    """审核通过（**存入主库**）：``p_`` 转 ``q_`` 落进主库，配图搬进 ``uploads/``。

    顺序是刻意的：先把配图搬进主库资源目录，再写题库——写库失败就把配图搬回去，
    池子里那一条原样留着，绝不出现「图进了主库、题没进」或反过来的半截状态。

    **查重**：主库里已有同题（题型、归一题干、归一选项、配图内容全一致）时，
    默认拦下来并把那道题的 id 报回去，让老师决定是改还是强行覆盖；
    ``force=True`` 时以池子里这条为准，覆盖主库那一条（题目 id 不变）。
    """
    item = get_pending(pending_id)
    assets = item.get("assets") or []
    document = copy.deepcopy(item["question"])
    document.pop("id", None)

    existing = find_duplicate(provider_id, document, assets)
    if existing and not force:
        raise PendingDuplicate(
            f"主库已有该题（{existing}），可返回修改或强行覆盖。", existing
        )

    mapping = move_assets_to_uploads(assets)
    rewrite_asset_uris(document, mapping)
    sync_dictionary_schools(provider_id, document)
    try:
        if existing:
            patch = {
                key: document[key]
                for key in ("stem", "options", "answer", "solution", "type", "difficulty",
                            "grade", "taxonomy", "tags", "source", "images")
                if key in document
            }
            question = bank.update_question(provider_id, existing, patch)
            created = False
        else:
            question = bank.create_question(provider_id, document)
            created = True
    except BaseException:
        # 写库没过：配图搬回去，池子里那一条原样等老师再审一次。
        for old_uri, new_uri in mapping.items():
            name = old_uri[len(PENDING_ASSET_URI_PREFIX):]
            target_name = new_uri[len(UPLOAD_ASSET_URI_PREFIX):]
            try:
                shutil.move(str(Path(settings.uploads_dir) / target_name),
                            str(asset_path(name)))
            except (OSError, PendingError):
                pass
        raise

    batch_id = str(item.get("batch_id") or "")
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM pending_questions WHERE id = ?", (pending_id,))
        remember_approved(con, batch_id, str(question.get("id") or ""))
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    drop_assets(assets)
    finished = _settle_batch(batch_id)
    return {
        "pending_id": pending_id,
        "question_id": question.get("id") or "",
        "created": created,
        "overwritten": bool(existing) and not created,
        "batch": finished,
        "question": question,
    }


def delete_pending(pending_id: str) -> dict[str, Any]:
    """彻底删除（**彻底删除**）：这一条连同它的配图从中转站消失，主库一个字节都不碰。

    删掉的是「这一道题」，不是「这一批」：批次本身留着，未审数减一。
    """
    item = get_pending(pending_id)
    batch_id = str(item.get("batch_id") or "")
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM pending_questions WHERE id = ?", (pending_id,))
        row = batch_row(con, batch_id)
        if row is not None:
            con.execute(
                "UPDATE batches SET total = MAX(total - 1, 0), updated_at = ?"
                " WHERE batch_id = ?",
                (questions.now_iso(), batch_id),
            )
        refresh_batch(con, batch_id)
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    drop_assets(item.get("assets") or [])
    finished = _settle_batch(batch_id)
    return {"pending_id": pending_id, "deleted": True, "batch": finished}


def _settle_batch(batch_id: str) -> dict[str, Any]:
    """批次未审数归零时：物理删掉原文件副本与本批残留切图，然后回一张卡片。

    批次**行留着**——老师还要看「未审：0 / 50 ✅」这一行，只是它已经沉底变灰。
    """
    if not batch_id:
        return {}
    con = connect()
    try:
        row = batch_row(con, batch_id)
        if row is None:
            return {}
        live = int(con.execute(
            "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (batch_id,)
        ).fetchone()[0])
        if live:
            return batch_card(row, live)
        assets = json.loads(row["assets_json"] or "[]")
    finally:
        con.close()
    drop_assets([{"name": name} for name in assets])
    for backup in backup_paths(str(row["source_backup"] or "")):
        try:
            if backup.is_file():
                backup.unlink()
        except OSError:
            pass
    return batch_card(row, 0)
