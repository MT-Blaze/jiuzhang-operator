"""插件索引（plugins.json）的解析与按需拉取。

索引地址来自用户在「插件索引」页的输入框（默认预填官方国内镜像，可当场改掉，
点【拉取清单】才发请求，PLUGIN_SPEC §1.3）。主源失败时按 ``plugin_sources``
登记的顺序自动切换备用镜像——只在用户填的是官方地址时成立，用户改成第三方
索引后底座只访问那一个地址。本模块只做「取回一份 JSON 并校验其结构」，
**不解压、不安装、不执行**，也不做任何签名/摘要/授权校验——
索引里的地址是不是官方，由用户自己判断。
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from app.core import plugin_sources

INDEX_VERSION = "1.0"
MAX_INDEX_BYTES = 512 * 1024
FETCH_TIMEOUT_SECONDS = 6.0
MIRROR_TIMEOUT_SECONDS = 5.0
MAX_ENTRIES = 200

_ALLOWED_SCHEMES = {"http", "https"}
_PLUGIN_ID = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


class IndexRejected(Exception):
    """索引地址或索引内容不可用。"""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IndexRejected(message)


def validate_index_url(url: str) -> str:
    """只接受明文的 http(s) 绝对地址，且不得携带任何凭证。"""
    candidate = str(url or "").strip()
    _require(bool(candidate), "请先填入插件索引的地址")
    parsed = urlparse(candidate)
    _require(
        parsed.scheme.lower() in _ALLOWED_SCHEMES,
        "只允许 http 或 https 地址（收到：%s），不接受 file、data 等本地协议" % (parsed.scheme or "无协议头"),
    )
    _require(bool(parsed.hostname), "地址缺少主机名")
    _require(
        not parsed.username and not parsed.password,
        "地址里不得携带用户名或密钥，索引服务不该需要凭证",
    )
    return candidate


def describe_public_url(url: str) -> str:
    """给界面与日志用的安全写法：只留协议与主机，剥掉路径查询。"""
    parsed = urlparse(url)
    return "%s://%s" % (parsed.scheme, parsed.netloc)


def _validate_download_url(value: Any, field: str, where: str) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("%s.%s 必须是字符串" % (where, field))
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES or not parsed.hostname:
        raise ValueError("%s.%s 必须是 http(s) 绝对地址" % (where, field))
    if parsed.username or parsed.password:
        raise ValueError("%s.%s 不得携带凭证" % (where, field))
    return value.strip()


def _parse_entry(entry: Any, position: int) -> dict[str, Any]:
    where = "entries[%d]" % position
    if not isinstance(entry, dict):
        raise ValueError("%s 必须是对象" % where)

    plugin_id = entry.get("id")
    if not isinstance(plugin_id, str) or _PLUGIN_ID.fullmatch(plugin_id) is None:
        raise ValueError("%s 的 id 必须是反向域名格式" % where)

    name = entry.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 64:
        raise ValueError("%s 的 name 长度必须为 1–64" % where)

    version = entry.get("version")
    if not isinstance(version, str) or _SEMVER.fullmatch(version) is None:
        raise ValueError("%s 的 version 必须是语义化版本" % where)

    zip_url = _validate_download_url(entry.get("zip_url"), "zip_url", where)
    if zip_url is None:
        raise ValueError("%s 缺少 zip_url（插件包的下载地址）" % where)

    mirrors_raw = entry.get("mirrors", [])
    if mirrors_raw is None:
        mirrors_raw = []
    if not isinstance(mirrors_raw, list):
        raise ValueError("%s 的 mirrors 必须是数组" % where)
    mirrors = [_validate_download_url(item, "mirrors[%d]" % idx, where) for idx, item in enumerate(mirrors_raw)]

    description = entry.get("description", "")
    if not isinstance(description, str) or len(description) > 200:
        raise ValueError("%s 的 description 长度必须为 0–200" % where)

    homepage = _validate_download_url(entry.get("homepage"), "homepage", where)

    return {
        "id": plugin_id,
        "name": name,
        "version": version,
        "zip_url": zip_url,
        "mirrors": [item for item in mirrors if item],
        "description": description,
        "homepage": homepage,
        "kind": entry.get("kind") if isinstance(entry.get("kind"), str) else "",
        "api_version": entry.get("api_version") if isinstance(entry.get("api_version"), str) else "",
    }


def parse_index(payload: Any) -> dict[str, Any]:
    """把一份索引 JSON 拆成「可用条目 + 被拒条目」。

    单条坏数据只让它自己出局并在界面上如实列出，不得让整份索引判死——
    否则用户面对的是「拉取失败」四个字，而不是一百条里那一条写错了字段。
    """
    _require(isinstance(payload, dict), "插件索引的顶层必须是 JSON 对象")
    _require(
        payload.get("index_version") == INDEX_VERSION,
        "index_version 必须为 %s（收到：%r）" % (INDEX_VERSION, payload.get("index_version")),
    )
    entries_raw = payload.get("entries")
    _require(isinstance(entries_raw, list), "entries 必须是数组")
    _require(len(entries_raw) <= MAX_ENTRIES, "entries 条数超过 %d 条上限" % MAX_ENTRIES)

    entries: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for position, raw in enumerate(entries_raw):
        try:
            entry = _parse_entry(raw, position)
        except ValueError as exc:
            rejected.append({"position": str(position), "reason": str(exc)})
            continue
        if entry["id"] in seen_ids:
            rejected.append({"position": str(position), "reason": "%s 的 id 与前一条重复" % entry["id"]})
            continue
        seen_ids.add(entry["id"])
        entries.append(entry)

    updated_at = payload.get("updated_at")
    return {
        "index_version": INDEX_VERSION,
        "index_name": payload.get("name") if isinstance(payload.get("name"), str) else "",
        "updated_at": updated_at if isinstance(updated_at, str) else "",
        "entries": entries,
        "rejected": rejected,
        "entry_count": len(entries),
        "rejected_count": len(rejected),
    }


def _fetch_once(target: str, timeout: float) -> dict[str, Any]:
    """向一个具体地址发一次只读 GET，返回解析后的索引（不含来源元数据）。"""
    request = urllib.request.Request(
        target,
        headers={"Accept": "application/json", "User-Agent": "jiuzhang-operator/local"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_INDEX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise IndexRejected("索引地址返回 HTTP %s" % exc.code) from exc
    except urllib.error.URLError as exc:
        raise IndexRejected("无法连接该地址：%s" % getattr(exc, "reason", exc)) from exc
    except Exception as exc:  # 超时、连接中断等一律降级为可读原因
        raise IndexRejected("拉取失败：%s" % exc) from exc

    _require(len(body) <= MAX_INDEX_BYTES, "索引超过 %d KB 上限" % (MAX_INDEX_BYTES // 1024))

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndexRejected("该地址返回的不是合法 JSON（%s）" % exc) from exc

    return parse_index(payload)


def fetch_index(url: str, allow_mirrors: bool = True) -> dict[str, Any]:
    """按用户填入的地址取回并解析索引；主源失败时自动切换官方备用镜像。

    失败一律抛 ``IndexRejected`` 并带上可行动的原因；若全部镜像都失败，
    原因里逐条列出每个主机与失败原因，用户不必猜是哪一层挂了。
    """
    requested = validate_index_url(url)
    candidates = [
        validate_index_url(item)
        for item in plugin_sources.index_candidates(requested, allow_mirrors)
    ]

    attempts: list[dict[str, Any]] = []
    for position, target in enumerate(candidates):
        timeout = FETCH_TIMEOUT_SECONDS if position == 0 else MIRROR_TIMEOUT_SECONDS
        try:
            index = _fetch_once(target, timeout)
        except IndexRejected as exc:
            attempts.append(
                {
                    "host": describe_public_url(target),
                    "ok": False,
                    "reason": str(exc),
                }
            )
            continue

        attempts.append({"host": describe_public_url(target), "ok": True, "reason": ""})
        index["source_url"] = target
        index["source_host"] = describe_public_url(target)
        index["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        index["requested_host"] = describe_public_url(requested)
        index["fallback_used"] = target != requested
        index["attempts"] = attempts
        return index

    detail = "；".join(
        "%s（%s）" % (item["host"], item["reason"]) for item in attempts
    )
    raise IndexRejected(
        "所有索引地址均不可用：%s。可在上方输入框手动填写其他索引地址后重试" % detail
    )
