"""v0.5.5 双向操控契约：富卡片、右侧面板、UI 动作与插件搜索。

三件事分开钉：
1. 后端：插件面板归一化/默认面板、随机抽题参数、ui_json 卡片帧、右栏面板提示词。
2. 搜索：只读用户拉取过的索引缓存，只出安装建议卡，绝不自动安装或联网。
3. 前端：结构不变量（ui_json 拦截、update_params/trigger_button、本地 KaTeX）。
   真机行为由 ``.system_generated`` 下的 Playwright 探针产出，本文件不启浏览器。

运行：``.venv/Scripts/python.exe -m unittest tests.test_rich_card_ui``
"""

from __future__ import annotations

import json
import os
import re
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

from app.api.agents import (  # noqa: E402
    build_chat_system_prompt,
    strip_code_fences,
)
from app.core import plugin_search, plugin_tools, ui_cards  # noqa: E402
from app.core import plugins as plugin_registry  # noqa: E402
from app.core.config import settings  # noqa: E402

STATIC = ROOT / "static"
HTML = (STATIC / "workspace.html").read_text(encoding="utf-8")
JS = (STATIC / "js" / "workspace.js").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "workspace.css").read_text(encoding="utf-8")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _index_entry(plugin_id: str, name: str, kind: str, description: str) -> dict:
    return {
        "id": plugin_id,
        "name": name,
        "version": "1.2.0",
        "zip_url": "https://example.org/%s.zip" % plugin_id,
        "mirrors": [],
        "description": description,
        "homepage": "",
        "kind": kind,
        "api_version": "1.0",
    }


class PluginPanelContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.plugins_dir = Path(cls.tmp.name) / "plugins"
        cls.plugins_dir.mkdir()
        with zipfile.ZipFile(ROOT / "examples" / "demo_plugin.zip") as zf:
            zf.extractall(cls.plugins_dir)
        cls.patcher = mock.patch.object(settings, "plugins_dir", cls.plugins_dir)
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.patcher.stop()
        cls.tmp.cleanup()

    def test_01_importer_gets_executable_default_panel(self) -> None:
        demo = [
            item
            for item in plugin_registry.discover_plugins()["plugins"]
            if item["id"] == "org.jiuzhang.demo-bank"
        ][0]
        ui = demo["ui"]
        self.assertEqual(ui["plugin_id"], "org.jiuzhang.demo-bank")
        selects = {item["key"]: item for item in ui["controls"] if item["type"] == "select"}
        self.assertEqual(set(selects), {"grade", "difficulty"})
        self.assertIn("高一", [item["value"] for item in selects["grade"]["options"]])
        self.assertIn("基础", [item["value"] for item in selects["difficulty"]["options"]])
        buttons = {item["id"]: item for item in ui["controls"] if item["type"] == "button"}
        self.assertIn("random_question", buttons)
        self.assertIn("{grade}", buttons["random_question"]["command"])
        self.assertIn("{difficulty}", buttons["random_question"]["command"])

    def test_02_bad_controls_are_dropped_not_fatal(self) -> None:
        ui = plugin_registry._normalize_ui(
            {
                "title": "我的面板",
                "controls": [
                    {"type": "select", "key": "Bad Key", "options": [{"value": "x"}]},
                    {"type": "select", "key": "grade", "label": "年级", "options": [{"value": "高一"}]},
                    {"type": "button", "label": "运行", "command": "跑一下", "id": "run"},
                    {"type": "button", "label": "", "command": "空标签"},
                    "not-a-control",
                ],
            },
            "org.example.demo",
            "示例",
        )
        self.assertIsNotNone(ui)
        self.assertEqual(ui["title"], "我的面板")
        self.assertEqual([item["id"] for item in ui["controls"]], ["grade", "run"])

    def test_03_duplicate_button_ids_are_deduped(self) -> None:
        ui = plugin_registry._normalize_ui(
            {
                "controls": [
                    {"type": "button", "label": "甲", "command": "a", "id": "go"},
                    {"type": "button", "label": "乙", "command": "b", "id": "go"},
                ]
            },
            "org.example.demo",
            "示例",
        )
        self.assertEqual([item["id"] for item in ui["controls"]], ["go", "go_2"])

    def test_04_random_grade_and_difficulty_are_routed(self) -> None:
        tools = plugin_tools.build_tools()
        intent = plugin_tools.match_intent("随机出一道高一基础题", tools)
        self.assertIsNotNone(intent)
        self.assertEqual(intent["arguments"]["action"], "import_questions")
        self.assertTrue(intent["arguments"]["random"])
        self.assertEqual(intent["arguments"]["difficulty"], "basic")
        self.assertEqual(intent["arguments"]["grade"], "高一")

    def test_05_random_tool_returns_question_payload(self) -> None:
        result = plugin_tools.execute_tool(
            "plugin_org_jiuzhang_demo-bank",
            {"action": "import_questions", "random": True, "difficulty": "basic"},
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["data"]["random"])
        self.assertEqual(len(result["data"]["questions"]), 1)
        self.assertTrue(result["data"]["questions"][0]["stem"])

    def test_06_grade_without_metadata_is_honest(self) -> None:
        result = plugin_tools.execute_tool(
            "plugin_org_jiuzhang_demo-bank",
            {"action": "import_questions", "random": True, "grade": "高三"},
        )
        self.assertTrue(result["ok"], result)
        self.assertIn("未按年级过滤", result["summary"])


