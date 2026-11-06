"""本地 YOLO 版面探路：本机 ONNX 四级瀑布（满血 > 量化 > CPU > 云端）。

模型不进插件包，第一次由界面点击按需下载到当前工作区的插件目录。
加载顺序严格按军令：满血+GPU → 量化+GPU → 量化+CPU → 失败交云端。
每一级都把「版本 + 硬件」写进 status，宿主中继到【运行日志】。

YOLO 只交坐标、不交文字；页图读不到或单页推理失败只丢那一页。
"""

from __future__ import annotations

import logging
from typing import Any

from app.core import pending_assets
from app.core.layout import layout_model_store, layout_yolo_runtime

logger = logging.getLogger(__name__)

KIND_LABEL = {"full": "满血版", "quantized": "量化版"}
OOM_WARNING = "⚠️ 显存不足，加载满血版失败，正在自动降级为量化版..."
CLOUD_WARNING = "[WARN] 本地 YOLO 彻底失败，已自动降级至云端版面 API"
OOM_MARKERS = (
    "out of memory", "outofmemory", "cuda_error_out_of_memory",
    "failed to allocate", "allocation failure", "not enough memory",
    "insufficient memory", "bad_alloc", "显存不足", "内存不足",
)


def detect(request: dict[str, Any]) -> dict[str, Any]:
    """逐页推理；单页失败只丢那一页，整级失败交给调度员降云端。"""
    statuses: list[dict[str, str]] = []
    hardware = layout_model_store.hardware()
    if not hardware.get("ready"):
        statuses.append(_line("warn", CLOUD_WARNING))
        logger.warning(CLOUD_WARNING)
        return _fail("本机缺少 onnxruntime：" + str(hardware.get("detail") or ""),
                     statuses)

    session, chosen, reason = _pick_session(hardware, statuses)
    if session is None:
        statuses.append(_line("warn", CLOUD_WARNING))
        logger.warning(CLOUD_WARNING)
        return _fail("本地 YOLO 不可用：" + (reason or "模型或运行库缺失"), statuses)

    kind, provider = chosen
    provider_label = ("CPU运行" if provider == "CPUExecutionProvider"
                      else str(hardware.get("hardware_label") or "CPU运行"))
    line = f"[INFO] 版面分析：{reason}本地 YOLO（{KIND_LABEL[kind]} / {provider_label}）"
    statuses.append(_line("info", line))
    logger.info(line)

    pages: dict[int, list[dict[str, Any]]] = {}
    notes: list[str] = []
    for entry in request.get("pages") or []:
        try:
            page_no = int(entry.get("page") or 0)
            width = float(entry.get("width") or 0)
            height = float(entry.get("height") or 0)
        except (TypeError, ValueError):
            continue
        if page_no <= 0 or width <= 0 or height <= 0:
            continue
        raw = _page_image(entry)
        if raw is None:
            notes.append(f"第 {page_no} 页读不到页图")
            continue
        try:
            regions = layout_yolo_runtime.infer_regions(session, raw, width, height)
        except Exception as exc:  # noqa: BLE001 - 单页失败继续下一张
            notes.append(f"第 {page_no} 页推理失败：{exc}")
            continue
        if regions:
            pages[page_no] = regions
    if not pages:
        statuses.append(_line("warn", CLOUD_WARNING))
        logger.warning(CLOUD_WARNING)
        detail = "YOLO 没探出题块" + (("：" + "；".join(notes[:3])) if notes else "")
        return _fail(detail, statuses)
    return {
        "ok": True,
        "engine": "yolo",
        "pages": pages,
        "columns": {page: 1 for page in pages},
        "detail": f"YOLO 探出 {len(pages)} 页题块（{KIND_LABEL[kind]} / {provider_label}）",
        "status": statuses,
        "model": {**layout_model_store.describe(kind),
                  "provider": provider, "hardware": provider_label},
    }


def _pick_session(hardware: dict[str, Any],
                  statuses: list[dict[str, str]]) -> tuple[Any, tuple[str, str] | None, str]:
    """严格按 满血+GPU → 量化+GPU → 量化+CPU 选，返回 (会话, (型号, 提供者), 前缀)。"""
    gpu_provider = {"cuda": "CUDAExecutionProvider",
                    "directml": "DmlExecutionProvider"}.get(str(hardware.get("gpu") or ""), "")
    reason = "已启用"
    if gpu_provider:
        if layout_model_store.present("full"):
            session, error = _load("full", [gpu_provider])
            if session is not None:
                return session, ("full", gpu_provider), reason
            if _is_oom(error):
                statuses.append(_line("error", OOM_WARNING))
                logger.warning(OOM_WARNING)
                reason = "显存不足，已降级为"
            else:
                reason = "满血版加载失败，已降级为"
        session, error = _load("quantized", [gpu_provider])
        if session is not None:
            return session, ("quantized", gpu_provider), reason
        if _is_oom(error):
            if not any(item.get("text") == OOM_WARNING for item in statuses):
                statuses.append(_line("error", OOM_WARNING))
                logger.warning(OOM_WARNING)
            reason = "显存不足，已降级为"
        elif reason == "已启用":
            reason = "显卡加速不可用，已降级为"

    session, error = _load("quantized", ["CPUExecutionProvider"])
    if session is not None:
        return session, ("quantized", "CPUExecutionProvider"), reason
    return None, None, str(error or reason)


def _load(kind: str, providers: list[str]) -> tuple[Any, Exception | None]:
    try:
        if not layout_model_store.present(kind):
            raise layout_yolo_runtime.RuntimeErrorYolo(
                f"{KIND_LABEL[kind]}模型未下载或文件不完整")
        path = layout_model_store.model_path(kind)
        return layout_yolo_runtime.load_session(str(path), providers), None
    except Exception as exc:  # noqa: BLE001 - 本档失败只该换下一档
        return None, exc


def _is_oom(error: Exception | None) -> bool:
    """MemoryError 或 ONNX Runtime 的显存/内存不足文案都算 OOM。"""
    seen: set[int] = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, MemoryError):
            return True
        text = str(error).lower()
        if any(marker in text for marker in OOM_MARKERS):
            return True
        error = error.__cause__ or error.__context__
    return False


def _page_image(entry: dict[str, Any]) -> bytes | None:
    name = str(entry.get("name") or "").strip()
    if not name:
        return None
    try:
        raw = pending_assets.asset_path(name).read_bytes()
    except Exception:  # noqa: BLE001 - 页图不在就交给下一级
        return None
    return raw or None


def _line(level: str, text: str) -> dict[str, str]:
    return {"level": level, "text": text}


def _fail(detail: str, statuses: list[dict[str, str]]) -> dict[str, Any]:
    return {"ok": False, "engine": "yolo", "pages": {}, "columns": {},
            "detail": detail, "status": statuses}
