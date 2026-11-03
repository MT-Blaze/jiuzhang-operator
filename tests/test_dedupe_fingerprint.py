"""查重指纹升级（军令 #32 · S2）：比对归一、正文骨架、公式签名与可解释置信度。

守的是判据 2.1–2.6 里几条「不写用例就会悄悄退回去」的底线：

1. **签名认写法不认语义**：``\\frac12``／``\\frac{1}{2}``／``1/2`` 必须撞成同一个签名，
   但 ``0.5`` 与 ``\\frac{1}{2}`` 抓不到——如实报「抓不到」，不许偷偷加规则（2.1／2.4）；
2. **符号一个都不省**：``A\\cap B`` 与 ``A\\cup B`` 签名不同，``x^2-3x+2`` 与
   ``x^2-5x+6`` 绝不能判「确定」——误报的下一站是删数据（2.2／2.3）；
3. **只有一把尺子**：旧 ``HIGH_SIMILARITY=0.92`` 并进 ``very_similar`` 档，
   ``pending_dedupe`` 不再另设阈值（2.6）；
4. **百分比只是档位内的排序刻度**：很像 ≤89，措辞永不出「98% 是同一道题」（2.5）；
5. **指纹拿比对归一算**，不拿原始源码算：同一句话两种打法同指纹，旧归一口径不回退。

运行：``.venv/Scripts/python.exe -m unittest tests.test_dedupe_fingerprint``
"""

from __future__ import annotations

import unittest

from app.core import bank_dedupe, pending_dedupe

PLACEHOLDER = bank_dedupe.SKELETON_PLACEHOLDER


def sig(text: str) -> str:
    return bank_dedupe.formula_signature(text)


def skel(text: str) -> str:
    return bank_dedupe.skeleton(text)


class SignatureCanonicalTest(unittest.TestCase):
    """判据 2.1：分数的三种写法签名全等；排版命令与段内空白透明。"""

    def test_01_three_fraction_forms_share_one_signature(self) -> None:
        cases = [
            r"已知 $a=\frac12$",
            r"已知 $a=\frac{1}{2}$",
            r"已知 $a=1/2$",
        ]
        marks = {sig(case) for case in cases}
        self.assertEqual(len(marks), 1, msg=str(cases))
        # 签名只由数学段组成（正文归骨架管），所以「已知」不进签名
        self.assertEqual(marks.pop(), "a = 1 / 2")

    def test_02_dfrac_and_left_right_are_transparent(self) -> None:
        self.assertEqual(sig(r"$\left(1,\dfrac{3}{4}\right)$"), sig(r"$(1,\frac34)$"))

    def test_03_displaystyle_and_thinspace_do_not_move_the_signature(self) -> None:
        self.assertEqual(sig(r"$\displaystyle x = 1$"), sig(r"$x\,=1$"))

    def test_04_signature_is_ordered_not_a_bag(self) -> None:
        # 顺序也是判据：a<b 与 b<a 是两句不同的话
        self.assertNotEqual(sig(r"$a<b$"), sig(r"$b<a$"))


class SignatureSymbolTest(unittest.TestCase):
    """判据 2.3：符号一个都不省。"""

    def test_01_cap_and_cup_separate(self) -> None:
        left, right = sig(r"设 $A\cap B$"), sig(r"设 $A\cup B$")
        self.assertNotEqual(left, right)
        self.assertIn(bank_dedupe.COMMAND_MARK + "cap", left)
        self.assertIn(bank_dedupe.COMMAND_MARK + "cup", right)

    def test_02_command_name_is_not_plain_letters(self) -> None:
        self.assertNotEqual(sig(r"$A\cap B$"), sig(r"$AcapB$"))

    def test_03_coefficients_differentiate(self) -> None:
        self.assertNotEqual(sig(r"$x^2-3x+2$"), sig(r"$x^2-5x+6$"))


class SemanticLimitTest(unittest.TestCase):
    """判据 2.4：语义等价抓不到就如实报，不许假装认得。"""

    def test_01_decimal_vs_fraction_signatures_differ(self) -> None:
        self.assertNotEqual(sig(r"$0.5$"), sig(r"$\frac{1}{2}$"))
        self.assertEqual(bank_dedupe.number_sequence(r"$0.5$"), ["0.5"])
        self.assertEqual(bank_dedupe.number_sequence(r"$\frac{1}{2}$"), ["1", "2"])

    def test_02_both_misses_are_reported_in_the_signals(self) -> None:
        result = bank_dedupe.confidence(r"若 $x=0.5$，则 $x^2$ 的值为",
                                       r"若 $x=\frac{1}{2}$，则 $x^2$ 的值为")
        self.assertFalse(result["signature_equal"])
        self.assertFalse(result["numbers_equal"])
        self.assertNotEqual(result["level"], "certain")
        hit = {item["key"]: item["hit"] for item in result["signals"]}
        self.assertFalse(hit["signature"])
        self.assertFalse(hit["numbers"])
        detail = {item["key"]: item["detail"] for item in result["signals"]}
        self.assertIn("0.5", detail["numbers"])

    def test_03_still_recalled_as_a_candidate(self) -> None:
        # 抓不到语义不等于不报：宽档必须把它留在候选里，交给老师肉眼
        result = bank_dedupe.confidence(r"若 $x=0.5$，则 $x^2$ 的值为",
                                       r"若 $x=\frac{1}{2}$，则 $x^2$ 的值为")
        self.assertIn(result["level"], bank_dedupe.TIER_LEVELS["loose"])


