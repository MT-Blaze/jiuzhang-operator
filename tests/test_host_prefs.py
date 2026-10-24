"""主机状态偏好层（军令 #16）：昵称、左栏文件夹树、停用时间、全局快捷键绑定。

钉死四件事：
1. **写范围只有一个文件**——所有偏好都落 ``data/plugin_state.json``，
   不新建侧文件、不碰插件代码目录、不碰各工作区题库（ADR-007 的口径扩展到整个状态层）；
2. **组合键归一唯一口径**——插件自报、用户改绑、前端比对都走
   :func:`canonical_combo`，写法五花八门也只认规范形，非法即「不绑定」；
3. **发现层把偏好投影进清单**——左栏树是「已启用顺序」的唯一事实来源，
   新装插件不会因为没人排过序就消失，卸载插件不会在树上留幽灵；
4. **HTTP 层写操作一律要本机令牌**，只读免令牌。

运行：``.venv/Scripts/python.exe -m unittest tests.test_host_prefs``
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "host-prefs-contract-token"

ALPHA = "com.example.prefs-alpha"
BETA = "com.example.prefs-beta"


def _manifest(plugin_id: str, **extra: object) -> dict:
    base = {
        "schema_version": "1.0",
        "id": plugin_id,
        "name": plugin_id.split(".")[-1],
        "version": "1.0.0",
        "api_version": "1.0",
        "kind": "tool",
        "description": "主机状态偏好契约用的最小插件",
        "license": "Apache-2.0",
        "entry": {"frontend": "dist/index.html"},
        "slots": ["stage.center"],
        "capabilities": ["question.export"],
        "permissions": [],
    }
    base.update(extra)
    return base


def _plugin_dir(root: Path, manifest: dict) -> Path:
    plugin_dir = root / manifest["id"]
    (plugin_dir / "dist").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "LICENSE").write_text("Apache License 2.0 (fixture)", encoding="utf-8")
    (plugin_dir / "dist" / "index.html").write_text(
        "<!doctype html><title>p</title>", encoding="utf-8"
    )
    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return plugin_dir


class CanonicalComboTest(unittest.TestCase):
    """组合键归一：老师怎么敲都行，落盘只有规范形一种写法。"""

    def test_01_modifiers_are_reordered_and_case_folded(self) -> None:
        from app.core import plugin_state

        for raw, want in (
            ("shift+ctrl+k", "Ctrl+Shift+K"),
            ("Ctrl + ALT + f2", "Ctrl+Alt+F2"),
            ("Cmd+A", "Meta+A"),
            ("Command+Shift+P", "Shift+Meta+P"),
            ("option+delete", "Alt+Delete"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(want, plugin_state.canonical_combo(raw))

    def test_02_key_names_are_normalized(self) -> None:
        from app.core import plugin_state

        self.assertEqual("Ctrl+Esc", plugin_state.canonical_combo("Ctrl+Escape"))
        self.assertEqual("Alt+Space", plugin_state.canonical_combo("alt+space"))
        self.assertEqual("Ctrl+Shift+ArrowUp", plugin_state.canonical_combo("ctrl+shift+arrowup"))
        self.assertEqual("Ctrl+-", plugin_state.canonical_combo("Ctrl+-"))

    def test_03_plus_is_a_legal_primary_key(self) -> None:
        from app.core import plugin_state

        self.assertEqual("Ctrl++", plugin_state.canonical_combo("Ctrl++"))
        self.assertEqual("Ctrl+Alt++", plugin_state.canonical_combo("ctrl+alt++"))

    def test_04_illegal_or_unbound_input_yields_empty(self) -> None:
        from app.core import plugin_state

        for raw in ("", None, "A", "Ctrl", "Ctrl+", "+", "F13", "Ctrl+F13",
                    "Ctrl+?", "Ctrl+Shift+Alt+Meta+K", "Ctrl+Shift", "Ctrl+  +K"):
            with self.subTest(raw=raw):
                self.assertEqual("", plugin_state.canonical_combo(raw))

    def test_05_function_and_navigation_keys_pass_through(self) -> None:
        from app.core import plugin_state

        for raw in ("Ctrl+F1", "Alt+F12", "Ctrl+PageUp", "Ctrl+Home", "Alt+Tab", "Ctrl+Enter"):
            with self.subTest(raw=raw):
                self.assertEqual(raw, plugin_state.canonical_combo(raw))


class PluginStatePrefsTest(unittest.TestCase):
    """core 层：昵称 / 左栏树 / 停用时间 / 快捷键改绑。"""

    def setUp(self) -> None:
        from app.core import plugin_state

        self.mod = plugin_state
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(plugin_state, "root_data_dir", lambda: self.data_dir)
        patch.start()
        self.addCleanup(patch.stop)

    def _raw(self) -> dict:
        return json.loads((self.data_dir / self.mod.STATE_FILENAME).read_text(encoding="utf-8"))

    # ---------- 昵称 ----------
    def test_10_nickname_round_trip_and_clear(self) -> None:
        self.assertEqual("导数 工坊", self.mod.set_nickname(ALPHA, "  导数  工坊  "))
        self.assertEqual({ALPHA: "导数 工坊"}, self._raw()["nicknames"])
        self.assertEqual("导数 工坊", self.mod.state()["nicknames"][ALPHA])
        self.assertEqual("", self.mod.set_nickname(ALPHA, "   "))
        self.assertEqual({}, self._raw()["nicknames"], "空昵称即清掉，回落官方原名")

    def test_11_nickname_is_capped(self) -> None:
        text = self.mod.set_nickname(ALPHA, "名" * (self.mod.NICKNAME_MAX + 30))
        self.assertEqual(self.mod.NICKNAME_MAX, len(text))

    def test_12_corrupt_nickname_map_is_dropped_on_read(self) -> None:
        path = self.data_dir / self.mod.STATE_FILENAME
        path.write_text(json.dumps({"nicknames": {"": "x", ALPHA: "   ", 42: "y"}}), encoding="utf-8")
        self.assertEqual({}, self.mod.state()["nicknames"])

    # ---------- 停用时间 ----------
    def test_20_disable_stamps_time_and_reenable_keeps_it(self) -> None:
        self.mod.set_enabled(ALPHA, False)
        stamps = self._raw()["disabled_at"]
        self.assertIn(ALPHA, stamps)
        self.assertTrue(stamps[ALPHA])
        self.mod.set_enabled(ALPHA, True)
        self.assertNotIn(ALPHA, self.mod.disabled_ids())
        self.assertIn(ALPHA, self.mod.state()["disabled_at"], "重新启用不抹历史停用时间——如实记账")

    def test_21_enable_toggle_touches_only_the_state_file(self) -> None:
        (self.data_dir / "keepme.json").write_text("{}", encoding="utf-8")
        self.mod.set_enabled(ALPHA, False)
        self.mod.set_enabled(ALPHA, True)
        names = sorted(p.name for p in self.data_dir.iterdir())
        self.assertEqual(["keepme.json", self.mod.STATE_FILENAME], names,
                         "状态层只许多出 plugin_state.json 这一个文件")

    # ---------- 左栏树 ----------
    def test_30_sidebar_round_trip_and_dedup(self) -> None:
        tree = self.mod.set_sidebar([
            {"kind": "folder", "id": "folder:tools", "name": "学科工具",
             "children": ["plugin:" + ALPHA, "plugin:" + BETA, "plugin:" + ALPHA]},
            {"kind": "plugin", "id": "plugin:" + ALPHA},
            {"kind": "plugin", "id": "plugin:" + BETA},
            {"kind": "plugin", "id": "folder:not_allowed"},
            {"kind": "bogus", "id": "plugin:x"},
            "not-a-dict",
        ])
        self.assertEqual(1, len(tree))
        folder = tree[0]
        self.assertEqual("folder:tools", folder["id"])
        self.assertEqual("学科工具", folder["name"])
        self.assertEqual(["plugin:" + ALPHA, "plugin:" + BETA], folder["children"],
                         "同一插件只认第一次出现的位置，重复条目丢弃")
        self.assertEqual(tree, self.mod.state()["sidebar"])

    def test_31_illegal_tree_is_treated_as_unconfigured(self) -> None:
        self.assertEqual([], self.mod.set_sidebar({"not": "a list"}))
        self.assertEqual([], self.mod.set_sidebar([{"kind": "folder", "id": "folder:../escape"}]))
        self.assertEqual([], self.mod.state()["sidebar"])

    def test_32_folder_name_defaults_when_blank(self) -> None:
        tree = self.mod.set_sidebar([{"kind": "folder", "id": "folder:a", "name": "  "}])
        self.assertEqual("未命名文件夹", tree[0]["name"])

    def test_33_prune_drops_ghosts_and_empty_folders(self) -> None:
        tree = self.mod.set_sidebar([
            {"kind": "folder", "id": "folder:a", "name": "甲",
             "children": ["plugin:" + ALPHA, "plugin:org.gone.gone"]},
            {"kind": "folder", "id": "folder:b", "name": "乙", "children": ["plugin:org.gone.gone"]},
            {"kind": "plugin", "id": "plugin:org.gone.gone"},
            {"kind": "plugin", "id": "plugin:" + BETA},
        ])
        pruned = self.mod.prune_sidebar(tree, {ALPHA, BETA})
        self.assertEqual(
            [{"kind": "folder", "id": "folder:a", "name": "甲", "children": ["plugin:" + ALPHA]},
             {"kind": "plugin", "id": "plugin:" + BETA}],
            pruned, "幽灵插件从树上抹掉；掏空的文件夹整个消失")
        self.assertEqual(tree, self.mod.state()["sidebar"], "prune 只投影，不改写用户排好的树")

    def test_34_folder_of_maps_children_only(self) -> None:
        tree = self.mod.set_sidebar([
            {"kind": "folder", "id": "folder:a", "name": "甲", "children": ["plugin:" + ALPHA]},
            {"kind": "plugin", "id": "plugin:" + BETA},
        ])
        self.assertEqual({"plugin:" + ALPHA: "folder:a"}, self.mod.folder_of(tree))

    # ---------- 快捷键改绑 ----------
    def test_40_shortcut_bind_rebind_and_unbind(self) -> None:
        self.assertEqual("Ctrl+B", self.mod.set_shortcut("sidebar.toggle", "ctrl+b"))
        self.assertEqual("Meta+K", self.mod.set_shortcut("sidebar.toggle", "meta+k"))
        self.assertEqual("Meta+K", self._raw()["shortcuts"]["sidebar.toggle"])
        self.assertEqual("", self.mod.set_shortcut("sidebar.toggle", ""))
        self.assertEqual("", self.mod.set_shortcut("sidebar.toggle", "非法键位"))
        self.assertEqual({}, self.mod.state()["shortcuts"])

    def test_41_illegal_action_never_persists(self) -> None:
        self.assertFalse(self.mod.is_action_key("Sidebar Toggle"))
        self.assertFalse(self.mod.is_action_key(None))
        self.assertEqual("", self.mod.set_shortcut("Sidebar Toggle", "Ctrl+K"))
        self.assertEqual({}, self.mod.state()["shortcuts"])

    # ---------- 整份文件的保真 ----------
    def test_50_unknown_keys_are_carried_forward(self) -> None:
        path = self.data_dir / self.mod.STATE_FILENAME
        path.write_text(json.dumps({"legacy_flag": True, "disabled": [ALPHA]}), encoding="utf-8")
        self.mod.set_nickname(ALPHA, "甲")
        payload = self._raw()
        self.assertTrue(payload["legacy_flag"], "未知键原样带着走，状态层不许顺手清掉别人的字段")
        self.assertEqual([ALPHA], payload["disabled"])
        self.assertEqual({ALPHA: "甲"}, payload["nicknames"])

    def test_51_atomic_write_leaves_no_temp_file(self) -> None:
        self.mod.set_nickname(ALPHA, "甲")
        self.assertEqual([], [p.name for p in self.data_dir.iterdir() if p.name.endswith(".tmp")])


class ManifestShortcutAndWeightTest(unittest.TestCase):
    """清单层：插件自报键位与舞台权重（缺省保守，底座绝不猜「这个插件很轻」）。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _validate(self, manifest: dict) -> dict:
        from app.core.plugins import validate_plugin

        return validate_plugin(_plugin_dir(self.root, manifest), manifest)

    def test_10_shortcuts_are_normalized_and_deduped(self) -> None:
        info = self._validate(_manifest(ALPHA, shortcuts=[
            {"combo": "ctrl+shift+k", "action": "open.panel", "label": "打开面板"},
            {"combo": "Ctrl+Shift+K", "action": "dup", "label": "同键位后来者"},
            {"combo": "banana", "action": "bad.combo", "label": "非法键位"},
            {"combo": "Alt+J", "action": "Bad Action", "label": "非法动作名"},
            {"combo": "Alt+J", "action": "ok.action", "label": ""},
        ]))
        self.assertEqual(
            [{"combo": "Ctrl+Shift+K", "action": "open.panel", "label": "打开面板"},
             {"combo": "Alt+J", "action": "ok.action", "label": "ok.action"}],
            info["shortcuts"], "非法条目丢弃、同键位只认第一个、label 缺省回落动作名")

    def test_11_shortcuts_absent_or_wrong_type_is_empty_list(self) -> None:
        self.assertEqual([], self._validate(_manifest(ALPHA))["shortcuts"])
        self.assertEqual([], self._validate(_manifest(ALPHA, shortcuts="Ctrl+K"))["shortcuts"])

    def test_12_shortcut_count_is_capped(self) -> None:
        rows = [{"combo": f"Ctrl+F{index}", "action": f"a{index}"} for index in range(1, 10)]
        self.assertEqual(8, len(self._validate(_manifest(ALPHA, shortcuts=rows))["shortcuts"]))

    def test_20_stage_weight_defaults_to_heavy(self) -> None:
        self.assertEqual("heavy", self._validate(_manifest(ALPHA, stage={}))["stage"]["weight"])
        self.assertEqual("heavy",
                         self._validate(_manifest(ALPHA, stage={"weight": "feather"}))["stage"]["weight"])

    def test_21_stage_weight_light_is_honored(self) -> None:
        self.assertEqual("light",
                         self._validate(_manifest(ALPHA, stage={"weight": "light"}))["stage"]["weight"])

    def test_22_stage_absent_stays_none(self) -> None:
        manifest = _manifest(ALPHA, slots=["sidebar.right"])
        self.assertIsNone(self._validate(manifest)["stage"])


