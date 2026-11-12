"""军令 #34 契约：插件全局化、工作区只存数据。

钉四件事：

1. 当前工作区指针缺失/损坏/非法一律回落 default，坏指针不能挡住启动；
2. ``plugins_dir()`` 与当前工作区无关：显式覆盖 → 底座根 ``plugins/`` →
   兄弟仓库 ``src/``；工作区切换后仍指向同一份代码；
3. 各状态文件与 ``.env`` 落点跟着当前工作区实时求值；新工作区只生成
   ``banks/`` 与空 ``plugin_state.toml``，**绝不生成 ``plugins/``**；
4. 旧根 ``data/`` 下的宿主状态仍迁入 default 工作区；删除工作区整目录进回收站。

运行：``.venv/Scripts/python.exe -m unittest tests.test_workspace_isolation``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))


import asyncio
import base64
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from app.api import workspaces as workspaces_api
from app.core import bank_provider, plugin_state, plugin_update, startup_prefs, toml_io, wire
from app.core import config, workspace_bootstrap, workspace_paths, workspace_removal
from app.core.config import current_workspace_id, env_file_path, plugins_dir, settings

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = "org.jiuzhang.bank-engine"


def _http_request(port: int | None = None):
    """端点新增的 Request 参数只用来取重启端口；进程内直调给个替身即可。"""
    return SimpleNamespace(url=SimpleNamespace(port=port))


class _TempEnv(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self._saved_ws = settings.workspace_id
        self._saved_env = {key: os.environ.get(key)
                           for key in ("JZO_DATA_DIR", "JZO_PLUGINS_DIR", "JZO_ENV_FILE",
                                       "JZO_RESTART_DISABLED")}
        os.environ["JZO_DATA_DIR"] = str(self.data)
        # 进程内直接调端点：决不能让切库端点把跑测试的进程自己重启掉。
        os.environ["JZO_RESTART_DISABLED"] = "1"
        os.environ.pop("JZO_PLUGINS_DIR", None)
        os.environ.pop("JZO_ENV_FILE", None)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        settings.workspace_id = self._saved_ws
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class PointerTest(_TempEnv):
    def test_01_missing_pointer_falls_back_to_default(self) -> None:
        self.assertEqual("", workspace_paths.read_current_workspace_pointer())
        self.assertEqual("default", current_workspace_id())

    def test_02_corrupt_or_illegal_pointer_falls_back_to_default(self) -> None:
        pointer = workspace_paths.current_workspace_pointer_path()
        for bad in ("../escape", "ws/a", "", "删我", "ws_ok\n../evil"):
            pointer.write_text(bad, encoding="utf-8")
            self.assertEqual("", workspace_paths.read_current_workspace_pointer(), repr(bad))

    def test_03_write_is_atomic_and_round_trips(self) -> None:
        path = workspace_paths.write_current_workspace_pointer("ws_abc123")
        self.assertEqual("ws_abc123\n", path.read_text(encoding="utf-8"))
        self.assertEqual("ws_abc123", workspace_paths.read_current_workspace_pointer())
        self.assertFalse((self.data / "current_workspace.tmp").exists(), "临时文件必须被替换掉")
        with self.assertRaises(ValueError):
            workspace_paths.write_current_workspace_pointer("../evil")


class DynamicPathTest(_TempEnv):
    def test_01_plugins_dir_is_global_not_workspace_scoped(self) -> None:
        """切工作区不得改变插件目录：全机只有一份代码。"""
        global_plugins = self.root / "global-plugins"
        global_plugins.mkdir()
        os.environ["JZO_PLUGINS_DIR"] = str(global_plugins)
        settings.workspace_id = None
        first = plugins_dir()
        settings.workspace_id = "ws_alpha"
        self.assertEqual(first, plugins_dir(), "插件代码全局一份，不跟工作区走")
        self.assertEqual(global_plugins, first, "显式覆盖口子必须优先")

    def test_02_plugins_dir_prefers_bundled(self) -> None:
        fake_project = self.root / "project"
        fake_project.mkdir()
        bundled = fake_project / "plugins"
        bundled.mkdir()
        sibling_src = fake_project.parent / "jiuzhang-plugins" / "src"
        sibling_src.mkdir(parents=True)
        with mock.patch.object(config, "PROJECT_ROOT", fake_project):
            os.environ.pop("JZO_PLUGINS_DIR", None)
            self.assertEqual(bundled, plugins_dir(), "有底座根 plugins/ 时必须优先")

    def test_03_plugins_dir_falls_back_to_sibling_source(self) -> None:
        fake_project = self.root / "project"
        fake_project.mkdir()
        sibling_src = fake_project.parent / "jiuzhang-plugins" / "src"
        sibling_src.mkdir(parents=True)
        with mock.patch.object(config, "PROJECT_ROOT", fake_project):
            os.environ.pop("JZO_PLUGINS_DIR", None)
            self.assertEqual(sibling_src, plugins_dir(), "开发树无根插件目录时直读兄弟仓库源码")

    def test_04_every_state_file_lives_in_the_current_workspace(self) -> None:
        settings.workspace_id = "ws_alpha"
        expected = self.data / "workspaces" / "ws_alpha"
        self.assertEqual(expected / plugin_state.STATE_FILENAME, plugin_state._state_path())
        self.assertEqual(expected / startup_prefs.STATE_FILENAME, startup_prefs.state_path())
        self.assertEqual(expected / bank_provider.STATE_FILENAME, bank_provider.state_path())
        self.assertEqual(expected / plugin_update.PENDING_FILENAME, plugin_update.pending_path())

    def test_05_env_file_follows_current_workspace_and_override(self) -> None:
        settings.workspace_id = None
        self.assertEqual(self.data / "workspaces" / "default" / ".env", env_file_path())
        settings.workspace_id = "ws_alpha"
        self.assertEqual(self.data / "workspaces" / "ws_alpha" / ".env", env_file_path())
        os.environ["JZO_ENV_FILE"] = str(self.root / "custom.env")
        self.assertEqual(self.root / "custom.env", env_file_path())

    def test_06_workspace_data_dir_keeps_default_history_layout(self) -> None:
        self.assertEqual(self.data, workspace_paths.workspace_data_dir("default"))
        self.assertEqual(self.data / "workspaces" / "ws_alpha",
                         workspace_paths.workspace_data_dir("ws_alpha"))


class LayoutTest(_TempEnv):
    def test_01_new_workspace_gets_banks_and_empty_state_but_no_plugins(self) -> None:
        root = workspace_bootstrap.ensure_workspace_layout("ws_fresh")
        self.assertEqual(self.data / "workspaces" / "ws_fresh", root)
        self.assertTrue((root / "banks").is_dir(), "工作区必须有自己的物理题库目录")
        self.assertFalse((root / "plugins").exists(), "插件代码全局一份，工作区绝不建 plugins/")
        self.assertEqual("", (root / "plugin_state.toml").read_text(encoding="utf-8"))

    def test_02_rebootstrap_never_overwrites_user_state(self) -> None:
        root = workspace_bootstrap.ensure_workspace_layout("ws_fresh")
        state = root / "plugin_state.toml"
        state.write_text("org.x.y = false\n", encoding="utf-8")
        workspace_bootstrap.ensure_workspace_layout("ws_fresh")
        self.assertEqual("org.x.y = false\n", state.read_text(encoding="utf-8"))

    def test_03_create_workspace_lands_banks_state_and_no_plugins(self) -> None:
        old_pointer = workspace_paths.read_current_workspace_pointer()
        result = asyncio.run(workspaces_api.create_workspace(
            workspaces_api.WorkspaceCreateRequest(name="隔离区"), _http_request()))
        workspace_id = result["id"]
        self.assertFalse(result["restarting"], "JZO_RESTART_DISABLED=1 必须让进程活着回包")
        storage = self.data / "workspaces" / workspace_id
        self.assertTrue((storage / "banks").is_dir(), "新工作区必须有独立题库目录")
        self.assertFalse((storage / "plugins").exists(), "新工作区不得生成插件副本")
        self.assertEqual("", (storage / "plugin_state.toml").read_text(encoding="utf-8"))
        registry = toml_io.load(self.data / "workspaces.toml").get("workspaces", [])
        self.assertIn(workspace_id, [row["id"] for row in registry])
        self.assertEqual(workspace_id, workspace_paths.read_current_workspace_pointer())
        self.assertEqual(workspace_id, settings.workspace_id)
        if old_pointer:
            workspace_paths.write_current_workspace_pointer(old_pointer)

    def test_04_import_workspace_lands_banks_state_and_no_plugins(self) -> None:
        source = self.root / "source.db"
        schema = (ROOT / "app" / "legacy" / "bank_schema_v1.sql").read_text(encoding="utf-8")
        con = sqlite3.connect(source)
        try:
            con.executescript(schema)
            now = "2026-10-24T00:00:00+08:00"
            con.execute(
                "INSERT INTO questions (id,type,stem,options,answer,solution,extensions,"
                "difficulty,created_at,updated_at) VALUES (?,'fill_blank','导入题','[]',"
                "NULL,NULL,'[]','L1',?,?)",
                ("q_import_0001", now, now),
            )
            con.commit()
        finally:
            con.close()
        blob = base64.b64encode(source.read_bytes()).decode("ascii")
        result = asyncio.run(workspaces_api.import_workspace(
            workspaces_api.WorkspaceImportRequest(name="导入区", db_base64=blob), _http_request()))
        workspace_id = result["id"]
        self.assertFalse(result["restarting"], "受控环境不该真的重启进程")
        storage = self.data / "workspaces" / workspace_id
        self.assertTrue((storage / "banks").is_dir())
        self.assertFalse((storage / "plugins").exists())
        self.assertEqual("", (storage / "plugin_state.toml").read_text(encoding="utf-8"))
        self.assertTrue((storage / "banks" / f"{PROVIDER}.db").is_file())
        self.assertEqual(1, result["question_count"])


class StateMigrationTest(unittest.TestCase):
    """旧根 data/ 状态迁移：开发树复制、发行包移动、目标已存在只补缺。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fake_project = self.root / "project"
        self.fake_project.mkdir()
        self.data = self.root / "data"
        self.data.mkdir()
        saved_plugins_env = os.environ.pop("JZO_PLUGINS_DIR", None)
        if saved_plugins_env is not None:
            self.addCleanup(os.environ.__setitem__, "JZO_PLUGINS_DIR", saved_plugins_env)
        self._env = mock.patch.dict(os.environ, {"JZO_DATA_DIR": str(self.data)})
        self._env.start()
        self.addCleanup(self._env.stop)
        self._patches = [
            mock.patch.object(workspace_bootstrap, "PROJECT_ROOT", self.fake_project),
            mock.patch.object(workspace_bootstrap, "_isolated_run", lambda: False),
            mock.patch.object(workspace_bootstrap, "LEGACY_ENV_FILE", self.fake_project / ".env"),
        ]
        for patch in self._patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_01_state_files_move_into_default_workspace(self) -> None:
        names = [plugin_state.STATE_FILENAME, startup_prefs.STATE_FILENAME,
                 bank_provider.STATE_FILENAME, plugin_update.PENDING_FILENAME]
        for name in names:
            (self.data / name).write_text("k = 1\n", encoding="utf-8")
        (self.fake_project / ".env").write_text("JZO_AI_API_KEY=x\n", encoding="utf-8")
        moved = workspace_bootstrap._migrate_legacy_state()
        default_root = self.data / "workspaces" / "default"
        self.assertEqual(sorted(names + [".env"]), sorted(moved))
        for name in names:
            self.assertTrue((default_root / name).is_file())
            self.assertFalse((self.data / name).exists(), "迁移后旧位置不得留副本")
        self.assertFalse((self.fake_project / ".env").exists())

    def test_02_existing_state_is_never_overwritten(self) -> None:
        (self.fake_project / ".git").mkdir()
        (self.data / plugin_state.STATE_FILENAME).write_text("old = true\n", encoding="utf-8")
        default_root = self.data / "workspaces" / "default"
        default_root.mkdir(parents=True)
        kept = default_root / plugin_state.STATE_FILENAME
        kept.write_text("new = true\n", encoding="utf-8")
        moved = workspace_bootstrap._migrate_legacy_state()
        self.assertEqual([], moved)
        self.assertEqual("new = true\n", kept.read_text(encoding="utf-8"))
        self.assertTrue((self.data / plugin_state.STATE_FILENAME).is_file(), "源文件保留待人工确认")


