"""中转站里「批次」这一层的生命周期：立批、挂原卷页图、整批删、剔重后收口。

与 ``pending_bank.py`` 的分工：那边管一道题的来去（暂存、入库、单条删除），
这边管一个批次从生到死——扫描版 PDF 先立一个空批次再挂页图；老师说不要了
就整批删干净（待审题、初查账、原卷资产与只读副本一起）；未审数归零时统一
清残留文件。两边共用 ``pending_db`` 的连接与号段、``pending_batches`` 的读写，
所以拆文件不拆口径。
"""

from __future__ import annotations

import json
from typing import Any

from app.core import bank, pending_dedupe, questions
from app.core.pending_assets import backup_path, backup_paths, drop_assets
from app.core.pending_batches import batch_card, batch_row, refresh_batch
from app.core.pending_db import (
    BATCH_ID_RE,
    PENDING_ASSET_RE,
    PENDING_ASSET_URI_PREFIX,
    PENDING_ID_RE,
    PendingError,
    PendingNotFound,
    batch_label,
    connect,
    local_now,
    next_batch_id,
)
from app.core.pending_meta import clean_text


def _page_entries(raw: Any) -> list[dict[str, Any]] | None:
    """校验原卷页面图清单；``None`` 表示这次暂存不动现有的页图。"""
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise PendingError("页面图清单必须是数组")
    entries: list[dict[str, Any]] = []
    for index, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict):
            raise PendingError("页面图的每一项都必须是对象")
        name = str(entry.get("name") or "")
        if not PENDING_ASSET_RE.match(name):
            raise PendingError("页面图文件名不合法")
        try:
            page = int(entry.get("page") or index)
        except (TypeError, ValueError) as exc:
            raise PendingError("页面图页码不合法") from exc
        entries.append({"name": name, "uri": PENDING_ASSET_URI_PREFIX + name, "page": page})
    return entries


