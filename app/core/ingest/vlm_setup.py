"""本地 VLM 一键装（T6 §3）：engines/vlm/ 独立 venv＋GGUF 权重预取＋subprocess 体检。

mineru 隔离环境带的是 mineru_llama_cpp 进程内 fork（无 llama_cpp.server），
故按卡走「不带」分支：独立环境装 llama-cpp-python（MIT 核许可，不装 torch）。
CPU 预编译轮来自 abetlen 官方轮索引（PyPI 只有 sdist），其余依赖走国内镜像；
GGUF 权重（Qwen2.5-VL-3B-Instruct Q4_K_M＋mmproj）从 modelscope 国内源点击预取，
sha256 逐文件校验。安装只由老师点【安装本地 VLM】发起；体检每次现算（D3b）；
失败显性化：人话原因进状态，不静默。
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.core import config

logger = logging.getLogger(__name__)

PACKAGE_SPEC = "llama-cpp-python[server]==0.3.36"
WHEEL_INDEX = "https://abetlen.github.io/llama-cpp-python/whl/cpu"
MIRRORS = (
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple/",
)
MODEL_REPO = "unsloth/Qwen2.5-VL-3B-Instruct-GGUF"
MODEL_BASE = "https://modelscope.cn/models/%s/resolve/master/" % MODEL_REPO
# （文件名, 字节数, sha256）：modelscope 仓库页实测核对（2026-11-19）。
GGUF_FILES = (
    ("Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf", 1929901408,
     "c47e8c1f6fb3e8cff6ec58909baff16dbeffb64a5bb3b746b96e05e6334c129f"),
    ("mmproj-F16.gguf", 1338428256,
     "4c1240f514de94c81b70709b0f9a80c7e3297598ea7c83f39dc00b18ee5be60c"),
)
MIN_PYTHON = (3, 11)
VENV_TIMEOUT = 300
INSTALL_TIMEOUT = 1800
HEALTH_TIMEOUT = 180
WEIGHT_TIMEOUT = 3600
TAIL_LINES = 12

_CHECK_CODE = (
    "from importlib.metadata import version\n"
    "import llama_cpp\n"
    "print('LLAMA_CPP_VERSION=' + version('llama-cpp-python'))\n"
)

_NETWORK_MARKERS = (
    "connection refused", "connection reset", "connectionerror",
    "max retries exceeded", "failed to establish", "timed out", "timeout",
    "proxyerror", "sslerror", "certificate verify failed",
    "temporary failure in name resolution", "getaddrinfo",
    "network is unreachable", "no route to host", "bad gateway",
    "service unavailable", "403", "404",
)
_NO_MATCH_MARKERS = (
    "no matching distribution", "could not find a version that satisfies",
    "from versions: none",
)

_LOCK = threading.Lock()
_STATE: dict[str, str] = {"state": "idle", "step": "", "message": ""}
_THREAD: threading.Thread | None = None


class VlmSetupError(Exception):
    """安装前置不满足或安装失败（人话原因）。"""


def engine_dir() -> Path:
    return config.PROJECT_ROOT / "engines" / "vlm"


def python_exe() -> Path:
    folder = engine_dir()
    return folder / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def model_paths() -> tuple[Path, Path]:
    """（主题重 GGUF, 视觉投影 mmproj）落地路径；只读，不触发起服。"""
    folder = engine_dir() / "models"
    return folder / GGUF_FILES[0][0], folder / GGUF_FILES[1][0]


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
        return "镜像里没有这个版本（llama-cpp-python 0.3.36 需 Python 3.11+ 的预编译轮）"
    return _tail(text) or "未知原因"


def health() -> dict[str, Any]:
    """装好没有：独立环境解释器在不在＋import/版本探测。每次现算（D3b）。"""
    py = python_exe()
    if not py.is_file():
        return {"ok": False, "state": "missing", "version": "",
                "message": "本地 VLM 未安装。"}
    rc, out = _run([str(py), "-c", _CHECK_CODE], HEALTH_TIMEOUT)
    version = ""
    for line in out.splitlines():
        if line.startswith("LLAMA_CPP_VERSION="):
            version = line.split("=", 1)[1].strip()
    if rc == 0 and version:
        return {"ok": True, "state": "ready", "version": version, "message": ""}
    return {"ok": False, "state": "error", "version": "",
            "message": "VLM 环境在但体检失败：%s" % _classify(out)}


def status() -> dict[str, str]:
    """安装进度快照（只读）：state=idle/installing/done/error＋step＋人话。"""
    with _LOCK:
        return dict(_STATE)


def weights_ready() -> bool:
    """GGUF 两件在不在本机（只读按字节数核对，不出网）；缺一律当不在。"""
    for path, (_name, size, _digest) in zip(model_paths(), GGUF_FILES):
        try:
            if not path.is_file() or path.stat().st_size != size:
                return False
        except OSError:
            return False
    return True


def _set(**fields: str) -> None:
    with _LOCK:
        _STATE.update(fields)


def _download_gguf(name: str, size: int, digest: str) -> None:
    """单件流式下载＋sha256 校验＋原子改名；失败抛 VlmSetupError（人话）。"""
    target = engine_dir() / "models" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    url = MODEL_BASE + name
    hasher = hashlib.sha256()
    written = 0
    try:
        with urllib.request.urlopen(url, timeout=120) as response, \
                part.open("wb") as sink:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                sink.write(chunk)
                hasher.update(chunk)
                written += len(chunk)
                _set(message="正在下载 %s（%.1f/%.1fGB，国内镜像）…"
                     % (name, written / 1e9, size / 1e9))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        part.unlink(missing_ok=True)
        raise VlmSetupError("权重下载失败（%s）：%s" % (name, _classify(str(exc))))
    if written != size or hasher.hexdigest() != digest:
        part.unlink(missing_ok=True)
        raise VlmSetupError("权重校验不过（%s）：字节数或 sha256 与仓库登记不符，已丢弃重来。" % name)
    part.replace(target)


def _prefetch_weights() -> bool:
    """GGUF 预取并入安装点击：modelscope 国内源，两件逐一校验。"""
    _set(step="预取权重",
         message="正在从国内镜像预取 GGUF 权重（Q4_K_M＋mmproj，约 3.2GB），请耐心等待。")
    try:
        for name, size, digest in GGUF_FILES:
            target = engine_dir() / "models" / name
            if target.is_file() and target.stat().st_size == size:
                continue
            _download_gguf(name, size, digest)
    except VlmSetupError as exc:
        logger.warning("[WARN] 本地 VLM 权重预取失败：%s", exc)
        _set(message=str(exc))
        return False
    return weights_ready()


def start_install() -> dict[str, str]:
    """老师点击才走到这里：已装直接 done；在装复用；否则起后台线程。"""
    global _THREAD
    if sys.version_info < MIN_PYTHON:
        raise VlmSetupError(
            "底座 Python %d.%d 太旧：llama-cpp-python 预编译轮需要 3.11+。"
            % sys.version_info[:2])
    check = health()
    if check["ok"] and weights_ready():
        _set(state="done", step="体检",
             message="本地 VLM 已就绪（llama-cpp %s）。" % check["version"])
        return status()
    with _LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            return dict(_STATE)
        if check["ok"]:
            _STATE.update({"state": "installing", "step": "预取权重",
                           "message": "环境已装好，正在补齐 GGUF 权重（国内镜像）。"})
        else:
            _STATE.update({"state": "installing", "step": "创建隔离环境",
                           "message": "正在创建 engines/vlm/ 独立环境，不碰底座 .venv。"})
        _THREAD = threading.Thread(target=_install, name="jzo-vlm-install",
                                   daemon=True)
    _THREAD.start()
    return status()


def _install() -> None:
    try:
        if not python_exe().is_file():
            rc, out = _run([sys.executable, "-m", "venv", str(engine_dir())],
                           VENV_TIMEOUT)
            if rc != 0:
                raise VlmSetupError("隔离环境创建失败：%s" % _classify(out))
        _set(step="安装依赖",
             message="从国内镜像安装 %s（CPU 预编译轮＋服务依赖），请耐心等待。" % PACKAGE_SPEC)
        installed = False
        last_error = "没有可用镜像"
        for index in MIRRORS:
            rc, out = _run(
                [str(python_exe()), "-m", "pip", "install",
                 "--no-input", "--disable-pip-version-check",
                 "--progress-bar", "off", "--timeout", "60", "--retries", "2",
                 "--only-binary", "llama-cpp-python",
                 "--index-url", index, "--extra-index-url", WHEEL_INDEX,
                 PACKAGE_SPEC], INSTALL_TIMEOUT)
            if rc == 0:
                installed = True
                break
            last_error = "%s → %s" % (index, _classify(out))
            logger.warning("本地 VLM 镜像安装失败：%s", last_error)
            _set(message="镜像失败，换源重试中（%s）" % last_error)
        if not installed:
            raise VlmSetupError("全部镜像失败：%s" % last_error)
        _set(step="体检", message="安装完成，正在做 import 体检。")
        check = health()
        if not check["ok"]:
            raise VlmSetupError(check["message"])
        if _prefetch_weights():
            _set(state="done", step="完成",
                 message="本地 VLM 已就绪（llama-cpp %s），GGUF 权重已预取。" % check["version"])
        else:
            _set(state="error", step="预取权重",
                 message="环境已装好（llama-cpp %s），但 GGUF 权重没预取成功：%s"
                         % (check["version"], status().get("message") or "见运行日志"))
        logger.info("[INFO] 本地 VLM 安装收口：%s", status().get("message"))
    except VlmSetupError as exc:
        _set(state="error", message=str(exc))
        logger.warning("[WARN] 本地 VLM 安装失败：%s", exc)
    except Exception as exc:  # noqa: BLE001 - 后台线程任何异常都要显性化
        _set(state="error", message="安装异常：%s" % exc)
        logger.warning("[WARN] 本地 VLM 安装异常：%s", exc)