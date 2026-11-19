"""PP-FormulaNet·M 安装链＋引擎口径＋三态（2.22.0 卡§2/§3/§5）。

不出网：urlopen 与 mirrors.race 全 mock；落地目录指临时目录，不碰真 engines/。
运行：``.venv/Scripts/python.exe -m unittest tests.test_formula_setup``
"""

from __future__ import annotations

import hashlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from app.core.ingest import formula_setup, registry
from app.core.ingest.recognize import formula_pp_m


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="jzo-formula-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        patcher = mock.patch.object(formula_setup, "engine_dir", return_value=self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)
        files = mock.patch.object(formula_setup, "WEIGHT_FILES", (
            ("model", "m.onnx", 16, "0" * 64),
            ("config", "m.yml", 24, "1" * 64)))
        files.start()
        self.addCleanup(files.stop)
        saved = dict(formula_setup._STATE)
        self.addCleanup(lambda: formula_setup._STATE.update(saved))
        formula_setup._STATE.update({"state": "idle", "step": "", "message": ""})

    def _source(self, name: str = "ModelScope") -> list[dict]:
        return [{"name": name, "url": "https://mirror.test/m.onnx", "ok": True, "ms": 12}]

    def test_weights_ready_checks_both_sizes(self) -> None:
        self.assertFalse(formula_setup.weights_ready())
        onnx, yml = formula_setup.model_paths()
        onnx.parent.mkdir(parents=True, exist_ok=True)
        onnx.write_bytes(b"x" * formula_setup.WEIGHT_FILES[0][2])
        self.assertFalse(formula_setup.weights_ready())
        yml.write_bytes(b"x" * formula_setup.WEIGHT_FILES[1][2])
        self.assertTrue(formula_setup.weights_ready())

    def test_download_verifies_sha_and_renames_atomically(self) -> None:
        payload = b"formula-weight-byte"
        digest = hashlib.sha256(payload).hexdigest()
        with mock.patch.object(formula_setup.urllib.request, "urlopen",
                               return_value=_Response(payload)) as opened:
            formula_setup._download_one("model", "tiny.onnx", len(payload), digest,
                                        self._source())
        target = self.tmp / "models" / "tiny.onnx"
        self.assertEqual(target.read_bytes(), payload)
        self.assertFalse(target.with_suffix(".onnx.part").exists())
        self.assertEqual(opened.call_count, 1)

    def test_sha_mismatch_retries_then_switches_and_all_fail_is_loud(self) -> None:
        payload = b"wrong-bytes"
        with mock.patch.object(formula_setup.urllib.request, "urlopen",
                               side_effect=lambda *a, **k: _Response(payload)) as opened:
            with self.assertRaises(formula_setup.FormulaSetupError) as caught:
                formula_setup._download_one("model", "tiny.onnx", len(payload), "0" * 64,
                                            self._source("甲") + self._source("乙"))
        self.assertEqual(opened.call_count, 4)
        self.assertIn("全败", str(caught.exception))
        self.assertIn("实收", str(caught.exception))
        self.assertFalse((self.tmp / "models" / "tiny.onnx").exists())
        self.assertFalse((self.tmp / "models" / "tiny.onnx.part").exists())

    def test_truncated_stream_recovers_on_same_source_retry(self) -> None:
        payload = b"full-weight-bytes"
        digest = hashlib.sha256(payload).hexdigest()
        with mock.patch.object(formula_setup.urllib.request, "urlopen",
                               side_effect=[_Response(b"full-weigh"),
                                            _Response(payload)]) as opened:
            formula_setup._download_one("model", "tiny.onnx", len(payload), digest,
                                        self._source("甲"))
        self.assertEqual(opened.call_count, 2)
        self.assertEqual((self.tmp / "models" / "tiny.onnx").read_bytes(), payload)

    def test_each_file_resolves_its_own_url_not_the_raced_one(self) -> None:
        payload = b"config-yml-bytes"
        digest = hashlib.sha256(payload).hexdigest()
        raced = [{"name": "ModelScope", "url": "https://mirror.test/m.onnx",
                  "ok": True, "ms": 12}]
        with mock.patch.object(formula_setup.urllib.request, "urlopen",
                               return_value=_Response(payload)) as opened:
            formula_setup._download_one("config", "m.yml", len(payload), digest, raced)
        url = opened.call_args[0][0]
        self.assertIn("/PP-FormulaNet_plus-M/m.yml", url)
        self.assertNotIn("m.onnx", url)

    def test_install_races_sources_and_skips_present_files(self) -> None:
        onnx, _yml = formula_setup.model_paths()
        onnx.parent.mkdir(parents=True, exist_ok=True)
        onnx.write_bytes(b"x" * formula_setup.WEIGHT_FILES[0][2])
        raced = [{"name": "ModelScope", "url": "https://mirror.test/m", "ok": True, "ms": 12}]
        with mock.patch.object(formula_setup.mirrors, "race", return_value=raced) as race, \
                mock.patch.object(formula_setup, "_download_one") as download:
            formula_setup._install()
        self.assertEqual(race.call_count, 1)
        self.assertEqual(download.call_count, 1)
        self.assertEqual(download.call_args[0][1], formula_setup.WEIGHT_FILES[1][1])
        self.assertEqual(formula_setup.status()["state"], "done")
        self.assertIn("校验通过", formula_setup.status()["message"])

    def test_all_sources_down_is_explicit_error(self) -> None:
        with mock.patch.object(formula_setup.mirrors, "race",
                               return_value=[{"name": "甲", "url": "u", "ok": False}]):
            formula_setup._install()
        self.assertEqual(formula_setup.status()["state"], "error")
        self.assertIn("全不通", formula_setup.status()["message"])

    def test_start_install_when_ready_does_not_spawn_thread(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=True), \
                mock.patch.object(formula_setup.threading, "Thread") as thread:
            state = formula_setup.start_install()
        self.assertEqual(state["state"], "done")
        thread.assert_not_called()


class UninstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="jzo-formula-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        root = mock.patch.object(formula_setup.config, "PROJECT_ROOT", self.tmp)
        root.start()
        self.addCleanup(root.stop)
        patcher = mock.patch.object(formula_setup, "engine_dir",
                                    return_value=self.tmp / "engines" / "formula")
        patcher.start()
        self.addCleanup(patcher.stop)
        saved = dict(formula_setup._STATE)
        self.addCleanup(lambda: formula_setup._STATE.update(saved))
        formula_setup._STATE.update({"state": "idle", "step": "", "message": ""})

    def test_uninstall_resets_cache_before_deleting(self) -> None:
        folder = self.tmp / "engines" / "formula"
        folder.mkdir(parents=True)
        calls = []
        with mock.patch.object(formula_pp_m, "reset",
                               side_effect=lambda: calls.append(("reset",))), \
                mock.patch.object(formula_setup.shutil, "rmtree",
                                  side_effect=lambda path: calls.append(("rmtree", path))):
            result = formula_setup.uninstall()
        self.assertEqual(calls, [("reset",), ("rmtree", folder)])
        self.assertTrue(result["ok"])

    def test_uninstall_missing_dir_is_noop(self) -> None:
        with mock.patch.object(formula_pp_m, "reset"):
            result = formula_setup.uninstall()
        self.assertTrue(result["ok"])
        self.assertIn("没下", result["message"])

    def test_uninstall_refuses_while_installing(self) -> None:
        alive = mock.Mock()
        alive.is_alive.return_value = True
        with mock.patch.object(formula_setup, "_THREAD", alive):
            with self.assertRaises(formula_setup.FormulaSetupError):
                formula_setup.uninstall()

    def test_uninstall_refuses_wrong_path(self) -> None:
        with mock.patch.object(formula_setup, "engine_dir",
                               return_value=self.tmp / "别处"):
            with self.assertRaises(formula_setup.FormulaSetupError) as caught:
                formula_setup.uninstall()
        self.assertIn("拒绝动手", str(caught.exception))


