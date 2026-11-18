"""ingest 失败显性化判据（2026-11-18 卡）：静默失败必须开口。

钉住六条：
- 壳题落池失败（service.py 原 :346）与整份落池失败（原 :373）：保批保卷行为
  一字不改（占位留、资产 drop 照旧），但 failures 必须有条目——人话 reason、
  完整 detail、retryable 表态；质检拒收有固定口径。
- 单份解析失败（原 :298）同样要开口，占位题照留。
- auto_split_pages 的失败 notes（原 :324 直接丢弃）不再丢：挂进 failures/progress。
- progress 是环形缓冲：上限 40 条、seq 单调递增；failures 按 file+step 去重。
- note 语义不动：成功批次不带 failures 键，过程流水照写。
- 识别调度员用全新快照重写 route 时，已落盘的 failures/progress 不丢。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ingest_failure_surface``
"""

from __future__ import annotations

import base64
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import config  # noqa: E402
from app.core.bank import questions  # noqa: E402
from app.core.ingest import route as ingest_route  # noqa: E402
from app.core.ingest import service as ingest  # noqa: E402
from app.core.pending import service  # noqa: E402
from app.core.pending import assets as pending_assets  # noqa: E402


def _data_url(text: str) -> str:
    return "data:text/markdown;base64," + base64.b64encode(
        text.encode("utf-8")).decode("ascii")


def _pages_with_regions() -> list[dict[str, Any]]:
    return [{
        "name": "pimg_0123456789abcdef.png",
        "uri": "/static/pending/pimg_0123456789abcdef.png",
        "page": 1, "width": 1000, "height": 1400,
        "regions": [{"no": 1, "x": 10, "y": 10, "w": 400, "h": 200}],
    }]


class _Isolated(unittest.IsolatedAsyncioTestCase):
    """临时数据目录：不碰老师真实工作区的一个字节。"""

    def setUp(self) -> None:
        # 落池即扫的后台线程可能还握着库文件：清理容错，不让收尾噪声盖过判据。
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._saved_env = os.environ.get("JZO_DATA_DIR")
        self._saved_ws = config.settings.workspace_id
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        config.settings.workspace_id = None
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._saved_env is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = self._saved_env
        config.settings.workspace_id = self._saved_ws
        self.tmp.cleanup()

    def _route(self, batch_id: str) -> dict[str, Any]:
        return service.read_batch_route(batch_id)

    def _placeholder_batch(self, name: str) -> tuple[str, str]:
        result = service.save_draft(
            [{"question": ingest._placeholder(f"（正在解析：{name}）")}],
            source_name=name, origin="ingest")
        return result["batch_id"], result["saved_ids"][0]


