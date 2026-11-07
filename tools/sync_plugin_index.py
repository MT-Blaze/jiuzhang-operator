# -*- coding: utf-8 -*-
"""同步官方插件索引：以各插件 ``plugin.toml`` 的实际版本与描述改写主仓 ``plugins.toml``。

远端插件仓库（``../jiuzhang-plugins``）仍发布 JSON，属于主仓范围之外的外部协议：
本工具只做**语义比对**并如实报告差异，不代写远端文件。远端要换格式时，
应在那个仓库里单独发版。

用法：.venv/Scripts/python.exe tools/sync_plugin_index.py
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import manifests, toml_io, wire  # noqa: E402

INDEX_MAIN = ROOT / "plugins.toml"
INDEX_REPO = ROOT.parent / "jiuzhang-plugins" / "plugins.json"
PLUGIN_DIRS = ("org.jiuzhang.bank-engine", "org.jiuzhang.bank-ui", "org.jiuzhang.editor",
               "org.jiuzhang.paper-gen", "org.jiuzhang.handout",
               "org.jiuzhang.dashboard")
# 只有这几条要求索引文案与清单逐字相同（tests/test_clean_latex.py 有契约判据）。
# 其余条目的索引描述是**店面文案**，比清单多一句「需底座 v1.0.0 及以上」之类的提示，
# 被清单覆盖掉就把这条信息丢了，所以不镜像。
MIRROR_DESCRIPTION = ("org.jiuzhang.editor",)


def actual_manifests() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name in PLUGIN_DIRS:
        manifest = manifests.load_manifest(ROOT / "plugins" / name)
        out[manifest["id"]] = manifest
    return out


def remote_entries() -> dict[str, dict] | None:
    if not INDEX_REPO.is_file():
        return None
    try:
        payload = wire.read(INDEX_REPO)
    except (OSError, ValueError):
        return None
    rows = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return None
    return {row.get("id"): row for row in rows if isinstance(row, dict) and row.get("id")}


def main() -> int:
    manifest_map = actual_manifests()
    payload = toml_io.load(INDEX_MAIN, {})
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise SystemExit("plugins.toml 缺少 entries 数组")
    changed: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        manifest = manifest_map.get(entry.get("id"))
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
    missing = set(manifest_map) - seen
    if missing:
        raise SystemExit("索引里缺条目：%s" % ", ".join(sorted(missing)))
    payload["updated_at"] = datetime.date.today().isoformat()
    toml_io.write(INDEX_MAIN, payload)

    remote = remote_entries()
    drift: list[str] = []
    if remote is not None:
        for entry in entries:
            row = remote.get(entry["id"])
            if row is None:
                drift.append("%s：远端缺条目" % entry["id"])
            elif row.get("version") != entry.get("version"):
                drift.append("%s：远端 %s / 本仓 %s"
                             % (entry["id"], row.get("version"), entry.get("version")))
    print("已改写：%s" % (", ".join(changed) if changed else "无版本变化"))
    print("条目：%s" % ", ".join(entry["id"] + "@" + entry["version"] for entry in entries))
    if remote is None:
        print("远端索引不存在，跳过语义比对")
    elif drift:
        print("远端语义漂移：")
        for line in drift:
            print("  - " + line)
        return 1
    else:
        print("远端语义一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