class BootstrapEnvTest(_TempEnv):
    def test_01_bootstrap_writes_pointer_and_layout_without_plugins(self) -> None:
        result = workspace_bootstrap.bootstrap()
        self.assertEqual("default", result["workspace_id"])
        self.assertEqual("default\n",
                         workspace_paths.current_workspace_pointer_path().read_text(encoding="utf-8"))
        default_root = self.data / "workspaces" / "default"
        self.assertTrue((default_root / "banks").is_dir())
        self.assertFalse((default_root / "plugins").exists(), "自举不得生成插件副本")
        self.assertEqual("", (default_root / "plugin_state.toml").read_text(encoding="utf-8"))

    def test_02_bootstrap_loads_only_current_workspace_env_and_explicit_wins(self) -> None:
        pointer = workspace_paths.current_workspace_pointer_path()
        pointer.write_text("ws_alpha\n", encoding="utf-8")
        alpha = self.data / "workspaces" / "ws_alpha"
        alpha.mkdir(parents=True)
        (alpha / ".env").write_text("JZO_PROBE_KEY=from-workspace\nJZO_LOCAL_TOKEN=file-token\n",
                                    encoding="utf-8")
        os.environ["JZO_LOCAL_TOKEN"] = "explicit-token"
        self.addCleanup(os.environ.pop, "JZO_PROBE_KEY", None)
        self.addCleanup(os.environ.pop, "JZO_LOCAL_TOKEN", None)
        result = workspace_bootstrap.bootstrap()
        self.assertEqual("ws_alpha", result["workspace_id"])
        self.assertIn("JZO_PROBE_KEY", result["env_loaded"])
        self.assertEqual("from-workspace", os.environ["JZO_PROBE_KEY"])
        self.assertEqual("explicit-token", os.environ["JZO_LOCAL_TOKEN"], "显式环境变量优先")
        self.assertTrue((alpha / "banks").is_dir(), "当前工作区也要补齐结构")
        self.assertFalse((alpha / "plugins").exists())

    def test_03_load_env_never_returns_values(self) -> None:
        path = self.root / "probe.env"
        path.write_text("# 注释\nJZO_SECRET=abc123\n这一行没有等号\n", encoding="utf-8")
        loaded = workspace_bootstrap.load_env_file(path)
        self.assertEqual(["JZO_SECRET"], list(loaded), "只回键名，不回凭据值")
        self.assertEqual("abc123", os.environ["JZO_SECRET"])
        self.addCleanup(os.environ.pop, "JZO_SECRET", None)


