"""AI 命令面（command_list / command_execute）契约：军令 #20 第三部分。

覆盖五层：
1. 字典查询：AI 看到的 16 条官方命令与清单、风险、参数声明同源；
2. 上下文防绑架：封口、底层保留键、公开 id 白名单、长度与枚举；
3. 高副作用拦截：requires_user 只发确认卡与一次性令牌，绝不执行；
4. 确认与取消：确认只核销一次，取消后令牌立即作废、命令不落地；
5. 标准数据放行：无界面引擎就地执行，有界面插件回 command_request 交宿主转发。

运行：``.venv/Scripts/python.exe -m unittest tests.test_agent_command_tools``
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.api import agents
from app.core import bank, command_tools
from app.core.config import settings

ROOT = Path(__file__).resolve().parents[1]
ENGINE = "org.jiuzhang.bank-engine"
STAMP = "2026-01-15T09:00:00+08:00"
SEARCH = "org.jiuzhang.action.data.bank_search"
STATS = "org.jiuzhang.action.data.bank_stats"
TOPICS = "org.jiuzhang.action.data.bank_topics"
FILTER = "org.jiuzhang.action.view.filter_questions"
MERGE = "org.jiuzhang.action.data.dedupe_merge"
EXPORT = "org.jiuzhang.action.output.export_paper"


def _seed_questions(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        for question_id, stem in (
            ("q_ai_cmd_0001", "AI 命令面测试：彩虹独角兽与导数"),
            ("q_ai_cmd_0002", "AI 命令面测试：彩虹独角兽与数列"),
            ("q_ai_cmd_0003", "AI 命令面测试：普通函数题"),
        ):
            con.execute(
                "INSERT OR REPLACE INTO questions (id,type,stem,options,answer,solution,"
                "extensions,difficulty,created_at,updated_at)"
                " VALUES (?,'solution',?,'[]',NULL,NULL,'[]','L2',?,?)",
                (question_id, stem, STAMP, STAMP),
            )
        con.commit()
    finally:
        con.close()


class CommandToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.saved = (os.environ.get("JZO_DATA_DIR"), os.environ.get("JZO_PLUGINS_DIR"),
                     settings.workspace_id)
        os.environ["JZO_DATA_DIR"] = str(base / "data")
        os.environ["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
        settings.workspace_id = None
        bank._structure_cache.clear()
        _seed_questions(bank.ensure_bank(ENGINE))

    @classmethod
    def tearDownClass(cls) -> None:
        bank._structure_cache.clear()
        for key, value in zip(("JZO_DATA_DIR", "JZO_PLUGINS_DIR"), cls.saved[:2]):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        settings.workspace_id = cls.saved[2]
        cls.tmp.cleanup()

    def setUp(self) -> None:
        with command_tools._pending_lock:
            command_tools._pending.clear()

    # --- 1. 字典查询 ---------------------------------------------------
    def test_01_tool_schemas_are_openai_functions(self) -> None:
        tools = command_tools.build_tools()
        names = [item["function"]["name"] for item in tools]
        self.assertEqual(["command_list", "command_execute"], names)
        execute = tools[1]["function"]["parameters"]
        self.assertEqual(["command_id"], execute["required"])
        self.assertEqual(
            ["input", "process", "output", "data", "view"],
            tools[0]["function"]["parameters"]["properties"]["category"]["enum"],
        )

    def test_02_dictionary_matches_manifest(self) -> None:
        result = command_tools.list_commands({})
        self.assertTrue(result["ok"])
        self.assertEqual("command.list", result["action"])
        commands = result["data"]["commands"]
        self.assertEqual(16, len(commands))
        ids = {item["id"] for item in commands}
        for command_id in (SEARCH, STATS, TOPICS, FILTER, MERGE, EXPORT):
            self.assertIn(command_id, ids)
        merge = next(item for item in commands if item["id"] == MERGE)
        self.assertTrue(merge["requires_user"])
        self.assertEqual("high", merge["risk"]["level"])
        self.assertFalse(merge["params_schema"]["additionalProperties"])
        search = next(item for item in commands if item["id"] == SEARCH)
        self.assertTrue(search["headless"])
        self.assertEqual("low", search["risk"]["level"])
        self.assertIn("query", search["params_schema"]["properties"])

    def test_03_dictionary_filters(self) -> None:
        engine = command_tools.list_commands({"plugin_id": ENGINE})
        self.assertEqual(3, engine["data"]["total"])
        high = command_tools.list_commands({"requires_user": True})
        self.assertEqual(7, high["data"]["total"])
        self.assertTrue(all(item["requires_user"] for item in high["data"]["commands"]))
        view = command_tools.list_commands({"category": "view"})
        self.assertEqual(2, view["data"]["total"])
        missing = command_tools.list_commands({"plugin_id": "com.example.nope"})
        self.assertFalse(missing["ok"])
        self.assertEqual("COMMAND_NOT_FOUND", missing["error_code"])

    # --- 2. 上下文防绑架 -----------------------------------------------
    def test_04_sealed_context_rejects_unknown_and_reserved_keys(self) -> None:
        schema = next(
            item for item in command_tools.list_commands({"plugin_id": ENGINE})["data"]["commands"]
            if item["id"] == SEARCH
        )["params_schema"]
        _, problem = command_tools.normalize_context(schema, {"query": "导数", "sql": "select *"})
        self.assertIn("保留键", problem)
        _, problem = command_tools.normalize_context(schema, {"query": "导数", "rowid": 42})
        self.assertIn("保留键", problem)
        _, problem = command_tools.normalize_context(schema, {"query": "导数", "table": "questions"})
        self.assertIn("保留键", problem)
        _, problem = command_tools.normalize_context(schema, {"query": "导数", "extra": 1})
        self.assertIn("未声明参数", problem)
        cleaned, problem = command_tools.normalize_context(schema, {"query": "导数"})
        self.assertEqual("", problem)
        self.assertEqual({"query": "导数"}, cleaned)

    def test_05_public_ids_only_never_rowids(self) -> None:
        merge = command_tools.list_commands({"requires_user": True})["data"]["commands"]
        schema = next(item for item in merge if item["id"] == MERGE)["params_schema"]
        _, problem = command_tools.normalize_context(
            schema, {"primary_id": "42", "copy_ids": ["q_ok"]}
        )
        self.assertIn("公开 id", problem)
        _, problem = command_tools.normalize_context(
            schema, {"primary_id": "q_ok", "copy_ids": [42]}
        )
        self.assertIn("公开 id", problem)
        _, problem = command_tools.normalize_context(
            schema, {"primary_id": "q_ok", "copy_ids": ["q_%d" % index for index in range(21)]}
        )
        self.assertIn("超过 20 项", problem)
        cleaned, problem = command_tools.normalize_context(
            schema, {"primary_id": "q_ok", "copy_ids": ["q_1", "q_2"]}
        )
        self.assertEqual("", problem)
        self.assertEqual(2, len(cleaned["copy_ids"]))

    def test_06_engine_schema_bounds_and_enum(self) -> None:
        search = next(
            item for item in command_tools.list_commands({"plugin_id": ENGINE})["data"]["commands"]
            if item["id"] == SEARCH
        )["params_schema"]
        _, problem = command_tools.normalize_context(search, {"limit": 0})
        self.assertIn("不得小于", problem)
        _, problem = command_tools.normalize_context(search, {"limit": 21})
        self.assertIn("不得大于", problem)
        _, problem = command_tools.normalize_context(search, {"grade": "大一"})
        self.assertIn("只能是", problem)
        _, problem = command_tools.normalize_context(search, {"query": "x" * 101})
        self.assertIn("超过 100", problem)
        cleaned, problem = command_tools.normalize_context(search, {"limit": 5, "grade": "高一"})
        self.assertEqual("", problem)
        self.assertEqual(5, cleaned["limit"])

    def test_07_context_size_cap(self) -> None:
        schema = {"type": "object", "properties": {}, "additionalProperties": True}
        _, problem = command_tools.normalize_context(schema, {"blob": "x" * 16400})
        self.assertIn("上限", problem)

    # --- 3. 高副作用拦截 -----------------------------------------------
    def test_08_high_risk_returns_card_and_never_executes(self) -> None:
        with mock.patch.object(command_tools, "_dispatch") as dispatch:
            result = command_tools.execute_command({
                "command_id": MERGE,
                "context": {"primary_id": "q_ai_cmd_0001", "copy_ids": ["q_ai_cmd_0002"]},
            })
        dispatch.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertTrue(result["pending"])
        self.assertFalse(result["executed"])
        self.assertEqual("high", result["risk"]["level"])
        token = result["confirmation"]["token"]
        self.assertEqual(16, len(token))
        card = result["ui_cards"][0]
        self.assertEqual("confirm_card", card["type"])
        self.assertIn("调用插件", card["description"])
        self.assertIn("功能", card["description"])
        self.assertIn("涉及数据", card["description"])
        self.assertIn("风险等级：高", card["description"])
        self.assertIn("copy_ids", card["description"])
        labels = [action["label"] for action in card["actions"]]
        self.assertEqual(["确认执行", "取消"], labels)
        for action in card["actions"]:
            intent = command_tools.match_intent(action["command"])
            self.assertIsNotNone(intent)
            self.assertEqual("command_execute", intent["tool"])
            self.assertEqual(token, intent["arguments"].get(
                "confirm_token") or intent["arguments"].get("cancel_token"))
            self.assertTrue(action.get("silent"))

    def test_09_bad_context_is_rejected_before_any_card(self) -> None:
        with mock.patch.object(command_tools, "_dispatch") as dispatch:
            result = command_tools.execute_command({
                "command_id": MERGE,
                "context": {"primary_id": "42", "copy_ids": ["q_ai_cmd_0002"]},
            })
        dispatch.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertFalse(result["executed"])
        self.assertEqual("CONTEXT_INVALID", result["error_code"])
        self.assertNotIn("ui_cards", result)
        self.assertEqual(0, len(command_tools._pending))

    def test_10_unknown_command_is_rejected(self) -> None:
        result = command_tools.execute_command({
            "command_id": "com.example.nope.run", "context": {},
        })
        self.assertFalse(result["ok"])
        self.assertFalse(result["executed"])
        self.assertEqual("COMMAND_NOT_FOUND", result["error_code"])

    # --- 4. 确认与取消 -------------------------------------------------
    def test_11_confirm_consumes_token_once(self) -> None:
        issued = command_tools.execute_command({
            "command_id": MERGE,
            "context": {"primary_id": "q_ai_cmd_0001", "copy_ids": ["q_ai_cmd_0002"]},
        })
        token = issued["confirmation"]["token"]
        with mock.patch.object(
            command_tools, "_dispatch", wraps=command_tools._dispatch
        ) as dispatch:
            confirmed = command_tools.execute_command({"confirm_token": token})
            repeated = command_tools.execute_command({"confirm_token": token})
        self.assertEqual(1, dispatch.call_count)
        self.assertTrue(confirmed["ok"])
        self.assertTrue(confirmed["confirmed"])
        self.assertFalse(confirmed["executed"])
        self.assertTrue(confirmed["pending"])
        self.assertEqual(MERGE, confirmed["command_request"]["command_id"])
        self.assertEqual(["q_ai_cmd_0002"], confirmed["command_request"]["context"]["copy_ids"])
        self.assertFalse(repeated["ok"])
        self.assertEqual("COMMAND_CONFIRM_EXPIRED", repeated["error_code"])

    def test_12_cancel_does_not_execute_and_kills_token(self) -> None:
        issued = command_tools.execute_command({
            "command_id": MERGE,
            "context": {"primary_id": "q_ai_cmd_0001", "copy_ids": ["q_ai_cmd_0002"]},
        })
        token = issued["confirmation"]["token"]
        with mock.patch.object(command_tools, "_dispatch") as dispatch:
            cancelled = command_tools.execute_command({"cancel_token": token})
        dispatch.assert_not_called()
        self.assertTrue(cancelled["ok"])
        self.assertTrue(cancelled["cancelled"])
        self.assertFalse(cancelled["executed"])
        self.assertIn("没有发送", cancelled["summary"])
        after = command_tools.execute_command({"confirm_token": token})
        self.assertFalse(after["ok"])
        self.assertEqual("COMMAND_CONFIRM_EXPIRED", after["error_code"])

    # --- 5. 标准数据放行 -------------------------------------------------
    def test_13_headless_search_executes_natively(self) -> None:
        result = command_tools.execute_command({
            "command_id": SEARCH,
            "context": {"query": "彩虹独角兽", "limit": 5},
        })
        self.assertTrue(result["ok"])
        self.assertTrue(result["executed"])
        self.assertFalse(result["pending"])
        self.assertEqual(2, result["data"]["total"])
        ids = {item["id"] for item in result["data"]["items"]}
        self.assertEqual({"q_ai_cmd_0001", "q_ai_cmd_0002"}, ids)
        for item in result["data"]["items"]:
            self.assertTrue(item["id"].startswith("q_"))
            self.assertLessEqual(len(item["stem"]), 120)
            self.assertNotIn("rowid", item)
        # 结果里不得泄露底层表名 / 数据库路径 / 行号。
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("questions", encoded)
        self.assertNotIn(".db", encoded)

    def test_14_headless_stats_and_topics_execute(self) -> None:
        stats = command_tools.execute_command({"command_id": STATS, "context": {}})
        self.assertTrue(stats["executed"])
        self.assertGreaterEqual(stats["data"]["total"], 3)
        for key in ("grades", "difficulties", "types", "chapters", "textbooks"):
            self.assertIn(key, stats["data"])
        topics = command_tools.execute_command({
            "command_id": TOPICS, "context": {"search": "函数"},
        })
        self.assertTrue(topics["executed"])
        self.assertIn("items", topics["data"])

    def test_15_iframe_command_is_handed_back_to_host(self) -> None:
        result = command_tools.execute_command({
            "command_id": FILTER, "context": {"grade": "高一", "difficulty": "L2"},
        })
        self.assertTrue(result["ok"])
        self.assertFalse(result["executed"])
        self.assertTrue(result["pending"])
        request = result["command_request"]
        self.assertEqual(FILTER, request["command_id"])
        self.assertEqual({"grade": "高一", "difficulty": "L2"}, request["context"])
        self.assertEqual("low", request["risk"]["level"])
        self.assertIn("宿主", result["summary"])

    def test_16_high_risk_confirm_then_host_request(self) -> None:
        issued = command_tools.execute_command({
            "command_id": MERGE,
            "context": {"primary_id": "q_ai_cmd_0001", "copy_ids": ["q_ai_cmd_0002"]},
        })
        confirmed = command_tools.execute_command({
            "confirm_token": issued["confirmation"]["token"],
        })
        self.assertTrue(confirmed["confirmed"])
        self.assertTrue(confirmed["pending"])
        self.assertEqual(MERGE, confirmed["command_request"]["command_id"])

    # --- 6. 宿主兜底与对话接线 -------------------------------------------
    def test_17_intent_matching(self) -> None:
        issued = command_tools.execute_command({
            "command_id": MERGE,
            "context": {"primary_id": "q_ai_cmd_0001", "copy_ids": ["q_ai_cmd_0002"]},
        })
        token = issued["confirmation"]["token"]
        self.assertEqual(
            {"tool": "command_execute", "arguments": {"confirm_token": token}},
            command_tools.match_intent("确认执行命令（确认码 %s）" % token),
        )
        self.assertEqual(
            {"tool": "command_execute", "arguments": {"cancel_token": token}},
            command_tools.match_intent("取消执行命令（确认码 %s）" % token),
        )
        self.assertEqual(
            {"tool": "command_list", "arguments": {}},
            command_tools.match_intent("有哪些命令"),
        )
        self.assertIsNone(command_tools.match_intent("确认执行命令"))
        self.assertIsNone(command_tools.match_intent("帮我把这道题改简单点"))

    def test_18_agent_wiring(self) -> None:
        listed = agents._run_tool("command_list", "{}")
        self.assertTrue(listed["ok"])
        self.assertEqual(16, listed["data"]["total"])
        calls = agents._execute_calls(
            [agents._make_host_call({
                "tool": "command_execute",
                "arguments": {"command_id": FILTER, "context": {"grade": "高一"}},
            })],
            "host",
        )
        self.assertEqual(1, len(calls))
        self.assertEqual(FILTER, calls[0]["command_request"]["command_id"])
        self.assertEqual("host", calls[0]["routed_by"])
        self.assertTrue(calls[0]["ok"])
        prompt = agents.build_chat_system_prompt({}, command_tools.build_tools())
        self.assertIn("command_list", prompt)
        self.assertIn("command_execute", prompt)
        text = (ROOT / "app" / "api" / "agents.py").read_text(encoding="utf-8")
        self.assertIn("direct_intent = command_tools.match_intent", text)
        self.assertIn("command_tools.match_intent(user_input)", text)

    def test_19_chat_plugin_executes_command_request(self) -> None:
        text = (
            ROOT / "plugins" / "org.jiuzhang.chat" / "dist" / "plugin.js"
        ).read_text(encoding="utf-8")
        self.assertIn("runCommandRequests", text)
        self.assertIn("command_request", text)
        self.assertIn('hostCall("command.execute"', text)
        self.assertIn("silent: action.silent === true", text)
        self.assertIn("if (!options.silent)", text)


if __name__ == "__main__":
    unittest.main()
