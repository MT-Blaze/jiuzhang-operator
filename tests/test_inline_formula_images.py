# -*- coding: utf-8 -*-
"""行内位图公式检测（#INLINE-BITMAP-FORMULA-01 刀 B）：三道筛选＋坐标换算＋并单。

覆盖：尺寸边界（44/45/46pt 高、399/400/401pt 宽）／文字行垂直重叠／
左右邻接与孤立图／整页背景/水印/横线/重复项排除／pt→题图像素换算／
无文字层直接空／并进公式裁图清单后原有条目保留且顺序稳定。
运行：``.venv/Scripts/python.exe -m unittest tests.test_inline_formula_images``
"""

from __future__ import annotations

import unittest
from unittest import mock

from app.core.ingest.recognize import formula, inline_formula_images as inline

PAGE_W, PAGE_H = 600.0, 800.0
PIXEL_W, PIXEL_H = 1200.0, 1600.0
REGION = {"x": 100.0, "y": 50.0, "w": 800.0, "h": 300.0}
NEWLINE = ("\n", (0.0, 0.0, 0.0, 0.0))


class FakeTextpage:
    def __init__(self, chars: list[tuple[str, tuple[float, float, float, float]]]):
        self.chars = chars
        self.closed = False

    def count_chars(self) -> int:
        return len(self.chars)

    def get_text_range(self, index: int, count: int = 1) -> str:
        return "".join(char for char, _box in self.chars[index:index + count])

    def get_charbox(self, index: int) -> tuple[float, float, float, float]:
        return self.chars[index][1]

    def close(self) -> None:
        self.closed = True


class FakeObject:
    def __init__(self, bounds: tuple[float, float, float, float]):
        self.bounds = bounds

    def get_bounds(self) -> tuple[float, float, float, float]:
        return self.bounds


class FakePage:
    def __init__(self, images: list[tuple[float, float, float, float]],
                 chars: list[tuple[str, tuple[float, float, float, float]]]):
        self.images = images
        self.chars = chars

    def get_size(self) -> tuple[float, float]:
        return PAGE_W, PAGE_H

    def get_textpage(self) -> FakeTextpage:
        return FakeTextpage(self.chars)

    def get_objects(self, filter=None, max_depth: int = 0):  # noqa: A002 - 对齐 pypdfium2
        return [FakeObject(bounds) for bounds in self.images]


def _char_at(left: float, bottom: float, right: float, top: float,
             text: str = "已") -> tuple[str, tuple[float, float, float, float]]:
    return (text, (left, bottom, right, top))


def _page(images: list[tuple[float, float, float, float]],
          chars: list[tuple[str, tuple[float, float, float, float]]] | None = None) -> FakePage:
    if chars is None:
        chars = [_char_at(55.0, 700.0, 59.5, 712.0), NEWLINE]
    return FakePage(images, chars)


def _detect(page: FakePage, existing=None) -> list[dict]:
    return inline.detect(page, REGION, PAGE_W, PAGE_H, PIXEL_W, PIXEL_H,
                         existing or [])


class SizeBoundaryTest(unittest.TestCase):
    def _height(self, height: float) -> list[dict]:
        center = 706.0
        image = (60.0, center - height / 2, 100.0, center + height / 2)
        return _detect(_page([image]))

    def test_height_44_and_45_pass(self) -> None:
        self.assertEqual(len(self._height(44.0)), 1)
        self.assertEqual(len(self._height(45.0)), 1)

    def test_height_46_rejected(self) -> None:
        self.assertEqual(self._height(46.0), [])

    def _width(self, width: float) -> list[dict]:
        image = (50.0, 696.0, 50.0 + width, 716.0)
        chars = [_char_at(45.0, 700.0, 49.5, 712.0), NEWLINE]
        return _detect(_page([image], chars))

    def test_width_399_and_400_pass(self) -> None:
        self.assertEqual(len(self._width(399.0)), 1)
        self.assertEqual(len(self._width(400.0)), 1)

    def test_width_401_rejected(self) -> None:
        self.assertEqual(self._width(401.0), [])


class RowAndAdjacencyTest(unittest.TestCase):
    def test_center_inside_line_band_hits(self) -> None:
        self.assertEqual(len(_detect(_page([(60.0, 700.0, 100.0, 712.0)]))), 1)

    def test_center_outside_line_band_misses(self) -> None:
        image = (60.0, 754.0, 100.0, 766.0)
        self.assertEqual(_detect(_page([image])), [])

    def test_text_on_left_hits(self) -> None:
        page = _page([(60.0, 700.0, 100.0, 712.0)])
        self.assertEqual(len(_detect(page)), 1)

    def test_text_on_right_hits(self) -> None:
        chars = [_char_at(101.0, 700.0, 105.0, 712.0), NEWLINE]
        page = _page([(60.0, 700.0, 100.0, 712.0)], chars)
        self.assertEqual(len(_detect(page)), 1)

    def test_isolated_image_misses(self) -> None:
        chars = [_char_at(300.0, 700.0, 305.0, 712.0), NEWLINE]
        page = _page([(60.0, 700.0, 100.0, 712.0)], chars)
        self.assertEqual(_detect(page), [])


