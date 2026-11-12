#!/usr/bin/env python3
"""字典种子一致性校验：用出厂种子临时重建新库，与活跃库逐表逐行比对。

只比纯字典表，不碰题目/解析/试卷等业务数据。
用法：
    .venv\\Scripts\\python.exe tools\\verify_dict_seeds.py
    .venv\\Scripts\\python.exe tools\\verify_dict_seeds.py --db data/banks/xxx.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bank_engine import builder, paths  # noqa: E402

COLUMNS: dict[str, tuple[str, ...]] = {
    "dict_subjects": ("id", "code", "name", "sort_order"),
    "dict_grades": ("id", "code", "name", "sort_order", "stage"),
    "dict_question_types": ("id", "code", "name", "sort_order"),
    "dict_difficulties": (
        "id", "code", "name", "sort_order", "level", "description", "ai_prompt",
    ),
    "dict_question_qualities": ("id", "code", "name", "sort_order"),
    "dict_exam_types": ("id", "name", "code", "sort_order"),
    "dict_subject_thoughts": (
        "id", "code", "name", "sort_order", "subject_id", "stage",
    ),
    "dict_solution_methods": (
        "id", "code", "name", "sort_order", "subject_id", "stage",
    ),
    "dict_core_competencies": (
        "id", "code", "name", "sort_order", "subject_id", "stage",
    ),
    "dim_regions": ("id", "name", "code", "level", "parent_id", "sort_order"),
    "dim_schools": (
        "id", "name", "short_name", "code", "region", "textbook_id", "region_id",
    ),
    "dim_textbook_versions": (
        "id", "name", "code", "sort_order", "publisher", "subject_id",
    ),
    "dim_textbooks": (
        "id", "name", "code", "sort_order", "publisher", "subject_id",
        "grade_id", "version_id", "volume_name",
    ),
    "dim_textbook_chapters": (
        "id", "name", "code", "sort_order", "textbook_id", "parent_id",
    ),
    "dim_knowledge_points": (
        "id", "code", "name", "sort_order", "subject_id", "parent_id",
    ),
    "dim_exam_directions": (
        "id", "name", "code", "sort_order", "subject_id", "chapter_id",
        "description",
    ),
    "knowledge_exam_map": (
        "knowledge_point_id", "exam_direction_id", "sort_order",
    ),
    "chapter_knowledge_map": ("chapter_id", "knowledge_point_id", "sort_order"),
}


def _load(conn: sqlite3.Connection, table: str) -> list[tuple]:
    columns = ", ".join(COLUMNS[table])
    return [tuple(row) for row in conn.execute(
        f"SELECT {columns} FROM {table} ORDER BY 1, 2"
    )]


def main() -> int:
    parser = argparse.ArgumentParser(description="校验字典种子与活跃库一致")
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args()
    live_path = Path(args.db or paths.engine_db_path())
    live = sqlite3.connect(f"file:{live_path.as_posix()}?mode=ro", uri=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="dict-seed-verify-"))
    built_path = tmp_dir / "rebuild.v2.db"
    try:
        builder.build_engine(
            db_path=built_path, schema=paths.schema_path(), force=True
        )
        built = sqlite3.connect(built_path)
        failures = 0
        try:
            for table in COLUMNS:
                expected = _load(live, table)
                actual = _load(built, table)
                if expected == actual:
                    print(f"OK   {table} ({len(expected)})")
                    continue
                failures += 1
                print(f"FAIL {table} live={len(expected)} rebuilt={len(actual)}")
                for index, (left, right) in enumerate(zip(expected, actual)):
                    if left != right:
                        print(f"     first diff #{index}: live={left} rebuilt={right}")
                        break
        finally:
            built.close()
    finally:
        live.close()
        for leftover in tmp_dir.glob("*"):
            leftover.unlink()
        tmp_dir.rmdir()
    print("PASS" if not failures else f"FAIL {failures} table(s)")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
