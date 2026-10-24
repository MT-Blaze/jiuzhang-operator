"""Provider 配置面板契约：保存写 .env 热生效、密钥不回显、连通性测试、令牌与守卫。

运行：``.venv/Scripts/python.exe -m unittest tests.test_provider_config``
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from app.core import ai_client

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "provider-config-test-token"
FIXTURE_KEY = "fixture-key-config-test"

FIXTURE_ENV = {
    "JZO_AI_PROVIDER": "",
    "JZO_AI_API_KEY": "",
    "JZO_AI_BASE_URL": "",
    "JZO_AI_MODEL": "",
    "JZO_BAILIAN_API_KEY": "",
    "JZO_BAILIAN_BASE_URL": "",
    "JZO_BAILIAN_MODEL": "",
    "JZO_SILICONFLOW_API_KEY": "",
    "JZO_SILICONFLOW_BASE_URL": "",
    "JZO_SILICONFLOW_MODEL": "",
    "JZO_OLLAMA_API_KEY": "",
    "JZO_OLLAMA_BASE_URL": "",
    "JZO_OLLAMA_MODEL": "",
}


class _ModelsHandler(BaseHTTPRequestHandler):
    """假网关：GET /models 返回两个模型，其余 404。"""

    def do_GET(self) -> None:  # noqa: N802 - http.server 命名约定
        if self.path.rstrip("/").endswith("/models"):
            body = json.dumps({"data": [{"id": "m1"}, {"id": "m2"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args) -> None:  # 静音
        pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ProviderConfigApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name) / "data"
        cls.env_file = Path(cls.tmp.name) / "test.env"
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = cls.data_dir.as_posix()
        env["JZO_ENV_FILE"] = cls.env_file.as_posix()
        env["JZO_LOCAL_TOKEN"] = TOKEN
        env.update(FIXTURE_ENV)
        cls.process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", str(cls.port), "--log-level", "warning",
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"

        # 假模型网关：连通性测试的成功路径打这里，不出这台机器
        cls.gateway = ThreadingHTTPServer(("127.0.0.1", 0), _ModelsHandler)
        cls.gateway_url = f"http://127.0.0.1:{cls.gateway.server_address[1]}/v1"
        threading.Thread(target=cls.gateway.serve_forever, daemon=True).start()

        deadline = time.time() + 20
        while time.time() < deadline:
            if cls.process.poll() is not None:
                output = cls.process.stdout.read() if cls.process.stdout else ""
                raise RuntimeError("服务提前退出：\n" + output)
            try:
                with urllib.request.urlopen(cls.base + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("服务未在 20 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.gateway.shutdown()
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        cls.tmp.cleanup()

    def call(
        self, method: str, path: str, body: dict | None = None, token: str | None = TOKEN
    ) -> tuple[int, object]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, self._decode(response.read())
        except urllib.error.HTTPError as error:
            try:
                return error.code, self._decode(error.read())
            finally:
                error.close()

    @staticmethod
    def _decode(raw: bytes):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode("utf-8", errors="replace")

    # --- 鉴权 ---

    def test_01_config_and_test_require_token(self) -> None:
        for path in ("/api/providers/config", "/api/providers/test"):
            status, _ = self.call("POST", path, {"name": "ollama"}, token=None)
            self.assertEqual(status, 401, path)
            status, _ = self.call("POST", path, {"name": "ollama"}, token="wrong")
            self.assertEqual(status, 401, path)

    # --- 保存配置 ---

    def test_02_save_config_hot_applies_and_never_echoes_key(self) -> None:
        status, body = self.call(
            "POST",
            "/api/providers/config",
            {
                "name": "ollama",
                "base_url": self.gateway_url,
                "api_key": FIXTURE_KEY,
                "model": "llama3",
            },
        )
        self.assertEqual(status, 200, body)
        self.assertTrue(body["configured"], body)
        self.assertEqual(body["model"], "llama3", body)
        self.assertEqual(body["host"], f"127.0.0.1:{self.gateway.server_address[1]}", body)
        self.assertNotIn(FIXTURE_KEY, json.dumps(body, ensure_ascii=False))

        # 列表接口同样只给「已配置 + 主机名」，密钥不出现在任何响应里
        status, listed = self.call("GET", "/api/providers", token=None)
        self.assertEqual(status, 200)
        ollama = [p for p in listed["providers"] if p["name"] == "ollama"][0]
        self.assertTrue(ollama["configured"], ollama)
        self.assertFalse(ollama["mock"], ollama)
        self.assertNotIn(FIXTURE_KEY, json.dumps(listed, ensure_ascii=False))

        # 密钥落在本机 .env（测试夹具文件），未入库
        env_text = self.env_file.read_text(encoding="utf-8")
        self.assertIn(f"JZO_OLLAMA_API_KEY={FIXTURE_KEY}", env_text)
        self.assertIn(f"JZO_OLLAMA_BASE_URL={self.gateway_url}", env_text)
        self.assertIn("JZO_OLLAMA_MODEL=llama3", env_text)

    def test_03_save_config_validates_inputs(self) -> None:
        status, _ = self.call("POST", "/api/providers/config", {"name": "ollama"})
        self.assertEqual(status, 400)  # 三项全缺
        status, body = self.call(
            "POST", "/api/providers/config", {"name": "ollama", "base_url": "file:///etc"}
        )
        self.assertEqual(status, 400, body)
        status, body = self.call(
            "POST", "/api/providers/config",
            {"name": "ollama", "base_url": "https://user:pass@example.com/v1"},
        )
        self.assertEqual(status, 400, body)  # 携带凭证
        status, body = self.call(
            "POST", "/api/providers/config", {"name": "no-such", "api_key": "x"}
        )
        self.assertEqual(status, 404, body)

    def test_04_partial_save_keeps_previous_fields(self) -> None:
        status, body = self.call(
            "POST", "/api/providers/config", {"name": "ollama", "model": "qwen2.5"}
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(body["model"], "qwen2.5", body)
        self.assertTrue(body["configured"], body)  # key 与 base_url 仍在

    # --- 连通性测试 ---

    def test_05_connectivity_ok_against_local_gateway(self) -> None:
        status, body = self.call("POST", "/api/providers/test", {"name": "ollama"})
        self.assertEqual(status, 200, body)
        self.assertTrue(body["ok"], body)
        self.assertEqual(body["status_code"], 200, body)
        self.assertIn("2", body["detail"], body)
        self.assertNotIn(FIXTURE_KEY, json.dumps(body, ensure_ascii=False))

    def test_06_connectivity_reports_unreachable_as_structured_result(self) -> None:
        dead_port = _free_port()
        status, _ = self.call(
            "POST", "/api/providers/config",
            {"name": "openai-compatible", "base_url": f"http://127.0.0.1:{dead_port}/v1",
             "api_key": "fixture-key-dead"},
        )
        self.assertEqual(status, 200)
        status, body = self.call("POST", "/api/providers/test", {"name": "openai-compatible"})
        self.assertEqual(status, 200, body)
        self.assertFalse(body["ok"], body)
        self.assertIn("连不上", body["detail"], body)

    def test_07_connectivity_of_unconfigured_profile_is_readable(self) -> None:
        status, body = self.call("POST", "/api/providers/test", {"name": "siliconflow"})
        self.assertEqual(status, 200, body)
        self.assertFalse(body["ok"], body)
        self.assertIn("尚未填齐", body["detail"], body)


class _ChatHandler(BaseHTTPRequestHandler):
    """假 chat/completions 网关：按 ``_reply`` 出包，``_delay`` 用来测事件循环会不会被按住。"""

    _reply: dict = {}
    _delay: float = 0.0
    _status: int = 200

    def do_POST(self) -> None:  # noqa: N802 - http.server 命名约定
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self._delay:
            time.sleep(self._delay)
        body = b'{"error": "boom"}' if self._status != 200 else json.dumps(self._reply).encode("utf-8")
        self.send_response(self._status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # 静音
        pass


class ChatCompletionClientTest(unittest.TestCase):
    """``ai_client.chat_completion`` 打的是本机假网关：不出这台机器，也不碰真密钥。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.gateway = ThreadingHTTPServer(("127.0.0.1", 0), _ChatHandler)
        threading.Thread(target=cls.gateway.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.gateway.server_address[1]}/v1"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.gateway.shutdown()

    def _client(self) -> "ai_client.OpenAICompatibleProvider":
        return ai_client.OpenAICompatibleProvider(
            api_key="fixture-key-chat", base_url=self.base, default_model="fixture-model"
        )

    def test_01_empty_choices_return_empty_content_instead_of_crashing(self) -> None:
        """内容被服务端拦下时 OpenAI 兼容口回 ``"choices": []``，裸下标会抛 IndexError。"""
        _ChatHandler._reply = {"choices": [], "model": "fixture-model"}
        result = asyncio.run(
            self._client().chat_completion("系统", "用户")
        )
        self.assertEqual(result["content"], "")
        self.assertEqual(result["tool_calls"], [])
        self.assertFalse(result["mock"])

    def test_02_http_error_is_a_readable_runtime_error(self) -> None:
        _ChatHandler._status = 503
        try:
            with self.assertRaises(RuntimeError) as raised:
                asyncio.run(self._client().chat_completion("系统", "用户"))
        finally:
            _ChatHandler._status = 200
        self.assertIn("AI API error 503", str(raised.exception))

    def test_03_slow_model_does_not_block_the_event_loop(self) -> None:
        """urllib 是阻塞 IO：网关睡 0.4 秒期间，事件循环照常跑别的协程。

        以前直接在 ``async def`` 里调 urlopen，一次 AI 调用能把整个底座（含正在录题的
        插件页面）按住到模型返回为止；这条判据就是钉住「必须放线程池」。
        """
        _ChatHandler._reply = {"choices": [{"message": {"content": "好"}}], "model": "fixture-model"}
        _ChatHandler._delay = 0.4
        ticks = {"n": 0}

        async def _tick() -> None:
            while True:
                await asyncio.sleep(0.01)
                ticks["n"] += 1

        async def _both() -> int:
            request = asyncio.ensure_future(self._client().chat_completion("系统", "用户"))
            ticker = asyncio.ensure_future(_tick())
            result = await request
            during = ticks["n"]          # 只看「等模型的那段时间」跑了几拍
            ticker.cancel()
            try:
                await ticker
            except asyncio.CancelledError:
                pass
            assert result["content"] == "好"
            return during

        try:
            during = asyncio.run(_both())
        finally:
            _ChatHandler._delay = 0.0
        # 睡 0.4 秒 ≈ 40 拍；事件循环若被 urlopen 按住，这里会是 0
        self.assertGreaterEqual(during, 15, f"等模型期间只跑了 {during} 拍，事件循环被按住了")

    def test_04_bad_timeout_env_falls_back_instead_of_killing_startup(self) -> None:
        """``JZO_AI_TIMEOUT_SECONDS`` 是用户写进 .env 的，写坏了不能让应用在导入期就起不来。"""
        for raw, expected in (("abc", 30), ("0", 30), ("-5", 30), ("45", 45), ("99999", 30)):
            with mock.patch.dict(os.environ, {"JZO_AI_TIMEOUT_SECONDS": raw}):
                self.assertEqual(ai_client._timeout_from_env(), expected, raw)


if __name__ == "__main__":
    unittest.main()
