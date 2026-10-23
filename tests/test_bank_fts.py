"""FTS5 题干检索预研契约（军令 #13 任务 5）。

核心口径：中文按单字入索引、查询按短语匹配，2 字词也能命中；
公式片段保持原样；索引建不起来必须显式抛 ``FtsUnavailable``，
调用方可退回 LIKE，不能把题库拖下水。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_fts``
"""

from __future__ import annotations

import sqlite3
import unittest

from app.core import bank_fts


class SegmentTest(unittest.TestCase):
    def test_01_cjk_chars_become_single_tokens(self) -> None:
        self.assertEqual(bank_fts.segment("一元二次方程"), "一 元 二 次 方 程")

    def test_02_latin_and_formulas_stay_whole(self) -> None:
        self.assertEqual(bank_fts.segment("已知 f(x)=x^2"), "已 知 f(x)=x^2")

    def test_03_whitespace_is_collapsed(self) -> None:
        self.assertEqual(bank_fts.segment("  函数\n\t与导数  "), "函 数 与 导 数")

    def test_04_non_string_is_empty(self) -> None:
        self.assertEqual(bank_fts.segment(None), "")  # type: ignore[arg-type]


class FtsTableTest(unittest.TestCase):
    def setUp(self) -> None:
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        if not bank_fts.available():
            self.skipTest("当前 SQLite 没有 FTS5")

    def seed(self) -> None:
        bank_fts.index_all(self.con, [
            ("q_0001", "一元二次方程的解法"),
            ("q_0002", "已知函数 f(x)=x^2，求导数值"),
            ("q_0003", "导数的几何意义"),
        ])

    def test_01_two_char_query_matches(self) -> None:
        self.seed()
        self.assertEqual(bank_fts.query_ids(self.con, "函数"), ["q_0002"])

    def test_02_multi_char_phrase_matches(self) -> None:
        self.seed()
        self.assertEqual(bank_fts.query_ids(self.con, "二次方程"), ["q_0001"])

    def test_03_phrase_order_matters(self) -> None:
        self.seed()
        self.assertEqual(bank_fts.query_ids(self.con, "数函"), [])

    def test_04_formula_fragment_matches(self) -> None:
        self.seed()
        self.assertEqual(bank_fts.query_ids(self.con, "x^2"), ["q_0002"])

    def test_05_upsert_replaces_old_stem(self) -> None:
        self.seed()
        bank_fts.upsert(self.con, "q_0003", "导数的物理意义")
        self.assertEqual(bank_fts.query_ids(self.con, "物理"), ["q_0003"])
        self.assertEqual(bank_fts.query_ids(self.con, "几何"), [])

    def test_06_remove_and_count(self) -> None:
        self.seed()
        self.assertEqual(bank_fts.doc_count(self.con), 3)
        self.assertEqual(bank_fts.remove(self.con, "q_0001"), 1)
        self.assertEqual(bank_fts.doc_count(self.con), 2)
        self.assertEqual(bank_fts.query_ids(self.con, "方程"), [])

    def test_07_limit_is_capped_and_respected(self) -> None:
        bank_fts.index_all(self.con, [(f"q_{i:04d}", "求函数的解析式") for i in range(30)])
        self.assertEqual(len(bank_fts.query_ids(self.con, "函数", limit=5)), 5)
        self.assertEqual(len(bank_fts.query_ids(self.con, "函数", limit=999)), 30)

    def test_08_empty_query_returns_nothing(self) -> None:
        self.seed()
        self.assertEqual(bank_fts.query_ids(self.con, "   "), [])

    def test_09_quotes_in_query_do_not_break_syntax(self) -> None:
        self.seed()
        self.assertEqual(bank_fts.query_ids(self.con, '函数"'), ["q_0002"])  # 引号被中和，不抛语法错

    def test_10_rebuild_from_source_table(self) -> None:
        self.con.execute("CREATE TABLE questions (id TEXT PRIMARY KEY, stem TEXT)")
        self.con.executemany(
            "INSERT INTO questions VALUES (?, ?)",
            [("q_1", "集合的交集"), ("q_2", "函数的单调性")],
        )
        self.assertEqual(bank_fts.rebuild(self.con), 2)
        self.assertEqual(bank_fts.query_ids(self.con, "单调"), ["q_2"])

    def test_11_index_table_is_separate_from_questions(self) -> None:
        """虚拟表独立存在：不改 questions 结构，旧库不必迁移就能加索引。"""
        self.seed()
        names = {row[0] for row in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        self.assertIn("question_fts", names)


class UnavailableTest(unittest.TestCase):
    def test_01_missing_fts_raises_a_dedicated_error(self) -> None:
        import unittest.mock as mock

        con = sqlite3.connect(":memory:")
        self.addCleanup(con.close)
        with mock.patch.object(bank_fts, "available", return_value=False):
            with self.assertRaises(bank_fts.FtsUnavailable):
                bank_fts.ensure_schema(con)


if __name__ == "__main__":
    unittest.main()
