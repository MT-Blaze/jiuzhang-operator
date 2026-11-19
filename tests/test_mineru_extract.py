"""MinerU 云端上传的线上头契约（mineru-put-fix）。

OSS 签名 URL 没把 Content-Type 签进签名：raw PUT 线上带任何 Content-Type
都 403 SignatureDoesNotMatch（2026-11-19 同 URL 双 PUT 实证，证据见
.system_generated/typst-bench/wire/fix_diag.md）。本模块用本机回环服务器
录「实收请求头」做断言——urllib 自动补 x-www-form-urlencoded 也逃不掉。

运行：``.venv/Scripts/python.exe -m unittest tests.test_mineru_extract``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

import io
import threading
import unittest
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.core import wire
from app.core.ingest.recognize import mineru_extract

SIGNED_QUERY = "Expires=1795171953&OSSAccessKeyId=TESTKEY&Signature=abc%2Fdef%3D"
UPLOAD_PATH = "/upload/obj.png?" + SIGNED_QUERY


def _zip_with_markdown(text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("full.md", text)
    return buffer.getvalue()


class _WireHandler(BaseHTTPRequestHandler):
    legs: list[dict] = []
    put_status = 200

    def _record(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        _WireHandler.legs.append({
            "method": self.command, "path": self.path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": body,
        })
        return body

    def _json(self, payload: dict, code: int = 200) -> None:
        body = wire.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - http.server 命名约定
        self._record()
        port = self.server.server_address[1]
        self._json({"code": 0, "data": {
            "batch_id": "batch-wire",
            "file_urls": [f"http://127.0.0.1:{port}{UPLOAD_PATH}"],
        }})

    def do_PUT(self) -> None:  # noqa: N802
        self._record()
        if _WireHandler.put_status != 200:
            body = b"<Error><Code>SignatureDoesNotMatch</Code></Error>"
            self.send_response(_WireHandler.put_status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._record()
        if self.path.startswith("/api/v4/extract-results/batch/"):
            port = self.server.server_address[1]
            self._json({"code": 0, "data": {"extract_result": [{
                "state": "done",
                "full_zip_url": f"http://127.0.0.1:{port}/zip",
            }]}})
            return
        blob = _zip_with_markdown("# 第 1 题\n求 $x+1=2$ 的解。")
        self.send_response(200)
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def log_message(self, *args) -> None:
        pass


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def clock(self) -> float:
        return self.now


class UploadWireTest(unittest.TestCase):
    def setUp(self) -> None:
        _WireHandler.legs = []
        _WireHandler.put_status = 200
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _WireHandler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _legs(self, method: str) -> list[dict]:
        return [leg for leg in _WireHandler.legs if leg["method"] == method]

    def test_01_capture_catches_urllib_auto_header(self) -> None:
        """ harness 自检：urllib 无显式头会被自动补头，实收断言必须能抓到。"""
        request = urllib.request.Request(
            self.base + UPLOAD_PATH, data=b"probe", method="PUT")
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
        put = self._legs("PUT")[0]
        self.assertEqual(put["headers"].get("content-type"),
                         "application/x-www-form-urlencoded")

    def test_02_raw_put_has_no_content_type(self) -> None:
        mineru_extract._put_raw(self.base + UPLOAD_PATH, b"IMG-BYTES", 10)
        put = self._legs("PUT")[0]
        self.assertNotIn("content-type", put["headers"])
        self.assertEqual(put["body"], b"IMG-BYTES")

    def test_03_signed_query_arrives_unpolluted(self) -> None:
        mineru_extract._put_raw(self.base + UPLOAD_PATH, b"x", 10)
        self.assertEqual(self._legs("PUT")[0]["path"], UPLOAD_PATH)

    def test_04_post_json_keeps_application_json(self) -> None:
        mineru_extract._request(self.base + "/api/v4/file-urls/batch",
                                method="POST", token="fixture-key",
                                payload={"files": []})
        post = self._legs("POST")[0]
        self.assertEqual(post["headers"].get("content-type"), "application/json")
        self.assertEqual(post["headers"].get("authorization"), "Bearer fixture-key")

    def test_05_full_flow_wire_contract(self) -> None:
        clock = _FakeClock()
        outcome = mineru_extract.extract(
            "卷.pdf", b"%PDF-1.7 body", self.base, "fixture-key",
            wait=10, sleep=clock.sleep, clock=clock.clock)
        self.assertTrue(outcome["ok"], outcome)
        self.assertIn("求 $x+1=2$", outcome["markdown"])
        put = self._legs("PUT")[0]
        self.assertNotIn("content-type", put["headers"])
        self.assertEqual(put["path"], UPLOAD_PATH)
        self.assertEqual(put["body"], b"%PDF-1.7 body")
        self.assertEqual(self._legs("POST")[0]["headers"].get("content-type"),
                         "application/json")

    def test_06_put_403_fails_without_signature_leak(self) -> None:
        _WireHandler.put_status = 403
        clock = _FakeClock()
        outcome = mineru_extract.extract(
            "卷.pdf", b"%PDF", self.base, "fixture-key",
            wait=10, sleep=clock.sleep, clock=clock.clock)
        self.assertFalse(outcome["ok"])
        self.assertIn("上传原文件失败", outcome["detail"])
        self.assertIn("403", outcome["detail"])
        self.assertNotIn("Signature", outcome["detail"])
        self.assertNotIn(SIGNED_QUERY, outcome["detail"])


if __name__ == "__main__":
    unittest.main()