"""军令 #17 第四步 + #34 契约：恢复校验、必选/可选、覆盖前备份与失败回滚。

钉八件事：
1. 包哈希不符直接拒，工作区一个字节都不动；
2. 题库与图片资产必选（前端传空也补回），其他数据文件按勾选覆盖；
3. 覆盖前生成 ``.pre-restore.bak``（库、边车、将被覆盖的文件），只留最近 1 份；
4. 落盘中途失败整批回滚，不留半恢复状态；
5. 网盘来源下载失败即止（不进入恢复）；
6. **本区配置随包恢复**，不勾就一行不动，且只碰当前工作区；
7. 旧包的插件目录摘要对不上、清单里塞凭据/隐藏/别区路径，一律拒在最前面；
8. 旧包里的 ``ws/plugins/`` 条目自动跳过并回报——插件代码已全局化，恢复不碰它；
9. 只读打开快照库留下的 ``-wal``/``-shm`` 边车不算「清单外文件」，但真正的清单外文件照旧判废。

运行：``.venv/Scripts/python.exe -m unittest tests.test_restore``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))


import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from app.api import settings as settings_api
from app.core import backup, restore, toml_io, wire
from app.core.config import settings
from tests.core_sources import settings_source  # noqa: E402

PROVIDER = "org.jiuzhang.bank-engine"
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
        self.config_path = self.ws_dir / "config.toml"
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
        self.config_path.write_text('v = "old"', encoding="utf-8")
        self.plugin_file = self.plugins / "org.jiuzhang.demo" / "dist" / "plugin.js"
        self.plugin_file.parent.mkdir(parents=True)
        self.plugin_file.write_text("OLD-CODE", encoding="utf-8")
        self.plugin_json = self.plugin_file.parent.parent / "plugin.toml"
        self.plugin_json.write_text('id = "org.jiuzhang.demo"', encoding="utf-8")
        self.state_path = self.ws_dir / "plugin_state.toml"
        self.state_path.write_text('v = "old"', encoding="utf-8")
        self.plugin_rel = "ws/plugins/org.jiuzhang.demo/dist/plugin.js"
        self.state_rel = "ws/plugin_state.toml"
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
        self.config_path.write_text('v = "new"', encoding="utf-8")
        self.plugin_file.write_text("NEW-CODE", encoding="utf-8")
        self.state_path.write_text('v = "new"', encoding="utf-8")

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
        return toml_io.load(self.manifest_path)

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
        self.assertEqual('v = "new"', self.config_path.read_text(encoding="utf-8"))

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
        self.assertNotIn("config.toml", selected)

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
        self.assertNotIn("config.toml", result["restored"])
        self.assertEqual("旧题干", self._db_stem())
        self.assertEqual(b"OLD-PNG", self.upload_path.read_bytes())
        self.assertEqual('v = "new"', self.config_path.read_text(encoding="utf-8"))

    # 4. 覆盖前 .pre-restore.bak 生成且只留最近 1 份
    def test_04_pre_restore_backup_generated_and_pruned(self) -> None:
        self._restore([self.bank_rel, "uploads/pic.png", "config.toml"])
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
        self.assertEqual('v = "new"', config_bak.read_text(encoding="utf-8"))

        # 第二次恢复只勾题库 + 图片（必选），config 未覆盖 → 旧 config 副本应被清掉。
        self.config_path.write_text('v = "newer"', encoding="utf-8")
        self._restore([self.bank_rel, "uploads/pic.png"])
        self.assertFalse(config_bak.exists(), "上一轮的非本轮副本应清理，只留最近 1 套")
        self.assertTrue(db_bak.is_file() and upload_bak.is_file())

    # 5. 落盘中途失败整批回滚
    def test_05_failure_midway_rolls_back_everything(self) -> None:
        plan = self._prepare([self.bank_rel, "uploads/pic.png", "config.toml"])
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
        self.assertEqual('v = "new"', self.config_path.read_text(encoding="utf-8"))
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

    # 8. 工作区配置能整批恢复；插件代码在全局面，不受备份影响
    def test_08_state_round_trip_and_plugin_code_untouched(self) -> None:
        manifest = self._manifest()
        paths = {item["path"] for item in manifest["files"]}
        self.assertIn(self.state_rel, paths)
        self.assertNotIn(self.plugin_rel, paths)
        self.assertEqual([], manifest["plugins"])

        result = self._restore([self.bank_rel, "uploads/pic.png", self.state_rel])
        self.assertEqual("旧题干", self._db_stem())
        self.assertEqual("NEW-CODE", self.plugin_file.read_text(encoding="utf-8"),
                         "插件代码不在备份里，恢复必须原样不动")
        self.assertEqual('v = "old"', self.state_path.read_text(encoding="utf-8"))
        self.assertEqual([], result["plugins_restored"])
        self.assertEqual([], result["plugins_skipped"])
        self.assertTrue(Path(str(self.state_path) + ".pre-restore.bak").is_file(),
                        "覆盖配置前同样要留一份 .pre-restore.bak")

    # 9. 不勾配置就一行都不动
    def test_09_state_is_optional_and_stays_untouched_when_unchecked(self) -> None:
        result = self._restore([self.bank_rel, "uploads/pic.png"])
        self.assertEqual("旧题干", self._db_stem())
        self.assertEqual([], result["plugins_restored"])
        self.assertEqual([], result["plugins_skipped"])
        self.assertEqual("NEW-CODE", self.plugin_file.read_text(encoding="utf-8"))
        self.assertEqual('v = "new"', self.state_path.read_text(encoding="utf-8"))
        self.assertFalse(list(self.plugins.rglob("*.pre-restore.bak")))

    # 10. 恢复只碰当前区，别区数据与全局插件原样不动
    def test_10_restore_leaves_other_workspaces_and_global_plugins_alone(self) -> None:
        foreign = self.data / "workspaces" / "ws_foreign000000000"
        foreign_code = foreign / "plugins" / "org.jiuzhang.foreign"
        foreign_code.mkdir(parents=True)
        (foreign_code / "plugin.toml").write_text("FOREIGN", encoding="utf-8")
        (foreign / "banks").mkdir()
        (foreign / "banks" / "foreign.db").write_bytes(b"FOREIGN-DB")
        self._restore([self.bank_rel, "uploads/pic.png", self.state_rel])
        self.assertEqual("FOREIGN", (foreign_code / "plugin.toml").read_text(encoding="utf-8"))
        self.assertEqual(b"FOREIGN-DB", (foreign / "banks" / "foreign.db").read_bytes())
        self.assertEqual("NEW-CODE", self.plugin_file.read_text(encoding="utf-8"))

    # 11. 旧包的插件摘要对不上：拒在最前面，工作区一个字节都不动
    def test_11_tampered_old_plugin_digest_blocks_restore(self) -> None:
        manifest = self._manifest()
        manifest["files"].append({
            "path": self.plugin_rel, "size": 8,
            "sha256": "a" * 64, "category": "plugins", "required": False,
        })
        manifest["plugins"] = backup.plugins_inventory(manifest["files"])
        restore.validate_manifest(manifest, WS_ID)
        manifest["plugins"][0]["sha256"] = "f" * 64
        before_code = self.plugin_file.read_text(encoding="utf-8")
        before_stem = self._db_stem()
        with self.assertRaises(restore.RestoreError) as caught:
            restore.validate_manifest(manifest, WS_ID)
        self.assertIn("摘要", str(caught.exception))
        self.assertEqual(before_code, self.plugin_file.read_text(encoding="utf-8"))
        self.assertEqual(before_stem, self._db_stem())

    # 12. 清单里塞凭据或隐藏文件：路径校验直接拒
    def test_12_hidden_and_secret_paths_are_refused(self) -> None:
        for smuggled in ("ws/.env", "ws/backup.json", "ws/plugins/.hidden/x.js",
                         "workspaces/other/plugins/x.js"):
            manifest = self._manifest()
            manifest["files"].append({
                "path": smuggled, "size": 1,
                "sha256": "0" * 64, "category": "other", "required": False,
            })
            with self.assertRaises(restore.RestoreError, msg=smuggled) as caught:
                restore.validate_manifest(manifest, WS_ID)
            self.assertTrue(
                any(word in str(caught.exception) for word in ("隐藏文件", "工作区容器", "宿主级")),
                str(caught.exception),
            )

    # 13. 配置写坏也整批回滚，不留半恢复
    def test_13_state_write_failure_rolls_everything_back(self) -> None:
        plan = self._prepare([self.bank_rel, "uploads/pic.png", self.state_rel])
        real_copy = restore._atomic_copy

        def flaky(source, target):
            if Path(target).name == "plugin_state.toml":
                raise OSError("模拟配置写入失败")
            real_copy(source, target)

        try:
            with mock.patch("app.core.restore._atomic_copy", side_effect=flaky):
                with self.assertRaises(OSError):
                    restore.execute_restore(WS_ID, plan)
        finally:
            restore.cleanup_plan(plan)

        self.assertEqual("新题干", self._db_stem(), "配置失败必须连坐回滚题库")
        self.assertEqual(b"NEW-PNG", self.upload_path.read_bytes())
        self.assertEqual('v = "new"', self.state_path.read_text(encoding="utf-8"))
        self.assertEqual("NEW-CODE", self.plugin_file.read_text(encoding="utf-8"))

    # 14. 读快照库留下的边车不许把整包判废（确认执行时还要再复核一遍）
    def test_14_snapshot_sidecars_do_not_block_reverification(self) -> None:
        plan = self._prepare()
        stage = Path(plan["stage"])
        stray = stage / "banks" / f"{PROVIDER}.db-shm"
        stray.write_bytes(b"read artifact")
        try:
            restore.verify_stage(stage, plan["manifest"])
            self.assertFalse(stray.exists(), "只读打开快照库留下的边车必须先清掉")
            result = restore.execute_restore(WS_ID, plan)
            self.assertEqual("旧题干", self._db_stem(), "复核两次都该走到落盘")
            self.assertIn(self.bank_rel, result["restored"])
        finally:
            restore.cleanup_plan(plan)

    # 15. 清单外文件仍然算篡改，不许顺手清掉了事
    def test_15_foreign_files_still_rejected(self) -> None:
        plan = self._prepare()
        try:
            (Path(plan["stage"]) / "banks" / "evil.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(restore.RestoreError) as caught:
                restore.verify_stage(Path(plan["stage"]), plan["manifest"])
            self.assertIn("清单外文件", str(caught.exception))
        finally:
            restore.cleanup_plan(plan)


class RestoreUiContractTest(unittest.TestCase):
    """恢复面板必须按新口径说话：插件代码全机一份，旧包插件条目只跳过、不落盘。"""

    def setUp(self) -> None:
        self.js = settings_source()

    def _manifest(self) -> dict:
        return {
            "manifest_version": backup.MANIFEST_VERSION,
            "workspace_id": WS_ID,
            "question_count": 0,
            "question_hashes": {},
            "package": {"filename": "backup_20260101_010101_001.zst",
                        "sha256": "0" * 64, "size": 1},
            "plugins": [],
            "files": [
                {"path": "banks/x.db", "size": 1, "sha256": "0" * 64,
                 "category": "bank", "required": True},
                {"path": "uploads/a.png", "size": 1, "sha256": "0" * 64,
                 "category": "uploads", "required": True},
                {"path": "ws/plugin_state.toml", "size": 3,
                 "sha256": "0" * 64, "category": "other", "required": False},
                {"path": "config.toml", "size": 1, "sha256": "0" * 64,
                 "category": "other", "required": False},
            ],
        }

    def test_every_backend_group_has_a_labelled_section(self) -> None:
        preview = restore.preview_view(self._manifest())
        self.assertEqual(
            ["bank", "other", "plugins", "uploads"], sorted(preview["groups"])
        )
        self.assertEqual([], preview["groups"]["plugins"])
        self.assertIn("ws/plugin_state.toml", preview["groups"]["other"])
        for group, label in (("bank", "题库数据（必选）"),
                             ("uploads", "图片资产（必选）"),
                             ("other", "其他数据文件（可选，默认勾选）")):
            self.assertIn(group, preview["groups"], f"后端少了 {group} 分组")
            self.assertIn(label, self.js, f"前端少了 {group} 这一组的标题")

    def test_legacy_plugin_entries_are_reported_as_skipped(self) -> None:
        # 插件代码已全局化：旧包条目不许再被当成可恢复勾选项展示。
        self.assertNotIn('["plugins", "插件代码（可选，覆盖后重开页签或重启生效）"]', self.js)
        self.assertNotIn("plugins_restored", self.js)
        self.assertIn("result.plugins_skipped", self.js)
        self.assertIn("旧包插件代码（已全局化，恢复时自动跳过）", self.js)
        self.assertIn("插件代码全机一份，不再随工作区恢复", self.js)


if __name__ == "__main__":
    unittest.main()
