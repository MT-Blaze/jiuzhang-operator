"""Pix2Text·MFR 公式专科引擎（安装接线卡座3）：公式图 → ONNX CPU → LaTeX。

TrOCR 系官方 ONNX（encoder DeiT 384＋decoder 无 KV cache，贪心环每步重喂全序列）；
权重住 engines/formula/models/（formula_setup 变体 p2t 一键装，hf-mirror 主源）。
预处理按官方 DeiTImageProcessor 口径（resize 384 bicubic＋1/255＋mean/std 0.5），
解码按 tokenizer.json ByteLevel 口径（vocab 1200，start/eos=2，max_new_tokens 512；
干净房间手写，不装依赖 torch 的 pix2text 库）。张量名侦查实证：pixel_values →
last_hidden_state [B,578,384]；input_ids＋encoder_hidden_states → logits [B,seq,1200]。
未安装＝显性引导去点安装，绝不静默换座；推理失败 ok=False 显性进失败账本。
输出过记号标准字典闭集清洗（latex_norm.clean），与云端通道同一写库口径。
"""

from __future__ import annotations

import io
import json
import logging
import threading
from typing import Any

import numpy as np

from app.core.ingest import formula_setup
from app.core.ingest.recognize import formula_pp_m

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ENGINE: tuple[Any, Any] | None = None
_TOK: dict[str, Any] | None = None
_SIZE = 384
_START_EOS = 2
_MAX_NEW = 512


def reset() -> None:
    """丢引擎与词表缓存（卸载权重前调用，防会话占着文件）。"""
    global _ENGINE, _TOK
    with _LOCK:
        _ENGINE = None
        _TOK = None


def _sessions() -> tuple[Any, Any]:
    global _ENGINE
    with _LOCK:
        if _ENGINE is None:
            if not formula_setup.weights_ready("p2t"):
                raise RuntimeError("Pix2Text·MFR 权重未安装，先在模型配置中心点【安装】")
            import onnxruntime as ort

            enc_path, dec_path, _tok = formula_setup.model_paths("p2t")
            _ENGINE = (
                ort.InferenceSession(str(enc_path), providers=["CPUExecutionProvider"]),
                ort.InferenceSession(str(dec_path), providers=["CPUExecutionProvider"]),
            )
        return _ENGINE


def _tokenizer() -> dict[str, Any]:
    """词表自 tokenizer.json（piece→id 反转＋特词表＋ByteLevel 字节逆映射）。"""
    global _TOK
    with _LOCK:
        if _TOK is None:
            _enc, _dec, tok_path = formula_setup.model_paths("p2t")
            doc = json.loads(tok_path.read_text(encoding="utf-8"))
            _TOK = {
                "vocab": {i: piece for piece, i in doc["model"]["vocab"].items()},
                "special": {int(t["id"]) for t in doc.get("added_tokens") or []},
                "bytes": formula_pp_m._byte_decoder(),
            }
        return _TOK


def _preprocess(png: bytes) -> Any:
    """公式图 → [1,3,384,384] float32；RGB→resize bicubic→1/255→mean/std 0.5。"""
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(png)).convert("RGB")
    except Exception:  # noqa: BLE001 - 坏图只影响这一块，显性交空
        return None
    img = img.resize((_SIZE, _SIZE), resample=3)
    arr = np.array(img).astype(np.float32) / 255.0
    arr = (arr - 0.5) / 0.5
    return arr.transpose(2, 0, 1)[np.newaxis, :, :, :]


def _decode(ids: list[int], tok: dict[str, Any]) -> str:
    """token ids → LaTeX：特词跳过→ByteLevel 拼字节→utf-8 解码。"""
    raw = bytearray()
    for i in ids:
        if i in tok["special"]:
            continue
        piece = tok["vocab"].get(i)
        if piece is None:
            continue
        for ch in piece:
            b = tok["bytes"].get(ch)
            if b is not None:
                raw.append(b)
    return raw.decode("utf-8", errors="replace").strip()


def recognize(png: bytes) -> dict[str, Any]:
    """一块公式图 → {"ok", "latex", "detail"}；未安装/坏图/推理失败全显性。"""
    if not png:
        return {"ok": False, "latex": "", "detail": "公式图为空，无法转写"}
    try:
        enc, dec = _sessions()
        x = _preprocess(png)
    except Exception as exc:  # noqa: BLE001 - 引擎缺装/起不来只该显性降级
        return {"ok": False, "latex": "", "detail": str(exc)[:300]}
    if x is None:
        return {"ok": False, "latex": "", "detail": "公式图解码失败，无法转写"}
    try:
        hidden = enc.run([enc.get_outputs()[0].name],
                         {enc.get_inputs()[0].name: x})[0]
        ids = [_START_EOS]
        for _ in range(_MAX_NEW):
            logits = dec.run([dec.get_outputs()[0].name],
                             {"input_ids": np.array([ids], dtype=np.int64),
                              "encoder_hidden_states": hidden})[0]
            nxt = int(logits[0, -1].argmax())
            if nxt == _START_EOS:
                break
            ids.append(nxt)
        latex = _decode(ids[1:], _tokenizer())
    except Exception as exc:  # noqa: BLE001 - 单块推理失败显性进失败账本
        logger.warning("Pix2Text·MFR 推理失败：%s", exc)
        return {"ok": False, "latex": "",
                "detail": "Pix2Text·MFR 推理失败：%s" % str(exc)[:200]}
    if not latex:
        return {"ok": False, "latex": "", "detail": "Pix2Text·MFR 没认出公式内容"}
    from app.core.content import latex_norm

    latex = str(latex_norm.clean(latex)["text"]).strip()
    if not latex:
        return {"ok": False, "latex": "", "detail": "公式内容经记号字典清洗后为空"}
    return {"ok": True, "latex": latex, "detail": "Pix2Text·MFR 公式已转写"}