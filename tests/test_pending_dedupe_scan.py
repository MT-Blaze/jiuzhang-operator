"""导入批次后台自动初查（军令 #31 · 3.1a）：``pending_dedupe.warm_batch_scan`` /
``scan_state`` 与 ``pending_bank.save_draft`` 的落池即扫挂点。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pending_dedupe_scan``

判据来源：``.qoder/records/biz/2026-11/20261102_dedupe-batch-purge-latex-preview.md``
``[DESIGN-2] ⑥`` 第 1~10 条（:810-821），其中第 3/5 条按 ``[DESIGN-2 勘误] ⑤``
（:913-921）的覆盖版执行；第 7~9 条属真机探针，本模块只覆盖单测侧。

钉住六条口径：

- **落池即扫，无需人工点按**：一次 ``save_draft`` 之后除它本身外没有任何触发方，
  ``scan_state`` 必须自己走到 ``done``（判据 1）；
- **同步路径不判重**：``save_draft`` 返回那一刻缓存里什么都没有（判据 2；实现只有
  ``pending/done/failed`` 三态，无 ``running``，故不断言 ``running``）；
- **只读增强**：初查零写主库、零写池子，同批次重复触发仍只有一条缓存（判据 3a）；
- **主库读不通绝不拦导入**：``failed`` 态带 ``code`` 与 ``retryable``，``save_draft``
  照常成功；provider 取不到也只是 ``failed``，异常不许冒出线程（判据 4 + 补漏 8）；
- **卡片向后兼容**：``batch_card`` 既有 11 键零缺失/零改名/零换型，第 12 键 ``dedupe``
  恒为 dict，无缓存即 ``{"status": "pending"}``（判据 5 + ⑤ 重写版）；
- **占位轮不挂任务**：``origin=="ingest"`` 且本次未传 ``batch_id`` 时
  ``dedupe_queued is False`` 且一个线程都不起（⑤ 第 3b 条的底座侧口径）。

时序纪律：等 daemon 线程只用 ``join``，线程体默认被一道 ``Event`` 闸拦住、由测试显式
放行，**不用 ``time.sleep`` 赌时序**（上一轮 ``test_plugin_update`` 负载抖动变红的先例）。
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
FAIL_CODE = "dedupe_scan_bank_unavailable"
# 卡片既有 11 键（app/core/pending_batches.py:67-79），v9 加原卷页图两键，
# v10 再加扫描批标记，第 15 键才是 dedupe
CARD_KEYS = {
    "batch_id", "label", "created_at", "updated_at", "source_backup", "source_name",
    "meta", "approved_count", "total", "pending_count", "done",
    "page_only", "scan_batch", "page_count",
}
CARD_TYPES = {
    "batch_id": str, "label": str, "created_at": str, "updated_at": str,
    "source_backup": str, "source_name": str, "meta": dict,
    "approved_count": int, "total": int, "pending_count": int, "done": bool,
    "page_only": bool, "scan_batch": bool, "page_count": int,
}

STEM_A = "初查口径题甲：已知 $f(x)=x^2-5x+6$，求它的零点个数（　　）。"
STEM_B = "初查口径题乙：在三角形 $ABC$ 中已知 $AB=3$、$AC=4$，求角 $A$ 的大小。"


def _doc(stem: str) -> dict:
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


class _ThreadProxy:
    """``pending_bank.threading`` 的替身：只换 ``Thread``，其余属性一律转发真模块。

    造出来的线程默认**卡在闸上不干活**，由测试显式 ``_drain()`` 放行并 ``join``：
    这样「``save_draft`` 返回时刻缓存里什么都没有」是确定的事实，不是赌出来的。
    """

    def __init__(self, recorder: list, gate: threading.Event) -> None:
        self._recorder = recorder
        self._gate = gate

    def __getattr__(self, name: str):
        return getattr(threading, name)

    def Thread(self, target=None, args=(), kwargs=None, name=None, daemon=None):
        gate, base = self._gate, target

        def _wrapped() -> None:
            gate.wait(30.0)
            if base is not None:
                base(*tuple(args), **(kwargs or {}))

        thread = threading.Thread(target=_wrapped, name=name, daemon=daemon)
        self._recorder.append(thread)
        return thread


class DedupeScanCase(unittest.TestCase):
    """隔离临时工作区：池库、主库、配图目录全部落在同一座 tmp 下。"""

    def setUp(self) -> None:
        from app.core.config import settings
        from app.core import bank, pending_bank, pending_batches, pending_dedupe, pending_db

        self.settings = settings
        self.bank = bank
        self.pending_bank = pending_bank
        self.pending_batches = pending_batches
        self.dedupe = pending_dedupe
        self.pending_db = pending_db
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (os.environ.get("JZO_DATA_DIR"), os.environ.get("JZO_PLUGINS_DIR"),
                       os.environ.get("JZO_POOL_ADMIT_DISABLED"), settings.workspace_id)
        # P1④：恢复器**先登记、再改环境**。addCleanup 即便用例失败也必跑（finally 语义），
        # 而原来那句 ``os.environ.pop`` 夹在两次赋值之间，留着「改了却没登记」的窗口；
        # 更关键的是 ``JZO_POOL_ADMIT_DISABLED`` 原先游离在 ``_restore_env`` 之外，
        # 读代码要翻两处才知道本模块动了哪几个环境变量。
        self.addCleanup(self._restore_env)
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        # 本模块测的是初查的账目与线程编排；抽走（判据 3.5）会把命中的行从待审池
        # 删掉，「缓存＝引擎」「redundant≥1」这些前提就此对不上。抽走本身由
        # tests/test_pending_pool.py 的 PoolEvictionTest 六条盯死，这里按用例隔离关掉。
        os.environ["JZO_POOL_ADMIT_DISABLED"] = "1"
        settings.workspace_id = None
        self.db_path = Path(self.tmp.name) / "banks" / f"{PLUGIN_ID}.db"
        bank.init_bank(PLUGIN_ID, db_path=self.db_path)
        # 模块级进程内单例：不清会跨用例串味（判据 3a 的「仅一条缓存」尤其依赖它）
        self.dedupe._scan_cache.clear()
        self.addCleanup(self.dedupe._scan_cache.clear)
        self.threads: list = []
        self.gate = threading.Event()
        self.addCleanup(self._settle_threads)
        self._thread_patcher = mock.patch.object(
            self.pending_bank, "threading", _ThreadProxy(self.threads, self.gate))
        self._thread_patcher.start()
        self.addCleanup(self._thread_patcher.stop)

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

    def _settle_threads(self) -> None:
        """用例收尾兜底放行，避免卡在闸上的 daemon 线程拖到解释器退出。"""
        self.gate.set()
        for thread in self.threads:
            thread.join(timeout=2.0)

    # ---------- 夹具 ----------

    def _seed_bank(self, *docs: dict) -> list:
        """往主库铺题（照 ``tests/test_pending_purge.py:87`` 的存储层口径）。"""
        ids = []
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
                        question_id, document["type"], document["stem"],
                        json.dumps(document["options"], ensure_ascii=False,
                                   separators=(",", ":")),
                        "A", document.get("solution"), "[]",
                        document.get("difficulty", "L2"), STAMP, STAMP,
                    ),
                )
            con.commit()
        finally:
            con.close()
        return ids

    def _draft(self, *docs: dict, **kwargs) -> dict:
        return self.pending_bank.save_draft([{"question": document} for document in docs],
                                            **kwargs)

    def _drain(self, timeout: float = 20.0) -> int:
        """放行闸门并 join 全部后台初查线程；返回本次累计挂了几个线程。"""
        self.gate.set()
        for thread in self.threads:
            thread.join(timeout)
            self.assertFalse(thread.is_alive(), f"后台初查线程未在 {timeout} 秒内收口")
        return len(self.threads)

    def _cache_rows(self) -> dict:
        return dict(self.dedupe._scan_cache)

    def _card_from_list(self, batch_id: str) -> dict:
        for card in self.pending_batches.batch_list()["batches"]:
            if card["batch_id"] == batch_id:
                return card
        raise AssertionError(f"批次列表里没有 {batch_id}")

    def _pool_count(self, batch_id: str | None = None) -> int:
        con = self.pending_db.connect()
        try:
            if batch_id is None:
                return int(con.execute("SELECT COUNT(*) FROM pending_questions").fetchone()[0])
            return int(con.execute(
                "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?",
                (batch_id,)).fetchone()[0])
        finally:
            con.close()

    def _bank_count(self) -> int:
        con = sqlite3.connect(self.db_path)
        try:
            return int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        finally:
            con.close()

    def _load_scan_from_db(self, batch_id: str) -> dict:
        """把这一批的进程内缓存摘掉再读一次＝底座重启后从 ``dedupe_scans`` 回读的那一拍。"""
        self.dedupe._scan_cache.pop(batch_id, None)
        return self.dedupe.scan_state(batch_id)


class AutoScanTest(DedupeScanCase):
    def test_01_save_draft_alone_finishes_the_scan(self) -> None:
        """判据 1（无需人工点按本体）：除 save_draft 外零触发方，缓存自己走到 done。"""
        self._seed_bank(_doc(STEM_A))
        saved = self._draft(_doc(STEM_A))
        batch_id = saved["batch_id"]
        self.assertIs(saved["dedupe_queued"], True)
        self.assertEqual(self._drain(), 1, "一次入池只该挂一个后台初查任务")
        state = self.dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "done")
        self.assertGreaterEqual(state["redundant"], 1)
        self.assertEqual(state["bank_redundant"], 1, "与主库指纹全等要归主库那一栏")
        self.assertEqual(state["batch_redundant"], 0)
        self.assertEqual(state["scanned"], 1)
        self.assertTrue(state.get("at"))

    def test_02_sync_path_never_dedupes(self) -> None:
        """判据 2：save_draft 返回那一刻缓存里什么都没有（实现无 running 态）。"""
        self._seed_bank(_doc(STEM_A))
        saved = self._draft(_doc(STEM_A))
        batch_id = saved["batch_id"]
        self.assertEqual(self.dedupe.scan_state(batch_id)["status"], "pending")
        self.assertNotIn(batch_id, self._cache_rows(), "同步路径上不许写任何初查缓存")
        self.assertEqual(self._drain(), 1)
        self.assertEqual(self.dedupe.scan_state(batch_id)["status"], "done")

    def test_03_two_appends_stay_one_entry_and_write_nothing(self) -> None:
        """判据 3a：同批两次追加——缓存仅一条、scanned 收敛、初查零写。"""
        first = self._draft(_doc(STEM_A), _doc(STEM_B))
        batch_id = first["batch_id"]
        self._drain()
        before_bank = self._bank_count()
        self._draft(_doc("初查口径题丙：求 $\\lim_{x\\to 0}\\sin x / x$。"),
                    _doc("初查口径题丁：已知等差数列首项 2、公差 3，求第 5 项。"),
                    batch_id=batch_id)
        self.assertEqual(self._drain(), 2, "两次入池各挂一次，不多挂也不合并")
        self.assertEqual(list(self._cache_rows()), [batch_id], "该批次在缓存里只能占一条")
        state = self.dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["scanned"], self._pool_count(batch_id),
                         "scanned 必须等于第二次扫完后的池内行数")
        self.assertEqual(self._pool_count() - self._bank_count(), 4,
                         "池与主库行数差值 == 入池题数：初查一个字节都不写")
        self.assertEqual(self._bank_count(), before_bank, "初查不许往主库写一行")

    def test_07_group_counts_split_batch_and_bank(self) -> None:
        """补漏 7：_group_counts 按 reason 拆两栏；reason 缺失或其它值一律归主库栏。"""
        counts = self.dedupe._group_counts
        self.assertEqual(counts([{"reason": "batch", "drop": ["p_1", "p_2"]},
                                 {"reason": "bank", "drop": ["p_3"]}]), (2, 1))
        self.assertEqual(counts([{"drop": ["p_4"]}]), (0, 1), "缺 reason 只能当主库命中")
        self.assertEqual(counts([{"reason": "", "drop": ["p_4"]}]), (0, 1))
        self.assertEqual(counts([{"reason": "identical", "drop": ["p_5"]}]), (0, 1))
        self.assertEqual(counts([{"reason": "batch"}]), (0, 0), "只数 drop 不数保留者")
        self.assertEqual(counts([{"reason": "batch", "drop": None}]), (0, 0))
        self.assertEqual(counts([]), (0, 0))
        self.assertEqual(counts(None), (0, 0))

    def test_07b_real_engine_split_matches_two_columns(self) -> None:
        """补漏 7（引擎同源）：批内 3 条 + 主库命中 1 条 → 批内 2 / 主库 1 / 合并 3。"""
        self._seed_bank(_doc(STEM_A), _doc(STEM_B))
        saved = self._draft(_doc(STEM_A), _doc(STEM_A), _doc(STEM_A), _doc(STEM_B))
        batch_id = saved["batch_id"]
        self._drain()
        state = self.dedupe.scan_state(batch_id)
        plan = self.dedupe.batch_duplicate_groups(batch_id, PLUGIN_ID)
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["batch_redundant"], 2, "批内组两条 drop")
        self.assertEqual(state["bank_redundant"], 1, "主库组一条 drop")
        self.assertEqual(state["redundant"], 3)
        self.assertEqual(state["redundant"], plan["redundant"], "缓存与引擎同一把尺子")
        self.assertEqual(state["scanned"], plan["scanned"])
        self.assertEqual(state["main_scanned"], plan["main_scanned"])

    def test_12_g2_c1_pooled_is_reported_in_every_status(self) -> None:
        """军令 #32 · G2 · C1：``pooled`` 任何状态都给，口径＝``duplicate_pool`` 实时行数。

        旧写法只在 ``done`` 那一支给 ``pooled``，于是「还没扫／正在扫／扫失败」的卡片
        拿不到池内数，前端 ``gone = total - pending - pooled - stored`` 把已经抽进池里的题
        折进「已裁删」——老师的题在账上凭空变成被删掉的（判据 5.4）。
        本模块按 ``JZO_POOL_ADMIT_DISABLED`` 关掉自动抽走，池表恒空，所以这里钉的是
        「**每一拍都给得出这个键、且与池表数同源**」；非零那一款在
        ``tests/test_pending_pool.py`` 的 ``test_49`` 里抽完真题再钉。
        """
        def pool_table(batch_id: str) -> int:
            con = self.pending_db.connect()
            try:
                return int(con.execute("SELECT COUNT(*) FROM duplicate_pool WHERE batch_id = ?",
                                       (batch_id,)).fetchone()[0])
            finally:
                con.close()

        self._seed_bank(_doc(STEM_A))
        saved = self._draft(_doc(STEM_A))
        batch_id = saved["batch_id"]
        # ① 从没扫过：pending 也得带 pooled
        self.assertEqual(self.dedupe.scan_state("B-never"), {"status": "pending", "pooled": 0})
        self.assertEqual(self.dedupe.scan_state(batch_id), {"status": "pending", "pooled": 0})
        # ② 后台线程还压在闸上：这一拍仍旧是 pending + 给得出 pooled
        self.assertIn("pooled", self.dedupe.scan_state(batch_id))
        self._drain()
        # ③ done
        done = self.dedupe.scan_state(batch_id)
        self.assertEqual(done["status"], "done")
        self.assertEqual(done["pooled"], pool_table(batch_id))
        # ④ 扫失败：重扫这一代是 failed，pooled 照样在，redundant 照样不许假报
        self.dedupe.warm_batch_scan(batch_id, "org.jiuzhang.bank-missing")
        failed = self.dedupe.scan_state(batch_id)
        self.assertEqual(failed["status"], "failed", msg=str(failed))
        self.assertIn("pooled", failed, "C1 要钉的就是这一拍")
        self.assertEqual(failed["pooled"], pool_table(batch_id))
        self.assertNotIn("redundant", failed)
        # ⑤ 缓存清掉（＝底座重启）后回读库，同一个键同一个数
        self.dedupe._scan_cache.clear()
        self.assertEqual(self.dedupe.scan_state(batch_id)["pooled"], pool_table(batch_id))
        # ⑥ 批次卡片上的那份注解同源
        card = self._card_from_list(batch_id)
        self.assertEqual(card["dedupe"]["pooled"], pool_table(batch_id))

    def test_13_g2_c2_redundant_is_the_partition_sum_on_three_reads(self) -> None:
        """军令 #32 · G2 · C2：重复条数收敛成**一把尺子**＝``groups`` 两个 drop 分区之和。

        选的是「``_group_counts(groups)`` 那套」，不是「``len(recompute)`` 那套」：
        卡片要同时印「疑似重复 N（批内 X ／ 主库 Y）」，N 必须**恒等于** X＋Y，
        而 ``recompute`` 是「两组 drop 的并集」——它今天是同一个数，靠的是
        「一条 ``p_`` 只进一个组」这条不变量；一旦哪个分区允许重复计数，
        两套口径就分叉，而且是在**缓存／库／卡片**三处各说各话。
        ``recompute``／``drop_ids`` 仍当默认勾选集与重算集，只是不再充当「条数」。
        """
        self._seed_bank(_doc(STEM_A), _doc(STEM_B))
        saved = self._draft(_doc(STEM_A), _doc(STEM_A), _doc(STEM_A), _doc(STEM_B))
        batch_id = saved["batch_id"]
        self._drain()
        plan = self.dedupe.batch_duplicate_groups(batch_id, PLUGIN_ID)
        batch_count, bank_count = self.dedupe._group_counts(plan["groups"])
        self.assertEqual((batch_count, bank_count), (2, 1), "本用例的形状：批内 2／主库 1")
        for label, view in (("缓存", self.dedupe.scan_state(batch_id)),
                            ("库", self._load_scan_from_db(batch_id)),
                            ("卡片", self._card_from_list(batch_id)["dedupe"])):
            self.assertEqual(view["redundant"], batch_count + bank_count, label)
            self.assertEqual(view["redundant"], view["batch_redundant"] + view["bank_redundant"],
                             f"{label}：三数相加对不平就是两套口径并存")
            self.assertEqual(view["batch_redundant"], batch_count, label)
            self.assertEqual(view["bank_redundant"], bank_count, label)
        self.assertEqual(plan["redundant"], batch_count + bank_count,
                         "收敛后的尺子与剔除引擎的并集今天仍是同一个数（不是改出口径）")

    def test_14_g4_one_scan_reads_the_bank_once(self) -> None:
        """军令 #32 · G4：一次初查**只读一次主库**，``main_scanned`` 与候选同源。

        真机现象是「同一代结论自相矛盾」：``main_scanned=0 / redundant=0`` 与
        ``candidate_count=1`` 同时成立，那条候选的 ``existing_id`` 正是这条待审
        **刚 approve 变成的那个** ``q_``（certain／1.0／``signals=[]``），且随结论落盘、
        跨重启可读。根因是 ``_run_scan`` 与 ``batch_duplicate_groups`` 各读一把主库快照。
        这里不靠睡眠赌竞态：把 ``bank_rows_snapshot`` 换成**每调用一次回一份不同代**的
        计数替身，两代都与批内那条指纹全等、题号不同。旧实现读两把 ⇒ 候选报出代 2 的
        号而账目出自代 1；新实现只读一把 ⇒ 调用一次、候选恒指代 1 的号。
        """
        self._seed_bank(_doc(STEM_A))
        saved = self._draft(_doc(STEM_A))
        batch_id = saved["batch_id"]
        real = [{key: row[key] for key in row.keys()}
                for row in self.dedupe.bank_rows_snapshot(PLUGIN_ID)]
        first = [dict(row) for row in real]
        second = [{**row, "id": "q_g4_second_generation"} for row in real]
        generations = [first, second]
        calls: list[list] = []

        def fake_snapshot(provider_id: str) -> list:
            index = min(len(calls), len(generations) - 1)
            calls.append(generations[index])
            return calls[-1]

        with mock.patch.object(self.dedupe, "bank_rows_snapshot", side_effect=fake_snapshot):
            self.dedupe.warm_batch_scan(batch_id, PLUGIN_ID)
        state = self.dedupe.scan_state(batch_id)
        self.assertEqual(len(calls), 1, f"一次初查读了 {len(calls)} 把主库快照")
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["main_scanned"], len(first), "行数与候选必须出自同一把快照")
        candidates = state["candidates"]
        self.assertEqual([item["existing_id"] for item in candidates],
                         [row["id"] for row in first], "候选指向的主库行出自第二代快照")
        self.assertEqual(state["bank_redundant"], 1)
        self.assertNotIn("q_g4_second_generation",
                         {str(item["existing_id"]) for item in candidates},
                         "自匹配的来源：代 2 才有的行被当成「主库已有」")
        # 只进不出：主库快照不许跟着结论一起进缓存／落库（G4 硬约束②）
        self.assertNotIn("main_rows", state)
        con = self.pending_db.connect()
        try:
            columns = {row[1] for row in con.execute("PRAGMA table_info(dedupe_scans)")}
            self.assertNotIn("main_rows", columns)
            self.assertEqual(columns, {"batch_id", "provider_id", "status", "scanned",
                                       "redundant", "batch_redundant", "bank_redundant",
                                       "main_scanned", "tier", "truncated", "code",
                                       "retryable", "message", "finished_at", "generation"})
        finally:
            con.close()

    def test_11_scan_state_returns_a_copy(self) -> None:
        """补漏 11：改返回值不污染进程内缓存（防共享可变状态）。"""
        saved = self._draft(_doc(STEM_A))
        batch_id = saved["batch_id"]
        self._drain()
        first = self.dedupe.scan_state(batch_id)
        self.assertIsNot(first, self.dedupe.scan_state(batch_id))
        first["status"] = "hacked"
        first["injected"] = True
        self.assertEqual(self.dedupe.scan_state(batch_id)["status"], "done")
        self.assertNotIn("injected", self.dedupe.scan_state(batch_id))
        pending = self.dedupe.scan_state("B-999")
        pending["status"] = "hacked"
        self.assertEqual(self.dedupe.scan_state("B-999"), {"status": "pending", "pooled": 0})


class DegradedTest(DedupeScanCase):
    def test_04_bank_unavailable_fails_but_never_blocks_import(self) -> None:
        """判据 4：主库读不通 → failed + code + retryable，save_draft 照常成功。"""
        self._seed_bank(_doc(STEM_A))
        with mock.patch.object(self.dedupe, "bank_rows_snapshot",
                               side_effect=self.bank.BankError("模拟主库读不通")):
            saved = self._draft(_doc(STEM_A))
            batch_id = saved["batch_id"]
            self.assertTrue(saved["saved_ids"], "入池本身必须已经提交成功")
            with self.assertLogs("uvicorn.error", level="WARNING") as captured:
                self.assertEqual(self._drain(), 1)
            self.assertTrue(any("初查失败" in line for line in captured.output),
                            captured.output)
            state = self.dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["code"], FAIL_CODE)
        self.assertIs(state["retryable"], True)
        self.assertNotIn("redundant", state, "读不通时不许假报任何重复数")
        self.assertEqual(self._pool_count(batch_id), 1, "初查失败不回滚暂存")
        self.assertEqual(self._card_from_list(batch_id)["dedupe"]["status"], "failed")

    def test_05_provider_resolve_failure_degrades_to_failed(self) -> None:
        """补漏 8：bank_provider.resolve() 抛异常只落 failed，绝不冒出线程。"""
        saved = self._draft(_doc(STEM_A))
        batch_id = saved["batch_id"]
        with mock.patch("app.core.bank_provider.resolve",
                        side_effect=RuntimeError("模拟 provider 解析炸了")):
            self.assertEqual(self._drain(), 1, "线程内异常必须被就地接住")
            state = self.dedupe.scan_state(batch_id)
            self.assertEqual(state["status"], "failed", "取不到题库要落进 failed 分支")
            self.assertEqual(state["code"], FAIL_CODE)
            self.dedupe._scan_cache.clear()
            self.dedupe.warm_dedupe_scan(batch_id)  # 直调同样不许抛（线程体已外迁到 pending_dedupe）
            self.assertEqual(self.dedupe.scan_state(batch_id)["status"], "failed")
        self.assertEqual(self._pool_count(batch_id), 1, "暂存不受初查牵连")

    def test_10_empty_batch_id_is_a_no_op(self) -> None:
        """补漏 10：空 batch_id 直接 return——不调引擎、不写缓存。"""
        with mock.patch.object(
                self.dedupe, "batch_duplicate_groups",
                return_value={"scanned": 0, "redundant": 0, "groups": [],
                              "main_scanned": 0}) as engine:
            self.dedupe.warm_batch_scan("", PLUGIN_ID)
            self.dedupe.warm_batch_scan(None, PLUGIN_ID)
            self.assertEqual(engine.call_count, 0, "空批次号一个引擎调用都不许发")
            self.assertEqual(self._cache_rows(), {})
            self.assertEqual(self.dedupe.scan_state(""), {"status": "pending", "pooled": 0})
            # 实测口径：实现只挡空串、不做 strip，纯空白批次号仍会打到引擎并落一条缓存
            # （无真实调用方能造出这种 id：save_draft 的 target_batch 恒为 B-xxx；
            # 作为实现事实钉在这里，同时记入结论「疑似缺陷」清单）
            self.dedupe.warm_batch_scan("   ", PLUGIN_ID)
            self.assertEqual(engine.call_count, 1)
            self.assertEqual(list(self._cache_rows()), ["   "])
            self.dedupe._scan_cache.clear()


class CardCompatTest(DedupeScanCase):
    def test_05_batch_card_keeps_eleven_keys_and_adds_dedupe(self) -> None:
        """判据 5 + ⑤ 重写版：两处卡片（列表与 save_draft 回执）14 键零缺失 + dedupe/route 是 dict。"""
        saved = self._draft(_doc(STEM_A), source_name="初查模拟.pdf")
        batch_id = saved["batch_id"]
        receipt = saved["batch"]
        listed = self._card_from_list(batch_id)
        self.assertEqual(set(receipt), set(listed), "两处卡片同出 batch_card，键不许分叉")
        for card in (receipt, listed):
            self.assertTrue(CARD_KEYS <= set(card),
                            f"既有键缺失：{sorted(CARD_KEYS - set(card))}")
            self.assertEqual(set(card) - CARD_KEYS, {"dedupe", "route"}, "不许再偷偷加键")
            for key, expected in CARD_TYPES.items():
                self.assertIsInstance(card[key], expected, f"{key} 换型了")
                if expected is int:
                    self.assertNotIsInstance(card[key], bool, f"{key} 不许被 bool 顶替")
            self.assertIsInstance(card["dedupe"], dict)
            self.assertIsInstance(card["route"], dict, "解析路由标记随卡片一起回")
        self.assertEqual(receipt["source_name"], "初查模拟.pdf")
        self.assertEqual(receipt["total"], 1)
        self.assertEqual(receipt["pending_count"], 1)
        self.assertIs(receipt["done"], False)
        self.assertIn(listed["dedupe"].get("status"), ("pending", "done", "failed"))

    def test_05b_no_cache_means_pending_on_both_cards(self) -> None:
        """判据 5（无缓存侧）：还没扫就是 pending，不等于「没有重复」。"""
        saved = self._draft(_doc(STEM_A))
        batch_id = saved["batch_id"]
        self.dedupe._scan_cache.clear()
        self.assertEqual(saved["batch"]["dedupe"], {"status": "pending", "pooled": 0})
        self.assertEqual(self._card_from_list(batch_id)["dedupe"], {"status": "pending", "pooled": 0})
        self._drain()
        self.assertEqual(self._card_from_list(batch_id)["dedupe"]["status"], "done")

    def test_05c_routes_are_wired_to_those_two_cards(self) -> None:
        """判据 5 的接线守卫：本模块不起 uvicorn，用源码锚点说明两处入口即上面两处。"""
        api = (ROOT / "app" / "api" / "pending.py").read_text(encoding="utf-8")
        self.assertIn("return pending_bank.batch_list()", api)
        self.assertIn("return pending_bank.save_draft(", api)
        self.assertIn('origin=str(payload.get("origin") or "")', api)


class QueuePlacementTest(DedupeScanCase):
    def test_09_placeholder_round_queues_nothing(self) -> None:
        """补漏 9 / ⑤ 3b 底座侧：ingest 占位轮 dedupe_queued is False 且零线程。"""
        placeholder = self._draft(_doc("（待识别：拖拽占位题）"), origin="ingest")
        self.assertIs(placeholder["dedupe_queued"], False)
        self.assertEqual(self.threads, [], "占位轮一个线程都不许起")
        self.assertEqual(self._cache_rows(), {})
        self._seed_bank(_doc(STEM_A))
        real = self._draft(_doc(STEM_A), origin="ingest", batch_id=placeholder["batch_id"])
        self.assertIs(real["dedupe_queued"], True)
        self.assertEqual(self._drain(), 1)
        state = self.dedupe.scan_state(placeholder["batch_id"])
        self.assertEqual(state["status"], "done", "识别轮挂载后必须补上这一次初查")
        self.assertGreaterEqual(state["redundant"], 1)

    def test_09b_other_origins_always_queue(self) -> None:
        """补漏 9（对照）：editor 侧 payload 不带 origin，以及别的 origin，都要挂任务。"""
        editor_round = self._draft(_doc(STEM_A))
        self.assertIs(editor_round["dedupe_queued"], True)
        manual = self._draft(_doc(STEM_B), origin="manual")
        self.assertIs(manual["dedupe_queued"], True)
        named = self._draft(_doc("初查口径题戊：求 $2+2$。"), origin="ingest",
                            batch_id=editor_round["batch_id"])
        self.assertIs(named["dedupe_queued"], True)
        self.assertEqual(self._drain(), 3)


class PerfTest(DedupeScanCase):
    def test_10b_queued_import_adds_no_synchronous_scan_work(self) -> None:
        """判据 10 的单测侧（只用相对差值，禁绝对秒数）。

        基线取「同样 50 题入池但不挂线程」的 ingest 占位轮，与「挂线程」那次的同步
        耗时做差值断言：线程只 ``start`` 不 ``join``，初查开销不该进导入的 HTTP 时长。
        真机侧的 50 题往返差值归 ``tools/editor_probe.py`` 的 3.1a 场景。
        """
        limit = getattr(self.pending_bank, "MAX_BATCH_QUESTIONS", 0)
        if limit < 50:
            self.skipTest(f"MAX_BATCH_QUESTIONS={limit} 不足以造 50 题一批")
        docs = [_doc(f"性能口径题 {i}：已知 $x^2+{i}=0$，求 $x$。") for i in range(50)]

        def _timed(**kwargs) -> tuple:
            started = time.perf_counter()
            saved = self._draft(*docs, **kwargs)
            elapsed = time.perf_counter() - started
            self.assertEqual(len(saved["saved_ids"]), 50)
            return elapsed, saved["batch_id"]

        baseline, _ = _timed(origin="ingest")          # 占位轮：不挂线程
        queued, saved_batch = _timed(source_name="perf.pdf")  # 正常轮：挂一个后台线程
        self.assertEqual(len(self.threads), 1)
        self.assertLess(queued - baseline, baseline,
                        "挂初查带来的同步增量必须小于导入自身耗时（同步路径上不该有判重）")
        self.assertEqual(self.dedupe.scan_state(saved_batch)["status"], "pending",
                         "线程还卡在闸上时同步侧必须仍是 pending")
        self._drain()
        state = self.dedupe.scan_state(saved_batch)
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["scanned"], 50)
        self.assertEqual(self._pool_count(), 100, "两轮各 50 题，初查不增删池内一行")


if __name__ == "__main__":
    unittest.main()
