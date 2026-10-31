"""能力路由字典的调用安全加固（军令 #19 第三部分）：契约级回归。

覆盖两层：
1. 后端：``requires_user`` 只认清单里的布尔真值，并原样进注册中心与发现接口；
2. 宿主：用户确认、64 KB 结果上限、按目标串行 + 1 秒 pending 通知、自动开页上限，
   以及配套的开发体验（设置页只读字典、打包工具打印被拒命令、模板调用方按钮）。

真实浏览器取证见 ``tools/command_registry_probe.py``（含 ``sidebar.right`` 面板目标）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_command_hardening``
"""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.core import commands
from app.core.plugins import validate_plugin

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "com.example.hardening"
MANIFEST = {
    "schema_version": "1.0",
    "id": PLUGIN_ID,
    "name": "加固契约探针",
    "version": "1.0.0",
    "api_version": "1.0",
    "kind": "renderer",
    "description": "只用于调用安全加固校验的最小插件",
    "license": "Apache-2.0",
    "entry": {"frontend": "dist/index.html"},
    "slots": ["stage.center"],
    "capabilities": ["question.render"],
    "permissions": [],
}


def build_plugin_dir(root: Path) -> Path:
    plugin_dir = root / PLUGIN_ID
    (plugin_dir / "dist").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "LICENSE").write_text("Apache License 2.0 (fixture)", encoding="utf-8")
    (plugin_dir / "dist" / "index.html").write_text("<!doctype html><title>p</title>", encoding="utf-8")
    (plugin_dir / "plugin.json").write_text(json.dumps(MANIFEST, ensure_ascii=False), encoding="utf-8")
    return plugin_dir


