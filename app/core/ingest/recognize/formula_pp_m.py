"""PP-FormulaNet·M 公式专科引擎（2.22.0 卡§3）：公式图 → ONNX CPU → LaTeX。

权重住 engines/formula/models/（formula_setup 一键装，国内镜像）；底座现成
onnxruntime 直跑，零新依赖。预处理/解码按 paddlex 3.7.2 UniMERNet 口径原创实现
（侦查证据 docs/handoff/evidence/pp-m-recon/，干净房间：只读算法口径不抄代码）。
未安装＝显性引导去点安装，绝不静默换座；推理失败 ok=False 显性进失败账本。
输出过记号标准字典闭集清洗（latex_norm.clean），与云端通道同一写库口径。
"""

from __future__ import annotations

import io
import logging
import re
import threading
from typing import Any

import numpy as np

from app.core.ingest import formula_setup

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ENGINE: Any = None
_DECODE: dict[str, Any] | None = None
_SIZE = 384
_MEAN = 0.7931
_STD = 0.1738
_EOS = 2
_TEXT_WRAP = re.compile(r"\\text\s*{([^{}]*[\u4e00-\u9fff]+[^{}]*)}")
_TEXT_REG = r"(\\(operatorname|mathrm|text|mathbf)\s?\*? {.*?})"
_CMD_SPACE = re.compile(r"(\\[a-zA-Z]+)\s(?=\w)|\\[a-zA-Z]+\s(?=})")
_PROTECTED = ("\\operatorname", "\\mathrm", "\\text", "\\mathbf")


def reset() -> None:
    """丢引擎与词表缓存（卸载权重前调用，防会话占着文件）。"""
    global _ENGINE, _DECODE
    with _LOCK:
        _ENGINE = None
        _DECODE = None


def _session() -> Any:
    global _ENGINE
    with _LOCK:
        if _ENGINE is None:
            if not formula_setup.weights_ready():
                raise RuntimeError("PP-FormulaNet·M 权重未安装，先在模型配置中心点【安装】")
            import onnxruntime as ort

            onnx, _yml = formula_setup.model_paths()
            _ENGINE = ort.InferenceSession(str(onnx), providers=["CPUExecutionProvider"])
        return _ENGINE


def _byte_decoder() -> dict[str, int]:
    """GPT-2 ByteLevel 字节↔可见字符逆映射（解码用）。"""
    bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


def _build_decoder(yml: Any) -> dict[str, Any]:
    """自 yml 内嵌 tokenizer 建解码表（M/L 词表同源，纯函数供兄弟引擎复用）。"""
    import yaml

    cfg = yaml.safe_load(yml.read_text(encoding="utf-8"))
    tok = cfg["PostProcess"]["character_dict"]["fast_tokenizer_file"]
    return {
        "vocab": {i: t for t, i in tok["model"]["vocab"].items()},
        "special": {t["id"] for t in tok["added_tokens"]},
        "bytes": _byte_decoder(),
    }


def _decoder() -> dict[str, Any]:
    """词表自 yml 内嵌 tokenizer（无需另下词表）；懒加载随引擎缓存同丢。"""
    global _DECODE
    with _LOCK:
        if _DECODE is None:
            _onnx, yml = formula_setup.model_paths()
            _DECODE = _build_decoder(yml)
        return _DECODE


def _crop_margin(img: Any) -> Any:
    """灰度 min-max 拉伸→阈值取墨迹→裁边（UniMERNet crop_margin 口径）。"""
    import cv2

    data = np.array(img.convert("L")).astype(np.uint8)
    mx, mn = int(data.max()), int(data.min())
    if mx == mn:
        return img
    stretched = (data - mn) / (mx - mn) * 255
    ink = 255 * (stretched < 200).astype(np.uint8)
    coords = cv2.findNonZero(ink)
    if coords is None:
        return img
    x, y, w, h = cv2.boundingRect(coords)
    return img.crop((x, y, x + w, y + h))


