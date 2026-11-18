"""版面引擎总调度：自动走瀑布，选了谁就只走谁（2026-11-18 主公拍板）。

- 自动：图片卷 OCR 主路优先（D7），不达标退回 python → yolo → cloud 瀑布；
- RapidOCR·快：只跑本地 OCR 切题；
- YOLO·版面：只跑本机 YOLO；
- 云端视觉：只跑云端版面。

具体档失败 ok=False 显性化，不级联、不偷换；旧值 cloud 兼容映射到云端视觉。
每一级都返回同一个 JSON 结构：``{ok, engine, pages, columns, detail}``；
``pages`` 是 ``{页码: [题块]}``，题块字段与 ``render.service`` 完全一致。
各级实现由调用方注入，测试不必真的起 YOLO 或云端。
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

LAYOUT_AUTO = "auto"
LAYOUT_OCR = "rapidocr_fast"
LAYOUT_YOLO = "yolo"
LAYOUT_CLOUD = "cloud_vision"
LAYOUT_ENGINES = (LAYOUT_AUTO, LAYOUT_OCR, LAYOUT_YOLO, LAYOUT_CLOUD)

# 老插件只会发旧引擎名：映射到新档位，旧调用方不必跟着改。
_ALIASES = {"cloud": LAYOUT_CLOUD, "ocr": LAYOUT_OCR}

# 队列里只写引擎名；自动永远从 python 起，具体档只有一级。
_PLANS = {
    LAYOUT_AUTO: ("python", "yolo", "cloud"),
    LAYOUT_OCR: ("ocr",),
    LAYOUT_YOLO: ("yolo",),
    LAYOUT_CLOUD: ("cloud",),
}


def normalize_engine(value: Any) -> str:
    """前端交来的引擎名 → 白名单内的一个；认不出就当自动，绝不猜。"""
    text = str(value or "").strip().lower()
    if text in LAYOUT_ENGINES:
        return text
    return _ALIASES.get(text, LAYOUT_AUTO)


def plan(engine: Any) -> tuple[str, ...]:
    """本次选择要依次尝试的引擎队列。"""
    return _PLANS[normalize_engine(engine)]


def default_providers() -> dict[str, Callable[[dict[str, Any]], Any]]:
    """默认实现按需导入：各子模块共用同一份请求结构，互不依赖。"""
    from app.core.ingest.layout import cloud as layout_cloud, python as layout_python, yolo as layout_yolo
    from app.core.ingest.recognize import ocr as recognize_ocr

    def ocr(request: dict[str, Any]) -> Any:
        return recognize_ocr.detect(request["name"], request["data"], request["pages"])

    return {
        "python": layout_python.detect,
        "yolo": layout_yolo.detect,
        "cloud": layout_cloud.detect,
        "ocr": ocr,
    }


async def run_scan(name: str, data: bytes, pages: list[dict[str, Any]],
                   engine: str = LAYOUT_AUTO,
                   health: dict[str, Any] | None = None,
                   providers: dict[str, Callable[[dict[str, Any]], Any]] | None = None
                   ) -> dict[str, Any]:
    """自动档：图片型卷 OCR 主路优先（决策台账 D7），不达标才退回原版面瀑布。

    具体档：跳过主路判断，只跑选中的那一级，失败显性化。
    """
    picked = normalize_engine(engine)
    if picked == LAYOUT_AUTO and not (health or {}).get("has_text_layer"):
        from app.core.ingest.recognize import ocr as recognize_ocr
        layout = recognize_ocr.detect(name, data, pages)
        if layout.get("ok"):
            return layout
    return await run(name, data, pages, picked, providers)


async def run(name: str, data: bytes, pages: list[dict[str, Any]],
              engine: str = LAYOUT_AUTO,
              providers: dict[str, Callable[[dict[str, Any]], Any]] | None = None) -> dict[str, Any]:
    """按队列逐级探路；第一个交出题块的引擎胜出。具体档队列只有一级。"""
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
                "lines_by_page": result.get("lines_by_page") or {},
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
        "detail": ("选中的版面引擎没找到题块（只走选中引擎，不降级）"
                   if picked != LAYOUT_AUTO else "所有版面引擎都没找到题块"),
    }