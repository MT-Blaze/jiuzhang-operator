"""Agent 接口：对话、拆题、审题三类智能体。

遵循 PROMPT_SPEC.md 契约，调用 app.core.ai_client 完成大模型交互。
无 API Key 时自动降级 Mock，保证前端不挂。
"""

from __future__ import annotations

import json
import re
import secrets
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from app.core import ai_client, plugin_search, plugin_tools, ui_cards

router = APIRouter(prefix="/api/agent", tags=["agents"])


# --- Request models (Pydantic contracts) ---
class ChatRequest(BaseModel):
    user_input: str = Field(..., description="用户指令")
    task_id: str = Field("", description="任务唯一标识")
    context: dict[str, Any] | None = Field(
        None, description="工作台右栏结构化上下文（当前任务/教材/模型等），注入 System 尾部"
    )
    history: list[dict[str, str]] | None = Field(
        None, description="此前对话轮次 [{role, content}]，折叠进本轮 user 消息"
    )


class SplitRequest(BaseModel):
    ocr_markdown: str = Field(..., description="OCR 后的整卷 Markdown")
    task_id: str = Field("", description="任务唯一标识")


class ReviewRequest(BaseModel):
    question_json: dict[str, Any] = Field(..., description="单题完整 JSON 结构")
    task_id: str = Field("", description="任务唯一标识")


# --- Prompt templates (fixed prefixes for cache friendliness) ---
CHAT_SYSTEM_PROMPT = """你是九章算子工作台的对话助手。你的任务是理解教师指令并返回可执行的操作计划。

插件优先（最高优先级）：
1. 当用户的意图匹配「已安装插件工具」时，必须直接发起 tool_calls 调用该工具，不要反问、不要只复述计划、也不要声称「即将执行」。
2. 用户说「拆分第 X 题」「看看第 X 题」「导入题目」「题库里有什么」时，优先调用带 import_questions 动作的插件工具。
3. 工具执行结果由底座交给用户，你不得编造工具没有返回的题目、答案或解析。
4. 只有没有任何插件工具能覆盖意图时，才使用下面的 action JSON 协议。

通用约束：
1. 未调用工具且不需要展示卡片时，输出必须是 JSON 对象，包含 action 字段。
2. 若指令模糊，返回 clarification 而非猜测。
3. 不得生成题目内容本身，只返回操作元数据；需要展示具体题目时，用下面的 ui_json 卡片协议。
4. 输出必须是「裸 JSON」：禁止 markdown 代码围栏包裹 action JSON、禁止 JSON 之外的额外解释（ui_json 卡片块除外）。
5. 必须结合「当前工作台上下文」与「此前对话记录」理解本轮指令：上下文里已给出的信息（如当前任务舞台）不得再反问；本轮指令若是延续前文（如「改成第 3-4 页」「再来一次」），必须结合历史推断完整意图，而不是孤立理解。
6. 只有当结合上下文与历史后仍无法确定意图时，才返回 clarify，且 clarify 的 question 必须是一句面向教师的自然语言问句，不得包含 JSON 或代码围栏。
7. 右侧面板可代人操作：用户要求调整年级/难度等参数时，返回 update_params；用户要求执行面板按钮时，返回 trigger_button。只能使用「右侧插件面板」小节里列出的 key 与 button id，不得编造。人类手动改动过的参数优先，不要覆盖。

可用 action：
- "split_paper": { page_range: [3, 5] }
- "tag_question": { question_id: "...", tags: ["集合", "基础"] }
- "export_paper": { format: "pdf" | "tex" | "docx" }
- "clarify": { question: "<澄清问题>" }
- "update_params": { params: { "grade": "高一", "difficulty": "基础" }, message: "<给用户的一句话>" }
- "trigger_button": { button: "<面板按钮 id>", message: "<给用户的一句话>" }

富卡片（ui_json）：
- 需要向教师展示一道具体题目时，可在回复末尾追加**恰好一个** ```ui_json 围栏，内容为：
  {"version":"1.0","type":"question_card","questions":[{"type":"single_choice","type_label":"单选","difficulty":"L1","difficulty_label":"基础","stem":"题干 Markdown+LaTeX","options":[{"key":"A","content":"..."}],"answer":"...","solution":"...","tags":[]}]}
- 题目必须真实来自工具结果或上下文，不得编造；没有真实题目就不要输出卡片。
- 安装建议卡由底座在插件搜索工具执行后生成，你不要手写 install_card，也不得声称已安装任何插件。
"""

