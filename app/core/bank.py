"""插件题库服务：core-bank v0.6.3 七张关系表的读写适配层。

为什么放在底座（而不是插件 JS 里）：
- 插件运行在沙箱 iframe 中，拿不到文件系统与数据库（AGENTS §2）；
- 插件又需要真题列表、年级/难度过滤与组卷取数，因此由底座提供一条
  **受控 Host API**，插件经舞台消息协议申请数据，宿主代为查询并回传。

存储层是 7 张关系表（schools / topics / questions / topic_notes / sources /
question_topics / question_sources + bank_meta），对外仍然只给
``schemas/question.json`` 的标准文档结构。两者的差异全部在本模块抹平：

- ``extensions``：库内是有序数组 ``[{key,label,value}]``，契约是反向域名对象；
- ``answer``：库内是单个文本列（选择题存 "A,C"，非选择题存答案正文），契约是
  ``{kind, choice_keys/content, final}`` 对象；库内为 ``NULL`` 时出参**省略**该字段，
  不拿任何字母冒充答案；
- ``grade``：库内在 ``sources.grade``（主公 2026-10-23 裁定的落位），出参仍给顶层
  ``grade``，与 v0.6.2 的前端口径保持一致；
- ``taxonomy``：库内是 ``question_topics`` → ``topics`` 的物化路径树，出参按祖先名还原；
- ``images``：库内寄生在 ``extensions`` 的 core-bank 配图条目，出参回到顶层数组。

安全边界：
- 插件 ID 必须匹配反向域名；数据库文件路径由底座拼装，插件传不了任意路径；
- 全部过滤条件走参数绑定；表名、列名与层别码只从常量取，不接受插件输入；
- 单页最多 100 条，搜索词最多 100 字，避免一次把 456 题全倒进 iframe。

数据库随插件包分发：``plugins/<id>/bank/bank.db``。首次访问时由底座原子复制到
当前工作区的 ``data/banks/<id>.db``，之后只读取这份工作区副本。
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from app.core import bank_fts
from app.core import question_parser
from app.core import questions as question_contract
from app.core.config import settings
from app.core.contract import (
    CONTRACT_VERSION,
    normalize_contract_version,
    normalize_difficulty,
)

LOCAL_TZ = timezone(timedelta(hours=8))

PLUGIN_ID_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
MAX_PAGE_SIZE = 100
MAX_SEARCH = 100
MAX_BASKET = 200
MAX_SEARCH_NODES = 100
MAX_TOPIC_IDS = 8

# 保存时阻断的体检问题。这些坏法会让公式、图片引用在任何渲染/导出端只剩半截，
# 与其入库后再靠人眼发现，不如在保存当场报错；选项标号一类交给 Schema 判。
BLOCKING_ISSUES = frozenset({
    "empty_stem",
    "unbalanced_math",
    "unbalanced_braces",
    "unbalanced_left_right",
    "unmatched_environment",
    "remote_asset",
    "stray_html",
    "stray_html_answer",
    "solution_unbalanced_math",
    "solution_unbalanced_braces",
    "solution_unbalanced_left_right",
    "solution_unmatched_environment",
    "solution_remote_asset",
    "solution_stray_html",
})

SCHEMA_VERSION = 2

CHOICE_TYPES = ("single_choice", "multiple_choice")
# 存储层 questions.type 的 CHECK 只收这四类；契约里的 proof/unknown 一律如实拒绝，
# 不静默折叠成 solution（主公 2026-10-23 批复）。
STORAGE_TYPES = CHOICE_TYPES + ("fill_blank", "solution")
STORAGE_YEAR_MIN, STORAGE_YEAR_MAX = 1990, 2100

# topics.id = tp_ + 层别码 + 8 位十六进制摘要，定长 13；层别看前缀即知，不另设冗余列。
# 因为所有节点 id 都以 "tp_" 开头且等长，路径前缀用 LIKE 直配不会误伤兄弟子树。
TOPIC_ID_RE = re.compile(r"^tp_(bo|ch|se|kx)[0-9a-f]{8}$")
TEXTBOOK_ID_RE = re.compile(r"^tb_[0-9a-f]{8}$")
LAYER_TAXONOMY_KEY = {"bo": "textbook", "ch": "chapter", "se": "section", "kx": "topic"}

REQUIRED_TABLES = (
    "schools", "topics", "questions", "topic_notes", "sources",
    "question_topics", "question_sources", "bank_meta",
    # v0.8.2 多版本地基：教材版本登记表 + 「版本目录节点 → 考向」映射表。
    # 考向表本身仍是所有版本的并集，版本身份只活在这两张表里。
    "textbooks", "node_topic_map",
)

EXT_GRADE_KEY = "org.jiuzhang.core-bank.grade"
EXT_TAXONOMY_KEY = "org.jiuzhang.core-bank.taxonomy"
EXT_IMAGES_KEY = "org.jiuzhang.core-bank.images"
EXT_MIGRATION_KEY = "org.jiuzhang.core-bank.migration"
# 灌库时打下的审核标记；老师修完一条就清一条，全清完则整个迁移条目移出库
REVIEW_FLAGS = (
    "answer_absent",        # 选择题没有任何字母依据
    "answer_region_empty",  # 有【答案】标记但标记后是空白
    "type_manual_review",   # 通篇解析、无结论标记可依
    "structure_conflict",   # 选项内嵌正文，拆不出选项
    "topic_unmapped",       # 旧库没登记考向 id，只挂到节/章
    "needs_conclusion",     # 结论没单独成字段，整段解析当答案
    "solution_absent",      # 非选择题连答案正文都没有
)
# 库内 extensions 的展示名；同一键在数组态里必须带稳定 label
EXTENSION_LABELS = {
    EXT_GRADE_KEY: "年级",
    EXT_TAXONOMY_KEY: "教材章节",
    EXT_IMAGES_KEY: "配图",
    "org.jiuzhang.core-bank.option_columns": "选项列数",
    "org.jiuzhang.core-bank.tikz": "TikZ 原码",
    "org.jiuzhang.core-bank.migration": "迁移标记",
    "org.jiuzhang.editor": "录题插件私有数据",
    "org.jiuzhang.legacy": "旧库还原数据",
}
# 数组态讲究顺序：底座自己的条目在前，插件私有数据在后
EXTENSION_ORDER = tuple(EXTENSION_LABELS)

# 初始化只复制一次；同一进程内并发访问共享这把锁，避免半写文件被发现。
_seed_lock = threading.Lock()
# 同一个库文件只确认一次表结构，避免每次请求都翻 sqlite_master
_structure_cache: set[str] = set()


class BankError(Exception):
    pass


class BankNotFound(BankError):
    pass


class BankConflict(BankError):
    pass


def validate_plugin_id(plugin_id: str) -> str:
    if not isinstance(plugin_id, str) or PLUGIN_ID_RE.fullmatch(plugin_id) is None:
        raise BankError("插件 ID 非法")
    return plugin_id


def bank_db_path(plugin_id: str, *, create: bool = True) -> Path:
    plugin_id = validate_plugin_id(plugin_id)
    path = Path(settings.data_dir) / "banks" / f"{plugin_id}.db"
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _seed_path(plugin_id: str) -> Path:
    return Path(settings.plugins_dir) / plugin_id / "bank" / "bank.db"


def _schema_path(plugin_id: str) -> Path:
    """冻结表结构的唯一事实来源：插件包里的 bank/schema.sql。"""
    return Path(settings.plugins_dir) / plugin_id / "bank" / "schema.sql"


def _upgrade_if_older(plugin_id: str, path: Path) -> None:
    """结构版本落后就地升级；不像 core-bank 的库一律放行给 connect 去报标准错。

    这里绝不抢 ``_check_structure`` 的判词：宽表库、缺表库都有各自指向具体出路的
    人话提示（见 ``test_wide_table_database_is_rejected_with_actionable_message``），
    升级器插一句「不是可升级的结构」反而把那条更管用的提示盖掉了。
    """
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10.0)
    except sqlite3.Error:
        return
    try:
        version = int(con.execute("PRAGMA user_version").fetchone()[0])
        names = {row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )}
    except sqlite3.Error:
        return
    finally:
        con.close()
    if version < 0 or version >= SCHEMA_VERSION:
        return
    if "bank_questions" in names or "topics" not in names:
        return          # 宽表 / 根本不是 core-bank：交给结构守卫如实报
    upgrade_structure(plugin_id, path)


def ensure_bank(plugin_id: str) -> Path:
    """确保当前工作区的题库存在。

    纯净发版口径（ADR-003）：底座**不再随包携带真题库**。
    - default 工作区（本机开发）：从插件包自带的 ``bank/bank.db`` 种子原子复制——
      本机那颗 456 题的种子只活在本地磁盘（已从 git 与发行包剔除），一启动就能看到题。
      种子也不在时（纯净克隆 / 首次发布环境）退回用 ``schema.sql`` 建**空库**，不报错。
    - 其它工作区（用户在工作区下拉里新建的）：一律建**空库**，绝不把 default 的种子
      复制过去——新库就该从白纸开始录题。
    """
    plugin_id = validate_plugin_id(plugin_id)
    path = bank_db_path(plugin_id)
    if path.is_file() and path.stat().st_size > 0:
        # 老库（v0.6.3 七表）就地升级到 v0.8.2 多版本地基：用户不该为升级去跑脚本，
        # 但也不能静默改数据——升级自带 .pre-v082.bak 备份与整事务回滚。
        _upgrade_if_older(plugin_id, path)
        return path

    with _seed_lock:
        if path.is_file() and path.stat().st_size > 0:
            return path
        seed = _seed_path(plugin_id) if settings.workspace_id is None else None
        if seed is not None and seed.is_file():
            tmp = path.with_suffix(".db.part")
            try:
                shutil.copyfile(seed, tmp)
                tmp.replace(path)
            finally:
                if tmp.exists():
                    tmp.unlink()
            _seed_assets(plugin_id)
            return path
        # 无种子（非 default 工作区，或纯净环境缺种子）：按冻结 schema 建空库。
        init_bank(plugin_id, db_path=path)   # init_bank 内部会清空结构缓存
    return path


def _seed_assets(plugin_id: str) -> None:
    """把插件包 ``bank/assets`` 里的配图补进当前工作区 uploads/（只补缺失文件）。

    图片不是题目结构的一部分，但 schema 指向 ``/static/uploads/``；插件要能在
    另一台机器上“装上就有图”，随包的图必须由底座在首次建库时落位。
    """
    source = Path(settings.plugins_dir) / plugin_id / "bank" / "assets"
    if not source.is_dir():
        return
    target_dir = Path(settings.uploads_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if not item.is_file() or item.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            continue
        target = target_dir / item.name
        if target.is_file():
            continue
        try:
            shutil.copyfile(item, target)
        except OSError:
            # 单张图坏了不阻断题库读取；题目里会显示缺图占位
            continue


def _check_structure(con: sqlite3.Connection, plugin_id: str, path: Path) -> None:
    """确认打开的是 7 张关系表；v0.6.2 宽表与缺表都报可读错误，不静默读空。"""
    names = sorted(
        row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    )
    key = f"{path.resolve()}|{len(names)}|{'questions' in names}"
    if key in _structure_cache:
        return
    if "bank_questions" in names and "questions" not in names:
        raise BankError(
            f"题库 {plugin_id} 仍是 v0.6.2 的 bank_questions 宽表结构。"
            f"请把 plugins/{plugin_id}/bank/bank.db 换成 v0.6.3 的 7 张关系表库"
            "（tools/migrate_bank_v063.py --promote）。"
        )
    missing = [table for table in REQUIRED_TABLES if table not in names]
    if missing:
        raise BankError(f"题库 {plugin_id} 缺表：{'、'.join(missing)}")
    _structure_cache.add(key)


def connect(plugin_id: str) -> sqlite3.Connection:
    path = ensure_bank(plugin_id)
    con = sqlite3.connect(path, timeout=10.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    try:
        _check_structure(con, plugin_id, path)
    except BaseException:
        # 结构不合就拒绝打开：此时必须收回句柄，否则 Windows 下库文件会被占用
        con.close()
        raise
    return con


def init_bank(plugin_id: str, db_path: Path | None = None) -> Path:
    """按插件包冻结的 schema.sql 建一份空题库（迁移脚本与测试共用）。"""
    path = db_path or bank_db_path(plugin_id)
    schema = _schema_path(plugin_id)
    if not schema.is_file():
        raise BankNotFound(f"缺少表结构定义：{schema}")
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10.0)
    try:
        try:
            con.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error:
            pass
        con.executescript(schema.read_text(encoding="utf-8"))
        version = int(con.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise BankError(
                f"题库结构版本 {version} 高于程序支持的 {SCHEMA_VERSION}，请升级底座。"
            )
        con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        con.commit()
    finally:
        con.close()
    _structure_cache.clear()
    return path


def _now() -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


# ---------- v0.8.2 结构升级：考向并集 + 教材版本映射 ----------
# 现网只有人教A版一份数据，但地基必须先立住：考向（tp_kx）不绑版本、是各版本并集，
# 版本身份只活在 textbooks / node_topic_map 两张表里。老库首启就地升级到 v2，
# 升级前落 .pre-v082.bak 备份，自检不过整事务回滚——绝不留半套结构。
V082_TEXTBOOK_NAME = "人教A版"
V082_TOPICS_DDL = """
CREATE TABLE topics_new (
    id           TEXT    NOT NULL,
    parent_id    TEXT    NULL,
    textbook_id  TEXT    NULL,
    name         TEXT    NOT NULL,
    path         TEXT    NOT NULL,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    status       TEXT    NOT NULL DEFAULT 'active',
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL,
    CONSTRAINT pk_topics        PRIMARY KEY (id),
    CONSTRAINT ck_topics_id     CHECK (length(id) = 13 AND substr(id, 1, 5) IN ('tp_bo', 'tp_ch', 'tp_se', 'tp_kx')
                                               AND substr(id, 6, 8) GLOB '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'),
    CONSTRAINT ck_topics_name   CHECK (length(trim(name)) BETWEEN 1 AND 120),
    CONSTRAINT ck_topics_path   CHECK (path GLOB 'tp_*' AND length(path) <= 512),
    CONSTRAINT ck_topics_status CHECK (status IN ('active', 'archived', 'draft')),
    CONSTRAINT ck_topics_sort   CHECK (sort_order >= 0),
    CONSTRAINT ck_topics_acyclic CHECK (parent_id IS NULL OR parent_id <> id),
    CONSTRAINT ck_topics_textbook CHECK (textbook_id IS NULL OR (textbook_id GLOB 'tb_*' AND length(textbook_id) = 11)),
    CONSTRAINT ck_topics_taxonomy_shared CHECK (substr(id, 1, 5) <> 'tp_kx' OR textbook_id IS NULL),
    CONSTRAINT fk_topics_parent FOREIGN KEY (parent_id) REFERENCES topics_new (id) ON DELETE CASCADE
)
"""
V082_TOPICS_INDEXES = (
    "CREATE UNIQUE INDEX uq_topics_path ON topics (path)",
    "CREATE UNIQUE INDEX uq_topics_sibling ON topics (parent_id, sort_order)",
    "CREATE INDEX idx_topics_parent_id ON topics (parent_id)",
    "CREATE INDEX idx_topics_name ON topics (name)",
    "CREATE INDEX idx_topics_textbook ON topics (textbook_id)",
)
# 索引在这里显式列出（与 schema.sql 逐条对齐）而不是从文本里猜边界：
# 迁移库与新建库的结构必须完全一致，靠解析注释切段迟早切错。
V082_NEW_TABLES = ("textbooks", "node_topic_map")
V082_NEW_TABLE_INDEXES = {
    "textbooks": (
        "CREATE UNIQUE INDEX uq_textbooks_name ON textbooks (name)",
        "CREATE UNIQUE INDEX uq_textbooks_default ON textbooks (is_default) WHERE is_default = 1",
    ),
    "node_topic_map": (
        "CREATE INDEX idx_ntm_textbook ON node_topic_map (textbook_id, outline_node_id)",
        "CREATE INDEX idx_ntm_topic ON node_topic_map (topic_id)",
    ),
}


def textbook_id_of(name: str) -> str:
    return "tb_" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]


def _new_table_ddl(plugin_id: str, name: str) -> str:
    """取冻结 schema.sql 里某张新表的 CREATE TABLE 段，再拼上本文件登记的索引。"""
    schema = _schema_path(plugin_id).read_text(encoding="utf-8")
    start = schema.index(f"CREATE TABLE {name} (")
    end = schema.index(");", start) + 2
    indexes = V082_NEW_TABLE_INDEXES.get(name)
    if indexes is None:
        raise BankError(f"没登记 {name} 的索引，拒绝建出一张缺索引的库")
    return schema[start:end] + "\n" + "\n".join(item.rstrip(";") + ";" for item in indexes)


def _v082_verify(con: sqlite3.Connection, expected_map: int, snapshot: dict[str, int]) -> None:
    """升级自检：行数、外键、完整性、并集不变量、映射可还原树、映射不静默丢行。"""
    problems: list[str] = []
    for table, count in snapshot.items():
        after = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if after != count:
            problems.append(f"{table} 行数 {count} → {after}")
    if con.execute("PRAGMA foreign_key_check").fetchall():
        problems.append("外键自检有违规")
    if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        problems.append("integrity_check 非 ok")
    bound = con.execute(
        "SELECT COUNT(*) FROM topics WHERE substr(id, 1, 5) = 'tp_kx' AND textbook_id IS NOT NULL"
    ).fetchone()[0]
    if bound:
        problems.append(f"{bound} 个考向被绑上版本，违反并集不变量")
    unreproducible = con.execute(
        """SELECT COUNT(*) FROM topics t WHERE substr(t.id, 1, 5) = 'tp_kx'
                 AND t.parent_id IS NOT NULL AND NOT EXISTS
           (SELECT 1 FROM node_topic_map m WHERE m.topic_id = t.id AND m.outline_node_id = t.parent_id)"""
    ).fetchone()[0]
    if unreproducible:
        problems.append(f"{unreproducible} 个考向的父子关系在映射表里还原不出来")
    actual = con.execute("SELECT COUNT(*) FROM node_topic_map").fetchone()[0]
    if actual != expected_map:
        problems.append(f"映射行只落 {actual} 条，期望 {expected_map} 条（有行被静默忽略）")
    if problems:
        raise BankError("；".join(problems))


def textbooks(plugin_id: str) -> list[dict[str, Any]]:
    """当前库里的教材版本清单（v0.8.2 多版本地基）。

    考向是全库并集、不绑版本；版本身份只在这张表与 node_topic_map 里。
    现网通常只有默认那一条（人教A版），第三方教材大纲导入后即在此并列多条。
    """
    con = connect(plugin_id)
    try:
        rows = con.execute(
            "SELECT id, name, publisher, edition, is_default FROM textbooks"
            " ORDER BY is_default DESC, name ASC"
        ).fetchall()
    finally:
        con.close()   # Windows 下漏句柄会把库文件占住，读函数一律显式收回
    return [dict(row) for row in rows]


def default_textbook_id(plugin_id: str) -> str:
    """库里登记为默认的教材版本；空库或没有默认标记时回空串。"""
    for item in textbooks(plugin_id):
        if item.get("is_default"):
            return str(item["id"])
    return ""


def upgrade_structure(plugin_id: str, path: Path | None = None) -> dict[str, Any]:
    """把 v0.6.3 七表库就地升级到 v0.8.2 多版本地基；已是 v2 直接返回。"""
    plugin_id = validate_plugin_id(plugin_id)
    db_path = path or bank_db_path(plugin_id)
    if not db_path.is_file():
        raise BankNotFound(f"题库不存在，无从升级：{db_path}")
    con = sqlite3.connect(db_path, timeout=30.0)
    try:
        version = int(con.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise BankError(f"题库结构版本 {version} 高于程序支持的 {SCHEMA_VERSION}，请升级底座。")
        names = {row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )}
        if version >= SCHEMA_VERSION and set(V082_NEW_TABLES) <= names:
            return {"upgraded": False, "user_version": version, "map_rows": 0}
        if "topics" not in names:
            raise BankError(f"题库 {plugin_id} 没有 topics 表，不是可升级的 core-bank 结构。")

        backup = db_path.with_name(db_path.name + ".pre-v082.bak")
        if not backup.exists():
            shutil.copyfile(db_path, backup)

        con.execute("PRAGMA foreign_keys = OFF")
        con.execute("BEGIN IMMEDIATE")
        try:
            snapshot = {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        for table in ("topics", "question_topics", "topic_notes")}
            # topics 用「建新表 → 搬数据 → 改名」而不是 ALTER ADD COLUMN：
            # ALTER 加不上 CHECK，那样新建库有并集不变量、迁移库没有，一份代码面对两种结构。
            con.execute(V082_TOPICS_DDL)
            con.execute(
                """INSERT INTO topics_new (id, parent_id, textbook_id, name, path, sort_order,
                                           status, created_at, updated_at)
                   SELECT id, parent_id, NULL, name, path, sort_order, status, created_at, updated_at
                   FROM topics"""
            )
            con.execute("DROP TABLE topics")
            con.execute("ALTER TABLE topics_new RENAME TO topics")
            for ddl in V082_TOPICS_INDEXES:
                con.execute(ddl)

            names = {row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )}
            for table in V082_NEW_TABLES:
                if table not in names:
                    con.executescript(_new_table_ddl(plugin_id, table))

            tb_id = textbook_id_of(V082_TEXTBOOK_NAME)
            stamp = con.execute("SELECT COALESCE(MAX(updated_at), ?) FROM topics", (_now(),)).fetchone()[0]
            con.execute(
                """INSERT OR IGNORE INTO textbooks (id, name, publisher, edition, is_default,
                                                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, 1, ?, ?)""",
                (tb_id, V082_TEXTBOOK_NAME, "人民教育出版社", "2019 课标版", stamp, stamp),
            )
            con.execute(
                "UPDATE topics SET textbook_id = ? WHERE substr(id, 1, 5) IN ('tp_bo', 'tp_ch', 'tp_se')",
                (tb_id,),
            )
            expected = 0
            for topic_id, path_value, sort_order in con.execute(
                "SELECT id, path, sort_order FROM topics WHERE substr(id, 1, 5) = 'tp_kx' ORDER BY path"
            ).fetchall():
                # path 是 "/" 分隔的 id 链；链上除自己外都是该版本的目录节点
                ancestors = [node for node in path_value.split("/") if node and node != topic_id]
                expected += len(ancestors)
                con.executemany(
                    """INSERT OR IGNORE INTO node_topic_map
                       (outline_node_id, topic_id, textbook_id, sort_order, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    [(node, topic_id, tb_id, sort_order, stamp) for node in ancestors],
                )
            _v082_verify(con, expected, snapshot)
            con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            con.commit()
        except BaseException:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        _structure_cache.clear()
        return {"upgraded": True, "user_version": SCHEMA_VERSION,
                "map_rows": expected, "backup": backup.name}
    finally:
        con.close()


