"""模型注册表：插件目录（数据驱动 toml）× 通用规则解释器 × 运行时体检 → 三态（D3）。

目录是插件财产（配置归插件卡，2026-11-18）：底座按「声明了 models.catalog 的
启用插件」找目录提供者（同 bank.provider 路由口径），读其安装目录 catalog.toml；
缺失/损坏＝空目录，下拉只剩自动。三态规则是通用契约留底座（Python ingest 路由
同步要用，问不了 iframe）：解释器只认七个规则名，不认任何模型；有哪些模型、
说明怎么写、硬件门槛多少、启用停用，全归插件 catalog＋model_prefs.toml。

状态每次现算，不缓存体检结论（D3b）。本模块只读状态、不开新下载通道：
- 账号指派住当前工作区 config.toml（ai center 既有口径）；
- 权重住当前工作区插件目录 models/（model_store 既有口径）；
- import 探测只做 find_spec；MinerU 本地座体检走 mineru_setup 隔离环境；
- 启用/停用＋默认选择是插件财产，住插件目录 model_prefs.toml。

主公拍板语义（2026-11-18）：没配置/没下载/没指派/被停用的条目不进下拉；
旧批次残留值选中了未就绪条目 → 闸口 normalize 回 auto 并给一句人话原因，
由调用方写进批次 note，绝不静默（D3a）。未知规则＝blocked＋提示更新底座。
"""

from __future__ import annotations

import importlib.util
import tomllib
from typing import Any, Callable

from app.core.ai.platform import center as ai_center
from app.core.config import plugins_dir
from app.core.ingest import hardware, mineru_setup, model_prefs, vlm_setup
from app.core.ingest.layout import model_store

CATALOG_CAPABILITY = "models.catalog"
CATALOG_FILENAME = "catalog.toml"
# 规则集＝契约（同 capabilities 校验口径）：catalog 声明规则名，底座解释。
RULES = ("import_probe", "weight_present", "task_assign",
         "mineru_local", "vlm_local", "vram_gate", "blocked")
_AUTO_PREFS = {"disabled": [], "default_layout": "auto", "default_recognize": "auto",
               "auto_image_seat": "auto", "auto_text_formula_seat": "auto"}


def catalog_provider() -> dict[str, Any] | None:
    """目录提供者：声明了 models.catalog 的启用插件，按发现顺序取第一个。"""
    from app.core.plugins.registry import discover_plugins

    for info in discover_plugins().get("plugins", []):
        if info.get("enabled") and CATALOG_CAPABILITY in (info.get("capabilities") or []):
            return info
    return None


def _document(plugin_id: str | None = None) -> dict[str, Any]:
    if plugin_id is None:
        provider = catalog_provider()
        if provider is None:
            return {}
        plugin_id = str(provider["id"])
    path = plugins_dir() / plugin_id / CATALOG_FILENAME
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return {}


