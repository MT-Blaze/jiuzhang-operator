"""本地 VLM 服务编排（T6 §3）：懒起服＋动态端口＋随机令牌＋健康轮询＋孤儿零容忍。

镜像 mineru_service 的收口纪律：只有解析/重认作业真要用才起服（出网铁律：
绝不在 app 启动时顺手起）；安装只由老师点【安装本地 VLM】发起，未安装一律
诚实失败引导去点安装。服务起不来/推理失败＝作业失败清单显性（router 口径），
不静默回 auto。stop 杀整棵进程树＋端口复验，挂 lifespan shutdown 收口。
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

from app.core.ingest import vlm_setup

logger = logging.getLogger(__name__)

START_TIMEOUT = 600
HEALTH_POLL_SECONDS = 1.0
REQUEST_TIMEOUT = 5

_LOCK = threading.Lock()
_PROC: subprocess.Popen | None = None
_PORT = 0
_TOKEN = ""
_LOG_HANDLE = None


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


def ensure_ready() -> dict[str, Any]:
    """作业入口：未安装/权重缺诚实失败引导点安装；已装懒起服（在跑复用）。"""
    check = vlm_setup.health()
    if not check["ok"]:
        return {"ok": False,
                "detail": "本地 VLM 未就绪（%s）。请到【模型配置】点【安装本地 VLM】，"
                          "装好后再选本引擎。" % (check.get("message") or check.get("state"))}
    if not vlm_setup.weights_ready():
        return {"ok": False,
                "detail": "本地 VLM 的 GGUF 权重不在本机。请到【模型配置】点【安装本地 VLM】"
                          "补齐权重（国内镜像），装好后再选本引擎。"}
    return start()


def start() -> dict[str, Any]:
    """起本地推理服务：动态空闲端口＋每次随机令牌；并发锁防双起。"""
    global _PROC, _PORT, _TOKEN, _LOG_HANDLE
    with _LOCK:
        if _PROC is not None and _PROC.poll() is None:
            base_url = "http://127.0.0.1:%d" % _PORT
            if _health_ok(base_url):
                return {"ok": True, "base_url": base_url, "token": _TOKEN,
                        "detail": "复用已在跑的本地 VLM 服务"}
            _kill_locked()
        py = vlm_setup.python_exe()
        model, mmproj = vlm_setup.model_paths()
        if not py.is_file() or not model.is_file() or not mmproj.is_file():
            return {"ok": False,
                    "detail": "本地 VLM 服务入口或权重不在（%s），请在【模型配置】重试安装。" % model}
        _PORT = _free_port()
        _TOKEN = secrets.token_hex(16)
        base_url = "http://127.0.0.1:%d" % _PORT
        env = os.environ.copy()
        log_path = vlm_setup.engine_dir() / "service.log"
        try:
            _LOG_HANDLE = log_path.open("a", encoding="utf-8", errors="replace")
            kwargs: dict[str, Any] = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            _PROC = subprocess.Popen(
                [str(py), "-m", "llama_cpp.server",
                 "--model", str(model), "--chat_format", "qwen2.5-vl",
                 "--clip_model_path", str(mmproj),
                 "--host", "127.0.0.1", "--port", str(_PORT),
                 "--api_key", _TOKEN, "--n_gpu_layers", "0", "--n_ctx", "8192"],
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
                        "detail": "本地 VLM 服务提前退出：%s" % tail}
            if _health_ok(base_url):
                logger.info("[INFO] 本地 VLM 服务就绪：端口 %d", _PORT)
                return {"ok": True, "base_url": base_url, "token": _TOKEN,
                        "detail": "本地 VLM 服务已就绪"}
            time.sleep(HEALTH_POLL_SECONDS)
        _kill_locked()
        return {"ok": False,
                "detail": "本地 VLM 服务 %d 秒内没就绪（首载 GGUF 可能超时），"
                          "详情见 engines/vlm/service.log。" % START_TIMEOUT}


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
    global _PROC, _PORT
    proc, port = _PROC, _PORT
    _PROC = None
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