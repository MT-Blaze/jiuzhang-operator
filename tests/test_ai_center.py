"""AI 配置中心契约：账号池热生效、掩码、四任务指派、模型拉取与令牌守卫。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ai_center``
"""

from __future__ import annotations

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

from app.core import ai_center

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "ai-center-test-token"
FIXTURE_KEY = "fixture-key-ai-center-1234567890"


class _ModelsHandler(BaseHTTPRequestHandler):
    """假网关：GET /models 返回两个模型，并记录 Authorization。"""

    seen_auth: list[str] = []

    def do_GET(self) -> None:  # noqa: N802 - http.server 命名约定
        _ModelsHandler.seen_auth.append(self.headers.get("Authorization") or "")
        if self.path.rstrip("/").endswith("/models"):
            body = json.dumps({"data": [{"id": "m1"}, {"id": "m2"}, "m3"]}).encode("utf-8")
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


class AiCenterCoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.config_file = root / "config.json"
        self.env_file = root / "test.env"
        self.patches = [
            mock.patch.object(ai_center, "_config_path", side_effect=lambda: self.config_file),
            mock.patch.object(ai_center, "env_file_path", side_effect=lambda: self.env_file),
        ]
        for patch in self.patches:
            patch.start()
        self.accounts: list[str] = []

    def tearDown(self) -> None:
        for account_id in self.accounts:
            base_name, key_name = ai_center._env_names(account_id)
            os.environ.pop(base_name, None)
            os.environ.pop(key_name, None)
        for patch in reversed(self.patches):
            patch.stop()
        self.tmp.cleanup()

    def _save(self, name: str, **kwargs) -> dict:
        account = ai_center.save_account(name=name, **kwargs)
        self.accounts.append(account["id"])
        return account

    def test_01_save_masks_key_and_writes_env_only(self) -> None:
        account = self._save(
            "阿里", base_url="https://dashscope.test/v1", api_key=FIXTURE_KEY
        )
        self.assertTrue(account["configured"])
        self.assertEqual(account["api_key_masked"], "fixt••••90")
        cluster = ai_center.cluster()
        self.assertNotIn(FIXTURE_KEY, json.dumps(cluster, ensure_ascii=False))
        env_text = self.env_file.read_text(encoding="utf-8")
        self.assertIn(FIXTURE_KEY, env_text, "密钥必须落本机 .env")
        config_text = self.config_file.read_text(encoding="utf-8")
        self.assertNotIn(FIXTURE_KEY, config_text, "config.json 只存非密钥字段")
        self.assertIn("阿里", config_text)

    def test_02_rename_keeps_key_and_duplicate_name_rejected(self) -> None:
        first = self._save("DeepSeek", base_url="https://a.test/v1", api_key=FIXTURE_KEY)
        second = self._save("MinerU", base_url="https://b.test/v1", api_key="other-key-000000")
        renamed = ai_center.save_account(
            account_id=first["id"], name="DeepSeek 主号", base_url="https://a.test/v1"
        )
        self.assertEqual(renamed["name"], "DeepSeek 主号")
        self.assertTrue(renamed["configured"], "不传 api_key 时必须保留旧 Key")
        with self.assertRaises(ai_center.AiCenterError):
            ai_center.save_account(
                account_id=second["id"], name="deepseek 主号", base_url="https://b.test/v1"
            )

    def test_03_assign_and_resolve(self) -> None:
        account = self._save("阿里", base_url="https://dashscope.test/v1", api_key=FIXTURE_KEY)
        cluster = ai_center.assign_task("ocr", account["id"], "qwen-vl-max")
        self.assertTrue(cluster["assignments"]["ocr"]["ready"])
        self.assertEqual(cluster["assignments"]["ocr"]["model"], "qwen-vl-max")
        binding = ai_center.resolve_task("ocr")
        self.assertTrue(binding.is_configured)
        self.assertEqual(binding.model, "qwen-vl-max")
        self.assertEqual(binding.api_key, FIXTURE_KEY)
        with self.assertRaises(ai_center.AiCenterError):
            ai_center.assign_task("ocr", account["id"], "")
        with self.assertRaises(ai_center.AiCenterError):
            ai_center.assign_task("unknown", account["id"], "m")
        empty = ai_center.resolve_task("tikz")
        self.assertFalse(empty.is_configured)

    def test_04_delete_clears_assignments_and_env(self) -> None:
        account = self._save("阿里", base_url="https://dashscope.test/v1", api_key=FIXTURE_KEY)
        ai_center.assign_task("meta", account["id"], "qwen-plus")
        cluster = ai_center.delete_account(account["id"])
        self.assertEqual(cluster["accounts"], [])
        self.assertEqual(cluster["assignments"]["meta"]["account_id"], "")
        base_name, key_name = ai_center._env_names(account["id"])
        self.assertNotIn(key_name, os.environ)
        self.assertNotIn(key_name, self.env_file.read_text(encoding="utf-8"))

    def test_05_clearing_key_marks_unconfigured(self) -> None:
        account = self._save("阿里", base_url="https://dashscope.test/v1", api_key=FIXTURE_KEY)
        cleared = ai_center.save_account(
            account_id=account["id"], name="阿里", base_url="https://dashscope.test/v1",
            api_key="",
        )
        self.assertFalse(cleared["configured"])
        self.assertEqual(cleared["api_key_masked"], "")

    def test_06_find_mineru_requires_a_key(self) -> None:
        account = self._save("MinerU", base_url="https://mineru.test/v1", api_key=FIXTURE_KEY)
        binding = ai_center.find_mineru()
        self.assertIsNotNone(binding)
        self.assertEqual(binding.account_id, account["id"])
        ai_center.save_account(
            account_id=account["id"], name="MinerU", base_url="https://mineru.test/v1",
            api_key="",
        )
        self.assertIsNone(ai_center.find_mineru())

    def test_07_fetch_models_by_id_and_temp_key(self) -> None:
        gateway = ThreadingHTTPServer(("127.0.0.1", 0), _ModelsHandler)
        threading.Thread(target=gateway.serve_forever, daemon=True).start()
        try:
            base_url = f"http://127.0.0.1:{gateway.server_address[1]}/v1"
            account = self._save("阿里", base_url=base_url, api_key=FIXTURE_KEY)
            result = ai_center.fetch_models(account_id=account["id"])
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["models"], ["m1", "m2", "m3"])
            self.assertNotIn(FIXTURE_KEY, json.dumps(result, ensure_ascii=False))
            temp = ai_center.fetch_models(base_url=base_url, api_key="temp-key-abcdef")
            self.assertTrue(temp["ok"], temp)
            self.assertTrue(
                any("temp-key-abcdef" in value for value in _ModelsHandler.seen_auth)
            )
            with self.assertRaises(ai_center.AiCenterError):
                ai_center.fetch_models(base_url=base_url, api_key="")
        finally:
            gateway.shutdown()
        with self.assertRaises(ai_center.AiCenterError):
            ai_center.fetch_models(account_id="acc_0000000000")


