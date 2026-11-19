"""记号标准字典（闭集＋开集）整机库层（2.21.0 卡 §1/§3）。

三表：``norm_entries``（条目）／``norm_variants``（变体行）／``norm_corrections``（开集四态）。
铁律一表表平等：变体独立成表，禁 JSON 字段藏跨表语义；读取分步查＋应用层组装，不做三表连级 JOIN。

- 闭集内容出厂冻结：种子只补差（按 entry_key），老师只写 ``chosen_default_variant_id``；
  恢复出厂＝选择回退（置 NULL），出厂默认永不动。
- 开集四态人闸：只有 confirmed 参与改写；收编＝状态翻转；raw_code 唯一键去重 hit_count+1；
  rejected＝黑名单永不再问；pending 命中排序、久未命中 archived；pending 一律不生效。
- 整机库住根 ``data/latex_norm.db``（config.latex_norm_db_path），不随工作区漂移；
  备份走 ``machine/`` 层，工作区导入不携带。

WAL 选边（add-data-store 坑）：照主库 ``db.py`` 先例只在建库/迁移时设——
字典读多写少，读连接不该为设日志模式去抢写锁（pending 每连必设是它写频繁的场景）。
本模块不碰 HTTP；清洗接线在 ``latex_style_dict``（字典从参数取），种子导入见 ``import_seed``。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from app.core import toml_io
from app.core.config import settings

SCHEMA_VERSION = 1

# 类别唯一轴＝记号族（主公砍学科分类）；UI 筹码与种子 category 共用这一张表。
FAMILIES = (
    "集合逻辑", "关系不等", "运算分数", "结构环境",
    "希腊变体", "箭头映射", "重音装饰", "单位杂项",
)
# 闭集变体只收这三类合法来源（卡 §2）；非标与 OCR 误识一律住开集。
SOURCE_LABELS = frozenset({"ISO/GB-T", "ISO 80000-2", "GB 3102.11", "教材版式约定"})
STATUSES = ("pending", "confirmed", "rejected", "archived")

SEED_PATH = Path(__file__).with_name("latex_norm_seed.toml")
SUPPORTED_SEED_VERSION = 1
# infix／结构命令换了会破坏参数结构（{a \over b} 改成 \frac 就错），永不进命令级改写；
# 即便未来种子误收单命令码也兜住（三硬规矩·不认识就不动的安全闸）。
_NO_REWRITE = frozenset({
    "over", "atop", "choose", "above", "root", "of", "not",
    "overwithdelims", "atopwithdelims", "abovewithdelims",
    "left", "right", "middle", "begin", "end",
    "bigl", "bigr", "Bigl", "Bigr", "bigm", "Bigm", "big", "Big", "bigg", "Bigg",
    "displaystyle", "textstyle", "scriptstyle", "scriptscriptstyle",
})


class NormError(Exception):
    """字典库前置校验或写入失败；message 可直接回给前端。"""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS norm_entries (
    entry_key                 TEXT PRIMARY KEY,
    name                      TEXT NOT NULL,
    category                  TEXT NOT NULL,
    factory_default_variant_id INTEGER NOT NULL,
    chosen_default_variant_id INTEGER,
    updated_at                TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS norm_variants (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_key        TEXT NOT NULL REFERENCES norm_entries(entry_key) ON DELETE CASCADE,
    latex_code       TEXT NOT NULL,
    source_label     TEXT NOT NULL,
    row_order        INTEGER NOT NULL,
    render_supported INTEGER NOT NULL DEFAULT 1,
    render_note      TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS norm_corrections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_code    TEXT NOT NULL UNIQUE,
    target_code TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'confirmed', 'rejected', 'archived')),
    hit_count   INTEGER NOT NULL DEFAULT 1,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    decided_at  TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_norm_variants_entry ON norm_variants (entry_key, row_order);
CREATE INDEX IF NOT EXISTS idx_norm_corrections_status ON norm_corrections (status, hit_count DESC)
"""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    path = settings.latex_norm_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    try:
        _ensure_schema(con)
    except Exception:
        # 版本过高时这条连接就废了：不关掉会在 Windows 上攥着库文件不放（pending 先例）。
        con.close()
        raise
    return con


