"""公式专科 M/L/p2t 安装链＋引擎口径＋三态（2.22.0 卡＋安装接线卡座2/3）。

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
from app.core.ingest.recognize import formula_p2t, formula_pp_l, formula_pp_m

# 测试用小权重规格（形状与真 VARIANTS 一致：name, size, sha256, repo, rel）。
FAKE_VARIANTS = {
    "m": {"label": "PP-FormulaNet·M", "size_note": "约 1KB", "files": (
        ("m.onnx", 16, "0" * 64, "RapidAI/RapidDoc",
         "formula/PP-FormulaNet_plus-M/m.onnx"),
        ("m.yml", 24, "1" * 64, "RapidAI/RapidDoc",
         "formula/PP-FormulaNet_plus-M/m.yml"))},
    "l": {"label": "PP-FormulaNet·L", "size_note": "约 1KB", "files": (
        ("l.onnx", 16, "2" * 64, "RapidAI/RapidDoc",
         "formula/PP-FormulaNet_plus-L/l.onnx"),
        ("l.yml", 24, "3" * 64, "PaddlePaddle/PP-FormulaNet_plus-L", "inference.yml"))},
    "p2t": {"label": "Pix2Text·MFR", "size_note": "约 1KB", "files": (
        ("p2t_encoder.onnx", 16, "4" * 64, "breezedeus/pix2text-mfr", "encoder_model.onnx"),
        ("p2t_decoder.onnx", 24, "5" * 64, "breezedeus/pix2text-mfr", "decoder_model.onnx"),
        ("p2t_tokenizer.json", 32, "6" * 64, "breezedeus/pix2text-mfr", "tokenizer.json"))},
}


def _reset_state() -> None:
    for variant in formula_setup.VARIANTS:
        formula_setup._STATE[variant] = {"state": "idle", "step": "", "message": ""}
        formula_setup._THREAD[variant] = None


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
        files = mock.patch.object(formula_setup, "VARIANTS", FAKE_VARIANTS)
        files.start()
        self.addCleanup(files.stop)
        saved_state = {v: dict(s) for v, s in formula_setup._STATE.items()}
        saved_thread = dict(formula_setup._THREAD)
        self.addCleanup(lambda: (formula_setup._STATE.update(saved_state),
                                 formula_setup._THREAD.update(saved_thread)))
        _reset_state()

    def _source(self, name: str = "ModelScope") -> list[dict]:
        return [{"name": name, "url": "https://mirror.test/m.onnx", "ok": True, "ms": 12}]

    def _spec(self, name: str, payload: bytes, digest: str | None = None) -> tuple:
        return (name, len(payload), digest or hashlib.sha256(payload).hexdigest(),
                "RapidAI/RapidDoc", "formula/PP-FormulaNet_plus-M/" + name)

    def test_weights_ready_checks_both_sizes(self) -> None:
        self.assertFalse(formula_setup.weights_ready())
        onnx, yml = formula_setup.model_paths()
        onnx.parent.mkdir(parents=True, exist_ok=True)
        onnx.write_bytes(b"x" * FAKE_VARIANTS["m"]["files"][0][1])
        self.assertFalse(formula_setup.weights_ready())
        yml.write_bytes(b"x" * FAKE_VARIANTS["m"]["files"][1][1])
        self.assertTrue(formula_setup.weights_ready())

    def test_weights_ready_l_is_independent_of_m(self) -> None:
        onnx, yml = formula_setup.model_paths("l")
        onnx.parent.mkdir(parents=True, exist_ok=True)
        onnx.write_bytes(b"x" * FAKE_VARIANTS["l"]["files"][0][1])
        yml.write_bytes(b"x" * FAKE_VARIANTS["l"]["files"][1][1])
        self.assertTrue(formula_setup.weights_ready("l"))
        self.assertFalse(formula_setup.weights_ready("m"))

    def test_weights_ready_p2t_needs_all_three_files(self) -> None:
        paths = formula_setup.model_paths("p2t")
        self.assertEqual(len(paths), 3)
        paths[0].parent.mkdir(parents=True, exist_ok=True)
        for idx, (path, spec) in enumerate(zip(paths, FAKE_VARIANTS["p2t"]["files"])):
            path.write_bytes(b"x" * spec[1])
            self.assertEqual(formula_setup.weights_ready("p2t"), idx == 2)
        paths[1].unlink()
        self.assertFalse(formula_setup.weights_ready("p2t"))

    def test_download_verifies_sha_and_renames_atomically(self) -> None:
        payload = b"formula-weight-byte"
        spec = self._spec("tiny.onnx", payload)
        with mock.patch.object(formula_setup.urllib.request, "urlopen",
                               return_value=_Response(payload)) as opened:
            formula_setup._download_one("m", spec, self._source())
        target = self.tmp / "models" / "tiny.onnx"
        self.assertEqual(target.read_bytes(), payload)
        self.assertFalse(target.with_suffix(".onnx.part").exists())
        self.assertEqual(opened.call_count, 1)

    def test_sha_mismatch_retries_then_switches_and_all_fail_is_loud(self) -> None:
        payload = b"wrong-bytes"
        spec = self._spec("tiny.onnx", payload, "0" * 64)
        with mock.patch.object(formula_setup.urllib.request, "urlopen",
                               side_effect=lambda *a, **k: _Response(payload)) as opened:
            with self.assertRaises(formula_setup.FormulaSetupError) as caught:
                formula_setup._download_one("m", spec,
                                            self._source("甲") + self._source("乙"))
        self.assertEqual(opened.call_count, 4)
        self.assertIn("全败", str(caught.exception))
        self.assertIn("实收", str(caught.exception))
        self.assertFalse((self.tmp / "models" / "tiny.onnx").exists())
        self.assertFalse((self.tmp / "models" / "tiny.onnx.part").exists())

    def test_truncated_stream_recovers_on_same_source_retry(self) -> None:
        payload = b"full-weight-bytes"
        spec = self._spec("tiny.onnx", payload)
        with mock.patch.object(formula_setup.urllib.request, "urlopen",
                               side_effect=[_Response(b"full-weigh"),
                                            _Response(payload)]) as opened:
            formula_setup._download_one("m", spec, self._source("甲"))
        self.assertEqual(opened.call_count, 2)
        self.assertEqual((self.tmp / "models" / "tiny.onnx").read_bytes(), payload)

    def test_each_file_resolves_its_own_url_not_the_raced_one(self) -> None:
        payload = b"config-yml-bytes"
        digest = hashlib.sha256(payload).hexdigest()
        raced = [{"name": "ModelScope", "url": "https://mirror.test/m.onnx",
                  "ok": True, "ms": 12}]
        spec = ("m.yml", len(payload), digest, "RapidAI/RapidDoc",
                "formula/PP-FormulaNet_plus-M/m.yml")
        with mock.patch.object(formula_setup.urllib.request, "urlopen",
                               return_value=_Response(payload)) as opened:
            formula_setup._download_one("m", spec, raced)
        url = opened.call_args[0][0]
        self.assertIn("/PP-FormulaNet_plus-M/m.yml", url)
        self.assertNotIn("m.onnx", url)

    def test_l_yml_resolves_official_repo_not_rapiddoc(self) -> None:
        payload = b"l-config-yml-bytes"
        digest = hashlib.sha256(payload).hexdigest()
        raced = [{"name": "ModelScope", "url": "https://mirror.test/l.onnx",
                  "ok": True, "ms": 12}]
        spec = ("l.yml", len(payload), digest, "PaddlePaddle/PP-FormulaNet_plus-L",
                "inference.yml")
        with mock.patch.object(formula_setup.urllib.request, "urlopen",
                               return_value=_Response(payload)) as opened:
            formula_setup._download_one("l", spec, raced)
        url = opened.call_args[0][0]
        self.assertIn("/PaddlePaddle/PP-FormulaNet_plus-L/resolve/master/inference.yml", url)
        self.assertNotIn("RapidDoc", url)

    def test_install_races_sources_and_skips_present_files(self) -> None:
        onnx, _yml = formula_setup.model_paths()
        onnx.parent.mkdir(parents=True, exist_ok=True)
        onnx.write_bytes(b"x" * FAKE_VARIANTS["m"]["files"][0][1])
        raced = [{"name": "ModelScope", "url": "https://mirror.test/m", "ok": True, "ms": 12}]
        with mock.patch.object(formula_setup.mirrors, "race", return_value=raced) as race, \
                mock.patch.object(formula_setup, "_download_one") as download:
            formula_setup._install("m")
        self.assertEqual(race.call_count, 1)
        self.assertEqual(download.call_count, 1)
        self.assertEqual(download.call_args[0][1], FAKE_VARIANTS["m"]["files"][1])
        self.assertEqual(formula_setup.status()["state"], "done")
        self.assertIn("校验通过", formula_setup.status()["message"])

    def test_install_l_keeps_m_state_untouched(self) -> None:
        raced = [{"name": "ModelScope", "url": "https://mirror.test/l", "ok": True, "ms": 12}]
        with mock.patch.object(formula_setup.mirrors, "race", return_value=raced), \
                mock.patch.object(formula_setup, "_download_one"):
            formula_setup._install("l")
        self.assertEqual(formula_setup.status("l")["state"], "done")
        self.assertEqual(formula_setup.status("m")["state"], "idle")

    def test_all_sources_down_is_explicit_error(self) -> None:
        with mock.patch.object(formula_setup.mirrors, "race",
                               return_value=[{"name": "甲", "url": "u", "ok": False}]):
            formula_setup._install("m")
        self.assertEqual(formula_setup.status()["state"], "error")
        self.assertIn("全不通", formula_setup.status()["message"])

    def test_start_install_when_ready_does_not_spawn_thread(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=True), \
                mock.patch.object(formula_setup.threading, "Thread") as thread:
            state = formula_setup.start_install()
        self.assertEqual(state["state"], "done")
        thread.assert_not_called()

    def test_start_install_l_spawns_l_thread_only(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False), \
                mock.patch.object(formula_setup.threading, "Thread") as thread:
            state = formula_setup.start_install("l")
        self.assertEqual(state["state"], "installing")
        self.assertEqual(formula_setup.status("m")["state"], "idle")
        self.assertEqual(thread.call_args.kwargs.get("args"), ("l",))

    def test_start_install_p2t_spawns_p2t_thread_only(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False), \
                mock.patch.object(formula_setup.threading, "Thread") as thread:
            state = formula_setup.start_install("p2t")
        self.assertEqual(state["state"], "installing")
        self.assertEqual(formula_setup.status("m")["state"], "idle")
        self.assertEqual(formula_setup.status("l")["state"], "idle")
        self.assertEqual(thread.call_args.kwargs.get("args"), ("p2t",))

    def test_install_p2t_races_first_file_and_downloads_all_three(self) -> None:
        raced = [{"name": "hf-mirror", "url": "https://mirror.test/enc", "ok": True, "ms": 12}]
        with mock.patch.object(formula_setup.mirrors, "race", return_value=raced) as race, \
                mock.patch.object(formula_setup, "_download_one") as download:
            formula_setup._install("p2t")
        self.assertEqual(race.call_count, 1)
        raced_urls = [url for _name, url in race.call_args[0][0]]
        self.assertTrue(all("breezedeus/pix2text-mfr" in u and "encoder_model.onnx" in u
                            for u in raced_urls))
        self.assertEqual(download.call_count, 3)
        self.assertEqual(formula_setup.status("p2t")["state"], "done")
        self.assertIn("校验通过", formula_setup.status("p2t")["message"])
        self.assertNotIn("两件", formula_setup.status("p2t")["message"])

    def test_unknown_variant_is_loud(self) -> None:
        with self.assertRaises(formula_setup.FormulaSetupError):
            formula_setup.status("xl")


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
        files = mock.patch.object(formula_setup, "VARIANTS", FAKE_VARIANTS)
        files.start()
        self.addCleanup(files.stop)
        saved_state = {v: dict(s) for v, s in formula_setup._STATE.items()}
        saved_thread = dict(formula_setup._THREAD)
        self.addCleanup(lambda: (formula_setup._STATE.update(saved_state),
                                 formula_setup._THREAD.update(saved_thread)))
        _reset_state()

    def _write(self, variant: str) -> tuple[Path, ...]:
        paths = formula_setup.model_paths(variant)
        paths[0].parent.mkdir(parents=True, exist_ok=True)
        for path, spec in zip(paths, FAKE_VARIANTS[variant]["files"]):
            path.write_bytes(b"x" * spec[1])
        return paths

    def test_uninstall_resets_cache_and_removes_folder_when_empty(self) -> None:
        folder = self.tmp / "engines" / "formula"
        self._write("m")
        calls = []
        with mock.patch.object(formula_pp_m, "reset",
                               side_effect=lambda: calls.append("reset")):
            result = formula_setup.uninstall()
        self.assertEqual(calls, ["reset"])
        self.assertTrue(result["ok"])
        self.assertFalse(folder.exists())

    def test_uninstall_l_keeps_m_weights_and_folder(self) -> None:
        folder = self.tmp / "engines" / "formula"
        m_paths = self._write("m")
        l_paths = self._write("l")
        with mock.patch.object(formula_pp_l, "reset") as reset_l, \
                mock.patch.object(formula_pp_m, "reset") as reset_m:
            result = formula_setup.uninstall("l")
        reset_l.assert_called_once()
        reset_m.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertFalse(any(p.exists() for p in l_paths))
        self.assertTrue(all(p.is_file() for p in m_paths))
        self.assertTrue(folder.is_dir())

    def test_uninstall_p2t_keeps_m_and_l_weights(self) -> None:
        folder = self.tmp / "engines" / "formula"
        m_paths = self._write("m")
        l_paths = self._write("l")
        p2t_paths = self._write("p2t")
        with mock.patch.object(formula_p2t, "reset") as reset_p2t, \
                mock.patch.object(formula_pp_m, "reset") as reset_m, \
                mock.patch.object(formula_pp_l, "reset") as reset_l:
            result = formula_setup.uninstall("p2t")
        reset_p2t.assert_called_once()
        reset_m.assert_not_called()
        reset_l.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertFalse(any(p.exists() for p in p2t_paths))
        self.assertTrue(all(p.is_file() for p in m_paths + l_paths))
        self.assertTrue(folder.is_dir())

    def test_uninstall_last_variant_removes_folder(self) -> None:
        folder = self.tmp / "engines" / "formula"
        self._write("p2t")
        with mock.patch.object(formula_p2t, "reset"):
            result = formula_setup.uninstall("p2t")
        self.assertTrue(result["ok"])
        self.assertFalse(folder.exists())

    def test_uninstall_missing_dir_is_noop(self) -> None:
        with mock.patch.object(formula_pp_m, "reset"):
            result = formula_setup.uninstall()
        self.assertTrue(result["ok"])
        self.assertIn("没下", result["message"])

    def test_uninstall_refuses_while_installing(self) -> None:
        alive = mock.Mock()
        alive.is_alive.return_value = True
        with mock.patch.dict(formula_setup._THREAD, {"m": alive}):
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
        formula_pp_l.reset()
        formula_p2t.reset()
        self.addCleanup(formula_pp_m.reset)
        self.addCleanup(formula_pp_l.reset)
        self.addCleanup(formula_p2t.reset)

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

    def test_decode_accepts_external_decoder(self) -> None:
        dec = {"vocab": {10: "x", 11: "+", 12: "1"}, "special": {0, 1, 2},
               "bytes": formula_pp_m._byte_decoder()}
        self.assertEqual(formula_pp_m._decode([10, 11, 12, 2], dec), "x+1")

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

    def test_l_without_weights_is_loud_not_silent_fallback(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False):
            result = formula_pp_l.recognize(b"fake-png")
        self.assertFalse(result["ok"])
        self.assertIn("PP-FormulaNet·L", result["detail"])
        self.assertIn("未安装", result["detail"])

    def test_l_empty_png_is_explicit(self) -> None:
        result = formula_pp_l.recognize(b"")
        self.assertFalse(result["ok"])
        self.assertIn("为空", result["detail"])

    def test_l_preprocess_uses_768(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (200, 60), "white")
        for x in range(40, 160):
            for y in range(20, 40):
                img.putpixel((x, y), (0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        x = formula_pp_m._preprocess(buf.getvalue(), 768)
        self.assertEqual(x.shape, (1, 1, 768, 768))
        self.assertEqual(x.dtype, np.float32)

    def test_l_reset_drops_engine_and_decoder(self) -> None:
        formula_pp_l._ENGINE = object()
        formula_pp_l._DECODE = {"vocab": {}}
        formula_pp_l.reset()
        self.assertIsNone(formula_pp_l._ENGINE)
        self.assertIsNone(formula_pp_l._DECODE)

    def test_p2t_without_weights_is_loud_not_silent_fallback(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False):
            result = formula_p2t.recognize(b"fake-png")
        self.assertFalse(result["ok"])
        self.assertIn("Pix2Text·MFR", result["detail"])
        self.assertIn("未安装", result["detail"])
        self.assertIn("安装", result["detail"])

    def test_p2t_empty_png_is_explicit(self) -> None:
        result = formula_p2t.recognize(b"")
        self.assertFalse(result["ok"])
        self.assertIn("为空", result["detail"])

    def test_p2t_bad_png_is_explicit(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=True), \
                mock.patch.object(formula_p2t, "_sessions", return_value=(None, None)):
            result = formula_p2t.recognize(b"not-an-image")
        self.assertFalse(result["ok"])
        self.assertIn("解码失败", result["detail"])

    def test_p2t_preprocess_shape_dtype_and_deit_norm(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (200, 60), "white")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        x = formula_p2t._preprocess(buf.getvalue())
        self.assertEqual(x.shape, (1, 3, 384, 384))
        self.assertEqual(x.dtype, np.float32)
        # 纯白 255 → (1-0.5)/0.5 = 1.0（DeiT mean/std 0.5 口径）。
        self.assertAlmostEqual(float(x[0, 0, 0, 0]), 1.0, places=5)

    def test_p2t_preprocess_bad_bytes_returns_none(self) -> None:
        self.assertIsNone(formula_p2t._preprocess(b"not-an-image"))

    def test_p2t_decode_skips_specials_and_bytelevel(self) -> None:
        enc = {b: c for c, b in formula_pp_m._byte_decoder().items()}
        tok = {"vocab": {10: "x", 11: "+", 12: "1", 13: enc[0xC2] + enc[0xBD]},
               "special": {0, 1, 2, 3, 4}, "bytes": formula_pp_m._byte_decoder()}
        self.assertEqual(formula_p2t._decode([10, 11, 12, 2], tok), "x+1")
        self.assertEqual(formula_p2t._decode([10, 1, 13], tok), "x½")

    def test_p2t_reset_drops_engine_and_tokenizer(self) -> None:
        formula_p2t._ENGINE = (object(), object())
        formula_p2t._TOK = {"vocab": {}}
        formula_p2t.reset()
        self.assertIsNone(formula_p2t._ENGINE)
        self.assertIsNone(formula_p2t._TOK)


class VerdictTest(unittest.TestCase):
    """registry 三态特例（store=formula/formula_l/formula_p2t）：就绪/未装引导安装/安装失败 blocked。"""

    ITEM_M = {"id": "formula_pp_m", "name": "PP-FormulaNet·M", "rule": "weight_present",
              "store": "formula", "ready_detail": "就绪", "degraded_detail": "未装",
              "install_error_detail": "安装失败：{message}"}
    ITEM_L = {**ITEM_M, "id": "formula_pp_l", "name": "PP-FormulaNet·L",
              "store": "formula_l"}
    ITEM_P2T = {**ITEM_M, "id": "formula_p2t", "name": "Pix2Text·MFR",
                "store": "formula_p2t"}

    def test_ready_when_weights_present(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=True), \
                mock.patch.object(formula_setup, "status",
                                  return_value={"state": "idle"}):
            verdict = registry._judge(self.ITEM_M, {}, [])
        self.assertEqual(verdict["state"], "ready")
        self.assertEqual(verdict["detail"], "就绪")

    def test_degraded_guides_install_when_missing(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False), \
                mock.patch.object(formula_setup, "status",
                                  return_value={"state": "idle"}):
            verdict = registry._judge(self.ITEM_M, {}, [])
        self.assertEqual(verdict["state"], "degraded")
        self.assertEqual(verdict["action"], "install_formula")

    def test_install_error_is_blocked_with_message(self) -> None:
        with mock.patch.object(formula_setup, "status",
                               return_value={"state": "error", "message": "源全不通"}):
            verdict = registry._judge(self.ITEM_M, {}, [])
        self.assertEqual(verdict["state"], "blocked")
        self.assertEqual(verdict["action"], "install_formula")
        self.assertIn("源全不通", verdict["detail"])

    def test_l_degraded_guides_install_formula_l(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False), \
                mock.patch.object(formula_setup, "status",
                                  return_value={"state": "idle"}):
            verdict = registry._judge(self.ITEM_L, {}, [])
        self.assertEqual(verdict["state"], "degraded")
        self.assertEqual(verdict["action"], "install_formula_l")

    def test_l_ready_when_weights_present(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=True), \
                mock.patch.object(formula_setup, "status",
                                  return_value={"state": "idle"}):
            verdict = registry._judge(self.ITEM_L, {}, [])
        self.assertEqual(verdict["state"], "ready")

    def test_l_install_error_is_blocked_with_message(self) -> None:
        with mock.patch.object(formula_setup, "status",
                               return_value={"state": "error", "message": "源全不通"}):
            verdict = registry._judge(self.ITEM_L, {}, [])
        self.assertEqual(verdict["state"], "blocked")
        self.assertEqual(verdict["action"], "install_formula_l")
        self.assertIn("源全不通", verdict["detail"])

    def test_p2t_degraded_guides_install_formula_p2t(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False), \
                mock.patch.object(formula_setup, "status",
                                  return_value={"state": "idle"}):
            verdict = registry._judge(self.ITEM_P2T, {}, [])
        self.assertEqual(verdict["state"], "degraded")
        self.assertEqual(verdict["action"], "install_formula_p2t")

    def test_p2t_ready_when_weights_present(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=True), \
                mock.patch.object(formula_setup, "status",
                                  return_value={"state": "idle"}):
            verdict = registry._judge(self.ITEM_P2T, {}, [])
        self.assertEqual(verdict["state"], "ready")

    def test_p2t_install_error_is_blocked_with_message(self) -> None:
        with mock.patch.object(formula_setup, "status",
                               return_value={"state": "error", "message": "源全不通"}):
            verdict = registry._judge(self.ITEM_P2T, {}, [])
        self.assertEqual(verdict["state"], "blocked")
        self.assertEqual(verdict["action"], "install_formula_p2t")
        self.assertIn("源全不通", verdict["detail"])


if __name__ == "__main__":
    unittest.main()