class SaveFailureSurfaceTest(_Isolated):
    async def test_shell_save_rejection_keeps_paper_and_speaks(self) -> None:
        """图片壳题落池被质检拒收：卷子留着、资产照 drop，成因必须落盘。"""
        batch_id, pending_id = self._placeholder_batch("拍照卷.png")
        pages = _pages_with_regions()
        error = questions.QuestionValidationError(["stem: 必填字段缺失"])
        with mock.patch.object(ingest.page_render, "build_pages",
                               return_value=(pages, [1], [])), \
                mock.patch.object(service, "save_draft", side_effect=error), \
                mock.patch.object(pending_assets, "drop_assets") as drop:
            await ingest.run_ingest_jobs(batch_id, [{
                "pending_id": pending_id, "name": "拍照卷.png",
                "data": b"\x89PNG-fake", "page_only": False,
            }])
        route = self._route(batch_id)
        failures = route.get("failures") or []
        self.assertEqual(len(failures), 1, "拒收必须留一条成因")
        entry = failures[0]
        self.assertEqual(entry["file"], "拍照卷.png")
        self.assertEqual(entry["step"], "落池")
        self.assertIn("题目质检", entry["reason"])
        self.assertIn("已留占位", entry["reason"])
        self.assertIn("stem: 必填字段缺失", entry["detail"],
                      "detail 要放 ValidationError 原文")
        self.assertTrue(entry["retryable"])
        drop.assert_called_once_with(pages)
        items = service.list_batch_questions(batch_id)["items"]
        self.assertEqual(len(items), 1, "占位题必须留着，卷子不能丢")
        self.assertIn("正在解析", items[0]["question"]["stem"])
        self.assertTrue(any(row["level"] == "error"
                            for row in route.get("progress") or []))

    async def test_items_save_failure_keeps_placeholder_and_speaks(self) -> None:
        """整份落池失败：占位留、资产 drop 照旧，failures 带兜底人话与堆栈现场。"""
        batch_id, pending_id = self._placeholder_batch("卷子.md")
        with mock.patch.object(ingest.page_render, "build_pages",
                               return_value=([], [], [])), \
                mock.patch.object(service, "save_draft",
                                  side_effect=RuntimeError("池子满了")) as save, \
                mock.patch.object(pending_assets, "drop_assets") as drop:
            await ingest.run_ingest_jobs(batch_id, [{
                "pending_id": pending_id, "name": "卷子.md",
                "data": "1. 求 $x+1=2$ 的解。".encode("utf-8"),
                "page_only": False,
            }])
        self.assertTrue(save.called)
        route = self._route(batch_id)
        failures = route.get("failures") or []
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["step"], "落池")
        self.assertIn("写不进待审池", failures[0]["reason"])
        self.assertIn("池子满了", failures[0]["detail"])
        self.assertIn("RuntimeError", failures[0]["detail"])
        self.assertTrue(failures[0]["retryable"])
        drop.assert_not_called()  # 文本卷没有页图资产，无资产可 drop
        items = service.list_batch_questions(batch_id)["items"]
        self.assertEqual(len(items), 1)
        self.assertIn("正在解析", items[0]["question"]["stem"])

    async def test_parse_failure_surfaces_and_keeps_placeholder(self) -> None:
        """单份解析炸了也要开口：占位照留，failures 记解析这一步。"""
        batch_id, pending_id = self._placeholder_batch("坏卷.docx")
        with mock.patch.object(ingest, "_items_from_file",
                               new=mock.AsyncMock(side_effect=ValueError("解不开"))), \
                mock.patch.object(ingest.page_render, "build_pages",
                                  return_value=([], [], [])):
            await ingest.run_ingest_jobs(batch_id, [{
                "pending_id": pending_id, "name": "坏卷.docx",
                "data": b"PK", "page_only": False,
            }])
        route = self._route(batch_id)
        failures = route.get("failures") or []
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["step"], "解析")
        self.assertIn("没解析开", failures[0]["reason"])
        self.assertIn("解不开", failures[0]["detail"])
        items = service.list_batch_questions(batch_id)["items"]
        self.assertEqual(len(items), 1, "解析失败仍留待识别占位")
        self.assertIn("待识别", items[0]["question"]["stem"])


class AutoSplitNotesSurfaceTest(_Isolated):
    async def test_split_notes_are_no_longer_dropped(self) -> None:
        """auto_split 返回的失败 notes 必须挂进 failures/progress，不再丢。"""
        created = service.create_batch(source_name="扫描卷.pdf", scan=True)
        batch_id = created["batch_id"]
        pages = _pages_with_regions()
        with mock.patch.object(ingest.page_render, "build_pages",
                               return_value=(pages, [1], [])), \
                mock.patch.object(ingest.page_render, "pdf_text_health",
                                  return_value={"has_text_layer": False,
                                                  "garbled": False,
                                                  "text_chars": 0,
                                                  "missing_chars": 0}), \
                mock.patch.object(ingest.layout_router, "run",
                                  new=mock.AsyncMock(return_value={"pages": {}})), \
                mock.patch.object(ingest.page_render, "crop_pdf_regions",
                                  return_value=({}, ["没有渲染器"])):
            await ingest.run_ingest_jobs(batch_id, [{
                "pending_id": "", "name": "扫描卷.pdf",
                "data": b"%PDF", "page_only": True,
            }])
        route = self._route(batch_id)
        failures = route.get("failures") or []
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["step"], "自动切题")
        self.assertIn("没有渲染器", failures[0]["reason"])
        self.assertIn("没有渲染器", failures[0]["detail"])
        self.assertTrue(any("没有渲染器" in row["text"]
                            for row in route.get("progress") or []))
        kept_pages = service.list_batch_questions(batch_id)["page_images"]
        self.assertEqual(len(kept_pages), 1, "页图与绿框照旧可用")
        self.assertEqual(kept_pages[0]["name"], "pimg_0123456789abcdef.png")
        self.assertTrue(kept_pages[0].get("regions"), "题块坐标不许丢")

    async def test_split_pool_failure_note_surfaces(self) -> None:
        """裁图成功但落池失败的那条 note 同样不许丢。"""
        created = service.create_batch(source_name="扫描卷2.pdf", scan=True)
        batch_id = created["batch_id"]
        pages = _pages_with_regions()
        crops = {1: [{"index": 0, "no": 1, "region": pages[0]["regions"][0],
                      "png": b"\x89PNG", "width": 10, "height": 10}]}
        with mock.patch.object(ingest.page_render, "build_pages",
                               return_value=(pages, [1], [])), \
                mock.patch.object(ingest.page_render, "pdf_text_health",
                                  return_value={"has_text_layer": False,
                                                  "garbled": False,
                                                  "text_chars": 0,
                                                  "missing_chars": 0}), \
                mock.patch.object(ingest.layout_router, "run",
                                  new=mock.AsyncMock(return_value={"pages": {}})), \
                mock.patch.object(ingest.page_render, "crop_pdf_regions",
                                  return_value=(crops, [])), \
                mock.patch.object(service, "save_draft",
                                  side_effect=RuntimeError("池子满了")):
            await ingest.run_ingest_jobs(batch_id, [{
                "pending_id": "", "name": "扫描卷2.pdf",
                "data": b"%PDF", "page_only": True,
            }])
        route = self._route(batch_id)
        failures = route.get("failures") or []
        self.assertEqual(len(failures), 1)
        self.assertIn("自动切图落池失败", failures[0]["reason"])
        self.assertIn("池子满了", failures[0]["detail"])


