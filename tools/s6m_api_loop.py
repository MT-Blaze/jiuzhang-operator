# -*- coding: utf-8 -*-
"""S6m · tests.test_pending_api 整模块连跑 N 次（默认 10），只报计数与失败原文。

复用 test47_flake_loop 的口径：exit==0 才算过，记录 stderr 尾部原文。
证据写 s6m_api_loop_<时间戳>.toml（新 tag，不覆盖）。
"""
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import toml_io  # noqa: E402

PY = ROOT / ".venv" / "Scripts" / "python.exe"
TARGET = "tests.test_pending_api"
EVIDENCE = (ROOT / ".qoder" / "records" / "biz" / "2026-11" /
            "20261103_order32-s6-evidence")


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    rows = []
    fails = 0
    for i in range(1, runs + 1):
        proc = subprocess.run(
            [str(PY), "-m", "unittest", TARGET],
            cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env={**subprocess.os.environ, "JZO_RESTART_DISABLED": "1",
                 "PYTHONUTF8": "1"})
        blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
        m = re.search(r"Ran (\d+) tests?", blob)
        ran = int(m.group(1)) if m else 0
        ok = proc.returncode == 0 and ran == 33
        if not ok:
            fails += 1
        print(f"[{i:02d}/{runs}] exit={proc.returncode} ran={ran} "
              f"{proc.returncode == 0 and 'OK' or 'FAIL'}", flush=True)
        rows.append({"i": i, "exit": proc.returncode, "ran": ran,
                     "ok": ok,
                     "output_tail": blob[-4000:] if not ok else None})
    body = {"target": TARGET, "runs": runs, "fail_count": fails,
            "rows": rows,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    out = EVIDENCE / f"s6m_api_loop_{time.strftime('%Y%m%d_%H%M%S')}.toml"
    out.write_text(toml_io.dumps(body), encoding="utf-8")
    print(f"EVIDENCE={out.name}")
    print(f"FAILS={fails}/{runs}")


if __name__ == "__main__":
    main()
