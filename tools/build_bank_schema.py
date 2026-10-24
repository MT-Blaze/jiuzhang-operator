# -*- coding: utf-8 -*-
"""结构冻结轮专用：用 bank/schema.sql 建一个 0 数据的 core-bank v063 空库。

本工具**不搬任何题目数据**（17:30 冻结令）。它只做三件事：
建空库 → 自检表结构与约束 → 出一份给主公审阅的结构报告。

用法：
    .venv/Scripts/python.exe tools/build_bank_schema.py            # 建库 + 自检 + 报告
    .venv/Scripts/python.exe tools/build_bank_schema.py --check    # 只自检，不重建
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_PATH = ROOT / "plugins" / "org.jiuzhang.core-bank" / "bank" / "schema.sql"
DB_PATH = ROOT / "plugins" / "org.jiuzhang.core-bank" / "bank" / "v063.db"
REPORT_PATH = ROOT / "data" / "bank_schema_freeze_report.md"

SCHEMA_VERSION = 2
EXPECTED_TABLES = (
    "schools",
    "topics",
    "questions",
    "topic_notes",
    "sources",
    "question_topics",
    "question_sources",
    "bank_meta",
    # v0.8.2 多版本地基：教材版本登记表 + 版本目录节点→考向 映射表
    "textbooks",
    "node_topic_map",
)
BANNED_TABLE_TOKENS = ("fingerprint", "similar", "same_type", "dedup")
CHECK_PATH = ROOT / "data" / "bank_v063_empty_check.md"


def build(db_path: Path) -> bytes:
    sql = SCHEMA_PATH.read_bytes()
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_path) + suffix)
        if candidate.exists():
            candidate.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.executescript(sql.decode("utf-8"))
        con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        con.commit()
        violations = list(con.execute("PRAGMA foreign_key_check"))
        if violations:
            raise SystemExit(f"外键自检失败：{violations}")
    finally:
        con.close()
    return sql


def inspect(db_path: Path) -> dict:
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    out: dict = {
        "user_version": con.execute("PRAGMA user_version").fetchone()[0],
        "integrity": con.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_keys_violation": list(con.execute("PRAGMA foreign_key_check")),
        "tables": [],
        "views": [r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='view'")],
        "triggers": [r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='trigger'")],
    }
    for row in con.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
    ):
        name = row["name"]
        cols = [
            {
                "cid": c["cid"],
                "name": c["name"],
                "type": c["type"],
                "notnull": bool(c["notnull"]),
                "default": c["dflt_value"],
                "pk": bool(c["pk"]),
            }
            for c in con.execute(f'PRAGMA table_info("{name}")')
        ]
        fks = [dict(f) for f in con.execute(f'PRAGMA foreign_key_list("{name}")')]
        counts = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        checks = [
            r["sql"]
            for r in con.execute("SELECT sql FROM sqlite_master WHERE type='CHECK'")
        ] if False else []
        out["tables"].append(
            {"name": name, "columns": cols, "foreign_keys": fks, "rows": counts, "ddl": row["sql"]}
        )
    con.close()
    return out


def verify(info: dict) -> list[str]:
    problems: list[str] = []
    names = [t["name"] for t in info["tables"]]
    missing = [t for t in EXPECTED_TABLES if t not in names]
    extra = [t for t in names if t not in EXPECTED_TABLES]
    if missing:
        problems.append("缺表：" + ", ".join(missing))
    if extra:
        problems.append("多出未在军令清单内的表：" + ", ".join(extra))
    if info["integrity"] != "ok":
        problems.append("integrity_check 不为 ok：" + str(info["integrity"]))
    if info["foreign_keys_violation"]:
        problems.append("foreign_key_check 有违规")
    if int(info["user_version"]) != SCHEMA_VERSION:
        problems.append(f"user_version={info['user_version']}，期望 {SCHEMA_VERSION}")
    for t in info["tables"]:
        if t["rows"] != 0:
            problems.append(f"{t['name']} 不为空（{t['rows']} 行）")
        lowered = t["name"].lower()
        for token in BANNED_TABLE_TOKENS:
            if token in lowered:
                problems.append(f"{t['name']} 命中禁用表名片段 {token}")
    q = next((t for t in info["tables"] if t["name"] == "questions"), None)
    if q:
        ddl = (q["ddl"] or "").lower()
        for column in ("id", "type", "stem", "options", "answer", "solution",
                       "extensions", "difficulty", "created_at", "updated_at"):
            if column not in ddl:
                problems.append(f"questions 缺列 {column}")
        if "'L1'" not in q["ddl"] or "'L4'" not in q["ddl"]:
            problems.append("questions.difficulty 未含 L1–L4 CHECK")
    return problems


def report(db_path: Path, info: dict, problems: list[str], digest: str) -> str:
    buf = io.StringIO()
    buf.write("# core-bank 存储层结构冻结报告（v0.6.3）\n\n")
    buf.write(f"- 建表脚本：`{SCHEMA_PATH.relative_to(ROOT).as_posix()}`\n")
    buf.write(f"- 空库文件：`{db_path.relative_to(ROOT).as_posix()}`（{db_path.stat().st_size:,} B）\n")
    buf.write(f"- schema.sql SHA-256：`{digest}`\n")
    buf.write(f"- user_version：{info['user_version']} · integrity_check：{info['integrity']} · "
              f"业务表行数：{sum(t['rows'] for t in info['tables'])}\n\n")
    buf.write("## 空库核对（SELECT COUNT(*)，逐表）\n\n")
    buf.write("| 表 | COUNT(*) | 军令清单 |\n|---|---|---|\n")
    for t in info["tables"]:
        buf.write("| %s | %d | %s |\n" % (
            t["name"], t["rows"], "在列" if t["name"] in EXPECTED_TABLES else "附加"))
    buf.write("\n")
    buf.write("## 表与约束\n\n")
    for t in info["tables"]:
        buf.write(f"### `{t['name']}`（{len(t['columns'])} 列，{t['rows']} 行）\n\n")
        buf.write("| 列 | 类型 | NOT NULL | 默认 | PK |\n|---|---|---|---|---|\n")
        for c in t["columns"]:
            buf.write("| %s | %s | %s | %s | %s |\n" % (
                c["name"], c["type"] or "—", "是" if c["notnull"] else "否",
                c["default"] if c["default"] is not None else "—", "是" if c["pk"] else ""))
        if t["foreign_keys"]:
            buf.write("\n外键：")
            buf.write("；".join(
                "%s(%s) → %s(%s) %s" % (
                    f["table"], f["from"], f["table"], f["to"],
                    "ON DELETE " + (f["on_update"] and "" or "") + str(f.get("on_delete") or "NO ACTION")
                ) for f in t["foreign_keys"]))
            buf.write("\n")
        buf.write("\n```sql\n%s\n```\n\n" % (t["ddl"] or "").strip())
    buf.write("## 自检结论\n\n")
    if problems:
        buf.write("存在问题：\n\n")
        for p in problems:
            buf.write("- %s\n" % p)
    else:
        buf.write("7 张业务表 + bank_meta 全部就位，库为 0 数据，无指纹/同类题表，外键与约束自检通过。\n")
    return buf.getvalue()


def write_empty_check(db_path: Path, info: dict, digest: str) -> None:
    lines = [
        "# core-bank v063 空库核对（0 数据）",
        "",
        "- 库：`%s`（%s B）" % (db_path.relative_to(ROOT).as_posix(), f"{db_path.stat().st_size:,}"),
        "- schema.sql SHA-256：`%s`" % digest,
        "- 建库命令：`.venv/Scripts/python.exe tools/build_bank_schema.py`",
        "",
        "```sql",
    ]
    for t in info["tables"]:
        lines.append('SELECT COUNT(*) FROM "%s";  -- %d' % (t["name"], t["rows"]))
    lines.append("```")
    lines.append("")
    lines.append("逐表 COUNT(*)：")
    lines.append("")
    lines.append("| 表 | COUNT(*) |")
    lines.append("|---|---|")
    for t in info["tables"]:
        lines.append("| %s | %d |" % (t["name"], t["rows"]))
    CHECK_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECK_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="core-bank v0.6.3 结构冻结建库")
    parser.add_argument("--check", action="store_true", help="只自检现有空库，不重建")
    parser.add_argument("--db", default=str(DB_PATH))
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    db_path = Path(args.db)
    digest = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
    if not args.check:
        build(db_path)
    info = inspect(db_path)
    problems = verify(info)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report(db_path, info, problems, digest), encoding="utf-8")
    write_empty_check(db_path, info, digest)

    print(json.dumps({
        "db": str(db_path),
        "bytes": db_path.stat().st_size if db_path.exists() else 0,
        "schema_sha256_12": digest[:12],
        "tables": [t["name"] for t in info["tables"]],
        "total_rows": sum(t["rows"] for t in info["tables"]),
        "user_version": info["user_version"],
        "integrity": info["integrity"],
        "problems": problems,
        "report": str(REPORT_PATH),
    }, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
