"""本地 VLM 一键装（2.20.0 卡§4/§7＋安装接线卡座5/6 多座泛化）：engines/vlm/ 隔离环境。

发动机（mineru-llama-cpp 自带 Vulkan 版 llama-server）三座共享；权重按座
（qwen/intern/minicpm）住 engines/vlm/models/，装拆按件互不误删。
pip 四家点击内测速选最快；pip 全败可迁移 engines/mineru 现成 Vulkan 栈
（engines 内迁移不算出网）。GGUF 三源测速选路＋sha256 逐件校验（vlm_weights）。
安装/卸载只由老师界面点击发起；体检每次现算（D3b）；失败显性化：人话进状态。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from app.core import config, toml_io
from app.core.ingest import mirrors, vlm_weights

logger = logging.getLogger(__name__)

ENGINE_PACKAGE = "mineru-llama-cpp==0.2.3"
ENGINE_MODULE = "mineru_llama_cpp"
MIN_PYTHON = (3, 11)
VENV_TIMEOUT = 300
INSTALL_TIMEOUT = 1800
TAIL_LINES = 12
ENGINE_LABELS = {"cuda": "CUDA", "vulkan": "Vulkan", "cpu": "CPU"}

_NETWORK_MARKERS = (
    "connection refused", "connection reset", "connectionerror",
    "max retries exceeded", "failed to establish", "timed out", "timeout",
    "proxyerror", "sslerror", "certificate verify failed", "getaddrinfo",
    "temporary failure in name resolution", "network is unreachable",
    "no route to host", "bad gateway", "service unavailable", "403", "404")
_NO_MATCH_MARKERS = (
    "no matching distribution", "could not find a version that satisfies",
    "from versions: none")

_LOCK = threading.Lock()
_ENGINE_LOCK = threading.Lock()
_STATE: dict[str, dict[str, str]] = {
    seat: {"state": "idle", "step": "", "message": ""} for seat in vlm_weights.SEATS}
_THREAD: dict[str, threading.Thread | None] = {seat: None for seat in vlm_weights.SEATS}


class VlmSetupError(Exception):
    """安装前置不满足或安装失败（人话原因）。"""


def _seat(seat: str) -> str:
    try:
        return vlm_weights.seat_of("vlm_" + seat)
    except vlm_weights.VlmWeightsError as exc:
        raise VlmSetupError(str(exc)) from exc


def engine_dir() -> Path:
    return config.PROJECT_ROOT / "engines" / "vlm"


def python_exe() -> Path:
    folder = engine_dir()
    return folder / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def model_paths(seat: str = "qwen") -> tuple[Path, Path]:
    """本座（主题重 GGUF, 视觉投影 mmproj）落地路径；只读，不触发起服。"""
    return vlm_weights.model_paths(seat)


def weights_ready(seat: str = "qwen") -> bool:
    """本座 GGUF 两件在不在本机；缺一律当不在。"""
    return vlm_weights.weights_ready(seat)


def _server_name() -> str:
    return "llama-server.exe" if sys.platform == "win32" else "llama-server"


def _venv_site_packages() -> Path:
    folder = engine_dir()
    if sys.platform == "win32":
        return folder / "Lib" / "site-packages"
    hits = sorted(folder.glob("lib/python*/site-packages"))
    return hits[-1] if hits else folder / "lib" / "site-packages"


def bin_dir() -> Path | None:
    """发动机二进制目录：pip 装的优先，其次离线迁移目录；都没有返回 None。"""
    for folder in (_venv_site_packages() / ENGINE_MODULE / "bin", engine_dir() / "llama-bin"):
        if (folder / _server_name()).is_file():
            return folder
    return None


def server_exe() -> Path | None:
    folder = bin_dir()
    return folder / _server_name() if folder else None


def _has_lib(folder: Path, stem: str) -> bool:
    return (folder / (stem + ".dll")).is_file() or (folder / ("lib" + stem + ".so")).is_file()


def engine_type() -> str:
    """发动机包类型现算（卡§4）：看真二进制，cuda/vulkan/cpu；没装返回空。"""
    folder = bin_dir()
    if folder is None:
        return ""
    if _has_lib(folder, "ggml-cuda"):
        return "cuda"
    if _has_lib(folder, "ggml-vulkan"):
        return "vulkan"
    return "cpu"


def _engine_version() -> str:
    folder = bin_dir()
    if folder is None:
        return ""
    if folder == engine_dir() / "llama-bin":
        marker = toml_io.load(folder / "engine.toml", {})
        return str(marker.get("version") or "迁移版")
    for info in _venv_site_packages().glob(ENGINE_MODULE + "-*.dist-info"):
        stem = info.name[: -len(".dist-info")]
        return stem.split("-", 1)[1] if "-" in stem else ""
    return ""


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
        return "镜像里没有这个版本（mineru-llama-cpp 0.2.3 需 Python 3.11+ 的预编译轮）"
    return _tail(text) or "未知原因"


def health() -> dict[str, Any]:
    """装好没有：llama-server 真二进制＋后端库现算（不出网、不起进程）。"""
    folder = bin_dir()
    if folder is None:
        return {"ok": False, "state": "missing", "version": "", "engine": "", "message": "本地 VLM 发动机未安装（缺 llama-server）。"}
    if not _has_lib(folder, "ggml"):
        return {"ok": False, "state": "error", "version": "", "engine": "", "message": "VLM 发动机文件残缺（ggml 运行库不在），请重试安装。"}
    return {"ok": True, "state": "ready", "version": _engine_version(), "engine": engine_type(), "message": ""}


def status(seat: str = "qwen") -> dict[str, str]:
    """本座安装进度快照（只读）：state=idle/installing/done/error＋step＋人话。"""
    _seat(seat)
    with _LOCK:
        return dict(_STATE[seat])


def gpu_ready(min_vram: int) -> bool:
    """能不能上显卡：真 GPU 后端＋显存过门槛；不够就 CPU 慢兜底（卡§5）。"""
    from app.core.ingest import hardware  # noqa: PLC0415 - 按需导入防循环

    return engine_type() in ("cuda", "vulkan") and float(
        hardware.probe().get("vram_gb") or 0) >= min_vram


def _set(seat: str, **fields: str) -> None:
    with _LOCK:
        _STATE[seat].update(fields)


def _mineru_bin() -> Path | None:
    """engines/mineru 现成 Vulkan 栈（迁移源）；不在返回 None。"""
    base = config.PROJECT_ROOT / "engines" / "mineru"
    folder = base / "Lib" / "site-packages" / ENGINE_MODULE / "bin"
    if sys.platform != "win32":
        hits = sorted(base.glob("lib/python*/site-packages/" + ENGINE_MODULE + "/bin"))
        folder = hits[-1] if hits else folder
    if (folder / _server_name()).is_file() and _has_lib(folder, "ggml-vulkan"):
        return folder
    return None


def _migrate_engine(seat: str) -> bool:
    """pip 全败时的离线兜底：engines 内迁移现成 Vulkan binary（不算出网）。"""
    source = _mineru_bin()
    if source is None:
        return False
    target = engine_dir() / "llama-bin"
    try:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        version = ""
        for info in source.parent.parent.glob(ENGINE_MODULE + "-*.dist-info"):
            stem = info.name[: -len(".dist-info")]
            version = stem.split("-", 1)[1] if "-" in stem else ""
        toml_io.write(target / "engine.toml", {"package": ENGINE_MODULE,
                      "version": version or "0.2.1", "origin": "engines/mineru 离线迁移"})
    except OSError as exc:
        logger.warning("[WARN] VLM 发动机迁移失败：%s", exc)
        return False
    _set(seat, message="pip 源全败，已从 engines/mineru 迁移现成 Vulkan 发动机（离线，不出网）。")
    return True


def start_install(seat: str = "qwen") -> dict[str, str]:
    """老师点击才走到这里：已装直接 done；在装复用；否则起后台线程。"""
    _seat(seat)
    label = vlm_weights.SEATS[seat]["label"]
    if sys.version_info < MIN_PYTHON:
        raise VlmSetupError("底座 Python %d.%d 太旧：mineru-llama-cpp 预编译轮需要 3.11+。"
                            % sys.version_info[:2])
    check = health()
    if check["ok"] and weights_ready(seat):
        _set(seat, state="done", step="体检", message="%s 已就绪（%s %s 发动机）。" % (
            label, check["version"], ENGINE_LABELS.get(check["engine"], check["engine"])))
        return status(seat)
    with _LOCK:
        if _THREAD[seat] is not None and _THREAD[seat].is_alive():
            return dict(_STATE[seat])
        if check["ok"]:
            _STATE[seat].update({"state": "installing", "step": "预取权重",
                                 "message": "发动机已装好，正在补齐 %s 的 GGUF 权重（国内源测速选路）。" % label})
        else:
            _STATE[seat].update({"state": "installing", "step": "创建隔离环境",
                                 "message": "正在创建 engines/vlm/ 独立环境，不碰底座 .venv。"})
        _THREAD[seat] = threading.Thread(target=_install, args=(seat,),
                                         name="jzo-vlm-%s-install" % seat, daemon=True)
    _THREAD[seat].start()
    return status(seat)


def _install_engine(seat: str) -> None:
    """测速选源装 mineru-llama-cpp；pip 全败迁移 engines/mineru 现成栈。"""
    _set(seat, step="测速选源", message="正在并行测速 pip 四家国内镜像（6 秒超时）…")
    raced = mirrors.race(mirrors.pip_candidates("mineru-llama-cpp"))
    _set(seat, step="安装发动机", message=mirrors.pick_note(raced))
    last_error = "没有可用镜像"
    for row in raced:
        if not row["ok"]:
            continue
        rc, out = _run([str(python_exe()), "-m", "pip", "install",
                        "--no-input", "--disable-pip-version-check",
                        "--progress-bar", "off", "--timeout", "60", "--retries", "2",
                        "--only-binary", ENGINE_MODULE,
                        "--index-url", row["url"], ENGINE_PACKAGE], INSTALL_TIMEOUT)
        if rc == 0:
            _set(seat, message="发动机已从 %s 装好（%s）。" % (row["name"], ENGINE_PACKAGE))
            return
        last_error = "%s → %s" % (row["name"], _classify(out))
        logger.warning("本地 VLM 镜像安装失败：%s", last_error)
        _set(seat, message="镜像失败，换源重试中（%s）" % last_error)
    if _migrate_engine(seat):
        return
    raise VlmSetupError("发动机安装全败：%s。CUDA 专轮国内镜像无货（欠账），"
                        "本机也没有可迁移的现成 Vulkan 栈。" % last_error)


def _install(seat: str) -> None:
    label = vlm_weights.SEATS[seat]["label"]
    try:
        with _ENGINE_LOCK:
            if not python_exe().is_file():
                rc, out = _run([sys.executable, "-m", "venv", str(engine_dir())], VENV_TIMEOUT)
                if rc != 0:
                    raise VlmSetupError("隔离环境创建失败：%s" % _classify(out))
            if not health()["ok"]:
                _install_engine(seat)
        _set(seat, step="体检", message="发动机安装完成，正在现算包类型体检。")
        check = health()
        if not check["ok"]:
            raise VlmSetupError(check["message"])
        engine_label = ENGINE_LABELS.get(check["engine"], check["engine"])
        if vlm_weights.prefetch(seat, lambda **fields: _set(seat, **fields)):
            _set(seat, state="done", step="完成",
                 message="%s 已就绪（mineru-llama-cpp %s，%s 发动机），GGUF 权重已预取。" % (
                     label, check["version"], engine_label))
        else:
            _set(seat, state="error", step="预取权重",
                 message="发动机已装好（%s %s），但 %s 的 GGUF 权重没预取成功：%s"
                         % (check["version"], engine_label, label,
                            status(seat).get("message") or "见运行日志"))
        logger.info("[INFO] %s 安装收口：%s", label, status(seat).get("message"))
    except VlmSetupError as exc:
        _set(seat, state="error", message=str(exc))
        logger.warning("[WARN] %s 安装失败：%s", label, exc)
    except Exception as exc:  # noqa: BLE001 - 后台线程任何异常都要显性化
        _set(seat, state="error", message="安装异常：%s" % exc)
        logger.warning("[WARN] %s 安装异常：%s", label, exc)


def uninstall(seat: str = "qwen") -> dict[str, Any]:
    """老师点【卸载】＋确认后才走到这里：只删本座两件权重（其他座不受影响）；
    全部座权重都空了才连发动机目录一起删。"""
    _seat(seat)
    label = vlm_weights.SEATS[seat]["label"]
    with _LOCK:
        if _THREAD[seat] is not None and _THREAD[seat].is_alive():
            raise VlmSetupError("正在安装中，不能同时卸载；等安装收口后再试。")
    folder = engine_dir()
    if folder.parent != config.PROJECT_ROOT / "engines":
        raise VlmSetupError("卸载路径不对（%s），拒绝动手。" % folder)
    if not folder.exists():
        _set(seat, state="idle", step="", message="")
        return {"ok": True, "message": "%s 本来就没装，无需卸载。" % label}
    models = folder / "models"
    try:
        for path in model_paths(seat):
            path.unlink(missing_ok=True)
        remaining = sorted(models.glob("*")) if models.is_dir() else []
        if not remaining:
            shutil.rmtree(folder)
            _set(seat, state="idle", step="", message="")
            logger.info("[INFO] 本地 VLM 已全卸：%s", folder)
            return {"ok": True, "message": "本地 VLM 已卸载（发动机＋权重全删）。"}
    except OSError as exc:
        raise VlmSetupError("卸载删不掉 engines/vlm/：%s（可能有服务占用，先停再试）" % exc)
    _set(seat, state="idle", step="", message="")
    logger.info("[INFO] %s 权重已卸载（其他座保留）", label)
    return {"ok": True, "message": "%s 本座两件权重已删（其他座不受影响）。" % label}