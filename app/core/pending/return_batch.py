"""整批打回文件收集框（2.20.0 卡§2）：源文件＋批次元数据原样交回插件。

语义钉死：未入库题随批作废、已入库题留库不动——复用 delete_batch 的既有口径
（它只清中转站，主库一个字节不碰）。原卷字节在删批之前读出来：delete_batch
提交后会物理删副本，顺序反了就只能打回一张空壳。

路由体检里的 text_layer 一并交回（三态：True/False/None＝没体检过），
插件据此把组合路对纯图卷灰掉；元数据给 read_meta 的原始形状，重新入库时
经 set_batch_meta 规整落批，PATCH 合并口径保证原样往返。
"""

from __future__ import annotations

import base64
import mimetypes
from typing import Any

from app.core.pending.assets import _sniff_mime, backup_paths
from app.core.pending.batch.batches import batch_row, read_approved, read_meta, read_route
from app.core.pending.batch.bank_batches import delete_batch
from app.core.pending.db import BATCH_ID_RE, PendingError, PendingNotFound, connect


def _source_name(row: Any, path: Any, single: bool) -> str:
    """打回筐里的文件名：单副本用批次登记的原名；多副本剥掉副本的时间戳前缀。"""
    if single:
        return str(row["source_name"] or "") or path.name
    stem = path.name.split("_", 2)
    return stem[2] if len(stem) == 3 else path.name


def return_batch(batch_id: Any) -> dict[str, Any]:
    """读原卷＋元数据＋入库账 → 删批（未入库作废）→ 交回收集框形状。"""
    text = str(batch_id or "").strip()
    if not BATCH_ID_RE.match(text):
        raise PendingNotFound("批次编号不合法")
    con = connect()
    try:
        row = batch_row(con, text)
        if row is None:
            raise PendingNotFound("中转站里没有这个批次")
        meta = read_meta(row)
        route = read_route(row)
        kept = len(read_approved(row))
        discarded = int(con.execute(
            "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (text,)
        ).fetchone()[0])
        backups = backup_paths(str(row["source_backup"] or ""))
        single = len(backups) == 1
        names = [_source_name(row, path, single) for path in backups]
    finally:
        con.close()
    files: list[dict[str, Any]] = []
    for name, path in zip(names, backups):
        if not path.is_file():
            continue
        payload = path.read_bytes()
        mime = (_sniff_mime(payload)
                or mimetypes.guess_type(name)[0]
                or "application/octet-stream")
        files.append({"name": name,
                      "data_url": "data:%s;base64,%s" % (
                          mime, base64.b64encode(payload).decode("ascii"))})
    if not files:
        raise PendingError("原卷文件不在了，打回不了：批次 %s 的源副本已缺失，"
                           "请重新拖入原卷。" % text)
    delete_batch(text)
    return {"batch_id": text, "files": files, "meta": meta,
            "text_layer": route.get("text_layer"),
            "discarded": discarded, "kept": kept}