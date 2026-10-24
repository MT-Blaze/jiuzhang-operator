"""插件管理与控制台契约：v0.8.0 军令「子龙」。

覆盖三态与导入的可判定部分：
1. show_in_sidebar：显式 false 生效、缺省 true，且 discover 每条带 enabled。
2. 启停状态落盘（plugin_state），新装默认启用。
3. 卸载两口径：保留数据只删代码目录；彻底删除连各工作区物理 .db 一起销毁（越界拒）。
4. 工作区导入：合法 7 表 .db → 建新工作区并切换；非库 / 缺表 → 拒绝且不留半成品。

运行：``.venv/Scripts/python.exe -m unittest tests.test_plugin_console``
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from app.core import plugin_lifecycle, plugin_state
from app.core.config import root_data_dir, settings
from app.core.plugins import discover_plugins, validate_plugin

ROOT = Path(__file__).resolve().parents[1]


def _make_bank_db(path: Path, questions: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript((ROOT / "plugins" / "org.jiuzhang.core-bank" / "bank" / "schema.sql").read_text(encoding="utf-8"))
        now = "2026-10-24T00:00:00+08:00"
        for index in range(questions):
            con.execute(
                "INSERT INTO questions (id,type,stem,options,answer,solution,extensions,difficulty,created_at,updated_at)"
                " VALUES (?,'fill_blank',?,'[]',NULL,NULL,'[]','L1',?,?)",
                (f"q_imp_{index:04d}", f"导入题 {index}", now, now),
            )
        con.commit()
    finally:
        con.close()


class ShowInSidebarContractTest(unittest.TestCase):
    def _manifest(self, plugin_dir: Path) -> dict:
        return validate_plugin(plugin_dir, json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8")))

    def test_explicit_false_and_default_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "org.jiuzhang.dashboard"
            shutil.copytree(ROOT / "plugins" / "org.jiuzhang.dashboard", sample)
            manifest_path = sample / "plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["show_in_sidebar"] = False
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            self.assertIs(self._manifest(sample)["show_in_sidebar"], False)
        self.assertIs(self._manifest(ROOT / "plugins" / "org.jiuzhang.core-bank")["show_in_sidebar"], True)

    def test_discover_tags_enabled_flag(self) -> None:
        data = discover_plugins()
        for plugin in data["plugins"]:
            self.assertIn("enabled", plugin)
            self.assertIsInstance(plugin["enabled"], bool)
            self.assertIsInstance(plugin["show_in_sidebar"], bool)


class PluginStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self._saved = settings.workspace_id, __import__("os").environ.get("JZO_DATA_DIR")
        __import__("os").environ["JZO_DATA_DIR"] = self.tmp.name
        settings.workspace_id = None

    def tearDown(self) -> None:
        ws, data = self._saved
        if data is None:
            __import__("os").environ.pop("JZO_DATA_DIR", None)
        else:
            __import__("os").environ["JZO_DATA_DIR"] = data
        settings.workspace_id = ws
        self.tmp.cleanup()

    def test_new_plugin_enabled_by_default_and_toggle_persists(self) -> None:
        self.assertTrue(plugin_state.is_enabled("org.jiuzhang.any"))
        plugin_state.set_enabled("org.jiuzhang.any", False)
        self.assertFalse(plugin_state.is_enabled("org.jiuzhang.any"))
        # 状态真的落盘（不是只存内存）
        persisted = json.loads((Path(self.tmp.name) / "plugin_state.json").read_text(encoding="utf-8"))
        self.assertIn("org.jiuzhang.any", persisted["disabled"])
        plugin_state.set_enabled("org.jiuzhang.any", True)
        self.assertTrue(plugin_state.is_enabled("org.jiuzhang.any"))

    def test_disable_never_touches_code_or_data(self) -> None:
        """ADR-007 禁令锁：停用只改 plugin_state.json，代码与 data/ 必须一根汗毛都不能动。

        判据取整棵树快照（相对路径 + 字节数 + mtime_ns）逐条比对：
        只断言「文件还在」会漏掉「被清空 / 被改名 / 被重写」这三种破坏。
        """
        pid = "org.jiuzhang.zzz-disable-probe"
        root = Path(self.tmp.name)
        data_root = root_data_dir()
        plugins_root = root / "plugins"
        saved_plugins = settings.plugins_dir
        settings.plugins_dir = plugins_root
        try:
            (plugins_root / pid / "dist").mkdir(parents=True)
            (plugins_root / pid / "dist" / "index.html").write_text("<main></main>", encoding="utf-8")
            _make_bank_db(data_root / "banks" / f"{pid}.db", 2)
            _make_bank_db(data_root / "workspaces" / "ws_probe" / "banks" / f"{pid}.db", 3)
            uploads = data_root / "uploads"
            uploads.mkdir(parents=True, exist_ok=True)
            (uploads / "fig.png").write_bytes(b"\x89PNG\r\n\x1a\n")

            def snapshot(base: Path) -> dict[str, tuple[int, int]]:
                return {
                    str(item.relative_to(base)).replace("\\", "/"): (item.stat().st_size, item.stat().st_mtime_ns)
                    for item in sorted(base.rglob("*"))
                    if item.is_file() and item.name != "plugin_state.json"
                }

            before_data = snapshot(data_root)
            before_code = snapshot(plugins_root)
            self.assertTrue(before_data, "探针没能造出 data/ 文件，这条断言会变成假阴性")

            plugin_state.set_enabled(pid, False)
            self.assertFalse(plugin_state.is_enabled(pid))
            plugin_state.set_enabled(pid, True)

            self.assertEqual(before_data, snapshot(data_root), "停用/启用改动碰了 data/（ADR-007 禁止）")
            self.assertEqual(before_code, snapshot(plugins_root), "停用/启用改动碰了 plugins/ 代码（ADR-007 禁止）")
            self.assertTrue((data_root / "banks" / f"{pid}.db").is_file())
            self.assertTrue((data_root / "workspaces" / "ws_probe" / "banks" / f"{pid}.db").is_file())
            self.assertTrue((uploads / "fig.png").is_file())
        finally:
            settings.plugins_dir = saved_plugins


class UninstallLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.plugins_dir = root / "plugins"
        self.data_dir = root / "data"
        self.plugins_dir.mkdir(parents=True)
        self._saved = (settings.plugins_dir, __import__("os").environ.get("JZO_DATA_DIR"))
        settings.plugins_dir = self.plugins_dir
        __import__("os").environ["JZO_DATA_DIR"] = str(self.data_dir)
        self.pid = "org.jiuzhang.zzz-demo"
        (self.plugins_dir / self.pid).mkdir(parents=True)

    def tearDown(self) -> None:
        plugins, data = self._saved
        settings.plugins_dir = plugins
        if data is None:
            __import__("os").environ.pop("JZO_DATA_DIR", None)
        else:
            __import__("os").environ["JZO_DATA_DIR"] = data
        self.tmp.cleanup()

    def _seed_dbs(self) -> None:
        _make_bank_db(self.data_dir / "banks" / f"{self.pid}.db", 2)
        ws_banks = self.data_dir / "workspaces" / "ws_x" / "banks"
        _make_bank_db(ws_banks / f"{self.pid}.db", 3)

    def test_keep_data_removes_only_code(self) -> None:
        self._seed_dbs()
        result = plugin_lifecycle.uninstall_plugin(self.pid, keep_data=True)
        self.assertTrue(result["removed_code"])
        self.assertFalse((self.plugins_dir / self.pid).exists())
        self.assertTrue((self.data_dir / "banks" / f"{self.pid}.db").exists(), "保留数据：db 必须还在")

    def test_purge_removes_code_and_every_workspace_db(self) -> None:
        self._seed_dbs()
        result = plugin_lifecycle.uninstall_plugin(self.pid, keep_data=False)
        self.assertEqual(result["keep_data"], False)
        self.assertFalse((self.plugins_dir / self.pid).exists())
        self.assertFalse((self.data_dir / "banks" / f"{self.pid}.db").exists())
        self.assertFalse((self.data_dir / "workspaces" / "ws_x" / "banks" / f"{self.pid}.db").exists())

    def test_missing_plugin_and_bad_id_rejected(self) -> None:
        with self.assertRaises(plugin_lifecycle.PluginUninstallError):
            plugin_lifecycle.uninstall_plugin("org.jiuzhang.not-there", keep_data=True)
        with self.assertRaises(plugin_lifecycle.PluginUninstallError):
            plugin_lifecycle.uninstall_plugin("../../etc", keep_data=False)


class ConsoleAndImportApiTest(unittest.TestCase):
    """HTTP 端到端：启停开关、卸载、以及把本地 .db 挂载成新工作区。"""

    TOKEN = "console-test-token"
    CARD = "org.jiuzhang.dashboard"

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        plugins = root / "plugins"
        plugins.mkdir(parents=True)
        # 拷一个真实、合规的小插件进来，并显式隐藏左栏入口，当被操作对象
        shutil.copytree(ROOT / "plugins" / cls.CARD, plugins / cls.CARD)
        manifest_path = plugins / cls.CARD / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["show_in_sidebar"] = False
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        cls.port = cls._free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(root / "data")
        env["JZO_PLUGINS_DIR"] = str(plugins)
        env["JZO_LOCAL_TOKEN"] = cls.TOKEN
        env["JZO_AI_API_KEY"] = ""
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(cls.port), "--log-level", "warning"],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        deadline = time.time() + 20
        while time.time() < deadline:
            if cls.process.poll() is not None:
                raise RuntimeError("服务提前退出：\n" + (cls.process.stdout.read() if cls.process.stdout else ""))
            try:
                with urllib.request.urlopen(cls.base + "/healthz", timeout=0.5) as r:
                    if r.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("服务未在 20 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        cls.tmp.cleanup()

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _call(self, method, path, body=None, token=True):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("X-JZO-Token", self.TOKEN)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(raw or "{}")
            except json.JSONDecodeError:
                return e.code, {"raw": raw}

    def _plugins(self):
        status, data = self._call("GET", "/api/plugins", token=False)
        self.assertEqual(status, 200)
        return {p["id"]: p for p in data["plugins"]}

    def test_01_toggle_enable_disable(self) -> None:
        self.assertTrue(self._plugins()[self.CARD]["enabled"])
        self.assertIs(self._plugins()[self.CARD]["show_in_sidebar"], False)
        status, _ = self._call("POST", f"/api/plugins/{self.CARD}/enabled", {"enabled": False})
        self.assertEqual(status, 200)
        self.assertFalse(self._plugins()[self.CARD]["enabled"])
        status, _ = self._call("POST", f"/api/plugins/{self.CARD}/enabled", {"enabled": True})
        self.assertEqual(status, 200)
        self.assertTrue(self._plugins()[self.CARD]["enabled"])

    def test_02_enabled_requires_token(self) -> None:
        status, _ = self._call("POST", f"/api/plugins/{self.CARD}/enabled", {"enabled": False}, token=False)
        self.assertEqual(status, 401)

    def test_03_import_valid_db_becomes_workspace(self) -> None:
        import base64
        src = Path(self.tmp.name) / "seed.db"
        _make_bank_db(src, 4)
        blob = base64.b64encode(src.read_bytes()).decode()
        status, data = self._call("POST", "/api/workspaces/import", {"name": "导入区", "db_base64": blob})
        self.assertEqual(status, 200, data)
        self.assertTrue(data["switched"])
        self.assertEqual(data["question_count"], 4)
        status, listing = self._call("GET", "/api/workspaces", token=False)
        self.assertEqual(status, 200)
        entry = next((w for w in listing["workspaces"] if w["id"] == data["id"]), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["question_count"], 4)
        # 切回 default，别污染后续
        self._call("POST", "/api/workspaces/switch", {"workspace_id": "default"})

    def test_04_import_rejects_non_library(self) -> None:
        import base64
        bogus = base64.b64encode(b"not a database at all").decode()
        status, data = self._call("POST", "/api/workspaces/import", {"name": "坏", "db_base64": bogus})
        self.assertEqual(status, 400, data)

    def test_05_import_rejects_sqlite_missing_tables(self) -> None:
        import base64
        stray = Path(self.tmp.name) / "empty.db"
        con = sqlite3.connect(stray)
        con.execute("CREATE TABLE junk(x INTEGER)")
        con.commit()
        con.close()
        blob = base64.b64encode(stray.read_bytes()).decode()
        status, data = self._call("POST", "/api/workspaces/import", {"name": "缺表", "db_base64": blob})
        self.assertEqual(status, 400, data)
        self.assertIn("缺少 core-bank 业务表", str(data.get("detail")))

    def test_06_uninstall_keep_then_purge(self) -> None:
        # 先装进 default 已有；卸载保留数据后目录没了，再彻底卸载同 id 应 404
        status, _ = self._call("DELETE", f"/api/plugins/{self.CARD}?keep_data=true")
        self.assertEqual(status, 200)
        self.assertNotIn(self.CARD, self._plugins())
        status, _ = self._call("DELETE", f"/api/plugins/{self.CARD}?keep_data=true")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
