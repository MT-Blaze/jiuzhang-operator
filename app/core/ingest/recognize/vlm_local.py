"""本地 VLM 逐题识别（T6 §3）：整题图 → OpenAI 兼容 chat completions → 契约题目。

请求走本机隔离服务（vlm_service 懒起 llama-server），image base64 内联、
试卷不出本机。提示词钉题目契约：行内公式 $...$、独立公式 $$...$$，只转录
看得见的内容、绝不编造。单题等待 900s（CPU 首题慢）；逐题进度 note；
失败 ok=False 显性化，不级联、不偷换。``recognize_image`` 也供公式裁图
通道（formula.py）复用同一张单图能力。
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from app.core import wire
from app.core.ingest.recognize import shared as recognize_shared

logger = logging.getLogger(__name__)

VLM_LOCAL_WAIT_SECONDS = 900.0
MAX_TOKENS = 4096

QUESTION_PROMPT = r"""你是数学试卷录题助手。看题图，只输出一个 JSON 对象，不要 Markdown 代码块，不要解释。
字段：
- "type": "single_choice" | "multiple_choice" | "fill_blank" | "solution" | "proof"
- "stem": 题干正文（含公式，行内公式用 $...$，独立公式用 $$...$$，不要带题号，不要带选项）
- "options": [{"key":"A","content":"..."}]，非选择题给空数组
- "answer": 答案（选择题写字母如 "A" 或 "AB"；填空题写答案；解答题写最终结果）
- "solution": 解析正文（不含「答案：」三个字）
- "question_no": 原卷题号（图上看不清就留空串）
- "difficulty": "L1" | "L2" | "L3" | "L4"（拿不准就 "L2"）
铁律：只转录看得见的内容，看不清就留空串；绝不编造答案、选项或题号。
公式：行内公式只用 $...$，独立公式只用 $$...$$，不要写 \( \) 或 \[ \]。
标点：照抄原卷标点，不要自行添加并列标点。"""

FORMULA_PROMPT = r"""你是公式转写助手。看图中的数学公式，只输出 LaTeX 正文：
行内形式直接给表达式，不要包 $ 或 $$，不要代码块，不要解释。
看不清的符号用 \square 占位，绝不编造。"""


def _data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _chat(png: bytes, prompt: str, endpoint: dict[str, str], *,
          wait: float = VLM_LOCAL_WAIT_SECONDS) -> dict[str, Any]:
    """一次 chat completions（单图＋提示词）；失败如实回报，不抛。"""
    base = str(endpoint.get("base_url") or "").rstrip("/")
    token = str(endpoint.get("token") or "")
    if not base.startswith("http://"):
        return {"ok": False, "detail": "本地 VLM 服务地址缺失"}
    payload = {
        "model": "local-vlm",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": _data_url(png)}},
            {"type": "text", "text": prompt},
        ]}],
        "temperature": 0.1,
        "max_tokens": MAX_TOKENS,
    }
    request = urllib.request.Request(
        base + "/v1/chat/completions",
        data=wire.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + token},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=max(1.0, wait)) as response:
            body = wire.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "detail": "本地 VLM 推理失败：HTTP %d" % exc.code}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "detail": "本地 VLM 推理失败：%s" % str(exc)[:200]}
    choices = body.get("choices") if isinstance(body, dict) else None
    message = (choices[0] or {}).get("message") if isinstance(choices, list) and choices else None
    text = str((message or {}).get("content") or "").strip()
    if not text:
        return {"ok": False, "detail": "本地 VLM 没有返回正文"}
    return {"ok": True, "text": text, "detail": "本地 VLM 已识别"}


def _question_json(text: str) -> dict[str, Any] | None:
    """模型偶尔包代码块或前后缀：取第一个 { 到最后一个 } 的 JSON，解不出当失败。"""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = wire.loads(text[start:end + 1])
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def recognize_image(png: bytes, endpoint: dict[str, str], *,
                    kind: str = "question",
                    wait: float = VLM_LOCAL_WAIT_SECONDS) -> dict[str, Any]:
    """单图能力：question＝整题契约 JSON；formula＝公式 LaTeX 正文。"""
    if not png:
        return {"ok": False, "detail": "题图为空，没法交本地 VLM"}
    prompt = FORMULA_PROMPT if kind == "formula" else QUESTION_PROMPT
    outcome = _chat(png, prompt, endpoint, wait=wait)
    if not outcome.get("ok"):
        return outcome
    text = str(outcome["text"])
    if kind == "formula":
        return {"ok": True, "latex": text.strip().strip("$").strip(),
                "detail": "本地 VLM 公式已转写"}
    question = _question_json(text)
    if question is None or not str(question.get("stem") or "").strip():
        return {"ok": False, "detail": "本地 VLM 返回的不是可解析的题目 JSON"}
    return {"ok": True, "question": question, "detail": "本地 VLM 已识别"}


async def run(batch_id: str, items: list[dict[str, Any]], indexes: list[int],
              endpoint: dict[str, str],
              route: dict[str, Any],
              on_progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """逐题交本地 VLM；返回成功下标，失败显性不级联（router 口径）。"""
    if not indexes:
        return {"ok": True, "attempted": 0, "filled": 0, "filled_indexes": [],
                "detail": "没有需要交给本地 VLM 的题"}
    filled_indexes: list[int] = []
    total = len(indexes)
    for position, index in enumerate(indexes, start=1):
        item = items[index]
        note = "正在将第 %d/%d 题交本地千问 VLM 推理（首载 GGUF 较慢，单题最长等 15 分钟）..." % (
            position, total)
        logger.info(note)
        route["note"] = note
        _progress(on_progress, route)
        data = recognize_shared.item_image_bytes(item)
        if not data:
            continue
        outcome = await asyncio.to_thread(
            recognize_image, data, endpoint, kind="question",
            wait=VLM_LOCAL_WAIT_SECONDS)
        if not outcome.get("ok"):
            route["note"] = "第 %d/%d 题本地 VLM 没成功（%s），继续下一题。" % (
                position, total, str(outcome.get("detail") or "")[:120])
            _progress(on_progress, route)
            continue
        document = recognize_shared.document_from_ai(
            outcome["question"], item.get("question") or {})
        document = recognize_shared.merge_local(document, item.get("question") or {})
        if recognize_shared.save_back(item, document, batch_id, "ingest.vlm_local"):
            filled_indexes.append(index)
    filled = len(filled_indexes)
    return {
        "ok": filled > 0,
        "attempted": total,
        "filled": filled,
        "filled_indexes": filled_indexes,
        "detail": "" if filled == total else ("只有 %d/%d 道回来了" % (filled, total)),
    }


def _progress(callback: Callable[[dict[str, Any]], None] | None,
              route: dict[str, Any]) -> None:
    if callback is None:
        return
    try:
        callback(route)
    except Exception:  # noqa: BLE001 - 进度写不进去不该打断识别
        pass