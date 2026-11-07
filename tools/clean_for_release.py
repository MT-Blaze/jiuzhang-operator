# -*- coding: utf-8 -*-
"""发版前大扫除：清掉随开发无限膨胀的本地产物，并给 `.git/` 打包瘦身。

用法：
    .venv/Scripts/python.exe tools/clean_for_release.py --dry-run
    .venv/Scripts/python.exe tools/clean_for_release.py
    .venv/Scripts/python.exe tools/clean_for_release.py --skip-git-gc

规矩（已写进 `docs/PROJECT_MEMORY.md` §一 第 8 条）：**每次改动底座版本号、准备发版之前，
必须手动跑一次本脚本**。它不做后台轮询、不在启动时顺手跑，只认人当场敲的这条命令。

与 `tools/cleanup_workspace.py` 的分工：那个是本机性能急救（一次性回收 GB 级探针产物）；
本脚本是发版例行动作，复用同一套护栏与清理手法，另外做三件事——
① 连临时诊断脚本 `diag_*.py` 一起清；② 探针产物的保留标准从「时间最新」换成
「最近一次判据全绿的跑批」（看 `probe.toml`，不看 mtime）；③ 收尾自动 `git gc --prune=now`。

护栏沿用 cleanup_workspace 的禁改区（`data/` 题库、`.venv/` 解释器、`examples/` 契约资产、
`.git/` 历史），并额外加一条发版特有的：**git 已跟踪的文件一律不删**——本脚本只清产物，
无权动源码。
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402

import argparse
import datetime
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cleanup_workspace as cw  # noqa: E402

ROOT = cw.ROOT
GENERATED_DIR = cw.GENERATED_DIR

# diag_*.py 只在第一方代码区里找；.system_generated/ 下的诊断脚本会随探针产物一起清掉。
DIAG_SCAN_DIRS = (ROOT, ROOT / "tools", ROOT / "tests", ROOT / "app", ROOT / "static", ROOT / "docs", ROOT / "dist")
PASS_KEYS = ("passed", "ok", "success", "pass")
CHECK_LIST_KEYS = ("checks", "results", "items", "report")
TRUE_WORDS = {"pass", "passed", "ok", "true", "green", "success"}


def tracked_paths() -> set[str]:
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=str(ROOT), capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {p for p in out.stdout.decode("utf-8", "replace").split("\0") if p}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def check_passed(check: dict) -> bool | None:
    for key in PASS_KEYS:
        if key in check:
            value = check[key]
            return bool(value) if isinstance(value, bool) else str(value).strip().lower() in TRUE_WORDS
    status = str(check.get("status", "")).strip().lower()
    return status in TRUE_WORDS if status else None


def probe_verdict(probe_file: Path) -> tuple[bool, str]:
    """读一份 probe.toml 判全绿不全绿；schema 不认或读不动一律按「不算通过」处理。"""
    try:
        payload = toml_io.load(probe_file)
    except OSError as exc:
        return False, f"读不了 {exc.__class__.__name__}"
    checks = None
    if isinstance(payload, dict):
        for key in CHECK_LIST_KEYS:
            if isinstance(payload.get(key), list):
                checks = payload[key]
                break
    elif isinstance(payload, list):
        checks = payload
    if checks is not None:
        verdicts = [check_passed(c) for c in checks if isinstance(c, dict)]
        if not verdicts:
            return False, "checks 里认不出判定字段"
        failed = sum(1 for v in verdicts if v is not True)
        return failed == 0, f"{len(verdicts) - failed}/{len(verdicts)} 判据通过"
    # 没有逐条清单，只报汇总数字的探针
    if isinstance(payload, dict):
        total = payload.get("total")
        passed = payload.get("passed")
        if isinstance(total, int) and isinstance(passed, (int, bool)):
            passed_n = total if passed is True else passed
            return passed_n >= total, f"{passed_n}/{total} 判据通过"
        if isinstance(payload.get("failures"), int):
            return payload["failures"] == 0, f"failures={payload['failures']}"
    return False, "schema 不认"


def latest_passing_run() -> tuple[Path | None, str]:
    """`.system_generated/` 下最近一次全绿的跑批目录；一份都没有就返回 None（等于全删）。"""
    if not GENERATED_DIR.exists():
        return None, "目录不存在"
    best: Path | None = None
    best_mtime = 0.0
    detail = ""
    scanned = 0
    for probe_file, _ in cw.walk_files(GENERATED_DIR):
        if Path(probe_file).name != "probe.toml":
            continue
        scanned += 1
        run_dir = Path(probe_file).parent
        ok, why = probe_verdict(Path(probe_file))
        if not ok:
            continue
        mtime = cw.newest_mtime(run_dir)
        if mtime > best_mtime:
            best, best_mtime, detail = run_dir, mtime, why
    if best is None:
        return None, f"{scanned} 份 probe.toml 里没有一份是全绿的"
    return best, f"{relative(best)}（{detail}）"


def find_diag_scripts(tracked: set[str]) -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()
    for base in DIAG_SCAN_DIRS:
        if not base.exists():
            continue
        for path in base.glob("diag_*.py"):
            key = str(path.resolve())
            if key in seen or relative(path) in tracked:
                continue
            seen.add(key)
            found.append(path)
    return sorted(found, key=str)


def run_git_gc(dry_run: bool) -> list[str]:
    """打包 + 回收不可达对象；先把不可达数量报出来，让主公知道剪掉了什么。"""
    lines: list[str] = []
    try:
        fsck = subprocess.run(["git", "fsck", "--no-progress", "--unreachable"],
                              cwd=str(ROOT), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"git fsck 跑不动：{exc}"]
    unreachable = [ln for ln in (fsck.stdout or "").splitlines() if ln.startswith("unreachable")]
    kinds: dict[str, int] = {}
    for line in unreachable:
        parts = line.split()
        if len(parts) > 2:
            kinds[parts[1]] = kinds.get(parts[1], 0) + 1
    summary = "、".join(f"{k}×{v}" for k, v in sorted(kinds.items())) or "无"
    lines.append(f"不可达对象：{len(unreachable)} 个（{summary}）")
    if dry_run:
        lines.append("git gc --prune=now（DRY RUN 未执行）")
        return lines
    gc = subprocess.run(["git", "gc", "--prune=now"], cwd=str(ROOT), capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=1800)
    tail = "\n".join(ln for ln in (gc.stdout or "").splitlines() if ln.strip())
    lines.append(f"git gc rc={gc.returncode}" + (f"\n{tail}" if tail else ""))
    if gc.returncode != 0:
        lines.append(f"stderr: {gc.stderr.strip()[:400]}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="发版前大扫除（绝不动 data/、.venv/、examples/ 与 git 已跟踪文件）")
    parser.add_argument("--dry-run", action="store_true", help="只报告要删什么，不落手")
    parser.add_argument("--skip-git-gc", action="store_true", help="不跑 git gc --prune=now")
    parser.add_argument("--keep-all-probes", action="store_true", help="不碰 .system_generated/")
    args = parser.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    if not (ROOT / "app").exists():
        cw.die(f"当前根不像九章算子仓库：{ROOT}")
    if args.dry_run:
        print("== DRY RUN ==")

    tracked = tracked_paths()
    if not tracked:
        print("[提示] 拿不到 git ls-files（不在 git 仓库里或 git 不可用），本轮不删任何非产物文件。")

    before_total = cw.tree_bytes(ROOT)
    before_files = cw.tree_files(ROOT)
    before_git = cw.tree_bytes(ROOT / ".git") if (ROOT / ".git").exists() else 0
    guarded_before = [(p, cw.tree_bytes(p)) for p in cw.FORBIDDEN_ROOTS if p.exists()]
    errors: list[str] = []
    manifest: list[str] = []

    pycaches = [(p, cw.tree_bytes(p)) for p in cw.find_pycache()]
    pycache_bytes = sum(s for _, s in pycaches)
    print(f"[1/4] __pycache__：{len(pycaches)} 个，{cw.human(pycache_bytes)}")
    for path, size in pycaches:
        cw.guard(path)
        manifest.append(f"PYCACHE\t{cw.human(size)}\t{path}")
        if not args.dry_run:
            cw.remove_tree(path, errors)

    diags = find_diag_scripts(tracked) if tracked else []
    diag_bytes = sum(cw.tree_bytes(p) for p in diags)
    print(f"[2/4] 临时诊断脚本 diag_*.py：{len(diags)} 个，{cw.human(diag_bytes)}"
          + ("" if tracked else "（拿不到 git 清单，为安全起见一个不动）"))
    for path in diags:
        cw.guard(path)
        manifest.append(f"DIAG\t{cw.human(cw.tree_bytes(path))}\t{path}")
        if not args.dry_run:
            try:
                path.unlink()
            except OSError as exc:
                errors.append(f"{path}: 删除失败 {exc}")

    keeper, keeper_note = (None, "--keep-all-probes，本轮跳过") if args.keep_all_probes else latest_passing_run()
    probe_targets = [] if args.keep_all_probes else cw.prune_generated(1 if keeper else 0, keeper)
    probe_bytes = sum(s for _, s, _ in probe_targets)
    print(f"[3/4] .system_generated：待删 {len(probe_targets)} 项，约 {cw.human(probe_bytes)}；保留 {keeper_note}")
    for path, size, files in probe_targets:
        cw.guard(path)
        manifest.append(f"PROBE\t{cw.human(size)}\t{files} 文件\t{cw.stamp(path)}\t{path}")
        if not args.dry_run:
            cw.remove_tree(path, errors)

    archives = cw.plan_archives(1)
    archive_bytes = sum(s for _, s, _ in archives)
    print(f"[4/4] dist/ 旧版 zip：{len(archives)} 个，约 {cw.human(archive_bytes)}")
    for path, size, reason in archives:
        if relative(path) in tracked:
            print(f"  [跳过] {path} 是 git 已跟踪文件")
            continue
        manifest.append(f"ZIP\t{cw.human(size)}\t{reason}\t{cw.stamp(path)}\t{path}")
        if not args.dry_run:
            try:
                path.unlink()
            except OSError as exc:
                errors.append(f"{path}: 删除失败 {exc}")

    print("[git] .git 瘦身")
    for line in ([] if args.skip_git_gc else run_git_gc(args.dry_run)):
        print(f"  {line}")

    if args.dry_run:
        print(f"预计回收 {cw.human(pycache_bytes + diag_bytes + probe_bytes + archive_bytes)}（未落手，git 未动）")
        for line in manifest:
            print("  " + line)
        return 0

    after_total = cw.tree_bytes(ROOT)
    after_files = cw.tree_files(ROOT)
    after_git = cw.tree_bytes(ROOT / ".git") if (ROOT / ".git").exists() else 0
    handle, report_path = tempfile.mkstemp(prefix="jzo_release_cleanup_", suffix=".txt")
    with os.fdopen(handle, "w", encoding="utf-8") as report:
        report.write(f"# 发版大扫除 {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        report.write(f"# 仓库根 {ROOT}\n")
        report.write(f"# 前 {cw.human(before_total)} / {before_files} 文件 → "
                     f"后 {cw.human(after_total)} / {after_files} 文件（回收 {cw.human(before_total - after_total)}）\n")
        report.write(f"# .git {cw.human(before_git)} → {cw.human(after_git)}\n")
        report.write(f"# 保留探针产物：{keeper_note}\n")
        report.writelines(line + "\n" for line in manifest)
    print(f"回收 {cw.human(before_total - after_total)}：{cw.human(before_total)}/{before_files} 文件 "
          f"→ {cw.human(after_total)}/{after_files} 文件；.git {cw.human(before_git)} → {cw.human(after_git)}")
    for path, size_before in guarded_before:
        size_after = cw.tree_bytes(path)
        print(f"[护栏] {relative(path)}：{cw.human(size_before)} → {cw.human(size_after)}")
        if size_after > size_before:
            cw.die(f"禁改区体积变大，异常：{path}")
    print(f"逐条清单：{report_path}")
    if errors:
        print(f"[残留] {len(errors)} 处未删净，前 10 条：")
        for line in errors[:10]:
            print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
