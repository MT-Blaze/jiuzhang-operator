"""core-bank v0.8.2 多版本地基契约测试：考向并集 + 版本映射 + 无损升级。

守的是四条不读代码就想不到的底线：

1. **考向是并集**：``topics`` 里 ``tp_kx`` 节点不许绑教材版本（CHECK 直接拒），
   版本身份只许活在 ``textbooks`` 与 ``node_topic_map`` 里；
2. **映射表方向**：只许「版本目录节点 → 考向」，挂错层（章→章、节挂节）必须被拒；
3. **新建库与迁移库同构**：升级用「建新表搬数据」而不是 ``ALTER ADD COLUMN``，
   因为 ALTER 加不上 CHECK——一旦两种库结构分叉，同一份代码面对两套不变量必出错；
4. **升级无损且幂等**：行数、外键、映射可还原原树、二次运行零改动；
   新教材版本接入时**考向零复制**（这是并集存在的唯一意义）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_multiversion``
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.core import bank
from app.core.config import settings

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "org.jiuzhang.core-bank"
SEED_DB = ROOT / "plugins" / PLUGIN_ID / "bank" / "bank.db"
SCHEMA_SQL = ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql"

# v0.6.3 的三张被升级器读写的表：topics 没有 textbook_id 列、没有并集不变量 CHECK
_SAVED_PLUGINS_ENV: str | None = None


def setUpModule() -> None:
    global _SAVED_PLUGINS_ENV
    _SAVED_PLUGINS_ENV = os.environ.get("JZO_PLUGINS_DIR")
    os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")


def tearDownModule() -> None:
    if _SAVED_PLUGINS_ENV is None:
        os.environ.pop("JZO_PLUGINS_DIR", None)
    else:
        os.environ["JZO_PLUGINS_DIR"] = _SAVED_PLUGINS_ENV


V063_DDL = """
CREATE TABLE questions (
    id TEXT NOT NULL PRIMARY KEY,
    type TEXT NOT NULL,
    stem TEXT NOT NULL,
    options TEXT NOT NULL DEFAULT '[]',
    answer TEXT NULL,
    solution TEXT NULL,
    extensions TEXT NOT NULL DEFAULT '[]',
    difficulty TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE topics (
    id          TEXT    NOT NULL,
    parent_id   TEXT    NULL,
    name        TEXT    NOT NULL,
    path        TEXT    NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    status      TEXT    NOT NULL DEFAULT 'active',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    CONSTRAINT pk_topics PRIMARY KEY (id),
    CONSTRAINT ck_topics_acyclic CHECK (parent_id IS NULL OR parent_id <> id),
    CONSTRAINT fk_topics_parent FOREIGN KEY (parent_id) REFERENCES topics (id) ON DELETE CASCADE
);
CREATE TABLE question_topics (
    question_id  TEXT NOT NULL,
    topic_id     TEXT NOT NULL,
    is_primary   INTEGER NOT NULL DEFAULT 0,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    CONSTRAINT pk_question_topics PRIMARY KEY (question_id, topic_id),
    CONSTRAINT fk_qt_question FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
    CONSTRAINT fk_qt_topic    FOREIGN KEY (topic_id)    REFERENCES topics (id)    ON DELETE CASCADE
);
CREATE TABLE topic_notes (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL,
    note_type TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CONSTRAINT fk_topic_notes_topic FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
);
CREATE TABLE bank_meta (key TEXT NOT NULL PRIMARY KEY, value TEXT NOT NULL);
"""


def build_v063_library(path: Path) -> dict:
    """造一座最小 v0.6.3 结构库：一册一章两节三考向，全部兄弟序相同。

    同兄弟序是故意的——迁移工具早期给映射表加了 (textbook, node, sort_order) 唯一索引，
    正好把这类行静默 IGNORE 掉一半。留着它当反向验证的探针。
    """
    con = sqlite3.connect(path)
    con.executescript(V063_DDL)
    now = "2026-01-01T00:00:00+08:00"
    # 兄弟序各不相同（topics 自己有 uq_topics_sibling 唯一索引）；但不同节下的考向
    # 会在「章/册」这一层撞同一个 sort_order——映射表若带唯一索引就会静默吞行。
    tree = [
        ("tp_bo00000001", None, "第一册", "tp_bo00000001", 0),
        ("tp_ch00000001", "tp_bo00000001", "第一章", "tp_bo00000001/tp_ch00000001", 0),
        ("tp_se00000001", "tp_ch00000001", "1.1 节", "tp_bo00000001/tp_ch00000001/tp_se00000001", 0),
        ("tp_se00000002", "tp_ch00000001", "1.2 节", "tp_bo00000001/tp_ch00000001/tp_se00000002", 1),
        ("tp_kx00000001", "tp_se00000001", "考向甲", "tp_bo00000001/tp_ch00000001/tp_se00000001/tp_kx00000001", 3),
        ("tp_kx00000002", "tp_se00000001", "考向乙", "tp_bo00000001/tp_ch00000001/tp_se00000001/tp_kx00000002", 4),
        ("tp_kx00000003", "tp_se00000002", "考向丙", "tp_bo00000001/tp_ch00000001/tp_se00000002/tp_kx00000003", 3),
    ]
    for node_id, parent, name, path_value, order in tree:
        con.execute(
            "INSERT INTO topics (id, parent_id, name, path, sort_order, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
            (node_id, parent, name, path_value, order, now, now),
        )
    con.execute(
        "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
        " difficulty, created_at, updated_at) VALUES ('q_seed0001', 'single_choice', '题干',"
        " '[{\"key\":\"A\",\"content\":\"1\"},{\"key\":\"B\",\"content\":\"2\"}]', 'A', NULL, '[]',"
        " 'L1', ?, ?)", (now, now))
    con.execute("INSERT INTO question_topics (question_id, topic_id, is_primary, sort_order, created_at)"
                " VALUES ('q_seed0001', 'tp_kx00000001', 1, 0, ?)", (now,))
    con.commit()
    counts = {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
              for table in ("topics", "questions", "question_topics")}
    con.close()
    return counts


class MultiversionSchemaTest(unittest.TestCase):
    """冻结结构本身的口径。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = SCHEMA_SQL.read_text(encoding="utf-8")

    def test_01_schema_declares_union_and_map(self) -> None:
        self.assertIn("CREATE TABLE textbooks", self.schema)
        self.assertIn("CREATE TABLE node_topic_map", self.schema)
        self.assertIn("textbook_id  TEXT    NULL", self.schema)
        # 并集不变量：考向节点不许绑版本
        self.assertIn("ck_topics_taxonomy_shared CHECK (substr(id, 1, 5) <> 'tp_kx' OR textbook_id IS NULL)",
                      self.schema)
        # 映射方向：目录侧只许 bo/ch/se，考向侧只许 kx
        self.assertIn("ck_ntm_outline_layer  CHECK (substr(outline_node_id, 1, 5) IN ('tp_bo', 'tp_ch', 'tp_se'))",
                      self.schema)
        self.assertIn("ck_ntm_topic_layer    CHECK (substr(topic_id, 1, 5) = 'tp_kx')", self.schema)

    def test_02_base_layer_knows_the_new_tables(self) -> None:
        self.assertEqual(bank.SCHEMA_VERSION, 2)
        for table in ("textbooks", "node_topic_map"):
            self.assertIn(table, bank.REQUIRED_TABLES, f"结构守卫没把 {table} 当必需表，缺表库会被静默打开")

    def test_03_union_and_direction_checks_reject_real_violations(self) -> None:
        """反向验证：真插一条违规记录必须被拒，否则 CHECK 是摆设。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fresh.db"
            bank.init_bank(PLUGIN_ID, db_path=path)
            con = sqlite3.connect(path)
            now = "2026-01-01T00:00:00+08:00"
            con.execute("INSERT INTO textbooks (id, name, publisher, edition, is_default, created_at, updated_at)"
                        " VALUES ('tb_aaaaaaaa', '人教A版', '', '', 1, ?, ?)", (now, now))
            con.execute("INSERT INTO topics (id, parent_id, textbook_id, name, path, sort_order, status,"
                        " created_at, updated_at) VALUES ('tp_bo11111111', NULL, 'tb_aaaaaaaa', '册',"
                        " 'tp_bo11111111', 0, 'active', ?, ?)", (now, now))
            con.execute("INSERT INTO topics (id, parent_id, textbook_id, name, path, sort_order, status,"
                        " created_at, updated_at) VALUES ('tp_kx11111111', 'tp_bo11111111', NULL, '考向',"
                        " 'tp_bo11111111/tp_kx11111111', 0, 'active', ?, ?)", (now, now))
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("INSERT INTO topics (id, parent_id, textbook_id, name, path, sort_order, status,"
                            " created_at, updated_at) VALUES ('tp_kx22222222', NULL, 'tb_aaaaaaaa', '私有考向',"
                            " 'tp_kx22222222', 0, 'active', ?, ?)", (now, now))
            with self.assertRaises(sqlite3.IntegrityError):     # 考向挂考向：映射方向错
                con.execute("INSERT INTO node_topic_map (outline_node_id, topic_id, textbook_id, sort_order,"
                            " created_at) VALUES ('tp_kx11111111', 'tp_kx22222222', 'tb_aaaaaaaa', 0, ?)", (now,))
            with self.assertRaises(sqlite3.IntegrityError):     # 目录侧挂考向：同样要拒
                con.execute("INSERT INTO node_topic_map (outline_node_id, topic_id, textbook_id, sort_order,"
                            " created_at) VALUES ('tp_kx11111111', 'tp_kx11111111', 'tb_aaaaaaaa', 0, ?)", (now,))
            con.rollback()
            # 兄弟序相同的多条映射必须都能落进去（早期唯一索引会静默吞掉）
            con.execute("INSERT INTO topics (id, parent_id, textbook_id, name, path, sort_order, status,"
                        " created_at, updated_at) VALUES ('tp_kx33333333', 'tp_bo11111111', NULL, '考向丁',"
                        " 'tp_bo11111111/tp_kx33333333', 0, 'active', ?, ?)", (now, now))
            for topic in ("tp_kx11111111", "tp_kx33333333"):
                con.execute("INSERT INTO node_topic_map (outline_node_id, topic_id, textbook_id, sort_order,"
                            " created_at) VALUES ('tp_bo11111111', ?, 'tb_aaaaaaaa', 0, ?)", (topic, now))
            self.assertEqual(2, con.execute("SELECT COUNT(*) FROM node_topic_map").fetchone()[0])
            con.close()


class UpgradeStructureTest(unittest.TestCase):
    """v0.6.3 → v0.8.2 升级：无损、幂等、与新建库同构。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _upgrade(self, path: Path) -> dict:
        return bank.upgrade_structure(PLUGIN_ID, path)

    def test_04_upgrade_is_lossless_and_backfills_map(self) -> None:
        path = self.dir / "v063.db"
        before = build_v063_library(path)
        result = self._upgrade(path)
        self.assertTrue(result["upgraded"])
        con = sqlite3.connect(path)
        try:
            self.assertEqual(2, int(con.execute("PRAGMA user_version").fetchone()[0]))
            for table, count in before.items():
                self.assertEqual(count, con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                                 f"升级改变了 {table} 的行数")
            # 3 考向 × 各自祖先链（节+章+册=3）= 9 行
            self.assertEqual(9, con.execute("SELECT COUNT(*) FROM node_topic_map").fetchone()[0])
            self.assertEqual(0, con.execute("SELECT COUNT(*) FROM topics WHERE substr(id,1,5)='tp_kx'"
                                            " AND textbook_id IS NOT NULL").fetchone()[0])
            self.assertEqual(0, con.execute("SELECT COUNT(*) FROM topics WHERE substr(id,1,5)<>'tp_kx'"
                                            " AND textbook_id IS NULL").fetchone()[0])
            self.assertEqual("人教A版", con.execute("SELECT name FROM textbooks WHERE is_default=1")
                             .fetchone()[0])
            self.assertEqual([], con.execute("PRAGMA foreign_key_check").fetchall())
            self.assertEqual("ok", con.execute("PRAGMA integrity_check").fetchone()[0])
        finally:
            con.close()
        self.assertTrue((self.dir / "v063.db.pre-v082.bak").is_file(), "升级前必须落备份")

    def test_05_upgrade_is_idempotent(self) -> None:
        path = self.dir / "again.db"
        build_v063_library(path)
        self.assertTrue(self._upgrade(path)["upgraded"])
        second = self._upgrade(path)
        self.assertFalse(second["upgraded"], "二次升级必须零改动，不能把映射行叠两遍")
        con = sqlite3.connect(path)
        self.assertEqual(9, con.execute("SELECT COUNT(*) FROM node_topic_map").fetchone()[0])
        con.close()

    def test_06_migrated_library_is_structurally_identical_to_fresh(self) -> None:
        """迁移库与新建库在升级涉及的表与索引上必须逐字同构。

        只比这三张表：测试夹具是精简 v063 库，没建全八表，比全量对象必然假失败。
        """
        migrated = self.dir / "migrated.db"
        build_v063_library(migrated)
        self._upgrade(migrated)
        fresh = self.dir / "fresh.db"
        bank.init_bank(PLUGIN_ID, db_path=fresh)
        watched = ("topics", "textbooks", "node_topic_map")

        def objects(path: Path) -> set[tuple[str, str, tuple[str, ...]]]:
            """比对象名 + 约束名/索引名集合，不比 SQL 原文（注释与空白不算结构差异）。"""
            con = sqlite3.connect(path)
            try:
                out = set()
                for kind, name, sql in con.execute(
                    "SELECT type, name, sql FROM sqlite_master"
                    " WHERE name IN ('topics','textbooks','node_topic_map')"
                    "    OR tbl_name IN ('topics','textbooks','node_topic_map')"
                ):
                    constraints = tuple(sorted(re.findall(r"CONSTRAINT (\w+)", sql or "")))
                    out.add((kind, name, constraints))
                return out
            finally:
                con.close()

        fresh_objects, migrated_objects = objects(fresh), objects(migrated)
        self.assertEqual(fresh_objects, migrated_objects,
                         "新建库与迁移库的结构对象/约束集合不一致（ALTER 加不上 CHECK，必须走建新表搬数据）")
        check_con = sqlite3.connect(migrated)
        try:
            migrated_sql = check_con.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'topics'").fetchone()[0]
        finally:
            check_con.close()   # Windows 下不收回句柄，临时目录删不掉
        self.assertIn("ck_topics_taxonomy_shared", migrated_sql, "迁移库没带上并集不变量 CHECK")
        self.assertNotIn("REFERENCES topics_new", migrated_sql,
                         "改名后自引用外键还指着已不存在的表，插入会报 no such table")

    def test_07_second_textbook_reuses_the_same_taxonomy(self) -> None:
        """并集的地基能不能用，看这一条：新教材版本接入时考向零复制。"""
        path = self.dir / "multi.db"
        build_v063_library(path)
        self._upgrade(path)
        con = sqlite3.connect(path)
        con.execute("PRAGMA foreign_keys = ON")
        now = "2026-02-01T00:00:00+08:00"
        tax_before = con.execute("SELECT COUNT(*) FROM topics WHERE substr(id,1,5)='tp_kx'").fetchone()[0]
        # 苏教版：只新增版本行 + 它自己的目录节点 + 指向既有考向的映射行
        con.execute("INSERT INTO textbooks (id, name, publisher, edition, is_default, created_at, updated_at)"
                    " VALUES ('tb_bbbbbbbb', '苏教版', '江苏教育出版社', '', 0, ?, ?)", (now, now))
        con.execute("INSERT INTO topics (id, parent_id, textbook_id, name, path, sort_order, status,"
                    " created_at, updated_at) VALUES ('tp_bo22222222', NULL, 'tb_bbbbbbbb', '必修第一册',"
                    " 'tp_bo22222222', 0, 'active', ?, ?)", (now, now))
        for topic in ("tp_kx00000001", "tp_kx00000003"):
            con.execute("INSERT INTO node_topic_map (outline_node_id, topic_id, textbook_id, sort_order,"
                        " created_at) VALUES ('tp_bo22222222', ?, 'tb_bbbbbbbb', 0, ?)", (topic, now))
        con.commit()
        self.assertEqual(tax_before,
                         con.execute("SELECT COUNT(*) FROM topics WHERE substr(id,1,5)='tp_kx'").fetchone()[0],
                         "新教材版本接入不该复制考向")
        # 同一道真题因此同时出现在两个版本的大纲里
        hit = con.execute(
            """SELECT COUNT(DISTINCT m.textbook_id) FROM question_topics qt
               JOIN node_topic_map m ON m.topic_id = qt.topic_id
               WHERE qt.question_id = 'q_seed0001'""").fetchone()[0]
        self.assertEqual(2, hit, "题目应能经映射表在两个版本目录里都出现")
        # 删掉一个版本，只回收它的目录节点与映射行，考向与题目一根毛都不动
        con.execute("DELETE FROM textbooks WHERE id = 'tb_bbbbbbbb'")
        con.commit()
        self.assertEqual(tax_before, con.execute(
            "SELECT COUNT(*) FROM topics WHERE substr(id,1,5)='tp_kx'").fetchone()[0])
        self.assertEqual(1, con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        self.assertEqual(0, con.execute("SELECT COUNT(*) FROM node_topic_map WHERE textbook_id='tb_bbbbbbbb'")
                         .fetchone()[0])
        self.assertEqual([], con.execute("PRAGMA foreign_key_check").fetchall())
        con.close()

    def test_08_wide_table_library_is_left_to_the_structure_guard(self) -> None:
        """首启自动升级不许抢走宽表库那句指向 migrate_bank_v063 的人话提示。"""
        path = self.dir / "wide.db"
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE bank_questions (id TEXT PRIMARY KEY, raw TEXT NOT NULL)")
        con.execute("INSERT INTO bank_questions VALUES ('q_1', '{}')")
        con.commit()
        con.close()
        bank._upgrade_if_older(PLUGIN_ID, path)      # 安静放行：不抛错、不改库
        con = sqlite3.connect(path)
        try:
            with self.assertRaises(bank.BankError) as ctx:
                bank._check_structure(con, PLUGIN_ID, path)
        finally:
            con.close()
        self.assertIn("bank_questions", str(ctx.exception))
        self.assertIn("migrate_bank_v063", str(ctx.exception))


@unittest.skipUnless(SEED_DB.is_file(), "本机没有 456 题种子库，跳过真数据对账")
class SeedLibraryTest(unittest.TestCase):
    """真数据口径：456 题 / 594 考向 / 1780 映射行，一条不丢。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.copy = Path(self.tmp.name) / "seed.db"
        shutil.copyfile(SEED_DB, self.copy)

    def test_09_seed_upgrades_without_losing_a_single_row(self) -> None:
        con = sqlite3.connect(self.copy)
        before = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("questions", "topics", "question_topics", "topic_notes", "schools", "sources")}
        taxonomy = con.execute("SELECT COUNT(*) FROM topics WHERE substr(id,1,5)='tp_kx'").fetchone()[0]
        con.close()
        bank.upgrade_structure(PLUGIN_ID, self.copy)
        con = sqlite3.connect(self.copy)
        try:
            after = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in before}
            self.assertEqual(before, after, "真库升级后行数对不上")
            self.assertEqual(0, con.execute("SELECT COUNT(*) FROM topics WHERE substr(id,1,5)='tp_kx'"
                                            " AND textbook_id IS NOT NULL").fetchone()[0])
            self.assertEqual(0, con.execute("SELECT COUNT(*) FROM topics t WHERE substr(t.id,1,5)='tp_kx'"
                                            " AND t.parent_id IS NOT NULL AND NOT EXISTS"
                                            "(SELECT 1 FROM node_topic_map m WHERE m.topic_id=t.id"
                                            " AND m.outline_node_id=t.parent_id)").fetchone()[0])
            self.assertEqual([], con.execute("PRAGMA foreign_key_check").fetchall())
            self.assertEqual(456, after["questions"])
            self.assertEqual(594, taxonomy)
            self.assertGreater(con.execute("SELECT COUNT(*) FROM node_topic_map").fetchone()[0], taxonomy,
                               "映射行应覆盖考向的每一层目录祖先，必须多于考向数")
        finally:
            con.close()


class TopicVersionScopeTest(unittest.TestCase):
    """大纲树按教材版本过滤：目录节点分版本，考向并集照常出现。"""

    TB_A = "tb_aaaaaaaa"
    TB_B = "tb_bbbbbbbb"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (settings.workspace_id, os.environ.get("JZO_DATA_DIR"))
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        settings.workspace_id = None
        self.addCleanup(self._restore_settings)
        bank.init_bank(PLUGIN_ID)
        self.path = Path(self.tmp.name) / "banks" / f"{PLUGIN_ID}.db"
        now = "2026-10-24T00:00:00+08:00"
        con = sqlite3.connect(self.path)
        try:
            con.executemany(
                "INSERT INTO textbooks (id, name, publisher, edition, is_default, created_at, updated_at)"
                " VALUES (?, ?, '', '', ?, ?, ?)",
                [(self.TB_A, "人教A版", 1, now, now), (self.TB_B, "苏教版", 0, now, now)],
            )
            rows = [
                ("tp_boaaaaaaaa", None, self.TB_A, "人教A版·必修一", "tp_boaaaaaaaa", 0),
                ("tp_chaaaaaaaa", "tp_boaaaaaaaa", self.TB_A, "A章", "tp_boaaaaaaaa/tp_chaaaaaaaa", 0),
                ("tp_kxaaaaaaaa", "tp_chaaaaaaaa", None, "共享考向",
                 "tp_boaaaaaaaa/tp_chaaaaaaaa/tp_kxaaaaaaaa", 0),
                ("tp_boaaaaaaab", None, self.TB_B, "苏教版·必修一", "tp_boaaaaaaab", 1),
                ("tp_chaaaaaaab", "tp_boaaaaaaab", self.TB_B, "B章", "tp_boaaaaaaab/tp_chaaaaaaab", 0),
            ]
            con.executemany(
                "INSERT INTO topics (id, parent_id, textbook_id, name, path, sort_order, status,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)",
                [(row + (now, now)) for row in rows],
            )
            con.commit()
        finally:
            con.close()

    def _restore_settings(self) -> None:
        workspace_id, data_dir = self._saved
        settings.workspace_id = workspace_id
        if data_dir is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = data_dir

    def test_01_root_list_follows_selected_textbook(self) -> None:
        only_a = bank.topics(PLUGIN_ID, textbook_id=self.TB_A)
        self.assertEqual([item["name"] for item in only_a], ["人教A版·必修一"])
        self.assertEqual(only_a[0]["textbook_id"], self.TB_A)
        only_b = bank.topics(PLUGIN_ID, textbook_id=self.TB_B)
        self.assertEqual([item["name"] for item in only_b], ["苏教版·必修一"])
        self.assertEqual({item["name"] for item in bank.topics(PLUGIN_ID)},
                         {"人教A版·必修一", "苏教版·必修一"})
        self.assertEqual(bank.default_textbook_id(PLUGIN_ID), self.TB_A)

    def test_02_search_keeps_shared_topics_but_hides_other_version_outline(self) -> None:
        shared_a = bank.topics(PLUGIN_ID, search="共享", textbook_id=self.TB_A)
        shared_b = bank.topics(PLUGIN_ID, search="共享", textbook_id=self.TB_B)
        self.assertEqual([item["name"] for item in shared_a], ["共享考向"])
        self.assertEqual([item["name"] for item in shared_b], ["共享考向"],
                         "考向是并集，不属于任何单一版本，换版本搜索仍应命中")
        self.assertEqual(bank.topics(PLUGIN_ID, search="B章", textbook_id=self.TB_A), [])
        self.assertEqual([item["name"] for item in bank.topics(
            PLUGIN_ID, search="B章", textbook_id=self.TB_B)], ["B章"])

    def test_03_invalid_textbook_id_is_rejected(self) -> None:
        with self.assertRaises(bank.BankError):
            bank.topics(PLUGIN_ID, textbook_id="tb_zzzzzzzz")


if __name__ == "__main__":
    unittest.main()
