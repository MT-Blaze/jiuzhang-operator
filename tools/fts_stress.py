# -*- coding: utf-8 -*-
"""FTS5 题干检索压测（军令 #13 任务 5）。

用法：``.venv/Scripts/python.exe tools/fts_stress.py [tag]``

做法：临时目录里造一个 10,000 题的库，分别测
  1. FTS5 建索引耗时；
  2. 300 次真实形态查询（两字词/长短语/公式片段）的 p50 / p95 / 最大值；
  3. 同一批查询走老 ``LIKE`` 的耗时，作为对照口径。
不碰开发者 ``data/``，报告落 ``.system_generated/fts-stress/<tag>/report.json``。
"""
from __future__ import annotations

import json
import random
import sqlite3
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import bank_fts  # noqa: E402

ROWS = 10000
QUERIES = 300
P95_BUDGET_MS = 50.0

NOUNS = ["函数", "方程", "集合", "导数", "向量", "数列", "概率", "三角形", "直线", "圆",
         "不等式", "对数", "指数", "抛物线", "椭圆", "双曲线", "排列", "组合", "极限", "积分"]
VERBS = ["求", "证明", "判断", "化简", "计算", "讨论"]
TAILS = ["的取值范围", "的单调区间", "的解析式", "的零点个数", "的最小值", "的定义域"]


def make_stem(index: int) -> str:
    # 名词与搭配按不同进位取，保证 120 种「名词 + 尾缀」组合都真的出现在样本里；
    # 否则压测会把「数据里没有」误记成「检索查不到」。
    noun = NOUNS[index % len(NOUNS)]
    tail = TAILS[(index // len(NOUNS)) % len(TAILS)]
    verb = VERBS[(index // (len(NOUNS) * len(TAILS))) % len(VERBS)]
    form = ["$f(x)=x^2-2x+1$", "$a_n=a_1+(n-1)d$", "$\\frac{1}{2}$", "$\\sin x$", "$|x-1|$"][index % 5]
    if index % 7 == 0:
        return f"已知{noun}{form}，{verb}{noun}{tail}。"
    return f"设{noun}满足{form}，{verb}{noun}{tail}（第{index}题）。"


def timed(fn):
    start = time.perf_counter()
    value = fn()
    return value, (time.perf_counter() - start) * 1000.0


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(round(ratio * (len(ordered) - 1)))))
    return ordered[index]


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "fts-stress" / tag
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"tag": tag, "rows": ROWS, "queries": QUERIES}

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = Path(tmp) / "stress.db"
        con = sqlite3.connect(db_path)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("CREATE TABLE questions (id TEXT PRIMARY KEY, stem TEXT NOT NULL)")

        rows = [(f"q_{i:05d}", make_stem(i)) for i in range(ROWS)]

        def fill_base() -> int:
            con.executemany("INSERT INTO questions VALUES (?, ?)", rows)
            con.commit()
            return len(rows)

        _, insert_ms = timed(fill_base)
        report["base_insert_ms"] = round(insert_ms, 1)

        if not bank_fts.available():
            report["fts5"] = False
            (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print("FTS5 不可用，压测未执行 ->", out / "report.json")
            return report

        def fill_index() -> int:
            count = bank_fts.rebuild(con)
            con.commit()
            return count

        indexed, index_ms = timed(fill_index)
        report["fts5"] = True
        report["index_ms"] = round(index_ms, 1)
        report["indexed"] = indexed
        report["docs_per_second"] = round(indexed / max(index_ms / 1000.0, 1e-6), 0)

        rng = random.Random(20261024)
        picks: list[str] = []
        for _ in range(QUERIES):
            kind = rng.randrange(4)
            if kind == 0:
                picks.append(rng.choice(NOUNS))
            elif kind == 1:
                picks.append(rng.choice(NOUNS) + rng.choice(TAILS))
            elif kind == 2:
                picks.append("已知" + rng.choice(NOUNS))
            else:
                picks.append(rng.choice(["f(x)", "x^2", "\\frac", "sin x"]))

        fts_times: list[float] = []
        hits = 0
        for query in picks:
            result, elapsed = timed(lambda q=query: bank_fts.query_ids(con, q, limit=20))
            fts_times.append(elapsed)
            hits += 1 if result else 0

        like_times: list[float] = []
        for query in picks:
            like_times.append(timed(lambda q=query: con.execute(
                "SELECT id FROM questions WHERE stem LIKE ? LIMIT 20", (f"%{q}%",)
            ).fetchall())[1])

        report["fts_ms"] = {
            "p50": round(percentile(fts_times, 0.50), 2),
            "p95": round(percentile(fts_times, 0.95), 2),
            "max": round(max(fts_times), 2),
            "mean": round(statistics.fmean(fts_times), 2),
        }
        report["like_ms"] = {
            "p50": round(percentile(like_times, 0.50), 2),
            "p95": round(percentile(like_times, 0.95), 2),
            "max": round(max(like_times), 2),
            "mean": round(statistics.fmean(like_times), 2),
        }
        report["queries_with_hits"] = hits
        report["p95_budget_ms"] = P95_BUDGET_MS
        report["passed"] = report["fts_ms"]["p95"] <= P95_BUDGET_MS and hits > 0
        con.close()

    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "index_ms": report["index_ms"],
        "indexed": report["indexed"],
        "p50": report["fts_ms"]["p50"],
        "p95": report["fts_ms"]["p95"],
        "like_p50": report["like_ms"]["p50"],
        "hits": report["queries_with_hits"],
        "passed": report["passed"],
    }, ensure_ascii=False))
    print("report ->", out / "report.json")
    return report


if __name__ == "__main__":
    result = run(sys.argv[1] if len(sys.argv) > 1 else "task5")
    sys.exit(0 if result.get("passed") else 1)
