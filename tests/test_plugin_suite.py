"""套件安装与整包同进同退契约（PLUGIN_SPEC §1.8）。

题库引擎退居纯后台后，套件只剩一个成员，这里守四条底线：

1. 套件一次装全部成员；左栏不再出现「九章题库」入口，引擎只经 Host API 供业务插件调用；
2. 包里声明的成员缺一不可，未声明内容一律拒绝且不落残渣；
3. 冲突时整包拒绝，绝不偷偷覆盖已装插件；显式 replace 才整体替换；
4. 套件包不能按单个插件热更新，必须整包安装。

运行：``.venv/Scripts/python.exe -m unittest tests.test_plugin_suite``
"""

from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.core import bank_query, plugin_install, plugin_suite, toml_io
from app.core.plugins import discover_plugins

ROOT = Path(__file__).resolve().parents[1]
ENGINE = "org.jiuzhang.bank-engine"
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
        target = build_tool.build_suite([ROOT / "plugins" / ENGINE], self.out_dir)
        return target.read_bytes()

    def _installed_ids(self) -> list[str]:
        return sorted(path.name for path in self.plugins_dir.iterdir())

    def _suite_zip(
        self,
        members: list[str],
        extra: dict[str, str] | None = None,
        *,
        payload_members: list[str] | None = None,
    ) -> bytes:
        """按套件版式拼一个最小 zip：suite.toml + 指定成员的真实目录。"""
        manifest = {
            "schema_version": "1.0",
            "id": SUITE,
            "name": "九章题库套件",
            "version": "1.0.0",
            "plugins": members,
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("suite.toml", toml_io.dumps(manifest))
            payload = members if payload_members is None else payload_members
            for plugin_id in payload:
                source = ROOT / "plugins" / plugin_id
                for path in sorted(source.rglob("*")):
                    if path.is_file():
                        relative = path.relative_to(source).as_posix()
                        archive.write(path, f"{plugin_id}/{relative}")
            for name, text in (extra or {}).items():
                archive.writestr(name, text)
        return buffer.getvalue()


class BuildSuiteTest(SuiteCase):
    def test_build_suite_packs_the_headless_package(self) -> None:
        target = build_tool.build_suite([ROOT / "plugins" / ENGINE], self.out_dir)
        with zipfile.ZipFile(target) as archive:
            suite = toml_io.loads(archive.read("suite.toml").decode("utf-8"))
            names = set(archive.namelist())
        self.assertEqual([ENGINE], suite["plugins"], "套件只该有题库引擎一个成员")
        self.assertEqual(SUITE, suite["id"])
        self.assertIn(f"{ENGINE}/plugin.toml", names)
        self.assertIn(f"{ENGINE}/bank/schema.sql", names, "纯引擎仍须随包带建库脚本")
        self.assertNotIn(f"{ENGINE}/webui/index.html", names)
        self.assertNotIn(f"{ENGINE}/dev/fixtures.toml", names)

    def test_build_suite_default_members_match_the_official_list(self) -> None:
        self.assertEqual((ENGINE,), build_tool.SUITE_DEFAULT_MEMBERS)


class SuiteInstallTest(SuiteCase):
    def test_install_kit_lands_headless_package_without_sidebar_entry(self) -> None:
        result = plugin_install.install_plugin_from_zip(self._build_suite())

        self.assertEqual(SUITE, result["suite"]["id"])
        self.assertEqual([ENGINE], [info["id"] for info in result["plugins"]])
        self.assertEqual([ENGINE], self._installed_ids())

        report = discover_plugins()
        by_id = {info["id"]: info for info in report["plugins"]}
        engine = by_id[ENGINE]
        self.assertTrue(engine["enabled"])
        self.assertFalse(engine["dependency_blocked"])
        self.assertTrue(engine["headless"])
        self.assertFalse(engine["show_in_sidebar"])
        self.assertEqual("", engine["entry_url"])

        visible = [
            info["id"] for info in report["plugins"]
            if info["enabled"] and info["show_in_sidebar"]
        ]
        self.assertEqual([], visible, "纯引擎不再在左栏占位")
        self.assertEqual([], report["dependency_blocked"])

        items, total = bank_query.list_questions(ENGINE)
        self.assertEqual([], items, "干净环境题库应为空，但引擎必须能正常读")
        self.assertEqual(0, total)

    def test_suite_member_missing_from_payload_is_rejected_without_residue(self) -> None:
        data = self._suite_zip([ENGINE], payload_members=[])
        with self.assertRaises(plugin_install.PluginInstallError) as ctx:
            plugin_install.install_plugin_from_zip(data)
        self.assertIn("不存在", ctx.exception.message)
        self.assertEqual([], self._installed_ids())

    def test_undeclared_top_level_content_is_rejected(self) -> None:
        data = self._suite_zip([ENGINE], {"org.example.extra/x.txt": "x"})
        with self.assertRaises(plugin_install.PluginInstallError) as ctx:
            plugin_install.install_plugin_from_zip(data)
        self.assertIn("未声明", ctx.exception.message)
        self.assertEqual([], self._installed_ids())

    def test_conflict_does_not_overwrite_the_installed_package(self) -> None:
        data = self._build_suite()
        plugin_install.install_plugin_from_zip(data)
        marker = self.plugins_dir / ENGINE / "local-marker.txt"
        marker.write_text("keep me", encoding="utf-8")

        with self.assertRaises(plugin_install.PluginInstallError) as ctx:
            plugin_install.install_plugin_from_zip(data)
        self.assertEqual(409, ctx.exception.status)
        self.assertTrue(marker.is_file(), "冲突时不许覆盖老师已装的包")

        plugin_install.install_plugin_from_zip(data, replace=True)
        self.assertEqual([ENGINE], self._installed_ids())
        self.assertFalse(marker.exists(), "显式 replace 才整体替换")
        self.assertTrue((self.plugins_dir / ENGINE / "plugin.toml").is_file())

    def test_suite_zip_cannot_be_applied_as_single_plugin_update(self) -> None:
        with self.assertRaises(plugin_install.PluginInstallError) as ctx:
            with plugin_install.staged_plugin_from_zip(self._build_suite()):
                pass
        self.assertEqual("suite_package", ctx.exception.code)


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
