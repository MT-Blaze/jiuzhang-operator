"""引擎库 v9 → v10 迁移：试卷表定型为 10 字段，考试类型清洗为 8 大类。

``exams`` 去掉 ``code`` / ``exam_subject`` / ``created_at``，补
``exam_org_name`` / ``school_id`` / ``mock_round`` / ``semester``；
``dict_exam_types`` 只留 8 个大类，旧的「一模 / 二模 / 竞赛题」等并回「模考」，
轮次从旧名称迁进 ``mock_round``。整段单事务，失败整体回滚。

迁移三律：
- 版本化分派：由 ``builder.migrate`` 统一调度，本模块只管 v9 → v10 一步；
- 备份优先：动结构前先落 ``<库名>.pre-v10.bak``（幂等，WAL 安全）；
- 可回滚：``rollback`` 显式降回 v9 形状，只丢新增列与新口径，题目关联行原样保留。
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from app.bank_engine.seeds.exam_seed import EXAM_TYPE_ROWS
from app.core.exam_name import parse_mock_round

EXAMS_TABLE = "exams"
TYPES_TABLE = "dict_exam_types"

OLD_EXAM_TYPES: tuple[tuple[int, str, str, int], ...] = (
    (1, "高考真题", "gaokao", 1),
    (5, "一模", "mock_one", 2),
    (6, "二模", "mock_two", 3),
    (7, "期中", "midterm", 4),
    (8, "期末", "final", 5),
    (9, "月考", "monthly", 6),
    (10, "竞赛题", "competition", 7),
    (11, "强基题", "qiangji", 8),
    (12, "自主招生", "independent_enrollment", 9),
    (13, "外国题", "foreign", 10),
    (14, "机构题", "institution", 11),
    (15, "汇编题", "compilation", 12),
    (16, "自编题", "self_made", 13),
)

CREATE_EXAMS_V10 = """
CREATE TABLE exams_v10 (
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

CREATE_EXAMS_V9 = """
CREATE TABLE exams_v9 (
    id           INTEGER PRIMARY KEY,
    code         TEXT NOT NULL UNIQUE,
    year         INTEGER NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    month        INTEGER CHECK (month IS NULL OR month BETWEEN 1 AND 12),
    subject_id   INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    grade_id     INTEGER NOT NULL REFERENCES dict_grades(id) ON DELETE RESTRICT,
    exam_type_id INTEGER NOT NULL REFERENCES dict_exam_types(id) ON DELETE RESTRICT,
    exam_subject TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
)
"""

_ROUND_SUFFIX = re.compile(r"(?:零|一|二|三|四|五|六|七|八|九|十|\d)+\s*模$")


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(" + table + ")")}


def backup_pre_v10(conn: sqlite3.Connection) -> Path | None:
    """迁移前备份：已存在则跳过（幂等）；内存库无文件可备，返回 None。"""
    row = conn.execute("PRAGMA database_list").fetchone()
    raw = str(row[2]) if row is not None else ""
    if not raw:
        return None
    path = Path(raw)
    target = path.with_name(path.name + ".pre-v10.bak")
    if target.exists():
        return target
    dest = sqlite3.connect(target, timeout=10.0)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return target


def _map_type(name: object) -> tuple[int, int | None]:
    """旧类型名 → (新大类 id, 迁移出的轮次)；认不出的一律归「模考」。"""
    text = str(name or "").strip()
    if text in ("高考真题", "高考"):
        return 1, None
    if text == "学业水平":
        return 2, None
    if text == "期中":
        return 4, None
    if text == "期末":
        return 5, None
    if text == "月考":
        return 6, None
    if text == "周测":
        return 7, None
    if text == "开学考":
        return 8, None
    if text in ("一模",):
        return 3, 1
    if text in ("二模",):
        return 3, 2
    return 3, parse_mock_round(text)


def _infer_semester(month: object) -> str | None:
    if month is None:
        return None
    value = int(month)
    if 9 <= value <= 12:
        return "上学期"
    if 1 <= value <= 6:
        return "下学期"
    return None


def _strip_round(org: object) -> str | None:
    text = str(org or "").strip()
    if not text:
        return None
    stripped = _ROUND_SUFFIX.sub("", text).strip()
    return stripped or None


def _first_schools(conn: sqlite3.Connection) -> dict[int, int]:
    if not _table_exists(conn, "exam_school_map"):
        return {}
    return {
        int(row[0]): int(row[1])
        for row in conn.execute(
            "SELECT exam_id, MIN(school_id) FROM exam_school_map GROUP BY exam_id"
        )
    }


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def _wipe_and_seed_types(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM " + TYPES_TABLE)
    conn.executemany(
        "INSERT INTO " + TYPES_TABLE + " (id, name, code, sort_order) VALUES (?, ?, ?, ?)",
        EXAM_TYPE_ROWS,
    )


def _rebuild_from_v9(conn: sqlite3.Connection) -> None:
    """旧 9 字段 exams → 新 10 字段；关联行按原 exam_id 保留。"""
    type_names = {
        int(row[0]): str(row[1]) for row in conn.execute(
            "SELECT id, name FROM " + TYPES_TABLE
        )
    }
    first_schools = _first_schools(conn)
    rows = conn.execute(
        "SELECT id, year, month, subject_id, grade_id, exam_type_id, exam_subject "
        "FROM exams ORDER BY id"
    ).fetchall()
    mapped: list[tuple] = []
    for row in rows:
        new_type, inferred_round = _map_type(type_names.get(int(row["exam_type_id"]), ""))
        org = str(row["exam_subject"] or "").strip() or None
        mock_round = inferred_round or parse_mock_round(org)
        month_value = None if row["month"] is None else int(row["month"])
        if new_type == 3:
            org = _strip_round(org)
            month_value = None
        semester = _infer_semester(month_value) if new_type in (4, 5) else None
        mapped.append(
            (
                int(row["id"]),
                int(row["year"]),
                org,
                first_schools.get(int(row["id"])),
                month_value,
                new_type,
                None if new_type != 3 else mock_round,
                int(row["grade_id"]),
                semester,
                int(row["subject_id"]),
            )
        )
    _wipe_and_seed_types(conn)
    conn.execute(CREATE_EXAMS_V10)
    conn.executemany(
        "INSERT INTO exams_v10 "
        "(id, year, exam_org_name, school_id, month, exam_type_id, mock_round, "
        "grade_id, semester, subject_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        mapped,
    )
    _replace_exams(conn, "exams_v10")


def _normalize_existing(conn: sqlite3.Connection) -> None:
    """库已经是新 10 字段（如 v6 老库一路升级建表）：只清洗字典并补齐轮次/学期。"""
    type_names = {
        int(row[0]): str(row[1]) for row in conn.execute(
            "SELECT id, name FROM " + TYPES_TABLE
        )
    }
    first_schools = _first_schools(conn)
    rows = conn.execute(
        "SELECT id, year, exam_org_name, school_id, month, exam_type_id, mock_round, "
        "grade_id, semester, subject_id FROM exams ORDER BY id"
    ).fetchall()
    updates: list[tuple] = []
    for row in rows:
        new_type, inferred_round = _map_type(type_names.get(int(row["exam_type_id"]), ""))
        org = str(row["exam_org_name"] or "").strip() or None
        mock_round = None if row["mock_round"] is None else int(row["mock_round"])
        month = None if row["month"] is None else int(row["month"])
        semester = None if row["semester"] is None else str(row["semester"])
        if new_type == 3:
            mock_round = mock_round or inferred_round or parse_mock_round(org)
            org = _strip_round(org)
            month = None
        if new_type in (4, 5):
            semester = semester or _infer_semester(month)
        updates.append(
            (
                org,
                None if row["school_id"] is not None else first_schools.get(int(row["id"])),
                month,
                new_type,
                mock_round,
                semester,
                int(row["id"]),
            )
        )
    _wipe_and_seed_types(conn)
    conn.executemany(
        "UPDATE exams SET exam_org_name = ?, "
        "school_id = COALESCE(school_id, ?), month = ?, exam_type_id = ?, "
        "mock_round = ?, semester = ? WHERE id = ?",
        updates,
    )


def _replace_exams(conn: sqlite3.Connection, staging: str) -> None:
    conn.execute("DROP TABLE exams")
    conn.execute("ALTER TABLE " + staging + " RENAME TO exams")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_exams_lookup "
        "ON exams (year, month, subject_id, grade_id, exam_type_id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_exams_school ON exams (school_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_exam_school_map_school "
        "ON exam_school_map (school_id)"
    )


def _run(conn: sqlite3.Connection, body) -> None:
    previous_factory = conn.row_factory
    conn.isolation_level = None
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            body(conn)
            conn.execute("PRAGMA user_version = 10")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.isolation_level = ""
        conn.row_factory = previous_factory


def upgrade(conn: sqlite3.Connection) -> None:
    """v9 → v10：清洗考试类型字典，重建 exams 并迁移旧行；幂等可重跑。"""
    backup_pre_v10(conn)
    columns = _columns(conn, EXAMS_TABLE)
    if "exam_subject" in columns or "code" in columns:
        _run(conn, _rebuild_from_v9)
    else:
        _run(conn, _normalize_existing)


def rollback(conn: sqlite3.Connection) -> None:
    """v10 → v9：恢复旧 13 类字典与旧 9 字段 exams；关联行只换 exam_id 口径。"""
    def body(inner: sqlite3.Connection) -> None:
        rows = inner.execute(
            "SELECT id, year, exam_org_name, school_id, month, exam_type_id, "
            "mock_round, grade_id, semester, subject_id FROM exams ORDER BY id"
        ).fetchall()
        old_ids = {
            1: 1, 2: 16, 3: 5, 4: 7, 5: 8, 6: 9, 7: 9, 8: 16,
        }
        mapped: list[tuple] = []
        for row in rows:
            new_id = int(row["exam_type_id"])
            old_id = old_ids.get(new_id, 16)
            if new_id == 3 and row["mock_round"] is not None:
                old_id = 6 if int(row["mock_round"]) == 2 else 5
            org = str(row["exam_org_name"] or "").strip() or "未命名试卷"
            mapped.append(
                (
                    int(row["id"]),
                    "exm_legacy_" + str(int(row["id"])),
                    int(row["year"]),
                    None if row["month"] is None else int(row["month"]),
                    int(row["subject_id"]),
                    int(row["grade_id"]),
                    old_id,
                    org[:120],
                )
            )
        inner.execute("DELETE FROM " + TYPES_TABLE)
        inner.executemany(
            "INSERT INTO " + TYPES_TABLE + " (id, name, code, sort_order) "
            "VALUES (?, ?, ?, ?)",
            OLD_EXAM_TYPES,
        )
        inner.execute(CREATE_EXAMS_V9)
        inner.executemany(
            "INSERT INTO exams_v9 "
            "(id, code, year, month, subject_id, grade_id, exam_type_id, exam_subject) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            mapped,
        )
        inner.execute("DROP TABLE exams")
        inner.execute("ALTER TABLE exams_v9 RENAME TO exams")
        inner.execute("DROP INDEX IF EXISTS ix_exams_school")
        inner.execute(
            "CREATE INDEX IF NOT EXISTS ix_exams_lookup "
            "ON exams (year, month, subject_id, grade_id, exam_type_id)"
        )
        inner.execute(
            "CREATE INDEX IF NOT EXISTS ix_exam_school_map_school "
            "ON exam_school_map (school_id)"
        )

    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            body(conn)
            conn.execute("PRAGMA user_version = 9")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.isolation_level = ""


__all__ = [
    "OLD_EXAM_TYPES",
    "backup_pre_v10",
    "rollback",
    "upgrade",
]
