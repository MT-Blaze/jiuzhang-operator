"""扫描卷文字 → Markdown + LaTeX（纯函数，无 IO）。

钉住五条：

- Unicode 数学字母折回 ASCII／LaTeX 命令（``𝐴`` → ``A``、``𝜋`` → ``\\pi``）；
- 公式包进 ``$...$``，中文正文原样；孤零零的数字不冒充公式；
- 集合花括号转义成 ``\\{ \\}``，上下标分组 ``x^{2}`` 原样保留；
- 题块文字能拆出题干、选项、答案与解析，题号只留在来源关系里；
- 抠不出题干就交空，绝不编。

运行：``.venv/Scripts/python.exe -m unittest tests.test_scan_text``
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import scan_text  # noqa: E402


class TextToLatexTest(unittest.TestCase):
    def test_01_unicode_math_letters_become_latex(self) -> None:
        """集合题：数学斜体字母折成 LaTeX，集合花括号转义，中文一个字不动。"""
        text = "已知集合 𝐴 = {𝑥 ∣ 𝑥 < 𝜋}，𝐵 = {𝑦 ∣ 𝑦 > 2}"
        self.assertEqual(
            scan_text.text_to_latex(text),
            r"已知集合 $A = \{x \mid x < \pi\}$，$B = \{y \mid y > 2\}$")

    def test_02_control_words_keep_a_word_boundary(self) -> None:
        """``\\forall`` 后面紧跟变量时不许粘成 ``\\forallm``。"""
        out = scan_text.text_to_latex("命题 𝑝 ∶ ∀𝑚 ⩾ 1, 𝑚^{3} > 𝑚")
        self.assertIn(r"\forall m \ge 1", out)
        self.assertIn("m^{3} > m", out)
        self.assertNotIn(r"\forallm", out)

    def test_03_script_groups_survive_set_braces_are_escaped(self) -> None:
        """扫描层补的 ``^{2}`` 原样保留；正文里的 ``{x}`` 当集合括号转义。"""
        out = scan_text.text_to_latex("𝑥^{2} 与 {𝑥}")
        self.assertIn("x^{2}", out)
        self.assertIn(r"\{x\}", out)
        self.assertNotIn(r"\^{", out)

    def test_04_minus_variants_join_one_math_run(self) -> None:
        """U+2212 减号也是公式字符，不该把一段公式拦腰截断。"""
        self.assertEqual(scan_text.text_to_latex("|𝑥 − 𝑦| ⩾ 2"),
                         r"$|x - y| \ge 2$")

    def test_05_lone_number_is_not_a_formula(self) -> None:
        """「共 8 小题」里的 8 是正文数字，不能包成公式。"""
        out = scan_text.text_to_latex("共 8 小题")
        self.assertEqual(out, "共 8 小题")
        self.assertNotIn("$8$", out)

    def test_06_sqrt_takes_letters_and_numbers(self) -> None:
        self.assertEqual(scan_text.text_to_latex("√2 + √𝑎"),
                         r"$\sqrt{2} + \sqrt{a}$")


class ParseScanTextTest(unittest.TestCase):
    def test_01_options_are_split_from_the_stem(self) -> None:
        parsed = scan_text.parse_scan_text(
            "1. 已知集合 A\nA. 甲\nB. 乙\nC. 丙\nD. 丁")
        self.assertEqual(parsed["stem"], "已知集合 A")
        self.assertEqual([item["key"] for item in parsed["options"]],
                         ["A", "B", "C", "D"])
        self.assertEqual(parsed["options"][0]["content"], "甲")

    def test_02_answer_and_solution_are_extracted(self) -> None:
        parsed = scan_text.parse_scan_text(
            "1. 求 x 的值。\n答案：2\n解析：移项即可")
        self.assertEqual(parsed["answer"], "2")
        self.assertEqual(parsed["solution"], "移项即可")
        self.assertEqual(parsed["stem"], "求 x 的值。")

    def test_03_section_heading_at_the_tail_is_cut(self) -> None:
        """题块尾巴常粘着下一大节说明，切题时一并去掉。"""
        parsed = scan_text.parse_scan_text(
            "1. 第一题\n二、多选题：本题共 3 小题")
        self.assertEqual(parsed["stem"], "第一题")

    def test_04_empty_text_stays_empty(self) -> None:
        parsed = scan_text.parse_scan_text("   \n ")
        self.assertEqual(parsed["stem"], "")
        self.assertEqual(parsed["options"], [])
        self.assertEqual(parsed["answer"], "")


if __name__ == "__main__":
    unittest.main()