class AiCenterApiTest(unittest.TestCase):
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

    def call(self, method: str, path: str, body: dict | None = None,
             token: str | None = TOKEN) -> tuple[int, object]:
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

    def test_01_writes_require_token(self) -> None:
        for method, path, body in (
            ("POST", "/api/ai-center/accounts", {"name": "x", "base_url": "https://x.test/v1"}),
            ("POST", "/api/ai-center/assign", {"task": "ocr", "account_id": "acc_0000000000", "model": "m"}),
            ("POST", "/api/ai-center/models", {"account_id": "acc_0000000000"}),
            ("DELETE", "/api/ai-center/accounts/acc_0000000000", None),
        ):
            status, _ = self.call(method, path, body, token=None)
            self.assertEqual(status, 401, path)

    def test_02_full_flow_masks_key(self) -> None:
        status, account = self.call(
            "POST", "/api/ai-center/accounts",
            {"name": "阿里", "base_url": self.gateway_url, "api_key": FIXTURE_KEY},
        )
        self.assertEqual(status, 200, account)
        self.assertTrue(account["configured"])
        self.assertNotIn(FIXTURE_KEY, json.dumps(account, ensure_ascii=False))
        status, cluster = self.call("GET", "/api/ai-center", token=None)
        self.assertEqual(status, 200, cluster)
        self.assertEqual(len(cluster["accounts"]), 1)
        self.assertEqual(
            [task["key"] for task in cluster["tasks"]],
            ["ocr", "solve", "meta", "tikz", "mineru"],
        )
        self.assertNotIn(FIXTURE_KEY, json.dumps(cluster, ensure_ascii=False))

        status, models = self.call(
            "POST", "/api/ai-center/models", {"account_id": account["id"]}
        )
        self.assertEqual(status, 200, models)
        self.assertTrue(models["ok"], models)
        self.assertEqual(models["models"], ["m1", "m2", "m3"])

        status, cluster = self.call(
            "POST", "/api/ai-center/assign",
            {"task": "ocr", "account_id": account["id"], "model": "m1"},
        )
        self.assertEqual(status, 200, cluster)
        self.assertTrue(cluster["assignments"]["ocr"]["ready"])
        self.assertEqual(cluster["assignments"]["ocr"]["account_name"], "阿里")

        env_text = self.env_file.read_text(encoding="utf-8")
        self.assertIn(FIXTURE_KEY, env_text)

        status, cluster = self.call(
            "DELETE", "/api/ai-center/accounts/" + account["id"]
        )
        self.assertEqual(status, 200, cluster)
        self.assertEqual(cluster["accounts"], [])
        self.assertEqual(cluster["assignments"]["ocr"]["account_id"], "")

    def test_03_bad_input_is_400(self) -> None:
        status, body = self.call(
            "POST", "/api/ai-center/accounts",
            {"name": "坏地址", "base_url": "file:///etc/passwd"},
        )
        self.assertEqual(status, 400, body)
        status, body = self.call(
            "POST", "/api/ai-center/accounts",
            {"name": "缺 Key 也能存", "base_url": "https://example.test/v1"},
        )
        self.assertEqual(status, 200, body)
        account_id = body["id"]
        status, body = self.call(
            "POST", "/api/ai-center/models", {"account_id": account_id}
        )
        self.assertEqual(status, 400, body)
        self.call("DELETE", "/api/ai-center/accounts/" + account_id)


if __name__ == "__main__":
    unittest.main()
