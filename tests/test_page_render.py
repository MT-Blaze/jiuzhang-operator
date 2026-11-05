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
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import (  # noqa: E402
    page_render, pending_assets, pending_bank, pending_batches, pending_db,
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

    def test_03_empty_text_never_invents_a_page(self) -> None:
        """抽不出文字的 PDF 不编页面：没有源文本就交白卷。"""
        entries, doc_pages, _warnings = page_render.build_pages(
            "扫描件.pdf", "pdf", b"%PDF-1.4", "", [_doc("1")])
        self.assertEqual(entries, [])
        self.assertEqual(doc_pages, [])


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
