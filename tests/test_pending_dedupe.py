"""高度相似（软查重）引擎的判据：``app/core/pending_dedupe.py``。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pending_dedupe``

钉住四条口径：

- 答案的**可比形式**：选择题按标号集合、填空按归一正文；没写答案回空串；
- 一边没表态 ≠ 答案不同：``answer_mismatch`` 必须回 ``None``，不许拿去拦老师；
- 相似比只做排版级归一之后的逐字比对，长短差一倍直接归零；
- 门槛常量是公开契约（界面拿它说「相似度 N%」），改动必须同时改测试。
"""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import pending_dedupe as dedupe  # noqa: E402


class AnswerKeyTest(unittest.TestCase):
    def test_01_choice_keys_are_order_insensitive(self) -> None:
        left = dedupe.answer_key({"kind": "choice", "choice_keys": ["B", "A"]})
        right = dedupe.answer_key({"kind": "choice", "choice_keys": ["b", "a"]})
        self.assertEqual(left, right)
        self.assertEqual(left, "choice:A,B")

    def test_02_text_answer_is_normalised(self) -> None:
        # 全角转半角、去空白、排版标点剔除：同一句话两种打法要撞成同一个键。
        left = dedupe.answer_key({"kind": "text", "content": "$x \\leq 2$"})
        right = dedupe.answer_key({"kind": "text", "content": "$x \\le 2$"})
        self.assertEqual(left, right, "LaTeX 归一必须让两种写法等价")

    def test_03_missing_answer_is_empty_not_wrong(self) -> None:
        self.assertEqual(dedupe.answer_key(None), "")
        self.assertEqual(dedupe.answer_key({}), "")
        self.assertEqual(dedupe.answer_key({"kind": "unknown"}), "")

    def test_04_library_json_text_is_accepted(self) -> None:
        """主库那边读到的是 JSON 文本，池子里这一条是对象：两种都得认。"""
        raw = '{"kind": "choice", "choice_keys": ["A"]}'
        self.assertEqual(dedupe.answer_key(raw), "choice:A")


class AnswerMismatchTest(unittest.TestCase):
    def test_05_same_answer_is_not_a_mismatch(self) -> None:
        self.assertIs(dedupe.answer_mismatch(
            {"kind": "choice", "choice_keys": ["A"]},
            {"kind": "choice", "choice_keys": ["A"]}), False)

    def test_06_different_answer_is_a_mismatch(self) -> None:
        self.assertIs(dedupe.answer_mismatch(
            {"kind": "choice", "choice_keys": ["A"]},
            {"kind": "choice", "choice_keys": ["C"]}), True)

    def test_07_one_side_silent_is_unknown(self) -> None:
        """任一边没写答案就回 None：不许把「没表态」当成「答案不同」去拦老师。"""
        self.assertIsNone(dedupe.answer_mismatch(
            {"kind": "unknown"}, {"kind": "choice", "choice_keys": ["A"]}))
        self.assertIsNone(dedupe.answer_mismatch(None, None))

    def test_07b_answers_agree_is_the_polarity_of_mismatch(self) -> None:
        """报告里的 ``same`` 字段就是本函数：界面只据 ``same is False`` 判红字拦截。"""
        same = {"kind": "choice", "choice_keys": ["A"]}
        other = {"kind": "choice", "choice_keys": ["C"]}
        self.assertIs(dedupe.answers_agree(same, same), True)
        self.assertIs(dedupe.answers_agree(same, other), False)
        self.assertIsNone(dedupe.answers_agree({"kind": "unknown"}, same))
        for left, right in ((same, same), (same, other)):
            self.assertEqual(dedupe.answers_agree(left, right),
                             not dedupe.answer_mismatch(left, right))


class SimilarityTest(unittest.TestCase):
    def test_08_identical_text_scores_one(self) -> None:
        self.assertEqual(dedupe.similarity("已知函数求零点", "已知函数求零点"), 1.0)

    def test_09_typo_still_scores_high(self) -> None:
        base = "已知函数$f(x)=x^2-5x+6$求它的零点个数并说明理由"
        typo = "已知函数$f(x)=x^2-5x+6$求他的零点个数并说明理由"
        self.assertGreaterEqual(dedupe.similarity(base, typo), dedupe.HIGH_SIMILARITY)

    def test_10_unrelated_text_scores_low(self) -> None:
        left = "已知函数$f(x)=x^2-5x+6$求它的零点个数"
        right = "在三角形$ABC$中已知$AB=3$求角$A$的大小"
        self.assertLess(dedupe.similarity(left, right), dedupe.HIGH_SIMILARITY)

    def test_11_far_apart_lengths_fall_to_zero(self) -> None:
        """长短差一倍以上直接归零：省掉一次逐字比对，也不会把短题干误判成长题干。"""
        self.assertEqual(dedupe.similarity("求值", "求值" + "并" * 40), 0.0)

    def test_12_empty_text_never_matches(self) -> None:
        self.assertEqual(dedupe.similarity("", "任何题干"), 0.0)


class LevelContractTest(unittest.TestCase):
    def test_13_levels_and_threshold_are_public(self) -> None:
        """界面要按这三档说话，常量改名或改值必须同时改契约测试。"""
        self.assertEqual(dedupe.LEVEL_IDENTICAL, "identical")
        self.assertEqual(dedupe.LEVEL_HIGH, "high")
        self.assertEqual(dedupe.LEVEL_NONE, "none")
        self.assertGreater(dedupe.HIGH_SIMILARITY, 0.8)
        self.assertLess(dedupe.HIGH_SIMILARITY, 1.0)


if __name__ == "__main__":
    unittest.main()
