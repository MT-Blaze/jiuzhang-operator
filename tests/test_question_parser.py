"""录题清洗与解析（app/core/question_parser.py）契约测试：军令 #13 任务 4。

覆盖四块纯逻辑：LaTeX 定界符归一、选项剥离、填空答案提取、题干体检。
全部是字符串进/字符串出的纯函数，不碰数据库与网络。

运行：``.venv/Scripts/python.exe -m unittest tests.test_question_parser``
"""

from __future__ import annotations

import unittest

from app.core.question_parser import (
    clean_question,
    count_blanks,
    extract_answer,
    normalize_latex,
    parse_question,
    sanity_check,
    split_options,
)


class NormalizeLatexTest(unittest.TestCase):
    def test_01_backslash_delimiters_become_dollars(self) -> None:
        self.assertEqual(normalize_latex(r"求 \(x^2\) 的值"), "求 $x^2$ 的值")
        self.assertEqual(normalize_latex(r"\[x^2-1=0\]"), "$$x^2-1=0$$")

    def test_02_line_break_spacing_is_not_mistaken_for_display_math(self) -> None:
        source = r"$\begin{cases}a\\[1ex]b\end{cases}$"
        self.assertEqual(normalize_latex(source), source)

    def test_03_equivalent_symbols_unify_inside_math_only(self) -> None:
        self.assertEqual(normalize_latex(r"$\dfrac{1}{2}\leq x$"), r"$\frac{1}{2}\le x$")
        self.assertEqual(normalize_latex(r"$\tfrac{3}{4}\geqslant y$"), r"$\frac{3}{4}\ge y$")
        self.assertEqual(normalize_latex(r"$a\neq b$"), r"$a\ne b$")
        # 正文里的同名字符串不是公式，不许改写
        self.assertEqual(normalize_latex(r"写作 \leq 的读法"), r"写作 \leq 的读法")

    def test_04_whitespace_and_invisible_characters_are_tidied(self) -> None:
        self.assertEqual(normalize_latex("  a\r\nb\u200b  \n\n\n\nc  "), "a\nb\n\nc")

    def test_05_normalization_is_idempotent(self) -> None:
        source = r"解 \(x\)：\[x=\dfrac{1}{2}\]"
        once = normalize_latex(source)
        self.assertEqual(normalize_latex(once), once)

    def test_06_non_string_input_is_tolerated(self) -> None:
        self.assertEqual(normalize_latex(None), "")  # type: ignore[arg-type]


class SplitOptionsTest(unittest.TestCase):
    def test_01_line_based_options_are_split_off(self) -> None:
        text = "下列各数中最大的一个是（  ）\nA. 1\nB. 2\nC. 3\nD. 4"
        result = split_options(text)
        self.assertTrue(result["split"])
        self.assertEqual(result["stem"], "下列各数中最大的一个是（  ）")
        self.assertEqual([item["label"] for item in result["options"]], ["A", "B", "C", "D"])
        self.assertEqual(result["options"][2]["text"], "3")

    def test_02_inline_options_are_split_off(self) -> None:
        result = split_options("选一个：A. 甲  B. 乙  C. 丙")
        self.assertTrue(result["split"])
        self.assertEqual(result["stem"], "选一个：")
        self.assertEqual([item["text"] for item in result["options"]], ["甲", "乙", "丙"])

    def test_03_full_width_labels_and_parens_are_recognized(self) -> None:
        text = "题干\nＡ．甲\nＢ．乙\nＣ．丙"
        result = split_options(text)
        self.assertTrue(result["split"])
        self.assertEqual([item["label"] for item in result["options"]], ["A", "B", "C"])

        paren = "题干\n（A）甲\n（B）乙"
        self.assertTrue(split_options(paren)["split"])

    def test_04_skipped_or_duplicated_labels_are_not_options(self) -> None:
        text = "题干\nA. 甲\nC. 丙"
        result = split_options(text)
        self.assertFalse(result["split"])
        self.assertEqual(result["options"], [])
        self.assertIn("A. 甲", result["stem"])

    def test_05_single_option_is_not_a_choice_list(self) -> None:
        result = split_options("题干\nA. 只有一个")
        self.assertFalse(result["split"])

    def test_06_markers_inside_math_do_not_count(self) -> None:
        text = "已知 $A. B.$ 是集合，求元素个数"
        result = split_options(text)
        self.assertFalse(result["split"])

    def test_07_explanation_after_options_is_not_swallowed(self) -> None:
        text = "题干\nA. 甲\nB. 乙\n解析：因为甲更小"
        result = split_options(text)
        self.assertEqual(result["options"][1]["text"], "乙")
        self.assertNotIn("解析", result["options"][1]["text"])

    def test_08_wrapped_option_text_keeps_its_second_line(self) -> None:
        text = "题干\nA. 甲说法\nB. 乙说法\n折叠过来的补充"
        result = split_options(text)
        self.assertTrue(result["split"])
        self.assertIn("折叠过来的补充", result["options"][1]["text"])