class UiCardFrameTest(unittest.TestCase):
    def test_01_question_block_is_sanitized_and_framed(self) -> None:
        block = ui_cards.question_block(
            [
                {
                    "id": "q_demo_1",
                    "question_no": 1,
                    "type": "single_choice",
                    "difficulty": "basic",
                    "stem": "已知 $x^2=1$，则 $x$ 等于（  ）",
                    "options": [{"key": "A", "content": "$1$"}, {"key": "B", "content": "$\\pm 1$"}],
                    "answer": "B",
                    "solution": "由 $x^2=1$ 得 $x=\\pm 1$。",
                    "tags": ["集合"],
                    "extra_field": "<script>alert(1)</script>",
                }
            ]
        )
        self.assertIsNotNone(block)
        self.assertEqual(block["type"], "question_card")
        self.assertNotIn("extra_field", block["questions"][0])
        frame = ui_cards.frame(block)
        self.assertTrue(frame.startswith("```ui_json\n"))
        self.assertTrue(frame.endswith("\n```"))
        self.assertEqual(json.loads(frame.split("\n")[1])["type"], "question_card")

    def test_02_blank_question_is_not_framed(self) -> None:
        self.assertIsNone(ui_cards.question_block([{"stem": "   "}]))
        self.assertEqual(ui_cards.frame({"type": "question_card"}), "")
        self.assertEqual(ui_cards.frame({"type": "evil_card"}), "")

    def test_03_install_block_carries_url_but_no_download(self) -> None:
        entry = _index_entry("org.example.export", "PDF 导出", "exporter", "把题目导出为 PDF")
        block = ui_cards.install_block(entry, "与你说的导出 PDF 匹配")
        self.assertEqual(block["type"], "install_card")
        self.assertEqual(block["plugin"]["zip_url"], entry["zip_url"])
        self.assertIn("匹配", block["reason"])


class PluginSearchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"JZO_DATA_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def _save_entries(self) -> None:
        plugin_search.save_index_cache(
            {
                "source_host": "https://example.org",
                "source_url": "https://example.org/plugins.json",
                "entries": [
                    _index_entry("org.example.export", "PDF 导出", "exporter", "把题目与试卷导出为 PDF 或 Word"),
                    _index_entry("org.example.render", "题卡渲染", "renderer", "在页面里渲染题卡与解析"),
                ],
            }
        )

    def test_01_no_cache_never_pretends_to_search(self) -> None:
        result = plugin_search.execute_tool(plugin_search.TOOL_SEARCH, {"query": "导出 PDF"})
        self.assertFalse(result["ok"])
        self.assertIn("拉取清单", result["summary"])
        self.assertFalse(result.get("ui_cards"))

    def test_02_search_returns_install_card_but_does_not_install(self) -> None:
        self._save_entries()
        result = plugin_search.execute_tool(
            plugin_search.TOOL_SEARCH, {"query": "我想找个能导出 PDF 的插件"}
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["host_tool"])
        self.assertEqual(result["ui_cards"][0]["type"], "install_card")
        self.assertEqual(result["ui_cards"][0]["plugin"]["id"], "org.example.export")
        self.assertIn("确认安装", result["summary"])
        self.assertNotIn("已安装成功", result["summary"])

    def test_03_suggest_by_id_uses_index_entry(self) -> None:
        self._save_entries()
        result = plugin_search.execute_tool(
            plugin_search.TOOL_SUGGEST,
            {"plugin_id": "org.example.render", "reason": "你要在对话里看题卡"},
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["ui_cards"][0]["plugin"]["id"], "org.example.render")

    def test_04_suggest_unknown_id_is_readable(self) -> None:
        self._save_entries()
        result = plugin_search.execute_tool(
            plugin_search.TOOL_SUGGEST, {"plugin_id": "org.example.missing"}
        )
        self.assertFalse(result["ok"])
        self.assertIn("没有", result["summary"])

    def test_05_search_module_has_no_network_code(self) -> None:
        source = (ROOT / "app" / "core" / "plugin_search.py").read_text(encoding="utf-8")
        for token in ("urllib.request", "urlopen", "requests.", "httpx."):
            self.assertNotIn(token, source, "插件搜索不得联网：" + token)

    def test_06_intent_routes_plugin_hunt_but_not_zip_install(self) -> None:
        self.assertIsNotNone(plugin_search.match_intent("我想找个能导出 PDF 的插件"))
        self.assertIsNone(plugin_search.match_intent("安装这个 zip 插件"))
        self.assertIsNone(plugin_search.match_intent("导出为 PDF"))


