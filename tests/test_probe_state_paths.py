"""探针偏好还原判据的路径契约（军令 #21 任务六）。

根 ``data/plugin_state.json`` 是 ADR-012 之前的历史遗留，宿主只读
``<data>/workspaces/<区>/plugin_state.json``。探针拿旧路径比对，等于对着一份
没人看的文件宣布「已还原」。这里钉死三件事：
  1. ``JZO_STATE_FILE`` 显式指路优先；
  2. 否则按 ``JZO_DATA_DIR`` + ``current_workspace`` 指针解析；
  3. 指针缺失/非法回落 default，且永不返回根目录那份幽灵文件。

运行：``.venv/Scripts/python.exe -m unittest tests.test_probe_state_paths``
"""

from __future__ import annotations

import contextlib
import os
import tempfile
import unittest
from pathlib import Path

from tools.probe_paths import resolve_plugin_state_file

ROOT = Path(__file__).resolve().parents[1]
PROBES = (ROOT / "tools" / "console_panel_probe.py", ROOT / "tools" / "tab_group_probe.py")


@contextlib.contextmanager
def env(**values: str):
    keys = ("JZO_STATE_FILE", "JZO_DATA_DIR")
    saved = {key: os.environ.pop(key, None) for key in keys}
    try:
        os.environ.update(values)
        yield
    finally:
        for key in keys:
            os.environ.pop(key, None)
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value


class ResolveStateFileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        (self.data / "workspaces" / "default").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_01_explicit_state_file_wins(self) -> None:
        target = Path(self.tmp.name) / "explicit" / "plugin_state.json"
        with env(JZO_STATE_FILE=str(target), JZO_DATA_DIR=str(self.data)):
            self.assertEqual(resolve_plugin_state_file(), target)

    def test_02_data_dir_plus_pointer(self) -> None:
        (self.data / "workspaces" / "ws_abc123").mkdir()
        (self.data / "current_workspace").write_text("ws_abc123\n", encoding="utf-8")
        with env(JZO_DATA_DIR=str(self.data)):
            self.assertEqual(
                resolve_plugin_state_file(),
                self.data / "workspaces" / "ws_abc123" / "plugin_state.json",
            )

    def test_03_missing_or_illegal_pointer_falls_back_to_default(self) -> None:
        with env(JZO_DATA_DIR=str(self.data)):
            self.assertEqual(
                resolve_plugin_state_file(),
                self.data / "workspaces" / "default" / "plugin_state.json",
            )
        (self.data / "current_workspace").write_text("../escape\n", encoding="utf-8")
        with env(JZO_DATA_DIR=str(self.data)):
            self.assertEqual(
                resolve_plugin_state_file(),
                self.data / "workspaces" / "default" / "plugin_state.json",
            )

    def test_04_never_reads_legacy_root_file(self) -> None:
        (self.data / "plugin_state.json").write_text('{"nicknames": {"x": "y"}}', encoding="utf-8")
        with env():
            resolved = resolve_plugin_state_file(self.data)
        self.assertEqual(resolved, self.data / "workspaces" / "default" / "plugin_state.json")
        self.assertNotEqual(resolved, self.data / "plugin_state.json")

    def test_05_explicit_root_argument(self) -> None:
        with env():
            resolved = resolve_plugin_state_file(self.data)
        self.assertEqual(resolved, self.data / "workspaces" / "default" / "plugin_state.json")


class ProbeSourceContractTest(unittest.TestCase):
    def test_01_both_probes_use_the_resolver(self) -> None:
        for probe in PROBES:
            source = probe.read_text(encoding="utf-8")
            self.assertIn("from probe_paths import resolve_plugin_state_file", source, probe.name)
            self.assertIn("resolve_plugin_state_file(", source, probe.name)

    def test_02_no_probe_defaults_to_the_ghost_file(self) -> None:
        for probe in PROBES:
            source = probe.read_text(encoding="utf-8")
            self.assertNotIn('ROOT / "data" / "plugin_state.json"', source, probe.name)
            self.assertNotIn('"data" / "plugin_state.json"', source, probe.name)

    def test_03_console_reads_state_file_for_restore_check(self) -> None:
        source = (ROOT / "tools" / "console_panel_probe.py").read_text(encoding="utf-8")
        self.assertIn("state_file.read_text", source)
        self.assertIn("state_clean", source)
        self.assertIn("隔离工作区状态文件", source)


if __name__ == "__main__":
    unittest.main()
