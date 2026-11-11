"""把高中数学 / 物理教材版本与册次目录补进已有引擎库，幂等可重跑。

用法：
    python scripts/load_hs_textbook_catalog.py
    python scripts/load_hs_textbook_catalog.py --db data/banks/xxx.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bank_engine import paths  # noqa: E402
from app.bank_engine.seeds.textbook_catalog import (  # noqa: E402
    CATALOG_BOOK_ROWS,
    CATALOG_VERSION_ROWS,
)


def apply_catalog(conn: sqlite3.Connection) -> tuple[int, int]:
    conn.execute("PRAGMA foreign_keys = ON")
    book_codes = [row[2] for row in CATALOG_BOOK_ROWS]
    version_codes = [row[2] for row in CATALOG_VERSION_ROWS]
    with conn:
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
    marks = ",".join("?" for _ in book_codes)
    books = int(conn.execute(
        "SELECT COUNT(*) FROM dim_textbooks WHERE code IN (" + marks + ")", book_codes
    ).fetchone()[0])
    marks = ",".join("?" for _ in version_codes)
    versions = int(conn.execute(
        "SELECT COUNT(*) FROM dim_textbook_versions WHERE code IN (" + marks + ")",
        version_codes,
    ).fetchone()[0])
    if books != len(CATALOG_BOOK_ROWS) or versions != len(CATALOG_VERSION_ROWS):
        raise SystemExit(
            f"目录写入不完整：版本 {versions}/{len(CATALOG_VERSION_ROWS)}，"
            f"册次 {books}/{len(CATALOG_BOOK_ROWS)}"
        )
    return versions, books


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补齐高中数学 / 物理教材目录")
    parser.add_argument("--db", type=Path, default=None, help="默认写入当前活跃引擎库")
    args = parser.parse_args(argv)
    db_path = args.db or paths.engine_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        versions, books = apply_catalog(conn)
    finally:
        conn.close()
    print(f"数据库：{db_path}")
    print(f"新增/已存在的目录版本：{versions} 个")
    print(f"新增/已存在的目录册次：{books} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
