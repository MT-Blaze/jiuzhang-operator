"""题目交换契约：dataclass 是唯一事实来源。

题目在底座、插件、导入导出之间流转的标准结构由本模块的 dataclass 定义，
校验逻辑与字段定义同住一处——不再读任何 Schema 文件，也不会出现「文档说 A、
代码校验 B」的两本账。文本字段统一 Markdown + LaTeX：行内 $...$，独立公式 $$...$$。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.core.contract import CONTRACT_VERSION, DIFFICULTY_LEVELS

QUESTION_TYPES = ("single_choice", "multiple_choice", "fill_blank", "solution", "proof", "unknown")
STATUSES = ("draft", "published", "archived")
ANSWER_KINDS = ("choice", "text", "expression", "proof", "unknown")
IMAGE_ROLES = ("stem", "option", "solution")

_ID_RE = re.compile(r"^q_[A-Za-z0-9_-]{8,64}$")
_OPTION_KEY_RE = re.compile(r"^[A-H]$")
_IMAGE_ID_RE = re.compile(r"^img_[A-Za-z0-9_-]{1,63}$")
_URI_RE = re.compile(r"^(asset://img_[A-Za-z0-9_-]+|/static/uploads/[^\s]+)$")
_SCHOOL_ID_RE = re.compile(r"^sch_[A-Za-z0-9_-]{4,40}$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_EXTENSION_KEY_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")

_MAX_ERRORS = 20


class ContractError(ValueError):
    """题目不符合契约；``errors`` 是逐条可读原因。"""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("题目不符合契约")


def _text(value: Any, path: str, errors: list[str], *, minimum: int = 0,
          maximum: int | None = None, pattern: re.Pattern[str] | None = None) -> str | None:
    if not isinstance(value, str):
        errors.append(f"{path}: 必须是字符串")
        return None
    if len(value) < minimum:
        errors.append(f"{path}: 至少 {minimum} 个字符")
    if maximum is not None and len(value) > maximum:
        errors.append(f"{path}: 最多 {maximum} 个字符")
    if pattern is not None and not pattern.match(value):
        errors.append(f"{path}: 格式不合法（{value!r}）")
    return value


def _integer(value: Any, path: str, errors: list[str], *, minimum: int | None = None,
             maximum: int | None = None) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{path}: 必须是整数")
        return None
    if minimum is not None and value < minimum:
        errors.append(f"{path}: 不得小于 {minimum}")
    if maximum is not None and value > maximum:
        errors.append(f"{path}: 不得大于 {maximum}")
    return value


def _enum(value: Any, path: str, errors: list[str], allowed: tuple[str, ...]) -> str | None:
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{path}: 取值必须是 {'/'.join(allowed)} 之一")
        return None
    return value


def _sequence(value: Any, path: str, errors: list[str], *, minimum: int | None = None,
              maximum: int | None = None) -> list[Any] | None:
    if not isinstance(value, list):
        errors.append(f"{path}: 必须是数组")
        return None
    if minimum is not None and len(value) < minimum:
        errors.append(f"{path}: 至少 {minimum} 项")
    if maximum is not None and len(value) > maximum:
        errors.append(f"{path}: 最多 {maximum} 项")
    return value


def _mapping(value: Any, path: str, errors: list[str], allowed: set[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{path}: 必须是对象")
        return None
    for key in value:
        if key not in allowed:
            errors.append(f"{path}.{key}: 不允许的字段")
    return value


def _unique(values: list[Any], path: str, errors: list[str]) -> None:
    seen: list[Any] = []
    for item in values:
        if item in seen:
            errors.append(f"{path}: 存在重复值 {item!r}")
            return
        seen.append(item)


def _present(mapping: dict[str, Any], path: str, required: tuple[str, ...],
             errors: list[str]) -> None:
    for key in required:
        if key not in mapping:
            errors.append(f"{path}.{key}: 必填字段缺失")


@dataclass(frozen=True)
class ImageLayout:
    align: str = "center"
    size: str = "auto"
    @classmethod
    def from_document(cls, data: Any, path: str, errors: list[str]) -> ImageLayout:
        mapping = _mapping(data, path, errors, {"align", "size"}) or {}
        align = _enum(mapping.get("align", "center"), f"{path}.align", errors,
                      ("inline", "left", "center", "right")) or "center"
        size = _enum(mapping.get("size", "auto"), f"{path}.size", errors,
                     ("auto", "small", "medium", "large")) or "auto"
        return cls(align=align, size=size)
    def as_document(self) -> dict[str, Any]:
        return {"align": self.align, "size": self.size}


@dataclass(frozen=True)
class Image:
    id: str
    role: str
    uri: str
    option_key: str | None = None
    alt: str | None = None
    sha256: str | None = None
    layout: ImageLayout | None = None
    @classmethod
    def from_document(cls, data: Any, path: str, errors: list[str]) -> Image:
        allowed = {"id", "role", "option_key", "uri", "alt", "sha256", "layout"}
        mapping = _mapping(data, path, errors, allowed) or {}
        _present(mapping, path, ("id", "role", "uri"), errors)
        image_id = _text(mapping.get("id"), f"{path}.id", errors, pattern=_IMAGE_ID_RE) or ""
        role = _enum(mapping.get("role"), f"{path}.role", errors, IMAGE_ROLES) or "stem"
        uri = _text(mapping.get("uri"), f"{path}.uri", errors, pattern=_URI_RE) or ""
        option_key = None
        if "option_key" in mapping:
            option_key = _text(mapping["option_key"], f"{path}.option_key", errors,
                               pattern=_OPTION_KEY_RE)
        if role == "option" and option_key is None:
            errors.append(f"{path}.option_key: role=option 时必须提供选项标号")
        alt = None
        if "alt" in mapping:
            alt = _text(mapping["alt"], f"{path}.alt", errors, maximum=200)
        sha256 = None
        if "sha256" in mapping:
            sha256 = _text(mapping["sha256"], f"{path}.sha256", errors, pattern=_SHA256_RE)
        layout = None
        if "layout" in mapping:
            layout = ImageLayout.from_document(mapping["layout"], f"{path}.layout", errors)
        return cls(image_id, role, uri, option_key, alt, sha256, layout)
    def as_document(self) -> dict[str, Any]:
        document = {"id": self.id, "role": self.role, "uri": self.uri}
        for key in ("option_key", "alt", "sha256"):
            value = getattr(self, key)
            if value is not None:
                document[key] = value
        if self.layout is not None:
            document["layout"] = self.layout.as_document()
        return document


@dataclass(frozen=True)
class QuestionOption:
    key: str
    content: str
    image_ids: tuple[str, ...] | None = None
    @classmethod
    def from_document(cls, data: Any, path: str, errors: list[str]) -> QuestionOption:
        mapping = _mapping(data, path, errors, {"key", "content", "image_ids"}) or {}
        _present(mapping, path, ("key", "content"), errors)
        key = _text(mapping.get("key"), f"{path}.key", errors, pattern=_OPTION_KEY_RE) or ""
        content = _text(mapping.get("content"), f"{path}.content", errors, maximum=5000) or ""
        image_ids = None
        if "image_ids" in mapping:
            items = _sequence(mapping["image_ids"], f"{path}.image_ids", errors, maximum=4)
            if items is not None:
                for index, item in enumerate(items):
                    _text(item, f"{path}.image_ids[{index}]", errors, pattern=_IMAGE_ID_RE)
                _unique(items, f"{path}.image_ids", errors)
                image_ids = tuple(items)
        return cls(key, content, image_ids)
    def as_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {"key": self.key, "content": self.content}
        if self.image_ids is not None:
            document["image_ids"] = list(self.image_ids)
        return document


@dataclass(frozen=True)
class Answer:
    kind: str
    choice_keys: tuple[str, ...] | None = None
    content: str | None = None
    final: str | None = None
    @classmethod
    def from_document(cls, data: Any, path: str, errors: list[str]) -> Answer:
        mapping = _mapping(data, path, errors, {"kind", "choice_keys", "content", "final"}) or {}
        _present(mapping, path, ("kind",), errors)
        kind = _enum(mapping.get("kind"), f"{path}.kind", errors, ANSWER_KINDS) or "unknown"
        choice_keys = None
        if "choice_keys" in mapping:
            items = _sequence(mapping["choice_keys"], f"{path}.choice_keys", errors,
                              minimum=1, maximum=8)
            if items is not None:
                for index, item in enumerate(items):
                    _text(item, f"{path}.choice_keys[{index}]", errors, pattern=_OPTION_KEY_RE)
                _unique(items, f"{path}.choice_keys", errors)
                choice_keys = tuple(items)
        content = None
        if "content" in mapping:
            content = _text(mapping["content"], f"{path}.content", errors, maximum=20000)
        final = None
        if "final" in mapping:
            final = _text(mapping["final"], f"{path}.final", errors, maximum=2000)
        if kind == "choice" and choice_keys is None:
            errors.append(f"{path}.choice_keys: kind=choice 时必填")
        if kind in ("text", "expression", "proof") and content is None:
            errors.append(f"{path}.content: kind={kind} 时必填")
        return cls(kind, choice_keys, content, final)
    def as_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {"kind": self.kind}
        if self.choice_keys is not None:
            document["choice_keys"] = list(self.choice_keys)
        for key in ("content", "final"):
            value = getattr(self, key)
            if value is not None:
                document[key] = value
        return document


@dataclass(frozen=True)
class Taxonomy:
    textbook: str | None = None
    chapter: str | None = None
    section: str | None = None
    topic: str | None = None
    topic_ids: tuple[str, ...] | None = None
    @classmethod
    def from_document(cls, data: Any, path: str, errors: list[str]) -> Taxonomy:
        allowed = {"textbook", "chapter", "section", "topic", "topic_ids"}
        mapping = _mapping(data, path, errors, allowed) or {}
        values = {
            key: _text(mapping[key], f"{path}.{key}", errors, minimum=1, maximum=64)
            if key in mapping else None
            for key in ("textbook", "chapter", "section", "topic")
        }
        topic_ids = None
        if "topic_ids" in mapping:
            items = _sequence(mapping["topic_ids"], f"{path}.topic_ids", errors, maximum=8)
            if items is not None:
                for index, item in enumerate(items):
                    _text(item, f"{path}.topic_ids[{index}]", errors, minimum=1, maximum=64)
                _unique(items, f"{path}.topic_ids", errors)
                topic_ids = tuple(items)
        return cls(topic_ids=topic_ids, **values)
    def as_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {}
        for key in ("textbook", "chapter", "section", "topic"):
            value = getattr(self, key)
            if value is not None:
                document[key] = value
        if self.topic_ids is not None:
            document["topic_ids"] = list(self.topic_ids)
        return document


@dataclass(frozen=True)
class Source:
    year: int | None = None
    region: str | None = None
    body: str | None = None
    school: str | None = None
    school_id: str | None = None
    school_ids: tuple[str, ...] | None = None
    scene_type: str | None = None
    exam_type: str | None = None
    paper_title: str | None = None
    question_no: str | None = None
    @classmethod
    def from_document(cls, data: Any, path: str, errors: list[str]) -> Source:
        allowed = {"year", "region", "body", "school", "school_id", "school_ids",
                   "scene_type", "exam_type", "paper_title", "question_no"}
        mapping = _mapping(data, path, errors, allowed) or {}
        year = None
        if "year" in mapping:
            year = _integer(mapping["year"], f"{path}.year", errors, minimum=1900, maximum=2100)
        text_fields: dict[str, str | None] = {}
        limits = {"region": 64, "body": 64, "school": 64, "scene_type": 64,
                  "exam_type": 64, "paper_title": 120, "question_no": 32}
        for key, limit in limits.items():
            text_fields[key] = (_text(mapping[key], f"{path}.{key}", errors, maximum=limit)
                                if key in mapping else None)
        school_id = (_text(mapping["school_id"], f"{path}.school_id", errors,
                           pattern=_SCHOOL_ID_RE) if "school_id" in mapping else None)
        school_ids = None
        if "school_ids" in mapping:
            items = _sequence(mapping["school_ids"], f"{path}.school_ids", errors, maximum=24)
            if items is not None:
                for index, item in enumerate(items):
                    _text(item, f"{path}.school_ids[{index}]", errors, pattern=_SCHOOL_ID_RE)
                _unique(items, f"{path}.school_ids", errors)
                school_ids = tuple(items)
        return cls(year=year, school_id=school_id, school_ids=school_ids, **text_fields)
    def as_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {}
        for key in ("year", "region", "body", "school", "school_id", "scene_type",
                    "exam_type", "paper_title", "question_no"):
            value = getattr(self, key)
            if value is not None:
                document[key] = value
        if self.school_ids is not None:
            document["school_ids"] = list(self.school_ids)
        return document


@dataclass(frozen=True)
class Meta:
    created_at: str
    updated_at: str
    revision: int
    status: str
    author: str | None = None
    @classmethod
    def from_document(cls, data: Any, path: str, errors: list[str]) -> Meta:
        mapping = _mapping(data, path, errors,
                           {"created_at", "updated_at", "revision", "status", "author"}) or {}
        _present(mapping, path, ("created_at", "updated_at", "revision", "status"), errors)
        created_at = _text(mapping.get("created_at"), f"{path}.created_at", errors) or ""
        updated_at = _text(mapping.get("updated_at"), f"{path}.updated_at", errors) or ""
        revision = _integer(mapping.get("revision"), f"{path}.revision", errors, minimum=1) or 1
        status = _enum(mapping.get("status"), f"{path}.status", errors, STATUSES) or "draft"
        author = (_text(mapping["author"], f"{path}.author", errors, maximum=64)
                  if "author" in mapping else None)
        return cls(created_at, updated_at, revision, status, author)
    def as_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "revision": self.revision,
            "status": self.status,
        }
        if self.author is not None:
            document["author"] = self.author
        return document


@dataclass(frozen=True)
class Question:
    schema_version: str
    id: str
    type: str
    stem: str
    difficulty: str
    meta: Meta
    options: tuple[QuestionOption, ...] | None = None
    answer: Answer | None = None
    solution: str | None = None
    grade: str | None = None
    tags: tuple[str, ...] | None = None
    taxonomy: Taxonomy | None = None
    source: Source | None = None
    images: tuple[Image, ...] | None = None
    extensions: dict[str, Any] = field(default_factory=dict)
    @classmethod
    def from_document(cls, data: Any, path: str = "(root)",
                      errors: list[str] | None = None) -> Question:
        caught: list[str] = [] if errors is None else errors
        allowed = {"schema_version", "id", "type", "stem", "options", "answer", "solution",
                   "grade", "difficulty", "tags", "taxonomy", "source", "images",
                   "extensions", "meta"}
        mapping = _mapping(data, path, caught, allowed) or {}
        _present(mapping, path, ("schema_version", "id", "type", "stem", "difficulty", "meta"),
                 caught)
        version = _text(mapping.get("schema_version"), f"{path}.schema_version", caught)
        if version is not None and version != CONTRACT_VERSION:
            caught.append(f"{path}.schema_version: 必须是 {CONTRACT_VERSION}")
        question_id = _text(mapping.get("id"), f"{path}.id", caught, pattern=_ID_RE) or ""
        qtype = _enum(mapping.get("type"), f"{path}.type", caught, QUESTION_TYPES) or "unknown"
        stem = _text(mapping.get("stem"), f"{path}.stem", caught,
                     minimum=1, maximum=50000) or ""
        difficulty = _enum(mapping.get("difficulty"), f"{path}.difficulty", caught,
                           DIFFICULTY_LEVELS) or "L1"
        grade = (_text(mapping["grade"], f"{path}.grade", caught, maximum=20)
                 if "grade" in mapping else None)
        solution = (_text(mapping["solution"], f"{path}.solution", caught, minimum=1,
                          maximum=50000) if "solution" in mapping else None)

        options = None
        if "options" in mapping:
            items = _sequence(mapping["options"], f"{path}.options", caught,
                              minimum=2, maximum=12)
            if items is not None:
                options = tuple(QuestionOption.from_document(item, f"{path}.options[{index}]", caught)
                                for index, item in enumerate(items))
        if qtype in ("single_choice", "multiple_choice") and options is None:
            caught.append(f"{path}.options: 选择题必须提供选项")

        answer = (Answer.from_document(mapping["answer"], f"{path}.answer", caught)
                  if "answer" in mapping else None)
        if answer is not None:
            if qtype == "single_choice":
                if answer.kind != "choice":
                    caught.append(f"{path}.answer.kind: 单选题答案必须是 choice")
                if answer.choice_keys is not None and len(answer.choice_keys) != 1:
                    caught.append(f"{path}.answer.choice_keys: 单选题必须恰好 1 项")
            elif qtype == "multiple_choice":
                if answer.kind != "choice":
                    caught.append(f"{path}.answer.kind: 多选题答案必须是 choice")
                if answer.choice_keys is not None and not 2 <= len(answer.choice_keys) <= 8:
                    caught.append(f"{path}.answer.choice_keys: 多选题需 2–8 项")
            elif qtype == "fill_blank" and answer.kind not in ("text", "expression"):
                caught.append(f"{path}.answer.kind: 填空题答案只收 text/expression")
            elif qtype in ("solution", "proof") and answer.kind not in (
                    "text", "expression", "proof"):
                caught.append(f"{path}.answer.kind: 解答/证明题答案只收 text/expression/proof")

        tags = None
        if "tags" in mapping:
            items = _sequence(mapping["tags"], f"{path}.tags", caught, maximum=32)
            if items is not None:
                for index, item in enumerate(items):
                    _text(item, f"{path}.tags[{index}]", caught, minimum=1, maximum=32)
                _unique(items, f"{path}.tags", caught)
                tags = tuple(items)

        taxonomy = (Taxonomy.from_document(mapping["taxonomy"], f"{path}.taxonomy", caught)
                    if "taxonomy" in mapping else None)
        source = (Source.from_document(mapping["source"], f"{path}.source", caught)
                  if "source" in mapping else None)
        images = None
        if "images" in mapping:
            items = _sequence(mapping["images"], f"{path}.images", caught, maximum=32)
            if items is not None:
                images = tuple(Image.from_document(item, f"{path}.images[{index}]", caught)
                               for index, item in enumerate(items))

        extensions: dict[str, Any] = {}
        if "extensions" in mapping:
            raw = mapping["extensions"]
            extension_map = (_mapping(raw, f"{path}.extensions", caught, set(raw))
                             if isinstance(raw, dict) else None)
            if not isinstance(raw, dict):
                caught.append(f"{path}.extensions: 必须是对象")
            if extension_map is not None:
                if len(extension_map) > 32:
                    caught.append(f"{path}.extensions: 最多 32 个键")
                for key in extension_map:
                    if not _EXTENSION_KEY_RE.match(key):
                        caught.append(f"{path}.extensions.{key}: 键必须是反向域名前缀")
                extensions = dict(extension_map)

        meta = (Meta.from_document(mapping["meta"], f"{path}.meta", caught)
                if "meta" in mapping else Meta("", "", 1, "draft"))

        if len(caught) > _MAX_ERRORS:
            del caught[_MAX_ERRORS:]
        if errors is None and caught:
            raise ContractError(caught)
        return cls(version or CONTRACT_VERSION, question_id, qtype, stem, difficulty, meta,
                   options, answer, solution, grade, tags, taxonomy, source, images, extensions)
    def as_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema_version": self.schema_version,
            "id": self.id,
            "type": self.type,
            "stem": self.stem,
            "difficulty": self.difficulty,
            "meta": self.meta.as_document(),
        }
        if self.options is not None:
            document["options"] = [item.as_document() for item in self.options]
        for key in ("answer", "solution", "grade", "taxonomy", "source"):
            value = getattr(self, key)
            if value is not None:
                document[key] = value.as_document() if hasattr(value, "as_document") else value
        if self.tags is not None:
            document["tags"] = list(self.tags)
        if self.images is not None:
            document["images"] = [item.as_document() for item in self.images]
        if self.extensions:
            document["extensions"] = dict(self.extensions)
        return document


def validate(document: Any) -> Question:
    """按契约校验并返回 dataclass；不合契约抛 ``ContractError``。"""
    errors: list[str] = []
    question = Question.from_document(document, errors=errors)
    if errors:
        raise ContractError(errors)
    return question