class SkeletonTest(unittest.TestCase):
    """骨架只负责召回：数学段挖成占位符，段外只留中文与标点。"""

    def test_01_math_becomes_one_placeholder(self) -> None:
        # 中文标点不进骨架（与 normalize_text 同一口径），所以占位符直接相连
        self.assertEqual(skel(r"已知 $a=1$，则 $b=2$ 的值是"),
                         f"已知{PLACEHOLDER}则{PLACEHOLDER}的值是")
        self.assertEqual(skel(r"已知 $\frac{1}{2}$，则"), f"已知{PLACEHOLDER}则")

    def test_02_placeholder_keeps_count_and_order(self) -> None:
        self.assertEqual(skel(r"已知 $a$，则 $b$").count(PLACEHOLDER), 2)

    def test_03_latin_digits_and_punctuation_are_dropped(self) -> None:
        # 骨架只留汉字：中文标点、全角括号、半角括号与标点、数字、字母一律不进
        self.assertEqual(skel("如图, AB=3, 则阴影部"), "如图则阴影部")
        self.assertEqual(skel("「下列」哪（个）正确？"), "下列哪个正确")
        self.assertEqual(skel("已知 1. 下列, 哪项正确."), "已知下列哪项正确")
        # 「、」(Po) 与「「」」(Ps/Pe) 折叠后仍在非 ASCII 区，靠 Unicode 类别那一道兜住
        self.assertEqual(skel("集合A、B的交集"), "集合的交集")
        self.assertEqual(skel("选项①正确，半径为○"), "选项正确半径为")
        self.assertEqual(skel("已知 $a<b$，则下列哪项正确"),
                         f"已知{PLACEHOLDER}则下列哪项正确")

    def test_03b_skeleton_keeps_one_placeholder_per_span(self) -> None:
        self.assertEqual(skel(r"$x$ 的取值范围是 $[1,2]$"),
                         f"{PLACEHOLDER}的取值范围是{PLACEHOLDER}")

    def test_04_identical_prose_scores_one(self) -> None:
        self.assertEqual(bank_dedupe.text_similarity("已知则的值是", "已知则的值是"), 1.0)

    def test_05_empty_or_huge_length_gap_scores_zero(self) -> None:
        self.assertEqual(bank_dedupe.text_similarity("", "已知"), 0.0)
        self.assertEqual(bank_dedupe.text_similarity("已知", "已知已知已知已知已知"), 0.0)

    def test_06_symbol_only_change_leaves_skeleton_untouched(self) -> None:
        self.assertEqual(skel(r"设 $A\cap B$，则"), skel(r"设 $A\cup B$，则"))


