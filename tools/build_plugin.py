"""一键打包插件：校验清单 → 过安全白名单 → 生成标准 zip（顶层目录 = 插件 id）。

用法：
    .venv/Scripts/python.exe tools/build_plugin.py plugins/org.jiuzhang.bank-engine
    .venv/Scripts/python.exe tools/build_plugin.py --all
    .venv/Scripts/python.exe tools/build_plugin.py <dir> --out dist/plugins
    .venv/Scripts/python.exe tools/build_plugin.py --suite
    .venv/Scripts/python.exe tools/build_plugin.py --suite org.jiuzhang.bank-engine

设计口径（PLUGIN_SPEC §1.2 / §1.8）：
- zip 只是分发容器，单插件包顶层必须是 ``<id>/``，解压即用；
- 套件包顶层是 ``suite.toml`` + 各子插件目录，一次安装、同进同退；
- 打包前必须通过 ``app.core.plugins.validate_plugin`` 全套契约校验，校验不过不产出；
- 套件必须自带全部依赖（requires 闭包），否则等于发一个空壳套件；
- 拒绝把密钥、临时文件、嵌套 zip、符号链接、缓存打进去；
- 同一输入重复打包得到稳定条目顺序（按路径排序），便于人工比对。
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import manifests, plugin_suite, toml_io  # noqa: E402
from app.core.plugins import PluginRejected, validate_plugin  # noqa: E402

DENY_NAMES = {
    ".env",
    ".DS_Store",
    "Thumbs.db",
    ".local_token",
    "plugin.zip",
}
DENY_SUFFIXES = {".pyc", ".pyo", ".zip", ".log", ".tmp", ".bak", ".db-shm", ".db-wal",
                 ".db-journal", ".db", ".part",
                 # 本地 YOLO 模型按需下载、绝不随包分发（军令：插件包 <10MB）。
                 ".onnx", ".ort", ".pt", ".pth", ".ckpt", ".bin", ".safetensors",
                 ".h5", ".pb", ".tflite"}
DENY_DIRS = {"__pycache__", ".git", ".idea", ".vscode", "node_modules", ".pytest_cache",
             "dev", "models"}
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
MAX_SUITE_BYTES = 20 * 1024 * 1024
# 军令 #23：``dev/`` 是开发期假数据（fixtures）的落点，只服务本机探针与浏览器验证，
# 一律不进发行包——沙箱 CSP 是 connect-src 'none'，假数据的唯一运行期事实来源是
# plugin.js 里 //# FIXTURES-BEGIN/END 之间的内嵌块，由 tools/sync_editor_fixtures.py 同步。
# 纯净发版（ADR-003）：插件包一律不带任何物理数据库，也不带随真题库分发的题库配图资产。
# core-bank 的 ``bank/schema.sql`` 仍在包里，首启由底座 ensure_bank 建空库；
# 真题库与它的配图只在本地开发机存在，绝不进任何对外发布的 zip。
DENY_PAYLOAD_PREFIXES = ("bank/assets/",)

SUITE_DEFAULT_MEMBERS = ("org.jiuzhang.bank-engine",)
SUITE_DEFAULT_ID = "org.jiuzhang.bank-suite"
SUITE_DEFAULT_NAME = "九章题库套件"
SUITE_DEFAULT_DESCRIPTION = (
    "九章题库：31 表纯后台数据引擎，不带界面，供录题、组卷、讲义等业务插件经 Host API 调用。"
)


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
    if manifests.manifest_path(plugin_dir) is None:
        raise BuildError(f"{plugin_dir} 下没有 plugin.toml")
    try:
        manifest = manifests.load_manifest(plugin_dir)
        # 声明了却被丢弃的命令要当场回给作者：打包成功不等于命令生效
        command_issues: list[dict[str, str]] = []
        info = validate_plugin(plugin_dir, manifest, command_issues)
    except (OSError, ValueError, PluginRejected) as exc:
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
    size = tmp.stat().st_size
    if size > MAX_PACKAGE_BYTES:
        tmp.unlink()
        raise BuildError(
            f"插件包 {size / 1024 / 1024:.1f} MB 超过 10 MB 上限："
            "模型等大文件必须按需下载，不能进发行包")
    tmp.replace(target)
    return target


def discover_package_dirs(plugins_dir: Path) -> list[Path]:
    if not plugins_dir.is_dir():
        return []
    result: list[Path] = []
    for child in sorted(plugins_dir.iterdir(), key=lambda item: item.name):
        if child.is_dir() and manifests.manifest_path(child) is not None:
            result.append(child)
    return result


def _resolve_plugin_dirs(members: list[str], plugins_dir: Path) -> list[Path]:
    result: list[Path] = []
    for item in members:
        candidate = Path(item)
        if manifests.manifest_path(candidate) is None:
            candidate = plugins_dir / item
        if manifests.manifest_path(candidate) is None:
            raise BuildError(f"找不到插件目录：{item}")
        result.append(candidate.resolve())
    return result


def _version_key(version: str) -> tuple[tuple[int, ...], int, str]:
    """语义化版本排序键：正式版高于同号预发布版。"""
    base = version.split("+", 1)[0]
    main, _, prerelease = base.partition("-")
    try:
        numbers = tuple(int(part) for part in main.split("."))
    except ValueError:
        numbers = (0,)
    return numbers, 0 if prerelease else 1, prerelease


def _order_by_dependency(loaded: list[tuple[dict, Path]]) -> list[tuple[dict, Path]]:
    """按 requires 拓扑排序：依赖在前，环直接拒绝。"""
    by_id = {info["id"]: (info, path) for info, path in loaded}
    ordered: list[tuple[dict, Path]] = []
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(plugin_id: str) -> None:
        if plugin_id in done:
            return
        if plugin_id in visiting:
            raise BuildError(f"套件内出现循环依赖：{plugin_id}")
        visiting.add(plugin_id)
        info, path = by_id[plugin_id]
        for required in info.get("requires") or []:
            if required in by_id:
                visit(required)
        visiting.discard(plugin_id)
        done.add(plugin_id)
        ordered.append((info, path))

    for plugin_id in by_id:
        visit(plugin_id)
    return ordered


def build_suite(
    member_dirs: list[Path],
    out_dir: Path,
    *,
    suite_id: str = SUITE_DEFAULT_ID,
    suite_name: str = SUITE_DEFAULT_NAME,
    description: str = SUITE_DEFAULT_DESCRIPTION,
    version: str = "",
) -> Path:
    """把若干已校验的子插件打成一个套件包（顶层 suite.toml + 各 <id>/）。"""
    loaded: list[tuple[dict, Path]] = []
    for plugin_dir in member_dirs:
        plugin_dir = plugin_dir.resolve()
        try:
            manifest = manifests.load_manifest(plugin_dir)
            command_issues: list[dict[str, str]] = []
            info = validate_plugin(plugin_dir, manifest, command_issues)
        except (OSError, ValueError, PluginRejected) as exc:
            raise BuildError(f"{plugin_dir.name} 清单校验失败：{exc}") from exc
        for issue in command_issues:
            label = f"「{issue['id']}」" if issue.get("id") else ""
            print(f"[WARN] {info['id']} 的命令 {label} 未登记：{issue.get('reason', '')}")
        loaded.append((info, plugin_dir))

    ids = [info["id"] for info, _ in loaded]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise BuildError("套件里有重复的插件 id：" + "、".join(duplicates))

    member_ids = set(ids)
    for info, _ in loaded:
        missing = [item for item in info.get("requires") or [] if item not in member_ids]
        if missing:
            raise BuildError(
                f"套件不完整：{info['id']} 依赖的 " + "、".join(missing)
                + " 不在套件成员里（套件必须自带全部依赖）")

    ordered = _order_by_dependency(loaded)
    suite_version = version or max(
        (info["version"] for info, _ in loaded), key=_version_key
    )
    suite_manifest = {
        "schema_version": plugin_suite.SUITE_SCHEMA_VERSION,
        "id": suite_id,
        "name": suite_name,
        "version": suite_version,
        "description": description,
        "plugins": [info["id"] for info, _ in ordered],
    }
    try:
        plugin_suite.parse_suite_manifest(suite_manifest)
    except plugin_suite.SuiteRejected as exc:
        raise BuildError(f"套件清单不合法：{exc}") from exc

    packed: list[tuple[dict, list[tuple[Path, Path]]]] = []
    total = 0
    for info, plugin_dir in ordered:
        payload = list(_iter_payload(plugin_dir))
        if not payload:
            raise BuildError(f"{info['id']} 的目录是空的")
        total += sum(path.stat().st_size for _, path in payload)
        packed.append((info, payload))
    if total > MAX_SUITE_BYTES:
        raise BuildError(
            f"套件解压总量 {total / 1024 / 1024:.1f} MB 超过 20 MB 上限："
            "大文件必须按需下载，不能进发行包")

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{suite_id}.zip"
    tmp = target.with_suffix(".zip.part")
    if tmp.exists():
        tmp.unlink()

    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr(
                plugin_suite.SUITE_FILENAME,
                toml_io.dumps(suite_manifest),
            )
            for info, payload in packed:
                for relative, path in payload:
                    arcname = PurePosixPath(info["id"], *relative.parts).as_posix()
                    archive.write(path, arcname)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise
    size = tmp.stat().st_size
    if size > MAX_SUITE_BYTES:
        tmp.unlink()
        raise BuildError(
            f"套件包 {size / 1024 / 1024:.1f} MB 超过 20 MB 上限："
            "大文件必须按需下载，不能进发行包")
    tmp.replace(target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验并打包九章算子插件（标准 zip，顶层为插件 id）")
    parser.add_argument("plugin_dir", nargs="?", help="插件目录（含 plugin.toml）")
    parser.add_argument("--all", action="store_true", help="打包 plugins/ 下全部插件")
    parser.add_argument("--plugins-dir", default=str(ROOT / "plugins"), help="插件根目录")
    parser.add_argument("--out", default=str(ROOT / "dist" / "plugins"), help="zip 输出目录")
    parser.add_argument(
        "--suite", nargs="*", default=None, metavar="PLUGIN",
        help="打套件包：成员为插件 id 或目录；不带成员时默认只打九章题库合并包",
    )
    parser.add_argument("--suite-id", default=SUITE_DEFAULT_ID, help="套件 id")
    parser.add_argument("--suite-name", default=SUITE_DEFAULT_NAME, help="套件显示名")
    parser.add_argument("--suite-version", default="", help="套件版本（缺省取成员最高版本）")
    args = parser.parse_args(argv)

    plugins_dir = Path(args.plugins_dir)
    out_dir = Path(args.out)

    if args.suite is not None:
        members = args.suite or list(SUITE_DEFAULT_MEMBERS)
        try:
            member_dirs = _resolve_plugin_dirs(members, plugins_dir)
            target = build_suite(
                member_dirs,
                out_dir,
                suite_id=args.suite_id,
                suite_name=args.suite_name,
                version=args.suite_version,
            )
        except (BuildError, OSError) as exc:
            print(f"[FAIL] 套件 {args.suite_id}: {exc}")
            return 1
        print(f"[OK] 套件 -> {target} ({target.stat().st_size / 1024:.1f} KB)")
        return 0

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
