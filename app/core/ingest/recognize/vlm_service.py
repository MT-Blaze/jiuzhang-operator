"""本地 VLM 服务编排（T6 §3／2.20.0 卡§4＋安装接线卡座5/6 多座泛化）：
懒起 llama-server＋动态端口＋随机令牌；单活座——切座先显式停旧座再起新座。
复用前用 /props 自检加载的是不是本座当前权重（死实例不复用）；服务闲停
20 分钟自动停（单题上限 900s＜1200s，推理中不会被误杀）。

镜像 mineru_service 的收口纪律：只有解析/重认作业真要用才起服（出网铁律：
绝不在 app 启动时顺手起）；安装只由老师点【安装】发起，未安装一律
诚实失败引导去点安装。发动机＝mineru-llama-cpp 自带的原生 llama-server
（三座共享；Vulkan/CUDA 后端 -ngl 999；显存不够或纯 CPU 包 -ngl 0 慢兜底，卡§5）。
服务起不来/推理失败＝作业失败清单显性（router 口径），不静默回 auto。
stop 杀整棵进程树＋端口复验，挂 lifespan shutdown 收口。
"""

from __future__ import annotations

import logging
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from app.core import wire
from app.core.ingest import vlm_setup, vlm_weights

logger = logging.getLogger(__name__)

START_TIMEOUT = 600
HEALTH_POLL_SECONDS = 1.0
REQUEST_TIMEOUT = 5
# 单题上限 900s（15 分钟）< 20 分钟闲停，推理中不会被误杀。
WARM_IDLE_SECONDS = 20 * 60
WATCH_INTERVAL_SECONDS = 30

