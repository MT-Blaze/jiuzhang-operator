"""第 57 条落清洗器：拆掉只圈数字的行内 ``$``（``$3$`` → ``3``）。

只认整体为纯数字的段（可选正负号含 U+2212、小数、``%``／``\\%``、度数 ``°``）；
``$$``、未闭合 ``$``、转义 ``\\$``、含字母/运算符/命令的段一律不动。
"""

from __future__ import annotations

import re

__all__ = ["unwrap_bare_number_dollars"]

_NUMBER = r"[+\-\u2212]?(?:\d+(?:\.\d+)?|\.\d+)(?:\\?%|°)?"
_BARE = re.compile(r"(?<![\\$])\$(?!\$)\s*(" + _NUMBER + r")\s*\$(?!\$)")


def unwrap_bare_number_dollars(text: str) -> tuple[str, int]:
    """返回 (拆后的文本, 拆掉的个数)；数字原样输出，不补空格、不转全角。"""
    if not isinstance(text, str):
        return "", 0
    return _BARE.subn(r"\1", text)
