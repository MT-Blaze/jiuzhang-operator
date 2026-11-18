"""A2 图片型卷第一刀（T4＋T8）定向单测。

运行：``.venv/Scripts/python.exe -m unittest tests.test_a2_image_ingest``
覆盖：OCR 行预处理（去重/补点/坐标回换）、栏内单调与分栏参数、
链门禁（回跳/密度）、跨页编排（两段原图留存）、判据(a)空白分支、run_scan 主路。
"""

import asyncio
import unittest
from unittest import mock

from app.core.ingest.layout import python as text_layout, router as layout_router
from app.core.ingest.recognize import crosspage, guards, ocr
from app.core.ingest.render import cross
from app.core.ingest.route import new_ledger


def _row(text, x0, y0, x1, y1, score=0.9):
    return {"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "score": score}


def _up(text, left, top, right=None, bottom=None):
    return {"text": text, "left": left, "top": top,
            "right": right if right is not None else left + 400,
            "bottom": bottom if bottom is not None else top - 40, "missing": 0}


class OcrPreprocessTest(unittest.TestCase):
    def test_01_dedupe_keeps_higher_score_on_overlap(self):
        rows = [_row("19.(本小题12分)", 200, 150, 500, 200, 0.99),
                _row("22.(本小题12分)", 205, 152, 495, 198, 0.80),
                _row("20.(本小题12分)", 200, 500, 500, 550, 0.95)]
        kept = ocr._dedupe(rows)
        self.assertEqual([r["text"] for r in kept],
                         ["19.(本小题12分)", "20.(本小题12分)"])

    def test_02_dedupe_keeps_disjoint_boxes(self):
        rows = [_row("A. 1/3", 40, 100, 200, 160),
                _row("B. 2/3", 400, 100, 560, 160)]
        self.assertEqual(len(ocr._dedupe(rows)), 2)

    def test_03_dotless_head_repaired_only_with_both_neighbours(self):
        up = [_up("16. 已知a<0", 40, 900), _up("17 已知集合A", 40, 700),
              _up("18. 已知二次函数", 40, 500), _up("5 随便一行", 40, 300)]
        fixed_up, fixed = ocr._repair_dotless(up)
        self.assertEqual(fixed, [17])
        self.assertTrue(fixed_up[1]["text"].startswith("17. "))
        self.assertEqual(fixed_up[3]["text"], "5 随便一行")

    def test_04_unrotate_round_trips_both_directions(self):
        box = (100.0, 200.0, 300.0, 400.0)
        for k in (1, 3):
            width, height = 1653, 2339
            x0, y0, x1, y1 = box
            if k == 1:
                rot = (y0, width - 1 - x1, y1, width - 1 - x0)
            else:
                rot = (height - 1 - y1, x0, height - 1 - y0, x1)
            back = ocr._unrotate_box(rot, k, width, height)
            self.assertEqual(tuple(round(v) for v in back),
                             tuple(round(v) for v in box))

    def test_05_column_chain_drops_backward_fake_head(self):
        up = [_up("8. 设三角形", 840, 2000), _up("9. 下列说法", 840, 1700),
              _up("10. 在三角形中", 840, 1400), _up("11. 下列关于向量", 840, 1100),
              _up("1.1", 840, 900, right=880, bottom=860),
              _up("1. sin", 60, 2000), _up("2. 已知向量", 60, 1700),
              _up("A. 选项内容", 60, 1500)]
        regions, columns, score = ocr._chain(up, 1653, 2339, bytearray(2339), True)
        self.assertEqual(columns, 2)
        self.assertEqual([r["no"] for r in regions if r["x"] > 800], [8, 9, 10, 11])
        self.assertEqual(score, 6)


class ColumnParamsTest(unittest.TestCase):
    def _info(self, right_heads=1):
        lines = [_up("1. 甲", 60, 2000), _up("2. 乙", 60, 1700),
                 _up("3. 丙", 60, 1400)]
        lines += [_up("题干正文", 60, top) for top in (1900, 1600, 1300, 1000)]
        lines += [_up("8. 丁", 1200, 2000 - i * 300) for i in range(right_heads)]
        return {"width_pt": 1653.0, "height_pt": 2339.0, "lines": lines}

    def test_06_default_requires_two_heads_per_side(self):
        self.assertIsNone(text_layout._column_split(self._info(1)))
        self.assertIsNotNone(text_layout._column_split(self._info(2)))

    def test_07_min_heads_one_accepts_last_single_question_column(self):
        self.assertIsNotNone(text_layout._column_split(self._info(1), 0.015, 1))

    def test_08_gutter_ratio_relaxes_landscape_gutter(self):
        info = self._info(2)
        for line in info["lines"]:
            if line["left"] < 800:
                line["right"] = 1170
        self.assertIsNone(text_layout._column_split(info))
        self.assertIsNotNone(text_layout._column_split(info, 0.015))


class ChainGuardsTest(unittest.TestCase):
    def _entries(self):
        return [{"page": 1, "regions": [{"no": n} for n in (1, 2, 3)]},
                {"page": 2, "regions": [{"no": n} for n in (4, 5)]}]

    def test_09_backward_page_dropped_with_per_page_failure(self):
        entries = self._entries()
        entries.append({"page": 3, "regions": [{"no": n} for n in (4, 5)]})
        ledger = new_ledger()
        notes = guards.apply_chain_guards(entries, ledger=ledger, file="卷.pdf")
        self.assertEqual(entries[2]["regions"], [])
        self.assertEqual([f["page_no"] for f in ledger["failures"]], [3])
        self.assertEqual(ledger["failures"][0]["step"], "自动切题·P3")
        self.assertTrue(notes)

    def test_10_increasing_pages_pass(self):
        entries = self._entries()
        ledger = new_ledger()
        self.assertEqual(guards.apply_chain_guards(entries, ledger=ledger), [])
        self.assertEqual(ledger["failures"], [])

    def test_11_density_floor_drops_whole_file(self):
        entries = [{"page": 1, "regions": [{"no": 1}]},
                   {"page": 2, "regions": []}, {"page": 3, "regions": []}]
        notes = guards.apply_chain_guards(entries)
        self.assertTrue(all(not e["regions"] for e in entries))
        self.assertIn("密度", notes[0])

    def test_12_ocr_lines_without_chain_get_per_page_failure(self):
        entries = [{"page": 1, "regions": []}]
        ledger = new_ledger()
        guards.apply_chain_guards(entries, {1: [{"text": "图"}]},
                                  ledger=ledger, file="卷.pdf")
        self.assertEqual([f["page_no"] for f in ledger["failures"]], [1])


class CrossBlankBranchTest(unittest.TestCase):
    def _page(self, last_bottom, ink_bottom):
        lines = [{"text": "8. 设数集 M", "left": 40, "top": 4000,
                  "right": 2900, "bottom": ink_bottom},
                 {"text": "第1页/共3页", "left": 1200, "top": 4600,
                  "right": 1600, "bottom": 4640}]
        regions = [{"no": 8, "x": 30, "y": 3980, "w": 2900,
                    "h": last_bottom - 3980}]
        return cross.PageView(document="卷.pdf", page_no=1, dpi=200, width=3000,
                              height=4739, lines=tuple(lines), regions=tuple(regions))

    def _next(self):
        lines = [{"text": "A. 1/3", "left": 40, "top": 150,
                  "right": 300, "bottom": 230}]
        return cross.PageView(document="卷.pdf", page_no=2, dpi=200, width=3000,
                              height=4739, lines=tuple(lines), regions=())

    def test_13_blank_before_footer_still_links_when_box_hugs_ink(self):
        found = cross.select_continuation(self._page(4295, 4285), self._next())
        self.assertIsNotNone(found)
        self.assertEqual(found.question_no, 8)

    def test_14_padded_box_tail_does_not_link(self):
        self.assertIsNone(cross.select_continuation(self._page(4400, 4100),
                                                    self._next()))


class CrossPageOrchestrationTest(unittest.TestCase):
    def _png(self, width, height):
        return cross._encode_png(width, height,
                                 [bytes([255, 255, 255] * width)] * height)

    def test_15_stitch_replaces_main_png_and_keeps_both_segments(self):
        entries = [{"page": 1, "width": 3000, "height": 4739,
                    "regions": [{"no": 8, "x": 30, "y": 3980, "w": 2900, "h": 315}]},
                   {"page": 2, "width": 3000, "height": 4739, "regions": []}]
        lines = {1: [{"text": "8. 设数集 M", "left": 40, "top": 4000,
                      "right": 2900, "bottom": 4285},
                     {"text": "第1页/共3页", "left": 1200, "top": 4600,
                      "right": 1600, "bottom": 4640}],
                 2: [{"text": "A. 1/3", "left": 40, "top": 150,
                      "right": 300, "bottom": 230},
                     {"text": "9. 下一题", "left": 40, "top": 600,
                      "right": 2900, "bottom": 660}]}
        main_png = self._png(60, 20)
        crops = {1: [{"index": 0, "no": 8, "region": dict(entries[0]["regions"][0]),
                      "png": main_png, "width": 60, "height": 20}]}

        def fake_crop(data, synth, dpi=300):
            made = {}
            for entry in synth:
                region = entry["regions"][0]
                made[entry["page"]] = [{"index": 0, "no": region["no"],
                                        "region": region,
                                        "png": self._png(60, 10),
                                        "width": 60, "height": 10}]
            return made, []

        with mock.patch.object(crosspage.page_render, "crop_pdf_regions", fake_crop):
            extra, trace, notes = crosspage.stitch_cross_questions(
                "卷.pdf", b"", entries, lines, {1: 1, 2: 1}, crops)
        key = (1, 0)
        self.assertIn(key, trace)
        self.assertEqual(trace[key]["cross_page"]["pages"], [1, 2])
        self.assertEqual(trace[key]["cross_page"]["seam_px"], 10)
        self.assertEqual(len(extra[key]), 2)
        self.assertNotEqual(crops[1][0]["png"], main_png)
        self.assertEqual(crops[1][0]["height"], 30)
        self.assertEqual(notes, [])
        self.assertIn("A. 1/3", entries[0]["regions"][0]["text"])

    def test_16_two_column_pages_are_not_stitched(self):
        entries = [{"page": 1, "width": 3000, "height": 4739,
                    "regions": [{"no": 7, "x": 30, "y": 3980, "w": 1400, "h": 315}]},
                   {"page": 2, "width": 3000, "height": 4739, "regions": []}]
        crops = {1: [{"index": 0, "no": 7, "region": dict(entries[0]["regions"][0]),
                      "png": self._png(60, 20), "width": 60, "height": 20}]}
        extra, trace, notes = crosspage.stitch_cross_questions(
            "卷.pdf", b"", entries, {}, {1: 2, 2: 2}, crops)
        self.assertEqual((extra, trace, notes), ({}, {}, []))


class RegionWhitelistTest(unittest.TestCase):
    def test_20_cross_trace_survives_page_region_whitelist(self):
        from app.core.pending.batch import bank_batches
        region = {"no": 8, "x": 30, "y": 3980, "w": 2900, "h": 315,
                  "cross_page": {"pages": [1, 2], "top_box": [1, 2, 3, 4],
                                 "bottom_box": [5, 6, 7, 8], "seam_px": 10,
                                 "stop_kind": "next_section"}}
        kept = bank_batches._page_regions([region], 3000, 4739)
        self.assertEqual(kept[0]["cross_page"]["pages"], [1, 2])
        self.assertEqual(kept[0]["cross_page"]["seam_px"], 10)
        self.assertEqual(kept[0]["cross_page"]["stop_kind"], "next_section")
        bad = dict(region, cross_page={"pages": "不是数组"})
        kept = bank_batches._page_regions([bad], 3000, 4739)
        self.assertNotIn("cross_page", kept[0])


class RunScanTest(unittest.TestCase):
    def test_17_text_layer_goes_straight_to_waterfall(self):
        calls = []

        def python_provider(request):
            calls.append("python")
            return {"ok": True, "pages": {1: [{"no": 1}]}}

        with mock.patch.object(ocr, "detect") as detect:
            outcome = asyncio.run(layout_router.run_scan(
                "卷.pdf", b"", [{"page": 1}], "auto",
                {"has_text_layer": True}, {"python": python_provider}))
        detect.assert_not_called()
        self.assertEqual(calls, ["python"])
        self.assertEqual(outcome["engine"], "python")

    def test_18_image_paper_ocr_wins_without_waterfall(self):
        layout = {"ok": True, "engine": "ocr", "pages": {1: [{"no": 1}]},
                  "lines_by_page": {1: []}}
        with mock.patch.object(ocr, "detect", return_value=layout) as detect:
            outcome = asyncio.run(layout_router.run_scan(
                "卷.pdf", b"", [{"page": 1}], "auto", {"has_text_layer": False}, {}))
        detect.assert_called_once()
        self.assertEqual(outcome["engine"], "ocr")
        self.assertIn("lines_by_page", outcome)

    def test_19_ocr_failure_falls_back_to_waterfall(self):
        def python_provider(request):
            return {"ok": True, "pages": {1: [{"no": 1}]}}

        with mock.patch.object(ocr, "detect", return_value={"ok": False}):
            outcome = asyncio.run(layout_router.run_scan(
                "卷.pdf", b"", [{"page": 1}], "auto", {"has_text_layer": False},
                {"python": python_provider}))
        self.assertEqual(outcome["engine"], "python")


if __name__ == "__main__":
    unittest.main()