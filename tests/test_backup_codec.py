# -*- coding: utf-8 -*-
"""压缩降级层的判据：群友的 Python 没有 3.14 的 ``compression.zstd``，备份子系统不能跟着塌。

``compression.zstd`` 是 PEP 784（Python 3.14）才进标准库的，写死这一句就等于让
3.10~3.13 的群友开机即 ``ModuleNotFoundError``。`app/core/backup_codec.py` 按
标准库 zstd → pip zstandard → gzip 降级，读侧按文件头魔数分辨格式。
本机跑在 3.14 上，所以「没有 zstd」这条路靠**把 ZSTD_MODULE 打桩成 None** 来真跑，
而不是只在代码里看一眼。

运行：``.venv/Scripts/python.exe -m unittest tests.test_backup_codec``
"""

from __future__ import annotations

import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import backup_codec as codec  # noqa: E402
from app.core.backup_files import BackupError  # noqa: E402


class BackendTest(unittest.TestCase):
    def test_01_backend_is_known(self) -> None:
        self.assertIn(codec.BACKEND, ("zstd", "gzip"))
        self.assertEqual(codec.content_type(),
                         "application/zstd" if codec.BACKEND == "zstd" else "application/gzip")


class RoundTripTest(unittest.TestCase):
    """写进去什么，读出来就得是什么——两种后端各跑一遍真实读写。"""

    def _roundtrip(self, writer) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "backup_20261102T100000Z_zst"
            with writer(package, "wb", level=10) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    raw = b"q_abcdef123456|frac{1}{2}\n"
                    info = tarfile.TarInfo("banks/org.jiuzhang.bank-engine.db")
                    info.size = len(raw)
                    archive.addfile(info, io.BytesIO(raw))
            self.assertTrue(package.is_file())
            with codec.open_package(package, "rb") as compressed:
                with tarfile.open(fileobj=compressed, mode="r") as archive:
                    names = archive.getnames()
                    self.assertEqual(archive.extractfile(names[0]).read(), b"q_abcdef123456|frac{1}{2}\n")

    def test_01_native_backend(self) -> None:
        self._roundtrip(codec.open_package)

    def test_02_gzip_fallback_when_zstd_absent(self) -> None:
        saved = codec.ZSTD_MODULE
        codec.ZSTD_MODULE = None
        try:
            self._roundtrip(codec.open_package)
            with tempfile.TemporaryDirectory() as tmp:
                package = Path(tmp) / "backup_x.zst"
                with codec.open_package(package, "wb", level=10) as stream:
                    stream.write(b"hello")
                # 降级后即使文件名叫 .zst，内容也是 gzip 魔数——读侧认魔数不认扩展名
                self.assertTrue(package.read_bytes().startswith(codec.GZIP_MAGIC))
        finally:
            codec.ZSTD_MODULE = saved

    def test_03_zstd_package_without_zstd_says_so(self) -> None:
        saved = codec.ZSTD_MODULE
        codec.ZSTD_MODULE = None
        try:
            with tempfile.TemporaryDirectory() as tmp:
                package = Path(tmp) / "backup_from_314.zst"
                package.write_bytes(codec.ZSTD_MAGIC + b"pretend-zstd-body")
                with self.assertRaises(BackupError) as caught:
                    codec.open_package(package, "rb")
                self.assertIn("zstandard", str(caught.exception))
        finally:
            codec.ZSTD_MODULE = saved

    def test_04_unknown_magic_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "backup_bogus.zst"
            package.write_bytes(b"not-a-compressed-package")
            with self.assertRaises(BackupError):
                codec.open_package(package, "rb")

    def test_05_missing_file_reports_plainly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(BackupError):
                codec.open_package(Path(tmp) / "不存在的包.zst", "rb")
