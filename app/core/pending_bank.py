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
"""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.core import bank, bank_dedupe, questions
from app.core.config import settings

PENDING_ID_PREFIX = "p_"
PENDING_ID_RE = re.compile(r"^p_[A-Za-z0-9_-]{8,64}$")
BATCH_ID_RE = re.compile(r"^B-\d{3,}$")
PENDING_DB_FILENAME = "pending.db"
PENDING_ASSETS_DIRNAME = "pending_assets"
PENDING_ASSET_PREFIX = "pimg_"
PENDING_ASSET_RE = re.compile(r"^pimg_[0-9a-f]{16}\.(?:png|jpg|webp)$")
PENDING_ASSET_URI_PREFIX = "/static/pending/"
UPLOAD_ASSET_URI_PREFIX = "/static/uploads/"
UPLOAD_ASSET_PREFIX = "img_"

SCHEMA_VERSION = 2
MAX_PAGE_SIZE = 100
MAX_BATCH_QUESTIONS = 500

# 配图的口径与 uploads 那条通道保持一致：只认 PNG / JPEG / WebP 的魔数，
# 解码后硬上限 8 MiB，文件名一律底座生成。
MAX_ASSET_BYTES = 8 * 1024 * 1024
MAX_DATA_URL_CHARS = 12 * 1024 * 1024
DATA_URL_RE = re.compile(r"^data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)$")
EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}

_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    batch_id      TEXT PRIMARY KEY,
    label         TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    source_backup TEXT NOT NULL DEFAULT '',
    total         INTEGER NOT NULL DEFAULT 0,
    pending_count INTEGER NOT NULL DEFAULT 0,
    assets_json   TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS pending_questions (
    id          TEXT PRIMARY KEY,
    batch_id    TEXT NOT NULL,
    doc_json    TEXT NOT NULL,
    assets_json TEXT NOT NULL,
    origin      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pending_questions_batch
    ON pending_questions (batch_id, created_at ASC, id ASC);
"""


class PendingError(Exception):
    """中转站操作失败（数据不合规、库不可写等）。"""


class PendingNotFound(PendingError):
    """池子里没有这一条（或没有这个批次）。"""


class PendingConflict(PendingError):
    """同一条被并发处理掉了。"""


class PendingDuplicate(PendingError):
    """主库已有同题。``existing_id`` 指向主库里那道题。

    这是**拦截**而不是拒绝：老师可以在界面上选「强行覆盖」再提交一次，
    底座只负责把「哪一道、差在哪儿」如实报出来，绝不自己替老师做主。
    """

    def __init__(self, message: str, existing_id: str = "") -> None:
        super().__init__(message)
        self.existing_id = existing_id


# ---------------------------------------------------------------- 路径与连接


def pending_db_path() -> Path:
    """中转站库文件：当前工作区下的独立 SQLite。"""
    return Path(settings.data_dir) / PENDING_DB_FILENAME


def pending_assets_dir() -> Path:
    """中转站配图目录：入库前配图只落在这里。"""
    return Path(settings.data_dir) / PENDING_ASSETS_DIRNAME


def init_pending_db() -> None:
    """幂等建库；结构版本写在 ``PRAGMA user_version``，与主库同一套规矩。"""
    con = _connect()
    try:
        con.commit()
    finally:
        con.close()


def _connect() -> sqlite3.Connection:
    path = pending_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    try:
        con.execute("PRAGMA journal_mode = WAL")
    except sqlite3.Error:
        # 只读或网络文件系统可能不支持 WAL，单机回退到默认日志模式。
        pass
    _ensure_schema(con)
    return con


def _table_names(con: sqlite3.Connection) -> set[str]:
    return {row[0] for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )}


def _ensure_schema(con: sqlite3.Connection) -> None:
    version = int(con.execute("PRAGMA user_version").fetchone()[0])
    if version > SCHEMA_VERSION:
        raise PendingError(
            f"中转站结构版本 {version} 高于程序支持的 {SCHEMA_VERSION}，请升级程序或恢复备份。"
        )
    if version == 1:
        # v1 只有一张没有批次的平表。先把旧表挪个名，新表建好后再把数据搬过去。
        if "pending_items" in _table_names(con):
            con.execute("ALTER TABLE pending_items RENAME TO pending_items_v1")
    for statement in _SCHEMA.strip().split(";"):
        text = statement.strip()
        if text:
            con.execute(text)
    if version == 1:
        _migrate_v1_rows(con)
    if version != SCHEMA_VERSION:
        con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.commit()


