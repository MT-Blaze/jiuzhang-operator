"""模型注册表：目录（数据驱动 toml）× 运行时体检 → 三态（决策台账 D3）。

目录住 ``catalog.toml``（本文件旁边）：加条目/改说明只动数据不改代码；
状态每次现算，不缓存体检结论（D3b）。本模块只读状态、不开新下载通道：
- 账号指派住当前工作区 ``config.toml``（ai center 既有口径）；
- YOLO 权重住当前工作区插件目录 ``models/``（model_store 既有口径）；
- RapidOCR 随底座 requirements 安装，体检只做 import 探测；
- MinerU 本地座体检走 mineru_setup（engines/mineru/ 隔离环境）；
- 启用/停用＋默认选择是插件财产，住插件目录 model_prefs.toml。

主公拍板语义（2026-11-18）：没配置/没下载/没指派/被停用的条目不进下拉；
旧批次残留值选中了未就绪条目 → 闸口 normalize 回 auto 并给一句人话原因，
由调用方写进批次 note，绝不静默（D3a）。本地 VLM 低于 6G 直写「电脑硬件
不支持」引导云端；VLM 推理与公式擂台本轮不建（待 T6），只登记条目＋门。
"""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from typing import Any, Callable

from app.core.ai.platform import center as ai_center
from app.core.ingest import hardware, mineru_setup, model_prefs
from app.core.ingest.layout import model_store, router as layout_router
from app.core.ingest.recognize import router as recognize_router

CATALOG_PATH = Path(__file__).with_name("catalog.toml")


def _catalog_document() -> dict[str, Any]:
    try:
        return tomllib.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return {}


def catalog() -> tuple[dict[str, Any], ...]:
    """目录全量条目（数据驱动）；文件缺失/损坏返回空，下拉只剩自动。"""
    rows = _catalog_document().get("entry")
    if not isinstance(rows, list):
        return ()
    return tuple(dict(row) for row in rows
                 if isinstance(row, dict) and row.get("id"))


def vram_tiers() -> list[dict[str, Any]]:
    rows = _catalog_document().get("vram_tier")
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _rapidocr_installed() -> bool:
    try:
        return importlib.util.find_spec("rapidocr") is not None
    except Exception:  # noqa: BLE001 - 体检失败只该降级，不该拖垮清单
        return False


def _judge_vlm(item: dict[str, Any], hw: dict[str, Any]) -> dict[str, str]:
    """本地 VLM 硬件门：低于最低显存直写不支持引导云；够格也只登记待 T6。"""
    need = int(item.get("min_vram") or 6)
    vram = float(hw.get("vram_gb") or 0)
    if vram < need:
        return {"state": "blocked",
                "detail": "电脑硬件不支持：本机显存 %s，本地 VLM 最低 %dG 起。"
                          "请用云端视觉或 MinerU 兜底。" % (hw.get("vram_label") or "读不到", need),
                "action": "assign", "assigned": ""}
    tier = hardware.tier_for(vram, vram_tiers())
    fits = str(tier.get("fits")) if tier else "入门档"
    return {"state": "blocked",
            "detail": "本机显存 %s，可跑 %s；本地推理通道尚未开通（待 T6），本轮只登记。"
                      % (hw.get("vram_label") or "读不到", fits),
            "action": "", "assigned": ""}


def _judge_mineru_local() -> dict[str, str]:
    install = mineru_setup.status()
    if install.get("state") == "error":
        return {"state": "blocked",
                "detail": "安装失败：%s" % install.get("message", ""),
                "action": "install", "assigned": ""}
    check = mineru_setup.health()
    if check["ok"]:
        return {"state": "ready",
                "detail": "已安装（%s），隔离环境体检通过；逐题解析接线在下一卡，暂由云端 MinerU 兜底。"
                          % check["version"],
                "action": "", "assigned": ""}
    if check["state"] == "error":
        return {"state": "blocked", "detail": check["message"],
                "action": "install", "assigned": ""}
    return {"state": "degraded",
            "detail": "未安装。点【安装本地 MinerU】一键装进隔离环境（国内镜像）。",
            "action": "install", "assigned": ""}


def _judge(item: dict[str, Any], ocr_ready: bool, yolo_present: bool,
           vision: ai_center.TaskBinding,
           mineru: ai_center.TaskBinding | None,
           hw: dict[str, Any]) -> dict[str, str]:
    """一条目录 × 运行时状态 → 三态＋人话说明＋动作（download/assign/install/空）。"""
    entry_id = str(item["id"])
    family = str(item.get("family") or "")
    if family == "vlm":
        return _judge_vlm(item, hw)
    if family == "formula":
        return {"state": "blocked",
                "detail": "公式专科擂台与推理尚未开通（待 T6），本轮只登记说明。",
                "action": "", "assigned": ""}
    if entry_id == "mineru_local":
        return _judge_mineru_local()
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
    """整块给配置页与下拉：目录全量×三态＋硬件快照＋档位表＋默认选择。"""
    prefs = model_prefs.load()
    disabled = set(prefs["disabled"])
    ocr_ready = _rapidocr_installed()
    yolo_present = model_store.present("full")
    vision = ai_center.resolve_task("ocr")
    mineru = ai_center.find_mineru()
    hw = hardware.probe()
    entries: list[dict[str, Any]] = []
    for item in catalog():
        entry = dict(item)
        entry.update(_judge(item, ocr_ready, yolo_present, vision, mineru, hw))
        entry["enabled"] = entry["id"] not in disabled
        entries.append(entry)
    return {"ok": True, "entries": entries, "hardware": hw,
            "vram_tiers": vram_tiers(),
            "vram_note": str(_catalog_document().get("vram_note") or ""),
            "defaults": {"layout": prefs["default_layout"],
                         "recognize": prefs["default_recognize"]}}


def _gate(value: Any, normalize: Callable[[Any], str],
          label: str) -> tuple[str, str]:
    """选中未就绪/已停用/未接线 → 回 auto＋原因；auto 与乱填值不带原因。

    目录里已就绪但调度还没接线的条目（如 mineru_local）由 normalize 归 auto，
    这里按原始值找回条目，照念 catalog 的 gate_note，绝不静默（D3a）。
    """
    picked = normalize(value)
    raw = str(value or "").strip().lower()
    target = picked if picked != "auto" else raw
    if not target or target == "auto":
        return "auto", ""
    for entry in status()["entries"]:
        if entry["id"] != target:
            continue
        if not entry.get("enabled", True):
            return "auto", ("%s引擎「%s」已停用，本次回到自动瀑布。"
                            % (label, entry["name"]))
        if entry["state"] != "ready":
            return "auto", ("%s引擎「%s」未就绪（%s），本次回到自动瀑布。"
                            % (label, entry["name"], entry["detail"]))
        note = str(entry.get("gate_note") or "")
        if note:
            return "auto", "%s引擎「%s」%s" % (label, entry["name"], note)
        return picked, ""
    return "auto", ""


def gate_layout(value: Any) -> tuple[str, str]:
    return _gate(value, layout_router.normalize_engine, "版面")


def gate_recognize(value: Any) -> tuple[str, str]:
    return _gate(value, recognize_router.normalize_engine, "识别")