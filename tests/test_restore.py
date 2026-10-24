"""军令 #17 第四步契约：恢复校验、必选/可选、覆盖前备份与失败回滚。

钉五件事：
1. 包哈希不符直接拒，工作区一个字节都不动；
2. 题库与图片资产必选（前端传空也补回），其他数据文件按勾选覆盖；
3. 覆盖前生成 ``.pre-restore.bak``（库、边车、将被覆盖的文件），只留最近 1 份；
4. 落盘中途失败整批回滚，不留半恢复状态；
5. 网盘来源下载失败即止（不进入恢复）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_restore``
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from app.api import settings as settings_api
from app.core import backup, restore
from app.core.config import settings

PROVIDER = "org.jiuzhang.core-bank"
WS_ID = "ws_restore0123456789"


class RestoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.plugins = self.root / "plugins"
        self.plugins.mkdir(parents=True)
        self.ws_dir = self.data / "workspaces" / WS_ID
        (self.ws_dir / "banks").mkdir(parents=True)
        (self.ws_dir / "uploads").mkdir()
        self.db_path = self.ws_dir / "banks" / f"{PROVIDER}.db"
        self.upload_path = self.ws_dir / "uploads" / "pic.png"
        self.config_path = self.ws_dir / "config.json"
        self._saved = (
            os.environ.get("JZO_DATA_DIR"),
            os.environ.get("JZO_PLUGINS_DIR"),
            settings.workspace_id,
        )
        os.environ["JZO_DATA_DIR"] = str(self.data)
        os.environ["JZO_PLUGINS_DIR"] = str(self.plugins)
        settings.workspace_id = WS_ID

        self._write_db("旧题干")
        self.upload_path.write_bytes(b"OLD-PNG")
        self.config_path.write_text('{"v":"old"}', encoding="utf-8")
        self.out = self.root / "backups"
        backup.save_backup_settings(
            {"local_enabled": True, "local_dir": str(self.out)}, WS_ID
        )
        result = backup.create_local_backup(WS_ID, local_dir=self.out)
        self.package_path = Path(result["package"])
        self.manifest_path = Path(result["manifest"])
        self.stem = self.package_path.name[len("backup_"):-len(".zst")]
        self.bank_rel = f"banks/{PROVIDER}.db"

        self._write_db("新题干")
        self.upload_path.write_bytes(b"NEW-PNG")
        self.config_path.write_text('{"v":"new"}', encoding="utf-8")

    def tearDown(self) -> None:
        data, plugins, ws = self._saved
        for key, value in (("JZO_DATA_DIR", data), ("JZO_PLUGINS_DIR", plugins)):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        settings.workspace_id = ws
        self.tmp.cleanup()

    def _write_db(self, stem: str) -> None:
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA user_version=3")
        con.execute("CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, stem TEXT)")
        con.execute("INSERT OR REPLACE INTO questions VALUES ('q_1', ?)", (stem,))
        con.commit()
        con.close()

    def _db_stem(self) -> str:
        con = sqlite3.connect(self.db_path)
        try:
            return con.execute("SELECT stem FROM questions WHERE id='q_1'").fetchone()[0]
        finally:
            con.close()

    def _manifest(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _prepare(self, files=None) -> dict:
        return restore.prepare_local_restore(self.stem, files, WS_ID)

    def _restore(self, files=None) -> dict:
        plan = self._prepare(files)
        try:
            return restore.execute_restore(WS_ID, plan)
        finally:
            restore.cleanup_plan(plan)

    # 1. 哈希失败拒恢复
    def test_01_package_hash_mismatch_rejects_without_touching_data(self) -> None:
        package = self.package_path.read_bytes()
        self.package_path.write_bytes(package[:-8] + b"BROKEN!!")
        with self.assertRaises(restore.RestoreError) as caught:
            self._prepare()
        self.assertIn("哈希", str(caught.exception))
        self.assertEqual("新题干", self._db_stem())
        self.assertEqual(b"NEW-PNG", self.upload_path.read_bytes())
        self.assertEqual('{"v":"new"}', self.config_path.read_text(encoding="utf-8"))

        with self.assertRaises(HTTPException) as api_error:
            settings_api.check_restore(
                {"source": "local", "stem": self.stem, "files": [self.bank_rel]}
            )
        self.assertEqual(400, api_error.exception.status_code)
        self.assertEqual("新题干", self._db_stem())

    # 2. 必选项不可取消
    def test_02_required_bank_and_uploads_cannot_be_cancelled(self) -> None:
        manifest = self._manifest()
        selected = restore.normalize_selection(manifest, [])
        self.assertIn(self.bank_rel, selected)
        self.assertIn("uploads/pic.png", selected)
        self.assertNotIn("config.json", selected)

        plan = self._prepare([self.bank_rel])
        try:
            self.assertIn(self.bank_rel, plan["selected"])
            self.assertIn("uploads/pic.png", plan["selected"])
        finally:
            restore.cleanup_plan(plan)

    # 3. 可选项勾选生效
    def test_03_optional_file_selection_is_honored(self) -> None:
        result = self._restore([self.bank_rel, "uploads/pic.png"])
        self.assertIn(self.bank_rel, result["restored"])
        self.assertIn("uploads/pic.png", result["restored"])
        self.assertNotIn("config.json", result["restored"])
        self.assertEqual("旧题干", self._db_stem())
        self.assertEqual(b"OLD-PNG", self.upload_path.read_bytes())
        self.assertEqual('{"v":"new"}', self.config_path.read_text(encoding="utf-8"))

    # 4. 覆盖前 .pre-restore.bak 生成且只留最近 1 份
    def test_04_pre_restore_backup_generated_and_pruned(self) -> None:
        self._restore([self.bank_rel, "uploads/pic.png", "config.json"])
        db_bak = Path(str(self.db_path) + ".pre-restore.bak")
        upload_bak = Path(str(self.upload_path) + ".pre-restore.bak")
        config_bak = Path(str(self.config_path) + ".pre-restore.bak")
        self.assertTrue(db_bak.is_file())
        self.assertTrue(upload_bak.is_file())
        self.assertTrue(config_bak.is_file())
        self.assertEqual("旧题干", self._db_stem(), "恢复后库应回到备份时的内容")
        con = sqlite3.connect(db_bak)
        try:
            self.assertEqual(
                "新题干", con.execute("SELECT stem FROM questions WHERE id='q_1'").fetchone()[0]
            )
        finally:
            con.close()
        self.assertEqual(b"NEW-PNG", upload_bak.read_bytes())
        self.assertEqual('{"v":"new"}', config_bak.read_text(encoding="utf-8"))

        # 第二次恢复只勾题库 + 图片（必选），config 未覆盖 → 旧 config 副本应被清掉。
        self.config_path.write_text('{"v":"newer"}', encoding="utf-8")
        self._restore([self.bank_rel, "uploads/pic.png"])
        self.assertFalse(config_bak.exists(), "上一轮的非本轮副本应清理，只留最近 1 套")
        self.assertTrue(db_bak.is_file() and upload_bak.is_file())

    # 5. 落盘中途失败整批回滚
    def test_05_failure_midway_rolls_back_everything(self) -> None:
        plan = self._prepare([self.bank_rel, "uploads/pic.png", "config.json"])
        real_copy = restore._atomic_copy
        calls = {"n": 0}

        def flaky(source, target):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("模拟磁盘写失败")
            real_copy(source, target)

        try:
            with mock.patch("app.core.restore._atomic_copy", side_effect=flaky):
                with self.assertRaises(OSError):
                    restore.execute_restore(WS_ID, plan)
        finally:
            restore.cleanup_plan(plan)

        self.assertEqual("新题干", self._db_stem())
        self.assertEqual(b"NEW-PNG", self.upload_path.read_bytes())
        self.assertEqual('{"v":"new"}', self.config_path.read_text(encoding="utf-8"))
        self.assertEqual([], list(self.ws_dir.glob(".restore-rollback-*")))
        self.assertEqual([], list(self.ws_dir.rglob("*.restore-new")))
        self.assertTrue(Path(str(self.db_path) + ".pre-restore.bak").is_file())

    # 6. 网盘下载失败即止
    def test_06_remote_download_failure_stops_before_restore(self) -> None:
        backup.save_backup_settings({"url": "https://dav.example.com/dav"}, WS_ID)
        with mock.patch.object(
            settings_api.webdav, "download_backup", side_effect=settings_api.webdav.WebdavError("断网")
        ):
            with self.assertRaises(HTTPException) as caught:
                settings_api.check_restore(
                    {"source": "remote", "stem": self.stem, "files": [self.bank_rel]}
                )
        self.assertEqual(400, caught.exception.status_code)
        self.assertEqual("新题干", self._db_stem())
        self.assertEqual(b"NEW-PNG", self.upload_path.read_bytes())

    # 7. 别的备份不能冒充当前工作区
    def test_07_foreign_workspace_manifest_rejected(self) -> None:
        manifest = self._manifest()
        manifest["workspace_id"] = "ws_other"
        with self.assertRaises(restore.RestoreError) as caught:
            restore.validate_manifest(manifest, WS_ID)
        self.assertIn("工作区", str(caught.exception))
        with self.assertRaises(restore.RestoreError):
            restore.validate_manifest({**self._manifest(), "files": []}, WS_ID)


if __name__ == "__main__":
    unittest.main()
