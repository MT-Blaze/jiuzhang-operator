"""题库引擎 v2 的录题写入：主表与从表逐张分步落库，全程单表语句、事务收口。

铁律对照：
- 不拼多表 JOIN，每张表一条独立 INSERT / SELECT；
- 不写 JSON 列，教研杂项落 ``question_supplements`` 的命名空间行；
- 题目身份由底座签发（``q_`` 前缀），表单带来的 id 一律不认；
- 任一从表写失败整题回滚，绝不留下「有主表没答案」的半道题。
"""

from __future__ import annotations

import re
import secrets
import sqlite3
from datetime import datetime, timezone

from app.bank_engine.exam_key import exam_natural_key, find_exam_id
from app.bank_engine.exam_orgs import ensure_exam_org
from app.bank_engine.models import CreatedQuestion, NewExam, NewImage, NewQuestion
from app.bank_engine.seeds.curriculum import QUESTION_TYPE_CHOICE_ID

OPTION_LABEL_RE = re.compile(r"^[A-H]$")
IMAGE_SLOTS = ("stem", "answer", "solution", "option")


class EntryRejected(ValueError):
    """录题表单不合格；``errors`` 是逐条可读原因，不写半截数据。"""

    def __init__(self, errors: list[str] | str) -> None:
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("；".join(self.errors))


def normalize_exam_type(text: str) -> str:
    """只做去空白：认不出就保留老师原话，绝不悄悄改成另一个类型。"""
    return str(text or "").strip()[:64]


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
    if question.exam is not None:
        exam = question.exam
        if not exam.exam_type:
            problems.append("考试类型不能为空")
        if not 1900 <= exam.year <= 2100:
            problems.append("试卷年份必须在 1900–2100 之间")
        if exam.month is not None and not 1 <= exam.month <= 12:
            problems.append("试卷月份必须在 1–12 之间")
        if exam.mock_round is not None and not 1 <= exam.mock_round <= 10:
            problems.append("模考轮次必须在 1–10 之间")
        if exam.semester not in (None, "上学期", "下学期"):
            problems.append("学期只能是上学期或下学期")
        if exam.subject_id != question.subject_id:
            problems.append("试卷学科与题目学科不一致")
        for table, value, label in (
            ("dict_grades", exam.grade_id, "年级"),
            ("dict_subjects", exam.subject_id, "学科"),
        ):
            if conn.execute("SELECT 1 FROM " + table + " WHERE id = ?", (value,)).fetchone() is None:
                problems.append(f"试卷里的{label}不存在")
        if exam.region_id is not None and conn.execute(
            "SELECT 1 FROM dim_regions WHERE id = ?", (exam.region_id,)
        ).fetchone() is None:
            problems.append("试卷里的参考地区不存在")
        for school_id in dict.fromkeys(exam.school_ids):
            if conn.execute("SELECT 1 FROM dim_schools WHERE id = ?", (school_id,)).fetchone() is None:
                problems.append("试卷里的学校不存在：" + str(school_id))
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
            "(question_id, belongs_to, option_id, path, tikz_code, alt, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                question_id,
                belongs_to,
                option_id,
                image.path[:500],
                None if not image.tikz_code else image.tikz_code[:20000],
                image.alt,
                position,
            ),
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


def ensure_exam_type_id(conn: sqlite3.Connection, name: str) -> int:
    """字典优先；字典里没有的新类型就地建档，绝不把老师填的类型丢掉或改名。"""
    text = normalize_exam_type(name)
    if not text:
        raise EntryRejected("考试类型不能为空")
    row = conn.execute(
        "SELECT id FROM dict_exam_types WHERE name = ? OR code = ?", (text, text)
    ).fetchone()
    if row is not None:
        return int(row["id"])
    sort_order = int(
        conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM dict_exam_types"
        ).fetchone()[0]
    )
    cursor = conn.execute(
        "INSERT INTO dict_exam_types (name, code, sort_order) VALUES (?, ?, ?)",
        (text, "custom_" + secrets.token_hex(5), sort_order),
    )
    return int(cursor.lastrowid)


def _exam_level_id(conn: sqlite3.Connection, name: str | None) -> int | None:
    text = str(name or "").strip()
    if not text:
        return None
    row = conn.execute(
        "SELECT id FROM dict_exam_levels WHERE name = ? OR code = ?", (text, text)
    ).fetchone()
    return None if row is None else int(row["id"])


def _ensure_exam(conn: sqlite3.Connection, exam: NewExam) -> int:
    exam_type_id = ensure_exam_type_id(conn, exam.exam_type)
    exam_org_id = ensure_exam_org(
        conn, exam.exam_org, exam.exam_org_type, exam.school_ids
    )
    exam_level_id = _exam_level_id(conn, exam.exam_level)
    key = exam_natural_key(
        year=exam.year,
        month=exam.month,
        mock_round=exam.mock_round,
        semester=exam.semester,
        exam_org_id=exam_org_id,
        subject_id=exam.subject_id,
        grade_id=exam.grade_id,
        exam_type_id=exam_type_id,
    )
    exam_id = find_exam_id(conn, key)
    if exam_id is not None:
        # 同一张卷再录一次：范围 / 层级按最后一次口径更新，其余字段由自然键锁定。
        conn.execute(
            "UPDATE exams SET region_id = COALESCE(?, region_id), "
            "exam_level_id = COALESCE(?, exam_level_id) WHERE id = ?",
            (exam.region_id, exam_level_id, exam_id),
        )
    else:
        cursor = conn.execute(
            "INSERT INTO exams "
            "(year, region_id, exam_org_id, exam_level_id, month, exam_type_id, "
            "mock_round, grade_id, semester, subject_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                exam.year,
                exam.region_id,
                exam_org_id,
                exam_level_id,
                exam.month,
                exam_type_id,
                exam.mock_round,
                exam.grade_id,
                exam.semester,
                exam.subject_id,
            ),
        )
        exam_id = int(cursor.lastrowid)
    for school_id in dict.fromkeys(exam.school_ids):
        conn.execute(
            "INSERT OR IGNORE INTO exam_school_map (exam_id, school_id) VALUES (?, ?)",
            (exam_id, school_id),
        )
    return exam_id


def _insert_exam(conn: sqlite3.Connection, question_id: str, exam: NewExam | None) -> None:
    if exam is None:
        return
    exam_id = _ensure_exam(conn, exam)
    conn.execute(
        "INSERT INTO question_exams (question_id, exam_id, question_no, score) "
        "VALUES (?, ?, ?, ?)",
        (question_id, exam_id, exam.question_no, max(0.0, float(exam.score or 0.0))),
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
        _insert_exam(conn, question_id, question.exam)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return CreatedQuestion(question_id)


__all__ = [
    "EntryRejected",
    "create_question",
    "ensure_exam_type_id",
    "new_question_id",
    "normalize_exam_type",
]
