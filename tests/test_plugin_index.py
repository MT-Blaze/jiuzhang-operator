"""插件索引（plugins.json）契约：零写死远程源、坏条目只出局不判死整份清单。

运行：``.venv/Scripts/python.exe -m unittest tests.test_plugin_index``
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import plugin_index, plugin_sources  # noqa: E402

TOKEN = "index-test-token"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def good_entry(**overrides) -> dict:
    entry = {
        "id": "cn.example.card",
        "name": "示例题卡",
        "version": "1.0.0",
        "zip_url": "https://mirror.example.cn/plugins/cn.example.card-1.0.0.zip",
    }
    entry.update(overrides)
    return entry


class IndexParsingTest(unittest.TestCase):
    def test_shipped_example_index_is_valid_and_self_describing(self) -> None:
        """仓库自带的示例必须能被自己的解析器接受（防止规范与样例分叉）。"""
        payload = json.loads(
            (ROOT / "examples" / "plugins-index.example.json").read_text(encoding="utf-8")
        )
        parsed = plugin_index.parse_index(payload)
        self.assertEqual(parsed["rejected"], [])
        self.assertGreaterEqual(parsed["entry_count"], 1)
        for entry in parsed["entries"]:
            self.assertTrue(entry["zip_url"].startswith("https://"))

    def test_one_broken_entry_is_skipped_not_fatal(self) -> None:
        """单条写错只让它自己出局，并留下可读原因——不得把整份清单判死。"""
        payload = {
            "index_version": "1.0",
            "entries": [
                good_entry(),
                {"id": "not-a-domain", "name": "坏 id", "version": "1.0.0", "zip_url": "https://a.example.cn/x.zip"},
                {"id": "cn.example.two", "name": "缺 zip", "version": "1.0.0"},
                good_entry(id="cn.example.card", name="重复 id"),
                good_entry(id="cn.example.three", zip_url="ftp://a.example.cn/x.zip"),
            ],
        }
        parsed = plugin_index.parse_index(payload)
        self.assertEqual(parsed["entry_count"], 1)
        self.assertEqual(parsed["rejected_count"], 4)
        reasons = "；".join(item["reason"] for item in parsed["rejected"])
        self.assertIn("反向域名", reasons)
        self.assertIn("zip_url", reasons)
        self.assertIn("重复", reasons)
        self.assertIn("http(s)", reasons)

    def test_duplicate_ids_are_rejected(self) -> None:
        payload = {
            "index_version": "1.0",
            "entries": [good_entry(), good_entry()],
        }
        parsed = plugin_index.parse_index(payload)
        self.assertEqual(parsed["entry_count"], 1)
        self.assertEqual(len(parsed["rejected"]), 1)

    def test_wrong_index_version_and_shapes_are_refused(self) -> None:
        with self.assertRaises(plugin_index.IndexRejected):
            plugin_index.parse_index({"index_version": "2.0", "entries": []})
        with self.assertRaises(plugin_index.IndexRejected):
            plugin_index.parse_index({"index_version": "1.0"})
        with self.assertRaises(plugin_index.IndexRejected):
            plugin_index.parse_index([])


class UrlGuardTest(unittest.TestCase):
    def test_only_plain_http_urls_without_credentials_are_accepted(self) -> None:
        self.assertEqual(
            plugin_index.validate_index_url("https://a.example.cn/plugins.json"),
            "https://a.example.cn/plugins.json",
        )
        for bad in ["", "   ", "file:///etc/passwd", "data:application/json,{}", "/plugins.json"]:
            with self.subTest(bad=bad):
                with self.assertRaises(plugin_index.IndexRejected):
                    plugin_index.validate_index_url(bad)
        with self.assertRaises(plugin_index.IndexRejected):
            plugin_index.validate_index_url("https://user:secret@a.example.cn/plugins.json")

    def test_describe_public_url_strips_path_and_query(self) -> None:
        self.assertEqual(
            plugin_index.describe_public_url("https://a.example.cn/dir/plugins.json?token=1"),
            "https://a.example.cn",
        )

    def test_fetch_never_accepts_local_protocols_before_touching_network(self) -> None:
        """file:// 必须在发起任何请求前被拒——否则一个地址就能读走本机任意文件。"""
        sample = ROOT / "examples" / "plugins-index.example.json"
        with self.assertRaises(plugin_index.IndexRejected):
            plugin_index.fetch_index(sample.as_uri())


