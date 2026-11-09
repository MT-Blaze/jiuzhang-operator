"""core-bank 引擎的地基：库文件从哪来、结构怎么建怎么升、以及通用编解码原语。

七张关系表的建库与升级全在这一层：``ensure_bank`` 原子复制工作区库，
``_check_structure`` 守卫结构，``upgrade_structure`` 走 v0.8.2 升级（自检不过整事务回滚）。
常量与错误类型也是这一层的对外口径——表名、列名、层别码只从这里取，绝不接受插件输入。

上层按域分工：编解码 bank_codec.py、查询 bank_query.py、写入 bank_write.py、看板 bank_dashboard.py、审核 bank_review.py；对外入口仍是 ``app.core.bank``。
"""

from __future__ import annotations

from app.core import wire  # noqa: E402
import hashlib
import re
import shutil
import sqlite3
import threading
from app.core.bank_provider import DEFAULT_PROVIDER_ID, LEGACY_PROVIDER_IDS
from app.core.config import DEFAULT_WORKSPACE_ID, current_workspace_id, plugins_dir, settings
from app.legacy import LEGACY_SCHEMA_PATH
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


LOCAL_TZ = timezone(timedelta(hours=8))

PLUGIN_ID_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
MAX_PAGE_SIZE = 100
MAX_SEARCH = 100
MAX_BASKET = 200
MAX_SEARCH_NODES = 100
MAX_TOPIC_IDS = 8
# 批量装配的分片大小：一次 IN 查询最多带这么多 ID，避开 SQLite 单条语句的变量数上限。
ASSEMBLE_CHUNK = 100

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
EXT_TAGS_KEY = "org.jiuzhang.core-bank.tags"
EXT_MIGRATION_KEY = "org.jiuzhang.core-bank.migration"
# 一题可挂多份原卷（各自带原卷题号）；主来源仍走契约的 source，其余挂这里。
MAX_QUESTION_SOURCES = 8
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
    EXT_TAGS_KEY: "知识点标签",
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


class BankImportError(BankError):
    """批量导入被拒：逐题校验没过。``errors`` 逐题给出序号、ID 与报错。"""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(f"{len(errors)} 道题不符合 Schema，导入已整体回滚")


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
    return plugins_dir() / plugin_id / "bank" / "bank.db"


def _schema_path(plugin_id: str) -> Path:
    if plugin_id == DEFAULT_PROVIDER_ID:
        return LEGACY_SCHEMA_PATH
    return plugins_dir() / plugin_id / "bank" / "schema.sql"


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


def _legacy_bank_path(plugin_id: str) -> Path | None:
    """拆分前的 core-bank 物理库：只读来源，绝不清空、绝不改名。

    仅当新引擎自己被要求建库时启用；其它插件（含第三方 provider）一概不碰。
    """
    if plugin_id != DEFAULT_PROVIDER_ID:
        return None
    for legacy_id in LEGACY_PROVIDER_IDS:
        candidate = Path(settings.data_dir) / "banks" / f"{legacy_id}.db"
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def _copy_legacy_bank(plugin_id: str, path: Path) -> bool:
    """把旧库连同 WAL 一起复制成新引擎的库；返回是否复制成功。

    顺序：先把主库写成临时文件，再把 ``-wal`` / ``-journal`` 复制到最终名，
    最后原子替换主库。中途崩溃时主库还没出现，下次启动会重试；
    旧库本体只读打开，字节不动（军令 #20 数据兼容口径）。
    """
    source = _legacy_bank_path(plugin_id)
    if source is None:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    if tmp.exists():
        tmp.unlink()
    try:
        shutil.copyfile(source, tmp)
        for suffix in ("-wal", "-journal"):
            sidecar = Path(str(source) + suffix)
            target_sidecar = Path(str(path) + suffix)
            if sidecar.is_file():
                shutil.copyfile(sidecar, target_sidecar)
            elif target_sidecar.exists():
                target_sidecar.unlink()   # 上一轮失败留下的孤儿边车不带走
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return path.is_file() and path.stat().st_size > 0


