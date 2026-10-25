"""在线安装契约（PLUGIN_SPEC §1.4）：官方索引、下载守卫、失败回滚、不阻塞主程序。

运行：``.venv/Scripts/python.exe -m unittest tests.test_plugin_install_url``
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import plugin_index, plugin_sources  # noqa: E402
from app.core.plugin_download import (  # noqa: E402
    download_plugin_zip,
    download_plugin_zip_sources,
)
from app.core.plugin_install import PluginInstallError  # noqa: E402
from app.core.plugins import validate_plugin  # noqa: E402

TOKEN = "install-url-test-token"
ONLINE_PROBE_ID = "org.jiuzhang.online-probe"
DEMO_ID = "org.jiuzhang.demo-bank"
TEMPLATE_ID = "org.example.template"
OFFICIAL_PRIMARY = plugin_sources.OFFICIAL_INDEX_PRIMARY


def _write_online_probe_zip(target: Path) -> None:
    """现造一个符合契约的最小插件包，测试不再依赖仓库里的示例 zip。"""
    manifest = {
        "schema_version": "1.0",
        "id": ONLINE_PROBE_ID,
        "name": "在线安装探针",
        "version": "0.1.0",
        "api_version": "1.0",
        "kind": "renderer",
        "description": "用于验证在线安装全链路的最小测试插件。",
        "license": "Apache-2.0",
        "entry": {"frontend": "dist/index.html"},
        "slots": ["question.card"],
        "capabilities": ["question.render"],
        "permissions": ["questions:read"],
    }
    with zipfile.ZipFile(target, "w") as zf:
        zf.writestr(f"{ONLINE_PROBE_ID}/plugin.json", json.dumps(manifest, ensure_ascii=False))
        zf.writestr(f"{ONLINE_PROBE_ID}/LICENSE", "Apache License 2.0\n")
        zf.writestr(f"{ONLINE_PROBE_ID}/dist/index.html", "<!doctype html><html><body></body></html>")
        zf.writestr(f"{ONLINE_PROBE_ID}/dist/plugin.js", "/* probe */\n")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class OfficialIndexFileTest(unittest.TestCase):
    """主仓库根 plugins.json 是官方索引的本地镜像，必须与插件仓库口径一致且不夹带 zip。"""

    def test_01_root_plugins_json_parses_with_zero_rejections(self) -> None:
        payload = json.loads((ROOT / "plugins.json").read_text(encoding="utf-8"))
        parsed = plugin_index.parse_index(payload)
        self.assertEqual(parsed["rejected"], [])
        ids = [entry["id"] for entry in parsed["entries"]]
        self.assertNotIn("org.jiuzhang.placeholder", ids)
        self.assertIn("org.jiuzhang.editor", ids)
        # v0.8.0 清理历史包袱：示例题库 demo-bank 不再进官方索引
        self.assertNotIn(DEMO_ID, ids)

    def test_02_official_entries_use_plugin_repo_mirrors(self) -> None:
        """v0.5.2：索引与 zip 全部指向独立插件仓库，主地址走 gh-proxy。"""
        payload = json.loads((ROOT / "plugins.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["entries"], "官方索引不应为空")
        for entry in payload["entries"]:
            self.assertTrue(entry["zip_url"].startswith("https://gh-proxy.com/"))
            self.assertIn("MT-Blaze/jiuzhang-plugins/main/plugins/", entry["zip_url"])
            self.assertTrue(entry["zip_url"].endswith(".zip"))
            self.assertGreaterEqual(len(entry["mirrors"]), 2)
            self.assertTrue(any("ghfast.top" in item for item in entry["mirrors"]))
            self.assertTrue(any("cdn.jsdelivr.net" in item for item in entry["mirrors"]))

    def test_03b_demo_plugin_zip_passes_full_plugin_contract(self) -> None:
        """示例题库包也要能过全套契约——它是插件仓库里第一个真实可装条目。"""
        zip_path = ROOT / "examples" / "demo_plugin.zip"
        self.assertTrue(zip_path.is_file(), "先运行 examples/build_demo_plugin.py")
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmp)
            plugin_dir = Path(tmp) / DEMO_ID
            manifest = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
            info = validate_plugin(plugin_dir, manifest)
        self.assertEqual(info["id"], DEMO_ID)
        self.assertEqual(info["kind"], "importer")

    def test_03c_template_plugin_zip_passes_full_plugin_contract(self) -> None:
        """第三方开发模板必须开箱即过全套契约：老师解压改完 id 就能装。"""
        zip_path = ROOT / "examples" / "template-plugin.zip"
        self.assertTrue(zip_path.is_file(), "先运行 examples/build_template_plugin.py")
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                self.assertTrue(all(n.startswith(TEMPLATE_ID + "/") for n in names))
                zf.extractall(tmp)
            plugin_dir = Path(tmp) / TEMPLATE_ID
            manifest = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
            info = validate_plugin(plugin_dir, manifest)
        self.assertEqual(info["id"], TEMPLATE_ID)
        self.assertEqual(info["min_host_version"], "0.11.2")
        self.assertTrue(info["stage"], "模板应演示 stage.center 画布接管")
        self.assertIn("region.dock", info["bus"]["publish"])
        self.assertEqual([item["id"] for item in info["commands"]],
                         ["org.example.template.echo"],
                         "模板要示范能力路由字典，否则第三方不知道 contributes.commands 怎么写")

    def test_03d_template_request_id_passes_host_message_guard(self) -> None:
        """宿主入口用 ^[A-Za-z0-9_-]{1,80}$ 校验请求 id，不带点号才不会被静默丢弃。"""
        stage_js = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        self.assertIn("/^[A-Za-z0-9_-]{1,80}$/", stage_js, "宿主请求 id 守卫形状变了，请同步模板与契约")
        plugin_js = (ROOT / "examples" / "template-plugin" / "dist" / "plugin.js").read_text(encoding="utf-8")
        id_lines = [line for line in plugin_js.splitlines() if "var requestId" in line]
        self.assertEqual(len(id_lines), 1, f"模板请求 id 构造应唯一，实际 {id_lines}")
        self.assertNotIn("PLUGIN_ID +", id_lines[0], "请求 id 不能拿带点号的插件 id 当片段")
        id_re = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
        for sample in ("p1_m0k3x9", "p12_zzzz"):
            self.assertTrue(id_re.match(sample), sample)

    def test_04_index_page_prefills_official_primary(self) -> None:
        html = (ROOT / "static" / "plugins.html").read_text(encoding="utf-8")
        self.assertIn('value="%s"' % OFFICIAL_PRIMARY, html)
        self.assertIn("拉取清单", html)
        self.assertIn("在线安装", html)
        self.assertIn("备用镜像", html)

    def test_05_frontend_install_wiring(self) -> None:
        js = (ROOT / "static" / "js" / "plugins.js").read_text(encoding="utf-8")
        self.assertIn("/api/plugins/install-url", js)
        self.assertIn("在线安装", js)
        self.assertIn("覆盖安装", js)
        # 409 必须走用户显式确认，不得静默覆盖
        self.assertIn("409", js)
        self.assertIn("confirm", js)

    def test_06_build_release_excludes_plugin_zips_from_dist(self) -> None:
        """胖仓库红线：官方插件 zip 走插件仓库分发，不得进发放包。"""
        bat = (ROOT / "build_release.bat").read_bytes().decode("ascii")
        xf_lines = [line for line in bat.splitlines() if "/XF" in line]
        self.assertTrue(xf_lines, "打包脚本缺少 /XF 排除清单")
        self.assertIn("template-plugin.zip", xf_lines[0])
        self.assertNotIn("placeholder_plugin.zip", xf_lines[0])
        # 种子包必须留在包里（首启静默安装依赖它），不许一刀切排除所有 zip
        self.assertNotIn("demo_plugin.zip", xf_lines[0])


class DownloadGuardTest(unittest.TestCase):
    """下载守卫：地址不合法在触网前就拒；网络失败给可读原因，不留半个文件。"""

    def test_01_local_schemes_and_credentials_rejected_before_network(self) -> None:
        for bad in ["", "file:///etc/passwd", "data:application/zip,xx", "/relative.zip"]:
            with self.subTest(bad=bad):
                with self.assertRaises(PluginInstallError) as ctx:
                    download_plugin_zip(bad)
                self.assertEqual(ctx.exception.status, 400)
        with self.assertRaises(PluginInstallError) as ctx:
            download_plugin_zip("https://user:secret@a.example.cn/p.zip")
        self.assertEqual(ctx.exception.status, 400)

    def test_02_unreachable_host_maps_to_502_with_readable_reason(self) -> None:
        with self.assertRaises(PluginInstallError) as ctx:
            download_plugin_zip("http://127.0.0.1:%d/p.zip" % _free_port())
        self.assertEqual(ctx.exception.status, 502)
        self.assertEqual(ctx.exception.code, "download_failed")
        self.assertTrue(ctx.exception.message.strip())

    def test_03_http_error_maps_to_502(self) -> None:
        class NotFoundHandler(SimpleHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_error(404, "gone")

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), NotFoundHandler) as httpd:
            port = httpd.server_address[1]
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                with self.assertRaises(PluginInstallError) as ctx:
                    download_plugin_zip("http://127.0.0.1:%d/missing.zip" % port)
            finally:
                httpd.shutdown()
        self.assertEqual(ctx.exception.status, 502)
        self.assertIn("404", ctx.exception.message)


class DownloadMirrorTest(unittest.TestCase):
    """zip 主地址失败时按条目 mirrors 回退；镜像仍受同一套地址守卫。"""

    def test_01_falls_back_to_mirror_and_reports_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "plugin.zip").write_bytes(b"PK\x03\x04mirror-test")
            handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
            with ThreadingHTTPServer(("127.0.0.1", 0), handler) as httpd:
                port = httpd.server_address[1]
                thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                thread.start()
                try:
                    dead = "http://127.0.0.1:%d/plugin.zip" % _free_port()
                    live = "http://127.0.0.1:%d/plugin.zip" % port
                    data, source = download_plugin_zip_sources(dead, [live])
                finally:
                    httpd.shutdown()
        self.assertEqual(data, b"PK\x03\x04mirror-test")
        self.assertEqual(source, live)

    def test_02_primary_still_wins_when_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "a.zip").write_bytes(b"primary")
            (directory / "b.zip").write_bytes(b"mirror")
            handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
            with ThreadingHTTPServer(("127.0.0.1", 0), handler) as httpd:
                port = httpd.server_address[1]
                thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                thread.start()
                try:
                    primary = "http://127.0.0.1:%d/a.zip" % port
                    mirror = "http://127.0.0.1:%d/b.zip" % port
                    data, source = download_plugin_zip_sources(primary, [mirror])
                finally:
                    httpd.shutdown()
        self.assertEqual(data, b"primary")
        self.assertEqual(source, primary)

    def test_03_all_bad_addresses_fail_before_network(self) -> None:
        with self.assertRaises(PluginInstallError) as ctx:
            download_plugin_zip_sources("file:///etc/passwd", ["data:application/zip,xx"])
        self.assertEqual(ctx.exception.status, 400)


class InstallUrlApiTest(unittest.TestCase):
    """接口面：真起底座 + 真起本地「CDN」，跑通下载 → 校验 → 落地全链路。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.plugins_dir = Path(cls.tmp.name) / "plugins"
        cls.data_dir = Path(cls.tmp.name) / "data"
        cls.cdn_dir = Path(cls.tmp.name) / "cdn"
        cls.cdn_dir.mkdir()
        # 本地 CDN：现造的合规插件包 + 一个非 zip + 一个空文件
        probe_zip = Path(cls.tmp.name) / f"{ONLINE_PROBE_ID}.zip"
        _write_online_probe_zip(probe_zip)
        shutil.copy(probe_zip, cls.cdn_dir / f"{ONLINE_PROBE_ID}.zip")
        (cls.cdn_dir / "notazip.txt").write_text("这不是 zip", encoding="utf-8")
        (cls.cdn_dir / "empty.zip").write_bytes(b"")

        cls.cdn_port = _free_port()
        handler = partial(_SlowCdnHandler, directory=str(cls.cdn_dir))
        cls.cdn = ThreadingHTTPServer(("127.0.0.1", cls.cdn_port), handler)
        cls.cdn_thread = threading.Thread(target=cls.cdn.serve_forever, daemon=True)
        cls.cdn_thread.start()

        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = cls.data_dir.as_posix()
        env["JZO_PLUGINS_DIR"] = cls.plugins_dir.as_posix()
        env["JZO_LOCAL_TOKEN"] = TOKEN
        cls.process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", str(cls.port), "--log-level", "warning",
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.cdn_base = f"http://127.0.0.1:{cls.cdn_port}"
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
        cls.cdn.shutdown()
        cls.cdn.server_close()
        cls.tmp.cleanup()

    def post_install(self, body: dict | None, token: str | None = TOKEN):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + "/api/plugins/install-url", data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            raw = error.read()
            try:
                return error.code, json.loads(raw)
            except json.JSONDecodeError:
                return error.code, raw.decode("utf-8", errors="replace")
            finally:
                error.close()

    def get_json(self, path: str):
        with urllib.request.urlopen(self.base + path, timeout=10) as response:
            return response.status, json.loads(response.read())

    def test_01_requires_write_token(self) -> None:
        status, _ = self.post_install({"url": self.cdn_base + "/" + ONLINE_PROBE_ID + ".zip"}, token=None)
        self.assertEqual(status, 401)
        status, _ = self.post_install({"url": self.cdn_base + "/" + ONLINE_PROBE_ID + ".zip"}, token="wrong")
        self.assertEqual(status, 401)

    def test_02_missing_or_bad_url_is_400(self) -> None:
        status, body = self.post_install({})
        self.assertEqual(status, 400)
        status, body = self.post_install({"url": "file:///etc/passwd"})
        self.assertEqual(status, 400)
        self.assertIn("http", str(body["detail"]))

    def test_03_online_install_full_loop(self) -> None:
        """拉清单同款守卫 + 真下载 + 真落地：装完立刻能被 /api/plugins 发现。"""
        status, body = self.post_install({"url": self.cdn_base + "/" + ONLINE_PROBE_ID + ".zip"})
        self.assertEqual(status, 200, body)
        self.assertTrue(body["installed"])
        self.assertEqual(body["plugin"]["id"], ONLINE_PROBE_ID)

        status, listing = self.get_json("/api/plugins")
        ids = {plugin["id"]: plugin for plugin in listing["plugins"]}
        self.assertIn(ONLINE_PROBE_ID, ids)
        self.assertTrue(ids[ONLINE_PROBE_ID]["entry_url"].startswith("/plugin-assets/"))

    def test_04_reinstall_is_409_until_explicit_replace(self) -> None:
        status, body = self.post_install({"url": self.cdn_base + "/" + ONLINE_PROBE_ID + ".zip"})
        self.assertEqual(status, 409)
        self.assertEqual(body["detail"]["code"], "exists")
        status, body = self.post_install({"url": self.cdn_base + "/" + ONLINE_PROBE_ID + ".zip", "replace": True})
        self.assertEqual(status, 200, body)

    def test_05_download_failure_leaves_zero_residue(self) -> None:
        """失败回滚：下载炸了 plugins/ 不许多出任何目录或半装文件。"""
        before = sorted(item.name for item in self.plugins_dir.iterdir()) if self.plugins_dir.is_dir() else []
        status, body = self.post_install({"url": "http://127.0.0.1:%d/x.zip" % _free_port()})
        self.assertEqual(status, 502)
        self.assertEqual(body["detail"]["code"], "download_failed")
        self.assertTrue(str(body["detail"]["message"]).strip())
        after = sorted(item.name for item in self.plugins_dir.iterdir()) if self.plugins_dir.is_dir() else []
        self.assertEqual(before, after)

    def test_06_bad_payloads_after_download_are_rejected(self) -> None:
        status, body = self.post_install({"url": self.cdn_base + "/notazip.txt"})
        self.assertEqual(status, 400)
        self.assertIn("zip", str(body["detail"]))
        status, body = self.post_install({"url": self.cdn_base + "/empty.zip"})
        self.assertEqual(status, 502, body)

    def test_07_slow_download_does_not_block_the_base(self) -> None:
        """下载再慢也不许卡死主程序：/slow.zip 拖 3 秒期间 /healthz 必须秒回。"""
        result: dict[str, int] = {}

        def worker() -> None:
            status, _ = self.post_install({"url": self.cdn_base + "/slow.zip", "replace": True})
            result["status"] = status

        thread = threading.Thread(target=worker)
        thread.start()
        time.sleep(0.6)  # 确保慢下载已在途
        started = time.monotonic()
        status, body = self.get_json("/healthz")
        elapsed = time.monotonic() - started
        thread.join(timeout=25)
        self.assertEqual(status, 200)
        self.assertLess(elapsed, 2.0, "慢下载期间 /healthz 响应超过 2 秒，事件循环疑似被阻塞")
        self.assertEqual(result.get("status"), 200)


class _SlowCdnHandler(SimpleHTTPRequestHandler):
    """/slow.zip 故意拖 3 秒再吐真包，用来验证下载不阻塞底座。"""

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/slow.zip"):
            time.sleep(3.0)
            self.path = "/" + ONLINE_PROBE_ID + ".zip"
        return super().do_GET()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
