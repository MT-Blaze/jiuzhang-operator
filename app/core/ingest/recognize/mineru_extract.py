"""MinerU 兜底通道：纯扫描件没有文本层时，试一次云端 OCR。

只实现 MinerU 官方 v4 批量接口（与账号池里的 ``MinerU`` 账号配套）：

1. ``POST {base}/api/v4/file-urls/batch`` 申请上传地址；
2. ``PUT`` 原文件到签名地址；
3. 轮询 ``GET {base}/api/v4/extract-results/batch/{batch_id}``；
4. 下载 ``full_zip_url`` 里的 Markdown。

任何一步失败都返回 ``{ok: False, detail}``，由调用方退回切图模式：
MinerU 只是备选通道，绝不能因为它连不上就吞掉整批卷子。
"""

from __future__ import annotations

from app.core import wire  # noqa: E402
import io
import secrets
import time
import urllib.error
import urllib.request
import zipfile
from typing import Any, Callable

REQUEST_TIMEOUT = 30
UPLOAD_TIMEOUT = 120
POLL_SECONDS = 2.0
# 单题截图可能排队很久：按 15 分钟等，逐题发送时由调用方显式传值。
MAX_WAIT_SECONDS = 900.0
MAX_ZIP_BYTES = 64 * 1024 * 1024
MAX_MARKDOWN_CHARS = 600_000


def _api_root(base_url: str) -> str:
    text = str(base_url or "").rstrip("/")
    return text if text.endswith("/api/v4") else text + "/api/v4"


def _request(url: str, *, method: str = "GET", token: str = "",
             payload: dict[str, Any] | None = None, raw: bytes | None = None,
             timeout: float = REQUEST_TIMEOUT) -> bytes:
    headers = {"Accept": "application/json"}
    data = raw
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = wire.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw is not None:
        headers["Content-Type"] = "application/octet-stream"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(MAX_ZIP_BYTES)


def _pick_markdown(blob: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".md")]
        if not names:
            return ""
        preferred = next(
            (name for name in names if name.rsplit("/", 1)[-1].lower() == "full.md"), names[0]
        )
        return archive.read(preferred).decode("utf-8", errors="replace")


def extract(name: str, data: bytes, base_url: str, token: str, *,
            model: str = "", wait: float = MAX_WAIT_SECONDS,
            sleep: Callable[[float], None] = time.sleep,
            clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """提交一份文件并等结果；超时与错误都如实回报。"""
    if not token:
        return {"ok": False, "detail": "MinerU 账号没有可用的 API Key"}
    root = _api_root(base_url)
    if not root.startswith(("http://", "https://")):
        return {"ok": False, "detail": "MinerU Base URL 不是 http(s) 地址"}
    version = model if model in ("vlm", "pipeline") else "vlm"
    data_id = "jzo-" + secrets.token_hex(4)
    try:
        raw = _request(
            root + "/file-urls/batch",
            method="POST",
            token=token,
            payload={
                "enable_formula": True,
                "language": "ch",
                "files": [{"name": name, "data_id": data_id}],
                "model_version": version,
            },
        )
        document = wire.loads(raw.decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
            ValueError) as exc:
        return {"ok": False, "detail": f"MinerU 申请上传地址失败：{exc}"}
    code = document.get("code") if isinstance(document, dict) else None
    if not isinstance(document, dict) or code is None or int(code) != 0:
        detail = document.get("msg") if isinstance(document, dict) else document
        return {"ok": False, "detail": f"MinerU 拒绝了这份文件：{detail}"}
    body = document.get("data") if isinstance(document.get("data"), dict) else {}
    batch_id = str(body.get("batch_id") or "")
    urls = body.get("file_urls") if isinstance(body.get("file_urls"), list) else []
    upload_url = str(urls[0] if urls else "")
    if not batch_id or not upload_url:
        return {"ok": False, "detail": "MinerU 没有返回上传地址或 batch_id"}

    try:
        _request(upload_url, method="PUT", raw=data, timeout=UPLOAD_TIMEOUT)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return {"ok": False, "detail": f"MinerU 上传原文件失败：{exc}"}

    deadline = clock() + max(1.0, wait)
    result_url = ""
    last_state = ""
    while clock() < deadline:
        sleep(POLL_SECONDS)
        try:
            raw = _request(root + "/extract-results/batch/" + batch_id, token=token)
            document = wire.loads(raw.decode("utf-8", errors="replace"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
                ValueError) as exc:
            return {"ok": False, "detail": f"MinerU 查询结果失败：{exc}"}
        body = document.get("data") if isinstance(document, dict) else {}
        rows = body.get("extract_result") if isinstance(body, dict) else None
        row = next(
            (item for item in (rows or []) if isinstance(item, dict)
             and str(item.get("data_id") or "") == data_id),
            (rows or [None])[0] if isinstance(rows, list) else None,
        )
        if not isinstance(row, dict):
            continue
        last_state = str(row.get("state") or "")
        if last_state == "done":
            result_url = str(row.get("full_zip_url") or "")
            break
        if last_state in ("failed", "error"):
            detail = row.get("err_msg") or row.get("message") or last_state
            return {"ok": False, "detail": f"MinerU 解析失败：{detail}"}
    if not result_url:
        return {
            "ok": False,
            "detail": "MinerU 在等待时限内没有返回结果"
                      + (f"（最后状态：{last_state}）" if last_state else ""),
        }

    try:
        blob = _request(result_url, timeout=UPLOAD_TIMEOUT)
        markdown = _pick_markdown(blob)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
            zipfile.BadZipFile) as exc:
        return {"ok": False, "detail": f"MinerU 结果包下载/解压失败：{exc}"}
    if not markdown.strip():
        return {"ok": False, "detail": "MinerU 结果包里没有 Markdown"}
    return {
        "ok": True,
        "markdown": markdown[:MAX_MARKDOWN_CHARS],
        "detail": "MinerU 已识别",
    }
