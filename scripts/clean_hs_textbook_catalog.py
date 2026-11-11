"""高中数学 / 高中物理教材版本清洗与补齐，幂等可重跑。

做四件事：
1. 数学人教A版：把旧册名（必修一/选修一）归正为必修第一册/选择性必修第一册，
   同册名重复时保留带真实章节的一册，其余空占位册合并后删除；
2. 物理：把「人教版（2019）」六册并入「人教版」，删除重复空册与空版本；
3. 补齐 101..109 的版本与其余版本册次（复用 seeds.textbook_catalog）；
4. 校验：高中口径下数学不再出现「人教版」，物理不再出现「人教版（2019）」，
   所有版本与册次的 subject_id 必须一致。

用法：
    python scripts/clean_hs_textbook_catalog.py
    python scripts/clean_hs_textbook_catalog.py --db data/banks/xxx.db --no-backup
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bank_engine import paths  # noqa: E402
from app.bank_engine.seeds.textbook_catalog import (  # noqa: E402
    CATALOG_BOOK_ROWS,
    CATALOG_VERSION_ROWS,
)

MATH_SUBJECT_ID = 2
PHYSICS_SUBJECT_ID = 4
HIGH_SCHOOL_GRADES = (10, 11, 12)

# (册次, 旧册名/别名, 排序, 年级)
MATH_A_VOLUMES = (
    ("必修第一册", ("必修一", "必修第一册"), 1, 10),
    ("必修第二册", ("必修二", "必修第二册"), 2, 10),
    ("选择性必修第一册", ("选修一", "选择性必修第一册"), 3, 11),
    ("选择性必修第二册", ("选修二", "选择性必修第二册"), 4, 11),
    ("选择性必修第三册", ("选修三", "选择性必修第三册"), 5, 11),
)
PHYSICS_RJ_VOLUMES = (
    ("必修第一册", 1, 10),
    ("必修第二册", 2, 10),
    ("必修第三册", 3, 10),
    ("选择性必修第一册", 4, 11),
    ("选择性必修第二册", 5, 11),
    ("选择性必修第三册", 6, 11),
)


def _chapter_count(conn: sqlite3.Connection, book_id: int) -> int:
    return int(conn.execute(
        "SELECT COUNT(*) FROM dim_textbook_chapters WHERE textbook_id = ?", (book_id,)
    ).fetchone()[0])


def _merge_into(
    conn: sqlite3.Connection,
    keeper_id: int,
    dup_id: int,
) -> None:
    """把重复册的章节与学校引用并到保留册，再删掉重复册。"""
    if keeper_id == dup_id:
        return
    if _chapter_count(conn, dup_id):
        conn.execute(
            "UPDATE dim_textbook_chapters SET textbook_id = ? WHERE textbook_id = ?",
            (keeper_id, dup_id),
        )
    conn.execute(
        "UPDATE dim_schools SET textbook_id = ? WHERE textbook_id = ?",
        (keeper_id, dup_id),
    )
    conn.execute("DELETE FROM dim_textbooks WHERE id = ?", (dup_id,))


def _pick_keeper(conn: sqlite3.Connection, book_ids: list[int]) -> int:
    return max(book_ids, key=lambda bid: (_chapter_count(conn, bid), -bid))


def normalize_math_a(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT id FROM dim_textbook_versions WHERE subject_id = ? AND name = '人教A版'",
        (MATH_SUBJECT_ID,),
    ).fetchone()
    if row is None:
        return 0
    version_id = int(row[0])
    merged = 0
    for volume, aliases, sort_order, grade_id in MATH_A_VOLUMES:
        marks = ",".join("?" for _ in aliases)
        ids = [
            int(item[0]) for item in conn.execute(
                "SELECT id FROM dim_textbooks WHERE version_id = ? AND volume_name IN ("
                + marks + ")",
                (version_id, *aliases),
            )
        ]
        if not ids:
            continue
        keeper = _pick_keeper(conn, ids)
        for dup in ids:
            if dup != keeper:
                _merge_into(conn, keeper, dup)
                merged += 1
        conn.execute(
            "UPDATE dim_textbooks SET name = ?, sort_order = ?, grade_id = ?, "
            "subject_id = ?, version_id = ?, volume_name = ? WHERE id = ?",
            (
                "人教A版·" + volume,
                sort_order,
                grade_id,
                MATH_SUBJECT_ID,
                version_id,
                volume,
                keeper,
            ),
        )
    return merged


def normalize_physics_rj(conn: sqlite3.Connection) -> int:
    rj = conn.execute(
        "SELECT id FROM dim_textbook_versions WHERE subject_id = ? AND name = '人教版'",
        (PHYSICS_SUBJECT_ID,),
    ).fetchone()
    if rj is None:
        return 0
    rj_id = int(rj[0])
    legacy = conn.execute(
        "SELECT id FROM dim_textbook_versions WHERE subject_id = ? AND name = '人教版（2019）'",
        (PHYSICS_SUBJECT_ID,),
    ).fetchone()
    legacy_id = None if legacy is None else int(legacy[0])
    scope = [rj_id] if legacy_id is None else [rj_id, legacy_id]
    marks = ",".join("?" for _ in scope)
    merged = 0
    for volume, sort_order, grade_id in PHYSICS_RJ_VOLUMES:
        ids = [
            int(item[0]) for item in conn.execute(
                "SELECT id FROM dim_textbooks WHERE subject_id = ? AND version_id IN ("
                + marks + ") AND volume_name IN (?, ?)",
                (PHYSICS_SUBJECT_ID, *scope, volume, "高中物理" + volume),
            )
        ]
        if not ids:
            continue
        keeper = _pick_keeper(conn, ids)
        for dup in ids:
            if dup != keeper:
                _merge_into(conn, keeper, dup)
                merged += 1
        conn.execute(
            "UPDATE dim_textbooks SET name = ?, sort_order = ?, grade_id = ?, "
            "subject_id = ?, version_id = ?, volume_name = ? WHERE id = ?",
            (
                "人教版·" + volume,
                sort_order,
                grade_id,
                PHYSICS_SUBJECT_ID,
                rj_id,
                volume,
                keeper,
            ),
        )
    if legacy_id is not None:
        left = int(conn.execute(
            "SELECT COUNT(*) FROM dim_textbooks WHERE version_id = ?", (legacy_id,)
        ).fetchone()[0])
        if left:
            raise SystemExit(f"人教版（2019）仍有 {left} 册，拒绝删除空版本")
        conn.execute("DELETE FROM dim_textbook_versions WHERE id = ?", (legacy_id,))
    return merged


def apply_catalog(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO dim_textbook_versions "
        "(id, name, code, sort_order, publisher, subject_id) VALUES (?, ?, ?, ?, ?, ?)",
        CATALOG_VERSION_ROWS,
    )
    conn.executemany(
        "INSERT OR IGNORE INTO dim_textbooks "
        "(id, name, code, sort_order, publisher, subject_id, grade_id, version_id, volume_name) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        CATALOG_BOOK_ROWS,
    )


def verify(conn: sqlite3.Connection) -> None:
    problems: list[str] = []
    math_versions = {
        str(row[0]) for row in conn.execute(
            "SELECT name FROM dim_textbook_versions WHERE subject_id = ?",
            (MATH_SUBJECT_ID,),
        )
    }
    required_math = {"人教A版", "人教B版", "北师大版", "苏教版", "湘教版", "沪教版"}
    if not required_math.issubset(math_versions):
        problems.append("数学缺少版本：" + "、".join(sorted(required_math - math_versions)))
    physics_versions = {
        str(row[0]) for row in conn.execute(
            "SELECT name FROM dim_textbook_versions WHERE subject_id = ?",
            (PHYSICS_SUBJECT_ID,),
        )
    }
    if "人教版（2019）" in physics_versions:
        problems.append("物理仍存在重复的「人教版（2019）」")
    required_physics = {"人教版", "鲁科版", "沪科版", "粤教版", "教科版"}
    if not required_physics.issubset(physics_versions):
        problems.append("物理缺少版本：" + "、".join(sorted(required_physics - physics_versions)))

    high_marks = ",".join("?" for _ in HIGH_SCHOOL_GRADES)
    high_math_versions = list(conn.execute(
        "SELECT DISTINCT v.name FROM dim_textbooks b "
        "JOIN dim_textbook_versions v ON v.id = b.version_id "
        "WHERE b.subject_id = ? AND b.grade_id IN (" + high_marks + ")",
        (MATH_SUBJECT_ID, *HIGH_SCHOOL_GRADES),
    ))
    if any(str(row[0]) == "人教版" for row in high_math_versions):
        problems.append("高中数学仍混入「人教版」")

    bad_subject = int(conn.execute(
        "SELECT COUNT(*) FROM dim_textbooks b "
        "JOIN dim_textbook_versions v ON v.id = b.version_id "
        "WHERE b.subject_id <> v.subject_id"
    ).fetchone()[0])
    if bad_subject:
        problems.append(f"{bad_subject} 册教材的学科与版本不一致")

    duplicates = list(conn.execute(
        "SELECT version_id, volume_name, COUNT(*) n FROM dim_textbooks "
        "WHERE version_id IS NOT NULL AND volume_name IS NOT NULL "
        "GROUP BY version_id, volume_name HAVING n > 1"
    ))
    if duplicates:
        problems.append("版本内册次重复：" + "、".join(
            f"版本{row[0]}·{row[1]}×{row[2]}" for row in duplicates
        ))

    if problems:
        raise SystemExit("清洗校验失败：\n- " + "\n- ".join(problems))


def _backup(db_path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = db_path.with_name(db_path.name + f".pre-hs-clean-{stamp}.bak")
    shutil.copy2(db_path, target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="清洗高中数学 / 物理教材版本并补齐册次")
    parser.add_argument("--db", type=Path, default=None, help="默认写入当前活跃引擎库")
    parser.add_argument("--no-backup", action="store_true", help="跳过落盘前备份（仅测试用）")
    args = parser.parse_args(argv)
    db_path = args.db or paths.engine_db_path()
    if not db_path.is_file():
        raise SystemExit(f"数据库不存在：{db_path}")
    backup = None if args.no_backup else _backup(db_path)
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            math_merged = normalize_math_a(conn)
            physics_merged = normalize_physics_rj(conn)
            apply_catalog(conn)
        verify(conn)
        math_versions = [
            str(row[0]) for row in conn.execute(
                "SELECT name FROM dim_textbook_versions WHERE subject_id = ? "
                "ORDER BY sort_order, id",
                (MATH_SUBJECT_ID,),
            )
        ]
        physics_versions = [
            str(row[0]) for row in conn.execute(
                "SELECT name FROM dim_textbook_versions WHERE subject_id = ? "
                "ORDER BY sort_order, id",
                (PHYSICS_SUBJECT_ID,),
            )
        ]
    finally:
        conn.close()
    if backup is not None:
        print(f"清洗前备份：{backup}")
    print(f"数据库：{db_path}")
    print(f"合并重复册：数学人教A版 {math_merged} 册，物理人教版 {physics_merged} 册")
    print("数学版本：" + "、".join(math_versions))
    print("物理版本：" + "、".join(physics_versions))
    print("校验：通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
