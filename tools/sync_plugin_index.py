# -*- coding: utf-8 -*-
"""同步两份官方插件索引：主仓库根 plugins.json 与插件仓库 plugins.json 必须逐字相同。

用法：.venv/Scripts/python.exe tools/sync_plugin_index.py
按插件目录里的 plugin.json 实际版本改写索引条目，再把同一份文本写到两处。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_MAIN = ROOT / "plugins.json"
INDEX_REPO = Path("E:/jiuzhang-plugins/plugins.json")
PLUGIN_DIRS = ("org.jiuzhang.core-bank", "org.jiuzhang.editor", "org.jiuzhang.paper-gen",
               "org.jiuzhang.handout")


def actual_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in PLUGIN_DIRS:
        manifest = json.loads((ROOT / "plugins" / name / "plugin.json").read_text(encoding="utf-8"))
        out[manifest["id"]] = manifest["version"]
    return out


def main() -> int:
    versions = actual_versions()
    text = INDEX_MAIN.read_text(encoding="utf-8")
    changed: list[str] = []
    for plugin_id, version in versions.items():
        pattern = re.compile(
            r'("id": "' + re.escape(plugin_id) + r'",\n\s*"name": "[^"]*",\n\s*"version": ")([^"]*)(")'
        )
        def replace(match: re.Match, new_value: str = version) -> str:
            old = match.group(2)
            if old != new_value:
                changed.append("%s: %s -> %s" % (plugin_id, old, new_value))
            return match.group(1) + new_value + match.group(3)
        text, hits = pattern.subn(replace, text)
        if hits != 1:
            raise SystemExit("索引里找不到唯一条目：%s（命中 %d 次）" % (plugin_id, hits))
    text = re.sub(r'"updated_at": "[^"]*"', '"updated_at": "2026-10-23"', text, count=1)
    json.loads(text)  # 语法自检
    INDEX_MAIN.write_text(text, encoding="utf-8")
    INDEX_REPO.write_text(text, encoding="utf-8")
    same = INDEX_MAIN.read_bytes() == INDEX_REPO.read_bytes()
    print(json.dumps({
        "changed": changed,
        "entries": [entry["id"] + "@" + entry["version"] for entry in json.loads(text)["entries"]],
        "两份全等": same,
    }, ensure_ascii=False, indent=2))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
