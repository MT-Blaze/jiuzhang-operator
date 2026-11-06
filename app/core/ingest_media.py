"""OCR 与单文件分拣：图片认字、Word 取文本，PDF 只交原卷大图。"""

from __future__ import annotations

import base64
from typing import Any

from app.core.ingest_text import (
    DEFAULT_DIFFICULTY,
    IMAGE_MIME,
    MAX_IMAGE_BYTES,
    build_documents,
    classify,
    decode_text,
    extract_docx_text,
    suffix_of,
)

__all__ = ["ocr_image", "_items_from_file", "_page_of", "_placeholder"]

OCR_SYSTEM_PROMPT = (
    "你是试卷转写助手。把图片里的题目**逐字**转成 Markdown + LaTeX 文本："
    "保留题号、题干、选项（A/B/C/D 各占一行）、答案与解析；"
    "公式写成 $...$ 或 $$...$$；看不清的地方写 [无法辨认]，"
    "绝不补写图片上没有的内容。"
)


async def ocr_image(data: bytes, mime: str) -> tuple[str, str]:
    """图片 → 文字。返回 (文本, 失败原因)；失败时文本是空串。

    认不出就是认不出：失败时**不编**任何题目文字，由调用方记「待识别」。
    """
    from app.core import ai_client

    client = ai_client.get_client()
    if client.is_mock:
        return "", "本机没有配置可用的 AI Provider（缺密钥），图片认不出来"
    data_url = f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
    try:
        result = await client.chat_completion(
            system_prompt=OCR_SYSTEM_PROMPT,
            user_message="请把这张图片里的题目逐字转写出来。",
            temperature=0.1,
            max_tokens=4000,
            images=[data_url],
        )
    except Exception as exc:  # noqa: BLE001 — 任何失败都如实报，绝不编题
        return "", f"OCR 调用失败：{exc}"
    return str(result.get("content") or ""), ""


def _placeholder(label: str) -> dict[str, Any]:
    """一条「待识别」的占位题：题干写明要老师补，不含任何编造内容。"""
    return {
        "type": "solution",
        "stem": label,
        "difficulty": DEFAULT_DIFFICULTY,
        "tags": ["待识别"],
    }


def _page_of(doc_pages: list[int], index: int) -> int:
    """第 index 道题落在原卷第几页；没有页号就退到第 1 页。"""
    if 0 <= index < len(doc_pages):
        return int(doc_pages[index]) or 1
    return 1


async def _items_from_file(name: str, data: bytes) -> tuple[
        list[dict[str, Any]], list[str], str, str, bool]:
    """一个文件 → (题目文档, 警告, 分拣类别, 抽出来的源文本, 是否原卷大图)。

    最后一个 ``True`` 表示这份 PDF 只当原卷大图：**一道题都不落池**，
    只把每页渲染成页面图并附带文本层抽出的题块坐标，老师在左栏确认切分。
    """
    kind = classify(name)
    warnings: list[str] = []
    if kind == "text":
        text = decode_text(data)
        documents, notes = build_documents(text)
        return documents, warnings + notes, kind, text, False
    if kind == "docx":
        text = extract_docx_text(data)
        documents, notes = build_documents(text)
        return documents, warnings + notes, kind, text, False
    if kind == "pdf":
        # 这里只负责分拣：页图、题块坐标与自动切图都在后台解析完成后做。
        warnings.append(
            f"{name}：已按原卷大图导入。页面图渲染完成后，识别出的每道题会自动裁好"
            "并排进待审池，左侧绿框可拖拽微调。"
        )
        return [], warnings, kind, "", True
    if kind == "image":
        mime = IMAGE_MIME.get(suffix_of(name), "image/png")
        if len(data) > MAX_IMAGE_BYTES:
            return [], warnings + [f"{name}：图片太大（上限 8 MiB），没认"], kind, "", False
        text, reason = await ocr_image(data, mime)
        if not text.strip():
            warnings.append(f"{name}：{reason or '认不出文字'}，留了一条待识别")
            return [_placeholder(f"（待识别：{name}，图片认不出文字，请老师补录）")], \
                warnings, kind, "", False
        documents, notes = build_documents(text)
        if not documents:
            warnings.append(f"{name}：认出来了，但没拆出题目，留了一条待识别")
            return [_placeholder(f"（待识别：{name}，认出了文字但没拆出题目）")], \
                warnings, kind, text, False
        return documents, warnings + notes, kind, text, False
    return [], warnings, kind, "", False
