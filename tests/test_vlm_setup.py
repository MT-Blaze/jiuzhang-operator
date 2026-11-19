# -*- coding: utf-8 -*-
"""本地 VLM 一键装·多座（2.20.0 卡§4/§7＋安装接线卡座5/6）：fake subprocess/urllib，绝不真装真下载。

覆盖：发动机真二进制体检（三座共享）／各座权重按字节数核对／GGUF 流式下载
sha256 校验不过即丢弃／三源测速选路＋中断换源＋浏览器 UA／pip 四家测速／
pip 全败迁移 engines/mineru 现成 Vulkan 栈／按座卸载互不误删、全座空才删目录／
已装点击直接 done／在装复用／失败分类人话／禁 GitHub／未知座显性。
运行：``.venv/Scripts/python.exe -m unittest tests.test_vlm_setup``
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core.ingest import vlm_setup, vlm_weights


class _FakeResponse:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    def read(self, _size: int = -1) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc) -> None:
        return None


def _sources(*names: str) -> list[dict]:
    return [{"name": name, "url": "https://%s.test/a.gguf" % name,
             "ok": True, "ms": 10} for name in names]


SMALL_SEATS = {"qwen": {"label": "测试千问", "repo": "t/q", "size_note": "约 0GB",
                        "files": (("a.gguf", 4, "x"), ("b.gguf", 4, "y"))},
               "intern": {"label": "测试书生", "repo": "t/i", "size_note": "约 0GB",
                          "files": (("c.gguf", 4, "z"), ("d.gguf", 4, "w"))}}


class SetupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        patcher = mock.patch.object(vlm_setup.config, "PROJECT_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        saved_state = {seat: dict(row) for seat, row in vlm_setup._STATE.items()}
        saved_thread = dict(vlm_setup._THREAD)
        self.addCleanup(self._restore, saved_state, saved_thread)
        for seat in vlm_setup._STATE:
            vlm_setup._STATE[seat] = {"state": "idle", "step": "", "message": ""}
            vlm_setup._THREAD[seat] = None

    def _restore(self, state: dict, thread: dict) -> None:
        for seat, row in state.items():
            worker = vlm_setup._THREAD.get(seat)
            if worker is not None and worker is not thread.get(seat):
                worker.join(timeout=10)
            vlm_setup._STATE[seat] = row
            vlm_setup._THREAD[seat] = thread.get(seat)

    def _materialize_engine(self, backend: str = "vulkan",
                            folder: Path | None = None) -> Path:
        """造真二进制布局：llama-server＋ggml＋后端库＋dist-info 版本号。"""
        site = vlm_setup._venv_site_packages()
        bin_dir = folder or site / vlm_setup.ENGINE_MODULE / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / vlm_setup._server_name()).write_bytes(b"stub")
        (bin_dir / "ggml.dll").write_bytes(b"stub")
        if backend in ("vulkan", "cuda"):
            (bin_dir / ("ggml-%s.dll" % backend)).write_bytes(b"stub")
        if folder is None:
            info = site / (vlm_setup.ENGINE_MODULE + "-0.2.3.dist-info")
            info.mkdir(parents=True, exist_ok=True)
            (info / "METADATA").write_text("Name: mineru-llama-cpp\n", encoding="utf-8")
        return bin_dir

    def test_engine_dir_is_independent_from_mineru(self) -> None:
        self.assertEqual(vlm_setup.engine_dir(), self.root / "engines" / "vlm")
        self.assertNotIn("mineru", str(vlm_setup.engine_dir()))

    def test_three_seats_each_gguf_plus_mmproj(self) -> None:
        self.assertEqual(sorted(vlm_weights.SEATS), ["intern", "minicpm", "qwen"])
        for seat in vlm_weights.SEATS:
            model, mmproj = vlm_setup.model_paths(seat)
            self.assertTrue(model.name.lower().endswith(".gguf"))
            self.assertIn("mmproj", mmproj.name.lower())
            self.assertEqual(model.parent, vlm_setup.engine_dir() / "models")

    def test_weight_sources_are_domestic_three_no_github(self) -> None:
        for seat in vlm_weights.SEATS:
            urls = vlm_weights.weight_urls(seat, "a.gguf")
            joined = " ".join(url for _name, url in urls)
            self.assertIn("modelscope.cn", joined)
            self.assertIn("hf-mirror.com", joined)
            self.assertIn("gitcode.com", joined)
            self.assertNotIn("github", joined.lower())
        pip_joined = " ".join(url for _n, url in
                              vlm_setup.mirrors.pip_candidates("mineru-llama-cpp"))
        self.assertNotIn("github", pip_joined.lower())
        self.assertNotIn("pypi.org", pip_joined)

    def test_unknown_seat_is_explicit_setup_error(self) -> None:
        for call in (lambda: vlm_setup.status("nope"),
                     lambda: vlm_setup.start_install("nope"),
                     lambda: vlm_setup.uninstall("nope")):
            with self.assertRaises(vlm_setup.VlmSetupError):
                call()
        with self.assertRaises(vlm_weights.VlmWeightsError):
            vlm_weights.seat_of("vlm_nope")
        self.assertEqual(vlm_weights.seat_of("vlm_intern"), "intern")

    def test_health_missing_when_no_server_binary(self) -> None:
        check = vlm_setup.health()
        self.assertFalse(check["ok"])
        self.assertEqual(check["state"], "missing")
        self.assertIn("未安装", check["message"])

    def test_health_ready_reports_version_and_engine(self) -> None:
        self._materialize_engine("vulkan")
        check = vlm_setup.health()
        self.assertTrue(check["ok"])
        self.assertEqual(check["state"], "ready")
        self.assertEqual(check["version"], "0.2.3")
        self.assertEqual(check["engine"], "vulkan")

    def test_engine_type_computed_from_real_binaries(self) -> None:
        bin_dir = self._materialize_engine("cuda")
        self.assertEqual(vlm_setup.engine_type(), "cuda")
        (bin_dir / "ggml-cuda.dll").unlink()
        (bin_dir / "ggml-vulkan.dll").write_bytes(b"stub")
        self.assertEqual(vlm_setup.engine_type(), "vulkan")
        (bin_dir / "ggml-vulkan.dll").unlink()
        self.assertEqual(vlm_setup.engine_type(), "cpu")

    def test_health_broken_binary_is_error_not_missing(self) -> None:
        bin_dir = self._materialize_engine("vulkan")
        (bin_dir / "ggml.dll").unlink()
        check = vlm_setup.health()
        self.assertFalse(check["ok"])
        self.assertEqual(check["state"], "error")
        self.assertIn("残缺", check["message"])

    def test_weights_ready_per_seat_checks_exact_bytes(self) -> None:
        with mock.patch.object(vlm_weights, "SEATS", SMALL_SEATS):
            self.assertFalse(vlm_setup.weights_ready("qwen"))
            folder = vlm_setup.engine_dir() / "models"
            folder.mkdir(parents=True)
            (folder / "a.gguf").write_bytes(b"abcd")
            self.assertFalse(vlm_setup.weights_ready("qwen"), "缺一件当不在")
            (folder / "b.gguf").write_bytes(b"abcd")
            self.assertTrue(vlm_setup.weights_ready("qwen"))
            self.assertFalse(vlm_setup.weights_ready("intern"), "别座在不算本座在")
            (folder / "b.gguf").write_bytes(b"abc")
            self.assertFalse(vlm_setup.weights_ready("qwen"), "字节数不符当不在")

    def test_start_install_when_ready_is_done_without_thread(self) -> None:
        ready = {"ok": True, "state": "ready", "version": "0.2.3",
                 "engine": "vulkan", "message": ""}
        with mock.patch.object(vlm_setup, "health", return_value=ready), \
                mock.patch.object(vlm_setup, "weights_ready", return_value=True), \
                mock.patch.object(vlm_setup.threading, "Thread") as thread:
            state = vlm_setup.start_install("intern")
        self.assertEqual(state["state"], "done")
        self.assertIn("0.2.3", state["message"])
        self.assertIn("Vulkan", state["message"])
        self.assertIn("书生", state["message"])
        thread.assert_not_called()

    def test_start_install_missing_env_spawns_background_thread(self) -> None:
        missing = {"ok": False, "state": "missing", "version": "", "engine": "",
                   "message": "本地 VLM 发动机未安装（缺 llama-server）。"}
        with mock.patch.object(vlm_setup, "health", return_value=missing), \
                mock.patch.object(vlm_setup, "_install") as install:
            state = vlm_setup.start_install("minicpm")
            self.assertEqual(state["state"], "installing")
            self.assertEqual(state["step"], "创建隔离环境")
            self.assertIn("engines/vlm/", state["message"])
            vlm_setup._THREAD["minicpm"].join(timeout=10)
        install.assert_called_once_with("minicpm")

    def test_start_install_engine_ready_only_prefetches_weights(self) -> None:
        ready = {"ok": True, "state": "ready", "version": "0.2.3",
                 "engine": "vulkan", "message": ""}
        with mock.patch.object(vlm_setup, "health", return_value=ready), \
                mock.patch.object(vlm_setup, "weights_ready", return_value=False), \
                mock.patch.object(vlm_setup, "_install"):
            state = vlm_setup.start_install("intern")
            vlm_setup._THREAD["intern"].join(timeout=10)
        self.assertEqual(state["step"], "预取权重")
        self.assertIn("书生", state["message"])

    def test_start_install_reuses_running_thread_per_seat(self) -> None:
        missing = {"ok": False, "state": "missing", "version": "", "engine": "",
                   "message": "本地 VLM 发动机未安装（缺 llama-server）。"}
        fake = mock.Mock()
        fake.is_alive.return_value = True
        vlm_setup._THREAD["intern"] = fake
        vlm_setup._STATE["intern"].update({"state": "installing", "step": "安装发动机",
                                           "message": "正在安装"})
        with mock.patch.object(vlm_setup, "health", return_value=missing), \
                mock.patch.object(vlm_setup.threading, "Thread") as thread:
            state = vlm_setup.start_install("intern")
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

    def test_install_failure_sets_error_state_for_that_seat_only(self) -> None:
        with mock.patch.object(vlm_setup, "python_exe",
                               return_value=self.root / "nope.exe"), \
                mock.patch.object(vlm_setup, "_run",
                                  return_value=(1, "connection refused")):
            vlm_setup._install("intern")
        state = vlm_setup.status("intern")
        self.assertEqual(state["state"], "error")
        self.assertIn("隔离环境创建失败", state["message"])
        self.assertIn("网络或镜像不通", state["message"])
        self.assertEqual(vlm_setup.status("qwen")["state"], "idle")

    def test_engine_install_races_pip_and_falls_to_next_mirror(self) -> None:
        exe = vlm_setup.python_exe()
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b"stub")
        raced = [{"name": "阿里云", "url": "https://aliyun.test/simple/mineru-llama-cpp/",
                  "ok": True, "ms": 90},
                 {"name": "清华", "url": "https://tsinghua.test/simple/mineru-llama-cpp/",
                  "ok": True, "ms": 150}]
        calls: list[list[str]] = []

        def run(cmd, timeout):
            calls.append(cmd)
            return (1, "403 forbidden") if len(calls) == 1 else (0, "ok")

        with mock.patch.object(vlm_setup.mirrors, "race", return_value=raced), \
                mock.patch.object(vlm_setup, "_run", side_effect=run):
            vlm_setup._install_engine("qwen")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][calls[0].index("--index-url") + 1], raced[0]["url"])
        self.assertEqual(calls[1][calls[1].index("--index-url") + 1], raced[1]["url"])
        self.assertIn(vlm_setup.ENGINE_PACKAGE, calls[0])
        self.assertIn("清华", vlm_setup.status("qwen")["message"])

    def test_pip_all_fail_migrates_existing_vulkan_stack_offline(self) -> None:
        exe = vlm_setup.python_exe()
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b"stub")
        source = (self.root / "engines" / "mineru" / "Lib" / "site-packages"
                  / vlm_setup.ENGINE_MODULE / "bin")
        source.mkdir(parents=True)
        (source / vlm_setup._server_name()).write_bytes(b"server")
        (source / "ggml-vulkan.dll").write_bytes(b"vulkan")
        (source / "ggml.dll").write_bytes(b"base")
        raced = [{"name": "阿里云", "url": "https://aliyun.test/x/", "ok": True, "ms": 90}]
        with mock.patch.object(vlm_setup.mirrors, "race", return_value=raced), \
                mock.patch.object(vlm_setup, "_run",
                                  return_value=(1, "connection refused")), \
                mock.patch.object(vlm_weights.urllib.request, "urlopen") as urlopen:
            vlm_setup._install_engine("intern")
        urlopen.assert_not_called()
        target = vlm_setup.engine_dir() / "llama-bin"
        self.assertTrue((target / vlm_setup._server_name()).is_file())
        self.assertTrue((target / "ggml-vulkan.dll").is_file())
        self.assertTrue((target / "engine.toml").is_file())
        check = vlm_setup.health()
        self.assertTrue(check["ok"])
        self.assertEqual(check["engine"], "vulkan")
        self.assertIn("迁移", vlm_setup.status("intern")["message"])

    def test_pip_all_fail_without_migration_source_is_explicit(self) -> None:
        exe = vlm_setup.python_exe()
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b"stub")
        raced = [{"name": "阿里云", "url": "https://aliyun.test/x/", "ok": True, "ms": 90}]
        with mock.patch.object(vlm_setup.mirrors, "race", return_value=raced), \
                mock.patch.object(vlm_setup, "_run",
                                  return_value=(1, "connection refused")):
            with self.assertRaises(vlm_setup.VlmSetupError) as caught:
                vlm_setup._install_engine("qwen")
        self.assertIn("发动机安装全败", str(caught.exception))
        self.assertIn("CUDA 专轮国内镜像无货", str(caught.exception))

    def test_gpu_ready_needs_real_backend_and_vram(self) -> None:
        self._materialize_engine("vulkan")
        with mock.patch.object(vlm_setup, "engine_type", return_value="vulkan"), \
                mock.patch("app.core.ingest.hardware.probe",
                           return_value={"vram_gb": 6.0}):
            self.assertTrue(vlm_setup.gpu_ready(6))
        with mock.patch.object(vlm_setup, "engine_type", return_value="vulkan"), \
                mock.patch("app.core.ingest.hardware.probe",
                           return_value={"vram_gb": 4.0}):
            self.assertFalse(vlm_setup.gpu_ready(6))
        with mock.patch.object(vlm_setup, "engine_type", return_value="cpu"), \
                mock.patch("app.core.ingest.hardware.probe",
                           return_value={"vram_gb": 16.0}):
            self.assertFalse(vlm_setup.gpu_ready(6))

    def test_uninstall_removes_only_this_seat_weights(self) -> None:
        self._materialize_engine("vulkan")
        with mock.patch.object(vlm_weights, "SEATS", SMALL_SEATS):
            folder = vlm_setup.engine_dir() / "models"
            folder.mkdir(parents=True)
            for name in ("a.gguf", "b.gguf", "c.gguf", "d.gguf"):
                (folder / name).write_bytes(b"abcd")
            result = vlm_setup.uninstall("qwen")
            self.assertTrue(result["ok"])
            self.assertIn("其他座不受影响", result["message"])
            self.assertFalse((folder / "a.gguf").exists())
            self.assertFalse((folder / "b.gguf").exists())
            self.assertTrue((folder / "c.gguf").exists())
            self.assertTrue((folder / "d.gguf").exists())
            self.assertTrue(vlm_setup.engine_dir().exists(), "别座还在，发动机不删")
            self.assertEqual(vlm_setup.status("qwen")["state"], "idle")

    def test_uninstall_last_seat_removes_whole_engine_dir(self) -> None:
        self._materialize_engine("vulkan")
        with mock.patch.object(vlm_weights, "SEATS", SMALL_SEATS):
            folder = vlm_setup.engine_dir() / "models"
            folder.mkdir(parents=True)
            (folder / "a.gguf").write_bytes(b"abcd")
            (folder / "b.gguf").write_bytes(b"abcd")
            result = vlm_setup.uninstall("qwen")
        self.assertTrue(result["ok"])
        self.assertIn("发动机＋权重全删", result["message"])
        self.assertFalse(vlm_setup.engine_dir().exists())
        self.assertEqual(vlm_setup.status("qwen")["state"], "idle")

    def test_uninstall_refuses_while_this_seat_installing(self) -> None:
        fake = mock.Mock()
        fake.is_alive.return_value = True
        vlm_setup._THREAD["minicpm"] = fake
        with self.assertRaises(vlm_setup.VlmSetupError) as caught:
            vlm_setup.uninstall("minicpm")
        self.assertIn("安装中", str(caught.exception))

    def test_uninstall_when_absent_is_honest(self) -> None:
        result = vlm_setup.uninstall("intern")
        self.assertTrue(result["ok"])
        self.assertIn("本来就没装", result["message"])


class WeightsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        patcher = mock.patch.object(vlm_weights.config, "PROJECT_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_download_checksum_mismatch_discards_part(self) -> None:
        with mock.patch.object(vlm_weights.urllib.request, "urlopen",
                               return_value=_FakeResponse([b"abc"])):
            with self.assertRaises(vlm_weights.VlmWeightsError) as caught:
                vlm_weights.download_gguf("qwen", "a.gguf", 3, "0" * 64,
                                          _sources("ModelScope"), lambda _m: None)
        self.assertIn("sha256", str(caught.exception))
        folder = vlm_weights.engine_dir() / "models"
        self.assertFalse((folder / "a.gguf").exists())
        self.assertFalse((folder / "a.gguf.part").exists())

    def test_download_good_checksum_lands_atomically(self) -> None:
        digest = hashlib.sha256(b"abc").hexdigest()
        with mock.patch.object(vlm_weights.urllib.request, "urlopen",
                               return_value=_FakeResponse([b"a", b"bc"])):
            vlm_weights.download_gguf("qwen", "a.gguf", 3, digest,
                                      _sources("ModelScope"), lambda _m: None)
        target = vlm_weights.engine_dir() / "models" / "a.gguf"
        self.assertEqual(target.read_bytes(), b"abc")
        self.assertFalse(target.with_suffix(".gguf.part").exists())

    def test_download_uses_browser_ua_not_script_default(self) -> None:
        digest = hashlib.sha256(b"abc").hexdigest()
        with mock.patch.object(vlm_weights.urllib.request, "urlopen",
                               return_value=_FakeResponse([b"abc"])) as urlopen:
            vlm_weights.download_gguf("qwen", "a.gguf", 3, digest,
                                      _sources("hf-mirror"), lambda _m: None)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), vlm_weights.mirrors.WEIGHT_UA)

    def test_download_interrupted_switches_to_next_source(self) -> None:
        digest = hashlib.sha256(b"abc").hexdigest()
        with mock.patch.object(vlm_weights.urllib.request, "urlopen",
                               side_effect=[OSError("connection reset"),
                                            _FakeResponse([b"abc"])]) as urlopen:
            vlm_weights.download_gguf("qwen", "a.gguf", 3, digest,
                                      _sources("ModelScope", "hf-mirror"), lambda _m: None)
        self.assertEqual(urlopen.call_count, 2)
        target = vlm_weights.engine_dir() / "models" / "a.gguf"
        self.assertEqual(target.read_bytes(), b"abc")

    def test_download_all_sources_fail_is_human_reason(self) -> None:
        with mock.patch.object(vlm_weights.urllib.request, "urlopen",
                               side_effect=OSError("connection refused")):
            with self.assertRaises(vlm_weights.VlmWeightsError) as caught:
                vlm_weights.download_gguf("qwen", "a.gguf", 3, "0" * 64,
                                          _sources("ModelScope", "hf-mirror"),
                                          lambda _m: None)
        self.assertIn("权重下载全败", str(caught.exception))

    def test_prefetch_skips_files_already_present(self) -> None:
        with mock.patch.object(vlm_weights, "SEATS", SMALL_SEATS):
            folder = vlm_weights.engine_dir() / "models"
            folder.mkdir(parents=True)
            (folder / "a.gguf").write_bytes(b"abcd")
            (folder / "b.gguf").write_bytes(b"abcd")
            with mock.patch.object(vlm_weights.mirrors, "race",
                                   return_value=_sources("ModelScope")), \
                    mock.patch.object(vlm_weights.urllib.request, "urlopen") as urlopen:
                self.assertTrue(vlm_weights.prefetch("qwen", lambda **_f: None))
            urlopen.assert_not_called()

    def test_prefetch_no_reachable_source_is_explicit(self) -> None:
        notes: list[str] = []
        with mock.patch.object(vlm_weights.mirrors, "race",
                               return_value=[{"name": "ModelScope", "url": "u",
                                              "ok": False, "ms": 2000}]):
            self.assertFalse(vlm_weights.prefetch(
                "qwen", lambda **fields: notes.append(fields.get("message", ""))))
        self.assertTrue(any("全不通" in note for note in notes))

    def test_prefetch_races_first_file_and_downloads_each(self) -> None:
        digest = hashlib.sha256(b"abcd").hexdigest()
        seats = {"qwen": {"label": "测试", "repo": "t/q", "size_note": "",
                          "files": (("a.gguf", 4, digest), ("b.gguf", 4, digest))}}
        with mock.patch.object(vlm_weights, "SEATS", seats), \
                mock.patch.object(vlm_weights.mirrors, "race",
                                  return_value=_sources("ModelScope")) as race, \
                mock.patch.object(vlm_weights.urllib.request, "urlopen",
                                  side_effect=lambda *_a, **_k: _FakeResponse([b"abcd"])) as urlopen:
            self.assertTrue(vlm_weights.prefetch("qwen", lambda **_f: None))
        raced_urls = race.call_args.args[0]
        self.assertTrue(all("a.gguf" in url for _name, url in raced_urls))
        self.assertEqual(urlopen.call_count, 2)
        folder = vlm_weights.engine_dir() / "models"
        self.assertEqual((folder / "a.gguf").read_bytes(), b"abcd")
        self.assertEqual((folder / "b.gguf").read_bytes(), b"abcd")


if __name__ == "__main__":
    unittest.main()