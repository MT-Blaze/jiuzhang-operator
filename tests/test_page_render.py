"""原卷页面图（v9）：所有格式拖进来都要有左栏可看的「原卷」。

判据：

- Word / 纯文本：没有 Word/LibreOffice 也出一页页 SVG 文本还原图，纯标准库；
- 图片：原图直接复制进 ``pending_assets/``，不重采样；
- 题号锚点：每道题知道自己在第几页，折页之后不串页；
- SVG 只当图片：禁用标签写不进去，文件名与正文都按 XML 转义；
- 页面图归批次层：``save_draft(page_images=?)`` 的整体替换与「不动」两态都成立。

运行：``.venv/Scripts/python.exe -m unittest tests.test_page_render``
"""

from __future__ import annotations

import base64
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import (  # noqa: E402
    page_furniture, page_render, page_render_cross, pending_assets, pending_bank,
    pending_batches, pending_db,
)

PLUGIN_ID = "org.jiuzhang.editor"
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _doc(number: str, stem: str = "") -> dict:
    return {
        "type": "single_choice",
        "stem": stem or ("第 " + number + " 题的题干"),
        "difficulty": "L2",
        "options": [
            {"key": "A", "content": "$1$"},
            {"key": "B", "content": "$2$"},
            {"key": "C", "content": "$3$"},
            {"key": "D", "content": "$4$"},
        ],
        "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
        "source": {"question_no": number},
    }


class PageRenderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.core.config import settings

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (os.environ.get("JZO_DATA_DIR"), settings.workspace_id)
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        settings.workspace_id = None
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        from app.core.config import settings

        settings.workspace_id = self._saved[1]
        if self._saved[0] is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = self._saved[0]

    def _asset_file(self, entry: dict) -> Path:
        name = str(entry["name"])
        self.assertTrue(pending_db.PENDING_ASSET_RE.match(name), name)
        path = pending_db.pending_assets_dir() / name
        self.assertTrue(path.is_file(), f"页面图没落盘：{name}")
        return path


