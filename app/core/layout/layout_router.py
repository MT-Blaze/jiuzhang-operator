"""版面引擎总调度：只按顺序分发，不实现任何一种探测。

铁律：纯 Python 永远排第一。三种选择只决定后面还能不能往下走——

- 自动：python → yolo → cloud
- YOLO：python → yolo → cloud
- 云端：python → cloud（跳过 YOLO）

每一级都返回同一个 JSON 结构：``{ok, engine, pages, columns, detail}``；
``pages`` 是 ``{页码: [题块]}``，题块字段与 ``page_render`` 完全一致。
各级实现由调用方注入，测试不必真的起 YOLO 或云端。
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

LAYOUT_AUTO = "auto"
LAYOUT_YOLO = "yolo"
LAYOUT_CLOUD = "cloud"
LAYOUT_ENGINES = (LAYOUT_AUTO, LAYOUT_YOLO, LAYOUT_CLOUD)

# 队列里只写引擎名；哪一级能跑由当前选择决定，顺序永远从 python 起。
_PLANS = {
    LAYOUT_AUTO: ("python", "yolo", "cloud"),
    LAYOUT_YOLO: ("python", "yolo", "cloud"),
    LAYOUT_CLOUD: ("python", "cloud"),
}


def normalize_engine(value: Any) -> str:
    """前端交来的引擎名 → 白名单内的一个；认不出就当自动，绝不猜。"""
    text = str(value or "").strip().lower()
    return text if text in LAYOUT_ENGINES else LAYOUT_AUTO


def plan(engine: Any) -> tuple[str, ...]:
    """本次选择要依次尝试的引擎队列。"""
    return _PLANS[normalize_engine(engine)]


def default_providers() -> dict[str, Callable[[dict[str, Any]], Any]]:
    """默认实现按需导入：三个子模块共用同一份请求结构，互不依赖。"""
    from app.core.layout import layout_cloud, layout_python, layout_yolo

    return {
        "python": layout_python.detect,
        "yolo": layout_yolo.detect,
        "cloud": layout_cloud.detect,
    }


async def run(name: str, data: bytes, pages: list[dict[str, Any]],
              engine: str = LAYOUT_AUTO,
              providers: dict[str, Callable[[dict[str, Any]], Any]] | None = None) -> dict[str, Any]:
    """按队列逐级探路；第一个交出题块的引擎胜出。"""
    picked = normalize_engine(engine)
    table = providers if providers is not None else default_providers()
    request = {"name": name, "data": data, "pages": pages}
    attempts: list[dict[str, Any]] = []
    statuses: list[dict[str, str]] = []
    for key in plan(picked):
        provider = table.get(key)
        if provider is None:
            attempts.append({"engine": key, "ok": False, "detail": "引擎没有注册"})
            continue
        try:
            result = provider(request)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:  # noqa: BLE001 - 单级异常只该降级，不该拖垮整批
            result = {"ok": False, "detail": f"{key} 探路异常：{exc}"}
        ok = bool(result.get("ok")) and bool(result.get("pages"))
        attempts.append({"engine": key, "ok": ok,
                         "detail": str(result.get("detail") or "")})
        statuses.extend(item for item in result.get("status") or []
                        if isinstance(item, dict))
        if ok:
            return {
                "ok": True,
                "requested": picked,
                "engine": key,
                "pages": result.get("pages") or {},
                "columns": result.get("columns") or {},
                "attempts": attempts,
                "status": statuses,
                "detail": str(result.get("detail") or ""),
            }
    return {
        "ok": False,
        "requested": picked,
        "engine": "",
        "pages": {},
        "columns": {},
        "attempts": attempts,
        "status": statuses,
        "detail": "所有版面引擎都没找到题块",
    }
