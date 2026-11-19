"""模型注册表的 HTTP 口子：只读聚合＋MinerU/本地 VLM/RapidOCR 准档/PP-FormulaNet·M/L 一键装＋配置勾选代笔。

注册表状态每次现算（插件目录 × 通用规则 × 运行时体检），不出网、不碰库；
下载与指派动作走既有的 layout.model_download 与 API 配置中心。写口都带写令牌：
MinerU 与本地 VLM 安装只由老师点击发起（国内镜像）；启用/停用＋默认选择
用请求插件自身 id 代笔进其插件目录 model_prefs.toml，绝不落宿主 data/；
未声明 models.catalog 的插件没有目录就没有勾选语义，一律 403。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.core.ingest import (
    formula_setup, mineru_setup, model_prefs, ocr_setup, registry, vlm_setup,
)
from app.core.security import require_write_token

router = APIRouter(tags=["models"])


@router.get("/api/models/registry", summary="模型目录 × 运行时三态（ready/degraded/blocked）")
def models_registry(probe: int = Query(1)) -> dict[str, Any]:
    # probe=0＝启动注入下拉：复用上次硬件快照，不跑探针（2.20.0 卡§1）。
    return registry.status(probe_hardware=bool(probe))


@router.get("/api/models/mineru/status", summary="本地 MinerU 安装进度（只读）")
def mineru_status() -> dict[str, Any]:
    return mineru_setup.status()


@router.post(
    "/api/models/mineru/install",
    status_code=202,
    summary="一键安装本地 MinerU（engines/mineru/ 隔离环境，国内镜像）",
    dependencies=[Depends(require_write_token)],
)
def mineru_install() -> dict[str, Any]:
    try:
        return mineru_setup.start_install()
    except mineru_setup.MineruSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/models/vlm/status", summary="本地 VLM 安装进度（只读）")
def vlm_status() -> dict[str, Any]:
    return vlm_setup.status()


@router.post(
    "/api/models/vlm/install",
    status_code=202,
    summary="一键安装本地 VLM（engines/vlm/ 隔离环境＋GGUF 权重，国内镜像）",
    dependencies=[Depends(require_write_token)],
)
def vlm_install() -> dict[str, Any]:
    try:
        return vlm_setup.start_install()
    except vlm_setup.VlmSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/models/vlm/uninstall",
    summary="卸载本地 VLM（先停服再删 engines/vlm/，老师点击＋确认发起）",
    dependencies=[Depends(require_write_token)],
)
def vlm_uninstall() -> dict[str, Any]:
    from app.core.ingest.recognize import vlm_service

    vlm_service.stop()
    try:
        return vlm_setup.uninstall()
    except vlm_setup.VlmSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/models/mineru/uninstall",
    summary="卸载本地 MinerU（先停服再删 engines/mineru/，老师点击＋确认发起）",
    dependencies=[Depends(require_write_token)],
)
def mineru_uninstall() -> dict[str, Any]:
    from app.core.ingest.recognize import mineru_service

    mineru_service.stop()
    try:
        return mineru_setup.uninstall()
    except mineru_setup.MineruSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/models/ocr/status", summary="RapidOCR·准权重安装进度（只读）")
def ocr_status() -> dict[str, Any]:
    return ocr_setup.status()


@router.post(
    "/api/models/ocr/install",
    status_code=202,
    summary="一键安装 RapidOCR·准（engines/ocr/models/ 两件 medium 权重，国内镜像）",
    dependencies=[Depends(require_write_token)],
)
def ocr_install() -> dict[str, Any]:
    try:
        return ocr_setup.start_install()
    except ocr_setup.OcrSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/models/ocr/uninstall",
    summary="卸载 RapidOCR·准（丢引擎缓存再删 engines/ocr/，老师点击＋确认发起）",
    dependencies=[Depends(require_write_token)],
)
def ocr_uninstall() -> dict[str, Any]:
    try:
        return ocr_setup.uninstall()
    except ocr_setup.OcrSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/models/formula/status", summary="PP-FormulaNet·M 权重安装进度（只读）")
def formula_status() -> dict[str, Any]:
    return formula_setup.status()


@router.get("/api/models/formula_l/status", summary="PP-FormulaNet·L 权重安装进度（只读）")
def formula_l_status() -> dict[str, Any]:
    return formula_setup.status("l")


@router.post(
    "/api/models/formula/install",
    status_code=202,
    summary="一键安装 PP-FormulaNet·M（engines/formula/models/ 两件权重，国内镜像）",
    dependencies=[Depends(require_write_token)],
)
def formula_install() -> dict[str, Any]:
    try:
        return formula_setup.start_install()
    except formula_setup.FormulaSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/models/formula/uninstall",
    summary="卸载 PP-FormulaNet·M（丢引擎缓存再删本档两件权重，老师点击＋确认发起）",
    dependencies=[Depends(require_write_token)],
)
def formula_uninstall() -> dict[str, Any]:
    try:
        return formula_setup.uninstall()
    except formula_setup.FormulaSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/models/formula_l/install",
    status_code=202,
    summary="一键安装 PP-FormulaNet·L（engines/formula/models/ 两件权重，国内镜像）",
    dependencies=[Depends(require_write_token)],
)
def formula_l_install() -> dict[str, Any]:
    try:
        return formula_setup.start_install("l")
    except formula_setup.FormulaSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/models/formula_l/uninstall",
    summary="卸载 PP-FormulaNet·L（丢引擎缓存再删本档两件权重，老师点击＋确认发起）",
    dependencies=[Depends(require_write_token)],
)
def formula_l_uninstall() -> dict[str, Any]:
    try:
        return formula_setup.uninstall("l")
    except formula_setup.FormulaSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _catalog_plugin(plugin_id: str) -> None:
    """代笔资格：已安装、启用且声明 models.catalog；不合格一律 403。"""
    from app.core.plugins.registry import discover_plugins

    for info in discover_plugins().get("plugins", []):
        if info["id"] != plugin_id:
            continue
        if registry.CATALOG_CAPABILITY not in (info.get("capabilities") or []):
            raise HTTPException(
                status_code=403,
                detail="插件未声明 models.catalog 能力，没有模型目录就没有勾选语义")
        if not info.get("enabled"):
            raise HTTPException(status_code=403, detail="插件已停用，不能改模型配置")
        return
    raise HTTPException(status_code=403, detail="插件未安装，不能代笔模型配置")


@router.post(
    "/api/models/prefs",
    summary="启用/停用＋默认选择（代笔进请求插件自身目录，不落 data/）",
    dependencies=[Depends(require_write_token)],
)
def models_prefs(payload: dict[str, Any] = Body(...),
                 plugin_id: str = Query("")) -> dict[str, Any]:
    _catalog_plugin(plugin_id)
    try:
        return model_prefs.save(
            payload, [item["id"] for item in registry.catalog(plugin_id)], plugin_id)
    except model_prefs.PrefsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc