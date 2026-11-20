# -*- coding: utf-8 -*-
"""MathType 私有区符号映射清理层（#PUA-MAP-01）契约。

钉住五件事：
1. 25 条码位逐条对上 600dpi 目检结论（含 F024=∃、F028=(、F02D=−、
   F0B3=≥、F044=Δ、F0D7=⋅），F072 明示保留；
2. 族门控：Kingsoft/PMExtra/未知字体即便码位相同也一个字不许换；
3. F072 的两种字符顺序都保持原字符（重音在文本流里整行之后才出现）；
4. 非私有区文本逐字不变，重复映射幂等；
5. 假「字符+字体名」序列以及 ``read_char`` 入口的集成行为。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pua_symbols``
"""

from __future__ import annotations

import unittest
from unittest import mock

from app.core.content import pua_symbols

# 报告 candidate_unicode 的逐条复写（不引用生产表，防它被改坏还一起绿）。
EXPECTED = {
    ("SymbolMT", 0xF024): "\u2203",  # ∃
    ("SymbolMT", 0xF028): "\u0028",  # (
    ("SymbolMT", 0xF029): "\u0029",  # )
    ("SymbolMT", 0xF02B): "\u002B",  # +
    ("SymbolMT", 0xF02D): "\u2212",  # −
    ("SymbolMT", 0xF03C): "\u003C",  # <
    ("SymbolMT", 0xF03D): "\u003D",  # =
    ("SymbolMT", 0xF03E): "\u003E",  # >
    ("SymbolMT", 0xF044): "\u0394",  # Δ
    ("SymbolMT", 0xF05E): "\u22A5",  # ⊥
    ("SymbolMT", 0xF061): "\u03B1",  # α
    ("SymbolMT", 0xF062): "\u03B2",  # β
    ("SymbolMT", 0xF070): "\u03C0",  # π
    ("SymbolMT", 0xF07B): "\u007B",  # {
    ("SymbolMT", 0xF07D): "\u007D",  # }
    ("SymbolMT", 0xF0A2): "\u2032",  # ′
    ("SymbolMT", 0xF0A3): "\u2264",  # ≤
    ("SymbolMT", 0xF0A5): "\u221E",  # ∞
    ("SymbolMT", 0xF0B0): "\u00B0",  # °
    ("SymbolMT", 0xF0B3): "\u2265",  # ≥
    ("SymbolMT", 0xF0CE): "\u2208",  # ∈
    ("SymbolMT", 0xF0D0): "\u2220",  # ∠
    ("SymbolMT", 0xF0D7): "\u22C5",  # ⋅
    ("MT-Extra", 0xF04C): "\u22EF",  # ⋯
    ("MT-Extra", 0xF072): None,      # 向量箭头重音：保留原字符
}

# 实际素材里的子集化前缀；族门控只认字体基名里的关键字。
FONT_PREFIX = "TZCMBP+"
MT_EXTRA_PREFIX = "MUFUVC+"


def font_name(family: str) -> str:
    return (FONT_PREFIX if family == "SymbolMT" else MT_EXTRA_PREFIX) + family


