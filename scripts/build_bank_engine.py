"""题库引擎 v2 建库脚本：建 32 表并灌入全量种子，可重复执行。

用法：
    python scripts/build_bank_engine.py            # 缺库/坏库才重建
    python scripts/build_bank_engine.py --force    # 强制重建（旧库先备份）
    python scripts/build_bank_engine.py --status   # 只打印现状，不建库
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bank_engine import builder, paths, service  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建九章题库引擎 v2")
    parser.add_argument("--force", action="store_true", help="强制重建（旧库先备份）")
    parser.add_argument("--db", type=Path, default=None, help="自定义数据库路径")
    parser.add_argument("--status", action="store_true", help="只打印现状")
    args = parser.parse_args(argv)

    if args.status:
        report = service.status(args.db)
        print(f"数据库：{report.db_path}")
        print(f"schema_version：{report.schema_version}")
        print(f"表数量：{report.table_count}")
        print(f"integrity_check：{report.integrity}")
        print(f"外键违规：{report.foreign_key_violations}")
        for table, count in report.counts.items():
            print(f"  {table}: {count}")
        return 0

    report = builder.build_engine(force=args.force, db_path=args.db)
    print(f"数据库：{report.db_path}")
    print(f"本次新建：{'是' if report.created else '否（复用已有合法库）'}")
    for table, count in report.counts.items():
        print(f"  {table}: {count}")
    print(f"schema：{paths.schema_path()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
