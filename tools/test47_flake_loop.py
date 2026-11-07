# -*- coding: utf-8 -*-
"""军令 #32 · S6i：判据 5.4 抖动复验——``test_47`` 连跑 N 次，原样记录每一拍。

只读产品、只跑现成用例，**不改期望值、不写 tests/**。
每次跑一台自起的隔离服务由用例自己的 ``setUpClass`` 负责（本脚本按「一次子进程 =
一次该用例」调度，父类其余用例不入选）；Windows 下子进程句柄与临时目录由
``unittest`` 自己收，脚本只做「计数 + 原文留证」。

用法：
    JZO_RESTART_DISABLED=1 .venv/Scripts/python.exe tools/test47_flake_loop.py 50
产物（新 tag，不覆盖）：
    .qoder/records/biz/2026-11/20261103_order32-s6-evidence/s6i_test47_loop_<ts>.toml
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
TARGET = "tests.test_pending_api.PoolEvictionHttpTest.test_47_http_done_first_frame_already_has_pooled"
EVIDENCE = ROOT / ".qoder" / "records" / "biz" / "2026-11" / "20261103_order32-s6-evidence"
RAN_RE = re.compile(r"Ran (\d+) tests?")
TIME_RE = re.compile(r"Ran \d+ tests? in ([\d.]+)s")


def main() -> int:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    rows = []
    for i in range(1, runs + 1):
        env = dict(__import__("os").environ)
        env["JZO_RESTART_DISABLED"] = "1"
        env["PYTHONUTF8"] = "1"
        started = time.time()
        p = subprocess.run([str(PY), "-m", "unittest", TARGET],
                           cwd=str(ROOT), env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        elapsed = round(time.time() - started, 2)
        blob = (p.stdout or "") + (p.stderr or "")
        m = RAN_RE.search(blob)
        ran = int(m.group(1)) if m else None
        rows.append({
            "i": i, "exit": p.returncode, "ran": ran,
            "seconds": elapsed,
            "ok": p.returncode == 0 and ran == 1,
            "output_tail": blob[-4000:] if p.returncode != 0 else "",
        })
        print(f"[{i:02d}/{runs}] exit={p.returncode} ran={ran} {elapsed}s", flush=True)
    fails = [r for r in rows if not r["ok"]]
    out = {
        "started": datetime.now().isoformat(timespec="seconds"),
        "target": TARGET, "runs": runs,
        "fail_count": len(fails),
        "pass_count": runs - len(fails),
        "seconds_min": min(r["seconds"] for r in rows),
        "seconds_max": max(r["seconds"] for r in rows),
        "seconds_avg": round(sum(r["seconds"] for r in rows) / len(rows), 2),
        "runs_with_ran_not_one": [r["i"] for r in rows if r["ran"] != 1],
        "failures": fails,
        "rows": [{k: v for k, v in r.items() if k != "output_tail"} for r in rows],
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / f"s6i_test47_loop_{time.strftime('%Y%m%d_%H%M%S')}.toml"
    path.write_text(toml_io.dumps(out), encoding="utf-8")
    print("EVIDENCE=" + path.name)
    print(f"FAILS={len(fails)}/{runs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
