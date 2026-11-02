#!/usr/bin/env bash
# L0 门禁：插件侧三查 + 依赖方向红线（docs/AGENTS.md 铁律二、机械证据回传单第 3 项）
# 只读，不写任何文件。插件打包时排除 dev/（tools/build_plugin.py:36-44），
# 所以 dev/ 下的调试页允许出现 fetch(，不纳入三查统计。
set -u
cd "$(dirname "$0")/.." || exit 1

SCOPE_INCLUDES=(--include=*.js --include=*.html --include=*.css --include=*.json --include=*.py)
EXCLUDES=(--exclude-dir=dev --exclude-dir=node_modules --exclude-dir=__pycache__)
PATTERNS=("fetch(" "parent.document" "localStorage")
fail=0

for pattern in "${PATTERNS[@]}"; do
  hits=$(grep -rnF "${EXCLUDES[@]}" "${SCOPE_INCLUDES[@]}" -- "$pattern" plugins/ 2>/dev/null)
  count=$(printf '%s' "$hits" | grep -c . || true)
  if [ "$count" -ne 0 ]; then
    echo "[FAIL] 插件侧三查命中：$pattern（$count 处，必须为 0）"
    printf '%s\n' "$hits" | head -10
    fail=1
  else
    echo "[PASS] 插件侧三查：$pattern 命中 0"
  fi
done

py_files=$(find plugins -name '*.py' -not -path '*/dev/*' 2>/dev/null | grep -c . || true)
if [ "$py_files" -ne 0 ]; then
  echo "[FAIL] plugins/ 下出现 Python 文件（$py_files 个），底座与插件之间不允许代码依赖"
  find plugins -name '*.py' -not -path '*/dev/*' | head -10
  fail=1
else
  echo "[PASS] plugins/ 内无 Python 文件"
fi

host_fetch=$(grep -rlF "${SCOPE_INCLUDES[@]}" -- "fetch(" static/js 2>/dev/null | grep -c . || true)
echo "[INFO] 宿主侧 static/js 中带 fetch( 的文件数：$host_fetch（出网必须由用户当场点击发起，见 docs/AGENTS.md §2）"

if [ "$fail" -ne 0 ]; then
  echo "check-plugin-boundary: FAIL"
  exit 1
fi
echo "check-plugin-boundary: PASS（三查 0 命中、插件零 Python 依赖）"