SPLIT_SYSTEM_PROMPT = """你是九章算子的拆题专家。给定一份试卷的完整 Markdown 文本，将其按题号切分为独立题目。

约束：
1. 每道题输出一个 JSON 对象，包含 id, type, stem, options(如有), difficulty。
2. 题型枚举：single_choice, multiple_choice, fill_blank, solution, proof。
3. 难度枚举：L1, L2, L3, L4（L1=基础，L2=中档，L3=难，L4=压轴）。
4. 保留 LaTeX 公式原样，不得转义或简化。
5. 若某题信息不全，标记 status: "incomplete" 并说明缺失字段。

输出格式：JSON 数组，每项为一道题。
"""

REVIEW_SYSTEM_PROMPT = """你是九章算子的审题质检员。给定一道题目的完整结构（题干、选项、答案、解析），执行以下检查：

1. 答案一致性：选择题答案字母是否在选项中存在；填空题答案是否与题干匹配。
2. 解析完整性：是否有【解析】块；解析是否覆盖关键步骤。
3. 配图合理性：题干提及图形但无图片时标记 missing_image。
4. 难度合理性：根据解题步骤复杂度判断难度标签是否恰当。

输出格式：JSON 对象，包含 checks 数组与 overall_score (1-5)。
"""


# --- 提示词/回执装配助手（纯函数，便于单测） ---
_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*[ \t]*\r?\n(?P<body>.*?)[ \t]*\r?```[ \t]*$", re.S)


def strip_code_fences(text: str) -> str:
    """剥掉模型爱套的 markdown 代码围栏，只留围栏内正文。

    背景（10.24 军令 P0-1）：模型把 ```json {...} ``` 原样吐回，前端解析失败
    就把整段围栏印进了聊天气泡。后端先剥一层，前端再兜一层，双保险。
    """
    if not text:
        return text
    # ui_json 是富卡片载荷，不是「动作 JSON 裸奔」；保留围栏交给前端拦截渲染。
    if text.strip().startswith("```ui_json"):
        return text
    match = _FENCE_RE.match(text.strip())
    if match:
        return match.group("body").strip()
    return text


def _ui_panel_prompt(context: dict[str, Any]) -> str:
    """把前端右侧面板的控件快照翻译成模型可操控的紧凑清单。"""
    ui = context.get("ui")
    if not isinstance(ui, dict):
        return ""
    controls = ui.get("controls")
    if not isinstance(controls, list) or not controls:
        return ""
    values = ui.get("values") if isinstance(ui.get("values"), dict) else {}
    lines = ["\n\n## 右侧插件面板（可由 update_params / trigger_button 操控）"]
    plugin_id = ui.get("plugin_id")
    if isinstance(plugin_id, str) and plugin_id.strip():
        lines.append("插件：" + plugin_id.strip()[:80])
    lines.append("可设置参数：")
    has_select = False
    for control in controls[:8]:
        if not isinstance(control, dict) or control.get("type") != "select":
            continue
        key = control.get("key")
        label = control.get("label")
        if not isinstance(key, str) or not isinstance(label, str):
            continue
        options = []
        for option in (control.get("options") or [])[:12]:
            if isinstance(option, dict) and isinstance(option.get("value"), str):
                options.append(option["value"])
        current = values.get(key)
        lines.append(
            "- %s（%s）：可选 %s；当前 %s"
            % (
                key[:16],
                label[:24],
                " / ".join(item[:16] for item in options),
                str(current)[:24] if current is not None else "未设置",
            )
        )
        has_select = True
    if not has_select:
        lines.append("- 无")
    lines.append("可触发按钮：")
    has_button = False
    for control in controls[:8]:
        if not isinstance(control, dict) or control.get("type") != "button":
            continue
        lines.append(
            "- %s（%s）"
            % (str(control.get("id") or "")[:32], str(control.get("label") or "")[:24])
        )
        has_button = True
    if not has_button:
        lines.append("- 无")
    lines.append(
        "规则：update_params 的 params 只能使用上面列出的参数 key，值必须是列出的选项；"
        "trigger_button 的 button 只能使用上面列出的按钮 id。不得虚构控件。"
    )
    return "\n".join(lines)


