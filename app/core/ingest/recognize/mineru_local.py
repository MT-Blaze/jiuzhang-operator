"""MinerU 本地逐题识别：一张单题截图一次本地解析，回填只动那一道。

镜像云端 ``mineru.py`` 的逐题循环，但请求走本机隔离服务（mineru_service
懒起服）。本地 API 实测形状＝``/v1/tasks`` 四步批量（建任务→PUT 上传→
轮询→下载 result.zip 取 markdown.md），与云端 ``/api/v4`` 路径/载荷不同，
故本地请求函数住本文件，云端客户端语义不变。单题等待 900s（CPU 首题慢，
首次解析可能懒下载模型）；失败 ok=False 显性化，不级联、不偷换。
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import urllib.error
import urllib.request
import zipfile
from typing import Any, Callable

from app.core import wire
from app.core.ingest.recognize import shared as recognize_shared

logger = logging.getLogger(__name__)

MINERU_LOCAL_WAIT_SECONDS = 900.0
REQUEST_TIMEOUT = 30
UPLOAD_TIMEOUT = 120
POLL_SECONDS = 2.0
MAX_ZIP_BYTES = 64 * 1024 * 1024
MAX_MARKDOWN_CHARS = 600_000


def _request(url: str, token: str, *, method: str = "GET",
             payload: dict[str, Any] | None = None, raw: bytes | None = None,
             timeout: float = REQUEST_TIMEOUT) -> bytes:
    headers = {"Accept": "application/json", "Authorization": "Bearer " + token}
    data = raw
    if payload is not None:
        data = wire.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw is not None:
        headers["Content-Type"] = "application/octet-stream"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(MAX_ZIP_BYTES)


def _error_text(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = wire.loads(exc.read().decode("utf-8", errors="replace"))
            detail = (body.get("error") or {}).get("message") if isinstance(body, dict) else None
            if detail:
                return str(detail)[:200]
        except (OSError, ValueError):
            pass
        return "HTTP %d" % exc.code
    return str(exc)[:200]


def _pick_markdown(blob: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".md")]
        if not names:
            return ""
        preferred = next(
            (name for name in names
             if name.rsplit("/", 1)[-1].lower() in ("markdown.md", "full.md")),
            names[0])
        return archive.read(preferred).decode("utf-8", errors="replace")


def parse_image(name: str, data: bytes, endpoint: dict[str, str], *,
                wait: float = MINERU_LOCAL_WAIT_SECONDS,
                sleep: Callable[[float], None] = time.sleep,
                clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """本地 /v1/tasks 四步：建任务→上传→轮询→取 markdown；失败如实回报。"""
    base = str(endpoint.get("base_url") or "").rstrip("/")
    token = str(endpoint.get("token") or "")
    if not base.startswith("http://"):
        return {"ok": False, "detail": "本地 MinerU 服务地址缺失"}
    try:
        raw = _request(base + "/v1/tasks", token, method="POST", payload={
            "files": [{"file_name": name, "bytes": len(data)}],
            "output_formats": ["default"],
        })
        created = wire.loads(raw.decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "detail": "本地 MinerU 建任务失败：%s" % _error_text(exc)}
    files = created.get("files") if isinstance(created, dict) else None
    row = files[0] if isinstance(files, list) and files else None
    task_id = str((created or {}).get("task_id") or "")
    upload = (row or {}).get("upload") if isinstance(row, dict) else None
    if not task_id or not isinstance(upload, dict) or not upload.get("url"):
        return {"ok": False, "detail": "本地 MinerU 没有返回上传地址"}
    try:
        _request(str(upload["url"]), token, method="PUT", raw=data,
                 timeout=UPLOAD_TIMEOUT)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "detail": "本地 MinerU 上传题图失败：%s" % _error_text(exc)}
    deadline = clock() + max(1.0, wait)
    last_state = ""
    result_url = ""
    while clock() < deadline:
        sleep(POLL_SECONDS)
        try:
            raw = _request(base + "/v1/tasks/" + task_id, token)
            detail = wire.loads(raw.decode("utf-8", errors="replace"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            return {"ok": False, "detail": "本地 MinerU 查询结果失败：%s" % _error_text(exc)}
        rows = detail.get("files") if isinstance(detail, dict) else None
        item = rows[0] if isinstance(rows, list) and rows else None
        if not isinstance(item, dict):
            continue
        last_state = str(item.get("status") or "")
        if last_state == "completed":
            result_url = str(item.get("result_url") or "")
            break
        if last_state in ("failed", "canceled"):
            message = ((item.get("error") or {}).get("message")
                       if isinstance(item.get("error"), dict) else "") or last_state
            return {"ok": False, "detail": "本地 MinerU 解析失败：%s" % message}
    if not result_url:
        return {"ok": False,
                "detail": "本地 MinerU 在等待时限内没有返回结果"
                          + ("（最后状态：%s）" % last_state if last_state else "")}
    try:
        blob = _request(result_url, token, timeout=UPLOAD_TIMEOUT)
        markdown = _pick_markdown(blob)
    except (urllib.error.URLError, TimeoutError, OSError, zipfile.BadZipFile) as exc:
        return {"ok": False, "detail": "本地 MinerU 结果包下载/解压失败：%s" % _error_text(exc)}
    if not markdown.strip():
        return {"ok": False, "detail": "本地 MinerU 结果包里没有 Markdown"}
    return {"ok": True, "markdown": markdown[:MAX_MARKDOWN_CHARS],
            "detail": "本地 MinerU 已识别"}


async def run(batch_id: str, items: list[dict[str, Any]], indexes: list[int],
              endpoint: dict[str, str],
              route: dict[str, Any],
              on_progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """逐题交本地 MinerU；返回成功下标，失败显性不级联（router 口径）。"""
    if not indexes:
        return {"ok": True, "attempted": 0, "filled": 0, "filled_indexes": [],
                "detail": "没有需要交给本地 MinerU 的题"}
    from app.core.ingest.service import build_documents

    filled_indexes: list[int] = []
    total = len(indexes)
    for position, index in enumerate(indexes, start=1):
        item = items[index]
        note = "正在将第 %d/%d 题交本地 MinerU 解析（首次解析需下载/加载模型，可能较慢）..." % (
            position, total)
        logger.info(note)
        route["note"] = note
        _progress(on_progress, route)
        data = recognize_shared.item_image_bytes(item)
        if not data:
            continue
        outcome = await asyncio.to_thread(
            parse_image, "第%d题.png" % position, data, endpoint,
            wait=MINERU_LOCAL_WAIT_SECONDS)
        if not outcome.get("ok"):
            route["note"] = "第 %d/%d 题本地 MinerU 没成功（%s），继续下一题。" % (
                position, total, str(outcome.get("detail") or "")[:120])
            _progress(on_progress, route)
            continue
        documents, _notes = build_documents(str(outcome.get("markdown") or ""))
        if not documents:
            continue
        document = recognize_shared.merge_local(
            documents[0], item.get("question") or {})
        if recognize_shared.save_back(item, document, batch_id, "ingest.mineru_local"):
            filled_indexes.append(index)
    filled = len(filled_indexes)
    return {
        "ok": filled > 0,
        "attempted": total,
        "filled": filled,
        "filled_indexes": filled_indexes,
        "detail": "" if filled == total else ("只有 %d/%d 道回来了" % (filled, total)),
    }


def _progress(callback: Callable[[dict[str, Any]], None] | None,
              route: dict[str, Any]) -> None:
    if callback is None:
        return
    try:
        callback(route)
    except Exception:  # noqa: BLE001 - 进度写不进去不该打断识别
        pass