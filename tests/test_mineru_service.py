"""MinerU 本地服务编排（任务卡 §2/§5）：fake subprocess，绝不起真服务。

覆盖：未安装诚实失败／懒起服（动态端口＋随机令牌）／健康复用／并发锁／
提前退出与超时显性失败／stop 杀树＋端口复验。
运行：``.venv/Scripts/python.exe -m unittest tests.test_mineru_service``
"""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from app.core.ingest.recognize import mineru_service as service


class FakeProc:
    def __init__(self, pid: int = 4321, exit_code: int | None = None) -> None:
        self.pid = pid
        self._exit = exit_code

    def poll(self) -> int | None:
        return self._exit

    def wait(self, timeout: float | None = None) -> int:
        return self._exit or 0

    def terminate(self) -> None:
        pass

    def kill(self) -> None:
        pass


class ServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        for name in ("_PROC", "_PORT", "_TOKEN", "_LOG_HANDLE"):
            self.addCleanup(setattr, service, name, getattr(service, name))
        self.addCleanup(self._close_log)
        service._PROC = None
        service._PORT = 0
        service._TOKEN = ""
        service._LOG_HANDLE = None
        patcher = mock.patch.object(service.mineru_setup, "engine_dir",
                                    return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(service, "_free_port", return_value=43210)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(service, "_port_open", return_value=False)
        self.port_open = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(service.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(service.subprocess, "run")
        self.kill_run = patcher.start()
        self.addCleanup(patcher.stop)

    def _close_log(self) -> None:
        if service._LOG_HANDLE is not None:
            service._LOG_HANDLE.close()
            service._LOG_HANDLE = None

    def _materialize_api(self) -> None:
        exe = self.root / "Scripts" / "mineru-api.exe"
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b"stub")

    def _popen(self, proc: FakeProc | None = None):
        return mock.patch.object(service.subprocess, "Popen",
                                 return_value=proc or FakeProc())

    def test_not_installed_is_honest_failure_never_auto_install(self) -> None:
        missing = {"ok": False, "state": "missing", "version": "",
                   "message": "本地 MinerU 未安装。"}
        with mock.patch.object(service.mineru_setup, "health", return_value=missing), \
                self._popen() as popen:
            result = service.ensure_ready()
        self.assertFalse(result["ok"])
        self.assertIn("安装本地 MinerU", result["detail"])
        popen.assert_not_called()

    def test_missing_api_entry_is_honest_failure(self) -> None:
        with self._popen() as popen:
            result = service.start()
        self.assertFalse(result["ok"])
        self.assertIn("服务入口不在", result["detail"])
        popen.assert_not_called()

    def test_start_uses_dynamic_port_and_random_token(self) -> None:
        self._materialize_api()
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True):
            first = service.start()
            token_one = first["token"]
            service._PROC = None
            service._close_log_locked()
            second = service.start()
        self.assertTrue(first["ok"])
        self.assertEqual(first["base_url"], "http://127.0.0.1:43210")
        self.assertTrue(token_one)
        self.assertNotEqual(token_one, second["token"])
        cmd = popen.call_args.args[0]
        self.assertIn("--api-key", cmd)
        self.assertIn("--port", cmd)
        self.assertEqual(cmd[cmd.index("--port") + 1], "43210")
        env = popen.call_args.kwargs["env"]
        self.assertEqual(env["MINERU_MODEL_SOURCE"], "modelscope")
        self.assertEqual(env["MINERU_LLAMA_CPP_BACKEND"], "cpu")

    def test_running_healthy_service_is_reused(self) -> None:
        self._materialize_api()
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True):
            service.start()
            again = service.start()
        self.assertTrue(again["ok"])
        self.assertIn("复用", again["detail"])
        self.assertEqual(popen.call_count, 1)

    def test_concurrent_starts_spawn_only_one_process(self) -> None:
        self._materialize_api()
        results: list[dict] = []
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True):
            threads = [threading.Thread(target=lambda: results.append(service.start()))
                       for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
        self.assertEqual(popen.call_count, 1)
        self.assertTrue(all(result["ok"] for result in results))

    def test_unhealthy_running_service_is_replaced(self) -> None:
        self._materialize_api()
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok",
                                  side_effect=[True, False, True]):
            service.start()
            again = service.start()
        self.assertTrue(again["ok"])
        self.assertEqual(popen.call_count, 2)
        self.kill_run.assert_called()
        self.assertEqual(self.kill_run.call_args.args[0][:2], ["taskkill", "/PID"])

    def test_early_exit_is_error_with_log_tail(self) -> None:
        self._materialize_api()
        (self.root / "service.log").write_text("boom: model load failed\n",
                                               encoding="utf-8")
        with self._popen(FakeProc(exit_code=1)), \
                mock.patch.object(service, "_health_ok", return_value=False):
            result = service.start()
        self.assertFalse(result["ok"])
        self.assertIn("提前退出", result["detail"])
        self.assertIn("boom", result["detail"])
        self.assertIsNone(service._PROC)

    def test_start_timeout_kills_and_fails(self) -> None:
        self._materialize_api()
        with self._popen(), \
                mock.patch.object(service, "_health_ok", return_value=False), \
                mock.patch.object(service, "START_TIMEOUT", 0):
            result = service.start()
        self.assertFalse(result["ok"])
        self.assertIn("没就绪", result["detail"])
        self.assertIsNone(service._PROC)
        self.assertEqual(service._PORT, 0)

    def test_stop_kills_tree_and_reverifies_port(self) -> None:
        self._materialize_api()
        with self._popen(FakeProc(pid=777)), \
                mock.patch.object(service, "_health_ok", return_value=True):
            service.start()
        result = service.stop()
        self.assertTrue(result["ok"])
        self.assertTrue(result["was_running"])
        self.assertTrue(result["port_closed"])
        self.assertEqual(result["port"], 43210)
        kill = self.kill_run.call_args.args[0]
        self.assertEqual(kill, ["taskkill", "/PID", "777", "/T", "/F"])
        self.port_open.assert_called_with(43210)
        self.assertIsNone(service.endpoint())

    def test_stop_when_idle_is_honest(self) -> None:
        result = service.stop()
        self.assertTrue(result["ok"])
        self.assertFalse(result["was_running"])
        self.kill_run.assert_not_called()

    def test_endpoint_is_readonly_none_when_stopped(self) -> None:
        self.assertIsNone(service.endpoint())
        self._materialize_api()
        with self._popen(), \
                mock.patch.object(service, "_health_ok", return_value=True):
            service.start()
        endpoint = service.endpoint()
        self.assertEqual(endpoint["base_url"], "http://127.0.0.1:43210")
        self.assertTrue(endpoint["token"])


if __name__ == "__main__":
    unittest.main()