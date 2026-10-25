"""题库图片资产校验脚本契约（军令 #21 任务五）。

脚本是「一次性查漏补缺」的眼睛，必须同时看清三种缺口：
  1. 引用了 ``/static/uploads/`` 但文件不在 uploads（可补）；
  2. 选项 image_ids 指向不存在的 image 条目（悬空）；
  3. 迁移器写下的「〔原卷配图缺失〕」占位符——图已经不在 uri 里，只扫引用会漏掉。

补齐只许新增、绝不覆盖，也绝不改数据库。全部用例在临时目录里跑，不碰真实 ``data/``。

运行：``.venv/Scripts/python.exe -m unittest tests.test_image_assets``
"""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools import check_image_assets


SEVEN_TABLE = (
    "create table questions (id text primary key, stem text, solution text, "
    "options text, extensions text)"
)
WIDE_TABLE = (
    "create table questions (id text primary key, stem text, solution text, "
    "options_json text, images_json text)"
)


def make_bank(path: Path, ddl: str, rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.execute(ddl)
        con.executemany("insert into questions values (?, ?, ?, ?, ?)", rows)
        con.commit()
    finally:
        con.close()


def image_entry(image_id: str, uri: str, role: str = "stem") -> dict:
    return {"id": image_id, "uri": uri, "role": role, "alt": "图"}


class AuditReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        (self.data / "uploads").mkdir(parents=True)
        (self.data / "uploads" / "a.png").write_bytes(b"real-a")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_tool(self, *extra: str) -> tuple[int, str, dict]:
        report_path = Path(self.tmp.name) / "report.json"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = check_image_assets.main(
                ["--data-dir", str(self.data), "--json", str(report_path), *extra]
            )
        payload = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        return code, buf.getvalue(), payload

    def test_01_seven_table_reports_missing_dangling_and_placeholder(self) -> None:
        make_bank(
            self.data / "banks" / "a.db",
            SEVEN_TABLE,
            [
                ("q1", "题一 ![配图](/static/uploads/a.png)", "",
                 json.dumps([{"key": "A", "content": "甲"}], ensure_ascii=False),
                 json.dumps([{"key": "org.demo.images", "value": {
                     "images": [image_entry("img_a", "/static/uploads/a.png")]}}],
                     ensure_ascii=False)),
                ("q2", "题二 \\includegraphics{/static/uploads/b.png}", "",
                 json.dumps([{"key": "A", "content": "", "image_ids": ["img_missing"]}],
                            ensure_ascii=False),
                 "[]"),
                ("q3", "〔原卷配图缺失〕题干", "〔原卷配图缺失〕", "[]", "[]"),
            ],
        )
        code, out, report = self.run_tool()
        self.assertEqual(code, 0)
        item = report["reports"][0]
        self.assertEqual(item["questions"], 3)
        self.assertEqual(list(item["missing"]), ["/static/uploads/b.png"])
        self.assertEqual(item["dangling_option_links"],
                         [{"question": "q2", "image_id": "img_missing"}])
        self.assertEqual(item["placeholder_count"], 2)
        self.assertIn("q3", item["placeholder_rows"])
        self.assertEqual(item["option_links"], 1)
        self.assertIn("缺失 1 张", out)

    def test_02_wide_table_and_non_local_references(self) -> None:
        make_bank(
            self.data / "banks" / "wide.db",
            WIDE_TABLE,
            [("w1", "![a](https://example.com/a.png) ![b](asset://x.png)", "",
              "[]", json.dumps([image_entry("img_1", "/static/uploads/a.png")],
                               ensure_ascii=False))],
        )
        _, _, report = self.run_tool()
        item = report["reports"][0]
        self.assertEqual(item["distinct_uris"], 3)
        self.assertEqual(item["missing"], {})
        # 远程与 asset:// 只计数，绝不当作「缺图」去补
        self.assertEqual(len(item["non_local"]), 2)

    def test_03_apply_adds_missing_file_without_overwriting(self) -> None:
        make_bank(
            self.data / "banks" / "a.db",
            SEVEN_TABLE,
            [("q1", "![配图](/static/uploads/b.png)", "", "[]", "[]")],
        )
        source = Path(self.tmp.name) / "source"
        source.mkdir()
        (source / "b.png").write_bytes(b"from-source")

        code, _, report = self.run_tool("--source", str(source), "--apply")
        self.assertEqual(code, 0)
        self.assertEqual((self.data / "uploads" / "b.png").read_bytes(), b"from-source")
        self.assertEqual(len(report["reports"][0]["restored"]), 1)
        self.assertEqual(report["reports"][0]["missing"], {})

        # 再来一次：文件已在 uploads，绝不许被同名副本覆盖
        (source / "b.png").write_bytes(b"different")
        _, _, second = self.run_tool("--source", str(source), "--apply")
        self.assertEqual((self.data / "uploads" / "b.png").read_bytes(), b"from-source")
        self.assertEqual(second["reports"][0]["restored"], [])

    def test_04_database_is_never_written(self) -> None:
        db = self.data / "banks" / "a.db"
        make_bank(db, SEVEN_TABLE, [("q1", "![配图](/static/uploads/a.png)", "", "[]", "[]")])
        before = db.read_bytes()
        self.run_tool("--apply")
        self.assertEqual(db.read_bytes(), before)

    def test_05_skips_databases_without_questions(self) -> None:
        other = self.data / "banks" / "empty.db"
        other.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(other)
        try:
            con.execute("create table notes (id integer)")
            con.commit()
        finally:
            con.close()
        code, out, report = self.run_tool()
        self.assertEqual(code, 0)
        self.assertEqual(report["reports"], [])
        self.assertIn("合计：数据库 0 个", out)


if __name__ == "__main__":
    unittest.main()
