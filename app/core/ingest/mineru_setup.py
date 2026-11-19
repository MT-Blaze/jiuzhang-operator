"""MinerU 本地一键装（四合一卡 §1）：engines/mineru/ 独立 venv＋subprocess 体检。

只写安装器与调用器：不复制 MinerU 代码、权重不进插件包（D1/D1a，AGPL
老师自装个人用已覆盖）。与底座 onnxruntime 同名互踩，故必须隔离，绝不
污染底座 .venv。安装只由老师点【安装本地 MinerU】发起，下载源只认国内
镜像；体检每次现算不缓存（D3b）。失败显性化：人话原因进状态，不静默。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from app.core import config
from app.core.ingest import mirrors

logger = logging.getLogger(__name__)

PACKAGE_SPEC = "mineru==4.2.3"
MIN_PYTHON = (3, 11)
VENV_TIMEOUT = 300
INSTALL_TIMEOUT = 1800
HEALTH_TIMEOUT = 180
WEIGHT_TIMEOUT = 1800
TAIL_LINES = 12

_CHECK_CODE = (
    "from importlib.metadata import version\n"
    "import mineru\n"
    "print('MINERU_VERSION=' + version('mineru'))\n"
)

# 权重就绪只读探查（不出网）：standard 档＝onnx 小模型＋llama-cpp 本地小 VLM。
_WEIGHT_CHECK_CODE = (
    "from mineru.model.registry import model_repos_for_tier\n"
    "from mineru.model.download import verify_model_repo\n"
    "repos = model_repos_for_tier('standard', small_backend='onnx', vlm_engine='llama-cpp')\n"
    "missing = [r.name for r in repos if not verify_model_repo(r).ready]\n"
    "print('WEIGHTS_MISSING=' + ','.join(missing))\n"
)

_NETWORK_MARKERS = (
    "connection refused", "connection reset", "connectionerror",
    "max retries exceeded", "failed to establish", "timed out", "timeout",
    "proxyerror", "sslerror", "certificate verify failed",
    "temporary failure in name resolution", "getaddrinfo",
    "network is unreachable", "no route to host", "bad gateway",
    "service unavailable",
)
_NO_MATCH_MARKERS = (
    "no matching distribution", "could not find a version that satisfies",
    "from versions: none",
)

_LOCK = threading.Lock()
_STATE: dict[str, str] = {"state": "idle", "step": "", "message": ""}
_THREAD: threading.Thread | None = None


class MineruSetupError(Exception):
    """安装前置不满足或安装失败（人话原因）。"""


def engine_dir() -> Path:
    return config.PROJECT_ROOT / "engines" / "mineru"


def python_exe() -> Path:
    folder = engine_dir()
    return folder / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _run(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "[超时] 超过 %d 秒" % timeout
    except OSError as exc:
        return 127, "[无法执行] %s" % exc
    raw = (proc.stdout or b"") + (proc.stderr or b"")
    for encoding in ("utf-8", "gbk"):
        try:
            return proc.returncode, raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return proc.returncode, raw.decode("utf-8", "replace")


def _tail(text: str) -> str:
    return " / ".join(text.splitlines()[-TAIL_LINES:])[:400]


def _classify(text: str) -> str:
    low = text.lower()
    if any(mark in low for mark in _NETWORK_MARKERS):
        return "网络或镜像不通"
    if any(mark in low for mark in _NO_MATCH_MARKERS):
        return "镜像里没有这个版本（mineru 4.2.3 需 Python 3.11–3.14）"
    return _tail(text) or "未知原因"


def health() -> dict[str, Any]:
    """装好没有：独立环境解释器在不在＋import/版本探测。每次现算（D3b）。"""
    py = python_exe()
    if not py.is_file():
        return {"ok": False, "state": "missing", "version": "",
                "message": "本地 MinerU 未安装。"}
    rc, out = _run([str(py), "-c", _CHECK_CODE], HEALTH_TIMEOUT)
    version = ""
    for line in out.splitlines():
        if line.startswith("MINERU_VERSION="):
            version = line.split("=", 1)[1].strip()
    if rc == 0 and version:
        return {"ok": True, "state": "ready", "version": version, "message": ""}
    return {"ok": False, "state": "error", "version": "",
            "message": "MinerU 环境在但体检失败：%s" % _classify(out)}


def status() -> dict[str, str]:
    """安装进度快照（只读）：state=idle/installing/done/error＋step＋人话。"""
    with _LOCK:
        return dict(_STATE)


def weights_ready() -> bool:
    """standard 档权重在不在本机（只读探查，不出网）；探不到一律当不在。"""
    py = python_exe()
    if not py.is_file():
        return False
    rc, out = _run([str(py), "-c", _WEIGHT_CHECK_CODE], HEALTH_TIMEOUT)
    if rc != 0:
        return False
    for line in out.splitlines():
        if line.startswith("WEIGHTS_MISSING="):
            return not line.split("=", 1)[1].strip()
    return False


def _models_download_exe() -> Path:
    folder = engine_dir()
    if sys.platform == "win32":
        return folder / "Scripts" / "mineru-models-download.exe"
    return folder / "bin" / "mineru-models-download"


def _prefetch_weights() -> bool:
    """包自带预取入口并入安装点击：modelscope 国内源，standard 档 onnx 路线。"""
    _set(step="预取模型",
         message="正在从国内镜像预取解析模型（standard 档，约 1–3GB），请耐心等待。")
    rc, out = _run(
        [str(_models_download_exe()), "--tier", "standard",
         "--small-backend", "onnx", "--vlm-engine", "llama-cpp",
         "--source", "modelscope"], WEIGHT_TIMEOUT)
    if rc != 0:
        logger.warning("[WARN] MinerU 模型预取失败：%s", _classify(out))
        return False
    return weights_ready()


def _set(**fields: str) -> None:
    with _LOCK:
        _STATE.update(fields)


def start_install() -> dict[str, str]:
    """老师点击才走到这里：已装直接 done；在装复用；否则起后台线程。"""
    global _THREAD
    if sys.version_info < MIN_PYTHON:
        raise MineruSetupError(
            "底座 Python %d.%d 太旧：MinerU 4.2.3 需要 3.11–3.14。"
            % sys.version_info[:2])
    check = health()
    if check["ok"] and weights_ready():
        _set(state="done", step="体检",
             message="本地 MinerU 已就绪（%s）。" % check["version"])
        return status()
    with _LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            return dict(_STATE)
        if check["ok"]:
            _STATE.update({"state": "installing", "step": "预取模型",
                           "message": "环境已装好，正在补齐解析模型权重（国内镜像）。"})
        else:
            _STATE.update({"state": "installing", "step": "创建隔离环境",
                           "message": "正在创建 engines/mineru/ 独立环境，不碰底座 .venv。"})
        _THREAD = threading.Thread(target=_install, name="jzo-mineru-install",
                                   daemon=True)
    _THREAD.start()
    return status()


def _install() -> None:
    try:
        if not python_exe().is_file():
            rc, out = _run([sys.executable, "-m", "venv", str(engine_dir())],
                           VENV_TIMEOUT)
            if rc != 0:
                raise MineruSetupError("隔离环境创建失败：%s" % _classify(out))
        _set(step="测速选源", message="正在并行测速 pip 四家国内镜像（2 秒超时）…")
        raced = mirrors.race(mirrors.pip_candidates("mineru"))
        _set(step="安装依赖",
             message="%s 安装 %s，首次约 1–2GB，请耐心等待。"
                     % (mirrors.pick_note(raced), PACKAGE_SPEC))
        installed = False
        last_error = "没有可用镜像"
        for row in raced:
            if not row["ok"]:
                continue
            rc, out = _run(
                [str(python_exe()), "-m", "pip", "install",
                 "--no-input", "--disable-pip-version-check",
                 "--progress-bar", "off", "--timeout", "60", "--retries", "2",
                 "--index-url", row["url"], PACKAGE_SPEC], INSTALL_TIMEOUT)
            if rc == 0:
                installed = True
                break
            last_error = "%s → %s" % (row["name"], _classify(out))
            logger.warning("MinerU 镜像安装失败：%s", last_error)
            _set(message="镜像失败，换源重试中（%s）" % last_error)
        if not installed:
            raise MineruSetupError("全部镜像失败：%s" % last_error)
        _set(step="体检", message="安装完成，正在做 import 体检。")
        check = health()
        if not check["ok"]:
            raise MineruSetupError(check["message"])
        if _prefetch_weights():
            _set(state="done", step="完成",
                 message="本地 MinerU 已就绪（%s），解析模型已预取。" % check["version"])
        else:
            _set(state="done", step="完成",
                 message="本地 MinerU 已就绪（%s）；模型预取未成功，首次解析时会再试下载"
                         "（需网络，进度见批次日志）。" % check["version"])
        logger.info("[INFO] 本地 MinerU 安装完成：%s", check["version"])
    except MineruSetupError as exc:
        _set(state="error", message=str(exc))
        logger.warning("[WARN] 本地 MinerU 安装失败：%s", exc)
    except Exception as exc:  # noqa: BLE001 - 后台线程任何异常都要显性化
        _set(state="error", message="安装异常：%s" % exc)
        logger.warning("[WARN] 本地 MinerU 安装异常：%s", exc)


def uninstall() -> dict[str, Any]:
    """老师点【卸载】＋确认后才走到这里：整个 engines/mineru/ 删掉（含权重）。"""
    with _LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            raise MineruSetupError("正在安装中，不能同时卸载；等安装收口后再试。")
    folder = engine_dir()
    if folder.parent != config.PROJECT_ROOT / "engines":
        raise MineruSetupError("卸载路径不对（%s），拒绝动手。" % folder)
    if not folder.exists():
        _set(state="idle", step="", message="")
        return {"ok": True, "message": "本地 MinerU 本来就没装，无需卸载。"}
    try:
        shutil.rmtree(folder)
    except OSError as exc:
        raise MineruSetupError(
            "卸载删不掉 engines/mineru/：%s（可能有服务占用，先停再试）" % exc)
    _set(state="idle", step="", message="")
    logger.info("[INFO] 本地 MinerU 已卸载：%s", folder)
    return {"ok": True, "message": "本地 MinerU 已卸载（隔离环境＋权重全删）。"}