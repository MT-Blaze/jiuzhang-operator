"""引擎库 v13 → v14：考试层级 / 考试主体字典落地，``exams`` 换成本地外键。

v14 把“考试主体”和“考试范围”从 ``exams`` 的两个文本/学校列里拆出来：
- 新增 ``dict_exam_levels``（7 个固定层级）与 ``dict_exam_orgs``（按需懒创建）；
- ``exams`` 去掉 ``exam_org_name`` / ``school_id``，改挂 ``region_id`` /
  ``exam_org_id`` / ``exam_level_id`` 三个真外键；
- ``dim_regions`` 放开 level=0，并补「全国」「东三省」两个宏观叶子节点。

历史脏数据按老师口径定点清洗：id=1 的「数学」不是主体，清空 org；
id=4 的「哈尔滨」是跨地市联考，地区落黑龙江、层级落跨地市联考。

迁移三律：版本化分派、备份优先（``.pre-v14.bak``，幂等）、整段单事务可回滚。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.bank_engine import regions
from app.bank_engine.exam_orgs import ensure_exam_org, infer_org_type
from app.bank_engine.seeds.exam_seed import EXAM_LEVEL_ROWS, EXAM_ORG_ROWS
from app.bank_engine.seeds.region_seed import MACRO_REGIONS

CREATE_REGIONS_V14 = """
CREATE TABLE dim_regions_v14 (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    code       TEXT NOT NULL UNIQUE,
    level      INTEGER NOT NULL CHECK (level IN (0, 1, 2)),
    parent_id  INTEGER REFERENCES dim_regions(id) ON DELETE RESTRICT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    CHECK (
        (level IN (0, 1) AND parent_id IS NULL)
        OR (level = 2 AND parent_id IS NOT NULL)
    )
)
"""

CREATE_EXAMS_V14 = """
CREATE TABLE exams_v14 (
    id            INTEGER PRIMARY KEY,
    year          INTEGER NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    region_id     INTEGER REFERENCES dim_regions(id) ON DELETE RESTRICT,
    exam_org_id   INTEGER REFERENCES dict_exam_orgs(id) ON DELETE RESTRICT,
    exam_level_id INTEGER REFERENCES dict_exam_levels(id) ON DELETE RESTRICT,
    month         INTEGER CHECK (month IS NULL OR month BETWEEN 1 AND 12),
    exam_type_id  INTEGER NOT NULL REFERENCES dict_exam_types(id) ON DELETE RESTRICT,
    mock_round    INTEGER CHECK (mock_round IS NULL OR mock_round BETWEEN 1 AND 10),
    grade_id      INTEGER NOT NULL REFERENCES dict_grades(id) ON DELETE RESTRICT,
    semester      TEXT CHECK (semester IS NULL OR semester IN ('上学期', '下学期')),
    subject_id    INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT
)
"""

CREATE_EXAMS_V13 = """
CREATE TABLE exams_v13 (
    id            INTEGER PRIMARY KEY,
    year          INTEGER NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    exam_org_name TEXT,
    school_id     INTEGER REFERENCES dim_schools(id) ON DELETE RESTRICT,
    month         INTEGER CHECK (month IS NULL OR month BETWEEN 1 AND 12),
    exam_type_id  INTEGER NOT NULL REFERENCES dict_exam_types(id) ON DELETE RESTRICT,
    mock_round    INTEGER CHECK (mock_round IS NULL OR mock_round BETWEEN 1 AND 10),
    grade_id      INTEGER NOT NULL REFERENCES dict_grades(id) ON DELETE RESTRICT,
    semester      TEXT CHECK (semester IS NULL OR semester IN ('上学期', '下学期')),
    subject_id    INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT
)
"""

_CREATE_LEVELS = """
CREATE TABLE IF NOT EXISTS dict_exam_levels (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    code       TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0
)
"""

_CREATE_ORGS = """
CREATE TABLE IF NOT EXISTS dict_exam_orgs (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    org_type   TEXT NOT NULL DEFAULT '其他'
               CHECK (org_type IN ('学校', '联考联盟', '地市级', '省级', '国家级', '区县级', '其他')),
    school_id  INTEGER REFERENCES dim_schools(id) ON DELETE RESTRICT
)
"""

# 脏数据定点：id=1 的「数学」是学科误填，id=4 的「哈尔滨」按跨地市联考落口径。
_CLEAR_ORG_ID = 1
_CROSS_CITY_ID = 4
_CROSS_CITY_REGION_CODE = "230000"

_LEVEL_BY_ORG_TYPE = {
    "国家级": "national",
    "联考联盟": "cross_province",
    "省级": "provincial",
    "地市级": "city",
    "区县级": "district",
    "学校": "school",
}


def backup_pre_v14(conn: sqlite3.Connection) -> Path | None:
    """迁移前备份：已存在则跳过（幂等）；内存库无文件可备，返回 None。"""
    row = conn.execute("PRAGMA database_list").fetchone()
    raw = str(row[2]) if row is not None else ""
    if not raw:
        return None
    path = Path(raw)
    target = path.with_name(path.name + ".pre-v14.bak")
    if target.exists():
        return target
    dest = sqlite3.connect(target, timeout=10.0)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return target


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(" + table + ")")}


def _value(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int | None:
    row = conn.execute(sql, params).fetchone()
    return None if row is None else int(row[0])


def _ensure_exam_dicts(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_LEVELS)
    conn.execute(_CREATE_ORGS)
    conn.executemany(
        "INSERT OR IGNORE INTO dict_exam_levels (id, name, code, sort_order) "
        "VALUES (?, ?, ?, ?)",
        EXAM_LEVEL_ROWS,
    )
    # 示例主体按名字补齐：现网可能已用 id=1 装了别的学校，不能按种子 id 硬插。
    for _seed_id, name, org_type, _school_id in EXAM_ORG_ROWS:
        ensure_exam_org(conn, name, org_type)
    # 现网旧库把「学业水平」「周测」写成了结业考试 / 小考：按 code 拉回契约名。
    conn.executemany(
        "UPDATE dict_exam_types SET name = ? WHERE code = ?",
        (("学业水平", "academic_proficiency"), ("周测", "weekly_test")),
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_dict_exam_orgs_school ON dict_exam_orgs (school_id)"
    )


def _regions_need_rebuild(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'dim_regions'"
    ).fetchone()
    body = str(row[0] if row is not None else "")
    return "IN (0, 1, 2)" not in body


def _rebuild_regions(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id, name, code, level, parent_id, sort_order FROM dim_regions ORDER BY id"
    ).fetchall()
    conn.execute(CREATE_REGIONS_V14)
    conn.executemany(
        "INSERT INTO dim_regions_v14 (id, name, code, level, parent_id, sort_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [tuple(row) for row in rows],
    )
    conn.execute("DROP TABLE dim_regions")
    conn.execute("ALTER TABLE dim_regions_v14 RENAME TO dim_regions")
    conn.execute(
        "CREATE UNIQUE INDEX ux_dim_regions_sibling_name "
        "ON dim_regions (COALESCE(parent_id, 0), name)"
    )
    conn.execute("CREATE INDEX ix_dim_regions_parent ON dim_regions (parent_id)")


def _ensure_macro_regions(conn: sqlite3.Connection) -> None:
    for name, code, order in MACRO_REGIONS:
        if _value(conn, "SELECT id FROM dim_regions WHERE code = ?", (code,)) is not None:
            continue
        conn.execute(
            "INSERT INTO dim_regions (name, code, level, parent_id, sort_order) "
            "VALUES (?, ?, 0, NULL, ?)",
            (name, code, order),
        )


def _level_id(conn: sqlite3.Connection, code: str | None) -> int | None:
    if not code:
        return None
    return _value(conn, "SELECT id FROM dict_exam_levels WHERE code = ?", (code,))


def _region_id_for(conn: sqlite3.Connection, org_text: str | None, school_id: int | None) -> int | None:
    if school_id is not None:
        row = conn.execute(
            "SELECT region_id FROM dim_schools WHERE id = ?", (school_id,)
        ).fetchone()
        if row is not None and row[0] is not None:
            return int(row[0])
    return regions.match_region_id(org_text)


def _infer_level(org_type: str) -> str | None:
    return _LEVEL_BY_ORG_TYPE.get(org_type)


def _link_school(conn: sqlite3.Connection, exam_id: int, school_id: int | None) -> None:
    if school_id is None:
        return
    conn.execute(
        "INSERT OR IGNORE INTO exam_school_map (exam_id, school_id) VALUES (?, ?)",
        (exam_id, int(school_id)),
    )


def _rebuild_exams(conn: sqlite3.Connection) -> None:
    columns = _columns(conn, "exams")
    legacy = "exam_org_name" in columns or "school_id" in columns
    if not legacy:
        return
    subject_names = {
        str(row[0]) for row in conn.execute("SELECT name FROM dict_subjects")
    }
    rows = conn.execute(
        "SELECT id, year, exam_org_name, school_id, month, exam_type_id, "
        "mock_round, grade_id, semester, subject_id FROM exams ORDER BY id"
    ).fetchall()
    mapped: list[tuple] = []
    for row in rows:
        exam_id = int(row["id"])
        org_text = str(row["exam_org_name"] or "").strip() or None
        school_id = None if row["school_id"] is None else int(row["school_id"])
        clear_org = exam_id == _CLEAR_ORG_ID or (org_text in subject_names)
        org_id = None
        org_type = None
        if org_text and not clear_org:
            org_type = infer_org_type(org_text)
            org_id = ensure_exam_org(conn, org_text, org_type)
        if exam_id == _CROSS_CITY_ID:
            region_id = _value(
                conn, "SELECT id FROM dim_regions WHERE code = ?", (_CROSS_CITY_REGION_CODE,)
            )
            level_id = _level_id(conn, "cross_city")
        else:
            region_id = _region_id_for(conn, org_text if not clear_org else None, school_id)
            level_id = _level_id(conn, _infer_level(org_type or ""))
        mapped.append(
            (
                exam_id,
                int(row["year"]),
                region_id,
                org_id,
                level_id,
                None if row["month"] is None else int(row["month"]),
                int(row["exam_type_id"]),
                None if row["mock_round"] is None else int(row["mock_round"]),
                int(row["grade_id"]),
                None if row["semester"] is None else str(row["semester"]),
                int(row["subject_id"]),
            )
        )
        _link_school(conn, exam_id, school_id)
    conn.execute(CREATE_EXAMS_V14)
    conn.executemany(
        "INSERT INTO exams_v14 "
        "(id, year, region_id, exam_org_id, exam_level_id, month, exam_type_id, "
        "mock_round, grade_id, semester, subject_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        mapped,
    )
    conn.execute("DROP TABLE exams")
    conn.execute("ALTER TABLE exams_v14 RENAME TO exams")
    _create_exam_indexes(conn)


def _create_exam_indexes(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_exams_lookup "
        "ON exams (year, month, subject_id, grade_id, exam_type_id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_exams_region ON exams (region_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_exams_org ON exams (exam_org_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_exams_level ON exams (exam_level_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_exam_school_map_school ON exam_school_map (school_id)"
    )


def _run(conn: sqlite3.Connection, body, version: int) -> None:
    previous_factory = conn.row_factory
    conn.isolation_level = None
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            body(conn)
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"v14 迁移后外键异常：{violations[:5]}")
            conn.execute("PRAGMA user_version = " + str(version))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.isolation_level = ""
        conn.row_factory = previous_factory


def _upgrade_body(conn: sqlite3.Connection) -> None:
    _ensure_exam_dicts(conn)
    if _regions_need_rebuild(conn):
        _rebuild_regions(conn)
    _ensure_macro_regions(conn)
    _rebuild_exams(conn)


def upgrade(conn: sqlite3.Connection) -> None:
    """v13 → v14：字典落地、区划放开宏观节点、``exams`` 换成三外键。幂等可重跑。"""
    backup_pre_v14(conn)
    _run(conn, _upgrade_body, 14)


def _rollback_exams(conn: sqlite3.Connection) -> None:
    columns = _columns(conn, "exams")
    if "exam_org_name" in columns:
        return
    rows = conn.execute(
        "SELECT id, year, exam_org_id, month, exam_type_id, mock_round, "
        "grade_id, semester, subject_id FROM exams ORDER BY id"
    ).fetchall()
    org_names: dict[int, str] = {
        int(row["id"]): str(row["name"])
        for row in conn.execute("SELECT id, name FROM dict_exam_orgs")
    }
    mapped: list[tuple] = []
    for row in rows:
        exam_id = int(row["id"])
        school_id = _value(
            conn, "SELECT school_id FROM exam_school_map WHERE exam_id = ? ORDER BY school_id LIMIT 1",
            (exam_id,),
        )
        org = org_names.get(int(row["exam_org_id"] or 0))
        mapped.append(
            (
                exam_id,
                int(row["year"]),
                org,
                school_id,
                None if row["month"] is None else int(row["month"]),
                int(row["exam_type_id"]),
                None if row["mock_round"] is None else int(row["mock_round"]),
                int(row["grade_id"]),
                None if row["semester"] is None else str(row["semester"]),
                int(row["subject_id"]),
            )
        )
    conn.execute(CREATE_EXAMS_V13)
    conn.executemany(
        "INSERT INTO exams_v13 "
        "(id, year, exam_org_name, school_id, month, exam_type_id, mock_round, "
        "grade_id, semester, subject_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        mapped,
    )
    conn.execute("DROP TABLE exams")
    conn.execute("ALTER TABLE exams_v13 RENAME TO exams")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_exams_lookup "
        "ON exams (year, month, subject_id, grade_id, exam_type_id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_exams_school ON exams (school_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_exam_school_map_school ON exam_school_map (school_id)"
    )


def rollback(conn: sqlite3.Connection) -> None:
    """v14 → v13：恢复旧 10 列 ``exams``；区划宏观节点与两张新字典保留。"""
    _run(conn, _rollback_exams, 13)


__all__ = ["backup_pre_v14", "rollback", "upgrade"]
