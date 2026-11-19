"""识别引擎总调度（T6 拍板）：自动＝按卷类型分流，选了谁就只走谁。

- 自动＋纯图卷 → catalog [auto] 段 image_seat 默认整题座直转（初值 MinerU 本地）；
- 自动＋文字卷 → 组合路：文字直取正文＋公式按坐标裁图送 text_formula_seat；
  无坐标/坏题走整题重认兜底并 note 明示；公式座失败→公式标待核，正文不动。
- 卷类型判定复用 ingest triage 既有 text_layer 字段，不另造判定、不挨个试。
- 默认座未就绪/未装 → 显性失败清单＋人话引导（装/指派/改默认），绝不静默换座。
- 具体档：引擎名单与步骤全由插件 catalog 声明（plan_recognize／aliases_recognize），
  底座只认步骤实现名、不认模型；失败 ok=False 显性化，不级联、不偷换。
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from app.core.ai.platform import center as ai_center
from app.core.ingest.recognize import (
    ai as recognize_ai, formula as recognize_formula, local as recognize_local,
    mineru as recognize_mineru, mineru_local as recognize_mineru_local,
    mineru_service, shared as recognize_shared, vlm_local as recognize_vlm_local,
    vlm_service,
)

RECOGNIZE_AUTO = "auto"
# 坏题率分诊线只供 triage 统计口径沿用；自动分流不再按它走瀑布（T6）。
BAD_RATE_THRESHOLD = 0.30


def _recognize_entries() -> list[dict[str, Any]]:
    from app.core.ingest import registry

    return [item for item in registry.catalog()
            if str(item.get("capability") or "") in ("recognize", "both")]


def normalize_engine(value: Any) -> str:
    """前端交来的引擎名 → 目录内的一个；认不出就当自动，绝不猜。"""
    text = str(value or "").strip().lower()
    if not text or text in (RECOGNIZE_AUTO, "local_ai"):
        return RECOGNIZE_AUTO
    for item in _recognize_entries():
        entry_id = str(item["id"])
        if text == entry_id.lower():
            return entry_id
        if text in [str(alias).lower() for alias in item.get("aliases_recognize") or []]:
            return entry_id
    return RECOGNIZE_AUTO


def from_legacy_channel(value: Any) -> str:
    """四通道老口径 → 识别引擎；认不出就当自动。"""
    return normalize_engine(value)


def plan(engine: Any) -> tuple[str, ...]:
    """具体档要走的步骤队列来自 catalog 数据；自动＝分流，不再是步骤队列。"""
    picked = normalize_engine(engine)
    if picked == RECOGNIZE_AUTO:
        return ()
    for item in _recognize_entries():
        if str(item["id"]) == picked:
            return tuple(str(step) for step in item.get("plan_recognize") or [])
    return ()


def _surface(route: dict[str, Any], step: str, reason: str, detail: str) -> None:
    """失败进失败清单（复用失败显性化资产）：人话成因＋现场，可重试。"""
    failures = route.setdefault("failures", [])
    for entry in failures:
        if entry.get("step") == step:
            return
    failures.append({"file": "", "page_no": 0, "step": step,
                     "reason": reason[:400], "detail": detail[:4000],
                     "retryable": True})


def _auto_seat(kind: str) -> tuple[str, dict[str, Any] | None]:
    """自动分流默认座（prefs 改座优先，其次 catalog [auto] 段）＋其三态。"""
    from app.core.ingest import registry

    seats = registry.auto_seats()
    seat = seats["auto_image_seat" if kind == "image" else "auto_text_formula_seat"]
    return seat, (registry.entry_state(seat) if seat else None)


async def _fill_single(picked: str, batch_id: str, items: list[dict[str, Any]],
                       total: int, route: dict[str, Any],
                       on_progress: Callable[[dict[str, Any]], None] | None,
                       indexes: list[int] | None = None) -> dict[str, Any]:
    """具体档：只走选中的通道，失败 ok=False 显性化，不级联不偷换。"""
    pending = list(range(total)) if indexes is None else list(indexes)
    steps = plan(picked)
    if steps == ("ai",):
        ai = await recognize_shared.guard(recognize_ai.run, batch_id, items, "all",
                                          {"total": total, "bad": total, "rate": 1.0,
                                           "bad_indexes": pending})
        pending = recognize_shared.remaining(pending, ai)
        route["mode"] = picked
        if ai.get("ok") and not pending:
            route["note"] = "云端视觉逐题识别完成：%d/%d 道回填成功。" % (
                ai["filled"], ai["attempted"])
        else:
            reason = "云端视觉识别未全部成功（%s），只走选中引擎，不降级，保留本地切图待人工核对。" % (
                ai.get("detail") or "不可用")
            route["note"] = reason + (("，%d 道保持本地切图" % len(pending)) if pending else "")
            _surface(route, "识别·云端视觉", reason, str(ai.get("detail") or ""))
    elif steps == ("mineru",):
        binding = ai_center.find_mineru()
        if binding is None:
            route["mode"] = picked
            reason = "MinerU 没有可用的账号：先在【API 配置】里指派云端解析，保留本地切图待人工核对。"
            route["note"] = reason
            _surface(route, "识别·MinerU", reason, "账号池里没有可用的 MinerU 指派")
        else:
            mineru = await recognize_shared.guard(
                recognize_mineru.run, batch_id, items, pending, binding,
                route, on_progress)
            mineru["binding"] = True
            pending = recognize_shared.remaining(pending, mineru)
            route["mode"] = picked
            if mineru.get("ok") and not pending:
                route["note"] = "MinerU 逐题解析完成：%d/%d 道回填成功。" % (
                    mineru["filled"], mineru["attempted"])
            else:
                reason = "MinerU 解析未全部成功（%s），只走选中引擎，不降级，保留本地切图待人工核对。" % (
                    mineru.get("detail") or "不可用")
                route["note"] = reason + (("，%d 道保持本地切图" % len(pending)) if pending else "")
                _surface(route, "识别·MinerU", reason, str(mineru.get("detail") or ""))
    elif steps in (("mineru_local",), ("vlm_local",)):
        service = mineru_service if steps[0] == "mineru_local" else vlm_service
        runner = (recognize_mineru_local if steps[0] == "mineru_local"
                  else recognize_vlm_local)
        label = "MinerU本地" if steps[0] == "mineru_local" else "本地VLM"
        ready = await asyncio.to_thread(service.ensure_ready)
        if not ready.get("ok"):
            route["mode"] = picked
            reason = "%s 服务不可用（%s），只走选中引擎，不降级，保留本地切图待人工核对。" % (
                "本地 MinerU" if steps[0] == "mineru_local" else "本地 VLM",
                ready.get("detail") or "未知原因")
            route["note"] = reason
            _surface(route, "识别·" + label, reason, str(ready.get("detail") or ""))
        else:
            local = await recognize_shared.guard(
                runner.run, batch_id, items, pending, ready, route, on_progress)
            pending = recognize_shared.remaining(pending, local)
            route["mode"] = picked
            if local.get("ok") and not pending:
                route["note"] = "%s 逐题解析完成：%d/%d 道回填成功。" % (
                    label, local["filled"], local["attempted"])
            else:
                reason = "%s 解析未全部成功（%s），只走选中引擎，不降级，保留本地切图待人工核对。" % (
                    label, local.get("detail") or "不可用")
                route["note"] = reason + (("，%d 道保持本地切图" % len(pending)) if pending else "")
                _surface(route, "识别·" + label, reason, str(local.get("detail") or ""))
    else:
        route["mode"] = picked
        reason = "选中引擎的解析通道尚未接线（%s），保留本地切图待人工核对。" % (
            "/".join(steps) if steps else "目录未声明步骤")
        route["note"] = reason
        _surface(route, "识别·选中引擎", reason, "catalog plan_recognize 未接到底座通道")
    route["phase"] = "done"
    route["done"] = True
    return route


async def _auto_image(batch_id: str, items: list[dict[str, Any]],
                      route: dict[str, Any],
                      on_progress: Callable[[dict[str, Any]], None] | None,
                      indexes: list[int] | None = None,
                      prefix: str = "自动分流（纯图卷）") -> dict[str, Any]:
    """纯图卷/整题兜底：默认整题座直转；未就绪显性失败引导，绝不静默换座。"""
    seat, entry = _auto_seat("image")
    route["auto_image_seat"] = seat
    if not seat or entry is None:
        reason = ("%s：默认整题座缺失（catalog [auto] 段没给 image_seat）。"
                  "请到【模型配置】→「自动分流默认」选一个就绪座。" % prefix)
        route["mode"] = "auto"
        route["note"] = reason
        _surface(route, "识别·自动分流", reason, "auto image_seat 缺失或不在目录")
    elif entry.get("state") != "ready" or not entry.get("enabled", True):
        reason = ("%s：默认座「%s」未就绪（%s）。不偷换引擎：请到【模型配置】安装/指派，"
                  "或在「自动分流默认」改选就绪座。" % (
                      prefix, entry.get("name") or seat, entry.get("detail") or "已停用"))
        route["mode"] = "auto"
        route["note"] = reason
        _surface(route, "识别·自动分流", reason, str(entry.get("detail") or ""))
    else:
        await _fill_single(seat, batch_id, items, len(items), route, on_progress, indexes)
        route["note"] = "%s→默认座「%s」。%s" % (prefix, entry.get("name") or seat,
                                                route.get("note") or "")
    route["phase"] = "done"
    route["done"] = True
    return route


async def _auto_text(batch_id: str, items: list[dict[str, Any]],
                     report: dict[str, Any], route: dict[str, Any],
                     on_progress: Callable[[dict[str, Any]], None] | None) -> dict[str, Any]:
    """文字卷组合路：文字直取正文＋公式裁图送默认公式座；无坐标/坏题整题兜底。"""
    total = len(items)
    local = recognize_local.probe(items, report)
    bad = set(local["bad_indexes"])
    good = [index for index in range(total) if index not in bad]
    seat, _entry = _auto_seat("text_formula")
    route["auto_formula_seat"] = seat
    page_images, pdf_bytes = await asyncio.to_thread(
        recognize_formula.batch_context, batch_id)
    combo = await recognize_formula.run_combo(
        batch_id, items, good, seat, route, on_progress, page_images, pdf_bytes)
    notes = ["自动分流（文字卷）→组合路：文字直取正文。"]
    if combo["attempted"]:
        notes.append("公式裁图 %d 道交「%s」，%d 道原位回填。" % (
            combo["attempted"], seat or "无", combo["filled"]))
    if combo["pending_marks"]:
        notes.append("%d 道题公式标待核（%s），正文保留文字直取、不整题降级。" % (
            combo["pending_marks"], combo["seat_reason"] or "公式转写未成功"))
    elif combo["seat_reason"]:
        notes.append(combo["seat_reason"])
    fallback = sorted(bad | set(combo["no_coord_indexes"]))
    if fallback:
        notes.append("%d 道无公式坐标或坏题，走整题重认兜底并明示。" % len(fallback))
        await _auto_image(batch_id, items, route, on_progress, indexes=fallback,
                          prefix="整题兜底")
        notes.append(str(route.get("note") or ""))
    route["mode"] = "auto_combo"
    route["note"] = " ".join(note for note in notes if note)
    route["phase"] = "done"
    route["done"] = True
    return route


async def fill_batch(batch_id: str, items: list[dict[str, Any]], engine: str,
                     report: dict[str, Any], route: dict[str, Any],
                     on_progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """自动档按卷类型分流（复用 triage 的 text_layer）；具体档只走选中通道。"""
    picked = normalize_engine(engine)
    total = len(items)
    if picked != RECOGNIZE_AUTO:
        return await _fill_single(picked, batch_id, items, total, route, on_progress)
    if bool(route.get("text_layer")):
        return await _auto_text(batch_id, items, report, route, on_progress)
    return await _auto_image(batch_id, items, route, on_progress)