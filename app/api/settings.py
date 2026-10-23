"""系统设置类端点：目前只有「启动行为」（打开软件先落在哪个界面）。

读写分开是刻意的：GET 供工作台启动路径调用，落在启动链上，绝不带写令牌、
绝不抛错；POST 是老师在设置页当场点【保存】，带本机写令牌，目标不合格
（形状非法 / 插件没装 / 已停用）直接 400，不落一个下次启动会静默回退的配置。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.startup_prefs import StartupRejected, resolve, set_target
from app.core.security import require_write_token

router = APIRouter(tags=["system"])


@router.get("/api/startup", summary="读取启动行为（含失效回退原因与候选插件清单）")
async def read_startup() -> dict[str, Any]:
    return resolve()


@router.post(
    "/api/startup",
    summary="保存启动行为（老师当场点保存才落盘）",
    dependencies=[Depends(require_write_token)],
)
def write_startup(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """同步函数不是省事：校验要扫 ``plugins/`` 目录、落盘要写文件，都是阻塞 IO，
    FastAPI 会把它放进线程池执行（与 ``/api/plugins/index`` 同款口径）。"""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    try:
        set_target(payload.get("target"))
    except StartupRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return resolve()
