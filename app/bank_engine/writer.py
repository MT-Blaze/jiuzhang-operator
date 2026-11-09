"""题库引擎 v2 的录题写入：主表与从表逐张分步落库，全程单表语句、事务收口。

铁律对照：
- 不拼多表 JOIN，每张表一条独立 INSERT / SELECT；
- 不写 JSON 列，教研杂项落 ``question_supplements`` 的命名空间行；
- 题目身份由底座签发（``q_`` 前缀），表单带来的 id 一律不认；
- 任一从表写失败整题回滚，绝不留下「有主表没答案」的半道题。
"""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timezone

from app.bank_engine.models import CreatedQuestion, NewImage, NewQuestion, NewSource
from app.bank_engine.seeds.curriculum import QUESTION_TYPE_CHOICE_ID

EXAM_TYPES = (
    "高考题", "联考题", "区域统考题", "校考题", "机构题",
    "汇编题", "自编题", "强基题", "竞赛题", "自主招生题", "外国题",
)
OPTION_LABEL_RE = re.compile(r"^[A-H]$")
IMAGE_SLOTS = ("stem", "answer", "solution", "option")
# 表单里的考试类型是老师随手写的词，落库必须收敛到 11 选 1 的 CHECK 取值。
_EXAM_TYPE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("高考题", ("高考",)),
    ("竞赛题", ("竞赛", "奥赛", "联赛")),
    ("强基题", ("强基",)),
    ("自主招生题", ("自主招生",)),
    ("外国题", ("外国", "amc", "a-level", "a level", "ib", "ap ")),
    ("区域统考题", ("统考", "一模", "二模", "市质检", "区质检")),
    ("校考题", ("校考", "月考", "期中", "期末", "周测")),
    ("联考题", ("联考", "模考")),
    ("机构题", ("机构", "补习", "培训")),
    ("汇编题", ("汇编", "真题集")),
)


class EntryRejected(ValueError):
    """录题表单不合格；``errors`` 是逐条可读原因，不写半截数据。"""

    def __init__(self, errors: list[str] | str) -> None:
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("；".join(self.errors))


def normalize_exam_type(text: str) -> str:
    value = str(text or "").strip()
    if value in EXAM_TYPES:
        return value
    lowered = value.lower()
    for canonical, hints in _EXAM_TYPE_HINTS:
        if any(hint in lowered for hint in hints):
            return canonical
    return "自编题"


def new_question_id() -> str:
    return "q_" + secrets.token_hex(6)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean(text: object, limit: int) -> str:
    return str("" if text is None else text).strip()[:limit]


def _validate(conn: sqlite3.Connection, question: NewQuestion) -> None:
    problems: list[str] = []
    if not question.stem.strip():
        problems.append("题干不能为空")
    if len(question.stem) > 50000:
        problems.append("题干过长（上限 50000 字）")
    for table, value, label in (
        ("dict_subjects", question.subject_id, "学科"),
        ("dict_question_types", question.question_type_id, "题型"),
        ("dict_difficulties", question.difficulty_id, "难度"),
        ("dict_question_qualities", question.quality_id, "质量分档"),
    ):
        if conn.execute("SELECT 1 FROM " + table + " WHERE id = ?", (value,)).fetchone() is None:
            problems.append(f"{label}不在字典里")
    labels: list[str] = []
    for option in question.options:
        if OPTION_LABEL_RE.match(option.label) is None:
            problems.append("选项标号只能是 A–H")
        if not option.content.strip():
            problems.append("选项 " + option.label + " 内容为空")
        if option.label in labels:
            problems.append("选项标号 " + option.label + " 重复")
        labels.append(option.label)
    is_choice = question.question_type_id == QUESTION_TYPE_CHOICE_ID
    if is_choice:
        if len(question.options) < 2:
            problems.append("选择题至少要有两个选项")
        if not any(option.is_correct for option in question.options):
            problems.append("选择题至少要标一个正确选项")
        if not question.answer.strip():
            problems.append("选择题答案不能为空")
    elif not question.answer.strip():
        problems.append("答案不能为空")
    if question.source is not None:
        source = question.source
        if source.exam_type not in EXAM_TYPES:
            problems.append("考试类型不合法")
        for table, value, label in (
            ("dict_grades", source.grade_id, "年级"),
            ("dim_textbook_chapters", source.chapter_id, "章节"),
            ("dim_schools", source.school_id, "学校"),
        ):
            if value is None:
                continue
            if conn.execute("SELECT 1 FROM " + table + " WHERE id = ?", (value,)).fetchone() is None:
                problems.append(f"来源里的{label}不存在")
    if problems:
        raise EntryRejected(problems)

    direction_ids = list(dict.fromkeys(question.exam_direction_ids))
    if direction_ids:
        placeholders = ",".join("?" for _ in direction_ids)
        rows = conn.execute(
            "SELECT id, subject_id FROM dim_exam_directions WHERE id IN (" + placeholders + ")",
            direction_ids,
        ).fetchall()
        found = {int(row["id"]): int(row["subject_id"]) for row in rows}
        missing = [key for key in direction_ids if key not in found]
        if missing:
            raise EntryRejected("考向不存在：" + "、".join(str(key) for key in missing))
        wrong = [str(key) for key, subject in found.items() if subject != question.subject_id]
        if wrong:
            raise EntryRejected("考向与学科不匹配：" + "、".join(wrong))

    point_ids = list(dict.fromkeys(question.knowledge_point_ids))
    if point_ids:
        placeholders = ",".join("?" for _ in point_ids)
        rows = conn.execute(
            "SELECT id, subject_id FROM dim_knowledge_points "
            "WHERE id IN (" + placeholders + ")",
            point_ids,
        ).fetchall()
        found = {int(row["id"]): int(row["subject_id"]) for row in rows}
        missing = [key for key in point_ids if key not in found]
        if missing:
            raise EntryRejected("知识点不存在：" + "、".join(str(key) for key in missing))
        wrong = [str(key) for key, subject in found.items() if subject != question.subject_id]
        if wrong:
            raise EntryRejected("知识点与学科不匹配：" + "、".join(wrong))


