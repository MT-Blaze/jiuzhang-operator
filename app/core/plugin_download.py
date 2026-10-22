"""按需下载单个插件 zip 包（在线安装的下载半步）。

契约来源：PLUGIN_SPEC §1.4。只有用户在「插件索引」页亲手点了某条目的
【在线安装】，底座才会替用户去取那一个 zip；除此之外不存在任何自动下载。
地址守卫复用索引拉取那一套（http/https、无凭证），下载失败一律降级为
可读原因抛 ``PluginInstallError``，不留半个字节在 ``plugins/``。

2026-10-24 v0.5.1：主直链失败时按索引条目自带的 ``mirrors`` 依次回退。
镜像仍来自用户点选的那一条，底座不跨条目、不批量、不自动更新。
"""

from __future__ import annotations

import urllib.error
import urllib.request

from app.core.plugin_index import IndexRejected, describe_public_url, validate_index_url
from app.core.plugin_install import MAX_ZIP_BYTES, PluginInstallError

DOWNLOAD_TIMEOUT_SECONDS = 30.0
MIRROR_TIMEOUT_SECONDS = 20.0
MAX_MIRRORS = 8
_CHUNK = 256 * 1024


def _candidate_urls(url: str, mirrors: list[str] | None) -> list[str]:
    """校验并去重本次允许尝试的地址；非法地址在触网前出局。"""
    raw: list[object] = [url]
    raw.extend(mirrors or [])
    valid: list[str] = []
    invalid: list[str] = []
    for item in raw[: MAX_MIRRORS + 1]:
        try:
            candidate = validate_index_url(str(item or ""))
        except IndexRejected as exc:
            invalid.append(str(exc))
            continue
        if candidate not in valid:
            valid.append(candidate)
    if not valid:
        raise PluginInstallError(
            invalid[0] if invalid else "没有可用的下载地址",
            status=400,
            code="bad_url",
        )
    return valid


def _download_once(target: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        target,
        headers={"Accept": "application/zip, application/octet-stream", "User-Agent": "jiuzhang-operator/local"},
        method="GET",
    )
    chunks: list[bytes] = []
    received = 0
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
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


def download_plugin_zip_sources(url: str, mirrors: list[str] | None = None) -> tuple[bytes, str]:
    """按主地址 + 镜像顺序取回 zip，返回 ``(数据, 实际使用的地址)``。"""
    targets = _candidate_urls(url, mirrors)
    failures: list[str] = []
    for position, target in enumerate(targets):
        timeout = DOWNLOAD_TIMEOUT_SECONDS if position == 0 else MIRROR_TIMEOUT_SECONDS
        try:
            return _download_once(target, timeout), target
        except PluginInstallError as exc:
            if exc.status == 413:
                raise
            failures.append("%s（%s）" % (describe_public_url(target), exc.message))
    raise PluginInstallError(
        "所有下载地址均失败：%s" % "；".join(failures),
        status=502,
        code="download_failed",
    )


def download_plugin_zip(url: str) -> bytes:
    """按用户点选的地址取回一个 zip 包本体（单地址兼容入口）。

    阻塞网络 IO——调用方必须放线程池执行（同步端点或 run_in_threadpool），
    否则会卡死事件循环，主程序跟着一起停摆。

    Raises:
        PluginInstallError: 地址不合法（400）、网络失败（502）、超过 50 MB（413）。
    """
    data, _ = download_plugin_zip_sources(url)
    return data
