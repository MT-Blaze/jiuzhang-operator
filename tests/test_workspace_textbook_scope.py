"""工作区教材版本偏好 → 大纲树生效版本 的解析契约。

为什么单独钉这一层：``POST /api/workspaces/textbook`` 只登记偏好，真正决定「树看哪一版」
的是活跃工作区 + 题库默认版本的回退链。偏好缺失、指向已不存在的版本、老库没有
``textbooks`` 表，都必须有确定行为，不能让树静默显示另一个版本。

运行：``.venv/Scripts/python.exe -m unittest tests.test_workspace_textbook_scope``
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.api import workspaces
from app.core import bank
from app.core.config import settings

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "org.jiuzhang.core-bank"
TB_A = "tb_aaaaaaaa"
TB_B = "tb_bbbbbbbb"


class ActiveTextbookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (settings.workspace_id, os.environ.get("JZO_DATA_DIR"),
                       os.environ.get("JZO_PLUGINS_DIR"))
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        settings.workspace_id = "ws_probe"
        self.addCleanup(self._restore)

        bank.init_bank(PLUGIN_ID)
        now = "2026-10-24T00:00:00+08:00"
        con = sqlite3.connect(Path(self.tmp.name) / "workspaces" / "ws_probe"
                              / "banks" / f"{PLUGIN_ID}.db")
        try:
            con.executemany(
                "INSERT INTO textbooks (id, name, publisher, edition, is_default, created_at, updated_at)"
                " VALUES (?, ?, '', '', ?, ?, ?)",
                [(TB_A, "人教A版", 1, now, now), (TB_B, "苏教版", 0, now, now)],
            )
            con.commit()
        finally:
            con.close()
        self.registry = Path(self.tmp.name) / "workspaces.json"
        self._write_registry("")

    def _restore(self) -> None:
        workspace_id, data_dir, plugins = self._saved
        settings.workspace_id = workspace_id
        for key, value in (("JZO_DATA_DIR", data_dir), ("JZO_PLUGINS_DIR", plugins)):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _write_registry(self, textbook_id: str) -> None:
        self.registry.write_text(json.dumps([
            {"id": "default", "name": "默认工作区", "created_at": "system"},
            {"id": "ws_probe", "name": "探针工作区", "created_at": "auto",
             "textbook_id": textbook_id},
        ], ensure_ascii=False), encoding="utf-8")

    def test_01_workspace_choice_wins(self) -> None:
        self._write_registry(TB_B)
        self.assertEqual(workspaces.active_textbook_id(PLUGIN_ID), TB_B)

    def test_02_missing_choice_falls_back_to_library_default(self) -> None:
        self._write_registry("")
        self.assertEqual(workspaces.active_textbook_id(PLUGIN_ID), TB_A)

    def test_03_stale_choice_falls_back_to_library_default(self) -> None:
        self._write_registry("tb_ffffffff")
        self.assertEqual(workspaces.active_textbook_id(PLUGIN_ID), TB_A,
                         "登记了库里不存在的版本时必须回落默认，不能把树清空")


if __name__ == "__main__":
    unittest.main()