def _encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(raw: Any, default: Any) -> Any:
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like(term: str) -> str:
    return "%" + _escape_like(term) + "%"


def _placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))


# ---------------------------------------------------------------- extensions

def extensions_to_array(extensions: Any) -> list[dict[str, Any]]:
    """契约的对象态 → 库内的有序数组态 ``[{key,label,value}]``。"""
    if not isinstance(extensions, dict):
        return []

    def rank(key: str) -> tuple[int, str]:
        index = EXTENSION_ORDER.index(key) if key in EXTENSION_ORDER else len(EXTENSION_ORDER)
        return (index, key)

    return [
        {"key": key, "label": EXTENSION_LABELS.get(key, key), "value": value}
        for key, value in sorted(extensions.items(), key=lambda item: rank(item[0]))
    ]


def extensions_to_object(raw: Any) -> dict[str, Any]:
    """库内的数组态 → 契约的反向域名对象态；缺 key 的残条目直接丢弃。"""
    items = raw if isinstance(raw, list) else _decode(raw, [])
    result: dict[str, Any] = {}
    if not isinstance(items, list):
        return result
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("key"), str):
            result[item["key"]] = item.get("value")
    return result


def _extension_value(extensions: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = extensions.get(key)
    return value if isinstance(value, dict) else None


def _grade_from(extensions: dict[str, Any]) -> str:
    """年级的取值顺序：底座年级条目 → 录题插件 → 旧库还原。"""
    for key in (EXT_GRADE_KEY, "org.jiuzhang.editor", "org.jiuzhang.legacy"):
        entry = _extension_value(extensions, key)
        if entry and entry.get("grade"):
            return str(entry["grade"])[:20]
    return ""


# -------------------------------------------------------------------- answer

def answer_to_storage(answer: Any, question_type: str) -> str | None:
    """契约答案对象 → 库内单个文本列。

    选择题存字母串（``A,C``）；非选择题存答案正文（``content`` 优先，退回 ``final``）。
    答案形态（text/expression/proof）在存储层不分列，读回统一合成 text。
    """
    if not isinstance(answer, dict):
        return None
    if question_type in CHOICE_TYPES or answer.get("kind") == "choice":
        keys = [item for item in (answer.get("choice_keys") or []) if isinstance(item, str)]
        return ",".join(keys) or None
    body = answer.get("content") or answer.get("final")
    return str(body)[:20000] if body else None


def answer_from_storage(value: str | None, question_type: str) -> dict[str, Any] | None:
    """库内文本 → 契约答案对象；``NULL`` 返回 None，由调用方省略该字段。"""
    if not value:
        return None
    if question_type in CHOICE_TYPES:
        keys = [item for item in re.split(r"[,\s]+", value) if item]
        return {"kind": "choice", "choice_keys": keys, "final": ",".join(keys)}
    return {"kind": "text", "content": value, "final": value[:2000]}


# ---------------------------------------------------------------- 出参装配

def _topic_index(con: sqlite3.Connection, qids: list[str]) -> dict[str, list[dict[str, Any]]]:
    """一题的考向挂载，带物化路径上各级祖先名。"""
    if not qids:
        return {}
    rows = con.execute(
        "SELECT qt.question_id, t.id, t.name, t.path, qt.is_primary"
        " FROM question_topics qt JOIN topics t ON t.id = qt.topic_id"
        f" WHERE qt.question_id IN ({_placeholders(len(qids))})"
        " ORDER BY qt.is_primary DESC, qt.sort_order, t.name",
        qids,
    ).fetchall()
    linked: dict[str, list[dict[str, Any]]] = {}
    ancestor_ids: set[str] = set()
    for row in rows:
        item = dict(row)
        item["ancestor_ids"] = [part for part in row["path"].split("/") if part]
        linked.setdefault(row["question_id"], []).append(item)
        ancestor_ids.update(item["ancestor_ids"])
    names: dict[str, str] = {}
    if ancestor_ids:
        ids = sorted(ancestor_ids)
        for row in con.execute(
            f"SELECT id, name FROM topics WHERE id IN ({_placeholders(len(ids))})", ids
        ):
            names[row["id"]] = row["name"]
    for items in linked.values():
        for item in items:
            item["ancestors"] = [
                {"id": pid, "name": names.get(pid, "")} for pid in item["ancestor_ids"]
            ]
    return linked


def _source_index(con: sqlite3.Connection, qids: list[str]) -> dict[str, dict[str, Any]]:
    """一题的首个来源（含学校与年级）；一题多来源的完整展开属于 P1 录题升级范围。"""
    if not qids:
        return {}
    rows = con.execute(
        "SELECT qs.question_id, qs.question_no, s.paper_name, s.year, s.exam_type, s.grade,"
        " sc.full_name, sc.short_name, sc.city, sc.province"
        " FROM question_sources qs"
        " JOIN sources s ON s.id = qs.source_id"
        " LEFT JOIN schools sc ON sc.id = s.school_id"
        f" WHERE qs.question_id IN ({_placeholders(len(qids))})"
        " ORDER BY qs.id",
        qids,
    ).fetchall()
    picked: dict[str, dict[str, Any]] = {}
    for row in rows:
        picked.setdefault(row["question_id"], dict(row))
    return picked


def _taxonomy_from_link(link: dict[str, Any]) -> dict[str, Any]:
    taxonomy: dict[str, Any] = {}
    for node in link["ancestors"]:
        field = LAYER_TAXONOMY_KEY.get(node["id"][3:5])
        if field and node["name"]:
            taxonomy[field] = node["name"]
    taxonomy["topic_ids"] = [link["id"]]
    return taxonomy


def _document_from(row: sqlite3.Row, link: dict[str, Any] | None,
                   source: dict[str, Any] | None) -> dict[str, Any]:
    extensions = extensions_to_object(row["extensions"])
    document: dict[str, Any] = {
        "schema_version": CONTRACT_VERSION,
        "id": row["id"],
        "type": row["type"],
        "stem": row["stem"],
        "difficulty": row["difficulty"],
    }
    options = _decode(row["options"], [])
    if options:
        document["options"] = options
    answer = answer_from_storage(row["answer"], row["type"])
    if answer:
        document["answer"] = answer
    if row["solution"]:
        document["solution"] = row["solution"]

    if link:
        document["taxonomy"] = _taxonomy_from_link(link)
    else:
        legacy_tax = _extension_value(extensions, EXT_TAXONOMY_KEY)
        if legacy_tax:
            document["taxonomy"] = {
                key: value
                for key, value in legacy_tax.items()
                if key in ("textbook", "chapter", "section", "topic") and value
            }
    images = _extension_value(extensions, EXT_IMAGES_KEY)
    if images and images.get("images"):
        document["images"] = images["images"]

    grade = ""
    if source:
        grade = source["grade"] or ""
        document["source"] = {
            "paper_title": source["paper_name"],
            "question_no": source["question_no"],
        }
        if source["year"] is not None:
            document["source"]["year"] = int(source["year"])
        for field, column in (("exam_type", "exam_type"), ("school", "short_name"),
                              ("region", "city")):
            value = source.get(column)
            if value:
                document["source"][field] = value
    if not grade:
        grade = _grade_from(extensions)
    if grade:
        document["grade"] = grade
    document["extensions"] = extensions
    document["meta"] = {
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "revision": 1,
        "status": "published",
    }
    return document


def _assemble(con: sqlite3.Connection, rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    row_list = list(rows)
    qids = [row["id"] for row in row_list]
    topics_by_qid = _topic_index(con, qids)
    sources_by_qid = _source_index(con, qids)
    return [
        _document_from(row, (topics_by_qid.get(row["id"]) or [None])[0], sources_by_qid.get(row["id"]))
        for row in row_list
    ]


# ---------------------------------------------------------------- 过滤与读取

def _flag_clause(flag: str) -> tuple[str, list[Any]]:
    """按灌库审核标记筛题；``any`` 表示「带任何未清标记」，即整条待审队列。"""
    if flag == "any":
        return (
            "EXISTS (SELECT 1 FROM json_each(q.extensions) e"
            " WHERE json_extract(e.value, '$.key') = ?"
            " AND json_array_length(json_extract(e.value, '$.value.flags')) > 0)",
            [EXT_MIGRATION_KEY],
        )
    if flag not in REVIEW_FLAGS:
        raise BankError(f"未知审核标记 {flag!r}，只认 any/{'/'.join(REVIEW_FLAGS)}")
    return (
        "EXISTS (SELECT 1 FROM json_each(q.extensions) e"
        " WHERE json_extract(e.value, '$.key') = ?"
        " AND EXISTS (SELECT 1 FROM json_each(json_extract(e.value, '$.value.flags')) f"
        "             WHERE f.value = ?))",
        [EXT_MIGRATION_KEY, flag],
    )


# ---------------------------------------------------------------- 题干索引

def _fts_ready(con: sqlite3.Connection) -> bool:
    """确保 FTS5 索引存在且条数与主表一致；任何失败都让调用方退回 LIKE。

    懒重建只发生在读路径：索引是派生数据，丢了可以随时从 questions 重建，
    绝不能因为索引坏了让题库打不开。
    """
    if not bank_fts.available():
        return False
    try:
        bank_fts.ensure_schema(con)
        total = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        if int(bank_fts.doc_count(con)) != total:
            bank_fts.index_all(con, con.execute("SELECT id, stem FROM questions"))
        return True
    except (bank_fts.FtsUnavailable, sqlite3.DatabaseError):
        return False


def _fts_upsert(con: sqlite3.Connection, question_id: str, stem: str) -> None:
    if not bank_fts.available():
        return
    try:
        bank_fts.upsert(con, question_id, stem)
    except (bank_fts.FtsUnavailable, sqlite3.DatabaseError):
        pass


def _fts_remove(con: sqlite3.Connection, question_id: str) -> None:
    if not bank_fts.available():
        return
    try:
        bank_fts.remove(con, question_id)
    except (bank_fts.FtsUnavailable, sqlite3.DatabaseError):
        pass


def _fts_clear(con: sqlite3.Connection) -> None:
    if not bank_fts.available():
        return
    try:
        bank_fts.ensure_schema(con)
        con.execute(f"DELETE FROM {bank_fts.TABLE}")
    except (bank_fts.FtsUnavailable, sqlite3.DatabaseError):
        pass


def _build_where(
    *,
    grade: str = "",
    difficulty: str = "",
    question_type: str = "",
    chapter: str = "",
    textbook: str = "",
    search: str = "",
    flag: str = "",
    ids: Iterable[str] | None = None,
    fts: bool = False,
) -> tuple[str, list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    values = {
        "grade": str(grade or "").strip(),
        "difficulty": str(normalize_difficulty(difficulty) or "").strip(),
        "type": str(question_type or "").strip(),
        "chapter": str(chapter or "").strip(),
        "textbook": str(textbook or "").strip(),
    }
    if values["difficulty"] and values["difficulty"] != "全部":
        where.append("q.difficulty = ?")
        params.append(values["difficulty"][:8])
    if values["type"] and values["type"] != "全部":
        where.append("q.type = ?")
        params.append(values["type"][:32])
    if values["grade"] and values["grade"] != "全部":
        where.append(
            "EXISTS (SELECT 1 FROM question_sources qs"
            " JOIN sources s ON s.id = qs.source_id"
            " WHERE qs.question_id = q.id AND s.grade = ?)"
        )
        params.append(values["grade"][:20])
    for value, layer in ((values["chapter"], "tp_ch"), (values["textbook"], "tp_bo")):
        if value and value != "全部":
            where.append(
                "EXISTS (SELECT 1 FROM question_topics qt"
                " JOIN topics node ON node.id = qt.topic_id"
                " JOIN topics ancestor ON ancestor.path = node.path"
                " OR node.path LIKE ancestor.path || '/%'"
                f" WHERE qt.question_id = q.id AND substr(ancestor.id, 1, 5) = '{layer}'"
                " AND ancestor.name = ?)"
            )
            params.append(value[:64])
    term = str(search or "").strip()[:MAX_SEARCH]
    if term:
        if fts:
            where.append(
                f"(q.id IN (SELECT question_id FROM {bank_fts.TABLE}"
                f" WHERE {bank_fts.TABLE} MATCH ?) OR q.id = ?)"
            )
            params.extend([bank_fts.query_expression(term), term])
        else:
            where.append("(q.stem LIKE ? ESCAPE '\\' OR q.id = ?)")
            params.extend([_like(term), term])
    if flag:
        flag_sql, flag_params = _flag_clause(flag)
        where.append(flag_sql)
        params.extend(flag_params)
    if ids is not None:
        wanted = list(ids)
        if not wanted:
            return "WHERE 1 = 0", []
        where.append(f"q.id IN ({_placeholders(len(wanted))})")
        params.extend(wanted)
    clause = "WHERE " + " AND ".join(where) if where else ""
    return clause, params


def _topic_subtree_sql(con: sqlite3.Connection, topic: str) -> tuple[str, list[Any]]:
    """按大纲节点取题：点节/章/册时把它子树里的题一并捞出来。

    物化路径只有册节点等于自身 id，章/节/考向的 path 是「祖先 id/…/自身 id」，
    所以必须先把 path 查出来当前缀，不能拿 id 直接比。节点 id 由 TOPIC_ID_RE
    严格校验、不含 LIKE 通配符，直接拼前缀即可；节点 id 定长且都以 "tp_" 开头，
    前缀匹配不会误伤兄弟子树。
    """
    if TOPIC_ID_RE.fullmatch(topic) is None:
        raise BankError("考向节点 ID 非法")
    row = con.execute("SELECT path FROM topics WHERE id = ?", (topic,)).fetchone()
    if row is None:
        raise BankNotFound(f"大纲里没有节点 {topic}")
    return (
        "EXISTS (SELECT 1 FROM question_topics qt JOIN topics node ON node.id = qt.topic_id"
        " WHERE qt.question_id = q.id AND (node.path = ? OR node.path LIKE ?))",
        [row["path"], row["path"] + "/%"],
    )


def list_questions(
    plugin_id: str,
    *,
    grade: str = "",
    difficulty: str = "",
    question_type: str = "",
    chapter: str = "",
    textbook: str = "",
    topic: str = "",
    search: str = "",
    flag: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
    con = connect(plugin_id)
    try:
        use_fts = bool(str(search or "").strip()) and _fts_ready(con)
        clause, params = _build_where(
            grade=grade, difficulty=difficulty, question_type=question_type,
            chapter=chapter, textbook=textbook, search=search, flag=flag,
            fts=use_fts,
        )
        if topic:
            scope, scope_params = _topic_subtree_sql(con, topic)
            clause = f"{clause} AND {scope}" if clause else f"WHERE {scope}"
            params.extend(scope_params)
        total = int(con.execute(f"SELECT COUNT(*) FROM questions q {clause}", params).fetchone()[0])
        rows = con.execute(
            f"SELECT q.* FROM questions q {clause} ORDER BY q.id LIMIT ? OFFSET ?",
            [*params, page_size, (page - 1) * page_size],
        ).fetchall()
        return _assemble(con, rows), total
    finally:
        con.close()


def get_question(plugin_id: str, question_id: str) -> dict[str, Any]:
    if not isinstance(question_id, str) or not question_id.startswith("q_"):
        raise BankNotFound("题目 ID 非法")
    con = connect(plugin_id)
    try:
        row = con.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        if row is None:
            raise BankNotFound(f"题库中没有题目 {question_id}")
        return _assemble(con, [row])[0]
    finally:
        con.close()


def get_many(plugin_id: str, ids: Iterable[str]) -> list[dict[str, Any]]:
    wanted = [item for item in ids if isinstance(item, str) and item.startswith("q_")][:MAX_BASKET]
    if not wanted:
        return []
    con = connect(plugin_id)
    try:
        rows = con.execute(
            f"SELECT * FROM questions WHERE id IN ({_placeholders(len(wanted))})", wanted
        ).fetchall()
        documents = _assemble(con, rows)
    finally:
        con.close()
    by_id = {document["id"]: document for document in documents}
    return [by_id[item] for item in wanted if item in by_id]


def random_question(
    plugin_id: str,
    *,
    grade: str = "",
    difficulty: str = "",
    question_type: str = "",
    chapter: str = "",
    textbook: str = "",
    topic: str = "",
    search: str = "",
) -> dict[str, Any] | None:
    clause, params = "", []
    con = connect(plugin_id)
    try:
        clause, params = _build_where(
            grade=grade, difficulty=difficulty, question_type=question_type,
            chapter=chapter, textbook=textbook, search=search,
            fts=bool(str(search or "").strip()) and _fts_ready(con),
        )
        if topic:
            scope, scope_params = _topic_subtree_sql(con, topic)
            clause = f"{clause} AND {scope}" if clause else f"WHERE {scope}"
            params.extend(scope_params)
        row = con.execute(
            f"SELECT q.* FROM questions q {clause} ORDER BY RANDOM() LIMIT 1", params
        ).fetchone()
        if row is None:
            return None
        return _assemble(con, [row])[0]
    finally:
        con.close()


def _grouped_counts(con: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    return [
        {"name": row["name"], "count": int(row["count"]), "id": row["id"]}
        for row in con.execute(sql, params)
    ]


def stats(plugin_id: str) -> dict[str, Any]:
    """出参键名与 v0.6.2 一致（total/grades/difficulties/types/chapters/textbooks）。"""
    con = connect(plugin_id)
    try:
        total = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])

        def column_grouped(column: str, limit: int) -> list[dict[str, Any]]:
            return _grouped_counts(
                con,
                f"SELECT '' AS id, {column} AS name, COUNT(*) AS count FROM questions"
                f" GROUP BY {column} ORDER BY count DESC, name ASC LIMIT ?",
                (limit,),
            )

        grades = _grouped_counts(
            con,
            "SELECT '' AS id, s.grade AS name, COUNT(DISTINCT qs.question_id) AS count"
            " FROM question_sources qs JOIN sources s ON s.id = qs.source_id"
            " WHERE s.grade <> '' GROUP BY s.grade ORDER BY count DESC, name ASC LIMIT 40",
        )
        # 大纲层的题量是子树之和：题目只挂在末级节点上
        outline = (
            "SELECT ancestor.id AS id, ancestor.name AS name,"
            " COUNT(DISTINCT qt.question_id) AS count"
            " FROM topics ancestor"
            " LEFT JOIN topics descendant ON descendant.path LIKE ancestor.path || '/%'"
            " LEFT JOIN question_topics qt ON qt.topic_id = descendant.id"
            " WHERE substr(ancestor.id, 1, 5) = ?"
            " GROUP BY ancestor.id ORDER BY count DESC, name ASC LIMIT ?"
        )
        return {
            "total": total,
            "grades": grades,
            "difficulties": column_grouped("difficulty", 40),
            "types": column_grouped("type", 40),
            "chapters": _grouped_counts(con, outline, ("tp_ch", 30)),
            "textbooks": _grouped_counts(con, outline, ("tp_bo", 40)),
        }
    finally:
        con.close()


def topics(
    plugin_id: str, *, parent_id: str = "", search: str = "", textbook_id: str = ""
) -> list[dict[str, Any]]:
    """大纲树的一层子节点（懒展开用），带题量、是否有下级与教研笔记条数。

    ``textbook_id`` 只约束**根层与搜索结果**：册/章/节是版本目录节点，选哪版就看哪版；
    考向（``tp_kx``）是全库并集、``textbook_id IS NULL``，永远随版本一起出现。
    给定 ``parent_id`` 时不再过滤——父节点本身已确定了版本身份。
    """
    if textbook_id and TEXTBOOK_ID_RE.fullmatch(textbook_id) is None:
        raise BankError("教材版本 ID 非法")
    con = connect(plugin_id)
    try:
        term = str(search or "").strip()[:MAX_SEARCH]
        fields = "id, parent_id, textbook_id, name, path, sort_order, status"
        if term:
            if textbook_id:
                rows = con.execute(
                    f"SELECT {fields} FROM topics"
                    " WHERE name LIKE ? ESCAPE '\\'"
                    " AND (textbook_id = ? OR textbook_id IS NULL)"
                    " ORDER BY path LIMIT ?",
                    (_like(term), textbook_id, MAX_SEARCH_NODES),
                ).fetchall()
            else:
                rows = con.execute(
                    f"SELECT {fields} FROM topics"
                    " WHERE name LIKE ? ESCAPE '\\' ORDER BY path LIMIT ?",
                    (_like(term), MAX_SEARCH_NODES),
                ).fetchall()
        elif parent_id:
            if TOPIC_ID_RE.fullmatch(parent_id) is None:
                raise BankError("考向节点 ID 非法")
            rows = con.execute(
                f"SELECT {fields} FROM topics"
                " WHERE parent_id = ? ORDER BY sort_order, name",
                (parent_id,),
            ).fetchall()
        elif textbook_id:
            rows = con.execute(
                f"SELECT {fields} FROM topics"
                " WHERE parent_id IS NULL AND textbook_id = ? ORDER BY sort_order, name",
                (textbook_id,),
            ).fetchall()
        else:
            rows = con.execute(
                f"SELECT {fields} FROM topics"
                " WHERE parent_id IS NULL ORDER BY sort_order, name"
            ).fetchall()
        result = []
        for row in rows:
            children = int(con.execute(
                "SELECT COUNT(*) FROM topics WHERE parent_id = ?", (row["id"],)
            ).fetchone()[0])
            mounted = int(con.execute(
                "SELECT COUNT(DISTINCT qt.question_id) FROM question_topics qt"
                " JOIN topics descendant ON descendant.id = qt.topic_id"
                " WHERE descendant.path = ? OR descendant.path LIKE ?",
                (row["path"], row["path"] + "/%"),
            ).fetchone()[0])
            notes = int(con.execute(
                "SELECT COUNT(*) FROM topic_notes WHERE topic_id = ?", (row["id"],)
            ).fetchone()[0])
            result.append({
                "id": row["id"],
                "parent_id": row["parent_id"],
                "textbook_id": row["textbook_id"],
                "name": row["name"],
                "layer": LAYER_TAXONOMY_KEY.get(row["id"][3:5], ""),
                "path": row["path"],
                "sort_order": int(row["sort_order"]),
                "status": row["status"],
                "has_children": children > 0,
                "question_count": mounted,
                "note_count": notes,
            })
        return result
    finally:
        con.close()


def topic_notes(plugin_id: str, topic_id: str) -> dict[str, Any]:
    """考向节点上的教研笔记（method/pitfall/knowledge/insight）。"""
    if TOPIC_ID_RE.fullmatch(topic_id) is None:
        raise BankError("考向节点 ID 非法")
    con = connect(plugin_id)
    try:
        node = con.execute(
            "SELECT id, name, path, status FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if node is None:
            raise BankNotFound(f"大纲里没有节点 {topic_id}")
        rows = con.execute(
            "SELECT id, note_type, content, sort_order FROM topic_notes"
            " WHERE topic_id = ? ORDER BY note_type, sort_order",
            (topic_id,),
        ).fetchall()
        return {
            "topic": {
                "id": node["id"], "name": node["name"],
                "path": node["path"], "status": node["status"],
            },
            "notes": [
                {
                    "id": int(row["id"]),
                    "note_type": row["note_type"],
                    "content": row["content"],
                    "sort_order": int(row["sort_order"]),
                }
                for row in rows
            ],
        }
    finally:
        con.close()


def import_count(plugin_id: str) -> int:
    con = connect(plugin_id)
    try:
        return int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
    finally:
        con.close()


def metadata(plugin_id: str) -> dict[str, Any]:
    con = connect(plugin_id)
    try:
        rows = con.execute("SELECT key, value FROM bank_meta").fetchall()
    finally:
        con.close()
    result: dict[str, Any] = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except json.JSONDecodeError:
            result[row["key"]] = row["value"]
    return result


# ---------------------------------------------------------------- 写入路径

def _storage_ready(document: dict[str, Any]) -> dict[str, Any]:
    """写入前的口径归一：版本号与难度按契约 2.0 归一，超出存储题型的如实拒绝。"""
    document = dict(document)
    document["schema_version"] = normalize_contract_version(document.get("schema_version"))
    document["difficulty"] = normalize_difficulty(document.get("difficulty"))
    if document.get("type") not in STORAGE_TYPES:
        raise question_contract.QuestionValidationError([
            f"type: core-bank 存储层只收 {'/'.join(STORAGE_TYPES)}，"
            f"不收 {document.get('type')!r}（契约里的 proof/unknown 需要先在表结构上解冻）。"
        ])
    return document


def _grade_of(document: dict[str, Any]) -> str:
    return _grade_from(document.get("extensions") or {})


def _question_row(document: dict[str, Any], now: str) -> list[Any]:
    meta = document.get("meta") or {}
    created = str(meta.get("created_at") or now)
    updated = str(meta.get("updated_at") or created)
    if updated < created:  # ck_questions_updated：updated_at 不得早于 created_at
        updated = created

    extensions = dict(document.get("extensions") or {})
    grade = _grade_of(document)
    if grade:
        extensions[EXT_GRADE_KEY] = {"grade": grade}
    if document.get("images"):
        extensions[EXT_IMAGES_KEY] = {"images": document["images"]}
    taxonomy = document.get("taxonomy") or {}
    if not taxonomy.get("topic_ids"):
        names = {
            key: taxonomy[key]
            for key in ("textbook", "chapter", "section", "topic")
            if taxonomy.get(key)
        }
        if names:
            extensions[EXT_TAXONOMY_KEY] = names

    question_type = document["type"]
    # 存储层强制「无选项题型 options 必须是空数组」，因此非选择题不带选项
    options = (document.get("options") or []) if question_type in CHOICE_TYPES else []
    return [
        document["id"],
        question_type,
        document["stem"],
        _encode(options),
        answer_to_storage(document.get("answer"), question_type),
        document.get("solution") or None,
        _encode(extensions_to_array(extensions)),
        document["difficulty"],
        created,
        updated,
    ]


def _ensure_school(con: sqlite3.Connection, name: Any, now: str) -> str | None:
    """学校按全称/简称查档，查无则建；只登记办学实体本身，与哪张卷子无关。"""
    text = str(name or "").strip()
    if not text:
        return None
    row = con.execute(
        "SELECT id FROM schools WHERE full_name = ? OR short_name = ? LIMIT 1",
        (text[:120], text[:60]),
    ).fetchone()
    if row:
        return row[0]    # 位置取值：批量导入的连接不一定带 row_factory
    uid = "sch_" + hashlib.sha256(("school:" + text).encode("utf-8")).hexdigest()[:11]
    con.execute(
        "INSERT INTO schools (id, full_name, short_name, province, city, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid, text[:120], text[:60], "", "", now, now),
    )
    return uid


def _ensure_source(con: sqlite3.Connection, document: dict[str, Any], grade: str,
                   now: str) -> str | None:
    """来源表一张卷一行；拆不出的字段一律留 NULL，不猜。"""
    source = document.get("source") or {}
    paper = str(source.get("paper_title") or "").strip()[:200]
    if not paper:
        return None
    school_id = _ensure_school(con, source.get("school"), now)
    year = source.get("year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError) as exc:
            raise question_contract.QuestionValidationError(
                ["source.year: 年份必须是整数"]
            ) from exc
        if not STORAGE_YEAR_MIN <= year <= STORAGE_YEAR_MAX:
            raise question_contract.QuestionValidationError([
                f"source.year: 存储层只收 {STORAGE_YEAR_MIN}–{STORAGE_YEAR_MAX}，收到 {year}。"
            ])
    exam_type = str(source.get("exam_type") or "")[:40]
    key = "\x1f".join([paper, school_id or "", str(year or ""), exam_type, grade])
    uid = "src_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:11]
    con.execute(
        "INSERT OR IGNORE INTO sources"
        " (id, school_id, year, exam_type, grade, paper_name, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, school_id, year, exam_type, grade, paper, now, now),
    )
    return uid


def _link_topics(con: sqlite3.Connection, question_id: str, document: dict[str, Any],
                 now: str) -> None:
    """考点挂载只认大纲里真实存在的节点，查无即拒——不允许静默挂到别处。"""
    taxonomy = document.get("taxonomy") or {}
    for index, topic_id in enumerate([
        item for item in (taxonomy.get("topic_ids") or []) if isinstance(item, str)
    ][:MAX_TOPIC_IDS]):
        if TOPIC_ID_RE.fullmatch(topic_id) is None or con.execute(
            "SELECT 1 FROM topics WHERE id = ?", (topic_id,)
        ).fetchone() is None:
            raise question_contract.QuestionValidationError(
                [f"taxonomy.topic_ids: 大纲里没有节点 {topic_id!r}，请先把考向补进大纲树。"]
            )
        con.execute(
            "INSERT OR IGNORE INTO question_topics"
            " (question_id, topic_id, is_primary, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
            (question_id, topic_id, 1 if index == 0 else 0, index, now),
        )


def _link_source(con: sqlite3.Connection, document: dict[str, Any], now: str) -> None:
    grade = _grade_of(document)
    source_id = _ensure_source(con, document, grade, now)
    if not source_id:
        return
    source = document.get("source") or {}
    con.execute(
        "INSERT OR IGNORE INTO question_sources (question_id, source_id, question_no, created_at)"
        " VALUES (?, ?, ?, ?)",
        (document["id"], source_id, str(source.get("question_no") or "")[:20], now),
    )


def _intake_document(
    document: Any, *, strict: bool = True, baseline: Any = None
) -> dict[str, Any]:
    """录题入口统一清洗与防呆。

    ``strict`` 时只拦**本次新引入**的致命问题：``baseline`` 传改题前的旧文档，
    旧数据里本来就有的坏公式不挡老师改其它字段，但改坏了必须当场报错。
    批量导入走非严格清洗：旧题库的脏文本要归一，但不能因为个别题把整批吞掉。
    """
    cleaned, issues = question_parser.clean_question(document)
    if not isinstance(cleaned, dict):
        raise question_contract.QuestionValidationError(["(root): 请求体必须是 JSON 对象"])
    if strict:
        known: set[str] = set()
        if baseline is not None:
            known = {item["code"] for item in question_parser.clean_question(baseline)[1]}
        blocking = [
            item for item in issues
            if item["code"] in BLOCKING_ISSUES and item["code"] not in known
        ]
        if blocking:
            raise question_contract.QuestionValidationError(
                [f"{item['code']}: {item['message']}" for item in blocking]
            )
    return cleaned


def _write_document(con: sqlite3.Connection, document: dict[str, Any], now: str,
                    *, upsert: bool = False) -> None:
    row = _question_row(document, now)
    columns = ("type", "stem", "options", "answer", "solution", "extensions", "difficulty", "updated_at")
    if upsert:
        con.execute(
            "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
            " difficulty, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET " + ", ".join(f"{name} = excluded.{name}" for name in columns),
            row,
        )
    else:
        con.execute(
            "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
            " difficulty, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            row,
        )
    if upsert:
        # 重复导入必须幂等：整组重挂，否则 ON CONFLICT 之后挂载关系会越滚越多
        con.execute("DELETE FROM question_sources WHERE question_id = ?", (row[0],))
    _link_source(con, document, now)
    if upsert:
        _remount_topics(con, row[0], document.get("taxonomy") or {}, now)
    else:
        _link_topics(con, row[0], document, now)
    _fts_upsert(con, row[0], document["stem"])


def _wipe(con: sqlite3.Connection) -> None:
    """整库清空：只用于 reset，按常量表删，删完再开外键。"""
    con.execute("PRAGMA foreign_keys = OFF")
    for table in REQUIRED_TABLES:
        con.execute(f'DELETE FROM "{table}"')
    con.execute("PRAGMA foreign_keys = ON")
    _fts_clear(con)


def import_documents(
    plugin_id: str,
    documents: Iterable[dict[str, Any]],
    *,
    reset: bool = False,
    source_info: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    """批量写入题库（迁移、灌库与测试共用），单事务，失败整体回滚。"""
    path = db_path or bank_db_path(plugin_id)
    if reset and path.exists():
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(path) + suffix)
            if candidate.exists():
                candidate.unlink()
    # 冻结的 schema.sql 没有 IF NOT EXISTS：只有缺库（或明确要求重建）时才建，
    # 否则重放 DDL 必然炸在第二张表上。
    if not path.exists():
        init_bank(plugin_id, path)

    prepared = [_storage_ready(_intake_document(document, strict=False)) for document in documents]
    for document in prepared:
        question_contract.validate_question(document)
    con = sqlite3.connect(path, timeout=10.0)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA busy_timeout = 5000")
        con.execute("BEGIN IMMEDIATE")
        if reset:
            _wipe(con)
        now = _now()
        for document in prepared:
            _write_document(con, document, now, upsert=True)
        if source_info:
            for key, value in source_info.items():
                con.execute(
                    "INSERT INTO bank_meta (key, value) VALUES (?, ?)"
                    " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (str(key), json.dumps(value, ensure_ascii=False)),
                )
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return len(prepared)


def create_question(plugin_id: str, payload: Any) -> dict[str, Any]:
    """往指定插件题库新增一道题，返回按读路径装配后的标准结构。

    录题插件不碰数据库：它把表单整理成 ``schemas/question.json`` 结构，经宿主
    带一次性令牌转到这里。校验与底座 ``questions`` 表共用同一份 Schema，
    避免两份存储对同一道题各说各话。ID 由底座生成，插件不得指定历史 ID。
    """
    if isinstance(payload, dict) and "id" in payload:
        # 旧 ID 可能是历史题目或他人题目：一律作废，由底座重新签发
        payload = {key: value for key, value in payload.items() if key != "id"}
    payload = _intake_document(payload)
    document = question_contract.prepare_new_question(payload)
    question_contract.validate_question(document)
    document = _storage_ready(document)

    con = connect(plugin_id)
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            _write_document(con, document, _now())
        except sqlite3.IntegrityError as exc:
            raise BankConflict(f"题目 ID {document['id']} 已存在，请重试。") from exc
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return get_question(plugin_id, document["id"])


# ---------------------------------------------------------------- 数据看板

def dashboard_stats(plugin_id: str) -> dict[str, Any]:
    """看板四数 + 最近录入 5 题（只读，军令 #11 阶段一）。

    口径（写进 API_REFERENCE.md，别处不得另说一套）：
    - ``total_questions``：questions 表总行数；
    - ``today_added``：按 ``created_at`` 前 10 位（东八区本地日）等于今天的入库数；
    - ``pending_review``：仍带未清灌库审核标记的题数（与待审队列 ``flag=any`` 同判据）；
    - ``stored_total``：总题数 − 待审核，即已清审、正式落库的题数；
    - ``recent``：按 ``created_at`` 倒序的 5 条轻量摘要（题干截 80 字），不装配全文。
    """
    today = datetime.now(LOCAL_TZ).date().isoformat()
    con = connect(plugin_id)
    try:
        total = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        today_added = int(con.execute(
            "SELECT COUNT(*) FROM questions WHERE substr(created_at, 1, 10) = ?",
            (today,),
        ).fetchone()[0])
        pending_review = int(con.execute(
            "SELECT COUNT(*) FROM questions q WHERE EXISTS ("
            " SELECT 1 FROM json_each(q.extensions) e"
            " WHERE json_extract(e.value, '$.key') = ?"
            " AND json_array_length(json_extract(e.value, '$.value.flags')) > 0)",
            (EXT_MIGRATION_KEY,),
        ).fetchone()[0])
        rows = con.execute(
            "SELECT id, type, difficulty, stem, created_at FROM questions"
            " ORDER BY created_at DESC, id DESC LIMIT 5"
        ).fetchall()
        return {
            "date": today,
            "total_questions": total,
            "today_added": today_added,
            "pending_review": pending_review,
            "stored_total": total - pending_review,
            "recent": [
                {
                    "id": row["id"],
                    "type": row["type"],
                    "difficulty": row["difficulty"],
                    "stem": row["stem"][:80],
                    "created_at": row["created_at"],
                }
                for row in rows
            ],
        }
    finally:
        con.close()


def daily_counts(plugin_id: str, days: int = 365) -> list[dict[str, Any]]:
    """最近 ``days`` 天（含今天）的按日入库数，逐日补零，供热力图直接铺格子。"""
    days = max(1, min(int(days), 3650))
    start = datetime.now(LOCAL_TZ).date() - timedelta(days=days - 1)
    con = connect(plugin_id)
    try:
        rows = con.execute(
            "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count FROM questions"
            " WHERE substr(created_at, 1, 10) >= ? GROUP BY day",
            (start.isoformat(),),
        ).fetchall()
    finally:
        con.close()
    counts = {row["day"]: int(row["count"]) for row in rows}
    result: list[dict[str, Any]] = []
    for offset in range(days):
        day = (start + timedelta(days=offset)).isoformat()
        result.append({"date": day, "count": counts.get(day, 0)})
    return result


# ---------------------------------------------------------------- 人工审核

def review_summary(plugin_id: str) -> dict[str, Any]:
    """待审队列概览：按灌库标记分组计数，供「待审任务」页签打角标。"""
    con = connect(plugin_id)
    try:
        total = int(con.execute(
            "SELECT COUNT(*) FROM questions q WHERE EXISTS ("
            " SELECT 1 FROM json_each(q.extensions) e"
            " WHERE json_extract(e.value, '$.key') = ?"
            " AND json_array_length(json_extract(e.value, '$.value.flags')) > 0)",
            (EXT_MIGRATION_KEY,),
        ).fetchone()[0])
        rows = con.execute(
            "SELECT f.value AS name, COUNT(DISTINCT q.id) AS count"
            " FROM questions q, json_each(q.extensions) e,"
            " json_each(json_extract(e.value, '$.value.flags')) f"
            " WHERE json_extract(e.value, '$.key') = ?"
            " GROUP BY f.value ORDER BY count DESC, name ASC",
            (EXT_MIGRATION_KEY,),
        ).fetchall()
        return {
            "total": total,
            "flags": [{"name": row["name"], "count": int(row["count"])} for row in rows],
            "known_flags": list(REVIEW_FLAGS),
        }
    finally:
        con.close()


def _strip_flags(extensions: dict[str, Any], flags: Iterable[str]) -> dict[str, Any]:
    """清掉指定审核标记；一个不剩时连迁移条目一起移出库（不留空壳）。"""
    entry = _extension_value(extensions, EXT_MIGRATION_KEY)
    if not entry:
        return extensions
    remaining = [item for item in (entry.get("flags") or []) if item not in set(flags)]
    result = dict(extensions)
    if remaining:
        result[EXT_MIGRATION_KEY] = {**entry, "flags": remaining}
    else:
        result.pop(EXT_MIGRATION_KEY, None)
    return result


def update_question(plugin_id: str, question_id: str, patch: Any) -> dict[str, Any]:
    """按题回写可审字段并清除审核标记，合并后仍过同一份契约。

    只接受题目内容与 ``clear_flags``；``id`` / ``meta.created_at`` / 大纲与来源挂载
    不在此通道里改——那些属于录题插件的改题删题范围（P1），混进来会让审核页
    变成能悄悄挪动题目身份的旁路。
    """
    if not isinstance(patch, dict):
        raise question_contract.QuestionValidationError(["(root): 请求体必须是 JSON 对象"])
    current = get_question(plugin_id, question_id)
    document = dict(current)
    for key in ("stem", "options", "answer", "solution", "type", "difficulty", "grade", "taxonomy"):
        if key in patch:
            document[key] = patch[key]
    # 改题型时答案形态必须跟着走：选择题的字母改判成非选择题后，那串字母就是答案正文。
    # 留着 choice 形态会被契约的 kind 约束整条拒掉，老师反而改不动——这里保事实，不编内容。
    answer = document.get("answer")
    if isinstance(answer, dict) and answer.get("kind") == "choice" and document["type"] not in CHOICE_TYPES:
        letters = ",".join(item for item in (answer.get("choice_keys") or []) if isinstance(item, str))
        body = letters or str(answer.get("final") or "")
        document["answer"] = {"kind": "text", "content": body, "final": body[:2000]} if body else None
        if document["answer"] is None:
            document.pop("answer")
    document["schema_version"] = normalize_contract_version(document.get("schema_version"))
    document["difficulty"] = normalize_difficulty(document.get("difficulty"))
    document = _intake_document(document, baseline=current)

    clear = patch.get("clear_flags")
    clear = [clear] if isinstance(clear, str) else list(clear or [])
    unknown = [item for item in clear if item not in REVIEW_FLAGS]
    if unknown:
        raise question_contract.QuestionValidationError(
            [f"clear_flags: 未知审核标记 {', '.join(map(repr, unknown))}"]
        )
    extensions = _strip_flags(dict(current.get("extensions") or {}), clear)
    grade = str(document.pop("grade", "") or "")
    if grade:
        extensions[EXT_GRADE_KEY] = {"grade": grade}
    document["extensions"] = extensions
    document["meta"] = {**current["meta"], "updated_at": _now()}

    document = _storage_ready(document)
    question_contract.validate_question(document)

    row = _question_row(document, _now())
    remount = "taxonomy" in patch
    con = connect(plugin_id)
    try:
        con.execute("BEGIN IMMEDIATE")
        cursor = con.execute(
            "UPDATE questions SET type = ?, stem = ?, options = ?, answer = ?, solution = ?,"
            " extensions = ?, difficulty = ?, updated_at = ? WHERE id = ?",
            [row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[9], row[0]],
        )
        if cursor.rowcount == 0:
            raise BankNotFound(f"题库中没有题目 {question_id}")
        _fts_upsert(con, question_id, document["stem"])
        if remount:
            _remount_topics(con, question_id, document.get("taxonomy") or {}, _now())
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return get_question(plugin_id, question_id)


def delete_question(plugin_id: str, question_id: str) -> dict[str, Any]:
    """按题号删除一道题（录题插件删题专用，经宿主带令牌转发到这里）。

    只删这道题本身：``question_topics`` / ``question_sources`` 两张关联表靠
    ``ON DELETE CASCADE`` 自动摘干净，共享的来源、学校与大纲节点一律保留——
    删一题不该顺带拆掉别人的考点。删除前确认题目在本库存在，查无即 404。
    """
    if not isinstance(question_id, str) or not question_id.startswith("q_"):
        raise BankNotFound("题目 ID 非法")
    con = connect(plugin_id)
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            cursor = con.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            if cursor.rowcount == 0:
                raise BankNotFound(f"题库中没有题目 {question_id}")
            _fts_remove(con, question_id)
        except BaseException:
            con.rollback()
            raise
        con.commit()
    finally:
        con.close()
    return {"id": question_id, "deleted": True}


def _remount_topics(con: sqlite3.Connection, question_id: str, taxonomy: dict[str, Any],
                    now: str) -> None:
    """重挂考向：整组换掉 ``question_topics`` 的挂载关系（录题插件改题专用）。

    只认大纲里真实存在的节点；一个都不给就清空挂载——清空后这道题在树上查无，
    比挂在错误节点上诚实。
    """
    wanted = [item for item in (taxonomy.get("topic_ids") or []) if isinstance(item, str)]
    if len(wanted) > MAX_TOPIC_IDS:
        raise question_contract.QuestionValidationError(
            [f"taxonomy.topic_ids: 一题最多挂 {MAX_TOPIC_IDS} 个考向"]
        )
    for topic_id in wanted:
        if TOPIC_ID_RE.fullmatch(topic_id) is None or con.execute(
            "SELECT 1 FROM topics WHERE id = ?", (topic_id,)
        ).fetchone() is None:
            raise question_contract.QuestionValidationError(
                [f"taxonomy.topic_ids: 大纲里没有节点 {topic_id!r}，请先把考向补进大纲树。"]
            )
    con.execute("DELETE FROM question_topics WHERE question_id = ?", (question_id,))
    for index, topic_id in enumerate(wanted):
        con.execute(
            "INSERT INTO question_topics (question_id, topic_id, is_primary, sort_order, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (question_id, topic_id, 1 if index == 0 else 0, index, now),
        )