def build_chat_system_prompt(
    context: dict[str, Any] | None,
    tools: list[dict[str, Any]] | None = None,
) -> str:
    """System 提示词 = 固定前缀（缓存友好）+ 插件工具目录 + 右栏上下文。

    工具目录放在上下文之前、固定前缀之后：插件数量变化时只影响尾部，
    仍然尽量保住前缀缓存；模型据此知道「现在有哪几件工具真能干活」。
    """
    prompt = CHAT_SYSTEM_PROMPT
    if tools:
        lines = ["\n\n## 已安装插件工具（意图匹配时必须直接发起 tool_calls）"]
        for tool in tools:
            function = tool.get("function") if isinstance(tool, dict) else None
            if not isinstance(function, dict):
                continue
            description = str(function.get("description") or "").strip()
            lines.append(f"- {function.get('name')}：{description[:300]}")
        prompt += "\n".join(lines)
    if context:
        plugin = context.get("plugin")
        if isinstance(plugin, dict):
            plugin_name = plugin.get("name")
            if isinstance(plugin_name, str) and plugin_name.strip():
                prompt += (
                    "\n\n## 当前插件工作模式\n"
                    f"现在处于「{plugin_name.strip()[:64]}」插件的工作模式下。"
                    "回答、计划与工具调用都必须围绕该插件的能力展开；"
                    "优先调用与该插件对应的已安装工具，不得声称拥有该插件未声明的能力。"
                )
        panel = _ui_panel_prompt(context)
        if panel:
            prompt += panel
        prompt += "\n\n## 当前工作台上下文（只读，供你结合决策）\n" + json.dumps(
            context, ensure_ascii=False
        )
    return prompt


def build_user_message_with_history(
    history: list[dict[str, str]] | None, user_input: str
) -> str:
    """把此前对话轮次折叠进本轮 user 消息，给模型连续上下文。"""
    if not history:
        return user_input
    lines: list[str] = []
    for turn in history:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        content = turn.get("content") or ""
        if role not in ("user", "assistant") or not str(content).strip():
            continue
        lines.append(("用户：" if role == "user" else "助手：") + str(content).strip())
    if not lines:
        return user_input
    return "## 此前对话记录\n" + "\n".join(lines) + "\n\n## 本轮指令\n" + user_input


def _make_host_call(intent: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "host_" + secrets.token_hex(6),
        "type": "function",
        "function": {
            "name": intent["tool"],
            "arguments": json.dumps(intent["arguments"], ensure_ascii=False),
        },
    }


def _run_tool(name: str, arguments: Any) -> dict[str, Any]:
    if name in plugin_search.TOOL_NAMES:
        return plugin_search.execute_tool(name, arguments)
    return plugin_tools.execute_tool(name, arguments)


def _execute_calls(
    tool_calls: list[dict[str, Any]], routed_by: str
) -> list[dict[str, Any]]:
    """执行模型（或宿主兜底）给出的工具调用，裁掉结果里的原始数据。"""
    public_calls: list[dict[str, Any]] = []
    for call in tool_calls[: plugin_tools.MAX_TOOL_CALLS]:
        function = call.get("function") if isinstance(call, dict) else None
        if not isinstance(function, dict):
            continue
        name = str(function.get("name") or "")
        outcome = _run_tool(name, function.get("arguments") or "{}")
        cards = [item for item in (outcome.get("ui_cards") or []) if isinstance(item, dict)]
        data = outcome.get("data") if isinstance(outcome.get("data"), dict) else {}
        question_block = ui_cards.question_block(data.get("questions") or [])
        if question_block:
            cards.insert(0, question_block)
        public_calls.append(
            {
                "tool": name,
                "plugin": outcome.get("plugin") or {},
                "action": outcome.get("action") or "",
                "ok": bool(outcome.get("ok")),
                "error": outcome.get("error") or "",
                "summary": outcome.get("summary") or "插件没有返回结果。",
                "routed_by": routed_by,
                "host_tool": bool(outcome.get("host_tool")),
                "cards": cards,
            }
        )
    return public_calls


def _plugin_bubble(plugin_calls: list[dict[str, Any]]) -> str:
    text = "\n\n".join(call["summary"] for call in plugin_calls if call["summary"])
    blocks: list[dict[str, Any]] = []
    for call in plugin_calls:
        for card in call.get("cards") or []:
            if isinstance(card, dict):
                blocks.append(card)
    frames = ui_cards.frames_for_blocks(blocks)
    if frames:
        text = (text + "\n\n" + frames).strip() if text else frames
    return text