class PromptPanelTest(unittest.TestCase):
    def test_01_panel_catalog_lists_keys_and_buttons(self) -> None:
        context = {
            "current_task": "示例题库",
            "plugin": {"id": "org.jiuzhang.demo-bank", "name": "示例题库"},
            "ui": {
                "plugin_id": "org.jiuzhang.demo-bank",
                "values": {"grade": "高一", "difficulty": "基础"},
                "controls": [
                    {
                        "id": "grade",
                        "type": "select",
                        "key": "grade",
                        "label": "年级",
                        "options": [{"value": "全部"}, {"value": "高一"}],
                        "default": "全部",
                    },
                    {
                        "id": "random_question",
                        "type": "button",
                        "label": "随机出题",
                    },
                ],
            },
        }
        prompt = build_chat_system_prompt(context)
        self.assertIn("## 右侧插件面板", prompt)
        self.assertIn("grade（年级）", prompt)
        self.assertIn("当前 高一", prompt)
        self.assertIn("random_question（随机出题）", prompt)
        self.assertIn("update_params", prompt)
        self.assertIn("trigger_button", prompt)

    def test_02_no_ui_means_no_panel_section(self) -> None:
        prompt = build_chat_system_prompt({"current_task": "自由对话"})
        self.assertNotIn("## 右侧插件面板", prompt)

    def test_03_ui_json_fence_is_not_stripped_as_action_json(self) -> None:
        raw = '```ui_json\n{"version":"1.0","type":"confirm_card","actions":[]}\n```'
        self.assertEqual(strip_code_fences(raw), raw)


