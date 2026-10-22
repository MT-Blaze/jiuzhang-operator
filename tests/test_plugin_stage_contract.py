"""插件舞台声明（stage / bus）后端校验契约：v0.6.0 军令任务 3.2。

要点：
- ``slots`` 新增 ``stage.center``，声明它的插件才能在中栏画布开页签；
- 写了 ``stage`` 却没要 ``stage.center`` 直接拒装：声明了没有落点的能力就是假能力；
- ``stage``/``bus`` 走宽容归一（同 ``ui`` 口径）：非法值退回最保守档，不整包拒装；
- ``bus.publish`` 白名单只放三区投递与舞台选区，绝不放行 ui.params.* / layout.*。

运行：``.venv/Scripts/python.exe -m unittest tests.test_plugin_stage_contract``
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app.api.plugins import InstalledPlugin
from app.core.plugins import PluginRejected, validate_plugin

PLUGIN_ID = "com.example.stage-probe"

BASE_MANIFEST = {
    "schema_version": "1.0",
    "id": PLUGIN_ID,
    "name": "舞台契约探针",
    "version": "1.0.0",
    "api_version": "1.0",
    "kind": "renderer",
    "description": "只用于舞台声明校验的最小插件",
    "license": "Apache-2.0",
    "entry": {"frontend": "dist/index.html"},
    "slots": ["question.card"],
    "capabilities": ["question.render"],
    "permissions": [],
}


def build_plugin_dir(root: Path, manifest: dict) -> Path:
    plugin_dir = root / manifest["id"]
    (plugin_dir / "dist").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "LICENSE").write_text("Apache License 2.0 (fixture)", encoding="utf-8")
    (plugin_dir / "dist" / "index.html").write_text("<!doctype html><title>p</title>", encoding="utf-8")
    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return plugin_dir


class StageDeclarationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def validate(self, **overrides) -> dict:
        manifest = json.loads(json.dumps(BASE_MANIFEST))
        manifest.update(overrides)
        return validate_plugin(build_plugin_dir(self.root, manifest), manifest)

    def test_01_stage_slot_is_accepted(self) -> None:
        info = self.validate(slots=["stage.center"])
        self.assertEqual(info["slots"], ["stage.center"])
        self.assertEqual(info["stage"]["region"], "center")
        self.assertEqual(info["stage"]["mode"], "embed", "未写 stage 时给最保守的内嵌档")

    def test_02_stage_without_slot_is_rejected(self) -> None:
        with self.assertRaises(PluginRejected) as caught:
            self.validate(stage={"mode": "takeover"})
        self.assertIn("stage.center", str(caught.exception))

    def test_03_unknown_slot_value_still_rejected(self) -> None:
        with self.assertRaises(PluginRejected):
            self.validate(slots=["stage.left"])

    def test_04_illegal_mode_falls_back_to_embed(self) -> None:
        info = self.validate(slots=["stage.center"], stage={"mode": "overlay"})
        self.assertEqual(info["stage"]["mode"], "embed")

    def test_05_fullscreen_and_priority_are_carried(self) -> None:
        info = self.validate(
            slots=["stage.center"],
            stage={"mode": "fullscreen", "title": "全屏答题卡", "priority": 999},
        )
        self.assertEqual(info["stage"]["mode"], "fullscreen")
        self.assertEqual(info["stage"]["title"], "全屏答题卡")
        self.assertEqual(info["stage"]["priority"], 100, "优先级必须夹在 ±100 内")

    def test_06_long_title_is_truncated(self) -> None:
        info = self.validate(slots=["stage.center"], stage={"title": "标" * 80})
        self.assertLessEqual(len(info["stage"]["title"]), 24)

    def test_07_stage_field_is_not_a_string(self) -> None:
        info = self.validate(slots=["stage.center"], stage="fullscreen")
        self.assertIsNone(info["stage"], "写错类型的 stage 只能作废，不许猜")


class BusGrantTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def validate(self, bus) -> dict:
        manifest = json.loads(json.dumps(BASE_MANIFEST))
        if bus is not None:
            manifest["bus"] = bus
        return validate_plugin(build_plugin_dir(self.root, manifest), manifest)

    def test_01_defaults_are_minimal(self) -> None:
        info = self.validate(None)
        self.assertEqual(info["bus"]["publish"], ["region.dock"])
        self.assertEqual(info["bus"]["subscribe"], ["ui.params.changed"])

    def test_02_publish_whitelist_blocks_panel_and_layout(self) -> None:
        info = self.validate(
            {"publish": ["region.dock", "ui.params.changed", "layout.changed", "region.right"]}
        )
        self.assertEqual(sorted(info["bus"]["publish"]), ["region.dock", "region.right"])

    def test_03_subscribe_whitelist_filters_unknown_topics(self) -> None:
        info = self.validate({"subscribe": ["ui.params.changed", "secrets.dump", "theme.changed"]})
        self.assertEqual(
            sorted(info["bus"]["subscribe"]), ["theme.changed", "ui.params.changed"]
        )

    def test_04_topic_lists_are_capped(self) -> None:
        info = self.validate({"subscribe": ["theme.changed"] * 40})
        self.assertLessEqual(len(info["bus"]["subscribe"]), 8)

    def test_05_garbage_bus_field_is_ignored(self) -> None:
        info = self.validate("everything")
        self.assertEqual(info["bus"]["publish"], ["region.dock"])


class DiscoverySurfaceTest(unittest.TestCase):
    def test_01_api_model_carries_stage_and_bus(self) -> None:
        fields = set(InstalledPlugin.model_fields)
        self.assertIn("stage", fields)
        self.assertIn("bus", fields)

    def test_02_shipped_demo_plugin_declares_a_stage(self) -> None:
        """官方示例插件必须真能上舞台，否则这条能力就没有活的样板。"""
        root = Path(__file__).resolve().parents[1]
        source = root / "examples" / "demo_plugin"
        manifest = json.loads((source / "plugin.json").read_text(encoding="utf-8"))
        self.assertIn("stage.center", manifest["slots"])
        self.assertEqual(manifest["stage"]["mode"], "takeover")

        # 目录名必须等于 id，所以复制到临时目录后再走一遍真实校验
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / manifest["id"]
            shutil.copytree(source, target)
            info = validate_plugin(target, manifest)
        self.assertEqual(info["stage"]["mode"], "takeover")
        self.assertIn("region.dock", info["bus"]["publish"])
        self.assertTrue(info["entry_url"].startswith("/plugin-assets/"))


if __name__ == "__main__":
    unittest.main()
