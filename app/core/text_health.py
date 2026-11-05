"""纯代码提取的文字体检：只判断「像不像乱码」，绝不自动调 AI。

判据保守：替换字符（U+FFFD）或控制字符出现 3 次以上、或占比超过 1% 才标记。
老师看到标记后自己决定要不要点【✨ AI 识别本题】——通道一永远不擅自出网。
"""

from __future__ import annotations

from typing import Any


def text_health(text: str) -> dict[str, Any]:
    raw = str(text or "")
    total = len(raw)
    replacement = raw.count("\ufffd")
    control = sum(1 for char in raw if ord(char) < 32 and char not in "\n\r\t")
    bad = replacement + control
    ratio = (bad / total) if total else 0.0
    return {
        "text_chars": total,
        "missing_chars": bad,
        "has_text_layer": total >= 20,
        "garbled": bad >= 3 or (total >= 100 and ratio >= 0.01),
    }
