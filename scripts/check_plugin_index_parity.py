# -*- coding: utf-8 -*-
"""两份官方插件索引逐字节全等校验（L0 门禁）+ 数据契约校验。

- 主仓 plugins.json 与插件仓库 plugins.json 必须完全相同（出处 docs/PROJECT_MEMORY.md:290,294）
- 索引条目版本必须等于插件目录 plugin.json 的实际版本
- schemas/*.json 必须是合法 JSON，且 schemas/question.json 的每个 example 必须自校验通过

兄弟仓库路径与官方清单都从 tools/sync_plugin_index.py 读，不在本脚本里写死。

用法：.venv/Scripts/python.exe scripts/check_plugin_index_parity.py
只读，不写任何文件；违反 L0 即 rc=1。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "tools" / "sync_plugin_index.py"
PLUGIN_DIRS_RE = re.compile(r"PLUGIN_DIRS\s*=\s*\((.*?)\)", re.S)
INDEX_REPO_RE = re.compile(r"INDEX_REPO\s*=\s*Path\(\s*[\"'](.+?)[\"']\s*\)")
MIRROR_RE = re.compile(r"MIRROR_DESCRIPTION\s*=\s*\((.*?)\)")
failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def parse_sync_constants() -> tuple[list[str], Path, list[str]]:
    if not SYNC.is_file():
        fail("缺 tools/sync_plugin_index.py，无法确定官方清单与索引路径")
        return [], ROOT / "plugins.json", []
    text = SYNC.read_text(encoding="utf-8")
    dirs_match = PLUGIN_DIRS_RE.search(text)
    repo_match = INDEX_REPO_RE.search(text)
    mirror_match = MIRROR_RE.search(text)
    if not dirs_match:
        fail("无法解析 PLUGIN_DIRS")
    if not repo_match:
        fail("无法解析 INDEX_REPO")
    official = [x.strip().strip("\"'") for x in dirs_match.group(1).split(",")] if dirs_match else []
    mirror = [x.strip().strip("\"'") for x in mirror_match.group(1).split(",")] if mirror_match else []
    repo_path = Path(repo_match.group(1)) if repo_match else ROOT / "plugins.json"
    return official, repo_path, mirror


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    official, repo_index, mirror_ids = parse_sync_constants()
    main_index = ROOT / "plugins.json"

    for path in (main_index, repo_index):
        if not path.is_file():
            fail(f"索引文件不存在：{path}")
    if not failures:
        if sha(main_index) != sha(repo_index):
            fail(f"两份 plugins.json 不全等：主仓 {sha(main_index)[:12]}… vs 插件仓 {sha(repo_index)[:12]}…，请跑 tools/sync_plugin_index.py")
        try:
            payload = json.loads(main_index.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            fail(f"主仓 plugins.json 不是合法 JSON（{exc}）")
            payload = None

        if isinstance(payload, dict):
            entries = payload.get("entries") or []
            entry_ids = [e.get("id") for e in entries if isinstance(e, dict)]
            missing = [name for name in official if name not in entry_ids]
            extra = [i for i in entry_ids if official and i not in official]
            if missing:
                fail(f"索引缺条目：{', '.join(missing)}")
            if extra:
                fail(f"索引有条目但不在 PLUGIN_DIRS：{', '.join(map(str, extra))}")
            for entry in entries:
                if not isinstance(entry, dict) or not entry.get("id"):
                    continue
                manifest_path = ROOT / "plugins" / entry["id"] / "plugin.json"
                if not manifest_path.is_file():
                    continue
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if entry.get("version") != manifest.get("version"):
                    fail(f"{entry['id']}: 索引 version={entry.get('version')!r} != 清单 version={manifest.get('version')!r}")
                if entry["id"] in mirror_ids and entry.get("description") != manifest.get("description"):
                    fail(f"{entry['id']}: 索引 description 与清单不一致（该条目要求逐字镜像）")

    for schema_path in sorted((ROOT / "schemas").glob("*.json")):
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            fail(f"{schema_path.name}: 不是合法 JSON（{exc}）")
            continue
        if schema_path.name != "question.json":
            continue
        if not schema.get("required"):
            fail("question.json: required 为空")
        if "schema_version" not in (schema.get("properties") or {}):
            fail("question.json: properties 缺 schema_version")
        examples = schema.get("examples") or []
        if not examples:
            fail("question.json: examples 为空（改契约必须同步示例）")
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            fail("缺 jsonschema，无法自校验示例（必须用 .venv/Scripts/python.exe 跑门禁）")
        else:
            validator = Draft202012Validator(schema)
            for index, example in enumerate(examples):
                errors = sorted(validator.iter_errors(example), key=lambda e: e.path)
                for error in errors[:3]:
                    fail(f"question.json: examples[{index}] 不过校验（{'/'.join(map(str, error.path))}: {error.message}）")

    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        print(f"check-plugin-index-parity: {len(failures)} 项违反 L0")
        return 1
    print("check-plugin-index-parity: PASS（两份索引全等、条目版本一致、Schema 示例自校验通过）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
