"""Agent 接口：对话、拆题、审题三类智能体。

遵循 PROMPT_SPEC.md 契约，调用 app.core.ai_client 完成大模型交互。
无 API Key 时自动降级 Mock，保证前端不挂。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from app.core import ai_client

router = APIRouter(prefix="/api/agent", tags=["agents"])


# --- Request models (Pydantic contracts) ---
class ChatRequest(BaseModel):
    user_input: str = Field(..., description="用户指令")
    task_id: str = Field("", description="任务唯一标识")


class SplitRequest(BaseModel):
    ocr_markdown: str = Field(..., description="OCR 后的整卷 Markdown")
    task_id: str = Field("", description="任务唯一标识")


class ReviewRequest(BaseModel):
    question_json: dict[str, Any] = Field(..., description="单题完整 JSON 结构")
    task_id: str = Field("", description="任务唯一标识")


# --- Prompt templates (fixed prefixes for cache friendliness) ---
CHAT_SYSTEM_PROMPT = """你是九章算子工作台的对话助手。你的任务是理解教师指令并返回可执行的操作计划。

约束：
1. 输出必须是 JSON 对象，包含 action 字段。
2. 若指令模糊，返回 clarification 而非猜测。
3. 不得生成题目内容本身，只返回操作元数据。

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


@router.post("/chat", summary="对话 Agent")
async def agent_chat(body: ChatRequest = Body(...)) -> dict[str, Any]:
    """处理自然语言指令，返回结构化操作建议。"""
    user_input = body.user_input
    task_id = body.task_id
    try:
        result = await ai_client.chat_completion(
            system_prompt=CHAT_SYSTEM_PROMPT,
            user_message=user_input,
            temperature=0.7,
            max_tokens=256,
        )
        return {
            "type": "complete",
            "data": {"content": result["content"], "usage": result["usage"]},
            "task_id": task_id or "unknown",
            "mock": result["mock"],
        }
    except Exception as exc:
        fallback = ai_client._mock_chat(CHAT_SYSTEM_PROMPT, user_input)
        return {
            "type": "error",
            "error": {"code": "MODEL_ERROR", "message": str(exc), "retryable": True},
            "task_id": task_id or "unknown",
            "fallback": {"content": fallback["content"], "mock": True},
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
            "data": {"content": result["content"], "usage": result["usage"]},
            "task_id": task_id or "unknown",
            "mock": result["mock"],
        }
    except Exception as exc:
        fallback = ai_client._mock_chat(SPLIT_SYSTEM_PROMPT, ocr_markdown[:200])
        return {
            "type": "error",
            "error": {"code": "MODEL_ERROR", "message": str(exc), "retryable": True},
            "task_id": task_id or "unknown",
            "fallback": {"content": fallback["content"], "mock": True},
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
            "data": {"content": result["content"], "usage": result["usage"]},
            "task_id": task_id or "unknown",
            "mock": result["mock"],
        }
    except Exception as exc:
        fallback = ai_client._mock_chat(REVIEW_SYSTEM_PROMPT, str(question_json)[:200])
        return {
            "type": "error",
            "error": {"code": "MODEL_ERROR", "message": str(exc), "retryable": True},
            "task_id": task_id or "unknown",
            "fallback": {"content": fallback["content"], "mock": True},
        }
