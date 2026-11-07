"""套件安装与 requires 硬依赖契约（PLUGIN_SPEC §1.8）。

守的五条底线：

1. 套件包一次装全部成员，左栏仍只有一个带界面的入口（引擎 headless 不占位）；
2. 只装 UI 不装引擎必须整包拒绝——绝不允许出现空壳界面；
3. 引擎被卸载或被停用后，UI 在发现阶段就被按住并给出人话原因；
4. 套件落地中途失败/冲突时不覆盖任何一个已装成员（整包同进同退）；
5. 打包脚本自动做 requires 闭包与拓扑排序，套件里缺依赖直接打不出来。

运行：``.venv/Scripts/python.exe -m unittest tests.test_plugin_suite``
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.core import bank_query, plugin_install, plugin_state, plugin_suite
from app.core.config import plugins_dir
from app.core.plugins import discover_plugins

ROOT = Path(__file__).resolve().parents[1]
ENGINE = "org.jiuzhang.bank-engine"
UI = "org.jiuzhang.bank-ui"
SUITE = "org.jiuzhang.bank-suite"


def _load_build_tool():
    spec = importlib.util.spec_from_file_location(
        "jzo_build_plugin", ROOT / "tools" / "build_plugin.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_tool = _load_build_tool()


class SuiteCase(unittest.TestCase):
    """把 plugins/ 与 data/ 都搬进临时区，绝不碰本机工作区。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.plugins_dir = base / "plugins"
        self.plugins_dir.mkdir()
        self.out_dir = base / "out"
        self._saved = (os.environ.get("JZO_PLUGINS_DIR"), os.environ.get("JZO_DATA_DIR"))
        os.environ["JZO_PLUGINS_DIR"] = str(self.plugins_dir)
        os.environ["JZO_DATA_DIR"] = str(base / "data")
        self.addCleanup(self._restore_env)

    def _restore_env(self) -> None:
        for key, value in zip(
            ("JZO_PLUGINS_DIR", "JZO_DATA_DIR"), self._saved, strict=True
        ):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _build_suite(self) -> bytes:
        target = build_tool.build_suite(
            [ROOT / "plugins" / ENGINE, ROOT / "plugins" / UI], self.out_dir
        )
        return target.read_bytes()

    def _installed_ids(self) -> list[str]:
        return sorted(path.name for path in self.plugins_dir.iterdir())

    def _suite_zip(self, members: list[str], extra: dict[str, str] | None = None) -> bytes:
        """按套件版式拼一个最小 zip：suite.json + 指定成员的真实目录。"""
        manifest = {
            "schema_version": "1.0",
            "id": SUITE,
            "name": "真题题库套件",
            "version": "1.0.0",
            "plugins": members,
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("suite.json", json.dumps(manifest, ensure_ascii=False))
            for plugin_id in members:
                source = ROOT / "plugins" / plugin_id
                for path in sorted(source.rglob("*")):
                    if path.is_file():
                        relative = path.relative_to(source).as_posix()
                        archive.write(path, f"{plugin_id}/{relative}")
            for name, text in (extra or {}).items():
                archive.writestr(name, text)
        return buffer.getvalue()


class BuildSuiteTest(SuiteCase):
    def test_build_suite_is_dependency_ordered_and_complete(self) -> None:
        target = build_tool.build_suite(
            [ROOT / "plugins" / UI, ROOT / "plugins" / ENGINE], self.out_dir
        )
        with zipfile.ZipFile(target) as archive:
            suite = json.loads(archive.read("suite.json"))
            names = set(archive.namelist())
        self.assertEqual([ENGINE, UI], suite["plugins"], "依赖必须排在前面")
        self.assertEqual(SUITE, suite["id"])
        self.assertIn(f"{ENGINE}/plugin.json", names)
        self.assertIn(f"{UI}/plugin.json", names)
        self.assertNotIn(f"{UI}/dev/fixtures.json", names)

    def test_build_suite_rejects_missing_dependency_member(self) -> None:
        with self.assertRaises(build_tool.BuildError) as ctx:
            build_tool.build_suite([ROOT / "plugins" / UI], self.out_dir)
        self.assertIn(ENGINE, str(ctx.exception))


class SuiteInstallTest(SuiteCase):
    def test_install_kit_lands_all_members_with_one_sidebar_entry(self) -> None:
        result = plugin_install.install_plugin_from_zip(self._build_suite())

        self.assertEqual(SUITE, result["suite"]["id"])
        self.assertEqual([ENGINE, UI], [info["id"] for info in result["plugins"]])
        self.assertEqual([ENGINE, UI], self._installed_ids())

        report = discover_plugins()
        by_id = {info["id"]: info for info in report["plugins"]}
        self.assertTrue(by_id[UI]["enabled"])
        self.assertFalse(by_id[UI]["dependency_blocked"])
        self.assertEqual([ENGINE], by_id[UI]["requires"])
        self.assertTrue(by_id[ENGINE]["headless"])
        self.assertFalse(by_id[ENGINE]["show_in_sidebar"])

        visible = [
            info["id"] for info in report["plugins"]
            if info["enabled"] and info["show_in_sidebar"]
        ]
        self.assertEqual([UI], visible, "左栏只该有【真题题库】一个入口")
        self.assertEqual([], report["dependency_blocked"])

        items, total = bank_query.list_questions(ENGINE)
        self.assertEqual([], items, "干净环境题库应为空，但引擎必须能正常读")
        self.assertEqual(0, total)

    def test_install_ui_alone_is_rejected_without_residue(self) -> None:
        ui_zip = build_tool.build_plugin(ROOT / "plugins" / UI, self.out_dir).read_bytes()
        with self.assertRaises(plugin_install.PluginInstallError) as ctx:
            plugin_install.install_plugin_from_zip(ui_zip)
        self.assertEqual("missing_dependency", ctx.exception.code)
        self.assertEqual([], self._installed_ids())

    def test_suite_missing_member_is_rejected_without_residue(self) -> None:
        data = self._suite_zip([UI])
        with self.assertRaises(plugin_install.PluginInstallError) as ctx:
            plugin_install.install_plugin_from_zip(data)
        self.assertEqual("incomplete_suite", ctx.exception.code)
        self.assertEqual([], self._installed_ids())

    def test_undeclared_top_level_content_is_rejected(self) -> None:
        data = self._suite_zip([ENGINE, UI], {"org.example.extra/x.txt": "x"})
        with self.assertRaises(plugin_install.PluginInstallError) as ctx:
            plugin_install.install_plugin_from_zip(data)
        self.assertIn("未声明", ctx.exception.message)
        self.assertEqual([], self._installed_ids())

    def test_conflict_does_not_leave_a_half_installed_suite(self) -> None:
        data = self._build_suite()
        plugin_install.install_plugin_from_zip(data)
        shutil.rmtree(self.plugins_dir / UI)

        with self.assertRaises(plugin_install.PluginInstallError) as ctx:
            plugin_install.install_plugin_from_zip(data)
        self.assertEqual(409, ctx.exception.status)
        self.assertFalse((self.plugins_dir / UI).exists(), "冲突时不许偷偷装另一半")
        self.assertTrue((self.plugins_dir / ENGINE / "plugin.json").is_file())

        plugin_install.install_plugin_from_zip(data, replace=True)
        self.assertEqual([ENGINE, UI], self._installed_ids())

    def test_suite_zip_cannot_be_applied_as_single_plugin_update(self) -> None:
        with self.assertRaises(plugin_install.PluginInstallError) as ctx:
            with plugin_install.staged_plugin_from_zip(self._build_suite()):
                pass
        self.assertEqual("suite_package", ctx.exception.code)


class DependencyDiscoveryTest(SuiteCase):
    def _install(self) -> None:
        plugin_install.install_plugin_from_zip(self._build_suite())

    def test_removed_engine_blocks_ui_at_discovery(self) -> None:
        self._install()
        shutil.rmtree(self.plugins_dir / ENGINE)

        report = discover_plugins()
        ui = next(info for info in report["plugins"] if info["id"] == UI)
        self.assertFalse(ui["enabled"])
        self.assertTrue(ui["dependency_blocked"])
        self.assertEqual([ENGINE], ui["missing_requires"])
        self.assertIn(ENGINE, ui["dependency_error"])
        self.assertEqual([UI], [row["id"] for row in report["dependency_blocked"]])

    def test_disabled_engine_blocks_ui_and_recovers_when_reenabled(self) -> None:
        self._install()
        plugin_state.set_enabled(ENGINE, False)

        ui = next(info for info in discover_plugins()["plugins"] if info["id"] == UI)
        self.assertFalse(ui["enabled"])
        self.assertTrue(ui["dependency_blocked"])
        self.assertIn(ENGINE, ui["missing_requires"])
        self.assertIn("已停用", ui["dependency_error"])

        plugin_state.set_enabled(ENGINE, True)
        ui = next(info for info in discover_plugins()["plugins"] if info["id"] == UI)
        self.assertTrue(ui["enabled"])
        self.assertFalse(ui["dependency_blocked"])
        self.assertEqual("", ui["dependency_error"])


class RequiresContractTest(unittest.TestCase):
    def test_requires_normalization_rules(self) -> None:
        self.assertEqual(["org.example.engine"], plugin_suite.normalize_requires(
            ["org.example.engine"], "org.example.ui"))
        self.assertEqual([], plugin_suite.normalize_requires(None, "org.example.ui"))
        for bad in (["org.example.ui"], ["org.example.ui", "org.example.ui"],
                    ["not a plugin id"], "org.example.engine", ["org.example..x"]):
            with self.assertRaises(ValueError):
                plugin_suite.normalize_requires(bad, "org.example.ui")

    def test_dependency_report_is_transitive(self) -> None:
        plugins = [
            {"id": "org.example.a", "requires": ["org.example.b"]},
            {"id": "org.example.b", "requires": ["org.example.c"]},
            {"id": "org.example.c", "requires": []},
        ]
        report = plugin_suite.dependency_report(plugins[:2], set())
        self.assertEqual({"a", "b"}, {item.rsplit(".", 1)[-1] for item in report})
        self.assertEqual([], report["org.example.a"]["missing"])
        self.assertEqual(["org.example.b"], report["org.example.a"]["blocked"])
        self.assertEqual(["org.example.c"], report["org.example.b"]["missing"])

    def test_cycle_with_all_members_present_is_satisfied(self) -> None:
        plugins = [
            {"id": "org.example.a", "requires": ["org.example.b"]},
            {"id": "org.example.b", "requires": ["org.example.a"]},
        ]
        self.assertEqual({}, plugin_suite.dependency_report(plugins, set()))

    def test_cycle_with_a_missing_member_blocks_the_whole_ring(self) -> None:
        plugins = [
            {"id": "org.example.a", "requires": ["org.example.b"]},
            {"id": "org.example.b", "requires": ["org.example.a", "org.example.c"]},
        ]
        report = plugin_suite.dependency_report(plugins, set())
        self.assertEqual({"org.example.a", "org.example.b"}, set(report))
        self.assertEqual(["org.example.c"], report["org.example.b"]["missing"])


if __name__ == "__main__":
    unittest.main()