def _table_names(con: sqlite3.Connection) -> set[str]:
    return {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _backup_before_migration(path: Path) -> Path:
    stamp = Path(str(path) + f".pre-v{SCHEMA_VERSION}.bak")
    if stamp.exists():
        return stamp
    con = sqlite3.connect(path, timeout=10.0)
    try:
        con.commit()
        target = sqlite3.connect(stamp)
        try:
            con.backup(target)
        finally:
            target.close()
    finally:
        con.close()
    return stamp


def _ensure_schema(con: sqlite3.Connection) -> None:
    version = int(con.execute("PRAGMA user_version").fetchone()[0])
    if version > SCHEMA_VERSION:
        raise NormError(
            f"记号字典结构版本 {version} 高于程序支持的 {SCHEMA_VERSION}，请升级程序或恢复备份。"
        )
    if version == SCHEMA_VERSION:
        return
    if _table_names(con):
        # 库里已有对象才备份；全新空文件无可备。迁移失败时 .pre-vN.bak 可整库回退。
        _backup_before_migration(Path(con.execute("PRAGMA database_list").fetchone()[2]))
    for statement in _SCHEMA.strip().split(";"):
        text = statement.strip()
        if text:
            con.execute(text)
    con.execute("PRAGMA journal_mode = WAL")
    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.commit()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def _rows(con: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in con.execute(sql, params)]


# --- 读：分步查＋应用层组装（星型切换，不做三表连级 JOIN） ---

def list_entries() -> list[dict[str, Any]]:
    """全部条目＋变体行；effective_default = 老师选择优先，未选回退出厂。"""
    con = connect()
    try:
        entries = _rows(con, "SELECT * FROM norm_entries ORDER BY category, entry_key")
        variants = _rows(con, "SELECT * FROM norm_variants ORDER BY entry_key, row_order, id")
    finally:
        con.close()
    by_entry: dict[str, list[dict[str, Any]]] = {}
    for variant in variants:
        by_entry.setdefault(variant["entry_key"], []).append(variant)
    for entry in entries:
        entry["variants"] = by_entry.get(entry["entry_key"], [])
        entry["effective_default_variant_id"] = (
            entry["chosen_default_variant_id"] or entry["factory_default_variant_id"]
        )
    return entries


def get_entry(entry_key: str) -> dict[str, Any] | None:
    return next((e for e in list_entries() if e["entry_key"] == entry_key), None)


def list_corrections(status: str | None = None) -> list[dict[str, Any]]:
    if status is not None and status not in STATUSES:
        raise NormError(f"开集状态非法：{status}")
    con = connect()
    try:
        if status == "pending":
            return _rows(con, "SELECT * FROM norm_corrections WHERE status = 'pending'"
                              " ORDER BY hit_count DESC, last_seen DESC")
        if status is not None:
            return _rows(con, "SELECT * FROM norm_corrections WHERE status = ?"
                              " ORDER BY last_seen DESC", (status,))
        return _rows(con, "SELECT * FROM norm_corrections ORDER BY last_seen DESC")
    finally:
        con.close()


def correction_counts() -> dict[str, int]:
    counts = {status: 0 for status in STATUSES}
    con = connect()
    try:
        for row in con.execute("SELECT status, COUNT(*) AS n FROM norm_corrections GROUP BY status"):
            counts[row["status"]] = int(row["n"])
    finally:
        con.close()
    return counts


# --- 写：老师只动选择与开集裁决；闭集内容由种子冻结 ---

def choose_default(entry_key: str, variant_id: int) -> dict[str, Any]:
    entry = get_entry(entry_key)
    if entry is None:
        raise NormError(f"条目不存在：{entry_key}")
    if not any(v["id"] == variant_id for v in entry["variants"]):
        raise NormError(f"变体 {variant_id} 不属于条目 {entry_key}")
    with transaction() as con:
        con.execute(
            "UPDATE norm_entries SET chosen_default_variant_id = ?, updated_at = ?"
            " WHERE entry_key = ?", (variant_id, now_iso(), entry_key),
        )
    return {"entry_key": entry_key, "chosen_default_variant_id": variant_id}


def reset_default(entry_key: str) -> dict[str, Any]:
    """恢复出厂＝选择回退（置 NULL）；出厂默认本身永不动。"""
    if get_entry(entry_key) is None:
        raise NormError(f"条目不存在：{entry_key}")
    with transaction() as con:
        con.execute(
            "UPDATE norm_entries SET chosen_default_variant_id = NULL, updated_at = ?"
            " WHERE entry_key = ?", (now_iso(), entry_key),
        )
    return {"entry_key": entry_key, "chosen_default_variant_id": None}


def record_unknown(raw_code: str) -> dict[str, Any]:
    """开集候选登记：唯一键去重，再犯 hit_count+1 不新增行。

    rejected 永不再问（只涨命中数）；archived 再犯回 pending（不再「久未命中」）；
    confirmed 保持 confirmed（其纠正已在生效）。候选不打印、不进日志（台账 49 修订）。
    """
    code = (raw_code or "").strip()
    if not code:
        raise NormError("开集候选代码不能为空")
    now = now_iso()
    with transaction() as con:
        con.execute(
            "INSERT INTO norm_corrections (raw_code, target_code, status, hit_count, first_seen, last_seen)"
            " VALUES (?, '', 'pending', 1, ?, ?)"
            " ON CONFLICT(raw_code) DO UPDATE SET"
            " hit_count = hit_count + 1, last_seen = excluded.last_seen,"
            " status = CASE WHEN norm_corrections.status = 'archived'"
            " THEN 'pending' ELSE norm_corrections.status END",
            (code, now, now),
        )
        row = con.execute("SELECT * FROM norm_corrections WHERE raw_code = ?", (code,)).fetchone()
    return dict(row)


def decide_correction(raw_code: str, decision: str, target_code: str = "") -> dict[str, Any]:
    """人闸裁决：pending → confirmed（须给目标代码）／rejected（黑名单）。"""
    if decision not in ("confirmed", "rejected"):
        raise NormError(f"裁决动作非法：{decision}")
    target = (target_code or "").strip()
    if decision == "confirmed" and not target:
        raise NormError("收编必须给出目标代码")
    code = (raw_code or "").strip()
    with transaction() as con:
        row = con.execute("SELECT * FROM norm_corrections WHERE raw_code = ?", (code,)).fetchone()
        if row is None:
            raise NormError(f"开集候选不存在：{code}")
        if row["status"] != "pending":
            raise NormError(f"候选已是 {row['status']}，只有 pending 可裁决")
        con.execute(
            "UPDATE norm_corrections SET status = ?, target_code = ?, decided_at = ?"
            " WHERE raw_code = ?",
            (decision, target if decision == "confirmed" else "", now_iso(), code),
        )
        updated = con.execute("SELECT * FROM norm_corrections WHERE raw_code = ?", (code,)).fetchone()
    return dict(updated)


def sweep_stale(cutoff_iso: str) -> int:
    """久未命中的 pending 沉底 archived；返回沉底条数。"""
    with transaction() as con:
        cursor = con.execute(
            "UPDATE norm_corrections SET status = 'archived'"
            " WHERE status = 'pending' AND last_seen < ?", (cutoff_iso,),
        )
        return int(cursor.rowcount)


# --- 改写驱动：清洗器从这里取字典（零 token，本地 SQLite） ---

def _command_name(code: str) -> str:
    """只有「\\frac」这类单命令码能进命令级别名改写；多 token 码留旧模块字符级规则。"""
    if code.startswith("\\") and code[1:].isalpha():
        return code[1:]
    return ""


def rewrite_aliases() -> dict[str, str] | None:
    """闭集别名映射（命令名→命令名）：非默认且可渲染的变体 → 选中默认。

    库里一条条目都没有（种子未导入）回 None，调用方回落冻结基线字典，
    保证新装环境清洗不断档；种子落地后以库为准。
    """
    entries = list_entries()
    if not entries:
        return None
    aliases: dict[str, str] = {}
    for entry in entries:
        default_id = entry["effective_default_variant_id"]
        canonical = next(
            (v["latex_code"] for v in entry["variants"] if v["id"] == default_id), "")
        canonical_name = _command_name(canonical)
        if not canonical_name or canonical_name in _NO_REWRITE:
            continue
        for variant in entry["variants"]:
            if variant["id"] == default_id or not variant["render_supported"]:
                continue
            name = _command_name(variant["latex_code"])
            if name and name != canonical_name and name not in _NO_REWRITE:
                aliases[name] = canonical_name
    return aliases


def confirmed_corrections() -> dict[str, str]:
    """开集纠正映射：只有 confirmed 参与改写；pending/rejected/archived 一律不生效。"""
    con = connect()
    try:
        rows = con.execute(
            "SELECT raw_code, target_code FROM norm_corrections WHERE status = 'confirmed'")
        return {row["raw_code"]: row["target_code"] for row in rows}
    finally:
        con.close()


# --- 闭集种子：全量写入四保险（卡 §2） ---

def load_seed(path: Path | None = None) -> dict[str, Any]:
    """读种子并前置校验：版本／清单计数／合法族／合法来源／默认下标／唯一键，任一不符显性失败。"""
    data = toml_io.loads((path or SEED_PATH).read_text(encoding="utf-8"))
    if data.get("seed_version") != SUPPORTED_SEED_VERSION:
        raise NormError(f"种子版本 {data.get('seed_version')} 与程序支持的 {SUPPORTED_SEED_VERSION} 不符")
    entries = data.get("entries") or []
    if len(entries) != data.get("entry_count"):
        raise NormError("种子清单条目数与实数不符")
    if sum(len(e.get("variants") or []) for e in entries) != data.get("variant_count"):
        raise NormError("种子清单变体数与实数不符")
    seen: set[str] = set()
    for entry in entries:
        key = entry.get("key") or ""
        if not key or key in seen:
            raise NormError(f"种子条目键缺失或重复：{key}")
        seen.add(key)
        if entry.get("category") not in FAMILIES:
            raise NormError(f"条目 {key} 记号族非法：{entry.get('category')}")
        variants = entry.get("variants") or []
        if not variants or not (0 <= entry.get("default", -1) < len(variants)):
            raise NormError(f"条目 {key} 变体为空或出厂默认越界")
        for variant in variants:
            if not variant.get("code") or variant.get("label") not in SOURCE_LABELS:
                raise NormError(f"条目 {key} 变体代码为空或来源标签非法")
    return data


def _reconcile(con: sqlite3.Connection, seed: dict[str, Any]) -> None:
    """导入后逐件对账：每条种子条目须在库、变体数与内容、出厂默认皆符；不符即抛（调用方回滚）。"""
    for entry in seed["entries"]:
        row = con.execute("SELECT factory_default_variant_id FROM norm_entries WHERE entry_key = ?",
                          (entry["key"],)).fetchone()
        if row is None:
            raise NormError(f"对账失败：条目 {entry['key']} 未落库")
        variants = con.execute("SELECT id, latex_code, source_label FROM norm_variants"
                               " WHERE entry_key = ? ORDER BY row_order", (entry["key"],)).fetchall()
        if len(variants) != len(entry["variants"]):
            raise NormError(f"对账失败：条目 {entry['key']} 变体数不符")
        for got, want in zip(variants, entry["variants"]):
            if got["latex_code"] != want["code"] or got["source_label"] != want["label"]:
                raise NormError(f"对账失败：条目 {entry['key']} 变体内容不符")
        if variants[entry["default"]]["id"] != row["factory_default_variant_id"]:
            raise NormError(f"对账失败：条目 {entry['key']} 出厂默认不符")


def import_seed(path: Path | None = None) -> dict[str, Any]:
    """四保险：①单事务 ②清单＋导入后逐件对账 ③幂等补差按 entry_key（已有条目整条跳过，
    老师选择与出厂内容永不被覆盖）④版本对账通过后才落。任何失败整体回滚。"""
    seed = load_seed(path)
    added = skipped = variants_added = 0
    with transaction() as con:
        for entry in seed["entries"]:
            if con.execute("SELECT 1 FROM norm_entries WHERE entry_key = ?",
                           (entry["key"],)).fetchone():
                skipped += 1
                continue
            con.execute("INSERT INTO norm_entries (entry_key, name, category,"
                        " factory_default_variant_id, updated_at) VALUES (?, ?, ?, 0, ?)",
                        (entry["key"], entry["name"], entry["category"], now_iso()))
            ids: list[int] = []
            for order, variant in enumerate(entry["variants"]):
                cursor = con.execute(
                    "INSERT INTO norm_variants (entry_key, latex_code, source_label, row_order)"
                    " VALUES (?, ?, ?, ?)",
                    (entry["key"], variant["code"], variant["label"], order))
                ids.append(int(cursor.lastrowid))
            con.execute("UPDATE norm_entries SET factory_default_variant_id = ? WHERE entry_key = ?",
                        (ids[entry["default"]], entry["key"]))
            added += 1
            variants_added += len(ids)
        _reconcile(con, seed)
    return {"seed_version": seed["seed_version"], "entries_added": added,
            "entries_skipped": skipped, "variants_added": variants_added,
            "entry_count": seed["entry_count"], "variant_count": seed["variant_count"]}


def apply_render_report(results: list[dict[str, Any]]) -> int:
    """渲染探针结论回写：只动 render_supported/render_note，不碰出厂内容。
    不认的命令显性 0＋原因（全量红线不静默丢），改写驱动据此排除。"""
    updated = 0
    with transaction() as con:
        for item in results:
            cursor = con.execute(
                "UPDATE norm_variants SET render_supported = ?, render_note = ?"
                " WHERE entry_key = ? AND row_order = ?",
                (1 if item.get("supported") else 0, str(item.get("note") or ""),
                 item["entry_key"], int(item["row_order"])))
            updated += int(cursor.rowcount)
    return updated