# -*- coding: utf-8 -*-
"""插件包结构只读校验（L0 门禁）。

范围取自 tools/sync_plugin_index.py 的 PLUGIN_DIRS（官方七支的唯一清单），
外加反向核对：plugins/ 下任何含 plugin.toml 的目录都必须已在 PLUGIN_DIRS 登记。

用法：.venv/Scripts/python.exe scripts/check_plugin_package.py
只读，不写任何文件；违反 L0 即 rc=1。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import manifests  # noqa: E402

PLUGIN_DIRS_RE = re.compile(r"PLUGIN_DIRS\s*=\s*\((.*?)\)", re.S)
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*){2,}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
REQUIRED_FIELDS = (
    "id", "name", "version", "api_version", "schema_version", "kind",
    "min_host_version", "license", "author", "description",
    "capabilities", "permissions", "bus", "slots",
)

failures: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def declared_official_plugins() -> list[str]:
    text = (ROOT / "tools" / "sync_plugin_index.py").read_text(encoding="utf-8")
    match = PLUGIN_DIRS_RE.search(text)
    if not match:
        fail("无法从 tools/sync_plugin_index.py 解析 PLUGIN_DIRS")
        return []
    return [item.strip().strip("\"'") for item in match.group(1).split(",") if item.strip()]


def check_manifest(plugin_dir: Path) -> None:
    if (plugin_dir / manifests.LEGACY_PLUGIN_MANIFEST).exists():
        fail(f"{plugin_dir.name}: 官方插件目录不许留 {manifests.LEGACY_PLUGIN_MANIFEST}")
    manifest_path = manifests.manifest_path(plugin_dir)
    if manifest_path is None:
        fail(f"{plugin_dir.name}: 缺 {manifests.PLUGIN_MANIFEST}")
        return
    try:
        manifest = manifests.load_manifest(plugin_dir)
    except Exception as exc:  # noqa: BLE001 - 门禁要把解析失败如实报出来
        fail(f"{plugin_dir.name}: {manifests.PLUGIN_MANIFEST} 解析失败（{exc}）")
        return

    if manifest.get("id") != plugin_dir.name:
        fail(f"{plugin_dir.name}: 顶层目录名 != 清单的 id（{manifest.get('id')!r}）")
    if not ID_RE.match(str(manifest.get("id", ""))):
        fail(f"{plugin_dir.name}: id 不符合反向域名格式")
    for field in REQUIRED_FIELDS:
        if field not in manifest:
            fail(f"{plugin_dir.name}: 清单缺字段 {field}")
    for field in ("version", "min_host_version"):
        value = manifest.get(field)
        if value is not None and not SEMVER_RE.match(str(value)):
            fail(f"{plugin_dir.name}: {field}={value!r} 不是语义化版本 x.y.z")
    engine = manifest.get("engine")
    if isinstance(engine, dict):
        host = engine.get("host_version")
        if host is not None and not SEMVER_RE.match(str(host)):
            fail(f"{plugin_dir.name}: engine.host_version={host!r} 不是语义化版本")

    if "backend" in manifest:
        fail(f"{plugin_dir.name}: 出现禁止的 backend 字段（底座不支持后端插件）")
    if manifest.get("license") != "Apache-2.0":
        fail(f"{plugin_dir.name}: license 必须是 Apache-2.0，当前 {manifest.get('license')!r}")

    license_path = plugin_dir / "LICENSE"
    if not license_path.is_file():
        fail(f"{plugin_dir.name}: 缺 LICENSE 文件")
    else:
        head = license_path.read_text(encoding="utf-8", errors="replace")[:400]
        if "Apache License" not in head or "Version 2.0" not in head:
            fail(f"{plugin_dir.name}: LICENSE 不是 Apache License 2.0 全文")

    if manifest.get("kind") == "ui":
        notes.append(f"{plugin_dir.name}: kind=ui 需在装载时确认沙箱 iframe 与净化链路")


def main() -> int:
    official = declared_official_plugins()
    on_disk = sorted(
        path.name for path in (ROOT / "plugins").iterdir()
        if path.is_dir() and manifests.manifest_path(path) is not None
    )
    for name in official:
        path = ROOT / "plugins" / name
        if not path.is_dir():
            fail(f"PLUGIN_DIRS 登记了 {name}，但 plugins/{name} 不存在")
            continue
        check_manifest(path)

    unregistered = [name for name in on_disk if name not in official]
    if unregistered:
        fail(f"plugins/ 下存在未登记进 PLUGIN_DIRS 的插件目录：{', '.join(unregistered)}")

    seed = ROOT / "plugins" / "org.jiuzhang.core-bank"
    if seed.is_dir() and manifests.manifest_path(seed) is not None:
        fail("种子库 org.jiuzhang.core-bank 出现了插件清单，它不应该是插件")

    for note in notes:
        print(f"[NOTE] {note}")
    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        print(f"check-plugin-package: {len(failures)} 项违反 L0")
        return 1
    print(f"check-plugin-package: PASS（官方插件 {len(official)} 支，结构红线全部通过）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
