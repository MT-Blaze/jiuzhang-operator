"""单题 AI 识别（人机共驾 · 方案 A）。

模型只负责「看题图，吐结构化正文」，环境骨架由 :mod:`app.core.exam_source`
统一套壳。任何失败都收敛成 ``{ok: false, detail}``，绝不抛给前端弹窗——
按钮点红点、详细现场进报错诊断即可。

出网前必须已有任务指派（OCR / 解题 / 元数据），且只读本地工作区里的图片；
前端交来的路径一律按白名单前缀解析，绝不认绝对路径与 ``..``。
"""

from __future__ import annotations

import base64
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core import ai_center, latex_style_dict, question_parser
from app.core.ai_client import OpenAICompatibleProvider
from app.core.config import settings
from app.core.exam_source import OPTION_KEYS, build_exam_source

MAX_IMAGES = 3
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_CONTEXT_CHARS = 12000
QUESTION_TYPES = {"single_choice", "multiple_choice", "fill_blank", "solution", "proof"}
DIFFICULTIES = {"L1", "L2", "L3", "L4"}
IMAGE_SUFFIX_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

SYSTEM_PROMPT = r"""你是数学试卷录题助手。看题图，只输出一个 JSON 对象，不要 Markdown 代码块，不要解释。
字段：
- "type": "single_choice" | "multiple_choice" | "fill_blank" | "solution" | "proof"
- "stem": 题干正文（含公式，行内公式用 $...$，不要带题号，不要带选项，不要写 \begin/\end 环境）
- "options": [{"key":"A","content":"..."}]，非选择题给空数组
- "answer": 答案（选择题写字母如 "A" 或 "AB"；填空题写答案；解答题写最终结果）
- "solution": 解析正文（不含「答案：」三个字）
- "question_no": 原卷题号（图上看不清就留空串）
- "difficulty": "L1" | "L2" | "L3" | "L4"（拿不准就 "L2"）
铁律：只转录看得见的内容，看不清就留空串；绝不编造答案、选项或题号。
公式：行内公式只用 $...$，独立公式只用 $$...$$，不要写 \( \) 或 \[ \]。
标点：照抄原卷标点；原卷有顿号/逗号就保留，原卷没有并列标点就直接输出变量，不要自行添加。
"""

SOLVE_SYSTEM_PROMPT = r"""你是数学解题助手。老师已经录好一道题，你只负责补答案与解析，不改题干、不改选项。
只输出一个 JSON 对象，不要 Markdown 代码块，不要解释：
- "answer": 最终答案（选择题写字母如 "A" 或 "AB"；填空题写答案；解答题写最终结果）
- "solution": 完整解析（推导步骤，公式用 $...$；不要写「答案：」三个字）
- "note": 一句话说明你的思路（可留空）
铁律：
1. 数学事实必须正确；题干已给答案时以其为准，只补推导，不另造答案。
2. 不得编造题干里没有的条件、数值或图形；信息不足就在 note 里说明。
3. 解析与答案都不能为空。
"""


def _resolve_image(uri: str) -> tuple[str, str]:
    """同源图片路径 → data URL。返回 ``(data_url, 失败原因)``。"""
    text = str(uri or "").strip()
    if not text:
        return "", "题图路径为空"
    if text.startswith("data:image/"):
        if len(text) > 12 * 1024 * 1024:
            return "", "题图 data URL 过大"
        return text, ""
    parsed = urlparse(text)
    if parsed.scheme or parsed.netloc or parsed.query:
        return "", "只接受本地工作区图片路径"
    roots = (
        ("/static/pending/", settings.pending_assets_dir),
        ("/static/uploads/", settings.uploads_dir),
        ("/static/pool/", settings.pool_assets_dir),
    )
    for prefix, root in roots:
        if not text.startswith(prefix):
            continue
        relative = text[len(prefix):]
        if not relative or "/" in relative or "\\" in relative or relative.startswith("."):
            return "", "图片路径非法"
        target = Path(root) / relative
        if target.is_symlink() or not target.is_file():
            return "", "题图不存在"
        mime = IMAGE_SUFFIX_MIME.get(target.suffix.lower())
        if mime is None:
            return "", "题图格式不支持"
        try:
            raw = target.read_bytes()
        except OSError as exc:
            return "", f"题图读取失败：{exc}"
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            return "", "题图为空或超过 8 MiB"
        return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii"), ""
    return "", "只接受 /static/pending、/static/uploads、/static/pool 下的图片"


