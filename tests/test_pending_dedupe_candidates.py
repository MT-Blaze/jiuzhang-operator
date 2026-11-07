"""整批自动初查产候选并跨重启可读（军令 #32 · S3 判据 3.1~3.4）。

钉住四条口径，全部围绕「重启之后老师看到的还是不是同一句话」：

- **3.1 复用引擎产候选**：初查不再只报数——``scan_state`` 必须带出候选清单，每条
  有档位（确定／很像／较像／可能）、百分比与可展开的信号明细；批内配对走
  ``collect_candidates`` 这一条纯函数路径，**不另起第二个判重引擎**；
- **3.2 默认档＝宽**：不传档位就是最宽档，「只差一个符号」的题必须进候选；
- **3.3 重启安全**：结论落 ``dedupe_scans`` + ``dedupe_findings``；把进程内缓存清空
  （等价于底座重启）后 ``scan_state`` 仍回同一份账目与候选，且**回填**缓存；
  从没扫过的批次仍然 ``pending``——「没扫过」与「扫过没重复」是两件事；
- **3.4 主库读不通绝不报 0**：``failed`` 带 ``code`` / ``retryable`` / 「初查失败、
  可重试」，且这条状态同样**落库**——重启后读到的还是「失败、可重试」，不是「0 条重复」。

另钉一条结构底线：``SCHEMA_VERSION`` 升到 11，旧库（user_version=6）连上就自动补表补列，
不删不改已有任何一行。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pending_dedupe_candidates``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import wire  # noqa: E402

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ``settings.data_dir`` 每次求值都现读 ``JZO_DATA_DIR``（app/core/config.py:66 是 property，
# 不是导入期死值），所以底座可以在这里照常顶层 import，临时工作区在 setUp 里换。
from app.core import bank_dedupe, pending_dedupe, pending_db  # noqa: E402

PLUGIN_ID = "org.jiuzhang.bank-engine"
STEM_POOL = r"已知向量 $\vec{a}=(1,2)$，$\vec{b}=(x,4)$，若 $\vec{a}\parallel\vec{b}$，则 $x$ 的值为（　　）。"
# 与池内那条「只差一个符号」：\parallel → \perp，中文骨架一字不差
STEM_BANK = r"已知向量 $\vec{a}=(1,2)$，$\vec{b}=(x,4)$，若 $\vec{a}\perp\vec{b}$，则 $x$ 的值为（　　）。"
STEM_UNRELATED = r"某工厂第三季度产值为 $a$ 万元，第四季度比第三季度增长 $10\%$，则第四季度产值为（　　）。"


def _doc(stem: str, answer: str = "A") -> dict:
    return {
        "type": "single_choice",
        "stem": stem,
        "difficulty": "L2",
        "options": [
            {"key": "A", "content": "$2$"},
            {"key": "B", "content": "$4$"},
            {"key": "C", "content": "$8$"},
            {"key": "D", "content": "$16$"},
        ],
        "answer": {"kind": "choice", "choice_keys": [answer], "final": answer},
    }


def _pool_row(item_id: str, document: dict, seq: int) -> dict:
    """造一行「池内行」——``collect_candidates`` 是纯函数，不碰数据库就能单独验。"""
    return {
        "id": item_id,
        "doc_json": wire.dumps(document, ensure_ascii=False),
        "assets_json": "[]",
        "seq": seq,
    }


def _bank_row(question_id: str, document: dict) -> dict:
    return {
        "id": question_id,
        "type": document["type"],
        "stem": document["stem"],
        "options": wire.dumps(document["options"], ensure_ascii=False),
        "extensions": "[]",
        "answer": "A",
    }


class CandidatesPureTest(unittest.TestCase):
    """判据 3.1／3.2：候选清单的档位与门槛（纯函数层，不依赖库）。"""

    def test_01_symbol_only_pair_enters_loose_tier(self) -> None:
        found = pending_dedupe.collect_candidates(
            [_pool_row("p_1", _doc(STEM_POOL), 1)],
            [_bank_row("q_1", _doc(STEM_BANK))])
        self.assertEqual(found["tier"], bank_dedupe.DEFAULT_TIER)
        self.assertEqual(found["tier"], "loose")
        hits = [item for item in found["candidates"] if item["item_id"] == "p_1"]
        self.assertEqual(len(hits), 1, msg=str(found["candidates"]))
        self.assertEqual(hits[0]["reason"], "bank")
        self.assertEqual(hits[0]["existing_id"], "q_1")
        self.assertEqual(hits[0]["level"], "fairly_similar")
        self.assertEqual(hits[0]["label"], "较像")
        # 判据 2.6：只有「确定」才配带指纹。较像是「像但不是同一枚指纹」，
        # 这里凭空造一个等号就是把相似度冒充成全等——必须是空串。
        self.assertEqual(hits[0]["fingerprint"], "")
        self.assertGreaterEqual(hits[0]["percent"], bank_dedupe.LEVEL_FLOOR["fairly_similar"])
        self.assertLessEqual(hits[0]["percent"], bank_dedupe.LEVEL_CEILING["fairly_similar"])

    def test_02_identical_stem_is_certain(self) -> None:
        found = pending_dedupe.collect_candidates(
            [_pool_row("p_1", _doc(STEM_POOL), 1)],
            [_bank_row("q_1", _doc(STEM_POOL))])
        hit = [item for item in found["candidates"] if item["item_id"] == "p_1"][0]
        self.assertEqual((hit["level"], hit["label"], hit["percent"]), ("certain", "确定", 100))
        self.assertEqual(hit["reason"], "bank")

    def test_03_unrelated_pair_produces_no_candidate(self) -> None:
        found = pending_dedupe.collect_candidates(
            [_pool_row("p_1", _doc(STEM_POOL), 1)],
            [_bank_row("q_1", _doc(STEM_UNRELATED))])
        self.assertEqual(found["candidates"], [])

    def test_04_batch_internal_twin_is_a_batch_reason(self) -> None:
        found = pending_dedupe.collect_candidates(
            [_pool_row("p_1", _doc(STEM_POOL), 1), _pool_row("p_2", _doc(STEM_POOL), 2)], [])
        self.assertEqual([c["reason"] for c in found["candidates"]], ["batch"])
        self.assertEqual(found["candidates"][0]["item_id"], "p_2")
        self.assertEqual(found["candidates"][0]["keep_id"], "p_1")

    def test_05_strict_tier_keeps_only_certain(self) -> None:
        rows = [_pool_row("p_1", _doc(STEM_POOL), 1)]
        main = [_bank_row("q_1", _doc(STEM_BANK))]
        self.assertEqual(pending_dedupe.collect_candidates(rows, main, tier="strict")["candidates"],
                         [])
        found = pending_dedupe.collect_candidates(rows, main, tier="loose")
        self.assertEqual(len(found["candidates"]), 1)

    def test_06_candidates_are_ranked_and_deduped_per_item(self) -> None:
        # 三条池内题：p_2 与 p_1 同题面（批内「确定」）、p_3 与主库 q_1 同题面（主库「确定」）、
        # p_1 只剩「较像」——每行只留最强的一对，成序按题号（与 groups/drop_ids 同一序）。
        rows = [_pool_row("p_1", _doc(STEM_POOL), 1),
                _pool_row("p_2", _doc(STEM_POOL), 2),
                _pool_row("p_3", _doc(STEM_BANK), 3)]
        main = [_bank_row("q_1", _doc(STEM_BANK))]
        found = pending_dedupe.collect_candidates(rows, main)
        self.assertEqual([c["item_id"] for c in found["candidates"]], ["p_1", "p_2", "p_3"])
        self.assertEqual([c["level"] for c in found["candidates"]],
                         ["fairly_similar", "certain", "certain"])
        self.assertEqual([c["reason"] for c in found["candidates"]], ["bank", "batch", "bank"])
        self.assertEqual(found["candidates"][1]["keep_id"], "p_1")
        self.assertEqual(found["candidates"][2]["existing_id"], "q_1")
        for item in found["candidates"]:
            self.assertEqual(len([x for x in found["candidates"]
                                  if x["item_id"] == item["item_id"]]), 1)

    def test_07_signals_are_expandable_rows(self) -> None:
        found = pending_dedupe.collect_candidates(
            [_pool_row("p_1", _doc(STEM_POOL), 1)], [_bank_row("q_1", _doc(STEM_BANK))])
        signals = found["candidates"][0]["signals"]
        self.assertEqual([s["key"] for s in signals],
                         ["mark", "signature", "skeleton", "numbers", "answer"])
        for signal in signals:
            self.assertIsInstance(signal["hit"], bool)
            self.assertTrue(signal["detail"])

    def test_08_max_compare_early_exit_still_keeps_the_best_hit(self) -> None:
        """军令 #32 · G2 · S2：撞到 ``MAX_COMPARE`` 从批内那一圈退出时，已经找到的 ``best`` 不许丢。

        旧写法是「批内圈一 break 就把外圈整个 break 掉」，那条题的 ``best`` 还挂在局部变量里
        没进候选账 —— 于是「比到一半被上限截断」在老师那儿等于「这道题没重题」，
        而 ``truncated`` 只说「截了」，说不出**截掉的那条其实已经有命中**。
        这里把上限压到 1 次比对：``p_1`` 先和 ``p_2`` 比出「较像」（best 已成立），
        下一步就撞上上限退出，主库那一圈根本进不去。修法后的形状是
        「外圈照旧停、best 先入账」，所以候选里必须有 ``p_1``，且它报的是批内命中。
        """
        stem_batch = r"已知向量 $\vec{a}=(1,2)$，$\vec{b}=(x,4)$，若 $\vec{a}\perp\vec{b}$，则 $x$ 的值为（　　）。"
        stem_third = r"一个圆柱的底面半径为 $2$，高为 $3$，则它的体积为（　　）。"
        rows = [_pool_row("p_1", _doc(STEM_POOL), 1),
                _pool_row("p_2", _doc(stem_batch), 2),
                _pool_row("p_3", _doc(stem_third), 3)]
        main = [_bank_row("q_1", _doc(STEM_UNRELATED))]
        with mock.patch.object(pending_dedupe, "MAX_COMPARE", 1):
            found = pending_dedupe.collect_candidates(rows, main)
        self.assertEqual(found["compared"], 1, "上限压到一次，别拿多比几次蒙过去")
        self.assertTrue(found["truncated"], "没撞上限的形态验的是另一件事，本用例必须截断")
        self.assertEqual([c["item_id"] for c in found["candidates"]], ["p_1"],
                         "早退丢掉 best＝把已经找到的命中报成没有（S2）")
        hit = found["candidates"][0]
        self.assertEqual((hit["reason"], hit["keep_id"], hit["existing_id"]),
                         ("batch", "p_2", ""), "批内那一圈的最优对，不是主库那一圈")
        self.assertEqual(hit["level"], "fairly_similar")


class _IdleThread:
    """只登记不启动的线程替身：``save_draft`` 的后台初查必须由测试显式触发。

    放真线程上路会同时踩两个坑——后台那轮用的是**正确**的 provider，会把我特意
    喂错 provider 的那轮 ``failed`` 覆盖掉；连接没关干净时临时目录还删不掉
    （Windows 上的 ``PermissionError``）。本模块判的是「结论的形状」，不是时序。
    """

    instances: list["_IdleThread"] = []

    def __init__(self, target=None, args=(), kwargs=None, name=None, daemon=None) -> None:
        self.target, self.args, self.kwargs, self.name = target, tuple(args), kwargs or {}, name
        self.started = False

    def start(self) -> None:
        self.started = True


class _NoSpawnThreading:
    """顶替 ``pending_bank.threading``：本模块只用到 ``Thread``。"""

    Thread = _IdleThread


class _ScanCase(unittest.TestCase):
    """带临时工作区的整链路用例：入池 → 初查 → 清空缓存 → 再读。"""

    def setUp(self) -> None:
        from app.core import bank, pending_bank, pending_batches, pending_db as pdb
        from app.core.config import settings

        self.bank = bank
        self.pending_bank = pending_bank
        self.pending_batches = pending_batches
        self.pdb = pdb
        _IdleThread.instances = []
        patcher = mock.patch.object(pending_bank, "threading", _NoSpawnThreading)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (os.environ.get("JZO_DATA_DIR"), os.environ.get("JZO_PLUGINS_DIR"),
                       settings.workspace_id)
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        # 现网指针可能指向别的工作区：不置 None，data_dir 会拼成 tmp/workspaces/<id>
        settings.workspace_id = None
        self.addCleanup(self._restore_env)
        self.db_path = Path(self.tmp.name) / "banks" / f"{PLUGIN_ID}.db"
        bank.init_bank(PLUGIN_ID, db_path=self.db_path)
        pending_dedupe._scan_cache.clear()
        self.addCleanup(pending_dedupe._scan_cache.clear)

    def _restore_env(self) -> None:
        for key, value in zip(("JZO_DATA_DIR", "JZO_PLUGINS_DIR"), self._saved[:2]):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        from app.core.config import settings as _s
        _s.workspace_id = self._saved[2]

    def _seed_bank(self, *documents: dict) -> list[str]:
        ids: list[str] = []
        con = sqlite3.connect(self.db_path)
        try:
            for index, document in enumerate(documents, start=1):
                question_id = f"q_seed{index:04d}"
                ids.append(question_id)
                con.execute(
                    "INSERT INTO questions (id, type, stem, options, answer, solution,"
                    " extensions, difficulty, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (question_id, document["type"], document["stem"],
                     wire.dumps(document["options"], ensure_ascii=False,
                                separators=(",", ":")),
                     "A", None, "[]", document.get("difficulty", "L2"),
                     "2026-01-15T09:00:00+08:00", "2026-01-15T09:00:00+08:00"))
            con.commit()
        finally:
            con.close()
        return ids

    def _draft(self, *documents: dict) -> dict:
        return self.pending_bank.save_draft([{"question": d} for d in documents])

    def _restart(self) -> None:
        """模拟底座重启：进程内缓存与世代号全部归零，库与主库原样不动。"""
        pending_dedupe._scan_cache.clear()
        pending_dedupe._scan_seq = 0

    def _scan(self, batch_id: str) -> None:
        pending_dedupe.warm_batch_scan(batch_id, PLUGIN_ID)


class PersistenceTest(_ScanCase):
    """判据 3.3／3.4：结论落库、重启可读、失败也落库。"""

    def test_01_scan_writes_account_and_findings(self) -> None:
        self._seed_bank(_doc(STEM_BANK))
        saved = self._draft(_doc(STEM_POOL))
        batch_id = saved["batch_id"]
        self._scan(batch_id)
        state = pending_dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "done", msg=str(state))
        self.assertGreaterEqual(state["candidate_count"], 1)
        self.assertEqual(state["candidates"][0]["reason"], "bank")
        self.assertEqual(state["tier"], "loose")
        con = self.pdb.connect()
        try:
            row = con.execute("SELECT status, tier, scanned FROM dedupe_scans"
                              " WHERE batch_id = ?", (batch_id,)).fetchone()
            self.assertEqual((row["status"], row["tier"]), ("done", "loose"))
            findings = con.execute("SELECT item_id, level FROM dedupe_findings"
                                   " WHERE batch_id = ?", (batch_id,)).fetchall()
            self.assertEqual(len(findings), len(state["candidates"]))
            self.assertIn(findings[0]["level"], bank_dedupe.LEVEL_ORDER)
        finally:
            con.close()

    def test_02_restart_still_reports_the_same_conclusion(self) -> None:
        self._seed_bank(_doc(STEM_BANK))
        batch_id = self._draft(_doc(STEM_POOL))["batch_id"]
        self._scan(batch_id)
        before = pending_dedupe.scan_state(batch_id)
        self._restart()
        after = pending_dedupe.scan_state(batch_id)
        for key in ("status", "scanned", "redundant", "batch_redundant",
                    "bank_redundant", "main_scanned", "tier", "candidate_count"):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual([c["item_id"] for c in before["candidates"]],
                         [c["item_id"] for c in after["candidates"]])
        self.assertEqual([c["signals"] for c in before["candidates"]],
                         [c["signals"] for c in after["candidates"]])
        self.assertNotIn("seq", after)

    def test_03_restart_backfills_the_cache(self) -> None:
        self._seed_bank(_doc(STEM_BANK))
        batch_id = self._draft(_doc(STEM_POOL))["batch_id"]
        self._scan(batch_id)
        self._restart()
        self.assertEqual(pending_dedupe._scan_cache, {})
        pending_dedupe.scan_state(batch_id)
        self.assertIn(batch_id, pending_dedupe._scan_cache)

    def test_04_never_scanned_batch_stays_pending(self) -> None:
        state = pending_dedupe.scan_state("B-never")
        self.assertEqual(state, {"status": "pending", "pooled": 0})

    def test_05_clean_scan_reports_zero_not_pending(self) -> None:
        # 「扫过且 0 条重复」必须是 done + 零候选，别和「没扫过」混成一件事
        self._seed_bank(_doc(STEM_UNRELATED))
        batch_id = self._draft(_doc(STEM_POOL))["batch_id"]
        self._scan(batch_id)
        self._restart()
        state = pending_dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["candidates"], [])
        self.assertEqual(state["redundant"], 0)

    def test_06_failed_scan_survives_restart(self) -> None:
        # 判据 3.4：主库读不通 → 初查失败、可重试；重启后读到的仍是这句话
        batch_id = self._draft(_doc(STEM_POOL))["batch_id"]
        pending_dedupe.warm_batch_scan(batch_id, "org.jiuzhang.bank-missing")
        state = pending_dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["code"], "dedupe_scan_bank_unavailable")
        self.assertTrue(state["retryable"])
        self.assertIn("可重试", state["message"])
        self.assertEqual(state.get("redundant"), None)
        self._restart()
        again = pending_dedupe.scan_state(batch_id)
        self.assertEqual(again["status"], "failed")
        self.assertEqual(again["code"], "dedupe_scan_bank_unavailable")
        self.assertTrue(again["retryable"])

    def test_07_recount_replaces_previous_findings(self) -> None:
        self._seed_bank(_doc(STEM_BANK))
        batch_id = self._draft(_doc(STEM_POOL))["batch_id"]
        self._scan(batch_id)
        first = pending_dedupe.scan_state(batch_id)["candidate_count"]
        self._scan(batch_id)          # 同一批再扫一次：结论覆盖，不累加
        self._restart()
        state = pending_dedupe.scan_state(batch_id)
        self.assertEqual(state["candidate_count"], first)
        con = self.pdb.connect()
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM dedupe_scans").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM dedupe_findings").fetchone()[0], first)
        finally:
            con.close()

    def test_08_failed_rescan_does_not_wipe_previous_findings(self) -> None:
        """军令 #32 · G2 · S1：一次重扫**失败**不许把上一代已落的 ``dedupe_findings`` 抹平。

        旧写法在写任何状态前都先 ``DELETE FROM dedupe_findings WHERE batch_id=?``，
        于是「主库读不通」这一趟把候选账清成 0 行：卡片与琥珀灯的账同拍断（判据 3.3/3.4），
        而且失败态本来就回不了候选，抹掉的行只能靠下一次成功重扫找回来 —— 老师重试前
        那一段是**裸的空账**。
        幂等口径在这里定死：**同一批的 findings 只由最新一代 ``done`` 拥有**；
        ``failed`` 只更新 ``dedupe_scans`` 那一行，一行 findings 都不碰；
        ``done`` 重扫整批替换（test_07 钉住不翻倍），所以「二次扫描不抹账」
        与「二次扫描不累账」是同一枚硬币的两面。
        """
        self._seed_bank(_doc(STEM_BANK))
        batch_id = self._draft(_doc(STEM_POOL))["batch_id"]
        self._scan(batch_id)
        state = pending_dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "done", msg=str(state))
        first = state["candidate_count"]
        self.assertGreaterEqual(first, 1, "零候选的本用例抹不抹都看不出来，先保证有账")

        def findings() -> list[tuple[str, str]]:
            con = self.pdb.connect()
            try:
                return [(str(row["item_id"]), str(row["level"])) for row in con.execute(
                    "SELECT item_id, level FROM dedupe_findings WHERE batch_id = ?"
                    " ORDER BY item_id ASC", (batch_id,))]
            finally:
                con.close()

        def scan_row() -> tuple[str, int]:
            con = self.pdb.connect()
            try:
                row = con.execute("SELECT status, generation FROM dedupe_scans"
                                  " WHERE batch_id = ?", (batch_id,)).fetchone()
                return (str(row["status"]), int(row["generation"] or 0))
            finally:
                con.close()

        before = findings()
        self.assertEqual(len(before), first)
        # 喂一个不存在的 provider 重扫 → 落 failed（判据 3.4 的同一条路径）
        pending_dedupe.warm_batch_scan(batch_id, "org.jiuzhang.bank-missing")
        failed = pending_dedupe.scan_state(batch_id)
        self.assertEqual(failed["status"], "failed", msg=str(failed))
        self.assertEqual(findings(), before, "S1：失败态一行 findings 都不许抹")
        # 直接读库：等价于「底座重启后拿到的那一行」（重启可读由 test_06 钉，这里只验账）
        self.assertEqual(scan_row()[0], "failed", "落库的这代确实是 failed")
        # 重试成功：整批替换，条数回到同一代，不翻倍
        self._scan(batch_id)
        self.assertEqual(pending_dedupe.scan_state(batch_id)["status"], "done")
        self.assertEqual(findings(), before, "done 重扫是覆盖，不是叠加")
        self._restart()
        self.assertEqual(pending_dedupe.scan_state(batch_id)["candidate_count"], first,
                         "重启后从库里读回的还是同一代账（S1 的后半：账没被失败那一代掏空）")


class SchemaMigrationTest(unittest.TestCase):
    """R03 迁移三律：新表只补不删，旧库连上即升到 7。"""

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

    def test_01_version_is_ten(self) -> None:
        self.assertEqual(pending_db.SCHEMA_VERSION, 11)

    def test_02_old_database_gains_the_two_tables(self) -> None:
        con = pending_db.connect()
        con.close()
        path = pending_db.pending_db_path()
        con = sqlite3.connect(path)
        try:
            self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 11)
            names = {row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertIn("dedupe_scans", names)
            self.assertIn("dedupe_findings", names)
            self.assertIn("pending_questions", names)   # 既有表一个都没少
        finally:
            con.close()

    def test_03_v6_database_migrates_without_losing_rows(self) -> None:
        path = pending_db.pending_db_path()
        con = sqlite3.connect(path)
        try:
            # 先把它退回「v6 且已有批次」的样子：建 v6 的表、塞一行、版本写 6
            con.executescript(pending_db._SCHEMA.strip())
            con.execute(
                "INSERT INTO batches (batch_id, label, created_at, updated_at)"
                " VALUES ('B-1', '旧批', '2026-01-01T00:00:00+08:00', '2026-01-01T00:00:00+08:00')")
            con.execute("DROP TABLE dedupe_scans")
            con.execute("DROP TABLE dedupe_findings")
            con.execute("PRAGMA user_version = 6")
            con.commit()
        finally:
            con.close()
        connect = pending_db.connect()
        connect.close()
        con = sqlite3.connect(path)
        try:
            self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 11)
            self.assertEqual(con.execute("SELECT label FROM batches").fetchone()[0], "旧批")
            names = {row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertIn("dedupe_scans", names)
        finally:
            con.close()

    def test_04_newer_database_than_supported_is_refused(self) -> None:
        path = pending_db.pending_db_path()
        con = sqlite3.connect(path)
        con.execute("PRAGMA user_version = 99")
        con.commit()
        con.close()
        with self.assertRaises(pending_db.PendingError):
            pending_db.connect()


if __name__ == "__main__":
    unittest.main()