class TextFacsimileTest(PageRenderTestCase):
    def test_01_word_text_becomes_svg_pages_with_numbered_anchors(self) -> None:
        """17 道题那种文本卷：一页放不下就折页，题号锚点把每道题带到它真正所在的页。"""
        filler = "\n".join("第 %d 行补充说明" % index for index in range(80))
        text = "1．第一题题干\n" + filler + "\n2．第二题题干\n3．第三题题干\n"
        documents = [_doc("1"), _doc("2"), _doc("3")]
        entries, doc_pages, warnings = page_render.build_pages(
            "闭环样卷_原卷.docx", "docx", b"", text, documents)

        self.assertEqual(warnings, [])
        self.assertGreaterEqual(len(entries), 2, "80 行填充必须折成两页")
        self.assertEqual(len(doc_pages), 3)
        self.assertEqual(doc_pages, sorted(doc_pages), "题号顺序不能乱")
        self.assertEqual(doc_pages[0], 1)
        self.assertGreaterEqual(doc_pages[1], 2, "第二题落在第二页")
        for entry in entries:
            self.assertTrue(entry["uri"].startswith("/static/pending/pimg_"))
            self.assertIsInstance(entry["page"], int)
            body = self._asset_file(entry).read_text(encoding="utf-8")
            self.assertIn("<svg", body)
            self.assertIn("闭环样卷_原卷.docx", body)
            self.assertIn("第 %d 页 / 共 %d 页" % (entry["page"], len(entries)), body)

    def test_02_svg_is_escaped_and_cannot_carry_scripts(self) -> None:
        """标题里的尖括号只当文字；含着脚本的 SVG 一步也进不了资产目录。"""
        documents = [_doc("1")]
        entries, _pages, _warnings = page_render.build_pages(
            "<script>alert(1)</script>.txt", "txt", b"", "1．题干\n", documents)
        self.assertEqual(len(entries), 1)
        body = self._asset_file(entries[0]).read_text(encoding="utf-8")
        self.assertNotIn("<script", body.lower())
        self.assertIn("&lt;script&gt;", body)

        with self.assertRaises(pending_db.PendingError):
            pending_assets.write_generated_asset(
                b'<svg xmlns="http://www.w3.org/2000/svg"><script>x</script></svg>',
                "image/svg+xml")

    def test_03_pdf_renders_pages_instead_of_using_text(self) -> None:
        """PDF 只出原卷大图：就算带着完美文本层，也不拿文字凑页面。"""
        pages = [{"name": "pimg_" + "c" * 16 + ".png",
                  "uri": "/static/pending/pimg_" + "c" * 16 + ".png", "page": 1}]
        with mock.patch.object(page_render, "_pdf_pages",
                               return_value=(pages, [])) as render, \
                mock.patch.object(page_render, "_facsimile") as facsimile:
            entries, doc_pages, warnings = page_render.build_pages(
                "模拟1.pdf", "pdf", b"%PDF-1.7", "1．完美文本层\n2．第二题\n", [_doc("1")])
        render.assert_called_once()
        facsimile.assert_not_called()
        self.assertEqual(entries, pages)
        self.assertEqual(doc_pages, [1])
        self.assertEqual(warnings, [])

    def test_04_pdf_without_renderer_reports_empty(self) -> None:
        """渲染器缺席就交白卷，绝不拿文本层顶替原卷页。"""
        with mock.patch.object(page_render, "_pdf_pages",
                               return_value=([], ["本机没有 PDF 页面渲染器（pdftoppm）"])):
            entries, doc_pages, warnings = page_render.build_pages(
                "扫描件.pdf", "pdf", b"%PDF-1.4", "1．一段文本\n", [_doc("1")])
        self.assertEqual(entries, [])
        self.assertEqual(doc_pages, [])
        self.assertTrue(warnings)

    def test_05_builtin_renderer_wins_without_touching_pdftoppm(self) -> None:
        """分发包优先用内置 pypdfium2；能用就不去碰开发机上的 pdftoppm。"""
        pages = [{"name": "pimg_" + "d" * 16 + ".png",
                  "uri": "/static/pending/pimg_" + "d" * 16 + ".png", "page": 1}]
        with mock.patch.object(page_render, "_pdf_pages_builtin",
                               return_value=(pages, [])) as builtin, \
                mock.patch.object(page_render, "_pdf_pages_pdftoppm") as pdftoppm:
            entries, warnings = page_render._pdf_pages(b"%PDF-1.7")
        builtin.assert_called_once()
        pdftoppm.assert_not_called()
        self.assertEqual(entries, pages)
        self.assertEqual(warnings, [])

    def test_06_builtin_failure_falls_back_to_pdftoppm(self) -> None:
        """内置引擎打不开（缺库/坏文件）时，才降级到本机 pdftoppm，并保留原因。"""
        pages = [{"name": "pimg_" + "e" * 16 + ".png",
                  "uri": "/static/pending/pimg_" + "e" * 16 + ".png", "page": 1}]
        with mock.patch.object(page_render, "_pdf_pages_builtin",
                               return_value=([], ["内置 PDF 渲染器打不开这份文件"])), \
                mock.patch.object(page_render, "_pdf_pages_pdftoppm",
                                  return_value=(pages, [])) as pdftoppm:
            entries, warnings = page_render._pdf_pages(b"%PDF-1.7")
        pdftoppm.assert_called_once()
        self.assertEqual(entries, pages)
        self.assertEqual(warnings, ["内置 PDF 渲染器打不开这份文件"])

    def test_07_both_renderers_failing_reports_empty(self) -> None:
        """两条路都不通：空清单 + 两条原因，绝不静默。"""
        with mock.patch.object(page_render, "_pdf_pages_builtin",
                               return_value=([], ["内置引擎不可用"])), \
                mock.patch.object(page_render, "_pdf_pages_pdftoppm",
                                  return_value=([], ["本机也没有 pdftoppm 兜底"])):
            entries, warnings = page_render._pdf_pages(b"%PDF-1.7")
        self.assertEqual(entries, [])
        self.assertEqual(warnings, ["内置引擎不可用", "本机也没有 pdftoppm 兜底"])

    def test_08a_question_regions_skip_instructions(self) -> None:
        """作答说明也带 1./2./3.，但只有更长的正式题号链才算题。"""
        lines = [
            {"text": "1. 答卷前，考生务必将姓名填在答题卡上", "left": 72, "bottom": 780,
             "right": 523, "top": 790},
            {"text": "2. 回答选择题时，选出每小题答案后", "left": 72, "bottom": 760,
             "right": 523, "top": 770},
            {"text": "3. 考试结束后，将本试卷交回", "left": 72, "bottom": 740,
             "right": 523, "top": 750},
            {"text": "1. 第一题题干", "left": 72, "bottom": 650, "right": 523, "top": 660},
            {"text": "A. 选项甲 B. 选项乙", "left": 80, "bottom": 630, "right": 480, "top": 640},
            {"text": "2. 第二题题干", "left": 72, "bottom": 560, "right": 523, "top": 570},
        ]
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339)
        self.assertEqual([region["no"] for region in regions], [1, 2])
        for region in regions:
            self.assertGreaterEqual(region["x"], 0)
            self.assertGreaterEqual(region["y"], 0)
            self.assertLessEqual(region["x"] + region["w"], 1654)
            self.assertLessEqual(region["y"] + region["h"], 2339)
        self.assertIn("选项甲", regions[0]["text"])

    def test_08a2_first_page_starts_after_section_heading(self) -> None:
        """首页从第一个大节标题之后找题号：卷首那些编号行一律不当题目。"""
        lines = [
            {"text": "1. 2024 年普通高等学校招生考试", "left": 72, "bottom": 800,
             "right": 523, "top": 810},
            {"text": "2. 数学", "left": 72, "bottom": 780, "right": 523, "top": 790},
            {"text": "一、选择题：本题共 8 小题", "left": 72, "bottom": 760,
             "right": 523, "top": 770},
            {"text": "1. 第一题题干", "left": 72, "bottom": 700, "right": 523, "top": 710},
            {"text": "2. 第二题题干", "left": 72, "bottom": 600, "right": 523, "top": 610},
        ]
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339,
                                                first_page=True)
        self.assertEqual([region["no"] for region in regions], [1, 2])
        self.assertIn("第一题题干", regions[0]["text"])
        self.assertNotIn("招生考试", regions[0]["text"])

    def test_08a2b_head_embedded_after_section_line_is_found(self) -> None:
        """文本层把「1．」并进上一句/大节标题时，题号链仍要从 1 开始。"""
        lines = [
            {"text": "一、单选题：共 8 小题，每小题 5 分", "left": 72, "bottom": 810,
             "right": 523, "top": 820},
            {"text": "是符合题目要求的. 1．", "left": 72, "bottom": 780,
             "right": 523, "top": 790},
            {"text": "sin1050 的值为", "left": 72, "bottom": 760, "right": 523, "top": 770},
            {"text": "2．已知扇形的圆心角为 2rad", "left": 72, "bottom": 700,
             "right": 523, "top": 710},
        ]
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339,
                                                first_page=True)
        self.assertEqual([region["no"] for region in regions], [1, 2])
        self.assertIn("sin1050", regions[0]["text"])

    def test_08a3_regions_leave_a_gap_so_boxes_do_not_overlap(self) -> None:
        """相邻两题之间至少留出一道缝；上下题号行不重叠。"""
        lines = [
            {"text": "1. 第一题题干", "left": 72, "bottom": 700, "right": 523, "top": 710},
            {"text": "A. 选项甲 B. 选项乙", "left": 80, "bottom": 680, "right": 480, "top": 690},
            {"text": "2. 第二题题干", "left": 72, "bottom": 600, "right": 523, "top": 610},
        ]
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339)
        self.assertEqual(len(regions), 2)
        first, second = regions
        self.assertLessEqual(first["y"] + first["h"], second["y"] - 8,
                             "第一题的框必须停在第二题上方，且留出可见的空隙")

    def test_08a4_ink_trim_only_shrinks_inward(self) -> None:
        """墨迹裁边只许往框内收：外扩会把相邻两题的框重新叠在一起。"""
        ink = bytearray(100)
        ink[40:50] = b"\x01" * 10
        top, height = page_render._trim_to_ink(30, 40, ink, 100)
        self.assertEqual((top, height), (34, 22))
        # 框的上边界已经压进墨迹里：裁边不许把它再往上推。
        ink2 = bytearray(100)
        ink2[42:48] = b"\x01" * 6
        top2, height2 = page_render._trim_to_ink(42, 6, ink2, 100)
        self.assertEqual(top2, 42)
        self.assertEqual(height2, 6)

    def test_08a5_footer_in_paren_form_is_not_joined_into_last_text(self) -> None:
        """「第1页（共3页）」是页脚：末题的 text 与框底都不能把它吃进去。"""
        lines = [
            {"text": "1. 第一题题干", "left": 72, "bottom": 700, "right": 523, "top": 710},
            {"text": "A. 选项甲 B. 选项乙", "left": 80, "bottom": 680, "right": 480, "top": 690},
            {"text": "第1页（共3页）", "left": 260, "bottom": 30, "right": 335, "top": 40},
        ]
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339)
        self.assertEqual([region["no"] for region in regions], [1])
        last = regions[-1]
        self.assertNotIn("第1页", last["text"])
        self.assertNotIn("共3页", last["text"])
        self.assertIn("选项甲", last["text"])
        footer_top_px = (842 - 40) * (2339 / 842)
        self.assertLessEqual(last["y"] + last["h"], footer_top_px,
                             "末题框底必须停在页脚上沿之上")

    def test_08a6_footer_in_slash_form_is_not_joined_into_last_text(self) -> None:
        """「第1页/共3页」也要认：这条真实素材的写法漏认会让页脚并进末题。"""
        lines = [
            {"text": "1. 第一题题干", "left": 72, "bottom": 700, "right": 523, "top": 710},
            {"text": "A. 选项甲 B. 选项乙", "left": 80, "bottom": 680, "right": 480, "top": 690},
            {"text": "第1页/共3页", "left": 260, "bottom": 30, "right": 335, "top": 40},
        ]
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339)
        self.assertEqual([region["no"] for region in regions], [1])
        last = regions[-1]
        self.assertNotIn("第1页", last["text"])
        self.assertNotIn("共3页", last["text"])
        self.assertIn("选项甲", last["text"])
        footer_top_px = (842 - 40) * (2339 / 842)
        self.assertLessEqual(last["y"] + last["h"], footer_top_px,
                             "末题框底必须停在页脚上沿之上")

    def test_08a7a_bare_page_number_at_page_bottom_is_a_footer(self) -> None:
        """页底裸数字页码：纯数字、贴底、行高比正文小——既不入 text 也不进框。"""
        lines = [
            {"text": "1. 第一题题干", "left": 72, "bottom": 700, "right": 523, "top": 710},
            {"text": "A. 选项甲 B. 选项乙", "left": 80, "bottom": 680, "right": 480, "top": 690},
            {"text": "1", "left": 295, "bottom": 21.4, "right": 300, "top": 29.5},
        ]
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339)
        self.assertEqual([region["no"] for region in regions], [1])
        last = regions[-1]
        self.assertNotIn("1", [line.strip() for line in last["text"].splitlines()])
        self.assertIn("选项甲", last["text"])
        footer_top_px = (842 - 29.5) * (2339 / 842)
        self.assertLessEqual(last["y"] + last["h"], footer_top_px,
                             "末题框底必须停在裸页码上沿之上")

    def test_08a7b_same_size_digit_answer_at_page_bottom_is_kept(self) -> None:
        """答案区贴底的单行纯数字答案与正文同字号：行高不满足页脚判据，必须保留。"""
        lines = [
            {"text": "1. 第一题题干", "left": 72, "bottom": 700, "right": 523, "top": 710},
            {"text": "A. 选项甲 B. 选项乙", "left": 80, "bottom": 680, "right": 480, "top": 690},
            {"text": "3", "left": 280, "bottom": 20, "right": 285, "top": 30},
        ]
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339)
        last = regions[-1]
        self.assertEqual([line.strip() for line in last["text"].splitlines()][-1], "3")
        self.assertGreater(last["y"] + last["h"], (842 - 30) * (2339 / 842),
                           "答案行既然不是页脚，框底就得盖住它")

    def test_08a7c_question_head_and_option_are_not_bare_page_numbers(self) -> None:
        """「4.」题号行与「A.7」选项行不是纯数字：裸页码判据不得误伤。"""
        lines = [
            {"text": "1. 第一题题干", "left": 72, "bottom": 700, "right": 523, "top": 710},
            {"text": "A.7 选项甲", "left": 80, "bottom": 680, "right": 480, "top": 690},
            {"text": "4. 第四题（题号不连续）", "left": 72, "bottom": 30, "right": 523, "top": 40},
        ]
        self.assertEqual(page_render._bare_page_footer_lines(lines, 842), [])
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339)
        last = regions[-1]
        self.assertIn("A.7", last["text"])
        self.assertIn("4. 第四题", last["text"])

    def test_08a7d_chinese_page_forms_stay_on_the_original_branch(self) -> None:
        """「第1页（共3页）」「第1页/共3页」仍走原正则分支，裸页码判据不接管。"""
        for footer in ("第1页（共3页）", "第1页/共3页"):
            lines = [
                {"text": "1. 第一题题干", "left": 72, "bottom": 700, "right": 523, "top": 710},
                {"text": "A. 选项甲 B. 选项乙", "left": 80, "bottom": 680, "right": 480, "top": 690},
                {"text": footer, "left": 260, "bottom": 30, "right": 335, "top": 40},
            ]
            self.assertEqual(page_render._bare_page_footer_lines(lines, 842), [])
            regions = page_render._question_regions(lines, 595, 842, 1654, 2339)
            last = regions[-1]
            self.assertNotIn("第1页", last["text"])
            self.assertNotIn("共3页", last["text"])
            self.assertLessEqual(last["y"] + last["h"], (842 - 40) * (2339 / 842))

    def test_08a7_head_top_covers_overlapping_formula_row(self) -> None:
        """题号行上方 20pt 内的公式行与题号行纵向重叠：框顶必须含住公式行顶。"""
        lines = [
            {"text": "上一题残余，不该被吃进来", "left": 72, "bottom": 730,
             "right": 523, "top": 740},
            {"text": "A={x∈N|−√3≤x≤√3}", "left": 200, "bottom": 655,
             "right": 500, "top": 680},
            {"text": "1. 已知集合", "left": 72, "bottom": 650, "right": 300, "top": 660},
            {"text": "A. 选项甲 B. 选项乙", "left": 80, "bottom": 620,
             "right": 480, "top": 630},
        ]
        regions = page_render._question_regions(lines, 595, 842, 1654, 2339)
        self.assertEqual([region["no"] for region in regions], [1])
        scale_y = 2339 / 842
        formula_top_px = (842 - 680) * scale_y
        previous_bottom_px = (842 - 730) * scale_y
        self.assertLessEqual(regions[0]["y"], formula_top_px,
                             "框顶必须高过公式行顶，不能留下 72px 的切口")
        self.assertGreater(regions[0]["y"], previous_bottom_px,
                           "上沿不许越过上一题残余行的底边")

    def test_08b_real_paper_has_nineteen_regions(self) -> None:
        """模拟1.pdf 自带文本层：五页共 19 道题，每题一块，页脚不切。"""
        pdf = Path(__file__).resolve().parents[2] / "testdata" / "20261105" / "模拟1.pdf"
        if not pdf.is_file():
            self.skipTest("本机没有 testdata/20261105/模拟1.pdf")
        entries, warnings = page_render._pdf_pages_builtin(pdf.read_bytes())
        self.assertEqual(warnings, [])
        self.assertEqual(len(entries), 5)
        numbers = [region["no"]
                   for entry in entries for region in (entry.get("regions") or [])]
        self.assertEqual(numbers, list(range(1, 20)))
        first = entries[0]
        self.assertEqual((first.get("width"), first.get("height")), (1654, 2339))

    def test_08c_real_paper_regions_never_overlap(self) -> None:
        """模拟1.pdf 的 19 个框按卷面从上到下排开，相邻两框之间留有缝隙。"""
        pdf = Path(__file__).resolve().parents[2] / "testdata" / "20261105" / "模拟1.pdf"
        if not pdf.is_file():
            self.skipTest("本机没有 testdata/20261105/模拟1.pdf")
        entries, _warnings = page_render._pdf_pages_builtin(pdf.read_bytes())
        for entry in entries:
            height = float(entry.get("height") or 0)
            regions = entry.get("regions") or []
            for previous, current in zip(regions, regions[1:]):
                self.assertLessEqual(
                    previous["y"] + previous["h"], current["y"] - 8,
                    "第 %s 题与第 %s 题的框叠在一起" % (previous["no"], current["no"]))
                self.assertGreaterEqual(current["y"], 0)
                self.assertLessEqual(current["y"] + current["h"], height)
            for region in regions:
                self.assertNotRegex(region["label"], r"绝密|启用前|注意事项")

    def test_08d_crop_pdf_regions_returns_one_png_per_box(self) -> None:
        """自动切图按框出图：一块一张真 PNG，尺寸与框的宽高比一致。"""
        pdf = Path(__file__).resolve().parents[2] / "testdata" / "20261105" / "模拟1.pdf"
        if not pdf.is_file():
            self.skipTest("本机没有 testdata/20261105/模拟1.pdf")
        entries, _warnings = page_render._pdf_pages_builtin(pdf.read_bytes())
        crops, warnings = page_render.crop_pdf_regions(pdf.read_bytes(), entries)
        self.assertEqual(warnings, [])
        total = sum(len(page.get("regions") or []) for page in entries)
        made = sum(len(items) for items in crops.values())
        self.assertEqual(made, total)
        self.assertEqual(total, 19)
        for page_no, items in crops.items():
            regions = entries[page_no - 1].get("regions") or []
            self.assertEqual([item["index"] for item in items], list(range(len(regions))))
            for item in items:
                self.assertTrue(item["png"].startswith(b"\x89PNG\r\n\x1a\n"))
                region = item["region"]
                ratio = (item["width"] / item["height"]) / (region["w"] / region["h"])
                self.assertAlmostEqual(ratio, 1.0, delta=0.03)

    def test_08_builtin_renderer_outputs_a4_png(self) -> None:
        """内置渲染器自己出的页图必须是可读 PNG，尺寸按 200 dpi 的 A4 算。"""
        pdfium = getattr(page_render, "_pdfium")
        if pdfium is None:
            self.skipTest("本机没装 pypdfium2")
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "blank.pdf"
            document = pdfium.PdfDocument.new()
            try:
                document.new_page(595, 842)
                document.save(str(source))
            finally:
                document.close()
            entries, warnings = page_render._pdf_pages_builtin(source.read_bytes())
        self.assertEqual(len(entries), 1)
        self.assertEqual(warnings, [])
        raw = self._asset_file(entries[0]).read_bytes()
        self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"))
        width, height = struct.unpack(">II", raw[16:24])
        self.assertAlmostEqual(width, 1653, delta=2)
        self.assertAlmostEqual(height, 2339, delta=2)


