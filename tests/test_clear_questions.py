# -*- coding: utf-8 -*-
"""清库脚本契约：题目清零、关联清空，但知识树与字典一行不少。

运行：``.venv/Scripts/python.exe -m unittest tests.test_clear_questions``
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "clear_all_questions.py"
SCHEMA = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"
NOW = "2026-01-01T00:00:00+08:00"


def _count(path: Path, table: str) -> int:
    con = sqlite3.connect(path)
    try:
        return int(con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
    finally:
        con.close()


class ClearAllQuestionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="clearq-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bank = self.tmp / "banks" / "bank.db"
        self.bank.parent.mkdir(parents=True)
        self.pending = self.tmp / "pending.db"
        self._seed_bank()
        self._seed_pending()

    def _seed_bank(self) -> None:
        con = sqlite3.connect(self.bank)
        try:
            con.executescript(SCHEMA.read_text(encoding="utf-8"))
            con.execute(
                "INSERT INTO textbooks (id, name, publisher, edition, is_default, created_at, updated_at)"
                " VALUES ('tb_00000001', '人教A版', '人民教育出版社', '2019 课标版', 1, ?, ?)",
                (NOW, NOW),
            )
            con.execute(
                "INSERT INTO schools (id, full_name, short_name, province, city, created_at, updated_at)"
                " VALUES ('sch_0000001', '测试中学', '测试', '', '', ?, ?)",
                (NOW, NOW),
            )
            topics = (
                ("tp_bo00000001", None, "tb_00000001", "必修一", "tp_bo00000001"),
                ("tp_ch00000001", "tp_bo00000001", "tb_00000001", "第一章", "tp_bo00000001/tp_ch00000001"),
                ("tp_se00000001", "tp_ch00000001", "tb_00000001", "第一节", "tp_bo00000001/tp_ch00000001/tp_se00000001"),
                ("tp_kx00000001", "tp_se00000001", None, "集合", "tp_bo00000001/tp_ch00000001/tp_se00000001/tp_kx00000001"),
            )
            con.executemany(
                "INSERT INTO topics (id, parent_id, textbook_id, name, path, sort_order, status, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, 0, 'active', ?, ?)",
                [(tid, parent, tb, name, path, NOW, NOW) for tid, parent, tb, name, path in topics],
            )
            con.execute(
                "INSERT INTO topic_notes (topic_id, note_type, content, sort_order, created_at, updated_at)"
                " VALUES ('tp_kx00000001', 'method', '教研笔记', 0, ?, ?)",
                (NOW, NOW),
            )
            con.execute(
                "INSERT INTO sources (id, school_id, year, exam_type, grade, paper_name, created_at, updated_at)"
                " VALUES ('src_test01', NULL, 2025, '月考', '高一', '测试卷', ?, ?)",
                (NOW, NOW),
            )
            con.execute(
                "INSERT INTO node_topic_map (outline_node_id, topic_id, textbook_id, sort_order, created_at)"
                " VALUES ('tp_se00000001', 'tp_kx00000001', 'tb_00000001', 0, ?)",
                (NOW,),
            )
            con.execute("INSERT INTO bank_meta (key, value) VALUES ('schema_version', '2')")
            for qid in ("q_0001", "q_0002"):
                con.execute(
                    "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
                    " difficulty, created_at, updated_at)"
                    " VALUES (?, 'single_choice', '测试题干', '[\"A\",\"B\"]', 'A', NULL, '[]',"
                    " 'L1', ?, ?)",
                    (qid, NOW, NOW),
                )
                con.execute(
                    "INSERT INTO question_topics (question_id, topic_id, is_primary, sort_order, created_at)"
                    " VALUES (?, 'tp_kx00000001', 1, 0, ?)",
                    (qid, NOW),
                )
                con.execute(
                    "INSERT INTO question_sources (question_id, source_id, question_no, created_at)"
                    " VALUES (?, 'src_test01', '1', ?)",
                    (qid, NOW),
                )
            try:
                con.execute(
                    "CREATE VIRTUAL TABLE question_fts USING fts5(stem, question_id UNINDEXED,"
                    " tokenize='unicode61')"
                )
            except sqlite3.OperationalError:
                self.skipTest("当前 SQLite 没有 FTS5")
            con.executemany(
                "INSERT INTO question_fts (stem, question_id) VALUES (?, ?)",
                [("测 试 题 干", "q_0001"), ("测 试 题 干", "q_0002")],
            )
            con.commit()
        finally:
            con.close()

    def _seed_pending(self) -> None:
        con = sqlite3.connect(self.pending)
        try:
            con.executescript(
                """
                CREATE TABLE batches (batch_id TEXT PRIMARY KEY);
                CREATE TABLE pending_questions (id TEXT PRIMARY KEY, batch_id TEXT NOT NULL);
                CREATE TABLE dedupe_scans (batch_id TEXT PRIMARY KEY);
                CREATE TABLE dedupe_findings (batch_id TEXT, item_id TEXT);
                CREATE TABLE duplicate_pool (pool_id TEXT PRIMARY KEY);
                CREATE TABLE pool_actions (action_id TEXT PRIMARY KEY);
                CREATE TABLE schools (id TEXT PRIMARY KEY);
                CREATE TABLE scene_types (id TEXT PRIMARY KEY);
                CREATE TABLE exam_types (name TEXT, scene TEXT);
                CREATE TABLE meta_history (kind TEXT, value TEXT);
                """
            )
            con.execute("INSERT INTO batches VALUES ('B-001')")
            con.execute("INSERT INTO pending_questions VALUES ('p_test0001', 'B-001')")
            con.execute("INSERT INTO dedupe_scans VALUES ('B-001')")
            con.execute("INSERT INTO dedupe_findings VALUES ('B-001', 'p_test0001')")
            con.execute("INSERT INTO duplicate_pool VALUES ('pool_test0001')")
            con.execute("INSERT INTO pool_actions VALUES ('pa_test0001')")
            con.execute("INSERT INTO scene_types VALUES ('scene_gaokao')")
            con.execute("INSERT INTO exam_types VALUES ('一模', '校考题')")
            con.execute("INSERT INTO meta_history VALUES ('group', '测试中学')")
            con.commit()
        finally:
            con.close()

    def _run(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--bank-db", str(self.bank),
             "--pending-db", str(self.pending), *extra],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_01_without_confirm_refuses_and_keeps_data(self) -> None:
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(_count(self.bank, "questions"), 2)
        self.assertEqual(_count(self.pending, "pending_questions"), 1)
        self.assertEqual(list(self.tmp.glob("banks/*.pre-clear-*.bak")), [])

    def test_02_clears_questions_but_keeps_tree_and_dictionaries(self) -> None:
        topics_before = _count(self.bank, "topics")

        proc = self._run("--confirm")

        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for table in ("questions", "question_topics", "question_sources", "question_fts"):
            self.assertEqual(_count(self.bank, table), 0, table)
        self.assertEqual(_count(self.bank, "topics"), topics_before)
        self.assertEqual(_count(self.bank, "textbooks"), 1)
        self.assertEqual(_count(self.bank, "schools"), 1)
        self.assertEqual(_count(self.bank, "sources"), 1)
        self.assertEqual(_count(self.bank, "topic_notes"), 1)
        self.assertEqual(_count(self.bank, "node_topic_map"), 1)
        self.assertEqual(_count(self.bank, "bank_meta"), 1)

        for table in ("pending_questions", "batches", "dedupe_scans",
                      "dedupe_findings", "duplicate_pool", "pool_actions"):
            self.assertEqual(_count(self.pending, table), 0, table)
        self.assertEqual(_count(self.pending, "scene_types"), 1)
        self.assertEqual(_count(self.pending, "exam_types"), 1)
        self.assertEqual(_count(self.pending, "meta_history"), 1)

        self.assertEqual(len(list(self.tmp.glob("banks/*.pre-clear-*.bak"))), 1)
        self.assertEqual(len(list(self.tmp.glob("*.pre-clear-*.bak"))), 1)


if __name__ == "__main__":
    unittest.main()
