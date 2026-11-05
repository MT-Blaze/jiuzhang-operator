"""一键剔除本批次重复题：``app/core/pending_bank.py::purge_batch_duplicates`` 的裁决口径。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pending_purge``

钉住 §3.7 的十七条判据，外加「写口只认 questions:write」的路由/中继守卫：

- dry-run 只读：池内行数、``batches.total``、``pending_count`` 一个字都不动；
- ``batch`` 组保留 seq 最小者，``bank`` 组只删池内行，主库一个字节都不碰；
- 载荷自洽只防截断与改写（``expected_drop_ids`` 顺序不敏感、少一项就 400）；
- 执行口径是**勾选集子集**：已不重复回 409 stale、勾到保留者回 409 keep_selected，
  剔空必须 ``allow_empty=true``——四道闸任何一道不成立都整批不动；
- 剔完账目同构回写：``total`` 减删除数、``pending_count`` 取真实行数；
- G5 回归：batch 组的保留者即使与主库同指纹，也不再被单列成 bank 组。
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PLUGIN_ID = "org.jiuzhang.bank-engine"
STAMP = "2026-01-15T09:00:00+08:00"
STEM = "一键剔除口径题：已知 $f(x)=x^2-5x+6$，求它的零点个数（　　）。"


def _doc(stem: str = STEM) -> dict:
    """一道合契约的选择题；只换题干就能造出「指纹相同 / 不同」两种料。"""
    return {
        "type": "single_choice",
        "stem": stem,
        "difficulty": "L2",
        "options": [
            {"key": "A", "content": "$1$"},
            {"key": "B", "content": "$2$"},
            {"key": "C", "content": "$3$"},
            {"key": "D", "content": "$4$"},
        ],
        "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
        "solution": "由 $x^2-5x+6=0$ 得 $x=2$ 或 $x=3$，共两个零点。",
    }


class PurgeCase(unittest.TestCase):
    """隔离临时工作区：池库、主库、配图目录全部落在同一座 tmp 下。"""

    def setUp(self) -> None:
        from app.core.config import settings
        from app.core import (bank, pending_bank, pending_bank_batches,
                              pending_batches, pending_dedupe, pending_db)

        self.settings = settings
        self.bank = bank
        self.pending_bank = pending_bank
        self.pending_bank_batches = pending_bank_batches
        self.pending_batches = pending_batches
        self.pending_dedupe = pending_dedupe
        self.pending_db = pending_db
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (os.environ.get("JZO_DATA_DIR"), os.environ.get("JZO_PLUGINS_DIR"),
                       os.environ.get("JZO_POOL_ADMIT_DISABLED"), settings.workspace_id)
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        settings.workspace_id = None
        self.addCleanup(self._restore_env)
        # 军令 #32 · S5d：本模块的用例前提全是「两条都还躺在待审里」，而判据 3.5 让
        # save_draft 的后台链（warm_batch_scan → admit_into_pool）**扫完就自己把冗余那条
        # 搬进重题池**——搬走之后 `pending_questions` 只剩 1 行，dry-run 的 scanned/drop_ids
        # 如实变成 1，与用例期望的 2 相撞（PM 复跑抓到的 `1 != 2` 就是这么来的）。
        # 这不是并发缺陷：那一行确实已经进了池，卡上 pending_count 也随之 -1，底座会发
        # system.pending_updated 回流。所以按 S3 既有的口子把自动抽走按住，**不动任何断言**，
        # 与 test_pending_meta / test_pending_api / test_pending_dedupe_scan 同一处理方式。
        os.environ["JZO_POOL_ADMIT_DISABLED"] = "1"
        # 军令 #31 · 3.1a 起，save_draft 会甩出一个名为 jzo-dedupe-warm 的 daemon 初查线程，
        # 它持着本 tmp 里池库/主库的 SQLite 句柄：不收口就 cleanup 必撞
        # PermissionError: [WinError 32]。addCleanup 后进先出，这条排在 tmp.cleanup 之前。
        # 注意这条只负责**收句柄**，不负责撤销已落地的抽走——抽走靠上面那个开关挡在门外。
        self.addCleanup(self._settle_dedupe_threads)
        self.db_path = Path(self.tmp.name) / "banks" / f"{PLUGIN_ID}.db"
        bank.init_bank(PLUGIN_ID, db_path=self.db_path)

    def _settle_dedupe_threads(self, timeout: float = 20.0) -> None:
        """按线程名 join 掉在跑的后台初查线程；超时就如实报，不静默吞掉句柄泄漏。"""
        stragglers = [t for t in threading.enumerate()
                      if getattr(t, "name", "") == "jzo-dedupe-warm"]
        deadline = time.monotonic() + timeout
        for thread in stragglers:
            thread.join(max(0.1, deadline - time.monotonic()))
        alive = [thread.name for thread in stragglers if thread.is_alive()]
        if alive:
            self.fail(f"后台初查线程未在 {timeout} 秒内收口，tmp 目录里的 SQLite 句柄还开着：{alive}")

    def _restore_env(self) -> None:
        # P1④：三个环境变量（含 ``JZO_POOL_ADMIT_DISABLED``）由这一条一次性还原，
        # 恢复器在 setUp 里**先登记再改环境**，用例失败也照跑（finally 语义）。
        for key, value in zip(("JZO_DATA_DIR", "JZO_PLUGINS_DIR",
                               "JZO_POOL_ADMIT_DISABLED"), self._saved[:3]):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.settings.workspace_id = self._saved[3]

    # ---------- 夹具 ----------

    def _seed_bank(self, *docs: dict) -> list[str]:
        """往主库铺题，返回题号；options 按存储层口径序列化。"""
        ids: list[str] = []
        con = sqlite3.connect(self.db_path)
        try:
            for index, document in enumerate(docs, start=1):
                question_id = f"q_seed{index:04d}"
                ids.append(question_id)
                con.execute(
                    "INSERT INTO questions (id, type, stem, options, answer, solution,"
                    " extensions, difficulty, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        question_id,
                        document["type"],
                        document["stem"],
                        json.dumps(document["options"], ensure_ascii=False, separators=(",", ":")),
                        "A",
                        document.get("solution"),
                        "[]",
                        document.get("difficulty", "L2"),
                        STAMP,
                        STAMP,
                    ),
                )
            con.commit()
        finally:
            con.close()
        return ids

    def _draft(self, *docs: dict, batch_id: str | None = None, **kwargs) -> tuple[str, list[str]]:
        payload = [{"question": document} for document in docs]
        if batch_id:
            kwargs["batch_id"] = batch_id
        saved = self.pending_bank.save_draft(payload, **kwargs)
        return saved["batch_id"], saved["saved_ids"]

    def _pool_ids(self, batch_id: str) -> list[str]:
        con = self.pending_db.connect()
        try:
            rows = con.execute(
                "SELECT id FROM pending_questions WHERE batch_id = ? ORDER BY seq ASC, id ASC",
                (batch_id,),
            ).fetchall()
        finally:
            con.close()
        return [str(row["id"]) for row in rows]

    def _pool_count(self) -> int:
        con = self.pending_db.connect()
        try:
            return int(con.execute("SELECT COUNT(*) FROM pending_questions").fetchone()[0])
        finally:
            con.close()

    def _card(self, batch_id: str) -> dict:
        for card in self.pending_batches.batch_list()["batches"]:
            if card["batch_id"] == batch_id:
                return card
        raise AssertionError(f"批次列表里没有 {batch_id}")

    def _groups(self, batch_id: str) -> dict:
        return self.pending_dedupe.batch_duplicate_groups(batch_id, PLUGIN_ID)

    def _purge(self, batch_id: str, drop_ids: list[str], *,
               expected: list[str] | None = None, allow_empty: bool = False) -> dict:
        return self.pending_bank.purge_batch_duplicates(
            batch_id, PLUGIN_ID, drop_ids,
            sorted(drop_ids) if expected is None else expected,
            allow_empty=allow_empty,
        )

    def _assert_code(self, code: str, batch_id: str, drop_ids: list[str], **kwargs) -> None:
        with self.assertRaises(self.pending_bank.BatchPurgeError) as caught:
            self._purge(batch_id, drop_ids, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def _bank_count(self) -> int:
        con = sqlite3.connect(self.db_path)
        try:
            return int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        finally:
            con.close()

    # ---------- 判据 ----------

    def test_01_dry_run_leaves_every_ledger_untouched(self) -> None:
        self._seed_bank(_doc())
        batch_id, ids = self._draft(_doc(), _doc())
        before = (self._pool_count(), self._card(batch_id)["total"],
                  self._card(batch_id)["pending_count"])
        plan = self._groups(batch_id)
        self.assertEqual(len(plan["groups"]), 1)
        self.assertEqual(plan["scanned"], 2)
        self.assertEqual(self._pool_count(), before[0], "dry-run 不许动池子")
        self.assertEqual(self._card(batch_id)["total"], before[1], "dry-run 不许动总题数")
        self.assertEqual(self._card(batch_id)["pending_count"], before[2])
        self.assertEqual(plan["drop_ids"], [ids[1]])

    def test_02_batch_group_keeps_the_smallest_seq(self) -> None:
        batch_id, ids = self._draft(_doc(), _doc(), _doc())
        plan = self._groups(batch_id)
        group = plan["groups"][0]
        self.assertEqual(group["reason"], "batch")
        self.assertEqual(group["keep"], ids[0], "保留者必须是 seq 最小的那一条")
        self.assertEqual(group["drop"], ids[1:])
        self.assertEqual(group["seq_keep"], 1)
        self.assertEqual(plan["redundant"], 2)

    def test_03_bank_group_only_deletes_the_pool_copy(self) -> None:
        existing = self._seed_bank(_doc())[0]
        batch_id, ids = self._draft(_doc())
        plan = self._groups(batch_id)
        self.assertEqual(plan["groups"], [{
            "reason": "bank",
            "keep": "",
            "drop": [ids[0]],
            "fingerprint": plan["groups"][0]["fingerprint"],
            "existing_id": existing,
        }])
        result = self._purge(batch_id, [ids[0]], allow_empty=True)
        self.assertEqual(result["deleted"], [ids[0]])
        self.assertEqual(self._pool_ids(batch_id), [])
        self.assertEqual(self._bank_count(), 1, "主库一行都不许少")
        con = sqlite3.connect(self.db_path)
        try:
            still_there = con.execute(
                "SELECT id FROM questions WHERE id = ?", (existing,)).fetchone()
        finally:
            con.close()
        self.assertEqual(still_there[0], existing)

    def test_04_ledgers_follow_the_deletions(self) -> None:
        batch_id, ids = self._draft(_doc(), _doc(), _doc(), _doc(STEM.replace("6", "7")))
        self.assertEqual(self._card(batch_id)["total"], 4)
        result = self._purge(batch_id, ids[1:3])
        self.assertEqual(result["deleted"], sorted(ids[1:3]), "执行口按编号升序逐条删")
        card = self._card(batch_id)
        self.assertEqual(card["total"], 2, "总题数按删除条数递减")
        self.assertEqual(card["pending_count"], 2)
        self.assertEqual(card["pending_count"], self._pool_count())
        self.assertFalse(card["done"])
        self.assertFalse(result["batch"]["done"], "没剔空就不算收口")

    def test_05_expected_echo_mismatch_is_rejected(self) -> None:
        batch_id, ids = self._draft(_doc(), _doc())
        before = (self._pool_count(), self._card(batch_id)["total"])
        self._assert_code("batch_purge_expected_mismatch_client", batch_id, [ids[1]],
                          expected=["p_zzzzzzzzzzzzzzzz"])
        self.assertEqual((self._pool_count(), self._card(batch_id)["total"]), before)

    def test_06_length_equal_swap_is_still_caught(self) -> None:
        batch_id, ids = self._draft(_doc(), _doc(), _doc(STEM.replace("6", "7")))
        before = (self._pool_count(), self._card(batch_id)["total"])
        self._assert_code("batch_purge_selection_stale", batch_id, [ids[2]])
        self.assertEqual((self._pool_count(), self._card(batch_id)["total"]), before,
                         "长度相等也拦得住：判断的是「还重复吗」，不是「集合等不等」")

    def test_07_expected_order_is_not_significant_but_a_missing_item_is(self) -> None:
        batch_id, ids = self._draft(_doc(), _doc(), _doc())
        drops = ids[1:]
        result = self._purge(batch_id, drops, expected=list(reversed(drops)))
        self.assertEqual(result["deleted"], sorted(drops),
                         "expected 只做集合回显，顺序不该敏感")

        other_batch, other_ids = self._draft(_doc(), _doc(), _doc())
        before = self._pool_count()
        self._assert_code("batch_purge_expected_mismatch_client", other_batch,
                          other_ids[1:], expected=[other_ids[1]])
        self.assertEqual(self._pool_count(), before)

    def test_08_foreign_pending_id_is_rejected(self) -> None:
        batch_id, ids = self._draft(_doc(), _doc())
        other_batch, other_ids = self._draft(_doc(STEM.replace("6", "7")))
        self.assertNotEqual(batch_id, other_batch)
        before = (self._pool_count(), self._card(batch_id)["total"])
        self._assert_code("batch_purge_pending_not_in_batch", batch_id, [other_ids[0]])
        self.assertEqual((self._pool_count(), self._card(batch_id)["total"]), before)

    def test_09_refresh_failure_rolls_the_whole_batch_back(self) -> None:
        batch_id, ids = self._draft(_doc(), _doc(), _doc())
        before = (self._pool_count(), self._card(batch_id)["total"],
                  self._card(batch_id)["pending_count"])
        with mock.patch.object(self.pending_bank_batches, "refresh_batch",
                               side_effect=RuntimeError("账目写不进去")):
            with self.assertRaises(RuntimeError):
                self._purge(batch_id, ids[1:])
        self.assertEqual((self._pool_count(), self._card(batch_id)["total"],
                          self._card(batch_id)["pending_count"]), before, "事务必须整体回滚")

    def test_10_purge_is_a_write_and_needs_questions_write(self) -> None:
        from app.api import pending as pending_api
        from app.core.security import require_write_token

        def route_for(path: str, method: str):
            for item in pending_api.router.routes:
                if item.path == path and method in (item.methods or set()):
                    return item
            return None

        read = route_for("/api/pending/batches/{batch_id}/duplicates", "GET")
        write = route_for("/api/pending/batches/{batch_id}/purge-duplicates", "POST")
        self.assertIsNotNone(read)
        self.assertIsNotNone(write)

        def guards(route) -> list:
            return [dep.call for dep in route.dependant.dependencies if hasattr(dep, "call")]

        self.assertIn(require_write_token, guards(write), "剔除是写动作，必须鉴权")
        self.assertNotIn(require_write_token, guards(read), "dry-run 是只读，不该要令牌")

        relay = (ROOT / "static/js/stage_relay_io.js").read_text(encoding="utf-8")
        read_branch, write_branch = relay.split('if (method === "pending.save_draft"', 1)
        self.assertIn('"pending.batch_duplicates"', read_branch)
        self.assertNotIn('"pending.purge_duplicates"', read_branch,
                         "写口不许混进只读分支，否则绕过 questions:write")
        self.assertIn('"pending.purge_duplicates"', write_branch)
        self.assertIn('pendingPermissions.indexOf("questions:write")', write_branch)

    def test_11_similar_but_not_identical_is_not_listed(self) -> None:
        left = _doc()
        right = _doc(STEM.replace("6", "7"))
        batch_id, ids = self._draft(left, right)
        self.assertGreaterEqual(
            self.pending_dedupe.similarity(left["stem"], right["stem"]), 0.9,
            "夹具必须先真的相似，判据才有意义")
        plan = self._groups(batch_id)
        self.assertEqual(plan["groups"], [])
        self.assertEqual(plan["drop_ids"], [])
        self.assertEqual(plan["redundant"], 0)

    def test_12_subset_execution_only_deletes_what_was_ticked(self) -> None:
        existing = self._seed_bank(_doc(STEM.replace("6", "7")))
        batch_id, ids = self._draft(_doc(), _doc(), _doc(STEM.replace("6", "7")))
        plan = self._groups(batch_id)
        self.assertEqual([group["reason"] for group in plan["groups"]], ["batch", "bank"])
        bank_drop = [item for group in plan["groups"] if group["reason"] == "bank"
                     for item in group["drop"]]
        self.assertEqual(len(bank_drop), 1)

        result = self._purge(batch_id, [ids[1]])
        self.assertEqual(result["deleted"], [ids[1]])
        self.assertIn(bank_drop[0], self._pool_ids(batch_id), "未勾的 bank 组必须留下")
        self.assertEqual(self._bank_count(), 1)
        self.assertEqual(result["new_redundant"], 1, "未勾的重复要如实报数")
        con = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(con.execute(
                "SELECT id FROM questions WHERE id = ?", (existing[0],)).fetchone()[0], existing[0])
        finally:
            con.close()

    def test_13_selection_that_stopped_being_duplicate_is_409(self) -> None:
        existing = self._seed_bank(_doc(STEM.replace("6", "7")))
        batch_id, ids = self._draft(_doc(STEM.replace("6", "7")))
        plan = self._groups(batch_id)
        self.assertEqual(plan["drop_ids"], [], "bank 组默认不勾，drop_ids 只装 batch 组")
        drop = plan["groups"][0]["drop"]
        self.assertEqual(drop, [ids[0]])
        con = sqlite3.connect(self.db_path)
        try:
            con.execute("DELETE FROM questions WHERE id = ?", (existing[0],))
            con.commit()
        finally:
            con.close()
        before = (self._pool_count(), self._card(batch_id)["total"],
                  self._card(batch_id)["pending_count"])
        self._assert_code("batch_purge_selection_stale", batch_id, drop)
        self.assertEqual((self._pool_count(), self._card(batch_id)["total"],
                          self._card(batch_id)["pending_count"]), before)

    def test_14_new_duplicate_after_dry_run_is_reported_not_deleted(self) -> None:
        batch_id, ids = self._draft(_doc(), _doc())
        plan = self._groups(batch_id)
        self.assertEqual(plan["drop_ids"], [ids[1]])
        # dry-run 之后老师又往同一批塞了一条同指纹题：它不在勾选集里，必须留下。
        _, fresh = self._draft(_doc(), batch_id=batch_id)
        result = self._purge(batch_id, [ids[1]])
        self.assertEqual(result["deleted"], [ids[1]])
        self.assertEqual(self._pool_ids(batch_id), [ids[0], fresh[0]])
        self.assertEqual(result["new_redundant"], 1)

    def test_15_ticking_the_keeper_is_rejected(self) -> None:
        batch_id, ids = self._draft(_doc(), _doc())
        before = (self._pool_count(), self._card(batch_id)["total"])
        self._assert_code("batch_purge_keep_selected", batch_id, [ids[0]])
        self.assertEqual((self._pool_count(), self._card(batch_id)["total"]), before)

    def test_16_keeper_also_in_bank_is_not_relisted_as_bank_group(self) -> None:
        self._seed_bank(_doc())
        batch_id, ids = self._draft(_doc(), _doc())
        plan = self._groups(batch_id)
        self.assertEqual(len(plan["groups"]), 1, "G5：keep 不许再列成 bank 组")
        group = plan["groups"][0]
        self.assertEqual(group["reason"], "batch")
        self.assertEqual(group["keep"], ids[0])
        self.assertNotIn(ids[0], [item for other in plan["groups"] for item in other["drop"]])
        result = self._purge(batch_id, [ids[1]])
        self.assertEqual(result["new_redundant"], 0, "剔完就该清零，不能永久计一条在途重复")

    def test_17_emptying_the_batch_needs_explicit_confirmation(self) -> None:
        self._seed_bank(_doc(STEM.replace("6", "7")))
        backups = Path(self.tmp.name) / "pending_sources"
        backups.mkdir(parents=True, exist_ok=True)
        backup = backups / "原卷.pdf"
        backup.write_bytes(b"%PDF-1.4 test")
        batch_id, ids = self._draft(
            _doc(STEM.replace("6", "7")), source_backup="pending_sources/原卷.pdf")
        plan = self._groups(batch_id)
        # bank 组默认不勾，所以服务端按默认勾选集算出的 will_empty 为假；
        # 老师手动勾上这一条后才是 scanned - 1 == 0，闸门必须由执行口拦。
        self.assertFalse(plan["will_empty"])
        self.assertEqual(plan["groups"][0]["drop"], [ids[0]])
        self._assert_code("batch_purge_empty_not_confirmed", batch_id, [ids[0]])
        self.assertEqual(self._pool_ids(batch_id), [ids[0]])
        self.assertTrue(backup.is_file(), "闸门拒绝时原卷副本不许动")

        result = self._purge(batch_id, [ids[0]], allow_empty=True)
        self.assertEqual(result["deleted"], [ids[0]])
        self.assertTrue(result["backup_removed"])
        self.assertTrue(self._card(batch_id)["done"])
        self.assertFalse(backup.exists(), "剔空后原卷副本必须物理删除")


if __name__ == "__main__":
    unittest.main()