def _row_assets(row: Any) -> list[dict[str, Any]]:
    """行上的配图清单；读不出来就当空数组（账要清，配图清不了也不能拦住删题）。"""
    try:
        data = json.loads(row["assets_json"] or "[]")
    except (TypeError, ValueError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def create_batch(*, source_backup: Any = "", source_name: Any = "",
                 scan: bool = False) -> dict[str, Any]:
    """只立批次、不放题：扫描版 PDF 在页面图渲染出来之前先要一个批次号。

    老师的原卷一个文件一个批次；文本层不可用时批次里**一道占位题都不放**，
    老师进批次只见左侧原卷页，自己框选切题。题目等切出来才落池。
    """
    backup_text = str(source_backup or "").strip()
    backup_path(backup_text)
    name_text = clean_text(source_name, 120)
    now = questions.now_iso()
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        target_batch = next_batch_id(con)
        con.execute(
            "INSERT INTO batches"
            " (batch_id, label, created_at, updated_at, source_backup, source_name,"
            "  total, pending_count, assets_json, page_assets_json, scan_batch)"
            " VALUES (?, ?, ?, ?, ?, ?, 0, 0, '[]', '[]', ?)",
            (target_batch, batch_label(local_now()), now, now, backup_text, name_text,
             1 if scan else 0),
        )
        card = batch_card(batch_row(con, target_batch), 0,
                          pooled=pending_dedupe.pooled_counts(con).get(target_batch, 0),
                          con=con)
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return {"batch_id": target_batch, "batch": card, "saved_ids": [],
            "dedupe_queued": False}


def set_batch_pages(batch_id: Any, page_images: Any) -> dict[str, Any]:
    """给批次挂上原卷页面图（扫描版 PDF 的页图在识别之后才渲染完）。"""
    text = str(batch_id or "").strip()
    if not BATCH_ID_RE.match(text):
        raise PendingNotFound("批次编号不合法")
    pages = _page_entries(page_images) or []
    now = questions.now_iso()
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        if batch_row(con, text) is None:
            raise PendingNotFound("中转站里没有这个批次")
        con.execute(
            "UPDATE batches SET page_assets_json = ?, updated_at = ? WHERE batch_id = ?",
            (json.dumps(pages, ensure_ascii=False, separators=(",", ":")), now, text),
        )
        live = int(con.execute(
            "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (text,)
        ).fetchone()[0])
        card = batch_card(batch_row(con, text), live,
                          pooled=pending_dedupe.pooled_counts(con).get(text, 0), con=con)
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return {"batch_id": text, "batch": card, "page_images": pages}


def delete_batch(batch_id: Any) -> dict[str, Any]:
    """彻底删除一整批：待审题、批次行、初查账与全部原卷资产一起清掉。

    主库一个字节都不碰——这里删的只是中转站。文件在事务提交之后删：
    数据先落定，删不掉的残留文件只是垃圾，不回滚。
    """
    text = str(batch_id or "").strip()
    if not BATCH_ID_RE.match(text):
        raise PendingNotFound("批次编号不合法")
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = batch_row(con, text)
        if row is None:
            raise PendingNotFound("中转站里没有这个批次")
        backup_text = str(row["source_backup"] or "")
        rows = con.execute(
            "SELECT id, assets_json FROM pending_questions WHERE batch_id = ?", (text,)
        ).fetchall()
        item_assets = [asset for one in rows for asset in _row_assets(one)]
        try:
            page_assets = json.loads(row["page_assets_json"] or "[]")
        except (TypeError, ValueError):
            page_assets = []
        con.execute("DELETE FROM pending_questions WHERE batch_id = ?", (text,))
        con.execute("DELETE FROM dedupe_findings WHERE batch_id = ?", (text,))
        con.execute("DELETE FROM dedupe_scans WHERE batch_id = ?", (text,))
        con.execute("DELETE FROM batches WHERE batch_id = ?", (text,))
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    drop_assets(item_assets)
    drop_assets([{"name": str(entry.get("name") or "")}
                 for entry in page_assets if isinstance(entry, dict)])
    for backup in backup_paths(backup_text):
        try:
            if backup.is_file():
                backup.unlink()
        except OSError:
            pass
    return {
        "batch_id": text,
        "deleted": True,
        "deleted_questions": len(rows),
        "deleted_pages": len([entry for entry in page_assets if isinstance(entry, dict)]),
    }


class BatchPurgeError(PendingError):
    """一键剔除被拒：带域错误码、HTTP 状态与可否重试，路由层照这三个属性翻。

    与 ``PendingNotFound`` / ``PendingConflict`` 的分工：那两个表达「哪一条不见了 /
    被并发改掉了」，本类表达「剔除动作本身不成立」——载荷自相矛盾、勾的条目已不再
    重复、勾到了保留者、要把整批剔空却没表态。码统一 ``batch_purge_`` 前缀。
    """

    def __init__(self, message: str, *, code: str, status: int = 400,
                 retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.retryable = retryable


def _id_text_list(raw: Any) -> list[str]:
    """把「中转站编号数组」规整成字符串列表；不是数组回 ``None``（形状错，不猜）。"""
    if not isinstance(raw, list):
        return None
    return [item.strip() if isinstance(item, str) else "" for item in raw]


def purge_batch_duplicates(batch_id: str, provider_id: str, drop_ids: Any,
                           expected_drop_ids: Any,
                           allow_empty: bool = False) -> dict[str, Any]:
    """一键剔除本批次重复题：只删 ``drop_ids`` 里那几条池内条目，主库一个字节都不碰。

    四重闸按顺序收口：① 载荷自洽（编号合规、非空、``sorted(drop_ids)`` 与
    ``expected_drop_ids`` 逐项相等，只防截断与中间层改写）；② 归属（勾的条目必须属于
    这一批）；③ **逐条判重**（真正的护栏，进事务后按本次请求的主库快照重算：已不再
    重复回 409 ``batch_purge_selection_stale``，勾到保留者回 409
    ``batch_purge_keep_selected``，两种情况都整批不动）；④ 剔空硬闸（会把整批剔空而
    ``allow_empty`` 不为真时回 400——持 ``questions:write`` 的插件绕过弹窗直投接口也拦得住）。

    主库判定只发生在本次请求的快照上，快照到提交之间不再读主库（毫秒级残窗）。老师
    真正可见的窗口是 ``[dry-run, 本次快照]``：期间主库删题由第 ③ 条闸以 409 拦下，
    主库新增同题则本次清单不含它（少剔），响应里的 ``new_redundant`` 如实报数。
    """
    text_batch = str(batch_id or "").strip()
    if not BATCH_ID_RE.match(text_batch):
        raise BatchPurgeError("批次编号不合法", code="batch_purge_batch_not_found", status=404)

    selected = _id_text_list(drop_ids)
    if selected is None:
        raise BatchPurgeError("drop_ids 必须是中转站编号数组",
                              code="batch_purge_bad_pending_id")
    if not selected:
        raise BatchPurgeError("drop_ids 为空：没有要剔除的条目",
                              code="batch_purge_empty_drop_ids")
    for pending_id in selected:
        if not PENDING_ID_RE.match(pending_id):
            raise BatchPurgeError(f"中转站编号不合法：{pending_id or '(空)'}",
                                  code="batch_purge_bad_pending_id")
    expected = _id_text_list(expected_drop_ids)
    # 回显只防截断与改写，不承担排序约定：两侧都按升序归一后逐项比。
    if expected is None or sorted(selected) != sorted(expected):
        raise BatchPurgeError("勾选清单与回显不一致（请重新扫描后再提交）",
                              code="batch_purge_expected_mismatch_client")

    # 主库快照必须在事务外：中转站库的写锁锁不住主库，进了事务再读只是把窗口拉长。
    try:
        main_rows = pending_dedupe.bank_rows_snapshot(provider_id)
    except bank.BankNotFound as exc:
        raise BatchPurgeError(str(exc) or "题库未安装或未启用",
                              code="batch_purge_bank_not_found", status=404) from exc
    except bank.BankError as exc:
        raise BatchPurgeError(str(exc) or "主库暂时不可用，请稍后重试",
                              code="batch_purge_bank_unavailable", retryable=True) from exc

    con = connect()
    try:
        row = batch_row(con, text_batch)
        if row is None:
            raise BatchPurgeError("中转站里没有这个批次",
                                  code="batch_purge_batch_not_found", status=404)
        source_backup = str(row["source_backup"] or "")
        con.execute("BEGIN IMMEDIATE")
        rows = con.execute(
            "SELECT id, doc_json, assets_json, seq FROM pending_questions"
            " WHERE batch_id = ? ORDER BY seq ASC, id ASC",
            (text_batch,),
        ).fetchall()
        known = {str(item["id"]) for item in rows}
        outsiders = [pending_id for pending_id in selected if pending_id not in known]
        if outsiders:
            raise BatchPurgeError(
                "这些条目不属于本批：" + "、".join(outsiders[:5]),
                code="batch_purge_pending_not_in_batch")
        # 事务内重算：主库用的仍是事务外那一份快照，进事务后不再碰主库连接。
        planned = pending_dedupe.group_duplicates(rows, main_rows)
        recompute = set(planned["recompute"])
        keeps = set(planned["keep_ids"])
        # 保留者保护先判：keep 本来就不在重复全集里，先判 stale 会让 keep_selected 永不可达。
        kept_back = [pending_id for pending_id in selected if pending_id in keeps]
        if kept_back:
            raise BatchPurgeError(
                "勾选里含本批要保留的那一条：" + "、".join(kept_back[:5]),
                code="batch_purge_keep_selected", status=409)
        stale = [pending_id for pending_id in selected if pending_id not in recompute]
        if stale:
            raise BatchPurgeError(
                "这些条目已不再重复：" + "、".join(stale[:5]) + "，请重新扫描",
                code="batch_purge_selection_stale", status=409, retryable=True)
        if len(rows) - len(selected) == 0 and allow_empty is not True:
            raise BatchPurgeError(
                "本次会把这一批剔空（原卷副本与本批残留切图会一并删除），需要显式确认",
                code="batch_purge_empty_not_confirmed")
        assets_by_id = {str(item["id"]): _row_assets(item) for item in rows}
        deleted: list[str] = []
        skipped: list[dict[str, str]] = []
        for pending_id in sorted(selected):
            cursor = con.execute(
                "DELETE FROM pending_questions WHERE id = ? AND batch_id = ?",
                (pending_id, text_batch),
            )
            if cursor.rowcount == 1:
                deleted.append(pending_id)
            else:
                skipped.append({"id": pending_id, "why": "row_gone"})
        con.execute(
            "UPDATE batches SET total = MAX(total - ?, 0), updated_at = ? WHERE batch_id = ?",
            (len(deleted), questions.now_iso(), text_batch),
        )
        refresh_batch(con, text_batch)
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()

    # 文件层在提交之后：数据已经落定，删不掉的残留文件只是垃圾，记一笔不回滚。
    files_failed: list[dict[str, str]] = []
    for pending_id in deleted:
        items = assets_by_id.get(pending_id) or []
        try:
            drop_assets(items)
        except (OSError, PendingError) as exc:
            why = str(exc) or "配图删除失败"
            files_failed.extend({"name": str(item.get("name") or ""), "why": why}
                                for item in items)
    settled = _settle_batch(text_batch)
    return {
        "batch_id": text_batch,
        "deleted": deleted,
        "skipped": skipped,
        "files_failed": files_failed,
        "batch": settled,
        "settled": bool(settled),
        "backup_removed": bool(source_backup) and settled.get("done") is True,
        "new_redundant": len(recompute - set(selected)),
    }


def _settle_batch(batch_id: str) -> dict[str, Any]:
    """批次未审数归零时：物理删掉原文件副本与本批残留切图，然后回一张卡片。

    批次**行留着**——老师还要看「未审：0 / 50 ✅」这一行，只是它已经沉底变灰。
    """
    if not batch_id:
        return {}
    con = connect()
    try:
        con.execute("BEGIN")  # G6：只读事务把这张卡片的四个读数钉在同一份快照上
        try:
            row = batch_row(con, batch_id)
            if row is None:
                return {}
            live = int(con.execute(
                "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (batch_id,)
            ).fetchone()[0])
            # 池内条数与初查结论都从这条连接读（给 con 就不碰进程内缓存），
            # 于是卡片不再出现「待审 2 ＋ 池内 2 而总数才 2」那种跨提交混代帧。
            card = batch_card(row, live,
                              pooled=pending_dedupe.pooled_counts(con).get(str(batch_id), 0),
                              con=con)
            assets = json.loads(row["assets_json"] or "[]")
            page_assets = json.loads(row["page_assets_json"] or "[]")
        finally:
            con.rollback()  # 只读事务就地收尾：本连接一行都没写
    finally:
        con.close()
    if live:
        return card
    if int(row["total"] or 0) == 0 and page_assets:
        # 扫描版批次：一道题都还没有，页面图正是老师的原卷入口，
        # 删掉最后一道切出来的题也不该把原卷一起清掉，否则老师无从再切。
        return card
    drop_assets([{"name": name} for name in assets])
    drop_assets([{"name": str(entry.get("name") or "")}
                 for entry in page_assets if isinstance(entry, dict)])
    for backup in backup_paths(str(row["source_backup"] or "")):
        try:
            if backup.is_file():
                backup.unlink()
        except OSError:
            pass
    # 未审数归零时 ``live`` 本来就是 0，卡片与旧写法 ``batch_card(row, 0)`` 全等；
    # 删的是磁盘上的原文件副本，不影响任何计数，所以卡片在读事务内就算好带回。
    return card
