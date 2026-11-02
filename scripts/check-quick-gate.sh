#!/usr/bin/env bash
# L0 快门禁：每个阶段收尾必跑（秒级，全部只读）。
# 逐项累积结果，任一失败最终 rc=1——不允许"前面失败后面静默跳过"。
set -u
cd "$(dirname "$0")/.." || exit 1
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
PY=".venv/Scripts/python.exe"

failures=0
steps=0

run_step() {
  local label="$1"; shift
  steps=$((steps + 1))
  echo "── [$label]"
  if "$@"; then
    echo "   ok: $label"
  else
    echo "   FAILED: $label"
    failures=$((failures + 1))
  fi
}

if [ ! -x "$PY" ]; then
  echo "[FAIL] 缺 $PY——门禁必须用项目虚拟环境解释器，系统 Python 会把全部模块打成假报错"
  exit 1
fi

run_step "命名规约 R00"        bash scripts/check-naming.sh
run_step "插件三查与依赖方向"  bash scripts/check-plugin-boundary.sh
run_step "插件包结构红线"      "$PY" scripts/check_plugin_package.py
run_step "索引全等与 Schema"   "$PY" scripts/check_plugin_index_parity.py
run_step "静态红线审计"        "$PY" tools/audit_code.py
run_step "版本单源与 bat 编码" "$PY" -m unittest tests.test_version_consistency

echo "════════════════════════════════════════"
if [ "$failures" -eq 0 ]; then
  echo "check-quick-gate: PASS（$steps 项全过）"
  exit 0
fi
echo "check-quick-gate: FAIL（$failures/$steps 项不合格）"
exit 1