class EngineTest(unittest.TestCase):
    """引擎口径：未安装显性不偷换；预处理形状；解码 eos/特词/ByteLevel；reset 丢缓存。"""

    def setUp(self) -> None:
        formula_pp_m.reset()
        self.addCleanup(formula_pp_m.reset)

    def test_without_weights_is_loud_not_silent_fallback(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False):
            result = formula_pp_m.recognize(b"fake-png")
        self.assertFalse(result["ok"])
        self.assertIn("未安装", result["detail"])
        self.assertIn("安装", result["detail"])

    def test_empty_png_is_explicit(self) -> None:
        result = formula_pp_m.recognize(b"")
        self.assertFalse(result["ok"])
        self.assertIn("为空", result["detail"])

    def test_preprocess_shape_and_dtype(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (200, 60), "white")
        for x in range(40, 160):
            for y in range(20, 40):
                img.putpixel((x, y), (0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        x = formula_pp_m._preprocess(buf.getvalue())
        self.assertEqual(x.shape, (1, 1, 384, 384))
        self.assertEqual(x.dtype, np.float32)

    def test_preprocess_bad_bytes_returns_none(self) -> None:
        self.assertIsNone(formula_pp_m._preprocess(b"not-an-image"))

    def test_decode_truncates_eos_and_skips_specials(self) -> None:
        dec = {"vocab": {10: "x", 11: "+", 12: "1"}, "special": {0, 1, 2},
               "bytes": formula_pp_m._byte_decoder()}
        with mock.patch.object(formula_pp_m, "_decoder", return_value=dec):
            self.assertEqual(formula_pp_m._decode([10, 11, 12, 2, 10]), "x+1")
            self.assertEqual(formula_pp_m._decode([10, 1, 11, 12]), "x+1")

    def test_decode_bytelevel_multibyte_utf8(self) -> None:
        # 「½」UTF-8 两字节 0xC2 0xBD → ByteLevel 可见字符 Â ½（逆映射拼回）。
        enc = {b: c for c, b in formula_pp_m._byte_decoder().items()}
        token = enc[0xC2] + enc[0xBD]
        dec = {"vocab": {10: token}, "special": {0, 1, 2},
               "bytes": formula_pp_m._byte_decoder()}
        with mock.patch.object(formula_pp_m, "_decoder", return_value=dec):
            self.assertEqual(formula_pp_m._decode([10, 2]), "½")

    def test_chinese_text_wrapping_unwrapped(self) -> None:
        self.assertEqual(formula_pp_m._TEXT_WRAP.sub(r"\1", r"\text{中文}x"), "中文x")

    def test_tidy_compresses_spaces_between_symbols(self) -> None:
        self.assertEqual(formula_pp_m._tidy("x + 1"), "x+1")
        self.assertEqual(formula_pp_m._tidy(r"\mathrm { d }"), r"\mathrm{d}")

    def test_tidy_protects_command_space_inside_text(self) -> None:
        # 命令后空格占位保住（\beta b），其余空格照压——与 paddlex 原口径一致。
        self.assertEqual(formula_pp_m._tidy(r"\text{a \beta b}"), r"\text{a\beta b}")

    def test_reset_drops_engine_and_decoder(self) -> None:
        formula_pp_m._ENGINE = object()
        formula_pp_m._DECODE = {"vocab": {}}
        formula_pp_m.reset()
        self.assertIsNone(formula_pp_m._ENGINE)
        self.assertIsNone(formula_pp_m._DECODE)


class VerdictTest(unittest.TestCase):
    """registry 三态特例（store=formula）：就绪/未装引导安装/安装失败 blocked。"""

    ITEM = {"id": "formula_pp_m", "name": "PP-FormulaNet·M", "rule": "weight_present",
            "store": "formula", "ready_detail": "就绪", "degraded_detail": "未装",
            "install_error_detail": "安装失败：{message}"}

    def test_ready_when_weights_present(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=True), \
                mock.patch.object(formula_setup, "status",
                                  return_value={"state": "idle"}):
            verdict = registry._judge(self.ITEM, {}, [])
        self.assertEqual(verdict["state"], "ready")
        self.assertEqual(verdict["detail"], "就绪")

    def test_degraded_guides_install_when_missing(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False), \
                mock.patch.object(formula_setup, "status",
                                  return_value={"state": "idle"}):
            verdict = registry._judge(self.ITEM, {}, [])
        self.assertEqual(verdict["state"], "degraded")
        self.assertEqual(verdict["action"], "install_formula")

    def test_install_error_is_blocked_with_message(self) -> None:
        with mock.patch.object(formula_setup, "status",
                               return_value={"state": "error", "message": "源全不通"}):
            verdict = registry._judge(self.ITEM, {}, [])
        self.assertEqual(verdict["state"], "blocked")
        self.assertEqual(verdict["action"], "install_formula")
        self.assertIn("源全不通", verdict["detail"])


if __name__ == "__main__":
    unittest.main()