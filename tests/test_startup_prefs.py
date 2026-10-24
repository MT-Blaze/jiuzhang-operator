"""启动行为（军令 #11 阶段三）：老师选「打开软件先落在哪个界面」。

覆盖三件事：
1. **后端持久化与校验**——落盘 ``data/startup.json``，写入严格（插件必须已装且
   已启用，否则 400 级拒绝），读取宽容（插件被删/被停用则回落默认欢迎页，
   带 fallback_reason 并打 WARNING 日志，配置原地保留）；
2. **下拉数据源口径**——只遍历已启用插件，停用的不进候选；
3. **前端接线**——设置页「系统设置」分区、工作台启动时执行并如实播报回退。

运行：``.venv/Scripts/python.exe -m unittest tests.test_startup_prefs``
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "startup-contract-token"
SETTINGS_HTML = (ROOT / "static" / "settings.html").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "js" / "settings.js").read_text(encoding="utf-8")
WORKSPACE_JS = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")

DASHBOARD_ID = "org.jiuzhang.dashboard"
EDITOR_ID = "org.jiuzhang.editor"


def _plugin(plugin_id: str, enabled: bool = True, sidebar: bool = True) -> dict:
    return {"id": plugin_id, "name": plugin_id.split(".")[-1], "version": "0.1.0",
            "enabled": enabled, "show_in_sidebar": sidebar, "stage": {"region": "center"}}


class StartupPrefsTest(unittest.TestCase):
    """core 层：读宽容、写严格、回退如实。"""

    def setUp(self) -> None:
        from app.core import startup_prefs

        self.mod = startup_prefs
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        self._patches = [
            mock.patch.object(startup_prefs, "state_path",
                              lambda: self.data_dir / startup_prefs.STATE_FILENAME),
            mock.patch.object(startup_prefs, "installed_plugins",
                              lambda: [_plugin(DASHBOARD_ID), _plugin(EDITOR_ID, enabled=False)]),
        ]
        for patch in self._patches:
            patch.start()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: [p.stop() for p in self._patches])

    # ---------- 默认态 ----------
    def test_01_defaults_to_welcome_page_when_unconfigured(self) -> None:
        resolved = self.mod.resolve()
        self.assertEqual("chat", resolved["target"])
        self.assertEqual("chat", resolved["effective"])
        self.assertEqual("chat", resolved["kind"])
        self.assertEqual("", resolved["fallback_reason"])
        self.assertFalse(self.mod.state_path().is_file(), "没配过就不该落文件")

    def test_02_candidates_only_list_enabled_plugins(self) -> None:
        ids = [item["id"] for item in self.mod.resolve()["candidates"]]
        self.assertIn(DASHBOARD_ID, ids)
        self.assertNotIn(EDITOR_ID, ids, "停用的插件不许进下拉数据源")

    def test_03_candidate_carries_target_value_and_sidebar_flag(self) -> None:
        entry = next(c for c in self.mod.resolve()["candidates"] if c["id"] == DASHBOARD_ID)
        self.assertEqual("plugin:" + DASHBOARD_ID, entry["target"])
        self.assertTrue(entry["show_in_sidebar"])
        self.assertTrue(entry["has_stage"])

    # ---------- 写入 ----------
    def test_10_set_plugin_target_persists_to_data_dir(self) -> None:
        self.mod.set_target("plugin:" + DASHBOARD_ID)
        path = self.data_dir / self.mod.STATE_FILENAME
        self.assertTrue(path.is_file())
        self.assertEqual({"target": "plugin:" + DASHBOARD_ID}, json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual("plugin:" + DASHBOARD_ID, self.mod.resolve()["effective"])
        self.assertEqual("plugin", self.mod.resolve()["kind"])
        self.assertEqual(DASHBOARD_ID, self.mod.resolve()["plugin_id"])

    def test_11_set_chat_target_persists(self) -> None:
        self.mod.set_target("plugin:" + DASHBOARD_ID)
        self.mod.set_target("chat")
        self.assertEqual("chat", self.mod.resolve()["effective"])

    def test_12_rejects_malformed_targets(self) -> None:
        for bad in ("", "  ", "plugin:", "Plugin:org.x.y", "org.example",
                    "plugin:ORG.Example", "plugin:../escape", None, 42, {"target": "chat"}):
            with self.subTest(target=bad):
                with self.assertRaises(self.mod.StartupRejected):
                    self.mod.set_target(bad)
        self.assertFalse((self.data_dir / self.mod.STATE_FILENAME).is_file(), "被拒的目标不许落盘")

    def test_13_rejects_missing_or_disabled_plugin(self) -> None:
        with self.assertRaises(self.mod.StartupRejected) as missing:
            self.mod.set_target("plugin:org.example.gone")
        self.assertIn("未安装", str(missing.exception))
        with self.assertRaises(self.mod.StartupRejected) as disabled:
            self.mod.set_target("plugin:" + EDITOR_ID)
        self.assertIn("已停用", str(disabled.exception))

    def test_14_normalizes_surrounding_whitespace(self) -> None:
        self.assertEqual("chat", self.mod.set_target("  chat  "))
        self.assertEqual("plugin:" + DASHBOARD_ID, self.mod.set_target(" plugin:" + DASHBOARD_ID + " "))

    # ---------- 失效回退 ----------
    def test_20_uninstalled_plugin_falls_back_and_logs(self) -> None:
        self.mod.set_target("plugin:" + DASHBOARD_ID)
        # 插件被卸载：清单里再也找不到它
        with mock.patch.object(self.mod, "installed_plugins", lambda: []):
            with self.assertLogs("jzo.startup", level="WARNING") as logs:
                resolved = self.mod.resolve()
        self.assertEqual("chat", resolved["effective"])
        self.assertEqual("plugin:" + DASHBOARD_ID, resolved["target"], "配置必须原地保留")
        self.assertIn("已卸载", resolved["fallback_reason"])
        self.assertTrue(any("已卸载" in line for line in logs.output), "回退必须打日志")

    def test_21_disabled_plugin_falls_back_and_logs(self) -> None:
        self.mod.set_target("plugin:" + DASHBOARD_ID)
        with mock.patch.object(self.mod, "installed_plugins",
                               lambda: [_plugin(DASHBOARD_ID, enabled=False)]):
            with self.assertLogs("jzo.startup", level="WARNING") as logs:
                resolved = self.mod.resolve()
        self.assertEqual("chat", resolved["effective"])
        self.assertIn("已停用", resolved["fallback_reason"])
        self.assertTrue(any("已停用" in line for line in logs.output))

    def test_22_reenabled_plugin_restores_original_target(self) -> None:
        self.mod.set_target("plugin:" + DASHBOARD_ID)
        with mock.patch.object(self.mod, "installed_plugins", lambda: []):
            self.assertEqual("chat", self.mod.resolve()["effective"])
        self.assertEqual("plugin:" + DASHBOARD_ID, self.mod.resolve()["effective"],
                         "插件装回来后原配置要自动恢复生效")

    def test_23_corrupt_state_file_is_treated_as_unconfigured(self) -> None:
        path = self.data_dir / self.mod.STATE_FILENAME
        path.write_text("{ not json", encoding="utf-8")
        self.assertEqual("chat", self.mod.read_target())
        path.write_text(json.dumps({"target": "plugin:../evil"}), encoding="utf-8")
        self.assertEqual("chat", self.mod.read_target(), "形状非法的历史配置一律当作没配过")
        path.write_text(json.dumps(["chat"]), encoding="utf-8")
        self.assertEqual("chat", self.mod.read_target())


class StartupRouteTest(unittest.TestCase):
    """HTTP 层：读免令牌、写带本机令牌。"""

    def test_01_routes_registered(self) -> None:
        from app.main import app

        # FastAPI 0.141 把 include_router 的路由包成 _IncludedRouter（path=None），
        # 从 app.routes 直接取 path 会漏掉；以 OpenAPI 的 paths 为准。
        paths = app.openapi().get("paths", {})
        self.assertIn("/api/startup", paths, "缺少 /api/startup 路由")
        self.assertIn("get", paths["/api/startup"])
        self.assertIn("post", paths["/api/startup"])

    def test_02_post_requires_write_token(self) -> None:
        source = (ROOT / "app" / "api" / "settings.py").read_text(encoding="utf-8")
        post_block = source.split("@router.post(", 1)[1].split("def write_startup", 1)[0]
        self.assertIn("require_write_token", post_block,
                      "保存启动行为是写操作，必须带本机写令牌")
        get_block = source.split("@router.get(", 1)[1].split("def read_startup", 1)[0]
        self.assertNotIn("require_write_token", get_block,
                         "读取落在启动链上，不能要求令牌")

    def test_03_rejected_target_maps_to_400(self) -> None:
        source = (ROOT / "app" / "api" / "settings.py").read_text(encoding="utf-8")
        self.assertIn("StartupRejected", source)
        self.assertIn("status_code=400", source)


class StartupCandidatesIntegrationTest(unittest.TestCase):
    """候选清单必须真来自插件发现结果（含仓库自带的数据看板）。"""

    def test_01_candidates_come_from_discovery(self) -> None:
        from app.core import startup_prefs

        with mock.patch.dict(os.environ, {"JZO_PLUGINS_DIR": str(ROOT / "plugins")}):
            ids = [item["id"] for item in startup_prefs.candidates()]
        self.assertIn(DASHBOARD_ID, ids, "数据看板必须出现在启动行为下拉里")
        self.assertTrue(all("plugin:" + item["id"] == item["target"]
                            for item in startup_prefs.candidates()))


class SettingsUiWiringTest(unittest.TestCase):
    """设置页「系统设置」分区与下拉接线。"""

    def test_01_system_panel_exists_in_nav_and_panels(self) -> None:
        self.assertIn('id="stNavSystem"', SETTINGS_HTML)
        self.assertIn('id="stPanelSystem"', SETTINGS_HTML)
        self.assertIn('data-panel="system"', SETTINGS_HTML)
        self.assertIn('aria-controls="stPanelSystem"', SETTINGS_HTML)

    def test_02_panel_key_registered(self) -> None:
        self.assertRegex(SETTINGS_JS, r'PANEL_KEYS\s*=\s*\[[^\]]*"system"[^\]]*\]')

    def test_03_controls_and_labels(self) -> None:
        for element_id in ("startupTarget", "startupSaveBtn", "startupStatus"):
            self.assertIn(f'id="{element_id}"', SETTINGS_HTML, f"系统设置缺少 {element_id}")
        self.assertIn('for="startupTarget"', SETTINGS_HTML)
        self.assertIn("启动行为", SETTINGS_HTML)
        self.assertIn('role="status"', SETTINGS_HTML.split('id="stPanelSystem"', 1)[1].split("</section>", 1)[0])

    def test_04_select_default_option_is_welcome_page(self) -> None:
        panel = SETTINGS_HTML.split('id="stPanelSystem"', 1)[1].split("</section>", 1)[0]
        self.assertIn('<option value="chat">', panel)
        self.assertIn("默认欢迎页", panel)

    def test_05_js_reads_and_writes_startup_endpoint(self) -> None:
        self.assertIn('apiCall("/api/startup", "GET")', SETTINGS_JS)
        self.assertIn('apiCall("/api/startup", "POST"', SETTINGS_JS)
        self.assertIn("candidates", SETTINGS_JS, "下拉数据源必须用后端回的已启用插件清单")

    def test_06_no_hardcoded_plugin_id_in_settings_js(self) -> None:
        block = SETTINGS_JS.split("系统设置：启动行为", 1)[1]
        self.assertNotIn("core-bank", block, "启动目标不许写死某个插件 id")

    def test_07_save_button_guards_busy_state(self) -> None:
        block = SETTINGS_JS.split("系统设置：启动行为", 1)[1]
        self.assertIn("aria-busy", block)
        self.assertIn("disabled = true", block)


class WorkspaceBootWiringTest(unittest.TestCase):
    """工作台启动时执行配置，失效则回落并播报。"""

    def test_01_boot_reads_startup_config(self) -> None:
        self.assertIn('fetch("/api/startup"', WORKSPACE_JS)
        self.assertIn("applyStartupBehavior", WORKSPACE_JS)
        boot = WORKSPACE_JS.split("// ============ 初始化 ============", 1)[1]
        self.assertIn("applyStartupBehavior(plugins)", boot, "启动链必须真的调用它")

    def test_02_fallback_reason_is_reported_not_swallowed(self) -> None:
        fn = WORKSPACE_JS.split("function applyStartupBehavior", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn("fallback_reason", fn)
        self.assertIn("addBubble", fn, "回退要在底栏输出日志区如实说明")
        self.assertIn("tone: \"warn\"", fn)

    def test_03_respects_effective_and_enabled_flag(self) -> None:
        fn = WORKSPACE_JS.split("function applyStartupBehavior", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn("body.effective", fn, "只认后端算好的生效值")
        self.assertIn("enabled !== false", fn, "停用插件不许被启动进去")
        self.assertIn("enterPluginMode(target, item)", fn)

    def test_04_sidebar_items_carry_plugin_id_for_highlight(self) -> None:
        self.assertIn('btn.setAttribute("data-plugin-id"', WORKSPACE_JS)
        self.assertIn('getAttribute("data-plugin-id")', WORKSPACE_JS)

    def test_05_boot_never_blocks_on_config_failure(self) -> None:
        fn = WORKSPACE_JS.split("function applyStartupBehavior", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn(".catch(function ()", fn, "读不到配置也要停在默认欢迎页")


class StartupHttpTest(unittest.TestCase):
    """端到端：真起服务、真落盘、真删插件，验证回退链路。

    全程在临时目录里跑（JZO_DATA_DIR / JZO_PLUGINS_DIR 指过去），
    既不碰开发者本机 ``data/``，也不碰仓库 ``plugins/``（只读复制）。
    """

    @classmethod
    def setUpClass(cls) -> None:
        import shutil
        import socket
        import subprocess
        import sys
        import time
        import urllib.error
        import urllib.request

        cls.shutil = shutil
        cls.urllib_request = urllib.request
        cls.urllib_error = urllib.error

        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.data_dir = cls.root / "data"
        cls.plugins_dir = cls.root / "plugins"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        cls.plugins_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT / "plugins" / DASHBOARD_ID, cls.plugins_dir / DASHBOARD_ID)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = int(sock.getsockname()[1])

        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(cls.port), "--log-level", "warning"],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        cls.base = f"http://127.0.0.1:{cls.port}"
        deadline = time.time() + 25
        while time.time() < deadline:
            if cls.process.poll() is not None:
                raise RuntimeError("服务提前退出：\n" + (cls.process.stdout.read() or ""))
            try:
                with urllib.request.urlopen(cls.base + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        else:
            raise RuntimeError("服务未在 25 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except Exception:  # noqa: BLE001
            cls.process.kill()
        if cls.process.stdout:
            cls.process.stdout.close()
        cls.tmp.cleanup()

    def _call(self, method: str, body: dict | None = None, token: bool = False) -> tuple[int, dict]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = self.urllib_request.Request(self.base + "/api/startup", data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", TOKEN)
        try:
            with self.urllib_request.urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read().decode("utf-8") or "{}")
        except self.urllib_error.HTTPError as error:
            payload = error.read().decode("utf-8")
            error.close()
            try:
                return error.code, json.loads(payload or "{}")
            except json.JSONDecodeError:
                return error.code, {"raw": payload}

    def test_01_get_is_open_and_defaults_to_chat(self) -> None:
        status, body = self._call("GET")
        self.assertEqual(200, status)
        self.assertEqual("chat", body["effective"])
        self.assertIn(DASHBOARD_ID, [item["id"] for item in body["candidates"]])
        self.assertNotIn("local_token", json.dumps(body), "启动接口不许回任何令牌信息")

    def test_02_post_without_token_is_rejected(self) -> None:
        status, _ = self._call("POST", {"target": "chat"})
        self.assertEqual(401, status, "保存启动行为必须带本机写令牌")

    def test_03_post_rejects_unknown_or_malformed_target(self) -> None:
        for bad in ("plugin:org.example.gone", "banana", "plugin:../escape", ""):
            with self.subTest(target=bad):
                status, body = self._call("POST", {"target": bad}, token=True)
                self.assertEqual(400, status)
                self.assertTrue(str(body.get("detail")))

    def test_04_save_then_delete_plugin_falls_back_then_recovers(self) -> None:
        status, body = self._call("POST", {"target": "plugin:" + DASHBOARD_ID}, token=True)
        self.assertEqual(200, status)
        self.assertEqual("plugin:" + DASHBOARD_ID, body["effective"])
        self.assertEqual("数据看板", body["plugin_name"])
        self.assertEqual({"target": "plugin:" + DASHBOARD_ID},
                         json.loads((self.data_dir / "workspaces" / "default" / "startup.json")
                                     .read_text(encoding="utf-8")))

        status, body = self._call("GET")
        self.assertEqual("plugin:" + DASHBOARD_ID, body["effective"])

        # 老师把插件删了（或整个目录搬走）：启动不许炸，回落默认欢迎页并说明原因
        plugin_dir = self.plugins_dir / DASHBOARD_ID
        backup = self.root / "backup-dashboard"
        self.shutil.move(str(plugin_dir), str(backup))
        try:
            status, body = self._call("GET")
            self.assertEqual(200, status)
            self.assertEqual("chat", body["effective"])
            self.assertEqual("chat", body["kind"])
            self.assertEqual("plugin:" + DASHBOARD_ID, body["target"], "配置原地保留")
            self.assertIn("已卸载", body["fallback_reason"])
        finally:
            self.shutil.move(str(backup), str(plugin_dir))

        status, body = self._call("GET")
        self.assertEqual("plugin:" + DASHBOARD_ID, body["effective"], "插件回来即自动恢复")
        self.assertEqual("", body["fallback_reason"])

        self._call("POST", {"target": "chat"}, token=True)


if __name__ == "__main__":
    unittest.main()
