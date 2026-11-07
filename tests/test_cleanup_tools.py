# -*- coding: utf-8 -*-
"""清理脚本的判定逻辑必须有测试钉住：它拿 `shutil.rmtree` 直接动本地磁盘，判错一次就是事故。

军令「本地仓库物理瘦身」（2026-11-02）立了两支脚本——`tools/cleanup_workspace.py`（本机急救）
与 `tools/clean_for_release.py`（发版例行）。本文件只测**决策**（该删谁、该留谁、什么绝对不许碰），
所有落手动作都发生在临时目录里，仓库本体一寸不动。

运行：``.venv/Scripts/python.exe -m unittest tests.test_cleanup_tools``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import clean_for_release as cfr  # noqa: E402 - 开发脚本不是包，按路径导入
from tools import cleanup_workspace as cw  # noqa: E402


def touch(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_newer(path: Path, seconds: int = 3600) -> None:
    stamp = path.stat().st_mtime + seconds
    os.utime(str(path), (stamp, stamp))


class GeneratedDirCase(unittest.TestCase):
    """把 GENERATED_DIR 换到临时目录，tearDown 还原——模块级全局，改完必须复原。"""

    def setUp(self) -> None:
        self._saved = (cw.GENERATED_DIR, cfr.GENERATED_DIR)
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        cw.GENERATED_DIR = self.base
        cfr.GENERATED_DIR = self.base

    def tearDown(self) -> None:
        cw.GENERATED_DIR, cfr.GENERATED_DIR = self._saved
        self.tmp.cleanup()


class GuardrailTest(unittest.TestCase):
    """禁改区护栏：`data/`、`.venv/`、`examples/`、`.git/` 与逃出仓库根的目标一律中止。"""

    def test_01_forbidden_roots_abort(self) -> None:
        for target in (ROOT / "data" / "banks" / "x.db", ROOT / ".venv" / "Lib" / "os.py",
                       ROOT / "examples" / "demo_plugin.zip", ROOT / ".git" / "config"):
            with self.subTest(target=str(target)):
                with self.assertRaises(SystemExit):
                    cw.guard(target)

    def test_02_outside_root_aborts(self) -> None:
        with self.assertRaises(SystemExit):
            cw.guard(ROOT.parent / "somewhere-else" / "plugins.json")

    def test_03_workspace_paths_pass(self) -> None:
        cw.guard(ROOT / ".system_generated" / "editor_probe" / "abc")
        cw.guard(ROOT / "dist" / "jiuzhang-operator-v1.0.0.zip")


class PruneSpineTest(GeneratedDirCase):
    """`.system_generated/` 只留一条 spine——「保留最新目录」会把 840 MB 的历史跑批整块留下。"""

    def test_01_keeps_named_leaf_and_dooms_siblings(self) -> None:
        keeper = touch(self.base / "editor_probe" / "run-green" / "probe.toml", "").parent
        touch(self.base / "editor_probe" / "run-red" / "a.png")
        touch(self.base / "paper_probe" / "old" / "b.png")
        touch(self.base / "loose.log")
        doomed = {str(p.relative_to(self.base)).replace("\\", "/")
                  for p, _, _ in cw.prune_generated(1, keeper)}
        self.assertEqual(doomed, {"editor_probe/run-red", "paper_probe", "loose.log"})

    def test_02_keep_latest_zero_wipes_everything(self) -> None:
        touch(self.base / "a" / "x.png")
        touch(self.base / "b" / "y.png")
        self.assertEqual({p.name for p, _, _ in cw.prune_generated(0, None)}, {"a", "b"})

    def test_03_keeper_outside_generated_is_rejected(self) -> None:
        outside = touch(self.base.parent / "sneaky" / "probe.toml", "").parent
        with self.assertRaises(SystemExit):
            cw.prune_generated(1, outside)


class ProbeVerdictTest(unittest.TestCase):
    """probe.toml 有三种历史 schema 都得认；**认不出就当作不通过**，宁可多留不可误删。"""

    def verdict(self, payload: object) -> tuple[bool, str]:
        with tempfile.TemporaryDirectory() as tmp:
            probe = touch(Path(tmp) / "probe.toml",
                          payload if isinstance(payload, str) else toml_io.dumps(payload))
            return cfr.probe_verdict(probe)

    def test_01_ok_key_all_green(self) -> None:
        self.assertEqual(self.verdict({"checks": [{"name": "a", "ok": True}, {"name": "b", "ok": True}]}),
                         (True, "2/2 判据通过"))

    def test_02_passed_key_with_one_red(self) -> None:
        self.assertEqual(self.verdict({"checks": [{"name": "a", "passed": True},
                                                  {"name": "b", "passed": False}]}),
                         (False, "1/2 判据通过"))

    def test_03_summary_only_counts(self) -> None:
        self.assertTrue(self.verdict({"passed": 153, "total": 153})[0])
        self.assertFalse(self.verdict({"passed": 24, "total": 25})[0])

    def test_04_unknown_schema_and_broken_toml_are_not_pass(self) -> None:
        self.assertFalse(self.verdict({"result": "也许行了"})[0])
        self.assertFalse(self.verdict("[[[不是 toml")[0])


class LatestPassingRunTest(GeneratedDirCase):
    """发版脚本留的是「最近一次全绿的跑批」，不是「时间最新的产物」。"""

    def test_01_picks_green_over_newer_red(self) -> None:
        green = touch(self.base / "editor_probe" / "run-1" / "probe.toml",
                      toml_io.dumps({"checks": [{"name": "a", "ok": True}]})).parent
        red = touch(self.base / "paper_probe" / "run-2" / "probe.toml",
                    toml_io.dumps({"checks": [{"name": "a", "ok": False}]})).parent
        make_newer(red)
        keeper, note = cfr.latest_passing_run()
        self.assertEqual(keeper, green)
        self.assertIn("1/1 判据通过", note)

    def test_02_no_green_means_wipe_all(self) -> None:
        touch(self.base / "only" / "probe.toml",
              toml_io.dumps({"checks": [{"name": "a", "ok": False}]}))
        keeper, note = cfr.latest_passing_run()
        self.assertIsNone(keeper)
        self.assertIn("没有一份是全绿的", note)


class ArchiveFamilyTest(unittest.TestCase):
    """发行包同族只留最新：版本号尾巴相同的算同族；插件包另按源码新鲜度判。"""

    def test_01_version_tail_strip(self) -> None:
        self.assertEqual(cw.VERSION_TAIL.sub("", "jiuzhang-operator-beta-v0.11.2"), "jiuzhang-operator-beta")
        self.assertEqual(cw.VERSION_TAIL.sub("", "jiuzhang-operator-v1.0.0"), "jiuzhang-operator")
        self.assertEqual(cw.VERSION_TAIL.sub("", "jiuzhang-dev-kit"), "jiuzhang-dev-kit")

    def test_02_non_plugin_zip_is_not_a_plugin_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = touch(Path(tmp) / "jiuzhang-operator-v9.9.9.zip")
            self.assertEqual(cw.plugin_zip_state(path), (False, None))

    def test_03_retired_plugin_zip_reports_no_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = touch(Path(tmp) / "org.jiuzhang.no-such-plugin.zip")
            self.assertEqual(cw.plugin_zip_state(path), (True, None))


if __name__ == "__main__":
    unittest.main()
