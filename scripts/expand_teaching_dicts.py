#!/usr/bin/env python3
"""教研属性字典扩量：把 curriculum.py 的种子行幂等补进存量库。

按 code 判断是否已存在，只补缺失行，不改老师已编辑的名称 / 学段；
写库前自动备份，默认 Dry-Run。
用法：
    python scripts/expand_teaching_dicts.py
    python scripts/expand_teaching_dicts.py --db data/banks/xxx.db
    python scripts/expand_teaching_dicts.py --apply
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bank_engine import paths  # noqa: E402
from app.bank_engine.seeds import curriculum  # noqa: E402

STAGE_VALUES = ("小学", "初中", "高中", "全学段")
TABLES = {
    "dict_subject_thoughts": curriculum.SUBJECT_THOUGHT_ROWS,
    "dict_solution_methods": curriculum.SOLUTION_METHOD_ROWS,
    "dict_core_competencies": curriculum.CORE_COMPETENCY_ROWS,
}
COLUMNS = "(id, code, name, sort_order, subject_id, stage)"


@dataclass(frozen=True)
class Pending:
    table: str
    row: tuple[int, str, str, int, int, str]


def plan(conn: sqlite3.Connection) -> tuple[list[Pending], list[str]]:
    pending: list[Pending] = []
    conflicts: list[str] = []
    subjects = {int(row[0]) for row in conn.execute("SELECT id FROM dict_subjects")}
    for table, seed_rows in TABLES.items():
        taken_codes = {str(row[0]) for row in conn.execute("SELECT code FROM " + table)}
        taken_names = {
            (int(row[0]), str(row[1]))
            for row in conn.execute("SELECT subject_id, name FROM " + table)
        }
        taken_ids = {int(row[0]) for row in conn.execute("SELECT id FROM " + table)}
        next_id = max(taken_ids, default=0)
        for seed in seed_rows:
            row_id, code, name, sort_order, subject_id, stage = seed
            if code in taken_codes:
                continue
            if (int(subject_id), name) in taken_names:
                conflicts.append(f"{table} 同学科内名称已占用：{name}（code={code}）")
                continue
            if int(subject_id) not in subjects:
                conflicts.append(f"{table} 学科不存在：{name}（subject_id={subject_id}）")
                continue
            if stage not in STAGE_VALUES:
                conflicts.append(f"{table} 学段非法：{name}（stage={stage}）")
                continue
            if row_id in taken_ids:
                next_id += 1
                row_id = next_id
            pending.append(Pending(table, (int(row_id), code, name, int(sort_order),
                                           int(subject_id), stage)))
            taken_codes.add(code)
            taken_names.add((int(subject_id), name))
            taken_ids.add(int(row_id))
    return pending, conflicts


def backup_db(db_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = db_path.with_name(db_path.name + f".pre-dict-expand-{stamp}.bak")
    src = sqlite3.connect(str(db_path), timeout=30.0)
    dest = sqlite3.connect(str(target), timeout=30.0)
    try:
        src.backup(dest)
    finally:
        dest.close()
        src.close()
    return target


def apply(conn: sqlite3.Connection, pending: list[Pending]) -> None:
    for table in TABLES:
        rows = [item.row for item in pending if item.table == table]
        if rows:
            conn.executemany(
                f"INSERT INTO {table} {COLUMNS} VALUES (?, ?, ?, ?, ?, ?)", rows
            )


def report(conn: sqlite3.Connection) -> None:
    for table in TABLES:
        total = int(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
        print(f"  {table}: {total} 行")
    senior = int(conn.execute(
        "SELECT COUNT(*) FROM dict_solution_methods "
        "WHERE subject_id = 2 AND stage IN ('高中', '全学段')"
    ).fetchone()[0])
    primary = int(conn.execute(
        "SELECT COUNT(*) FROM dict_solution_methods "
        "WHERE subject_id = 2 AND stage IN ('小学', '全学段')"
    ).fetchone()[0])
    print(f"  高中·数学 可见解题方法：{senior} 条")
    print(f"  小学·数学 可见解题方法：{primary} 条")


def main() -> int:
    parser = argparse.ArgumentParser(description="教研属性字典扩量（默认 Dry-Run）")
    parser.add_argument("--db", default=str(paths.engine_db_path()), help="引擎库路径")
    parser.add_argument("--apply", action="store_true", help="真正写库（默认只读）")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.is_file():
        print(f"库不存在：{db_path}")
        return 1

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        pending, conflicts = plan(conn)
        print(f"库：{db_path}")
        print(f"待补：{len(pending)} 行")
        for item in pending:
            print(f"  + {item.table}#{item.row[0]} {item.row[2]}（{item.row[5]}）")
        for conflict in conflicts:
            print(f"  ! {conflict}")
        if not args.apply:
            print("Dry-Run 结束：未写库。")
            return 0
        if not pending:
            print("无需补数。")
            report(conn)
            return 0
        backup = backup_db(db_path)
        with conn:
            apply(conn, pending)
        print(f"已备份：{backup}")
        print("补数后复核：")
        report(conn)
        return 0 if not conflicts else 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
