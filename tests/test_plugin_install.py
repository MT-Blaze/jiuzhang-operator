"""插件 zip 一键安装契约：令牌、防穿越、防加密、防嵌套、覆盖语义、落地发现。

运行：``.venv/Scripts/python.exe -m unittest tests.test_plugin_install``
"""

from __future__ import annotations

import io
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "plugin-install-test-token"

PLUGIN_ID = "org.jiuzhang.install-test"

MANIFEST = {
    "schema_version": "1.0",
    "id": PLUGIN_ID,
    "name": "安装契约测试插件",
    "version": "1.0.0",
    "api_version": "1.0",
    "kind": "renderer",
    "description": "仅用于安装接口契约测试的最小渲染插件",
    "license": "Apache-2.0",
    "slots": ["question.card"],
    "capabilities": ["question.render"],
    "permissions": ["questions:read"],
    "entry": {"frontend": "dist/plugin.js"},
}

PLUGIN_JS = "console.log('install-test plugin');"
LICENSE_TEXT = "Apache License 2.0 (fixture)"


def build_zip(
    top_dir: str | None = PLUGIN_ID,
    manifest: dict | None = MANIFEST,
    extra: dict[str, str] | None = None,
    raw_entries: dict[str, bytes] | None = None,
) -> bytes:
    """按 PLUGIN_SPEC §1.2 的合法结构打一个最小插件 zip。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        def prefixed(name: str) -> str:
            return f"{top_dir}/{name}" if top_dir else name

        if manifest is not None:
            zf.writestr(prefixed("plugin.json"), json.dumps(manifest, ensure_ascii=False))
        zf.writestr(prefixed("LICENSE"), LICENSE_TEXT)
        zf.writestr(prefixed("dist/plugin.js"), PLUGIN_JS)
        for name, text in (extra or {}).items():
            zf.writestr(prefixed(name), text)
        for name, data in (raw_entries or {}).items():
            zf.writestr(name, data)
    return buffer.getvalue()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class PluginInstallApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.plugins_dir = Path(cls.tmp.name) / "plugins"
        cls.data_dir = Path(cls.tmp.name) / "data"
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

    def post_zip(
        self, data: bytes, token: str | None = TOKEN, replace: bool = False
    ) -> tuple[int, object]:
        url = self.base + "/api/plugins/install" + ("?replace=true" if replace else "")
        request = urllib.request.Request(url, data=data, method="POST")
        request.add_header("Content-Type", "application/zip")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            raw = error.read()
            try:
                return error.code, json.loads(raw)
            except json.JSONDecodeError:
                return error.code, raw.decode("utf-8", errors="replace")
            finally:
                error.close()

    def get_json(self, path: str) -> tuple[int, object]:
        with urllib.request.urlopen(self.base + path, timeout=10) as response:
            return response.status, json.loads(response.read())

    # --- 鉴权 ---

    def test_01_install_requires_token(self) -> None:
        status, _ = self.post_zip(build_zip(), token=None)
        self.assertEqual(status, 401)
        status, _ = self.post_zip(build_zip(), token="wrong-token")
        self.assertEqual(status, 401)
        self.assertFalse((self.plugins_dir / PLUGIN_ID).exists())

    # --- 正常安装 ---

    def test_02_install_happy_path_and_discovery(self) -> None:
        status, body = self.post_zip(build_zip())
        self.assertEqual(status, 200, body)
        self.assertTrue(body["installed"], body)
        self.assertEqual(body["plugin"]["id"], PLUGIN_ID, body)
        self.assertEqual(body["plugin"]["version"], "1.0.0", body)

        installed = self.plugins_dir / PLUGIN_ID
        self.assertTrue((installed / "plugin.json").is_file())
        self.assertTrue((installed / "dist" / "plugin.js").is_file())

        status, listed = self.get_json("/api/plugins")
        self.assertEqual(status, 200)
        ids = [p["id"] for p in listed["plugins"]]
        self.assertIn(PLUGIN_ID, ids, listed)

    def test_03_reinstall_conflicts_then_replace_upgrades(self) -> None:
        status, body = self.post_zip(build_zip())
        self.assertEqual(status, 409, body)
        self.assertEqual(body["detail"]["code"], "exists", body)

        upgraded = build_zip(manifest={**MANIFEST, "version": "1.1.0"})
        status, body = self.post_zip(upgraded, replace=True)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["plugin"]["version"], "1.1.0", body)

    def test_04_flat_zip_layout_installs_under_manifest_id(self) -> None:
        # plugin.json 直接在 zip 顶层：落地目录名以清单 id 为准
        status, body = self.post_zip(build_zip(top_dir=None))
        self.assertEqual(status, 409, body)  # 同 id 已装 → 冲突语义一致
        status, body = self.post_zip(build_zip(top_dir=None), replace=True)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["plugin"]["id"], PLUGIN_ID, body)

    # --- 安全拒绝 ---

    def test_05_rejects_path_traversal(self) -> None:
        payload = build_zip(raw_entries={f"{PLUGIN_ID}/../../evil.txt": b"pwned"})
        status, body = self.post_zip(payload, replace=True)
        self.assertEqual(status, 400, body)
        self.assertIn("穿越", json.dumps(body, ensure_ascii=False))

    def test_06_rejects_absolute_and_drive_paths(self) -> None:
        status, body = self.post_zip(build_zip(raw_entries={"/etc/evil.txt": b"x"}), replace=True)
        self.assertEqual(status, 400, body)
        status, body = self.post_zip(build_zip(raw_entries={"C:/evil.txt": b"x"}), replace=True)
        self.assertEqual(status, 400, body)

    def test_07_rejects_encrypted_entry(self) -> None:
        # zipfile.writestr 会把 flag_bits 清零，只能在字节层把加密位补回去
        def mark_encrypted(data: bytes) -> bytes:
            out = bytearray(data)
            local = out.find(b"PK\x03\x04")
            self.assertNotEqual(local, -1)
            out[local + 6] |= 0x01
            central = out.find(b"PK\x01\x02")
            self.assertNotEqual(central, -1)
            out[central + 8] |= 0x01
            return bytes(out)

        payload = mark_encrypted(build_zip())
        status, body = self.post_zip(payload, replace=True)
        self.assertEqual(status, 400, body)
        self.assertIn("加密", json.dumps(body, ensure_ascii=False))

    def test_08_rejects_symlink_entry(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            for name, text in [
                (f"{PLUGIN_ID}/plugin.json", json.dumps(MANIFEST, ensure_ascii=False)),
                (f"{PLUGIN_ID}/LICENSE", LICENSE_TEXT),
                (f"{PLUGIN_ID}/dist/plugin.js", PLUGIN_JS),
            ]:
                zf.writestr(name, text)
            link = zipfile.ZipInfo(f"{PLUGIN_ID}/dist/evil")
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            link.create_system = 3
            zf.writestr(link, "../../../")
        status, body = self.post_zip(buffer.getvalue(), replace=True)
        self.assertEqual(status, 400, body)
        self.assertIn("符号链接", json.dumps(body, ensure_ascii=False))

    def test_09_rejects_nested_zip(self) -> None:
        payload = build_zip(extra={"dist/inner.zip": "not-a-plugin"})
        status, body = self.post_zip(payload, replace=True)
        self.assertEqual(status, 400, body)
        self.assertIn("嵌套", json.dumps(body, ensure_ascii=False))

    def test_10_rejects_non_zip_and_empty_body(self) -> None:
        status, body = self.post_zip(b"PK\x03\x04 broken", replace=True)
        self.assertEqual(status, 400, body)
        status, body = self.post_zip(b"", replace=True)
        self.assertEqual(status, 400, body)

    def test_11_rejects_zip_without_manifest(self) -> None:
        payload = build_zip(manifest=None)
        status, body = self.post_zip(payload, replace=True)
        self.assertEqual(status, 400, body)
        self.assertIn("plugin.json", json.dumps(body, ensure_ascii=False))

    def test_12_rejects_manifest_contract_violation(self) -> None:
        broken = {**MANIFEST, "license": "MIT"}  # 契约要求 Apache-2.0
        status, body = self.post_zip(build_zip(manifest=broken), replace=True)
        self.assertEqual(status, 400, body)
        self.assertIn("license", json.dumps(body, ensure_ascii=False))

    def test_13_failed_install_leaves_previous_version_intact(self) -> None:
        before = (self.plugins_dir / PLUGIN_ID / "plugin.json").read_text(encoding="utf-8")
        status, _ = self.post_zip(build_zip(manifest={**MANIFEST, "license": "MIT"}), replace=True)
        self.assertEqual(status, 400)
        after = (self.plugins_dir / PLUGIN_ID / "plugin.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
