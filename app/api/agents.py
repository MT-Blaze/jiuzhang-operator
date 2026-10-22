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

from app.core import ai_client, plugin_tools

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
1. 输出必须是 JSON 对象，包含 action 字段（仅在没有调用工具时）。
2. 若指令模糊，返回 clarification 而非猜测。
3. 不得生成题目内容本身，只返回操作元数据。
4. 输出必须是「裸 JSON」：禁止 markdown 代码围栏（```json ... ```）、禁止 JSON 之外的任何解释文字或前后缀。
5. 必须结合「当前工作台上下文」与「此前对话记录」理解本轮指令：上下文里已给出的信息（如当前任务舞台）不得再反问；本轮指令若是延续前文（如「改成第 3-4 页」「再来一次」），必须结合历史推断完整意图，而不是孤立理解。
6. 只有当结合上下文与历史后仍无法确定意图时，才返回 clarify，且 clarify 的 question 必须是一句面向教师的自然语言问句，不得包含 JSON 或代码围栏。

可用 action：
- "split_paper": { page_range: [3, 5] }
- "tag_question": { question_id: "...", tags: ["集合", "基础"] }
- "export_paper": { format: "pdf" | "tex" | "docx" }
- "clarify": { question: "<澄清问题>" }
"""

SPLIT_SYSTEM_PROMPT = """你是九章算子的拆题专家。给定一份试卷的完整 Markdown 文本，将其按题号切分为独立题目。

约束：
1. 每道题输出一个 JSON 对象，包含 id, type, stem, options(如有), difficulty。
2. 题型枚举：single_choice, multiple_choice, fill_blank, solution, proof。
3. 难度枚举：basic, medium, hard, novel。
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
    match = _FENCE_RE.match(text.strip())
    if match:
        return match.group("body").strip()
    return text


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
        outcome = plugin_tools.execute_tool(name, function.get("arguments") or "{}")
        public_calls.append(
            {
                "tool": name,
                "plugin": outcome.get("plugin") or {},
                "action": outcome.get("action") or "",
                "ok": bool(outcome.get("ok")),
                "error": outcome.get("error") or "",
                "summary": outcome.get("summary") or "插件没有返回结果。",
                "routed_by": routed_by,
            }
        )
    return public_calls


def _plugin_bubble(plugin_calls: list[dict[str, Any]]) -> str:
    return "\n\n".join(call["summary"] for call in plugin_calls if call["summary"])


@router.post("/chat", summary="对话 Agent")
async def agent_chat(body: ChatRequest = Body(...)) -> dict[str, Any]:
    """处理自然语言指令：插件工具优先，其次回落到 action JSON 协议。"""
    user_input = body.user_input
    task_id = body.task_id
    tools = plugin_tools.build_tools()
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
            intent = plugin_tools.match_intent(user_input, tools)
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
        intent = plugin_tools.match_intent(user_input, tools)
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