class PageFurnitureTest(unittest.TestCase):
    """全卷页眉页脚：同一位置 + 同一文字跨页重复才剔，页数少一律不动。"""

    @staticmethod
    def _line(text: str, top: float, bottom: float,
              left: float = 72.0, right: float = 523.0) -> dict:
        # 两个 y 值不要求先后：PDF 的 top（上沿）永远大于 bottom（下沿）。
        return {"text": text, "left": left, "bottom": min(top, bottom),
                "right": right, "top": max(top, bottom), "missing": 0}

    @staticmethod
    def _page(lines: list[dict], height: float = 842.0) -> dict:
        return {"width": 595.0, "height": height, "lines": lines}

    @staticmethod
    def _texts(kept: list[list[dict]]) -> list[list[str]]:
        return [[line["text"] for line in lines] for lines in kept]

    def test_01_single_page_is_returned_untouched(self) -> None:
        """单页卷不判页眉页脚：行清单必须原样交给切题。"""
        lines = [
            self._line("1. 第一题题干", 700, 710),
            self._line("A. 选项甲 B. 选项乙", 680, 690),
            self._line("第1页（共1页）", 20, 30),
        ]
        kept = page_furniture.filter_pages([self._page(lines)])
        self.assertIs(kept[0], lines, "单页卷一个字都不许剔，且不能换新列表")

    def test_02_two_pages_keep_repeated_footer(self) -> None:
        """两页卷同样不判：即使两页都有页脚，也要原样返回。"""
        pages = [
            self._page([self._line("1. 第一题题干", 700, 710),
                        self._line("第1页（共2页）", 20, 30)]),
            self._page([self._line("2. 第二题题干", 760, 770),
                        self._line("第2页（共2页）", 20, 30)]),
        ]
        kept = page_furniture.filter_pages(pages)
        for index, page in enumerate(pages):
            self.assertIs(kept[index], page["lines"])

    def test_03_three_pages_require_all_three(self) -> None:
        """三页卷 3/3 全中才剔；只出现在两页的同位置行必须留下。"""
        def pages_with(header_pages: int) -> list[dict]:
            pages = []
            for index in range(3):
                header = (self._line("哈九中高一数学 第1页", 800, 810)
                          if index < header_pages
                          else self._line("一、选择题", 800, 810))
                pages.append(self._page([header,
                                         self._line("1. 第一题题干", 700, 710)]))
            return pages

        kept = page_furniture.filter_pages(pages_with(2))
        for page_texts in self._texts(kept)[:2]:
            self.assertIn("哈九中高一数学 第1页", page_texts[0])
        self.assertIn("一、选择题", self._texts(kept)[2])

        kept = page_furniture.filter_pages(pages_with(3))
        for page_texts in self._texts(kept):
            self.assertNotIn("哈九中高一数学 第1页", page_texts)

    def test_04_four_pages_use_two_thirds(self) -> None:
        """四页卷 2/3 即可（向上取整 = 3 页）；两页重复仍不算。"""
        def pages_with(header_pages: int) -> list[dict]:
            return [
                self._page([
                    (self._line("试卷页眉", 800, 810) if index < header_pages
                     else self._line("一、选择题", 800, 810)),
                    self._line("1. 第一题题干", 700, 710)])
                for index in range(4)
            ]

        kept = page_furniture.filter_pages(pages_with(2))
        self.assertIn("试卷页眉", self._texts(kept)[0])
        kept = page_furniture.filter_pages(pages_with(3))
        for page_texts in self._texts(kept):
            self.assertNotIn("试卷页眉", page_texts)

    def test_05_similar_option_rows_are_never_furniture(self) -> None:
        """每页都有的选项行位置相同、文字只差一两个字符，也绝不删。"""
        rows = [
            "A. 1/3 B. 2/3 C. 1/12 D. 5/12",
            "A. 1/4 B. 3/4 C. 1/12 D. 5/12",
            "A. 1/5 B. 4/5 C. 1/12 D. 5/12",
            "A. 1/6 B. 5/6 C. 1/12 D. 5/12",
        ]
        pages = [self._page([self._line("1. 第一题题干", 700, 710),
                             self._line(row, 60, 70)]) for row in rows]
        kept = page_furniture.filter_pages(pages)
        for index, row in enumerate(rows):
            self.assertIn(row, self._texts(kept)[index])

    def test_06_last_question_pressed_to_bottom_is_kept(self) -> None:
        """末题正文压进页底带、只在少数页出现：文本不同/页数不够都不得删。"""
        pages = []
        for index in range(4):
            pages.append(self._page([
                self._line("18. 末题题干", 720, 731),
                self._line("（2）求实数 a 的取值范围．" if index < 2
                           else "（2）证明不等式成立．", 50, 62),
            ]))
        kept = page_furniture.filter_pages(pages)
        self.assertEqual(self._texts(kept)[0][-1], "（2）求实数 a 的取值范围．")
        self.assertEqual(self._texts(kept)[2][-1], "（2）证明不等式成立．")

    def test_07_small_numeric_page_numbers_are_removed(self) -> None:
        """四页起：页底纯数字页码只要行高小于正文中位数，少数页也认。"""
        pages = []
        for number in range(1, 5):
            pages.append(self._page([
                self._line("1. 正文行", 700, 712),
                self._line(str(number), 20, 28),
            ]))
        kept = page_furniture.filter_pages(pages)
        for page_texts in self._texts(kept):
            self.assertEqual(page_texts, ["1. 正文行"])

    def test_08_same_size_numeric_answer_is_kept(self) -> None:
        """与正文同字号的页底数字答案：行高过不了页码判据，必须留下。"""
        pages = []
        for _ in range(4):
            pages.append(self._page([
                self._line("1. 正文行", 700, 712),
                self._line("3", 60, 72),
            ]))
        kept = page_furniture.filter_pages(pages)
        self.assertIn("3", self._texts(kept)[0])

    def test_09_three_page_numeric_requires_all_three(self) -> None:
        """三页卷的纯数字页码也按 3/3：只出现在两页时不许剔。"""
        two = [
            self._page([self._line("1. 正文行", 700, 712),
                        self._line(str(number), 20, 28)])
            for number in (1, 2)
        ]
        two.append(self._page([self._line("1. 正文行", 700, 712)]))
        kept = page_furniture.filter_pages(two)
        self.assertIn("1", self._texts(kept)[0])
        self.assertIn("2", self._texts(kept)[1])

        three = [
            self._page([self._line("1. 正文行", 700, 712),
                        self._line(str(number), 20, 28)])
            for number in (1, 2, 3)
        ]
        kept = page_furniture.filter_pages(three)
        for page_texts in self._texts(kept):
            self.assertEqual(page_texts, ["1. 正文行"])

    def test_10_footer_with_changing_page_numbers_is_one_template(self) -> None:
        """「第N页（共M页）」数字逐页变化，归一化后仍是同一条页脚。"""
        pages = [
            self._page([self._line("1. 正文行", 700, 712),
                        self._line("第%d页（共4页）" % number, 20, 30)])
            for number in range(1, 5)
        ]
        kept = page_furniture.filter_pages(pages)
        for page_texts in self._texts(kept):
            self.assertEqual(page_texts, ["1. 正文行"])

    def test_11_question_regions_can_skip_legacy_fallbacks(self) -> None:
        """兜底判据保留可调：默认照旧剔除页脚，上层可显式关掉。"""
        lines = [
            self._line("1. 第一题题干", 700, 710),
            self._line("A. 选项甲 B. 选项乙", 680, 690),
            self._line("第1页（共3页）", 30, 40),
        ]
        legacy = page_render._question_regions(lines, 595, 842, 1654, 2339)
        self.assertNotIn("第1页", legacy[-1]["text"])
        raw = page_render._question_regions(lines, 595, 842, 1654, 2339,
                                            apply_fallbacks=False)
        self.assertIn("第1页", raw[-1]["text"])


