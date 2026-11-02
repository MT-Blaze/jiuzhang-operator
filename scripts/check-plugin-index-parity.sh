#!/usr/bin/env bash
# R00 命名入口：实际校验逻辑在同名 .py（scripts/check_plugin_index_parity.py），只读，rc=1 即违反 L0。
set -u
cd "$(dirname "$0")/.." || exit 1
export PYTHONUTF8=1
exec .venv/Scripts/python.exe scripts/check_plugin_index_parity.py "$@"
