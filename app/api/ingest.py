"""拖入文件的入库通道：把老师拖进来的文件变成中转站里的一批待审题。

写通道与中转站同权：必须带一次性写令牌（AGENTS §5）。
插件走宿主转发（``ingest.files``），宿主自己拖进来的文件走这条 HTTP 口子，
两条路最终落进同一个 ``pending_bank``，口径只有一处。

**两段式**：响应先把批次立起来（Word / 文本类放一条「正在解析」占位题，
PDF 只立空批次），识别、页图渲染与 OCR 在响应之后的后台任务里跑完。
老师粘贴一张截图不必盯着屏幕等模型转写。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException

from app.core import ingest, pending_bank, questions
from app.core.layout import layout_router
from app.core.recognize import recognize_router
from app.core.security import require_write_token

router = APIRouter(tags=["ingest"])


@router.post(
    "/api/ingest/files",
    status_code=201,
    summary="拖入的文件 → 中转站新批次",
    dependencies=[Depends(require_write_token)],
)
async def ingest_files(background: BackgroundTasks,
                       payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体形如 ``{"files": [...], "layout_engine": "auto", "recognize_engine": "auto"}``。

    ``layout_engine`` 取 ``auto`` / ``yolo`` / ``cloud``，``recognize_engine``
    取 ``auto`` / ``full_ocr`` / ``mineru``；老插件仍可只发 ``channel``，
    后端会映射到新的识别引擎。后端按**后缀**分拣：文本类与 Word 走轻量解析，
    PDF 一律渲染成原卷大图，图片走识别引擎。``.zip`` 静默忽略。

    **一个文件一个批次**：拖 9 份卷子就立 9 个批次（B-002、B-003……），
    各认各的、各解析各的；``batch_id`` 回第一份的批次号，``batch_ids`` / ``batches``
    回完整清单，单文件时与旧口径完全一致。

    认不出的文件不会凭空生成题目：留一条明写「待识别」的占位题，
    图也挂在那儿，等老师自己补。返回体里的 ``warnings`` 是这些如实说明。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise HTTPException(status_code=400, detail="缺少 files 数组")
    try:
        layout_engine = layout_router.normalize_engine(payload.get("layout_engine"))
        recognize_engine = payload.get("recognize_engine")
        if not recognize_engine and payload.get("channel"):
            recognize_engine = recognize_router.from_legacy_channel(payload.get("channel"))
        recognize_engine = recognize_router.normalize_engine(recognize_engine)
        staged = ingest.stage_ingest(files, layout_engine=layout_engine,
                                     recognize_engine=recognize_engine)
        job_groups = staged.pop("jobs", [])
        # 一个文件一个批次：每批各排各的后台解析，互不拖累。
        for group in job_groups:
            background.add_task(ingest.run_ingest_jobs, group["batch_id"],
                                group["jobs"], group["layout_engine"],
                                group["recognize_engine"])
        staged["parsing"] = bool(job_groups)
        return staged
    except ingest.IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except questions.QuestionValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": "题目不符合 Schema", "errors": exc.errors}
        ) from exc
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
