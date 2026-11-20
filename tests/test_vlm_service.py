# -*- coding: utf-8 -*-
"""本地 VLM 服务编排（2.20.0 卡§4＋安装接线卡座5/6 多座）：fake subprocess，绝不起真 llama-server。

镜像 test_mineru_service 的收口纪律：未安装/权重缺诚实失败引导点安装／
懒起原生 llama-server（Vulkan/CUDA -ngl 999，显存不够 -ngl 0 CPU 慢兜底）／
动态端口＋每次随机令牌／健康同座复用／异座显式切换先停旧座／并发锁防双起／
提前退出与超时显性失败／stop 杀整棵进程树＋端口复验／endpoint 只读不触发起服。
生命周期小刀：/props 自检模型名（死实例不复用，fail-closed）／20 分钟闲停看门狗。
运行：``.venv/Scripts/python.exe -m unittest tests.test_vlm_service``
"""

from __future__ import annotations

import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from app.core import wire
from app.core.ingest.recognize import vlm_service as service


class FakeProc:
    def __init__(self, pid: int = 5321, exit_code: int | None = None) -> None:
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


class FakePropsResponse:
    def __init__(self, body: bytes = b"", status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakePropsResponse":
        return self

    def __exit__(self, *_exc) -> None:
        return None


class VlmServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        for name in ("_PROC", "_PORT", "_TOKEN", "_SEAT", "_LOG_HANDLE",
                     "_LAST_USED", "_WATCHDOG"):
            self.addCleanup(setattr, service, name, getattr(service, name))
        self.addCleanup(self._close_log)
        service._PROC = None
        service._PORT = 0
        service._TOKEN = ""
        service._SEAT = ""
        service._LOG_HANDLE = None
        service._LAST_USED = 0.0
        service._WATCHDOG = None
        self.real_start_watchdog = service._start_watchdog
        patcher = mock.patch.object(service, "_start_watchdog")
        self.watchdog_start = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(service.vlm_setup, "engine_dir",
                                    return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(service.vlm_weights, "engine_dir",
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
        patcher = mock.patch.object(service.vlm_setup, "gpu_ready", return_value=True)
        self.gpu_ready = patcher.start()
        self.addCleanup(patcher.stop)

    def _close_log(self) -> None:
        if service._LOG_HANDLE is not None:
            service._LOG_HANDLE.close()
            service._LOG_HANDLE = None

    def _materialize(self, seat: str = "qwen") -> None:
        bin_dir = self.root / "llama-bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / service.vlm_setup._server_name()).write_bytes(b"stub")
        (bin_dir / "ggml.dll").write_bytes(b"stub")
        (bin_dir / "ggml-vulkan.dll").write_bytes(b"stub")
        for path in service.vlm_setup.model_paths(seat):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"stub-gguf")

    def _popen(self, proc: FakeProc | None = None):
        return mock.patch.object(service.subprocess, "Popen",
                                 return_value=proc or FakeProc())

    def test_not_installed_is_honest_failure_never_auto_install(self) -> None:
        missing = {"ok": False, "state": "missing", "version": "",
                   "message": "本地 VLM 未安装。"}
        with mock.patch.object(service.vlm_setup, "health", return_value=missing), \
                self._popen() as popen:
            result = service.ensure_ready()
        self.assertFalse(result["ok"])
        self.assertIn("点【安装】", result["detail"])
        popen.assert_not_called()

    def test_missing_weights_is_honest_failure(self) -> None:
        ready = {"ok": True, "state": "ready", "version": "0.3.36", "message": ""}
        with mock.patch.object(service.vlm_setup, "health", return_value=ready), \
                mock.patch.object(service.vlm_setup, "weights_ready",
                                  return_value=False), \
                self._popen() as popen:
            result = service.ensure_ready()
        self.assertFalse(result["ok"])
        self.assertIn("GGUF 权重不在本机", result["detail"])
        popen.assert_not_called()

    def test_missing_entry_or_weights_is_honest_failure(self) -> None:
        with self._popen() as popen:
            result = service.start()
        self.assertFalse(result["ok"])
        self.assertIn("重试安装", result["detail"])
        popen.assert_not_called()

    def test_start_uses_dynamic_port_random_token_and_gpu(self) -> None:
        self._materialize()
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
        cmd = popen.call_args_list[0].args[0]
        self.assertTrue(cmd[0].endswith(service.vlm_setup._server_name()))
        self.assertEqual(cmd[cmd.index("--port") + 1], "43210")
        self.assertEqual(cmd[cmd.index("--api-key") + 1], token_one)
        self.assertIn("--mmproj", cmd)
        self.assertIn("--jinja", cmd)
        self.assertEqual(cmd[cmd.index("--ctx-size") + 1], "8192")
        self.assertEqual(cmd[cmd.index("-ngl") + 1], "999")
        self.assertEqual(cmd[cmd.index("--host") + 1], "127.0.0.1")
        self.assertIn("显卡加速", first["detail"])

    def test_start_low_vram_falls_back_to_cpu_layers(self) -> None:
        self._materialize()
        self.gpu_ready.return_value = False
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True):
            result = service.start()
        self.assertTrue(result["ok"])
        cmd = popen.call_args.args[0]
        self.assertEqual(cmd[cmd.index("-ngl") + 1], "0")
        self.assertIn("CPU 慢兜底", result["detail"])

    def test_running_healthy_service_is_reused(self) -> None:
        self._materialize()
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True), \
                mock.patch.object(service, "_serves_expected_model",
                                  return_value=True):
            service.start()
            again = service.start()
        self.assertTrue(again["ok"])
        self.assertIn("复用", again["detail"])
        self.assertEqual(popen.call_count, 1)

    def test_concurrent_starts_spawn_only_one_process(self) -> None:
        self._materialize()
        results: list[dict] = []
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True), \
                mock.patch.object(service, "_serves_expected_model",
                                  return_value=True):
            threads = [threading.Thread(target=lambda: results.append(service.start()))
                       for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
        self.assertEqual(popen.call_count, 1)
        self.assertTrue(all(result["ok"] for result in results))

    def test_unhealthy_running_service_is_replaced(self) -> None:
        self._materialize()
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
        self._materialize()
        (self.root / "service.log").write_text("boom: gguf load failed\n",
                                               encoding="utf-8")
        with self._popen(FakeProc(exit_code=1)), \
                mock.patch.object(service, "_health_ok", return_value=False):
            result = service.start()
        self.assertFalse(result["ok"])
        self.assertIn("提前退出", result["detail"])
        self.assertIn("boom", result["detail"])
        self.assertIsNone(service._PROC)

    def test_start_timeout_kills_and_fails(self) -> None:
        self._materialize()
        with self._popen(), \
                mock.patch.object(service, "_health_ok", return_value=False), \
                mock.patch.object(service, "START_TIMEOUT", 0):
            result = service.start()
        self.assertFalse(result["ok"])
        self.assertIn("没就绪", result["detail"])
        self.assertIn("service.log", result["detail"])
        self.assertIsNone(service._PROC)
        self.assertEqual(service._PORT, 0)

    def test_stop_kills_tree_and_reverifies_port(self) -> None:
        self._materialize()
        with self._popen(FakeProc(pid=888)), \
                mock.patch.object(service, "_health_ok", return_value=True):
            service.start()
        result = service.stop()
        self.assertTrue(result["ok"])
        self.assertTrue(result["was_running"])
        self.assertTrue(result["port_closed"])
        self.assertEqual(result["port"], 43210)
        kill = self.kill_run.call_args.args[0]
        self.assertEqual(kill, ["taskkill", "/PID", "888", "/T", "/F"])
        self.port_open.assert_called_with(43210)
        self.assertIsNone(service.endpoint())

    def test_stop_when_idle_is_honest(self) -> None:
        result = service.stop()
        self.assertTrue(result["ok"])
        self.assertFalse(result["was_running"])
        self.kill_run.assert_not_called()

    def test_endpoint_is_readonly_none_when_stopped(self) -> None:
        self.assertIsNone(service.endpoint())
        self._materialize()
        with self._popen(), \
                mock.patch.object(service, "_health_ok", return_value=True):
            service.start()
        endpoint = service.endpoint()
        self.assertEqual(endpoint["base_url"], "http://127.0.0.1:43210")
        self.assertTrue(endpoint["token"])

    def test_seat_switch_stops_old_and_spawns_new_with_seat_weights(self) -> None:
        self._materialize("qwen")
        self._materialize("intern")
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True):
            first = service.start("qwen")
            self.assertEqual(service.active_seat(), "qwen")
            second = service.start("intern")
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(popen.call_count, 2)
        self.kill_run.assert_called()
        self.assertEqual(service.active_seat(), "intern")
        self.assertEqual(second["seat"], "intern")
        self.assertIn("书生", second["seat_label"])
        cmd = popen.call_args_list[1].args[0]
        self.assertIn("InternVL3-2B.Q4_K_M.gguf", cmd[cmd.index("--model") + 1])
        self.assertIn("InternVL3-2B.mmproj-f16.gguf", cmd[cmd.index("--mmproj") + 1])

    def test_same_seat_healthy_reuse_does_not_kill(self) -> None:
        self._materialize("intern")
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True), \
                mock.patch.object(service, "_serves_expected_model",
                                  return_value=True):
            service.start("intern")
            again = service.start("intern")
        self.assertIn("复用", again["detail"])
        self.assertEqual(popen.call_count, 1)
        self.kill_run.assert_not_called()

    def test_healthy_service_with_expected_weights_is_reused(self) -> None:
        self._materialize()
        model = service.vlm_setup.model_paths("qwen")[0]
        body = wire.dumps({"model_path": str(model)}).encode("utf-8")
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True), \
                mock.patch.object(service.urllib.request, "urlopen",
                                  return_value=FakePropsResponse(body)):
            service.start()
            again = service.start()
        self.assertTrue(again["ok"])
        self.assertIn("复用", again["detail"])
        self.assertEqual(popen.call_count, 1)
        self.kill_run.assert_not_called()

    def test_healthy_service_with_stale_weights_is_restarted(self) -> None:
        self._materialize()
        body = wire.dumps({"model_path": "E:/old/Old-Qwen.gguf"}).encode("utf-8")
        with self._popen() as popen, \
                mock.patch.object(service, "_health_ok", return_value=True), \
                mock.patch.object(service.urllib.request, "urlopen",
                                  return_value=FakePropsResponse(body)), \
                self.assertLogs(service.logger, level="WARNING") as logs:
            service.start()
            again = service.start()
        self.assertTrue(again["ok"])
        self.assertNotIn("复用", again["detail"])
        self.assertEqual(popen.call_count, 2)
        self.kill_run.assert_called()
        self.assertTrue(any("复用自检不通过" in line for line in logs.output))

    def test_props_selfcheck_compares_expected_model_name(self) -> None:
        model = service.vlm_setup.model_paths("qwen")[0]
        body = wire.dumps({"model_path": "D:/weights/" + model.name}).encode("utf-8")
        with mock.patch.object(service.urllib.request, "urlopen",
                               return_value=FakePropsResponse(body)) as urlopen:
            result = service._serves_expected_model("http://127.0.0.1:1", "tok", model)
        self.assertTrue(result)
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/props"))
        self.assertEqual(request.get_header("Authorization"), "Bearer tok")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 5)

    def test_props_selfcheck_mismatch_or_failures_are_fail_closed(self) -> None:
        model = service.vlm_setup.model_paths("qwen")[0]
        args = ("http://127.0.0.1:1", "tok", model)
        stale = wire.dumps({"model_path": "D:/weights/Old-Qwen.gguf"}).encode("utf-8")
        with mock.patch.object(service.urllib.request, "urlopen",
                               return_value=FakePropsResponse(stale)):
            self.assertFalse(service._serves_expected_model(*args))
        with mock.patch.object(service.urllib.request, "urlopen",
                               return_value=FakePropsResponse(b"", status=404)):
            self.assertFalse(service._serves_expected_model(*args))
        with mock.patch.object(service.urllib.request, "urlopen",
                               side_effect=urllib.error.URLError("refused")):
            self.assertFalse(service._serves_expected_model(*args))
        with mock.patch.object(service.urllib.request, "urlopen",
                               side_effect=TimeoutError("timeout")):
            self.assertFalse(service._serves_expected_model(*args))
        with mock.patch.object(service.urllib.request, "urlopen",
                               return_value=FakePropsResponse(b"not-json")):
            self.assertFalse(service._serves_expected_model(*args))
        with mock.patch.object(service.urllib.request, "urlopen",
                               return_value=FakePropsResponse(wire.dumps({}).encode())):
            self.assertFalse(service._serves_expected_model(*args))

    def test_watchdog_stops_only_when_idle_expired(self) -> None:
        self.assertTrue(service._idle_expired(
            100.0, 100.0 + service.WARM_IDLE_SECONDS + 1))
        self.assertFalse(service._idle_expired(
            100.0, 100.0 + service.WARM_IDLE_SECONDS))
        self.assertFalse(service._idle_expired(0.0, 10 ** 9))
        self._materialize()
        with self._popen(FakeProc(pid=777)), \
                mock.patch.object(service, "_health_ok", return_value=True):
            service.start()
        now = service.time.monotonic()
        service._LAST_USED = now - (service.WARM_IDLE_SECONDS + 1)
        self.assertTrue(service._watchdog_tick(now))
        self.assertIsNone(service._PROC)
        self.assertIsNone(service.endpoint())
        self.assertEqual(self.kill_run.call_args.args[0],
                         ["taskkill", "/PID", "777", "/T", "/F"])

    def test_watchdog_keeps_service_within_idle_window(self) -> None:
        self._materialize()
        with self._popen(), \
                mock.patch.object(service, "_health_ok", return_value=True):
            service.start()
        self.assertFalse(service._watchdog_tick(service.time.monotonic()))
        self.assertIsNotNone(service._PROC)
        self.kill_run.assert_not_called()

    def test_touch_refreshes_idle_clock(self) -> None:
        self._materialize()
        with self._popen(), \
                mock.patch.object(service, "_health_ok", return_value=True):
            service.start()
        now = service.time.monotonic()
        service._LAST_USED = now - (service.WARM_IDLE_SECONDS + 60)
        service.touch()
        self.assertFalse(service._watchdog_tick(now))
        self.assertIsNotNone(service._PROC)
        self.kill_run.assert_not_called()

    def test_touch_without_running_service_is_silent(self) -> None:
        service._LAST_USED = 123.0
        service.touch()
        self.assertEqual(service._LAST_USED, 123.0)

    def test_watchdog_thread_starts_only_once(self) -> None:
        service._WATCHDOG = None
        with mock.patch.object(service.threading, "Thread") as thread_cls:
            thread_cls.return_value.is_alive.return_value = True
            self.real_start_watchdog()
            self.real_start_watchdog()
        self.assertEqual(thread_cls.call_count, 1)
        thread_cls.return_value.start.assert_called_once()

    def test_active_seat_empty_when_stopped(self) -> None:
        self.assertEqual(service.active_seat(), "")
        self._materialize()
        with self._popen(), \
                mock.patch.object(service, "_health_ok", return_value=True):
            service.start()
        self.assertEqual(service.active_seat(), "qwen")
        service.stop()
        self.assertEqual(service.active_seat(), "")

    def test_ensure_ready_checks_requested_seat_weights(self) -> None:
        ready = {"ok": True, "state": "ready", "version": "0.2.3", "message": ""}
        with mock.patch.object(service.vlm_setup, "health", return_value=ready), \
                mock.patch.object(service.vlm_setup, "weights_ready",
                                  return_value=False) as weights, \
                self._popen() as popen:
            result = service.ensure_ready("minicpm")
        weights.assert_called_once_with("minicpm")
        self.assertFalse(result["ok"])
        self.assertIn("面壁", result["detail"])
        popen.assert_not_called()

    def test_min_vram_reads_matching_seat_catalog_entry(self) -> None:
        entries = [{"id": "vlm_qwen", "min_vram": 6},
                   {"id": "vlm_intern", "min_vram": 4}]
        with mock.patch("app.core.ingest.registry.catalog", return_value=entries):
            self.assertEqual(service._min_vram("intern"), 4)
            self.assertEqual(service._min_vram("qwen"), 6)
            self.assertEqual(service._min_vram("minicpm"), 6)


if __name__ == "__main__":
    unittest.main()