# -*- coding: utf-8 -*-
"""本地工作区物理瘦身：回收探针产物、字节码缓存与过期发行包。

用法：
    .venv/Scripts/python.exe tools/cleanup_workspace.py --dry-run
    .venv/Scripts/python.exe tools/cleanup_workspace.py
    .venv/Scripts/python.exe tools/cleanup_workspace.py --keep-latest 3

为什么要有这个脚本：探针每跑一轮就往 `.system_generated/` 落几十张截图、一份隔离库副本
和一整套插件树拷贝；三十多道军令攒下来把本机推到 2.6 GB / 5 万文件，IDE 索引、
全盘杀毒和 git 状态扫描全被拖慢。这些东西全部可再生，不该占本地。

四条护栏，写死在代码里，参数绕不过去：
  1. `data/` 是老师题库的物理载体，`.venv/` 是本机唯一的解释器来源，`examples/` 是 git 里
     的契约资产，`.git/` 是历史——任何删除目标一旦落在这些目录内，脚本直接终止。
  2. 目标必须真在仓库根之下（防 `..` 逃逸）。
  3. 链接与 junction 只做「断开」，绝不顺着删到别处去。
  4. 删了什么先落一份逐条清单到系统临时目录并打印路径，主公可事后复核。
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / ".system_generated"
DIST_DIR = ROOT / "dist"
PLUGINS_DIR = ROOT / "plugins"

# 无论传什么参数都不许被删到的地方（题库命根子 + 解释器 + 契约资产 + 历史）。
FORBIDDEN_ROOTS = (ROOT / "data", ROOT / ".venv", ROOT / "examples", ROOT / ".git")

VERSION_TAIL = re.compile(r"[-_.]v?\d+(?:\.\d+)*$")


def die(message: str) -> None:
    print(f"[中止] {message}")
    raise SystemExit(1)


def guard(target: Path) -> None:
    """删除前置校验：必须在仓库内，且不在任何禁改区里。"""
    resolved = Path(os.path.abspath(str(target)))
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        die(f"目标 {resolved} 逃出仓库根 {ROOT}")
    for forbidden in FORBIDDEN_ROOTS:
        if resolved == forbidden or forbidden in resolved.parents:
            die(f"目标 {resolved} 落在禁改区 {forbidden}")


def is_link(path: Path) -> bool:
    if os.path.islink(str(path)):
        return True
    checker = getattr(os.path, "isjunction", None)
    return bool(checker and checker(str(path)))


def detach(path: Path, errors: list[str]) -> None:
    """断开符号链接 / junction 本身，不触碰它指向的内容。"""
    try:
        if os.path.isdir(str(path)):
            os.rmdir(str(path))
        else:
            os.unlink(str(path))
    except OSError as exc:
        errors.append(f"{path}: 断开失败 {exc}")


def remove_tree(target: Path, errors: list[str]) -> None:
    if is_link(target):
        detach(target, errors)
        return
    try:
        shutil.rmtree(str(target))
        return
    except OSError:
        pass
    # 逐项退路：遇到 junction / 权限问题只跳过该子项，其余继续删。
    if target.is_file():
        try:
            target.unlink()
        except OSError as exc:
            errors.append(f"{target}: 删除失败 {exc}")
        return
    if not target.exists():
        return
    for child in sorted(target.iterdir(), key=lambda p: str(p)):
        remove_tree(child, errors)
    try:
        target.rmdir()
    except OSError as exc:
        errors.append(f"{target}: 目录清空失败 {exc}")


def walk_files(root: Path):
    """遍历文件，绝不跟随链接；链接目录只报告自身。"""
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(str(current)) as it:
                entries = list(it)
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            if is_link(path):
                yield path, True
            elif entry.is_dir(follow_symlinks=False):
                stack.append(path)
            elif entry.is_file(follow_symlinks=False):
                yield path, False


def tree_bytes(root: Path) -> int:
    if root.is_file():
        return root.stat().st_size
    total = 0
    for path, linked in walk_files(root):
        if linked:
            continue
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return total


def tree_files(root: Path) -> int:
    if root.is_file():
        return 1
    return sum(1 for _ in walk_files(root))


def newest_mtime(root: Path) -> float:
    newest = root.stat().st_mtime
    for path, linked in walk_files(root):
        if linked:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime > newest:
            newest = mtime
    return newest


def human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} GB"


def stamp(path: Path) -> str:
    try:
        return datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return "?"


# ---------------------------------------------------------------- 任务一：字节码缓存
def find_pycache() -> list[Path]:
    """仓库内所有 __pycache__，跳过禁改区（.venv 里的缓存属于依赖本体，不碰）。"""
    found: list[Path] = []
    stack = [ROOT]
    forbidden = {str(p) for p in FORBIDDEN_ROOTS}
    while stack:
        current = stack.pop()
        if str(current) in forbidden:
            continue
        try:
            with os.scandir(str(current)) as it:
                entries = [e for e in it if e.is_dir(follow_symlinks=False) and not is_link(Path(e.path))]
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            if path.name == "__pycache__":
                found.append(path)
                continue
            stack.append(path)
    return sorted(found, key=lambda p: str(p))


# ---------------------------------------------------------------- 任务二：探针产物
def _covers(keeper: Path, candidate: Path) -> bool:
    """candidate 是否就是 keeper 或 keeper 的祖先。"""
    return keeper == candidate or candidate in keeper.parents


def prune_generated(keep_latest: int = 1, keeper: Path | None = None) -> list[tuple[Path, int, int]]:
    """从根往叶子留一条 spine：每层只保留一项，其余整棵删掉。

    单纯「保留最新目录」在本机等于保留 840 MB 的 editor_probe——它底下有 94 轮历史跑批，
    所以必须递归下钻，最后只留下一轮探针的那一个叶子。``keeper`` 给定时按指名留 spine
    （发版脚本留「最近一次全绿的跑批」），不给就按最新时间留；``keep_latest=0`` 等于全删。
    """
    doomed: list[tuple[Path, int, int]] = []
    if not GENERATED_DIR.exists():
        return doomed
    if keeper is not None:
        keeper = Path(os.path.abspath(str(keeper)))
        try:
            keeper.relative_to(GENERATED_DIR)
        except ValueError:
            die(f"指定的保留项 {keeper} 不在 {GENERATED_DIR} 内")
    current = GENERATED_DIR
    while True:
        entries = list(current.iterdir())
        if keeper is not None:
            retained = [p for p in entries if _covers(keeper, Path(os.path.abspath(str(p))))]
        else:
            ranked = sorted(entries, key=newest_mtime, reverse=True)
            retained = ranked[:max(0, keep_latest)] if keep_latest > 0 else []
        hits = {str(p) for p in retained}
        for path in (p for p in entries if str(p) not in hits):
            doomed.append((path, tree_bytes(path), tree_files(path)))
        if not retained:
            break
        nxt = Path(os.path.abspath(str(retained[0])))
        if keeper is not None and nxt == keeper:
            break
        if not nxt.is_dir() or is_link(nxt):
            break
        current = nxt
    return doomed


# ---------------------------------------------------------------- 任务三：过期发行包
def plugin_zip_state(path: Path) -> tuple[bool, float | None]:
    """返回 (是不是插件包, 对应插件源码的最新时间)。源码目录已退役时时间为 None。"""
    match = re.fullmatch(r"org\.jiuzhang\.([A-Za-z0-9_-]+)\.zip", path.name)
    if not match:
        return False, None
    source = PLUGINS_DIR / f"org.jiuzhang.{match.group(1)}"
    if not source.exists():
        return True, None
    return True, newest_mtime(source)


def plan_archives(keep_per_family: int) -> list[tuple[Path, int, str]]:
    doomed: list[tuple[Path, int, str]] = []
    candidates = sorted(list(ROOT.glob("*.zip")) + list(DIST_DIR.glob("*.zip")), key=str)
    families: dict[str, list[Path]] = {}
    for path in candidates:
        guard(path)
        if path.parent != DIST_DIR:
            doomed.append((path, tree_bytes(path), "根目录散包（发行包只该落在 dist/）"))
            continue
        is_plugin_zip, source_newest = plugin_zip_state(path)
        if is_plugin_zip:
            if source_newest is None:
                doomed.append((path, tree_bytes(path), "插件目录已退役"))
            elif path.stat().st_mtime < source_newest:
                doomed.append((path, tree_bytes(path), "插件源码已更新，包是旧的"))
            continue
        families.setdefault(VERSION_TAIL.sub("", path.stem), []).append(path)
    for name, paths in sorted(families.items()):
        ranked = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
        for path in ranked[max(0, keep_per_family):]:
            doomed.append((path, tree_bytes(path), f"同族 {name} 已有更新包"))
    return doomed


# ---------------------------------------------------------------- 主流程
def main() -> int:
    parser = argparse.ArgumentParser(description="本地工作区物理瘦身（绝不动 data/ 与 .venv/）")
    parser.add_argument("--dry-run", action="store_true", help="只报告要删什么，不落手")
    parser.add_argument("--keep-latest", type=int, default=1,
                        help=".system_generated 每层保留最新的几项（默认 1，且只下钻保留到那一个叶子）")
    parser.add_argument("--keep-archives", type=int, default=1, help="发行包同族保留最新的几个（默认 1）")
    parser.add_argument("--skip-archives", action="store_true", help="不动任何 zip")
    parser.add_argument("--list-all", action="store_true", help="逐条打印全部目标，不只前 40 条")
    args = parser.parse_args()

    # Windows 控制台默认 GBK，中文报告不打码只能先把标准输出钉成 UTF-8。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    if not (ROOT / "app").exists():
        die(f"当前根不像九章算子仓库：{ROOT}")

    if args.dry_run:
        print("== DRY RUN ==")

    before_total = tree_bytes(ROOT)
    before_files = tree_files(ROOT)
    # 禁改区在收尾时再称一次重量，作为「一寸没动」的正面证据。
    before_guarded = [(p, tree_bytes(p)) for p in FORBIDDEN_ROOTS if p.exists()]
    errors: list[str] = []
    manifest: list[str] = []

    pycaches = [(p, tree_bytes(p)) for p in find_pycache()]
    pycache_bytes = sum(size for _, size in pycaches)
    print(f"[1/3] __pycache__：{len(pycaches)} 个目录，{human(pycache_bytes)}")
    for path, size in pycaches:
        guard(path)
        manifest.append(f"PYCACHE\t{human(size)}\t{path}")
        if not args.dry_run:
            remove_tree(path, errors)

    probe_targets = prune_generated(args.keep_latest)
    probe_bytes = sum(size for _, size, _ in probe_targets)
    print(f"[2/3] .system_generated：待删 {len(probe_targets)} 项，约 {human(probe_bytes)}")
    for path, size, files in probe_targets:
        guard(path)
        manifest.append(f"PROBE\t{human(size)}\t{files} 文件\t{stamp(path)}\t{path}")
        if not args.dry_run:
            remove_tree(path, errors)

    archives: list[tuple[Path, int, str]] = [] if args.skip_archives else plan_archives(args.keep_archives)
    archive_bytes = sum(size for _, size, _ in archives)
    print(f"[3/3] 过期 zip：{len(archives)} 个，约 {human(archive_bytes)}")
    for path, size, reason in archives:
        manifest.append(f"ZIP\t{human(size)}\t{reason}\t{stamp(path)}\t{path}")
        if not args.dry_run:
            try:
                path.unlink()
            except OSError as exc:
                errors.append(f"{path}: 删除失败 {exc}")

    if args.dry_run:
        print(f"预计回收 {human(pycache_bytes + probe_bytes + archive_bytes)}（未落手）")
        for line in manifest if args.list_all else manifest[:40]:
            print("  " + line)
        if not args.list_all and len(manifest) > 40:
            print(f"  …另 {len(manifest) - 40} 条")
        return 0

    after_total = tree_bytes(ROOT)
    after_files = tree_files(ROOT)
    handle, report_path = tempfile.mkstemp(prefix="jzo_cleanup_manifest_", suffix=".txt")
    with os.fdopen(handle, "w", encoding="utf-8") as report:
        report.write(f"# 清理时间 {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        report.write(f"# 仓库根 {ROOT}\n")
        report.write(f"# 前 {human(before_total)} / {before_files} 文件；"
                     f"后 {human(after_total)} / {after_files} 文件；"
                     f"实收 {human(before_total - after_total)}\n")
        report.writelines(line + "\n" for line in manifest)
    print(f"实收 {human(before_total - after_total)}：{human(before_total)}/{before_files} 文件 "
          f"→ {human(after_total)}/{after_files} 文件")
    drifted = []
    for guarded, size_before in before_guarded:
        size_after = tree_bytes(guarded)
        print(f"[护栏] {guarded.relative_to(ROOT)}：{human(size_before)} → {human(size_after)}")
        if size_after > size_before:
            drifted.append(str(guarded))
    print(f"逐条清单：{report_path}")
    if drifted:
        die(f"禁改区体积变大，异常：{', '.join(drifted)}")
    if errors:
        print(f"[残留] {len(errors)} 处未删净，前 10 条：")
        for line in errors[:10]:
            print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
