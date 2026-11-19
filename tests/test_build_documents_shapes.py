# -*- coding: utf-8 -*-
"""BDP-01 切题解析四形状修实定向测试（build-documents-shapes）。

钉住八件事：
1. 四形状各 ≥2 案（真实 MinerU 夹具逐字＋变体）：选项独立成行 / 卷首图片行 /
   整题 $$ 包裹＋裂题号 / 填空转义下划线；
2. 7 题夹具（3/6/10/11/13/14/15）→ 7 文档，stem 非空、题号头号正确、选项/blanks 按形状；
3. 20 夹具 → 20/20 出文档；
4. 对照 13 题与修前快照逐字段一致（字典改写口径已含在快照里）；
5. 幂等：归一文本两遍稳定＋解析文档稳定；
6. 图片行剥掉不静默丢（warnings 如实登记）；
7. $$ unwrap 把裂题号「1 3.」修成「13.」，且只在 $$ 语境修——正常文本数字不碰；
8. 填空 blanks 按 question_parser 现有口径计数；存量发问词题（Q16）与节标题题（Q12）
   的形状归一逐字不动（边界谓词守住）。

题号口径：与对照 13 题一致，题号住在 stem 头号，source.question_no 为空——mineru
回填路的题号由 recognize.shared.merge_local 用本地切题题号覆盖，build_documents 不强加，
以保「对照逐字段一致＋幂等」两硬约束。

运行：``.venv/Scripts/python.exe -m unittest tests.test_build_documents_shapes``
"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.core import toml_io
from app.core.content import question_parser
from app.core.ingest.intake import shapes
from app.core.ingest.service import build_documents

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "bdp01"
SEVEN = (3, 6, 10, 11, 13, 14, 15)
CONTROLS = tuple(n for n in range(1, 21) if n not in SEVEN)
# 形状期望：(type, 选项数, 空数)
SHAPE = {3: ("single_choice", 4, 0), 6: ("single_choice", 4, 0),
         10: ("single_choice", 4, 0), 11: ("single_choice", 4, 0),
         13: ("solution", 0, 0), 14: ("fill_blank", 0, 1), 15: ("solution", 0, 0)}


def md(no: int) -> str:
    return (FIX / f"full_md_fix_{no:02d}.md").read_text(encoding="utf-8")


def before_by_no() -> dict[int, dict]:
    data = toml_io.load(FIX / "before.toml")
    return {int(f["no"]): f for f in data["fixture"]}


class ShapeOneOptionLinesTest(unittest.TestCase):
    """形状一：选项被空行劈成碎段，只并跑到文末的选项块。"""

    def test_real_q3_four_options(self) -> None:
        docs, _w = build_documents(md(3))
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["type"], "single_choice")
        self.assertEqual([o["key"] for o in docs[0]["options"]], ["A", "B", "C", "D"])
        self.assertEqual([o["content"] for o in docs[0]["options"]], ["1", "2", "3", "4"])
        self.assertTrue(docs[0]["stem"].lstrip().startswith("3."))

    def test_real_q6_inline_options_separate_paragraph(self) -> None:
        docs, _w = build_documents(md(6))
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["type"], "single_choice")
        self.assertEqual(len(docs[0]["options"]), 4)
        self.assertTrue(docs[0]["stem"].lstrip().startswith("6."))

    def test_variant_no_ask_word_still_splits(self) -> None:
        text = "5. 集合 $M$ 的元素个数是 ( )\n\nA. 1\n\nB. 2\n\nC. 3\n\nD. 4"
        docs, _w = build_documents(text)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["type"], "single_choice")
        self.assertEqual(len(docs[0]["options"]), 4)

    def test_q12_trailing_section_header_not_merged(self) -> None:
        # 选项后面还跟着节标题：不并（并了会改变存量解析）。
        normalized, warnings = shapes.normalize(md(12))
        self.assertEqual(normalized, md(12))
        self.assertEqual(warnings, [])


class ShapeTwoImageLineTest(unittest.TestCase):
    """形状二：卷首图片行剥掉＋如实登记警告。"""

    def test_real_q10_stripped_with_warning(self) -> None:
        docs, warnings = build_documents(md(10))
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["type"], "single_choice")
        self.assertEqual(len(docs[0]["options"]), 4)
        self.assertNotIn("![", docs[0]["stem"])
        self.assertTrue(docs[0]["stem"].lstrip().startswith("10."))
        self.assertTrue(any("图片行已剥离" in w and "images/" in w for w in warnings))

    def test_real_q11_stripped_with_warning(self) -> None:
        docs, warnings = build_documents(md(11))
        self.assertEqual(len(docs), 1)
        self.assertEqual(len(docs[0]["options"]), 4)
        self.assertNotIn("![", docs[0]["stem"])
        self.assertTrue(any("图片行已剥离" in w for w in warnings))

    def test_variant_image_then_inline_options(self) -> None:
        text = ("![](images/a.jpg)\n\n2. 已知 $x>0$，则正确的是 ( )\n\n"
                "A. $x>1$ B. $x<1$ C. $x=1$ D. 不确定")
        docs, warnings = build_documents(text)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["type"], "single_choice")
        self.assertNotIn("![", docs[0]["stem"])
        self.assertTrue(any("images/a.jpg" in w for w in warnings))

    def test_image_only_not_silently_dropped(self) -> None:
        _docs, warnings = build_documents("![](images/only.jpg)")
        self.assertTrue(any("图片行已剥离" in w and "only.jpg" in w for w in warnings))


class ShapeThreeDisplayWrapTest(unittest.TestCase):
    """形状三：整题 $$ 包裹 unwrap＋裂题号修复（只在 $$ 语境）。"""

    def test_real_q13_unwrap_and_repair(self) -> None:
        docs, _w = build_documents(md(13))
        self.assertEqual(len(docs), 1)
        stem = docs[0]["stem"]
        self.assertTrue(stem.lstrip().startswith("13."))
        self.assertNotIn("1 3.", stem)
        self.assertNotIn("$$", stem)
        self.assertIn("不等式", stem)

    def test_real_q15_unwrap_and_repair(self) -> None:
        docs, _w = build_documents(md(15))
        self.assertEqual(len(docs), 1)
        stem = docs[0]["stem"]
        self.assertTrue(stem.lstrip().startswith("15."))
        self.assertNotIn("1 5.", stem)
        self.assertNotIn("$$", stem)

    def test_variant_two_digit_split(self) -> None:
        docs, _w = build_documents("$$\n2 0. \\text{ 求 } x+1=2 \\text{ 的解 }\n$$")
        self.assertEqual(len(docs), 1)
        self.assertTrue(docs[0]["stem"].lstrip().startswith("20."))

    def test_variant_single_digit_no_split(self) -> None:
        docs, _w = build_documents("$$\n7. \\text{ 计算 } 1+1\n$$")
        self.assertEqual(len(docs), 1)
        self.assertTrue(docs[0]["stem"].lstrip().startswith("7."))

    def test_split_number_not_repaired_outside_display(self) -> None:
        # 正常文本里的「1 3.」不修：没有 $$ 包裹，归一逐字不动。
        text = "已知 1 3. 这样的数字不碰，求 $x$ 的值。"
        normalized, warnings = shapes.normalize(text)
        self.assertEqual(normalized, text)
        self.assertEqual(warnings, [])
        docs, _w = build_documents(text)
        self.assertEqual(len(docs), 1)
        self.assertIn("1 3.", docs[0]["stem"])

    def test_normal_number_head_not_mangled(self) -> None:
        docs, _w = build_documents("13. 求 $x+1=2$ 的解。")
        self.assertEqual(len(docs), 1)
        self.assertTrue(docs[0]["stem"].lstrip().startswith("13."))


class ShapeFourFillBlankTest(unittest.TestCase):
    """形状四：转义下划线还原，按现有 count_blanks 口径计数。"""

    def test_real_q14_fill_blank(self) -> None:
        docs, _w = build_documents(md(14))
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["type"], "fill_blank")
        self.assertNotIn("\\_", docs[0]["stem"])
        self.assertTrue(docs[0]["stem"].lstrip().startswith("14."))
        self.assertEqual(question_parser.count_blanks(docs[0]["stem"]), 1)

    def test_variant_escaped_blank_no_ask_word(self) -> None:
        docs, _w = build_documents("9. 方程 $x^2=4$ 的解是 \\_\\_\\_\\_.")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["type"], "fill_blank")
        self.assertEqual(question_parser.count_blanks(docs[0]["stem"]), 1)

    def test_q16_with_ask_word_left_untouched(self) -> None:
        # 已有发问词的存量题：归一逐字不动，不改它的空与题型。
        normalized, warnings = shapes.normalize(md(16))
        self.assertEqual(normalized, md(16))
        self.assertEqual(warnings, [])
        docs, _w = build_documents(md(16))
        self.assertEqual(docs[0]["type"], "solution")


class SevenAndTwentyTest(unittest.TestCase):
    """7 题全量＋20 题全量。"""

    def test_seven_fixtures_seven_documents(self) -> None:
        for no in SEVEN:
            with self.subTest(question=no):
                docs, _w = build_documents(md(no))
                self.assertEqual(len(docs), 1)
                stem = docs[0]["stem"]
                self.assertTrue(stem.strip())
                self.assertTrue(stem.lstrip().startswith(f"{no}."))
                exp_type, exp_opts, exp_blanks = SHAPE[no]
                self.assertEqual(docs[0]["type"], exp_type)
                self.assertEqual(len(docs[0].get("options") or []), exp_opts)
                if exp_blanks:
                    self.assertEqual(question_parser.count_blanks(stem), exp_blanks)

    def test_twenty_fixtures_all_yield_documents(self) -> None:
        for no in range(1, 21):
            with self.subTest(question=no):
                docs, _w = build_documents(md(no))
                self.assertGreaterEqual(len(docs), 1)


class ControlNoRegressionTest(unittest.TestCase):
    """对照 13 题与修前快照逐字段一致。"""

    def test_controls_field_identical_to_before(self) -> None:
        baseline = before_by_no()
        for no in CONTROLS:
            with self.subTest(question=no):
                docs, warnings = build_documents(md(no))
                snap = baseline[no]
                self.assertEqual(len(docs), snap["doc_count"])
                self.assertEqual(docs, snap["documents"])
                self.assertEqual(warnings, snap["warnings"])

    def test_normalize_noop_on_every_control(self) -> None:
        for no in CONTROLS:
            with self.subTest(question=no):
                normalized, warnings = shapes.normalize(md(no))
                self.assertEqual(normalized, md(no))
                self.assertEqual(warnings, [])


class IdempotencyTest(unittest.TestCase):
    """归一文本两遍稳定＋解析文档稳定。"""

    def test_normalize_text_idempotent(self) -> None:
        for no in range(1, 21):
            with self.subTest(question=no):
                once, _w = shapes.normalize(md(no))
                twice, _w2 = shapes.normalize(once)
                self.assertEqual(twice, once)

    def test_parse_documents_stable_under_renormalize(self) -> None:
        for no in range(1, 21):
            with self.subTest(question=no):
                once, _w = build_documents(md(no))
                normalized, _n = shapes.normalize(md(no))
                twice, _w2 = build_documents(normalized)
                self.assertEqual(twice, once)


if __name__ == "__main__":
    unittest.main()