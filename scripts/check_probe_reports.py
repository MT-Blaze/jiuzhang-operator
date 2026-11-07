# -*- coding: utf-8 -*-
"""探针报告归一判定（收尾门禁，只读）。

判据归一复用 tools/clean_for_release.py 的 probe_verdict（同时认三种历史 schema：
checks[]+passed/total、只有 checks[]、只有 failures 计数；认不出 schema 一律算不通过）。
每个探针只取**最新一份** probe.toml 判定，历史红跑批不追究（否则开发迭代留下的红永远清不掉）。

用法：
    .venv/Scripts/python.exe scripts/check_probe_reports.py
    .venv/Scripts/python.exe scripts/check_probe_reports.py --require editor_probe startup_probe
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import clean_for_release as cleaner  # noqa: E402  复用判据归一，不重写一遍 schema 认知

GENERATED = ROOT / ".system_generated"


def main() -> int:
    required = set()
    args = sys.argv[1:]
    if "--require" in args:
        index = args.index("--require") + 1
        required = {a for a in args[index:] if not a.startswith("--")}

    if not GENERATED.is_dir():
        print("[FAIL] .system_generated/ 不存在，本次没有任何探针报告可判")
        return 1

    failures: list[str] = []
    rows: list[tuple[str, str, str, bool]] = []
    for probe_dir in sorted(p for p in GENERATED.iterdir() if p.is_dir()):
        reports = sorted(probe_dir.rglob("probe.toml"), key=lambda p: p.stat().st_mtime)
        if not reports:
            continue
        newest = reports[-1]
        ok, detail = cleaner.probe_verdict(newest)
        tag = newest.parent.name
        stamp = datetime.fromtimestamp(newest.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        rows.append((probe_dir.name, tag, f"{detail} @ {stamp}", ok))
        if not ok:
            failures.append(f"{probe_dir.name}[{tag}] 最新跑批未全绿：{detail}")

    for name, tag, detail, ok in rows:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}（{tag}）：{detail}")

    missing = sorted(r for r in required if not any(name == r for name, _, _, _ in rows))
    for name in missing:
        failures.append(f"要求的探针 {name} 没有报告（未跑或产物被清）")

    if not rows:
        failures.append(".system_generated/ 下没有任何 probe.toml——工序 06 必须有真机探针证据")

    if failures:
        print(f"check-probe-reports: {len(failures)} 项不合格")
        for item in failures:
            print(f"[FAIL] {item}")
        return 1
    print(f"check-probe-reports: PASS（{len(rows)} 支探针最新跑批全部全绿）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
