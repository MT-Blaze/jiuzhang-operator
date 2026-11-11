"""补齐「梅河口市」区划节点，并把梅河口市第五中学重新挂到该节点上，幂等可重跑。

梅河口市是吉林省直管县级市（国标 220581），dim_regions 只有省 / 地两级，
故按地级节点挂在「吉林」省下；只写 dim_regions / dim_schools 两表，不动其它数据。
用法：
    python scripts/fix_meihekou_region.py
    python scripts/fix_meihekou_region.py --db data/banks/xxx.db
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bank_engine import paths  # noqa: E402

PROVINCE_CODE = "220000"
REGION_NAME = "梅河口市"
REGION_CODE = "220581"
REGION_SORT = 10
SCHOOL_NAME = "梅河口市第五中学"


def _backup(db_path: Path) -> Path | None:
    target = db_path.with_name(db_path.name + ".pre-meihekou.bak")
    if target.exists():
        return target
    shutil.copy2(db_path, target)
    return target


def _province_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT id FROM dim_regions WHERE code = ?", (PROVINCE_CODE,)).fetchone()
    if row is None:
        raise SystemExit("找不到吉林省节点（220000），请先确认区划种子已落库")
    return int(row[0])


def _region_id(conn: sqlite3.Connection, province_id: int) -> tuple[int, bool]:
    row = conn.execute("SELECT id, parent_id FROM dim_regions WHERE code = ?", (REGION_CODE,)).fetchone()
    if row is not None:
        if int(row[1]) != province_id:
            raise SystemExit("220581 已存在但不挂在吉林省下，请人工核对")
        return int(row[0]), False
    new_id = int(conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM dim_regions").fetchone()[0])
    conn.execute(
        "INSERT INTO dim_regions (id, name, code, level, parent_id, sort_order) "
        "VALUES (?, ?, ?, 2, ?, ?)",
        (new_id, REGION_NAME, REGION_CODE, province_id, REGION_SORT),
    )
    return new_id, True


def _relink_school(conn: sqlite3.Connection, region_id: int) -> tuple[int, bool]:
    row = conn.execute("SELECT id, region_id FROM dim_schools WHERE name = ?", (SCHOOL_NAME,)).fetchone()
    if row is None:
        raise SystemExit(f"找不到学校「{SCHOOL_NAME}」")
    school_id = int(row[0])
    if row[1] == region_id:
        return school_id, False
    conn.execute("UPDATE dim_schools SET region_id = ? WHERE id = ?", (region_id, school_id))
    return school_id, True


def apply_fix(conn: sqlite3.Connection) -> dict[str, object]:
    province_id = _province_id(conn)
    with conn:
        region_id, created = _region_id(conn, province_id)
        school_id, relinked = _relink_school(conn, region_id)
    return {
        "region_id": region_id,
        "created": created,
        "school_id": school_id,
        "relinked": relinked,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="补齐梅河口市区划并重挂学校")
    parser.add_argument("--db", type=Path, default=None, help="默认写入当前活跃引擎库")
    args = parser.parse_args(argv)
    db_path = args.db or paths.engine_db_path()
    backup = _backup(db_path) if db_path.exists() else None
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        first = apply_fix(conn)
        again = apply_fix(conn)
        total = int(conn.execute("SELECT COUNT(*) FROM dim_schools").fetchone()[0])
        nulls = int(
            conn.execute("SELECT COUNT(*) FROM dim_schools WHERE region_id IS NULL").fetchone()[0]
        )
        region = conn.execute(
            "SELECT id, name, code, level, parent_id FROM dim_regions WHERE code = ?",
            (REGION_CODE,),
        ).fetchone()
        school = conn.execute(
            "SELECT id, name, region, region_id FROM dim_schools WHERE id = ?",
            (first["school_id"],),
        ).fetchone()
    finally:
        conn.close()
    print(f"数据库：{db_path}")
    if backup:
        print(f"备份：{backup}")
    print(f"区划节点：{region}")
    print(f"学校：{school}")
    print(f"学校总数：{total}　region_id 为空：{nulls}")
    print(f"首次：新增区划 {int(first['created'])} 条，重挂学校 {int(first['relinked'])} 条")
    print(f"幂等重跑：新增区划 {int(again['created'])} 条，重挂学校 {int(again['relinked'])} 条")
    if again["created"] or again["relinked"] or nulls:
        print("幂等或挂接检查失败", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
