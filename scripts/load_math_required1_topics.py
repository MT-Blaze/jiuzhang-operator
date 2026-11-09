"""人教A版必修一知识树落库与分步校验。

用法：
    python scripts/load_math_required1_topics.py            # 迁移库结构并幂等落库
    python scripts/load_math_required1_topics.py --verify   # 只校验，不写库
    python scripts/load_math_required1_topics.py --db 副本.db
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bank_engine import builder, paths  # noqa: E402
from app.bank_engine.seeds.math_required1 import (  # noqa: E402
    MATH_REQUIRED1_CHAPTER_KNOWLEDGE_ROWS,
    MATH_REQUIRED1_EXAM_ROWS,
    MATH_REQUIRED1_KNOWLEDGE_EXAM_ROWS,
    MATH_REQUIRED1_KNOWLEDGE_ROWS,
)

DIRTY_TITLE = re.compile(r"^(第[一二三四五六七八九十百]+[章节]|\d+(?:\.\d+)*[ .、])")
PLACEHOLDER = "（未细分考向）"

INSERT_STATEMENTS = (
    (
        "INSERT OR IGNORE INTO dim_knowledge_points "
        "(id, code, name, sort_order, subject_id, parent_id) VALUES (?, ?, ?, ?, ?, ?)",
        MATH_REQUIRED1_KNOWLEDGE_ROWS,
    ),
    (
        "INSERT OR IGNORE INTO dim_exam_directions "
        "(id, name, code, sort_order, subject_id, chapter_id, description) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        MATH_REQUIRED1_EXAM_ROWS,
    ),
    (
        "INSERT OR IGNORE INTO knowledge_exam_map "
        "(knowledge_point_id, exam_direction_id) VALUES (?, ?)",
        MATH_REQUIRED1_KNOWLEDGE_EXAM_ROWS,
    ),
    (
        "INSERT OR IGNORE INTO chapter_knowledge_map "
        "(chapter_id, knowledge_point_id) VALUES (?, ?)",
        MATH_REQUIRED1_CHAPTER_KNOWLEDGE_ROWS,
    ),
)


def open_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> bool:
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    return builder.migrate(conn, version)


def load(conn: sqlite3.Connection) -> None:
    with conn:
        for sql, rows in INSERT_STATEMENTS:
            conn.executemany(sql, tuple(rows))


def _ids(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> set[int]:
    return {int(row[0]) for row in conn.execute(sql, params)}


def check(conn: sqlite3.Connection, sample_code: str) -> list[str]:
    problems: list[str] = []
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if version != paths.SCHEMA_VERSION:
        problems.append(f"结构版本 {version} != {paths.SCHEMA_VERSION}")

    names = [
        str(row[0]) for row in conn.execute(
            "SELECT name FROM dim_knowledge_points WHERE code LIKE 'KP_MATH_H_%'"
        )
    ]
    if len(names) != 70:
        problems.append(f"必修一知识点应为 70 条，实为 {len(names)}")
    dirty = [name for name in names if DIRTY_TITLE.match(name)]
    if dirty:
        problems.append("知识点混入教材标题：" + "、".join(dirty[:5]))

    directions = [
        str(row[0]) for row in conn.execute(
            "SELECT name FROM dim_exam_directions WHERE code LIKE 'ED_MATH_H_%'"
        )
    ]
    if len(directions) != 194:
        problems.append(f"必修一考向应为 194 条，实为 {len(directions)}")
    if PLACEHOLDER in directions:
        problems.append("考向字典残留“（未细分考向）”占位")
    dirty_directions = [name for name in directions if DIRTY_TITLE.match(name)]
    if dirty_directions:
        problems.append("考向混入教材标题：" + "、".join(dirty_directions[:5]))

    new_points = _ids(
        conn, "SELECT id FROM dim_knowledge_points WHERE code LIKE 'KP_MATH_H_%'"
    )
    new_directions = _ids(
        conn, "SELECT id FROM dim_exam_directions WHERE code LIKE 'ED_MATH_H_%'"
    )
    mapped_points = _ids(
        conn, "SELECT knowledge_point_id FROM knowledge_exam_map"
    )
    mapped_directions = _ids(
        conn, "SELECT exam_direction_id FROM knowledge_exam_map"
    )
    chapter_points = _ids(
        conn, "SELECT knowledge_point_id FROM chapter_knowledge_map"
    )

    orphan_points = sorted(new_points - mapped_points)
    if orphan_points:
        problems.append(f"{len(orphan_points)} 个知识点没有挂任何考向")
    orphan_directions = sorted(new_directions - mapped_directions)
    if orphan_directions:
        problems.append(f"{len(orphan_directions)} 个考向没有挂任何知识点")
    unchaptered = sorted(new_points - chapter_points)
    if unchaptered:
        problems.append(f"{len(unchaptered)} 个知识点没有挂任何教材章节")

    counts = {
        "knowledge_exam_map": int(
            conn.execute("SELECT COUNT(*) FROM knowledge_exam_map").fetchone()[0]
        ),
        "chapter_knowledge_map": int(
            conn.execute("SELECT COUNT(*) FROM chapter_knowledge_map").fetchone()[0]
        ),
    }
    if counts["knowledge_exam_map"] != 200:
        problems.append(f"knowledge_exam_map 应为 200 条，实为 {counts['knowledge_exam_map']}")
    if counts["chapter_knowledge_map"] != 74:
        problems.append(
            f"chapter_knowledge_map 应为 74 条，实为 {counts['chapter_knowledge_map']}"
        )

    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        problems.append("integrity_check 异常")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        problems.append("foreign_key_check 异常")

    map_tables = [
        str(row[0]) for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE '%_map'"
        )
    ]
    print("映射表：" + "、".join(map_tables))
    print(f"结构版本：{version}")
    print(f"必修一知识点：{len(names)}；考向：{len(directions)}")
    print(f"知识点-考向映射：{counts['knowledge_exam_map']}；章节-知识点映射：{counts['chapter_knowledge_map']}")

    print("\n分步链路（严禁连级 JOIN）：")
    direction = conn.execute(
        "SELECT id, name, code FROM dim_exam_directions WHERE code = ?", (sample_code,)
    ).fetchone()
    if direction is None:
        problems.append(f"样例考向 {sample_code} 不存在")
        return problems
    print(f"  1. 考向：{direction['name']}（{direction['code']}，id={direction['id']}）")
    point_ids = [
        int(row[0]) for row in conn.execute(
            "SELECT knowledge_point_id FROM knowledge_exam_map WHERE exam_direction_id = ?",
            (direction["id"],),
        )
    ]
    if not point_ids:
        problems.append(f"样例考向 {sample_code} 没挂知识点")
        return problems
    for point_id in point_ids:
        point = conn.execute(
            "SELECT id, name, code FROM dim_knowledge_points WHERE id = ?", (point_id,)
        ).fetchone()
        print(f"  2. 知识点：{point['name']}（{point['code']}，id={point['id']}）")
        chapter_ids = [
            int(row[0]) for row in conn.execute(
                "SELECT chapter_id FROM chapter_knowledge_map WHERE knowledge_point_id = ?",
                (point_id,),
            )
        ]
        if not chapter_ids:
            problems.append(f"知识点 {point['code']} 没挂章节")
            continue
        for chapter_id in chapter_ids:
            chapter = conn.execute(
                "SELECT id, name, textbook_id FROM dim_textbook_chapters WHERE id = ?",
                (chapter_id,),
            ).fetchone()
            book = conn.execute(
                "SELECT name FROM dim_textbooks WHERE id = ?", (chapter["textbook_id"],)
            ).fetchone()
            print(
                f"  3. 章节：{chapter['name']}（id={chapter['id']}）"
                f" ← 教材：{book['name']}（id={chapter['textbook_id']}）"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="必修一知识树落库与校验")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--verify", action="store_true", help="只校验，不迁移不写库")
    parser.add_argument("--sample", default="ED_MATH_H_001")
    args = parser.parse_args(argv)

    db_path = Path(args.db) if args.db else paths.engine_db_path()
    if not db_path.is_file():
        raise SystemExit(f"库不存在：{db_path}")
    conn = open_db(db_path)
    try:
        if not args.verify:
            migrated = migrate(conn)
            print(f"结构迁移：{'已升级到 v' + str(paths.SCHEMA_VERSION) if migrated else '无需迁移'}")
            load(conn)
            print("数据落库：完成（幂等）")
        problems = check(conn, args.sample)
    finally:
        conn.close()

    if problems:
        print("\n校验未通过：")
        for problem in problems:
            print("  -", problem)
        return 1
    print("\n校验通过：脏数据 0 条，映射链路通畅。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
