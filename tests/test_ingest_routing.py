"""解析路由账本 + MinerU 适配器契约。

- 文本体检与乱码标记：只写提示，**绝不自动调 AI**；
- 批次路由：版面与识别两个引擎名并存入账，说明随选择变化；
- MinerU 适配器的申请-上传-轮询-下载四步与失败收敛。

运行：``.venv/Scripts/python.exe -m unittest tests.test_ingest_routing``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))


import io
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.core import ingest_route, mineru_extract, text_health, wire


class TextHealthTest(unittest.TestCase):
    def test_clean_text_is_not_garbled(self) -> None:
        health = text_health.text_health("1. 求 $x+1=2$ 的解。\n2. 求证 $a=b$。")
        self.assertTrue(health["has_text_layer"])
        self.assertFalse(health["garbled"])

    def test_replacement_chars_are_flagged(self) -> None:
        health = text_health.text_health("1. 求 \ufffd\ufffd\ufffd 的解")
        self.assertTrue(health["garbled"])
        self.assertGreaterEqual(health["missing_chars"], 3)


class RoutePayloadTest(unittest.TestCase):
    def test_garbled_note_says_no_auto_ai(self) -> None:
        route = ingest_route.route_payload("text", {
            "garbled": True, "missing_chars": 9, "text_chars": 100, "has_text_layer": True,
        })
        self.assertEqual(route["channel"], "text")
        self.assertTrue(route["garbled"])
        self.assertIn("不会自动调用 AI", route["note"])
        self.assertIn("9", route["note"])

    def test_scan_note_points_to_manual_action(self) -> None:
        route = ingest_route.route_payload("scan_image", {
            "garbled": False, "text_chars": 0, "has_text_layer": False,
        }, text_layer=False)
        self.assertFalse(route["text_layer"])
        self.assertIn("切图模式", route["note"])


class ScanRouteNoteTest(unittest.TestCase):
    def test_cloud_layout_skips_yolo_in_the_note(self) -> None:
        route = ingest_route.scan_route("cloud", "mineru",
                                        {"has_text_layer": True, "garbled": False})
        self.assertEqual(route["layout_engine"], "cloud")
        self.assertEqual(route["recognize_engine"], "mineru")
        self.assertIn("跳过 YOLO", route["note"])
        self.assertIn("MinerU", route["note"])
        self.assertEqual(route["phase"], "parsing")
        self.assertFalse(route["done"])

    def test_auto_layout_mentions_both_fallbacks(self) -> None:
        route = ingest_route.scan_route("auto", "auto",
                                        {"has_text_layer": False, "garbled": False})
        self.assertIn("本机 YOLO", route["note"])
        self.assertIn("云端", route["note"])
        self.assertIn("全量", route["note"])
        self.assertIn("没有文本层", route["note"])



def _zip_with_markdown(text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("result/full.md", text)
        archive.writestr("result/other.txt", "x")
    return buffer.getvalue()


class _MineruHandler(BaseHTTPRequestHandler):
    batch_state = "done"
    fail_code = 0
    uploaded = bytearray()

    def _json(self, payload: dict, code: int = 200) -> None:
        body = wire.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - http.server 命名约定
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.path.endswith("/file-urls/batch"):
            if _MineruHandler.fail_code:
                self._json({"code": _MineruHandler.fail_code, "msg": "余额不足"})
                return
            port = self.server.server_address[1]
            self._json({
                "code": 0,
                "data": {"batch_id": "batch-1",
                         "file_urls": [f"http://127.0.0.1:{port}/upload"]},
            })
            return
        self._json({"code": 404}, 404)

    def do_PUT(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        _MineruHandler.uploaded = bytearray(self.rfile.read(length))
        self._json({"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/v4/extract-results/batch/"):
            port = self.server.server_address[1]
            self._json({
                "code": 0,
                "data": {"extract_result": [{
                    "data_id": self.headers.get("X-Data-Id") or "",
                    "state": _MineruHandler.batch_state,
                    "err_msg": "模型拒绝",
                    "full_zip_url": f"http://127.0.0.1:{port}/zip",
                }]},
            })
            return
        if self.path.endswith("/zip"):
            blob = _zip_with_markdown("# 第 1 题\n求 $x+1=2$ 的解。")
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
            return
        self._json({"code": 404}, 404)

    def log_message(self, *args) -> None:
        pass


class _Poll:
    """轮询里的 sleep/clock 用假时钟：不真的等两秒。"""

    def __init__(self) -> None:
        self.now = 0.0

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def clock(self) -> float:
        return self.now


class MineruAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        _MineruHandler.batch_state = "done"
        _MineruHandler.fail_code = 0
        _MineruHandler.uploaded = bytearray()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _MineruHandler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()

    def test_01_full_flow_downloads_markdown(self) -> None:
        poll = _Poll()
        outcome = mineru_extract.extract(
            "卷.pdf", b"%PDF-1.7 body", self.base, "fixture-key",
            wait=10, sleep=poll.sleep, clock=poll.clock,
        )
        self.assertTrue(outcome["ok"], outcome)
        self.assertIn("求 $x+1=2$", outcome["markdown"])
        self.assertEqual(bytes(_MineruHandler.uploaded), b"%PDF-1.7 body")

    def test_02_failed_state_is_reported(self) -> None:
        _MineruHandler.batch_state = "failed"
        poll = _Poll()
        outcome = mineru_extract.extract(
            "卷.pdf", b"%PDF", self.base, "fixture-key",
            wait=10, sleep=poll.sleep, clock=poll.clock,
        )
        self.assertFalse(outcome["ok"])
        self.assertIn("MinerU 解析失败", outcome["detail"])

    def test_03_rejected_submission_is_reported(self) -> None:
        _MineruHandler.fail_code = -500
        poll = _Poll()
        outcome = mineru_extract.extract(
            "卷.pdf", b"%PDF", self.base, "fixture-key",
            wait=10, sleep=poll.sleep, clock=poll.clock,
        )
        self.assertFalse(outcome["ok"])
        self.assertIn("余额不足", outcome["detail"])

    def test_04_missing_key_never_calls_network(self) -> None:
        outcome = mineru_extract.extract("卷.pdf", b"%PDF", self.base, "")
        self.assertFalse(outcome["ok"])
        self.assertIn("API Key", outcome["detail"])


if __name__ == "__main__":
    unittest.main()
