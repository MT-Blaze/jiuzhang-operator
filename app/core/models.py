"""Pydantic 响应模型：题目单题与分页列表。

这些模型用于 FastAPI 路由的 ``response_model``，确保返回结构稳定、类型安全。
注意：模型字段必须与 ``app.core.questions._row_to_document`` 返回结构一致。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Question(BaseModel):
    """单题完整结构（与 _row_to_document 输出一致）。"""

    id: str = Field(..., description="题目唯一 ID")
    schema_version: str = Field(..., description="Schema 版本")
    type: str = Field(..., description="题型 single_choice/multiple_choice/fill_blank/solution/proof/unknown")
    stem: str = Field(..., description="题干 Markdown + LaTeX")
    difficulty: str = Field(..., description="难度 basic/medium/hard/novel")
    options: dict[str, str] | None = Field(None, description="选择题选项 A/B/C/D")
    answer: dict[str, Any] | None = Field(None, description="答案结构")
    solution: str | None = Field(None, description="解析")
    tags: list[str] | None = Field(None, description="标签列表")
    taxonomy: dict[str, str] | None = Field(None, description="分类树")
    source: dict[str, Any] | None = Field(None, description="来源信息")
    images: list[str] | None = Field(None, description="图片路径列表")
    extensions: dict[str, Any] | None = Field(None, description="扩展字段")
    meta: dict[str, Any] = Field(..., description="元数据（created_at/updated_at/revision/status/author）")


class QuestionPage(BaseModel):
    """分页响应结构。"""

    items: list[Question] = Field(..., description="当前页题目列表")
    total: int = Field(..., ge=0, description="总题数")
    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, le=100, description="每页大小")
    total_pages: int = Field(..., ge=1, description="总页数")
