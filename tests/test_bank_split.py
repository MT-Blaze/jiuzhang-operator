"""题库去 UI 化：引擎退居纯后台、旧视图目录退役、数据兼容。

去 UI 后最容易出事的几条线，各有判据：

1. **清单边界**：``org.jiuzhang.bank-engine`` 只声明 provider，``headless: true``，
   不注册 entry / ui / stage / slots，不占左栏；
2. **单包唯一**：旧 ``org.jiuzhang.bank-ui`` 目录不再作为独立插件被发现，
   老工作区残留也不会变成第二个更新条目；
3. **旧库只读复制**：升级后旧 ``core-bank`` 物理库字节不动，新引擎库把题目原样带过来，
   旧库连同 ``-wal`` 一起复制，失败留下的孤儿边车不带走；
4. **退役护栏**：全库查重的 relay 分支与命令声明已下架，不许被加回来。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_split``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))


import hashlib
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.core import bank, manifests, wire
from app.core.config import settings
from app.core.plugins import PluginRejected, discover_plugins, validate_plugin
from tests.core_sources import stage_source  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
ENGINE = "org.jiuzhang.bank-engine"
RETIRED_UI = "org.jiuzhang.bank-ui"
LEGACY = "org.jiuzhang.core-bank"
PAPER = "org.jiuzhang.paper-gen"
BASELINE = ROOT / "tests" / "fixtures" / "v063.db"
STAMP = "2026-01-15T09:00:00+08:00"


def _manifest(plugin_id: str) -> dict:
    return manifests.load_manifest(PLUGIN_SOURCE_DIR / plugin_id)


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
    """引擎只做后台 provider；旧视图目录退出历史舞台。"""

    def test_01_engine_is_the_single_headless_package(self) -> None:
        manifest = _manifest(ENGINE)
        self.assertIs(manifest.get("headless"), True, "引擎已退居纯后台，不再带界面")
        self.assertIs(manifest.get("uninstallable"), False, "引擎必须带免死金牌")
        self.assertIs(manifest.get("show_in_sidebar"), False, "纯引擎不在左栏占位")
        self.assertEqual(manifest.get("slots") or [], [])
        self.assertEqual(["bank.provider"], manifest.get("capabilities"))
        self.assertEqual({"questions:read", "questions:write"},
                         set(manifest.get("permissions") or []))
        self.assertEqual("九章题库", manifest.get("name"))
        self.assertNotIn("entry", manifest, "headless 插件不得声明前端入口")
        self.assertNotIn("ui", manifest)
        self.assertNotIn("stage", manifest)
        self.assertFalse((PLUGIN_SOURCE_DIR / ENGINE / "webui").exists(),
                         "webui 目录必须物理删除，纯引擎不留前端资产")

    def test_02_retired_view_plugin_directory_is_gone(self) -> None:
        self.assertFalse((PLUGIN_SOURCE_DIR / RETIRED_UI).exists(),
                         "旧 bank-ui 目录必须物理删除，不能作为第二个包继续发布")

    def test_03_validation_exposes_headless_and_data_commands(self) -> None:
        info = validate_plugin(PLUGIN_SOURCE_DIR / ENGINE, _manifest(ENGINE))
        self.assertTrue(info["headless"])
        self.assertEqual("", info["entry_url"])
        self.assertIsNone(info["ui"])
        self.assertIsNone(info["stage"])
        self.assertFalse(info["uninstallable"])
        self.assertFalse(info["show_in_sidebar"])
        ids = {command["id"] for command in info["commands"]}
        self.assertEqual({
            "org.jiuzhang.action.data.bank_stats",
            "org.jiuzhang.action.data.bank_search",
            "org.jiuzhang.action.data.bank_topics",
        }, ids)

    def test_04_headless_cannot_smuggle_an_entry_or_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ENGINE
            shutil.copytree(PLUGIN_SOURCE_DIR / ENGINE, target)
            manifest = _manifest(ENGINE)
            for extra in ({"ui": {"title": "偷塞的界面"}},
                          {"stage": {"region": "center", "mode": "takeover"}},
                          {"entry": {"frontend": "webui/index.html"}}):
                broken = {**manifest, **extra}
                with self.assertRaises(PluginRejected, msg=str(extra)):
                    validate_plugin(target, broken)

    def test_05_retired_view_directory_never_shows_up_in_discovery(self) -> None:
        """老工作区残留的 bank-ui 目录不许再变成第二个插件/第二个更新条目。"""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugins_dir = base / "plugins"
            plugins_dir.mkdir()
            shutil.copytree(PLUGIN_SOURCE_DIR / ENGINE, plugins_dir / ENGINE)
            leftover = plugins_dir / RETIRED_UI
            shutil.copytree(PLUGIN_SOURCE_DIR / ENGINE, leftover)
            stale = _manifest(ENGINE)
            stale.update({"id": RETIRED_UI, "name": "旧真题题库"})
            (leftover / "plugin.toml").unlink()
            (leftover / "plugin.json").write_text(
                wire.dumps(stale, ensure_ascii=False, indent=2), encoding="utf-8")
            saved = (os.environ.get("JZO_PLUGINS_DIR"), os.environ.get("JZO_DATA_DIR"),
                     settings.workspace_id)
            os.environ["JZO_PLUGINS_DIR"] = str(plugins_dir)
            os.environ["JZO_DATA_DIR"] = str(base / "data")
            settings.workspace_id = None
            try:
                ids = {item["id"] for item in discover_plugins()["plugins"]}
                self.assertIn(ENGINE, ids)
                self.assertNotIn(RETIRED_UI, ids, "残留的旧视图目录必须退出发现")
            finally:
                for key, value in zip(("JZO_PLUGINS_DIR", "JZO_DATA_DIR"), saved[:2]):
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                settings.workspace_id = saved[2]

    def test_06_retired_core_bank_leaves_discovery_only_when_engine_is_gone(self) -> None:
        """旧 core-bank 目录可能还留在老工作区：引擎一装，它就得退出发现。"""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugins_dir = base / "plugins"
            plugins_dir.mkdir()
            shutil.copytree(PLUGIN_SOURCE_DIR / ENGINE, plugins_dir / ENGINE)
            legacy_dir = plugins_dir / LEGACY
            shutil.copytree(PLUGIN_SOURCE_DIR / ENGINE, legacy_dir)
            legacy_manifest = _manifest(ENGINE)
            legacy_manifest.update({
                "id": LEGACY,
                "name": "旧题库",
                "description": "拆分前的旧题库插件目录，只用于升级映射的发现判据。",
                "capabilities": ["bank.provider"],
            })
            (legacy_dir / "plugin.toml").unlink()
            (legacy_dir / "plugin.json").write_text(
                wire.dumps(legacy_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            saved = (os.environ.get("JZO_PLUGINS_DIR"), os.environ.get("JZO_DATA_DIR"),
                     settings.workspace_id)
            os.environ["JZO_PLUGINS_DIR"] = str(plugins_dir)
            os.environ["JZO_DATA_DIR"] = str(base / "data")
            settings.workspace_id = None
            try:
                ids = {item["id"] for item in discover_plugins()["plugins"]}
                self.assertIn(ENGINE, ids)
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
        os.environ["JZO_PLUGINS_DIR"] = str(PLUGIN_SOURCE_DIR)
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

    def test_02_dedupe_relay_branches_are_retired(self) -> None:
        """3.6 已下架全库查重：relay 分支与命令声明都不许回来。"""
        source = stage_source()
        self.assertNotIn('method === "bank.dedupe_scan"', source)
        self.assertNotIn('method === "bank.dedupe_merge"', source)

    def test_03_the_engine_no_longer_ships_a_bank_view(self) -> None:
        """去 UI 后引擎不再声明 bank.view，也不许把 webui 资产偷偷加回来。"""
        manifest = _manifest(ENGINE)
        self.assertNotIn("bank.view", manifest.get("capabilities") or [])
        self.assertFalse((PLUGIN_SOURCE_DIR / ENGINE / "webui").exists())


if __name__ == "__main__":
    unittest.main()
