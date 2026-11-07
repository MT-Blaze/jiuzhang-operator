"""插件套件（suite.toml）与插件依赖声明（requires）的契约。

契约来源：PLUGIN_SPEC §1.8。套件只是**分发容器**：一个 zip 里装若干子插件，
底座仍然按普通插件目录逐个发现、启用与校验；套件本身不是插件，不占左栏、
没有入口页、不参与热更新。``requires`` 是清单里的硬依赖：缺了它插件就不启用，
绝不允许只装一个空壳界面。
"""

from __future__ import annotations

import re
from typing import Any

SUITE_FILENAME = "suite.toml"
SUITE_SCHEMA_VERSION = "1.0"
MAX_SUITE_PLUGINS = 16
MAX_REQUIRES = 16
MAX_SUITE_BYTES = 64 * 1024

_PLUGIN_ID = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


class SuiteRejected(ValueError):
    """套件清单未通过校验。"""


def normalize_requires(raw: Any, plugin_id: str) -> list[str]:
    """归一 ``requires``；写坏一律拒绝——依赖是硬约束，不能静默丢弃。

    与 ``bus``/``ui`` 的宽容归一不同：少一条依赖，插件会在运行时变成空壳，
    作者却以为声明生效了。这里宁可装不上，也要让作者当场看到原因。
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("requires 必须是数组")
    if len(raw) > MAX_REQUIRES:
        raise ValueError(f"requires 最多 {MAX_REQUIRES} 条")
    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        if not isinstance(item, str) or _PLUGIN_ID.fullmatch(item) is None:
            raise ValueError(f"requires 里的 {item!r} 不是合法插件 id（反向域名）")
        if item == plugin_id:
            raise ValueError("requires 不能依赖插件自己")
        if item in seen:
            raise ValueError(f"requires 重复声明：{item}")
        seen.add(item)
        result.append(item)
    return result


def parse_suite_manifest(raw: Any) -> dict[str, Any]:
    """校验 suite.toml 并返回归一后的套件元信息。"""
    if not isinstance(raw, dict):
        raise SuiteRejected("套件清单必须是表（TOML 对象）")
    if raw.get("schema_version") != SUITE_SCHEMA_VERSION:
        raise SuiteRejected(f"套件清单的 schema_version 必须为 {SUITE_SCHEMA_VERSION}")

    suite_id = raw.get("id")
    if not isinstance(suite_id, str) or _PLUGIN_ID.fullmatch(suite_id) is None:
        raise SuiteRejected("套件清单的 id 缺失或不是反向域名格式")

    name = raw.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 64:
        raise SuiteRejected("套件清单的 name 长度必须为 1–64")

    version = raw.get("version", "")
    if version and (not isinstance(version, str) or _SEMVER.fullmatch(version) is None):
        raise SuiteRejected("套件清单的 version 必须是语义化版本")

    description = raw.get("description", "")
    if not isinstance(description, str):
        raise SuiteRejected("套件清单的 description 必须是字符串")

    plugins = raw.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        raise SuiteRejected("套件清单的 plugins 必须是非空数组")
    if len(plugins) > MAX_SUITE_PLUGINS:
        raise SuiteRejected(f"一个套件最多装 {MAX_SUITE_PLUGINS} 个子插件")

    seen: set[str] = set()
    members: list[str] = []
    for item in plugins:
        if not isinstance(item, str) or _PLUGIN_ID.fullmatch(item) is None:
            raise SuiteRejected(f"suite.toml 的成员 {item!r} 不是合法插件 id")
        if item in seen:
            raise SuiteRejected(f"suite.toml 的成员重复：{item}")
        seen.add(item)
        members.append(item)
    if suite_id in seen:
        raise SuiteRejected("套件 id 不能与其子插件 id 相同")

    return {
        "schema_version": SUITE_SCHEMA_VERSION,
        "id": suite_id,
        "name": name,
        "version": version,
        "description": description[:200],
        "plugins": members,
    }


def dependency_report(
    plugins: list[dict[str, Any]], disabled: set[str]
) -> dict[str, dict[str, list[str]]]:
    """按 ``requires`` 算依赖闭包，返回被依赖卡住的插件。

    依赖可以传递：A 依赖 B、B 依赖 C，C 没装则 A、B 一起出局。算法反复剔除
    「依赖不在可用集合里」的插件，直到稳定（不动点）——顺序无关，也不会死循环。
    环上的成员若都在，彼此的依赖都算满足，不剔除；环里缺一个才会整圈出局。

    返回 ``{插件 id: {"missing": [...], "disabled": [...], "blocked": [...]}}``；
    三者分别表示：没装、装了但被人停用、装了但自己也被依赖卡住。
    """
    installed = {info["id"] for info in plugins}
    active = installed - set(disabled)
    requires = {
        info["id"]: [item for item in info.get("requires") or [] if isinstance(item, str)]
        for info in plugins
    }
    blocked: dict[str, dict[str, list[str]]] = {}
    changed = True
    while changed:
        changed = False
        for plugin_id in sorted(active):
            missing = [item for item in requires[plugin_id] if item not in active]
            if not missing:
                continue
            blocked[plugin_id] = {
                "missing": [item for item in missing if item not in installed],
                "disabled": [item for item in missing if item in disabled],
                "blocked": [item for item in missing if item in blocked],
            }
            active.discard(plugin_id)
            changed = True
    return blocked


def dependency_message(plugin_id: str, problem: dict[str, list[str]]) -> str:
    """把依赖问题翻成一句人话，直接进接口与界面。"""
    parts: list[str] = []
    if problem.get("missing"):
        parts.append("未安装：" + "、".join(problem["missing"]))
    if problem.get("disabled"):
        parts.append("已停用：" + "、".join(problem["disabled"]) + "（请在设置页重新启用）")
    if problem.get("blocked"):
        parts.append("依赖链不可用：" + "、".join(problem["blocked"]))
    detail = "；".join(parts) or "依赖不可用"
    return f"{plugin_id} 缺少依赖插件（{detail}），已保持停用"