class DiscoveryPrefsTest(unittest.TestCase):
    """发现层：偏好投影进清单，左栏树就是顺序的唯一事实来源。"""

    def setUp(self) -> None:
        from app.core import plugin_state, plugins as plugins_core

        self.core = plugins_core
        self.state = plugin_state
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plugins_dir = self.root / "plugins"
        self.data_dir = self.root / "data"
        self.plugins_dir.mkdir()
        _plugin_dir(self.plugins_dir, _manifest(ALPHA, name="甲插件"))
        _plugin_dir(self.plugins_dir, _manifest(BETA, name="乙插件"))
        self._patches = [
            mock.patch.object(plugins_core.settings, "plugins_dir", self.plugins_dir),
            mock.patch.object(plugin_state, "root_data_dir", lambda: self.data_dir),
        ]
        for patch in self._patches:
            patch.start()
        self.addCleanup(lambda: [p.stop() for p in self._patches])
        self.addCleanup(self.tmp.cleanup)

    def _rows(self) -> dict[str, dict]:
        return {item["id"]: item for item in self.core.discover_plugins()["plugins"]}

    def test_01_rows_carry_prefs_defaults(self) -> None:
        rows = self._rows()
        for plugin_id in (ALPHA, BETA):
            self.assertEqual("", rows[plugin_id]["nickname"])
            self.assertEqual("", rows[plugin_id]["folder_id"])
            self.assertEqual("", rows[plugin_id]["disabled_at"])
            self.assertTrue(rows[plugin_id]["enabled"])

    def test_02_nickname_and_disable_stamp_are_projected(self) -> None:
        self.state.set_nickname(ALPHA, "我的导数台")
        self.state.set_enabled(BETA, False)
        rows = self._rows()
        self.assertEqual("我的导数台", rows[ALPHA]["nickname"])
        self.assertFalse(rows[BETA]["enabled"])
        self.assertTrue(rows[BETA]["disabled_at"], "停用时间随清单交给前端渲染相对时间")
        self.assertEqual("", rows[ALPHA]["disabled_at"])

    def test_03_unlisted_plugins_are_appended_and_ghosts_pruned(self) -> None:
        tree = self.state.set_sidebar([
            {"kind": "folder", "id": "folder:a", "name": "甲组",
             "children": ["plugin:" + ALPHA, "plugin:org.gone.gone"]},
        ])
        listing = self.core.discover_plugins()
        self.assertEqual(
            [{"kind": "folder", "id": "folder:a", "name": "甲组", "children": ["plugin:" + ALPHA]},
             {"kind": "plugin", "id": "plugin:" + BETA}],
            listing["sidebar"], "树上幽灵抹掉，没排过序的新插件按发现顺序追加")
        self.assertEqual("folder:a", self._rows()[ALPHA]["folder_id"])
        self.assertEqual("", self._rows()[BETA]["folder_id"])
        self.assertEqual(tree, self.state.state()["sidebar"], "投影不改写用户排好的树")

    def test_10_signature_changes_when_prefs_change(self) -> None:
        first = self.core.discover_plugins()["signature"]
        self.state.set_nickname(ALPHA, "改名了")
        second = self.core.discover_plugins()["signature"]
        self.assertNotEqual(first, second, "改昵称要立刻反映到签名，左栏才会当场重排")
        self.state.set_sidebar([{"kind": "plugin", "id": "plugin:" + BETA},
                                {"kind": "plugin", "id": "plugin:" + ALPHA}])
        third = self.core.discover_plugins()["signature"]
        self.assertNotEqual(second, third, "挪分组也要改签名")
        self.state.set_shortcut("sidebar.toggle", "Ctrl+B")
        self.assertNotEqual(third, self.core.discover_plugins()["signature"], "改绑快捷键也要改签名")

    def test_11_signature_is_stable_without_changes(self) -> None:
        self.assertEqual(self.core.discover_plugins()["signature"],
                         self.core.discover_plugins()["signature"])

    def test_12_host_shortcut_bindings_travel_with_the_listing(self) -> None:
        self.state.set_shortcut("sidebar.toggle", "ctrl+b")
        self.assertEqual({"sidebar.toggle": "Ctrl+B"}, self.core.discover_plugins()["shortcuts"])


