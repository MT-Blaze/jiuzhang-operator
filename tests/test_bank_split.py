"""军令 #20 题库拆分解耦：引擎 / 视图边界与数据兼容。

拆分后最容易出事的四条线，各有判据：

1. **清单边界**：引擎是 headless provider——没有 iframe、不进左栏、不可卸载；
   视图插件只声明 ``bank.view``，绝不冒充 provider；
2. **旧库只读复制**：升级后旧 ``core-bank`` 物理库字节不动，新引擎库把题目原样带过来，
   旧库连同 ``-wal`` 一起复制，失败留下的孤儿边车不带走；
3. **升级映射**：引擎已装时旧插件目录退出发现，旧目录与旧物理库原地保留；
4. **宿主门禁**：查重只对 provider 页签或 ``bank.view`` 视图插件开放。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_split``
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.core import bank
from app.core.config import settings
from app.core.plugins import PluginRejected, discover_plugins, validate_plugin

ROOT = Path(__file__).resolve().parents[1]
ENGINE = "org.jiuzhang.bank-engine"
UI = "org.jiuzhang.bank-ui"
LEGACY = "org.jiuzhang.core-bank"
PAPER = "org.jiuzhang.paper-gen"
BASELINE = ROOT / "plugins" / ENGINE / "bank" / "v063.db"
STAMP = "2026-01-15T09:00:00+08:00"


def _manifest(plugin_id: str) -> dict:
    path = ROOT / "plugins" / plugin_id / "plugin.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _insert_question(path: Path, question_id: str, stem: str) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(
            "INSERT INTO questions (id,type,stem,options,answer,solution,extensions,"
            "difficulty,created_at,updated_at) VALUES (?,'fill_blank',?,'[]',NULL,NULL,'[]','L1',?,?)",
            (question_id, stem, STAMP, STAMP),
        )
        con.commit()
    finally:
        con.close()


def _question_ids(path: Path) -> list[str]:
    con = sqlite3.connect(path)
    try:
        return [row[0] for row in con.execute("SELECT id FROM questions ORDER BY id")]
    finally:
        con.close()


class ManifestBoundaryTest(unittest.TestCase):
    """两份清单各司其职：引擎只给能力，视图只给界面。"""

    def test_01_engine_is_a_headless_provider_without_ui(self) -> None:
        manifest = _manifest(ENGINE)
        self.assertIs(manifest.get("headless"), True)
        self.assertIs(manifest.get("uninstallable"), False, "引擎必须带免死金牌")
        self.assertIs(manifest.get("show_in_sidebar"), False, "引擎不占左栏")
        self.assertEqual([], manifest.get("slots"))
        for key in ("entry", "ui", "stage"):
            self.assertNotIn(key, manifest, f"headless 引擎不得声明 {key}")
        self.assertEqual(["bank.provider"], manifest.get("capabilities"))
        self.assertEqual({"questions:read", "questions:write"},
                         set(manifest.get("permissions") or []))

    def test_02_view_plugin_declares_bank_view_only(self) -> None:
        manifest = _manifest(UI)
        self.assertIn("bank.view", manifest.get("capabilities") or [])
        self.assertNotIn("bank.provider", manifest.get("capabilities") or [],
                         "视图插件不得冒充题库 provider")
        self.assertNotEqual(False, manifest.get("show_in_sidebar", True))
        self.assertNotEqual(False, manifest.get("uninstallable", True))
        self.assertIn("question.card", manifest.get("slots") or [])
        frontend = (manifest.get("entry") or {}).get("frontend") or ""
        self.assertTrue((ROOT / "plugins" / UI / frontend).is_file(), frontend)

    def test_03_validation_turns_headless_into_empty_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine_dir = Path(tmp) / ENGINE
            ui_dir = Path(tmp) / UI
            shutil.copytree(ROOT / "plugins" / ENGINE, engine_dir)
            shutil.copytree(ROOT / "plugins" / UI, ui_dir)
            engine_info = validate_plugin(engine_dir, _manifest(ENGINE))
            ui_info = validate_plugin(ui_dir, _manifest(UI))
        self.assertTrue(engine_info["headless"])
        self.assertEqual("", engine_info["entry_url"])
        self.assertIsNone(engine_info["ui"])
        self.assertEqual([], engine_info["slots"])
        self.assertFalse(engine_info["uninstallable"])
        self.assertFalse(engine_info["show_in_sidebar"])
        self.assertFalse(ui_info["headless"])
        self.assertTrue(ui_info["entry_url"].startswith(f"/plugin-assets/{UI}/dist/"))
        self.assertIn("bank.view", ui_info["capabilities"])

    def test_04_headless_cannot_smuggle_an_entry_or_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ENGINE
            shutil.copytree(ROOT / "plugins" / ENGINE, target)
            manifest = _manifest(ENGINE)
            for extra in ({"entry": {"frontend": "dist/index.html"}},
                          {"ui": {"title": "偷塞的界面"}},
                          {"stage": {"center": {"takeover": True}}}):
                broken = {**manifest, **extra}
                with self.assertRaises(PluginRejected, msg=str(extra)):
                    validate_plugin(target, broken)

    def test_05_retired_core_bank_leaves_discovery_only_when_engine_is_gone(self) -> None:
        """旧插件目录可能还留在老工作区：引擎一装，它就得退出发现（同一份题库不能两个主人）。"""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugins_dir = base / "plugins"
            plugins_dir.mkdir()
            for plugin_id in (ENGINE, UI):
                shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)
            legacy_dir = plugins_dir / LEGACY
            shutil.copytree(ROOT / "plugins" / ENGINE, legacy_dir)
            legacy_manifest = _manifest(ENGINE)
            legacy_manifest.update({
                "id": LEGACY,
                "name": "旧题库",
                "description": "拆分前的旧题库插件目录，只用于升级映射的发现判据。",
                "capabilities": ["bank.provider"],
            })
            (legacy_dir / "plugin.json").write_text(
                json.dumps(legacy_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            saved = (os.environ.get("JZO_PLUGINS_DIR"), os.environ.get("JZO_DATA_DIR"),
                     settings.workspace_id)
            os.environ["JZO_PLUGINS_DIR"] = str(plugins_dir)
            os.environ["JZO_DATA_DIR"] = str(base / "data")
            settings.workspace_id = None
            try:
                ids = {item["id"] for item in discover_plugins()["plugins"]}
                self.assertIn(ENGINE, ids)
                self.assertIn(UI, ids)
                self.assertNotIn(LEGACY, ids, "引擎已装时旧 core-bank 不该再被发现")
                shutil.rmtree(plugins_dir / ENGINE)
                ids = {item["id"] for item in discover_plugins()["plugins"]}
                self.assertIn(LEGACY, ids, "引擎没装时旧目录仍在，回退路径要留得住")
            finally:
                for key, value in zip(("JZO_PLUGINS_DIR", "JZO_DATA_DIR"), saved[:2]):
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                settings.workspace_id = saved[2]


class LegacyBankCopyTest(unittest.TestCase):
    """升级不丢题：旧库只读复制，旧文件字节不动。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self._saved = (os.environ.get("JZO_DATA_DIR"), os.environ.get("JZO_PLUGINS_DIR"),
                       settings.workspace_id)
        os.environ["JZO_DATA_DIR"] = str(base / "data")
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        settings.workspace_id = None
        bank._structure_cache.clear()
        self.addCleanup(self._restore)
        self.legacy = base / "data" / "banks" / f"{LEGACY}.db"
        self.legacy.parent.mkdir(parents=True)
        shutil.copyfile(BASELINE, self.legacy)
        _insert_question(self.legacy, "q_legacy_0001", "旧库第一题：$1+1=2$")
        _insert_question(self.legacy, "q_legacy_0002", "旧库第二题：$2+2=4$")
        self.legacy_digest = _digest(self.legacy)

    def _restore(self) -> None:
        bank._structure_cache.clear()
        for key, value in zip(("JZO_DATA_DIR", "JZO_PLUGINS_DIR"), self._saved[:2]):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        settings.workspace_id = self._saved[2]

    def test_01_engine_copies_legacy_questions_and_leaves_the_file_alone(self) -> None:
        path = bank.ensure_bank(ENGINE)
        self.assertTrue(path.is_file())
        self.assertEqual(["q_legacy_0001", "q_legacy_0002"], _question_ids(path))
        self.assertEqual(self.legacy_digest, _digest(self.legacy),
                         "旧 core-bank 物理库必须逐字节原样保留")
        self.assertNotEqual(path, self.legacy)

    def test_02_existing_engine_bank_wins_over_legacy_source(self) -> None:
        path = bank.ensure_bank(ENGINE)
        _insert_question(path, "q_engine_0003", "拆分后新录的题")
        bank.ensure_bank(ENGINE)
        self.assertEqual(["q_engine_0003", "q_legacy_0001", "q_legacy_0002"],
                         _question_ids(path), "已存在的引擎库不该被旧库覆盖")
        self.assertEqual(self.legacy_digest, _digest(self.legacy))
        self.legacy.unlink()
        bank.ensure_bank(ENGINE)
        self.assertEqual(3, len(_question_ids(path)), "旧库没了也不影响已建好的引擎库")

    def test_03_non_engine_plugins_never_touch_the_legacy_bank(self) -> None:
        target = Path(self.tmp.name) / "data" / "banks" / f"{PAPER}.db"
        self.assertFalse(bank._copy_legacy_bank(PAPER, target))
        self.assertFalse(target.exists())
        self.assertEqual(self.legacy_digest, _digest(self.legacy))

    def test_04_wal_is_copied_and_orphan_sidecars_are_removed(self) -> None:
        wal = Path(str(self.legacy) + "-wal")
        wal.write_bytes(b"WAL-PROBE-BYTES")
        target = Path(self.tmp.name) / "data" / "banks" / f"{ENGINE}.db"
        self.assertTrue(bank._copy_legacy_bank(ENGINE, target))
        self.assertEqual(b"WAL-PROBE-BYTES", Path(str(target) + "-wal").read_bytes())
        self.assertEqual(b"WAL-PROBE-BYTES", wal.read_bytes(), "旧库的 WAL 只读，不许搬走")
        self.assertEqual(self.legacy_digest, _digest(self.legacy))

        wal.unlink()
        other_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(other_tmp.cleanup)
        other_target = Path(other_tmp.name) / f"{ENGINE}.db"
        Path(str(other_target) + "-wal").write_bytes(b"STALE")
        self.assertTrue(bank._copy_legacy_bank(ENGINE, other_target))
        self.assertFalse(Path(str(other_target) + "-wal").exists(),
                         "源库没有 WAL 时，上一轮遗留的孤儿边车必须清掉")


class HostGateTest(unittest.TestCase):
    """宿主门禁：查重与跳转只认能力，不认插件 id。"""

    def test_01_both_capabilities_are_declared_by_the_host(self) -> None:
        source = (ROOT / "app" / "core" / "plugins.py").read_text(encoding="utf-8")
        self.assertIn('"bank.provider"', source)
        self.assertIn('"bank.view"', source)

    def test_02_dedupe_is_gated_by_capability_not_by_plugin_id(self) -> None:
        source = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        self.assertIn('method === "bank.dedupe_scan" || method === "bank.dedupe_merge"', source)
        self.assertIn('hasCapability(tab, "bank.view")', source)
        self.assertIn('code: "FORBIDDEN"', source)

    def test_03_bank_view_plugin_reads_the_active_bank_not_its_own(self) -> None:
        """视图插件只走 active_* / active_add：它的页签 id 不是题库 id。"""
        source = (ROOT / "plugins" / UI / "dist" / "plugin.js").read_text(encoding="utf-8")
        self.assertIn("bank.active_list", source)
        self.assertIn("basket.active_add", source)
        self.assertNotIn("bank.list", source)
        self.assertNotIn("basket.add", source)


if __name__ == "__main__":
    unittest.main()