class MathTypeTableTest(unittest.TestCase):
    def test_table_is_exactly_report_25(self):
        self.assertEqual(pua_symbols.MATH_TYPE_SYMBOLS, EXPECTED)
        self.assertEqual(len(pua_symbols.MATH_TYPE_SYMBOLS), 25)
        self.assertEqual(sum(1 for value in EXPECTED.values() if value is not None), 24)

    def test_each_code_maps_per_family(self):
        for (family, code), want in EXPECTED.items():
            with self.subTest(family=family, code=hex(code)):
                got = pua_symbols.map_char(chr(code), font_name(family))
                if want is None:
                    self.assertEqual(got, chr(code))
                else:
                    self.assertEqual(got, want)

    def test_named_codes(self):
        cases = {
            0xF024: ("∃", 0x2203),
            0xF028: ("(", 0x0028),
            0xF02D: ("−", 0x2212),
            0xF0B3: ("≥", 0x2265),
            0xF044: ("Δ", 0x0394),
            0xF0D7: ("⋅", 0x22C5),
        }
        for code, (char, point) in cases.items():
            with self.subTest(code=hex(code)):
                mapped = pua_symbols.map_char(chr(code), "TZCMBP+SymbolMT")
                self.assertEqual(mapped, char)
                self.assertEqual(ord(mapped), point)

    def test_font_family_gate(self):
        self.assertEqual(pua_symbols.font_family("TZCMBP+SymbolMT"), "SymbolMT")
        self.assertEqual(pua_symbols.font_family("MUFUVC+MT-Extra"), "MT-Extra")
        self.assertEqual(pua_symbols.font_family("tzcmbp+symbolmt"), "SymbolMT")
        self.assertEqual(pua_symbols.font_family("mufuvc+mt-extra"), "MT-Extra")
        for name in ("LNUHNF+SimSun", "ABCDEF+KingsoftExtra", "ABCDEF+PMExtra",
                     "ABCDEF+MT", None, ""):
            with self.subTest(font=name):
                self.assertEqual(pua_symbols.font_family(name), "")

    def test_other_families_keep_pua(self):
        for name in ("ABCDEF+KingsoftExtra", "ABCDEF+PMExtra",
                     "ABCDEF+KingsoftSign", "ABCDEF+Unknown", None, ""):
            for code in (0xF024, 0xF044, 0xF072, 0xF04C):
                with self.subTest(font=name, code=hex(code)):
                    self.assertEqual(pua_symbols.map_char(chr(code), name), chr(code))

    def test_non_pua_untouched_even_in_mathtype(self):
        for char in "x=1，中文α∞":
            with self.subTest(char=char):
                self.assertEqual(
                    pua_symbols.map_char(char, "TZCMBP+SymbolMT"), char)

    def test_f072_both_orders_hold(self):
        # 基字符在前、重音在后：I3 实测本就是这个形态，但两者常隔换行。
        base_then_accent = "a\uf072"
        accent_then_base = "\uf072a"
        for text in (base_then_accent, accent_then_base):
            with self.subTest(text=text):
                self.assertEqual(
                    pua_symbols.map_text(
                        text, lambda _index: "MUFUVC+MT-Extra"),
                    (text, 0))


class MapTextTest(unittest.TestCase):
    def test_non_pua_text_unchanged(self):
        text = "在 △ABC 中，角 A,B,C 所对的边分别为 a,b,c。"
        self.assertEqual(
            pua_symbols.map_text(text, lambda _index: "TZCMBP+SymbolMT"),
            (text, 0))

    def test_empty_text(self):
        self.assertEqual(pua_symbols.map_text("", lambda _i: "x"), ("", 0))

    def test_idempotent(self):
        text = "x\uf0ce(0,+\uf0a5)"
        font = lambda _index: "TZCMBP+SymbolMT"
        once, first = pua_symbols.map_text(text, font)
        twice, second = pua_symbols.map_text(once, font)
        self.assertEqual(once, "x\u2208(0,+\u221E)")
        self.assertEqual(first, 2)
        self.assertEqual((twice, second), (once, 0))

    def test_fake_char_font_sequence(self):
        # 下标 → 字体名：两个家族混排，未知族的码位必须原样留下。
        text = "a\uf024b\uf04c\uf072c\uf024"
        fonts = {
            1: "TZCMBP+SymbolMT",
            3: "MUFUVC+MT-Extra",
            4: "MUFUVC+MT-Extra",
            6: "ABCDEF+PMExtra",
        }
        mapped, count = pua_symbols.map_text(text, lambda i: fonts.get(i))
        self.assertEqual(mapped, "a∃b⋯\uf072c\uf024")
        self.assertEqual(count, 2)


class ReadCharTest(unittest.TestCase):
    class FakeTextPage:
        raw = object()

        def __init__(self, text: str) -> None:
            self.text = text

        def get_text_range(self, index: int, count: int = 1) -> str:
            return self.text[index:index + count]

    def test_read_char_maps_with_font(self):
        page = self.FakeTextPage("\uf024")
        with mock.patch.object(pua_symbols, "_font_name",
                               return_value="TZCMBP+SymbolMT"):
            self.assertEqual(pua_symbols.read_char(page, 0), "∃")

    def test_read_char_keeps_when_font_unknown(self):
        page = self.FakeTextPage("\uf024")
        with mock.patch.object(pua_symbols, "_font_name", return_value=""):
            self.assertEqual(pua_symbols.read_char(page, 0), "\uf024")

    def test_read_char_skips_font_lookup_for_plain_text(self):
        page = self.FakeTextPage("a")
        with mock.patch.object(pua_symbols, "_font_name") as lookup:
            self.assertEqual(pua_symbols.read_char(page, 0), "a")
            lookup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
