"""拖入文件的入库通道：把老师拖进来的文件变成中转站里的一批待审题。

写通道与中转站同权：必须带一次性写令牌（AGENTS §5）。
插件走宿主转发（``ingest.files``），宿主自己拖进来的文件走这条 HTTP 口子，
两条路最终落进同一个 ``pending_bank``，口径只有一处。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core import ingest, pending_bank, questions
from app.core.security import require_write_token

router = APIRouter(tags=["ingest"])


@router.post(
    "/api/ingest/files",
    status_code=201,
    summary="拖入的文件 → 中转站新批次",
    dependencies=[Depends(require_write_token)],
)
async def ingest_files(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体形如 ``{"files": [{"name": "卷子.pdf", "data_url": "data:...;base64,..."}]}``。

    后端按**后缀**分拣：文本类走轻量解析，PDF 尽力抽文本层，图片走 OCR。
    ``.zip`` 静默忽略（插件安装包走另一条道）。

    认不出的文件不会凭空生成题目：留一条明写「待识别」的占位题，
    图也挂在那儿，等老师自己补。返回体里的 ``warnings`` 是这些如实说明。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise HTTPException(status_code=400, detail="缺少 files 数组")
    try:
        return await ingest.ingest_files(files)
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
