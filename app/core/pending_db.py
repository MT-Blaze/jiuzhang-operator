"""中转站的库层：独立 SQLite、号段、结构版本与字典基线。

只回答三个问题：库文件在哪、表结构怎么升、基线字典（学校/场景/交叉标签）怎么播。
「批次与条目怎么读写」见 pending_batches.py，「元数据规则」见 pending_meta.py，
「审核动作」见 pending_bank.py。

结构版本写在 ``PRAGMA user_version``，与主库同一套规矩：版本只能往前走，
高于程序支持的版本号直接拒绝启动，绝不猜测怎么降级。
每次连接都播种字典（``INSERT OR IGNORE``）——老师删过的标签不复活，老师加的不冲掉。
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core import bank, pinyin, questions
from app.core.config import settings

PENDING_ID_PREFIX = "p_"
PENDING_ID_RE = re.compile(r"^p_[A-Za-z0-9_-]{8,64}$")
# 重题池与它的裁决记录各自一条号段（军令 #32 · S4），与 p_ / q_ 都不相交。
POOL_ID_PREFIX = "pool_"
POOL_ACTION_ID_PREFIX = "pa_"
POOL_ID_RE = re.compile(r"^pool_[A-Za-z0-9_-]{8,64}$")
BATCH_ID_RE = re.compile(r"^B-\d{3,}$")
PENDING_DB_FILENAME = "pending.db"
PENDING_ASSETS_DIRNAME = "pending_assets"
PENDING_ASSET_PREFIX = "pimg_"
PENDING_ASSET_RE = re.compile(r"^pimg_[0-9a-f]{16}\.(?:png|jpg|webp|svg)$")
PENDING_ASSET_URI_PREFIX = "/static/pending/"
UPLOAD_ASSET_URI_PREFIX = "/static/uploads/"
UPLOAD_ASSET_PREFIX = "img_"
# 重题池的成品图自成一户（军令 #32 · S5）：抽走时**复制**进 ``pool_assets/``，
# 号段 ``cimg_`` 与待审池的 ``pimg_``、主库的 ``img_`` 都不相交。目录分开是
# 「井水不犯河水」的落点——批次审完 ``_settle_batch`` 清 ``pending_assets/``，
# 清不到池里那条的图；池内 ``delete`` 也删不到批次还在用的图。
POOL_ASSETS_DIRNAME = "pool_assets"
POOL_ASSET_PREFIX = "cimg_"
POOL_ASSET_RE = re.compile(r"^cimg_[0-9a-f]{16}\.(?:png|jpg|webp)$")
POOL_ASSET_URI_PREFIX = "/static/pool/"

SCHEMA_VERSION = 10
MAX_BATCH_QUESTIONS = 500

# 配图的口径与 uploads 那条通道保持一致：只认 PNG / JPEG / WebP 的魔数，
# 解码后硬上限 8 MiB，文件名一律底座生成。
MAX_ASSET_BYTES = 8 * 1024 * 1024
MAX_DATA_URL_CHARS = 12 * 1024 * 1024
DATA_URL_RE = re.compile(r"^data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)$")
EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
              "image/svg+xml": ".svg"}

_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

# 明细学校最多 24 所（老师一眼数得过来）；标准名与题面标签各有各的上限，
# 口径一律跟契约对齐，不自造。
META_SCHOOL_LIMIT = 24
# 标准名最终落进 source.paper_title，契约上限 120 字；这里跟契约对齐，不自造口径。
META_NAME_LIMIT = 120
# 老版本的明细学校以隐藏标签形式存过校名；升到 2.1 后题目只存 school_id，
# 这些遗留隐藏标签在一次元数据同步时清掉。
HIDDEN_TAG_PREFIX = "#"
# 「主体 → 明细名单」的对应关系在 meta_history 里用一行记。
# 主体与名单之间用竖线分，学校名之间用单元分隔符分——校名里可能有逗号（"哈三中,分校"），
# 拿逗号当分隔会把一所学校劈成两半。
GROUP_SEP = "|"
GROUP_ITEM_SEP = "\x1f"

# 11 大主场景（主公 2026-11-01 裁定）。场景名就是题目里存的值，字典表只做登记与排序。
SCENE_SEED = (
    ("scene_gaokao", "高考题"),
    ("scene_liankao", "联考题"),
    ("scene_region", "区域统考题"),
    ("scene_school", "校考题"),
    ("scene_agency", "机构题"),
    ("scene_compilation", "汇编题"),
    ("scene_selfmade", "自编题"),
    ("scene_qiangji", "强基题"),
    ("scene_contest", "竞赛题"),
    ("scene_selftest", "自主招生题"),
    ("scene_foreign", "外国题"),
)
SCENE_NAMES = tuple(name for _id, name in SCENE_SEED)
SCENE_BY_NAME = {name: scene_id for scene_id, name in SCENE_SEED}

# 交叉标签的初始权重：场景专属权重排前面，全局权重垫底。
# 「外国题」优先 AMC / A-Level / IB；「校考题」优先 9月月考 / 一模；
# 输入「模」要能把零到七模一次带出来。
EXAM_SEED = (
    ("AMC", "外国题", 100),
    ("A-Level", "外国题", 90),
    ("IB", "外国题", 80),
    ("9月月考", "校考题", 100),
    ("一模", "校考题", 90),
    ("零模", "校考题", 80),
    ("二模", "校考题", 70),
    ("三模", "校考题", 60),
    ("四模", "校考题", 50),
    ("五模", "校考题", 40),
    ("六模", "校考题", 30),
    ("七模", "校考题", 20),
    ("AMC", "竞赛题", 100),
    ("全国高中数学联赛", "竞赛题", 90),
    ("零模", "", 10),
    ("一模", "", 10),
    ("二模", "", 10),
    ("三模", "", 10),
    ("四模", "", 10),
    ("五模", "", 10),
    ("六模", "", 10),
    ("七模", "", 10),
    ("百日誓师考", "", 5),
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    batch_id      TEXT PRIMARY KEY,
    label         TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    source_backup TEXT NOT NULL DEFAULT '',
    source_name   TEXT NOT NULL DEFAULT '',
    meta_json     TEXT NOT NULL DEFAULT '{}',
    approved_json TEXT NOT NULL DEFAULT '[]',
    total         INTEGER NOT NULL DEFAULT 0,
    pending_count INTEGER NOT NULL DEFAULT 0,
    assets_json   TEXT NOT NULL DEFAULT '[]',
    -- 原卷页面图（批次层，不挂题身）：[{"name","uri","page"}]。
    page_assets_json TEXT NOT NULL DEFAULT '[]',
    -- 原卷批次：1 表示这一批按原卷大图导入，左栏整卷铺页图、老师自己框选切题。
    -- 判定要跨刷新与重启都留着，不能靠「当前有没有题」来猜。
    scan_batch    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pending_questions (
    id          TEXT PRIMARY KEY,
    batch_id    TEXT NOT NULL,
    doc_json    TEXT NOT NULL,
    assets_json TEXT NOT NULL,
    origin      TEXT NOT NULL DEFAULT '',
    page_no     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    seq         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_pending_questions_batch
    ON pending_questions (batch_id, created_at ASC, id ASC);
CREATE TABLE IF NOT EXISTS meta_history (
    kind       TEXT NOT NULL,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (kind, value)
);
CREATE TABLE IF NOT EXISTS schools (
    id         TEXT PRIMARY KEY,
    full_name  TEXT NOT NULL,
    short_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_schools_short_name ON schools (short_name);
CREATE INDEX IF NOT EXISTS idx_schools_full_name ON schools (full_name);
CREATE TABLE IF NOT EXISTS scene_types (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exam_types (
    name       TEXT NOT NULL,
    scene      TEXT NOT NULL DEFAULT '',
    weight     INTEGER NOT NULL DEFAULT 0,
    pinyin     TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (name, scene)
);
CREATE INDEX IF NOT EXISTS idx_exam_types_name ON exam_types (name);
-- 整批初查的结论（军令 #32 · S3 判据 3.3）。进程内缓存只是「这一次会话里的快取」，
-- 底座一起就全空；批次卡片于是报「还没扫」，老师重开程序会以为初查白跑了。
-- 这两张表就是让结论跨过重启可读：**只存结论，不存题目**，池内容永远是事实来源。
CREATE TABLE IF NOT EXISTS dedupe_scans (
    batch_id      TEXT PRIMARY KEY,
    provider_id   TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL,                 -- done / failed
    scanned       INTEGER NOT NULL DEFAULT 0,
    redundant     INTEGER NOT NULL DEFAULT 0,
    batch_redundant INTEGER NOT NULL DEFAULT 0,
    bank_redundant  INTEGER NOT NULL DEFAULT 0,
    main_scanned  INTEGER NOT NULL DEFAULT 0,
    tier          TEXT NOT NULL DEFAULT 'loose',
    truncated     INTEGER NOT NULL DEFAULT 0,
    code          TEXT NOT NULL DEFAULT '',      -- failed 时的机读码（可重试）
    retryable     INTEGER NOT NULL DEFAULT 0,
    message       TEXT NOT NULL DEFAULT '',      -- failed 时给老师看的那句话
    finished_at   TEXT NOT NULL,
    generation    INTEGER NOT NULL DEFAULT 0     -- 落库时的进程内世代号，防旧代覆盖新代
);
CREATE TABLE IF NOT EXISTS dedupe_findings (
    batch_id     TEXT NOT NULL,
    item_id      TEXT NOT NULL,
    reason       TEXT NOT NULL,                  -- batch（批内互重）/ bank（主库已有）
    keep_id      TEXT NOT NULL DEFAULT '',       -- reason=batch 时保留者；bank 为空
    existing_id  TEXT NOT NULL DEFAULT '',       -- reason=bank 时命中的主题号
    level        TEXT NOT NULL,                  -- certain/very_similar/fairly_similar/possible
    percent      INTEGER NOT NULL DEFAULT 0,
    similarity   REAL NOT NULL DEFAULT 0,        -- 骨架相似度：候选行的可解释数字
    fingerprint  TEXT NOT NULL DEFAULT '',
    signals_json TEXT NOT NULL DEFAULT '[]',     -- 可展开的命中/未命中明细（原样回投）
    created_at   TEXT NOT NULL,
    PRIMARY KEY (batch_id, item_id)
);
CREATE INDEX IF NOT EXISTS idx_dedupe_findings_batch_level
    ON dedupe_findings (batch_id, level, item_id);
-- 重题池（军令 #32 · S4 判据 4.1–4.3）。这张表**独立于待审池与批次**：
-- 一条进来题只占一条（``item_id`` 唯一），自带题目文档与自己裁下来的成品图，
-- 批次删了照常可读；来源批次号与原文件名只是溯源字段。整页底图不进这里。
CREATE TABLE IF NOT EXISTS duplicate_pool (
    pool_id      TEXT PRIMARY KEY,
    item_id      TEXT NOT NULL UNIQUE,          -- 一条一题：同一进来题不占两条
    batch_id     TEXT NOT NULL DEFAULT '',      -- 溯源：来自哪一批（不作外键）
    source_name  TEXT NOT NULL DEFAULT '',      -- 溯源：来自哪个原文件
    provider_id  TEXT NOT NULL DEFAULT '',      -- 配的主库
    main_id      TEXT NOT NULL DEFAULT '',      -- 最像的那道主库原题
    level        TEXT NOT NULL DEFAULT '',      -- certain/very_similar/fairly_similar/possible
    percent      INTEGER NOT NULL DEFAULT 0,
    similarity   REAL NOT NULL DEFAULT 0,
    signals_json TEXT NOT NULL DEFAULT '[]',
    doc_json     TEXT NOT NULL,                 -- 池内自带完整题目文档
    assets_json  TEXT NOT NULL DEFAULT '[]',    -- 只记题自己的成品图，不记底图
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_duplicate_pool_main ON duplicate_pool (main_id, item_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_pool_batch ON duplicate_pool (batch_id);
-- 裁决记录（判据 4.9 + 5.3 的数据层那一半）：条目裁决完就从池里退场，
-- 但这条记录留着——拖档重扫时按它挡住复活，同时它就是最小审计
-- （时间、动作、来源批次、主库题 id），不再另开第三张表。
CREATE TABLE IF NOT EXISTS pool_actions (
    action_id   TEXT PRIMARY KEY,
    pool_id     TEXT NOT NULL DEFAULT '',
    item_id     TEXT NOT NULL DEFAULT '',
    batch_id    TEXT NOT NULL DEFAULT '',       -- 来源批次（审计字段）
    main_id     TEXT NOT NULL DEFAULT '',       -- 主库题 id（审计字段）
    action      TEXT NOT NULL,                  -- 四个动作之一
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pool_actions_item ON pool_actions (item_id, created_at);
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


class PendingDuplicateAnswer(PendingDuplicate):
    """主库已有高度相似题，**且两边答案对不上**——这一档只许放弃，不许覆盖或合并。

    答案不同意味着这多半是两道不同的题（或其中一道抄错了），此时覆盖等于拿错答案
    盖掉对答案、合并等于把两套互相矛盾的解法并进一道题。两种都是在毁数据，
    所以这里把 ``existing`` / ``incoming`` 两份答案原样报出去，让老师自己回池子里改。
    """

    def __init__(self, message: str, existing_id: str = "", *, existing: str = "",
                 incoming: str = "") -> None:
        super().__init__(message, existing_id)
        self.existing_answer = existing
        self.incoming_answer = incoming


# ---------------------------------------------------------------- 路径与连接


def pending_db_path() -> Path:
    """中转站库文件：当前工作区下的独立 SQLite。"""
    return Path(settings.data_dir) / PENDING_DB_FILENAME


def pending_assets_dir() -> Path:
    """中转站配图目录：入库前配图只落在这里。"""
    return Path(settings.data_dir) / PENDING_ASSETS_DIRNAME


def pool_assets_dir() -> Path:
    """重题池成品图目录：只归重题池自己清理，批次那边的删除动作碰不到这里。"""
    return Path(settings.data_dir) / POOL_ASSETS_DIRNAME



def connect() -> sqlite3.Connection:
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
    try:
        _ensure_schema(con)
    except Exception:
        # 结构版本过高时这条连接就废了：不关掉会在 Windows 上攥着库文件不放，
        # 调用方接住异常也删不掉临时目录（测试与「恢复备份」流程都吃这个亏）。
        con.close()
        raise
    return con


def _table_names(con: sqlite3.Connection) -> set[str]:
    return {row[0] for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )}


# 军令 #32 · S3 本轮新增列的补丁表：``表名 -> ((列名, 列定义), ...)``。
# 只在「版本号已是 7、表却是开发期旧形状」时补，正常库一句 DDL 都不发。
_DEDUPE_COLUMN_PATCHES = {
    "dedupe_scans": (("message", "TEXT NOT NULL DEFAULT ''"),),
    "dedupe_findings": (("similarity", "REAL NOT NULL DEFAULT 0"),),
}

# v9 新增的两列：批次存原卷页面图清单，条目存它来自第几页。
# 版本号已是 9、库却还是 v8 形状的半成品，也走同一个补列分支。
_PAGE_COLUMN_PATCHES = {
    "batches": (("page_assets_json", "TEXT NOT NULL DEFAULT '[]'"),
                ("scan_batch", "INTEGER NOT NULL DEFAULT 0")),
    "pending_questions": (("page_no", "INTEGER NOT NULL DEFAULT 1"),),
}


_DEDUPE_TABLES = ("dedupe_scans", "dedupe_findings")
# 重题池两张表（军令 #32 · S4）与上面两张同属「本轮新长出来的表」：
# 版本号已是最新、表却还没建的半成品库，靠同一个补建分支收口。
_POOL_TABLES = ("duplicate_pool", "pool_actions")


def _ensure_dedupe_columns(con: sqlite3.Connection) -> None:
    """``PRAGMA table_info`` 逐表探一次，缺列才 ``ALTER TABLE ADD COLUMN``。

    只补列、不动任何一行、不删任何一张表：库里已有的初查结论原样保留。
    全是读 + 至多两条补列语句，缺省时零写入，不抢 WAL 写锁。
    """
    names = _table_names(con)
    if not set(_DEDUPE_TABLES + _POOL_TABLES) <= names:
        # 表整个不存在（开发期拿半成品库跑过）：把 _SCHEMA 里那两句
        # ``CREATE TABLE IF NOT EXISTS`` 补上——全是 IF NOT EXISTS，已有对象一律不动。
        for statement in _SCHEMA.strip().split(";"):
            text = statement.strip()
            if text:
                con.execute(text)
        con.commit()
        return
    patched = False
    for patches_by_table in (_DEDUPE_COLUMN_PATCHES, _PAGE_COLUMN_PATCHES):
        for table, patches in patches_by_table.items():
            if table not in names:
                continue
            have = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
            for column, ddl in patches:
                if column in have:
                    continue
                con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                patched = True
    if patched:
        con.commit()


def _ensure_schema(con: sqlite3.Connection) -> None:
    version = int(con.execute("PRAGMA user_version").fetchone()[0])
    if version > SCHEMA_VERSION:
        raise PendingError(
            f"中转站结构版本 {version} 高于程序支持的 {SCHEMA_VERSION}，请升级程序或恢复备份。"
        )
    if version == SCHEMA_VERSION:
        # 结构已经是最新：连接只做读，绝不因为「每次连接都建表/播种」而在
        # 别人持有写锁时再抢一把写锁（WAL 下照样会 BUSY）。
        # 唯一例外是 dedupe 那两张**本轮新建**的表：7 版还没发出去，机器上可能
        # 已经有一个「版本号写着 7、但表是开发期旧形状」的库（少 message /
        # similarity 两列）。这里只做一次 PRAGMA 探查、缺列才补，不缺就一句 DDL 都不发。
        _ensure_dedupe_columns(con)
        return
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
    if version < 3:
        _migrate_v2_columns(con)
    if version < 4:
        _migrate_v3_sequence(con)
    if version < 5:
        _migrate_v4_dictionary(con)
    if version < 6:
        _migrate_v5_pinyin(con)
    if version < 9:
        _migrate_v8_page_images(con)
    if version < 10:
        _migrate_v9_scan_batch(con)
    _seed_dictionary(con)
    # 次序号的索引必须等迁移把列补上再建：
    # 老库里还没有 seq 这一列，先建索引就是一句「no such column: seq」，
    # 整个服务起不来。
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_pending_questions_seq"
        " ON pending_questions (batch_id, seq ASC)"
    )
    if version != SCHEMA_VERSION:
        con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.commit()


def _seed_dictionary(con: sqlite3.Connection) -> None:
    """字典基线：11 个主场景与带权重的交叉标签只补不删。

    每次连接都``INSERT OR IGNORE``——老师删过的标签不会复活，老师新增的标签
    也不会被冲掉；种子只在缺行时填上。
    """
    now = questions.now_iso()
    for order, (scene_id, name) in enumerate(SCENE_SEED, start=1):
        con.execute(
            "INSERT OR IGNORE INTO scene_types (id, name, sort_order, created_at)"
            " VALUES (?, ?, ?, ?)",
            (scene_id, name, order, now),
        )
    for name, scene, weight in EXAM_SEED:
        con.execute(
            "INSERT OR IGNORE INTO exam_types (name, scene, weight, pinyin, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (name, scene, weight, pinyin.initials(name), now),
        )


def _school_id_for_name(name: str) -> str:
    """迁移与旧客户端按名字建档时的稳定 ID：同一名字在哪台机器上都得到同一号。"""
    return "sch_" + hashlib.sha256(("school:" + name).encode("utf-8")).hexdigest()[:11]


def _migrate_v4_dictionary(con: sqlite3.Connection) -> None:
    """v4 → v5：把旧批次里的学校名搬进字典，题目只留 ID。

    旧 ``meta_json`` 的 ``schools`` 是校名数组。迁移时按名字建字典行（全称先按
    简称占位，老师之后可补全），再把 meta 改写成 ``school_ids``。老批次的
    标准名与可见标签都不动——升级不替老师改题。
    """
    now = questions.now_iso()
    from app.core.pending_meta import build_standard_name  # 元数据层建在本库之上，只能就地取

    rows = con.execute("SELECT batch_id, meta_json FROM batches").fetchall()
    for row in rows:
        try:
            meta = json.loads(row["meta_json"] or "{}")
        except (TypeError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        names = meta.pop("schools", None)
        if not isinstance(names, list):
            continue
        ids: list[str] = []
        for raw in names:
            name = str(raw or "").strip()[:120]
            if not name:
                continue
            existing = con.execute(
                "SELECT id FROM schools WHERE full_name = ? OR short_name = ? LIMIT 1",
                (name, name),
            ).fetchone()
            if existing is not None:
                school_id = str(existing["id"])
            else:
                school_id = _school_id_for_name(name)
                con.execute(
                    "INSERT OR IGNORE INTO schools"
                    " (id, full_name, short_name, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (school_id, name, name[:60], now, now),
                )
            if school_id not in ids:
                ids.append(school_id)
        meta["school_ids"] = ids
        meta.setdefault("name_mode", "auto")
        if not meta.get("standard_name"):
            meta["standard_name"] = build_standard_name(meta)
        con.execute(
            "UPDATE batches SET meta_json = ? WHERE batch_id = ?",
            (json.dumps(meta, ensure_ascii=False, separators=(",", ":")), row["batch_id"]),
        )


def _migrate_v5_pinyin(con: sqlite3.Connection) -> None:
    """v5 → v6：交叉标签补一列拼音首字母。

    老库只有标签原文，敲「J」找不到「集合」——补一列拼音首字母后，
    首字母就能当检索键用。已存在的标签按原文重算一遍，不动权重。
    """
    columns = {str(row["name"]) for row in con.execute("PRAGMA table_info(exam_types)")}
    if "pinyin" not in columns:
        con.execute("ALTER TABLE exam_types ADD COLUMN pinyin TEXT NOT NULL DEFAULT ''")
    rows = con.execute("SELECT DISTINCT name FROM exam_types").fetchall()
    for row in rows:
        name = str(row["name"])
        con.execute("UPDATE exam_types SET pinyin = ? WHERE name = ?",
                    (pinyin.initials(name), name))


def _migrate_v3_sequence(con: sqlite3.Connection) -> None:
    """v3 → v4：给每一批的题补上「录入次序」。

    老库没有次序列，拉出来只能按 ``created_at`` 排——而同一批题是**一次**写进去的，
    时间戳一模一样，于是只能退回按随机号排：老师看到的一批题是乱的。
    补号时按老口径（时间 + 号）排一遍，把当时的相对次序原样固化成次序号，
    老批次的顺序不会因为升级而变。
    """
    columns = {str(row["name"]) for row in con.execute("PRAGMA table_info(pending_questions)")}
    if "seq" not in columns:
        con.execute("ALTER TABLE pending_questions ADD COLUMN seq INTEGER NOT NULL DEFAULT 0")
    rows = con.execute(
        "SELECT id, batch_id FROM pending_questions"
        " ORDER BY batch_id ASC, created_at ASC, id ASC"
    ).fetchall()
    counters: dict[str, int] = {}
    for row in rows:
        batch_id = str(row["batch_id"])
        counters[batch_id] = counters.get(batch_id, 0) + 1
        con.execute("UPDATE pending_questions SET seq = ? WHERE id = ?",
                    (counters[batch_id], row["id"]))


def _migrate_v8_page_images(con: sqlite3.Connection) -> None:
    """v8 → v9：批次补原卷页面图清单，待审条目补页号。

    老批次没有页面图（它们本来就是没渲染过的），补空数组；老条目不知道来自
    哪一页，统一记第 1 页——页面图缺失时前端照旧显示「本题没有配图」，
    不拿第 1 页冒充某道题的原页。
    """
    for table, patches in _PAGE_COLUMN_PATCHES.items():
        have = {str(row[1]) for row in con.execute(f"PRAGMA table_info({table})")}
        for column, ddl in patches:
            if column not in have:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _migrate_v9_scan_batch(con: sqlite3.Connection) -> None:
    """v9 → v10：批次补「纯图片卷」标记，默认 0（老批次都按有文本处理）。"""
    have = {str(row[1]) for row in con.execute("PRAGMA table_info(batches)")}
    if "scan_batch" not in have:
        con.execute("ALTER TABLE batches ADD COLUMN scan_batch INTEGER NOT NULL DEFAULT 0")


def _migrate_v2_columns(con: sqlite3.Connection) -> None:
    """v2 → v3：批次补上「原文件名」「公共元数据」「已入库题号」三列，外加一张历史名单表。

    老批次没有原文件名（它们本来就不是从一份文件里来的），补空串即可；
    公共元数据补空对象，语义上就是「这一批还没预填过公共字段」；
    已入库题号补空数组，语义上就是「这一批还没有题进过主库」。
    """
    columns = {str(row["name"]) for row in con.execute("PRAGMA table_info(batches)")}
    if "source_name" not in columns:
        con.execute("ALTER TABLE batches ADD COLUMN source_name TEXT NOT NULL DEFAULT ''")
    if "meta_json" not in columns:
        con.execute("ALTER TABLE batches ADD COLUMN meta_json TEXT NOT NULL DEFAULT '{}'")
    if "approved_json" not in columns:
        con.execute("ALTER TABLE batches ADD COLUMN approved_json TEXT NOT NULL DEFAULT '[]'")


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


def local_now() -> datetime:
    return datetime.now(bank.LOCAL_TZ)


def batch_label(moment: Any) -> str:
    """批次的时间标签：``2026-11-01-星期日-15:30``。"""
    if isinstance(moment, str):
        try:
            moment = datetime.fromisoformat(moment)
        except ValueError:
            moment = local_now()
    return f"{moment:%Y-%m-%d}-{_WEEKDAYS[moment.weekday()]}-{moment:%H:%M}"


def new_pending_id() -> str:
    """签发中转站号段：``p_`` + 十六进制，与主库的 ``q_`` 号段永不相交。"""
    return PENDING_ID_PREFIX + secrets.token_hex(12)


def new_pool_id() -> str:
    """重题池号段（军令 #32 · S4）：``pool_`` 前缀，与 ``p_`` / ``q_`` 都不相交。"""
    return POOL_ID_PREFIX + secrets.token_hex(12)


def new_pool_action_id() -> str:
    """裁决记录号段：``pa_``，一条动作一号，回传单按它对账。"""
    return POOL_ACTION_ID_PREFIX + secrets.token_hex(12)


def next_batch_id(con: sqlite3.Connection) -> str:
    """批次号 ``B-001`` 起递增；删过批次也不回填——号段只增不复用。"""
    numbers = []
    for row in con.execute("SELECT batch_id FROM batches"):
        matched = BATCH_ID_RE.match(str(row["batch_id"] or ""))
        if matched:
            numbers.append(int(matched.group(0)[2:]))
    return "B-%03d" % ((max(numbers) + 1) if numbers else 1)