class FrontendStructureTest(unittest.TestCase):
    def test_01_panel_and_katex_are_local(self) -> None:
        self.assertIn('id="wsPluginPanel"', HTML)
        self.assertIn('id="wsPluginControls"', HTML)
        self.assertIn("/static/vendor/katex/katex.min.css", HTML)
        self.assertIn("/static/vendor/katex/katex.min.js", HTML)
        self.assertNotIn("cdn.jsdelivr.net", HTML)
        self.assertNotIn("unpkg.com", HTML)

        vendor_css = (STATIC / "vendor" / "katex" / "katex.min.css").read_text(encoding="utf-8")
        self.assertNotIn("http://", vendor_css)
        self.assertNotIn("https://", vendor_css)
        self.assertTrue((STATIC / "vendor" / "katex" / "LICENSE").is_file())
        self.assertTrue((STATIC / "vendor" / "katex" / "katex.min.js").is_file())

    def test_02_ui_json_cards_are_intercepted_before_text(self) -> None:
        self.assertIn("function splitUiBlocks", JS)
        self.assertIn("ui_json", JS)
        self.assertIn("question_card", JS)
        self.assertIn("install_card", JS)
        self.assertIn("查看解析", JS)
        self.assertIn("katex.renderToString", JS)
        # 模型/插件返回的卡片数据只以 textContent 落 DOM，公式交给 KaTeX
        self.assertNotIn("bubble.innerHTML", JS)

    def test_03_ui_actions_and_human_override_are_wired(self) -> None:
        self.assertIn("update_params", JS)
        self.assertIn("trigger_button", JS)
        self.assertIn("applyUiParams", JS)
        self.assertIn("snapshotRevisions", JS)
        self.assertIn("你刚手动改过", JS)
        self.assertIn("origin: \"ai_button\"", JS)
        self.assertIn("origin === \"ui_button\"", JS)

    def test_04_panel_sends_commands_and_context_carries_values(self) -> None:
        self.assertIn("function renderPluginPanel", JS)
        self.assertIn("expandCommand", JS)
        self.assertIn("origin: \"ui_button\"", JS)
        self.assertIn("context.ui =", JS)
        self.assertIn("controls: compactControls()", JS)
        self.assertIn("data-ui-key", JS)
        self.assertIn("data-ui-button", JS)

    def test_05_install_card_only_calls_install_on_click(self) -> None:
        self.assertIn("installSuggestedPlugin", JS)
        self.assertIn('fetch("/api/plugins/install-url"', JS)
        # 卡片渲染阶段不得直接发起安装请求
        card_start = JS.index("function buildInstallCard")
        card_end = JS.index("function installSuggestedPlugin")
        card_block = JS[card_start:card_end]
        self.assertNotIn("/api/plugins/install-url", card_block)
        self.assertIn("确认安装", card_block)

    def test_06_cards_and_controls_are_44px_and_overflow_safe(self) -> None:
        self.assertIn(".ws-card", CSS)
        self.assertIn(".ws-tag-type", CSS)
        self.assertIn(".ws-ui-select", CSS)
        self.assertIn(".ws-math-block", CSS)
        media = CSS[CSS.index("@media (max-width: 768px)") :]
        self.assertRegex(media, r"\.ws-ui-select\s*\{[^}]*min-height:\s*44px")
        self.assertIn("@media (prefers-reduced-motion: reduce)", CSS)

    def test_07_no_remote_asset_requests_in_workspace_script(self) -> None:
        # Provider 弹窗里的 https://api.example.com/v1 只是占位提示，不是资源请求；
        # 这里钉的是脚本不得引入任何远程静态资源或 CDN。
        for token in ("cdn.", "fonts.googleapis", "unpkg.com", "jsdelivr"):
            self.assertNotIn(token, JS, "工作台脚本出现远程资源：" + token)
        self.assertNotIn('fetch("http', JS)


class ChatUiEndToEndTest(unittest.TestCase):
    """真实 HTTP + Mock 模型：插件卡与安装建议卡都必须从后端一路到 content。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        plugins_dir = root / "plugins"
        plugins_dir.mkdir()
        with zipfile.ZipFile(ROOT / "examples" / "demo_plugin.zip") as zf:
            zf.extractall(plugins_dir)
        data_dir = root / "data"
        data_dir.mkdir()
        (data_dir / plugin_search.CACHE_FILENAME).write_text(
            json.dumps(
                {
                    "source_host": "https://example.org",
                    "source_url": "https://example.org/plugins.json",
                    "entries": [
                        _index_entry(
                            "org.example.export",
                            "PDF 导出",
                            "exporter",
                            "把题目与试卷导出为 PDF 或 Word",
                        )
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(data_dir)
        env["JZO_PLUGINS_DIR"] = str(plugins_dir)
        env["JZO_AI_API_KEY"] = ""
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
        cls.base = "http://127.0.0.1:%d" % cls.port
        deadline = time.time() + 20
        while time.time() < deadline:
            if cls.process.poll() is not None:
                raise RuntimeError("服务提前退出")
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

    def test_01_split_first_question_returns_question_card(self) -> None:
        payload = self.post_chat("拆分第一题")
        content = payload["data"]["content"]
        self.assertIn("```ui_json", content)
        block = json.loads(re.search(r"```ui_json\s*(\{.*?\})\s*```", content, re.S).group(1))
        self.assertEqual(block["type"], "question_card")
        self.assertTrue(block["questions"][0]["stem"])

    def test_02_plugin_search_returns_install_card(self) -> None:
        payload = self.post_chat("我想找个能导出 PDF 的插件")
        self.assertEqual(payload["route"], "host")
        calls = payload["data"]["plugin_calls"]
        self.assertEqual(calls[0]["plugin"]["name"], "插件索引")
        self.assertTrue(calls[0]["host_tool"])
        block = json.loads(
            re.search(r"```ui_json\s*(\{.*?\})\s*```", payload["data"]["content"], re.S).group(1)
        )
        self.assertEqual(block["type"], "install_card")
        self.assertEqual(block["plugin"]["id"], "org.example.export")


if __name__ == "__main__":
    unittest.main(verbosity=2)
