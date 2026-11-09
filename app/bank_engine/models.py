"""题库引擎 v2 的 Dataclass 对象映射：表行 → Python 对象，跨表拼装在应用层完成。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExamDirection:
    id: int
    name: str
    code: str
    sort_order: int
    subject_id: int
    grade_id: int | None
    chapter_id: int | None
    description: str | None
    question_count: int = 0


@dataclass(frozen=True)
class KnowledgePoint:
    id: int
    name: str
    code: str
    sort_order: int
    subject_id: int
    grade_id: int | None
    parent_id: int | None
    question_count: int = 0


@dataclass(frozen=True)
class KnowledgeNode:
    point: KnowledgePoint
    children: tuple["KnowledgeNode", ...] = ()


@dataclass(frozen=True)
class Textbook:
    id: int
    name: str
    code: str
    sort_order: int
    publisher: str | None
    subject_id: int
    grade_id: int | None


@dataclass(frozen=True)
class Chapter:
    id: int
    name: str
    code: str
    sort_order: int
    textbook_id: int
    parent_id: int | None


@dataclass(frozen=True)
class QuestionOption:
    id: int
    label: str
    content: str
    is_correct: bool


@dataclass(frozen=True)
class QuestionAnswer:
    content: str
    is_primary: bool
    sort_order: int


@dataclass(frozen=True)
class QuestionSolution:
    content: str
    is_primary: bool
    sort_order: int


@dataclass(frozen=True)
class QuestionImage:
    belongs_to: str
    path: str
    alt: str | None
    sort_order: int
    option_id: int | None


@dataclass(frozen=True)
class QuestionSupplement:
    namespace: str
    field_key: str
    field_value: str
    sort_order: int


@dataclass(frozen=True)
class QuestionSource:
    id: int
    name: str
    code: str
    exam_type: str
    year: int | None
    region: str | None
    question_no: str | None
    score: float
    grade_id: int | None
    chapter_id: int | None
    school_id: int | None
    school_name: str | None = None


@dataclass(frozen=True)
class QuestionSummary:
    id: str
    stem: str
    subject_id: int
    question_type: str
    difficulty: str
    quality: str
    deleted_at: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class QuestionRecord:
    id: str
    stem: str
    subject_id: int
    question_type: str
    difficulty: str
    quality: str
    deleted_at: str | None
    created_at: str
    updated_at: str
    options: tuple[QuestionOption, ...] = ()
    answers: tuple[QuestionAnswer, ...] = ()
    solutions: tuple[QuestionSolution, ...] = ()
    remarks: tuple[str, ...] = ()
    supplements: tuple[QuestionSupplement, ...] = ()
    images: tuple[QuestionImage, ...] = ()
    sources: tuple[QuestionSource, ...] = ()
    exam_directions: tuple[ExamDirection, ...] = ()
    knowledge_points: tuple[KnowledgePoint, ...] = ()


@dataclass(frozen=True)
class QuestionPage:
    items: tuple[QuestionSummary, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class BuildReport:
    db_path: str
    created: bool
    counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class EngineStatus:
    db_path: str
    schema_version: int
    integrity: str
    foreign_key_violations: int
    table_count: int
    counts: dict[str, int] = field(default_factory=dict)
