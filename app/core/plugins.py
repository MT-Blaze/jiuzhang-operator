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

# 右侧面板控件（v0.5.5）：插件只能声明「文本 + 指令模板」，不能塞 HTML。
_UI_KEY = re.compile(r"^[a-z][a-z0-9_]{0,15}$")
_UI_MAX_CONTROLS = 8
_UI_MAX_OPTIONS = 12
_UI_MAX_LABEL = 24
_UI_MAX_COMMAND = 200

_GRADE_OPTIONS = [
    {"value": "全部", "label": "全部"},
    {"value": "高一", "label": "高一"},
    {"value": "高二", "label": "高二"},
    {"value": "高三", "label": "高三"},
]
_DIFFICULTY_OPTIONS = [
    {"value": "全部", "label": "全部"},
    {"value": "基础", "label": "基础"},
    {"value": "中档", "label": "中档"},
    {"value": "压轴", "label": "压轴"},
    {"value": "新定义", "label": "新定义"},
]


def _ui_text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _ui_select(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or raw.get("type") != "select":
        return None
    key = raw.get("id") or raw.get("key")
    if not isinstance(key, str) or _UI_KEY.fullmatch(key) is None:
        return None
    label = _ui_text(raw.get("label"), _UI_MAX_LABEL) or key
    options: list[dict[str, str]] = []
    for option in raw.get("options") or []:
        if not isinstance(option, dict):
            continue
        value = _ui_text(option.get("value"), 32)
        text = _ui_text(option.get("label"), _UI_MAX_LABEL) or value
        if value and text:
            options.append({"value": value, "label": text})
        if len(options) >= _UI_MAX_OPTIONS:
            break
    if not options:
        return None
    default = _ui_text(raw.get("default"), 32) or options[0]["value"]
    if default not in [item["value"] for item in options]:
        default = options[0]["value"]
    return {
        "id": key,
        "type": "select",
        "key": key,
        "label": label,
        "options": options,
        "default": default,
    }


def _ui_button(raw: Any, position: int, used_ids: set[str]) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or raw.get("type") != "button":
        return None
    label = _ui_text(raw.get("label"), _UI_MAX_LABEL)
    command = _ui_text(raw.get("command"), _UI_MAX_COMMAND)
    if not label or not command:
        return None
    control_id = _ui_text(raw.get("id"), 32) or "btn_%d" % position
    if _UI_KEY.fullmatch(control_id) is None:
        control_id = "btn_%d" % position
    base = control_id
    suffix = 2
    while control_id in used_ids:
        control_id = "%s_%d" % (base, suffix)
        suffix += 1
    used_ids.add(control_id)
    return {"id": control_id, "type": "button", "label": label, "command": command}


def _normalize_ui(raw: Any, plugin_id: str, name: str) -> dict[str, Any] | None:
    """校验插件自报的右侧面板；坏控件逐条丢弃，全坏则回落到默认面板。"""
    if not isinstance(raw, dict):
        return None
    controls: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for position, item in enumerate(raw.get("controls") or []):
        if len(controls) >= _UI_MAX_CONTROLS:
            break
        if not isinstance(item, dict):
            continue
        if item.get("type") == "select":
            control = _ui_select(item)
            if control and control["id"] not in used_ids:
                used_ids.add(control["id"])
                controls.append(control)
        elif item.get("type") == "button":
            control = _ui_button(item, position + 1, used_ids)
            if control:
                controls.append(control)
    if not controls:
        return None
    return {
        "plugin_id": plugin_id,
        "title": _ui_text(raw.get("title"), 40) or (name + "快捷操作"),
        "hint": _ui_text(raw.get("hint"), 120)
        or "点按钮等于在对话区发送对应指令；下拉选择会同步给 AI 上下文。",
        "controls": controls,
    }


def _default_ui(plugin_id: str, name: str, kind: str, capabilities: list[str]) -> dict[str, Any]:
    """没有自报面板时，按插件类型/能力生成一套真能执行的默认控件。"""
    controls: list[dict[str, Any]] = []
    if "question.import" in capabilities:
        controls.extend(
            [
                {
                    "id": "grade",
                    "type": "select",
                    "key": "grade",
                    "label": "年级",
                    "options": _GRADE_OPTIONS,
                    "default": "全部",
                },
                {
                    "id": "difficulty",
                    "type": "select",
                    "key": "difficulty",
                    "label": "难度",
                    "options": _DIFFICULTY_OPTIONS,
                    "default": "全部",
                },
                {
                    "id": "random_question",
                    "type": "button",
                    "label": "随机出题",
                    "command": "随机出一道题（年级：{grade}；难度：{difficulty}）",
                },
                {
                    "id": "list_questions",
                    "type": "button",
                    "label": "列出题库",
                    "command": "列出题库里的所有题目",
                },
                {
                    "id": "show_first",
                    "type": "button",
                    "label": "查看第一题",
                    "command": "渲染第一题题卡",
                },
            ]
        )
    elif "question.render" in capabilities:
        controls.extend(
            [
                {
                    "id": "render_first",
                    "type": "button",
                    "label": "渲染示例题",
                    "command": "渲染一道示例题卡",
                },
                {
                    "id": "show_solution",
                    "type": "button",
                    "label": "查看解析",
                    "command": "查看第一题的解析",
                },
            ]
        )
    elif kind == "exporter" or "question.export" in capabilities:
        controls.append(
            {
                "id": "export_pdf",
                "type": "button",
                "label": "导出 PDF",
                "command": "把当前题目导出为 PDF",
            }
        )
    else:
        controls.append(
            {
                "id": "what_can",
                "type": "button",
                "label": "这个插件能做什么",
                "command": "这个插件能做什么？",
            }
        )
    return {
        "plugin_id": plugin_id,
        "title": name + "快捷操作",
        "hint": "点按钮等于在对话区发送对应指令；下拉选择会同步给 AI 上下文。",
        "controls": controls,
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

    ui = _normalize_ui(manifest.get("ui"), plugin_id, name)
    if ui is None:
        ui = _default_ui(plugin_id, name, manifest["kind"], capabilities)

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
        "ui": ui,
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