class ConfidenceTest(unittest.TestCase):
    """判据 2.5：四档标签 + 百分比 + 可展开的命中/未命中信号明细。"""

    def _pair(self) -> dict:
        return bank_dedupe.confidence("设全集为U，若 $A\\cap B$，则下列正确的是",
                                      "设全集为U，若 $A\\cup B$，则下列正确的是")

    def test_01_symbol_only_difference_lands_in_loose_tier(self) -> None:
        result = self._pair()
        self.assertIn(result["level"], ("fairly_similar", "possible"))
        self.assertTrue(bank_dedupe.accepts(result["level"], "loose"))
        self.assertFalse(bank_dedupe.accepts(result["level"], "standard"))
        self.assertFalse(bank_dedupe.accepts(result["level"], "strict"))

    def test_02_signals_are_five_expandable_rows(self) -> None:
        result = bank_dedupe.confidence(r"$x=1$", r"$x=1$")
        self.assertEqual([item["key"] for item in result["signals"]],
                         ["mark", "signature", "skeleton", "numbers", "answer"])
        for item in result["signals"]:
            self.assertIsInstance(item["hit"], bool)
            self.assertTrue(item["detail"])
            self.assertEqual(item["label"], bank_dedupe.SIGNAL_LABELS[item["key"]])
        self.assertEqual(bank_dedupe.CALIBRATED_TOTAL,
                         sum(item["weight"] for item in result["signals"] if item["key"] != "mark"))

    def test_03_percent_stays_inside_the_level_band(self) -> None:
        result = self._pair()
        level = result["level"]
        self.assertGreaterEqual(result["percent"], bank_dedupe.LEVEL_FLOOR[level])
        self.assertLessEqual(result["percent"], bank_dedupe.LEVEL_CEILING[level])

    def test_04_very_similar_band_stays_below_90(self) -> None:
        # 签名差一个上标位置（x²y vs xy²）→ 只能落到「较像」，档位区间 55~69
        result = bank_dedupe.confidence("已知 $x^2y$，则下列正确的是",
                                        r"已知 $a=\frac{2}{2}$，则下列正确的是")
        self.assertEqual(result["level"], "fairly_similar")
        self.assertLess(result["percent"], 90)
        self.assertEqual(result["label"], "较像")

    def test_04b_signature_equal_plus_skeleton_is_very_similar(self) -> None:
        # 同一道题的两种打法（\( \) 定界符 + \dfrac）：签名全等 ＋ 骨架 100% ⇒ 「很像」。
        # 「很像」这一档就是旧 0.92 那一档（判据 2.6）——命中线不再另设。
        result = bank_dedupe.confidence(r"已知 \(a=\dfrac{1}{2}\)，则下列正确的是",
                                        r"已知 $a=\frac{1}{2}$，则下列正确的是")
        self.assertTrue(result["signature_equal"], msg=str(result["signals"]))
        self.assertEqual(result["level"], "very_similar")
        self.assertEqual(result["label"], "很像")
        self.assertLess(result["percent"], 90)
        self.assertTrue(result["numbers_equal"])

    def test_04d_decimal_vs_fraction_stays_below_very_similar(self) -> None:
        # 判据 2.4 的另一面：0.5 与 \frac{1}{2} 语义相同但签名不同，只能落「较像」，
        # 靠宽档进候选、由老师肉眼定——不许为它偷偷加语义规则。
        result = bank_dedupe.confidence("已知 $a=0.5$，则下列正确的是",
                                        r"已知 $a=\frac{1}{2}$，则下列正确的是")
        self.assertFalse(result["signature_equal"])
        self.assertEqual(result["level"], "fairly_similar")
        self.assertTrue(bank_dedupe.accepts(result["level"], "loose"))
        self.assertFalse(bank_dedupe.accepts(result["level"], "standard"))

    def test_04c_equal_raw_numbers_keep_the_signature_apart(self) -> None:
        # x²y 与 xy²：数字集合相同，但写法顺序不同 ⇒ 签名必须分开（判据 2.2 的反面）
        result = bank_dedupe.confidence("已知 $x^2y$，则下列正确的是",
                                        r"已知 $a=\frac{2}{2}$，则下列正确的是")
        self.assertFalse(result["signature_equal"])
        self.assertEqual(result["level"], "fairly_similar")

    def test_05_wording_never_claims_same_question(self) -> None:
        # 「98% 是同一道题」这种话不许出现在任何对外字段里。note 是唯一一句**否定式**
        # 免责说明，按整句断言；别拿 repr 找「同一道」子串——那会命中它自己。
        for pair in [(r"已知 $a=1$，则 $b$ 的值为", r"已知 $a=2$，则 $b$ 的值为"),
                     (r"设 $A\cap B$，则", r"设 $A\cup B$，则")]:
            result = bank_dedupe.confidence(pair[0], pair[1])
            # 只查**会被前端直接拼进文案**的那几个字段：信号明细里带我们自己写的
            # 「四要素指纹全等」这类标签，拿整包 repr 找子串会命中自己的措辞。
            outward = " ".join(str(result[key]) for key in ("level", "label", "percent"))
            for banned in ("同一道", "98%"):
                self.assertNotIn(banned, outward)
            self.assertLessEqual(result["percent"], bank_dedupe.LEVEL_CEILING[result["level"]])
        self.assertIn("不表示是不是同一道题", bank_dedupe.confidence("甲", "乙")["note"])
        self.assertIn("老师", bank_dedupe.confidence("甲", "乙")["note"])

    def test_06_missing_answer_is_not_read_as_mismatch(self) -> None:
        result = bank_dedupe.confidence("已知 $a=1$", "已知 $a=1$", answer_state=None)
        answer = [item for item in result["signals"] if item["key"] == "answer"][0]
        self.assertFalse(answer["hit"])
        self.assertIn("没写答案", answer["detail"])

    def test_07_mark_equal_is_certain_and_percent_100(self) -> None:
        result = bank_dedupe.confidence("任意题干", "完全不同的题干", mark_equal=True)
        self.assertEqual((result["level"], result["label"], result["percent"]),
                         ("certain", "确定", 100))

    def test_08_below_every_threshold_is_no_level(self) -> None:
        result = bank_dedupe.confidence("已知 $a=1$，则下列正确的是",
                                       "函数 $f(x)$ 的最小正周期为")
        self.assertEqual((result["level"], result["label"], result["percent"]), ("", "", 0))
        self.assertFalse(bank_dedupe.accepts(result["level"], "loose"))

    def test_09_labels_are_the_four_words(self) -> None:
        self.assertEqual([bank_dedupe.LEVEL_LABELS[level] for level in bank_dedupe.LEVEL_ORDER],
                         ["确定", "很像", "较像", "可能"])
        self.assertEqual(bank_dedupe.TIER_LABELS, {"strict": "严", "standard": "标准", "loose": "宽"})