def _migrate_v1_rows(con: sqlite3.Connection) -> None:
    """v1 → v2：老池子里的题整体收进一个历史批次 ``B-001``，一条不丢。"""
    if "pending_items_v1" not in _table_names(con):
        return
    rows = con.execute(
        "SELECT id, doc_json, assets_json, origin, created_at, updated_at"
        " FROM pending_items_v1 ORDER BY created_at ASC, id ASC"
    ).fetchall()
    created = rows[0]["created_at"] if rows else questions.now_iso()
    con.execute(
        "INSERT OR REPLACE INTO batches"
        " (batch_id, label, created_at, updated_at, source_backup, total, pending_count, assets_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("B-001", batch_label(created), created, questions.now_iso(), "",
         len(rows), len(rows), "[]"),
    )
    for row in rows:
        con.execute(
            "INSERT OR REPLACE INTO pending_questions"
            " (id, batch_id, doc_json, assets_json, origin, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row["id"], "B-001", row["doc_json"], row["assets_json"],
             row["origin"], row["created_at"], row["updated_at"]),
        )
    con.execute("DROP TABLE pending_items_v1")


# ---------------------------------------------------------------- 时间与编号


def _now() -> datetime:
    return datetime.now(bank.LOCAL_TZ)


def batch_label(moment: Any) -> str:
    """批次的时间标签：``2026-11-01-星期日-15:30``。"""
    if isinstance(moment, str):
        try:
            moment = datetime.fromisoformat(moment)
        except ValueError:
            moment = _now()
    return f"{moment:%Y-%m-%d}-{_WEEKDAYS[moment.weekday()]}-{moment:%H:%M}"


def _new_pending_id() -> str:
    """签发中转站号段：``p_`` + 十六进制，与主库的 ``q_`` 号段永不相交。"""
    return PENDING_ID_PREFIX + secrets.token_hex(12)


def _next_batch_id(con: sqlite3.Connection) -> str:
    """批次号 ``B-001`` 起递增；删过批次也不回填——号段只增不复用。"""
    numbers = []
    for row in con.execute("SELECT batch_id FROM batches"):
        matched = BATCH_ID_RE.match(str(row["batch_id"] or ""))
        if matched:
            numbers.append(int(matched.group(0)[2:]))
    return "B-%03d" % ((max(numbers) + 1) if numbers else 1)


# ---------------------------------------------------------------- id 与文档


def _contract_probe(document: dict[str, Any]) -> dict[str, Any]:
    """把暂存文档投影成「契约形状」的影子，用它跑真正的 Schema 校验。

    暂存文档有两处刻意与契约不同：id 走 ``p_`` 号段，配图 uri 指向
    ``pending_assets/``。影子只把这两处换回契约认可的形状，其余字段一字不改——
    这样「暂存时不合规」与「入库时不合规」是同一把尺子量出来的，
    不会出现「池子里躺着、审核时才发现是废题」。
    """
    probe = copy.deepcopy(document)
    probe["id"] = "q_" + secrets.token_hex(12)
    probe["schema_version"] = "2.0"
    images = probe.get("images")
    if isinstance(images, list):
        for image in images:
            if isinstance(image, dict):
                image["uri"] = UPLOAD_ASSET_URI_PREFIX + "_probe.png"
    return probe


def _sniff_mime(data: bytes) -> str:
    """按魔数认图；不认识就回空串（绝不信请求自报的 MIME）。"""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return ""


def _decode_data_url(data_url: Any) -> tuple[str, bytes]:
    """data URL → (MIME, 字节)。不合规就抛，绝不猜。"""
    if not isinstance(data_url, str) or not data_url:
        raise PendingError("配图缺少 data_url")
    if len(data_url) > MAX_DATA_URL_CHARS:
        raise PendingError("图片过大（解码后上限 8 MiB）")
    matched = DATA_URL_RE.match(data_url)
    if matched is None:
        raise PendingError("只接受 PNG / JPEG / WebP 的 base64 data URL")
    declared, payload = matched.group(1), matched.group(2)
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PendingError("图片 base64 内容不合法") from exc
    if not raw:
        raise PendingError("图片内容为空")
    if len(raw) > MAX_ASSET_BYTES:
        raise PendingError("图片过大（解码后上限 8 MiB）")
    actual = _sniff_mime(raw)
    if not actual:
        raise PendingError("不是可识别的 PNG / JPEG / WebP 图片")
    if actual != declared:
        raise PendingError("图片魔数与声明的格式不一致")
    return actual, raw


