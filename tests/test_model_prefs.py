"""模型配置状态（四合一卡 §2）：住插件目录、不落 data/、更新合并 carried 保住。

运行：``.venv/Scripts/python.exe -m unittest tests.test_model_prefs``
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core import config, toml_io
from app.core.ingest import model_prefs as prefs
from app.core.plugins.lifecycle import update


class PrefsStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plugin = self.root / prefs.PLUGIN_ID
        self.plugin.mkdir()
        env = mock.patch.dict(os.environ, {"JZO_PLUGINS_DIR": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(self.temp.cleanup)

    def test_path_lives_in_plugin_dir_not_data(self) -> None:
        path = prefs.path()
        self.assertEqual(path, self.plugin / "model_prefs.toml")
        self.assertEqual(path.parent, config.plugins_dir() / prefs.PLUGIN_ID)
        self.assertNotIn("data", path.parts)

    def test_missing_file_means_all_enabled_auto(self) -> None:
        self.assertEqual(prefs.load(),
                         {"disabled": [], "default_layout": "auto",
                          "default_recognize": "auto"})

    def test_save_roundtrip(self) -> None:
        saved = prefs.save({"disabled": ["yolo", "mineru"],
                            "default_layout": "yolo",
                            "default_recognize": "mineru"},
                           ["yolo", "mineru", "cloud_vision"])
        self.assertEqual(saved["disabled"], ["yolo", "mineru"])
        self.assertEqual(prefs.load(), saved)
        document = toml_io.load(prefs.path(), {})
        self.assertEqual(document["default_layout"], "yolo")

    def test_partial_save_keeps_other_keys(self) -> None:
        prefs.save({"disabled": ["yolo"]}, ["yolo", "mineru"])
        saved = prefs.save({"default_recognize": "mineru"}, ["yolo", "mineru"])
        self.assertEqual(saved["disabled"], ["yolo"])
        self.assertEqual(saved["default_recognize"], "mineru")

    def test_unknown_id_rejected(self) -> None:
        with self.assertRaises(prefs.PrefsError):
            prefs.save({"disabled": ["乱填"]}, ["yolo"])
        with self.assertRaises(prefs.PrefsError):
            prefs.save({"default_layout": "乱填"}, ["yolo"])
        self.assertFalse(prefs.path().exists())

    def test_auto_cannot_be_disabled(self) -> None:
        with self.assertRaises(prefs.PrefsError):
            prefs.save({"disabled": ["auto"]}, ["yolo"])

    def test_corrupt_file_degrades_to_defaults(self) -> None:
        prefs.path().write_text("这不是 toml = = =", encoding="utf-8")
        self.assertEqual(prefs.load()["disabled"], [])


class CarriedSemanticsTest(unittest.TestCase):
    """插件更新合并语义：新包没有 model_prefs.toml → 原地保住（carried）。"""

    def test_update_preserves_prefs_file(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            old = root / "old"
            staged = root / "staged"
            (old / "dist").mkdir(parents=True)
            (staged / "dist").mkdir(parents=True)
            (staged / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
            toml_io.write(old / prefs.FILENAME,
                          {"disabled": ["yolo"], "default_layout": "auto",
                           "default_recognize": "mineru"})
            kept = update._preserve_local_files(old, staged)
            self.assertIn(prefs.FILENAME, kept["carried"])
            merged = toml_io.load(staged / prefs.FILENAME, {})
        self.assertEqual(merged["disabled"], ["yolo"])
        self.assertEqual(merged["default_recognize"], "mineru")

    def test_prefs_is_user_state_not_seed_data(self) -> None:
        # 新包若哪天自带同名文件，按代码覆盖（它不在数据白名单里）；
        # 官方包永远不发这个文件，老师的勾选只走 carried。
        self.assertFalse(update._is_data_file(Path(prefs.FILENAME)))


if __name__ == "__main__":
    unittest.main()