class WordEnrichmentTest(unittest.TestCase):
    """数学字形读不出来时，用 Poppler 的按词坐标把文字补回来（可选兜底）。"""

    def test_01_parse_pdftotext_keeps_words_and_boxes(self) -> None:
        raw = (
            '<doc><page width="595" height="842"><flow><block><line>'
            '<word xMin="1.5" yMin="2.5" xMax="3.5" yMax="4.5">已知</word>'
            '<word xMin="5" yMin="2" xMax="6" yMax="4">&lt;x&gt;</word>'
            '</line></block></flow></page></doc>'
        ).encode("utf-8")
        pages = page_render._parse_pdftotext(raw)
        self.assertEqual([word["text"] for word in pages[1]], ["已知", "<x>"])
        self.assertEqual(pages[1][0]["left"], 1.5)
        self.assertEqual(pages[1][0]["bottom"], 4.5)

    def test_02_superscripts_are_grouped_and_never_double(self) -> None:
        """相邻两个上标并进同一对花括号——``^{1}^{2}`` 是非法公式。"""
        words = [
            {"text": "x", "left": 0, "top": 100, "right": 5, "bottom": 110},
            {"text": "1", "left": 5, "top": 96, "right": 8, "bottom": 102},
            {"text": "2", "left": 8, "top": 96, "right": 11, "bottom": 102},
        ]
        self.assertEqual(page_render._line_words_text(words), "x^{1 2}")
        lower = [
            {"text": "m", "left": 0, "top": 100, "right": 5, "bottom": 110},
            {"text": "1", "left": 5, "top": 108, "right": 8, "bottom": 116},
        ]
        self.assertEqual(page_render._line_words_text(lower), "m_{1}")

    def test_03_chinese_words_are_not_spaced_apart(self) -> None:
        words = [
            {"text": "已知", "left": 0, "top": 0, "right": 20, "bottom": 10},
            {"text": "集合", "left": 23, "top": 0, "right": 43, "bottom": 10},
            {"text": "A", "left": 46, "top": 0, "right": 52, "bottom": 10},
        ]
        self.assertEqual(page_render._line_words_text(words), "已知集合 A")

    def test_04_region_text_reorders_side_by_side_columns(self) -> None:
        """左右并排的选项按横坐标重排，不按 Poppler 的 block 顺序。"""
        words = [
            {"text": "B.", "left": 300, "top": 50, "right": 308, "bottom": 60},
            {"text": "(2,", "left": 310, "top": 50, "right": 320, "bottom": 60},
            {"text": "A.", "left": 100, "top": 50, "right": 108, "bottom": 60},
            {"text": "∅", "left": 110, "top": 50, "right": 117, "bottom": 60},
            {"text": "1.", "left": 100, "top": 10, "right": 108, "bottom": 20},
        ]
        text = page_render._words_region_text(
            words, 0, 0, 595, 842, 1.0, 1.0)
        self.assertEqual(text, "1.\nA. ∅ B. (2,")

    def test_05_words_outside_the_box_are_ignored(self) -> None:
        words = [
            {"text": "里", "left": 10, "top": 10, "right": 20, "bottom": 20},
            {"text": "外", "left": 400, "top": 400, "right": 410, "bottom": 410},
        ]
        text = page_render._words_region_text(
            words, 0, 0, 100, 100, 1.0, 1.0)
        self.assertEqual(text, "里")

    def test_06_real_paper_regains_math_letters_from_poppler(self) -> None:
        """模拟1.pdf 的数学字体没有 ToUnicode：本机有 Poppler 时文字必须补齐。"""
        pdf = Path(__file__).resolve().parents[2] / "testdata" / "20261105" / "模拟1.pdf"
        if not pdf.is_file():
            self.skipTest("本机没有 testdata/20261105/模拟1.pdf")
        data = pdf.read_bytes()
        if not page_render._pdftotext_words(data, 1):
            self.skipTest("本机没有支持 -bbox-layout 的 pdftotext")
        entries, _warnings = page_render._pdf_pages_builtin(data)
        first = entries[0]["regions"][0]["text"]
        self.assertIn("𝜋", first)
        self.assertIn("𝑥", first)


