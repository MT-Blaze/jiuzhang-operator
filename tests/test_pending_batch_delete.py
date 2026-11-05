"""批次生命周期：扫描版只立空批、页图挂靠、整批彻底删除、画框新题置顶。

这一层判的是「老师的一批原卷怎么生、怎么死」：

- 纯图片 PDF 先立批次，**一道占位题都没有**；页图渲染完再挂到批次上，
  卡片据此变成 ``page_only``（还能点进去框选），``scan_batch`` 永久为真；
- 【框选切题】松手即落一条新题，``position="top"`` 让它排在右侧三栏最上面；
- 删除最后一道切出来的题，原卷页图**跟着留下**——老师还得接着切；
- 【删除批次】把待审题、初查账、原卷页图、题目配图与只读副本一次清干净，
  主库一个字节都不碰。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pending_batch_delete``
"""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PLUGIN_ID = "org.jiuzhang.bank-engine"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _doc(stem: str = "框选切题口径题：已知 $f(x)=x^2-5x+6$，求零点个数（　　）。",
         *, images: list | None = None) -> dict:
    document = {
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
    if images:
        document["images"] = images
    return document


class BatchLifecycleCase(unittest.TestCase):
    """隔离临时工作区；后台初查线程按名 join，Windows 上不抢 SQLite 句柄。"""

    def setUp(self) -> None:
        from app.core import (bank, pending_assets, pending_bank,
                              pending_bank_batches, pending_batches, pending_db,
                              pending_dedupe)

        self.bank = bank
        self.pending_assets = pending_assets
        self.pending_bank = pending_bank
        self.pending_bank_batches = pending_bank_batches
        self.pending_batches = pending_batches
        self.pending_db = pending_db
        self.pending_dedupe = pending_dedupe
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        from app.core.config import settings

        self.settings = settings
        self._saved = (os.environ.get("JZO_DATA_DIR"), os.environ.get("JZO_PLUGINS_DIR"),
                       os.environ.get("JZO_POOL_ADMIT_DISABLED"), settings.workspace_id)
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        # 本模块只判批次生死，不判「扫完自动抽走」；抽走会把刚落的题搬出池子。
        os.environ["JZO_POOL_ADMIT_DISABLED"] = "1"
        settings.workspace_id = None
        self.addCleanup(self._restore_env)
        self.addCleanup(self._settle_dedupe_threads)
        bank.init_bank(PLUGIN_ID, db_path=Path(self.tmp.name) / "banks" / f"{PLUGIN_ID}.db")

    def _settle_dedupe_threads(self, timeout: float = 20.0) -> None:
        stragglers = [t for t in threading.enumerate()
                      if getattr(t, "name", "") == "jzo-dedupe-warm"]
        deadline = time.monotonic() + timeout
        for thread in stragglers:
            thread.join(max(0.1, deadline - time.monotonic()))
        alive = [thread.name for thread in stragglers if thread.is_alive()]
        if alive:
            self.fail(f"后台初查线程未收口，SQLite 句柄还开着：{alive}")

    def _restore_env(self) -> None:
        for key, value in zip(("JZO_DATA_DIR", "JZO_PLUGINS_DIR",
                               "JZO_POOL_ADMIT_DISABLED"), self._saved[:3]):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.settings.workspace_id = self._saved[3]

    # ---------- 夹具 ----------

    def _card(self, batch_id: str) -> dict:
        for card in self.pending_batches.batch_list()["batches"]:
            if card["batch_id"] == batch_id:
                return card
        raise AssertionError(f"批次列表里没有 {batch_id}")

    def _count(self, table: str, batch_id: str) -> int:
        con = self.pending_db.connect()
        try:
            return int(con.execute(
                f"SELECT COUNT(*) FROM {table} WHERE batch_id = ?", (batch_id,)
            ).fetchone()[0])
        finally:
            con.close()

    def _scan_batch(self, **kwargs) -> str:
        return self.pending_bank.create_batch(
            source_name="模拟1.pdf", scan=True, **kwargs)["batch_id"]

    def _attach_page(self, batch_id: str) -> str:
        name = self.pending_assets.write_pending_asset(PNG, "image/png")
        self.pending_bank.set_batch_pages(batch_id, [{"name": name, "page": 1}])
        return name

    # ---------- 立批与页图 ----------

    def test_01_scan_batch_starts_with_zero_questions(self) -> None:
        """纯图片 PDF 只立批次：没有占位题，卡片也不谎报「原卷页」。"""
        batch_id = self._scan_batch()
        data = self.pending_batches.list_batch_questions(batch_id)
        self.assertEqual(data["items"], [])
        self.assertTrue(data["scan_batch"])
        self.assertEqual(data["page_images"], [])

        card = self._card(batch_id)
        self.assertTrue(card["scan_batch"])
        self.assertFalse(card["page_only"], "页图还没挂上，先别当成纯原卷批次")
        self.assertEqual(card["page_count"], 0)
        self.assertEqual(card["pending_count"], 0)

    def test_02_attach_pages_turns_card_into_page_only(self) -> None:
        """页图挂上后卡片可点开继续框选，读列表也带 scan_batch。"""
        from app.core.pending_db import PENDING_ASSET_URI_PREFIX

        batch_id = self._scan_batch()
        name = self._attach_page(batch_id)
        card = self._card(batch_id)
        self.assertTrue(card["page_only"])
        self.assertTrue(card["scan_batch"])
        self.assertEqual(card["page_count"], 1)

        data = self.pending_batches.list_batch_questions(batch_id)
        self.assertEqual(data["page_images"], [
            {"name": name, "uri": PENDING_ASSET_URI_PREFIX + name, "page": 1},
        ])
        self.assertTrue(data["scan_batch"])

    def test_03_deleting_last_cropped_question_keeps_page_images(self) -> None:
        """删掉最后一道切出来的题，原卷页图不能被「批次收口」一并清掉。"""
        batch_id = self._scan_batch()
        page_name = self._attach_page(batch_id)
        saved = self.pending_bank.save_draft([{"question": _doc()}], batch_id=batch_id)
        self.assertEqual(len(saved["saved_ids"]), 1)

        self.pending_bank.delete_pending(saved["saved_ids"][0])
        self.assertEqual(self._count("pending_questions", batch_id), 0)
        page_path = self.pending_assets.asset_path(page_name)
        self.assertTrue(page_path.is_file(), "纯原卷批次还要留着页图让老师继续框选")
        self.assertTrue(self._card(batch_id)["page_only"])

    # ---------- 画框新题置顶 ----------

    def test_04_cropped_question_goes_to_top(self) -> None:
        """框选切出来的新题排在右侧三栏最上面，后切的仍压在最前。"""
        batch_id, first_ids = (
            lambda saved: (saved["batch_id"], saved["saved_ids"])
        )(self.pending_bank.save_draft(
            [{"question": _doc(f"已有题 {n}：$x^2={n}$ 的解。（　　）。")} for n in (1, 2, 3)]))
        self.assertEqual(len(first_ids), 3)

        top_one = self.pending_bank.save_draft(
            [{"question": _doc("先框出来的一题：$x+1=2$。（　　）。")}],
            batch_id=batch_id, position="top")["saved_ids"][0]
        top_two = self.pending_bank.save_draft(
            [{"question": _doc("后框出来的一题：$x+2=3$。（　　）。")}],
            batch_id=batch_id, position="top")["saved_ids"][0]

        items = self.pending_batches.list_batch_questions(batch_id)["items"]
        self.assertEqual([str(item["id"]) for item in items[:2]], [top_two, top_one])
        self.assertEqual([str(item["id"]) for item in items[2:]], first_ids)

    # ---------- 整批删除 ----------

    def test_05_delete_batch_clears_rows_files_and_backup(self) -> None:
        """整批删除：待审题、初查账、页图、配图与只读副本一起清，主库不动。"""
        backup = self.pending_assets.store_source_backup("模拟1.pdf", b"%PDF-1.4 fake")
        batch_id = self._scan_batch(source_backup=backup)
        page_name = self._attach_page(batch_id)
        saved = self.pending_bank.save_draft(
            [{"question": _doc(images=[{"id": "img_a", "role": "stem",
                                        "uri": "/static/uploads/img_a.png", "alt": "题图"}]),
              "assets": [{"id": "img_a",
                          "data_url": "data:image/png;base64," + base64.b64encode(PNG).decode()}]}],
            batch_id=batch_id)
        item_id = saved["saved_ids"][0]
        # 先等这一批的后台初查收口：它和「删除批次」同时跑会在删完之后补写结论行，
        # 那时再断言「初查账清空」就变成跟线程赛跑，测的也不是删除本身了。
        self._settle_dedupe_threads()
        con = self.pending_db.connect()
        try:
            item_asset = json.loads(con.execute(
                "SELECT assets_json FROM pending_questions WHERE id = ?", (item_id,)
            ).fetchone()["assets_json"])
            con.execute("INSERT OR REPLACE INTO dedupe_scans"
                        " (batch_id, status, finished_at)"
                        " VALUES (?, 'done', '2026-11-05T10:00:00+08:00')", (batch_id,))
            con.execute(
                "INSERT OR REPLACE INTO dedupe_findings"
                " (batch_id, item_id, reason, level, created_at)"
                " VALUES (?, ?, 'batch', 'certain', '2026-11-05T10:00:00+08:00')",
                (batch_id, item_id))
            con.commit()
        finally:
            con.close()
        item_asset_name = str(item_asset[0]["name"])
        item_path = self.pending_assets.asset_path(item_asset_name)
        self.assertTrue(item_path.is_file())
        backup_file = self.pending_assets.backup_path(backup)
        self.assertTrue(backup_file.is_file())

        result = self.pending_bank.delete_batch(batch_id)
        self.assertEqual(result["batch_id"], batch_id)
        self.assertEqual(result["deleted_questions"], 1)
        self.assertEqual(result["deleted_pages"], 1)

        batch_ids = {card["batch_id"]
                     for card in self.pending_batches.batch_list()["batches"]}
        self.assertNotIn(batch_id, batch_ids)
        for table in ("pending_questions", "dedupe_scans", "dedupe_findings"):
            self.assertEqual(self._count(table, batch_id), 0, table)
        self.assertFalse(self.pending_assets.asset_path(page_name).exists())
        self.assertFalse(item_path.exists())
        self.assertFalse(backup_file.exists())

    def test_06_delete_unknown_or_invalid_batch_is_not_found(self) -> None:
        with self.assertRaises(self.pending_bank.PendingNotFound):
            self.pending_bank.delete_batch("B-999")
        with self.assertRaises(self.pending_bank.PendingNotFound):
            self.pending_bank.delete_batch("not-a-batch")

    def test_07_delete_route_is_a_write(self) -> None:
        """删除批次挂 DELETE，且必须过写令牌——删的是老师整批原卷。"""
        from app.api import pending as pending_api
        from app.core.security import require_write_token

        route = None
        for item in pending_api.router.routes:
            if (item.path == "/api/pending/batches/{batch_id}"
                    and "DELETE" in (item.methods or set())):
                route = item
                break
        self.assertIsNotNone(route)
        calls = [dep.call for dep in route.dependant.dependencies
                 if getattr(dep, "call", None) is not None]
        self.assertIn(require_write_token, calls)


if __name__ == "__main__":
    unittest.main()
