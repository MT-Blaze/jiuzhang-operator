"""把全国教材版本目录与每版每学段的首册锚点补进已有引擎库，幂等可重跑。

只写 dim_textbook_versions / dim_textbooks，绝不写 dim_textbook_chapters。
用法：
    python scripts/load_national_textbook_catalog.py
    python scripts/load_national_textbook_catalog.py --db data/banks/xxx.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bank_engine import paths  # noqa: E402
from app.bank_engine.seeds import national_catalog  # noqa: E402

STAGE_ORDER = ("P", "J", "S")
STAGE_LABELS = {"P": "小学", "J": "初中", "S": "高中"}
SAMPLES = ("冀教版", "大象版", "湘少版", "沪粤版", "赣美版")


def _stage_codes(conn: sqlite3.Connection) -> dict[int, str]:
    codes = {name: code for code, name in national_catalog.STAGE_NAMES.items()}
    return {
        int(row[0]): codes.get(str(row[2]), "")
        for row in conn.execute("SELECT id, name, stage FROM dict_grades")
    }


def _existing_versions(conn: sqlite3.Connection) -> dict[tuple[int, str], int]:
    return {
        (int(row[2]), str(row[1])): int(row[0])
        for row in conn.execute("SELECT id, name, subject_id FROM dim_textbook_versions")
    }


def _covered_stages(conn: sqlite3.Connection) -> dict[int, set[str]]:
    stages = _stage_codes(conn)
    covered: dict[int, set[str]] = {}
    for row in conn.execute(
        "SELECT version_id, grade_id FROM dim_textbooks WHERE version_id IS NOT NULL"
    ):
        stage = stages.get(int(row[1]))
        if stage:
            covered.setdefault(int(row[0]), set()).add(stage)
    return covered


def _next_id(conn: sqlite3.Connection, table: str, floor: int) -> int:
    current = int(conn.execute("SELECT COALESCE(MAX(id), 0) FROM " + table).fetchone()[0])
    return max(floor, current + 1)


def _plan(conn: sqlite3.Connection) -> tuple[tuple[tuple, ...], tuple[tuple, ...]]:
    return national_catalog.build(
        _existing_versions(conn),
        _covered_stages(conn),
        next_version_id=_next_id(conn, "dim_textbook_versions", national_catalog.NEXT_VERSION_ID),
        next_book_id=_next_id(conn, "dim_textbooks", national_catalog.NEXT_BOOK_ID),
    )


def apply_catalog(conn: sqlite3.Connection) -> tuple[int, int]:
    version_rows, book_rows = _plan(conn)
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO dim_textbook_versions "
            "(id, name, code, sort_order, publisher, subject_id) VALUES (?, ?, ?, ?, ?, ?)",
            version_rows,
        )
        conn.executemany(
            "INSERT OR IGNORE INTO dim_textbooks "
            "(id, name, code, sort_order, publisher, subject_id, grade_id, version_id, volume_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            book_rows,
        )
    return len(version_rows), len(book_rows)


def _version_stats(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    subjects = {
        int(row[0]): str(row[1])
        for row in conn.execute("SELECT id, name FROM dict_subjects")
    }
    stages = _stage_codes(conn)
    buckets: dict[str, dict[str, set[int]]] = {code: {} for code in STAGE_ORDER}
    for row in conn.execute(
        "SELECT version_id, subject_id, grade_id FROM dim_textbooks "
        "WHERE version_id IS NOT NULL AND grade_id IS NOT NULL"
    ):
        stage = stages.get(int(row[2]))
        if not stage:
            continue
        subject = subjects.get(int(row[1]), "未知学科")
        buckets[stage].setdefault(subject, set()).add(int(row[0]))
    return {
        code: {subject: len(ids) for subject, ids in sorted(buckets[code].items())}
        for code in STAGE_ORDER
    }


def _print_stats(conn: sqlite3.Connection) -> None:
    stats = _version_stats(conn)
    print("\n========== 全库版本统计（按学段 / 学科） ==========")
    for code in STAGE_ORDER:
        subjects = stats[code]
        print(f"\n【{STAGE_LABELS[code]}】共 {len(subjects)} 个学科，"
              f"{sum(subjects.values())} 个版本（同一版本跨学科分别计数）")
        for subject, count in subjects.items():
            print(f"  {subject}：{count} 个版本")
    total = int(conn.execute("SELECT COUNT(*) FROM dim_textbook_versions").fetchone()[0])
    books = int(conn.execute("SELECT COUNT(*) FROM dim_textbooks").fetchone()[0])
    print(f"\n版本总数：{total}　册次总数：{books}")


def _print_samples(conn: sqlite3.Connection) -> None:
    print("\n========== 非主流版本抽查（证明全量写入） ==========")
    subjects = {
        int(row[0]): str(row[1])
        for row in conn.execute("SELECT id, name FROM dict_subjects")
    }
    stages = _stage_codes(conn)
    for name in SAMPLES:
        rows = conn.execute(
            "SELECT id, publisher, subject_id FROM dim_textbook_versions "
            "WHERE name = ? ORDER BY subject_id, id",
            (name,),
        ).fetchall()
        if not rows:
            print(f"  {name}：未找到！")
            continue
        for version_id, publisher, subject_id in rows:
            stage_set: set[str] = set()
            volumes: list[str] = []
            for volume, grade_id in conn.execute(
                "SELECT volume_name, grade_id FROM dim_textbooks "
                "WHERE version_id = ? ORDER BY grade_id, sort_order, id",
                (int(version_id),),
            ):
                stage = stages.get(int(grade_id)) if grade_id is not None else None
                if stage:
                    stage_set.add(stage)
                if volume:
                    volumes.append(str(volume))
            labels = "、".join(STAGE_LABELS[c] for c in STAGE_ORDER if c in stage_set)
            sample = "、".join(volumes[:3]) + ("…" if len(volumes) > 3 else "")
            print(f"  {name}（{subjects.get(int(subject_id), '?')} / {labels} / "
                  f"{publisher or '—'}）：{sample or '未挂册次'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补齐全国教材版本目录")
    parser.add_argument("--db", type=Path, default=None, help="默认写入当前活跃引擎库")
    args = parser.parse_args(argv)
    db_path = args.db or paths.engine_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        before_chapters = int(
            conn.execute("SELECT COUNT(*) FROM dim_textbook_chapters").fetchone()[0]
        )
        versions, books = apply_catalog(conn)
        again_versions, again_books = apply_catalog(conn)
        after_chapters = int(
            conn.execute("SELECT COUNT(*) FROM dim_textbook_chapters").fetchone()[0]
        )
        _print_stats(conn)
        _print_samples(conn)
    finally:
        conn.close()
    print(f"\n数据库：{db_path}")
    print(f"本次新增版本：{versions} 个　新增册次锚点：{books} 册")
    print(f"幂等重跑：新增版本 {again_versions} 个　新增册次 {again_books} 册")
    print(f"章节目录：{before_chapters} → {after_chapters}（铁律：不写章节目录）")
    if again_versions or again_books:
        print("幂等检查失败：第二次执行仍有新增", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