class CrossPageStitchTest(unittest.TestCase):
    """D15：跨页题续页归属与同题纵向拼接。"""

    def _line(self, text: str, top: float, bottom: float,
              left: float = 40, right: float = 2900) -> dict:
        return {"text": text, "left": left, "top": top,
                "right": right, "bottom": bottom}

    def _page(self, lines, regions, *, page_no: int = 1,
              document: str = "paper.pdf", dpi: int = 200,
              width: int = 3000, height: int = 4739):
        return page_render_cross.PageView(
            document=document, page_no=page_no, dpi=dpi, width=width,
            height=height, lines=tuple(lines), regions=tuple(regions))

    def _first_page(self, *, last_bottom: float = 4600) -> object:
        lines = [
            self._line("7. 上一题", 3600, 3700),
            self._line("8. 设数集 M", 4000, 4100),
            self._line("第1页/共3页", 4600, 4640),
        ]
        regions = [
            {"no": 7, "x": 30, "y": 3580, "w": 2900, "h": 300},
            {"no": 8, "x": 30, "y": 3980, "w": 2900, "h": last_bottom - 3980},
        ]
        return self._page(lines, regions)

    def _second_page(self, *extra) -> object:
        lines = [
            self._line("A. 1/3", 150, 230),
            self._line("B. 2/3", 150, 230),
            self._line("C. 1/12", 150, 230),
            self._line("D. 5/12", 150, 230),
        ]
        return self._page(list(lines) + list(extra), [], page_no=2)

    def test_09a_continuation_is_assigned_and_stops_before_next_section(self) -> None:
        """三判据成立：续段归到 Q8，截止在下一节标题之前，标题不进续段。"""
        next_page = self._second_page(
            self._line("二、多项选择题", 360, 400),
            self._line("9. 下一节第一题", 500, 540))
        found = page_render_cross.select_continuation(self._first_page(), next_page)
        self.assertIsNotNone(found)
        self.assertEqual(found.question_no, 8)
        self.assertEqual(found.stop_kind, "next_section")
        self.assertLess(found.bottom, 360, "续段必须停在下一节标题上方")
        texts = [line["text"] for line in found.lines]
        self.assertEqual(texts, ["A. 1/3", "B. 2/3", "C. 1/12", "D. 5/12"])

    def test_09b_no_link_when_last_region_stops_above_footer(self) -> None:
        """本页末题下沿离页脚还远：不算跨页，绝不硬拼。"""
        page = self._first_page(last_bottom=4400)
        self.assertIsNone(page_render_cross.select_continuation(
            page, self._second_page(self._line("二、多项选择题", 360, 400))))

    def test_09c_no_link_when_next_page_opens_with_a_question_head(self) -> None:
        """下一页第一行就是题号行：那是新题，不是本题续段。"""
        next_page = self._page(
            [self._line("9. 下一题", 100, 180), self._line("A. 选项", 200, 280)],
            [], page_no=2)
        self.assertIsNone(page_render_cross.select_continuation(
            self._first_page(), next_page))

    def test_09d_cutoff_is_the_next_head_not_the_page_bottom(self) -> None:
        """没有下一节标题时，截止点仍是下一个题号行，之后的行不许吃进来。"""
        next_page = self._second_page(
            self._line("9. 下一题", 500, 540),
            self._line("A. 下一题的选项", 560, 600))
        found = page_render_cross.select_continuation(self._first_page(), next_page)
        self.assertIsNotNone(found)
        self.assertEqual(found.stop_kind, "next_head")
        self.assertLess(found.bottom, 500)
        self.assertNotIn("下一题的选项", [line["text"] for line in found.lines])

    def _png(self, width: int, height: int, shade: int) -> bytes:
        rows = [bytes([shade]) * (width * 3)] * height
        return page_render_cross._encode_png(width, height, rows)

    def _segments(self, **changes):
        values = {
            "document": "paper.pdf", "question_no": 8, "page_no": 1, "dpi": 200,
            "page_width": 3000, "box": (10, 20, 16, 23),
            "png": self._png(6, 3, 0),
        }
        values.update(changes.get("top", {}))
        top = page_render_cross.Segment(**values)
        values = {
            "document": "paper.pdf", "question_no": 8, "page_no": 2, "dpi": 200,
            "page_width": 3000, "box": (10, 100, 16, 102),
            "png": self._png(6, 2, 0),
        }
        values.update(changes.get("bottom", {}))
        bottom = page_render_cross.Segment(**values)
        return top, bottom

    def test_09e_stitch_keeps_both_segments_and_inserts_seam(self) -> None:
        """拼图保留两段原图与坐标；接缝为纯白，宽度与两段一致。"""
        top, bottom = self._segments()
        stitched = page_render_cross.stitch_cross_page(top, bottom, seam_px=10)
        self.assertIs(stitched.top, top)
        self.assertIs(stitched.bottom, bottom)
        self.assertEqual(stitched.seam_px, 10)
        self.assertEqual((stitched.width, stitched.height), (6, 3 + 10 + 2))
        raster = page_render_cross._decode_png(stitched.png)
        for row in raster.rows[3:13]:
            self.assertEqual(row, b"\xff" * 18, "接缝必须留白，不许直接粘死")

    def test_09f_stitch_rejects_a_mismatched_question_or_paper(self) -> None:
        top, bottom = self._segments(bottom={"question_no": 9})
        with self.assertRaises(page_render_cross.CrossPageError) as caught:
            page_render_cross.stitch_cross_page(top, bottom)
        self.assertTrue(any("同题同卷" in item for item in caught.exception.problems))
        top, bottom = self._segments(bottom={"document": "other.pdf"})
        with self.assertRaises(page_render_cross.CrossPageError):
            page_render_cross.stitch_cross_page(top, bottom)

    def test_09g_stitch_rejects_mismatched_dpi_or_page_width(self) -> None:
        top, bottom = self._segments(bottom={"dpi": 300})
        with self.assertRaises(page_render_cross.CrossPageError) as caught:
            page_render_cross.stitch_cross_page(top, bottom)
        self.assertTrue(any("dpi" in item for item in caught.exception.problems))
        top, bottom = self._segments(bottom={"page_width": 2480})
        with self.assertRaises(page_render_cross.CrossPageError) as caught:
            page_render_cross.stitch_cross_page(top, bottom)
        self.assertTrue(any("页宽" in item for item in caught.exception.problems))

    def test_09h_stitch_rejects_a_seam_outside_eight_to_twelve_px(self) -> None:
        top, bottom = self._segments()
        for seam in (7, 13):
            with self.assertRaises(page_render_cross.CrossPageError) as caught:
                page_render_cross.stitch_cross_page(top, bottom, seam_px=seam)
            self.assertTrue(any("8–12" in item for item in caught.exception.problems))
        page_render_cross.stitch_cross_page(top, bottom, seam_px=8)
        page_render_cross.stitch_cross_page(top, bottom, seam_px=12)

    def test_09i_stitch_rejects_crop_widths_that_do_not_match(self) -> None:
        top, bottom = self._segments(bottom={"png": self._png(5, 2, 0)})
        with self.assertRaises(page_render_cross.CrossPageError) as caught:
            page_render_cross.stitch_cross_page(top, bottom)
        self.assertTrue(any("宽度" in item for item in caught.exception.problems))