def _insert_options(
    conn: sqlite3.Connection, question_id: str, question: NewQuestion
) -> dict[str, int]:
    option_ids: dict[str, int] = {}
    for option in question.options:
        cursor = conn.execute(
            "INSERT INTO question_options (question_id, option_label, content, is_correct) "
            "VALUES (?, ?, ?, ?)",
            (question_id, option.label, option.content.strip(), 1 if option.is_correct else 0),
        )
        option_ids[option.label] = int(cursor.lastrowid)
    return option_ids


def _insert_images(
    conn: sqlite3.Connection,
    question_id: str,
    images: tuple[NewImage, ...],
    option_ids: dict[str, int],
) -> None:
    for position, image in enumerate(images):
        belongs_to = image.belongs_to if image.belongs_to in IMAGE_SLOTS else "stem"
        option_id = None
        if belongs_to == "option":
            option_id = option_ids.get(image.option_label or "")
            if option_id is None:
                continue
        conn.execute(
            "INSERT INTO question_images "
            "(question_id, belongs_to, option_id, path, alt, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (question_id, belongs_to, option_id, image.path[:500], image.alt, position),
        )


def _insert_text_tables(conn: sqlite3.Connection, question_id: str, question: NewQuestion) -> None:
    if question.answer.strip():
        conn.execute(
            "INSERT INTO question_answers (question_id, answer_content, is_primary, sort_order) "
            "VALUES (?, ?, 1, 0)",
            (question_id, question.answer.strip()),
        )
    if question.solution.strip():
        conn.execute(
            "INSERT INTO question_solutions (question_id, content, is_primary, sort_order) "
            "VALUES (?, ?, 1, 0)",
            (question_id, question.solution.strip()),
        )
    if question.remark.strip():
        conn.execute(
            "INSERT INTO question_remarks (question_id, remark) VALUES (?, ?)",
            (question_id, question.remark.strip()),
        )
    for supplement in question.supplements:
        conn.execute(
            "INSERT INTO question_supplements "
            "(question_id, namespace, field_key, field_value, sort_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                question_id,
                _clean(supplement.namespace, 32),
                _clean(supplement.field_key, 32),
                supplement.field_value,
                supplement.sort_order,
            ),
        )


def _insert_maps(conn: sqlite3.Connection, question_id: str, question: NewQuestion) -> None:
    for direction_id in dict.fromkeys(question.exam_direction_ids):
        conn.execute(
            "INSERT INTO question_exam_map (question_id, exam_direction_id) VALUES (?, ?)",
            (question_id, direction_id),
        )
    for point_id in dict.fromkeys(question.knowledge_point_ids):
        conn.execute(
            "INSERT INTO question_knowledge_map (question_id, knowledge_point_id) VALUES (?, ?)",
            (question_id, point_id),
        )


def _source_code(name: str, year: int | None, region: str | None) -> str:
    seed = f"{name}\u0001{year or 0}\u0001{region or ''}".encode("utf-8")
    return "src_" + hashlib.sha1(seed).hexdigest()[:16]


def _ensure_source(conn: sqlite3.Connection, source: NewSource) -> int:
    row = conn.execute(
        "SELECT id FROM dim_sources WHERE name = ? "
        "AND COALESCE(year, 0) = ? AND COALESCE(region, '') = ?",
        (source.name, source.year or 0, source.region or ""),
    ).fetchone()
    if row is not None:
        return int(row["id"])
    cursor = conn.execute(
        "INSERT INTO dim_sources "
        "(name, code, exam_type, year, region, grade_id, chapter_id, school_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            source.name,
            _source_code(source.name, source.year, source.region),
            source.exam_type,
            source.year,
            source.region,
            source.grade_id,
            source.chapter_id,
            source.school_id,
        ),
    )
    return int(cursor.lastrowid)


def _insert_source(conn: sqlite3.Connection, question_id: str, source: NewSource | None) -> None:
    if source is None or not source.name:
        return
    source_id = _ensure_source(conn, source)
    conn.execute(
        "INSERT INTO question_source_map (question_id, source_id, question_no, score) "
        "VALUES (?, ?, ?, ?)",
        (question_id, source_id, source.question_no, max(0.0, float(source.score or 0.0))),
    )


def create_question(conn: sqlite3.Connection, question: NewQuestion) -> CreatedQuestion:
    """把一道题分步写进主表与五张从表 / 关系表；失败整题回滚。"""
    _validate(conn, question)
    question_id = new_question_id()
    try:
        conn.execute("BEGIN")
        conn.execute(
            "INSERT INTO questions "
            "(id, stem, subject_id, question_type_id, difficulty_id, quality_id, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                question_id,
                question.stem.strip(),
                question.subject_id,
                question.question_type_id,
                question.difficulty_id,
                question.quality_id,
                _now(),
                _now(),
            ),
        )
        option_ids = _insert_options(conn, question_id, question)
        _insert_images(conn, question_id, question.images, option_ids)
        _insert_text_tables(conn, question_id, question)
        _insert_maps(conn, question_id, question)
        _insert_source(conn, question_id, question.source)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return CreatedQuestion(question_id)


__all__ = [
    "EXAM_TYPES",
    "EntryRejected",
    "create_question",
    "new_question_id",
    "normalize_exam_type",
]
