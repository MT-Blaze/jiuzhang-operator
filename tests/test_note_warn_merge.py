# -*- coding: utf-8 -*-
"""note-warn-merge 卡回归钉死＋CRLF 归一卡⑤转正。

侦查定案见 docs/handoff/evidence/note-warn-merge/recon.md：卡面「dedupe 重写
route.note 冲掉剥图警告」的冲掉点不存在——dedupe 族零 route 写，LF 夹具的警告
全接线存活到池内 route.note；BDP-01 观察到的丢失真根因是 CRLF 行尾（警告根本没产）。
本模块钉死：
- LF 带卷首图夹具走全接线 ingest_files→落池→dedupe 后，note 含剥图警告且只一条；
- 无警告夹具 note 与现状逐字一致（干净文字批 note 为空串）；
- dedupe 抽走启用态：route 写盘全经 save_route（过程流水多笔），dedupe 零直写，警告不丢；
- CRLF 转正（卡⑤ decode_text 归一后）：CRLF 也剥也警告，且与 LF 同文逐字同语义；
- 老 Mac lone \\r 行尾同样剥图警告。

运行：``.venv/Scripts/python.exe -m unittest tests.test_note_warn_merge``
"""

from __future__ import annotations

import base64
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import config  # noqa: E402
from app.core.ingest import service as ingest  # noqa: E402
from app.core.ingest.intake.text import decode_text  # noqa: E402
from app.core.pending import service as pending  # noqa: E402
from tests.catalog_fixture import write_catalog_plugin  # noqa: E402

WARN_MD = (
    "![](images/header_photo.jpg)\n"
    "\n"
    "10. 已知集合 $A=\\{x \\mid 0<x<a\\}$，则下列结论正确的是（ ）\n"
    "\n"
    "A. $a>0$ B. $a<0$ C. $a=0$ D. 无法确定\n"
)
PLAIN_MD = "1. 求 $x+1=2$ 的解。\n"
WARN_PHRASE = "题干图片行已剥离"


def _url(text: str) -> str:
    return "data:text/markdown;base64," + base64.b64encode(
        text.encode("utf-8")).decode("ascii")


