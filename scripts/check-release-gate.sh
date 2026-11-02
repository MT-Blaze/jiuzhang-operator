#!/usr/bin/env bash
# L0 收尾门禁：工序 06、发版前必跑 = 快门禁全部 + 全模块单测 + 探针报告归一。
# 全模块单测会真起 uvicorn（22 个模块），耗时以分钟计；探针执行本身不在这里做。
set -u
cd "$(dirname "$0")/.." || exit 1
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
PY=".venv/Scripts/python.exe"
failures=0

echo "══════ 1/3 快门禁 ══════"
bash scripts/check-quick-gate.sh || failures=$((failures + 1))

echo "══════ 2/3 全模块单测 ══════"
"$PY" tools/run_all_tests.py || failures=$((failures + 1))

echo "══════ 3/3 探针报告归一 ══════"
"$PY" scripts/check_probe_reports.py || failures=$((failures + 1))

echo "════════════════════════════════════════"
if [ "$failures" -eq 0 ]; then
  echo "check-release-gate: PASS（三大块全绿）"
  exit 0
fi
echo "check-release-gate: FAIL（$failures/3 块不合格）"
exit 1
