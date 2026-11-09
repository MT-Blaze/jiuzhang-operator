"""插件发现、清单校验与只读资产解析。

契约来源：docs/PLUGIN_SPEC.md。底座当前只实现前端插件；清单里的 backend
仍按规范拒绝，避免出现“声明了却没有运行时”的假能力。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Any

from app.core import commands as command_registry
from app.core import manifests, plugin_state, plugin_suite, toml_io
from app.core.config import plugins_dir

PROTOCOL = "jzo-plugin/1"
SUPPORTED_API_MAJOR = 1
# 前端资源根：dist/ 是通用约定，webui/ 供「引擎 + 界面同包」的插件；只认包内相对路径。
_ASSET_ROOTS = ("dist", "webui")

_PLUGIN_ID = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
_API_VERSION = re.compile(r"^(\d+)\.\d+$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

_KINDS = {"renderer", "importer", "exporter", "tool"}
_SLOTS = {
    "question.card",
    "question.detail",
    "question.paper",
    "answer.panel",
    # v0.6.0：中栏画布。声明它的插件可以在舞台开一个 Tabs 页（沙箱 iframe）
    "stage.center",
    # 军令 #13：右栏辅助面板。同一时刻只挂一个，没插件认领时回退原生 AI 副驾
    "sidebar.right",
}
_CAPABILITIES = {
    "question.render",
    "question.export",
    "question.import",
    # 录题工作台：产出标准题目并写入公共题库（v0.6.2）
    "question.edit",
    # 组卷与讲义是「消费题篮、产出 A4」的能力，不等同于单题渲染/导出
    "paper.generate",
    "handout.render",
    # v0.8.2：声明自己可当作「活跃题库」的插件（默认是官方 bank-engine）
    "bank.provider",
    # 军令 #20：纯视图插件——只读活跃题库、可走查重扫描与合并的宿主通道，
    # 自己不持有题库。与 bank.provider 分离，界面换皮不必动数据引擎。
    "bank.view",
}
_PERMISSIONS = {
    "questions:read",
    "questions:write",
    "assets:read",
    "assets:write",
    "storage:plugin",
    "ai:invoke",
    "export:file",
}

# 舞台接管（v0.6.0）：embed 内嵌一角 / takeover 占满中栏 / fullscreen 收掉左右栏
_STAGE_MODES = {"embed", "takeover", "fullscreen"}
_STAGE_MAX_TITLE = 24
# 页签权重（军令 #16 模块三）：light 后台只收定时器（浅休眠），heavy 计入 LRU 存活上限。
# 缺省一律按 heavy——底座绝不猜「这个插件很轻」，是插件自己声明才给它免死金牌。
_STAGE_WEIGHTS = {"light", "heavy"}

# 事件总线主题白名单。发布只许投给底座托管的三区与舞台选区——
# 不许插件发 ui.params.* / layout.*，那是人和底座的地盘（防插件反向操控面板）。
_BUS_PUBLISH = {"region.dock", "region.left", "region.right", "stage.selection",
                # 军令 #27：录题插件在辅助栏那张 iframe 里收到的文件，转交给宿主，
                # 由宿主送进画布的收集筐（插件两帧之间不直连）。
                "editor.collect_files",
                # 军令 #29：画布把「鼠标停在哪一题」「画布在滚动」报给辅助栏，
                # 辅助栏据此亮边缘、收批次公共元数据。
                "editor.canvas_state",
                # 军令 #31：辅助栏把查重命中报告投给画布（渲染能力只在画布那帧），
                # 办完再投一声「收窗」。两帧之间始终隔着宿主这一跳。
                "editor.dup_review",
                # 军令 #31 · 4.3：清洗后的「先看后换」——辅助栏把对照投给画布，
                # 画布回一声 opened / closed / tab_not_live，面板据此放按钮或降级。
                "editor.clean_review",
                "editor.clean_review_state",
                # 军令 #32 · 第五步：重题池的左右渲染对比住画布那帧（它才有 MathJax），
                # 四个动作住辅助栏——辅助栏把「开窗 / 关窗」投过来，跟 dup_review 同一形状。
                "editor.pool_review",
                # 同一步：辅助栏的【全部入库】要让画布先整批扫琥珀灯、有缺件就跳到最上面
                # 那道；跳与不跳都是画布那帧的事（它才有滚动与题号）。
                "editor.batch_review",
                # 查重三栏：辅助栏的裁判台发令，画布变身三栏；画布 Esc 收窗回投辅助栏。
                "editor.dup_compare"}
_BUS_SUBSCRIBE = {
    "ui.params.changed",
    "layout.changed",
    "stage.tab.activated",
    "stage.tab.opened",
    "stage.tab.closed",
    "stage.tab.sleep",
    "theme.changed",
    "question.updated",
    "basket.changed",
    # 军令 #15：人点面板按钮 → 底座把展开后的指令交给右栏助手插件代发
    "panel.button.click",
    # 录题插件的当前题：随对话一起搬进右栏的助手插件要能感知选区（AI 副驾）
    "stage.selection",
    # #18-结 任务二：底座真在广播、插件也真在订的五个主题。以前白名单缺这几条，
    # 插件照着 PLUGIN_SPEC 声明照样被 _normalize_bus 静默丢弃——「声明了不算数」
    # 比不声明更坏：作者以为是权限问题，其实是清单压根没授权通道。
    "system.question_updated",
    "system.bank_query",
    "plugin.updated",
    "editor.apply_patch",
    "system.open_editor",
    # 军令 #24：中转站动了（暂存 / 入库 / 彻底删除）→ 录题插件据此撤掉已走的题
    "system.pending_updated",
    # 军令 #27：宿主把收集到的文件转给画布的收集筐
    "editor.collect_files",
    # 军令 #29：画布的悬停与滚动信号（呼吸灯与批次折叠）
    "editor.canvas_state",
    # 军令 #31：查重命中的开窗 / 收窗指令（对比浮层住在画布帧）
    "editor.dup_review",
    # 军令 #31 · 4.3：清洗预览的两条通道——画布订「对照」，辅助栏订「画布回执」。
    # 少了这两条，清单写着、_normalize_bus 静默丢弃，面板永远等不到 opened/closed。
    "editor.clean_review",
    "editor.clean_review_state",
    # 军令 #32 · 第五步：重题池画布（辅助栏→画布开窗）与整批扫灯 / 全部入库（辅助栏→画布）。
    # 画布那帧有 MathJax 与滚动，辅助栏那帧有按钮——两帧之间还是隔宿主这一跳。
    "editor.pool_review",
    "editor.batch_review",
    # 查重三栏：两帧之间的变身 / 决断后换题 / Esc 收窗都走这一条。
    "editor.dup_compare",
}
# 每个插件最多声明多少个主题。军令 #31 给录题插件加了第九条（查重开窗），
# 上限跟着抬到 10；4.3 再加两条（清洗对照 + 回执）后录题插件订到 11 条，
# 上限抬到 12——仍然是个紧箍咒，只是不许再拿旧上限当理由拒掉真需求。
# 军令 #32 · 第五步实数：录题插件订 13 条（新增池画布开窗 + 整批扫灯两条）、
# 发 11 条，12 的上限已经贴边——再走一条真需求就会静默丢声明（丢的是清单里
# 写得明明白白的主题，比拒得更早还坏）。抬到 16：留三条余量，不放宽白名单。
_BUS_MAX_TOPICS = 16

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
        # panel=false：插件把这套控件画进自己的面板，宿主不再重复一层快捷操作。
        # 控件本身照常登记，宿主仍可据此仲裁插件经 ui.params.set 发来的参数。
        # 录题辅助栏现在靠「自己声明了 sidebar.right」这条结构性判据由宿主自动判断，
        # 不再靠这个开关——字面上的 panel=false 容易被读成「关掉辅助栏」。
        "panel": raw.get("panel") is not False,
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
        "panel": True,
    }


def _normalize_stage(raw: Any) -> dict[str, Any] | None:
    """校验插件自报的舞台声明（v0.6.0）。

    与 ``ui`` 同口径：宽容归一而不是整包拒装——写错一个字段不该让插件装不上，
    但非法值一律退回最保守的 ``embed``，绝不因为清单写得大就给它更大的舞台。
    """
    if not isinstance(raw, dict):
        return None
    mode = raw.get("mode")
    if mode not in _STAGE_MODES:
        mode = "embed"
    weight = raw.get("weight")
    if weight not in _STAGE_WEIGHTS:
        weight = "heavy"
    title = _ui_text(raw.get("title"), _STAGE_MAX_TITLE)
    priority = raw.get("priority")
    if not isinstance(priority, int) or isinstance(priority, bool):
        priority = 0
    return {
        "region": "center",
        "mode": mode,
        "weight": weight,
        "title": title,
        "priority": max(-100, min(100, priority)),
        "singleton": bool(raw.get("singleton", True)),
    }


def _normalize_bus(raw: Any) -> dict[str, Any]:
    """归一插件事件总线授权；未声明的按最小集给，白名单外的一律丢弃。"""
    subscribe = ["ui.params.changed"]
    publish = ["region.dock"]
    if isinstance(raw, dict):
        wanted_sub = raw.get("subscribe")
        if isinstance(wanted_sub, list):
            subscribe = [
                item for item in wanted_sub
                if isinstance(item, str) and item in _BUS_SUBSCRIBE
            ][:_BUS_MAX_TOPICS]
        wanted_pub = raw.get("publish")
        if isinstance(wanted_pub, list):
            publish = [
                item for item in wanted_pub
                if isinstance(item, str) and item in _BUS_PUBLISH
            ][:_BUS_MAX_TOPICS]
    return {"subscribe": subscribe, "publish": publish}


class PluginRejected(Exception):
    """清单未通过校验。"""


class PluginAssetError(Exception):
    """插件资源路径不可用。"""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PluginRejected(message)


def validate_plugin(
    plugin_dir: Path, manifest: Any, command_issues: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """按 PLUGIN_SPEC 校验一份清单，返回发现接口下发的插件信息。

    ``command_issues`` 是可选出参：发现流程把被丢弃的命令声明收进去记账，
    安装/打包流程不传，保持旧调用点不变。
    """
    _require(isinstance(manifest, dict), "插件清单必须是表（TOML 对象）")
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

    # 军令 #20：数据引擎这类「只提供能力、没有界面」的插件可声明 headless。
    # 它不出现在左栏、不挂舞台、没有 iframe，能力全部经 Host API 暴露；
    # 反过来，headless 插件不许声明 ui/stage/slots，避免清单与运行时对不上。
    headless = manifest.get("headless") is True
    if headless:
        _require("stage" not in manifest and "ui" not in manifest,
                 "headless 插件不得声明 ui 或 stage")
        _require("entry" not in manifest, "headless 插件不得声明 entry")
    slots = manifest.get("slots")
    _require(
        isinstance(slots, list)
        and all(item in _SLOTS for item in slots)
        and (headless or bool(slots)),
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

    # 硬依赖（PLUGIN_SPEC §1.8）：缺了它插件就只是空壳，所以拒绝安装，
    # 而不是像 bus 那样宽容丢弃。写坏的声明必须让作者当场看见。
    try:
        requires = plugin_suite.normalize_requires(manifest.get("requires"), plugin_id)
    except ValueError as exc:
        raise PluginRejected(str(exc)) from exc

    # 舞台声明与插槽必须自洽：写了 stage 却没要 stage.center，等于声明了没有落点的能力
    if "stage" in manifest:
        _require("stage.center" in slots, "声明 stage 必须同时在 slots 里带上 stage.center")
        stage = _normalize_stage(manifest.get("stage"))
    elif "stage.center" in slots:
        stage = _normalize_stage({})
    else:
        stage = None
    bus_grants = _normalize_bus(manifest.get("bus"))
    plugin_commands, rejected_commands = command_registry.normalize_commands(
        manifest.get("contributes"), plugin_id
    )
    if command_issues is not None:
        command_issues.extend(rejected_commands)

    entry_url = ""
    css_url = None
    if not headless:
        entry = manifest.get("entry")
        _require(isinstance(entry, dict), "entry 缺失")
        frontend = entry.get("frontend")
        _require(isinstance(frontend, str) and bool(frontend), "entry.frontend 缺失")
        relative = PurePosixPath(frontend)
        _require(
            not relative.is_absolute() and ".." not in relative.parts,
            "entry.frontend 必须是包内相对路径",
        )
        _require(len(relative.parts) > 1 and relative.parts[0] in _ASSET_ROOTS,
                 "entry.frontend 必须位于 dist/ 或 webui/")
        frontend_path = plugin_dir.joinpath(*relative.parts)
        _require(frontend_path.is_file(), "entry.frontend 指向的文件不存在")
        entry_url = f"/plugin-assets/{plugin_id}/{relative.as_posix()}"

        css_relative = relative.parent / "plugin.css"
        css_path = plugin_dir.joinpath(*css_relative.parts)
        if css_path.is_file():
            css_url = f"/plugin-assets/{plugin_id}/{css_relative.as_posix()}"

    ui = None if headless else _normalize_ui(manifest.get("ui"), plugin_id, name)
    if ui is None and not headless:
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
        # 硬依赖：发现阶段按这张表算闭包，缺依赖的插件一律不启用（§1.8）。
        "requires": requires,
        "headless": headless,
        "entry_url": entry_url,
        "css_url": css_url,
        "ui": ui,
        "stage": stage,
        "bus": bus_grants,
        # 能力路由字典（PLUGIN_SPEC §2.14）：只登记清单里声明的命令，
        # 越权命名空间与坏条目在 normalize_commands 里逐条丢弃并记账。
        "commands": plugin_commands,
        # 只用于「检查更新」时判断底座是否够新；缺省不设限，底座绝不据此拒绝加载已装插件。
        "min_host_version": (
            manifest["min_host_version"]
            if isinstance(manifest.get("min_host_version"), str)
            and _SEMVER.fullmatch(manifest["min_host_version"])
            else ""
        ),
        # 渲染/工具类插件可显式声明 show_in_sidebar:false，不在左栏占位；缺省一律显示。
        "show_in_sidebar": manifest.get("show_in_sidebar") is not False,
        # 军令 #20：题库引擎的免死金牌。false 表示后端拒绝卸载（连代码目录也不删），
        # 前端据实把卸载按钮换成「受保护」标签。
        "uninstallable": manifest.get("uninstallable") is not False,
    }


def _sidebar_with_unlisted(tree: list[dict[str, Any]], plugin_ids: list[str]) -> list[dict[str, Any]]:
    """左栏树 = 用户排的序 + 树上还没有的新插件（按发现顺序追加）。

    这样「设置面板的已启用顺序」和「左栏顺序」读的是同一棵树，天然对齐；
    新装插件不会因为没人排过就消失。
    """
    listed = {item["id"] for item in tree if item.get("kind") == "plugin"}
    for folder in tree:
        if folder.get("kind") == "folder":
            listed.update(folder.get("children") or [])
    built = [dict(item) for item in tree]
    for plugin_id in plugin_ids:
        key = "plugin:" + plugin_id
        if key not in listed:
            built.append({"kind": "plugin", "id": key})
    return built


def _retired_plugin_ids(root: Path) -> set[str]:
    """历史插件目录不再参与发现：旧 core-bank 与已并入引擎的旧视图插件。

    旧视图插件已物理并入 bank-engine，老工作区残留目录也不再作为第二个插件
    出现在控制台（否则老师会被要求分别更新两个包）；目录原样保留以便回退。
    """
    from app.core.bank_provider import DEFAULT_PROVIDER_ID, LEGACY_PROVIDER_IDS

    retired = {"org.jiuzhang.bank-ui"}
    if manifests.manifest_path(root / DEFAULT_PROVIDER_ID) is None:
        return retired
    return retired | set(LEGACY_PROVIDER_IDS)


def discover_plugins() -> dict[str, Any]:
    plugins: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    # 声明了却被丢弃的命令：不拦插件装不装得上，但必须让作者看得见
    # （自查口径：装完后 command.list 里有没有你那条）。
    command_issues: list[dict[str, str]] = []
    root = plugins_dir()
    fingerprint: list[str] = []
    # 一次性读满整份主机状态：停用过谁、谁被改过名、左栏怎么分组、快捷键怎么绑。
    prefs = plugin_state.state()
    disabled = prefs["disabled"]

    retired = _retired_plugin_ids(root)
    if root.is_dir():
        for plugin_dir in sorted(root.iterdir(), key=lambda item: item.name):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue
            if plugin_dir.name in retired:
                continue
            manifest_path = manifests.manifest_path(plugin_dir)
            if manifest_path is None:
                continue
            try:
                stat = manifest_path.stat()
                fingerprint.append(
                    f"{plugin_dir.name}:{stat.st_mtime_ns}:{stat.st_size}"
                )
            except OSError:
                fingerprint.append(f"{plugin_dir.name}:unreadable")
            try:
                manifest = manifests.load_manifest(plugin_dir)
                info = validate_plugin(plugin_dir, manifest, command_issues)
                info["enabled"] = info["id"] not in disabled
                # 视图层偏好就地附着：昵称空串表示「没起过名，用官方原名」，
                # disabled_at 空串表示「历史停用、本机没记下时间」。
                info["nickname"] = prefs["nicknames"].get(info["id"], "")
                info["disabled_at"] = prefs["disabled_at"].get(info["id"], "")
                plugins.append(info)
            except (PluginRejected, OSError, ValueError) as exc:
                rejected.append({"id": plugin_dir.name, "reason": str(exc)})

    # 依赖闭包（PLUGIN_SPEC §1.8）：装了但缺依赖的插件一律不启用。
    # 用 enabled=False 表达，前端所有既有判据（左栏、舞台、右栏认领）自动生效，
    # 不用逐个改；dependency_error 负责说清为什么，绝不留一个空壳界面。
    blocked = plugin_suite.dependency_report(plugins, set(disabled))
    for info in plugins:
        problem = blocked.get(info["id"])
        info["dependency_blocked"] = problem is not None
        info["missing_requires"] = (
            sorted(set(problem["missing"]) | set(problem["disabled"]) | set(problem["blocked"]))
            if problem else []
        )
        info["dependency_error"] = (
            plugin_suite.dependency_message(info["id"], problem) if problem else ""
        )
        if problem:
            info["enabled"] = False

    installed = [info["id"] for info in plugins]
    sidebar = plugin_state.prune_sidebar(prefs["sidebar"], set(installed))
    tree = _sidebar_with_unlisted(sidebar, installed)
    parents = plugin_state.folder_of(tree)
    for info in plugins:
        info["folder_id"] = parents.get("plugin:" + info["id"], "")

    # 启停状态也进签名：停用一个插件后左栏要能立刻知道清单变了。
    fingerprint.append("disabled:" + ",".join(sorted(disabled)))
    # 改昵称、挪分组都算清单变化——左栏与设置面板必须当场重排，
    # 而不是等下一次重启或手动刷新。
    fingerprint.append("nick:" + toml_io.dumps({"values": prefs["nicknames"]}))
    fingerprint.append("side:" + toml_io.dumps({"tree": tree}))
    # 热插拔的判据：清单文件的 mtime/size 任何一项变化都会改签名。
    # 前端只拿签名比对，不必自己猜“有没有新插件”；同版本号覆盖安装也能被发现。
    signature = hashlib.sha256("\n".join(fingerprint).encode("utf-8")).hexdigest()[:16]
    registry = command_registry.build_registry(plugins)
    return {
        "protocol": PROTOCOL,
        "plugins": plugins,
        "rejected": rejected,
        "sidebar": tree,
        # 能力路由字典：启用的插件声明了什么，这里就有什么（同 id 先到先得）。
        # 插件之间不直连，command.execute 查的就是这张表。
        "commands": registry["commands"],
        "commands_rejected": command_issues + registry["issues"],
        # 因依赖缺失/被停用而保持停用的插件：左栏与设置页据此给出人话提示。
        "dependency_blocked": [
            {
                "id": info["id"],
                "name": info["name"],
                "missing_requires": info["missing_requires"],
                "reason": info["dependency_error"],
            }
            for info in plugins if info["dependency_blocked"]
        ],
        # 后端树为空 = 用户从没在设置面板拖过组。前端据此决定要不要一次性搬走
        # 早期存在浏览器里的左栏顺序（搬完即弃，不做双向同步）。
        "sidebar_customized": bool(sidebar),
        "signature": signature,
    }


def resolve_plugin_asset(plugin_id: str, asset_path: str) -> Path:
    if not plugin_id or _PLUGIN_ID.fullmatch(plugin_id) is None:
        raise PluginAssetError("插件 ID 非法")

    package_root = (plugins_dir() / plugin_id).resolve()
    if not any((package_root / root).is_dir() for root in _ASSET_ROOTS):
        raise PluginAssetError("插件不存在")

    relative = PurePosixPath(asset_path.replace("\\", "/"))
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise PluginAssetError("插件资源路径非法")
    if relative.parts[0] not in _ASSET_ROOTS:
        raise PluginAssetError("只允许访问插件的 dist/ 或 webui/ 资源")

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