_LOCK = threading.Lock()
_PROC: subprocess.Popen | None = None
_PORT = 0
_TOKEN = ""
_SEAT = ""
_LOG_HANDLE = None
_LAST_USED = 0.0
_WATCHDOG: threading.Thread | None = None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _health_ok(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(base_url + "/health",
                                    timeout=REQUEST_TIMEOUT) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def _serves_expected_model(base_url: str, token: str, model_path: Any) -> bool:
    """在跑的服务加载的是不是本座当前权重（/props 的 model_path 比文件名）。
    非 200／解析失败／字段缺失一律 False：宁重启，不复用能应答但答不对的死实例。"""
    request = urllib.request.Request(
        base_url + "/props", headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            if response.status != 200:
                return False
            body = wire.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False
    served = body.get("model_path") if isinstance(body, dict) else None
    if not isinstance(served, str) or not served:
        return False
    return (os.path.normcase(os.path.basename(served))
            == os.path.normcase(os.path.basename(str(model_path))))


def touch() -> None:
    """记一次使用（推理请求前/后）；服务没跑静默无操作。"""
    with _LOCK:
        _touch_locked()


def _touch_locked() -> None:
    global _LAST_USED
    if _PROC is not None and _PROC.poll() is None:
        _LAST_USED = time.monotonic()


def _idle_expired(last_used: float, now: float) -> bool:
    """闲停判定纯函数（便于单测不睡 20 分钟）：超过 WARM_IDLE_SECONDS 才算。"""
    return last_used > 0 and now - last_used > WARM_IDLE_SECONDS


def _watchdog_tick(now: float) -> bool:
    """看门狗一次检查（锁内）：进程活且闲停超时 → 停服；真停了返回 True。"""
    with _LOCK:
        if _PROC is None or _PROC.poll() is not None:
            return False
        if not _idle_expired(_LAST_USED, now):
            return False
        logger.info("[INFO] 本地 VLM 服务闲停超过 %d 分钟，自动停止释放显存",
                    WARM_IDLE_SECONDS // 60)
        _kill_locked()
        return True


def _watchdog_loop() -> None:
    while True:
        time.sleep(WATCH_INTERVAL_SECONDS)
        try:
            _watchdog_tick(time.monotonic())
        except Exception:  # noqa: BLE001 - 看门狗异常不许拖垮主流程
            pass


def _start_watchdog() -> None:
    """首个服务就绪时起唯一 daemon 看门狗；调用方已持锁（线程先睡再查，不抢锁）。"""
    global _WATCHDOG
    if _WATCHDOG is not None and _WATCHDOG.is_alive():
        return
    _WATCHDOG = threading.Thread(target=_watchdog_loop,
                                 name="jzo-vlm-idle-watchdog", daemon=True)
    _WATCHDOG.start()


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def endpoint() -> dict[str, str] | None:
    """在跑的服务地址＋令牌；没起服返回 None（只读，不触发起服）。"""
    with _LOCK:
        if _PROC is None or _PROC.poll() is not None:
            return None
        return {"base_url": "http://127.0.0.1:%d" % _PORT, "token": _TOKEN}


def active_seat() -> str:
    """当前在跑的座键（qwen/intern/minicpm）；没起服返回空串（只读）。"""
    with _LOCK:
        if _PROC is None or _PROC.poll() is not None:
            return ""
        return _SEAT


def ensure_ready(seat: str = "qwen") -> dict[str, Any]:
    """作业入口：未安装/权重缺诚实失败引导点安装；已装懒起服（在跑同座复用、
    异座显式切换）。"""
    label = vlm_weights.SEATS.get(seat, {}).get("label", seat)
    check = vlm_setup.health()
    if not check["ok"]:
        return {"ok": False,
                "detail": "本地 VLM 未就绪（%s）。请到【模型配置】点【安装】，"
                          "装好后再选本引擎。" % (check.get("message") or check.get("state"))}
    if not vlm_setup.weights_ready(seat):
        return {"ok": False,
                "detail": "「%s」的 GGUF 权重不在本机。请到【模型配置】点【安装】"
                          "补齐权重（国内镜像），装好后再选本引擎。" % label}
    return start(seat)


def _min_vram(seat: str = "qwen") -> int:
    """显存门槛是插件 catalog 数据（本座 id=vlm_<seat> 条目）；目录缺失按 6G 保守。"""
    from app.core.ingest import registry  # noqa: PLC0415 - 按需导入防循环

    entry_id = "vlm_" + seat
    for item in registry.catalog():
        if str(item.get("id") or "") == entry_id:
            try:
                return int(item.get("min_vram") or 6)
            except (TypeError, ValueError):
                return 6
    return 6


def start(seat: str = "qwen") -> dict[str, Any]:
    """起本地推理服务：动态空闲端口＋每次随机令牌；并发锁防双起。
    单活座：在跑同座且健康＝复用；在跑异座＝先显式停旧座再起新座。"""
    global _PROC, _PORT, _TOKEN, _SEAT, _LOG_HANDLE
    label = vlm_weights.SEATS.get(seat, {}).get("label", seat)
    with _LOCK:
        if _PROC is not None and _PROC.poll() is None:
            base_url = "http://127.0.0.1:%d" % _PORT
            healthy = _health_ok(base_url)
            if (_SEAT == seat and healthy
                    and _serves_expected_model(base_url, _TOKEN,
                                               vlm_setup.model_paths(seat)[0])):
                _touch_locked()
                _start_watchdog()
                return {"ok": True, "base_url": base_url, "token": _TOKEN,
                        "seat": seat, "seat_label": label,
                        "detail": "复用已在跑的本地 VLM 服务（%s）" % label}
            if _SEAT == seat and healthy:
                logger.warning("[WARN] 复用自检不通过：服务装的不是本座当前权重，重启")
            if _SEAT != seat:
                logger.info("[INFO] 本地 VLM 切座：%s → %s，先停旧座", _SEAT or "无", label)
            _kill_locked()
        exe = vlm_setup.server_exe()
        model, mmproj = vlm_setup.model_paths(seat)
        if exe is None or not model.is_file() or not mmproj.is_file():
            return {"ok": False,
                    "detail": "本地 VLM 发动机或「%s」权重不在（%s），请在【模型配置】重试安装。"
                              % (label, model)}
        gpu = vlm_setup.gpu_ready(_min_vram(seat))
        layers = "999" if gpu else "0"
        _PORT = _free_port()
        _TOKEN = secrets.token_hex(16)
        _SEAT = seat
        base_url = "http://127.0.0.1:%d" % _PORT
        env = os.environ.copy()
        log_path = vlm_setup.engine_dir() / "service.log"
        try:
            _LOG_HANDLE = log_path.open("a", encoding="utf-8", errors="replace")
            kwargs: dict[str, Any] = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            _PROC = subprocess.Popen(
                [str(exe), "--model", str(model), "--mmproj", str(mmproj),
                 "--host", "127.0.0.1", "--port", str(_PORT),
                 "--api-key", _TOKEN, "-ngl", layers,
                 "--ctx-size", "8192", "--jinja"],
                stdout=_LOG_HANDLE, stderr=subprocess.STDOUT, env=env,
                cwd=str(vlm_setup.engine_dir()), **kwargs)
        except OSError as exc:
            _close_log_locked()
            return {"ok": False, "detail": "本地 VLM 服务起不来：%s" % exc}
        deadline = time.monotonic() + START_TIMEOUT
        while time.monotonic() < deadline:
            if _PROC.poll() is not None:
                tail = _log_tail(log_path)
                _kill_locked()
                return {"ok": False,
                        "detail": "本地 VLM 服务（%s）提前退出：%s" % (label, tail)}
            if _health_ok(base_url):
                logger.info("[INFO] 本地 VLM 服务就绪：%s 端口 %d（%s）", label, _PORT,
                            "GPU -ngl 999" if gpu else "CPU 慢兜底 -ngl 0")
                _touch_locked()
                _start_watchdog()
                return {"ok": True, "base_url": base_url, "token": _TOKEN,
                        "seat": seat, "seat_label": label,
                        "detail": "本地 VLM 服务已就绪（%s，%s）"
                                  % (label, "显卡加速" if gpu else "CPU 慢兜底")}
            time.sleep(HEALTH_POLL_SECONDS)
        _kill_locked()
        return {"ok": False,
                "detail": "本地 VLM 服务（%s）%d 秒内没就绪（首载 GGUF 可能超时），"
                          "详情见 engines/vlm/service.log。" % (label, START_TIMEOUT)}


def _log_tail(log_path) -> str:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "日志读不到"
    return " / ".join(text.splitlines()[-8:])[:400] or "无日志输出"


def _close_log_locked() -> None:
    global _LOG_HANDLE
    if _LOG_HANDLE is not None:
        try:
            _LOG_HANDLE.close()
        except OSError:
            pass
        _LOG_HANDLE = None


def _kill_locked() -> None:
    """杀整棵进程树（Windows 用 taskkill /T 点杀，禁 /IM）＋端口复验。"""
    global _PROC, _PORT, _SEAT
    proc, port = _PROC, _PORT
    _PROC = None
    _SEAT = ""
    if proc is not None and proc.poll() is None:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, timeout=30)
        else:
            proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
    _close_log_locked()
    if port:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and _port_open(port):
            time.sleep(0.3)
    _PORT = 0


def stop() -> dict[str, Any]:
    """显式收口：杀子进程树＋端口复验关闭；没在跑也如实回报。"""
    with _LOCK:
        was_running = _PROC is not None and _PROC.poll() is None
        port = _PORT
        _kill_locked()
        closed = not port or not _port_open(port)
    if not closed:
        logger.warning("[WARN] 本地 VLM 服务端口 %d 收口后仍开着", port)
    return {"ok": closed, "was_running": was_running, "port": port,
            "port_closed": closed,
            "detail": "本地 VLM 服务已停" if closed else "端口 %d 仍开着" % port}