def _write_pending_asset(raw: bytes, mime: str) -> str:
    """配图落进 ``pending_assets/``：文件名底座生成，先写临时文件再原子改名。"""
    root = pending_assets_dir()
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(5):
        name = PENDING_ASSET_PREFIX + secrets.token_hex(8) + EXTENSIONS[mime]
        target = root / name
        if target.exists():
            continue
        temp = root / (".pending-" + secrets.token_hex(8) + ".tmp")
        try:
            temp.write_bytes(raw)
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
        return name
    raise PendingError("生成配图文件名失败，请重试")


def _asset_path(name: str) -> Path:
    """把池子里记的文件名解析成真实路径；名字不合规一律拒绝，绝不拼路径。"""
    if not PENDING_ASSET_RE.match(str(name or "")):
        raise PendingError("配图文件名不合法")
    root = pending_assets_dir()
    target = root / name
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise PendingError("配图路径越界") from exc
    return target


def _rewrite_asset_uris(document: dict[str, Any], mapping: dict[str, str]) -> None:
    """把文档里的配图 uri 换一批：``mapping`` 是「旧 uri → 新 uri」。"""
    images = document.get("images")
    if not isinstance(images, list):
        return
    for image in images:
        if isinstance(image, dict):
            new_uri = mapping.get(str(image.get("uri") or ""))
            if new_uri:
                image["uri"] = new_uri


def _drop_assets(assets: Iterable[dict[str, Any]]) -> None:
    """把配图从 ``pending_assets/`` 里删掉（否决与入库失败都要走这条）。"""
    for item in assets or []:
        name = str(item.get("name") or "")
        if not PENDING_ASSET_RE.match(name):
            continue
        path = pending_assets_dir() / name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            # 删不掉的残留文件不该让整次操作失败：它只是垃圾，不是数据。
            pass


def _backup_path(source_backup: str) -> Path | None:
    """原文件副本的路径：只许工作区 ``data/`` 里的相对路径，越界一律拒绝。"""
    text = str(source_backup or "").strip()
    if not text:
        return None
    if text.startswith("/") or "\\" in text:
        raise PendingError("原文件副本路径必须是工作区内的相对路径")
    parts = [part for part in text.split("/") if part]
    if not parts or any(part in (".", "..") for part in parts):
        raise PendingError("原文件副本路径非法")
    root = Path(settings.data_dir).resolve()
    target = root.joinpath(*parts)
    try:
        target.resolve().relative_to(root)
    except ValueError as exc:
        raise PendingError("原文件副本路径越界") from exc
    return target


# ---------------------------------------------------------------- 查重口径


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


# ---------------------------------------------------------------- 批次读写


