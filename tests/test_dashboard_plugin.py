"""数据看板插件契约（军令 #11 阶段二）：org.jiuzhang.dashboard。

钉死五件事：
1. 真实插件目录过全套 validate_plugin 契约，不被拒装；
2. 左栏第一位：stage.priority 高于所有其他官方插件；
3. 宿主接线：RELAY 白名单含两条看板通道，PUBLISH_ALLOW 含 system.open_editor，
   且 openEditor 的目标是「录题工作台」而非已退役的题库视图；
4. 原生 DOM 铁律：插件三文件无 iframe、无重型框架、无远程资源、无 localStorage、
   无正则后行断言（AGENTS §6），请求 id 用官方无点号形状；
5. 看板 UI 三件套齐全：四卡片 / 7 行 CSS Grid 热力图 / 最近 5 题可点击跳录题工作台。

运行：``.venv/Scripts/python.exe -m unittest tests.test_dashboard_plugin``
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core import manifests, plugins as plugins_core
from tests.core_sources import stage_source  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "org.jiuzhang.dashboard"
PLUGIN_DIR = ROOT / "plugins" / PLUGIN_ID
STAGE = stage_source()
PLUGIN_JS = (PLUGIN_DIR / "dist" / "plugin.js").read_text(encoding="utf-8")
PLUGIN_CSS = (PLUGIN_DIR / "dist" / "plugin.css").read_text(encoding="utf-8")
PLUGIN_HTML = (PLUGIN_DIR / "dist" / "index.html").read_text(encoding="utf-8")
MANIFEST = manifests.load_manifest(PLUGIN_DIR)


class DashboardManifestTest(unittest.TestCase):
    def test_01_real_plugin_dir_passes_full_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugins_root = Path(tmp) / "plugins"
            plugins_root.mkdir()
            shutil.copytree(PLUGIN_DIR, plugins_root / PLUGIN_ID)
            with mock.patch.dict(os.environ, {"JZO_PLUGINS_DIR": str(plugins_root)}):
                result = plugins_core.discover_plugins()
        ids = [item["id"] for item in result["plugins"]]
        rejected = [item for item in result["rejected"] if item.get("id") == PLUGIN_ID]
        self.assertIn(PLUGIN_ID, ids)
        self.assertEqual(rejected, [])

    def test_02_sidebar_first_position_by_priority(self) -> None:
        self.assertEqual(MANIFEST["stage"]["priority"], 100)
        for plugin_dir in (ROOT / "plugins").iterdir():
            if plugin_dir.name == PLUGIN_ID or manifests.manifest_path(plugin_dir) is None:
                continue
            other = manifests.load_manifest(plugin_dir)
            other_priority = (other.get("stage") or {}).get("priority", 0)
            self.assertGreater(
                MANIFEST["stage"]["priority"], other_priority,
                f"{other['id']} 的 priority 不得高于看板（看板必须挂左栏第一位）",
            )

    def test_03_readonly_permissions_and_capabilities(self) -> None:
        self.assertEqual(MANIFEST["permissions"], ["questions:read"])
        self.assertIn("question.render", MANIFEST["capabilities"])
        self.assertIn("stage.center", MANIFEST["slots"])
        self.assertTrue((PLUGIN_DIR / "LICENSE").is_file())


class HostWiringTest(unittest.TestCase):
    def test_01_relay_whitelist_has_dashboard_channels(self) -> None:
        self.assertIn('"bank.dashboard_stats"', STAGE)
        self.assertIn('"bank.dashboard_heatmap"', STAGE)
        self.assertIn('fetchJson("/api/bank/dashboard/stats")', STAGE)
        self.assertIn('fetchJson("/api/bank/dashboard/heatmap")', STAGE)

    def test_02_recent_click_routes_to_editor(self) -> None:
        self.assertIn('"system.open_editor"', STAGE)
        self.assertIn('bus.on("system.open_editor"', STAGE)
        self.assertIn("function openEditor", STAGE)
        # 题库界面已退役：看板跳转改为打开录题工作台，不再依赖 bank.view 页签
        self.assertIn('"system.open_editor"', PLUGIN_JS)
        self.assertNotIn("system.open_bank", PLUGIN_JS)
        self.assertIn("system.open_editor", MANIFEST["bus"]["publish"])


class NativeDomHygieneTest(unittest.TestCase):
    def test_01_no_iframe_no_framework_no_remote_assets(self) -> None:
        for name, source in (("plugin.js", PLUGIN_JS), ("index.html", PLUGIN_HTML),
                             ("plugin.css", PLUGIN_CSS)):
            self.assertNotIn("<iframe", source.lower(), f"{name} 不得嵌 iframe")
            self.assertNotIn("createElement(\"iframe\"", source, name)
            self.assertNotIn("http://", source, f"{name} 不得引远程资源")
            self.assertNotIn("https://", source, f"{name} 不得引远程资源")
            self.assertNotIn("cdn.", source.lower(), name)

    def test_02_no_localstorage_no_lookbehind(self) -> None:
        self.assertNotIn("localStorage", PLUGIN_JS)
        self.assertNotIn("(?<!", PLUGIN_JS)
        self.assertNotIn("(?<=", PLUGIN_JS)

    def test_03_request_id_shape_is_dot_free(self) -> None:
        # 官方形状 "p" + 序号 + "_" + 时间戳36进制；带点号的插件 id 拼 id 会被宿主拒发
        self.assertIn('"p" + seq + "_" + Date.now().toString(36)', PLUGIN_JS)


class DashboardUiContractTest(unittest.TestCase):
    def test_01_four_stat_cards(self) -> None:
        for kind in ("total", "today", "pending", "stored"):
            self.assertIn(f'"{kind}"', PLUGIN_JS)
        self.assertIn("db-cards", PLUGIN_CSS)

    def test_02_heatmap_is_css_grid_seven_rows(self) -> None:
        self.assertIn(".db-heatmap", PLUGIN_CSS)
        self.assertIn("display: grid", PLUGIN_CSS)
        self.assertIn("grid-template-rows: repeat(7", PLUGIN_CSS)
        self.assertIn("grid-auto-flow: column", PLUGIN_CSS)
        self.assertIn("renderHeatmap", PLUGIN_JS)
        self.assertIn("bank.dashboard_heatmap", PLUGIN_JS)

    def test_03_recent_five_clickable_to_editor(self) -> None:
        self.assertIn("db-recent-link", PLUGIN_JS)
        self.assertIn("system.open_editor", PLUGIN_JS)
        self.assertIn("question_id", PLUGIN_JS)
        self.assertIn("db-recent-link", PLUGIN_CSS)
        # 触控目标不小于 44px（AGENTS §6）
        self.assertIn("min-height: 44px", PLUGIN_CSS)

    def test_04_refresh_debounce_and_idempotent_notifications(self) -> None:
        self.assertIn("system.question_updated", PLUGIN_JS)
        self.assertIn("question.updated", PLUGIN_JS)
        self.assertIn("REFRESH_DEBOUNCE_MS", PLUGIN_JS)


if __name__ == "__main__":
    unittest.main()