class DeleteWorkspaceTest(_TempEnv):
    def test_delete_recycles_the_whole_workspace(self) -> None:
        workspace_id = "ws_abcdef01"
        storage = self.data / "workspaces" / workspace_id
        (storage / "banks").mkdir(parents=True)
        (storage / "banks" / "bank.db").write_text("x", encoding="utf-8")
        (storage / "plugin_state.toml").write_text("", encoding="utf-8")
        with mock.patch.object(workspace_removal, "send_to_recycle_bin") as recycle:
            result = workspace_removal.recycle_workspace(workspace_id)
        recycle.assert_called_once()
        recycled = Path(recycle.call_args.args[0])
        self.assertEqual(storage, recycled)
        self.assertTrue((recycled / "banks" / "bank.db").is_file(),
                        "题库必须随工作区目录一起进回收站")
        self.assertEqual(workspace_id, result["workspace_id"])
        audit = toml_io.load(self.data / workspace_removal.AUDIT_FILENAME)["records"]
        self.assertEqual("success", audit[-1]["result"])

    def test_delete_refuses_paths_outside_the_workspace_root(self) -> None:
        with self.assertRaises(workspace_removal.WorkspaceRemovalError):
            workspace_removal.workspace_path("../default")
        with self.assertRaises(workspace_removal.WorkspaceRemovalError):
            workspace_removal.workspace_path("default")


if __name__ == "__main__":
    unittest.main()
