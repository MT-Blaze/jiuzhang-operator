"""重题池数据层（军令 #32 · 第四步）：``app/core/pending_pool.py`` 的判据回归。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pending_pool``

全程落在隔离临时工作区（``JZO_DATA_DIR`` / ``JZO_PLUGINS_DIR`` 指到 tmp），
**绝不读写真实的 ``data/pending.db``**。钉住判据 4.1–4.9 与 5.5 的数据层这一半：

- 4.1 一条一题：``item_id`` 唯一，重复进池不多占一条，不分组不折叠；
- 4.2 跨批次：``batches`` 行删掉（模拟批次消失）后池内条目与成品图仍可读；
- 4.3 底图：池内只记题自己的成品图，没有任何整页底图的位置；
- 4.4 合并元数据：只并来源/标签/考向（主考向仍是主库那道题的）、难度仅补缺，
  题干/选项/答案/解析/配图逐字不变，冲突只列清单不覆盖；
- 4.5 新增解析：并成下一个解法并追加来源；没有解析就拒绝；
- 4.6 不重复：写进主库一道新题、原题不动；缺答案/考向时不写库、留在池里并报缺项；
- 4.7 删除：只删池内这条，主库题与批次不受影响；图只在没人引用时才删；
- 4.8 答案闸门：答案明确不同时前两项锁死，后两项照走；
- 4.9 重启可读：条目与已裁决状态都在库里，重开连接照读，拖档重扫不复活；
- 5.5 终局闸门：绕过前端直接 ``pending.approve``，精确同题仍然拦。
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
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PLUGIN_ID = "org.jiuzhang.bank-engine"
STAMP = "2026-01-15T09:00:00+08:00"
STEM = "重题池口径题：已知 $x^2-5x+6=0$，求它的两个根之和（　　）。"
PNG_BASE64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
              "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
# 配图口径与暂存契约一致：题面挂 images（带 uri），字节走信封里的 assets
_IMAGE = {"id": "img_pool", "role": "stem",
          "uri": "/static/uploads/img_pool.png", "alt": "题图"}
_ASSET = [{"id": "img_pool", "data_url": f"data:image/png;base64,{PNG_BASE64}"}]


def _doc(stem: str = STEM, *, answer: str = "A", solution: str | None = None,
         taxonomy: dict | None = None, tags: list | None = None,
         difficulty: str = "L2", source: dict | None = None,
         images: list | None = None) -> dict[str, Any]:
    document: dict[str, Any] = {
        "type": "single_choice",
        "stem": stem,
        "difficulty": difficulty,
        "options": [
            {"key": "A", "content": "$2$"},
            {"key": "B", "content": "$3$"},
            {"key": "C", "content": "$5$"},
            {"key": "D", "content": "$6$"},
        ],
        "answer": {"kind": "choice", "choice_keys": [answer], "final": answer},
        "solution": solution if solution is not None else "由韦达定理，两根之和为 $5$。",
    }
    if taxonomy:
        document["taxonomy"] = taxonomy
    if tags:
        document["tags"] = tags
    if source:
        document["source"] = source
    if images:
        document["images"] = images
    return document


def _other_doc(*, taxonomy: dict | None = None, tags: list | None = None) -> dict[str, Any]:
    """一道跟口径题明显不同的选择题：实测落在档位门槛以下，不会被抽进池子。

    「整批入库」那几条用例要有真留在待审池里的题当对照，靠它。
    """
    document: dict[str, Any] = {
        "type": "single_choice",
        "stem": ("重题池口径题：一个袋里有 3 个红球 2 个白球，任取一球是红球的概率（　　）。"),
        "difficulty": "L2",
        "options": [
            {"key": "A", "content": "$\\frac{2}{5}$"},
            {"key": "B", "content": "$\\frac{3}{5}$"},
            {"key": "C", "content": "$\\frac{1}{2}$"},
            {"key": "D", "content": "$\\frac{3}{2}$"},
        ],
        "answer": {"kind": "choice", "choice_keys": ["B"], "final": "B"},
        "solution": "红球 3 个除以总数 5 个。",
    }
    if taxonomy:
        document["taxonomy"] = taxonomy
    if tags:
        document["tags"] = tags
    return document


class PoolCase(unittest.TestCase):
    """隔离工作区 + 一座真主库 + 一条已扫过的批次。"""

    def setUp(self) -> None:
        from app.core.config import settings
        from app.core import (bank, pending_assets, pending_bank, pending_batches,
                              pending_db, pending_dedupe, pending_pool)

        self.settings = settings
        self.bank = bank
        self.pending_bank = pending_bank
        self.pending_batches = pending_batches
        self.pending_db = pending_db
        self.pending_dedupe = pending_dedupe
        self.pending_pool = pending_pool
        self.pending_assets = pending_assets
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (os.environ.get("JZO_DATA_DIR"), os.environ.get("JZO_PLUGINS_DIR"),
                       settings.workspace_id)
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        settings.workspace_id = None
        self.addCleanup(self._restore_env)
        # save_draft 会甩出 jzo-dedupe-warm 线程，它持着 tmp 里两座库的 SQLite 句柄：
        # 不收口就 cleanup 必撞 PermissionError（addCleanup 后进先出，这条先跑）。
        self.addCleanup(self._settle_dedupe_threads)
        self.db_path = Path(self.tmp.name) / "banks" / f"{PLUGIN_ID}.db"
        bank.init_bank(PLUGIN_ID, db_path=self.db_path)
        # ``_scan_cache`` 是进程内的，键只有批次号：每个用例从空缓存起步，否则上一条
        # 用例记在内存里的「B-001 已扫完」会被这一条读到（本模块所有用例的批次号都是
        # B-001）。真机换工作区必然重启进程，读不到别人的缓存，所以只在用例侧收口。
        pending_dedupe._scan_cache.clear()
        self.addCleanup(pending_dedupe._scan_cache.clear)

    def tearDown(self) -> None:
        self._settle_dedupe_threads()

    def _settle_dedupe_threads(self, timeout: float = 20.0) -> None:
        stragglers = [t for t in threading.enumerate()
                      if getattr(t, "name", "") == "jzo-dedupe-warm"]
        deadline = time.monotonic() + timeout
        for thread in stragglers:
            thread.join(max(0.1, deadline - time.monotonic()))
        alive = [thread.name for thread in stragglers if thread.is_alive()]
        if alive:
            self.fail(f"后台初查线程未在 {timeout} 秒内收口，句柄还开着：{alive}")

    def _restore_env(self) -> None:
        for key, value in zip(("JZO_DATA_DIR", "JZO_PLUGINS_DIR"), self._saved[:2]):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.settings.workspace_id = self._saved[2]

    # ---------- 夹具 ----------

    def _con(self) -> sqlite3.Connection:
        con = self.pending_db.connect()
        self.addCleanup(con.close)
        return con

    def _seed_bank(self, *documents: dict) -> list[str]:
        ids: list[str] = []
        con = sqlite3.connect(self.db_path)
        try:
            for index, document in enumerate(documents, start=1):
                question_id = f"q_pool{index:04d}"
                ids.append(question_id)
                con.execute(
                    "INSERT INTO questions (id, type, stem, options, answer, solution,"
                    " extensions, difficulty, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        question_id, document["type"], document["stem"],
                        json.dumps(document["options"], ensure_ascii=False,
                                   separators=(",", ":")),
                        str((document.get("answer") or {}).get("final") or "A"),
                        document.get("solution"), "[]",
                        document.get("difficulty", "L2"), STAMP, STAMP,
                    ),
                )
            con.commit()
        finally:
            con.close()
        return ids

    def _seed_topic(self, letter: str) -> dict[str, str]:
        """造一个真实考向叶子：``taxonomy.topic_ids`` 里的号必须在 topics 表里。"""
        topic_id = f"tp_kx{int(letter, 16):08x}"
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                "INSERT INTO topics (id, parent_id, textbook_id, name, path,"
                " sort_order, status, created_at, updated_at)"
                " VALUES (?, NULL, NULL, ?, ?, 0, 'active', ?, ?)",
                (topic_id, f"考向{letter}", topic_id, STAMP, STAMP),
            )
            con.commit()
        finally:
            con.close()
        return {"topic_ids": [topic_id]}

    def _draft(self, *documents: dict, source_name: str = "期末模拟卷.docx",
               assets: list | None = None, hold_admit: bool = False) -> tuple[str, list[str]]:
        """存一批进待审池；后台链跑完就**自己扫完并自己抽走**（判据 3.5）。

        ``hold_admit=True`` 把自动抽走按住，只留自动初查——失败注入那两条要用
        「扫完了但还没抽」这个中间态，才有地方塞损坏。
        """
        original = self.pending_dedupe.admit_into_pool
        if hold_admit:
            self.pending_dedupe.admit_into_pool = lambda *_a, **_k: None
        try:
            payload = [{"question": document, "assets": assets or []}
                       for document in documents]
            saved = self.pending_bank.save_draft(payload, source_name=source_name)
            self._settle_dedupe_threads()
        finally:
            self.pending_dedupe.admit_into_pool = original
        return saved["batch_id"], saved["saved_ids"]

    def _scan(self, batch_id: str) -> dict[str, Any]:
        """同步跑一次整批初查：省掉 daemon 线程，结论照样落 ``dedupe_findings``。"""
        self.pending_dedupe.warm_batch_scan(batch_id, PLUGIN_ID)
        return self.pending_dedupe.scan_state(batch_id)

    def _admit(self, batch_id: str, **kwargs) -> dict[str, Any]:
        return self.pending_pool.admit_from_scan(batch_id, provider_id=PLUGIN_ID, **kwargs)

    def _prepare_pool(self, incoming: dict, *, assets: list | None = None,
                      seed: bool = True) -> tuple[str, str]:
        """主库铺一道原题、批次里存一条同题，后台链扫完即抽走；回 ``(batch_id, pool_id)``。

        ``seed=False`` 给那些自己先往主库摆过题、还想改过那道题元数据用例用。
        """
        main_ids = self._seed_bank(_doc()) if seed else ["q_pool0001"]
        batch_id, item_ids = self._draft(incoming, assets=assets)
        entries = self.pending_pool.list_pool()["items"]
        self.assertEqual(len(entries), 1, f"后台链没把这条抽进池子：{entries}")
        self.assertEqual(entries[0]["main_id"], main_ids[0])
        self.assertEqual(self._live_count(batch_id), 0,
                         "抽走＝进池与删待审同时成立，待审池里不该再留这一条")
        return batch_id, entries[0]["pool_id"]

    def _live_count(self, batch_id: str) -> int:
        return int(self._con().execute(
            "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?",
            (batch_id,)).fetchone()[0])

    def _pool_raw(self, pool_id: str) -> sqlite3.Row:
        return self._con().execute("SELECT * FROM duplicate_pool WHERE pool_id = ?",
                                   (pool_id,)).fetchone()

    def _bank_row(self, question_id: str) -> dict[str, Any]:
        return self.bank.get_question(PLUGIN_ID, question_id)

    def _insert_row(self, pool_id: str, item_id: str, level: str, percent: int) -> None:
        """直接摆一条池内记录：只用于「读侧按档位过滤」，不经过判重。"""
        con = self._con()
        con.execute(
            "INSERT INTO duplicate_pool (pool_id, item_id, batch_id, source_name,"
            " provider_id, main_id, level, percent, similarity, signals_json, doc_json,"
            " assets_json, created_at, updated_at)"
            " VALUES (?, ?, 'B-001', '卷.docx', ?, 'q_pool0001', ?, ?, 0, '[]', '{}',"
            " '[]', ?, ?)",
            (pool_id, item_id, PLUGIN_ID, level, percent, STAMP, STAMP),
        )
        con.commit()

    def _set_doc(self, pool_id: str, document: dict) -> None:
        """改写池内条目自带的文档：造「缺答案 / 占位符未清」这类料。"""
        con = self._con()
        con.execute("UPDATE duplicate_pool SET doc_json = ? WHERE pool_id = ?",
                    (json.dumps(document, ensure_ascii=False), pool_id))
        con.commit()

    def _pool_asset_names(self, pool_id: str) -> list[str]:
        """池内这条自己那份成品图的文件名（``pool_assets/cimg_…``，与待审池不同目录）。"""
        row = self._pool_raw(pool_id)
        return [str(item["name"]) for item in json.loads(row["assets_json"] or "[]")]


class PoolAdmissionTest(PoolCase):
    """判据 4.1 / 4.2 / 4.3 与读接口。"""

    def test_01_one_row_per_incoming_question(self) -> None:
        """4.1 一条一题：同一条进来题重复进池只占一条，配一条最像的主库原题。"""
        self._prepare_pool(_doc())
        batch_id = "B-001"
        again = self._admit(batch_id)
        self.assertEqual(again["admitted"], 0)
        rows = self._con().execute("SELECT COUNT(*) FROM duplicate_pool").fetchone()[0]
        self.assertEqual(int(rows), 1)
        entry = self.pending_pool.list_pool()["items"][0]
        self.assertEqual(entry["level"], "certain")
        self.assertTrue(entry["label"])
        self.assertEqual(entry["item_id"], self._con().execute(
            "SELECT item_id FROM duplicate_pool").fetchone()[0])

    def test_02_two_items_are_two_rows_not_one_group(self) -> None:
        """4.1 不分组、不折叠：两条进来题就是两条独立条目（后台链自己抽，抽完就两条）。"""
        self._seed_bank(_doc(), _doc(stem="重题池口径题：已知 $x^2-7x+12=0$，求根之和（　　）。"))
        batch_id, item_ids = self._draft(
            _doc(), _doc(stem="重题池口径题：已知 $x^2-7x+12=0$，求根之和（　　）。"))
        items = self.pending_pool.list_pool()["items"]
        self.assertEqual(len(items), 2, items)
        self.assertEqual({item["item_id"] for item in items}, set(item_ids))
        self.assertEqual({item["main_id"] for item in items},
                         {"q_pool0001", "q_pool0002"})
        self.assertEqual(self._live_count(batch_id), 0, "两条都抽走了，一条不折叠")

    def test_03_entry_survives_batch_disappearance(self) -> None:
        """4.2 跨批次：测试里直接删 ``batches`` 行模拟批次消失（现网没有删批次入口）。

        池内条目、左右两侧渲染文档、成品图文件都必须照读——来源批次号只是溯源字段。
        抽走之后图跟着题走：那张 ``cimg_`` 是这条自己的，跟批次残留切图同删同留都不相干。
        """
        batch_id, pool_id = self._prepare_pool(_doc(images=[_IMAGE]), assets=_ASSET)
        con = self._con()
        con.execute("DELETE FROM batches WHERE batch_id = ?", (batch_id,))
        con.commit()
        entry = self.pending_pool.get_entry(pool_id)
        self.assertEqual(entry["batch_id"], batch_id)
        self.assertEqual(entry["incoming"]["stem"], STEM)
        self.assertEqual(entry["existing"]["id"], "q_pool0001")
        self.assertTrue(entry["existing"]["stem"])
        name = self._pool_asset_names(pool_id)[0]
        path = self.pending_assets.pool_asset_path(name)
        self.assertEqual(path.name, name)
        self.assertTrue(path.is_file(), "批次都没了，池里这条的成品图照样要能读")
        self.assertEqual(entry["incoming"]["images"][0]["uri"], f"/static/pool/{name}",
                         "题面里的图地址要跟着换到池子自己那份，不能还指着批次的目录")

    def test_04_pool_holds_no_page_backup(self) -> None:
        """4.3 底图不进池：条目只带题自己的成品图，没有任何整页底图的位置。"""
        batch_id, pool_id = self._prepare_pool(_doc(images=[_IMAGE]), assets=_ASSET)
        row = self._pool_raw(pool_id)
        assets = json.loads(row["assets_json"])
        self.assertEqual(len(assets), 1)
        self.assertTrue(str(assets[0]["name"]).startswith("cimg_"),
                        "图跟题走：池内这条的成品图是自己那一份，不是批次的 pimg_")
        blob = f"{row['doc_json']}{row['assets_json']}{row['source_name']}"
        for mark in ("page", "backup", "pending_sources", ".pdf", ".docx\""):
            self.assertNotIn(mark, blob, f"池内记录里不该出现整页底图的痕迹：{mark}")
        self.assertEqual(self.pending_pool.get_entry(pool_id)["asset_count"], 1)

    def test_04b_images_are_copied_not_shared(self) -> None:
        """3.6 的图归属：抽走复制出 ``cimg_``，批次那枚 ``pimg_`` 原样留在 ``pending_assets/``。

        两边各留一份是「同生共死」的前提——事务一旦回滚，字节还在；批次清残留
        切图时也不会碰到池里这一份。
        """
        batch_id, pool_id = self._prepare_pool(_doc(images=[_IMAGE]), assets=_ASSET)
        pool_name = self._pool_asset_names(pool_id)[0]
        item_id = str(self._pool_raw(pool_id)["item_id"])
        batch_name = "pimg_" + pool_name[len("cimg_"):]
        self.assertTrue(self.pending_assets.pool_asset_path(pool_name).is_file())
        self.assertTrue(self.pending_assets.asset_path(batch_name).is_file(),
                        "批次的成品图不该被搬走，它还没审完")
        self.assertEqual(self._con().execute(
            "SELECT 1 FROM pending_questions WHERE id = ?", (item_id,)).fetchone(), None,
            "抽走＝待审行已删")
        self.assertIn(batch_name,
                      json.loads(self._con().execute(
                          "SELECT assets_json FROM batches WHERE batch_id = ?",
                          (batch_id,)).fetchone()[0]),
                      "批次残留切图清单继续记着 pimg_，等未审数归零由 _settle_batch 清")

    def test_05_tier_is_read_side_filter_only(self) -> None:
        """读接口按档位取候选（4.3）：档位不落盘，只在取的时候过滤一次。"""
        self._insert_row("pool_aaaaaaaa", "p_" + "a" * 24, "certain", 100)
        self._insert_row("pool_bbbbbbbb", "p_" + "b" * 24, "possible", 32)
        loose = self.pending_pool.list_pool(tier="loose")["items"]
        strict = self.pending_pool.list_pool(tier="strict")["items"]
        self.assertEqual([item["pool_id"] for item in loose],
                         ["pool_aaaaaaaa", "pool_bbbbbbbb"])
        self.assertNotIn("pool_bbbbbbbb", [item["pool_id"] for item in strict])
        con = self._con()
        self.assertIsNone(
            con.execute("SELECT 1 FROM pragma_table_info('duplicate_pool')"
                        " WHERE name = 'tier'").fetchone(),
            "档位不许落盘：池表里不能长出 tier 这一列")

    def test_06_failed_scan_admits_nothing(self) -> None:
        """3.4 的下游：初查失败时进池接口照实报，不伪装成「本批没有重题」。"""
        self._seed_bank(_doc())
        result = self.pending_pool.admit_from_scan("B-900", provider_id=PLUGIN_ID)
        self.assertEqual(result["admitted"], 0)
        self.assertEqual(result["status"], "pending")


class PoolActionsTest(PoolCase):
    """判据 4.4–4.8 的四个动作语义。"""

    def test_10_merge_metadata_touches_only_metadata(self) -> None:
        """4.4 只并元数据：题面五个字段逐字不变，标签/考向取并集，难度只在缺省时补。

        存储层 ``ck_questions_difficulty`` 把难度钉死成 L1–L4，主库那侧不可能真缺省，
        所以「仅补缺」这一支在真库上是防御性代码；两侧同值时既不覆盖也不报冲突。
        """
        topic_main = self._seed_topic("1")["topic_ids"][0]
        topic_incoming = self._seed_topic("2")["topic_ids"][0]
        main_id = self._seed_bank(_doc())[0]
        con = sqlite3.connect(self.db_path)
        try:
            con.execute("INSERT INTO question_topics (question_id, topic_id, is_primary,"
                        " sort_order, created_at) VALUES (?, ?, 1, 0, ?)",
                        (main_id, topic_main, STAMP))
            con.commit()
        finally:
            con.close()
        self.bank.update_question(PLUGIN_ID, main_id, {"tags": ["基础"]})
        before = self._bank_row(main_id)
        incoming = _doc(tags=["函数与方程"], taxonomy={"topic_ids": [topic_incoming]})
        batch_id, pool_id = self._prepare_pool(incoming, seed=False)

        result = self.pending_pool.merge_metadata(pool_id)
        self.assertTrue(result["ok"])
        after = self._bank_row(main_id)
        for field in ("stem", "options", "answer", "solution", "images"):
            self.assertEqual(after.get(field), before.get(field), f"{field} 被改动了")
        self.assertEqual(sorted(after["tags"]), sorted(["基础", "函数与方程"]))
        # 主考向仍是主库那道题的：层名与首位挂载都不许被池里这条顶掉。
        self.assertEqual(after["taxonomy"]["topic_ids"][0], topic_main)
        self.assertIn(topic_incoming, after["taxonomy"]["topic_ids"])
        self.assertEqual(after["difficulty"], "L2")
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(self.pending_pool.list_pool()["total"], 0)

    def test_11_merge_metadata_conflicts_are_listed_not_overwritten(self) -> None:
        """4.4 冲突不覆盖：两侧都有且值不同 → 只列清单，主库原值一个不改。"""
        pool_id = self._prepare_pool(_doc(difficulty="L4", tags=["新标签"]))[1]
        result = self.pending_pool.merge_metadata(pool_id)
        self.assertEqual(result["conflicts"],
                         [{"field": "difficulty", "main": "L2", "incoming": "L4"}])
        self.assertEqual(self._bank_row("q_pool0001")["difficulty"], "L2")

    def test_12_merge_metadata_appends_source(self) -> None:
        """4.4 来源追加：池内这条的原卷并进主库那道题的原卷组，已有挂载不掉。"""
        main_id = self._seed_bank(_doc())[0]
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                "INSERT INTO sources (id, paper_name, school_id, year, exam_type, grade,"
                " created_at, updated_at) VALUES ('so_aaabbbb', '期中卷', NULL, 2025,"
                " '期中', '高一', ?, ?)", (STAMP, STAMP))
            con.execute("INSERT INTO question_sources (question_id, source_id,"
                        " question_no, created_at) VALUES (?, 'so_aaabbbb', '3', ?)",
                        (main_id, STAMP))
            con.commit()
        finally:
            con.close()
        pool_id = self._prepare_pool(_doc(source={"paper_title": "期末卷",
                                                  "question_no": "7", "year": 2026}), seed=False)[1]
        self.pending_pool.merge_metadata(pool_id)
        titles = {item["paper_title"] for item in
                  self.bank.question_sources(PLUGIN_ID, main_id)["items"]}
        self.assertEqual(titles, {"期中卷", "期末卷"})

    def test_13_add_solution_appends_next_solution(self) -> None:
        """4.5 新增解析：主库原题解析后接上新解法，并追加来源。"""
        pool_id = self._prepare_pool(_doc(solution="另解：因式分解 $(x-2)(x-3)=0$。",
                                          source={"paper_title": "竞赛模拟卷",
                                                  "question_no": "1"}))[1]
        result = self.pending_pool.add_solution(pool_id)
        self.assertTrue(result["ok"])
        solution = self._bank_row("q_pool0001")["solution"]
        self.assertIn("因式分解", solution)
        self.assertIn("解法", solution)
        self.assertEqual(result["solution_ordinal"], 1)
        self.assertIn("竞赛模拟卷", {item["paper_title"] for item in
                                    self.bank.question_sources(PLUGIN_ID, "q_pool0001")["items"]})

    def test_14_add_solution_without_solution_refuses(self) -> None:
        """4.5 没有解析就没有能并进去的内容：如实报错，不静默成功。"""
        pool_id = self._prepare_pool(_doc())[1]
        blank = _doc()
        blank["solution"] = "   "
        self._set_doc(pool_id, blank)
        with self.assertRaises(self.pending_bank.PendingError):
            self.pending_pool.add_solution(pool_id)
        self.assertEqual(self.pending_pool.list_pool()["total"], 1, "失败后条目必须还在池里")

    def test_15_keep_separate_creates_new_question(self) -> None:
        """4.6 不重复：主库新增一道独立题，原题逐字不动。"""
        topic = self._seed_topic("3")
        main_id = "q_pool0001"
        pool_id = self._prepare_pool(_doc(taxonomy=topic))[1]
        result = self.pending_pool.keep_separate(pool_id)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["written"])
        created = str(result["created_id"])
        self.assertTrue(created.startswith("q_") and created != main_id)
        self.assertEqual(self._bank_row(main_id)["stem"], STEM)
        self.assertEqual(self._bank_row(created)["taxonomy"]["topic_ids"], topic["topic_ids"])
        self.assertEqual(self.pending_pool.list_pool()["total"], 0)

    def test_16_keep_separate_missing_items_stays_in_pool(self) -> None:
        """4.6 缺项不写库：缺答案与缺考向都留在池里，并把缺什么原样回给老师。"""
        pool_id = self._prepare_pool(_doc())[1]
        stripped = _doc()
        stripped.pop("answer", None)
        self._set_doc(pool_id, stripped)
        result = self.pending_pool.keep_separate(pool_id)
        self.assertFalse(result["ok"])
        self.assertFalse(result["written"])
        self.assertTrue(result["kept_in_pool"])
        self.assertIn("答案", result["missing"])
        self.assertIn("考向", result["missing"])
        self.assertEqual(self.pending_pool.list_pool()["total"], 1)
        main_con = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(
                main_con.execute("SELECT COUNT(*) FROM questions").fetchone()[0], 1)
        finally:
            main_con.close()
        placeholder = _doc(taxonomy=self._seed_topic("9"))
        placeholder["stem"] = "（待识别：题干未清）已知 $x^2-5x+6=0$，求根之和（　　）。"
        self._set_doc(result["pool_id"], placeholder)
        again = self.pending_pool.keep_separate(result["pool_id"])
        self.assertFalse(again["ok"], again)
        self.assertIn("占位符未清", again["missing"])

    def test_17_delete_removes_only_the_pool_entry(self) -> None:
        """4.7 删除：只删池内这条与它自己的 ``cimg_``；主库题与批次目录一张都不碰。

        批次侧的账本在这里：``batches.assets_json`` 记着的每一枚 ``pimg_``（含本条
        抽走前那一份）都原样留在 ``pending_assets/``，等未审数归零由 ``_settle_batch``
        清——池子没有那个目录的删除权（判据 4.7／3.6）。
        """
        batch_id, pool_id = self._prepare_pool(_doc(images=[_IMAGE]), assets=_ASSET)
        pool_name = self._pool_asset_names(pool_id)[0]
        batch_names = json.loads(self._con().execute(
            "SELECT assets_json FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()[0])
        self.assertTrue(batch_names, "批次侧的残留切图清单本该记着这枚 pimg_")

        result = self.pending_pool.delete_entry(pool_id)
        self.assertTrue(result["ok"])
        self.assertEqual(self.pending_pool.list_pool()["total"], 0)
        self.assertEqual(self._bank_row("q_pool0001")["stem"], STEM)
        for name in batch_names:
            self.assertTrue(self.pending_assets.asset_path(name).is_file(),
                            f"批次的图 {name} 不许被池内删除动到")
        self.assertFalse(self.pending_assets.pool_asset_path(pool_name).is_file())
        self.assertEqual(result["deleted_assets"], 1)

    def test_18_delete_drops_asset_once_unreferenced(self) -> None:
        """4.7 的图归属（最终形态）：抽走之后池内这条自己的成品图删得掉，也只删它自己。"""
        batch_id, pool_id = self._prepare_pool(_doc(images=[_IMAGE]), assets=_ASSET)
        pool_name = self._pool_asset_names(pool_id)[0]
        batch_name = "pimg_" + pool_name[len("cimg_"):]
        result = self.pending_pool.delete_entry(pool_id)
        self.assertEqual(result["deleted_assets"], 1)
        self.assertFalse(self.pending_assets.pool_asset_path(pool_name).is_file())
        self.assertTrue(self.pending_assets.asset_path(batch_name).is_file(),
                        "批次那一份留到 _settle_batch 统一清，池子不越界")

    def test_19_answer_mismatch_locks_first_two_only(self) -> None:
        """4.8 答案闸门：明确不同 → 合并元数据与新增解析锁死，分开存与删除照走。"""
        topic = self._seed_topic("4")
        self._seed_bank(_doc())
        incoming = _doc(answer="B", taxonomy=topic, solution="换个答案的另一种解法。")
        batch_id, _ = self._draft(incoming)
        self._scan(batch_id)
        self._admit(batch_id)
        pool_id = self.pending_pool.list_pool()["items"][0]["pool_id"]
        entry = self.pending_pool.get_entry(pool_id)
        self.assertTrue(entry["answer"]["mismatch"])
        self.assertEqual(entry["locked_actions"], ["merge_metadata", "add_solution"])
        for action in ("merge_metadata", "add_solution"):
            with self.assertRaises(self.pending_pool.PoolActionRefused) as caught:
                self.pending_pool.act(pool_id, action)
            self.assertEqual(caught.exception.code, "answer_mismatch")
        self.assertEqual(self._bank_row("q_pool0001")["answer"]["final"], "A")
        kept = self.pending_pool.act(pool_id, "keep_separate")
        self.assertTrue(kept["ok"], kept)

    def test_20_unknown_action_is_refused(self) -> None:
        """池里只有四个动作：【覆盖】【放弃】与任何别的名字都不认。"""
        pool_id = self._prepare_pool(_doc())[1]
        for action in ("overwrite", "give_up", "", "删除"):
            with self.assertRaises(self.pending_bank.PendingError):
                self.pending_pool.act(pool_id, action)


class PoolPersistenceTest(PoolCase):
    """判据 4.9 与 5.5：落盘、不复活、终局闸门。"""

    def test_30_restart_reads_entries_and_adjudications(self) -> None:
        """4.9 重启可读：条目与已裁决状态都在库里，换一个连接照样读。"""
        pool_id = self._prepare_pool(_doc())[1]
        self.pending_pool.delete_entry(pool_id)
        fresh = sqlite3.connect(Path(self.tmp.name) / "pending.db")
        fresh.row_factory = sqlite3.Row
        self.addCleanup(fresh.close)
        try:
            rows = fresh.execute("SELECT * FROM pool_actions").fetchall()
        except sqlite3.OperationalError as error:   # 表没建到磁盘上就是这个错
            self.fail(f"裁决记录没有落盘：{error}")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["action"], "delete")
        self.assertEqual(row["batch_id"], "B-001")            # 最小审计四要素
        self.assertEqual(row["main_id"], "q_pool0001")
        self.assertTrue(str(row["created_at"]))
        self.assertEqual(fresh.execute("PRAGMA user_version").fetchone()[0],
                         self.pending_db.SCHEMA_VERSION)

    def test_31_rescan_does_not_resurrect_adjudicated_item(self) -> None:
        """已裁决不复活（5.3 的数据层）：同一条待审号再被扫到，进池接口照旧挡下。

        抽走之后待审行本来就没了，重扫自然带不出它；这条用例把那一行**原号补回**
        批次（模拟老师把同一张卷子又拖进来一次），专门盯住防复活那一道闸。
        """
        batch_id, pool_id = self._prepare_pool(_doc())
        raw = self._pool_raw(pool_id)
        item_id = str(raw["item_id"])
        self.pending_pool.delete_entry(pool_id)
        self._reinsert_pending(raw)
        self._scan(batch_id)
        result = self._admit(batch_id, tier="loose")
        self.assertEqual(result["admitted"], 0, result)
        self.assertEqual(result["skipped_adjudicated"], 1, result)
        self.assertEqual(self.pending_pool.list_pool()["total"], 0)
        self.assertEqual(self._con().execute(
            "SELECT COUNT(*) FROM pool_actions WHERE item_id = ?",
            (item_id,)).fetchone()[0], 1)

    def _reinsert_pending(self, pool_row: sqlite3.Row) -> None:
        """把抽走时删掉的那一行按原号补回待审池（只用于防复活用例）。"""
        con = self._con()
        con.execute(
            "INSERT INTO pending_questions (id, batch_id, doc_json, assets_json, origin,"
            " created_at, updated_at, seq) VALUES (?, ?, ?, '[]', 'test', ?, ?, 9)",
            (str(pool_row["item_id"]), str(pool_row["batch_id"]), str(pool_row["doc_json"]),
             str(pool_row["created_at"]), str(pool_row["updated_at"])))
        con.commit()

    def test_32_terminal_gate_still_blocks_exact_duplicate(self) -> None:
        """5.5 终局闸门没拆：绕过池子直接 approve 同一条，精确同题仍然拦。

        这条要的是「题还留在待审池」的原状态，所以把后台的自动抽走按住——
        抽走之后那条已经不在池子里，闸门压根轮不到它说话。
        """
        self._seed_bank(_doc())
        batch_id, item_ids = self._draft(_doc(), hold_admit=True)
        self._scan(batch_id)
        with self.assertRaises(self.pending_bank.PendingDuplicate) as caught:
            self.pending_bank.approve(item_ids[0], PLUGIN_ID)
        self.assertEqual(caught.exception.existing_id, "q_pool0001")

    def test_33_schema_version_and_tables(self) -> None:
        """结构底线：``SCHEMA_VERSION`` 到 9，旧库连上自动补池表与页面图列。"""
        self.assertEqual(self.pending_db.SCHEMA_VERSION, 9)
        names = {row[0] for row in self._con().execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertIn("duplicate_pool", names)
        self.assertIn("pool_actions", names)

    def test_34_admit_twice_same_batch_adds_nothing(self) -> None:
        """一条进来题只占一条：同批重复进池不多占，也不折叠成一组。"""
        batch_id, _ = self._prepare_pool(_doc())
        again = self._admit(batch_id)
        self.assertEqual(again["admitted"], 0, again)
        self.assertEqual(self.pending_pool.list_pool()["total"], 1)
        ids = [row[0] for row in self._con().execute(
            "SELECT pool_id FROM duplicate_pool ORDER BY pool_id")]
        self.assertEqual(len(ids), 1)


class PoolEvictionTest(PoolCase):
    """判据 3.5／3.6 与 5.4 的后台侧：抽走的时机、原子性与账目。"""

    STEM2 = "重题池口径题：已知 $x^2-7x+12=0$，求根之和（　　）。"

    def _pool_dir_files(self) -> list[str]:
        root = Path(self.tmp.name) / "pool_assets"
        return sorted(p.name for p in root.glob("*")) if root.is_dir() else []

    def _pending_ids(self, batch_id: str) -> list[str]:
        return [str(row["id"]) for row in self._con().execute(
            "SELECT id FROM pending_questions WHERE batch_id = ? ORDER BY seq", (batch_id,))]

    def _spy_admit(self) -> list[dict[str, Any]]:
        """把后台链的**抽走那一步**接住：记下「抽走前那一轮的结论」＋「那一刻
        ``scan_state`` 读到什么」，然后原样放行，让抽走照旧真跑。

        抽走前的结论只在内存里递进来（``state=``），它还没发布；发布排在抽走之后，
        所以读到的应当还是 ``pending``——判据 3.5 那个 0.4 秒空窗就藏在这一步的次序里。
        """
        records: list[dict[str, Any]] = []
        real = self.pending_dedupe.admit_into_pool

        def spy(batch_id: str, provider_id: str, **kwargs):
            records.append({
                "pre": dict(kwargs.get("state") or {}),
                "readable": self.pending_dedupe.scan_state(batch_id),
            })
            return real(batch_id, provider_id, **kwargs)

        self.pending_dedupe.admit_into_pool = spy
        self.addCleanup(setattr, self.pending_dedupe, "admit_into_pool", real)
        return records

    def test_40_automatic_eviction_happens_at_persist_time(self) -> None:
        """3.5 抽走在落库阶段完成：后台链跑完就是最终集合，前端一次都没参与。

        纸带不跳是这一条在界面上的效果，本机真机才能验；数据层能证的是
        「首次读到批次时，命中的题已经不在待审池里了」。
        """
        self._seed_bank(_doc())
        batch_id, item_ids = self._draft(_doc())          # 只有 save_draft，没有手动扫、没有手动抽
        state = self.pending_dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "done", state)
        self.assertEqual(state["pooled"], 1, "初查结论要能报出这批已抽走几条")
        self.assertEqual(self._pending_ids(batch_id), [],
                         "首次读到的就该是抽完的集合，不许等前端拉一次才少")
        self.assertEqual([item["item_id"] for item in
                          self.pending_pool.list_pool()["items"]], item_ids)
        card = next(c for c in self.pending_batches.batch_list()["batches"]
                    if c["batch_id"] == batch_id)
        self.assertEqual((card["pending_count"], card["total"]), (0, 1), card)

    def test_41_rescan_after_eviction_adds_nothing(self) -> None:
        """3.5 的下游：抽完再整批重扫，候选集已空，不会二次搬同一条、也不会补删。"""
        batch_id, _ = self._prepare_pool(_doc())
        state = self._scan(batch_id)
        self.assertEqual(state["candidate_count"], 0,
                         "待审池里那条已经没了，重扫不该再把它当候选")
        result = self._admit(batch_id)
        self.assertEqual(result["admitted"], 0, result)
        self.assertEqual(result["evicted"], 0, result)
        self.assertEqual(self.pending_pool.list_pool()["total"], 1)
        self.assertEqual(self._pending_ids(batch_id), [])

    def test_42_missing_image_file_moves_nothing_for_that_row(self) -> None:
        """3.6 失败注入·图文件缺失：这一条整条不搬，既不进池也不删待审行。

        宁可让这条留在批次里一张张审，也不能让池里躺一条点开是死链的题。
        """
        self._seed_bank(_doc())
        batch_id, item_ids = self._draft(_doc(images=[_IMAGE]), assets=_ASSET,
                                         hold_admit=True)
        name = self._pending_asset_names(batch_id)[0]
        self.pending_assets.asset_path(name).unlink()

        result = self._admit(batch_id)
        self.assertEqual(result["admitted"], 0, result)
        self.assertEqual(result["skipped_missing_asset"], item_ids, result)
        self.assertEqual(self.pending_pool.list_pool()["total"], 0)
        self.assertEqual(self._pending_ids(batch_id), item_ids, "待审行一条都没少")
        self.assertEqual(self._pool_dir_files(), [], "复制失败的产物不许留在池目录里")

    def test_43_write_error_rolls_the_whole_batch_back(self) -> None:
        """3.6 失败注入·写库报错：整批事务回滚，池里不多一条、待审不少一条、图不留孤儿。

        用 ``BEFORE DELETE`` 触发器把删待审行那一步变成真 SQLite 错误——第一条的
        「写池行」已经执行、第二条删行时报错，才能证明回滚跨语句、不是单语句自救。
        """
        self._seed_bank(_doc(), _doc(stem=self.STEM2))
        batch_id, item_ids = self._draft(_doc(), _doc(stem=self.STEM2),
                                         assets=_ASSET, hold_admit=True)
        con = self._con()
        con.execute("CREATE TRIGGER inj_fail_before_delete BEFORE DELETE ON pending_questions"
                    " BEGIN SELECT RAISE(ABORT, '注入：写库失败'); END")
        con.commit()
        try:
            with self.assertRaises(sqlite3.Error):
                self._admit(batch_id)
        finally:
            con.execute("DROP TRIGGER inj_fail_before_delete")
            con.commit()
        self.assertEqual(self.pending_pool.list_pool()["total"], 0,
                         "回滚后池里一条都不该多出来")
        self.assertEqual(sorted(self._pending_ids(batch_id)), sorted(item_ids),
                         "回滚后待审池一条都不该少")
        self.assertEqual(self._pool_dir_files(), [], "回滚要把这次复制的成品图一并删干净")
        self.assertEqual(self.pending_batches.batch_list()["batches"]
                         [0]["pending_count"], 2, "未审数也得跟着回滚")
        # 触发器拆掉后同一次抽走照样成功：证明回滚没把库留在半截状态上。
        after = self._admit(batch_id)
        self.assertEqual(after["admitted"], 2, after)
        self.assertEqual(after["evicted"], 2)
        self.assertEqual(self._pending_ids(batch_id), [])

    def test_44_batch_settle_keeps_pool_image_readable(self) -> None:
        """判据 4.2／4.7 的必做用例：抽走 → 整批入库 → ``_settle_batch`` 删副本 → 池内照读。

        批次清的是 ``pending_assets/`` 里那些 ``pimg_``（含这条抽走前用过的那一枚），
        池里这条靠自己的 ``cimg_`` 活下来，题面地址也已经换到池目录。
        """
        topic = self._seed_topic("7")
        self._seed_bank(_doc())
        batch_id, item_ids = self._draft(_doc(images=[_IMAGE]), _other_doc(taxonomy=topic),
                                         assets=_ASSET)
        entry = self.pending_pool.list_pool()["items"][0]
        pool_id = entry["pool_id"]
        pool_name = self._pool_asset_names(pool_id)[0]
        self.assertEqual(self._pending_ids(batch_id), [item_ids[1]],
                         "命中的那条已抽走，没命中的那条留在批次里等审")

        approved = self.pending_bank.approve(item_ids[1], PLUGIN_ID)
        self.assertTrue(approved.get("question") or approved.get("ok") or approved,
                        approved)
        card = self.pending_bank._settle_batch(batch_id)
        self.assertTrue(card["done"], card)
        self.assertFalse(self.pending_assets.asset_path(
            "pimg_" + pool_name[len("cimg_"):]).is_file(),
            "批次的残留切图确实被清掉了——这张就是池内条目唯一还读得到的图")
        detail = self.pending_pool.get_entry(pool_id)
        self.assertEqual(detail["incoming"]["stem"], STEM)
        self.assertTrue(self.pending_assets.pool_asset_path(pool_name).is_file(),
                        "整批入库、副本删干净之后，池内这条的成品图仍要能读")
        self.assertEqual(detail["incoming"]["images"][0]["uri"], f"/static/pool/{pool_name}")

    def test_45_pooled_items_are_not_pending_duplicates(self) -> None:
        """5.4 不串账：抽走之后，一键剔除与整批扫灯都再也看不见池内那条。"""
        topic = self._seed_topic("8")
        self._seed_bank(_doc())
        batch_id, item_ids = self._draft(_doc(), _other_doc(taxonomy=topic), assets=None)
        pooled_id = item_ids[0]
        self.assertEqual(self._pending_ids(batch_id), [item_ids[1]])

        report = self.pending_dedupe.batch_duplicate_groups(batch_id, PLUGIN_ID)
        self.assertEqual(report["scanned"], 1, report)
        self.assertNotIn(pooled_id, report["drop_ids"],
                         "池内那条不再算待审重复，一键剔除的清单里不许有它")

        with self.assertRaises(self.pending_bank.BatchPurgeError) as caught:
            self.pending_bank.purge_batch_duplicates(batch_id, PLUGIN_ID,
                                                     [pooled_id], [pooled_id])
        self.assertEqual(caught.exception.code, "batch_purge_pending_not_in_batch",
                         "池内那条早已不在待审池，一键剔除直接认它「不在本批」，整批不动")
        self.assertEqual(self.pending_pool.list_pool()["total"], 1,
                         "剔除失败不该把池内条目一起带走")

        listed = self.pending_batches.list_batch_questions(batch_id)
        self.assertEqual(listed["pending_count"], 1)
        self.assertEqual(listed["total"], 2, "总题数记的是这一批导入了几道，不因抽而走")
        self.assertEqual([item["id"] for item in listed["items"]], [item_ids[1]])

    def test_46_four_identical_hits_are_all_pooled_not_one(self) -> None:
        """S6 缺陷 1 的形状搬到服务层钉住：4 道同题面命中 + 1 道独题，命中的一条不留。

        旧形状：``group_duplicates`` 的「一条 p_ 只进一个组」把批内组当先占坑，
        成员全被判成「批内互重」，主库命中从**候选清单**里消失；抽走只认
        ``reason="bank"`` ⇒ 4 道命中只搬 1 道（那道「要留的」），剩下 3 道挂在
        待审里等一个已经被抽走的保留者。HTTP 真机跑出来是 ``pooled=2``／
        ``pending_count=3``，服务层当时的用例没有「批内成组 + 主库同指纹」这个形状，
        于是两层各说各话——判据 3.5 要的是「命中的题一条不剩」。
        """
        main_ids = self._seed_bank(_doc())
        records = self._spy_admit()
        # 逐题带自己的 assets——与 S6 探针那一批完全同形：只有第一道配图。
        saved = self.pending_bank.save_draft([
            {"question": _doc(images=[_IMAGE]), "assets": _ASSET},
            {"question": _doc(solution="另解：因式分解 $(x-2)(x-3)=0$，和为 $5$。"),
             "assets": []},
            {"question": _doc(answer="B"), "assets": []},
            {"question": _doc(solution="又解：求根公式得 $x=2,3$，和为 $5$。"), "assets": []},
            {"question": _other_doc(), "assets": []},
        ], source_name="期末模拟卷.docx")
        self._settle_dedupe_threads()
        batch_id, item_ids = saved["batch_id"], saved["saved_ids"]
        pre = records[0]["pre"]
        self.assertEqual(pre["status"], "done", pre)
        self.assertEqual(pre["scanned"], 5, "五道都进了初查的眼睛")
        self.assertFalse(pre["truncated"],
                         "没撞到 MAX_COMPARE／MAX_CANDIDATES，别拿截断圆解「命中 4 只抽 1」")
        self.assertEqual(pre["candidate_count"], 4, pre)
        self.assertEqual({c["reason"] for c in pre["candidates"]}, {"bank"},
                         "批内成组但主库有同指纹的，报的就是主库命中，不是批内互重")
        self.assertEqual({c["existing_id"] for c in pre["candidates"]}, set(main_ids))
        self.assertEqual({c["item_id"] for c in pre["candidates"]}, set(item_ids[:4]))

        state = self.pending_dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "done", state)
        self.assertEqual(state["pooled"], 4, "四道命中一条不留")
        self.assertEqual(self._pending_ids(batch_id), [item_ids[4]],
                         "留在待审里的只有那道独题")
        # PM 要的「先数行数」：``dedupe_findings`` 的行数＝候选条数＝实际搬进的池行数，
        # 三者 1:1:1——「命中 4 只抽 2」既不是每组只取第一条的去重键，也不是上限。
        # 抽完不再重算发布，所以这里落的仍是整批初查那一版账（``scanned``＝5）。
        findings = self._con().execute(
            "SELECT reason, COUNT(*) AS n FROM dedupe_findings WHERE batch_id = ?"
            " GROUP BY reason", (batch_id,)).fetchall()
        self.assertEqual([(row["reason"], row["n"]) for row in findings], [("bank", 4)],
                         "findings 行数与池行对不上＝抽走与结论分了两张账")
        self.assertEqual(state["scanned"], 5, "结论报的是整批初查的账，不是抽剩的账")

        entries = self.pending_pool.list_pool()["items"]
        self.assertEqual(len(entries), 4, "一条一题：四道命中就是四条池内条目")
        by_item = {entry["item_id"]: entry for entry in entries}
        self.assertEqual(set(by_item), set(item_ids[:4]))
        # 四要素全等（题型／题干／选项／配图）的三条是「确定」；配图按内容哈希比，
        # 多一张图就差一个要素，落到「很像」——这一条把「配图也进判据」钉在池里。
        self.assertEqual(by_item[item_ids[0]]["level"], "very_similar")
        self.assertEqual([by_item[i]["level"] for i in item_ids[1:4]],
                         ["certain", "certain", "certain"])
        self.assertEqual(by_item[item_ids[0]]["asset_count"], 1,
                         "S6 缺陷 3：成品图跟着命中题进池，不是恒 0")
        pool_asset = self._pool_asset_names(by_item[item_ids[0]]["pool_id"])[0]
        on_disk = (Path(self.tmp.name) / "pool_assets" / pool_asset).read_bytes()
        self.assertEqual(on_disk, base64.b64decode(PNG_BASE64),
                         "池目录里那一份就是导入的原图字节，抽走不是只搬了个文件名")

    def test_47_done_is_readable_only_after_the_evict_lands(self) -> None:
        """S6 缺陷 2：``done`` 被读到的那一刻，抽走已经落地——中间不许有空窗。

        旧时序是「先发布 done，再回头抽走」，真机轮询能读到一整拍
        ``status=done / pooled=0 / pending_count=5``——老师看到的正是「已扫完、无重题」
        这个假象。修法不改前端、不让轮询多等一拍，只把顺序倒过来：抽走排在发布之前，
        抽完再重算一次账，然后**只发布一次**。这里在抽走那一步里回读 ``scan_state``，
        它必须还不是 ``done``；等 ``done`` 读到了，池表与卡片账目已经对平。
        """
        self._seed_bank(_doc())
        records = self._spy_admit()
        batch_id, item_ids = self._draft(_doc(), _doc(answer="B"))

        self.assertTrue(records, "后台链没走抽走这一步，本用例无从判时序")
        for record in records:
            self.assertNotEqual(record["readable"].get("status"), "done",
                                f"抽走落库时 done 已经可读，空窗又回来了：{record['readable']}")
        self.assertEqual(records[0]["pre"]["candidate_count"], 2, records[0]["pre"])

        state = self.pending_dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "done", state)
        rows = int(self._con().execute(
            "SELECT COUNT(*) FROM duplicate_pool WHERE batch_id = ?",
            (batch_id,)).fetchone()[0])
        self.assertEqual(state["pooled"], rows,
                         "读到 done 就得给出抽完的池内条数，不能先报 0 再补")
        card = next(c for c in self.pending_batches.batch_list()["batches"]
                    if c["batch_id"] == batch_id)
        self.assertEqual(card["pending_count"] + state["pooled"], card["total"],
                         "5.4 的账在 done 第一帧就对平：未审＋池内＝本批总数")
        self.assertEqual(self._pending_ids(batch_id), [])

    def test_48_done_pool_and_account_are_one_commit_not_two_steps(self) -> None:
        """S6 缺陷 2 的最终形态：**「done 已可读」与「卡片还说全在待审」不能分两拍**。

        PM 读原始日志的定性比测试工程师更准：旧证据那一拍是 ``scan_status=done``、
        ``pooled=0``、``pending_count=5``、``items`` 长 5，而**池表里已经有 2 条**——
        病根不在「抽走排在 done 之后」（把 done 往后推只会把空窗换个位置），而在
        「批次卡账目落后池表一拍」。所以修法是把四件事塞进同一条事务：写池行＋删待审行
        ＋``refresh_batch``＋落 ``dedupe_scans/dedupe_findings``，一次提交。

        这里在 ``persist_scan_in_txn`` 那一步同时抓两张快照：
        - **事务内**（拿事务自己的连接）：池行、待审残留、批次账目、``done`` 四件已经齐了；
        - **事务外**（另起连接，提交前）：四件**一件都不许露出来**——这才是「一次提交」
          的机械证据，而不是「我先写了池行、顺手补了个 done」。
        最后验对外第一帧 ``done`` 的自洽：``pooled``＝池表数＝``dedupe_findings`` 里
        ``reason=bank`` 的行数，``pending_count``＝待审实际行数，``pool_total`` 对得上。
        """
        self._seed_bank(_doc())
        real = self.pending_dedupe.persist_scan_in_txn
        shots: list[dict[str, Any]] = []
        wal = str(self._con().execute("PRAGMA journal_mode").fetchone()[0]).lower() == "wal"

        def spy(con: Any, batch_id: str, state: dict[str, Any]) -> bool:
            wrote = real(con, batch_id, state)
            def snap(reader: Any) -> dict[str, int | str]:
                return {
                    "pool": int(reader.execute(
                        "SELECT COUNT(*) FROM duplicate_pool WHERE batch_id = ?",
                        (batch_id,)).fetchone()[0]),
                    "pending": int(reader.execute(
                        "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?",
                        (batch_id,)).fetchone()[0]),
                    "card": int(reader.execute(
                        "SELECT pending_count FROM batches WHERE batch_id = ?",
                        (batch_id,)).fetchone()[0]),
                    "findings": int(reader.execute(
                        "SELECT COUNT(*) FROM dedupe_findings WHERE batch_id = ?",
                        (batch_id,)).fetchone()[0]),
                    "status": str((reader.execute(
                        "SELECT status FROM dedupe_scans WHERE batch_id = ?",
                        (batch_id,)).fetchone() or [""])[0]),
                }
            in_txn = snap(con)
            # 另起一把连接读：WAL 下提交前对外不可见（非 WAL 会被写锁挡住，读不到
            # 中间态，这条断言就只在 WAL 环境成立——如实标注，不假装有证据）。
            # 这条链在 jzo-dedupe-warm 线程里跑，句柄必须**当场同线程关掉**，
            # 挂 addCleanup 会让主线程去关别人的连接（sqlite3 直接报 ProgrammingError）。
            outside = None
            if wal:
                probe = self.pending_db.connect()
                try:
                    outside = snap(probe)
                finally:
                    probe.close()
            shots.append({"in_txn": in_txn, "outside": outside})
            return wrote

        self.pending_dedupe.persist_scan_in_txn = spy
        self.addCleanup(setattr, self.pending_dedupe, "persist_scan_in_txn", real)
        batch_id, item_ids = self._draft(_doc(), _doc(answer="B"), _other_doc())

        self.assertTrue(shots, "抽走事务里根本没落初查结论，四合一就无从谈起")
        for shot in shots:
            self.assertEqual(shot["in_txn"]["status"], "done", shot["in_txn"])
            self.assertEqual((shot["in_txn"]["pool"], shot["in_txn"]["findings"]),
                             (2, 2), "同题面的两道在**同一笔事务里**各占一条池行——"
                                     "不是「一组只抽一条」")
            self.assertEqual(shot["in_txn"]["pending"], 1, shot["in_txn"])
            self.assertEqual(shot["in_txn"]["card"], 1, "卡账与待审行数在提交前就一致")
            if shot["outside"] is not None:
                self.assertEqual(shot["outside"], {"pool": 0, "pending": 3, "card": 3,
                                                   "findings": 0, "status": ""},
                                 "提交前对外还看得见中间态＝分两步落库，空窗又回来了")

        state = self.pending_dedupe.scan_state(batch_id)
        self.assertEqual(state["status"], "done", state)
        self.assertEqual(state["pooled"], 2, state)
        self.assertEqual(self._pending_ids(batch_id), [item_ids[2]])
        card = next(c for c in self.pending_batches.batch_list()["batches"]
                    if c["batch_id"] == batch_id)
        pool = self.pending_pool.list_pool()
        self.assertEqual(
            (card["pending_count"], len(self._pending_ids(batch_id)),
             state["pooled"], card["dedupe"]["pooled"]),
            (1, 1, 2, 2), "同一拍里卡片账、待审列表、初查注解三处报的是同一套账")
        self.assertEqual(card["pending_count"] + state["pooled"], card["total"],
                         "5.4 的账在 done 第一帧就对平")
        self.assertEqual(pool["total"], 2, "池表总数就是抽进来的两条，不多不少")
        self.assertEqual({entry["item_id"] for entry in pool["items"]},
                         set(item_ids[:2]))

    def test_49_g2_c1_pooled_still_readable_when_the_rescan_fails(self) -> None:
        """军令 #32 · G2 · C1（非零款）：抽过题的批次即使重扫失败，池内数照样给得出。

        这一半在 ``tests/test_pending_dedupe_scan.py`` 拿不到——那个模块按
        ``JZO_POOL_ADMIT_DISABLED`` 关掉抽走，池表恒空，「同源」只能钉成 0＝0。
        这里先真抽两条进池，再把这一批的初查结论刷成 ``failed``，读侧三拍
        （缓存／清缓存回库／批次卡片）都必须还说得出 ``pooled=2``：
        缺了这一拍前端就只能按 ``gone = total - pending - pooled - stored`` 把
        这两道**抽进池里的题**折成「已裁删」，老师的题在账上凭空被删（判据 5.4）。
        """
        def pool_rows() -> int:
            return int(self._con().execute(
                "SELECT COUNT(*) FROM duplicate_pool WHERE batch_id = ?",
                (batch_id,)).fetchone()[0])

        self._seed_bank(_doc())
        batch_id, _item_ids = self._draft(_doc(), _doc(answer="B"))
        self.assertEqual(pool_rows(), 2, "前置：两条已经抽进池")
        self.pending_dedupe.warm_batch_scan(batch_id, "org.jiuzhang.bank-missing")
        failed = self.pending_dedupe.scan_state(batch_id)
        self.assertEqual(failed["status"], "failed", msg=str(failed))
        self.assertEqual(failed["pooled"], pool_rows(), "C1：失败态给的池内数＝池表数")
        self.pending_dedupe._scan_cache.clear()
        off_db = self.pending_dedupe.scan_state(batch_id)
        self.assertEqual((off_db["status"], off_db["pooled"]), ("failed", 2),
                         "重启回库读到的同一拍：状态是失败，池内数不跟着丢")
        card = next(c for c in self.pending_batches.batch_list()["batches"]
                    if c["batch_id"] == batch_id)
        self.assertEqual(card["dedupe"]["pooled"], 2)
        self.assertEqual(card["pending_count"] + card["dedupe"]["pooled"], card["total"],
                         "5.4 的账在失败态照样对平：未审＋池内＝本批总数")

    def test_50_g2_i7_crash_before_commit_leaves_no_half_account(self) -> None:
        """军令 #32 · G2 欠账 7：「抽走中途重启」——commit 前被打断，账目整批退回。

        断点钉在 :func:`pending_dedupe.persist_scan_in_txn` 上，那是抽走事务的**最里侧**
        一步（``pending_pool.py:346``，紧挨着 ``con.commit()``）：进程恰好在这里没掉，
        事务里前面写下的池行、待审删除、``refresh_batch`` 都还只在这条连接里。判据三拍：
        ① 打断后另起连接读四件事＝**抽走前那一拍**（池 0／待审原样／卡片账没动／
        初查世代号没被这一代写进去）；②「重启」（清进程内缓存）后 ``pooled`` 与池表同源＝0；
        ③ 补一次真抽走，四件事同时对平——中间任何一拍露出半截账都是 FAIL。
        """
        def frame() -> dict[str, int]:
            con = self._con()
            return {
                "pool": int(con.execute("SELECT COUNT(*) FROM duplicate_pool"
                                        " WHERE batch_id = ?", (batch_id,)).fetchone()[0]),
                "pending": self._live_count(batch_id),
                "card": int(next(c for c in self.pending_batches.batch_list()["batches"]
                                 if c["batch_id"] == batch_id)["pending_count"]),
                "findings": int(con.execute(
                    "SELECT COUNT(*) FROM dedupe_findings WHERE batch_id = ?",
                    (batch_id,)).fetchone()[0]),
                "generation": int(con.execute(
                    "SELECT generation FROM dedupe_scans WHERE batch_id = ?",
                    (batch_id,)).fetchone()[0]),
            }

        self._seed_bank(_doc())
        batch_id, _item_ids = self._draft(_doc(), hold_admit=True)
        before = frame()
        self.assertEqual((before["pool"], before["pending"], before["card"]), (0, 1, 1), before)
        self.assertGreaterEqual(before["findings"], 1, "前置：初查已经把候选账落好了")
        with mock.patch.object(self.pending_dedupe, "persist_scan_in_txn",
                               side_effect=RuntimeError("模拟 commit 前进程被打断")):
            with self.assertRaises(RuntimeError):
                self._admit(batch_id)
        self.assertEqual(frame(), before, "打断后四件事必须整批退回，不许留半截账")
        self.pending_dedupe._scan_cache.clear()
        restarted = self.pending_dedupe.scan_state(batch_id)
        self.assertEqual(restarted["status"], "done", "重启后读到的还是抽走前那一代结论")
        self.assertEqual(restarted["pooled"], 0, "pooled 与池表同源＝0，不是抽走的 1")
        outcome = self._admit(batch_id)
        self.assertEqual(outcome["admitted"], 1)
        after = frame()
        self.assertEqual((after["pool"], after["pending"], after["card"]), (1, 0, 0), after)
        # 同步补抽这一路读到的 state 里 ``seq`` 已被 ``scan_state`` 剥掉（回 0），
        # 世代号守卫于是**不重写**结论行——它只把池行、待审删除、批次账目三件一起提交。
        # 这不是缺陷：库里那一行本来就是同一代账（``test_46`` 钉过「落的是整批初查那版账」），
        # 但「谁在什么时机写结论」这条口径必须写明白，否则看用例的人会以为四件都在这里落。
        self.assertEqual(after["generation"], before["generation"])
        self.assertEqual(after["findings"], before["findings"])
        self.assertEqual(self.pending_dedupe.scan_state(batch_id)["pooled"], after["pool"],
                         "对外第一帧的 pooled＝池表数＝抽走的条数")

    def test_51_g2_p13_account_homology_holds_without_wal(self) -> None:
        """军令 #32 · G2 · P1③：账目同源**不靠 WAL**——退回 rollback journal 再验一次。

        WAL 下「提交前外部读不到」是快照隔离给的；``journal_mode=DELETE`` 下改动页要到
        commit 才落主文件，读者拿到的同样是**改造前的整份旧账**（或者干脆被锁住读不到）。
        这里把抽走那条连接的 journal 模式压成 ``delete``，在 ``persist_scan_in_txn`` 那一拍
        另起一条连接读四件事：允许「读不到」，不允许读到半截账；提交后再读，四件同时对平。
        """
        mode_seen: list[str] = []
        mid: list[dict[str, Any]] = []
        real_connect = self.pending_pool.connect

        def opener() -> sqlite3.Connection:
            con = real_connect()
            if str(con.execute("PRAGMA journal_mode").fetchone()[0]).lower() != "delete":
                con.execute("PRAGMA journal_mode = DELETE")
            return con

        def reader() -> sqlite3.Connection:
            # 不走 pending_db.connect()：它每次都把文件拧回 WAL，前提就没了
            con = sqlite3.connect(str(self.pending_db.pending_db_path()), timeout=2.0)
            con.row_factory = sqlite3.Row
            return con

        self._seed_bank(_doc())
        batch_id, _item_ids = self._draft(_doc(), hold_admit=True)
        real_persist = self.pending_dedupe.persist_scan_in_txn

        def spy(con: Any, target: str, state: dict[str, Any]) -> bool:
            wrote = real_persist(con, target, state)
            probe: dict[str, Any] = {"journal": None, "error": ""}
            try:
                ext = reader()
                try:
                    probe["journal"] = str(ext.execute("PRAGMA journal_mode").fetchone()[0]).lower()
                    probe["pool"] = int(ext.execute(
                        "SELECT COUNT(*) FROM duplicate_pool WHERE batch_id = ?",
                        (target,)).fetchone()[0])
                    probe["pending"] = int(ext.execute(
                        "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?",
                        (target,)).fetchone()[0])
                finally:
                    ext.close()
            except sqlite3.OperationalError as error:
                probe["error"] = str(error)
            mid.append(probe)
            return wrote

        with mock.patch.object(self.pending_pool, "connect", opener), \
                mock.patch.object(self.pending_dedupe, "persist_scan_in_txn", spy):
            outcome = self._admit(batch_id)
        self.assertEqual(outcome["admitted"], 1, outcome)
        self.assertTrue(mid, "没进事务里那一拍，本用例无从判起")
        for probe in mid:
            if probe["error"]:
                self.assertIn("locked", probe["error"], probe)
                continue
            self.assertEqual(probe["journal"], "delete", probe)
            self.assertEqual((probe["pool"], probe["pending"]), (0, 1),
                             f"非 WAL 下也读出了半截账：{probe}")
        final = reader()
        try:
            self.assertEqual((int(final.execute("SELECT COUNT(*) FROM duplicate_pool"
                                                " WHERE batch_id = ?", (batch_id,)).fetchone()[0]),
                              int(final.execute("SELECT COUNT(*) FROM pending_questions"
                                                " WHERE batch_id = ?", (batch_id,)).fetchone()[0]),
                              int(final.execute("SELECT pending_count FROM batches"
                                                " WHERE batch_id = ?", (batch_id,)).fetchone()[0])),
                             (1, 0, 0), "提交后四件事一起可见")
        finally:
            final.close()

    def _pending_asset_names(self, batch_id: str) -> list[str]:
        row = self._con().execute("SELECT assets_json FROM batches WHERE batch_id = ?",
                                  (batch_id,)).fetchone()
        return [str(name) for name in json.loads(row["assets_json"] or "[]") if name]


if __name__ == "__main__":
    unittest.main()
