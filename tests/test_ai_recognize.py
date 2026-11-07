"""单题 AI 识别契约：方案 A 套壳、失败不抛栈、题图路径白名单。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ai_recognize``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))


import asyncio
import base64
import unittest
from unittest import mock

from app.core import ai_center, ai_recognize, wire
from app.core.exam_source import build_exam_source

IMAGE = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode("ascii")
BINDING = ai_center.TaskBinding(
    task="ocr", account_id="acc_0000000000", name="阿里",
    base_url="https://gateway.test/v1", api_key="fixture-key", model="qwen-vl-max",
)


def _chat(content: str):
    async def fake(self, **_kwargs):
        return {"content": content, "mock": False, "model": "qwen-vl-max"}

    return fake


class ExamSourceTest(unittest.TestCase):
    def test_choice_wrapping(self) -> None:
        source = build_exam_source({
            "type": "single_choice", "stem": "已知 $x=1$", "answer": "B",
            "solution": "代入即可", "options": [
                {"key": "A", "content": "0"}, {"key": "B", "content": "$1$"},
            ],
        })
        self.assertIn("\\begin{question}", source)
        self.assertIn("已知 $x=1$（  ）", source)
        self.assertIn("\\begin{choices}", source)
        self.assertIn("  \\item $1$", source)
        self.assertIn("\\begin{solution}\n答案：B\n代入即可\n\\end{solution}", source)

    def test_multi_adds_marker_and_duplicate_bracket_is_merged(self) -> None:
        source = build_exam_source({
            "type": "multiple_choice", "stem": "下列正确的是（  ）（ ）", "answer": "AB",
            "options": [{"key": "A", "content": "a"}, {"key": "B", "content": "b"}],
        })
        self.assertIn("（多选）", source)
        self.assertEqual(source.count("（  ）"), 1)

    def test_solution_uses_problem_env(self) -> None:
        source = build_exam_source({"type": "solution", "stem": "求证 $a=b$", "answer": "略"})
        self.assertTrue(source.startswith("\\begin{problem}"))
        self.assertIn("答案：略", source)

    def test_delimiters_are_normalized_before_wrapping(self) -> None:
        """模型给的 \\(...\\) / \\[...\\] 不许原样落进源码，必须归一成 $ / $$。"""
        source = build_exam_source({
            "type": "solution",
            "stem": r"求 \[x=1\] 的值",
            "answer": r"\(2\)",
            "solution": r"代入 \(x=1\) 得 \(y=2\)。",
        })
        self.assertIn("$$x=1$$", source)
        self.assertIn("答案：$2$", source)
        self.assertIn("代入 $x=1$ 得 $y=2$。", source)
        self.assertNotIn(r"\(", source)
        self.assertNotIn(r"\[", source)


class RecognizeTest(unittest.TestCase):
    def _run(self, content: str, images=None, context=None, task="ocr", binding=BINDING):
        with mock.patch.object(ai_center, "resolve_task", return_value=binding), \
                mock.patch.object(ai_recognize.OpenAICompatibleProvider, "chat_completion",
                                  _chat(content)):
            return asyncio.run(ai_recognize.recognize(images or [IMAGE], context or {}, task))

    def test_01_structured_answer_is_wrapped_by_base_code(self) -> None:
        document = {
            "type": "single_choice",
            "stem": "函数 $f(x)=x^2$ 的导数是（  ）",
            "options": [{"key": "A", "content": "$x$"}, {"key": "B", "content": "$2x$"}],
            "answer": "B",
            "solution": "由幂函数求导公式 $f'(x)=2x$。",
            "question_no": "7",
            "difficulty": "L2",
        }
        result = self._run("```json\n" + wire.dumps(document, ensure_ascii=False) + "\n```")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["question"]["type"], "single_choice")
        self.assertEqual(result["question"]["question_no"], "7")
        self.assertIn("\\begin{question}", result["source"])
        self.assertIn("（  ）", result["source"])
        self.assertIn("\\begin{solution}\n答案：B", result["source"])
        self.assertFalse(result["mock"])

    def test_02_missing_assignment_is_structured_failure(self) -> None:
        empty = ai_center.TaskBinding("ocr", "", "", "", "", "")
        result = self._run("{}", binding=empty)
        self.assertFalse(result["ok"])
        self.assertIn("API 配置", result["detail"])

    def test_03_bad_json_is_reported_not_raised(self) -> None:
        result = self._run("抱歉，我看不清这张图")
        self.assertFalse(result["ok"])
        self.assertIn("JSON", result["detail"])

    def test_04_empty_stem_is_rejected(self) -> None:
        result = self._run(wire.dumps({"stem": "", "type": "solution"}))
        self.assertFalse(result["ok"])
        self.assertIn("题干", result["detail"])

    def test_05_image_path_whitelist(self) -> None:
        result = self._run("{}", images=["/static/pending/../../etc/passwd"])
        self.assertFalse(result["ok"])
        self.assertIn("非法", result["detail"])
        result = self._run("{}", images=["https://evil.test/a.png"])
        self.assertFalse(result["ok"])
        self.assertIn("本地工作区", result["detail"])

    def test_06_no_image_is_rejected_before_network(self) -> None:
        result = self._run("{}", images=[])
        self.assertFalse(result["ok"])
        self.assertIn("题图", result["detail"])

    def test_07_normalizer_infers_type_and_clamps_fields(self) -> None:
        question = ai_recognize.normalize_question(
            {"stem": "填空 $\\fillin$", "options": [], "difficulty": "L9", "answer": ["1", "2"]},
            {"difficulty": "L3", "question_no": "12"},
        )
        self.assertEqual(question["type"], "fill_blank")
        self.assertEqual(question["answer"], "12")
        self.assertEqual(question["difficulty"], "L3")
        self.assertEqual(question["question_no"], "12")

    def test_08_returned_text_is_write_cleaned(self) -> None:
        """识别回来的正文必须过写库清洗：\\( \\) → $，相邻下标变量补 \\,。"""
        document = {
            "type": "solution",
            "stem": r"若 \(m_1 m_2\) 是方程两根，求 \(m_1+m_2\)。",
            "answer": r"\(5\)",
            "solution": r"由韦达定理 \[m_1+m_2=5\] 得证。",
        }
        result = self._run(wire.dumps(document, ensure_ascii=False))
        self.assertTrue(result["ok"], result)
        question = result["question"]
        self.assertEqual(question["stem"], r"若 $m_{1}\,m_{2}$ 是方程两根，求 $m_{1}+m_{2}$。")
        self.assertEqual(question["answer"], "$5$")
        self.assertEqual(question["solution"], r"由韦达定理 $$m_{1}+m_{2}=5$$ 得证。")
        self.assertIn(r"$m_{1}\,m_{2}$", result["source"])
        self.assertNotIn(r"\(", result["source"])
        self.assertNotIn(r"\[", result["source"])


SOLVE_BINDING = ai_center.TaskBinding(
    task="solve", account_id="acc_0000000001", name="解题档",
    base_url="https://gateway.test/v1", api_key="fixture-key", model="qwen-max",
)


class SolveTest(unittest.TestCase):
    """【解析本题】：只补答案与解析，题干与选项原样保留，不需要题图。"""

    def _run(self, content: str, context=None, binding=SOLVE_BINDING):
        with mock.patch.object(ai_center, "resolve_task", return_value=binding), \
                mock.patch.object(ai_recognize.OpenAICompatibleProvider, "chat_completion",
                                  _chat(content)):
            return asyncio.run(ai_recognize.recognize([], context or {}, "solve"))

    def test_01_answer_and_solution_are_merged_into_source(self) -> None:
        context = {
            "type": "single_choice",
            "stem": "函数 $f(x)=x^2$ 的导数是（  ）",
            "options": [{"key": "A", "content": "$x$"}, {"key": "B", "content": "$2x$"}],
            "answer": "",
            "question_no": "7",
        }
        result = self._run(wire.dumps({
            "answer": "B", "solution": "由幂函数求导公式得 $f'(x)=2x$。", "note": "直接求导",
        }, ensure_ascii=False), context)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["question"]["answer"], "B")
        self.assertEqual(result["question"]["stem"], context["stem"], "题干必须原样保留")
        self.assertEqual(len(result["question"]["options"]), 2)
        self.assertIn("\\begin{solution}\n答案：B", result["source"])
        self.assertIn("$2x$", result["source"])

    def test_02_missing_stem_is_rejected_before_network(self) -> None:
        result = self._run("{}", {"stem": ""})
        self.assertFalse(result["ok"])
        self.assertIn("题干", result["detail"])

    def test_03_missing_assignment_is_structured_failure(self) -> None:
        empty = ai_center.TaskBinding("solve", "", "", "", "", "")
        result = self._run("{}", {"stem": "求证 $a=b$"}, binding=empty)
        self.assertFalse(result["ok"])
        self.assertIn("API 配置", result["detail"])

    def test_04_empty_solution_is_a_failure_not_a_half_write(self) -> None:
        result = self._run(wire.dumps({"answer": "A", "solution": ""}), {"stem": "题干"})
        self.assertFalse(result["ok"])
        self.assertIn("解析", result["detail"])

    def test_05_bad_json_is_reported_not_raised(self) -> None:
        result = self._run("我算不出来", {"stem": "题干"})
        self.assertFalse(result["ok"])
        self.assertIn("JSON", result["detail"])

    def test_06_model_answer_and_solution_are_normalized_stem_kept(self) -> None:
        context = {"type": "solution", "stem": r"若 \(m_1 m_2\) 是两根", "answer": "", "options": []}
        result = self._run(wire.dumps({
            "answer": r"\(m_1=1\)", "solution": r"由 \[m_1 m_2=2\] 得证。",
        }, ensure_ascii=False), context)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["question"]["answer"], "$m_{1}=1$")
        self.assertEqual(result["question"]["solution"], r"由 $$m_{1}\,m_{2}=2$$ 得证。")
        self.assertEqual(result["question"]["stem"], context["stem"], "题干必须原样保留")


if __name__ == "__main__":
    unittest.main()
