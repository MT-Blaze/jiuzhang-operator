"""地基清账契约：stage.priority / singleton 真实消费、插件热插拔与一键打包。

钉死四件事：
1. 舞台页签按 ``stage.priority`` 降序排（原生对话页不参与抢位）；
2. ``stage.singleton=false`` 允许同一插件开多个页签，默认仍是单例；
3. ``/api/plugins`` 回清单签名，前端定时比对——往 plugins/ 解压新目录无需重启；
4. ``tools/build_plugin.py`` 只产出通过全套契约校验的标准 zip（顶层 = 插件 id）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_hotplug_stage_priority``
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from app.core import plugins as plugins_core
from tools.build_plugin import BuildError, build_plugin

ROOT = Path(__file__).resolve().parents[1]
STAGE = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")

MANIFEST = {
    "schema_version": "1.0",
    "id": "com.example.priority-probe",
    "name": "优先级探针",
    "version": "1.0.0",
    "api_version": "1.0",
    "kind": "renderer",
    "description": "只用于热插拔与打包契约测试的最小插件",
    "license": "Apache-2.0",
    "entry": {"frontend": "dist/index.html"},
    "slots": ["stage.center"],
    "capabilities": ["question.render"],
    "permissions": [],
    "stage": {"priority": 42, "singleton": True},
}


def make_plugin(root: Path, manifest: dict = MANIFEST) -> Path:
    plugin_dir = root / manifest["id"]
    (plugin_dir / "dist").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "LICENSE").write_text("Apache License 2.0 (fixture)", encoding="utf-8")
    (plugin_dir / "dist" / "index.html").write_text("<!doctype html><title>p</title>", encoding="utf-8")
    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return plugin_dir


class StagePrioritySourceTest(unittest.TestCase):
    def test_01_tabs_are_ordered_by_priority(self) -> None:
        self.assertIn("function orderPluginTabs", STAGE)
        self.assertIn("priorityOf(b) - priorityOf(a)", STAGE)
        self.assertIn("orderPluginTabs();", STAGE)
        self.assertIn("priority: tab.kind === \"plugin\" ? priorityOf(tab) : null", STAGE)

    def test_02_singleton_false_allows_multiple_tabs(self) -> None:
        self.assertIn("plugin.stage.singleton === false", STAGE)
        self.assertIn('key = baseKey + "#" + serial', STAGE)
        self.assertIn("singleton: tab.kind", STAGE)

    def test_03_left_panel_sorts_by_priority(self) -> None:
        self.assertIn("function pluginPriority", WORKSPACE)
        self.assertIn("pluginPriority(b) - pluginPriority(a)", WORKSPACE)

    def test_04_hot_plug_poll_compares_signature(self) -> None:
        self.assertIn("data.signature", WORKSPACE)
        self.assertIn("window.setInterval(pollPlugins, 5000)", WORKSPACE)
        self.assertIn("visibilitychange", WORKSPACE)
        self.assertIn("updatePlugin(plugin)", WORKSPACE)

    def test_05_no_lookbehind_in_stage_host(self) -> None:
        self.assertNotRegex(STAGE + WORKSPACE, r"\(\?<[=!]")


class DiscoverySignatureTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.plugins_dir = self.root / "plugins"
        self.plugins_dir.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def test_01_signature_changes_after_hot_install(self) -> None:
        with mock.patch.dict(os.environ, {"JZO_PLUGINS_DIR": str(self.plugins_dir)}):
            empty = plugins_core.discover_plugins()
            self.assertEqual(empty["plugins"], [])
            make_plugin(self.plugins_dir, MANIFEST)
            first = plugins_core.discover_plugins()
            self.assertEqual([p["id"] for p in first["plugins"]], [MANIFEST["id"]])
            self.assertNotEqual(first["signature"], empty["signature"], "新目录落地后签名必须变化")

            hot_manifest = dict(MANIFEST, version="1.0.1")
            make_plugin(self.plugins_dir, hot_manifest)
            # 签名只认 mtime/size；同版本号覆盖时 size 不变，必须让 mtime 确定性地前进。
            # Windows 的文件时间戳会被系统时钟粒度量化（本机实测连续两次写入 92% 同戳），
            # 直接 utime(now) 约三分之一概率仍等于旧值——这不是产品缺陷，是测试自身的抖。
            manifest_path = self.plugins_dir / MANIFEST["id"] / "plugin.json"
            bumped = manifest_path.stat().st_mtime + 1
            os.utime(manifest_path, (bumped, bumped))
            second = plugins_core.discover_plugins()
            self.assertNotEqual(second["signature"], first["signature"], "覆盖同 id 也要被发现")


class BuildPluginTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_01_zip_top_level_is_plugin_id(self) -> None:
        plugin_dir = make_plugin(self.root)
        (plugin_dir / ".env").write_text("SECRET=1", encoding="utf-8")
        (plugin_dir / "dist" / "__pycache__").mkdir()
        (plugin_dir / "dist" / "__pycache__" / "x.pyc").write_bytes(b"x")
        (plugin_dir / "dist" / "nested.zip").write_bytes(b"PK")
        target = build_plugin(plugin_dir, self.root / "out")
        self.assertTrue(target.is_file())
        with zipfile.ZipFile(target) as archive:
            names = archive.namelist()
        self.assertTrue(all(name.startswith(MANIFEST["id"] + "/") for name in names))
        self.assertNotIn(f"{MANIFEST['id']}/.env", names)
        self.assertFalse(any("__pycache__" in name for name in names))
        self.assertFalse(any(name.endswith(".zip") for name in names))

    def test_02_invalid_manifest_never_produces_zip(self) -> None:
        broken = dict(MANIFEST, license="GPL-3.0")
        plugin_dir = make_plugin(self.root, broken)
        with self.assertRaises(BuildError):
            build_plugin(plugin_dir, self.root / "out")
        self.assertFalse((self.root / "out" / f"{MANIFEST['id']}.zip").exists())


if __name__ == "__main__":
    unittest.main()
