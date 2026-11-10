"""录题表单 → ``NewQuestion``：把老师填的名字/编码解析成 35 表的外键。

只做解析与归一，不写库；任何解析不了的词都在这里收成 ``EntryRejected``，
由路由原样回 422。所有字典查询都是单表 SELECT，跨表关系留给 writer 分步落库。
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.bank_engine import dao_dictionary
from app.bank_engine.models import (
    NewExam,
    NewImage,
    NewOption,
    NewQuestion,
    NewSupplement,
)
from app.bank_engine.writer import EntryRejected, normalize_exam_type

_IMAGE_ROLES = {"stem": "stem", "option": "option", "solution": "solution", "answer": "answer"}


def _text(value: Any, limit: int) -> str:
    return str("" if value is None else value).strip()[:limit]


def _int_or_none(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number


def _float_or_zero(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if number >= 0 else 0.0


def _ids_of(values: Any) -> list[int | str]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        values = [values]
    return [item for item in values if isinstance(item, (int, str)) and str(item).strip()]


def _resolve_ids(
    conn: sqlite3.Connection, values: Any, lookup
) -> tuple[tuple[int, ...], tuple[str, ...]]:
    numeric: list[int] = []
    codes: list[str] = []
    for item in _ids_of(values):
        if isinstance(item, int) and not isinstance(item, bool):
            numeric.append(item)
        else:
            codes.append(str(item).strip())
    found_codes, missing = lookup(conn, codes)
    return tuple(dict.fromkeys([*numeric, *found_codes])), missing


def _option_rows(document: dict[str, Any]) -> tuple[NewOption, ...]:
    raw = document.get("options")
    if not isinstance(raw, list):
        return ()
    options: list[NewOption] = []
    for index, item in enumerate(raw[:8]):
        if not isinstance(item, dict):
            continue
        label = _text(item.get("key") or item.get("label"), 1).upper() or "ABCDEFGH"[index]
        content = _text(item.get("content") or item.get("text"), 20000)
        if content:
            options.append(NewOption(label, content, False))
    return tuple(options)


def _answer_text(document: dict[str, Any], is_choice: bool) -> tuple[str, list[str]]:
    answer = document.get("answer")
    letters: list[str] = []
    if isinstance(answer, dict):
        raw_letters = answer.get("choice_keys")
        if isinstance(raw_letters, list):
            letters = [_text(item, 1).upper() for item in raw_letters if _text(item, 1)]
        text = _text(answer.get("final") or answer.get("content"), 20000)
    else:
        text = _text(answer, 20000)
        letters = [letter for letter in text.upper() if letter in "ABCDEFGH"]
    if is_choice:
        letters = list(dict.fromkeys(letters))
        return "".join(letters), letters
    return text, []


def _mark_correct(options: tuple[NewOption, ...], letters: list[str]) -> tuple[NewOption, ...]:
    if not letters:
        return options
    return tuple(
        NewOption(option.label, option.content, option.label in letters) for option in options
    )


def _images(document: dict[str, Any]) -> tuple[NewImage, ...]:
    raw = document.get("images")
    if not isinstance(raw, list):
        return ()
    images: list[NewImage] = []
    for index, item in enumerate(raw[:32]):
        if not isinstance(item, dict):
            continue
        path = _text(item.get("uri") or item.get("path") or item.get("src"), 500)
        if not path:
            continue
        role = _IMAGE_ROLES.get(_text(item.get("role"), 16), "stem")
        images.append(
            NewImage(
                belongs_to=role,
                path=path,
                alt=_text(item.get("alt"), 200) or None,
                sort_order=index,
                option_label=_text(item.get("option_key"), 1).upper() or None,
            )
        )
    return tuple(images)


def _supplements(document: dict[str, Any]) -> tuple[NewSupplement, ...]:
    raw = document.get("supplements")
    items: list[NewSupplement] = []
    seen: set[tuple[str, str]] = set()

    def add(namespace: str, field_key: str, value: str) -> None:
        if not namespace or not value or (namespace, field_key) in seen:
            return
        seen.add((namespace, field_key))
        items.append(NewSupplement(namespace, field_key, value, len(items)))

    if isinstance(raw, list):
        for item in raw[:32]:
            if not isinstance(item, dict):
                continue
            add(
                _text(item.get("namespace"), 32),
                _text(item.get("field_key"), 32) or "正文",
                _text(item.get("field_value") or item.get("value"), 20000),
            )
    # 引擎没有标签表：录题端收集的交叉标签按命名空间落进补充表，一条一个。
    tags = document.get("tags")
    if isinstance(tags, str):
        tags = [tag for tag in tags.replace("，", ",").split(",") if tag.strip()]
    if isinstance(tags, list):
        for tag in tags[:32]:
            text = _text(tag, 32)
            add("标签", text, text)
    return tuple(items)


def _taxonomy_ids(document: dict[str, Any], key: str) -> Any:
    taxonomy = document.get("taxonomy")
    if not isinstance(taxonomy, dict):
        return None
    return taxonomy.get(key)


DEFAULT_EXAM_GRADE_ID = 12


def _school_ids(conn: sqlite3.Connection, raw: dict[str, Any]) -> tuple[int, ...]:
    values = raw.get("school_ids")
    if not isinstance(values, list):
        values = []
    primary = raw.get("school_id")
    if primary not in (None, ""):
        values = [primary, *values]
    ids: list[int] = []
    missing: list[str] = []
    for item in values[:24]:
        school_id = _int_or_none(item)
        if school_id is None:
            code = _text(item, 40)
            row = conn.execute(
                "SELECT id FROM dim_schools WHERE code = ?", (code,)
            ).fetchone()
            school_id = None if row is None else int(row[0])
            if school_id is None:
                missing.append(code)
                continue
        if school_id not in ids:
            ids.append(school_id)
    if missing:
        raise EntryRejected("学校编码不在字典里：" + "、".join(missing))
    return tuple(ids)


def _exam(
    conn: sqlite3.Connection,
    document: dict[str, Any],
    *,
    subject_id: int,
    grade_id: int | None,
) -> NewExam | None:
    raw = document.get("source")
    if not isinstance(raw, dict):
        return None
    exam_subject = _text(
        raw.get("exam_subject") or raw.get("body") or raw.get("paper_title") or raw.get("name"),
        120,
    )
    if not exam_subject:
        return None
    year = _int_or_none(raw.get("year"))
    if year is None or not 1900 <= year <= 2100:
        year = 1900
    month = _int_or_none(raw.get("month"))
    if month is not None and not 1 <= month <= 12:
        month = None
    return NewExam(
        year=year,
        month=month,
        subject_id=subject_id,
        grade_id=grade_id or DEFAULT_EXAM_GRADE_ID,
        exam_type=normalize_exam_type(raw.get("exam_type")),
        exam_subject=exam_subject,
        question_no=_text(raw.get("question_no"), 20) or None,
        score=_float_or_zero(raw.get("score")),
        school_ids=_school_ids(conn, raw),
    )


def prepare_question(conn: sqlite3.Connection, document: Any) -> NewQuestion:
    if not isinstance(document, dict):
        raise EntryRejected("题目必须是对象")
    dictionaries = dao_dictionary.load_dictionaries(conn)

    subject = dao_dictionary.resolve_subject(
        dictionaries,
        subject_id=_int_or_none(document.get("subject_id")),
        name=_text(document.get("subject"), 40),
        # 录题端目前只做数学：表单没带学科时默认收进数学，不把题写进空学科。
        code=_text(document.get("subject_code"), 32) or "mathematics",
    )
    if subject is None:
        raise EntryRejected("学科不在字典里：请从下拉候选里选")
    grade = dao_dictionary.resolve_grade(
        dictionaries,
        grade_id=_int_or_none(document.get("grade_id")),
        name=_text(document.get("grade"), 20),
        code=_text(document.get("grade_code"), 16),
    )
    question_type = dao_dictionary.resolve_question_type(
        dictionaries, _text(document.get("type"), 32)
    )
    if question_type is None:
        raise EntryRejected("题型不在字典里")
    difficulty = dao_dictionary.resolve_difficulty(
        dictionaries, _text(document.get("difficulty"), 8)
    )
    if difficulty is None:
        raise EntryRejected("难度不在字典里（L1–L5）")
    quality = dao_dictionary.resolve_quality(dictionaries, _text(document.get("quality"), 16))
    if quality is None:
        raise EntryRejected("质量分档不在字典里")

    is_choice = question_type.code == "choice"
    options = _option_rows(document)
    answer_text, letters = _answer_text(document, is_choice)
    options = _mark_correct(options, letters)

    direction_ids, missing_directions = _resolve_ids(
        conn,
        document.get("exam_direction_ids") or _taxonomy_ids(document, "topic_ids"),
        dao_dictionary.direction_ids_by_codes,
    )
    if missing_directions:
        raise EntryRejected("考向编码不在字典里：" + "、".join(missing_directions))
    point_ids, missing_points = _resolve_ids(
        conn,
        document.get("knowledge_point_ids") or _taxonomy_ids(document, "knowledge_point_ids"),
        dao_dictionary.knowledge_ids_by_codes,
    )
    if missing_points:
        raise EntryRejected("知识点编码不在字典里：" + "、".join(missing_points))

    return NewQuestion(
        stem=_text(document.get("stem"), 50000),
        subject_id=subject.id,
        question_type_id=question_type.id,
        difficulty_id=difficulty.id,
        quality_id=quality.id,
        options=options,
        answer=answer_text,
        solution=_text(document.get("solution"), 60000),
        remark=_text(document.get("remark"), 20000),
        supplements=_supplements(document),
        images=_images(document),
        exam_direction_ids=direction_ids,
        knowledge_point_ids=point_ids,
        exam=_exam(
            conn,
            document,
            subject_id=subject.id,
            grade_id=None if grade is None else grade.id,
        ),
    )


__all__ = ["prepare_question"]
