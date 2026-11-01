#!/usr/bin/env bash
# 逐模块跑 unittest，按退出码 + 输出里任意位置的 "OK" 行判胜负。
# 不能只看 tail -3：ResourceWarning 会把 OK 行挤出去,曾误报过一次假失败。
cd "$(dirname "$0")/.." || exit 2
PY=".venv/Scripts/python.exe"
OUT=".system_generated/sweep"
mkdir -p "$OUT"
pass=0
fail=0
failed=""
for f in tests/test_*.py; do
  mod=$(basename "$f" .py)
  log="$OUT/$mod.log"
  if "$PY" -m unittest "tests.$mod" >"$log" 2>&1; then
    if grep -q "^OK" "$log"; then
      pass=$((pass+1))
    else
      fail=$((fail+1)); failed="$failed $mod(no-OK-line)"
      echo "FAIL(no OK line) $mod"
    fi
  else
    fail=$((fail+1)); failed="$failed $mod"
    echo "FAIL $mod"
  fi
done
echo "=== sweep done: pass=$pass fail=$fail ==="
[ -n "$failed" ] && echo "failed:$failed"
exit $((fail>0))
