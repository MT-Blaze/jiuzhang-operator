"""能力路由字典（Command Registry）：清单声明 → 宿主内存字典。

契约来源：PLUGIN_SPEC §2.14。三条硬边界：

1. **只认清单**：插件在 ``contributes.commands`` 里写什么，底座才登记什么。
   运行期自报的 id 一律不查表——与 ``plugin_id`` 不认 payload 自报同一条规矩。
2. **官方命名空间只给官方插件**：``org.jiuzhang.*`` 的命令必须落在五大分类
   ``org.jiuzhang.action.{input,process,output,data,view}.`` 之下，且只有插件 id
   同样以 ``org.jiuzhang.`` 开头的清单才能声明。第三方用自定义反向域名
   （如 ``com.zhang.tidy``），越权声明逐条丢弃——不拒装，也绝不生效。
3. **命令 id 是全局唯一的路由键**：同一个 id 被多个插件声明时，按插件 id
   字典序先到先得，后来者丢弃并记账（``commands_rejected`` 回给前端）。

底座不做签名/摘要校验（白嫖条款 §1.1），所以第 2 条只保证「声明与命名空间
自洽」，不是身份认证：装了谁的插件是老师自己的选择。

第 4 条安全闸在宿主侧：清单给某条命令标 ``requires_user: true``，宿主在转发前
弹一次当场确认，用户拒绝就回 ``COMMAND_DENIED``，请求绝不落到目标插件。
"""

from __future__ import annotations

import re
from typing import Any

OFFICIAL_PLUGIN_PREFIX = "org.jiuzhang."
OFFICIAL_COMMAND_PREFIX = "org.jiuzhang.action."
OFFICIAL_CATEGORIES = ("input", "process", "output", "data", "view")

MAX_COMMANDS = 32
MAX_COMMAND_ID = 96
MAX_COMMAND_TITLE = 32
MAX_COMMAND_SEGMENTS = 8

# 小写、点/连字符分段、至少三段（org.jiuzhang.action.output.export_word 为五段）；
# 段内允许下划线，官方叶子名与第三方惯例都是 snake_case（export_word / tidy_tags）。
_COMMAND_ID = re.compile(r"^[a-z0-9][a-z0-9_]*(?:[.-][a-z0-9_]+){2,7}$")


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _issue(plugin_id: str, command_id: str, reason: str) -> dict[str, str]:
    return {"plugin_id": plugin_id, "id": command_id, "reason": reason}


def _id_problem(command_id: str, plugin_id: str) -> str:
    """命令 id 自身的问题；空串表示合法。"""
    if not command_id:
        return "缺少命令 id"
    if len(command_id) > MAX_COMMAND_ID:
        return f"命令 id 超过 {MAX_COMMAND_ID} 个字符"
    if _COMMAND_ID.fullmatch(command_id) is None:
        return "命令 id 必须是小写反向域名、至少三段（如 com.zhang.tidy）"
    if command_id.count(".") + 1 > MAX_COMMAND_SEGMENTS:
        return f"命令 id 最多 {MAX_COMMAND_SEGMENTS} 段"
    if command_id.startswith(OFFICIAL_PLUGIN_PREFIX):
        if not plugin_id.startswith(OFFICIAL_PLUGIN_PREFIX):
            return "官方命名空间 org.jiuzhang.* 只能由官方插件声明"
        if not command_id.startswith(OFFICIAL_COMMAND_PREFIX):
            return "官方命令必须以 org.jiuzhang.action. 开头"
        rest = command_id[len(OFFICIAL_COMMAND_PREFIX):]
        category, _, leaf = rest.partition(".")
        if category not in OFFICIAL_CATEGORIES:
            return "官方命令必须落在 input/process/output/data/view 五大分类下"
        if not leaf:
            return "官方命令缺叶子名（org.jiuzhang.action.<分类>.<动作>）"
    return ""


def normalize_commands(
    contributes: Any, plugin_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """把清单里的 ``contributes.commands`` 归一成登记条目；坏条目逐条丢弃并记账。

    ``requires_user`` 只认清单里的布尔真值：高副作用命令（导出、覆盖、批量删改）
    由作者自己声明，宿主据此在转发前弹一次确认；非布尔值一律按 false 处理，
    不猜作者意图。
    """
    if contributes is None:
        return [], []
    if not isinstance(contributes, dict):
        return [], [_issue(plugin_id, "", "contributes 必须是对象")]
    raw = contributes.get("commands")
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], [_issue(plugin_id, "", "contributes.commands 必须是数组")]

    commands: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []
    seen: set[str] = set()
    for position, item in enumerate(raw):
        if len(commands) >= MAX_COMMANDS:
            issues.append(
                _issue(plugin_id, "", f"命令数超过 {MAX_COMMANDS} 条上限，其余已忽略")
            )
            break
        if not isinstance(item, dict):
            issues.append(_issue(plugin_id, "", f"第 {position + 1} 条命令不是对象"))
            continue
        command_id = item.get("id") if isinstance(item.get("id"), str) else ""
        command_id = command_id.strip()
        problem = _id_problem(command_id, plugin_id)
        if problem:
            issues.append(_issue(plugin_id, command_id[:MAX_COMMAND_ID], problem))
            continue
        if command_id in seen:
            issues.append(_issue(plugin_id, command_id, "同一插件里命令 id 重复"))
            continue
        title = _text(item.get("title"), MAX_COMMAND_TITLE)
        if not title:
            issues.append(_issue(plugin_id, command_id, "缺少 title"))
            continue
        seen.add(command_id)
        commands.append({
            "id": command_id,
            "title": title,
            "requires_user": item.get("requires_user") is True,
        })
    return commands, issues


def build_registry(plugins: list[dict[str, Any]]) -> dict[str, Any]:
    """按启用插件集建全局字典（同 id 先到先得），并返回冲突账。

    停用的插件不进字典：它的 iframe 已被释放，路由过去只会得到超时。
    """
    registry: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, str]] = []
    for plugin in sorted(plugins, key=lambda item: str(item.get("id") or "")):
        if plugin.get("enabled") is False:
            continue
        plugin_id = str(plugin.get("id") or "")
        plugin_name = str(plugin.get("name") or plugin_id)
        for command in plugin.get("commands") or []:
            command_id = str(command.get("id") or "")
            if not command_id:
                continue
            if command_id in registry:
                issues.append(
                    _issue(
                        plugin_id,
                        command_id,
                        "命令 id 已被 " + registry[command_id]["plugin_id"] + " 占用",
                    )
                )
                continue
            registry[command_id] = {
                "id": command_id,
                "title": str(command.get("title") or command_id),
                "plugin_id": plugin_id,
                "plugin_name": plugin_name,
                "requires_user": command.get("requires_user") is True,
            }
    return {
        "commands": [registry[key] for key in sorted(registry)],
        "issues": issues,
    }
