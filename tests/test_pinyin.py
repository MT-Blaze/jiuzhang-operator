"""拼音首字母检索表的契约测试。

守三条：

1. **汉字取首字母**：集合→jh、一模→ym；表外的字宁可少给也不给错。
2. **拉丁与数字原样保留**：AMC→amc、9月月考→9yyk——外国题标签照样能按原文捞。
3. **符号丢掉**：搜索框里打标点不该影响命中，也不该把整库端出来。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pinyin``
"""

from __future__ import annotations

import unittest

from app.core import pinyin


class PinyinInitialsTest(unittest.TestCase):
    def test_01_han_chars_become_their_initials(self) -> None:
        self.assertEqual(pinyin.initials("集合"), "jh")
        self.assertEqual(pinyin.initials("一模"), "ym")
        self.assertEqual(pinyin.initials("全国高中数学联赛"), "qggzsxls")

    def test_02_latin_and_digits_pass_through_lowercase(self) -> None:
        self.assertEqual(pinyin.initials("AMC"), "amc")
        self.assertEqual(pinyin.initials("A-Level"), "alevel")
        self.assertEqual(pinyin.initials("9月月考"), "9yyk")

    def test_03_symbols_and_spaces_are_dropped(self) -> None:
        self.assertEqual(pinyin.initials("高三·联考（一）"), "gslky")
        self.assertEqual(pinyin.initials("  一模  "), "ym")
        self.assertEqual(pinyin.initials("%_%"), "")

    def test_04_unknown_han_char_is_skipped_not_guessed(self) -> None:
        """表外的字（认不准读音的生僻字）不进串：宁可少给，给错会把人带偏。"""
        self.assertEqual(pinyin.initials("囧"), "")
        self.assertEqual(pinyin.initials("囧模"), "m")

    def test_05_query_case_is_normalised_too(self) -> None:
        """查询串走的是同一个函数：大写 ``J`` 与小写 ``j`` 得同一把钥匙。"""
        self.assertEqual(pinyin.initials("J"), pinyin.initials("j"))
        self.assertEqual(pinyin.initials("JH"), "jh")


if __name__ == "__main__":
    unittest.main()
