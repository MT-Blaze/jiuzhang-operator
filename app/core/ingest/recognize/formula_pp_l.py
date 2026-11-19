"""PP-FormulaNet·L 公式专科引擎（全模型安装接线卡座2）：公式图 → ONNX CPU → LaTeX。

与 PP-M 同族（UniMERNet 口径），差别只在输入尺寸 768 与权重文件；预处理/解码/
词表构建全复用 formula_pp_m 纯函数（M/L tokenizer 同源已实证），零新依赖。
权重住 engines/formula/models/（formula_setup 变体 l 一键装，按件卸载互不误删）。
未安装＝显性引导去点安装，绝不静默换座；推理失败 ok=False 显性进失败账本。
输出过记号标准字典闭集清洗（latex_norm.clean），与云端通道同一写库口径。
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from app.core.ingest import formula_setup
from app.core.ingest.recognize import formula_pp_m

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ENGINE: Any = None
_DECODE: dict[str, Any] | None = None
_SIZE = 768


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
            if not formula_setup.weights_ready("l"):
                raise RuntimeError("PP-FormulaNet·L 权重未安装，先在模型配置中心点【安装】")
            import onnxruntime as ort

            onnx, _yml = formula_setup.model_paths("l")
            _ENGINE = ort.InferenceSession(str(onnx), providers=["CPUExecutionProvider"])
        return _ENGINE


def _decoder() -> dict[str, Any]:
    """词表自 L yml 内嵌 tokenizer（与 M 同源）；懒加载随引擎缓存同丢。"""
    global _DECODE
    with _LOCK:
        if _DECODE is None:
            _onnx, yml = formula_setup.model_paths("l")
            _DECODE = formula_pp_m._build_decoder(yml)
        return _DECODE


def recognize(png: bytes) -> dict[str, Any]:
    """一块公式图 → {"ok", "latex", "detail"}；未安装/坏图/推理失败全显性。"""
    if not png:
        return {"ok": False, "latex": "", "detail": "公式图为空，无法转写"}
    try:
        sess = _session()
        x = formula_pp_m._preprocess(png, _SIZE)
    except Exception as exc:  # noqa: BLE001 - 引擎缺装/起不来只该显性降级
        return {"ok": False, "latex": "", "detail": str(exc)[:300]}
    if x is None:
        return {"ok": False, "latex": "", "detail": "公式图解码失败或无墨迹，无法转写"}
    try:
        inp, out = sess.get_inputs()[0], sess.get_outputs()[0]
        pred = sess.run([out.name], {inp.name: x})[0]
        latex = formula_pp_m._decode(pred[0], _decoder())
    except Exception as exc:  # noqa: BLE001 - 单块推理失败显性进失败账本
        logger.warning("PP-FormulaNet·L 推理失败：%s", exc)
        return {"ok": False, "latex": "",
                "detail": "PP-FormulaNet·L 推理失败：%s" % str(exc)[:200]}
    if not latex.strip():
        return {"ok": False, "latex": "", "detail": "PP-FormulaNet·L 没认出公式内容"}
    from app.core.content import latex_norm

    latex = str(latex_norm.clean(latex)["text"]).strip()
    if not latex:
        return {"ok": False, "latex": "", "detail": "公式内容经记号字典清洗后为空"}
    return {"ok": True, "latex": latex, "detail": "PP-FormulaNet·L 公式已转写"}