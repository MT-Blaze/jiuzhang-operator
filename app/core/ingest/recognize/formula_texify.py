"""Texify 公式专科引擎（接线卡④）：公式图 → ONNX CPU fp16 → LaTeX。

社区干净房间接线：donut-swin 编码器＋mbart 解码器（Spedon/texify-fp16-onnx，
cc-by-sa-4.0 权重内容许可，署名＋相同方式共享；底座代码手写，不抄 texify/Surya）。
贪心环每步重喂全序列（use_cache_branch=False＋空 past）：侦查实锤两档 merged 导出
cache 分支 present 接线损坏（自喂必崩），no-cache 分支两档全绿——可以慢不能不稳。
权重住 engines/formula/models/（formula_setup 变体 texify 一键装，hf-mirror 主源）。
预处理按 DonutImageProcessor 口径（resize 420² bilinear＋1/255＋ImageNet mean/std，
侦查实证直缩吐字正确）；解码按 tokenizer.json ByteLevel 口径（vocab 50000，
start=0/eos=2，生成帽取 config decoder.max_position_embeddings=1536；零新依赖，
不装 torch/tokenizers/sentencepiece）。张量名侦查实证：pixel_values →
last_hidden_state [B,196,1024] float16；input_ids＋encoder_hidden_states＋空 past →
logits [B,seq,50000]。未安装＝显性引导去点安装，绝不静默换座；推理失败 ok=False
显性进失败账本。输出过记号标准字典闭集清洗（latex_norm.clean），与云端通道同一写库口径。
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
_ENGINE: tuple[Any, Any, dict[str, Any]] | None = None
_TOK: dict[str, Any] | None = None
_SIZE = 420
_START = 0
_EOS = 2
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def reset() -> None:
    """丢引擎与词表缓存（卸载权重前调用，防会话占着文件）。"""
    global _ENGINE, _TOK
    with _LOCK:
        _ENGINE = None
        _TOK = None


def _sessions() -> tuple[Any, Any, dict[str, Any]]:
    """enc/dec 会话＋dec 喂料规格（空 past 形状/dtype、输出名、生成帽），懒加载。"""
    global _ENGINE
    with _LOCK:
        if _ENGINE is None:
            if not formula_setup.weights_ready("texify"):
                raise RuntimeError("Texify 权重未安装，先在模型配置中心点【安装】")
            import onnxruntime as ort

            enc_path, dec_path, tok_path, cfg_path, prep_path, _gen = \
                formula_setup.model_paths("texify")
            prep = json.loads(prep_path.read_text(encoding="utf-8"))
            size = prep.get("size") or {}
            if (size.get("height"), size.get("width")) != (_SIZE, _SIZE):
                raise RuntimeError("Texify 预处理配置尺寸不是 420×420，与引擎口径不符")
            enc = ort.InferenceSession(str(enc_path), providers=["CPUExecutionProvider"])
            dec = ort.InferenceSession(str(dec_path), providers=["CPUExecutionProvider"])
            past: dict[str, tuple[int, ...]] = {}
            past_dtype = np.float16
            has_branch = False
            for inp in dec.get_inputs():
                if inp.name.startswith("past_key_values."):
                    # 空 past 沿序列维（第 3 维）置 0，其余符号维填 1——侦查实证喂料口径；
                    # no-cache 分支忽略 past，形状只为过 merged 图的输入校验。
                    shape = tuple(0 if i == 2 else (1 if isinstance(d, str) else int(d))
                                  for i, d in enumerate(inp.shape))
                    past[inp.name] = shape
                    if inp.type == "tensor(float)":
                        past_dtype = np.float32
                elif inp.name == "use_cache_branch":
                    has_branch = True
            if not past or not has_branch:
                raise RuntimeError("Texify 解码器不是 merged 导出（缺 past/use_cache_branch 输入）")
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            max_new = int((cfg.get("decoder") or {}).get("max_position_embeddings") or 1536)
            out_names = [o.name for o in dec.get_outputs()]
            if out_names[0] != "logits":
                raise RuntimeError("Texify 解码器首输出不是 logits，与引擎口径不符")
            _ENGINE = (enc, dec, {"past": past, "past_dtype": past_dtype,
                                  "max_new": max_new, "out_names": out_names,
                                  "tok_path": tok_path})
        return _ENGINE


def _tokenizer(tok_path: Any) -> dict[str, Any]:
    """词表自 tokenizer.json（piece→id 反转＋特词表＋ByteLevel 字节逆映射）。"""
    global _TOK
    with _LOCK:
        if _TOK is None:
            doc = json.loads(tok_path.read_text(encoding="utf-8"))
            _TOK = {
                "vocab": {i: piece for piece, i in doc["model"]["vocab"].items()},
                "special": {int(t["id"]) for t in doc.get("added_tokens") or []},
                "bytes": formula_pp_m._byte_decoder(),
            }
        return _TOK


def _preprocess(png: bytes) -> Any:
    """公式图 → [1,3,420,420] float16；RGB→resize bilinear→1/255→ImageNet 归一。"""
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(png)).convert("RGB")
    except Exception:  # noqa: BLE001 - 坏图只影响这一块，显性交空
        return None
    img = img.resize((_SIZE, _SIZE), resample=2)
    arr = np.array(img).astype(np.float32) / 255.0
    arr = (arr - _MEAN) / _STD
    return arr.transpose(2, 0, 1)[np.newaxis, :, :, :].astype(np.float16)


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
        enc, dec, spec = _sessions()
        x = _preprocess(png)
    except Exception as exc:  # noqa: BLE001 - 引擎缺装/起不来只该显性降级
        return {"ok": False, "latex": "", "detail": str(exc)[:300]}
    if x is None:
        return {"ok": False, "latex": "", "detail": "公式图解码失败，无法转写"}
    try:
        hidden = enc.run([enc.get_outputs()[0].name],
                         {enc.get_inputs()[0].name: x})[0]
        empty = {name: np.zeros(shape, dtype=spec["past_dtype"])
                 for name, shape in spec["past"].items()}
        ids = [_START]
        for _ in range(spec["max_new"]):
            feed = {"input_ids": np.array([ids], dtype=np.int64),
                    "encoder_hidden_states": hidden,
                    "use_cache_branch": np.array([False])}
            feed.update(empty)
            logits = dec.run(spec["out_names"], feed)[0]
            nxt = int(logits[0, -1].argmax())
            if nxt == _EOS:
                break
            ids.append(nxt)
        latex = _decode(ids[1:], _tokenizer(spec["tok_path"]))
    except Exception as exc:  # noqa: BLE001 - 单块推理失败显性进失败账本
        logger.warning("Texify 推理失败：%s", exc)
        return {"ok": False, "latex": "",
                "detail": "Texify 推理失败：%s" % str(exc)[:200]}
    if not latex:
        return {"ok": False, "latex": "", "detail": "Texify 没认出公式内容"}
    # texify 训练口径自带 $$…$$ 包裹；专科座契约是裸 LaTeX（pp_m/p2t 同口径），剥外层。
    if latex.startswith("$$") and latex.endswith("$$") and len(latex) > 4:
        latex = latex[2:-2].strip()
    elif latex.startswith("$") and latex.endswith("$") and len(latex) > 2:
        latex = latex[1:-1].strip()
    from app.core.content import latex_norm

    latex = str(latex_norm.clean(latex)["text"]).strip()
    if not latex:
        return {"ok": False, "latex": "", "detail": "公式内容经记号字典清洗后为空"}
    return {"ok": True, "latex": latex, "detail": "Texify 公式已转写"}