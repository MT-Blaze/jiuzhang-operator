"""插件清单与套件清单的落点与读取。

新格式只有 TOML：``plugin.toml`` / ``suite.toml``。旧包里的 ``plugin.json`` /
``suite.json`` 只作为第三方存量兼容读入，安装/更新落地时立即转成 TOML，
不把 JSON 留在工作区。
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from app.core import toml_io, wire

PLUGIN_MANIFEST = "plugin.toml"
LEGACY_PLUGIN_MANIFEST = "plugin.json"
SUITE_MANIFEST = "suite.toml"
LEGACY_SUITE_MANIFEST = "suite.json"

PLUGIN_MANIFESTS = (PLUGIN_MANIFEST, LEGACY_PLUGIN_MANIFEST)
SUITE_MANIFESTS = (SUITE_MANIFEST, LEGACY_SUITE_MANIFEST)


def manifest_path(folder: Path) -> Path | None:
    """目录里的插件清单；TOML 优先，旧 JSON 兜底。都没有返回 None。"""
    for name in PLUGIN_MANIFESTS:
        candidate = folder / name
        if candidate.is_file():
            return candidate
    return None


def load_manifest(folder: Path) -> dict[str, Any]:
    """读插件清单；解析失败抛 ``ValueError``（调用方按拒绝处置）。"""
    path = manifest_path(folder)
    if path is None:
        raise FileNotFoundError("未找到 %s" % PLUGIN_MANIFEST)
    return parse_manifest(path.read_text(encoding="utf-8"), path.suffix)


def parse_manifest(text: str, suffix: str) -> dict[str, Any]:
    data = toml_io.loads(text) if suffix == ".toml" else wire.loads(text)
    if not isinstance(data, dict):
        raise ValueError("插件清单顶层必须是表（对象）")
    return data


def normalize_manifest(folder: Path) -> dict[str, Any]:
    """读清单；若来自旧 ``plugin.json``，就地写成 ``plugin.toml`` 并删掉旧文件。

    只在安装/更新的暂存区或落地目录调用——那是底座自己的写范围。
    """
    path = manifest_path(folder)
    if path is None:
        raise FileNotFoundError("未找到 %s" % PLUGIN_MANIFEST)
    manifest = parse_manifest(path.read_text(encoding="utf-8"), path.suffix)
    if path.name == LEGACY_PLUGIN_MANIFEST:
        toml_io.write(folder / PLUGIN_MANIFEST, manifest)
        path.unlink()
    return manifest


def suite_entry_names(entries: list[PurePosixPath]) -> list[str]:
    """zip 顶层实际存在的套件清单名（可能同时有新旧两份）。"""
    names = {str(entry) for entry in entries}
    return [name for name in SUITE_MANIFESTS if name in names]


def plugin_root_prefix(entries: list[PurePosixPath]) -> tuple[str, ...] | None:
    """定位单插件包的插件根；兼容顶层直接放清单或唯一顶层目录两种版式。"""
    for name in PLUGIN_MANIFESTS:
        if PurePosixPath(name) in entries:
            return ()
    tops = {
        parts[0]
        for parts in (entry.parts for entry in entries)
        if parts and parts[0] != "__MACOSX" and not parts[0].startswith(".")
    }
    if len(tops) == 1:
        top = next(iter(tops))
        if any(PurePosixPath(top) / name in entries for name in PLUGIN_MANIFESTS):
            return (top,)
    return None