def _preprocess(png: bytes, size: int = _SIZE) -> Any:
    """公式图 → [1,1,size,size] float32；裁边→短边size→只缩→居中补黑→归一化。"""
    from PIL import Image, ImageOps

    try:
        img = Image.open(io.BytesIO(png)).convert("RGB")
    except Exception:  # noqa: BLE001 - 坏图只影响这一块，显性交空
        return None
    img = _crop_margin(img)
    if img.width == 0 or img.height == 0:
        return None
    w, h = img.size
    nw, nh = (size, int(size * h / w)) if w <= h else (int(size * w / h), size)
    img = img.resize((nw, nh), resample=2)
    img.thumbnail((size, size))
    dw, dh = size - img.width, size - img.height
    pad = (dw // 2, dh // 2, dw - dw // 2, dh - dh // 2)
    arr = np.array(ImageOps.expand(img, pad)).astype(np.float32)
    arr = (arr / 255.0 - _MEAN) / _STD
    return arr[:, :, 0][np.newaxis, np.newaxis, :, :]


def _tidy(s: str) -> str:
    """空白压缩（三条规则迭代至稳定）；\\operatorname 等保护词内空格先占位。"""
    names: list[str] = []
    for x in re.findall(_TEXT_REG, s):
        for m in _CMD_SPACE.findall(x[0]):
            if m not in _PROTECTED and m.strip():
                s = s.replace(m, m + "XXXXXXX").replace(" ", "")
                names.append(s)
    if names:
        s = re.sub(_TEXT_REG, lambda m: names.pop(0) if names else m.group(0), s)
    noletter, letter = r"[\W_^\d]", r"[a-zA-Z]"
    rules = (r"(?!\\ )(%s)\s+?(%s)" % (noletter, noletter),
             r"(?!\\ )(%s)\s+?(%s)" % (noletter, letter),
             r"(%s)\s+?(%s)" % (letter, noletter))
    while True:
        news = s
        for rule in rules:
            news = re.sub(rule, r"\1\2", news)
        if news == s:
            break
        s = news
    return s.replace("XXXXXXX", " ")


def _decode(ids: Any, dec: dict[str, Any] | None = None) -> str:
    """token ids → LaTeX：eos 截断→特词跳过→ByteLevel 拼字节→中文解包→空白压缩。"""
    dec = dec if dec is not None else _decoder()
    seq = [int(i) for i in np.array(ids).reshape(-1)]
    if _EOS in seq:
        seq = seq[:seq.index(_EOS)]
    raw = bytearray()
    for i in seq:
        if i in dec["special"]:
            continue
        token = dec["vocab"].get(i)
        if token is None:
            continue
        for ch in token:
            b = dec["bytes"].get(ch)
            if b is not None:
                raw.append(b)
    text = raw.decode("utf-8", errors="replace")
    text = _TEXT_WRAP.sub(r"\1", text).replace('"', "")
    return _tidy(text)


def recognize(png: bytes) -> dict[str, Any]:
    """一块公式图 → {"ok", "latex", "detail"}；未安装/坏图/推理失败全显性。"""
    if not png:
        return {"ok": False, "latex": "", "detail": "公式图为空，无法转写"}
    try:
        sess = _session()
        x = _preprocess(png)
    except Exception as exc:  # noqa: BLE001 - 引擎缺装/起不来只该显性降级
        return {"ok": False, "latex": "", "detail": str(exc)[:300]}
    if x is None:
        return {"ok": False, "latex": "", "detail": "公式图解码失败或无墨迹，无法转写"}
    try:
        inp, out = sess.get_inputs()[0], sess.get_outputs()[0]
        pred = sess.run([out.name], {inp.name: x})[0]
        latex = _decode(pred[0])
    except Exception as exc:  # noqa: BLE001 - 单块推理失败显性进失败账本
        logger.warning("PP-FormulaNet·M 推理失败：%s", exc)
        return {"ok": False, "latex": "",
                "detail": "PP-FormulaNet·M 推理失败：%s" % str(exc)[:200]}
    if not latex.strip():
        return {"ok": False, "latex": "", "detail": "PP-FormulaNet·M 没认出公式内容"}
    from app.core.content import latex_norm

    latex = str(latex_norm.clean(latex)["text"]).strip()
    if not latex:
        return {"ok": False, "latex": "", "detail": "公式内容经记号字典清洗后为空"}
    return {"ok": True, "latex": latex, "detail": "PP-FormulaNet·M 公式已转写"}