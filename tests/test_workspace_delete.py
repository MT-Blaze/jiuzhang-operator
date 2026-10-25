"""工作区删除兜底：红字确认、路径防穿越、系统回收站与审计日志（军令 #17 第五步）。

删除是数据安全最后一道闸：服务端必须再验一次确认语；目录整体走回收站，
绝不 ``unlink`` / ``rmtree``；每次操作留审计。单测把回收站调用替换成 mock，
验证「传给系统回收站的路径」正好是工作区目录，且审计字段齐全。

运行：``.venv/Scripts/python.exe -m unittest tests.test_workspace_delete``
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from app.api import workspaces
from app.core import workspace_removal
from app.core.config import settings

WS_ID = "ws_abcdef0123456789"


class WorkspaceDeleteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self._saved = (settings.workspace_id, os.environ.get("JZO_DATA_DIR"))
        os.environ["JZO_DATA_DIR"] = str(self.root)
        settings.workspace_id = None
        self.addCleanup(self._restore)

        self.ws_dir = self.root / "workspaces" / WS_ID
        (self.ws_dir / "banks").mkdir(parents=True)
        (self.ws_dir / "banks" / "org.jiuzhang.bank-engine.db").write_bytes(b"SQLite format 3\0")
        (self.ws_dir / "uploads").mkdir()
        (self.ws_dir / "uploads" / "pic.png").write_bytes(b"PNG")
        (self.ws_dir / "config.json").write_text('{"ok":true}', encoding="utf-8")
        self._write_registry([
            {"id": "default", "name": "默认工作区", "created_at": "system"},
            {"id": WS_ID, "name": "待删工作区", "created_at": "auto"},
        ])

    def _restore(self) -> None:
        workspace_id, data_dir = self._saved
        settings.workspace_id = workspace_id
        if data_dir is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = data_dir

    def _write_registry(self, entries: list[dict]) -> None:
        (self.root / "workspaces.json").write_text(
            json.dumps(entries, ensure_ascii=False), encoding="utf-8"
        )

    def _registry_ids(self) -> list[str]:
        path = self.root / "workspaces.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return [entry["id"] for entry in data]

    def _delete(self, confirm: str = "确认删除") -> dict:
        return asyncio.run(
            workspaces.delete_workspace(
                WS_ID, workspaces.WorkspaceDeleteRequest(confirm=confirm)
            )
        )

    def _fake_recycle(self, path: Path) -> None:
        self.recycled.append(path)
        shutil.rmtree(path)

    def test_01_wrong_confirm_is_intercepted(self) -> None:
        with mock.patch.object(workspace_removal, "send_to_recycle_bin") as recycle:
            for wrong in ("", "确认", "确认删除 "):
                with self.assertRaises(HTTPException) as caught:
                    self._delete(wrong)
                self.assertEqual(caught.exception.status_code, 400)
            recycle.assert_not_called()
        self.assertTrue(self.ws_dir.is_dir())
        self.assertIn(WS_ID, self._registry_ids())
        self.assertFalse((self.root / "deletion_audit.json").exists())

    def test_02_recycle_receives_exact_workspace_dir_and_audits(self) -> None:
        self.recycled: list[Path] = []
        with mock.patch.object(
            workspace_removal, "send_to_recycle_bin", side_effect=self._fake_recycle
        ) as recycle:
            result = self._delete()
        recycle.assert_called_once()
        recycled_path = recycle.call_args.args[0]
        self.assertEqual(recycled_path, self.ws_dir.resolve())
        self.assertFalse(self.ws_dir.exists())
        self.assertNotIn(WS_ID, self._registry_ids())
        self.assertIn("default", self._registry_ids())

        audit = json.loads((self.root / "deletion_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(len(audit), 1)
        record = audit[0]
        self.assertEqual(record["workspace_id"], WS_ID)
        self.assertEqual(record["path"], str(self.ws_dir.resolve()))
        self.assertEqual(record["result"], "success")
        self.assertTrue(record["time"])
        self.assertEqual(result["deleted"], WS_ID)
        self.assertTrue(Path(result["audit"]).is_file())

    def test_03_recycle_failure_keeps_workspace_and_audits_failure(self) -> None:
        with mock.patch.object(
            workspace_removal,
            "send_to_recycle_bin",
            side_effect=workspace_removal.WorkspaceRemovalError("回收站拒绝"),
        ):
            with self.assertRaises(HTTPException) as caught:
                self._delete()
        self.assertEqual(caught.exception.status_code, 400)
        self.assertTrue(self.ws_dir.is_dir())
        self.assertIn(WS_ID, self._registry_ids())
        audit = json.loads((self.root / "deletion_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(audit[-1]["result"], "failed")
        self.assertIn("回收站拒绝", audit[-1]["detail"])

    def test_04_path_traversal_and_foreign_ids_are_rejected(self) -> None:
        for bad in (
            "../default",
            WS_ID + "/../../default",
            "ws_../ws_abcdef0123456789",
            "default",
            "",
            "ws_ABCDEF0123456789",
        ):
            with self.assertRaises(workspace_removal.WorkspaceRemovalError):
                workspace_removal.workspace_path(bad)
        # 默认工作区所在根目录绝不能被当成工作区目录
        with self.assertRaises(workspace_removal.WorkspaceRemovalError):
            workspace_removal.workspace_path("ws_abcdef0123456789" + "/..")
        with self.assertRaises(HTTPException):
            asyncio.run(
                workspaces.delete_workspace(
                    "default", workspaces.WorkspaceDeleteRequest(confirm="确认删除")
                )
            )

    def test_05_active_workspace_cannot_be_deleted(self) -> None:
        settings.workspace_id = WS_ID
        with mock.patch.object(workspace_removal, "send_to_recycle_bin") as recycle:
            with self.assertRaises(HTTPException) as caught:
                self._delete()
            recycle.assert_not_called()
        self.assertEqual(caught.exception.status_code, 400)
        self.assertTrue(self.ws_dir.is_dir())

    def test_06_settings_page_requires_typed_confirmation(self) -> None:
        root = Path(__file__).resolve().parents[1]
        html = (root / "static" / "settings.html").read_text(encoding="utf-8")
        script = (root / "static" / "js" / "settings.js").read_text(encoding="utf-8")
        self.assertIn('id="wsDeleteModal"', html)
        self.assertIn("mg-danger", html)
        self.assertIn("确认删除", html)
        self.assertIn("系统回收站", html)
        self.assertIn('wsDeleteInput.value !== "确认删除"', script)
        self.assertIn("wsDeleteConfirm.disabled = true", script)


if __name__ == "__main__":
    unittest.main()