class PrefsRouteTest(unittest.TestCase):
    """HTTP 层：三个写端点登记在册且都要本机令牌。"""

    SOURCE = (ROOT / "app" / "api" / "plugins.py").read_text(encoding="utf-8")

    def test_01_routes_registered(self) -> None:
        from app.main import app

        paths = app.openapi().get("paths", {})
        for path in ("/api/plugins/{plugin_id}/nickname", "/api/plugins/sidebar",
                     "/api/plugins/shortcuts"):
            with self.subTest(path=path):
                self.assertIn(path, paths, f"缺少 {path} 路由")
                self.assertIn("post", paths[path])

    def test_02_every_write_demands_a_token(self) -> None:
        for path in ("/api/plugins/{plugin_id}/nickname", "/api/plugins/sidebar",
                     "/api/plugins/shortcuts"):
            with self.subTest(path=path):
                block = self.SOURCE.split(f'"{path}"', 1)[1].split("def ", 1)[0]
                self.assertIn("require_write_token", block, "写偏好必须带本机写令牌")

    def test_03_state_layer_write_scope_is_one_file(self) -> None:
        source = (ROOT / "app" / "core" / "plugin_state.py").read_text(encoding="utf-8")
        for banned in ("shutil", "rmtree", "unlink", "plugins_dir", "bank.db", "sqlite3"):
            self.assertNotIn(banned, source, f"状态层不许碰 {banned}（ADR-007）")


