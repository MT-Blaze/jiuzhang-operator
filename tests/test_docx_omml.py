# -*- coding: utf-8 -*-
"""OMML → LaTeX 转换判据：最低覆盖 + 未知节点保真。

运行：``.venv/Scripts/python.exe -m unittest tests.test_docx_omml``
"""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from app.core.ingest.intake.docx_omml import omml_to_latex

MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def math_node(inner: str) -> ET.Element:
    return ET.fromstring('<m:oMath xmlns:m="%s">%s</m:oMath>' % (MATH_NS, inner))


def run(text: str) -> str:
    return "<m:r><m:t>%s</m:t></m:r>" % text


class OmmlConvertTest(unittest.TestCase):
    def test_01_fraction(self) -> None:
        node = math_node(
            "<m:f><m:num>%s</m:num><m:den>%s</m:den></m:f>" % (run("a"), run("b")))
        result = omml_to_latex(node)
        self.assertEqual(result.latex, r"\frac{a}{b}")
        self.assertEqual(result.warnings, [])

    def test_02_superscript_and_subscript(self) -> None:
        sup = math_node(
            "<m:sSup><m:e>%s</m:e><m:sup>%s</m:sup></m:sSup>" % (run("x"), run("2")))
        self.assertEqual(omml_to_latex(sup).latex, "x^{2}")
        sub = math_node(
            "<m:sSub><m:e>%s</m:e><m:sub>%s</m:sub></m:sSub>" % (run("a"), run("i")))
        self.assertEqual(omml_to_latex(sub).latex, "a_{i}")

    def test_03_root_without_degree(self) -> None:
        node = math_node(
            "<m:rad><m:radPr><m:degHide m:val=\"1\"/></m:radPr>"
            "<m:deg/><m:e>%s</m:e></m:rad>" % run("x"))
        self.assertEqual(omml_to_latex(node).latex, r"\sqrt{x}")

    def test_04_summation(self) -> None:
        node = math_node(
            "<m:nary><m:naryPr><m:chr m:val=\"∑\"/></m:naryPr>"
            "<m:sub>%s</m:sub><m:sup>%s</m:sup><m:e>%s</m:e></m:nary>"
            % (run("i=1"), run("n"), run("i")))
        self.assertEqual(omml_to_latex(node).latex, r"\sum_{i=1}^{n} i")

    def test_05_greek_letter(self) -> None:
        node = math_node(run("α") + run("+") + run("β"))
        self.assertEqual(omml_to_latex(node).latex, r"\alpha +\beta")

    def test_06_delimiter(self) -> None:
        node = math_node(
            "<m:d><m:dPr><m:begChr m:val=\"(\"/><m:endChr m:val=\")\"/></m:dPr>"
            "<m:e>%s</m:e></m:d>" % run("x"))
        self.assertEqual(omml_to_latex(node).latex, r"\left( x \right)")

    def test_07_unknown_node_keeps_text_and_warns(self) -> None:
        node = math_node("<m:weird>%s</m:weird>" % run("Q"))
        result = omml_to_latex(node)
        self.assertIn("Q", result.latex)
        self.assertTrue(any("未识别的 OMML 节点 m:weird" in text
                            for text in result.warnings))


if __name__ == "__main__":
    unittest.main()