class LedgerShapeTest(unittest.TestCase):
    def test_progress_ring_buffer_caps_at_40(self) -> None:
        ledger = ingest_route.new_ledger()
        for index in range(60):
            ingest_route.ledger_progress(ledger, f"第 {index} 步")
        self.assertEqual(len(ledger["progress"]), 40)
        self.assertEqual(ledger["progress"][0]["seq"], 21)
        self.assertEqual(ledger["progress"][-1]["seq"], 60)
        self.assertEqual(ledger["progress"][-1]["text"], "第 59 步")

    def test_failures_dedupe_by_file_and_step(self) -> None:
        ledger = ingest_route.new_ledger()
        for _ in range(3):
            ingest_route.ledger_failure(
                ledger, file="a.pdf", page_no=1, step="落池",
                reason="同一处失败", detail="原文")
        self.assertEqual(len(ledger["failures"]), 1)
        ingest_route.ledger_failure(
            ledger, file="a.pdf", page_no=2, step="解析",
            reason="另一步失败", detail="原文")
        self.assertEqual(len(ledger["failures"]), 2)

    def test_attach_surface_leaves_success_route_clean(self) -> None:
        ledger = ingest_route.new_ledger()
        route = ingest_route.attach_surface({"note": "原话"}, ledger)
        self.assertNotIn("failures", route)
        self.assertNotIn("progress", route)
        self.assertEqual(route["note"], "原话")


class SurfacePersistenceTest(_Isolated):
    async def test_snapshot_rewrite_does_not_drop_surface(self) -> None:
        """识别调度员的全新 route 快照不带两键时，库里旧账必须保全。"""
        created = service.create_batch(source_name="保全.pdf", scan=True)
        batch_id = created["batch_id"]
        ledger = ingest_route.new_ledger()
        ingest_route.ledger_failure(
            ledger, file="保全.pdf", page_no=1, step="落池",
            reason="质检拒收", detail="原文")
        ingest_route.ledger_progress(ledger, "第一步完成")
        ingest_route.save_route(
            service, batch_id, ingest_route.attach_surface({"note": "甲"}, ledger))
        # 模拟 fill_batch 中途快照：全新 dict，只有 note，没有两键。
        ingest_route.save_route(service, batch_id, {"note": "乙", "phase": "done"})
        route = self._route(batch_id)
        self.assertEqual(route["note"], "乙", "note 语义照旧由最新快照说了算")
        self.assertEqual(len(route.get("failures") or []), 1)
        self.assertEqual(len(route.get("progress") or []), 2)

    async def test_success_text_ingest_keeps_note_and_writes_progress(self) -> None:
        """成功卷：note 语义不动、不挂 failures，过程流水有绿字落池行。"""
        staged = ingest.stage_ingest([{
            "name": "成功卷.md",
            "data_url": _data_url("1. 求 $x+1=2$ 的解。\n2. 求 $x-1=0$ 的解。"),
        }])
        group = staged["jobs"][0]
        await ingest.run_ingest_jobs(group["batch_id"], group["jobs"])
        route = self._route(group["batch_id"])
        self.assertNotIn("failures", route, "成功批次不许挂失败痕")
        self.assertEqual(route.get("note", ""), "",
                         "普通文本卷的 note 语义保持原样（空）")
        self.assertEqual(route.get("channel"), "text")
        progress = route.get("progress") or []
        self.assertTrue(progress, "成功步骤也要写过程流水")
        self.assertTrue(any(row["level"] == "ok" and "落池完成" in row["text"]
                            for row in progress))
        seqs = [row["seq"] for row in progress]
        self.assertEqual(seqs, sorted(seqs), "seq 必须单调递增")


if __name__ == "__main__":
    unittest.main()