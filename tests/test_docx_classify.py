# -*- coding: utf-8 -*-
"""Word 预分拣判据：A/B/C/D、空文档、坏 zip、缺正文与图形顺序表。

运行：``.venv/Scripts/python.exe -m unittest tests.test_docx_classify``
"""

from __future__ import annotations

import io
import struct
import unittest
import zipfile

from app.core.ingest.intake.docx_classify import DocxProbeError, classify_docx

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
V = "urn:schemas-microsoft-com:vml"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def document(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="%s" xmlns:m="%s" xmlns:r="%s" xmlns:wp="%s"'
        ' xmlns:a="%s" xmlns:v="%s"><w:body>%s</w:body></w:document>'
        % (W, M, R, WP, A, V, body)
    )


def rels(target: str, rel_id: str = "rId5") -> str:
    return (
        '<Relationships xmlns="%s"><Relationship Id="%s"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"'
        ' Target="%s"/></Relationships>' % (REL_NS, rel_id, target)
    )


def png(width: int, height: int) -> bytes:
    """只带 IHDR 的 PNG 头；分拣只读尺寸，不解码像素。"""
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
            + struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00"
            + b"\x00\x00\x00\x00")


def docx(body: str, media: dict[str, bytes] | None = None,
         rel_xml: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document(body))
        for name, payload in (media or {}).items():
            archive.writestr(name, payload)
        if rel_xml is not None:
            archive.writestr("word/_rels/document.xml.rels", rel_xml)
    return buffer.getvalue()


def math_fraction() -> str:
    return ("<m:oMath><m:f><m:num><m:r><m:t>a</m:t></m:r></m:num>"
            "<m:den><m:r><m:t>b</m:t></m:r></m:den></m:f></m:oMath>")


def drawing(rel_id: str) -> str:
    return '<w:r><w:drawing><a:blip r:embed="%s"/></w:drawing></w:r>' % rel_id


class ProbeClassifyTest(unittest.TestCase):
    def test_01_structural_document_is_class_a(self) -> None:
        body = ('<w:p><w:r><w:t>已知函数</w:t></w:r>%s'
                '<w:r><w:t>，求它的值。</w:t></w:r></w:p>' % math_fraction())
        result = classify_docx(docx(body))
        self.assertEqual(result.kind, "A")
        self.assertEqual(result.graphics, [])
        self.assertIn(r"$\frac{a}{b}$", result.text)
        self.assertEqual(result.warnings, [])

    def test_02_text_with_formula_image_is_class_b(self) -> None:
        body = ('<w:p><w:r><w:t>1. 已知函数 f(x) 满足条件，求其最小值'
                '与图象的对称轴方程。</w:t></w:r>%s'
                '<w:r><w:t>并说明理由。</w:t></w:r></w:p>' % drawing("rId5"))
        result = classify_docx(
            docx(body, {"word/media/image1.png": png(80, 30)}, rels("media/image1.png")))
        self.assertEqual(result.kind, "B")
        self.assertIn("[公式图:1]", result.text)
        self.assertTrue(any("第 1 处公式是图片，待后续识别" in text
                            for text in result.warnings))
        graphic = result.graphics[0]
        self.assertTrue(graphic.inline)
        self.assertEqual(graphic.index, 1)
        self.assertEqual(graphic.paragraph, 1)
        self.assertEqual(graphic.media, "word/media/image1.png")
        self.assertTrue(graphic.has_image)

    def test_03_full_page_image_is_class_c(self) -> None:
        body = ('<w:p><w:r><w:t>1</w:t></w:r>%s</w:p>'
                % drawing("rId7"))
        result = classify_docx(
            docx(body, {"word/media/image1.png": png(1240, 1754)},
                 rels("media/image1.png", "rId7")))
        self.assertEqual(result.kind, "C")
        self.assertTrue(result.page_only)
        self.assertEqual(result.text, "")
        self.assertTrue(any("整页扫描图" in text for text in result.warnings))

    def test_04_floating_anchor_is_class_d(self) -> None:
        body = ('<w:p><w:r><w:t>这是一段足够长的正文，用来证明文字层是好的。</w:t></w:r>'
                '<w:r><w:drawing><wp:anchor><a:blip r:embed="rId9"/></wp:anchor>'
                '</w:drawing></w:r></w:p>')
        result = classify_docx(
            docx(body, {"word/media/image1.png": png(80, 30)}, rels("media/image1.png", "rId9")))
        self.assertEqual(result.kind, "D")
        self.assertTrue(any("排版复杂" in text for text in result.warnings))

    def test_05_empty_document(self) -> None:
        result = classify_docx(docx(""))
        self.assertEqual(result.kind, "A")
        self.assertEqual(result.text, "")
        self.assertEqual(result.graphics, [])

    def test_06_scan_with_header_logo_is_still_class_c(self) -> None:
        body = '<w:p><w:r><w:t>1</w:t></w:r>%s</w:p>' % drawing("rId7")
        result = classify_docx(docx(
            body,
            {"word/media/scan.png": png(1240, 1754), "word/media/logo.png": png(120, 40)},
            rels("media/scan.png", "rId7")))
        self.assertEqual(result.kind, "C")
        self.assertTrue(result.page_only)


class ProbeFailureTest(unittest.TestCase):
    def test_01_broken_zip_raises_bad_zip_file(self) -> None:
        with self.assertRaises(zipfile.BadZipFile):
            classify_docx(b"this is not a zip")

    def test_02_missing_document_xml_raises_probe_error(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/styles.xml", "<x/>")
        with self.assertRaises(DocxProbeError):
            classify_docx(buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
