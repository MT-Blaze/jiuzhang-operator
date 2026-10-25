"""一键打包插件：校验清单 → 过安全白名单 → 生成标准 zip（顶层目录 = 插件 id）。

用法：
    .venv/Scripts/python.exe tools/build_plugin.py plugins/org.jiuzhang.core-bank
    .venv/Scripts/python.exe tools/build_plugin.py --all
    .venv/Scripts/python.exe tools/build_plugin.py <dir> --out dist/plugins

设计口径（PLUGIN_SPEC §1.2）：
- zip 只是分发容器，顶层必须是 ``<id>/``，解压即用；
- 打包前必须通过 ``app.core.plugins.validate_plugin`` 全套契约校验，校验不过不产出；
- 拒绝把密钥、临时文件、嵌套 zip、符号链接、缓存打进去；
- 同一输入重复打包得到稳定条目顺序（按路径排序），便于人工比对。
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.plugins import PluginRejected, validate_plugin  # noqa: E402

DENY_NAMES = {
    ".env",
    ".DS_Store",
    "Thumbs.db",
    ".local_token",
    "plugin.zip",
}
DENY_SUFFIXES = {".pyc", ".pyo", ".zip", ".log", ".tmp", ".bak", ".db-shm", ".db-wal", ".db-journal", ".db"}
DENY_DIRS = {"__pycache__", ".git", ".idea", ".vscode", "node_modules", ".pytest_cache"}
# 纯净发版（ADR-003）：插件包一律不带任何物理数据库，也不带随真题库分发的题库配图资产。
# core-bank 的 ``bank/schema.sql`` 仍在包里，首启由底座 ensure_bank 建空库；
# 真题库与它的配图只在本地开发机存在，绝不进任何对外发布的 zip。
DENY_PAYLOAD_PREFIXES = ("bank/assets/",)


class BuildError(Exception):
    pass


def _iter_payload(plugin_dir: Path):
    for path in sorted(plugin_dir.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_dir():
            continue
        relative = path.relative_to(plugin_dir)
        if any(part in DENY_DIRS for part in relative.parts):
            continue
        relative_posix = relative.as_posix()
        if any(relative_posix.startswith(prefix) for prefix in DENY_PAYLOAD_PREFIXES):
            continue
        if any(part.startswith(".") and part not in {".gitkeep"} for part in relative.parts):
            continue
        if path.name in DENY_NAMES:
            continue
        if path.suffix.lower() in DENY_SUFFIXES:
            continue
        if path.is_symlink():
            raise BuildError(f"插件包内不得包含符号链接：{relative.as_posix()}")
        yield relative, path


def build_plugin(plugin_dir: Path, out_dir: Path) -> Path:
    plugin_dir = plugin_dir.resolve()
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.is_file():
        raise BuildError(f"{plugin_dir} 下没有 plugin.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # 声明了却被丢弃的命令要当场回给作者：打包成功不等于命令生效
        command_issues: list[dict[str, str]] = []
        info = validate_plugin(plugin_dir, manifest, command_issues)
    except (OSError, json.JSONDecodeError, PluginRejected) as exc:
        raise BuildError(f"清单校验失败：{exc}") from exc
    for issue in command_issues:
        label = f"「{issue['id']}」" if issue.get("id") else ""
        print(f"[WARN] {info['id']} 的命令 {label} 未登记：{issue.get('reason', '')}")

    payload = list(_iter_payload(plugin_dir))
    if not payload:
        raise BuildError("插件目录是空的")

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{info['id']}.zip"
    tmp = target.with_suffix(".zip.part")
    if tmp.exists():
        tmp.unlink()

    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, path in payload:
                arcname = PurePosixPath(info["id"], *relative.parts).as_posix()
                archive.write(path, arcname)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise
    tmp.replace(target)
    return target


def discover_package_dirs(plugins_dir: Path) -> list[Path]:
    if not plugins_dir.is_dir():
        return []
    result: list[Path] = []
    for child in sorted(plugins_dir.iterdir(), key=lambda item: item.name):
        if child.is_dir() and (child / "plugin.json").is_file():
            result.append(child)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验并打包九章算子插件（标准 zip，顶层为插件 id）")
    parser.add_argument("plugin_dir", nargs="?", help="插件目录（含 plugin.json）")
    parser.add_argument("--all", action="store_true", help="打包 plugins/ 下全部插件")
    parser.add_argument("--plugins-dir", default=str(ROOT / "plugins"), help="插件根目录")
    parser.add_argument("--out", default=str(ROOT / "dist" / "plugins"), help="zip 输出目录")
    args = parser.parse_args(argv)

    plugins_dir = Path(args.plugins_dir)
    if args.all:
        targets = discover_package_dirs(plugins_dir)
    elif args.plugin_dir:
        targets = [Path(args.plugin_dir)]
    else:
        parser.error("请给出插件目录，或使用 --all")
        return 2

    if not targets:
        print("没有找到可打包的插件目录。")
        return 1

    out_dir = Path(args.out)
    failures = 0
    for plugin_dir in targets:
        try:
            target = build_plugin(plugin_dir, out_dir)
            size = target.stat().st_size
            print(f"[OK] {plugin_dir.name} -> {target} ({size / 1024:.1f} KB)")
        except (BuildError, OSError) as exc:
            failures += 1
            print(f"[FAIL] {plugin_dir.name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