def between(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    return text[begin:text.index(end, begin)]


class RequiresUserNormalizeTest(unittest.TestCase):
    def validate(self, entries: list) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = json.loads(json.dumps(MANIFEST))
            manifest["contributes"] = {"commands": entries}
            info = validate_plugin(build_plugin_dir(Path(tmp)), manifest)
        return info["commands"]

    def test_01_true_flag_is_registered_as_boolean(self) -> None:
        rows = self.validate([{"id": "com.example.hard.destructive", "title": "批量删改",
                               "requires_user": True}])
        self.assertEqual(1, len(rows))
        self.assertEqual("com.example.hard.destructive", rows[0]["id"])
        self.assertEqual("批量删改", rows[0]["title"])
        self.assertIs(True, rows[0]["requires_user"])
        # 军令 #20 第二部分起，命令条目固定带三件说明字段（缺省为空/封口空 schema）。
        self.assertEqual("", rows[0]["description"])
        self.assertEqual("", rows[0]["returns"])
        self.assertEqual(
            {"type": "object", "properties": {}, "additionalProperties": False},
            rows[0]["params_schema"],
        )

    def test_02_non_boolean_values_are_false(self) -> None:
        rows = self.validate([
            {"id": "com.example.hard.one", "title": "一", "requires_user": 1},
            {"id": "com.example.hard.two", "title": "二", "requires_user": "true"},
            {"id": "com.example.hard.three", "title": "三", "requires_user": "yes"},
            {"id": "com.example.hard.four", "title": "四"},
        ])
        self.assertEqual([row["requires_user"] for row in rows], [False, False, False, False])

    def test_03_registry_propagates_flag(self) -> None:
        built = commands.build_registry([
            {"id": "com.example.a", "name": "甲", "enabled": True,
             "commands": [{"id": "com.example.a.export", "title": "导出", "requires_user": True}]},
            {"id": "com.example.b", "name": "乙", "enabled": True,
             "commands": [{"id": "com.example.b.tidy", "title": "整理"}]},
        ])
        flags = {row["id"]: row["requires_user"] for row in built["commands"]}
        self.assertEqual(flags, {"com.example.a.export": True, "com.example.b.tidy": False})

    def test_04_installed_plugin_model_carries_flag(self) -> None:
        from app.api.plugins import InstalledPlugin

        model = InstalledPlugin(
            id=PLUGIN_ID, name="x", version="1.0.0", api_version="1.0", kind="tool",
            description="d", license="Apache-2.0", slots=["stage.center"],
            capabilities=["question.render"], permissions=[],
            entry_url="/plugin-assets/com.example.hardening/dist/index.html",
            commands=[{"id": "com.example.hard.destructive", "title": "删改", "requires_user": True}],
        )
        self.assertIs(model.commands[0]["requires_user"], True)


class HostHardeningContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        cls.dialogs = (ROOT / "static" / "js" / "dialogs.js").read_text(encoding="utf-8")

    def test_05_limits_are_pinned(self) -> None:
        for line in (
            "var COMMAND_RESULT_MAX = 65536;",
            "var COMMAND_PENDING_MS = 1000;",
            "var COMMAND_QUEUE_MAX = 8;",
            "var COMMAND_AUTO_TAB_MAX = 5;",
        ):
            self.assertIn(line, self.stage)

    def test_06_requires_user_gate_precedes_dispatch(self) -> None:
        gate = self.stage.index("if (entry.requires_user)")
        dispatch = self.stage.index("function dispatchCommand")
        self.assertLess(gate, self.stage.index("dispatchCommand(caller, entry, plugin, commandId, context, trace, done, failWith);",
                                               gate))
        self.assertLess(self.stage.index("function confirmCommand"), dispatch)
        block = between(self.stage, "function confirmCommand", "function dispatchCommand")
        self.assertIn("window.JzoDialogs.confirm", block)
        self.assertIn("onAccept:", block)
        self.assertIn("onCancel:", block)
        self.assertIn('"COMMAND_DENIED"', self.stage)

    def test_07_result_size_cap_and_unserializable(self) -> None:
        self.assertIn("function commandResultBytes", self.stage)
        self.assertIn("new TextEncoder().encode(text).length", self.stage)
        self.assertIn('"COMMAND_RESULT_TOO_LARGE"', self.stage)
        self.assertIn('"COMMAND_RESULT_INVALID"', self.stage)
        body = between(self.stage, "function commandResultBytes", "function queueCommand")
        self.assertIn("JSON.stringify", body)
        self.assertIn("return -1;", body)

    def test_08_serial_queue_pending_and_busy(self) -> None:
        self.assertIn("var commandQueues = Object.create(null);", self.stage)
        queue = between(self.stage, "function queueCommand", "function commandOpenedTabs")
        self.assertIn("queue.tail.then", queue)
        self.assertIn("queue.depth -= 1;", queue)
        self.assertIn('"COMMAND_BUSY"', queue)
        dispatch = between(self.stage, "function dispatchCommand", "function replyHost")
        self.assertIn("COMMAND_PENDING_MS", dispatch)
        self.assertIn('notify(caller, "command.pending"', dispatch)
        self.assertIn('code: "COMMAND_PENDING"', dispatch)
        self.assertIn('"stage.command.pending"', dispatch)
        self.assertIn("window.clearTimeout(pendingTimer)", dispatch)

    def test_09_auto_opened_tab_cap(self) -> None:
        self.assertIn("function commandOpenedTabs", self.stage)
        self.assertIn("tab.openedByCommand === true", self.stage)
        self.assertIn("handle.openedByCommand = true;", self.stage)
        self.assertIn('"COMMAND_LIMIT"', self.stage)
        gate = self.stage.index("commandOpenedTabs() >= COMMAND_AUTO_TAB_MAX")
        open_call = self.stage.index("handle = openPlugin(plugin);", gate)
        self.assertLess(gate, open_call)

    def test_10_list_and_catalog_expose_flag(self) -> None:
        listing = between(self.stage, "function listCommands", "function commandTarget")
        self.assertIn("requires_user: item.requires_user === true", listing)
        catalog = between(self.stage, "function setPluginCatalog", "function listCommands")
        self.assertIn("requires_user: command.requires_user === true", catalog)

    def test_11_dialog_confirms_cancel_callback(self) -> None:
        block = between(self.dialogs, "confirm: function (spec)", "}\n  };")
        self.assertIn('typeof options.onCancel === "function"', block)
        self.assertIn("options.onCancel()", block)


class DeveloperExperienceTest(unittest.TestCase):
    def test_12_settings_has_readonly_dictionary(self) -> None:
        html = (ROOT / "static" / "settings.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "js" / "settings.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "settings.css").read_text(encoding="utf-8")
        self.assertIn('id="cmdRegistry"', html)
        self.assertIn('id="cmdRegistryBody"', html)
        self.assertIn('id="cmdRegistryIssues"', html)
        self.assertIn("只读", html)
        block = between(script, "function renderCommandRegistry", "function renameFromCard")
        self.assertIn('body.commands', block)
        self.assertIn('body.commands_rejected', block)
        self.assertIn("command.requires_user", block)
        self.assertNotIn("innerHTML", block, "字典表只许 textContent 落文案")
        self.assertIn("renderCommandRegistry(installedBody)", script)
        self.assertIn(".mg-cmdtable", css)

    def test_13_build_tool_prints_rejected_commands(self) -> None:
        source = (ROOT / "tools" / "build_plugin.py").read_text(encoding="utf-8")
        self.assertIn("command_issues: list[dict[str, str]] = []", source)
        self.assertIn("validate_plugin(plugin_dir, manifest, command_issues)", source)
        self.assertIn("[WARN]", source)
        self.assertIn("未登记", source)

    def test_14_template_has_caller_buttons_and_zip_in_sync(self) -> None:
        template = ROOT / "examples" / "template-plugin"
        html = (template / "dist" / "index.html").read_text(encoding="utf-8")
        script = (template / "dist" / "plugin.js").read_text(encoding="utf-8")
        manifest = json.loads((template / "plugin.json").read_text(encoding="utf-8"))
        self.assertIn('id="list-cmd-btn"', html)
        self.assertIn('id="echo-cmd-btn"', html)
        self.assertIn('callHost("command.list")', script)
        self.assertIn('callHost("command.execute"', script)
        self.assertIn('message.event === "command.pending"', script)
        self.assertIn('"requires_user": true', script, "模板注释要教会作者高副作用标记")
        self.assertEqual([item["id"] for item in manifest["contributes"]["commands"]],
                         ["org.example.template.echo"])
        package = ROOT / "examples" / "template-plugin.zip"
        self.assertTrue(package.is_file(), "模板 zip 必须随仓库分发")
        with zipfile.ZipFile(package) as archive:
            self.assertEqual(
                archive.read("org.example.template/dist/plugin.js").decode("utf-8"), script,
                "zip 里的脚本必须与源码同步，改模板后要重打包")
            self.assertEqual(
                archive.read("org.example.template/dist/index.html").decode("utf-8"), html)

    def test_15_docs_list_every_new_code(self) -> None:
        spec = (ROOT / "PLUGIN_SPEC.md").read_text(encoding="utf-8")
        api = (ROOT / "API_REFERENCE.md").read_text(encoding="utf-8")
        for code in ("COMMAND_DENIED", "COMMAND_RESULT_TOO_LARGE", "COMMAND_RESULT_INVALID",
                     "COMMAND_BUSY", "COMMAND_LIMIT", "COMMAND_PENDING"):
            self.assertIn(code, spec)
            self.assertIn(code, api)
        # 极简 README 只留指引，这四个口径跟着「给 AI 的提示词」一起搬进了 PLUGIN_SPEC §8；
        # README 已改为指向该章，所以判据落在 spec 上，不再要求速览页复述细节。
        for hint in ("requires_user", "65536", "command.pending", "COMMAND_LIMIT"):
            self.assertIn(hint, spec)
        self.assertIn("如何用 AI 写插件", (ROOT / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
