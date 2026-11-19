# -*- coding: utf-8 -*-
"""本地 VLM 一键装（T6 §3）：fake subprocess/urllib，绝不真装真下载。

覆盖：体检三态（missing/ready/error）每次现算／权重按字节数核对／
GGUF 流式下载 sha256 校验不过即丢弃／已装点击直接 done／在装复用／
失败分类人话（网络/无轮）。
运行：``.venv/Scripts/python.exe -m unittest tests.test_vlm_setup``
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core.ingest import vlm_setup


class _FakeResponse:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    def read(self, _size: int = -1) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc) -> None:
        return None


class SetupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        patcher = mock.patch.object(vlm_setup.config, "PROJECT_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        saved_state = dict(vlm_setup._STATE)
        saved_thread = vlm_setup._THREAD
        self.addCleanup(self._restore, saved_state, saved_thread)
        vlm_setup._STATE.update({"state": "idle", "step": "", "message": ""})
        vlm_setup._THREAD = None

    def _restore(self, state: dict, thread) -> None:
        if vlm_setup._THREAD is not None and vlm_setup._THREAD is not thread:
            vlm_setup._THREAD.join(timeout=10)
        vlm_setup._STATE.clear()
        vlm_setup._STATE.update(state)
        vlm_setup._THREAD = thread

    def _materialize_python(self) -> Path:
        exe = vlm_setup.python_exe()
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b"stub")
        return exe

    def test_engine_dir_is_independent_from_mineru(self) -> None:
        self.assertEqual(vlm_setup.engine_dir(), self.root / "engines" / "vlm")
        self.assertNotIn("mineru", str(vlm_setup.engine_dir()))

    def test_gguf_contract_is_qwen_q4_plus_mmproj(self) -> None:
        names = [row[0] for row in vlm_setup.GGUF_FILES]
        self.assertEqual(names, ["Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf", "mmproj-F16.gguf"])
        self.assertIn("modelscope.cn", vlm_setup.MODEL_BASE)
        self.assertIn("unsloth/Qwen2.5-VL-3B-Instruct-GGUF", vlm_setup.MODEL_BASE)
        model, mmproj = vlm_setup.model_paths()
        self.assertEqual(model.name, names[0])
        self.assertEqual(mmproj.name, names[1])

    def test_health_missing_when_no_interpreter(self) -> None:
        check = vlm_setup.health()
        self.assertFalse(check["ok"])
        self.assertEqual(check["state"], "missing")
        self.assertIn("未安装", check["message"])

    def test_health_ready_reports_version(self) -> None:
        self._materialize_python()
        with mock.patch.object(vlm_setup, "_run",
                               return_value=(0, "LLAMA_CPP_VERSION=0.3.36\n")):
            check = vlm_setup.health()
        self.assertTrue(check["ok"])
        self.assertEqual(check["state"], "ready")
        self.assertEqual(check["version"], "0.3.36")

    def test_health_broken_env_is_error_not_missing(self) -> None:
        self._materialize_python()
        with mock.patch.object(vlm_setup, "_run",
                               return_value=(1, "dll load failed")):
            check = vlm_setup.health()
        self.assertFalse(check["ok"])
        self.assertEqual(check["state"], "error")
        self.assertIn("体检失败", check["message"])

    def test_weights_ready_checks_exact_bytes(self) -> None:
        small = (("a.gguf", 4, "x"), ("b.gguf", 4, "y"))
        with mock.patch.object(vlm_setup, "GGUF_FILES", small):
            self.assertFalse(vlm_setup.weights_ready())
            folder = vlm_setup.engine_dir() / "models"
            folder.mkdir(parents=True)
            (folder / "a.gguf").write_bytes(b"abcd")
            self.assertFalse(vlm_setup.weights_ready(), "缺一件当不在")
            (folder / "b.gguf").write_bytes(b"abcd")
            self.assertTrue(vlm_setup.weights_ready())
            (folder / "b.gguf").write_bytes(b"abc")
            self.assertFalse(vlm_setup.weights_ready(), "字节数不符当不在")

    def test_download_checksum_mismatch_discards_part(self) -> None:
        with mock.patch.object(vlm_setup.urllib.request, "urlopen",
                               return_value=_FakeResponse([b"abc"])):
            with self.assertRaises(vlm_setup.VlmSetupError) as caught:
                vlm_setup._download_gguf("a.gguf", 3, "0" * 64)
        self.assertIn("校验不过", str(caught.exception))
        folder = vlm_setup.engine_dir() / "models"
        self.assertFalse((folder / "a.gguf").exists())
        self.assertFalse((folder / "a.gguf.part").exists())

    def test_download_good_checksum_lands_atomically(self) -> None:
        digest = hashlib.sha256(b"abc").hexdigest()
        with mock.patch.object(vlm_setup.urllib.request, "urlopen",
                               return_value=_FakeResponse([b"a", b"bc"])):
            vlm_setup._download_gguf("a.gguf", 3, digest)
        target = vlm_setup.engine_dir() / "models" / "a.gguf"
        self.assertEqual(target.read_bytes(), b"abc")
        self.assertFalse(target.with_suffix(".gguf.part").exists())

    def test_download_network_failure_is_human_reason(self) -> None:
        with mock.patch.object(vlm_setup.urllib.request, "urlopen",
                               side_effect=OSError("connection refused")):
            with self.assertRaises(vlm_setup.VlmSetupError) as caught:
                vlm_setup._download_gguf("a.gguf", 3, "0" * 64)
        self.assertIn("网络或镜像不通", str(caught.exception))

    def test_prefetch_skips_files_already_present(self) -> None:
        small = (("a.gguf", 4, "x"), ("b.gguf", 4, "y"))
        folder = vlm_setup.engine_dir() / "models"
        folder.mkdir(parents=True)
        (folder / "a.gguf").write_bytes(b"abcd")
        (folder / "b.gguf").write_bytes(b"abcd")
        with mock.patch.object(vlm_setup, "GGUF_FILES", small), \
                mock.patch.object(vlm_setup.urllib.request, "urlopen") as urlopen:
            self.assertTrue(vlm_setup._prefetch_weights())
        urlopen.assert_not_called()

    def test_start_install_when_ready_is_done_without_thread(self) -> None:
        ready = {"ok": True, "state": "ready", "version": "0.3.36", "message": ""}
        with mock.patch.object(vlm_setup, "health", return_value=ready), \
                mock.patch.object(vlm_setup, "weights_ready", return_value=True), \
                mock.patch.object(vlm_setup.threading, "Thread") as thread:
            state = vlm_setup.start_install()
        self.assertEqual(state["state"], "done")
        self.assertIn("0.3.36", state["message"])
        thread.assert_not_called()

    def test_start_install_missing_env_spawns_background_thread(self) -> None:
        missing = {"ok": False, "state": "missing", "version": "",
                   "message": "本地 VLM 未安装。"}
        with mock.patch.object(vlm_setup, "health", return_value=missing), \
                mock.patch.object(vlm_setup, "_install") as install:
            state = vlm_setup.start_install()
            self.assertEqual(state["state"], "installing")
            self.assertEqual(state["step"], "创建隔离环境")
            self.assertIn("engines/vlm/", state["message"])
            vlm_setup._THREAD.join(timeout=10)
        install.assert_called_once()

    def test_start_install_reuses_running_thread(self) -> None:
        missing = {"ok": False, "state": "missing", "version": "",
                   "message": "本地 VLM 未安装。"}
        fake = mock.Mock()
        fake.is_alive.return_value = True
        vlm_setup._THREAD = fake
        vlm_setup._STATE.update({"state": "installing", "step": "安装依赖",
                                 "message": "正在安装"})
        with mock.patch.object(vlm_setup, "health", return_value=missing), \
                mock.patch.object(vlm_setup.threading, "Thread") as thread:
            state = vlm_setup.start_install()
        self.assertEqual(state["state"], "installing")
        thread.assert_not_called()

    def test_old_python_is_rejected_with_human_reason(self) -> None:
        with mock.patch.object(vlm_setup.sys, "version_info", (3, 10, 0)):
            with self.assertRaises(vlm_setup.VlmSetupError) as caught:
                vlm_setup.start_install()
        self.assertIn("3.11+", str(caught.exception))

    def test_classify_network_and_no_wheel(self) -> None:
        self.assertEqual(vlm_setup._classify("Max retries exceeded with url"),
                         "网络或镜像不通")
        self.assertIn("镜像里没有这个版本",
                      vlm_setup._classify("No matching distribution found"))
        self.assertEqual(vlm_setup._classify(""), "未知原因")

    def test_install_failure_sets_error_state(self) -> None:
        with mock.patch.object(vlm_setup, "python_exe",
                               return_value=self.root / "nope.exe"), \
                mock.patch.object(vlm_setup, "_run",
                                  return_value=(1, "connection refused")):
            vlm_setup._install()
        state = vlm_setup.status()
        self.assertEqual(state["state"], "error")
        self.assertIn("隔离环境创建失败", state["message"])
        self.assertIn("网络或镜像不通", state["message"])


if __name__ == "__main__":
    unittest.main()