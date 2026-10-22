"""插件发现、清单校验与只读资产解析。

契约来源：PLUGIN_SPEC.md。底座当前只实现前端插件；清单里的 backend
仍按规范拒绝，避免出现“声明了却没有运行时”的假能力。
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from app.core.config import settings

PROTOCOL = "jzo-plugin/1"
SUPPORTED_API_MAJOR = 1

_PLUGIN_ID = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
_API_VERSION = re.compile(r"^(\d+)\.\d+$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

_KINDS = {"renderer", "importer", "exporter", "tool"}
_SLOTS = {"question.card", "question.detail", "question.paper", "answer.panel"}
_CAPABILITIES = {"question.render", "question.export", "question.import"}
_PERMISSIONS = {
    "questions:read",
    "questions:write",
    "assets:read",
    "assets:write",
    "storage:plugin",
    "ai:invoke",
    "export:file",
}


class PluginRejected(Exception):
    """清单未通过校验。"""


class PluginAssetError(Exception):
    """插件资源路径不可用。"""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PluginRejected(message)


def validate_plugin(plugin_dir: Path, manifest: Any) -> dict[str, Any]:
    """按 PLUGIN_SPEC 校验一份清单，返回发现接口下发的插件信息。"""
    _require(isinstance(manifest, dict), "plugin.json 必须是 JSON 对象")
    _require(manifest.get("schema_version") == "1.0", "schema_version 必须为 1.0")

    plugin_id = manifest.get("id")
    _require(
        isinstance(plugin_id, str) and _PLUGIN_ID.fullmatch(plugin_id) is not None,
        "id 必须是反向域名格式",
    )
    _require(plugin_dir.name == plugin_id, "目录名必须与 id 一致")

    name = manifest.get("name")
    _require(isinstance(name, str) and 1 <= len(name) <= 64, "name 长度必须为 1–64")

    version = manifest.get("version")
    _require(
        isinstance(version, str) and _SEMVER.fullmatch(version) is not None,
        "version 必须是语义化版本",
    )

    api_match = _API_VERSION.fullmatch(str(manifest.get("api_version", "")))
    _require(
        api_match is not None and int(api_match.group(1)) == SUPPORTED_API_MAJOR,
        f"api_version 主版本必须为 {SUPPORTED_API_MAJOR}.x",
    )

    _require(manifest.get("kind") in _KINDS, "kind 非法")
    description = manifest.get("description")
    _require(
        isinstance(description, str) and 1 <= len(description) <= 200,
        "description 长度必须为 1–200",
    )
    _require(manifest.get("license") == "Apache-2.0", "license 必须为 Apache-2.0")
    _require((plugin_dir / "LICENSE").is_file(), "缺少插件 LICENSE 文件")
    _require("backend" not in manifest, "当前底座不支持后端插件")

    slots = manifest.get("slots")
    _require(
        isinstance(slots, list) and bool(slots) and all(item in _SLOTS for item in slots),
        "slots 缺失或包含未定义插槽",
    )
    capabilities = manifest.get("capabilities")
    _require(
        isinstance(capabilities, list)
        and bool(capabilities)
        and all(item in _CAPABILITIES for item in capabilities),
        "capabilities 缺失或包含未定义能力",
    )
    permissions = manifest.get("permissions")
    _require(
        isinstance(permissions, list) and all(item in _PERMISSIONS for item in permissions),
        "permissions 包含未定义权限",
    )
    if manifest["kind"] == "renderer":
        _require("question.render" in capabilities, "renderer 必须声明 question.render")

    entry = manifest.get("entry")
    _require(isinstance(entry, dict), "entry 缺失")
    frontend = entry.get("frontend")
    _require(isinstance(frontend, str) and bool(frontend), "entry.frontend 缺失")
    relative = PurePosixPath(frontend)
    _require(
        not relative.is_absolute() and ".." not in relative.parts,
        "entry.frontend 必须是包内相对路径",
    )
    _require(
        len(relative.parts) > 1 and relative.parts[0] == "dist",
        "entry.frontend 必须位于 dist/",
    )
    frontend_path = plugin_dir.joinpath(*relative.parts)
    _require(frontend_path.is_file(), "entry.frontend 指向的文件不存在")

    css_relative = relative.parent / "plugin.css"
    css_path = plugin_dir.joinpath(*css_relative.parts)
    css_url = None
    if css_path.is_file():
        css_url = f"/plugin-assets/{plugin_id}/{css_relative.as_posix()}"

    return {
        "id": plugin_id,
        "name": name,
        "version": version,
        "api_version": manifest["api_version"],
        "kind": manifest["kind"],
        "description": description,
        "author": manifest.get("author"),
        "license": manifest["license"],
        "slots": slots,
        "capabilities": capabilities,
        "permissions": permissions,
        "entry_url": f"/plugin-assets/{plugin_id}/{relative.as_posix()}",
        "css_url": css_url,
    }


def discover_plugins() -> dict[str, Any]:
    plugins: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    root = Path(settings.plugins_dir)

    if root.is_dir():
        for plugin_dir in sorted(root.iterdir(), key=lambda item: item.name):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue
            manifest_path = plugin_dir / "plugin.json"
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                plugins.append(validate_plugin(plugin_dir, manifest))
            except (PluginRejected, OSError, json.JSONDecodeError) as exc:
                rejected.append({"id": plugin_dir.name, "reason": str(exc)})

    return {"protocol": PROTOCOL, "plugins": plugins, "rejected": rejected}


def resolve_plugin_asset(plugin_id: str, asset_path: str) -> Path:
    if not plugin_id or _PLUGIN_ID.fullmatch(plugin_id) is None:
        raise PluginAssetError("插件 ID 非法")

    package_root = (Path(settings.plugins_dir) / plugin_id).resolve()
    if not (package_root / "dist").is_dir():
        raise PluginAssetError("插件不存在")

    relative = PurePosixPath(asset_path.replace("\\", "/"))
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise PluginAssetError("插件资源路径非法")
    if relative.parts[0] != "dist":
        raise PluginAssetError("只允许访问插件的 dist/ 资源")

    walk = package_root
    for part in relative.parts:
        walk = walk / part
        if walk.is_symlink():
            raise PluginAssetError("插件包内不得包含符号链接")

    target = walk.resolve()
    try:
        target.relative_to(package_root)
    except ValueError as exc:
        raise PluginAssetError("插件资源路径越界") from exc
    if not target.is_file():
        raise PluginAssetError("插件资源不存在")
    return target
