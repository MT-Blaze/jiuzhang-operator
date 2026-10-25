"""能力路由字典（Command Registry）契约：军令 #19 第二部分。

覆盖四层：
1. 清单侧：``contributes.commands`` 归一、官方命名空间只给官方插件、坏条目逐条丢弃；
2. 注册中心：启用集内建全局字典，同 id 先到先得，停用插件的命令不登记；
3. 发现接口：``GET /api/plugins`` 的 ``commands`` / ``commands_rejected`` 与插件条目同源；
4. 宿主侧：``command.list`` / ``command.execute`` 在转发白名单里、有明确分发分支、
   不经 HTTP 直连别家插件。

运行：``.venv/Scripts/python.exe -m unittest tests.test_command_registry``
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core import commands
from app.core.plugins import discover_plugins, validate_plugin

ROOT = Path(__file__).resolve().parents[1]
BASE_MANIFEST = {
    "schema_version": "1.0",
    "id": "org.jiuzhang.command-probe",
    "name": "命令契约探针",
    "version": "1.0.0",
    "api_version": "1.0",
    "kind": "renderer",
    "description": "只用于能力路由字典校验的最小插件",
    "license": "Apache-2.0",
    "entry": {"frontend": "dist/index.html"},
    "slots": ["question.card"],
    "capabilities": ["question.render"],
    "permissions": [],
}
THIRD_PARTY_ID = "com.example.command-probe"


def build_plugin_dir(root: Path, manifest: dict) -> Path:
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


class NormalizeCommandsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def validate(self, contributes, plugin_id: str | None = None) -> tuple[dict, list]:
        manifest = json.loads(json.dumps(BASE_MANIFEST))
        if plugin_id:
            manifest["id"] = plugin_id
        if contributes is not None:
            manifest["contributes"] = contributes
        issues: list = []
        info = validate_plugin(build_plugin_dir(self.root, manifest), manifest, issues)
        return info, issues

    def test_01_absent_contributes_yields_empty_list(self) -> None:
        info, issues = self.validate(None)
        self.assertEqual(info["commands"], [])
        self.assertEqual(issues, [])

    def test_02_official_plugin_registers_all_five_categories(self) -> None:
        wanted = [
            "org.jiuzhang.action.input.import_pdf",
            "org.jiuzhang.action.process.format_latex",
            "org.jiuzhang.action.output.export_word",
            "org.jiuzhang.action.data.bank_stats",
            "org.jiuzhang.action.view.open_dashboard",
        ]
        info, issues = self.validate(
            {"commands": [{"id": cid, "title": "示例 " + cid.rsplit(".", 1)[-1]} for cid in wanted]}
        )
        self.assertEqual([item["id"] for item in info["commands"]], wanted)
        self.assertEqual(issues, [])

    def test_03_third_party_cannot_claim_official_namespace(self) -> None:
        info, issues = self.validate(
            {
                "commands": [
                    {"id": "org.jiuzhang.action.output.export_word", "title": "导出为Word"},
                    {"id": "com.example.tidy_tags", "title": "整理标签"},
                ]
            },
            plugin_id=THIRD_PARTY_ID,
        )
        self.assertEqual([item["id"] for item in info["commands"]], ["com.example.tidy_tags"])
        self.assertEqual(len(issues), 1)
        self.assertIn("官方插件", issues[0]["reason"])
        self.assertEqual(issues[0]["plugin_id"], THIRD_PARTY_ID)

    def test_04_official_namespace_must_use_five_categories(self) -> None:
        info, issues = self.validate(
            {"commands": [{"id": "org.jiuzhang.action.render.card", "title": "越界分类"}]}
        )
        self.assertEqual(info["commands"], [])
        self.assertIn("五大分类", issues[0]["reason"])

    def test_05_official_command_needs_leaf_segment(self) -> None:
        info, issues = self.validate(
            {"commands": [{"id": "org.jiuzhang.action.output", "title": "缺叶子"}]}
        )
        self.assertEqual(info["commands"], [])
        self.assertIn("缺叶子名", issues[0]["reason"])

    def test_06_bad_shapes_are_dropped_one_by_one(self) -> None:
        info, issues = self.validate(
            {
                "commands": [
                    {"id": "com.example.Upper", "title": "大写"},
                    {"id": "com.example", "title": "段数不够"},
                    {"id": "com.example.deep.a.b.c.d.e.f.g", "title": "段数过多"},
                    {"id": "com.example.no-title"},
                    {"id": "com.example.good", "title": "  正常   标题  "},
                    "not-an-object",
                ]
            }
        )
        self.assertEqual([item["id"] for item in info["commands"]], ["com.example.good"])
        self.assertEqual(info["commands"][0]["title"], "正常 标题")
        self.assertEqual(len(issues), 5)

    def test_07_duplicate_inside_one_plugin_kept_once(self) -> None:
        info, issues = self.validate(
            {
                "commands": [
                    {"id": "com.example.dup", "title": "第一次"},
                    {"id": "com.example.dup", "title": "第二次"},
                ]
            }
        )
        self.assertEqual(len(info["commands"]), 1)
        self.assertEqual(info["commands"][0]["title"], "第一次")
        self.assertIn("重复", issues[0]["reason"])

    def test_08_command_count_is_capped(self) -> None:
        items = [
            {"id": "com.example.cmd%02d" % index, "title": "命令 %d" % index}
            for index in range(commands.MAX_COMMANDS + 5)
        ]
        info, issues = self.validate({"commands": items})
        self.assertEqual(len(info["commands"]), commands.MAX_COMMANDS)
        self.assertTrue(any("上限" in item["reason"] for item in issues))

    def test_09_non_dict_contributes_is_ignored_with_reason(self) -> None:
        info, issues = self.validate([{"id": "com.example.x", "title": "x"}])
        self.assertEqual(info["commands"], [])
        self.assertIn("必须是对象", issues[0]["reason"])


class RegistryTest(unittest.TestCase):
    def _plugin(self, plugin_id: str, name: str, cmds: list[str], enabled: bool = True) -> dict:
        return {
            "id": plugin_id,
            "name": name,
            "enabled": enabled,
            "commands": [{"id": cid, "title": cid.rsplit(".", 1)[-1]} for cid in cmds],
        }

    def test_10_registry_is_sorted_and_owned(self) -> None:
        built = commands.build_registry(
            [
                self._plugin("org.jiuzhang.b", "乙", ["org.jiuzhang.action.output.print"]),
                self._plugin("org.jiuzhang.a", "甲", ["org.jiuzhang.action.output.export_word"]),
            ]
        )
        self.assertEqual(
            [item["id"] for item in built["commands"]],
            ["org.jiuzhang.action.output.export_word", "org.jiuzhang.action.output.print"],
        )
        self.assertEqual(built["commands"][0]["plugin_id"], "org.jiuzhang.a")
        self.assertEqual(built["commands"][0]["plugin_name"], "甲")

    def test_11_duplicate_command_first_owner_wins(self) -> None:
        built = commands.build_registry(
            [
                self._plugin("org.jiuzhang.z", "后", ["org.jiuzhang.action.view.panel"]),
                self._plugin("org.jiuzhang.a", "先", ["org.jiuzhang.action.view.panel"]),
            ]
        )
        self.assertEqual(len(built["commands"]), 1)
        self.assertEqual(built["commands"][0]["plugin_id"], "org.jiuzhang.a")
        self.assertEqual(len(built["issues"]), 1)
        self.assertEqual(built["issues"][0]["plugin_id"], "org.jiuzhang.z")

    def test_12_disabled_plugin_commands_are_not_registered(self) -> None:
        built = commands.build_registry(
            [self._plugin("com.example.off", "停用", ["com.example.off.tidy"], enabled=False)]
        )
        self.assertEqual(built["commands"], [])
        self.assertEqual(built["issues"], [])


class DiscoveryContractTest(unittest.TestCase):
    def test_13_discovery_ships_registry_and_rejections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = json.loads(json.dumps(BASE_MANIFEST))
            good["contributes"] = {
                "commands": [{"id": "org.jiuzhang.action.output.export_word", "title": "导出为Word"}]
            }
            build_plugin_dir(root, good)
            bad = json.loads(json.dumps(BASE_MANIFEST))
            bad["id"] = THIRD_PARTY_ID
            bad["contributes"] = {
                "commands": [{"id": "org.jiuzhang.action.output.export_word", "title": "蹭名"}]
            }
            build_plugin_dir(root, bad)
            with mock.patch.dict(os.environ, {"JZO_PLUGINS_DIR": tmp}):
                data = discover_plugins()
        self.assertEqual(
            [item["id"] for item in data["commands"]],
            ["org.jiuzhang.action.output.export_word"],
        )
        self.assertEqual(data["commands"][0]["plugin_id"], "org.jiuzhang.command-probe")
        self.assertTrue(
            any(item["plugin_id"] == THIRD_PARTY_ID for item in data["commands_rejected"])
        )
        for plugin in data["plugins"]:
            self.assertIsInstance(plugin["commands"], list)


class HostApiContractTest(unittest.TestCase):
    """宿主侧只做源码级契约：真实转发由 tools/command_registry_probe.py 在浏览器里取证。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.stage = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        cls.workspace = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")

    def _array_block(self, name: str) -> str:
        start = self.stage.index("var " + name + " = [")
        end = self.stage.index("];", start)
        return self.stage[start:end]

    def test_14_both_methods_are_whitelisted_but_not_ai_only(self) -> None:
        relay = self._array_block("RELAY_METHODS")
        self.assertIn('"command.list"', relay)
        self.assertIn('"command.execute"', relay)
        ai_only = self._array_block("AI_ONLY_METHODS")
        self.assertNotIn("command.", ai_only, "查表与调度不要求 ai:invoke，普通插件也能用")

    def test_15_dispatch_precedes_the_tail_refusal(self) -> None:
        # 白名单里的方法必须有分支：漏分发会掉到末尾的 UNSUPPORTED_METHOD（真机曾清空题篮）。
        tail = self.stage.index('failWith("UNSUPPORTED_METHOD", "宿主转发表未实现方法：')
        list_at = self.stage.index('if (method === "command.list")')
        execute_at = self.stage.index('if (method === "command.execute")')
        self.assertLess(list_at, tail)
        self.assertLess(execute_at, tail)

    def test_16_execute_looks_up_then_forwards_through_the_host(self) -> None:
        for code in (
            '"COMMAND_NOT_FOUND"',
            '"COMMAND_TARGET_MISSING"',
            '"COMMAND_NOT_READY"',
            '"COMMAND_LOOP"',
            'request(target, "command.execute"',
            "trace: trace.concat([entry.plugin_id])",
        ):
            self.assertIn(code, self.stage)
        self.assertNotIn(
            "fetch(",
            self.stage[self.stage.index("function executeCommand"):self.stage.index("function replyHost")],
            "命令调度不许绕过宿主另起 HTTP",
        )

    def test_17_catalog_is_refreshed_with_every_plugin_list(self) -> None:
        self.assertIn("window.JzoStage.setPluginCatalog(plugins)", self.workspace)
        self.assertIn("setPluginCatalog: setPluginCatalog", self.stage)

    def test_18_install_response_model_carries_commands(self) -> None:
        from app.api.plugins import InstalledPlugin

        model = InstalledPlugin(
            id="com.example.x",
            name="x",
            version="1.0.0",
            api_version="1.0",
            kind="tool",
            description="d",
            license="Apache-2.0",
            slots=["stage.center"],
            capabilities=["question.render"],
            permissions=[],
            entry_url="/plugin-assets/com.example.x/dist/index.html",
        )
        self.assertEqual(model.commands, [])


class TemplatePluginTest(unittest.TestCase):
    def test_19_template_declares_and_handles_a_command(self) -> None:
        template = ROOT / "examples" / "template-plugin"
        manifest = json.loads((template / "plugin.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            # 校验器要求顶层目录名与 id 一字不差；模板目录为了肉眼好认叫 template-plugin。
            plugin_dir = Path(tmp) / manifest["id"]
            shutil.copytree(template, plugin_dir)
            info = validate_plugin(plugin_dir, manifest)
        self.assertEqual([item["id"] for item in info["commands"]], ["org.example.template.echo"])
        script = (template / "dist" / "plugin.js").read_text(encoding="utf-8")
        self.assertIn('if (method === "command.execute")', script)


if __name__ == "__main__":
    unittest.main()
