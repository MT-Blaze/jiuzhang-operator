"""插件工具桥与对话工具调用契约（v0.5.1）。

覆盖：
1. 已安装插件 → OpenAI ``tools`` 结构（名称、动作枚举、参数约束）。
2. 明确句式 → 插件工具路由（问题号解析、无关指令不误判）。
3. 工具真实执行：读取插件自带题库并输出自然语言拆分结果。
4. 无模型密钥时，宿主兜底仍能把「拆分第一题」执行成插件结果（端到端）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_agent_plugin_tools``
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import plugin_tools  # noqa: E402
from app.core.config import settings  # noqa: E402

DEMO_TOOL = "plugin_org_jiuzhang_demo-bank"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class PluginToolsUnitTest(unittest.TestCase):
    """用临时插件目录跑，不依赖仓库里是否已静默安装种子插件。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.plugins_dir = Path(cls.tmp.name) / "plugins"
        cls.plugins_dir.mkdir()
        with zipfile.ZipFile(ROOT / "examples" / "demo_plugin.zip") as zf:
            zf.extractall(cls.plugins_dir)
        cls.patcher = mock.patch.dict(os.environ, {"JZO_PLUGINS_DIR": str(cls.plugins_dir)})
        cls.patcher.start()
        cls.tools = plugin_tools.build_tools()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.patcher.stop()
        cls.tmp.cleanup()

    def test_01_tools_follow_openai_function_schema(self) -> None:
        self.assertEqual(len(self.tools), 1)
        function = self.tools[0]["function"]
        self.assertEqual(function["name"], DEMO_TOOL)
        self.assertIn("示例题库", function["description"])
        parameters = function["parameters"]
        self.assertEqual(parameters["required"], ["action"])
        actions = parameters["properties"]["action"]["enum"]
        self.assertIn("import_questions", actions)
        self.assertIn("render_question", actions)
        self.assertEqual(parameters["properties"]["question_no"]["minimum"], 1)

    def test_02_explicit_intent_routes_to_plugin(self) -> None:
        for text, action, number in [
            ("拆分第一题", "import_questions", 1),
            ("帮我拆一下第 2 题", "import_questions", 2),
            ("看看第三题", "render_question", 3),
        ]:
            with self.subTest(text=text):
                intent = plugin_tools.match_intent(text, self.tools)
                self.assertIsNotNone(intent)
                self.assertEqual(intent["tool"], DEMO_TOOL)
                self.assertEqual(intent["arguments"]["action"], action)
                self.assertEqual(intent["arguments"]["question_no"], number)

    def test_03_unrelated_intent_is_not_hijacked(self) -> None:
        for text in ["导出为 PDF", "拆分一份试卷", "帮我校对解析", ""]:
            with self.subTest(text=text):
                self.assertIsNone(plugin_tools.match_intent(text, self.tools))

    def test_04_execute_import_returns_split_result(self) -> None:
        result = plugin_tools.execute_tool(
            DEMO_TOOL, {"action": "import_questions", "question_no": 1}
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["plugin"]["name"], "示例题库")
        self.assertIn("拆分第 1 题", result["summary"])
        self.assertIn("答案：B", result["summary"])
        self.assertIn("解析：", result["summary"])
        self.assertEqual(result["data"]["total"], 5)

    def test_05_execute_render_uses_question_number(self) -> None:
        result = plugin_tools.execute_tool(
            DEMO_TOOL, {"action": "render_question", "question_no": 2}
        )
        self.assertTrue(result["ok"], result)
        self.assertIn("渲染第 2 题", result["summary"])
        self.assertIn("复数", result["summary"])

    def test_06_untrusted_arguments_are_rejected_readably(self) -> None:
        cases = [
            ({"action": "delete_everything"}, "不支持动作"),
            ({"action": "import_questions", "question_no": 99}, "不存在"),
            ({"action": "render_question", "question_id": "'; DROP TABLE --"}, "question_id"),
            ("not-json", "合法 JSON"),
            ({"action": "import_questions", "question_no": "第一题"}, "失败"),
        ]
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                result = plugin_tools.execute_tool(DEMO_TOOL, arguments)
                self.assertFalse(result["ok"])
                self.assertIn(expected, result["summary"])

    def test_07_unknown_tool_is_rejected(self) -> None:
        result = plugin_tools.execute_tool("plugin_not_installed", {"action": "import_questions"})
        self.assertFalse(result["ok"])
        self.assertIn("没有找到", result["summary"])


class ChatToolCallApiTest(unittest.TestCase):
    """端到端：无密钥（Mock）+ 宿主兜底，仍必须真正调用插件并回结果。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(Path(cls.tmp.name) / "data")
        env["JZO_PLUGINS_DIR"] = str(Path(cls.tmp.name) / "plugins")
        env["JZO_LOCAL_TOKEN"] = "tool-test-token"
        env["JZO_AI_API_KEY"] = ""  # 强制 Mock，验证兜底路径
        # 底座已不再首启自动安装示例插件（v0.8.0 清理历史包袱）；本测要验的
        # 「对话→插件工具」桥接需要一个真实样本插件，这里显式把它装进临时插件目录，
        # 不再依赖任何自动安装通道。
        plugins_dir = Path(cls.tmp.name) / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ROOT / "examples" / "demo_plugin.zip") as bundle:
            bundle.extractall(plugins_dir)
        cls.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
                "--log-level",
                "warning",
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        deadline = time.time() + 20
        while time.time() < deadline:
            if cls.process.poll() is not None:
                output = cls.process.stdout.read() if cls.process.stdout else ""
                raise RuntimeError("服务提前退出：\n" + output)
            try:
                with urllib.request.urlopen(cls.base + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        else:
            raise RuntimeError("服务未在 20 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        cls.tmp.cleanup()

    def post_chat(self, text: str) -> dict:
        body = json.dumps({"user_input": text, "task_id": "t1"}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.base + "/api/agent/chat",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_01_split_first_question_executes_plugin(self) -> None:
        payload = self.post_chat("拆分第一题")
        self.assertTrue(payload["mock"])
        self.assertEqual(payload["route"], "host")
        calls = payload["data"]["plugin_calls"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["plugin"]["name"], "示例题库")
        self.assertTrue(calls[0]["ok"])
        content = payload["data"]["content"]
        self.assertIn("已调用插件「示例题库」", content)
        self.assertIn("拆分第 1 题", content)
        self.assertIn("答案：B", content)

    def test_02_non_plugin_intent_keeps_json_action_path(self) -> None:
        payload = self.post_chat("导出为 PDF")
        self.assertEqual(payload["data"]["plugin_calls"], [])
        parsed = json.loads(payload["data"]["content"])
        self.assertIn("action", parsed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
