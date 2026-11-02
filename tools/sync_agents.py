# -*- coding: utf-8 -*-
"""六工序角色卡同步：把 .qoder/agents/*.md 镜像到 Qoder 用户级 agents 目录。

背景（2026-11-02 实测）：`.qoder/skills/**/SKILL.md` 落盘即被识别为可用 skill（无需重启），
但 `.qoder/agents/*.md` 定义的子智能体在**当次会话**不会进可调用类型清单——
项目级与用户级都试过一次，都报 `Unknown agent type`。因此角色卡的可调用性只能在**新会话**验证，
而 Qoder 文档保证用户级目录一定被扫描（本机 `~/.qoder/agents/sample/*.md` 就是现成的可调用样本）。

策略：仓库 `.qoder/agents/` 是唯一事实源（随 git 走、可评审），本脚本把它镜像到
`~/.qoder/agents/jiuzhang-pipeline/` 作为运行时兜底；若新会话确认项目级也能识别，镜像留着无害
（同名时项目级优先级高于用户级）。

用法：
    .venv/Scripts/python.exe tools/sync_agents.py            # 安装/刷新镜像
    .venv/Scripts/python.exe tools/sync_agents.py --check    # 只比对，不一致 rc=1
    .venv/Scripts/python.exe tools/sync_agents.py --remove   # 删除镜像目录
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / ".qoder" / "agents"
TARGET_DIR = Path.home() / ".qoder" / "agents" / "jiuzhang-pipeline"


def sources() -> list[Path]:
    return sorted(p for p in SOURCE_DIR.glob("*.md"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diff_report() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for path in sources():
        target = TARGET_DIR / path.name
        if not target.is_file():
            rows.append((path.name, "MISSING"))
        elif sha(target) != sha(path):
            rows.append((path.name, "STALE"))
        else:
            rows.append((path.name, "OK"))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只比对不写")
    parser.add_argument("--remove", action="store_true", help="删除用户级镜像目录")
    args = parser.parse_args()

    if not SOURCE_DIR.is_dir():
        print(f"[FAIL] 缺角色卡源目录：{SOURCE_DIR}")
        return 1

    if args.remove:
        if TARGET_DIR.is_dir():
            shutil.rmtree(TARGET_DIR)
            print(f"removed {TARGET_DIR}")
        else:
            print("镜像目录不存在，无需删除")
        return 0

    rows = diff_report()
    if args.check:
        for name, state in rows:
            print(f"[{state}] {name}")
        bad = [n for n, s in rows if s != "OK"]
        if bad:
            print(f"check: {len(bad)} 个角色卡未同步或过期 → {', '.join(bad)}")
            return 1
        print(f"check: PASS（{len(rows)} 张角色卡与用户级镜像逐字节一致）")
        return 0

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    changed = 0
    for path in sources():
        target = TARGET_DIR / path.name
        if not target.is_file() or sha(target) != sha(path):
            shutil.copyfile(path, target)
            changed += 1
    print(f"已镜像 {len(rows)} 张角色卡到 {TARGET_DIR}（本次更新 {changed} 张）")
    print("生效条件：新开一个会话才会把角色卡读进可调用清单；本会话内可用 general-purpose + 角色卡路径兜底。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
