"""扫描版 PDF（无可用文本层）的入库判据。

钉住四条：
- 文本层抽不出时，**一条占位题都不落池**——只把 PDF 拆成原卷页面图；
- 页面图挂到批次上，老师进批次后在左侧自己【框选切题】；
- 页数按**实际渲染出的页面图**算，不认文本解析猜的数；
- 渲染器缺席时同样不造假题，批次空着等老师处理。

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

from app.core import ingest, pending_bank  # noqa: E402


def _pages(count: int) -> list[dict[str, Any]]:
    return [
        {"name": f"pimg_page{index:04d}.png", "uri": f"/static/pending/pimg_page{index:04d}.png",
         "page": index}
        for index in range(1, count + 1)
    ]


class ScanModeDetectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_pdf_without_text_layer_returns_no_documents(self) -> None:
        with mock.patch.object(ingest, "extract_pdf_text", return_value=("乱码", 1)), \
                mock.patch.object(ingest, "_text_usable", return_value=False):
            documents, warnings, kind, text, scan = await ingest._items_from_file(
                "模拟1.pdf", b"%PDF-1.7")
        self.assertTrue(scan)
        self.assertEqual(kind, "pdf")
        self.assertEqual(text, "")
        self.assertEqual(documents, [])
        self.assertTrue(any("框选切题" in warning for warning in warnings))

    async def test_usable_text_does_not_enter_scan_mode(self) -> None:
        with mock.patch.object(ingest, "extract_pdf_text",
                               return_value=("1. 求 $x+1=2$ 的解。\n2. 求 $x-1=0$ 的解。", 1)):
            documents, _warnings, _kind, _text, scan = await ingest._items_from_file(
                "文本层.pdf", b"%PDF-1.7")
        self.assertFalse(scan)
        self.assertGreaterEqual(len(documents), 1)


class StagePageOnlyTest(unittest.TestCase):
    """纯图片 PDF 在立批次时就不该有占位题。"""

    def test_page_only_pdf_creates_batch_without_questions(self) -> None:
        created = {"batch_id": "B-001", "batch": {"batch_id": "B-001"},
                   "saved_ids": [], "dedupe_queued": False}
        with mock.patch.object(ingest, "_page_only_pdf", return_value=True), \
                mock.patch.object(pending_bank, "store_source_backup",
                                  return_value="pending_backup/x.pdf"), \
                mock.patch.object(pending_bank, "create_batch", return_value=created) as create, \
                mock.patch.object(pending_bank, "save_draft") as save:
            result = ingest._stage_one_batch("模拟1.pdf", b"%PDF")
        create.assert_called_once()
        self.assertTrue(create.call_args.kwargs["scan"])
        save.assert_not_called()
        self.assertEqual(result["saved_ids"], [])
        self.assertTrue(result["page_only"])
        self.assertTrue(any("框选切题" in text for text in result["warnings"]))
        self.assertEqual(result["jobs"][0]["pending_id"], "")
        self.assertTrue(result["jobs"][0]["page_only"])

    def test_text_pdf_still_uses_parsing_placeholder(self) -> None:
        saved = {"batch_id": "B-002", "batch": {"batch_id": "B-002"},
                 "saved_ids": ["p_placeholder01"], "dedupe_queued": False}
        with mock.patch.object(ingest, "_page_only_pdf", return_value=False), \
                mock.patch.object(pending_bank, "store_source_backup",
                                  return_value="pending_backup/y.pdf"), \
                mock.patch.object(pending_bank, "save_draft", return_value=saved) as save:
            result = ingest._stage_one_batch("文本层.pdf", b"%PDF")
        save.assert_called_once()
        self.assertEqual(result["jobs"][0]["pending_id"], "p_placeholder01")
        self.assertFalse(result["jobs"][0]["page_only"])


class RunJobsScanExpansionTest(unittest.IsolatedAsyncioTestCase):
    """页数只认渲染出来的页面图；扫描卷只挂页图，不落题。"""

    async def test_page_only_job_attaches_pages_and_saves_nothing(self) -> None:
        pages = _pages(2)
        with mock.patch.object(ingest.page_render, "build_pages",
                               return_value=(pages, [1, 2], [])), \
                mock.patch.object(pending_bank, "set_batch_pages") as set_pages, \
                mock.patch.object(pending_bank, "save_draft") as save:
            await ingest.run_ingest_jobs("B-001", [{
                "pending_id": "", "name": "模拟1.pdf", "data": b"%PDF", "page_only": True,
            }])
        set_pages.assert_called_once_with("B-001", pages)
        save.assert_not_called()

    async def test_renderer_missing_still_saves_nothing(self) -> None:
        with mock.patch.object(ingest.page_render, "build_pages",
                               return_value=([], [], [])), \
                mock.patch.object(pending_bank, "set_batch_pages") as set_pages, \
                mock.patch.object(pending_bank, "save_draft") as save:
            await ingest.run_ingest_jobs("B-002", [{
                "pending_id": "", "name": "无渲染器.pdf", "data": b"%PDF", "page_only": True,
            }])
        set_pages.assert_not_called()
        save.assert_not_called()

    async def test_legacy_scan_placeholder_is_cleaned_after_pages_attach(self) -> None:
        pages = _pages(1)
        with mock.patch.object(
                ingest, "_items_from_file",
                new=mock.AsyncMock(return_value=([], [], "pdf", "", True))), \
                mock.patch.object(ingest.page_render, "build_pages",
                                  return_value=(pages, [1], [])), \
                mock.patch.object(pending_bank, "set_batch_pages") as set_pages, \
                mock.patch.object(pending_bank, "delete_pending") as delete, \
                mock.patch.object(pending_bank, "save_draft") as save:
            await ingest.run_ingest_jobs("B-003", [{
                "pending_id": "p_placeholder02", "name": "老占位.pdf", "data": b"%PDF",
            }])
        set_pages.assert_called_once_with("B-003", pages)
        delete.assert_called_once_with("p_placeholder02")
        save.assert_not_called()

    async def test_non_scan_documents_are_replaced_in_place(self) -> None:
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
                mock.patch.object(pending_bank, "save_draft", side_effect=capture):
            await ingest.run_ingest_jobs("B-004", [{
                "pending_id": "p_placeholder03", "name": "卷子.docx", "data": b"PK",
            }])

        self.assertEqual(len(saved), 2)
        self.assertEqual([item["question"]["stem"] for item in saved], ["真题一道", "真题两道"])
        self.assertEqual(saved[0]["pending_id"], "p_placeholder03")


if __name__ == "__main__":
    unittest.main()