@router.post("/chat", summary="对话 Agent")
async def agent_chat(body: ChatRequest = Body(...)) -> dict[str, Any]:
    """处理自然语言指令：插件工具优先，其次回落到 action JSON 协议。"""
    user_input = body.user_input
    task_id = body.task_id
    installed_tools = plugin_tools.build_tools()
    tools = installed_tools + plugin_search.build_tools()
    system_prompt = build_chat_system_prompt(body.context, tools)
    user_message = build_user_message_with_history(body.history, user_input)
    try:
        result = await ai_client.chat_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.4,
            max_tokens=512,
            tools=tools or None,
            tool_choice="auto" if tools else None,
        )

        tool_calls = result.get("tool_calls") or []
        routed_by = "model"
        if not tool_calls:
            # 模型没发 tool_calls（漏判 / Provider 不支持）时，按高置信句式兜底，
            # 保证「拆分第一题」这类明确指令不会退化成一句反问。
            intent = plugin_tools.match_intent(user_input, installed_tools)
            if not intent:
                intent = plugin_search.match_intent(user_input)
            if intent:
                tool_calls = [_make_host_call(intent)]
                routed_by = "host"

        if tool_calls:
            plugin_calls = _execute_calls(tool_calls, routed_by)
            if plugin_calls:
                return {
                    "type": "complete",
                    "data": {
                        "content": _plugin_bubble(plugin_calls),
                        "plugin_calls": plugin_calls,
                        "usage": result["usage"],
                        "model": result["model"],
                    },
                    "task_id": task_id or "unknown",
                    "mock": result["mock"],
                    "route": routed_by,
                }

        return {
            "type": "complete",
            "data": {
                "content": strip_code_fences(result["content"]),
                "plugin_calls": [],
                "usage": result["usage"],
                "model": result["model"],
            },
            "task_id": task_id or "unknown",
            "mock": result["mock"],
            "route": "model",
        }
    except Exception as exc:
        intent = plugin_tools.match_intent(user_input, installed_tools) or plugin_search.match_intent(user_input)
        if intent:
            plugin_calls = _execute_calls([_make_host_call(intent)], "host")
            if plugin_calls:
                return {
                    "type": "complete",
                    "data": {
                        "content": _plugin_bubble(plugin_calls),
                        "plugin_calls": plugin_calls,
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                        "model": "host-router",
                    },
                    "task_id": task_id or "unknown",
                    "mock": False,
                    "route": "host",
                    "model_error": str(exc),
                }
        fallback = ai_client._mock_chat(system_prompt, user_message)
        return {
            "type": "error",
            "error": {"code": "MODEL_ERROR", "message": str(exc), "retryable": True},
            "task_id": task_id or "unknown",
            "fallback": {"content": strip_code_fences(fallback["content"]), "mock": True},
            "route": "mock",
        }


@router.post("/split", summary="拆题 Agent")
async def agent_split(body: SplitRequest = Body(...)) -> dict[str, Any]:
    """将整卷 OCR 文本切分为独立题目卡片。"""
    ocr_markdown = body.ocr_markdown
    task_id = body.task_id
    try:
        result = await ai_client.chat_completion(
            system_prompt=SPLIT_SYSTEM_PROMPT,
            user_message=ocr_markdown,
            temperature=0.3,
            max_tokens=2048,
        )
        return {
            "type": "complete",
            "data": {
                "content": strip_code_fences(result["content"]),
                "usage": result["usage"],
                "model": result["model"],
            },
            "task_id": task_id or "unknown",
            "mock": result["mock"],
        }
    except Exception as exc:
        fallback = ai_client._mock_chat(SPLIT_SYSTEM_PROMPT, ocr_markdown[:200])
        return {
            "type": "error",
            "error": {"code": "MODEL_ERROR", "message": str(exc), "retryable": True},
            "task_id": task_id or "unknown",
            "fallback": {"content": strip_code_fences(fallback["content"]), "mock": True},
        }


@router.post("/review", summary="审题 Agent")
async def agent_review(body: ReviewRequest = Body(...)) -> dict[str, Any]:
    """对单道题目进行质量审查。"""
    question_json = body.question_json
    task_id = body.task_id
    try:
        user_msg = f"请审查以下题目：\n\n{question_json}"
        result = await ai_client.chat_completion(
            system_prompt=REVIEW_SYSTEM_PROMPT,
            user_message=user_msg,
            temperature=0.5,
            max_tokens=512,
        )
        return {
            "type": "complete",
            "data": {
                "content": strip_code_fences(result["content"]),
                "usage": result["usage"],
                "model": result["model"],
            },
            "task_id": task_id or "unknown",
            "mock": result["mock"],
        }
    except Exception as exc:
        fallback = ai_client._mock_chat(REVIEW_SYSTEM_PROMPT, str(question_json)[:200])
        return {
            "type": "error",
            "error": {"code": "MODEL_ERROR", "message": str(exc), "retryable": True},
            "task_id": task_id or "unknown",
            "fallback": {"content": strip_code_fences(fallback["content"]), "mock": True},
        }
