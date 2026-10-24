"""切库重启：让底座在新工作区的插件与配置下重新起来。

为什么不用 ``os.execv``：Windows 没有真正的 exec，旧进程仍会占着监听端口，
新进程必然 ``WinError 10048``。改用一次性 ``.bat``：等旧 PID 真正退出 →
在原目录用同一解释器拉起 uvicorn → 自删。等待循环用 ``for /f`` 读 tasklist
的 CSV 输出（不碰 ``find``，Git Bash 的 find.exe 会抢占 PATH 让整篇脚本终止），
睡眠用 ``ping``（DETACHED_PROCESS 没有控制台，``timeout`` 不可靠）——两条
都是 v0.9.0 真机压测换来的教训，见 :mod:`app.core.plugin_update`。

``/healthz`` 回 ``boot_id``：每次进程启动生成一次。前端只有在看到 boot_id
变化后才重载页面，旧进程退出前的 200 不会被误认成「已经恢复」。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.plugin_update import _write_batch_script

BOOT_ID = uuid.uuid4().hex


def boot_id() -> str:
    """本次进程的身份证；重启后必然不同。"""
    return BOOT_ID


def restart_disabled() -> bool:
    """测试/受控环境的总闸：置 1 时只切指针、不重启。

    ``JZO_RESTART_DISABLED=1`` 让单测里的服务器在收到切换请求后仍能活着回包；
    生产不设它，切换一律走真实重启。
    """
    return os.environ.get("JZO_RESTART_DISABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def build_restart_script(*, pid: int, root: Path, python_exe: str, host: str, port: int) -> str:
    """生成一次性重启脚本的内容（纯字符串，便于逐条断言）。"""
    lines = [
        "@echo off",
        "rem 九章算子切库重启（一次性脚本，跑完自删；由用户确认切换工作区后生成）",
        "setlocal",
        f'set "JZO_ROOT={root}"',
        f'set "JZO_PID={pid}"',
        "echo [1/3] 等待底座进程退出...",
        ":wait_exit",
        'set "JZO_ALIVE=0"',
        r'for /f "usebackq tokens=2 delims=," %%p in (`""%SystemRoot%\System32\tasklist.exe" /FI "PID eq %JZO_PID%" /NH /FO CSV"`) do if "%%~p"=="%JZO_PID%" set "JZO_ALIVE=1"',
        'if "%JZO_ALIVE%"=="1" (',
        r'  "%SystemRoot%\System32\ping.exe" -n 2 127.0.0.1 >nul',
        "  goto wait_exit",
        ")",
        "echo [2/3] 在新工作区上重新拉起底座",
        'cd /d "%JZO_ROOT%"',
        f'start "" "{python_exe}" -m uvicorn app.main:app --host {host} --port {int(port)}',
        "echo [3/3] 清理临时脚本",
        'del "%~f0"',
        "endlocal",
        "",
    ]
    return "\r\n".join(lines)


def prepare_restart(*, port: int | None = None) -> dict[str, Any] | None:
    """落盘一次性脚本并接好日志；``JZO_RESTART_DISABLED=1`` 时返回 ``None``。

    只准备、不执行：调用方先把工作区指针写稳，再 :func:`launch_restart`，
    避免「脚本没生成但指针已改」的半截状态。
    """
    if restart_disabled():
        return None
    root = Path(settings.project_root)
    script_path = Path(tempfile.gettempdir()) / f"jzo_restart_{os.getpid()}.bat"
    log_path = script_path.with_name(script_path.stem + ".log")
    script = build_restart_script(
        pid=os.getpid(),
        root=root,
        python_exe=sys.executable,
        host=settings.host,
        port=int(port or settings.port),
    )
    _write_batch_script(script_path, script)
    return {"script_path": script_path, "log_path": log_path, "root": root}


def launch_restart(prepared: dict[str, Any], *, delay: float = 1.5) -> None:
    """拉起脚本，并在 ``delay`` 秒后结束当前进程，给 HTTP 响应留出落地时间。

    脚本的 stdout/stderr 一律接日志文件：DETACHED_PROCESS 下没有控制台，
    ``echo`` 写控制台失败会让整篇批处理当场终止，重启也就不会发生。
    """
    script_path: Path = prepared["script_path"]
    log_path: Path = prepared["log_path"]
    handle = open(log_path, "ab")
    try:
        subprocess.Popen(
            ["cmd.exe", "/c", str(script_path)], cwd=str(prepared["root"]),
            stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    finally:
        handle.close()
    timer = threading.Timer(delay, _exit_process)
    timer.daemon = True
    timer.start()


def _exit_process() -> None:
    """硬退出：uvicorn 的优雅关闭会等连接排空，而这里要的是「立刻腾出端口」。"""
    os._exit(0)
