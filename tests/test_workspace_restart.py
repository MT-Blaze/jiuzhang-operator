"""军令 #18 第四步契约：切库必须重启底座，前端必须真人等真进程。

钉六件事：

1. ``/healthz`` 带 ``boot_id``，每次进程启动换新——它是「新进程真的起来了」的唯一凭据；
2. 重启脚本按 v0.9.0 真机教训生成：``tasklist`` + ``ping``（不碰 ``find``、不用 ``timeout``），
   等旧 PID 退出后才拉起 uvicorn，跑完自删；
3. ``JZO_RESTART_DISABLED=1`` 是单测/受控环境的总闸：只切指针、不杀进程；
4. ``POST /api/workspaces/switch`` 先准备脚本再写指针，写完指针才调度重启；
   新建与导入同样走重启（它们也在切库），教材版本随新建一次登记，
   避免重启开始后再补一刀 ``/textbook`` 撞在进程退出上；
5. 前端确认弹窗的红字警告逐字固定，点确认后进入全屏遮罩并按 ``boot_id`` 变化才重载；
   超时如实报错并交出「手动刷新」——严禁假死装像；
6. 草稿按工作区分箱（军令 #18-终 阶段一）：红字承诺的是「留在原区、切回恢复」，
   不是「丢弃」；宿主不知道自己在哪个区时宁可不开草稿箱，也绝不跨区存取。

运行：``.venv/Scripts/python.exe -m unittest tests.test_workspace_restart``
"""

from __future__ import annotations

import asyncio
import base64
import os
import sqlite3
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from app.api import health, workspaces as workspaces_api
from app.core import bank as core_bank
from app.core import host_restart
from app.core.config import settings, switch_workspace

ROOT = Path(__file__).resolve().parents[1]
WARNING_TEXT = ("切换工作区需要重启底座以加载该区的插件与配置，"
                "未保存的草稿会留在原工作区、切回时自动恢复，是否继续？")


def _request(port: int | None = 8123) -> SimpleNamespace:
    return SimpleNamespace(url=SimpleNamespace(port=port))


def _run(coroutine):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