class SingleRulerTest(unittest.TestCase):
    """判据 2.6：旧 0.92 口径并进新档位，全库只留一把尺子。"""

    def test_01_very_similar_level_is_the_old_threshold(self) -> None:
        self.assertEqual(bank_dedupe.SKELETON_LEVELS["very_similar"], 0.92)
        self.assertEqual(pending_dedupe.HIGH_SIMILARITY,
                         bank_dedupe.SKELETON_LEVELS["very_similar"])

    def test_02_no_second_ruler_in_pending_dedupe(self) -> None:
        # 相似比只能来自底座那一把尺子；这里再算一遍就是第二把
        self.assertEqual(pending_dedupe.similarity("已知则", "已知则值"),
                         bank_dedupe.text_similarity("已知则", "已知则值"))
        self.assertEqual(pending_dedupe.similarity("已知则", ""), 0.0)
        self.assertNotIn("difflib", vars(pending_dedupe))

    def test_03_tiers_and_default_wide(self) -> None:
        self.assertEqual(bank_dedupe.TIER_LEVELS["strict"], ("certain",))
        self.assertEqual(bank_dedupe.TIER_LEVELS["standard"], ("certain", "very_similar"))
        self.assertEqual(bank_dedupe.TIER_LEVELS["loose"], bank_dedupe.LEVEL_ORDER)
        self.assertEqual(bank_dedupe.DEFAULT_TIER, "loose")
        self.assertTrue(bank_dedupe.accepts("possible", None))
        self.assertTrue(bank_dedupe.accepts("possible", "unknown-tier"))

    def test_04_level_rank_orders_and_puts_empty_last(self) -> None:
        ranks = [bank_dedupe.level_rank(level) for level in bank_dedupe.LEVEL_ORDER]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(bank_dedupe.level_rank(""), len(bank_dedupe.LEVEL_ORDER))


class FingerprintRulerTest(unittest.TestCase):
    """判据 2.6 前半：指纹不再拿原始源码算，旧归一口径不许回退。"""

    def test_01_same_meaning_two_styles_share_fingerprint(self) -> None:
        left = bank_dedupe.fingerprint("choice", r"求 \(\dfrac{1}{2}\) 的值", [])
        right = bank_dedupe.fingerprint("choice", r"求 $\frac{1}{2}$ 的值 ", [])
        self.assertEqual(left, right)

    def test_02_one_symbol_apart_splits_the_fingerprint(self) -> None:
        left = bank_dedupe.fingerprint("choice", r"$A\cap B$", [])
        right = bank_dedupe.fingerprint("choice", r"$A\cup B$", [])
        self.assertNotEqual(left, right)

    def test_03_legacy_punctuation_ruler_still_collapses(self) -> None:
        self.assertEqual(bank_dedupe.normalize_text("已知，$x=1$。"),
                         bank_dedupe.normalize_text("已知 $x = 1$"))

    def test_04_factorial_and_brackets_are_still_never_dropped(self) -> None:
        # 旧底线（ASCII 标点不吞）在比较归一之后仍然成立
        self.assertNotEqual(bank_dedupe.normalize_text("$3!$"), bank_dedupe.normalize_text("$3$"))
        self.assertNotEqual(bank_dedupe.normalize_text(r"$\{a,b\}$"),
                            bank_dedupe.normalize_text(r"$ab$"))

    def test_05_options_and_images_still_compose_the_mark(self) -> None:
        base = bank_dedupe.fingerprint("choice", "题干", [{"key": "A", "content": "1"}])
        shuffled = bank_dedupe.fingerprint("choice", "题干",
                                          [{"key": "B", "content": "1"},
                                           {"key": "A", "content": "2"}])
        self.assertNotEqual(base, shuffled)
        with_image = bank_dedupe.fingerprint("choice", "题干", [],
                                             '[{"key":"core-bank.images","images":[{"uri":"a.png"}]}]')
        self.assertNotEqual(base, with_image)


if __name__ == "__main__":
    unittest.main()