class ExclusionTest(unittest.TestCase):
    def test_full_page_background_rejected(self) -> None:
        self.assertEqual(_detect(_page([(0.0, 0.0, 600.0, 800.0)])), [])

    def test_wide_watermark_rejected(self) -> None:
        self.assertEqual(_detect(_page([(60.0, 700.0, 440.0, 704.0)])), [])

    def test_horizontal_line_rejected(self) -> None:
        self.assertEqual(_detect(_page([(60.0, 700.0, 450.0, 700.5)])), [])

    def test_duplicate_of_textlayer_span_rejected(self) -> None:
        existing = [{"bbox": [41.6667, 262.5, 166.6667, 50.0], "origin": "textlayer"}]
        self.assertEqual(_detect(_page([(60.0, 700.0, 100.0, 712.0)]), existing), [])

    def test_half_overlap_kept(self) -> None:
        existing = [{"bbox": [0.0, 262.5, 83.3333, 50.0], "origin": "textlayer"}]
        self.assertEqual(len(_detect(_page([(60.0, 700.0, 100.0, 712.0)]), existing)), 1)


class CoordinateTest(unittest.TestCase):
    def test_points_to_crop_pixels(self) -> None:
        page = _page([(60.0, 700.0, 100.0, 712.0)], [_char_at(45.0, 700.0, 49.5, 712.0),
                                                         NEWLINE])
        spans = _detect(page)
        self.assertEqual(len(spans), 1)
        bbox = spans[0]["bbox"]
        self.assertAlmostEqual(bbox[0], (60.0 - 50.0) * 300 / 72.0, places=2)
        self.assertAlmostEqual(bbox[1], ((PAGE_H - 712.0) - 25.0) * 300 / 72.0, places=2)
        self.assertAlmostEqual(bbox[2], 40.0 * 300 / 72.0, places=2)
        self.assertAlmostEqual(bbox[3], 12.0 * 300 / 72.0, places=2)
        self.assertEqual(spans[0]["origin"], "inline_bitmap")
        self.assertEqual(spans[0]["text"], "")

    def test_outside_region_rejected(self) -> None:
        image = (500.0, 700.0, 540.0, 712.0)
        chars = [_char_at(495.0, 700.0, 499.5, 712.0), NEWLINE]
        self.assertEqual(_detect(_page([image], chars)), [])


class NoTextLayerTest(unittest.TestCase):
    def test_zero_chars_returns_empty(self) -> None:
        self.assertEqual(_detect(_page([(60.0, 700.0, 100.0, 712.0)], [])), [])

    def test_whitespace_only_page_returns_empty(self) -> None:
        chars = [(" ", (0.0, 0.0, 1.0, 1.0)), NEWLINE]
        self.assertEqual(_detect(_page([(60.0, 700.0, 100.0, 712.0)], chars)), [])


class MergeAndIntegrationTest(unittest.TestCase):
    def test_merge_keeps_original_and_orders_by_position(self) -> None:
        first = {"bbox": [10.0, 50.0, 20.0, 10.0], "text": "a", "latex": "",
                 "origin": "textlayer"}
        second = {"bbox": [5.0, 10.0, 20.0, 10.0], "text": "b", "latex": "",
                  "origin": "textlayer"}
        inline_span = {"bbox": [30.0, 5.0, 10.0, 10.0], "text": "", "latex": "",
                       "origin": "inline_bitmap"}
        merged = inline.merge_spans([first, second], [inline_span])
        self.assertEqual(len(merged), 3)
        self.assertIs(merged[0], inline_span)
        self.assertIs(merged[1], second)
        self.assertIs(merged[2], first)

    def test_discover_spans_merges_inline_after_textlayer(self) -> None:
        text_span = {"bbox": [0.0, 10.0, 20.0, 10.0], "text": "x", "latex": "",
                     "origin": "textlayer"}
        inline_span = {"bbox": [0.0, 40.0, 20.0, 10.0], "text": "", "latex": "",
                       "origin": "inline_bitmap"}
        pages = [{"page": 1, "width": 1200.0, "height": 1600.0, "regions": []}]
        with mock.patch.object(formula.recognize_shared, "item_image_bytes",
                               return_value=b"png"), \
                mock.patch.object(formula, "_mineru_spans", return_value=[]), \
                mock.patch.object(formula, "_textlayer_spans",
                                  return_value=[text_span]), \
                mock.patch.object(formula.inline_formula_images, "discover",
                                  return_value=[inline_span]) as discovered:
            spans = formula.discover_spans({"id": "p1"}, pages, b"%PDF")
        discovered.assert_called_once()
        self.assertEqual(spans, [text_span, inline_span])


if __name__ == "__main__":
    unittest.main()
