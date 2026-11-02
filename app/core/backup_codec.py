# -*- coding: utf-8 -*-
"""备份包压缩后端的兼容层：同一份包在 Python 3.10 ~ 3.14 之间都要能读写。

**为什么要有这一层**：``compression.zstd`` 是 Python 3.14 才进标准库的（PEP 784），而
``backup_package.py`` 与 ``restore.py`` 过去都写死 ``from compression import zstd``——
3.10/3.11/3.12 的群友一启动就在 import 期 ``ModuleNotFoundError``，备份子系统整块打不开。
这里按 **标准库 zstd → pip zstandard → 标准库 gzip** 逐级降级，本机装得到哪档就用哪档。

**读侧不信扩展名，只认文件头魔数**：zstd 是 ``28 B5 2F FD``，gzip 是 ``1F 8B``。
老师在一台 3.14 机器上打的 zstd 包，拿到只有 gzip 的机器上会收到一句人话
（「本机解不了 zstd，请 pip install zstandard 或升级 Python 3.14」），
而不是崩在 ``tarfile`` 深处的堆栈里。包名仍按 ``backup_<stamp>.zst`` 落盘，
历史备份与 ``BACKUP_FILE_RE``、manifest 门禁都不受影响。
"""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import IO, Any

from app.core.backup_files import BackupError

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
GZIP_MAGIC = b"\x1f\x8b"
DEFAULT_LEVEL = 10


def _load_stdlib_zstd() -> Any | None:
    try:
        from compression import zstd
    except ImportError:
        return None
    return zstd


def _load_pip_zstd() -> Any | None:
    try:
        import zstandard
    except ImportError:
        return None
    return zstandard


ZSTD_MODULE = _load_stdlib_zstd() or _load_pip_zstd()
BACKEND = "zstd" if ZSTD_MODULE is not None else "gzip"


class _GzipWriter(gzip.GzipFile):
    """把 zstd 的 ``level=`` 记号翻译成 gzip 的 ``compresslevel=``（gzip 只吃 1~9）。"""

    def __init__(self, package: str | Path, level: int) -> None:
        super().__init__(str(package), "wb", compresslevel=min(9, max(1, level)))


def open_package(package: str | Path, mode: str = "rb", *, level: int | None = None) -> IO[bytes]:
    """打开备份包的压缩流：写用本机最好的后端，读按文件头魔数决定用什么后端。"""
    if mode.startswith("w"):
        if ZSTD_MODULE is None:
            return _GzipWriter(package, DEFAULT_LEVEL if level is None else level)
        return ZSTD_MODULE.ZstdFile(str(package), "wb", level=level)
    head = _magic(package)
    if head.startswith(GZIP_MAGIC):
        return gzip.GzipFile(str(package), "rb")
    if head.startswith(ZSTD_MAGIC):
        if ZSTD_MODULE is None:
            raise BackupError(
                "这份备份是 zstd 压缩，本机 Python 没有 zstd 能力："
                "请 pip install zstandard，或升级到 Python 3.14")
        return ZSTD_MODULE.ZstdFile(str(package), "rb")
    raise BackupError(f"备份包压缩格式无法识别：{Path(package).name}")


def _magic(package: str | Path) -> bytes:
    try:
        with open(str(package), "rb") as raw:
            return raw.read(4)
    except OSError as exc:
        raise BackupError(f"备份包读不出来：{exc}") from exc


def content_type() -> str:
    """本机写包用的压缩档对应的 MIME，供上传侧如实声明。"""
    return "application/zstd" if BACKEND == "zstd" else "application/gzip"