def _batch_card(row: sqlite3.Row, live: int) -> dict[str, Any]:
    """批次卡片：时间、编号、未审数 / 总题数。"""
    return {
        "batch_id": str(row["batch_id"]),
        "label": str(row["label"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "source_backup": str(row["source_backup"] or ""),
        "total": int(row["total"] or 0),
        "pending_count": live,
        "done": live == 0,
    }


def batch_list() -> dict[str, Any]:
    """所有批次（卡片视图）。

    排序口径：**有未审的批次在前**（新到旧），**已审完的批次沉在最后**（新到旧）。
    未审数一律按池子里真实的行数算——存的计数只是缓存，不是事实来源。
    """
    con = _connect()
    try:
        rows = con.execute("SELECT * FROM batches").fetchall()
        live = {str(row["batch_id"]): int(row["n"]) for row in con.execute(
            "SELECT batch_id, COUNT(*) AS n FROM pending_questions GROUP BY batch_id"
        )}
    finally:
        con.close()
    cards = [_batch_card(row, live.get(str(row["batch_id"]), 0)) for row in rows]
    cards.sort(key=lambda card: (card["pending_count"] == 0,
                                 _sort_key(card["created_at"], card["batch_id"])))
    return {"batches": cards}


def _sort_key(created_at: str, batch_id: str) -> tuple[str, str]:
    """倒序用的排序键：先看时间，时间相同再看批次号（号大的新）。"""
    return (str(created_at or ""), str(batch_id or ""))


def _batch_row(con: sqlite3.Connection, batch_id: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()


def _refresh_batch(con: sqlite3.Connection, batch_id: str) -> None:
    """把批次的未审数刷成池子里的真实行数（总题数另有其账，见 save_draft）。"""
    live = int(con.execute(
        "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (batch_id,)
    ).fetchone()[0])
    row = _batch_row(con, batch_id)
    if row is None:
        return
    con.execute(
        "UPDATE batches SET pending_count = ?, updated_at = ? WHERE batch_id = ?",
        (live, questions.now_iso(), batch_id),
    )


def list_batch_questions(batch_id: str) -> dict[str, Any]:
    """按批次拉取待审题目（录入先后顺序）。"""
    if not BATCH_ID_RE.match(str(batch_id or "")):
        raise PendingNotFound("批次编号不合法")
    con = _connect()
    try:
        batch = _batch_row(con, batch_id)
        if batch is None:
            raise PendingNotFound("中转站里没有这个批次")
        rows = con.execute(
            "SELECT id, batch_id, doc_json, assets_json, origin, created_at, updated_at"
            " FROM pending_questions WHERE batch_id = ? ORDER BY created_at ASC, id ASC",
            (batch_id,),
        ).fetchall()
    finally:
        con.close()
    return {
        "batch_id": batch_id,
        "items": [_row_to_item(row) for row in rows],
        "pending_count": len(rows),
        "total": int(batch["total"] or 0),
    }


def _row_to_item(row: sqlite3.Row) -> dict[str, Any]:
    document = json.loads(row["doc_json"])
    document["id"] = row["id"]
    assets = json.loads(row["assets_json"]) if row["assets_json"] else []
    return {
        "id": row["id"],
        "batch_id": row["batch_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "origin": row["origin"],
        "question": document,
        "assets": assets,
    }


# ---------------------------------------------------------------- 写入


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
               origin: Any = "") -> dict[str, Any]:
    """把一道题或一批题存进中转站（**存为待办**）。

    - ``batch_id`` 给了就并进那一批；没给就新开一批（``B-001`` 起）。
    - ``source_backup`` 是原文件只读副本在工作区 ``data/`` 里的相对路径；
      批次未审数归零时底座会**物理删掉**它，磁盘不留废纸。
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
    backup = _backup_path(backup_text)

    prepared: list[tuple[dict[str, Any], list[dict[str, Any]], str]] = []
    for item in items:
        payload, assets, pending_id = _item_parts(item)
        document, stored = _prepare_document(payload, assets, pending_id or None)
        prepared.append((document, stored, pending_id))

    now = questions.now_iso()
    con = _connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        target_batch = str(batch_id or "").strip()
        if target_batch:
            if not BATCH_ID_RE.match(target_batch):
                raise PendingError("批次编号不合法")
            if _batch_row(con, target_batch) is None:
                raise PendingNotFound("中转站里没有这个批次")
        else:
            target_batch = _next_batch_id(con)
            con.execute(
                "INSERT INTO batches"
                " (batch_id, label, created_at, updated_at, source_backup, total, pending_count, assets_json)"
                " VALUES (?, ?, ?, ?, ?, 0, 0, ?)",
                (target_batch, batch_label(_now()), now, now, backup_text, "[]"),
            )
        if backup_text and not str(
            (_batch_row(con, target_batch) or {"source_backup": ""})["source_backup"] or ""
        ):
            con.execute(
                "UPDATE batches SET source_backup = ? WHERE batch_id = ?",
                (backup_text, target_batch),
            )
        names: list[str] = []
        inserted = 0
        for document, stored, pending_id in prepared:
            if pending_id:
                # 就地更新：号、批次与未审数都不动，只换内容。
                names.extend(str(item.get("name") or "") for item in _replace_pending(
                    con, pending_id, document, stored))
                continue
            con.execute(
                "INSERT INTO pending_questions"
                " (id, batch_id, doc_json, assets_json, origin, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    document["id"], target_batch,
                    json.dumps(document, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(stored, ensure_ascii=False, separators=(",", ":")),
                    str(origin or "")[:64], now, now,
                ),
            )
            inserted += 1
            names.extend(str(item.get("name") or "") for item in stored)
        row = _batch_row(con, target_batch)
        merged = list(json.loads(row["assets_json"] or "[]"))
        merged.extend(name for name in names if name)
        con.execute(
            "UPDATE batches SET total = total + ?, assets_json = ?, updated_at = ?"
            " WHERE batch_id = ?",
            (inserted, json.dumps(merged, ensure_ascii=False, separators=(",", ":")),
             now, target_batch),
        )
        _refresh_batch(con, target_batch)
        live = int(con.execute(
            "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (target_batch,)
        ).fetchone()[0])
        card = _batch_card(_batch_row(con, target_batch), live)
        con.commit()
    except BaseException:
        con.rollback()
        for _document, stored, _pending_id in prepared:
            _drop_assets(stored)
        raise
    finally:
        con.close()
    return {
        "batch_id": target_batch,
        "batch": card,
        "saved_ids": [document["id"] for document, _stored, _pending_id in prepared],
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
    body["id"] = pending_id or _new_pending_id()
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
            mime, raw = _decode_data_url(entry.get("data_url"))
            name = _write_pending_asset(raw, mime)
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
        questions.validate_question(_contract_probe(document))
    except questions.QuestionValidationError:
        _drop_assets(stored_assets)
        raise
    return document, stored_assets


# ---------------------------------------------------------------- 审核动作


def get_pending(pending_id: str) -> dict[str, Any]:
    """取池子里的一条；不在就是 404。"""
    if not PENDING_ID_RE.match(str(pending_id or "")):
        raise PendingNotFound("中转站编号不合法")
    con = _connect()
    try:
        row = con.execute(
            "SELECT id, batch_id, doc_json, assets_json, origin, created_at, updated_at"
            " FROM pending_questions WHERE id = ?",
            (pending_id,),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise PendingNotFound("中转站里没有这一条")
    return _row_to_item(row)


def _move_assets_to_uploads(assets: list[dict[str, Any]]) -> dict[str, str]:
    """把配图从 ``pending_assets/`` 搬进 ``uploads/``，返回「旧 uri → 新 uri」。

    文件名也跟着换：池子里叫 ``pimg_x.png``，进主库后叫 ``img_x.png``——
    两套目录的名字空间本来就该分开，不然主库里会出现一堆 ``pimg_`` 开头的文件。
    """
    mapping: dict[str, str] = {}
    uploads_root = Path(settings.uploads_dir)
    uploads_root.mkdir(parents=True, exist_ok=True)
    for asset in assets:
        name = str(asset.get("name") or "")
        if not PENDING_ASSET_RE.match(name):
            continue
        source = _asset_path(name)
        if not source.is_file():
            continue
        target_name = UPLOAD_ASSET_PREFIX + name[len(PENDING_ASSET_PREFIX):]
        target = uploads_root / target_name
        shutil.move(str(source), str(target))
        mapping[PENDING_ASSET_URI_PREFIX + name] = UPLOAD_ASSET_URI_PREFIX + target_name
    return mapping


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

    mapping = _move_assets_to_uploads(assets)
    _rewrite_asset_uris(document, mapping)
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
                            str(_asset_path(name)))
            except (OSError, PendingError):
                pass
        raise

    batch_id = str(item.get("batch_id") or "")
    con = _connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM pending_questions WHERE id = ?", (pending_id,))
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    _drop_assets(assets)
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
    con = _connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM pending_questions WHERE id = ?", (pending_id,))
        row = _batch_row(con, batch_id)
        if row is not None:
            con.execute(
                "UPDATE batches SET total = MAX(total - 1, 0), updated_at = ?"
                " WHERE batch_id = ?",
                (questions.now_iso(), batch_id),
            )
        _refresh_batch(con, batch_id)
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    _drop_assets(item.get("assets") or [])
    finished = _settle_batch(batch_id)
    return {"pending_id": pending_id, "deleted": True, "batch": finished}


def _settle_batch(batch_id: str) -> dict[str, Any]:
    """批次未审数归零时：物理删掉原文件副本与本批残留切图，然后回一张卡片。

    批次**行留着**——老师还要看「未审：0 / 50 ✅」这一行，只是它已经沉底变灰。
    """
    if not batch_id:
        return {}
    con = _connect()
    try:
        row = _batch_row(con, batch_id)
        if row is None:
            return {}
        live = int(con.execute(
            "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (batch_id,)
        ).fetchone()[0])
        if live:
            return _batch_card(row, live)
        assets = json.loads(row["assets_json"] or "[]")
    finally:
        con.close()
    _drop_assets([{"name": name} for name in assets])
    backup = _backup_path(str(row["source_backup"] or ""))
    if backup is not None:
        try:
            if backup.is_file():
                backup.unlink()
        except OSError:
            pass
    return _batch_card(row, 0)
