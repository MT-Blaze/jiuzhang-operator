#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
export PYTHONUTF8=1
PY=".venv/Scripts/python.exe"
echo "##A1 editor_probe"; $PY tools/editor_probe.py s9b-ed1 2>&1 | tail -3
echo "##A2 latex_clean_probe"; $PY tools/latex_clean_probe.py s9b-latex1 2>&1 | tail -3
echo "##A3 pool_canvas_probe"; $PY tools/pool_canvas_probe.py s9b-pool1 2>&1 | tail -3
echo "##B s9b_browser_proof"; $PY tools/s9b_browser_proof.py s9bbr1 2>&1 | tail -14
echo "##A4 check-probe-reports"; bash scripts/check-probe-reports.sh 2>&1 | tail -10
echo "##C1 modules"
for m in test_editor_contract test_stage_tab_group test_workspace_fold_state test_command_registry; do
  echo "-- $m"; JZO_RESTART_DISABLED=1 $PY -m unittest tests.$m 2>&1 | tail -3
done
echo "##C2 plugin-package"; bash scripts/check-plugin-package.sh 2>&1 | tail -2
echo "##C3 quick-gate"; bash scripts/check-quick-gate.sh 2>&1 | tail -2
echo "##DONE"
