"""识别引擎共用的小零件：取题图、拼契约题目、单题回填。

只做无状态搬运，不决定走哪一级，也不直接出网——路由与降级归
``recognize_router``，具体引擎只管「怎么认、认出来怎么落」。
"""

from __future__ import annotations

from typing import Any

from app.core import pending_assets

_URI_PREFIXES = ("/static/pending/", "/static/uploads/")


def first_image_uri(item: dict[str, Any]) -> str:
    """题图在池内的同源地址；没有就交空串。"""
    document = item.get("question") if isinstance(item.get("question"), dict) else {}
    for image in document.get("images") or []:
        if not isinstance(image, dict):
            continue
        uri = str(image.get("uri") or "")
        if uri.startswith(_URI_PREFIXES):
            return uri
    for asset in item.get("assets") or []:
        if isinstance(asset, dict) and asset.get("name"):
            return "/static/pending/" + str(asset["name"])
    return ""


def item_image_bytes(item: dict[str, Any]) -> bytes:
    """单题截图的原始 PNG：优先按池内资产名取，取不到再看题面里的 uri。"""
    for asset in item.get("assets") or []:
        name = str((asset or {}).get("name") or "") if isinstance(asset, dict) else ""
        if not name:
            continue
        try:
            return pending_assets.asset_path(name).read_bytes()
        except Exception:  # noqa: BLE001 - 单个资产读不到就试下一个，绝不编图
            continue
    uri = first_image_uri(item)
    if uri.startswith("/static/pending/"):
        try:
            return pending_assets.asset_path(uri.rsplit("/", 1)[-1]).read_bytes()
        except Exception:  # noqa: BLE001
            return b""
    return b""


def context_of(item: dict[str, Any]) -> dict[str, Any]:
    """交给视觉模型的上下文只留能帮它定位的字段，别把整题再传一遍。"""
    document = item.get("question") if isinstance(item.get("question"), dict) else {}
    return {
        "type": str(document.get("type") or ""),
        "stem": str(document.get("stem") or "")[:6000],
        "question_no": str((document.get("source") or {}).get("question_no") or ""),
    }


def document_from_ai(question: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """AI 识别结果 → 契约题目；题图与来源沿用本地切题那一条，绝不丢。"""
    from app.core.ingest import DEFAULT_DIFFICULTY, _document

    options = [
        {"key": str(option.get("key") or ""), "content": str(option.get("content") or "")}
        for option in (question.get("options") or [])
        if isinstance(option, dict) and str(option.get("content") or "").strip()
    ]
    kind = str(question.get("type") or "")
    document = _document(
        str(question.get("stem") or ""),
        options,
        str(question.get("answer") or ""),
        1 if kind == "fill_blank" else 0,
        str(question.get("solution") or ""),
        str(question.get("question_no")
            or (base.get("source") or {}).get("question_no") or ""),
    )
    difficulty = str(question.get("difficulty") or "").upper()
    if difficulty:
        document["difficulty"] = difficulty or DEFAULT_DIFFICULTY
    source = dict(base.get("source") or {})
    if question.get("question_no"):
        source["question_no"] = str(question["question_no"])
    if source:
        document["source"] = source
    if base.get("images"):
        document["images"] = list(base["images"])
    return document


def merge_local(incoming: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    """云端正文字段替换，题图、来源与页面定位仍用本地那一条。"""
    if local.get("source"):
        incoming["source"] = dict(local["source"])
    if local.get("images"):
        incoming["images"] = list(local["images"])
    return incoming


def save_back(item: dict[str, Any], document: dict[str, Any], batch_id: str,
              origin: str) -> bool:
    """单题回填；失败只丢这一道，不拖垮整批。"""
    from app.core import pending_bank

    try:
        pending_bank.save_draft(
            [{"question": document, "pending_id": item.get("id"),
              "page_no": item.get("page_no", 1)}],
            batch_id=batch_id,
            origin=origin,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


async def guard(call, *args) -> dict[str, Any]:
    """跑一级引擎；异常只记失败，交给下一级，不拖垮整批。"""
    try:
        return await call(*args)
    except Exception as exc:  # noqa: BLE001 - 单级异常只该降级
        return {"ok": False, "attempted": 0, "filled": 0,
                "filled_indexes": [], "detail": f"识别引擎异常：{exc}"}


def remaining(pending: list[int], outcome: dict[str, Any]) -> list[int]:
    """这一级回填成功后，还没人接手的下标。"""
    done = set(int(index) for index in outcome.get("filled_indexes") or [])
    return [index for index in pending if index not in done]


def note_for(picked: str, full: bool, rate: float,
             ai: dict[str, Any] | None, mineru: dict[str, Any] | None,
             total: int, pending: list[int], threshold: float) -> str:
    """把整条瀑布的结果写成老师能读懂的一句路由账。"""
    total = max(total, 1)
    left = ("，%d 道保持本地切图" % len(pending)) if pending else ""
    if picked == "mineru":
        if mineru is None or not mineru.get("binding"):
            return "MinerU 没有可用的账号：先在【API 配置】里指派云端解析，保留本地切图待人工核对。"
        return "MinerU 逐题解析完成：%d/%d 道回填成功%s。" % (
            mineru["filled"], mineru["attempted"], left)
    if ai and ai["filled"]:
        if full:
            trigger = "（达到分诊线）" if rate >= threshold else ""
            return "坏题率 %.1f%%%s：已触发并发全量 OCR，%d/%d 道回填成功%s。" % (
                rate * 100.0, trigger, ai["filled"], ai["attempted"], left)
        return "坏题率 %.1f%% 低于分诊线，已局部修补 %d/%d 道坏题%s。" % (
            rate * 100.0, ai["filled"], ai["attempted"], left)
    if mineru and mineru["filled"]:
        return "AI 未成功（%s），已改用 MinerU：%d/%d 道回填成功%s。" % (
            (ai or {}).get("detail") or "不可用", mineru["filled"],
            mineru["attempted"], left)
    if mineru is not None and not mineru.get("binding"):
        return "AI 未成功（%s），MinerU 也没有可用账号：保留本地切图待人工核对。" % (
            (ai or {}).get("detail") or "不可用")
    if mineru is not None:
        return "云端识别都没成功（MinerU：%s），保留本地切图待人工核对。" % (
            mineru.get("detail") or "不可用")
    return "AI 未成功（%s），保留本地切图待人工核对。" % (
        (ai or {}).get("detail") or "不可用")