class PluginIndexApiTest(unittest.TestCase):
    """接口面：无令牌不放行、成功只回清单、失败只给可读原因。"""

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

    def call(self, method: str, path: str, body: dict | None = None, token: str | None = None):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            with error:
                raw = error.read()
            try:
                return error.code, json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return error.code, {"raw": raw.decode("utf-8", errors="replace")[:200]}

    def test_01_index_requires_write_token(self) -> None:
        status, _ = self.call("POST", "/api/plugins/index", {"url": self.base + "/plugins/index-example"})
        self.assertEqual(status, 401)

    def test_02_pull_shipped_example_index(self) -> None:
        """同源示例地址跑通整条链路：底座确实只按用户给的地址发一次只读 GET。"""
        status, body = self.call(
            "POST", "/api/plugins/index", {"url": self.base + "/plugins/index-example"}, token=TOKEN
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(body["entry_count"], 2)
        self.assertEqual(body["rejected_count"], 0)
        self.assertTrue(body["source_host"].startswith("http://127.0.0.1:"))
        self.assertIn("fetched_at", body)
        first = body["entries"][0]
        self.assertEqual(first["id"], "org.jiuzhang.classic-card")
        self.assertTrue(first["mirrors"])

    def test_03_rejects_non_http_scheme(self) -> None:
        sample = (ROOT / "examples" / "plugins-index.example.json").as_posix()
        status, body = self.call("POST", "/api/plugins/index", {"url": "file:///" + sample.lstrip("/")}, token=TOKEN)
        self.assertEqual(status, 400)
        self.assertIn("http", str(body["detail"]))

    def test_04_unreachable_host_gives_readable_reason_not_500(self) -> None:
        status, body = self.call(
            "POST", "/api/plugins/index", {"url": "http://127.0.0.1:%d/plugins.json" % _free_port()}, token=TOKEN
        )
        self.assertEqual(status, 400, body)
        self.assertTrue(str(body.get("detail", "")).strip())

    def test_05_official_mirrors_are_registered_in_one_place(self) -> None:
        """v0.5.1 出网口径：官方索引主源 + 至少两套备用镜像，只在 plugin_sources 登记。

        与 v0.5.0 的区别：raw.githubusercontent.com 国内不可达，默认主源改成
        gh-proxy 反代（jsDelivr 的 @main 分支缓存会滞后），并在主源失败时自动回退。
        底座依然不自动拉取、不自动更新，备用源只在本机用户点击【拉取清单】后按序尝试。
        """
        sources = plugin_sources.OFFICIAL_INDEX_SOURCES
        self.assertGreaterEqual(len(sources), 3, "主源之外至少要有两套备用镜像")
        self.assertEqual(sources[0], plugin_sources.OFFICIAL_INDEX_PRIMARY)
        self.assertIn("gh-proxy.com", sources[0])
        self.assertFalse(sources[0].startswith("https://raw.githubusercontent.com"))
        self.assertIn("ghfast.top", " ".join(sources))
        self.assertIn("cdn.jsdelivr.net", " ".join(sources))
        self.assertEqual(len(sources), len(set(sources)), "镜像地址不得重复")

        # 拉取入口仍然只读请求体里的 url，不偷偷塞默认值
        router_source = (ROOT / "app" / "api" / "plugins.py").read_text(encoding="utf-8")
        self.assertIn('payload.get("url"', router_source)
        self.assertNotIn("OFFICIAL_INDEX_PRIMARY", router_source)

        # 页面默认预填必须与后端主源逐字一致，且只出现一处
        html = (ROOT / "static" / "plugins.html").read_text(encoding="utf-8")
        official = plugin_sources.OFFICIAL_INDEX_PRIMARY
        self.assertIn('value="%s"' % official, html)
        self.assertEqual(html.count(official), 1, "官方主源只允许预填一处")

        js = (ROOT / "static" / "js" / "plugins.js").read_text(encoding="utf-8")
        self.assertIn("allow_mirrors", js, "前端必须把「是否官方地址」告诉后端")
        self.assertIn("mirrors", js, "在线安装必须把条目镜像列表交给后端")


class IndexFallbackTest(unittest.TestCase):
    """主源失败自动切备用源；第三方地址只在用户填的那一个上访问。"""

    def test_official_candidates_follow_registered_order(self) -> None:
        candidates = plugin_sources.index_candidates(
            plugin_sources.OFFICIAL_INDEX_PRIMARY, True
        )
        self.assertEqual(candidates[0], plugin_sources.OFFICIAL_INDEX_PRIMARY)
        self.assertEqual(candidates, list(plugin_sources.OFFICIAL_INDEX_SOURCES))
        for url in candidates:
            self.assertTrue(plugin_sources.is_official_index_url(url))

    def test_custom_url_never_switches_source(self) -> None:
        custom = "https://my.school.example.cn/plugins.json"
        self.assertEqual(plugin_sources.index_candidates(custom, True), [custom])
        self.assertEqual(
            plugin_sources.index_candidates(plugin_sources.OFFICIAL_INDEX_PRIMARY, False),
            [plugin_sources.OFFICIAL_INDEX_PRIMARY],
        )

    def test_fetch_falls_back_when_primary_fails(self) -> None:
        payload = {"index_version": "1.0", "entries": [good_entry()]}
        seen: list[str] = []

        def fake_fetch(target: str, timeout: float) -> dict:
            seen.append(target)
            if len(seen) == 1:
                raise plugin_index.IndexRejected("模拟主源超时")
            return plugin_index.parse_index(payload)

        with mock.patch.object(plugin_index, "_fetch_once", side_effect=fake_fetch):
            index = plugin_index.fetch_index(plugin_sources.OFFICIAL_INDEX_PRIMARY)

        self.assertTrue(index["fallback_used"])
        self.assertEqual(index["source_url"], plugin_sources.OFFICIAL_INDEX_SOURCES[1])
        self.assertEqual(len(index["attempts"]), 2)
        self.assertFalse(index["attempts"][0]["ok"])
        self.assertTrue(index["attempts"][1]["ok"])
        self.assertEqual(index["entry_count"], 1)

    def test_all_sources_failing_lists_every_host(self) -> None:
        def fake_fetch(target: str, timeout: float) -> dict:
            raise plugin_index.IndexRejected("模拟断网")

        with mock.patch.object(plugin_index, "_fetch_once", side_effect=fake_fetch):
            with self.assertRaises(plugin_index.IndexRejected) as ctx:
                plugin_index.fetch_index(plugin_sources.OFFICIAL_INDEX_PRIMARY)
        message = str(ctx.exception)
        for url in plugin_sources.OFFICIAL_INDEX_SOURCES:
            self.assertIn(plugin_index.describe_public_url(url), message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
