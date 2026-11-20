# -*- coding: utf-8 -*-
"""MathType 符号字体私有区 → Unicode 同义字符（文字直取清洗层）。

MathType 生成的卷子会把 SymbolMT / MT-Extra 里的符号写成 U+F0xx 私有区字符，
文字直取出来后正文就是乱码。码位身份按 600dpi 渲染目检确定（证据见
``.system_generated/private-use-recon/report.toml``）：两族嵌入字体被剥掉了
post/cmap/name 表，没有 glyph 名，也**不能**套通用 Adobe Symbol 表。

查表钥匙是 (字体族, 码位) 两样：字体基名含 ``SymbolMT`` / ``MT-Extra`` 才查，
其余家族（WPS-Kingsoft、PMExtra 等）与普通私有区字符一律原样保留。
整块可下架：删掉本文件、把 ``read_char`` 换回 ``textpage.get_text_range`` 即复原。
"""

from __future__ import annotations

import ctypes
from typing import Any, Callable

__all__ = ["MATH_TYPE_SYMBOLS", "font_family", "map_char", "map_text", "read_char"]

SYMBOL_MT = "SymbolMT"
MT_EXTRA = "MT-Extra"
_FONT_NAME_BYTES = 256

# (字体族, 码位) → Unicode。None = 已识别但故意不换：F072 是字母上方的向量
# 箭头重音，实测文本流把重音排在整行之后、与基字符隔着换行，字符流内定不了
# 基字符；换成 U+2192 会错位，裸 \vec 更不允许，只能原样保留。
MATH_TYPE_SYMBOLS: dict[tuple[str, int], str | None] = {
    (SYMBOL_MT, 0xF024): "\u2203",  # ∃
    (SYMBOL_MT, 0xF028): "\u0028",  # (
    (SYMBOL_MT, 0xF029): "\u0029",  # )
    (SYMBOL_MT, 0xF02B): "\u002B",  # +
    (SYMBOL_MT, 0xF02D): "\u2212",  # −
    (SYMBOL_MT, 0xF03C): "\u003C",  # <
    (SYMBOL_MT, 0xF03D): "\u003D",  # =
    (SYMBOL_MT, 0xF03E): "\u003E",  # >
    (SYMBOL_MT, 0xF044): "\u0394",  # Δ
    (SYMBOL_MT, 0xF05E): "\u22A5",  # ⊥
    (SYMBOL_MT, 0xF061): "\u03B1",  # α
    (SYMBOL_MT, 0xF062): "\u03B2",  # β
    (SYMBOL_MT, 0xF070): "\u03C0",  # π
    (SYMBOL_MT, 0xF07B): "\u007B",  # {
    (SYMBOL_MT, 0xF07D): "\u007D",  # }
    (SYMBOL_MT, 0xF0A2): "\u2032",  # ′
    (SYMBOL_MT, 0xF0A3): "\u2264",  # ≤
    (SYMBOL_MT, 0xF0A5): "\u221E",  # ∞
    (SYMBOL_MT, 0xF0B0): "\u00B0",  # °
    (SYMBOL_MT, 0xF0B3): "\u2265",  # ≥
    (SYMBOL_MT, 0xF0CE): "\u2208",  # ∈
    (SYMBOL_MT, 0xF0D0): "\u2220",  # ∠
    (SYMBOL_MT, 0xF0D7): "\u22C5",  # ⋅
    (MT_EXTRA, 0xF04C): "\u22EF",   # ⋯
    (MT_EXTRA, 0xF072): None,       # 向量箭头重音：见上，保留原字符
}


def font_family(font_name: str | None) -> str:
    """PDF 字体基名 → MathType 家族；不认识的一律交空串。"""
    name = (font_name or "").lower()
    if "symbolmt" in name:
        return SYMBOL_MT
    if "mt-extra" in name:
        return MT_EXTRA
    return ""


def map_char(char: str, font_name: str | None) -> str:
    """单个字符按字体族换字；不命中就原样返回（没有字体名也算不命中）。"""
    if len(char) == 1:
        target = MATH_TYPE_SYMBOLS.get((font_family(font_name), ord(char)))
        if target is not None:
            return target
    return char


def map_text(text: str, font_of_char: Callable[[int], str | None]) -> tuple[str, int]:
    """整段文字按「字符下标 → 字体名」重写；返回 (新文字, 实际换掉的个数)。"""
    if not text:
        return text, 0
    pieces: list[str] = []
    mapped = 0
    for index, char in enumerate(text):
        new = char
        if "\uF000" <= char <= "\uF0FF":
            new = map_char(char, font_of_char(index))
            if new != char:
                mapped += 1
        pieces.append(new)
    return "".join(pieces), mapped


def read_char(textpage: Any, index: int) -> str:
    """PDFium 文本页第 index 个字符；命中 MathType 私有区符号才换成 Unicode。"""
    char = textpage.get_text_range(index, 1)
    if len(char) != 1 or not "\uF000" <= char <= "\uF0FF":
        return char
    return map_char(char, _font_name(textpage, index))


def _font_name(textpage: Any, index: int) -> str:
    """第 index 个字符的字体基名；取不到就交空串（按未知族处理，原样保留）。"""
    try:
        from pypdfium2 import raw
        obj = raw.FPDFText_GetTextObject(textpage.raw, index)
        font = raw.FPDFTextObj_GetFont(obj) if obj else None
        if not font:
            return ""
        buffer = ctypes.create_string_buffer(_FONT_NAME_BYTES)
        need = int(raw.FPDFFont_GetBaseFontName(font, buffer, _FONT_NAME_BYTES))
        if need > _FONT_NAME_BYTES:
            buffer = ctypes.create_string_buffer(need)
            raw.FPDFFont_GetBaseFontName(font, buffer, need)
        return buffer.value.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - 字体名缺席只该让字符原样保留
        return ""