def ensure_bank(plugin_id: str) -> Path:
    """确保当前工作区的题库存在。

    纯净发版口径（ADR-003）：底座**不再随包携带真题库**。
    - 升级过渡（军令 #20）：新引擎首次建库时，把旧 ``core-bank`` 物理库原样复制
      一份过来（旧文件保留），老师装完新版立刻能看到原来的题。
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
        if _copy_legacy_bank(plugin_id, path):
            _seed_assets(plugin_id)
            return path
        seed = _seed_path(plugin_id) if current_workspace_id() == DEFAULT_WORKSPACE_ID else None
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


def _asset_dirs(plugin_id: str) -> list[Path]:
    """配图来源：新插件自己的 ``bank/assets``，以及升级过渡期的旧 core-bank 目录。"""
    dirs = [plugins_dir() / plugin_id / "bank" / "assets"]
    if plugin_id == DEFAULT_PROVIDER_ID:
        dirs.extend(plugins_dir() / legacy / "bank" / "assets" for legacy in LEGACY_PROVIDER_IDS)
    return dirs


def _seed_assets(plugin_id: str) -> None:
    """把插件包 ``bank/assets`` 里的配图补进当前工作区 uploads/（只补缺失文件）。

    图片不是题目结构的一部分，但 schema 指向 ``/static/uploads/``；插件要能在
    另一台机器上“装上就有图”，随包的图必须由底座在首次建库时落位。
    升级过渡期旧插件的 assets 目录仍在就一并补上（同名文件以新插件为准）。
    """
    target_dir = Path(settings.uploads_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for source in _asset_dirs(plugin_id):
        if not source.is_dir():
            continue
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


def _new_table_ddl(plugin_id: str, name: str) -> list[str]:
    """取冻结 schema.sql 里某张新表的 CREATE TABLE 段，再拼上本文件登记的索引。

    返回**语句列表**而不是一整段脚本：调用方在升级事务里逐句 ``execute``（与本文件
    ``V082_TOPICS_INDEXES`` 同款写法）。``executescript`` 会隐式提交挂起的事务，
    升级尾部的自检失败就回滚不回去，留下半套库——口径见 ``app/core/db.py::run_statements``。
    """
    indexes = V082_NEW_TABLE_INDEXES.get(name)
    if indexes is None:
        raise BankError(f"没登记 {name} 的索引，拒绝建出一张缺索引的库")
    schema_path = _schema_path(plugin_id)
    if not schema_path.is_file():
        # 题库还在、插件包已被删时升级照样会走到这里：给 BankNotFound（404 与「缺定义」的人话），
        # 不许把裸 FileNotFoundError 抛成 500。与 init_bank 同一句判词。
        raise BankNotFound(f"缺少表结构定义：{schema_path}")
    schema = schema_path.read_text(encoding="utf-8")
    # 冻结的 schema.sql 排版被人动过时，str.index 会抛裸 ValueError 打成 500；
    # 这里换成 BankError，让调用方（升级/建库路径）拿到「哪张表取不到 DDL」的人话。
    marker = f"CREATE TABLE {name} ("
    start = schema.find(marker)
    if start < 0:
        raise BankError(f"冻结的 schema.sql 里找不到表 {name} 的 CREATE TABLE 段")
    end = schema.find(");", start)
    if end < 0:
        raise BankError(f"表 {name} 的 CREATE TABLE 段没有收尾的 );")
    end += 2
    return [schema[start:end], *(item.rstrip(";") + ";" for item in indexes)]


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
                    for statement in _new_table_ddl(plugin_id, table):
                        con.execute(statement)

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
    return wire.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(raw: Any, default: Any) -> Any:
    if raw is None or raw == "":
        return default
    try:
        return wire.loads(raw)
    except (wire.JSONDecodeError, TypeError):
        return default


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like(term: str) -> str:
    return "%" + _escape_like(term) + "%"


def _placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))
