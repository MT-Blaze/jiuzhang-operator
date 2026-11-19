"""记号标准字典 Host API：``/api/norm/*`` 的契约（2.21.0 卡 §4/§6）。

钉住六件事：
- 闭集条目全量返回（223 条目／八记号族），effective_default 老师选择优先、未选回退出厂；
- 写接口（choose/reset/decide）必须带一次性令牌，缺令 401；
- 老师只写选择：choose 翻转默认、reset 回退出厂，出厂内容永不动；
- choose 拒收外条目变体／不存在条目／非整数 variant_id；
- 开集候选经清洗端点真实落 pending，corrections 按状态过滤＋四态计数；
- 人闸只有 pending 可裁决：confirmed 须给目标且参与改写、rejected 黑名单永不生效。

运行：``.venv/Scripts/python.exe -m unittest tests.test_norm_api``
隔离：JZO_DATA_DIR/JZO_PLUGINS_DIR 指临时副本，启动钩子幂等播种闭集，不碰用户 data/。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import wire  # noqa: E402

import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "norm-dict-contract-token"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class NormApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.data_dir = root / "data"
        cls.plugins_dir = root / "plugins"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        cls.plugins_dir.mkdir(parents=True, exist_ok=True)
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        env["JZO_RESTART_DISABLED"] = "1"
        for key in ("JZO_AI_API_KEY", "JZO_BAILIAN_API_KEY",
                    "JZO_SILICONFLOW_API_KEY", "JZO_OLLAMA_API_KEY"):
            env[key] = ""
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(cls.port), "--log-level", "warning"],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        deadline = time.time() + 25
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
        raise RuntimeError("服务未在 25 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        cls.tmp.cleanup()

    def _request(self, path, method="GET", body=None, token=TOKEN):
        data = None
        request = urllib.request.Request(
            self.base + urllib.parse.quote(path, safe="/?=&"), method=method)
        if body is not None:
            data = wire.dumps(body, ensure_ascii=False).encode("utf-8")
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, data=data, timeout=30) as response:
                raw = response.read()
                return response.status, (wire.loads(raw.decode("utf-8")) if raw else None)
        except urllib.error.HTTPError as error:
            try:
                raw = error.read()
                return error.code, (wire.loads(raw.decode("utf-8")) if raw else None)
            finally:
                error.close()

    def _entries(self):
        status, body = self._request("/api/norm/entries")
        self.assertEqual(status, 200, body)
        return {e["entry_key"]: e for e in body["entries"]}, body

    def _le_variant(self, entries, code):
        return next(v["id"] for v in entries["le"]["variants"] if v["latex_code"] == code)

    def _clean(self, text):
        status, body = self._request("/api/agent/clean_latex", "POST", {"text": text})
        self.assertEqual(status, 200, body)
        return body["data"]["text"]

    def _pending_codes(self):
        status, body = self._request("/api/norm/corrections?status=pending")
        self.assertEqual(status, 200, body)
        return [c["raw_code"] for c in body["corrections"]], body["counts"]

    def test_01_entries_full_closed_set_with_factory_default(self):
        entries, body = self._entries()
        self.assertEqual(len(entries), 223)
        self.assertEqual(len(body["families"]), 8)
        self.assertEqual(len(body["source_labels"]), 4)
        le = entries["le"]
        self.assertEqual(le["category"], "关系不等")
        default = next(v for v in le["variants"] if v["id"] == le["effective_default_variant_id"])
        self.assertEqual(default["latex_code"], r"\leqslant")
        self.assertIsNone(le["chosen_default_variant_id"])

    def test_02_writes_require_the_write_token(self):
        for path, payload in (
            ("/api/norm/choose", {"entry_key": "le", "variant_id": 1}),
            ("/api/norm/reset", {"entry_key": "le"}),
            ("/api/norm/decide", {"raw_code": "x", "decision": "rejected"}),
        ):
            status, body = self._request(path, "POST", payload, token=None)
            self.assertEqual(status, 401, (path, body))

    def test_03_choose_flip_and_reset_roundtrip(self):
        entries, _ = self._entries()
        upright = self._le_variant(entries, r"\le")
        status, body = self._request("/api/norm/choose", "POST",
                                     {"entry_key": "le", "variant_id": upright})
        self.assertEqual(status, 200, body)
        entries, _ = self._entries()
        self.assertEqual(entries["le"]["chosen_default_variant_id"], upright)
        default = next(v for v in entries["le"]["variants"]
                       if v["id"] == entries["le"]["effective_default_variant_id"])
        self.assertEqual(default["latex_code"], r"\le")
        status, body = self._request("/api/norm/reset", "POST", {"entry_key": "le"})
        self.assertEqual(status, 200, body)
        entries, _ = self._entries()
        self.assertIsNone(entries["le"]["chosen_default_variant_id"])
        default = next(v for v in entries["le"]["variants"]
                       if v["id"] == entries["le"]["effective_default_variant_id"])
        self.assertEqual(default["latex_code"], r"\leqslant")

    def test_04_choose_rejects_foreign_missing_and_non_integer(self):
        entries, _ = self._entries()
        foreign = entries["ge"]["variants"][0]["id"]
        status, body = self._request("/api/norm/choose", "POST",
                                     {"entry_key": "le", "variant_id": foreign})
        self.assertEqual(status, 400, body)
        status, body = self._request("/api/norm/choose", "POST",
                                     {"entry_key": "no_such_entry", "variant_id": 1})
        self.assertEqual(status, 400, body)
        status, body = self._request("/api/norm/choose", "POST",
                                     {"entry_key": "le", "variant_id": "abc"})
        self.assertEqual(status, 400, body)

    def test_05_unknown_lands_pending_and_counts(self):
        self._clean(r"$\zqnormapi$")
        codes, counts = self._pending_codes()
        self.assertIn("zqnormapi", codes)
        self.assertGreaterEqual(counts["pending"], 1)
        self.assertEqual(set(counts), {"pending", "confirmed", "rejected", "archived"})

    def test_06_confirmed_requires_target_and_rewrites(self):
        self._clean(r"$\zqconf$")
        status, body = self._request("/api/norm/decide", "POST",
                                     {"raw_code": "zqconf", "decision": "confirmed"})
        self.assertEqual(status, 400, body)
        status, body = self._request("/api/norm/decide", "POST",
                                     {"raw_code": "zqconf", "decision": "confirmed", "target_code": "le"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"], "confirmed")
        self.assertIn(r"\leqslant", self._clean(r"$\zqconf$"))

    def test_07_rejected_blacklist_never_rewrites(self):
        self._clean(r"$\zqrej$")
        status, body = self._request("/api/norm/decide", "POST",
                                     {"raw_code": "zqrej", "decision": "rejected"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"], "rejected")
        self.assertIn(r"\zqrej", self._clean(r"$\zqrej$"))
        status, body = self._request("/api/norm/corrections?status=rejected")
        self.assertIn("zqrej", [c["raw_code"] for c in body["corrections"]])

    def test_08_decide_only_pending_and_valid_action(self):
        self._clean(r"$\zqpend$")
        self._request("/api/norm/decide", "POST",
                      {"raw_code": "zqpend", "decision": "rejected"})
        status, body = self._request("/api/norm/decide", "POST",
                                     {"raw_code": "zqpend", "decision": "confirmed", "target_code": "le"})
        self.assertEqual(status, 400, body)
        status, body = self._request("/api/norm/decide", "POST",
                                     {"raw_code": "zqpend", "decision": "maybe"})
        self.assertEqual(status, 400, body)
        status, body = self._request("/api/norm/decide", "POST",
                                     {"raw_code": "no_such_candidate", "decision": "rejected"})
        self.assertEqual(status, 400, body)


if __name__ == "__main__":
    unittest.main()