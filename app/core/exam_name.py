"""试卷名称拼装：只由 exams 的属性动态算出，任何表都不存冗余试卷名。

四条规则（主公 2026-11-11 定案）：
- 月考：年份 + 组织/学校 + 年级 + 月份 + 月考 + 学科；
- 模考：年份 + 组织/学校 + 年级 + 轮次 + 模考 + 学科（不显示月份，轮次优先显示 2模）；
- 期中/期末：年份 + 组织/学校 + 年级 + 学期 + 类型 + 学科；
- 其他：年份 + 组织/学校 + 年级 + 类型 + 学科。
空段不占位，段与段之间不加分隔符。
"""

from __future__ import annotations

import re

_ROUND_DIGITS = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}
MOCK_ROUND_RE = re.compile(r"([零一二三四五六七八九十\d]+)\s*模")


def parse_mock_round(text: object) -> int | None:
    """从「一模 / 二模 / 2模」之类的文本里认出轮次；认不出返回 None。"""
    match = MOCK_ROUND_RE.search(str(text or ""))
    if match is None:
        return None
    raw = match.group(1)
    if raw.isdigit():
        value = int(raw)
    elif raw == "十":
        value = 10
    elif raw.startswith("十"):
        value = 10 + _ROUND_DIGITS.get(raw[1:], 0)
    elif raw.endswith("十"):
        value = _ROUND_DIGITS.get(raw[0], 0) * 10
    else:
        value = _ROUND_DIGITS.get(raw, 0)
    return value if 1 <= value <= 10 else None


def round_label(mock_round: int | None) -> str:
    return f"{int(mock_round)}模" if mock_round else ""


def compose_exam_name(
    *,
    year: int | None,
    exam_type: str,
    exam_org_name: str | None = None,
    school_name: str | None = None,
    grade_name: str = "",
    month: int | None = None,
    mock_round: int | None = None,
    semester: str | None = None,
    subject_name: str = "",
) -> str:
    parts: list[str] = []
    if year:
        parts.append(f"{int(year)}年")
    org = str(exam_org_name or school_name or "").strip()
    if org:
        parts.append(org)
    if grade_name:
        parts.append(str(grade_name).strip())
    exam_type = str(exam_type or "").strip()
    if exam_type == "月考":
        if month:
            parts.append(f"{int(month)}月")
        parts.append("月考")
    elif exam_type == "模考":
        parts.append(round_label(mock_round) or "模考")
    elif exam_type in ("期中", "期末"):
        if semester:
            parts.append(str(semester).strip())
        parts.append(exam_type)
    else:
        if exam_type:
            parts.append(exam_type)
    if subject_name:
        parts.append(str(subject_name).strip())
    return "".join(part for part in parts if part)


__all__ = ["MOCK_ROUND_RE", "compose_exam_name", "parse_mock_round", "round_label"]
