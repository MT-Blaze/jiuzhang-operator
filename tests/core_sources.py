"""底座源码的「微内核 + 组合根」拼接读取（军令 #30 拆解后）。

stage.js / workspace.js 已按 workspace.html 的加载顺序拆成微内核：

    core_bus.js → core_tabs.js → stage.js
    core_log.js → workspace.js

测试里的结构断言要看到完整语义，必须按同一顺序把内核拼回组合根前面。
集中放在这里，免得二十多个测试各写一套拼接顺序、日后又漂移。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_DIR = ROOT / "static" / "js"

STAGE_PARTS = ("core_bus.js", "core_tabs.js", "stage.js")
WORKSPACE_PARTS = ("core_log.js", "workspace.js")


def stage_source() -> str:
    return "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in STAGE_PARTS)


def workspace_source() -> str:
    return "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in WORKSPACE_PARTS)
