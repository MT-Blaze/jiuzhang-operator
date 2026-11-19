"""RapidOCR·准（medium）权重一键装（2.20.0 卡§6）：engines/ocr/models/ 权重目录。

底座 .venv 已带 rapidocr（快档 small 随底座自带）；准档只缺 det/rec 两件 medium
权重，不建隔离环境、不装 torch。主源走 modelscope 包内置通道（仓库页已核实
字节数＋sha256），hf-mirror/gitcode 同路径候选参与点击内测速选路——路径未核实
的源测速自然判不通，下载后 sha256 逐件校验，绝不拿错文件加载。
安装/卸载只由老师界面点击发起；失败显性化：人话原因进状态，不静默。
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.core import config
from app.core.ingest import mirrors

logger = logging.getLogger(__name__)

# （任务, 文件名, 字节数, sha256）：modelscope v3.10.0 仓库页实测核对（2026-11-19）。
WEIGHT_FILES = (
    ("det", "PP-OCRv6_det_medium.onnx", 62119454,
     "92078b7355007ccfffcd4c8cd441a3afd4538904d06881b29a155e1e679907c2"),
    ("rec", "PP-OCRv6_rec_medium.onnx", 76629984,
     "eef444829dbbe18d7fea59a3f6eb75647518d2b3a9568d27c92e42940204894b"),
)
WEIGHT_TIMEOUT = 120

_LOCK = threading.Lock()
_STATE: dict[str, str] = {"state": "idle", "step": "", "message": ""}
_THREAD: threading.Thread | None = None


class OcrSetupError(Exception):
    """安装前置不满足或安装失败（人话原因）。"""


def engine_dir() -> Path:
    return config.PROJECT_ROOT / "engines" / "ocr"


def model_paths() -> tuple[Path, Path]:
    """（det, rec）落地路径；只读，不触发下载。"""
    folder = engine_dir() / "models"
    return folder / WEIGHT_FILES[0][1], folder / WEIGHT_FILES[1][1]


def weights_ready() -> bool:
    """两件在不在本机（只读按字节数核对，不出网）；缺一律当不在。"""
    for path, (_task, _name, size, _digest) in zip(model_paths(), WEIGHT_FILES):
        try:
            if not path.is_file() or path.stat().st_size != size:
                return False
        except OSError:
            return False
    return True


def status() -> dict[str, str]:
    """安装进度快照（只读）：state=idle/installing/done/error＋step＋人话。"""
    with _LOCK:
        return dict(_STATE)


def _set(**fields: str) -> None:
    with _LOCK:
        _STATE.update(fields)


def _weight_urls(task: str, name: str) -> list[tuple[str, str]]:
    rel = "onnx/PP-OCRv6/%s/%s" % (task, name)
    return [
        ("ModelScope", "https://www.modelscope.cn/models/RapidAI/RapidOCR/"
                       "resolve/v3.10.0/" + rel),
        ("hf-mirror", "https://hf-mirror.com/RapidAI/RapidOCR/resolve/main/" + rel),
        ("GitCode", "https://gitcode.com/RapidAI/RapidOCR/resolve/main/" + rel),
    ]


def _download_one(task: str, name: str, size: int, digest: str,
                  sources: list[dict[str, Any]]) -> None:
    """单件流式下载＋sha256＋原子改名；中断换下一家；全败抛人话错误。"""
    target = engine_dir() / "models" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    last_error = "没有可达的权重源"
    for row in sources:
        url = row["url"]
        hasher = hashlib.sha256()
        written = 0
        try:
            with urllib.request.urlopen(url, timeout=WEIGHT_TIMEOUT) as response, \
                    part.open("wb") as sink:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    sink.write(chunk)
                    hasher.update(chunk)
                    written += len(chunk)
                    _set(message="正在从 %s 下载 %s（%.1f/%.1fMB）…"
                         % (row["name"], name, written / 1e6, size / 1e6))
            if written != size or hasher.hexdigest() != digest:
                raise OSError("字节数或 sha256 与仓库登记不符")
            part.replace(target)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            part.unlink(missing_ok=True)
            last_error = "%s → %s" % (row["name"], exc)
            logger.warning("RapidOCR 准档权重源失败：%s", last_error)
            _set(message="权重源失败，换下一家（%s）" % last_error)
    raise OcrSetupError("权重下载全败（%s）：%s" % (name, last_error))


def start_install() -> dict[str, str]:
    """老师点击才走到这里：已装直接 done；在装复用；否则起后台线程。"""
    global _THREAD
    if weights_ready():
        _set(state="done", step="体检", message="RapidOCR·准权重已在本机，无需再下。")
        return status()
    with _LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            return dict(_STATE)
        _STATE.update({"state": "installing", "step": "测速选源",
                       "message": "正在测速选权重源（modelscope/hf-mirror/gitcode），"
                                  "随后下载约 139MB。"})
        _THREAD = threading.Thread(target=_install, name="jzo-ocr-install", daemon=True)
    _THREAD.start()
    return status()


def _install() -> None:
    try:
        raced = mirrors.race(_weight_urls(*WEIGHT_FILES[0][:2]))
        sources = [row for row in raced if row["ok"]]
        _set(step="下载权重", message=mirrors.pick_note(raced))
        if not sources:
            raise OcrSetupError("权重源全不通（modelscope/hf-mirror/gitcode），无法下载。")
        for task, name, size, digest in WEIGHT_FILES:
            target = engine_dir() / "models" / name
            if target.is_file() and target.stat().st_size == size:
                continue
            _download_one(task, name, size, digest, sources)
        _set(state="done", step="完成",
             message="RapidOCR·准已就绪（det/rec 两件 medium 权重校验通过）。")
        logger.info("[INFO] RapidOCR 准档安装收口：%s", status().get("message"))
    except OcrSetupError as exc:
        _set(state="error", message=str(exc))
        logger.warning("[WARN] RapidOCR 准档安装失败：%s", exc)
    except Exception as exc:  # noqa: BLE001 - 后台线程任何异常都要显性化
        _set(state="error", message="安装异常：%s" % exc)
        logger.warning("[WARN] RapidOCR 准档安装异常：%s", exc)


def uninstall() -> dict[str, Any]:
    """老师点【卸载】＋确认后才走到这里：整个 engines/ocr/ 删掉（含权重）。"""
    with _LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            raise OcrSetupError("正在安装中，不能同时卸载；等安装收口后再试。")
    folder = engine_dir()
    if folder.parent != config.PROJECT_ROOT / "engines":
        raise OcrSetupError("卸载路径不对（%s），拒绝动手。" % folder)
    from app.core.ingest.recognize import ocr  # noqa: PLC0415 - 按需导入防循环

    ocr.reset("medium")
    if not folder.exists():
        _set(state="idle", step="", message="")
        return {"ok": True, "message": "RapidOCR·准权重本来就没下，无需卸载。"}
    try:
        shutil.rmtree(folder)
    except OSError as exc:
        raise OcrSetupError("卸载删不掉 engines/ocr/：%s（可能有会话占用，稍后再试）" % exc)
    _set(state="idle", step="", message="")
    logger.info("[INFO] RapidOCR 准档已卸载：%s", folder)
    return {"ok": True, "message": "RapidOCR·准已卸载（medium 权重全删，快档不受影响）。"}