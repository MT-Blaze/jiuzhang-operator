"""逐模块跑 unittest（AGENTS §7：不许引入 pytest，且必须用 .venv 的解释器）。"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
modules = sorted(path.stem for path in (ROOT / "tests").glob("test_*.py"))

failed = []
total = 0
for name in modules:
    proc = subprocess.run([str(PY), "-m", "unittest", "tests.%s" % name],
                          cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    # unittest 的统计行打在 stderr 上（"Ran N tests in ..."）
    merged = proc.stdout + "\n" + proc.stderr
    match = re.search(r"Ran (\d+) tests?", merged)
    count = int(match.group(1)) if match else 0
    total += count
    ok = proc.returncode == 0
    if not ok:
        failed.append(name)
        print("FAIL %-40s %s" % (name, proc.stderr.strip()[-600:]))
    else:
        print("OK   %-40s %d" % (name, count))

print("=" * 60)
print("模块 %d 个，用例 %d 个，失败模块 %d 个" % (len(modules), total, len(failed)))
if failed:
    print("失败：", ", ".join(failed))
    sys.exit(1)
print("全绿")
