#!/usr/bin/env python3
"""课标清单落库：用课标原文整表替换学科思想与核心素养。

口径：
1. 只动 ``dict_subject_thoughts`` / ``dict_core_competencies``，解题方法原样保留；
2. 整表换成 ``curriculum_standards.py`` 的课标原文清单，清掉历史脏词；
3. 落库前查关联表引用，有引用就中止，绝不静默丢关联；
4. 写前自动备份 ``.pre-curriculum.bak``，默认 Dry-Run，``--apply`` 才写库；
5. 写后复核：行数、学段分布、零「全学段」、零重复键、零脏词。

用法：
    python scripts/standardize_curriculum.py --db data/banks/xxx.db
    python scripts/standardize_curriculum.py --db data/banks/xxx.db --apply
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

from app.bank_engine.seeds.curriculum_standards import (  # noqa: E402
    CORE_COMPETENCY_ROWS,
    SUBJECT_THOUGHT_ROWS,
)

DEFAULT_DB = ROOT / "data" / "banks" / "org.jiuzhang.bank-engine.v2.db"
TARGET_STAGES = ("小学", "初中", "高中")
# 历史脏词：本应属于解题方法或自造术语，不允许留在学科思想里。
DIRTY_THOUGHT_TERMS = (
    "等效替代", "守恒思", "守恒", "微元", "控制变量", "函数思想", "方程思想",
    "转化与化归", "分类讨论", "整体思想", "类比思想", "模型思想", "系统思想",
    "对称思想", "理想化思想", "转换思想", "模型建构思想",
)
# 核心素养表的关联表：一旦有引用，整表替换会丢关联，必须先人工处理。
REFERENCE_TABLES = (
    ("solution_thought_map", "thought_id", "dict_subject_thoughts"),
    ("solution_competency_map", "competency_id", "dict_core_competencies"),
)
COLUMNS = "(id, code, name, sort_order, subject_id, stage)"


@dataclass(frozen=True)
class Plan:
    table: str
    rows: tuple[tuple[int, str, str, int, int, str], ...]
    old_count: int
    old_stages: str
    old_bad: tuple[str, ...]


def _write(text: str = "") -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("utf-8", "replace").decode("utf-8"))


def validate_rows(table: str, rows: tuple[tuple[int, str, str, int, int, str], ...]) -> None:
    if not rows:
        raise SystemExit(f"{table} 课标清单为空，拒绝落库")
    ids = [row[0] for row in rows]
    codes = [row[1] for row in rows]
    keys = [(row[4], row[2], row[5]) for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"{table} id 有重复")
    if len(codes) != len(set(codes)):
        raise SystemExit(f"{table} code 有重复")
    if len(keys) != len(set(keys)):
        raise SystemExit(f"{table} (subject_id, name, stage) 有重复")
    bad_stage = sorted({row[5] for row in rows} - set(TARGET_STAGES))
    if bad_stage:
        raise SystemExit(f"{table} 学段越界：{bad_stage}")
    empty = [row for row in rows if not str(row[2]).strip()]
    if empty:
        raise SystemExit(f"{table} 存在空名称")


def validate_thought_terms() -> None:
    hits = [
        name for _, _, name, _, _, _ in SUBJECT_THOUGHT_ROWS
        for term in DIRTY_THOUGHT_TERMS if term in name
    ]
    if hits:
        raise SystemExit("学科思想仍含脏词：" + "、".join(sorted(set(hits))))


def check_references(conn: sqlite3.Connection) -> None:
    for child, column, parent in REFERENCE_TABLES:
        count = int(conn.execute(
            "SELECT COUNT(*) FROM " + child + " WHERE " + column + " IN "
            "(SELECT id FROM " + parent + ")"
        ).fetchone()[0])
        if count:
            raise SystemExit(
                f"{child} 已有 {count} 行引用 {parent}，整表替换会丢关联，已中止"
            )


def build_plans(conn: sqlite3.Connection) -> list[Plan]:
    plans: list[Plan] = []
    for table, rows in (
        ("dict_subject_thoughts", SUBJECT_THOUGHT_ROWS),
        ("dict_core_competencies", CORE_COMPETENCY_ROWS),
    ):
        validate_rows(table, rows)
        old_count = int(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
        stages = ", ".join(
            f"{row[0]}:{row[1]}"
            for row in conn.execute(
                "SELECT stage, COUNT(*) FROM " + table + " GROUP BY stage ORDER BY stage"
            )
        )
        bad = tuple(
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM " + table + " WHERE name LIKE '%（生物）' "
                "OR name LIKE '%（科学）' OR name LIKE '%（美术）' ORDER BY id"
            )
        )
        plans.append(Plan(table, rows, old_count, stages, bad))
    return plans


def print_plan(plans: list[Plan], subjects: dict[int, str]) -> None:
    for plan in plans:
        _write(f"\n== {plan.table}：存量 {plan.old_count} 行（{plan.old_stages}）"
               f" → 课标原文 {len(plan.rows)} 行 ==")
        if plan.old_bad:
            _write("  历史带学科后缀的脏名：" + "、".join(plan.old_bad))
        for subject_id, stage in sorted({(row[4], row[5]) for row in plan.rows}):
            names = [row[2] for row in plan.rows if (row[4], row[5]) == (subject_id, stage)]
            _write(
                f"  {subjects.get(subject_id, str(subject_id))}·{stage}"
                f"（{len(names)}）：" + "、".join(names)
            )


def backup_db(db_path: Path) -> Path:
    target = db_path.with_name(db_path.name + ".pre-curriculum.bak")
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


def apply_plans(db_path: Path, plans: list[Plan]) -> None:
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            for plan in plans:
                conn.execute("DELETE FROM " + plan.table)
                conn.executemany(
                    "INSERT INTO " + plan.table + " " + COLUMNS + " VALUES (?, ?, ?, ?, ?, ?)",
                    plan.rows,
                )
    finally:
        conn.close()


def audit(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    problems = 0
    try:
        for table, expected in (
            ("dict_subject_thoughts", len(SUBJECT_THOUGHT_ROWS)),
            ("dict_core_competencies", len(CORE_COMPETENCY_ROWS)),
        ):
            count = int(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
            all_stage = int(conn.execute(
                "SELECT COUNT(*) FROM " + table + " WHERE stage = '全学段'"
            ).fetchone()[0])
            by_stage = ", ".join(
                f"{row[0]}:{row[1]}"
                for row in conn.execute(
                    "SELECT stage, COUNT(*) FROM " + table + " GROUP BY stage ORDER BY stage"
                )
            )
            dup = int(conn.execute(
                "SELECT COUNT(*) FROM (SELECT subject_id, name, stage FROM " + table
                + " GROUP BY subject_id, name, stage HAVING COUNT(*) > 1)"
            ).fetchone()[0])
            _write(f"  {table}: {count}/{expected} 行；学段 {by_stage}；"
                   f"全学段 {all_stage} 行；重复键 {dup} 组")
            problems += count != expected or all_stage != 0 or dup != 0
        dirty = [
            str(row[0]) for row in conn.execute(
                "SELECT name FROM dict_subject_thoughts"
            ) if any(term in str(row[0]) for term in DIRTY_THOUGHT_TERMS)
        ]
        if dirty:
            _write("  学科思想仍有脏词：" + "、".join(dirty))
            problems += 1
    finally:
        conn.close()
    return problems


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="课标原文清单整表落库（默认 Dry-Run）")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="引擎库路径")
    parser.add_argument("--apply", action="store_true", help="真正写库（默认只读）")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.is_file():
        _write(f"库不存在：{db_path}")
        return 1

    validate_thought_terms()
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    try:
        check_references(conn)
        plans = build_plans(conn)
        subjects = {
            int(row[0]): str(row[1])
            for row in conn.execute("SELECT id, name FROM dict_subjects")
        }
    finally:
        conn.close()

    _write(f"库：{db_path}")
    print_plan(plans, subjects)
    if not args.apply:
        _write("\nDry-Run 结束：未写库。加 --apply 才落库。")
        return 0

    backup = backup_db(db_path)
    apply_plans(db_path, plans)
    _write(f"\n已备份：{backup}")
    problems = audit(db_path)
    if problems:
        _write(f"复核仍有 {problems} 项异常，请检查。")
        return 2
    _write("落库完成：学科思想与核心素养全部为课标原文，零「全学段」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
