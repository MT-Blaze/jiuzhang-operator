"""军令 #17 第三步契约：WebDAV 凭据、远端保留 1 份、失败不删旧份。

用本机临时 HTTP 服务模拟 WebDAV（不是真机网盘）：真实走 urllib 的
MKCOL / PROPFIND / PUT / DELETE 与 Basic 认证，避免把「协议层」也 mock 掉。

运行：``.venv/Scripts/python.exe -m unittest tests.test_webdav_backup``
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.core import backup, webdav
from app.core.config import settings

WS_ID = "ws_abcdef0123456789"
OLD_STAMP = "20250101_010101_001"
NEW_STAMP = "20260101_010101_001"
FAIL_STAMP = "20260102_010101_001"


class _FakeDavHandler(BaseHTTPRequestHandler):
    server_version = "FakeDav/1.0"

    def log_message(self, *args) -> None:  # noqa: ANN002 - 静音访问日志
        pass

    def _name(self) -> str:
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        return path.rstrip("/").rsplit("/", 1)[-1]

    def _auth_ok(self) -> bool:
        header = self.headers.get("Authorization") or ""
        self.server.auth_headers.append(header)
        expected = "Basic " + base64.b64encode(b"teacher:s3cret").decode("ascii")
        return header == expected

    def _send(self, status: int, body: bytes = b"", content_type: str = "text/plain") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_MKCOL(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 约定
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if not self._auth_ok():
            self._send(401)
            return
        self.server.methods.append("MKCOL")
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).rstrip("/")
        if path in self.server.dirs:
            # 真实 WebDAV（Apache/Nginx/坚果云）对已存在的集合回 405。
            self._send(405)
            return
        self.server.dirs.add(path)
        self._send(201)

    def do_PUT(self) -> None:  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if not self._auth_ok():
            self._send(401)
            return
        name = self._name()
        self.server.methods.append("PUT")
        if name == self.server.fail_name:
            self._send(500, b"disk full")
            return
        self.server.files[name] = body
        self.server.puts.append(name)
        self._send(201)

    def do_DELETE(self) -> None:  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if not self._auth_ok():
            self._send(401)
            return
        name = self._name()
        self.server.methods.append("DELETE")
        self.server.deletes.append(name)
        existed = self.server.files.pop(name, None) is not None
        self._send(204 if existed else 404)

    def do_GET(self) -> None:  # noqa: N802
        if not self._auth_ok():
            self._send(401)
            return
        body = self.server.files.get(self._name())
        if body is None:
            self._send(404)
        else:
            self._send(200, body, "application/octet-stream")

    def do_PROPFIND(self) -> None:  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if not self._auth_ok():
            self._send(401)
            return
        self.server.methods.append("PROPFIND")
        parts = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<d:multistatus xmlns:d="DAV:">',
            '<d:response><d:href>/dav/jz/</d:href><d:propstat><d:prop>'
            '<d:resourcetype><d:collection/></d:resourcetype>'
            "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>",
        ]
        for name in sorted(self.server.files):
            parts.append(
                "<d:response><d:href>/dav/jz/"
                + urllib.parse.quote(name)
                + "</d:href><d:propstat><d:prop><d:resourcetype/></d:prop>"
                "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
            )
        parts.append("</d:multistatus>")
        self._send(207, "".join(parts).encode("utf-8"), "application/xml; charset=utf-8")


class _FakeDav:
    def __init__(self) -> None:
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _FakeDavHandler)
        self.httpd.files: dict[str, bytes] = {}
        self.httpd.methods: list[str] = []
        self.httpd.puts: list[str] = []
        self.httpd.deletes: list[str] = []
        self.httpd.auth_headers: list[str] = []
        self.httpd.dirs: set[str] = set()
        self.httpd.fail_name = ""
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{port}/dav"

    @property
    def files(self) -> dict[str, bytes]:
        return self.httpd.files

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self._saved = (os.environ.get("JZO_DATA_DIR"), settings.workspace_id)
        os.environ["JZO_DATA_DIR"] = str(self.data)
        settings.workspace_id = WS_ID
        self.out = self.root / "local-backups"
        self.out.mkdir()

    def tearDown(self) -> None:
        data, ws = self._saved
        if data is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = data
        settings.workspace_id = ws
        self.tmp.cleanup()

    def _pair(self, stamp: str) -> tuple[Path, Path]:
        stage = self.root / f"stage-{stamp}"
        (stage / "uploads").mkdir(parents=True)
        (stage / "uploads" / "a.png").write_bytes(b"PNG-" + stamp.encode())
        # 打包器只装清单点名的文件（军令 #18-终 阶段二），所以这里必须给出真实清单，
        # 而不是靠「整目录 rglob」的旧默契。
        manifest = {
            "workspace_id": WS_ID,
            "question_count": 0,
            "files": [{
                "path": "uploads/a.png",
                "size": (stage / "uploads" / "a.png").stat().st_size,
                "sha256": backup.sha256_file(stage / "uploads" / "a.png"),
                "category": "uploads",
                "required": True,
            }],
        }
        result = backup.package_snapshot(stage, manifest, self.out, stamp=stamp)
        return result["package"], result["manifest_path"]


class CredentialTest(_Base):
    def test_01_credentials_roundtrip_and_masking(self) -> None:
        saved = backup.save_backup_settings(
            {
                "webdav_enabled": True,
                "local_dir": str(self.out),
                "url": "https://dav.example.com/dav",
                "username": "teacher",
                "password": "s3cret",
                "remote_dir": "jz",
            },
            WS_ID,
        )
        self.assertTrue(saved["local_enabled"] and saved["webdav_enabled"])

        path = backup.backup_settings_path(WS_ID)
        self.assertEqual(
            (self.data / "workspaces" / WS_ID / "backup.json").resolve(), path
        )
        self.assertNotIn("plugins", path.parts)
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("s3cret", on_disk["password"])

        loaded = backup.load_backup_settings(WS_ID)
        self.assertEqual("s3cret", loaded["password"])
        public = backup.public_backup_settings(loaded)
        self.assertNotIn("password", public)
        self.assertTrue(public["password_set"])
        self.assertEqual("••••••••", public["password_masked"])
        self.assertNotIn("s3cret", json.dumps(public, ensure_ascii=False))

        backup.save_backup_settings({"username": "teacher2", "password": "••••••••"}, WS_ID)
        self.assertEqual("s3cret", backup.load_backup_settings(WS_ID)["password"])

        backup.record_upload_result({"ok": True, "uploaded": ["x"]}, WS_ID)
        after = backup.load_backup_settings(WS_ID)
        self.assertEqual({"ok": True, "uploaded": ["x"]}, after["last_upload"])
        self.assertEqual("s3cret", after["password"])
        self.assertNotIn("last_upload", backup.public_backup_settings(after))


class RemoteCleanupTest(_Base):
    def test_01_prune_only_tool_named_files_and_keep_latest(self) -> None:
        names = [
            f"backup_{OLD_STAMP}.zst",
            f"manifest_{OLD_STAMP}.json",
            f"backup_{NEW_STAMP}.zst",
            f"manifest_{NEW_STAMP}.json",
            "notes.txt",
            "archive_backup_20240101_010101_001.zst",
            "backup_latest.zst",
        ]
        doomed = webdav.prune_remote_names(names, keep=1)
        self.assertEqual(
            sorted([f"backup_{OLD_STAMP}.zst", f"manifest_{OLD_STAMP}.json"]), doomed
        )
        self.assertEqual([], webdav.prune_remote_names(names[:4], keep=3))
        self.assertEqual([], webdav.prune_remote_names(names, keep=2))

    def test_02_upload_then_cleanup_leaves_foreign_files(self) -> None:
        fake = _FakeDav()
        self.addCleanup(fake.close)
        fake.files[f"backup_{OLD_STAMP}.zst"] = b"old-zst"
        fake.files[f"manifest_{OLD_STAMP}.json"] = b"{}"
        fake.files["notes.txt"] = b"keep me"
        package, manifest_path = self._pair(NEW_STAMP)
        config = {
            "url": fake.url,
            "username": "teacher",
            "password": "s3cret",
            "remote_dir": "jz",
        }

        result = webdav.upload_backup(config, package, manifest_path)

        self.assertTrue(result["ok"])
        self.assertEqual(
            [package.name, manifest_path.name], result["uploaded"]
        )
        self.assertEqual(
            sorted([f"backup_{OLD_STAMP}.zst", f"manifest_{OLD_STAMP}.json"]),
            sorted(result["deleted"]),
        )
        self.assertEqual(
            {package.name, manifest_path.name, "notes.txt"}, set(fake.files)
        )
        self.assertEqual(package.read_bytes(), fake.files[package.name])
        self.assertEqual(manifest_path.read_bytes(), fake.files[manifest_path.name])
        self.assertIn(package.name, fake.httpd.puts)
        self.assertNotIn("notes.txt", fake.httpd.deletes)
        self.assertTrue(fake.httpd.auth_headers)
        self.assertTrue(all(h.startswith("Basic ") for h in fake.httpd.auth_headers))
        self.assertEqual(
            sorted([p.name for p in self.out.iterdir()]),
            sorted([package.name, manifest_path.name]),
            "本地目录不应出现临时文件",
        )

    def test_03_upload_failure_keeps_old_remote_and_local(self) -> None:
        fake = _FakeDav()
        self.addCleanup(fake.close)
        fake.files[f"backup_{OLD_STAMP}.zst"] = b"old-zst"
        fake.files[f"manifest_{OLD_STAMP}.json"] = b"{}"
        fake.httpd.fail_name = f"manifest_{FAIL_STAMP}.json"
        package, manifest_path = self._pair(FAIL_STAMP)
        config = {
            "url": fake.url,
            "username": "teacher",
            "password": "s3cret",
            "remote_dir": "jz",
        }

        with self.assertRaises(webdav.WebdavError):
            webdav.upload_backup(config, package, manifest_path)

        self.assertEqual([], fake.httpd.deletes, "失败时不得发起任何远端删除")
        self.assertIn(f"backup_{OLD_STAMP}.zst", fake.files)
        self.assertIn(f"manifest_{OLD_STAMP}.json", fake.files)
        self.assertTrue(package.is_file() and manifest_path.is_file(), "本地备份不许被删")

    def test_04_missing_local_pair_never_touches_network(self) -> None:
        with self.assertRaises(webdav.WebdavError):
            webdav.upload_backup(
                {"url": "http://127.0.0.1:9/dav"},
                self.out / f"backup_{NEW_STAMP}.zst",
                self.out / f"manifest_{NEW_STAMP}.json",
            )

    def test_05_existing_remote_dir_405_is_tolerated(self) -> None:
        """第二次上传时目录已存在（405）不得中断上传——真实网盘的常态。"""
        fake = _FakeDav()
        self.addCleanup(fake.close)
        fake.httpd.dirs.add("/dav/jz")
        package, manifest_path = self._pair(NEW_STAMP)
        config = {
            "url": fake.url,
            "username": "teacher",
            "password": "s3cret",
            "remote_dir": "jz",
        }

        result = webdav.upload_backup(config, package, manifest_path)

        self.assertTrue(result["ok"])
        self.assertIn(package.name, fake.files)
        self.assertIn("MKCOL", fake.httpd.methods)


class WebdavValidationTest(unittest.TestCase):
    def test_01_rejects_non_http_and_traversal(self) -> None:
        with self.assertRaises(webdav.WebdavError):
            webdav.ensure_remote_dir({"url": "ftp://dav.example.com"})
        with self.assertRaises(webdav.WebdavError):
            webdav.remote_dir_of({"remote_dir": "../escape"})
        with self.assertRaises(webdav.WebdavError):
            webdav.remote_dir_of({"remote_dir": "."})
        self.assertEqual("jiuzhang-backups", webdav.remote_dir_of({}))
        self.assertEqual("a/b", webdav.remote_dir_of({"remote_dir": "/a/b/"}))

    def test_02_download_rejects_foreign_names_before_network(self) -> None:
        with self.assertRaises(webdav.WebdavError):
            webdav.download_backup(
                {"url": "http://127.0.0.1:9/dav"}, "notes.txt", Path("x")
            )


if __name__ == "__main__":
    unittest.main()