class ImagePageTest(PageRenderTestCase):
    def test_01_an_image_is_copied_as_the_source_page(self) -> None:
        entries, doc_pages, warnings = page_render.build_pages(
            "原卷.png", "image", PNG_1X1, "", [_doc("1")])
        self.assertEqual(warnings, [])
        self.assertEqual(doc_pages, [1])
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["name"].endswith(".png"))
        self.assertEqual(self._asset_file(entries[0]).read_bytes(), PNG_1X1)

    def test_02_unknown_image_bytes_are_refused(self) -> None:
        entries, doc_pages, warnings = page_render.build_pages(
            "怪图.png", "image", b"not-an-image", "", [_doc("1")])
        self.assertEqual(entries, [])
        self.assertEqual(doc_pages, [])
        self.assertTrue(warnings)

    def test_03_pdf_pages_spread_across_questions(self) -> None:
        """PDF 没有逐题页号时按顺序均匀摊页，至少保证题与页同序。"""
        self.assertEqual(page_render._spread_pages(0, 3), [])
        self.assertEqual(page_render._spread_pages(1, 3), [1, 1, 1])
        spread = page_render._spread_pages(4, 4)
        self.assertEqual(spread, [1, 2, 3, 4])
        self.assertEqual(spread, sorted(spread))


