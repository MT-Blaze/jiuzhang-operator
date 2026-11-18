"""模型注册表：目录 × 运行时体检 → 三态（决策台账 D3），配置页与引擎下拉的单源。

目录是 shipped 常量（本文件）；状态每次现算，不缓存体检结论（D3b）。
本模块只读状态、不开新下载通道、不写新配置文件：
- 账号指派住当前工作区 ``config.toml``（ai center 既有口径）；
- YOLO 权重住当前工作区插件目录 ``models/``（model_store 既有口径）；
- RapidOCR 随底座 requirements 安装，体检只做 import 探测。

主公拍板语义（2026-11-18）：没配置/没下载/没指派的条目不进下拉；
旧批次残留值选中了未就绪条目 → 闸口 normalize 回 auto 并给一句人话原因，
由调用方写进批次 note，绝不静默（D3a）。
"""

from __future__ import annotations

import importlib.util
from typing import Any, Callable

from app.core.ai.platform import center as ai_center
from app.core.ingest.layout import model_store, router as layout_router
from app.core.ingest.recognize import router as recognize_router

# capability：layout=切题（版面下拉）、recognize=转写（识别下拉）、both=两边都进。
CATALOG: tuple[dict[str, str], ...] = (
    {"id": "rapidocr_fast", "name": "RapidOCR·快", "capability": "layout",
     "summary": "本地轻量 OCR 切题，随底座安装，图片型卷的切题主路。"},
    {"id": "rapidocr_accurate", "name": "RapidOCR·准", "capability": "layout",
     "summary": "更高精度的 OCR 档，模型未核实、暂不开下载。"},
    {"id": "yolo", "name": "YOLO·版面", "capability": "layout",
     "summary": "本地版面检测模型，权重按需下载（约 75MB），不进插件包。"},
    {"id": "cloud_vision", "name": "云端视觉", "capability": "both",
     "summary": "API 配置里指派的视觉模型，切题兜底与整批转写共用。"},
    {"id": "mineru", "name": "MinerU", "capability": "recognize",
     "summary": "API 配置里指派的 MinerU 云端解析，逐题转写题图。"},
)


def _rapidocr_installed() -> bool:
    try:
        return importlib.util.find_spec("rapidocr") is not None
    except Exception:  # noqa: BLE001 - 体检失败只该降级，不该拖垮清单
        return False


def _judge(entry_id: str, ocr_ready: bool, yolo_present: bool,
           vision: ai_center.TaskBinding,
           mineru: ai_center.TaskBinding | None) -> dict[str, str]:
    """一条目录 × 运行时状态 → 三态＋人话说明＋动作（download/assign/空）。"""
    if entry_id == "rapidocr_fast":
        if ocr_ready:
            return {"state": "ready", "detail": "已随底座安装，本地切题主路可用。",
                    "action": "", "assigned": ""}
        return {"state": "degraded", "detail": "rapidocr 没装上，本地 OCR 切题不可用。",
                "action": "", "assigned": ""}
    if entry_id == "rapidocr_accurate":
        return {"state": "blocked", "detail": "模型未核实、暂不开下载。",
                "action": "", "assigned": ""}
    if entry_id == "yolo":
        if yolo_present:
            return {"state": "ready", "detail": "权重已落地本机，本地版面检测可用。",
                    "action": "", "assigned": ""}
        return {"state": "degraded", "detail": "权重未下载，点【下载】从国内镜像按需获取。",
                "action": "download", "assigned": ""}
    if entry_id == "cloud_vision":
        if vision.is_configured:
            return {"state": "ready",
                    "detail": "已指派：%s（%s）。" % (vision.name, vision.model),
                    "action": "", "assigned": vision.name}
        return {"state": "degraded", "detail": "未指派视觉识别账号。",
                "action": "assign", "assigned": ""}
    if mineru is not None:
        return {"state": "ready", "detail": "已指派：%s。" % mineru.name,
                "action": "", "assigned": mineru.name}
    return {"state": "degraded", "detail": "未指派 MinerU 账号。",
            "action": "assign", "assigned": ""}


def status() -> dict[str, Any]:
    """整块给配置页与下拉：目录全量条目，每条三态＋名字＋一句人话＋动作。"""
    ocr_ready = _rapidocr_installed()
    yolo_present = model_store.present("full")
    vision = ai_center.resolve_task("ocr")
    mineru = ai_center.find_mineru()
    entries: list[dict[str, str]] = []
    for item in CATALOG:
        entry = dict(item)
        entry.update(_judge(item["id"], ocr_ready, yolo_present, vision, mineru))
        entries.append(entry)
    return {"ok": True, "entries": entries}


def _gate(value: Any, normalize: Callable[[Any], str],
          label: str) -> tuple[str, str]:
    """选中的引擎未就绪 → 回 auto＋原因；auto 与乱填值不带原因（乱填本就静默归一）。"""
    picked = normalize(value)
    if picked == "auto":
        return "auto", ""
    for entry in status()["entries"]:
        if entry["id"] != picked:
            continue
        if entry["state"] == "ready":
            return picked, ""
        return "auto", ("%s引擎「%s」未就绪（%s），本次回到自动瀑布。"
                        % (label, entry["name"], entry["detail"]))
    return "auto", ""


def gate_layout(value: Any) -> tuple[str, str]:
    return _gate(value, layout_router.normalize_engine, "版面")


def gate_recognize(value: Any) -> tuple[str, str]:
    return _gate(value, recognize_router.normalize_engine, "识别")