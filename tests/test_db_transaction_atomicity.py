"""结构迁移的原子性：建库/升级脚本必须逐句执行，不许用 executescript。

军令 #18-终 阶段六审计底座时实测（本机 Python 3.14.6）：``BEGIN IMMEDIATE`` 之后调
``executescript``，``in_transaction`` 立刻变 False——挂起的事务被隐式提交了。于是
``app/core/db.py::init_db`` 与 ``app/core/bank.py`` 的 v0.8.2 升级路径里「自检失败就回滚」
只是半句真话：脚本之前的 DDL/DML 早已落盘，失败后留下的是「结构已改、``user_version``
仍是旧值」的半套库，下一次启动按旧版本再跑一遍迁移就直接打不开。

运行：``.venv/Scripts/python.exe -m unittest tests.test_db_transaction_atomicity``
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import bank, db  # noqa: E402 - 底座模块按路径导入，测试不装包

PROBE_DDL = ("CREATE TABLE one (id INTEGER PRIMARY KEY);", "CREATE TABLE two (id INTEGER);")


class ImplicitCommitHazardTest(unittest.TestCase):
    """先证明这个坑真实存在，再证明 run_statements 不掉进去。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "probe.db"
        con = sqlite3.connect(self.path)
        con.execute("CREATE TABLE base (id INTEGER PRIMARY KEY)")
        con.commit()
        con.close()

    def _con(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def test_01_executescript_commits_the_pending_transaction(self) -> None:
        con = self._con()
        self.addCleanup(con.close)
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT INTO base (id) VALUES (1)")
        self.assertTrue(con.in_transaction, "BEGIN 之后应当处在事务里")
        con.executescript(" ".join(PROBE_DDL))
        self.assertFalse(con.in_transaction, "executescript 把挂起的事务提交了——这正是隐患")
        con.execute("CREATE TABLE must_fail (id INTEGER NOT NULL CHECK (id > 100))")
        # 生产代码里这一步对应升级自检失败：异常抛出、except 分支 rollback。
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO must_fail (id) VALUES (1)")
        con.rollback()
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM base").fetchone()[0], 1,
            "回滚之后第 1 步的写入仍在：结构已改、user_version 仍是旧值的半套库就是这么来的",
        )

    def test_02_run_statements_keeps_everything_rollbackable(self) -> None:
        con = self._con()
        self.addCleanup(con.close)
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT INTO base (id) VALUES (1)")
        db.run_statements(con, PROBE_DDL)
        self.assertTrue(con.in_transaction, "逐句 execute 不许提交事务")
        con.rollback()
        self.assertEqual(con.execute("SELECT COUNT(*) FROM base").fetchone()[0], 0)
        built = con.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name IN ('one','two')").fetchone()[0]
        self.assertEqual(built, 0, "SQLite 的 DDL 也在事务里：整段一起撤回才算原子")


class NewTableDdlShapeTest(unittest.TestCase):
    """``_new_table_ddl`` 交出的必须是一条条完整语句，否则逐句执行会直接语法错。"""

    def setUp(self) -> None:
        # 工作区物理隔离后默认落点是 data/workspaces/<id>/plugins；这里钉住仓库里的插件包
        env = mock.patch.dict(os.environ, {"JZO_PLUGINS_DIR": str(ROOT / "plugins")})
        env.start()
        self.addCleanup(env.stop)

    def test_01_each_entry_is_one_complete_statement(self) -> None:
        for table in bank.V082_NEW_TABLES:
            statements = bank._new_table_ddl("org.jiuzhang.core-bank", table)
            self.assertGreater(len(statements), 1, f"{table} 只剩建表段，索引没跟上")
            self.assertTrue(statements[0].startswith(f"CREATE TABLE {table} "), table)
            for statement in statements:
                self.assertTrue(sqlite3.complete_statement(statement.rstrip() + ";"), statement)
                self.assertNotIn("CREATE TABLE", statement[1:], f"{table} 的一段里塞了两张表")

    def test_02_unregistered_index_is_a_readable_bank_error(self) -> None:
        with self.assertRaises(bank.BankError) as raised:
            bank._new_table_ddl("org.jiuzhang.core-bank", "no_such_table")
        self.assertIn("没登记", str(raised.exception))

    def test_03_missing_schema_file_is_not_a_bare_crash(self) -> None:
        """插件包被删、库还在时，升级路径读不到 schema.sql 要说人话（404 档），不许裸 FileNotFoundError。"""
        with mock.patch.object(bank, "_schema_path", lambda plugin_id: Path("E:/不存在/schema.sql")):
            with self.assertRaises(bank.BankNotFound):
                bank._new_table_ddl("org.jiuzhang.core-bank", "textbooks")


    def test_04_retyped_schema_section_is_readable_error(self) -> None:
        """冻结的 schema.sql 被人改过排版时，取不到 CREATE TABLE 段要说人话，不许裸 ValueError。"""
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "schema.sql"
            fake.write_text("CREATE TABLE other (id INTEGER);\n", encoding="utf-8")
            with mock.patch.object(bank, "_schema_path", lambda plugin_id: fake):
                with self.assertRaises(bank.BankError) as raised:
                    bank._new_table_ddl("org.jiuzhang.core-bank", "textbooks")
        self.assertIn("找不到表 textbooks", str(raised.exception))


class HostDdlStatementListTest(unittest.TestCase):
    """``_DDL`` 拆成语句列表后，逐句执行建出来的宿主结构必须一条不漏。"""

    def test_01_every_object_is_built(self) -> None:
        con = sqlite3.connect(":memory:")
        self.addCleanup(con.close)
        db.run_statements(con, db._DDL)
        names = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','index')")
        }
        self.assertIn("questions", names)
        self.assertIn("question_tombstones", names)
        for index in ("idx_questions_created_at", "idx_questions_type",
                      "idx_questions_difficulty", "idx_questions_status"):
            self.assertIn(index, names, f"{index} 没建成：_DDL 拆句后漏了它")
        # 迁移路径共用同一批语句：DROP/RENAME 之后重建索引不能少条目
        self.assertEqual(len(db._QUESTIONS_INDEXES), 4)
        for statement in db._QUESTIONS_INDEXES:
            self.assertTrue(sqlite3.complete_statement(statement), statement)


if __name__ == "__main__":
    unittest.main()
