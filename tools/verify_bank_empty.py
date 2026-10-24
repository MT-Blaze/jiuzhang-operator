# -*- coding: utf-8 -*-
"""空库交付证据：对 v063.db 跑逐表 COUNT(*)，输出核对文件与终端文本。"""
import io
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\jiuzhang-operator")
DB = ROOT / "plugins/org.jiuzhang.core-bank/bank/v063.db"
OUT_MD = ROOT / "data/bank_v063_empty_check.md"

ORDER = ["schools", "topics", "topic_notes", "sources", "questions",
         "question_topics", "question_sources", "bank_meta"]

con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
objects = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
missing = [t for t in ORDER if t not in objects]
extra = [t for t in objects if t not in ORDER]
counts = {t: con.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] for t in objects}
indexes = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'").fetchone()[0]
triggers = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
views = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'").fetchone()[0]
version = con.execute("PRAGMA user_version").fetchone()[0]
integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
fingerprint = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE name LIKE '%fingerprint%' OR name LIKE '%similar%'")]
con.close()

total = sum(counts.values())
import hashlib
schema_sha = hashlib.sha256((ROOT / "plugins/org.jiuzhang.core-bank/bank/schema.sql").read_bytes()).hexdigest()
stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
lines = [
    "core-bank v0.6.3 结构冻结 · 空库核对",
    "库文件 : %s" % DB.relative_to(ROOT).as_posix(),
    "大小   : %s B" % f"{DB.stat().st_size:,}",
    "核对时间: %s（本机本地钟）" % stamp,
    "schema.sql SHA-256 : %s" % schema_sha,
    "user_version : %d   integrity_check : %s" % (version, integrity),
    "表 : %d   索引 : %d   触发器 : %d   视图 : %d" % (len(objects), indexes, triggers, views),
    "",
]
for t in ORDER:
    lines.append('SELECT COUNT(*) FROM "%s";  -- %d' % (t, counts.get(t, -1)))
lines += ["", "总计行数 : %d" % total,
          "缺表 : %s" % (missing or "无"),
          "清单外的表 : %s" % (extra or "无"),
          "指纹/同类题表 : %s" % (fingerprint or "无（已按要求抛弃）")]
text = "\n".join(lines)
print(text)

buf = io.StringIO()
buf.write("# core-bank v0.6.3 空库核对（交付证据）\n\n")
buf.write("- 库：`%s`（%s B）\n" % (DB.relative_to(ROOT).as_posix(), f"{DB.stat().st_size:,}"))
buf.write("- 核对时间：%s（本机本地钟，与军令表头的北京时间差 +9h，机器钟未校）\n" % stamp)
buf.write("- 建库脚本：`plugins/org.jiuzhang.core-bank/bank/schema.sql`"
          "（SHA-256 `%s`）\n" % schema_sha)
buf.write("- user_version：%d · integrity_check：%s · 表 %d / 索引 %d / 触发器 %d / 视图 %d\n\n"
          % (version, integrity, len(objects), indexes, triggers, views))
buf.write("```sql\n")
for t in ORDER:
    buf.write('SELECT COUNT(*) FROM "%s";  -- %d\n' % (t, counts.get(t, -1)))
buf.write("```\n\n| 表 | COUNT(*) |\n|---|---|\n")
for t in ORDER:
    buf.write("| %s | %d |\n" % (t, counts.get(t, -1)))
buf.write("\n**总行数 = %d**；缺表 %s；清单外的表 %s；指纹/同类题表 %s。\n"
          % (total, missing or "无", extra or "无", fingerprint or "无"))
buf.write("\n---\n\n## 终端原文（可直接比对）\n\n```\n%s\n```\n" % text)
OUT_MD.write_text(buf.getvalue(), encoding="utf-8")
print("\n-> %s" % OUT_MD)
