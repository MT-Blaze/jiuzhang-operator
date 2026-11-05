"""扫描版 PDF（无可用文本层）的入库判据。

钉住三条：
- 文本层抽不出时，绝不把整页冒充成一道题——每页一条「原卷页入口」，
  题干明写未识别、指路左侧手动框选与切分新题；
- 页数按**实际渲染出的页面图**算：PDF 的页对象可能压在对象流里，
  文本解析数出来的页数不可信（真实卷子曾因此 5 页只落 1 条）；
- 页面渲染器缺席时退成一条，并提示老师贴入页面截图再框选。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ingest_scan``
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import ingest  # noqa: E402

GUIDE = "未识别出文本"


class ScanGuideLabelTest(unittest.TestCase):
    def test_one_entry_per_rendered_page(self) -> None:
        guides = ingest._scan_guides("模拟1.pdf", 5)
        self.assertEqual(len(guides), 5)
        for page, guide in enumerate(guides, start=1):
            self.assertEqual(guide["type"], "solution")
            self.assertEqual(guide["tags"], ["待识别"])
            self.assertIn(GUIDE, guide["stem"])
            self.assertIn(f"第 {page}/5 页", guide["stem"])
            self.assertIn("切分新题", guide["stem"])
            self.assertIn("原卷页入口", guide["stem"])

    def test_single_page_reads_as_first_page(self) -> None:
        guides = ingest._scan_guides("一页.pdf", 1)
        self.assertEqual(len(guides), 1)
        self.assertIn("第 1 页", guides[0]["stem"])
        self.assertNotIn("1/1", guides[0]["stem"])

    def test_renderer_missing_points_to_paste_screenshot(self) -> None:
        guides = ingest._scan_guides("无渲染器.pdf", 0)
        self.assertEqual(len(guides), 1)
        self.assertIn("没有 PDF 页面渲染器", guides[0]["stem"])
        self.assertIn("粘贴", guides[0]["stem"])

    def test_page_entries_are_capped(self) -> None:
        self.assertEqual(len(ingest._scan_guides("厚卷.pdf", 200)), 40)


class ScanModeDetectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_pdf_without_text_layer_enters_scan_mode(self) -> None:
        with mock.patch.object(ingest, "extract_pdf_text", return_value=("乱码", 1)), \
                mock.patch.object(ingest, "_text_usable", return_value=False):
            documents, warnings, kind, text, scan = await ingest._items_from_file(
                "模拟1.pdf", b"%PDF-1.7")
        self.assertTrue(scan)
        self.assertEqual(kind, "pdf")
        self.assertEqual(text, "")
        self.assertEqual(len(documents), 1)
        self.assertIn(GUIDE, documents[0]["stem"])
        self.assertTrue(any("未识别出文本" in warning for warning in warnings))

    async def test_usable_text_does_not_enter_scan_mode(self) -> None:
        with mock.patch.object(ingest, "extract_pdf_text",
                               return_value=("1. 求 $x+1=2$ 的解。\n2. 求 $x-1=0$ 的解。", 1)):
            documents, _warnings, _kind, _text, scan = await ingest._items_from_file(
                "文本层.pdf", b"%PDF-1.7")
        self.assertFalse(scan)
        self.assertGreaterEqual(len(documents), 1)


class RunJobsScanExpansionTest(unittest.IsolatedAsyncioTestCase):
    """页数只认渲染出来的页面图，不认文本解析猜的页数。"""

    async def test_guides_follow_rendered_page_count(self) -> None:
        base = ingest._placeholder(f"（{GUIDE}：占位）")
        pages = [
            {"name": "pimg_1.png", "uri": "/static/pending/pimg_1.png", "page": 1},
            {"name": "pimg_2.png", "uri": "/static/pending/pimg_2.png", "page": 2},
        ]
        saved: list[dict[str, Any]] = []

        def capture(items: Any, **_kwargs: Any) -> dict[str, Any]:
            saved.extend(items)
            return {"saved_ids": [item.get("pending_id") or "p_new" for item in items]}

        with mock.patch.object(ingest, "_items_from_file",
                               new=mock.AsyncMock(return_value=([base], [], "pdf", "", True))), \
                mock.patch.object(ingest.page_render, "build_pages",
                                  return_value=(pages, [1], [])), \
                mock.patch("app.core.pending_bank.save_draft", side_effect=capture):
            await ingest.run_ingest_jobs("B-001", [{
                "pending_id": "p_placeholder01", "name": "模拟1.pdf", "data": b"%PDF",
            }])

        self.assertEqual(len(saved), 2)
        self.assertEqual([item["page_no"] for item in saved], [1, 2])
        self.assertIn("第 1/2 页", saved[0]["question"]["stem"])
        self.assertIn("第 2/2 页", saved[1]["question"]["stem"])
        self.assertEqual(saved[0]["pending_id"], "p_placeholder01")

    async def test_non_scan_documents_are_not_expanded(self) -> None:
        documents = [ingest._placeholder("真题一道"), ingest._placeholder("真题两道")]
        saved: list[dict[str, Any]] = []

        def capture(items: Any, **_kwargs: Any) -> dict[str, Any]:
            saved.extend(items)
            return {"saved_ids": ["p_x"]}

        with mock.patch.object(
                ingest, "_items_from_file",
                new=mock.AsyncMock(return_value=(documents, [], "docx", "源文本", False))), \
                mock.patch.object(ingest.page_render, "build_pages",
                                  return_value=([], [1, 1], [])), \
                mock.patch("app.core.pending_bank.save_draft", side_effect=capture):
            await ingest.run_ingest_jobs("B-002", [{
                "pending_id": "p_placeholder02", "name": "卷子.docx", "data": b"PK",
            }])

        self.assertEqual(len(saved), 2)
        self.assertEqual([item["question"]["stem"] for item in saved], ["真题一道", "真题两道"])


if __name__ == "__main__":
    unittest.main()
