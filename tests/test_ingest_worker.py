# -*- coding: utf-8 -*-
"""后台解析不堵事件循环（#INGEST-UX-01）：假卡死回归判据。

钉住两条：
- 「开始解析 <文件名>」必须在重活（页图渲染）开工**之前**落盘，
  解析中途轮询批次就能看到 progress 流水，而不是收口一起跳；
- 重活跑在单工作线程上（线程号 ≠ 事件循环线程号），解析进行中
  /healthz 与批次列表照常秒回，POST 响应不等重活。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ingest_worker``
"""

from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import config  # noqa: E402
from app.core.ingest import service as ingest  # noqa: E402
from app.core.pending import service  # noqa: E402

TOKEN = "ingest-worker-token"


def _data_url(text: str) -> str:
    return "data:text/markdown;base64," + base64.b64encode(
        text.encode("utf-8")).decode("ascii")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get(url: str, timeout: float) -> tuple[int, float, str]:
    t0 = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, time.time() - t0, resp.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, time.time() - t0, repr(exc)


class StartLinePersistTest(unittest.IsolatedAsyncioTestCase):
    """重活开工那一刻，开头流水必须已经在库里（不是收口一起跳）。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._saved_env = os.environ.get("JZO_DATA_DIR")
        self._saved_ws = config.settings.workspace_id
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        config.settings.workspace_id = None
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._saved_env is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = self._saved_env
        config.settings.workspace_id = self._saved_ws
        self.tmp.cleanup()

    async def test_start_line_on_disk_before_heavy_work(self) -> None:
        staged = ingest.stage_ingest([{"name": "小卷.md", "data_url": _data_url(
            "1. 求 $x+1=2$ 的解。\n答案：$x=1$。\n")}])
        group = staged["jobs"][0]
        seen: dict[str, Any] = {}

        def peek(*args: Any, **kwargs: Any) -> tuple[list, list, list]:
            seen["route"] = service.read_batch_route(group["batch_id"])
            seen["thread"] = threading.get_ident()
            return [], [], []

        with mock.patch.object(ingest.page_render, "build_pages", side_effect=peek):
            await ingest.run_ingest_jobs(group["batch_id"], group["jobs"],
                                         group["layout_engine"], group["recognize_engine"])
        route = seen.get("route") or {}
        progress = route.get("progress") or []
        self.assertTrue(any("开始解析" in str(entry.get("text") or "")
                            for entry in progress),
                        "重活开工前「开始解析」必须已落盘")
        self.assertFalse(route.get("done"), "中途快照不许提前收口")


class WorkerThreadHttpTest(unittest.TestCase):
    """真 HTTP：重活线程 ≠ 循环线程；解析进行中底座照常应答。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(cls.tmp.name)
        cls.worker_marker = root / "worker_thread.txt"
        cls.loop_marker = root / "loop_thread.txt"
        port = _free_port()
        cls.base = f"http://127.0.0.1:{port}"
        # 服务进程内打桩：build_pages 睡 3 秒模拟重活并记下工作线程号；
        # stage_ingest 在 async 端点里直跑，记下事件循环线程号。
        code = (
            "import threading, time, uvicorn\n"
            "from app.core.ingest.render import service as pr\n"
            "from app.core.ingest import service as ing\n"
            f"worker_marker = {str(cls.worker_marker)!r}\n"
            f"loop_marker = {str(cls.loop_marker)!r}\n"
            "orig_build = pr.build_pages\n"
            "def slow_build(*a, **k):\n"
            "    open(worker_marker, 'w').write(str(threading.get_ident()))\n"
            "    time.sleep(3)\n"
            "    return orig_build(*a, **k)\n"
            "pr.build_pages = slow_build\n"
            "orig_stage = ing.stage_ingest\n"
            "def stage(*a, **k):\n"
            "    open(loop_marker, 'w').write(str(threading.get_ident()))\n"
            "    return orig_stage(*a, **k)\n"
            "ing.stage_ingest = stage\n"
            f"uvicorn.run('app.main:app', host='127.0.0.1', port={port}, log_level='warning')\n"
        )
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(root / "data")
        env["JZO_PLUGINS_DIR"] = str(root / "plugins")
        env["JZO_LOCAL_TOKEN"] = TOKEN
        (root / "data").mkdir()
        (root / "plugins").mkdir()
        cls.proc = subprocess.Popen(
            [sys.executable, "-c", code], cwd=str(ROOT), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        deadline = time.time() + 20
        while time.time() < deadline:
            if cls.proc.poll() is not None:
                raise RuntimeError("服务没起来：" + (cls.proc.stdout.read() or ""))
            status, _, _ = _get(cls.base + "/healthz", 0.5)
            if status == 200:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("服务 20 秒没就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
        cls.tmp.cleanup()

    def test_heavy_work_off_loop_and_loop_stays_responsive(self) -> None:
        payload = {"files": [{"name": "小卷.md", "data_url": _data_url(
            "1. 求 $x+1=2$ 的解。\n答案：$x=1$。\n")}]}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base + "/api/ingest/files", data=body, method="POST",
            headers={"Content-Type": "application/json", "X-JZO-Token": TOKEN})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=30) as resp:
            staged = json.loads(resp.read().decode("utf-8"))
        post_seconds = time.time() - t0
        self.assertEqual(staged.get("parsing"), True)
        self.assertLess(post_seconds, 2.0, "响应不许等重活（桩睡 3 秒）")
        batch_id = staged["batch_id"]

        deadline = time.time() + 10
        while time.time() < deadline and not self.worker_marker.exists():
            time.sleep(0.05)
        self.assertTrue(self.worker_marker.exists(), "重活桩没开工")
        # 重活正睡：事件循环必须照常应答，且开头流水已可轮询到。
        status, health_seconds, _ = _get(self.base + "/healthz", 2.0)
        self.assertEqual(status, 200)
        self.assertLess(health_seconds, 0.5, "解析中 /healthz 被堵")
        status, list_seconds, raw = _get(self.base + "/api/pending/batches", 2.0)
        self.assertEqual(status, 200)
        self.assertLess(list_seconds, 0.5, "解析中批次列表被堵")
        cards = json.loads(raw).get("batches") or []
        card = next((c for c in cards if c.get("batch_id") == batch_id), None)
        self.assertIsNotNone(card)
        route = card.get("route") or {}
        progress = route.get("progress") or []
        self.assertTrue(any("开始解析" in str(entry.get("text") or "")
                            for entry in progress), "中途必须看得到开头流水")
        self.assertFalse(route.get("done"), "重活没完不许收口")

        deadline = time.time() + 30
        finished = False
        while time.time() < deadline:
            status, _, raw = _get(self.base + "/api/pending/batches", 2.0)
            if status == 200:
                cards = json.loads(raw).get("batches") or []
                card = next((c for c in cards if c.get("batch_id") == batch_id), {})
                texts = [str(entry.get("text") or "")
                         for entry in (card.get("route") or {}).get("progress") or []]
                if any("落池完成" in text for text in texts):
                    finished = True
                    break
            time.sleep(0.2)
        self.assertTrue(finished, "收口流水 30 秒内必须落盘")

        self.assertTrue(self.loop_marker.exists(), "没记到事件循环线程号")
        worker_id = self.worker_marker.read_text().strip()
        loop_id = self.loop_marker.read_text().strip()
        self.assertNotEqual(worker_id, loop_id, "重活绝不在事件循环线程上跑")


if __name__ == "__main__":
    unittest.main()