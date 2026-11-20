# -*- coding: utf-8 -*-
"""note-warn-merge 卡回归钉死（停链卡：生产代码零改，只钉语义）。

侦查定案见 docs/handoff/evidence/note-warn-merge/recon.md：卡面「dedupe 重写
route.note 冲掉剥图警告」的冲掉点不存在——dedupe 族零 route 写，LF 夹具的警告
全接线存活到池内 route.note；BDP-01 观察到的丢失真根因是 CRLF 行尾（警告根本没产）。
本模块钉死四条：
- LF 带卷首图夹具走全接线 ingest_files→落池→dedupe 后，note 含剥图警告且只一条；
- 无警告夹具 note 与现状逐字一致（干净文字批 note 为空串）；
- dedupe 抽走启用态：route 写盘只有一笔（save_route），警告不被第二笔重写；
- CRLF 现状 Canary：同文 CRLF 夹具今日不产警告（note 空）——治它须解冻
  shapes/text 解析段（另卡），届时本案变红是有意的：提醒更新钉死并对照回单。

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

    async def test_dedupe_enabled_single_route_write_keeps_warning(self) -> None:
        """抽走启用态：route 写盘只有一笔（save_route），dedupe 不重写 note。"""
        os.environ.pop("JZO_POOL_ADMIT_DISABLED", None)
        with mock.patch.object(pending, "set_batch_route",
                               wraps=pending.set_batch_route) as spy:
            batch_id = await self._ingest("lf_warn_dedupe.md", WARN_MD)
        self._join_dedupe()
        self.assertEqual(spy.call_count, 1, "ingest 全程 route 只该写一笔")
        self.assertIn(WARN_PHRASE, self._note(batch_id))

    async def test_crlf_current_behavior_canary(self) -> None:
        """现状 Canary（待另卡治）：CRLF 同文今日不产剥图警告，note 为空。

        根因：decode_text 不归一换行，shapes._IMAGE_LINE 行尾不认 \\r，图片行
        不剥不警告（随后被切段器静默丢掉）。修复须解冻 shapes/text 解析段；
        届时本案变红是有意钉死——更新它并对照 note-warn-merge 回单。
        """
        batch_id = await self._ingest("crlf_warn.md", WARN_MD.replace("\n", "\r\n"))
        self.assertEqual(self._note(batch_id), "")
        rows = pending.list_batch_questions(batch_id)
        self.assertEqual(len(rows["items"]), 1, "CRLF 下题目本身仍拆得出")


if __name__ == "__main__":
    unittest.main()