def _strip_fences(content: str) -> str:
    text = str(content or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return text


def _raw_text(value: Any, limit: int) -> str:
    return unicodedata.normalize("NFC", str(value or "")).strip()[:limit]


def _clean_text(value: Any, limit: int) -> str:
    """模型给的正文先过写库清洗：``\\(`` / ``\\[`` 归一成 ``$`` / ``$$``，
    再按写法字典补显式脚本与相邻变量的细空格。不合规的公式语法绝不落库。"""
    text = unicodedata.normalize("NFC", str(value or "")).strip()
    text = question_parser.normalize_latex(text)
    text = latex_style_dict.clean_for_write(text)["text"]
    return text[:limit]


def _normalize_type(raw: Any, options: list[dict[str, str]], has_fillin: bool) -> str:
    text = str(raw or "").strip().lower()
    aliases = {
        "choice": "single_choice", "single": "single_choice", "单选": "single_choice",
        "multiple": "multiple_choice", "多选": "multiple_choice",
        "fill": "fill_blank", "blank": "fill_blank", "填空": "fill_blank",
        "proof": "proof", "证明": "proof", "解答": "solution", "solution": "solution",
    }
    kind = aliases.get(text, text)
    if kind not in QUESTION_TYPES:
        kind = ""
    if not kind:
        if options:
            kind = "single_choice"
        elif has_fillin:
            kind = "fill_blank"
        else:
            kind = "solution"
    if kind in ("single_choice", "multiple_choice") and len(options) < 2:
        kind = "solution"
    return kind


def normalize_question(document: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """模型输出 → 契约口径的结构化题；缺什么就老实留空，不猜。"""
    stem = _clean_text(document.get("stem"), 8000)
    stem = re.sub(r"\\begin\{(question|problem)\}", "", stem)
    stem = re.sub(r"\\end\{(question|problem)\}", "", stem)
    stem = re.sub(r"\\begin\{choices\}[\s\S]*?\\end\{choices\}", "", stem).strip()
    options: list[dict[str, str]] = []
    raw_options = document.get("options")
    if isinstance(raw_options, list):
        for index, option in enumerate(raw_options[: len(OPTION_KEYS)]):
            if isinstance(option, dict):
                content = _clean_text(option.get("content"), 2000)
                key = _raw_text(option.get("key"), 4) or OPTION_KEYS[index]
            else:
                content = _clean_text(option, 2000)
                key = OPTION_KEYS[index]
            if content:
                options.append({"key": key, "content": content})
    kind = _normalize_type(document.get("type"), options, "\\fillin" in stem)

    answer = document.get("answer")
    if isinstance(answer, list):
        answer_text = "".join(str(item) for item in answer)
    elif isinstance(answer, dict):
        answer_text = str(answer.get("final") or answer.get("content") or "")
    else:
        answer_text = str(answer or "")
    solution = document.get("solution")
    if solution is None:
        solution = document.get("analysis")
    if isinstance(solution, dict):
        solution = solution.get("content") or solution.get("final") or ""

    question_no = _raw_text(document.get("question_no") or context.get("question_no"), 20)
    difficulty = _raw_text(document.get("difficulty"), 4).upper()
    if difficulty not in DIFFICULTIES:
        difficulty = _raw_text(context.get("difficulty"), 4).upper()
    if difficulty not in DIFFICULTIES:
        difficulty = "L2"

    return {
        "type": kind,
        "stem": stem,
        "options": options if kind in ("single_choice", "multiple_choice") else [],
        "answer": _clean_text(answer_text, 2000),
        "solution": _clean_text(solution, 8000),
        "question_no": question_no,
        "difficulty": difficulty,
    }


def _context_question(context: dict[str, Any]) -> dict[str, Any]:
    """前端交来的现有题目 → 可回传的契约题；只认已知字段，不猜。"""
    raw_type = str((context or {}).get("type") or "").strip()
    kind = raw_type if raw_type in QUESTION_TYPES else "solution"
    options: list[dict[str, str]] = []
    for index, option in enumerate((context or {}).get("options") or []):
        if not isinstance(option, dict):
            continue
        content = _raw_text(option.get("content"), 2000)
        if not content:
            continue
        key = _raw_text(option.get("key"), 4) or OPTION_KEYS[min(index, len(OPTION_KEYS) - 1)]
        options.append({"key": key, "content": content})
    if kind not in ("single_choice", "multiple_choice"):
        options = []
    difficulty = _raw_text((context or {}).get("difficulty"), 4).upper()
    return {
        "type": kind,
        "stem": _raw_text((context or {}).get("stem"), 8000),
        "options": options,
        "answer": _raw_text((context or {}).get("answer"), 2000),
        "solution": _raw_text((context or {}).get("solution"), 8000),
        "question_no": _raw_text((context or {}).get("question_no"), 20),
        "difficulty": difficulty if difficulty in DIFFICULTIES else "L2",
    }


async def solve(context: dict[str, Any] | None = None) -> dict[str, Any]:
    """【解析本题】：只补答案与解析，题干与选项原样保留。

    不需要题图：老师往往已经识别并改过题干，再让模型看图只会多烧一遍 token。
    """
    question = _context_question(context or {})
    if not question["stem"]:
        return {"ok": False, "detail": "这道题还没有题干：先识别本题或手输题干，再点解析。"}
    binding = ai_center.resolve_task("solve")
    if not binding.is_configured:
        return {
            "ok": False,
            "detail": "「解题」还没指派可用的模型：先在【API 配置】里填账号、指派任务并保存。",
        }
    payload = {
        "type": question["type"],
        "stem": question["stem"],
        "options": question["options"],
        "answer": question["answer"],
    }
    client = OpenAICompatibleProvider(
        api_key=binding.api_key,
        base_url=binding.base_url,
        default_model=binding.model,
        timeout=120,
        label=binding.name,
    )
    try:
        result = await client.chat_completion(
            system_prompt=SOLVE_SYSTEM_PROMPT,
            user_message="题目如下（JSON）：\n" + json.dumps(payload, ensure_ascii=False),
            temperature=0.1,
            max_tokens=4000,
        )
    except Exception as exc:  # noqa: BLE001 - 出网失败只回结构化错误，不抛栈
        return {"ok": False, "detail": f"模型调用失败：{exc}"}

    content = str(result.get("content") or "")
    try:
        document = json.loads(_strip_fences(content))
    except (TypeError, ValueError):
        return {"ok": False, "detail": "模型没有返回可解析的 JSON：" + content[:500]}
    if not isinstance(document, dict):
        return {"ok": False, "detail": "模型返回的 JSON 不是对象"}

    answer = document.get("answer")
    if isinstance(answer, list):
        answer = "".join(str(item) for item in answer)
    elif isinstance(answer, dict):
        answer = answer.get("final") or answer.get("content") or ""
    answer_text = _clean_text(answer, 2000)
    solution_text = _clean_text(document.get("solution") or document.get("analysis"), 8000)
    if not solution_text:
        return {"ok": False, "detail": "模型没给出解析正文；题干可能不完整，补全后再试。"}
    question["answer"] = answer_text
    question["solution"] = solution_text
    return {
        "ok": True,
        "question": question,
        "source": build_exam_source(question),
        "note": _raw_text(document.get("note"), 200),
        "mock": bool(result.get("mock")),
        "model": binding.model,
    }


async def recognize(
    images: list[str], context: dict[str, Any] | None = None, task: str = "ocr"
) -> dict[str, Any]:
    """识别一道题。配置缺失、图片读不出、模型输出坏掉都返回结构化失败。"""
    if task == "solve":
        return await solve(context)
    binding = ai_center.resolve_task(task if task in ai_center.TASK_KEYS else "ocr")
    if not binding.is_configured:
        label = ai_center.TASK_LABELS.get(binding.task, "视觉识别(OCR)")
        return {
            "ok": False,
            "detail": f"「{label}」还没指派可用的模型：先在【API 配置】里填账号、指派任务并保存。",
        }

    source_images: list[str] = []
    for uri in (images or [])[:MAX_IMAGES]:
        data_url, reason = _resolve_image(uri)
        if not data_url:
            return {"ok": False, "detail": f"题图没读出来：{reason}"}
        source_images.append(data_url)
    if not source_images:
        return {"ok": False, "detail": "这道题没有题图可识别：先框选切题或挂上原卷页图。"}

    payload = dict(context or {})
    if len(json.dumps(payload, ensure_ascii=False)) > MAX_CONTEXT_CHARS:
        payload = {"type": payload.get("type"), "stem": str(payload.get("stem") or "")[:6000]}
    user_message = (
        "已有信息（可能为空，仅作对照；以图为准）：\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n请只输出一个 JSON 对象。"
    )

    client = OpenAICompatibleProvider(
        api_key=binding.api_key,
        base_url=binding.base_url,
        default_model=binding.model,
        timeout=120,
        label=binding.name,
    )
    try:
        result = await client.chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.1,
            max_tokens=4000,
            images=source_images,
        )
    except Exception as exc:  # noqa: BLE001 - 出网失败只回结构化错误，不抛栈
        return {"ok": False, "detail": f"模型调用失败：{exc}"}

    content = str(result.get("content") or "")
    try:
        document = json.loads(_strip_fences(content))
    except (TypeError, ValueError):
        return {"ok": False, "detail": "模型没有返回可解析的 JSON：" + content[:500]}
    if not isinstance(document, dict):
        return {"ok": False, "detail": "模型返回的 JSON 不是对象"}

    question = normalize_question(document, payload)
    if not question["stem"]:
        return {"ok": False, "detail": "模型没认出题干；题图可能太糊或不是题目。"}
    source = build_exam_source(question)
    return {
        "ok": True,
        "question": question,
        "source": source,
        "note": str(result.get("note") or "")[:200],
        "mock": bool(result.get("mock")),
        "model": binding.model,
    }
