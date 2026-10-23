"""题目配图上传契约（军令 #13）：``POST /api/assets``。

运行：``.venv/Scripts/python.exe -m unittest tests.test_assets_api``

钉住四条安全边界：
- 必须带一次性写令牌；
- 只认 PNG / JPEG / WebP，魔数与声明 MIME 必须一致（SVG 直接拒）；
- 解码后 ≤8 MiB；
- 文件名/落盘路径由底座生成，请求里的任何路径片段都不参与。
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "assets-contract-token"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class AssetsApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = cls.tmp.name
        env["JZO_LOCAL_TOKEN"] = TOKEN
        cls.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
                "--log-level",
                "warning",
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        deadline = time.time() + 20
        while time.time() < deadline:
            if cls.process.poll() is not None:
                output = cls.process.stdout.read() if cls.process.stdout else ""
                raise RuntimeError("服务提前退出：\n" + output)
            try:
                with urllib.request.urlopen(cls.base + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("服务未在 20 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        cls.tmp.cleanup()

    def upload(self, body: dict | None, token: str | None = TOKEN) -> tuple[int, object]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + "/api/assets", data=data, method="POST")
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                raw = error.read()
                return error.code, json.loads(raw.decode("utf-8")) if raw else None
            finally:
                error.close()

    def test_01_write_token_is_required(self) -> None:
        status, body = self.upload({"data_url": "data:image/png;base64," + base64.b64encode(PNG).decode()},
                                   token=None)
        self.assertEqual(status, 401, body)

    def test_02_rejects_missing_or_bad_data_url(self) -> None:
        status, _ = self.upload({})
        self.assertEqual(status, 400)
        status, _ = self.upload({"data_url": "not-a-data-url"})
        self.assertEqual(status, 400)
        status, _ = self.upload({"data_url": "data:image/svg+xml;base64,PHN2Zy8+"})
        self.assertEqual(status, 400, "SVG 可内嵌脚本，不能当配图放行")
        status, _ = self.upload({"data_url": "data:image/png;base64,!!!!"})
        self.assertEqual(status, 400)

    def test_03_magic_must_match_declared_mime(self) -> None:
        encoded = base64.b64encode(PNG).decode()
        status, body = self.upload({"data_url": "data:image/jpeg;base64," + encoded})
        self.assertEqual(status, 400, body)
        status, body = self.upload({"data_url": "data:image/png;base64," + base64.b64encode(b"not an image").decode()})
        self.assertEqual(status, 400, body)

    def test_04_upload_lands_in_current_workspace_uploads(self) -> None:
        encoded = base64.b64encode(PNG).decode()
        status, body = self.upload({"data_url": "data:image/png;base64," + encoded,
                                    "filename": "../../evil.png"})
        self.assertEqual(status, 201, body)
        self.assertRegex(body["id"], r"^img_[A-Za-z0-9_-]{1,63}$")
        self.assertEqual(body["mime"], "image/png")
        self.assertEqual(body["bytes"], len(PNG))
        self.assertEqual(body["sha256"], hashlib.sha256(PNG).hexdigest())
        self.assertRegex(body["uri"], r"^/static/uploads/img_[A-Za-z0-9_-]+\.png$")
        self.assertNotIn("evil", body["uri"], "请求里的文件名不得参与落盘")
        target = Path(self.tmp.name) / "uploads" / Path(body["uri"]).name
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_bytes(), PNG)

        with urllib.request.urlopen(self.base + body["uri"], timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get("Content-Type"), "image/png")
            self.assertEqual(response.read(), PNG)

    def test_05_rejects_oversized_payload(self) -> None:
        oversized = PNG + b"\x00" * (8 * 1024 * 1024)
        encoded = base64.b64encode(oversized).decode()
        status, body = self.upload({"data_url": "data:image/png;base64," + encoded})
        self.assertEqual(status, 400, body)


class AssetsSniffTest(unittest.TestCase):
    def test_sniff_accepts_only_three_magic(self) -> None:
        from app.api.assets import _sniff_mime

        self.assertEqual(_sniff_mime(PNG), "image/png")
        self.assertEqual(_sniff_mime(b"\xff\xd8\xff\xe0rest"), "image/jpeg")
        self.assertEqual(_sniff_mime(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "image/webp")
        self.assertEqual(_sniff_mime(b"GIF89a"), "")
        self.assertEqual(_sniff_mime(b"<svg xmlns=\"http://www.w3.org/2000/svg\"/>"), "")


if __name__ == "__main__":
    unittest.main()