def _entries(doc: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = doc.get("entry")
    if not isinstance(rows, list):
        return ()
    return tuple(dict(row) for row in rows
                 if isinstance(row, dict) and row.get("id"))


def catalog(plugin_id: str | None = None) -> tuple[dict[str, Any], ...]:
    """目录全量条目（数据驱动）；无提供者/文件缺失/损坏返回空，下拉只剩自动。"""
    return _entries(_document(plugin_id))


def vram_tiers(plugin_id: str | None = None) -> list[dict[str, Any]]:
    rows = _document(plugin_id).get("vram_tier")
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _import_ok(module: str) -> bool:
    try:
        return bool(module) and importlib.util.find_spec(module) is not None
    except Exception:  # noqa: BLE001 - 体检失败只该降级，不该拖垮清单
        return False


def _say(template: Any, ctx: dict[str, Any]) -> str:
    """人话模板由 catalog 给、底座填占位符；填不上原样念，不静默不崩。"""
    text = str(template or "")
    try:
        return text.format(**ctx)
    except (KeyError, IndexError, ValueError):
        return text


def _verdict(state: str, detail: str, action: str = "", assigned: str = "") -> dict[str, str]:
    return {"state": state, "detail": detail, "action": action, "assigned": assigned}


def _rule_import_probe(item: dict[str, Any], ctx: dict[str, Any],
                       hw: dict[str, Any], tiers: list[dict[str, Any]]) -> dict[str, str]:
    if _import_ok(str(item.get("probe") or "")):
        return _verdict("ready", _say(item.get("ready_detail"), ctx))
    return _verdict("degraded", _say(item.get("degraded_detail"), ctx),
                    str(item.get("degraded_action") or ""))


def _rule_weight_present(item: dict[str, Any], ctx: dict[str, Any],
                         hw: dict[str, Any], tiers: list[dict[str, Any]]) -> dict[str, str]:
    if model_store.present(str(item.get("store") or "full")):
        return _verdict("ready", _say(item.get("ready_detail"), ctx))
    return _verdict("degraded", _say(item.get("degraded_detail"), ctx),
                    str(item.get("degraded_action") or ""))


def _rule_task_assign(item: dict[str, Any], ctx: dict[str, Any],
                      hw: dict[str, Any], tiers: list[dict[str, Any]]) -> dict[str, str]:
    task = str(item.get("task") or "")
    try:
        binding = ai_center.find_mineru() if task == "mineru" else ai_center.resolve_task(task)
    except Exception:  # noqa: BLE001 - 任务键写坏只该降级，不该拖垮清单
        binding = None
    if binding is not None and binding.is_configured:
        filled = {**ctx, "name": binding.name, "model": binding.model}
        return _verdict("ready", _say(item.get("ready_detail"), filled),
                        assigned=binding.name)
    return _verdict("degraded", _say(item.get("degraded_detail"), ctx),
                    str(item.get("degraded_action") or "assign"))


def _rule_mineru_local(item: dict[str, Any], ctx: dict[str, Any],
                       hw: dict[str, Any], tiers: list[dict[str, Any]]) -> dict[str, str]:
    install = mineru_setup.status()
    if install.get("state") == "error":
        filled = {**ctx, "message": install.get("message", "")}
        return _verdict("blocked", _say(item.get("install_error_detail"), filled), "install")
    check = mineru_setup.health()
    if check["ok"]:
        filled = {**ctx, "version": check["version"]}
        return _verdict("ready", _say(item.get("ready_detail"), filled))
    if check["state"] == "error":
        filled = {**ctx, "message": check["message"]}
        return _verdict("blocked", _say(item.get("broken_detail"), filled), "install")
    return _verdict("degraded", _say(item.get("missing_detail"), ctx), "install")


def _rule_vlm_local(item: dict[str, Any], ctx: dict[str, Any],
                    hw: dict[str, Any], tiers: list[dict[str, Any]]) -> dict[str, str]:
    """本地 VLM 座（T6）：安装体检＋权重＋显存门组合；显存门沿用 hardware.probe。"""
    install = vlm_setup.status()
    if install.get("state") == "error":
        filled = {**ctx, "message": install.get("message", "")}
        return _verdict("blocked", _say(item.get("install_error_detail"), filled), "install_vlm")
    check = vlm_setup.health()
    if not check["ok"]:
        if check["state"] == "error":
            filled = {**ctx, "message": check["message"]}
            return _verdict("blocked", _say(item.get("broken_detail"), filled), "install_vlm")
        return _verdict("degraded", _say(item.get("missing_detail"), ctx), "install_vlm")
    if not vlm_setup.weights_ready():
        return _verdict("degraded", _say(item.get("missing_detail"), ctx), "install_vlm")
    need = int(item.get("min_vram") or 6)
    vram = float(hw.get("vram_gb") or 0)
    label = str(hw.get("vram_label") or "读不到")
    if vram < need:
        filled = {**ctx, "vram_label": label, "min_vram": need}
        detail = _say(item.get("low_detail"), filled)
        disclosure = str(hw.get("detail") or "")
        if disclosure:
            detail += "（%s）" % disclosure
        return _verdict("blocked", detail, str(item.get("low_action") or "assign"))
    filled = {**ctx, "version": check["version"], "vram_label": label, "min_vram": need}
    return _verdict("ready", _say(item.get("ready_detail"), filled))


def _rule_vram_gate(item: dict[str, Any], ctx: dict[str, Any],
                    hw: dict[str, Any], tiers: list[dict[str, Any]]) -> dict[str, str]:
    need = int(item.get("min_vram") or 6)
    vram = float(hw.get("vram_gb") or 0)
    label = str(hw.get("vram_label") or "读不到")
    if vram < need:
        filled = {**ctx, "vram_label": label, "min_vram": need}
        return _verdict("blocked", _say(item.get("low_detail"), filled),
                        str(item.get("low_action") or "assign"))
    tier = hardware.tier_for(vram, tiers)
    fits = str(tier.get("fits")) if tier else "入门档"
    filled = {**ctx, "vram_label": label, "fits": fits}
    return _verdict("blocked", _say(item.get("ok_detail"), filled),
                    str(item.get("ok_action") or ""))


def _rule_blocked(item: dict[str, Any], ctx: dict[str, Any],
                  hw: dict[str, Any], tiers: list[dict[str, Any]]) -> dict[str, str]:
    return _verdict("blocked", _say(item.get("detail"), ctx),
                    str(item.get("action") or ""))


_HANDLERS: dict[str, Callable[..., dict[str, str]]] = {
    "import_probe": _rule_import_probe,
    "weight_present": _rule_weight_present,
    "task_assign": _rule_task_assign,
    "mineru_local": _rule_mineru_local,
    "vlm_local": _rule_vlm_local,
    "vram_gate": _rule_vram_gate,
    "blocked": _rule_blocked,
}


def _judge(item: dict[str, Any], hw: dict[str, Any],
           tiers: list[dict[str, Any]]) -> dict[str, str]:
    """一条目录 × 运行时状态 → 三态＋人话说明＋动作；只认规则名，不认模型。"""
    rule = str(item.get("rule") or "")
    handler = _HANDLERS.get(rule)
    if handler is None:
        return _verdict("blocked",
                        "底座不认识这条规则「%s」，请更新底座后再用该条目。"
                        % (rule or "缺 rule 声明"))
    ctx = {"id": str(item.get("id") or ""), "name": str(item.get("name") or "")}
    return handler(item, ctx, hw, tiers)


def status() -> dict[str, Any]:
    """整块给配置页与下拉：目录全量×三态＋硬件快照＋档位表＋默认选择。"""
    provider = catalog_provider()
    plugin_id = str(provider["id"]) if provider else None
    doc = _document(plugin_id) if plugin_id else {}
    prefs = model_prefs.load(plugin_id) if plugin_id else dict(_AUTO_PREFS)
    disabled = set(prefs["disabled"])
    hw = hardware.probe()
    tiers = [dict(row) for row in doc.get("vram_tier") or []
             if isinstance(row, dict)]
    entries: list[dict[str, Any]] = []
    for item in _entries(doc):
        entry = dict(item)
        entry.update(_judge(item, hw, tiers))
        entry["enabled"] = entry["id"] not in disabled
        entries.append(entry)
    return {"ok": True, "entries": entries, "hardware": hw,
            "vram_tiers": tiers,
            "vram_note": str(doc.get("vram_note") or ""),
            "auto_seats": auto_seats(plugin_id),
            "defaults": {"layout": prefs["default_layout"],
                         "recognize": prefs["default_recognize"],
                         "auto_image_seat": prefs.get("auto_image_seat", "auto"),
                         "auto_text_formula_seat": prefs.get("auto_text_formula_seat", "auto")}}


def auto_seats(plugin_id: str | None = None) -> dict[str, str]:
    """自动分流生效座（T6）：prefs 改座优先，选「自动」沿用 catalog [auto] 段。

    空串＝目录没给默认座：调用方必须显性失败引导，绝不静默换座。
    """
    if plugin_id is None:
        provider = catalog_provider()
        plugin_id = str(provider["id"]) if provider else None
    doc = _document(plugin_id) if plugin_id else {}
    section = doc.get("auto") if isinstance(doc.get("auto"), dict) else {}
    prefs = model_prefs.load(plugin_id) if plugin_id else dict(_AUTO_PREFS)
    seats: dict[str, str] = {}
    for key, catalog_key in (("auto_image_seat", "image_seat"),
                             ("auto_text_formula_seat", "text_formula_seat")):
        value = str(prefs.get(key) or "auto")
        seats[key] = str(section.get(catalog_key) or "") if value == "auto" else value
    return seats


def entry_state(seat_id: str) -> dict[str, Any] | None:
    """按 id 取一条目录×三态（重认/分流取席用）；不在目录返回 None。"""
    for entry in status()["entries"]:
        if entry["id"] == str(seat_id or ""):
            return entry
    return None


def _gate(value: Any, normalize: Callable[[Any], str],
          label: str) -> tuple[str, str]:
    """选中未就绪/已停用/未接线 → 回 auto＋原因；auto 与乱填值不带原因。

    目录里已就绪但调度还没接线的条目由 normalize 归 auto，这里按原始值找回
    条目，照念 catalog 的 gate_note，绝不静默（D3a）。
    """
    picked = normalize(value)
    raw = str(value or "").strip().lower()
    target = picked if picked != "auto" else raw
    if not target or target == "auto":
        return "auto", ""
    for entry in status()["entries"]:
        if entry["id"] != target:
            continue
        if not entry.get("enabled", True):
            return "auto", ("%s引擎「%s」已停用，本次回到自动瀑布。"
                            % (label, entry["name"]))
        if entry["state"] != "ready":
            return "auto", ("%s引擎「%s」未就绪（%s），本次回到自动瀑布。"
                            % (label, entry["name"], entry["detail"]))
        note = str(entry.get("gate_note") or "")
        if note:
            return "auto", "%s引擎「%s」%s" % (label, entry["name"], note)
        return picked, ""
    return "auto", ""


def gate_layout(value: Any) -> tuple[str, str]:
    from app.core.ingest.layout import router as layout_router

    return _gate(value, layout_router.normalize_engine, "版面")


def gate_recognize(value: Any) -> tuple[str, str]:
    from app.core.ingest.recognize import router as recognize_router

    return _gate(value, recognize_router.normalize_engine, "识别")