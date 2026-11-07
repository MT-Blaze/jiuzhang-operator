# -*- coding: utf-8 -*-
"""清空题库题目数据（保留知识树、教材版本与学校字典）。

用途：给全新标签体系腾出干净场地。物理删除范围仅限：

- 主库 ``questions`` 与其关系表 ``question_topics`` / ``question_sources``；
- 主库 FTS5 虚拟表 ``question_fts``（含其影子表由 SQLite 自行维护）；
- 待审池 ``pending.db`` 的批次、条目、初查结论与重题池数据。

``topics``、``textbooks``、``schools``、``sources``、``topic_notes``、
``node_topic_map``、``bank_meta`` 以及待审池的字典表一律不碰；脚本在提交前
重新点数，发现受保护表行数有任何变化就整事务回滚。

安全措施：必须带 ``--confirm`` 才执行；执行前先用 SQLite 备份 API 把两份库
原样落成 ``*.pre-clear-<时间戳>.bak``；所有删除在 ``BEGIN IMMEDIATE`` 事务内完成。
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 只允许删除这些表；任何新增表都必须先在这里登记，防止手滑扩大删除面。
BANK_DELETE_TABLES = (
    "question_topics",
    "question_sources",
    "question_fts",
    "questions",
)
BANK_PROTECTED_TABLES = (
    "schools",
    "textbooks",
    "topics",
    "topic_notes",
    "sources",
    "node_topic_map",
    "bank_meta",
)
PENDING_DELETE_TABLES = (
    "pending_questions",
    "batches",
    "dedupe_findings",
    "dedupe_scans",
    "duplicate_pool",
    "pool_actions",
)
PENDING_PROTECTED_TABLES = (
    "schools",
    "scene_types",
    "exam_types",
    "meta_history",
)

# 表名全部是脚本内常量；集中成固定语句表，执行处不再拼 SQL。
_COUNT_SQL = {
    name: f"SELECT COUNT(*) FROM {name}"
    for name in (
        *BANK_DELETE_TABLES,
        *BANK_PROTECTED_TABLES,
        *PENDING_DELETE_TABLES,
        *PENDING_PROTECTED_TABLES,
    )
}
_DELETE_SQL = {
    name: f"DELETE FROM {name}" for name in (*BANK_DELETE_TABLES, *PENDING_DELETE_TABLES)
}


class ClearError(RuntimeError):
    pass


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=30.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 15000")
    return con


def _tables(con: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _counts(con: sqlite3.Connection, names: Iterable[str]) -> dict[str, int | None]:
    existing = _tables(con)
    result: dict[str, int | None] = {}
    for name in names:
        result[name] = (
            int(con.execute(_COUNT_SQL[name]).fetchone()[0]) if name in existing else None
        )
    return result


def _backup(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.name}.pre-clear-{stamp}.bak")
    source = sqlite3.connect(path, timeout=30.0)
    try:
        dest = sqlite3.connect(target)
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()
    return target


def _clear_database(
    path: Path,
    delete_tables: tuple[str, ...],
    protected_tables: tuple[str, ...],
    label: str,
) -> dict[str, object]:
    """在一个 BEGIN IMMEDIATE 事务里清表，提交前核对受保护表行数。"""
    con = _connect(path)
    try:
        existing = _tables(con)
        before = _counts(con, [*delete_tables, *protected_tables])
        protected_before = _counts(con, protected_tables)

        con.execute("BEGIN IMMEDIATE")
        try:
            for table in delete_tables:
                if table not in existing:
                    continue
                con.execute(_DELETE_SQL[table])

            protected_after = _counts(con, protected_tables)
            if protected_after != protected_before:
                changed = {
                    name: (protected_before[name], protected_after[name])
                    for name in protected_tables
                    if protected_before[name] != protected_after[name]
                }
                raise ClearError(f"{label} 受保护表行数异常：{changed}")
            con.commit()
        except BaseException:
            con.rollback()
            raise

        after = _counts(con, [*delete_tables, *protected_tables])
        return {
            "path": str(path),
            "before": before,
            "after": after,
        }
    finally:
        con.close()


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.bank_db and args.pending_db:
        return Path(args.bank_db), Path(args.pending_db)

    from app.core import config
    from app.core.bank_provider import DEFAULT_PROVIDER_ID
    from app.core.bank_schema import bank_db_path
    from app.core.pending_db import pending_db_path

    config.load_current_workspace()
    bank = Path(args.bank_db) if args.bank_db else bank_db_path(DEFAULT_PROVIDER_ID, create=False)
    pending = Path(args.pending_db) if args.pending_db else pending_db_path()
    return bank, pending


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="清空题库题目数据（保留知识树、教材版本与学校字典）"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="确认执行物理删除；不带此参数直接报错退出。",
    )
    parser.add_argument("--bank-db", help="覆盖主库路径（测试用）")
    parser.add_argument("--pending-db", help="覆盖待审池路径（测试用）")
    args = parser.parse_args(argv)

    if not args.confirm:
        print(
            "拒绝执行：本脚本会物理删除所有题目数据。确认无误后请加 --confirm 重跑。",
            file=sys.stderr,
        )
        return 2

    try:
        bank_path, pending_path = _resolve_paths(args)
    except Exception as exc:  # noqa: BLE001 - 路径解析失败要给人话而不是栈
        print(f"路径解析失败：{exc}", file=sys.stderr)
        return 1

    if not bank_path.is_file():
        print(f"主库不存在：{bank_path}", file=sys.stderr)
        return 1

    print(f"主库：{bank_path}")
    print(f"待审池：{pending_path}（不存在则跳过）")

    try:
        bank_backup = _backup(bank_path)
        print(f"主库备份：{bank_backup.name}")
        if pending_path.is_file():
            print(f"待审池备份：{_backup(pending_path).name}")
        bank_result = _clear_database(
            bank_path, BANK_DELETE_TABLES, BANK_PROTECTED_TABLES, "主库"
        )
        print(
            "主库完成："
            f"questions {bank_result['before']['questions']} → {bank_result['after']['questions']}，"
            f"question_topics {bank_result['before']['question_topics']} → "
            f"{bank_result['after']['question_topics']}，"
            f"question_sources {bank_result['before']['question_sources']} → "
            f"{bank_result['after']['question_sources']}，"
            f"question_fts {bank_result['before']['question_fts']} → "
            f"{bank_result['after']['question_fts']}"
        )
        print(
            "知识树/字典保持："
            f"topics={bank_result['after']['topics']}，"
            f"textbooks={bank_result['after']['textbooks']}，"
            f"schools={bank_result['after']['schools']}，"
            f"sources={bank_result['after']['sources']}"
        )

        if pending_path.is_file():
            pending_result = _clear_database(
                pending_path, PENDING_DELETE_TABLES, PENDING_PROTECTED_TABLES, "待审池"
            )
            print(
                "待审池完成："
                f"pending_questions {pending_result['before']['pending_questions']} → "
                f"{pending_result['after']['pending_questions']}，"
                f"batches {pending_result['before']['batches']} → "
                f"{pending_result['after']['batches']}，"
                f"duplicate_pool {pending_result['before']['duplicate_pool']} → "
                f"{pending_result['after']['duplicate_pool']}，"
                f"dedupe_findings {pending_result['before']['dedupe_findings']} → "
                f"{pending_result['after']['dedupe_findings']}"
            )
            print(
                "待审字典保持："
                f"scene_types={pending_result['after']['scene_types']}，"
                f"exam_types={pending_result['after']['exam_types']}"
            )
        else:
            print("待审池不存在，跳过。")
    except ClearError as exc:
        print(f"清库失败（已回滚）：{exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"数据库操作失败（已回滚）：{exc}", file=sys.stderr)
        return 1

    print("清空完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
