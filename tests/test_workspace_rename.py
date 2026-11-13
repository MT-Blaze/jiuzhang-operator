"""工作区重命名契约（2026-11-13）：只改展示名、写操作必须带令牌。

左栏底部工作区弹窗的第三块是【重命名当前工作区】。名称只是登记表里的展示字段，
目录、题库、插件状态都以 ``id`` 为身份，因此重命名不重启底座、不碰数据目录；
但它是写操作，必须挂 ``require_write_token``。

运行：``.venv/Scripts/python.exe -m unittest tests.test_workspace_rename``
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from app.api import workspace_rename
from app.core import toml_io
from app.core.config import settings
from app.core.security import require_write_token

WS_ID = "ws_abcdef0123456789"


class WorkspaceRenameTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self._saved = (settings.workspace_id, os.environ.get("JZO_DATA_DIR"))
        os.environ["JZO_DATA_DIR"] = str(self.root)
        settings.workspace_id = None
        self.addCleanup(self._restore)
        (self.root / "workspaces.toml").write_text(
            toml_io.dumps({"workspaces": [
                {"id": "default", "name": "默认工作区", "created_at": "system"},
                {"id": WS_ID, "name": "旧名字", "created_at": "auto"},
            ]}),
            encoding="utf-8",
        )

    def _restore(self) -> None:
        workspace_id, data_dir = self._saved
        settings.workspace_id = workspace_id
        if data_dir is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = data_dir

    def _rename(self, name: str, workspace_id: str = WS_ID) -> dict:
        return asyncio.run(
            workspace_rename.rename_workspace(
                workspace_rename.WorkspaceRenameRequest(workspace_id=workspace_id, name=name)
            )
        )

    def _names(self) -> dict[str, str]:
        rows = toml_io.load(self.root / "workspaces.toml").get("workspaces", [])
        return {row["id"]: row["name"] for row in rows}

    def test_01_rename_updates_registry_without_touching_dirs(self) -> None:
        result = self._rename("  高二备课  ")
        self.assertEqual(result["name"], "高二备课")
        self.assertEqual(result["workspace_id"], WS_ID)
        self.assertEqual(self._names()[WS_ID], "高二备课")
        self.assertEqual(self._names()["default"], "默认工作区")
        self.assertFalse((self.root / "workspaces" / WS_ID).exists(),
                         "重命名不该创建或改写工作区目录")

    def test_02_active_flag_follows_current_pointer(self) -> None:
        settings.workspace_id = WS_ID
        self.assertTrue(self._rename("当前区")["is_active"])
        settings.workspace_id = None
        self.assertFalse(self._rename("非当前区")["is_active"])

    def test_03_blank_name_is_rejected(self) -> None:
        # 纯空白能过模型层的 min_length，必须由端点 strip 后再挡一次。
        for blank in ("   ", "\t\n", " \u3000 "):
            with self.assertRaises(HTTPException) as caught:
                self._rename(blank)
            self.assertEqual(caught.exception.status_code, 400)
        # 空串直接过不了 Pydantic 的 min_length=1（API 层返回 422）。
        with self.assertRaises(ValueError):
            workspace_rename.WorkspaceRenameRequest(workspace_id=WS_ID, name="")
        self.assertEqual(self._names()[WS_ID], "旧名字")

    def test_04_unknown_workspace_is_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            self._rename("新名", "ws_0000000000000000")
        self.assertEqual(caught.exception.status_code, 404)

    def test_05_route_requires_write_token(self) -> None:
        route = next(
            item for item in workspace_rename.router.routes
            if getattr(item, "path", "") == "/api/workspaces/rename"
        )
        self.assertIn(require_write_token, [dep.dependency for dep in route.dependencies])

    def test_06_sidebar_modal_has_three_sections_under_the_footer_entry(self) -> None:
        static = Path(__file__).resolve().parents[1] / "static"
        html = (static / "workspace.html").read_text(encoding="utf-8")
        script = (static / "js" / "ws_users.js").read_text(encoding="utf-8")
        for token in (
            'id="wsWorkspaceBtn"',
            'id="wsWorkspaceModal"',
            "切换工作区",
            "新建工作区",
            "重命名当前工作区",
            'id="wsWorkspaceRenameForm"',
        ):
            self.assertIn(token, html)
        self.assertIn('"/api/workspaces/rename"', script)
        self.assertIn("paintWorkspace", script)
        self.assertNotIn("wsUserSwitchBtn", html, "顶部用户大卡必须已退役")


if __name__ == "__main__":
    unittest.main()
