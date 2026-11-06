"""纯本地识别：题块文字 → 契约题目，外加一份坏题体检。

不联网、不读模型：只要 PDF 文本层还读得出字，这一级就能把题干、选项、
答案与解析填好。它是识别矩阵的第一级，也是唯一永远先跑的一级。
"""

from __future__ import annotations

from typing import Any

from app.core import scan_text


def build_document(region: dict[str, Any] | None, page_no: int, number: Any,
                   asset_id: str, title: str) -> dict[str, Any]:
    """自动切图生成的一道待审题：文字层读得出就填正文，读不出才落占位提示。

    题干、选项、答案与解析都从题块坐标内的文字还原（Unicode 数学字符折成
    LaTeX，公式包 ``$...$``）；原题图始终挂在题身上，切图与文字互为对照。
    """
    from app.core.ingest import DEFAULT_DIFFICULTY, _document

    label = str(number or "")
    parsed = scan_text.parse_scan_text((region or {}).get("text"), label)
    source = {"question_no": label, "paper_title": title}
    images = [{
        "id": asset_id,
        "role": "stem",
        "uri": "/static/uploads/" + asset_id + ".png",
    }]
    if parsed["stem"]:
        document = _document(parsed["stem"], parsed["options"], parsed["answer"],
                             parsed["blanks"], parsed["solution"], label)
        document["source"] = source
        document["images"] = images
        return document
    return {
        "schema_version": "2.0",
        "type": "solution",
        "stem": "（自动切题：原卷第 %d 页第 %s 题，请对照题图录入题干与答案）"
                % (page_no, label or "?"),
        "difficulty": DEFAULT_DIFFICULTY,
        "source": source,
        "images": images,
    }


def probe(items: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
    """本地这一级认出了多少、剩多少坏题；坏题索引交给下一级。"""
    total = len([item for item in items if isinstance(item, dict)])
    bad_indexes = [int(index) for index in (report.get("bad_indexes") or [])
                   if isinstance(index, int) and 0 <= index < total]
    if total == 0:
        return {"ok": False, "filled": 0, "bad_indexes": [],
                "detail": "这次没切出题目"}
    return {
        "ok": not bad_indexes,
        "filled": total - len(bad_indexes),
        "bad_indexes": bad_indexes,
        "detail": ("本地提取 %d 题未发现坏题" % total if not bad_indexes
                   else "本地提取有 %d 道坏题" % len(bad_indexes)),
    }
