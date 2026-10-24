"""WebDAV 备份客户端：整包 PUT，不做分片与断点续传。

边界（军令 #17 第三步）：
- 凭据由调用方从 ``data/workspaces/<ws_id>/backup.json`` 读出后传入，本模块不落盘、不打日志；
- 上传的就是本地备份文件本身，不生成临时包；
- 上传失败不删远端旧份；只有整包 + manifest 都成功后才按「只删本工具命名文件」清理到最近 1 份。
"""

from __future__ import annotations

import base64
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from app.core.backup import BACKUP_FILE_RE, MANIFEST_FILE_RE

DAV_NS = "DAV:"
PROPFIND_BODY = (
    b'<?xml version="1.0" encoding="utf-8"?>'
    b'<d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/></d:prop></d:propfind>'
)


class WebdavError(Exception):
    """上传/列目录/下载失败；message 可直接回给前端（绝不含凭据）。"""


def _base_url(config: dict[str, Any]) -> str:
    url = str(config.get("url") or "").strip().rstrip("/")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise WebdavError("WebDAV 地址必须是 http/https 绝对地址")
    return url


def remote_dir_of(config: dict[str, Any]) -> str:
    raw = str(config.get("remote_dir") or "").strip().strip("/")
    parts = [part for part in raw.split("/") if part]
    if any(part in (".", "..") for part in parts):
        raise WebdavError("远端目录不合法")
    return "/".join(parts) or "jiuzhang-backups"


def _quote(segment: str) -> str:
    return urllib.parse.quote(segment, safe="")


def _auth_header(config: dict[str, Any]) -> dict[str, str]:
    username = str(config.get("username") or "")
    password = str(config.get("password") or "")
    if not username and not password:
        return {}
    raw = f"{username}:{password}".encode("utf-8")
    return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}


def _request(
    method: str,
    url: str,
    config: dict[str, Any],
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    expected: tuple[int, ...] = (200, 201, 204),
    timeout: float = 60.0,
) -> tuple[int, bytes]:
    merged = dict(headers or {})
    merged.update(_auth_header(config))
    request = urllib.request.Request(url, data=data, method=method, headers=merged)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            body = response.read()
    except urllib.error.HTTPError as exc:
        body = b""
        detail = ""
        try:
            body = exc.read()
            detail = body.decode("utf-8", "replace")[:200]
        except Exception:  # noqa: BLE001 - 错误体读不到就算了
            body, detail = b"", ""
        finally:
            exc.close()
        # 405/409/404 这类「已在预期内」的状态必须当成正常返回，
        # 否则 ensure_remote_dir 的「目录已存在」容忍逻辑永远走不到。
        if exc.code in expected:
            return exc.code, body
        raise WebdavError(f"{method} {url} 返回 HTTP {exc.code}{('：' + detail) if detail else ''}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WebdavError(f"{method} {url} 失败：{exc}") from exc
    if status not in expected:
        raise WebdavError(f"{method} {url} 返回 HTTP {status}")
    return status, body


def ensure_remote_dir(config: dict[str, Any]) -> str:
    """逐级 MKCOL；已存在（405/409）不算错。返回目录 URL。"""
    _base_url(config)
    segments = [part for part in remote_dir_of(config).split("/") if part]
    current = _base_url(config)
    for segment in segments:
        current = current + "/" + _quote(segment)
        try:
            _request("MKCOL", current, config, expected=(200, 201, 204, 405, 409))
        except WebdavError:
            # 409 在部分服务端表示父目录尚未就绪；下一轮父目录已建时重试一次
            _request("MKCOL", current, config, expected=(200, 201, 204, 405))
    return current


def list_remote_names(config: dict[str, Any]) -> list[str]:
    """PROPFIND Depth:1，只返回本级文件名（不递归、不含目录）。"""
    directory = ensure_remote_dir(config)
    _, body = _request(
        "PROPFIND",
        directory,
        config,
        data=PROPFIND_BODY,
        headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
        expected=(207, 200),
    )
    if not body:
        return []
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise WebdavError("WebDAV 目录清单不是合法 XML") from exc
    names: list[str] = []
    for response in root.findall(f".//{{{DAV_NS}}}response"):
        href = response.findtext(f"{{{DAV_NS}}}href") or ""
        propstat = response.find(f"{{{DAV_NS}}}propstat")
        resource = propstat.find(f"{{{DAV_NS}}}prop/{{{DAV_NS}}}resourcetype") if propstat is not None else None
        if resource is not None and resource.find(f"{{{DAV_NS}}}collection") is not None:
            continue
        path = urllib.parse.unquote(href).rstrip("/")
        name = path.rsplit("/", 1)[-1] if path else ""
        if name:
            names.append(name)
    return sorted(set(names))


def prune_remote_names(names: list[str], keep: int = 1) -> list[str]:
    """只挑本工具命名的 backup_* / manifest_* 删除，保留最近 keep 份。"""
    keep = max(1, int(keep))
    stamps = sorted(
        {
            match.group(1)
            for name in names
            for match in (BACKUP_FILE_RE.match(name), MANIFEST_FILE_RE.match(name))
            if match
        },
        reverse=True,
    )
    doomed = set(stamps[keep:])
    return sorted(
        name for name in names
        if (BACKUP_FILE_RE.match(name) or MANIFEST_FILE_RE.match(name))
        and (BACKUP_FILE_RE.match(name) or MANIFEST_FILE_RE.match(name)).group(1) in doomed
    )


def _put_file(config: dict[str, Any], directory: str, local: Path, content_type: str) -> str:
    name = Path(local).name
    data = Path(local).read_bytes()
    _request(
        "PUT",
        directory + "/" + _quote(name),
        config,
        data=data,
        headers={"Content-Type": content_type, "Content-Length": str(len(data))},
        expected=(200, 201, 204),
    )
    return name


def upload_backup(
    config: dict[str, Any],
    package_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    """上传本地备份包与同名 manifest；全部成功后才清理远端旧份。"""
    package = Path(package_path)
    manifest = Path(manifest_path)
    if not package.is_file() or not manifest.is_file():
        raise WebdavError("本地备份文件不完整，未上传")
    directory = ensure_remote_dir(config)
    uploaded: list[str] = []
    try:
        uploaded.append(_put_file(config, directory, package, "application/zstd"))
        uploaded.append(_put_file(config, directory, manifest, "application/json"))
    except WebdavError:
        # 上传失败：旧份原样保留，至少还有一份可用。
        raise
    warnings: list[str] = []
    deleted: list[str] = []
    try:
        names = list_remote_names(config)
        for name in prune_remote_names(names, keep=1):
            try:
                _request(
                    "DELETE",
                    directory + "/" + _quote(name),
                    config,
                    expected=(200, 202, 204, 404),
                )
                deleted.append(name)
            except WebdavError as exc:
                warnings.append(f"旧份 {name} 删除失败：{exc}")
    except WebdavError as exc:
        warnings.append(f"远端清理失败（新份已上传）：{exc}")
    return {
        "ok": True,
        "uploaded": uploaded,
        "deleted": deleted,
        "warnings": warnings,
        "remote_name": package.name,
    }


def download_backup(config: dict[str, Any], remote_name: str, dest: Path) -> Path:
    """下载单个远端文件到本地临时区；名字必须先过本工具白名单。"""
    if not (BACKUP_FILE_RE.match(remote_name) or MANIFEST_FILE_RE.match(remote_name)):
        raise WebdavError("远端文件名不合法")
    directory = ensure_remote_dir(config)
    _, body = _request("GET", directory + "/" + _quote(remote_name), config, expected=(200,))
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return dest
