"""审核入库的错误映射：状态码与 ``detail`` 的形状只在这里定一次。"""

from __future__ import annotations

from fastapi import HTTPException

from app.bank_engine.writer import EntryRejected
from app.core.pending import service
from app.core.bank import questions
from app.core.bank import service as bank


def approve_error(exc: Exception) -> HTTPException:
    """把入库链路上的各类异常翻成 HTTP 错误；调用方负责 ``raise ... from exc``。"""
    if isinstance(exc, EntryRejected):
        return HTTPException(
            status_code=422,
            detail={"code": "entry_rejected", "message": str(exc), "errors": exc.errors},
        )
    if isinstance(exc, service.PendingDuplicateAnswer):
        return HTTPException(
            status_code=409,
            detail={"message": str(exc), "existing_id": exc.existing_id, "duplicate": True,
                    "answer_mismatch": True, "code": "duplicate_answer_mismatch",
                    "existing_answer": exc.existing_answer,
                    "incoming_answer": exc.incoming_answer},
        )
    if isinstance(exc, service.PendingDuplicate):
        return HTTPException(
            status_code=409,
            detail={"message": str(exc), "existing_id": exc.existing_id, "duplicate": True},
        )
    if isinstance(exc, service.PendingNotFound) or isinstance(exc, bank.BankNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, questions.QuestionValidationError):
        return HTTPException(
            status_code=422, detail={"message": "题目不符合 Schema", "errors": exc.errors}
        )
    if isinstance(exc, service.PendingConflict):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, bank.BankError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, service.PendingError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="入库失败")


__all__ = ["approve_error"]