class _IsolatedData(unittest.TestCase):
    """每个用例一套临时 data/，切换指针与建库都不碰本机真数据。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / "data"
        self.data.mkdir()
        self._saved_ws = settings.workspace_id
        self._saved_env = {key: os.environ.get(key)
                           for key in ("JZO_DATA_DIR", "JZO_PLUGINS_DIR", "JZO_RESTART_DISABLED")}
        os.environ["JZO_DATA_DIR"] = str(self.data)
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        settings.workspace_id = self._saved_ws
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def register(self, workspace_id: str, name: str = "试验区") -> None:
        workspaces_api._save_workspaces([
            {"id": "default", "name": "默认工作区"},
            {"id": workspace_id, "name": name},
        ])

    def _known_textbooks(self) -> set[str]:
        try:
            return {str(item["id"]) for item in core_bank.textbooks(workspaces_api._provider_id())}
        except Exception:  # noqa: BLE001 - 与端点同口径：读不到登记表就当没有
            return set()


class BootIdTest(unittest.TestCase):
    def test_boot_id_is_stable_hex(self) -> None:
        first = host_restart.boot_id()
        self.assertEqual(len(first), 32)
        self.assertEqual(first.lower(), first)
        int(first, 16)                       # 必须是合法 hex，前端拿它当身份证比对
        self.assertEqual(first, host_restart.boot_id())

    def test_healthz_reports_boot_id(self) -> None:
        payload = _run(health.healthz())
        self.assertEqual(payload["boot_id"], host_restart.boot_id())
        self.assertEqual(payload["status"], "ok")

    def test_new_process_would_report_new_boot_id(self) -> None:
        with mock.patch.object(host_restart, "BOOT_ID", "f" * 32):
            self.assertEqual(_run(health.healthz())["boot_id"], "f" * 32)


class RestartScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.script = host_restart.build_restart_script(
            pid=4321, root=Path("C:\\jzo"), python_exe="C:\\jzo\\.venv\\Scripts\\python.exe",
            host="127.0.0.1", port=8123,
        )

    def test_waits_for_old_pid_then_relaunches_same_port(self) -> None:
        self.assertIn('"PID eq %JZO_PID%"', self.script)
        self.assertIn("set \"JZO_PID=4321\"", self.script)
        self.assertIn("goto wait_exit", self.script)
        self.assertIn('-m uvicorn app.main:app --host 127.0.0.1 --port 8123', self.script)
        self.assertIn('cd /d "%JZO_ROOT%"', self.script)
        self.assertIn('del "%~f0"', self.script)

    def test_avoids_the_two_known_batch_traps(self) -> None:
        """v0.9.0 真机踩过的坑：``find`` 被 Git Bash 抢占、``timeout`` 在无控制台时卡死。"""
        self.assertNotIn("timeout /t", self.script)
        self.assertNotIn("| find", self.script)
        self.assertIn(r"%SystemRoot%\System32\tasklist.exe", self.script)
        self.assertIn(r"%SystemRoot%\System32\ping.exe", self.script)

    def test_is_crlf_and_touches_no_program_files(self) -> None:
        self.assertIn("\r\n", self.script)
        self.assertNotIn("\r\r\n", self.script)
        self.assertNotIn("robocopy", self.script.lower())

    def test_port_is_coerced_to_int(self) -> None:
        script = host_restart.build_restart_script(
            pid=1, root=Path("C:\\jzo"), python_exe="python", host="127.0.0.1", port="8123")  # type: ignore[arg-type]
        self.assertIn("--port 8123", script)


class PrepareAndLaunchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_disabled_gate_returns_none(self) -> None:
        with mock.patch.dict(os.environ, {"JZO_RESTART_DISABLED": "1"}):
            self.assertIsNone(host_restart.prepare_restart(port=8123))

    def test_prepare_writes_script_with_live_port(self) -> None:
        env = {"JZO_RESTART_DISABLED": "", "JZO_PORT": "9000"}
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.object(type(settings), "project_root", self.root, create=False):
            prepared = host_restart.prepare_restart(port=8123)
        self.assertIsNotNone(prepared)
        assert prepared is not None
        script = Path(prepared["script_path"])
        self.assertTrue(script.is_file())
        self.assertIn("--port 8123", script.read_text(encoding="utf-8", errors="replace"))

    def test_launch_spawns_detached_and_schedules_exit(self) -> None:
        prepared = {"script_path": self.root / "r.bat", "log_path": self.root / "r.log",
                    "root": self.root}
        (self.root / "r.bat").write_text("@echo off\r\n", encoding="ascii")
        with mock.patch("app.core.host_restart.subprocess.Popen") as popen, \
             mock.patch.object(host_restart, "_exit_process") as exit_now:
            host_restart.launch_restart(prepared, delay=0.05)
            args, kwargs = popen.call_args
            time.sleep(0.6)
        self.assertEqual(args[0][:3], ["cmd.exe", "/c", str(self.root / "r.bat")])
        self.assertEqual(kwargs["cwd"], str(self.root))
        self.assertTrue(kwargs["creationflags"])          # DETACHED_PROCESS
        self.assertEqual(kwargs["stderr"], subprocess.STDOUT)   # 绝不接控制台
        self.assertTrue(hasattr(kwargs["stdout"], "write"))     # 接的是日志文件句柄
        exit_now.assert_called_once()


class RequestPortTest(unittest.TestCase):
    def test_uses_live_port_and_falls_back_to_settings(self) -> None:
        self.assertEqual(workspaces_api._request_port(_request(8123)), 8123)
        self.assertEqual(workspaces_api._request_port(_request(None)), int(settings.port))
        self.assertEqual(workspaces_api._request_port(_request(70000)), int(settings.port))


class SwitchEndpointTest(_IsolatedData):
    def test_disabled_gate_keeps_process_alive_and_still_switches(self) -> None:
        os.environ["JZO_RESTART_DISABLED"] = "1"
        self.register("ws_a", "A 区")
        with mock.patch.object(host_restart, "launch_restart") as launch:
            result = _run(workspaces_api.switch_workspace_endpoint(
                workspaces_api.WorkspaceSwitchRequest(workspace_id="ws_a"), _request()))
        self.assertFalse(result["restarting"])
        launch.assert_not_called()
        self.assertEqual(settings.workspace_id, "ws_a")
        pointer = (self.data / "current_workspace").read_text(encoding="utf-8").strip()
        self.assertEqual(pointer, "ws_a")

    def test_enabled_switches_then_schedules_restart(self) -> None:
        os.environ.pop("JZO_RESTART_DISABLED", None)
        self.register("ws_b", "B 区")
        sentinel = {"script_path": Path("x.bat")}
        with mock.patch.object(host_restart, "prepare_restart", return_value=sentinel) as prepare, \
             mock.patch.object(host_restart, "launch_restart") as launch:
            result = _run(workspaces_api.switch_workspace_endpoint(
                workspaces_api.WorkspaceSwitchRequest(workspace_id="ws_b"), _request(8799)))
        self.assertTrue(result["restarting"])
        self.assertEqual(result["boot_id"], host_restart.boot_id())
        self.assertEqual(result["workspace_id"], "ws_b")
        prepare.assert_called_once_with(port=8799)
        launch.assert_called_once_with(sentinel)

    def test_unknown_workspace_never_prepares_a_restart(self) -> None:
        os.environ.pop("JZO_RESTART_DISABLED", None)
        self.register("ws_known")
        before = settings.workspace_id
        with mock.patch.object(host_restart, "prepare_restart") as prepare:
            with self.assertRaises(Exception) as raised:
                _run(workspaces_api.switch_workspace_endpoint(
                    workspaces_api.WorkspaceSwitchRequest(workspace_id="ws_ghost"), _request()))
        self.assertEqual(getattr(raised.exception, "status_code", None), 404)
        prepare.assert_not_called()
        self.assertEqual(settings.workspace_id, before)

    def test_registry_entry_without_name_or_id_does_not_break_the_switch(self) -> None:
        """``workspaces.json`` 是人能改的文件：条目缺 name 只退回 id，非对象条目读时出局。

        切库回包是在「指针已写入、重启已发起」之后才组装的，这里抛 KeyError 会变成
        「库确实切了、前端只收到 500」的半截状态——比显示成 id 难查得多。
        """
        os.environ["JZO_RESTART_DISABLED"] = "1"
        workspaces_api._save_workspaces([
            {"id": "default", "name": "默认工作区"},
            {"id": "ws_noname"},
            "不是对象",
            {"name": "没有 id 的条目"},
        ])
        result = _run(workspaces_api.switch_workspace_endpoint(
            workspaces_api.WorkspaceSwitchRequest(workspace_id="ws_noname"), _request()))
        self.assertEqual(result["workspace_id"], "ws_noname")
        self.assertEqual(result["name"], "ws_noname")
        listed = _run(workspaces_api.list_workspaces())
        self.assertEqual([item["id"] for item in listed["workspaces"]], ["default", "ws_noname"])

    def test_switch_to_default_works_without_registry_entry(self) -> None:
        os.environ["JZO_RESTART_DISABLED"] = "1"
        switch_workspace("ws_somewhere")
        result = _run(workspaces_api.switch_workspace_endpoint(
            workspaces_api.WorkspaceSwitchRequest(workspace_id="default"), _request()))
        self.assertEqual(result["workspace_id"], "default")
        self.assertIsNone(settings.workspace_id)


class CreateAndImportRestartTest(_IsolatedData):
    def test_create_carries_textbook_and_schedules_restart(self) -> None:
        os.environ.pop("JZO_RESTART_DISABLED", None)
        workspaces_api._save_workspaces([])
        # 取当前库真实登记的版本；空环境没有登记表时按「不拦」口径用合法假 id。
        known = self._known_textbooks()
        textbook = sorted(known)[0] if known else "tb_aaaaaaaa"
        sentinel = {"script_path": Path("x.bat")}
        with mock.patch.object(host_restart, "prepare_restart", return_value=sentinel), \
             mock.patch.object(host_restart, "launch_restart") as launch:
            result = _run(workspaces_api.create_workspace(
                workspaces_api.WorkspaceCreateRequest(name="新建区", textbook_id=textbook),
                _request(8799)))
        launch.assert_called_once_with(sentinel)
        self.assertTrue(result["restarting"])
        entry = next(item for item in workspaces_api._load_workspaces()
                     if item["id"] == result["id"])
        self.assertEqual(entry["textbook_id"], textbook)

    def test_create_rejects_textbook_outside_the_registry(self) -> None:
        os.environ["JZO_RESTART_DISABLED"] = "1"
        workspaces_api._save_workspaces([])
        if not self._known_textbooks():
            self.skipTest("当前环境没有并集登记表，无法验证「不在登记表里」这一路")
        with self.assertRaises(Exception) as raised:
            _run(workspaces_api.create_workspace(
                workspaces_api.WorkspaceCreateRequest(name="坏区", textbook_id="tb_ffffffff"),
                _request()))
        self.assertEqual(getattr(raised.exception, "status_code", None), 400)
        self.assertEqual(workspaces_api._load_workspaces(), [])

    def test_create_rejects_bad_textbook_before_touching_anything(self) -> None:
        os.environ["JZO_RESTART_DISABLED"] = "1"
        workspaces_api._save_workspaces([])
        with self.assertRaises(Exception) as raised:
            _run(workspaces_api.create_workspace(
                workspaces_api.WorkspaceCreateRequest(name="坏区", textbook_id="../etc"), _request()))
        self.assertEqual(getattr(raised.exception, "status_code", None), 400)
        self.assertEqual(workspaces_api._load_workspaces(), [])

    def test_import_also_schedules_restart(self) -> None:
        os.environ.pop("JZO_RESTART_DISABLED", None)
        workspaces_api._save_workspaces([])
        bank = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "seed.db"
            con = sqlite3.connect(db)
            con.executescript(bank.read_text(encoding="utf-8"))
            con.commit()
            con.close()
            blob = db.read_bytes()
        sentinel = {"script_path": Path("x.bat")}
        payload = workspaces_api.WorkspaceImportRequest(
            name="导入区", db_base64=base64.b64encode(blob).decode("ascii"))
        with mock.patch.object(host_restart, "prepare_restart", return_value=sentinel), \
             mock.patch.object(host_restart, "launch_restart") as launch:
            result = _run(workspaces_api.import_workspace(payload, _request(8799)))
        launch.assert_called_once_with(sentinel)
        self.assertTrue(result["restarting"])


class TextbookIdContractTest(_IsolatedData):
    """军令 #18-终 阶段一 3：新建工作区随请求登记教材版本——契约三层（模型/端点/前端）都要钉住。"""

    def test_model_defaults_to_empty_and_caps_length(self) -> None:
        import pydantic

        self.assertEqual(workspaces_api.WorkspaceCreateRequest(name="区").textbook_id, "",
                         "不填即「跟随默认版本」，不能是 None")
        with self.assertRaises(pydantic.ValidationError):
            workspaces_api.WorkspaceCreateRequest(name="区", textbook_id="t" * 33)

    def test_blank_textbook_registers_no_key(self) -> None:
        os.environ["JZO_RESTART_DISABLED"] = "1"
        workspaces_api._save_workspaces([])
        result = _run(workspaces_api.create_workspace(
            workspaces_api.WorkspaceCreateRequest(name="无版本区", textbook_id="   "), _request()))
        entry = next(item for item in workspaces_api._load_workspaces() if item["id"] == result["id"])
        self.assertNotIn("textbook_id", entry, "空版本不该往档案里塞一个空键")

    def test_textbook_id_is_stripped_before_validation(self) -> None:
        os.environ["JZO_RESTART_DISABLED"] = "1"
        workspaces_api._save_workspaces([])
        known = self._known_textbooks()
        if not known:
            self.skipTest("当前环境没有并集登记表，无法验证前后空格这一路")
        padded = f"  {sorted(known)[0]}  "
        result = _run(workspaces_api.create_workspace(
            workspaces_api.WorkspaceCreateRequest(name="带空格区", textbook_id=padded), _request()))
        entry = next(item for item in workspaces_api._load_workspaces() if item["id"] == result["id"])
        self.assertEqual(entry["textbook_id"], padded.strip(), "登记的是去掉空白的净值")

    def test_front_end_registers_version_in_the_single_create_post(self) -> None:
        js = (ROOT / "static" / "js" / "settings.js").read_text(encoding="utf-8")
        block = js[js.index("function createWorkspace()"):
                   js.index("if (wsCreateBtn) wsCreateBtn.addEventListener")]
        self.assertIn('apiCall("/api/workspaces", "POST", { name: name, textbook_id: textbookId })', block)
        self.assertNotIn('apiCall("/api/workspaces/textbook"', block,
                         "新建路径不得再补一刀 /textbook——重启已经开始，那一刀会丢在进程退出当口")

    def test_api_reference_documents_the_field(self) -> None:
        doc = (ROOT / "docs" / "API_REFERENCE.md").read_text(encoding="utf-8")
        self.assertIn("textbook_id", doc)


class UiRestartContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "static" / "settings.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "static" / "js" / "settings.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "static" / "css" / "settings.css").read_text(encoding="utf-8")

    def _block(self, start_marker: str, end_marker: str) -> str:
        start = self.html.index(start_marker)
        return self.html[start:self.html.index(end_marker, start)]

    def test_switch_modal_carries_the_verbatim_warning(self) -> None:
        modal = self._block('id="wsSwitchModal"', 'id="wsRestartOverlay"')
        self.assertIn(WARNING_TEXT, " ".join(modal.split()))
        self.assertIn('class="mg-danger"', modal)
        self.assertIn('role="dialog"', modal)
        self.assertIn('aria-modal="true"', modal)
        self.assertIn("wsSwitchCancel", modal)

    def test_overlay_text_and_initial_state(self) -> None:
        overlay = self._block('id="wsRestartOverlay"', "<section class=\"st-block st-about\"")
        self.assertIn("正在重启底座，请稍候…", overlay)
        self.assertIn('role="alertdialog"', overlay)
        self.assertIn('aria-hidden="true"', overlay)
        self.assertIn("hidden", overlay)
        self.assertIn('id="wsRestartReloadBtn"', overlay)

    def test_js_waits_for_a_new_boot_id_before_reloading(self) -> None:
        self.assertIn('fetch("/healthz"', self.js)
        self.assertIn("setTimeout(tick, RESTART_POLL_MS)", self.js)
        self.assertIn("id !== oldBootId", self.js)
        self.assertIn("reloadHostPage()", self.js)
        self.assertIn('"TypeError"', self.js)

    def test_poll_uses_no_periodic_wall_clock_timer(self) -> None:
        """控制台页的锁死规则：不许 setInterval/requestAnimationFrame 这类周期墙钟。"""
        self.assertNotIn("setInterval", self.js)
        self.assertNotIn("requestAnimationFrame", self.js)
        self.assertNotIn("clearInterval", self.js)

    def test_js_never_fakes_recovery(self) -> None:
        """超时/失败必须显形：遮罩上给出如实文案与手动刷新出口。"""
        self.assertIn("重启等待超时", self.js)
        self.assertIn("restartFailed", self.js)
        self.assertIn("hideRestartWait()", self.js)
        self.assertIn("result.restarting", self.js)

    def test_overlay_sits_above_the_confirm_modal(self) -> None:
        restart_z = int(self.css.split(".st-restart-overlay {")[1].split("z-index:")[1]
                        .split(";")[0].strip())
        modal_z = int(self.css.split(".mg-modal-overlay {")[1].split("z-index:")[1]
                      .split(";")[0].strip())
        self.assertGreater(restart_z, modal_z)

    def test_workspace_list_entry_opens_the_modal_not_a_direct_switch(self) -> None:
        self.assertIn("function openWsSwitch(ws)", self.js)
        self.assertIn("confirmWsSwitch", self.js)
        self.assertIn('apiCall("/api/workspaces/switch", "POST"', self.js)