class ExtractAnswerTest(unittest.TestCase):
    def test_01_bracket_label(self) -> None:
        result = extract_answer("题干\n【答案】42\n【解析】略")
        self.assertEqual(result["answer"], "42")
        self.assertTrue(result["matched"])

    def test_02_colon_label_keeps_latex(self) -> None:
        result = extract_answer("填空题\n答案：$x=1$")
        self.assertEqual(result["answer"], "$x=1$")
        self.assertEqual(result["body"], "填空题")

    def test_03_answer_stops_before_explanation(self) -> None:
        result = extract_answer("题干\n答案：3【解析】因为……")
        self.assertEqual(result["answer"], "3")

    def test_04_short_label_at_line_start(self) -> None:
        result = extract_answer("题干\n答：乙")
        self.assertEqual(result["answer"], "乙")

    def test_05_missing_answer_leaves_body_intact(self) -> None:
        result = extract_answer("题干没有答案")
        self.assertEqual(result["answer"], "")
        self.assertFalse(result["matched"])
        self.assertEqual(result["body"], "题干没有答案")

    def test_06_empty_answer_label_is_ignored(self) -> None:
        result = extract_answer("题干\n答案：\n")
        self.assertEqual(result["answer"], "")


class CountBlanksTest(unittest.TestCase):
    def test_01_underlines_and_underline_macro(self) -> None:
        self.assertEqual(count_blanks("甲是____，乙是____"), 2)
        self.assertEqual(count_blanks(r"甲是\underline{}"), 1)
        self.assertEqual(count_blanks("没有空"), 0)


class SanityCheckTest(unittest.TestCase):
    def codes(self, stem: str, options=None, answer: str = "") -> list[str]:
        return [item["code"] for item in sanity_check(stem, options, answer)]

    def test_01_clean_question_has_no_issue(self) -> None:
        self.assertEqual(self.codes(r"求 $x^2$ 的值"), [])

    def test_02_empty_stem(self) -> None:
        self.assertEqual(self.codes("   "), ["empty_stem"])

    def test_03_unbalanced_math(self) -> None:
        self.assertIn("unbalanced_math", self.codes("求 $x^2 的值"))

    def test_04_unbalanced_braces_inside_math(self) -> None:
        self.assertIn("unbalanced_braces", self.codes(r"$\frac{1}{2$"))

    def test_05_left_right_mismatch(self) -> None:
        self.assertIn("unbalanced_left_right", self.codes(r"$\left( x + 1$"))

    def test_06_unmatched_environment(self) -> None:
        self.assertIn("unmatched_environment", self.codes(r"$\begin{cases} x$"))

    def test_07_stray_html(self) -> None:
        self.assertIn("stray_html", self.codes("题干<script>alert(1)</script>"))

    def test_08_remote_image_is_rejected(self) -> None:
        self.assertIn("remote_asset", self.codes(r"$\includegraphics{https://a.test/x.png}$"))

    def test_09_option_problems(self) -> None:
        self.assertIn("option_labels", self.codes("题干", [{"label": "A", "text": "甲"}, {"label": "A", "text": "乙"}]))
        self.assertIn("empty_option", self.codes("题干", [{"label": "A", "text": "甲"}, {"label": "B", "text": " "}]))

    def test_10_answer_html(self) -> None:
        self.assertIn("stray_html_answer", self.codes("题干", None, "<b>3</b>"))

    def test_11_asset_scheme_is_a_local_asset_not_a_remote_url(self) -> None:
        self.assertNotIn("remote_asset", self.codes(r"$\includegraphics{asset://img_abc123}$"))
        self.assertNotIn("remote_asset", self.codes("图：![x](/static/uploads/a.png)"))
        self.assertIn("remote_asset", self.codes("图：![x](//cdn.test/a.png)"))


