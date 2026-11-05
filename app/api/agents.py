"""Agent 接口：AI 副驾改写与确定性 LaTeX 清洗。

常驻对话/拆题/审题智能体已于 2026-11-05 随 AI 助手一并下架。
改写遵循 docs/API_REFERENCE.md §6「Agent Prompt 契约」，调用 app.core.ai_client
完成大模型交互；无 API Key 时自动降级 Mock，保证前端不挂。``/clean_latex`` 不经过模型。
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from app.core import ai_client, question_parser

router = APIRouter(prefix="/api/agent", tags=["agents"])


# --- Request models (Pydantic contracts) ---
class RefineRequest(BaseModel):
    question: dict[str, Any] = Field(..., description="当前正在编辑的题目（标准结构或其表单态子集）")
    instruction: str = Field(..., description="老师对 AI 副驾的一句话指令，如「把题干改得更简洁」")
    field: str = Field("stem", description="要改写并回填的字段：stem / solution")
    task_id: str = Field("", description="任务唯一标识")


class CleanLatexRequest(BaseModel):
    text: str = Field(..., max_length=20000, description="待清洗的脏文本（题干/解析/选项任一）")
    task_id: str = Field("", description="任务唯一标识")
    mode: str = Field(
        "contract",
        max_length=20,
        description="清洗口径：contract=契约正文（默认，与 #21 逐字一致）；"
                    "exam_source=录题画布的 exam-zh 源码（只归一写法，不碰环境骨架）",
    )


REFINE_SYSTEM_PROMPT = """你是九章算子录题端的 AI 数学副驾。老师正在编辑一道题，你会看到题目当前内容与一句改写指令。

任务：只改写老师指定的那一个字段（默认题干 stem），其它字段一律不动，也不要改动题目编号或身份。

铁律：
1. 数学事实不得改错：等式、不等式、定义域、选项与答案所依据的关系必须保持正确；改写题干只能换措辞、调繁简、补条件表述，不能把对的改错、把题改成另一道无解题。
2. 文本一律 Markdown + LaTeX：行内公式 $...$，独立公式 $$...$$；保留老师原有的公式，不新增未经要求的公式。
3. 不得编造题目里没有的数值、答案或解析。
4. 输出「裸 JSON」：不要 markdown 代码围栏、不要 JSON 之外的任何解释。

输出格式（严格 JSON）：
{"field": "<stem 或 solution>", "<该字段名>": "<改写后的完整文本>", "note": "<一句话说明你改了什么>"}
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


def build_refine_user_message(
    question: dict[str, Any], instruction: str, field: str, original: str
) -> str:
    """把「当前题 + 待改字段 + 老师指令」拼成给副驾的 user 消息。

    只带上题目正文的可见字段做上下文，避免把 extensions/令牌一类的东西喂给模型。
    """
    snapshot = {
        key: question.get(key)
        for key in ("type", "difficulty", "stem", "options", "answer", "solution")
        if question.get(key) not in (None, "", [], {})
    }
    return (
        "## 当前题目（只读上下文）\n"
        + json.dumps(snapshot, ensure_ascii=False)
        + f"\n\n## 需要改写的字段\n{field}\n\n## 该字段当前内容\n{original}\n\n"
        + "## 老师指令\n" + instruction.strip()
    )


def parse_refine_reply(raw: str, field: str) -> dict[str, str]:
    """解析副驾返回的裸 JSON，取回改写后的字段文本与一句话说明。

    模型偶尔会把字段名写错或套上围栏；这里剥围栏、认 field/value/text 三种键，
    取不到非空文本就抛错，交给路由走回显兜底——绝不把空串回填进老师表单。
    """
    text = strip_code_fences(raw or "")
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError("AI 副驾返回的不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("AI 副驾返回的不是 JSON 对象")
    value = data.get(field) or data.get("value") or data.get("text") or ""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("AI 副驾没有给出可用的改写内容")
    note = data.get("note")
    return {"value": value.strip(), "note": note.strip() if isinstance(note, str) else ""}


@router.post("/clean_latex", summary="脏 LaTeX 规则清洗（不调模型）")
async def agent_clean_latex(body: CleanLatexRequest = Body(...)) -> dict[str, Any]:
    """把老师粘来的脏文本收敛成契约口径，供录题端一键回填。

    与 ``/refine`` 不同，这里不碰模型也不碰题库：同一段输入永远得到同一段输出，
    清洗规则只有 ``app/core/question_parser`` 一处实现。

    ``mode`` 选口径（军令 #32 · 1.6）：``contract`` 是默认、与 #21 逐字一致；
    ``exam_source`` 给录题画布的 exam-zh 源码用——同一个写法字典，但不拆环境骨架。
    插件侧由此不必再自带第二份规则表。
    """
    data = (question_parser.clean_exam_source(body.text)
            if body.mode == "exam_source"
            else question_parser.clean_dirty_latex(body.text))
    return {
        "type": "complete",
        "data": data,
        "task_id": body.task_id or "unknown",
        "mock": False,
    }


@router.post("/refine", summary="AI 副驾改写单字段（题干/解析）供回填")
async def agent_refine(body: RefineRequest = Body(...)) -> dict[str, Any]:
    """按老师指令改写当前题的一个字段，返回改写文本供前端「回填到表单」。

    这里不落库、不覆盖原题：副驾只产出候选文本，老师点「回填」才进表单，
    点「保存」才经录题插件走宿主写库——改题的主动权始终在老师手里。
    """
    field = body.field if body.field in ("stem", "solution") else "stem"
    original = str((body.question or {}).get(field) or "")
    task_id = body.task_id
    user_message = build_refine_user_message(body.question or {}, body.instruction, field, original)
    try:
        result = await ai_client.chat_completion(
            system_prompt=REFINE_SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.3,
            max_tokens=800,
        )
        if result.get("mock"):
            return {
                "type": "complete",
                "data": {
                    "field": field,
                    "value": original,
                    "note": "未配置模型：AI 副驾需在「设置」里配好 Provider 才能真正改写，本次仅原样回显。",
                    "model": result["model"],
                    "usage": result["usage"],
                },
                "task_id": task_id or "unknown",
                "mock": True,
            }
        reply = parse_refine_reply(result["content"], field)
        return {
            "type": "complete",
            "data": {
                "field": field,
                "value": reply["value"],
                "note": reply["note"],
                "model": result["model"],
                "usage": result["usage"],
            },
            "task_id": task_id or "unknown",
            "mock": False,
        }
    except Exception as exc:
        return {
            "type": "error",
            "error": {"code": "MODEL_ERROR", "message": str(exc), "retryable": True},
            "task_id": task_id or "unknown",
            "fallback": {"field": field, "value": original, "note": "改写失败，已原样回显。", "mock": True},
            "route": "mock",
        }

