#!/usr/bin/env python3
"""教研字典学段清洗：把 stage 空值全部落成明码，幂等可重跑。

规则：
1. 种子内条目按 curriculum.py 的口径覆盖为 小学 / 初中 / 高中 / 全学段；
2. 种子外的人工条目：已有合法学段保留，空值或非法值统一回填「全学段」；
3. 落库后三张表不允许存在 NULL / 空串 / 四值以外的 stage。

默认 Dry-Run 只读；``--apply`` 才写库，写前自动备份 ``.pre-stage-clean.bak``。
用法：
    python scripts/normalize_dict_stage.py
    python scripts/normalize_dict_stage.py --db data/banks/xxx.db
    python scripts/normalize_dict_stage.py --apply
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bank_engine.seeds import curriculum  # noqa: E402

DEFAULT_DB = ROOT / "data" / "banks" / "org.jiuzhang.bank-engine.v2.db"
STAGE_VALUES = ("小学", "初中", "高中", "全学段")
STAGE_ALL = "全学段"
TABLES = {
    "dict_subject_thoughts": curriculum.SUBJECT_THOUGHT_ROWS,
    "dict_solution_methods": curriculum.SOLUTION_METHOD_ROWS,
    "dict_core_competencies": curriculum.CORE_COMPETENCY_ROWS,
}


@dataclass(frozen=True)
class Change:
    table: str
    row_id: int
    name: str
    old: str | None
    new: str


def backup_db(db_path: Path) -> Path:
    target = db_path.with_name(db_path.name + ".pre-stage-clean.bak")
    if target.is_file():
        return target
    src = sqlite3.connect(str(db_path), timeout=30.0)
    dest = sqlite3.connect(str(target), timeout=30.0)
    try:
        src.backup(dest)
    finally:
        dest.close()
        src.close()
    return target


def stage_counts(conn: sqlite3.Connection, table: str) -> dict[str, int]:
    return {
        str(row[0]) if row[0] is not None else "<NULL>": int(row[1])
        for row in conn.execute(
            "SELECT stage, COUNT(*) FROM " + table + " GROUP BY stage"
        )
    }


def plan_changes(conn: sqlite3.Connection) -> list[Change]:
    changes: list[Change] = []
    for table, seed_rows in TABLES.items():
        mapping = {str(row[1]): str(row[5]) for row in seed_rows}
        for row in conn.execute(
            "SELECT id, code, name, stage FROM " + table + " ORDER BY id"
        ):
            row_id, code, name, old = int(row[0]), str(row[1]), str(row[2]), row[3]
            old = None if old is None else str(old)
            target = mapping.get(code)
            if target is None:
                target = old if old in STAGE_VALUES else STAGE_ALL
            if old != target:
                changes.append(Change(table, row_id, name, old, target))
    return changes


def apply_changes(db_path: Path, changes: list[Change]) -> Path:
    backup = backup_db(db_path)
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    try:
        with conn:
            conn.executemany(
                "UPDATE dict_subject_thoughts SET stage = ? WHERE id = ?",
                [(c.new, c.row_id) for c in changes if c.table == "dict_subject_thoughts"],
            )
            conn.executemany(
                "UPDATE dict_solution_methods SET stage = ? WHERE id = ?",
                [(c.new, c.row_id) for c in changes if c.table == "dict_solution_methods"],
            )
            conn.executemany(
                "UPDATE dict_core_competencies SET stage = ? WHERE id = ?",
                [(c.new, c.row_id) for c in changes if c.table == "dict_core_competencies"],
            )
    finally:
        conn.close()
    return backup


def audit(conn: sqlite3.Connection) -> int:
    bad = 0
    for table in TABLES:
        placeholders = ", ".join("?" for _ in STAGE_VALUES)
        count = int(conn.execute(
            "SELECT COUNT(*) FROM " + table + " WHERE stage IS NULL OR TRIM(stage) = '' "
            "OR stage NOT IN (" + placeholders + ")",
            STAGE_VALUES,
        ).fetchone()[0])
        bad += count
        print(f"  {table}: 非法/空 stage {count} 行，分布 {stage_counts(conn, table)}")
    return bad


def main() -> int:
    parser = argparse.ArgumentParser(description="教研字典 stage 空值清洗（默认 Dry-Run）")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="引擎库路径")
    parser.add_argument("--apply", action="store_true", help="真正写库（默认只读）")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.is_file():
        print(f"库不存在：{db_path}")
        return 1

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    try:
        before = {table: stage_counts(conn, table) for table in TABLES}
        changes = plan_changes(conn)
    finally:
        conn.close()

    print(f"库：{db_path}")
    for table, counts in before.items():
        print(f"  {table} 清洗前：{counts}")
    print(f"待更新：{len(changes)} 行")
    for change in changes:
        old = "<NULL>" if change.old is None else change.old
        print(f"  {change.table}#{change.row_id} {change.name}：{old} -> {change.new}")

    if not args.apply:
        print("Dry-Run 结束：未写库。")
        return 0

    backup = apply_changes(db_path, changes)
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    try:
        print(f"已备份：{backup}")
        print("清洗后复核：")
        bad = audit(conn)
    finally:
        conn.close()
    if bad:
        print(f"仍有 {bad} 行不合法，请复核。")
        return 2
    print("清洗完成：三张教研字典 stage 全部为明码，零 NULL。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
