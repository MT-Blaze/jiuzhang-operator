"""发行包纯净度与同级插件目录发现契约。

2026-11-13 第十令：install.bat 改为「底座 Release 纯净包 + 插件仓库 main
源码」双文件夹安装。底座目录不再带 plugins/，必须靠
``PROJECT_ROOT.parent / "jiuzhang-plugins" / "src"`` 自动发现插件。
本模块把这两件事钉死：发行脚本不许再打包开发目录，路径解析不许丢同级探测。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core import config

ROOT = Path(__file__).resolve().parents[1]


class ReleaseBuilderPurityTest(unittest.TestCase):
    """build_release.bat 只产运行树，开发目录与插件源码一律不进包。"""

    def setUp(self) -> None:
        self.raw = (ROOT / "build_release.bat").read_bytes()
        self.text = self.raw.decode("ascii")

    def test_01_ascii_only_with_crlf(self) -> None:
        self.assertEqual(self.text.count("\r\n"), self.text.count("\n"))
        self.assertGreater(self.text.count("\r\n"), 100)

    def test_02_excludes_dev_trees(self) -> None:
        xd = " ".join(line for line in self.text.splitlines() if "/XD" in line)
        for name in (
            ".qoder", "tests", "tools", "scripts", "examples", "docs",
            "data", "plugins", ".venv", ".git",
        ):
            self.assertIn(name, xd, f"/XD 没排除 {name}，发行包会带开发文件")

    def test_03_no_plugin_source_staging(self) -> None:
        self.assertNotIn("PLUGIN_SRC", self.text, "发行包不再装配插件源码")
        self.assertNotIn("Staging plugin source", self.text)

    def test_04_emits_stable_latest_download_asset(self) -> None:
        self.assertIn('set "STABLE=%OUTDIR%\\jiuzhang-operator.zip"', self.text)
        self.assertIn('copy /Y "%ZIP%" "%STABLE%"', self.text,
                      "必须产出 latest/download 使用的稳定资产名")

    def test_05_installer_scripts_not_shipped(self) -> None:
        xf = " ".join(line for line in self.text.splitlines() if "/XF" in line)
        self.assertIn("install.bat", xf)
        self.assertIn("build_release.bat", xf)


class SiblingPluginDiscoveryTest(unittest.TestCase):
    """双文件夹布局下，底座必须认 ../jiuzhang-plugins/src。"""

    def _layout(self, tmp: str) -> tuple[Path, Path, Path]:
        root = Path(tmp)
        base = root / "jiuzhang-operator"
        src = root / "jiuzhang-plugins" / "src"
        plugin = src / "org.jiuzhang.bank-engine"
        plugin.mkdir(parents=True)
        (plugin / "plugin.toml").write_text('id = "org.jiuzhang.bank-engine"\n', encoding="utf-8")
        base.mkdir()
        return root, base, src

    def test_01_sibling_src_used_without_bundled_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _root, base, src = self._layout(tmp)
            env = {"JZO_PLUGIN_SOURCE_DIR": "", "JZO_PLUGINS_DIR": ""}
            with mock.patch.dict(os.environ, env), mock.patch.object(
                config, "PROJECT_ROOT", base
            ):
                self.assertEqual(config.plugin_source_root(), src)
                self.assertEqual(config.plugins_dir(), src)

    def test_02_bundled_plugins_still_wins_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _root, base, _src = self._layout(tmp)
            bundled = base / "plugins"
            bundled.mkdir()
            env = {"JZO_PLUGIN_SOURCE_DIR": "", "JZO_PLUGINS_DIR": ""}
            with mock.patch.dict(os.environ, env), mock.patch.object(
                config, "PROJECT_ROOT", base
            ):
                self.assertEqual(config.plugin_source_root(), bundled)
                self.assertEqual(config.plugins_dir(), bundled)


if __name__ == "__main__":
    unittest.main()