class DraftGuardContractTest(unittest.TestCase):
    """草稿保护的口径：红字必须如实说出草稿的去向，由用户当场裁决是否切换。"""

    def test_warning_names_both_restart_and_draft_parking(self) -> None:
        self.assertIn("重启底座", WARNING_TEXT)
        self.assertIn("未保存的草稿", WARNING_TEXT)
        self.assertIn("留在原工作区", WARNING_TEXT)
        self.assertIn("切回时自动恢复", WARNING_TEXT)
        self.assertTrue(WARNING_TEXT.endswith("是否继续？"))

    def test_modal_copy_does_not_promise_discard(self) -> None:
        """草稿已按区分箱留存，红字再写「丢弃」就是骗老师。"""
        html = (ROOT / "static" / "settings.html").read_text(encoding="utf-8")
        block = html[html.index('id="wsSwitchModalText"'):html.index("</p>", html.index('id="wsSwitchModalText"'))]
        self.assertNotIn("丢弃", block)
        self.assertIn("留在原工作区", block)

    def test_host_shell_does_not_silent_switch(self) -> None:
        workspace_js = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")
        self.assertNotIn("/api/workspaces/switch", workspace_js)


class DraftWorkspaceBoxContractTest(unittest.TestCase):
    """军令 #18-终 阶段一：草稿箱按工作区分箱——切库不丢、也不串到别的区。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.js = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")

    def test_slot_key_carries_workspace_then_plugin(self) -> None:
        self.assertIn("return draftPrefix(draftWorkspace) + pluginId + \".\" + key;", self.js,
                      "草稿槽位必须先是工作区、再是插件，缺一段就会串库")

    def test_workspace_id_comes_from_host_bootstrap(self) -> None:
        self.assertIn('fetch("/api/settings"', self.js)
        self.assertIn("data.workspace_id", self.js)

    def test_box_stays_closed_until_workspace_is_known(self) -> None:
        """问不到区就不许开箱：宁可存不下，也不能把 A 区草稿挂到 B 区。"""
        self.assertIn("if (!draftWorkspace) return draftBoxUnknown();", self.js)
        self.assertIn("草稿箱未开放", self.js)
        save = self.js[self.js.index("function saveDraft(pluginId, key, value)"):
                       self.js.index("function loadDraft(pluginId, key)")]
        self.assertIn("draftBoxUnknown", save)

    def test_relay_waits_for_boxing_before_answering_draft(self) -> None:
        block = self.js[self.js.index('if (method === "draft.save" || method === "draft.load")'):
                        self.js.index('var base = "/api/bank/plugins/')]
        self.assertIn("resolveDraftBox().then", block, "分箱没落地就答复，等于拿空区名存取")
        self.assertIn("return;", block, "草稿答复仍须短路，不发题库请求")

    def test_stale_and_overflowing_slots_are_swept(self) -> None:
        self.assertIn("DRAFT_TTL_MS", self.js)
        self.assertIn("DRAFT_BOX_MAX", self.js)
        self.assertIn("function sweepDraftBox()", self.js)

    def test_legacy_untagged_slots_are_migrated_not_dropped(self) -> None:
        block = self.js[self.js.index("function migrateLegacyDrafts(workspaceId)"):
                        self.js.index("function resolveDraftBox()")]
        self.assertIn("window.localStorage.setItem(next, text)", block, "旧草稿要搬家，不能一删了事")
        self.assertIn("if (text && !window.localStorage.getItem(next))", block,
                      "新箱已有同槽时以新箱为准，不许覆盖回来的草稿")

    def test_other_workspaces_boxed_slots_are_never_touched(self) -> None:
        """真机踩过的坑：B 区开机把 A 区已分箱的草稿当旧槽搬走，切回 A 区草稿就没了。
        判据必须是「工作区段形状」而不是「有没有点」——插件 id 是反向域名，天然带点。"""
        block = self.js[self.js.index("function migrateLegacyDrafts(workspaceId)"):
                        self.js.index("function resolveDraftBox()")]
        self.assertIn("DRAFT_BOXED_HEAD_RE", block, "已分箱的槽位要先让位，否则会在别区开机时被当旧草稿搬走")
        head = self.js[self.js.index("var DRAFT_BOXED_HEAD_RE"):
                       self.js.index("var draftWorkspace =")]
        self.assertIn("default", head)
        self.assertIn("ws_", head, "工作区段只认 default 与底座生成的 ws_ 前缀，插件 id 的首段永不长这样")

    def test_settings_api_exposes_workspace_id(self) -> None:
        main_py = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('"workspace_id": current_workspace_id()', main_py)


if __name__ == "__main__":
    unittest.main()