class _Isolated(unittest.IsolatedAsyncioTestCase):
    """临时 data/＋plugins/＋最小目录夹具插件：不碰老师真实工作区一个字节。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = Path(self.tmp.name)
        self.plugins_dir = base / "plugins"
        self.plugins_dir.mkdir()
        self.data_dir = base / "data"
        self._saved = {key: os.environ.get(key) for key in
                       ("JZO_DATA_DIR", "JZO_PLUGINS_DIR",
                        "JZO_POOL_ADMIT_DISABLED", "JZO_RESTART_DISABLED")}
        self._saved_ws = config.settings.workspace_id
        os.environ["JZO_DATA_DIR"] = str(self.data_dir)
        os.environ["JZO_PLUGINS_DIR"] = str(self.plugins_dir)
        os.environ["JZO_POOL_ADMIT_DISABLED"] = "1"
        os.environ["JZO_RESTART_DISABLED"] = "1"
        config.settings.workspace_id = None
        write_catalog_plugin(self.plugins_dir)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        config.settings.workspace_id = self._saved_ws
        self.tmp.cleanup()

    @staticmethod
    def _join_dedupe() -> None:
        for thread in threading.enumerate():
            if thread.name.startswith("jzo-dedupe-warm"):
                thread.join(timeout=10)

    async def _ingest(self, name: str, text: str) -> str:
        result = await ingest.ingest_files([{"name": name, "data_url": _url(text)}])
        self._join_dedupe()
        return result["batch_ids"][0]

    def _note(self, batch_id: str) -> str:
        rows = pending.list_batch_questions(batch_id)
        return str((rows.get("route") or {}).get("note") or "")


class NoteWarnMergeTest(_Isolated):
    async def test_lf_header_image_warning_survives_full_wiring(self) -> None:
        """带卷首图 LF 夹具：全接线落池＋dedupe 后 note 含剥图警告，只一条。"""
        batch_id = await self._ingest("lf_warn.md", WARN_MD)
        note = self._note(batch_id)
        self.assertIn(WARN_PHRASE, note)
        self.assertIn("images/header_photo.jpg", note)
        self.assertEqual(note.count(WARN_PHRASE), 1, "一条图片行只该有一条警告")
        rows = pending.list_batch_questions(batch_id)
        self.assertEqual(len(rows["items"]), 1)
        stem = str(rows["items"][0]["question"].get("stem") or "")
        self.assertTrue(stem.lstrip().startswith("10."), "题号仍由题干头号承载")
        self.assertNotIn("![](images/header_photo.jpg)", stem, "图片行已剥不入题干")

    async def test_no_warning_note_verbatim(self) -> None:
        """无警告夹具：note 与现状逐字一致（干净文字批为空串，不多一字）。"""
        batch_id = await self._ingest("lf_plain.md", PLAIN_MD)
        self.assertEqual(self._note(batch_id), "")
        rows = pending.list_batch_questions(batch_id)
        self.assertEqual(len(rows["items"]), 1)

    async def test_dedupe_enabled_route_writes_keep_warning(self) -> None:
        """抽走启用态：过程流水多笔落盘但全经 save_route，dedupe 零直写，警告不丢。"""
        os.environ.pop("JZO_POOL_ADMIT_DISABLED", None)
        with mock.patch.object(pending, "set_batch_route",
                               wraps=pending.set_batch_route) as spy_set, \
                mock.patch.object(ingest, "save_route",
                                  wraps=ingest.save_route) as spy_save:
            batch_id = await self._ingest("lf_warn_dedupe.md", WARN_MD)
        self._join_dedupe()
        self.assertGreaterEqual(spy_save.call_count, 1, "过程流水至少要落一笔")
        self.assertEqual(spy_set.call_count, spy_save.call_count,
                         "route 写盘只许经 save_route，dedupe 不许直写")
        note = self._note(batch_id)
        self.assertIn(WARN_PHRASE, note)
        self.assertEqual(note.count(WARN_PHRASE), 1, "多笔落盘不许把警告写成两条")

    async def test_crlf_header_image_warning_normalized(self) -> None:
        """CRLF 转正（卡⑤）：decode_text 归一后 CRLF 也剥图也警告，只一条。

        原为现状 Canary（CRLF 不产警告）；decode_text 单源归一 CRLF→LF 后
        本案按卡文改断言转正，对照 note-warn-merge 与 crlf-normalize 回单。
        """
        batch_id = await self._ingest("crlf_warn.md", WARN_MD.replace("\n", "\r\n"))
        note = self._note(batch_id)
        self.assertIn(WARN_PHRASE, note)
        self.assertIn("images/header_photo.jpg", note)
        self.assertEqual(note.count(WARN_PHRASE), 1, "一条图片行只该有一条警告")
        rows = pending.list_batch_questions(batch_id)
        self.assertEqual(len(rows["items"]), 1)
        stem = str(rows["items"][0]["question"].get("stem") or "")
        self.assertTrue(stem.lstrip().startswith("10."), "题号仍由题干头号承载")
        self.assertNotIn("![](images/header_photo.jpg)", stem, "图片行已剥不入题干")

    async def test_crlf_lf_same_semantics_verbatim(self) -> None:
        """归一后 CRLF/LF 同语义：同名夹具 note 与题目文档（除 id）逐字一致。"""
        lf_id = await self._ingest("parity.md", WARN_MD)
        crlf_id = await self._ingest("parity.md", WARN_MD.replace("\n", "\r\n"))
        self.assertEqual(self._note(lf_id), self._note(crlf_id))
        lf_rows = pending.list_batch_questions(lf_id)
        crlf_rows = pending.list_batch_questions(crlf_id)
        self.assertEqual(len(lf_rows["items"]), len(crlf_rows["items"]))
        for lf_row, crlf_row in zip(lf_rows["items"], crlf_rows["items"]):
            lf_q = {k: v for k, v in lf_row["question"].items() if k != "id"}
            crlf_q = {k: v for k, v in crlf_row["question"].items() if k != "id"}
            self.assertEqual(lf_q, crlf_q, "归一后 CRLF 与 LF 题目文档须逐字一致")

    async def test_lone_cr_old_mac_header_image_warning(self) -> None:
        """老 Mac lone \\r 行尾：同样剥图警告，题目与 LF 对照同语义。"""
        batch_id = await self._ingest("cr_warn.md", WARN_MD.replace("\n", "\r"))
        note = self._note(batch_id)
        self.assertIn(WARN_PHRASE, note)
        self.assertEqual(note.count(WARN_PHRASE), 1)
        rows = pending.list_batch_questions(batch_id)
        self.assertEqual(len(rows["items"]), 1)
        stem = str(rows["items"][0]["question"].get("stem") or "")
        self.assertTrue(stem.lstrip().startswith("10."))
        self.assertNotIn("![](images/header_photo.jpg)", stem)

    async def test_crlf_plain_note_still_empty(self) -> None:
        """无警告夹具 CRLF 版：归一不产多余警告，note 仍为空串。"""
        batch_id = await self._ingest("crlf_plain.md", PLAIN_MD.replace("\n", "\r\n"))
        self.assertEqual(self._note(batch_id), "")
        rows = pending.list_batch_questions(batch_id)
        self.assertEqual(len(rows["items"]), 1)


class DecodeTextNormalizeTest(unittest.TestCase):
    """decode_text 单源归一钉死：LF 逐字不变，编码兜底顺序不变。"""

    def test_lf_verbatim_unchanged(self) -> None:
        self.assertEqual(decode_text(WARN_MD.encode("utf-8")), WARN_MD)
        self.assertEqual(decode_text("纯中文 $x+1=2$\n".encode("utf-8")),
                         "纯中文 $x+1=2$\n")

    def test_crlf_and_lone_cr_to_lf(self) -> None:
        self.assertEqual(decode_text(WARN_MD.replace("\n", "\r\n").encode("utf-8")),
                         WARN_MD)
        self.assertEqual(decode_text(WARN_MD.replace("\n", "\r").encode("utf-8")),
                         WARN_MD)
        self.assertEqual(decode_text(b"a\r\nb\rc\n"), "a\nb\nc\n")

    def test_encoding_fallback_order_unchanged(self) -> None:
        gbk = "1. 求 $x+1=2$ 的解。\r\n".encode("gb18030")
        self.assertEqual(decode_text(gbk), "1. 求 $x+1=2$ 的解。\n")
        # utf-8 优先：BOM 被解成 \ufeff 字符是现状口径，归一只动换行不动它。
        bom = "1. 求 $x+1=2$ 的解。\r\n".encode("utf-8-sig")
        self.assertEqual(decode_text(bom), "\ufeff1. 求 $x+1=2$ 的解。\n")


if __name__ == "__main__":
    unittest.main()