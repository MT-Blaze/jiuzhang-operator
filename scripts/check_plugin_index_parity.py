# -*- coding: utf-8 -*-
"""插件索引一致性校验（L0 门禁）+ 数据契约校验。

- 主仓 ``plugins.toml`` 与插件仓 ``plugins.json`` 必须语义一致：条目集合相同、
  每条 version 相同；要求镜像文案的条目 description 也相同。远端仓库仍发布 JSON，
  属于主仓范围之外的外部协议，因此按语义比对而不是逐字节比对。
- 索引条目版本必须等于插件目录 ``plugin.toml`` 的实际版本
- 题目契约以 ``app/core/question_contract.py`` 的 dataclass 为准，示例种子题必须过校验

兄弟仓库路径与官方清单都从 tools/sync_plugin_index.py 读，不在本脚本里写死。

用法：.venv/Scripts/python.exe scripts/check_plugin_index_parity.py
只读，不写任何文件；违反 L0 即 rc=1。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
from app.core import manifests, question_contract, toml_io, wire  # noqa: E402

SYNC = ROOT / "tools" / "sync_plugin_index.py"
failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def parse_sync_constants() -> tuple[list[str], Path, list[str]]:
    if not SYNC.is_file():
        fail("缺 tools/sync_plugin_index.py，无法确定官方清单与索引路径")
        return [], ROOT.parent / "jiuzhang-plugins" / "plugins.json", []
    spec = importlib.util.spec_from_file_location("sync_plugin_index", SYNC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.PLUGIN_DIRS), module.INDEX_REPO, list(module.MIRROR_DESCRIPTION)


def by_id(entries: list[dict]) -> dict[str, dict]:
    return {row["id"]: row for row in entries if isinstance(row, dict) and row.get("id")}


def main() -> int:
    official, repo_index, mirror_ids = parse_sync_constants()
    main_index = ROOT / "plugins.toml"

    for path in (main_index, repo_index):
        if not path.is_file():
            fail(f"索引文件不存在：{path}")
    if not failures:
        try:
            payload = toml_io.load(main_index, {})
        except (OSError, ValueError) as exc:
            fail(f"主仓 plugins.toml 读不出来（{exc}）")
            payload = None

        if isinstance(payload, dict):
            entries = payload.get("entries") or []
            local = by_id(entries)
            missing = [name for name in official if name not in local]
            extra = [i for i in local if official and i not in official]
            if missing:
                fail(f"索引缺条目：{', '.join(missing)}")
            if extra:
                fail(f"索引有条目但不在 PLUGIN_DIRS：{', '.join(map(str, extra))}")
            for entry_id, entry in local.items():
                if manifests.manifest_path(PLUGIN_SOURCE_DIR / entry_id) is None:
                    continue
                manifest = manifests.load_manifest(PLUGIN_SOURCE_DIR / entry_id)
                if entry.get("version") != manifest.get("version"):
                    fail(f"{entry_id}: 索引 version={entry.get('version')!r} != 清单 version={manifest.get('version')!r}")
                if entry_id in mirror_ids and entry.get("description") != manifest.get("description"):
                    fail(f"{entry_id}: 索引 description 与清单不一致（该条目要求逐字镜像）")

            try:
                remote_payload = wire.read(repo_index)
            except (OSError, ValueError) as exc:
                fail(f"插件仓索引读不出来（{exc}）")
                remote_payload = None
            if isinstance(remote_payload, dict):
                remote = by_id(remote_payload.get("entries") or [])
                if set(remote) != set(local):
                    fail("两份索引条目集合不一致：主仓 %s / 插件仓 %s"
                         % (sorted(local), sorted(remote)))
                for entry_id in sorted(set(local) & set(remote)):
                    if local[entry_id].get("version") != remote[entry_id].get("version"):
                        fail(f"{entry_id}: 索引 version 不一致（主仓 {local[entry_id].get('version')!r} / 插件仓 {remote[entry_id].get('version')!r}），请跑 tools/sync_plugin_index.py")
                    if entry_id in mirror_ids and local[entry_id].get("description") != remote[entry_id].get("description"):
                        fail(f"{entry_id}: 索引 description 不一致（该条目要求镜像）")

    seed_path = ROOT / "examples" / "demo_plugin" / "seed" / "questions.toml"
    try:
        seeds = toml_io.load(seed_path, {}).get("questions") or []
    except (OSError, ValueError) as exc:
        fail(f"示例种子题读不出来（{exc}）")
        seeds = []
    if not seeds:
        fail("示例种子题为空：改契约必须同步可运行示例")
    for index, item in enumerate(seeds):
        try:
            question_contract.validate(item)
        except question_contract.ContractError as exc:
            fail(f"种子题[{index}] 不过契约校验：{'; '.join(exc.errors[:3])}")

    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        print(f"check-plugin-index-parity: {len(failures)} 项违反 L0")
        return 1
    print("check-plugin-index-parity: PASS（两份索引语义一致、条目版本一致、示例题过契约校验）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
