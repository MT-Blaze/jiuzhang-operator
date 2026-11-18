"""模型勾选（配置归插件卡）：住请求插件自己的目录、不落 data/、更新合并语义。

两条更新语义钉死（卡 §1）：
- 新包**没有** model_prefs.toml → 原地保住（carried，教师财产）；
- 新包**带了** catalog.toml → 覆盖旧目录（清单可更新，.toml 不在数据白名单）。

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

PLUGIN_ID = "org.jiuzhang.editor"
OTHER_ID = "org.example.other"


class PrefsStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plugin = self.root / PLUGIN_ID
        self.plugin.mkdir()
        env = mock.patch.dict(os.environ, {"JZO_PLUGINS_DIR": str(self.root),
                                           "JZO_DATA_DIR": str(self.root / "data")})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(self.temp.cleanup)

    def test_path_lives_in_plugin_dir_not_data(self) -> None:
        path = prefs.path(PLUGIN_ID)
        self.assertEqual(path, self.plugin / "model_prefs.toml")
        self.assertEqual(path.parent, config.plugins_dir() / PLUGIN_ID)
        self.assertNotIn("data", path.parts)

    def test_missing_file_means_all_enabled_auto(self) -> None:
        self.assertEqual(prefs.load(PLUGIN_ID),
                         {"disabled": [], "default_layout": "auto",
                          "default_recognize": "auto"})

    def test_save_roundtrip(self) -> None:
        saved = prefs.save({"disabled": ["yolo", "mineru"],
                            "default_layout": "yolo",
                            "default_recognize": "mineru"},
                           ["yolo", "mineru", "cloud_vision"], PLUGIN_ID)
        self.assertEqual(saved["disabled"], ["yolo", "mineru"])
        self.assertEqual(prefs.load(PLUGIN_ID), saved)
        document = toml_io.load(prefs.path(PLUGIN_ID), {})
        self.assertEqual(document["default_layout"], "yolo")

    def test_partial_save_keeps_other_keys(self) -> None:
        prefs.save({"disabled": ["yolo"]}, ["yolo", "mineru"], PLUGIN_ID)
        saved = prefs.save({"default_recognize": "mineru"}, ["yolo", "mineru"], PLUGIN_ID)
        self.assertEqual(saved["disabled"], ["yolo"])
        self.assertEqual(saved["default_recognize"], "mineru")

    def test_unknown_id_rejected(self) -> None:
        with self.assertRaises(prefs.PrefsError):
            prefs.save({"disabled": ["乱填"]}, ["yolo"], PLUGIN_ID)
        with self.assertRaises(prefs.PrefsError):
            prefs.save({"default_layout": "乱填"}, ["yolo"], PLUGIN_ID)
        self.assertFalse(prefs.path(PLUGIN_ID).exists())

    def test_auto_cannot_be_disabled(self) -> None:
        with self.assertRaises(prefs.PrefsError):
            prefs.save({"disabled": ["auto"]}, ["yolo"], PLUGIN_ID)

    def test_corrupt_file_degrades_to_defaults(self) -> None:
        prefs.path(PLUGIN_ID).write_text("这不是 toml = = =", encoding="utf-8")
        self.assertEqual(prefs.load(PLUGIN_ID)["disabled"], [])

    def test_invalid_plugin_id_rejected(self) -> None:
        for bad in ("", "../evil", "no_dots", "org.jiuzhang.editor/../../x", "UPPER.case"):
            with self.assertRaises(prefs.PrefsError):
                prefs.path(bad)

    def test_two_plugins_do_not_share_prefs(self) -> None:
        other = self.root / OTHER_ID
        other.mkdir()
        prefs.save({"disabled": ["yolo"]}, ["yolo"], PLUGIN_ID)
        self.assertEqual(prefs.load(OTHER_ID)["disabled"], [])
        prefs.save({"default_layout": "mineru"}, ["mineru"], OTHER_ID)
        self.assertEqual(prefs.load(PLUGIN_ID)["default_layout"], "auto")
        self.assertEqual(prefs.load(OTHER_ID)["default_layout"], "mineru")

    def test_data_tree_never_holds_model_prefs(self) -> None:
        """卡 §3 铁律：data/ 全树不得出现 model_prefs.toml（探针同判据）。"""
        prefs.save({"disabled": ["yolo"]}, ["yolo"], PLUGIN_ID)
        data_root = config.settings.data_dir
        data_root.mkdir(parents=True, exist_ok=True)
        hits = [p for p in data_root.rglob(prefs.FILENAME)]
        self.assertEqual(hits, [])


class UpdateSemanticsTest(unittest.TestCase):
    """插件更新合并语义：prefs carried 保住；catalog 随新包覆盖（清单可更新）。"""

    def _stage(self, root: Path, with_catalog: bool, with_prefs: bool) -> tuple[Path, Path]:
        old = root / "old"
        staged = root / "staged"
        (old / "dist").mkdir(parents=True)
        (staged / "dist").mkdir(parents=True)
        (staged / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
        toml_io.write(old / prefs.FILENAME,
                      {"disabled": ["yolo"], "default_layout": "auto",
                       "default_recognize": "mineru"})
        (old / "catalog.toml").write_text('vram_note = "旧目录"\n', encoding="utf-8")
        if with_catalog:
            (staged / "catalog.toml").write_text('vram_note = "新目录"\n', encoding="utf-8")
        if with_prefs:
            toml_io.write(staged / prefs.FILENAME, {"disabled": []})
        return old, staged

    def test_update_preserves_prefs_file(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            old, staged = self._stage(Path(name), with_catalog=True, with_prefs=False)
            kept = update._preserve_local_files(old, staged)
            self.assertIn(prefs.FILENAME, kept["carried"])
            merged = toml_io.load(staged / prefs.FILENAME, {})
        self.assertEqual(merged["disabled"], ["yolo"])
        self.assertEqual(merged["default_recognize"], "mineru")

    def test_new_package_catalog_overrides_old(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            old, staged = self._stage(Path(name), with_catalog=True, with_prefs=False)
            kept = update._preserve_local_files(old, staged)
            self.assertNotIn("catalog.toml", kept["carried"])
            self.assertNotIn("catalog.toml", kept["data_overridden"])
            merged = toml_io.load(staged / "catalog.toml", {})
        self.assertEqual(merged["vram_note"], "新目录")

    def test_catalog_absent_from_new_package_is_carried(self) -> None:
        """新包没带目录时按合并语义保住旧目录——降级不停摆，但官方包永远带目录。"""
        with tempfile.TemporaryDirectory() as name:
            old, staged = self._stage(Path(name), with_catalog=False, with_prefs=False)
            kept = update._preserve_local_files(old, staged)
            self.assertIn("catalog.toml", kept["carried"])
            merged = toml_io.load(staged / "catalog.toml", {})
        self.assertEqual(merged["vram_note"], "旧目录")

    def test_prefs_is_user_state_not_seed_data(self) -> None:
        # 新包若哪天自带同名文件，按代码覆盖（它不在数据白名单里）；
        # 官方包永远不发这个文件，老师的勾选只走 carried。
        self.assertFalse(update._is_data_file(Path(prefs.FILENAME)))
        self.assertFalse(update._is_data_file(Path("catalog.toml")))


if __name__ == "__main__":
    unittest.main()