class CleanQuestionTest(unittest.TestCase):
    def document(self, **overrides) -> dict:
        document = {
            "schema_version": "2.0",
            "type": "single_choice",
            "stem": r"已知 \(x^2=1\)，则 $x$ 为（　　）",
            "options": [
                {"key": "A", "content": r"\(\dfrac{1}{2}\)"},
                {"key": "B", "content": "$1$"},
            ],
            "answer": {"kind": "choice", "choice_keys": ["B"], "final": "B"},
            "solution": r"由 \[x^2-1=0\] 得 $x=\pm1$。",
        }
        document.update(overrides)
        return document

    def test_01_every_text_field_is_normalized(self) -> None:
        cleaned, issues = clean_question(self.document())
        self.assertEqual(cleaned["stem"], "已知 $x^2=1$，则 $x$ 为（　　）")
        self.assertEqual(cleaned["options"][0]["content"], r"$\frac{1}{2}$")
        self.assertEqual(cleaned["solution"], "由 $$x^2-1=0$$ 得 $x=\\pm1$。")
        self.assertEqual(issues, [])

    def test_02_source_document_is_not_mutated(self) -> None:
        source = self.document()
        clean_question(source)
        self.assertIn(r"\(\dfrac{1}{2}\)", source["options"][0]["content"])

    def test_03_solution_issue_carries_its_own_prefix(self) -> None:
        _cleaned, issues = clean_question(self.document(solution=r"由 $\frac{1}{2$ 得"))
        self.assertEqual([item["code"] for item in issues], ["solution_unbalanced_braces"])

    def test_04_answer_html_is_reported(self) -> None:
        document = self.document()
        document["answer"] = {"kind": "text", "content": "<b>1</b>", "final": "1"}
        _cleaned, issues = clean_question(document)
        self.assertIn("stray_html_answer", [item["code"] for item in issues])

    def test_05_non_document_is_reported(self) -> None:
        cleaned, issues = clean_question("不是对象")  # type: ignore[arg-type]
        self.assertEqual(cleaned, "不是对象")
        self.assertEqual([item["code"] for item in issues], ["invalid_document"])


class ParseQuestionTest(unittest.TestCase):
    def test_01_end_to_end_pipeline(self) -> None:
        source = (
            "已知 \\(x^2-1=0\\)，下列哪个是正根？\n"
            "A. -1\nB. 1\nC. 0\nD. 2\n"
            "【答案】B\n【解析】略"
        )
        result = parse_question(source)
        self.assertEqual(result["stem"], "已知 $x^2-1=0$，下列哪个是正根？")
        self.assertEqual([item["label"] for item in result["options"]], ["A", "B", "C", "D"])
        self.assertEqual(result["answer"], "B")
        self.assertEqual(result["issues"], [])

    def test_02_fill_in_question_counts_blanks(self) -> None:
        result = parse_question("甲是____，乙是____。\n答案：3、4")
        self.assertEqual(result["blanks"], 2)
        self.assertEqual(result["answer"], "3、4")
        self.assertEqual(result["options"], [])

    def test_03_dirty_input_is_reported_not_repaired(self) -> None:
        result = parse_question("求 $x 的值")
        self.assertIn("unbalanced_math", [item["code"] for item in result["issues"]])


if __name__ == "__main__":
    unittest.main()
