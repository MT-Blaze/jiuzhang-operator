# -*- coding: utf-8 -*-
"""把 dev/fixtures.json 同步进录题插件源码的内嵌假数据块。

为什么要这一步：插件跑在 CSP ``connect-src 'none'`` 的沙箱里，发不出任何请求，
假数据只能内嵌进 ``dist/plugin.js``；但内嵌一旦成为第二份事实，就会和
``dev/fixtures.json`` 漂移。本工具把 dev/fixtures.json 当唯一来源，按标记整块重写，
契约测试（tests/test_editor_contract.py）再逐字段比对两处，漂移当场红。

用法：``.venv/Scripts/python.exe tools/sync_editor_fixtures.py``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "org.jiuzhang.editor"
FIXTURES = PLUGIN_DIR / "dev" / "fixtures.json"
SCRIPT = PLUGIN_DIR / "dist" / "plugin.js"

BEGIN = "  //# FIXTURES-BEGIN"
END = "  //# FIXTURES-END"
DECL = "  var DEV_FIXTURES = "


def rendered() -> str:
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("fixtures.json 顶层必须是数组")
    return DECL + json.dumps(data, ensure_ascii=False, indent=2) + ";"


def main() -> int:
    text = SCRIPT.read_text(encoding="utf-8")
    start = text.index(BEGIN)
    end = text.index(END)
    head = text[: start + len(BEGIN) + 1]
    tail = text[end:]
    SCRIPT.write_text(head + rendered() + "\n" + tail, encoding="utf-8")
    print(f"已同步假数据到 {SCRIPT}（来源 {FIXTURES}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
