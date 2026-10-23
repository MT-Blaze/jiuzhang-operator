"""录题防呆与题干检索接线（军令 #14 阶段一）契约测试。

守两条新接线：

1. **保存链路走解析器**：文本先按契约 2.0 归一（``\\(`` → ``$``、``\\dfrac`` → ``\\frac``），
   坏公式/远程配图在入库前拒绝；改题时旧数据本来就有的问题不挡人，只拦本次改坏的。
2. **顶部搜索走 FTS5**：MATCH 子查询嵌入原筛选 SQL（分页总数不丢条件），
   FTS 不可用时退回 LIKE；写入路径同步索引，读路径发现条数不符会懒重建。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_search``
"""

from __future__ import annotations

import sqlite3
import unittest

from app.core import bank, bank_fts
from app.core.questions import QuestionValidationError


def _document(**overrides) -> dict:
    document = {
        "schema_version": "1.0",
        "type": "fill_blank",
        "stem": r"求 \(\dfrac{1}{2}\) 的值",
        "answer": {"kind": "expression", "content": "$x=1$", "final": "1"},
        "solution": r"由 \[x^2-1=0\] 得 $x=1$。",
        "difficulty": "basic",
        "extensions": {"org.jiuzhang.editor": {"grade": "高一"}},
        "meta": {"status": "published", "author": "测试"},
    }
    document.update(overrides)
    return document


class IntakeTest(unittest.TestCase):
    def test_01_text_is_normalized_before_write(self) -> None:
        cleaned = bank._intake_document(_document())
        self.assertEqual(cleaned["stem"], r"求 $\frac{1}{2}$ 的值")
        self.assertEqual(cleaned["solution"], "由 $$x^2-1=0$$ 得 $x=1$。")
        self.assertEqual(cleaned["answer"]["content"], "$x=1$")

    def test_02_input_document_is_not_mutated(self) -> None:
        source = _document()
        bank._intake_document(source)
        self.assertEqual(source["stem"], r"求 \(\dfrac{1}{2}\) 的值")

    def test_03_blocking_formula_is_rejected(self) -> None:
        with self.assertRaises(QuestionValidationError) as caught:
            bank._intake_document(_document(stem="求 $x 的值"))
        self.assertIn("unbalanced_math", str(caught.exception.errors))

    def test_04_blocking_solution_is_rejected_with_its_own_code(self) -> None:
        with self.assertRaises(QuestionValidationError) as caught:
            bank._intake_document(_document(solution=r"由 $\frac{1}{2$ 得"))
        self.assertIn("solution_unbalanced_braces", str(caught.exception.errors))

    def test_05_remote_image_is_rejected_and_asset_scheme_is_allowed(self) -> None:
        with self.assertRaises(QuestionValidationError):
            bank._intake_document(_document(stem=r"图：$\includegraphics{https://a.test/x.png}$"))
        allowed = bank._intake_document(_document(stem=r"图：$\includegraphics{asset://img_abc123}$"))
        self.assertIn("asset://img_abc123", allowed["stem"])

    def test_06_baseline_keeps_legacy_issue_from_blocking_edits(self) -> None:
        legacy = _document(stem="旧题 $x 的公式本来就断")
        fixed = dict(legacy, difficulty="L2")
        cleaned = bank._intake_document(fixed, baseline=legacy)
        self.assertEqual(cleaned["difficulty"], "L2")

    def test_07_update_still_blocks_newly_broken_field(self) -> None:
        legacy = _document(stem="求 $x$ 的值")
        with self.assertRaises(QuestionValidationError):
            bank._intake_document(dict(legacy, stem="改成 $x 又断了"), baseline=legacy)

    def test_08_import_path_is_non_strict(self) -> None:
        cleaned = bank._intake_document(_document(stem="旧库脏题 $x 未闭合"), strict=False)
        self.assertEqual(cleaned["stem"], "旧库脏题 $x 未闭合")


class SearchSqlTest(unittest.TestCase):
    def test_01_fts_search_is_a_match_subquery(self) -> None:
        clause, params = bank._build_where(search="二次方程", fts=True)
        self.assertIn("question_fts MATCH ?", clause)
        self.assertIn('"二 次 方 程"', params)

    def test_02_fts_off_falls_back_to_like(self) -> None:
        clause, params = bank._build_where(search="二次方程", fts=False)
        self.assertIn("LIKE ?", clause)
        self.assertIn("%二次方程%", params)

    def test_03_exact_id_is_still_searchable_in_both_modes(self) -> None:
        for fts in (False, True):
            clause, params = bank._build_where(search="q_abc_12345678", fts=fts)
            self.assertIn("q.id = ?", clause, fts)
            self.assertIn("q_abc_12345678", params)


class FtsSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        if not bank_fts.available():
            self.skipTest("当前 SQLite 没有 FTS5")
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        self.con.execute("CREATE TABLE questions (id TEXT PRIMARY KEY, stem TEXT)")
        self.con.executemany(
            "INSERT INTO questions VALUES (?, ?)",
            [("q_0001", "一元二次方程"), ("q_0002", "函数的单调性")],
        )

    def test_01_reader_rebuilds_stale_index(self) -> None:
        self.assertTrue(bank._fts_ready(self.con))
        self.assertEqual(bank_fts.doc_count(self.con), 2)
        self.assertEqual(bank_fts.query_ids(self.con, "单调"), ["q_0002"])

    def test_02_writer_keeps_index_in_sync(self) -> None:
        bank._fts_ready(self.con)
        bank._fts_upsert(self.con, "q_0003", "导数的几何意义")
        self.assertEqual(bank_fts.query_ids(self.con, "几何"), ["q_0003"])
        bank._fts_remove(self.con, "q_0001")
        self.assertEqual(bank_fts.query_ids(self.con, "方程"), [])
        self.assertEqual(bank_fts.doc_count(self.con), 2)

    def test_03_clear_empties_index(self) -> None:
        bank._fts_ready(self.con)
        bank._fts_clear(self.con)
        self.assertEqual(bank_fts.doc_count(self.con), 0)


if __name__ == "__main__":
    unittest.main()
