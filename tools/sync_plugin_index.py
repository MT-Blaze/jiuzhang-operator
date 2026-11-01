# -*- coding: utf-8 -*-
"""同步两份官方插件索引：主仓库根 plugins.json 与插件仓库 plugins.json 必须逐字相同。

用法：.venv/Scripts/python.exe tools/sync_plugin_index.py
按插件目录里的 plugin.json 实际版本与描述改写索引条目，再把同一份文本写到两处。

索引就是清单的镜像：版本与描述一律从 plugin.json 取，索引里手写的旧文案会被覆盖。
以前只同步版本，于是清单一改描述，索引就成了过期副本（编辑器 2.1.0 就踩过）。
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_MAIN = ROOT / "plugins.json"
INDEX_REPO = Path("E:/jiuzhang-plugins/plugins.json")
PLUGIN_DIRS = ("org.jiuzhang.bank-engine", "org.jiuzhang.bank-ui", "org.jiuzhang.editor",
               "org.jiuzhang.paper-gen", "org.jiuzhang.handout", "org.jiuzhang.chat",
               "org.jiuzhang.dashboard")
# 只有这几条要求索引文案与清单逐字相同（tests/test_clean_latex.py 有契约判据）。
# 其余条目的索引描述是**店面文案**，比清单多一句「需底座 v1.0.0 及以上」之类的提示，
# 被清单覆盖掉就把这条信息丢了，所以不镜像。
MIRROR_DESCRIPTION = ("org.jiuzhang.editor",)


def actual_manifests() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name in PLUGIN_DIRS:
        manifest = json.loads((ROOT / "plugins" / name / "plugin.json").read_text(encoding="utf-8"))
        out[manifest["id"]] = manifest
    return out


def main() -> int:
    manifests = actual_manifests()
    payload = json.loads(INDEX_MAIN.read_text(encoding="utf-8"))
    changed: list[str] = []
    seen: set[str] = set()
    for entry in payload["entries"]:
        manifest = manifests.get(entry["id"])
        if manifest is None:
            continue
        seen.add(entry["id"])
        if entry.get("version") != manifest["version"]:
            changed.append("%s: version %s -> %s"
                           % (entry["id"], entry.get("version"), manifest["version"]))
            entry["version"] = manifest["version"]
        if entry["id"] in MIRROR_DESCRIPTION and entry.get("description") != manifest["description"]:
            changed.append("%s: description 已按清单同步" % entry["id"])
            entry["description"] = manifest["description"]
    missing = set(manifests) - seen
    if missing:
        raise SystemExit("索引里缺条目：%s" % ", ".join(sorted(missing)))
    # updated_at 跟着今天走：写死日期会让索引永远停在改它的那天。
    payload["updated_at"] = datetime.date.today().isoformat()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    INDEX_MAIN.write_text(text, encoding="utf-8")
    INDEX_REPO.write_text(text, encoding="utf-8")
    same = INDEX_MAIN.read_bytes() == INDEX_REPO.read_bytes()
    print(json.dumps({
        "changed": changed,
        "entries": [entry["id"] + "@" + entry["version"] for entry in payload["entries"]],
        "两份全等": same,
    }, ensure_ascii=False, indent=2))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
