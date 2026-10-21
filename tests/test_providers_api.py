"""Provider 注册表契约：列表不泄密钥、切换要令牌、未知档 404、活跃档落盘。

运行：``.venv/Scripts/python.exe -m unittest tests.test_providers_api``
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
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "provider-test-token"

# 固定夹具：覆盖仓库 .env 里可能存在的真密钥，测试不得触网
FIXTURE_ENV = {
    "JZO_AI_PROVIDER": "",
    "JZO_AI_API_KEY": "fixture-key-openai",
    "JZO_AI_BASE_URL": "https://gateway.test/v1",
    "JZO_AI_MODEL": "fixture-model-openai",
    "JZO_BAILIAN_API_KEY": "",
    "JZO_BAILIAN_BASE_URL": "https://bailian.test/v1",
    "JZO_BAILIAN_MODEL": "fixture-model-bailian",
    "JZO_SILICONFLOW_API_KEY": "fixture-key-silicon",
    "JZO_SILICONFLOW_BASE_URL": "https://silicon.test/v1",
    "JZO_SILICONFLOW_MODEL": "fixture-model-silicon",
}
SECRET_VALUES = sorted({v for v in FIXTURE_ENV.values() if v.startswith("fixture-key")})


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ProvidersApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name)
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = cls.data_dir.as_posix()
        env["JZO_LOCAL_TOKEN"] = TOKEN
        env.update(FIXTURE_ENV)
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
                        return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("服务未在 20 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        cls.tmp.cleanup()

    def call(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        token: str | None = TOKEN,
    ) -> tuple[int, object]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
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

    def test_01_list_exposes_no_secret(self) -> None:
        status, document = self.call("GET", "/api/providers", token=None)
        self.assertEqual(status, 200, document)
        names = [p["name"] for p in document["providers"]]
        self.assertEqual(
            set(["openai-compatible", "bailian", "siliconflow"]) - set(names), set(), names
        )
        self.assertIn(document["active"], names)
        actives = [p for p in document["providers"] if p["active"]]
        self.assertEqual(len(actives), 1, actives)

        for profile in document["providers"]:
            self.assertEqual(
                set(profile),
                {"name", "label", "model", "host", "configured", "mock", "active"},
                profile,
            )
        self.assertEqual(actives[0]["host"], "gateway.test", actives[0])
        self.assertFalse(actives[0]["mock"], actives[0])

        body = json.dumps(document, ensure_ascii=False)
        for secret in SECRET_VALUES:
            self.assertNotIn(secret, body)

    def test_02_unconfigured_profile_reports_mock(self) -> None:
        status, document = self.call("GET", "/api/providers", token=None)
        self.assertEqual(status, 200, document)
        bailian = [p for p in document["providers"] if p["name"] == "bailian"][0]
        self.assertFalse(bailian["configured"], bailian)
        self.assertTrue(bailian["mock"], bailian)

    def test_03_switch_requires_token(self) -> None:
        status, _ = self.call("POST", "/api/providers/active", {"name": "bailian"}, token=None)
        self.assertEqual(status, 401)
        status, _ = self.call(
            "POST", "/api/providers/active", {"name": "bailian"}, token="wrong-token"
        )
        self.assertEqual(status, 401)

    def test_04_switch_persists_into_workspace_config(self) -> None:
        status, document = self.call("POST", "/api/providers/active", {"name": "bailian"})
        self.assertEqual(status, 200, document)
        self.assertEqual(document["active"], "bailian")
        self.assertEqual(document["model"], "fixture-model-bailian")
        self.assertTrue(document["mock"], document)

        config = json.loads((self.data_dir / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config.get("provider"), "bailian", config)

        status, listed = self.call("GET", "/api/providers", token=None)
        self.assertEqual(status, 200, listed)
        self.assertEqual(listed["active"], "bailian", listed)

        self.call("POST", "/api/providers/active", {"name": "openai-compatible"})

    def test_05_unknown_profile_is_404(self) -> None:
        status, document = self.call("POST", "/api/providers/active", {"name": "no-such-vendor"})
        self.assertEqual(status, 404, document)
        self.assertIn("no-such-vendor", json.dumps(document, ensure_ascii=False))


class ProviderResolutionTest(unittest.TestCase):
    """活跃档优先级：环境变量 > 工作区配置 > 默认档。"""

    def setUp(self) -> None:
        from app.core import providers

        self.providers = providers
        self.tmp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tmp.name) / "config.json"
        self.patcher = mock.patch.object(self.providers, "_config_path", return_value=self.config_path)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.tmp.cleanup)

        patcher = mock.patch.dict(os.environ, FIXTURE_ENV)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_registry_collects_every_builtin_profile(self) -> None:
        names = set(self.providers.registry())
        self.assertTrue({"openai-compatible", "bailian", "siliconflow"} <= names, names)

    def test_stored_config_wins_over_fallback(self) -> None:
        self.config_path.write_text(
            json.dumps({"provider": "siliconflow"}), encoding="utf-8"
        )
        self.assertEqual(self.providers.active_name(), "siliconflow")

    def test_env_override_wins_over_stored_config(self) -> None:
        self.config_path.write_text(json.dumps({"provider": "siliconflow"}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"JZO_AI_PROVIDER": "bailian"}):
            self.assertEqual(self.providers.active_name(), "bailian")

    def test_unknown_stored_value_falls_back(self) -> None:
        self.config_path.write_text(json.dumps({"provider": "ghost"}), encoding="utf-8")
        self.assertEqual(self.providers.active_name(), "openai-compatible")

    def test_set_active_rejects_unregistered_name(self) -> None:
        with self.assertRaises(KeyError):
            self.providers.set_active_name("ghost")


if __name__ == "__main__":
    unittest.main()