class BatchPageImageTest(PageRenderTestCase):
    def _save(self, *args, **kwargs) -> dict:
        # 落池即扫是生产行为；这些用例只验页面图，别让后台线程攥着临时库不放。
        with mock.patch.object(pending_bank.pending_dedupe, "warm_dedupe_scan"):
            return pending_bank.save_draft(*args, **kwargs)

    def _draft(self, *, page_images=None) -> dict:
        return self._save(
            {"question": _doc("1"), "page_no": 2},
            source_name="闭环样卷_原卷.docx", page_images=page_images)

    def test_01_page_images_are_kept_on_the_batch_not_the_question(self) -> None:
        entries = [{"name": "pimg_" + "a" * 16 + ".svg", "page": 1}]
        for entry in entries:
            (pending_db.pending_assets_dir()).mkdir(parents=True, exist_ok=True)
            (pending_db.pending_assets_dir() / entry["name"]).write_text(
                "<svg/>", encoding="utf-8")
        result = self._draft(page_images=entries)
        batch_id = result["batch_id"]
        listed = pending_batches.list_batch_questions(batch_id)
        self.assertEqual(listed["page_images"], [
            {"name": entries[0]["name"], "uri": "/static/pending/" + entries[0]["name"],
             "page": 1},
        ])
        self.assertEqual(listed["items"][0]["page_no"], 2)
        self.assertEqual(listed["items"][0]["question"].get("images", []), [],
                         "原卷页只挂批次，不能污染题身的配图")

    def test_01a_auto_regions_survive_batch_round_trip(self) -> None:
        """自动切分框随页图存进批次；越界的坏框直接丢，不让前端画出鬼框。"""
        name = "pimg_" + "f" * 16 + ".png"
        pending_db.pending_assets_dir().mkdir(parents=True, exist_ok=True)
        (pending_db.pending_assets_dir() / name).write_bytes(PNG_1X1)
        entry = {
            "name": name, "page": 1, "width": 1000, "height": 1400,
            "regions": [
                {"no": 1, "x": 10, "y": 20, "w": 300, "h": 400,
                 "label": "1. 第一题", "text": "1. 第一题题干"},
                {"no": 2, "x": 2000, "y": 20, "w": 300, "h": 400},
            ],
        }
        result = self._draft(page_images=[entry])
        listed = pending_batches.list_batch_questions(result["batch_id"])
        page = listed["page_images"][0]
        self.assertEqual((page["width"], page["height"]), (1000, 1400))
        self.assertEqual(len(page["regions"]), 1)
        self.assertEqual(page["regions"][0]["no"], 1)
        self.assertEqual(page["regions"][0]["text"], "1. 第一题题干")

    def test_02_autosave_without_page_images_does_not_clear_them(self) -> None:
        name = "pimg_" + "b" * 16 + ".svg"
        pending_db.pending_assets_dir().mkdir(parents=True, exist_ok=True)
        (pending_db.pending_assets_dir() / name).write_text("<svg/>", encoding="utf-8")
        first = self._draft(page_images=[{"name": name, "page": 1}])
        # 编辑端自动保存只回一道题的正文，不带 page_no：原页号必须原地保留。
        second = self._save({"question": _doc("2")},
                            batch_id=first["batch_id"], origin="editor")
        listed = pending_batches.list_batch_questions(first["batch_id"])
        self.assertEqual([entry["name"] for entry in listed["page_images"]], [name])
        self.assertEqual([item["page_no"] for item in listed["items"]], [2, 1])
        # 明确带了页号才改：老师把这道题重新定位到第 4 页。
        self._save({"question": _doc("2"), "page_no": 4,
                    "pending_id": second["saved_ids"][0]},
                   batch_id=first["batch_id"], origin="editor")
        listed = pending_batches.list_batch_questions(first["batch_id"])
        self.assertEqual([item["page_no"] for item in listed["items"]], [2, 4])
        self.assertTrue(second["saved_ids"])


if __name__ == "__main__":
    unittest.main()