class PrefsHttpTest(unittest.TestCase):
    """端到端：真起服务、真落盘，验证令牌边界与读写闭环。"""

    @classmethod
    def setUpClass(cls) -> None:
        import socket
        import subprocess
        import sys
        import time
        import urllib.error
        import urllib.request

        cls.urllib_request = urllib.request
        cls.urllib_error = urllib.error

        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.data_dir = cls.root / "data"
        cls.plugins_dir = cls.root / "plugins"
        cls.data_dir.mkdir(parents=True)
        cls.plugins_dir.mkdir(parents=True)
        _plugin_dir(cls.plugins_dir, _manifest(ALPHA, name="甲插件"))

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

    def _call(self, method: str, path: str, body: dict | None = None,
              token: bool = False) -> tuple[int, dict]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = self.urllib_request.Request(self.base + path, data=data, method=method)
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

    def test_01_reads_are_open(self) -> None:
        status, body = self._call("GET", "/api/plugins")
        self.assertEqual(200, status)
        row = next(item for item in body["plugins"] if item["id"] == ALPHA)
        self.assertEqual("", row["nickname"])
        self.assertEqual("", row["folder_id"])
        self.assertEqual([{"kind": "plugin", "id": "plugin:" + ALPHA}], body["sidebar"])

    def test_02_writes_without_token_are_rejected(self) -> None:
        for path, payload in (
            (f"/api/plugins/{ALPHA}/nickname", {"nickname": "甲"}),
            ("/api/plugins/sidebar", {"sidebar": [{"kind": "plugin", "id": "plugin:" + ALPHA}]}),
            ("/api/plugins/shortcuts", {"action": "sidebar.toggle", "combo": "Ctrl+B"}),
        ):
            with self.subTest(path=path):
                status, _ = self._call("POST", path, payload)
                self.assertEqual(401, status, "写偏好必须带本机写令牌")

    def test_03_nickname_round_trip(self) -> None:
        status, body = self._call("POST", f"/api/plugins/{ALPHA}/nickname",
                                  {"nickname": "  我的  甲台  "}, token=True)
        self.assertEqual(200, status)
        self.assertEqual("我的 甲台", body["nickname"])
        listing = self._call("GET", "/api/plugins")[1]
        self.assertEqual("我的 甲台",
                         next(item for item in listing["plugins"] if item["id"] == ALPHA)["nickname"])
        persisted = json.loads((self.data_dir / "plugin_state.json").read_text(encoding="utf-8"))
        self.assertEqual({ALPHA: "我的 甲台"}, persisted["nicknames"])

        status, body = self._call("POST", f"/api/plugins/{ALPHA}/nickname",
                                  {"nickname": ""}, token=True)
        self.assertEqual(200, status)
        self.assertEqual("", body["nickname"])

    def test_04_nickname_rejects_bad_input_and_unknown_plugin(self) -> None:
        status, _ = self._call("POST", f"/api/plugins/{ALPHA}/nickname", {}, token=True)
        self.assertEqual(400, status, "nickname 必须是字符串")
        status, _ = self._call("POST", "/api/plugins/org.gone.gone/nickname",
                               {"nickname": "幽灵"}, token=True)
        self.assertEqual(404, status)

    def test_05_sidebar_and_shortcut_round_trip(self) -> None:
        tree = [{"kind": "folder", "id": "folder:a", "name": "甲组", "children": ["plugin:" + ALPHA]}]
        status, body = self._call("POST", "/api/plugins/sidebar", {"sidebar": tree}, token=True)
        self.assertEqual(200, status)
        self.assertEqual(tree, body["sidebar"])
        self.assertEqual("folder:a",
                         next(item for item in self._call("GET", "/api/plugins")[1]["plugins"]
                              if item["id"] == ALPHA)["folder_id"])
        status, _ = self._call("POST", "/api/plugins/sidebar", {"sidebar": "not-a-list"}, token=True)
        self.assertEqual(400, status)

        status, body = self._call("POST", "/api/plugins/shortcuts",
                                  {"action": "sidebar.toggle", "combo": "ctrl+b"}, token=True)
        self.assertEqual(200, status)
        self.assertEqual("Ctrl+B", body["combo"])
        status, _ = self._call("POST", "/api/plugins/shortcuts",
                               {"action": "Bad Action", "combo": "Ctrl+B"}, token=True)
        self.assertEqual(400, status)
        self.assertEqual({"sidebar.toggle": "Ctrl+B"},
                         self._call("GET", "/api/plugins")[1]["shortcuts"])

    def test_06_writes_add_no_extra_file_to_data_dir(self) -> None:
        before = {str(p) for p in self.data_dir.rglob("*")}
        self._call("POST", f"/api/plugins/{ALPHA}/nickname", {"nickname": "再改"}, token=True)
        self.assertEqual(before, {str(p) for p in self.data_dir.rglob("*")},
                         "改昵称只原地改写那一份状态文件，不新增任何侧文件")
        self.assertEqual([], [p for p in self.plugins_dir.rglob("*.tmp")],
                         "写偏好不许碰插件代码目录")


if __name__ == "__main__":
    unittest.main()
