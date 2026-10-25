"""官方插件的 bus.subscribe 与代码监听必须逐字全等（#18-结 第七条遗留）。

三段判据，缺一不算收口：
- **清单 == 代码**：``plugin.json`` 的 ``bus.subscribe`` 与 ``dist/plugin.js`` 里真的按 ``event``
  分支处理的主题集合必须完全相等——多写是假授权，少写是暗通道；
- **声明即生效**：声明的每个主题必须活在宿主白名单里，装上后一条不许被 ``_normalize_bus`` 丢弃；
- **投递可达**：代码处理的每个主题必须能在 ``static/js`` 里找到宿主的一次 ``broadcast``/``notify``，
  否则那条分支永远不触发（``stage.tab.*`` 就是这么断掉右栏助手清快照的）。

扫描器本身带负向对照，防止「扫不到」被当成「没问题」。

运行：``.venv/Scripts/python.exe -m unittest tests.test_plugin_bus_parity``
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from app.core.plugins import _normalize_bus

ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = ROOT / "plugins"
HOST_JS = sorted((ROOT / "static" / "js").glob("*.js"))

HANDLED = re.compile(r"\.event\s*(?:===|==)\s*[\"']([A-Za-z0-9_.]+)[\"']")
DELIVERED = re.compile(r"\b(?:broadcast|notify)\(\s*(?:[^,()]+,\s*)?[\"']([A-Za-z0-9_.]+)[\"']")


def official_plugins() -> list[Path]:
    return sorted(p for p in PLUGINS_DIR.glob("org.jiuzhang.*") if (p / "plugin.json").is_file())


def handled_topics(plugin_dir: Path) -> set[str]:
    found: set[str] = set()
    for js in (plugin_dir / "dist").glob("*.js"):
        found |= set(HANDLED.findall(js.read_text(encoding="utf-8")))
    return found


def declared_topics(plugin_dir: Path) -> set[str]:
    manifest = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
    return set((manifest.get("bus") or {}).get("subscribe") or [])


def delivered_topics() -> set[str]:
    found: set[str] = set()
    for js in HOST_JS:
        found |= set(DELIVERED.findall(js.read_text(encoding="utf-8")))
    return found


class BusParityContract(unittest.TestCase):
    def setUp(self) -> None:
        self.plugins = official_plugins()
        self.assertTrue(self.plugins, "plugins/ 下必须扫到官方插件目录")
        self.delivered = delivered_topics()

    def test_01_scanner_is_not_vacuous(self) -> None:
        """负向对照：扫描器必须真能分辨「多声明」「少声明」两种漂移。"""
        self.assertEqual(
            set(HANDLED.findall('a.addEventListener(function(e){ m.event === "p.q"; if (m.event == "r.s") {} });')),
            {"p.q", "r.s"},
        )
        self.assertNotIn("secrets.dump", self.delivered)
        self.assertTrue(self.delivered, "宿主投递主题扫成空集说明判据失效")

    def test_02_manifest_matches_known_shape(self) -> None:
        """官方插件至少要覆盖这批主题，缺一个说明扫描或清单被动过手脚。"""
        expect = {
            "org.jiuzhang.chat": {"stage.tab.activated", "stage.tab.closed", "stage.selection",
                                  "question.updated", "plugin.updated", "panel.button.click"},
            "org.jiuzhang.bank-engine": set(),
            "org.jiuzhang.bank-ui": {"ui.params.changed", "system.question_updated",
                                     "question.updated", "system.bank_query"},
            "org.jiuzhang.dashboard": {"question.updated", "system.question_updated"},
            "org.jiuzhang.editor": {"system.open_editor", "ui.params.changed", "editor.apply_patch"},
            "org.jiuzhang.handout": {"ui.params.changed", "system.question_updated", "question.updated"},
            "org.jiuzhang.paper-gen": {"ui.params.changed", "basket.changed",
                                       "system.question_updated", "question.updated"},
        }
        for plugin_dir in self.plugins:
            with self.subTest(plugin=plugin_dir.name):
                self.assertEqual(declared_topics(plugin_dir), expect[plugin_dir.name])

    def test_03_declared_equals_handled(self) -> None:
        for plugin_dir in self.plugins:
            with self.subTest(plugin=plugin_dir.name):
                declared, handled = declared_topics(plugin_dir), handled_topics(plugin_dir)
                self.assertEqual(
                    declared, handled,
                    f"声明未处理={sorted(declared - handled)} 处理未声明={sorted(handled - declared)}")

    def test_04_every_declaration_survives_normalize(self) -> None:
        for plugin_dir in self.plugins:
            with self.subTest(plugin=plugin_dir.name):
                declared = sorted(declared_topics(plugin_dir))
                info = _normalize_bus({"subscribe": declared, "publish": ["region.dock"]})
                self.assertEqual(sorted(info["subscribe"]), declared,
                                 "有主题被宿主白名单静默丢弃：清单写着、通道却不存在")

    def test_05_every_handler_is_reachable(self) -> None:
        for plugin_dir in self.plugins:
            with self.subTest(plugin=plugin_dir.name):
                silent = sorted(handled_topics(plugin_dir) - self.delivered)
                self.assertEqual(silent, [], "这些主题宿主压根不投递，代码分支永远不触发")


if __name__ == "__main__":
    unittest.main()
