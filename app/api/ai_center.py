"""AI 配置中心端点：密钥池、四任务指派、模型列表。

读接口只回掩码；写接口与出网（拉模型）一律要 ``X-JZO-Token``。
密钥只落当前工作区 ``.env`` 与 ``os.environ``，响应里永不出现原文。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.core import ai_center, ai_recognize
from app.core.security import require_write_token

router = APIRouter(prefix="/api/ai-center", tags=["ai-center"])


class AccountSaveRequest(BaseModel):
    id: str | None = Field(default=None, max_length=64, description="修改时带上账号 id")
    name: str = Field(..., min_length=1, max_length=ai_center.NAME_MAX)
    base_url: str = Field(..., min_length=1, max_length=512)
    api_key: str | None = Field(
        default=None,
        max_length=ai_center.KEY_MAX,
        description="留空表示保留旧 Key；传空串表示清掉 Key",
    )


class AssignRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=16)
    account_id: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=ai_center.MODEL_MAX)


class ModelsRequest(BaseModel):
    account_id: str = Field(default="", max_length=64, description="已保存账号")
    base_url: str = Field(default="", max_length=512, description="未保存账号的临时地址")
    api_key: str = Field(default="", max_length=ai_center.KEY_MAX, description="未保存账号的临时 Key，不落盘")


class RecognizeRequest(BaseModel):
    images: list[str] = Field(default_factory=list, max_length=3)
    context: dict[str, Any] = Field(default_factory=dict)
    task: str = Field(default="ocr", max_length=16)


@router.get("", summary="读取密钥池（掩码）与任务指派")
def read_cluster() -> dict:
    return ai_center.cluster()


@router.post(
    "/accounts",
    summary="新增或修改账号（Key 只写本机 .env）",
    dependencies=[Depends(require_write_token)],
)
def save_account(body: AccountSaveRequest = Body(...)) -> dict:
    try:
        return ai_center.save_account(
            account_id=body.id, name=body.name, base_url=body.base_url, api_key=body.api_key
        )
    except ai_center.AiCenterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/accounts/{account_id}",
    summary="删除账号，并清掉它的指派与 .env 密钥",
    dependencies=[Depends(require_write_token)],
)
def delete_account(account_id: str) -> dict:
    try:
        return ai_center.delete_account(account_id)
    except ai_center.AiCenterError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/assign",
    summary="把某任务指派到某账号的某模型",
    dependencies=[Depends(require_write_token)],
)
def assign_task(body: AssignRequest = Body(...)) -> dict:
    try:
        return ai_center.assign_task(body.task, body.account_id, body.model)
    except ai_center.AiCenterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/models",
    summary="拉取某账号的模型列表（用户点击触发的外部请求）",
    dependencies=[Depends(require_write_token)],
)
async def fetch_models(body: ModelsRequest = Body(...)) -> dict:
    try:
        return await run_in_threadpool(
            ai_center.fetch_models,
            account_id=body.account_id,
            base_url=body.base_url,
            api_key=body.api_key,
        )
    except ai_center.AiCenterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/recognize",
    summary="单题 AI 识别：只回结构化正文 + 底座套好的 exam-zh 源码",
    dependencies=[Depends(require_write_token)],
)
async def recognize(body: RecognizeRequest = Body(...)) -> dict:
    return await ai_recognize.recognize(body.images, body.context, body.task)
