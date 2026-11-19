# -*- coding: utf-8 -*-
"""整批打回（2.20.0 卡§2）：源文件＋元数据原样交回，未入库作废、已入库留库。

覆盖：原卷字节在删批之前读出（删时副本仍在）／删批后批次行与待审题清空、
副本物理删除／元数据原始形状往返／text_layer 三态（True/False/None）／
discarded/kept 计数／多副本剥时间戳前缀还原原名／MIME 按魔数不信后缀／
源副本缺失显性报错且批次不动／坏编号与不存在批次各有人话错／HTTP 口子形状。
真库隔离在临时目录，绝不触用户 data/；主库语义复用 delete_batch 既有口径。
运行：``.venv/Scripts/python.exe -m unittest tests.test_return_batch``
"""

from __future__ import annotations

import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from app.api import pending_return as api
from app.core import wire
from app.core.config import settings
from app.core.pending import assets, return_batch as core_return
from app.core.pending.batch import bank_batches
from app.core.pending.db import PendingError, PendingNotFound, connect

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png-body"
PDF = b"%PDF-1.4 fake-pdf-body"


class _PendingIsolated(unittest.TestCase):
    """临时数据目录：真库真副本，绝不触老师工作区的一个字节。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir(parents=True)
        self._saved = (os.environ.get("JZO_DATA_DIR"),
                       os.environ.get("JZO_PLUGINS_DIR"))
        os.environ["JZO_DATA_DIR"] = str(self.data)
        os.environ["JZO_PLUGINS_DIR"] = str(self.root / "plugins")

    def tearDown(self) -> None:
        for key, value in zip(("JZO_DATA_DIR", "JZO_PLUGINS_DIR"), self._saved):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def _seed(self, files: list[tuple[str, bytes]], *, meta: dict | None = None,
              route: dict | None = None, pending: int = 2,
              approved: int = 0) -> tuple[str, list[Path]]:
        rels = [assets.store_source_backup(name, data) for name, data in files]
        backup = rels[0] if len(rels) == 1 else wire.dumps(rels)
        batch_id = bank_batches.create_batch(
            source_backup=backup, source_name=files[0][0])["batch_id"]
        con = connect()
        try:
            con.execute(
                "UPDATE batches SET meta_json = ?, route_json = ?, approved_json = ?"
                " WHERE batch_id = ?",
                (wire.dumps(meta or {}), wire.dumps(route or {}),
                 wire.dumps([{"question_id": "q_bank_%d" % i}
                             for i in range(approved)]), batch_id))
            for i in range(pending):
                con.execute(
                    "INSERT INTO pending_questions"
                    " (id, batch_id, doc_json, assets_json, origin, created_at,"
                    "  updated_at, seq, page_no)"
                    " VALUES (?, ?, '{}', '[]', 'test', 't', 't', ?, 1)",
                    ("p_return%04d" % i, batch_id, i))
            con.commit()
        finally:
            con.close()
        paths = [Path(self.data) / rel for rel in rels]
        return batch_id, paths


class ReturnBatchTest(_PendingIsolated):

    def test_bytes_read_before_delete_and_batch_gone_after(self) -> None:
        batch_id, paths = self._seed([("卷.png", PNG)])
        seen_alive: list[bool] = []
        real_delete = core_return.delete_batch

        def guarded_delete(bid: str) -> dict:
            seen_alive.append(paths[0].is_file())
            return real_delete(bid)

        with mock.patch.object(core_return, "delete_batch", guarded_delete):
            result = core_return.return_batch(batch_id)
        self.assertEqual(seen_alive, [True])
        declared, payload = result["files"][0]["data_url"].split(",", 1)
        self.assertEqual(declared, "data:image/png;base64")
        self.assertEqual(base64.b64decode(payload), PNG)
        self.assertEqual(result["files"][0]["name"], "卷.png")
        self.assertFalse(paths[0].exists())
        con = connect()
        try:
            self.assertIsNone(con.execute(
                "SELECT 1 FROM batches WHERE batch_id = ?", (batch_id,)).fetchone())
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?",
                (batch_id,)).fetchone()[0], 0)
        finally:
            con.close()

    def test_meta_raw_and_text_layer_false_roundtrip(self) -> None:
        meta = {"year": "2026", "subject": "数学", "grade": "九年级",
                "region": "海淀", "school_ids": ["s1"]}
        batch_id, _ = self._seed([("卷.pdf", PDF)], meta=meta,
                                 route={"text_layer": False})
        result = core_return.return_batch(batch_id)
        self.assertEqual(result["meta"], meta)
        self.assertIs(result["text_layer"], False)

    def test_text_layer_tri_state(self) -> None:
        for route, expected in (({"text_layer": True}, True), ({}, None)):
            with self.subTest(route=route):
                batch_id, _ = self._seed([("卷.pdf", PDF)], route=route)
                result = core_return.return_batch(batch_id)
                self.assertIs(result["text_layer"], expected)

    def test_discarded_and_kept_counts(self) -> None:
        batch_id, _ = self._seed([("卷.png", PNG)], pending=3, approved=2)
        result = core_return.return_batch(batch_id)
        self.assertEqual(result["discarded"], 3)
        self.assertEqual(result["kept"], 2)

    def test_multi_file_names_strip_stamp_prefix(self) -> None:
        batch_id, _ = self._seed([("甲卷.pdf", PDF), ("乙卷.png", PNG)])
        result = core_return.return_batch(batch_id)
        self.assertEqual([f["name"] for f in result["files"]], ["甲卷.pdf", "乙卷.png"])
        self.assertEqual(len(result["files"]), 2)

    def test_mime_sniffs_magic_not_extension(self) -> None:
        batch_id, _ = self._seed([("伪装.pdf", PNG), ("真卷.pdf", PDF)])
        result = core_return.return_batch(batch_id)
        self.assertTrue(result["files"][0]["data_url"].startswith("data:image/png;"))
        self.assertTrue(result["files"][1]["data_url"].startswith("data:application/pdf;"))

    def test_missing_source_is_loud_and_batch_survives(self) -> None:
        batch_id, paths = self._seed([("卷.png", PNG)])
        paths[0].unlink()
        with self.assertRaises(PendingError) as caught:
            core_return.return_batch(batch_id)
        self.assertIn("原卷文件不在了", str(caught.exception))
        con = connect()
        try:
            self.assertIsNotNone(con.execute(
                "SELECT 1 FROM batches WHERE batch_id = ?", (batch_id,)).fetchone())
        finally:
            con.close()

    def test_bad_id_and_unknown_batch(self) -> None:
        with self.assertRaises(PendingNotFound):
            core_return.return_batch("乱填")
        with self.assertRaises(PendingNotFound):
            core_return.return_batch("B-999")

    def test_delete_reuses_bank_batches_semantics(self) -> None:
        batch_id, _ = self._seed([("卷.png", PNG)])
        with mock.patch.object(core_return, "delete_batch",
                               wraps=bank_batches.delete_batch) as spy:
            core_return.return_batch(batch_id)
        spy.assert_called_once_with(batch_id)


class ReturnMetaReentryTest(_PendingIsolated):
    """打回重入（卡§2）：交回的元数据经 stage_ingest 原样落新批，占位题继承。"""

    def setUp(self) -> None:
        super().setUp()
        self._saved_ws = settings.workspace_id
        settings.workspace_id = None

    def tearDown(self) -> None:
        settings.workspace_id = self._saved_ws
        super().tearDown()

    def test_returned_meta_lands_on_new_batch_and_placeholder(self) -> None:
        from app.core.ingest import service as ingest
        from app.core.pending import service as pending_service
        from app.core.pending.batch.batches import batch_row, read_meta
        from app.core.pending.meta.rules import normalize_batch_meta

        meta = {"year": "2026", "subject": "数学", "grade": "九年级", "region": "海淀"}
        batch_id, _ = self._seed([("原卷.md", b"# 1. solve x")], meta=meta)
        returned = core_return.return_batch(batch_id)
        self.assertEqual(returned["meta"], meta)
        staged = ingest.stage_ingest([
            {"name": one["name"], "data_url": one["data_url"],
             "meta": returned["meta"]} for one in returned["files"]])
        new_id = staged["batch_id"]
        expected = normalize_batch_meta({}, meta)
        con = connect()
        try:
            self.assertEqual(read_meta(batch_row(con, new_id)), expected)
        finally:
            con.close()
        items = pending_service.list_batch_questions(new_id)["items"]
        self.assertEqual(len(items), 1)
        source = items[0]["question"]["source"]
        self.assertEqual(source["year"], 2026)
        self.assertEqual(source["region"], "海淀")

    def test_no_meta_keeps_old_behavior(self) -> None:
        from app.core.ingest import service as ingest
        from app.core.pending.batch.batches import batch_row, read_meta

        staged = ingest.stage_ingest([{"name": "白卷.md",
                                       "data_url": "data:text/markdown;base64,"
                                       + base64.b64encode(b"# 1. solve x").decode("ascii")}])
        con = connect()
        try:
            self.assertEqual(read_meta(batch_row(con, staged["batch_id"])), {})
        finally:
            con.close()


class ImageShellReentryTest(_PendingIsolated):
    """PNG 重入占位壳必须过质检落池（2.20.0 探针实证：pimg_*.png 当图 id 被契约拒，
    壳落不了池，识别根本开不了工）。不跑任何引擎，只到落池为止。"""

    def test_shell_passes_contract_and_lands_in_pool(self) -> None:
        from app.core.config import settings
        from app.core.ingest.service import _image_shell
        from app.core.pending import service
        saved_workspace = settings.workspace_id
        settings.workspace_id = None
        try:
            shell = _image_shell("探针纯图卷.png", [
                {"name": "pimg_bb98fdc551c56cfe.png",
                 "uri": "/static/pending/pimg_bb98fdc551c56cfe.png", "page": 1}])
            # 落池即扫的后台线程会按活环境串库（Windows 上攥着下一个用例的库文件）：
            # 与 test_page_render 同款打桩，线程体空转，不碰任何库。
            with mock.patch.object(service.dedupe, "warm_dedupe_scan"):
                result = service.save_draft([{"question": shell, "page_no": 1}],
                                            origin="probe.shell")
            self.assertEqual(len(result["saved_ids"]), 1)
        finally:
            settings.workspace_id = saved_workspace


class ApiShapeTest(unittest.IsolatedAsyncioTestCase):
    """HTTP 口子只做鉴权与形状校验；写令牌依赖由探针真服务器覆盖。"""

    async def test_bad_shapes_are_400(self) -> None:
        for payload in ([], {"batch_id": ""}, {"batch_id": "bad"}, {}):
            with self.subTest(payload=payload):
                with self.assertRaises(HTTPException) as caught:
                    await api.pending_return_batch(payload)
                self.assertEqual(caught.exception.status_code, 400)

    async def test_valid_payload_reaches_core(self) -> None:
        core = mock.Mock(return_value={"batch_id": "B-001", "files": []})
        with mock.patch.object(api.core_return, "return_batch", core):
            result = await api.pending_return_batch({"batch_id": "B-001"})
        self.assertEqual(result["batch_id"], "B-001")
        core.assert_called_once_with("B-001")

    async def test_not_found_is_404_and_domain_error_is_400(self) -> None:
        for exc, status in ((PendingNotFound("没有"), 404), (PendingError("缺副本"), 400)):
            with self.subTest(exc=exc):
                with mock.patch.object(api.core_return, "return_batch",
                                       side_effect=exc):
                    with self.assertRaises(HTTPException) as caught:
                        await api.pending_return_batch({"batch_id": "B-001"})
                self.assertEqual(caught.exception.status_code, status)


if __name__ == "__main__":
    unittest.main()