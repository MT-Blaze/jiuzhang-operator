"""core-bank 查重引擎（军令 #18-终 阶段四）：指纹口径、只读扫描与收敛合并事务。

守的是几条不读代码就想不到的底线：

1. **归一只到排版级**：``\\(\\)`` 与 ``$``、``\\leq`` 与 ``\\le``、全角句读、多余空格都撞成同一指纹；
   但 ASCII 的 ``!``（阶乘）、``:``（比）、``()``（分组）一个都不许吞——误报的下一站是删数据；
2. **选项内容排序入指纹**：A/B 打乱的同款题算重复，正文改一个符号就不算；
   配图 URI 进指纹：题干一字不差而图不同，是两道题；答案/解析/难度/备注不进指纹；
3. **扫描零副作用**：扫完全库一字不动，出参走 ``bank`` 读路径装配（与题库浏览器同源）；
4. **合并先核对后提交**：搬挂载/来源/备注 + 追加解法 + 删副本同在一个事务里，
   中途写失败或核对不过都整事务回滚，不许出现「题删了、挂载还挂着」；
5. **保留项是事实来源**：题干/选项/答案/难度/题型原样不动；插件私有备注同名键不合成，
   只如实报冲突（AGENTS §3）；副本独有的键与配图一律搬走，不许随副本消失。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_dedupe``
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "org.jiuzhang.bank-engine"
TOKEN = "dedupe-token"
# 建库时间必须落在过去：schema 上有 ck_questions_updated（updated_at >= created_at），
# 合并时写入的 updated_at 是真机当前时间，未来的夹具时间会让所有合并用例假失败。
STAMP = "2026-01-15T09:00:00+08:00"

TEXTBOOK = "tb_aaaaaaaa"
SRC_A = "src_aaaaaaaa"
SRC_B = "src_bbbbbbbb"
KX_A = "tp_kx00000001"
KX_B = "tp_kx00000002"
KX_C = "tp_kx00000003"
KEPT_NODES = {KX_A, KX_B, KX_C}

STEM_KEEP = "若 $a>b>0$，则下列不等式成立的是（　　）"
# 同一道题的两种打法：定界符、括号全半角、全角句读、空格全不一样，题面语义一字不差。
STEM_TYPED = "若 \\(a>b>0\\)，则下列不等式成立的是（　　）"
STEM_PLAIN = "若$a > b > 0$ ， 则下列不等式成立的是(  )"

OPTIONS = [
    {"key": "A", "content": "$2a>2b$"},
    {"key": "B", "content": "$\\ln a>\\ln b$"},
    {"key": "C", "content": "$a^{2}>b^{2}$"},
    {"key": "D", "content": "$\\dfrac{1}{a}<\\dfrac{1}{b}$"},
]
SOLUTION_KEEP = "因为 $a>b>0$，两边同乘 2 得 $2a>2b$，故选 A。"
SOLUTION_OTHER = "**解析**：由 $a>b>0$ 取对数单调性知 $\\ln a>\\ln b$，故选 B。"
# 组 2 的两份解析：一份紧凑、一份空格与全角句读满天飞，归一后是同一句话。
SOLUTION_PAIR = "求导得 $f'(x)=3x^{2}-1$，代 $x=1$ 得 $2$。"


def _encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _options(spec: list[dict[str, str]], *, shuffle: bool = False, dfrac: bool = True) -> str:
    items = [dict(item) for item in spec]
    if not dfrac:
        items = [{**item, "content": item["content"].replace("\\dfrac", "\\frac")} for item in items]
    if shuffle:
        # 保序换内容：字母还是 A~D，正文倒过来 ⇒ 正文集合不变，必须撞成同一个指纹
        items = [{"key": item["key"], "content": other["content"]}
                 for item, other in zip(items, reversed(items))]
    return _encode(items)


def _extensions(entries: dict[str, object]) -> str:
    from app.core import bank  # noqa: PLC0415

    return _encode(bank.extensions_to_array(entries))


def _question_row(qid: str, *, stem: str, qtype: str = "single_choice", options: str | None = None,
                  answer: str | None = "A", solution: str | None = None, difficulty: str = "L2",
                  extensions: str | None = None) -> tuple:
    return (qid, qtype, stem,
            options if options is not None else _options(OPTIONS),
            answer, solution,
            extensions if extensions is not None else _extensions(
                {"org.jiuzhang.core-bank.grade": {"grade": "高一"}}),
            difficulty, STAMP, STAMP)


# 组 1：q_dup001（保留项口径）/ q_dup002（选项乱序、另一种解法、挂另一个考向）
#       / q_dup003（第三种打法、带迁移标记、解法与 q_dup002 相同）
# 组 2：q_pair001 / q_pair002（填空题，两份解析只差排版）
# 独苗：q_solo001（题干含 ASCII 阶乘与比号）
QUESTION_ROWS = [
    _question_row("q_dup001", stem=STEM_KEEP, solution=SOLUTION_KEEP,
                  extensions=_extensions({"org.jiuzhang.core-bank.grade": {"grade": "高一"},
                                          "org.jiuzhang.editor": {"note": "保留项备注"}})),
    _question_row("q_dup002", stem=STEM_KEEP, options=_options(OPTIONS, shuffle=True),
                  answer="B", difficulty="L3", solution=SOLUTION_OTHER),
    _question_row("q_dup003", stem=STEM_PLAIN, solution=SOLUTION_OTHER,
                  extensions=_extensions({"org.jiuzhang.core-bank.grade": {"grade": "高二"},
                                          "org.jiuzhang.core-bank.migration": {"flags": ["answer_absent"]}
                                          })),
    _question_row("q_pair001", stem="已知 $f(x)=x^{3}-x$，则 $f'(1)=$ ____。", qtype="fill_blank",
                  options="[]", answer="2", solution=SOLUTION_PAIR),
    _question_row("q_pair002", stem="已知 $f(x)=x^{3}-x$，则 $f'(1)=$ ____。", qtype="fill_blank",
                  options="[]", answer="2",
                  solution="求导得 $f' ( x )=3 x^{2}-1$ ，  代 $x=1$ 得 $2$ 。"),
    _question_row("q_solo001", stem="计算 $5!$ 与 $3:2$ 的商是（　　）",
                  options=_options([{"key": "A", "content": "$60$"}, {"key": "B", "content": "$1.5$"}])),
]

TOPIC_LINKS = [
    ("q_dup001", KX_A, 1, 0),
    ("q_dup002", KX_B, 1, 0),
    ("q_dup003", KX_A, 1, 0),
    ("q_dup003", KX_C, 0, 1),
    ("q_pair001", KX_C, 1, 0),
    ("q_pair002", KX_C, 1, 0),
    ("q_solo001", KX_A, 1, 0),
]
SOURCE_LINKS = [
    ("q_dup001", SRC_A, "1"),
    ("q_dup002", SRC_B, "7"),
    ("q_dup003", SRC_A, "1"),
    ("q_pair001", SRC_A, "12"),
    ("q_pair002", SRC_A, "12"),
    ("q_solo001", SRC_B, "3"),
]


@contextmanager
def _cursor(path: Path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def build_bank(path: Path) -> None:
    """按冻结 schema 建库并铺夹具：1 个版本、2 张 source、3 个考向、6 道题（两组重复 + 一道独苗）。"""
    from app.core import bank  # noqa: PLC0415

    bank.init_bank(PLUGIN_ID, db_path=path)
    with _cursor(path) as con:
        con.execute(
            "INSERT INTO textbooks (id, name, publisher, edition, is_default, created_at, updated_at)"
            " VALUES (?, '人教A版', '人民教育出版社', '2019 课标版', 1, ?, ?)", (TEXTBOOK, STAMP, STAMP))
        for node_id, parent, name, path_value, order in [
            ("tp_bo00000001", None, "必修第一册", "tp_bo00000001", 0),
            ("tp_ch00000001", "tp_bo00000001", "第一章 不等式", "tp_bo00000001/tp_ch00000001", 0),
            (KX_A, "tp_ch00000001", "不等式性质", f"tp_bo00000001/tp_ch00000001/{KX_A}", 0),
            (KX_B, "tp_ch00000001", "对数比较", f"tp_bo00000001/tp_ch00000001/{KX_B}", 1),
            (KX_C, "tp_ch00000001", "平方比较", f"tp_bo00000001/tp_ch00000001/{KX_C}", 2),
        ]:
            con.execute(
                "INSERT INTO topics (id, parent_id, textbook_id, name, path, sort_order, status,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)",
                (node_id, parent, None if node_id in KEPT_NODES else TEXTBOOK,
                 name, path_value, order, STAMP, STAMP))
        for source_id, paper, year in ((SRC_A, "2026 级高一期中", 2026), (SRC_B, "2025 级高一期末", 2025)):
            con.execute(
                "INSERT INTO sources (id, school_id, year, exam_type, grade, paper_name,"
                " created_at, updated_at) VALUES (?, NULL, ?, '期中考试', '高一', ?, ?, ?)",
                (source_id, year, paper, STAMP, STAMP))
        con.executemany(
            "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
            " difficulty, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", QUESTION_ROWS)
        con.executemany(
            "INSERT INTO question_topics (question_id, topic_id, is_primary, sort_order, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            [(qid, topic, primary, order, STAMP) for qid, topic, primary, order in TOPIC_LINKS])
        con.executemany(
            "INSERT INTO question_sources (question_id, source_id, question_no, created_at)"
            " VALUES (?, ?, ?, ?)",
            [(qid, source, number, STAMP) for qid, source, number in SOURCE_LINKS])


class DedupeCase(unittest.TestCase):
    """公共夹具：一座隔离临时库，每个用例重建，互不留状态。"""

    def setUp(self) -> None:
        sys.path.insert(0, str(ROOT))
        from app.core import bank_dedupe
        from app.core.config import settings

        self.dedupe = bank_dedupe
        self.settings = settings
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (os.environ.get("JZO_DATA_DIR"), os.environ.get("JZO_PLUGINS_DIR"),
                       settings.workspace_id)
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        settings.workspace_id = None
        self.addCleanup(self._restore_env)
        self.db_path = Path(self.tmp.name) / "banks" / f"{PLUGIN_ID}.db"
        build_bank(self.db_path)

    def _restore_env(self) -> None:
        for key, value in zip(("JZO_DATA_DIR", "JZO_PLUGINS_DIR"), self._saved[:2]):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.settings.workspace_id = self._saved[2]

    def _sql(self, statement: str, params: tuple = ()) -> list[sqlite3.Row]:
        with _cursor(self.db_path) as con:
            return list(con.execute(statement, params))

    def _count(self, table: str) -> int:
        return int(self._sql(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"])

    def _row(self, question_id: str) -> sqlite3.Row:
        rows = self._sql("SELECT * FROM questions WHERE id = ?", (question_id,))
        self.assertEqual(len(rows), 1, f"{question_id} 应该还在库里")
        return rows[0]


class FingerprintTest(DedupeCase):
    """指纹口径：排版差异要撞在一起，语义差异必须分开。"""

    def _mark(self, *, qtype: str = "single_choice", stem: str = STEM_KEEP,
              options: str | None = None, extensions: str | None = None) -> str:
        return self.dedupe.fingerprint(
            qtype, stem,
            _options(OPTIONS) if options is None else options,
            _extensions({}) if extensions is None else extensions)

    def test_01_typography_differences_share_one_fingerprint(self) -> None:
        self.assertEqual(self.dedupe.normalize_text(STEM_TYPED), self.dedupe.normalize_text(STEM_PLAIN),
                         "反斜杠定界符、全半角括号、全角句读与多余空格必须归一到同一个串")
        self.assertEqual(self._mark(), self._mark(stem=STEM_PLAIN))
        self.assertEqual(self._mark(), self._mark(stem=STEM_TYPED))

    def test_02_dfrac_and_frac_are_the_same_math(self) -> None:
        self.assertEqual(self._mark(), self._mark(options=_options(OPTIONS, dfrac=False)))

    def test_03_option_order_is_normalised_but_content_is_not(self) -> None:
        self.assertEqual(self._mark(), self._mark(options=_options(OPTIONS, shuffle=True)),
                         "A/B 顺序打乱的同款题算重复")
        changed = [{"key": "A", "content": "$2a<2b$"}, *OPTIONS[1:]]
        self.assertNotEqual(self._mark(), self._mark(options=_options(changed)),
                            "选项正文改一个符号就是另一道题")

    def test_04_images_take_part_in_the_fingerprint(self) -> None:
        first = _extensions({"org.jiuzhang.core-bank.images": {
            "images": [{"id": "img_1", "role": "stem", "uri": "/static/uploads/a.png"}]}})
        second = _extensions({"org.jiuzhang.core-bank.images": {
            "images": [{"id": "img_2", "role": "stem", "uri": "/static/uploads/b.png"}]}})
        self.assertNotEqual(self._mark(), self._mark(extensions=first), "带图与不带图不算同一道")
        self.assertNotEqual(self._mark(extensions=first), self._mark(extensions=second))

    def test_05_content_outside_the_stem_does_not_split_a_group(self) -> None:
        """答案/解析/难度/备注不进指纹：它们不同正是「同一道题录了两遍」的特征。"""
        self.assertEqual(self._mark(), self._mark(
            extensions=_extensions({"org.jiuzhang.editor": {"note": "教师备注"}})))
        self.assertEqual(self._mark(), self._mark(
            extensions=_extensions({"org.jiuzhang.core-bank.grade": {"grade": "高二"}})))

    def test_06_ascii_punctuation_survives_normalisation(self) -> None:
        """``!`` 是阶乘、``:`` 是比、``()`` 是分组：吞掉任何一类都会把两道不同的题并成一道。"""
        self.assertNotEqual(self._mark(stem="计算 $5!$"), self._mark(stem="计算 $5$"))
        self.assertNotEqual(self._mark(stem="比 $3:2$"), self._mark(stem="比 $32$"))
        self.assertNotEqual(self._mark(stem="$f(g(x))$"), self._mark(stem="$fg(x)$"))

    def test_07_question_type_is_part_of_the_fingerprint(self) -> None:
        self.assertNotEqual(self._mark(), self._mark(qtype="multiple_choice"))


class ScanTest(DedupeCase):
    """只读扫描：分组、全量出参与零副作用。"""

    def test_08_groups_and_counters(self) -> None:
        report = self.dedupe.duplicate_groups(PLUGIN_ID)
        self.assertEqual(report["scanned"], 6)
        self.assertEqual(report["group_count"], 2)
        self.assertEqual(report["redundant"], 3, "(3-1)+(2-1)")
        self.assertEqual(report["truncated"], 0)
        self.assertEqual(sorted(group["count"] for group in report["groups"]), [2, 3])
        big = report["groups"][0]
        self.assertEqual(big["count"], 3, "大组排前面")
        self.assertEqual(len(big["documents"]), 3, "每组必须带全量结构")

    def test_09_documents_use_the_read_path_contract(self) -> None:
        big = next(group for group in self.dedupe.duplicate_groups(PLUGIN_ID)["groups"]
                   if group["count"] == 3)
        first = big["documents"][0]
        self.assertEqual(first["id"], "q_dup001")
        self.assertEqual(first["schema_version"], "2.0")
        self.assertEqual(len(first["options"]), 4)
        self.assertEqual(first["answer"]["choice_keys"], ["A"])
        self.assertEqual(first["difficulty"], "L2")
        self.assertEqual(first["source"]["paper_title"], "2026 级高一期中")
        self.assertEqual(first["taxonomy"]["topic_ids"], [KX_A])
        self.assertIn("org.jiuzhang.editor", first["extensions"])

    def test_10_differing_fields_lights_up_every_real_difference(self) -> None:
        report = self.dedupe.duplicate_groups(PLUGIN_ID)
        big = next(group for group in report["groups"] if group["count"] == 3)
        self.assertEqual(big["differing_fields"],
                         ["answer", "difficulty", "extensions", "grade", "solution", "sources", "topics"])
        pair = next(group for group in report["groups"] if group["count"] == 2)
        self.assertEqual(pair["differing_fields"], [],
                         "两份解析只差空格与全角句读，归一后同一句话，不该点亮任何字段")

    def test_11_scan_leaves_the_library_untouched(self) -> None:
        before = {table: self._count(table) for table in
                  ("questions", "question_topics", "question_sources", "topics", "sources")}
        digest = self._digest()
        self.dedupe.duplicate_groups(PLUGIN_ID)
        self.assertEqual(before, {table: self._count(table) for table in before})
        self.assertEqual(digest, self._digest(), "扫描一个字都不许改")

    def test_12_truncation_is_reported_not_hidden(self) -> None:
        original = self.dedupe.MAX_GROUPS
        try:
            self.dedupe.MAX_GROUPS = 1
            report = self.dedupe.duplicate_groups(PLUGIN_ID)
        finally:
            self.dedupe.MAX_GROUPS = original
        self.assertEqual(report["group_count"], 2, "总组数仍按全库报")
        self.assertEqual(report["truncated"], 1, "被截掉的组数要如实报出来")
        self.assertEqual(len(report["groups"]), 1)

    def _digest(self) -> str:
        rows = self._sql("SELECT id, type, stem, options, answer, solution, extensions,"
                         " difficulty, created_at, updated_at FROM questions ORDER BY id")
        return json.dumps([tuple(row) for row in rows], ensure_ascii=False)


class MergeTest(DedupeCase):
    """收敛合并：搬运、追加解法、删副本与核对回滚。"""

    def _merge(self, primary: str, copies: list[str]) -> dict:
        return self.dedupe.merge_questions(PLUGIN_ID, primary, copies)

    def test_13_links_notes_and_copies_converge(self) -> None:
        report = self._merge("q_dup001", ["q_dup002", "q_dup003"])
        self.assertTrue(report["same_fingerprint"])
        self.assertEqual(report["fingerprint_mismatch"], [])
        self.assertEqual((report["questions_before"], report["questions_after"]), (6, 4))
        self.assertEqual(self._count("questions"), 4)
        self.assertEqual(self._sql(
            "SELECT 1 FROM questions WHERE id IN ('q_dup002','q_dup003')"), [],
            "副本必须真删：存储层没有软删列")
        self.assertEqual([row["topic_id"] for row in self._sql(
            "SELECT topic_id FROM question_topics WHERE question_id = 'q_dup001' ORDER BY sort_order")],
            [KX_A, KX_B, KX_C], "副本独有的考向要搬到保留项上，且排在原挂载之后")
        self.assertEqual([row["topic_id"] for row in self._sql(
            "SELECT topic_id FROM question_topics WHERE question_id = 'q_dup001' AND is_primary = 1")],
            [KX_A], "保留项的主挂载不许被副本顶掉")
        self.assertEqual(self._sql(
            "SELECT 1 FROM question_topics WHERE question_id IN ('q_dup002','q_dup003')"), [],
            "副本的挂载行得随副本一起走")
        self.assertEqual({(row["source_id"], row["question_no"]) for row in self._sql(
            "SELECT source_id, question_no FROM question_sources WHERE question_id = 'q_dup001'")},
            {(SRC_A, "1"), (SRC_B, "7")}, "同一张卷子同题号并成一行，副本独有的来源要搬过来")
        self.assertEqual(self._sql(
            "SELECT 1 FROM question_sources WHERE question_id IN ('q_dup002','q_dup003')"), [])
        keys = {item["key"] for item in json.loads(self._row("q_dup001")["extensions"])}
        self.assertIn("org.jiuzhang.core-bank.migration", keys, "副本独有的单题备注要搬过来")
        self.assertIn("org.jiuzhang.editor", keys, "保留项自己的备注不许被动")
        self.assertEqual(report["moved"]["topics"], sorted([KX_B, KX_C]))
        self.assertEqual(report["moved"]["sources"], [f"{SRC_B}#7"])
        self.assertEqual(report["moved"]["extensions"], ["org.jiuzhang.core-bank.migration"])
        kept = self._row("q_dup001")
        self.assertEqual((kept["stem"], kept["answer"], kept["difficulty"], kept["type"]),
                         (STEM_KEEP, "A", "L2", "single_choice"),
                         "题干/答案/难度/题型一律原样保留")

    def test_14_solutions_are_appended_once_per_distinct_method(self) -> None:
        report = self._merge("q_dup001", ["q_dup002", "q_dup003"])
        solution = self._row("q_dup001")["solution"]
        self.assertEqual(report["solution_appended_from"], ["q_dup002"],
                         "q_dup003 与 q_dup002 解法相同，不该再堆一段")
        self.assertIn("**解法二**", solution)
        self.assertNotIn("**解法三**", solution)
        self.assertTrue(solution.startswith(SOLUTION_KEEP), "保留项原解析必须打头")
        self.assertIn(SOLUTION_OTHER, solution)

    def test_15_primary_without_solution_adopts_the_copy_plainly(self) -> None:
        self._sql("UPDATE questions SET solution = NULL WHERE id = 'q_pair001'")
        self._sql("UPDATE questions SET solution = ? WHERE id = 'q_pair002'", (SOLUTION_OTHER,))
        report = self._merge("q_pair001", ["q_pair002"])
        solution = self._row("q_pair001")["solution"]
        self.assertEqual(solution, SOLUTION_OTHER,
                         "保留项本就没有解析时，副本那段是解法一，不许顶着「解法二」")
        self.assertNotIn("解法", solution)
        self.assertEqual(report["solution_appended_from"], ["q_pair002"])

    def test_16_extension_conflicts_are_reported_not_merged(self) -> None:
        self._sql("UPDATE questions SET extensions = ? WHERE id = 'q_dup002'",
                  (_extensions({"org.jiuzhang.editor": {"note": "副本备注"}}),))
        report = self._merge("q_dup001", ["q_dup002"])
        entry = next(item for item in json.loads(self._row("q_dup001")["extensions"])
                     if item["key"] == "org.jiuzhang.editor")
        self.assertEqual(entry["value"], {"note": "保留项备注"},
                         "同名键保留项赢：底座不合成插件私有数据（AGENTS §3）")
        self.assertEqual(report["moved"]["conflict_extensions"], ["org.jiuzhang.editor"])
        self.assertEqual(report["moved"]["extensions"], [])

    def test_17_images_of_the_copy_survive_a_forced_merge(self) -> None:
        self._sql("UPDATE questions SET extensions = ? WHERE id = 'q_dup002'",
                  (_extensions({"org.jiuzhang.core-bank.images": {
                      "images": [{"id": "img_9", "role": "stem", "uri": "/static/uploads/copy.png"}]}}),))
        report = self._merge("q_dup001", ["q_dup002"])
        self.assertFalse(report["same_fingerprint"], "带图与不带图本不是同一指纹，这是老师强制合并的")
        self.assertEqual(report["fingerprint_mismatch"], ["q_dup002"])
        entry = next(item for item in json.loads(self._row("q_dup001")["extensions"])
                     if item["key"] == "org.jiuzhang.core-bank.images")
        self.assertEqual(entry["value"]["images"][0]["uri"], "/static/uploads/copy.png",
                         "老师的配图不许随副本一起消失")
        self.assertEqual(report["moved"]["extensions"], ["org.jiuzhang.core-bank.images"])

    def test_18_write_failure_rolls_the_whole_merge_back(self) -> None:
        """真写失败：用触发器让搬运中途炸，库必须回到合并前的样子。"""
        self._sql("CREATE TRIGGER boom BEFORE INSERT ON question_topics"
                  " WHEN NEW.topic_id = 'tp_kx00000003'"
                  " BEGIN SELECT RAISE(ABORT, '模拟中断'); END")
        with self.assertRaises(self.dedupe.MergeRejected) as ctx:
            self._merge("q_dup001", ["q_dup002", "q_dup003"])
        self.assertIn("回滚", str(ctx.exception))
        self.assertEqual(self._count("questions"), 6, "回滚不彻底：副本被删掉了")
        self.assertEqual(self._count("question_topics"), 7)
        self.assertEqual(self._count("question_sources"), 6)
        kept = self._row("q_dup001")
        self.assertEqual(kept["solution"], SOLUTION_KEEP)
        self.assertNotIn("migration", kept["extensions"])
        self._sql("DROP TRIGGER boom")
        self.assertEqual(self._merge("q_dup001", ["q_dup002", "q_dup003"])["questions_after"], 4,
                         "回滚后库仍然干净，可以直接重跑")

    def test_19_failed_reconciliation_blocks_the_commit(self) -> None:
        """核对不过就不许提交：把 _verify 换成必然报错，观察整事务回滚。"""
        with mock.patch.object(self.dedupe, "_verify",
                               side_effect=self.dedupe.MergeRejected("模拟行数对不上")):
            with self.assertRaises(self.dedupe.MergeRejected):
                self._merge("q_dup001", ["q_dup002"])
        self.assertEqual(self._count("questions"), 6)
        self.assertEqual(self._count("question_topics"), 7)

    def test_20_fts_index_keeps_no_ghost_of_the_copy(self) -> None:
        from app.core import bank_fts  # noqa: PLC0415

        if not bank_fts.available():
            self.skipTest("当前 SQLite 没有编译 FTS5")
        con = sqlite3.connect(self.db_path)
        try:
            bank_fts.rebuild(con)
        finally:
            con.close()
        self._merge("q_dup001", ["q_dup002"])
        indexed = [row["question_id"] for row in self._sql("SELECT question_id FROM question_fts")]
        self.assertIn("q_dup001", indexed)
        self.assertNotIn("q_dup002", indexed, "搜索里留着已删副本，点进去就是 404")

    def test_21_rejected_inputs_leave_the_library_alone(self) -> None:
        from app.core import bank  # noqa: PLC0415

        cases = [
            (("q_dup001", []), self.dedupe.MergeRejected, "副本列表为空"),
            (("q_dup001", ["q_dup001"]), self.dedupe.MergeRejected, "不能同时出现在副本列表里"),
            (("q_dup001", ["q_dup002", "q_dup002"]), self.dedupe.MergeRejected, "重复出现"),
            (("q_dup001", ["1"]), self.dedupe.MergeRejected, "不是合法题目 ID"),
            (("q_dup001", "q_dup002"), self.dedupe.MergeRejected, "副本列表必须是"),
            (("q_dup001", [f"q_copy{i:03d}" for i in range(21)]),
             self.dedupe.MergeRejected, "一次最多合并"),
            (("q_ghost", ["q_dup002"]), bank.BankNotFound, "题库里没有这些题目"),
        ]
        for args, expected, needle in cases:
            with self.subTest(args=args[1] if isinstance(args[1], list) else "str"):
                with self.assertRaises(expected) as ctx:
                    self._merge(*args)
                self.assertIn(needle, str(ctx.exception))
        self.assertEqual(self._count("questions"), 6, "被拒的合并一条都不许动库")
        self.assertEqual(self._row("q_dup001")["solution"], SOLUTION_KEEP)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class DedupeHttpTest(unittest.TestCase):
    """Host API：扫描只读不鉴权，合并必须带写令牌，且错误码分得清。"""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(ROOT))
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name) / "data"
        banks = cls.data_dir / "banks"
        banks.mkdir(parents=True, exist_ok=True)
        # 建库在父进程里跑，schema.sql 要按 JZO_PLUGINS_DIR 找；只给子进程设环境变量不够。
        cls._saved_env = {key: os.environ.get(key)
                          for key in ("JZO_DATA_DIR", "JZO_PLUGINS_DIR", "JZO_LOCAL_TOKEN")}
        os.environ["JZO_DATA_DIR"] = str(cls.data_dir)
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        os.environ["JZO_LOCAL_TOKEN"] = TOKEN
        build_bank(banks / f"{PLUGIN_ID}.db")

        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        env["JZO_LOCAL_TOKEN"] = TOKEN
        env["JZO_RESTART_DISABLED"] = "1"
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(cls.port), "--log-level", "warning"],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        cls.base = f"http://127.0.0.1:{cls.port}"
        deadline = time.time() + 25
        while time.time() < deadline:
            if cls.process.poll() is not None:
                output = cls.process.stdout.read() if cls.process.stdout else ""
                raise RuntimeError("服务提前退出：\n" + output)
            try:
                with urllib.request.urlopen(cls.base + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("服务未在 25 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        for key, value in cls._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls.tmp.cleanup()

    def _request(self, path: str, method: str = "GET", body: dict | None = None,
                 token: bool = False) -> tuple[int, dict]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", TOKEN)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as error:
            payload = error.read()
            error.close()
            try:
                return error.code, json.loads(payload.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return error.code, {"raw": payload.decode("utf-8", "replace")}

    def _total(self) -> int:
        status, data = self._request(f"/api/bank/plugins/{PLUGIN_ID}/questions?page_size=1")
        self.assertEqual(status, 200, data)
        return int(data["total"])

    def test_22_scan_is_open_and_read_only(self) -> None:
        before = self._total()
        status, report = self._request(f"/api/bank/plugins/{PLUGIN_ID}/duplicates")
        self.assertEqual(status, 200, report)
        self.assertEqual(report["scanned"], before)
        self.assertEqual(report["group_count"], 2)
        big = report["groups"][0]
        self.assertEqual(len(big["documents"]), big["count"], "每组带全量结构，双栏面板不用再逐题取详情")
        self.assertIn("answer", big["differing_fields"])
        self.assertEqual(self._total(), before, "扫描完题数一字不动")

    def test_23_bad_plugin_id_is_rejected(self) -> None:
        status, data = self._request("/api/bank/plugins/bad_id/duplicates")
        self.assertEqual(status, 400, data)
        self.assertIn("插件 ID 非法", str(data))

    def test_24_merge_requires_token(self) -> None:
        before = self._total()
        status, data = self._request(f"/api/bank/plugins/{PLUGIN_ID}/duplicates/merge", "POST",
                                     {"primary_id": "q_dup001", "copy_ids": ["q_dup002"]})
        self.assertEqual(status, 401, data)
        self.assertEqual(self._total(), before)

    def test_25_merge_input_errors_and_codes(self) -> None:
        base = f"/api/bank/plugins/{PLUGIN_ID}/duplicates/merge"
        before = self._total()
        cases = [
            ({"primary_id": "q_solo001", "copy_ids": "q_pair001"}, 400),
            ({"copy_ids": ["q_pair001"]}, 400),
            ({"primary_id": "q_ghost", "copy_ids": ["q_pair001"]}, 404),
            ({"primary_id": "q_pair001", "copy_ids": ["q_pair001"]}, 409),
            ({"primary_id": "q_pair001", "copy_ids": ["1"]}, 409),
        ]
        for body, expected in cases:
            with self.subTest(body=str(body)):
                status, data = self._request(base, "POST", body, token=True)
                self.assertEqual(status, expected, data)
        self.assertEqual(self._total(), before, "被拒的合并一条不许动")

    def test_26_merge_converges_through_the_host(self) -> None:
        status, report = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/duplicates/merge", "POST",
            {"primary_id": "q_dup001", "copy_ids": ["q_dup002", "q_dup003"]}, token=True)
        self.assertEqual(status, 200, report)
        self.assertEqual(report["questions_after"], self._total())
        self.assertIn("**解法二**", report["primary"]["solution"])
        self.assertEqual(report["primary"]["answer"]["choice_keys"], ["A"])
        status, gone = self._request(f"/api/bank/plugins/{PLUGIN_ID}/questions/q_dup002")
        self.assertEqual(status, 404, gone)
        status, report = self._request(f"/api/bank/plugins/{PLUGIN_ID}/duplicates")
        self.assertEqual(status, 200, report)
        self.assertEqual([group["ids"] for group in report["groups"]],
                         [[q["id"] for q in report["groups"][0]["documents"]]] if report["groups"] else [],
                         "合并后重复组应当消失")


if __name__ == "__main__":
    unittest.main()
