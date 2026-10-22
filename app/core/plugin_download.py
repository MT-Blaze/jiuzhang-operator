"""按需下载单个插件 zip 包（在线安装的第一步）。

契约来源：PLUGIN_SPEC §1.4。只有用户在「插件索引」页亲手点了某条目的
【在线安装】，底座才会替用户去取那一个 zip；除此之外不存在任何自动下载。
地址守卫复用索引拉取那一套（http/https、无凭证），下载失败一律降级为
可读原因抛 ``PluginInstallError``，不留半个字节在 ``plugins/``。
"""

from __future__ import annotations

import urllib.error
import urllib.request

from app.core.plugin_index import IndexRejected, validate_index_url
from app.core.plugin_install import MAX_ZIP_BYTES, PluginInstallError

DOWNLOAD_TIMEOUT_SECONDS = 30.0
_CHUNK = 256 * 1024


def download_plugin_zip(url: str) -> bytes:
    """按用户点选的地址取回一个 zip 包本体。

    阻塞网络 IO——调用方必须放线程池执行（同步端点或 run_in_threadpool），
    否则会卡死事件循环，主程序跟着一起停摆。

    Raises:
        PluginInstallError: 地址不合法（400）、网络失败（502）、超过 50 MB（413）。
    """
    try:
        target = validate_index_url(url)
    except IndexRejected as exc:
        raise PluginInstallError(str(exc), status=400, code="bad_url") from exc

    request = urllib.request.Request(
        target,
        headers={"Accept": "application/zip, application/octet-stream", "User-Agent": "jiuzhang-operator/local"},
        method="GET",
    )
    chunks: list[bytes] = []
    received = 0
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            while True:
                chunk = response.read(_CHUNK)
                if not chunk:
                    break
                received += len(chunk)
                if received > MAX_ZIP_BYTES:
                    # 半途掐断即可：还没落地任何文件，天然「回滚」
                    raise PluginInstallError("下载超过 50 MB 上限，已中止", status=413, code="too_large")
                chunks.append(chunk)
    except PluginInstallError:
        raise
    except urllib.error.HTTPError as exc:
        raise PluginInstallError(
            "下载地址返回 HTTP %s，换个镜像或稍后再试" % exc.code,
            status=502,
            code="download_failed",
        ) from exc
    except urllib.error.URLError as exc:
        raise PluginInstallError(
            "无法连接下载地址：%s" % getattr(exc, "reason", exc),
            status=502,
            code="download_failed",
        ) from exc
    except Exception as exc:  # 超时、连接中断等一律降级为可读原因
        raise PluginInstallError("下载失败：%s" % exc, status=502, code="download_failed") from exc

    data = b"".join(chunks)
    if not data:
        raise PluginInstallError("下载地址返回了空内容", status=502, code="download_failed")
    return data
