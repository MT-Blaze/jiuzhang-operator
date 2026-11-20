# -*- coding: utf-8 -*-
"""Texify 公式专科引擎口径（接线卡④§5）：mock ort 会话钉死——预处理形状/归一、
no-cache 贪心环（空 past＋全前缀重喂＋use_cache_branch=False）、eos 停、生成帽、
ByteLevel 解码（实物非 metaspace）、$$ 包裹剥外层、坏输出/未安装显性不偷换。
运行：``.venv/Scripts/python.exe -m unittest tests.test_formula_texify``
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

from app.core.ingest import formula_setup
from app.core.ingest.recognize import formula_pp_m, formula_texify

VOCAB = {"x": 10, "+": 11, "1": 12}
SPECIALS = [{"id": 0, "content": "<s>"}, {"id": 1, "content": "<pad>"},
            {"id": 2, "content": "</s>"}]


def _png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (120, 40), "white").save(out, "PNG")
    return out.getvalue()


def _inp(name: str, shape: list, dtype: str = "tensor(float16)") -> types.SimpleNamespace:
    return types.SimpleNamespace(name=name, shape=shape, type=dtype)


def _out(name: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(name=name)


class FakeEnc:
    def __init__(self) -> None:
        self.feeds: list[dict] = []

    def get_inputs(self) -> list:
        return [_inp("pixel_values", [1, 3, 420, 420])]

    def get_outputs(self) -> list:
        return [_out("last_hidden_state")]

    def run(self, names: list, feed: dict) -> list:
        self.feeds.append(feed)
        return [np.zeros((1, 196, 1024), dtype=np.float16)]


class FakeDec:
    """logits 按脚本吐 argmax；past 输入带符号序列维，use_cache_branch 在位。"""

    def __init__(self, script: list[int], vocab_size: int = 50000,
                 past_dtype: str = "tensor(float16)", with_branch: bool = True,
                 first_output: str = "logits") -> None:
        self.script = list(script)
        self.vocab_size = vocab_size
        self.past_dtype = past_dtype
        self.with_branch = with_branch
        self.first_output = first_output
        self.feeds: list[dict] = []
        self.calls = 0

    def get_inputs(self) -> list:
        inputs = [_inp("input_ids", [1, "seq"], "tensor(int64)"),
                  _inp("encoder_hidden_states", [1, 196, 1024])]
        for piece in ("0.decoder.key", "0.decoder.value", "0.encoder.key", "0.encoder.value"):
            inputs.append(_inp("past_key_values." + piece, [1, 16, "past", 64],
                               self.past_dtype))
        if self.with_branch:
            inputs.append(_inp("use_cache_branch", [1], "tensor(bool)"))
        return inputs

    def get_outputs(self) -> list:
        return [_out(self.first_output), _out("present.0.decoder.key")]

    def run(self, names: list, feed: dict) -> list:
        self.feeds.append(feed)
        token = self.script[self.calls] if self.calls < len(self.script) else self.script[-1]
        self.calls += 1
        seq = int(feed["input_ids"].shape[1])
        logits = np.zeros((1, seq, self.vocab_size), dtype=np.float16)
        logits[0, -1, token] = 10.0
        return [logits, np.zeros((1, 16, seq, 64), dtype=np.float16)]


class EngineTest(unittest.TestCase):
    def setUp(self) -> None:
        formula_texify.reset()
        self.addCleanup(formula_texify.reset)
        self.tmp = Path(tempfile.mkdtemp(prefix="jzo-texify-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "tokenizer.json").write_text(
            json.dumps({"model": {"vocab": VOCAB}, "added_tokens": SPECIALS}),
            encoding="utf-8")
        (self.tmp / "config.json").write_text(
            json.dumps({"decoder": {"max_position_embeddings": 1536}}), encoding="utf-8")
        (self.tmp / "preprocessor_config.json").write_text(
            json.dumps({"size": {"height": 420, "width": 420}}), encoding="utf-8")
        (self.tmp / "generation_config.json").write_text("{}", encoding="utf-8")
        paths = tuple(self.tmp / name for name in (
            "enc.onnx", "dec.onnx", "tokenizer.json", "config.json",
            "preprocessor_config.json", "generation_config.json"))
        ready = mock.patch.object(formula_setup, "weights_ready", return_value=True)
        ready.start()
        self.addCleanup(ready.stop)
        model_paths = mock.patch.object(formula_setup, "model_paths", return_value=paths)
        model_paths.start()
        self.addCleanup(model_paths.stop)
        # 清洗走 mock：引擎环口径测试不碰记号字典库；写路口径另有判据。
        clean = mock.patch("app.core.content.latex_norm.clean",
                           side_effect=lambda text, **kw: {"text": str(text)})
        self.clean = clean.start()
        self.addCleanup(clean.stop)

    def _sessions(self, dec: FakeDec, enc: FakeEnc | None = None) -> mock._patch:
        enc = enc or FakeEnc()
        self.enc = enc
        return mock.patch("onnxruntime.InferenceSession", side_effect=[enc, dec])

    def test_preprocess_shape_dtype_and_imagenet_norm(self) -> None:
        x = formula_texify._preprocess(_png())
        self.assertEqual(x.shape, (1, 3, 420, 420))
        self.assertEqual(x.dtype, np.float16)
        # 纯白 255 → (1-0.485)/0.229（ImageNet 口径，fp16 容差）。
        self.assertAlmostEqual(float(x[0, 0, 0, 0]), (1 - 0.485) / 0.229, places=2)
        self.assertAlmostEqual(float(x[0, 1, 0, 0]), (1 - 0.456) / 0.224, places=2)

    def test_preprocess_bad_bytes_returns_none(self) -> None:
        self.assertIsNone(formula_texify._preprocess(b"not-an-image"))

    def test_preprocess_thumbnail_preserves_aspect_and_pads_zero(self) -> None:
        # 120×40 白图 → 长边 420 保比例 → 420×140 内容左上、余区归一后补 0。
        x = formula_texify._preprocess(_png())
        self.assertAlmostEqual(float(x[0, 0, 139, 0]), (1 - 0.485) / 0.229, places=2)
        self.assertEqual(float(x[0, 0, 140, 0]), 0.0)
        self.assertEqual(float(x[0, 2, 419, 419]), 0.0)

    def test_decode_bytelevel_specials_and_space_piece(self) -> None:
        enc = {b: c for c, b in formula_pp_m._byte_decoder().items()}
        tok = {"vocab": {10: "x", 11: "+", 12: "1", 13: enc[0x20] + "x",
                         14: enc[0xC2] + enc[0xBD]},
               "special": {0, 1, 2}, "bytes": formula_pp_m._byte_decoder()}
        self.assertEqual(formula_texify._decode([10, 11, 12, 2], tok), "x+1")
        self.assertEqual(formula_texify._decode([10, 1, 13], tok), "x x")
        self.assertEqual(formula_texify._decode([10, 14], tok), "x½")

    def test_greedy_loop_refeeds_full_prefix_with_empty_past(self) -> None:
        dec = FakeDec([10, 11, 12, 2])
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertTrue(out["ok"])
        self.assertEqual(out["latex"], "x+1")
        self.assertEqual(len(self.enc.feeds), 1, "编码器只跑一次")
        self.assertEqual(dec.calls, 4, "三 token＋eos 判停一步")
        prefixes = [feed["input_ids"].tolist()[0] for feed in dec.feeds]
        self.assertEqual(prefixes, [[0], [0, 10], [0, 10, 11], [0, 10, 11, 12]])
        for feed in dec.feeds:
            self.assertEqual(feed["use_cache_branch"].tolist(), [False])
            for name, value in feed.items():
                if name.startswith("past_key_values."):
                    self.assertEqual(value.shape[2], 0, "空 past 序列维置 0")
                    self.assertEqual(value.dtype, np.float16)

    def test_eos_first_step_is_explicit_empty(self) -> None:
        dec = FakeDec([2])
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertFalse(out["ok"])
        self.assertIn("没认出公式内容", out["detail"])
        self.assertEqual(dec.calls, 1)

    def test_max_new_cap_no_eos_is_explicit_failure(self) -> None:
        (self.tmp / "config.json").write_text(
            json.dumps({"decoder": {"max_position_embeddings": 5}}), encoding="utf-8")
        dec = FakeDec([10])
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertEqual(dec.calls, 5, "生成帽取 config 位置天花板与预算的较小者")
        self.assertFalse(out["ok"], "达帽未收敛绝不把漫环输出当成功")
        self.assertIn("未收敛", out["detail"])

    def test_generation_budget_capped_at_256(self) -> None:
        (self.tmp / "config.json").write_text(
            json.dumps({"decoder": {"max_position_embeddings": 1536}}), encoding="utf-8")
        dec = FakeDec([10])
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertEqual(dec.calls, 256, "1536 是位置天花板，生成预算 256 防漫环挂死")
        self.assertFalse(out["ok"])
        self.assertIn("256", out["detail"])

    def test_dollar_wrapper_is_stripped_to_bare_latex(self) -> None:
        (self.tmp / "tokenizer.json").write_text(
            json.dumps({"model": {"vocab": {"$$x": 10, "+1$$": 11}},
                        "added_tokens": SPECIALS}), encoding="utf-8")
        dec = FakeDec([10, 11, 2])
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertTrue(out["ok"])
        self.assertEqual(out["latex"], "x+1")
        self.clean.assert_called_once()

    def test_float32_past_dtype_follows_session_inputs(self) -> None:
        dec = FakeDec([10, 2], past_dtype="tensor(float)")
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertTrue(out["ok"])
        for name, value in dec.feeds[0].items():
            if name.startswith("past_key_values."):
                self.assertEqual(value.dtype, np.float32)

    def test_uninstalled_is_loud_not_silent_fallback(self) -> None:
        with mock.patch.object(formula_setup, "weights_ready", return_value=False):
            out = formula_texify.recognize(_png())
        self.assertFalse(out["ok"])
        self.assertIn("Texify", out["detail"])
        self.assertIn("未安装", out["detail"])
        self.assertIn("安装", out["detail"])

    def test_empty_png_is_explicit(self) -> None:
        out = formula_texify.recognize(b"")
        self.assertFalse(out["ok"])
        self.assertIn("为空", out["detail"])

    def test_bad_png_is_explicit(self) -> None:
        dec = FakeDec([10, 2])
        with self._sessions(dec):
            out = formula_texify.recognize(b"not-an-image")
        self.assertFalse(out["ok"])
        self.assertIn("解码失败", out["detail"])
        self.assertEqual(dec.calls, 0)

    def test_inference_exception_is_explicit(self) -> None:
        dec = FakeDec([10, 2])
        dec.run = mock.Mock(side_effect=RuntimeError("会话崩了"))
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertFalse(out["ok"])
        self.assertIn("Texify 推理失败", out["detail"])
        self.assertIn("会话崩了", out["detail"])

    def test_preprocessor_size_mismatch_is_loud(self) -> None:
        (self.tmp / "preprocessor_config.json").write_text(
            json.dumps({"size": {"height": 384, "width": 384}}), encoding="utf-8")
        dec = FakeDec([10, 2])
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertFalse(out["ok"])
        self.assertIn("420", out["detail"])

    def test_non_merged_decoder_is_loud(self) -> None:
        dec = FakeDec([10, 2], with_branch=False)
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertFalse(out["ok"])
        self.assertIn("merged", out["detail"])

    def test_first_output_not_logits_is_loud(self) -> None:
        dec = FakeDec([10, 2], first_output="present.0.decoder.key")
        with self._sessions(dec):
            out = formula_texify.recognize(_png())
        self.assertFalse(out["ok"])
        self.assertIn("logits", out["detail"])

    def test_reset_drops_engine_and_tokenizer(self) -> None:
        formula_texify._ENGINE = (object(), object(), {})
        formula_texify._TOK = {"vocab": {}}
        formula_texify.reset()
        self.assertIsNone(formula_texify._ENGINE)
        self.assertIsNone(formula_texify._TOK)


if __name__ == "__main__":
    unittest.main()