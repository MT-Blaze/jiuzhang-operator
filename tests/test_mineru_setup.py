"""MinerU 本地一键装（四合一卡 §1）：隔离 venv、国内镜像、体检不缓存、失败显性化。

全部 subprocess 打桩，绝不出网、绝不真装。
运行：``.venv/Scripts/python.exe -m unittest tests.test_mineru_setup``
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core import config
from app.core.ingest import mineru_setup as setup


class LayoutTest(unittest.TestCase):
    def test_engine_dir_is_isolated_from_base_venv(self) -> None:
        folder = setup.engine_dir()
        self.assertEqual(folder, config.PROJECT_ROOT / "engines" / "mineru")
        self.assertNotIn(".venv", folder.parts)

    def test_package_and_mirrors_are_pinned_domestic(self) -> None:
        self.assertEqual(setup.PACKAGE_SPEC, "mineru==4.2.3")
        names = [name for name, _url in setup.mirrors.PIP_MIRRORS]
        self.assertEqual(len(names), 4)
        joined = " ".join(url for _name, url in setup.mirrors.PIP_MIRRORS)
        self.assertIn("tsinghua", joined)
        self.assertIn("aliyun", joined)
        self.assertIn("tencent", joined)
        self.assertIn("ustc", joined)
        self.assertNotIn("pypi.org", joined)
        self.assertNotIn("github", joined.lower())


class HealthTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        patcher = mock.patch.object(setup, "python_exe",
                                    return_value=self.root / "python.exe")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_missing_env_is_missing_not_error(self) -> None:
        check = setup.health()
        self.assertFalse(check["ok"])
        self.assertEqual(check["state"], "missing")

    def test_import_probe_reads_version(self) -> None:
        (self.root / "python.exe").write_bytes(b"stub")
        with mock.patch.object(setup, "_run",
                               return_value=(0, "MINERU_VERSION=4.2.3\n")):
            check = setup.health()
        self.assertTrue(check["ok"])
        self.assertEqual(check["version"], "4.2.3")

    def test_broken_env_is_error_with_human_reason(self) -> None:
        (self.root / "python.exe").write_bytes(b"stub")
        with mock.patch.object(setup, "_run",
                               return_value=(1, "ImportError: DLL load failed")):
            check = setup.health()
        self.assertFalse(check["ok"])
        self.assertEqual(check["state"], "error")
        self.assertIn("体检失败", check["message"])

    def test_health_recomputed_every_call(self) -> None:
        (self.root / "python.exe").write_bytes(b"stub")
        with mock.patch.object(setup, "_run",
                               side_effect=[(1, "boom"), (0, "MINERU_VERSION=4.2.3\n")]) as run:
            first = setup.health()["ok"]
            second = setup.health()["ok"]
        self.assertEqual((first, second), (False, True))
        self.assertEqual(run.call_count, 2)

    def test_weights_ready_parses_readonly_probe(self) -> None:
        (self.root / "python.exe").write_bytes(b"stub")
        for rc, text, expected in ((0, "WEIGHTS_MISSING=\n", True),
                                   (0, "WEIGHTS_MISSING=repoA,repoB\n", False),
                                   (1, "boom", False)):
            with mock.patch.object(setup, "_run", return_value=(rc, text)):
                self.assertEqual(setup.weights_ready(), expected)

    def test_weights_missing_when_no_env(self) -> None:
        self.assertFalse(setup.weights_ready())


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        for name, value in (("engine_dir", self.root),
                            ("python_exe", self.root / "Scripts" / "python.exe")):
            patcher = mock.patch.object(setup, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        setup._STATE.update({"state": "idle", "step": "", "message": ""})
        setup._THREAD = None
        self.addCleanup(setup._STATE.update,
                        {"state": "idle", "step": "", "message": ""})
        patcher = mock.patch.object(
            setup.mirrors, "race",
            return_value=[{"name": "阿里云", "url": "https://aliyun.test/simple/mineru/",
                           "ok": True, "ms": 90},
                          {"name": "清华", "url": "https://tsinghua.test/simple/mineru/",
                           "ok": True, "ms": 150}])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _materialize(self) -> None:
        py = setup.python_exe()
        py.parent.mkdir(parents=True, exist_ok=True)
        py.write_bytes(b"stub")

    def _fake_run(self, venv=(0, ""), pips=None, health=(0, "MINERU_VERSION=4.2.3\n")):
        pips = list(pips if pips is not None else [(0, "ok")])

        def run(cmd, timeout):
            if cmd[1:3] == ["-m", "venv"]:
                if venv[0] == 0:
                    self._materialize()
                return venv
            if cmd[1:3] == ["-m", "pip"]:
                return pips.pop(0)
            return health
        return run

    def test_fresh_install_creates_venv_then_pip_then_health(self) -> None:
        calls = []

        def run(cmd, timeout):
            calls.append(cmd)
            if cmd[1:3] == ["-m", "venv"]:
                self._materialize()
                return 0, ""
            if cmd[1:3] == ["-m", "pip"]:
                self.assertIn("--index-url", cmd)
                return 0, "ok"
            return 0, "MINERU_VERSION=4.2.3\n"

        with mock.patch.object(setup, "_run", side_effect=run):
            setup._install()
        self.assertEqual(setup.status()["state"], "done")
        self.assertIn("4.2.3", setup.status()["message"])
        self.assertEqual(calls[0][1:3], ["-m", "venv"])
        self.assertEqual(calls[1][1:3], ["-m", "pip"])
        self.assertIn(setup.PACKAGE_SPEC, calls[1])

    def test_mirror_failure_falls_to_next_mirror(self) -> None:
        pips = [(1, "ConnectionError: max retries exceeded"), (0, "ok")]
        with mock.patch.object(setup, "_run",
                               side_effect=self._fake_run(pips=pips)):
            setup._install()
        self.assertEqual(setup.status()["state"], "done")

    def test_all_mirrors_fail_is_error_with_reason(self) -> None:
        pips = [(1, "timed out"), (1, "NO MATCHING DISTRIBUTION")]
        with mock.patch.object(setup, "_run",
                               side_effect=self._fake_run(pips=pips)):
            setup._install()
        state = setup.status()
        self.assertEqual(state["state"], "error")
        self.assertIn("全部镜像失败", state["message"])

    def test_venv_failure_stops_before_pip(self) -> None:
        with mock.patch.object(setup, "_run",
                               side_effect=self._fake_run(venv=(1, "disk full"))) as run:
            setup._install()
        self.assertEqual(setup.status()["state"], "error")
        self.assertIn("隔离环境创建失败", setup.status()["message"])
        self.assertEqual(run.call_count, 1)

    def test_post_install_health_failure_is_error(self) -> None:
        with mock.patch.object(setup, "_run",
                               side_effect=self._fake_run(health=(1, "DLL load failed"))):
            setup._install()
        self.assertEqual(setup.status()["state"], "error")
        self.assertIn("体检失败", setup.status()["message"])

    def _prefetch_run(self, calls, download, weights="WEIGHTS_MISSING=\n"):
        def run(cmd, timeout):
            calls.append(cmd)
            if cmd[1:3] == ["-m", "venv"]:
                self._materialize()
                return 0, ""
            if cmd[1:3] == ["-m", "pip"]:
                return 0, "ok"
            if cmd[0] == str(setup._models_download_exe()):
                return download
            if cmd[1] == "-c" and setup._WEIGHT_CHECK_CODE in cmd:
                return 0, weights
            return 0, "MINERU_VERSION=4.2.3\n"
        return run

    def test_install_prefetches_weights_in_same_click(self) -> None:
        calls = []
        with mock.patch.object(setup, "_run",
                               side_effect=self._prefetch_run(calls, (0, "ok"))):
            setup._install()
        state = setup.status()
        self.assertEqual(state["state"], "done")
        self.assertIn("解析模型已预取", state["message"])
        download = [cmd for cmd in calls
                    if cmd[0] == str(setup._models_download_exe())]
        self.assertEqual(len(download), 1)
        self.assertIn("modelscope", download[0])
        self.assertIn("standard", download[0])

    def test_prefetch_failure_is_done_with_lazy_download_note(self) -> None:
        calls = []
        with mock.patch.object(setup, "_run",
                               side_effect=self._prefetch_run(calls, (1, "timed out"))):
            setup._install()
        state = setup.status()
        self.assertEqual(state["state"], "done")
        self.assertIn("首次解析时会再试下载", state["message"])

    def test_start_install_short_circuits_when_ready(self) -> None:
        ready = {"ok": True, "state": "ready", "version": "4.2.3", "message": ""}
        with mock.patch.object(setup, "health", return_value=ready), \
                mock.patch.object(setup, "weights_ready", return_value=True), \
                mock.patch.object(setup.threading, "Thread") as thread:
            state = setup.start_install()
        self.assertEqual(state["state"], "done")
        thread.assert_not_called()

    def test_start_install_prefetches_when_weights_missing(self) -> None:
        ready = {"ok": True, "state": "ready", "version": "4.2.3", "message": ""}
        with mock.patch.object(setup, "health", return_value=ready), \
                mock.patch.object(setup, "weights_ready", return_value=False), \
                mock.patch.object(setup.threading, "Thread") as thread:
            state = setup.start_install()
        self.assertEqual(state["state"], "installing")
        self.assertEqual(state["step"], "预取模型")
        thread.assert_called_once()
        self.addCleanup(setattr, setup, "_THREAD", None)

    def test_start_install_rejects_old_python(self) -> None:
        with mock.patch.object(setup.sys, "version_info", (3, 10, 0)):
            with self.assertRaises(setup.MineruSetupError) as caught:
                setup.start_install()
        self.assertIn("3.11", str(caught.exception))

    def test_start_install_reuses_running_thread(self) -> None:
        missing = {"ok": False, "state": "missing", "version": "", "message": ""}
        alive = mock.Mock()
        alive.is_alive.return_value = True
        setup._THREAD = alive
        setup._STATE.update({"state": "installing", "step": "安装依赖", "message": "进行中"})
        with mock.patch.object(setup, "health", return_value=missing), \
                mock.patch.object(setup.threading, "Thread") as thread:
            state = setup.start_install()
        self.assertEqual(state["state"], "installing")
        thread.assert_not_called()
        self.addCleanup(setattr, setup, "_THREAD", None)


if __name__ == "__main__":
    unittest.main()