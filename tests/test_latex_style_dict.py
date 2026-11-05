"""军令 #32 · S1：LaTeX 写法字典与两把尺子（底座纯函数）。

钉六件事，逐条对验收判据 1.1–1.6：

- 1.1 字典合并项清洗后**逐字相等**（\\dfrac/\\frac、\\leq/\\le、x^2/x^{2}、
  \\frac12/\\frac{1}{2}、三种减号）；
- 1.2 不合并项清洗后**逐字不相等**（\\times 与 \\cdot、\\{\\} 与 () 与 []）；
- 1.3 按命令切词安全（\\left 不当 \\le 改坏、\\text{} 内汉字不动、cases 不换 array）；
- 1.4 幂等（洗一遍 == 洗十遍）；
- 1.5 两把尺子（写库清洗不动 \\left\\right 与间距；比对归一忽略它们且不改原文）；
- 1.6 与 #31 同源（编辑器清洗端点与本字典同一张表，规则表不在本地留一份）。

每条规则都配正例与反例；不认识的一律原样保留，只把命令名记进返回值，
不落盘、不打印、不进日志（硬条件③）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_latex_style_dict``
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import io
import unittest

from app.api.agents import CleanLatexRequest, agent_clean_latex
from app.core import latex_style_dict, question_parser


def write(text: str) -> str:
    """写库清洗后的正文。"""
    return latex_style_dict.clean_for_write(text)["text"]


def compare(text: str) -> str:
    """比对归一后的指纹输入串。"""
    return latex_style_dict.normalize_for_compare(text)["text"]


class MergedFormsTest(unittest.TestCase):
    """判据 1.1：字典里的合并项清洗后逐字相等。"""

    def test_01_dfrac_tfrac_become_frac(self) -> None:
        self.assertEqual(write(r"$\dfrac{1}{2}$"), r"$\frac{1}{2}$")
        self.assertEqual(write(r"$\tfrac{3}{4}$"), r"$\frac{3}{4}$")
        self.assertEqual(write(r"$\dfrac{1}{2}$"), write(r"$\frac{1}{2}$"))
        self.assertEqual(write(r"$\tfrac{3}{4}$"), write(r"$\frac{3}{4}$"))

    def test_02_relation_aliases(self) -> None:
        for source in (r"$a\leq b$", r"$a\leqslant b$", r"$a\le b$"):
            self.assertEqual(write(source), r"$a\le b$", source)
        for source in (r"$a\geq b$", r"$a\geqslant b$", r"$a\ge b$"):
            self.assertEqual(write(source), r"$a\ge b$", source)
        self.assertEqual(write(r"$a\neq b$"), r"$a\ne b$")
        self.assertEqual(write(r"$a\neq b$"), write(r"$a\ne b$"))

    def test_03_scripts_get_explicit_braces(self) -> None:
        self.assertEqual(write(r"$x^2$"), r"$x^{2}$")
        self.assertEqual(write(r"$x^2$"), write(r"$x^{2}$"))
        self.assertEqual(write(r"$a_1$"), r"$a_{1}$")
        self.assertEqual(write(r"$a_1$"), write(r"$a_{1}$"))

    def test_04_frac_without_braces(self) -> None:
        self.assertEqual(write(r"$\frac12$"), r"$\frac{1}{2}$")
        self.assertEqual(write(r"$\frac 12$"), r"$\frac{1}{2}$")
        self.assertEqual(write(r"$\frac{1}2$"), r"$\frac{1}{2}$")
        self.assertEqual(write(r"$\dfrac12$"), r"$\frac{1}{2}$")
        self.assertEqual(write(r"$\frac12$"), write(r"$\frac{1}{2}$"))

    def test_05_three_minus_signs_collapse(self) -> None:
        for variant in ("−", "－", "‐"):
            self.assertEqual(write("$5%s2$" % variant), r"$5-2$", variant)
        self.assertEqual(write(r"$5-2$"), r"$5-2$")          # 反例：半角不动
        self.assertEqual(write("$5%s2$" % "−"), write(r"$5-2$"))

    def test_06_rules_are_reported_per_hit(self) -> None:
        result = latex_style_dict.clean_for_write(r"$\leqslant x^2$")
        self.assertEqual(result["rules"], ["symbols", "script_braces"])
        self.assertEqual(latex_style_dict.clean_for_write(r"$x^{2}$")["rules"], [])
        self.assertFalse(latex_style_dict.clean_for_write(r"$x^{2}$")["changed"])

    def test_07_adjacent_scripted_vars_get_thin_space(self) -> None:
        self.assertEqual(write(r"$m_1 m_2$"), r"$m_{1}\,m_{2}$")
        self.assertEqual(write(r"$m_1m_2$"), r"$m_{1}\,m_{2}$")
        self.assertEqual(write(r"$a_1 a_2 a_3$"), r"$a_{1}\,a_{2}\,a_{3}$")
        self.assertEqual(write(r"$a_1\,a_2$"), r"$a_{1}\,a_{2}$", "已有细空格不重复补")
        self.assertEqual(write(r"$m_1, m_2$"), r"$m_{1}, m_{2}$", "逗号隔开不动")
        self.assertEqual(write(r"$m_1^{2}m_2$"), r"$m_{1}^{2}m_{2}$", "幂次隔开不动")
        self.assertEqual(write(r"$\text{m_{1} m_{2}}$"), r"$\text{m_{1} m_{2}}$", "文字组不动")


class NotMergedTest(unittest.TestCase):
    """判据 1.2：长得像但含义不同的写法绝不合并。"""

    def test_01_times_and_cdot_stay_different(self) -> None:
        self.assertEqual(write(r"$A\times B$"), r"$A\times B$")
        self.assertEqual(write(r"$A\cdot B$"), r"$A\cdot B$")
        self.assertNotEqual(write(r"$A\times B$"), write(r"$A\cdot B$"))
        self.assertNotEqual(compare(r"$A\times B$"), compare(r"$A\cdot B$"))

    def test_02_brace_systems_stay_different(self) -> None:
        cases = [r"$\{1,2\}$", r"$(1,2)$", r"$[1,2]$"]
        cleaned = [write(source) for source in cases]
        self.assertEqual(cleaned, cases)
        self.assertEqual(len(set(cleaned)), 3, "集合／开区间／闭区间必须分得开")
        self.assertEqual(len(set(compare(source) for source in cases)), 3)

    def test_03_cap_and_cup_stay_different(self) -> None:
        self.assertNotEqual(write(r"$A\cap B$"), write(r"$A\cup B$"))
        self.assertNotEqual(compare(r"$A\cap B$"), compare(r"$A\cup B$"))


class TokenizingSafetyTest(unittest.TestCase):
    """判据 1.3：按 LaTeX 命令切词改写，不做字符串替换。"""

    def test_01_left_right_are_not_read_as_le(self) -> None:
        source = r"$\left(0,1\right)$"
        self.assertEqual(write(source), source)
        self.assertNotIn(r"\le(ft", write(source), "切词失败就会把 \\left 劈成 \\le(ft")
        self.assertEqual(write(r"$\left\{x\right\}$"), r"$\left\{x\right\}$")
        self.assertEqual(compare(r"$\left(0,1\right)$"), r"$(0,1)$")

    def test_02_text_group_keeps_chinese(self) -> None:
        self.assertEqual(write(r"$\text{最大值}$"), r"$\text{最大值}$")
        self.assertEqual(write(r"$\text{a\leq b}$"), r"$\text{a\leq b}$")
        self.assertEqual(write(r"写作 \leq 的读法"), r"写作 \leq 的读法")

    def test_03_cases_and_array_are_not_swapped(self) -> None:
        source = r"$\begin{cases}x>0\\y<0\end{cases}$"
        self.assertEqual(write(source), r"$\begin{cases}x>0\\y<0\end{cases}$")
        self.assertNotIn("array", write(source))
        self.assertEqual(write(r"$\begin{tabular}{cc}甲&乙\end{tabular}$"),
                         r"$\begin{tabular}{cc}甲&乙\end{tabular}$")

    def test_04_line_break_spacing_is_not_a_delimiter(self) -> None:
        source = r"$\begin{cases}a\\[1ex]b\end{cases}$"
        self.assertEqual(write(source), source)
        self.assertEqual(latex_style_dict.clean_for_write(source)["rules"], [])

    def test_05_unrecognized_command_is_untouched_and_listed(self) -> None:
        source = r"$\myunknownop{x}$"
        result = latex_style_dict.clean_for_write(source)
        self.assertEqual(result["text"], source)
        self.assertFalse(result["changed"])
        self.assertEqual(result["unknown"], ["myunknownop"])
        self.assertEqual(compare(source), source)

    def test_06_scripts_only_brace_single_alnum_atoms(self) -> None:
        self.assertEqual(write(r"$x^{-1}$"), r"$x^{-1}$")
        self.assertEqual(write(r"$x^\alpha$"), r"$x^\alpha$")
        self.assertEqual(write(r"$x^{10}$"), r"$x^{10}$")

    def test_07_stdout_stays_silent(self) -> None:
        """unknown 只进返回值：不许 print、不许写日志。"""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            latex_style_dict.clean_for_write(r"$\myunknownop{x}^2$")
            latex_style_dict.normalize_for_compare(r"$\myunknownop{x}$")
        self.assertEqual(buffer.getvalue(), "")


class IdempotentTest(unittest.TestCase):
    """判据 1.4：洗一遍与洗十遍逐字相同。"""

    SAMPLES = [
        r"求 \(\dfrac{1}{2}\) 与 \[x^2-1=0\] 的值",
        r"$\left\{\begin{array}{l}x\geqslant 0\\y\leq 1\end{array}\right.$",
        r"$\frac12$ 与 $a_1$ 和 $5-2$ 以及 $A\cdot B$",
        "已知 $x^2$，且 \\fillin 处填 $\\text{最小值}$",
        r"$\displaystyle \frac{2}3 \leqslant x$",
        r"$a_1 a_2 a_3$ 与 $b_1, b_2$ 以及 $\text{m_{1} m_{2}}$",
    ]

    def assert_stable(self, clean, text: str) -> None:
        once = clean(text)
        twice = clean(once)
        self.assertEqual(twice, once, text)
        ten = text
        for _ in range(10):
            ten = clean(ten)
        self.assertEqual(ten, once, text)

    def test_01_clean_for_write_is_idempotent(self) -> None:
        for source in self.SAMPLES:
            with self.subTest(source=source):
                self.assert_stable(write, source)

    def test_02_normalize_for_compare_is_idempotent(self) -> None:
        for source in self.SAMPLES:
            with self.subTest(source=source):
                self.assert_stable(compare, source)

    def test_03_host_cleaner_is_idempotent(self) -> None:
        for source in self.SAMPLES:
            with self.subTest(source=source):
                once = question_parser.clean_dirty_latex(source)["text"]
                twice = question_parser.clean_dirty_latex(once)
                self.assertEqual(twice["text"], once)
                self.assertFalse(twice["changed"])


class TwoRulersTest(unittest.TestCase):
    """判据 1.5：写库清洗保守，比对归一才把排版当透明。"""

    SOURCE = r"$\left(\dfrac{1}{2}\,x \right)$"

    def test_01_write_keeps_left_right_and_spacing(self) -> None:
        self.assertEqual(write(self.SOURCE), r"$\left(\frac{1}{2}\,x \right)$")
        self.assertEqual(write(r"$x\quad y$"), r"$x\quad y$")
        self.assertEqual(write(r"$a\ b$"), r"$a\ b$")

    def test_02_compare_ignores_layout_but_differs_from_write(self) -> None:
        self.assertEqual(compare(self.SOURCE), r"$(\frac{1}{2} x)$")
        self.assertEqual(compare(r"$x\quad y$"), r"$xy$")
        self.assertEqual(compare(r"$x\quad y$"), compare(r"$xy$"), "间距在比对态是透明的")
        self.assertEqual(compare(r"$a\le\quad b$"), r"$a\le b$", "但命令边界不是")
        self.assertEqual(compare(r"$a\ b$"), r"$ab$")
        self.assertNotEqual(write(self.SOURCE), compare(self.SOURCE))

    def test_03_compare_returns_a_copy_never_the_source(self) -> None:
        source = self.SOURCE
        result = latex_style_dict.normalize_for_compare(source)
        self.assertEqual(source, self.SOURCE, "归一不许动原文")
        self.assertTrue(result["changed"])
        self.assertEqual(latex_style_dict.normalize_for_compare(source)["text"],
                         r"$(\frac{1}{2} x)$")

    def test_03b_spacing_differences_collapse_but_word_bounds_survive(self) -> None:
        self.assertEqual(compare(r"$\frac{1}{2}x$"), compare(r"$\frac{1}{2} x$"))
        self.assertEqual(compare(r"$a\leq b$"), compare(r"$a \leq  b$"))
        self.assertNotEqual(compare(r"$\le x$"), compare(r"$\lex$"),
                            r"空格全抹会把 \le 与 x 粘成假命令 \lex")

    def test_04_both_rulers_share_the_dictionary(self) -> None:
        self.assertEqual(compare(r"$\leqslant x^2$"), r"$\le x^{2}$")
        self.assertEqual(compare(r"$\leqslant x^2$"), write(r"$\leqslant x^2$"))
        self.assertEqual(latex_style_dict.normalize_for_compare(None)["text"], "")  # type: ignore[arg-type]


class HostChainTest(unittest.TestCase):
    """判据 1.6 + 雷区：规则表只有一处，normalize_latex 的旧口径一个字不变。"""

    def test_01_normalize_latex_output_is_unchanged(self) -> None:
        self.assertEqual(question_parser.normalize_latex(r"求 \(x^2\) 的值"), "求 $x^2$ 的值")
        self.assertEqual(question_parser.normalize_latex(r"\[x^2-1=0\]"), "$$x^2-1=0$$")
        self.assertEqual(question_parser.normalize_latex(r"$\dfrac{1}{2}\leq x$"),
                         r"$\frac{1}{2}\le x$")
        self.assertEqual(question_parser.normalize_latex(r"$\begin{cases}a\\[1ex]b\end{cases}$"),
                         r"$\begin{cases}a\\[1ex]b\end{cases}$")
        self.assertEqual(question_parser.normalize_latex(None), "")  # type: ignore[arg-type]

    def test_02_parser_keeps_no_local_copy_of_the_rules(self) -> None:
        source = inspect.getsource(question_parser)
        self.assertNotIn('_SYMBOL_MAP', source, "规则表不许在 question_parser 里留第二份")
        self.assertNotIn('"dfrac"', source)
        self.assertNotIn("'leqslant'", source)
        self.assertIn("latex_style_dict", source)

    def test_03_clean_dirty_latex_shape_is_backward_compatible(self) -> None:
        self.assertEqual(
            question_parser.clean_dirty_latex(None),
            {"text": "", "changed": False, "rules": [], "options": []},
        )
        result = question_parser.clean_dirty_latex(r"求 \(x^2\) 与 \(y\leq 1\) 的值")
        self.assertEqual(sorted(result), ["changed", "options", "rules", "text"])
        self.assertEqual(result["text"], r"求 $x^{2}$ 与 $y\le 1$ 的值")
        self.assertIn("script_braces", result["rules"])
        self.assertIn("symbols", result["rules"])

    def test_04_editor_endpoint_shares_the_dictionary(self) -> None:
        """编辑器【清洗当前题 LaTeX】的宿主端点走的就是这张表（不在插件里另抄规则）。"""
        result = asyncio.run(agent_clean_latex(CleanLatexRequest(
            text=r"化简 \(\frac12\)，且 \(x^2\)，并填 \fillin", task_id="t1"
        )))
        self.assertEqual(result["data"]["text"], r"化简 $\frac{1}{2}$，且 $x^{2}$，并填 ＿＿＿＿")
        for rule in ("fillin", "frac_args", "script_braces"):
            self.assertIn(rule, result["data"]["rules"])


    def test_05_exam_source_batch_entry_shares_the_dictionary(self) -> None:
        """判据 1.6 的**批量半边**：``mode="exam_source"`` 走的就是同一张写法字典。

        不钉金串（字典加一条规则不该炸这条），钉三件事：
        ① **差分全等**——``clean_exam_source`` 的输出逐字等于 ``clean_for_write``
          套在 ``normalize_latex`` 之上的组合：批量入口没有自己的规则，只有这张表；
        ② **骨架不拆**——``exam-zh`` 的 ``choices`` 环境与 ``\\fillin`` 原样活着，
          证明它没去复用 ``clean_dirty_latex``（那条会把骨架拆成选项数组）；
        ③ **模块同源**——``question_parser`` 命名空间里的 ``latex_style_dict`` 与
          本用例引的是同一个模块对象，且源码里批量入口点名调用它。
        HTTP 半边（``POST /api/agent/clean_latex`` 的 ``mode="exam_source"``）由
        S6d 载体 3 的 C8 真机取证覆盖（修 URL 后 200），本条不重跑。
        """
        source = (
            "求 $x^2$ 与 \\(y\\leqslant 1\\) 的值。\n"
            r"\begin{choices}" + "\n" + r"\item $\dfrac{1}{2}$" + "\n"
            + r"\item $x^{2}$" + "\n" + r"\end{choices}" + "\n"
            + r"填空：\fillin"
        )
        result = question_parser.clean_exam_source(source)
        chained = latex_style_dict.clean_for_write(
            question_parser.normalize_latex(source))["text"]
        self.assertEqual(result["text"], chained,
                         "批量入口必须等于 normalize_latex + clean_for_write 的复合，不许自带规则")
        self.assertTrue(result["changed"], "别名（\\leqslant/\\dfrac）没洗就不是同一张表")
        self.assertIn("symbols", result["rules"], result)
        # 差分全等已经钉死「规则不许多不许少」，这里不再点名其它规则名。
        self.assertIn(r"\begin{choices}", result["text"], "exam-zh 骨架不许被拆")
        self.assertIn(r"\fillin", result["text"], "\\fillin 在源码态是占位命令，不许换下划线")
        self.assertIn("latex_style_dict.clean_for_write",
                      inspect.getsource(question_parser.clean_exam_source))
        self.assertIs(question_parser.latex_style_dict, latex_style_dict,
                      "批量入口与本字典必须是同一个模块对象")


if __name__ == "__main__":
    unittest.main()
