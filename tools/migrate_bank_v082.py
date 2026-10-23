# -*- coding: utf-8 -*-
"""core-bank v0.8.2 结构迁移的命令行入口（实现只在 app/core/bank.py 一处）。

user_version 1 → 2：考向改成各教材版本的**并集**（topics 里 tp_kx 不绑版本），
版本身份另立 textbooks，跨版本归属走 node_topic_map「版本目录节点 → 考向」。
现网只有人教A版，本脚本把它登记为默认版本，并让映射表能独立还原当前这棵树。

用法：
    .venv/Scripts/python.exe tools/migrate_bank_v082.py --check      # 只体检（默认，不改库）
    .venv/Scripts/python.exe tools/migrate_bank_v082.py --apply      # 升级（自动落 .pre-v082.bak）
    .venv/Scripts/python.exe tools/migrate_bank_v082.py --path X.db  # 只处理指定文件

底座首启也会对落后的库调用同一个 ``bank.upgrade_structure``；本脚本是给
「交付前离线洗库」和排障用的，两者共用一套 DDL 与自检，不存在第二份实现。
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import bank  # noqa: E402  结构与升级的唯一实现

PLUGIN_ID = "org.jiuzhang.core-bank"
BASE_TABLES = ("schools", "topics", "questions", "topic_notes", "sources",
               "question_topics", "question_sources", "bank_meta")


def inspect(path: Path) -> dict:
    """只读体检：结构版本、新表是否到位、并集不变量、映射能否还原树。"""
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        names = {row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )}
        info: dict = {
            "user_version": int(con.execute("PRAGMA user_version").fetchone()[0]),
            "missing_base": [t for t in BASE_TABLES if t not in names],
            "has_new_tables": all(t in names for t in bank.V082_NEW_TABLES),
            "questions": con.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
            if "questions" in names else -1,
        }
        if "topics" in names:
            columns = {row[1] for row in con.execute("PRAGMA table_info(topics)")}
            info["topics"] = con.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
            info["taxonomy"] = con.execute(
                "SELECT COUNT(*) FROM topics WHERE substr(id, 1, 5) = 'tp_kx'").fetchone()[0]
            info["outline_nodes"] = con.execute(
                "SELECT COUNT(*) FROM topics WHERE substr(id, 1, 5) IN ('tp_bo','tp_ch','tp_se')").fetchone()[0]
            info["textbook_id_column"] = "textbook_id" in columns
            if info["textbook_id_column"]:
                info["bound_taxonomy"] = con.execute(
                    "SELECT COUNT(*) FROM topics WHERE substr(id, 1, 5) = 'tp_kx' "
                    "AND textbook_id IS NOT NULL").fetchone()[0]
                info["unowned_outline"] = con.execute(
                    "SELECT COUNT(*) FROM topics WHERE substr(id, 1, 5) IN ('tp_bo','tp_ch','tp_se') "
                    "AND textbook_id IS NULL").fetchone()[0]
        if info["has_new_tables"]:
            info["textbooks"] = con.execute("SELECT COUNT(*) FROM textbooks").fetchone()[0]
            info["map_rows"] = con.execute("SELECT COUNT(*) FROM node_topic_map").fetchone()[0]
            info["tree_reproducible"] = con.execute(
                """SELECT COUNT(*) FROM topics t WHERE substr(t.id, 1, 5) = 'tp_kx'
                         AND t.parent_id IS NOT NULL AND NOT EXISTS
                   (SELECT 1 FROM node_topic_map m
                    WHERE m.topic_id = t.id AND m.outline_node_id = t.parent_id)"""
            ).fetchone()[0]
            row = con.execute("SELECT name FROM textbooks WHERE is_default = 1").fetchone()
            info["default_textbook"] = row[0] if row else None
        return info
    finally:
        con.close()


def default_targets() -> list[Path]:
    targets = [
        ROOT / "data/banks/org.jiuzhang.core-bank.db",
        ROOT / "plugins/org.jiuzhang.core-bank/bank/bank.db",
    ]
    return [path for path in targets if path.is_file()]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    parser = argparse.ArgumentParser(description="core-bank v0.8.2 多版本地基迁移")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="只体检，不改库（默认）")
    group.add_argument("--apply", action="store_true", help="升级到 user_version=2，先落备份")
    parser.add_argument("--path", help="只处理指定 .db（默认处理现网库与本地种子库）")
    args = parser.parse_args()

    paths = [Path(args.path)] if args.path else default_targets()
    if not paths:
        print("没有找到待处理的库文件。")
        return 1
    failures = 0
    for path in paths:
        report = inspect(path)
        if report["missing_base"]:
            failures += 1
            print(f"[FAIL] {path.name}: 缺基础表，拒绝处理 {report['missing_base']}")
            continue
        if args.apply:
            try:
                result = bank.upgrade_structure(PLUGIN_ID, path)
            except bank.BankError as exc:
                failures += 1
                print(f"[FAIL] {path.name}: {exc}")
                continue
            flag = "APPLY" if result["upgraded"] else "SKIP"
            extra = (f" · 映射行 {result['map_rows']} · 备份 {result['backup']}"
                     if result["upgraded"] else " · 已是 v2，未改动")
            print(f"[{flag}] {path.name}{extra}")
            report = inspect(path)
        else:
            print(f"[CHECK] {path.name}")
        print(f"       user_version={report['user_version']} · 题 {report['questions']} · "
              f"考向 {report['taxonomy']}（并集）· 目录节点 {report['outline_nodes']} · "
              f"新表={report['has_new_tables']} · textbook_id 列={report.get('textbook_id_column')}")
        print(f"       默认版本={report.get('default_textbook')} · 映射行={report.get('map_rows')} · "
              f"还原不出的父子={report.get('tree_reproducible')} · "
              f"被绑版本的考向={report.get('bound_taxonomy')} · "
              f"无版本归属的目录节点={report.get('unowned_outline')}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
