"""RapidOCR·准权重安装链（2.20.0 卡§6）：测速选路/sha256 校验/换源/卸载顺序。

不出网：urlopen 与 mirrors.race 全 mock；落地目录指临时目录，不碰真 engines/。
运行：``.venv/Scripts/python.exe -m unittest tests.test_ocr_setup``
"""

from __future__ import annotations

import hashlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core.ingest import ocr_setup


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="jzo-ocr-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        patcher = mock.patch.object(ocr_setup, "engine_dir", return_value=self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)
        # 测试用小额权重清单：字节数逻辑同真件，不真写 139MB。
        files = mock.patch.object(ocr_setup, "WEIGHT_FILES", (
            ("det", "det_medium.onnx", 16, "0" * 64),
            ("rec", "rec_medium.onnx", 24, "1" * 64)))
        files.start()
        self.addCleanup(files.stop)
        saved = dict(ocr_setup._STATE)
        self.addCleanup(lambda: ocr_setup._STATE.update(saved))
        ocr_setup._STATE.update({"state": "idle", "step": "", "message": ""})

    def _source(self, name: str = "ModelScope") -> list[dict]:
        return [{"name": name, "url": "https://mirror.test/model.onnx",
                 "ok": True, "ms": 12}]

    def test_weights_ready_checks_both_sizes(self) -> None:
        self.assertFalse(ocr_setup.weights_ready())
        det, rec = ocr_setup.model_paths()
        det.parent.mkdir(parents=True, exist_ok=True)
        det.write_bytes(b"x" * ocr_setup.WEIGHT_FILES[0][2])
        self.assertFalse(ocr_setup.weights_ready())
        rec.write_bytes(b"x" * ocr_setup.WEIGHT_FILES[1][2])
        self.assertTrue(ocr_setup.weights_ready())

    def test_download_verifies_sha_and_renames_atomically(self) -> None:
        payload = b"medium-weight-bytes"
        digest = hashlib.sha256(payload).hexdigest()
        with mock.patch.object(ocr_setup.urllib.request, "urlopen",
                               return_value=_Response(payload)) as opened:
            ocr_setup._download_one("det", "tiny.onnx", len(payload), digest,
                                    self._source())
        target = self.tmp / "models" / "tiny.onnx"
        self.assertEqual(target.read_bytes(), payload)
        self.assertFalse(target.with_suffix(".onnx.part").exists())
        self.assertEqual(opened.call_count, 1)

    def test_sha_mismatch_switches_source_and_all_fail_is_loud(self) -> None:
        payload = b"wrong-bytes"
        with mock.patch.object(ocr_setup.urllib.request, "urlopen",
                               side_effect=lambda *a, **k: _Response(payload)) as opened:
            with self.assertRaises(ocr_setup.OcrSetupError) as caught:
                ocr_setup._download_one("det", "tiny.onnx", len(payload), "0" * 64,
                                        self._source("甲") + self._source("乙"))
        self.assertEqual(opened.call_count, 2)
        self.assertIn("全败", str(caught.exception))
        self.assertFalse((self.tmp / "models" / "tiny.onnx").exists())
        self.assertFalse((self.tmp / "models" / "tiny.onnx.part").exists())

    def test_install_races_sources_and_skips_present_files(self) -> None:
        det, _rec = ocr_setup.model_paths()
        det.parent.mkdir(parents=True, exist_ok=True)
        det.write_bytes(b"x" * ocr_setup.WEIGHT_FILES[0][2])
        raced = [{"name": "ModelScope", "url": "https://mirror.test/m",
                  "ok": True, "ms": 12}]
        with mock.patch.object(ocr_setup.mirrors, "race", return_value=raced) as race, \
                mock.patch.object(ocr_setup, "_download_one") as download:
            ocr_setup._install()
        self.assertEqual(race.call_count, 1)
        self.assertEqual(download.call_count, 1)
        self.assertEqual(download.call_args[0][1], ocr_setup.WEIGHT_FILES[1][1])
        self.assertEqual(ocr_setup.status()["state"], "done")
        self.assertIn("校验通过", ocr_setup.status()["message"])

    def test_all_sources_down_is_explicit_error(self) -> None:
        with mock.patch.object(ocr_setup.mirrors, "race",
                               return_value=[{"name": "甲", "url": "u", "ok": False}]):
            ocr_setup._install()
        self.assertEqual(ocr_setup.status()["state"], "error")
        self.assertIn("全不通", ocr_setup.status()["message"])

    def test_start_install_when_ready_does_not_spawn_thread(self) -> None:
        with mock.patch.object(ocr_setup, "weights_ready", return_value=True), \
                mock.patch.object(ocr_setup.threading, "Thread") as thread:
            state = ocr_setup.start_install()
        self.assertEqual(state["state"], "done")
        thread.assert_not_called()


class UninstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="jzo-ocr-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        root = mock.patch.object(ocr_setup.config, "PROJECT_ROOT", self.tmp)
        root.start()
        self.addCleanup(root.stop)
        patcher = mock.patch.object(ocr_setup, "engine_dir",
                                    return_value=self.tmp / "engines" / "ocr")
        patcher.start()
        self.addCleanup(patcher.stop)
        saved = dict(ocr_setup._STATE)
        self.addCleanup(lambda: ocr_setup._STATE.update(saved))
        ocr_setup._STATE.update({"state": "idle", "step": "", "message": ""})

    def test_uninstall_resets_cache_before_deleting(self) -> None:
        folder = self.tmp / "engines" / "ocr"
        folder.mkdir(parents=True)
        calls = []
        with mock.patch("app.core.ingest.recognize.ocr.reset",
                        side_effect=lambda tier=None: calls.append(("reset", tier))), \
                mock.patch.object(ocr_setup.shutil, "rmtree",
                                  side_effect=lambda path: calls.append(("rmtree", path))):
            result = ocr_setup.uninstall()
        self.assertEqual(calls, [("reset", "medium"), ("rmtree", folder)])
        self.assertTrue(result["ok"])

    def test_uninstall_missing_dir_is_noop(self) -> None:
        with mock.patch("app.core.ingest.recognize.ocr.reset"):
            result = ocr_setup.uninstall()
        self.assertTrue(result["ok"])
        self.assertIn("没下", result["message"])

    def test_uninstall_refuses_while_installing(self) -> None:
        alive = mock.Mock()
        alive.is_alive.return_value = True
        with mock.patch.object(ocr_setup, "_THREAD", alive):
            with self.assertRaises(ocr_setup.OcrSetupError):
                ocr_setup.uninstall()

    def test_uninstall_refuses_wrong_path(self) -> None:
        with mock.patch.object(ocr_setup, "engine_dir",
                               return_value=self.tmp / "别处"):
            with self.assertRaises(ocr_setup.OcrSetupError) as caught:
                ocr_setup.uninstall()
        self.assertIn("拒绝动手", str(caught.exception))


class TierEngineTest(unittest.TestCase):
    """准档引擎缓存：权重不在显性报错不偷换快档；reset 丢缓存。"""

    def setUp(self) -> None:
        from app.core.ingest.recognize import ocr

        self.ocr = ocr
        ocr.reset()
        self.addCleanup(ocr.reset)

    def test_medium_without_weights_is_loud_not_silent_fallback(self) -> None:
        with mock.patch.object(ocr_setup, "weights_ready", return_value=False):
            result = self.ocr.detect("卷.pdf", b"", [], tier="medium")
        self.assertFalse(result["ok"])
        self.assertEqual(result["engine"], "ocr_medium")
        self.assertIn("准档权重未安装", result["detail"])

    def test_medium_params_point_at_local_weights(self) -> None:
        det, rec = ocr_setup.model_paths()
        built = {}

        def fake_rapidocr(params=None):
            built.update(params or {})
            return object()

        with mock.patch.object(ocr_setup, "weights_ready", return_value=True), \
                mock.patch.dict("sys.modules", {"rapidocr": mock.Mock(
                    RapidOCR=fake_rapidocr)}):
            self.ocr._engine("medium")
        self.assertEqual(built["Det.model_type"], "medium")
        self.assertEqual(built["Rec.model_type"], "medium")
        self.assertEqual(built["Det.model_path"], str(det))
        self.assertEqual(built["Rec.model_path"], str(rec))

    def test_reset_drops_only_named_tier(self) -> None:
        self.ocr._ENGINES.update({"small": object(), "medium": object()})
        self.ocr.reset("medium")
        self.assertIn("small", self.ocr._ENGINES)
        self.assertNotIn("medium", self.ocr._ENGINES)


if __name__ == "__main__":
    unittest.main()