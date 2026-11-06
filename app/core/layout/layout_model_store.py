"""本地 YOLO 模型仓库：配置、硬件探底与后台镜像下载。

模型不进插件包：老师第一次选【YOLO】时才从国内镜像按需下载，落进当前
工作区插件目录的 ``models/``。下载只由界面点击发起，地址只认
``model_config.json`` 里写死的镜像，绝不接受插件或请求体自带的 URL。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request
from pathlib import Path
from typing import Any

from app.core import config

logger = logging.getLogger(__name__)

PLUGIN_ID = "org.jiuzhang.editor"
CONFIG_NAME = "model_config.json"
MODEL_KINDS = ("full", "quantized")
CHUNK_BYTES = 1024 * 1024
PART_SUFFIX = ".tmp"
# 完整性下限：半截文件绝不允许改名成 .onnx 进入加载环节。
# 满血版按已核实的真实文件（75,324,598 字节）取下限，量化版按军令 >10MB。
MIN_BYTES = {"full": 70 * 1000 * 1000, "quantized": 10 * 1024 * 1024}
DOWNLOAD_TIMEOUT = 30.0

_STATE_LOCK = threading.Lock()
_DOWNLOADS: dict[str, dict[str, Any]] = {}
_THREADS: dict[str, threading.Thread] = {}


class ModelStoreError(Exception):
    """配置、模型编号或下载状态不合法。"""


def _plugin_dir() -> Path:
    return config.plugins_dir() / PLUGIN_ID


def _config_path() -> Path:
    return _plugin_dir() / CONFIG_NAME


def load_config() -> dict[str, Any]:
    """每次按当前工作区重读；缺失或损坏一律当「没有模型配置」。"""
    try:
        document = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {"models": {}}
    if not isinstance(document, dict) or not isinstance(document.get("models"), dict):
        return {"models": {}}
    return document


def _entry(kind: str) -> dict[str, Any]:
    if kind not in MODEL_KINDS:
        raise ModelStoreError("模型编号只认 full / quantized")
    entry = (load_config().get("models") or {}).get(kind)
    if not isinstance(entry, dict) or not entry.get("filename"):
        raise ModelStoreError(f"model_config.json 里没有可用的 {kind} 条目")
    return entry


def models_dir() -> Path:
    name = str(load_config().get("models_dir") or "models")
    folder = _plugin_dir() / Path(name).name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def model_path(kind: str) -> Path:
    entry = _entry(kind)
    # 目录由底座决定，配置文件只能给一个纯文件名，禁止再拼路径。
    return models_dir() / Path(str(entry["filename"])).name


def describe(kind: str) -> dict[str, str]:
    entry = _entry(kind)
    return {
        "kind": kind,
        "label": str(entry.get("label") or ("满血版" if kind == "full" else "量化版")),
        "version": str(entry.get("version") or "v1.0"),
        "display_size": str(entry.get("display_size") or ""),
    }


def _minimum(kind: str, entry: dict[str, Any]) -> int:
    # 清单可以按真实文件大小把下限写死；缺省值仍留军令口径。
    return max(1, int(entry.get("min_bytes") or MIN_BYTES[kind]))


def _usable(path: Path, minimum: int) -> bool:
    return path.is_file() and path.stat().st_size >= minimum


def present(kind: str) -> bool:
    try:
        return _usable(model_path(kind), _minimum(kind, _entry(kind)))
    except ModelStoreError:
        return False


def hardware() -> dict[str, Any]:
    """探测 ONNX Runtime 与可用执行提供者；运行库缺失时如实标为未就绪。"""
    try:
        import onnxruntime as ort  # noqa: PLC0415 - 按需导入，没装也不拖垮底座
    except Exception as exc:  # noqa: BLE001 - 缺运行库属于常态降级
        return {"ready": False, "providers": ["CPUExecutionProvider"],
                "gpu": "", "hardware_label": "CPU运行",
                "detail": f"未安装 onnxruntime：{exc}"}
    try:
        providers = [str(item) for item in ort.get_available_providers()]
    except Exception as exc:  # noqa: BLE001 - 坏运行库只该降级
        return {"ready": False, "providers": ["CPUExecutionProvider"],
                "gpu": "", "hardware_label": "CPU运行",
                "detail": f"读取执行提供者失败：{exc}"}
    if "CUDAExecutionProvider" in providers:
        gpu, label = "cuda", "CUDA显卡加速"
    elif "DmlExecutionProvider" in providers:
        gpu, label = "directml", "DirectML显卡加速"
    else:
        gpu, label = "", "CPU运行"
    return {"ready": True, "providers": providers, "gpu": gpu,
            "hardware_label": label, "detail": ""}


def status() -> dict[str, Any]:
    """给插件看的只读快照：模型是否落地、本机硬件与正在跑的下载。"""
    document = load_config()
    models: dict[str, Any] = {}
    for kind in MODEL_KINDS:
        entry = (document.get("models") or {}).get(kind)
        if not isinstance(entry, dict):
            continue
        path = model_path(kind)
        actual = path.stat().st_size if path.is_file() else 0
        minimum = _minimum(kind, entry)
        models[kind] = {
            "label": str(entry.get("label") or ("满血版" if kind == "full" else "量化版")),
            "version": str(entry.get("version") or "v1.0"),
            "display_size": str(entry.get("display_size") or ""),
            "filename": str(entry.get("filename") or ""),
            "present": actual >= minimum,
            "bytes": actual,
            "min_bytes": minimum,
        }
    with _STATE_LOCK:
        download = _snapshot_locked()
    return {"ok": True, "hardware": hardware(), "models": models, "download": download}


def start_download(kind: str) -> dict[str, Any]:
    """由界面点击发起：同一个模型已在下载就复用，不在启动时自动触发。"""
    entry = _entry(kind)
    target = model_path(kind)
    minimum = _minimum(kind, entry)
    if target.is_file():
        if target.stat().st_size >= minimum:
            return {"kind": kind, "state": "done", "percent": 100,
                    "received": target.stat().st_size,
                    "total": target.stat().st_size, "message": "模型已在本机"}
        # 半截/损坏文件：先丢掉再重下，绝不拿它去加载。
        try:
            target.unlink()
        except OSError as exc:
            raise ModelStoreError(f"旧模型文件删不掉：{exc}") from exc
    with _STATE_LOCK:
        thread = _THREADS.get(kind)
        if thread and thread.is_alive():
            return dict(_DOWNLOADS[kind])
        _DOWNLOADS[kind] = {
            "kind": kind, "state": "downloading", "percent": 0,
            "received": 0, "total": int(entry.get("size_bytes") or 0),
            "url": "", "message": "准备下载",
        }
        worker = threading.Thread(target=_download, args=(kind, entry, target),
                                  name=f"jzo-yolo-{kind}", daemon=True)
        _THREADS[kind] = worker
    worker.start()
    with _STATE_LOCK:
        return dict(_DOWNLOADS[kind])


def _snapshot_locked() -> dict[str, Any] | None:
    running = [dict(item) for item in _DOWNLOADS.values()
               if item.get("state") == "downloading"]
    if running:
        return running[0]
    finished = [dict(item) for item in _DOWNLOADS.values() if item.get("state") != "downloading"]
    return finished[-1] if finished else None


def _download(kind: str, entry: dict[str, Any], target: Path) -> None:
    # 先写 .tmp，大小与完整性都过了才原子改名为 .onnx；断网只留一个临时文件。
    part = target.with_name(target.name + PART_SUFFIX)
    minimum = _minimum(kind, entry)
    urls = [str(item) for item in entry.get("urls") or []
            if str(item).startswith(("https://", "http://"))]
    last_error = "配置里没有可用的下载地址"
    with _STATE_LOCK:
        _DOWNLOADS.setdefault(kind, {
            "kind": kind, "state": "downloading", "percent": 0,
            "received": 0, "total": int(entry.get("size_bytes") or 0),
            "url": "", "message": "准备下载",
        })
    for url in urls:
        try:
            if part.exists():
                part.unlink()
            received, total = _stream(kind, url, part)
            if total and received != total:
                raise OSError(f"下载不完整（{received}/{total} 字节）")
            if received < minimum:
                raise OSError(f"文件过小（{received} 字节，至少需要 {minimum}）")
            os.replace(part, target)
        except Exception as exc:  # noqa: BLE001 - 换下一个镜像，全部失败才报错
            last_error = f"{url} → {exc}"
            logger.warning("YOLO 模型下载失败：%s", last_error)
            try:
                if part.exists():
                    part.unlink()
            except OSError:
                pass
            with _STATE_LOCK:
                _DOWNLOADS[kind].update({"message": "镜像失败，换源重试中"})
            continue
        with _STATE_LOCK:
            _DOWNLOADS[kind].update({
                "state": "done", "percent": 100, "received": received,
                "total": total or received, "url": url, "message": "下载完成，校验通过"})
        logger.info("[INFO] 本地 YOLO 模型已就绪：%s（%d 字节，来源 %s）",
                    kind, received, url)
        return
    with _STATE_LOCK:
        _DOWNLOADS[kind].update({"state": "error", "message": last_error[:300]})
    logger.warning("[WARN] 本地 YOLO 模型下载失败：%s", last_error)


def _stream(kind: str, url: str, part: Path) -> tuple[int, int]:
    request = urllib.request.Request(
        url, method="GET",
        headers={"User-Agent": "JiuzhangOperator/1.0 (+local-yolo)",
                 "Accept": "application/octet-stream"})
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
        header = response.headers.get("Content-Length") if response.headers else None
        total = int(header) if header and str(header).isdigit() else 0
        received = 0
        with part.open("wb") as handle:
            while True:
                chunk = response.read(CHUNK_BYTES)
                if not chunk:
                    break
                handle.write(chunk)
                received += len(chunk)
                percent = min(99, int(received * 100 / total)) if total > 0 else 0
                with _STATE_LOCK:
                    item = _DOWNLOADS.get(kind)
                    if item is not None and item.get("state") == "downloading":
                        item.update({"received": received, "total": total,
                                     "percent": percent, "url": url,
                                     "message": "下载中"})
    return received, total
