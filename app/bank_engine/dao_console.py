"""字典控制台 DAO：基础五表的单表 CRUD 与删除防呆（阶段二）。

铁律对照：
- 每条 SQL 只碰一张表，表名 / 列名全部来自下方白名单 spec，绝不拼用户输入；
- 值一律走 ``?`` 占位符，不用 f-string 拼 SQL；
- 删除前用 ``PRAGMA foreign_key_list`` 逐张子表单表计数，发现引用即拦截，
  跨表关系在 Python 层组装，不做连级 JOIN。

spec 驱动：五张表共用一套读写逻辑，列定义、可编辑列、搜索列与全局设置
绑定都集中在 ``SPECS``，改口径只改这里。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from app.bank_engine.models import (
    Chapter,
    CoreCompetency,
    Difficulty,
    ExamDirection,
    ExamType,
    Grade,
    ImportReport,
    KnowledgePoint,
    Quality,
    QuestionType,
    ReferenceHit,
    Region,
    School,
    SolutionMethod,
    Subject,
    SubjectThought,
    TextbookVersion,
)


class ConsoleLookupError(KeyError):
    """未知的表名，或更新 / 删除时行不存在。"""


class ReferencedError(RuntimeError):
    """删除被外键引用的行：携带引用明细，由 API 换成 HTTP 409。"""

    def __init__(self, hits: tuple[ReferenceHit, ...]) -> None:
        self.hits = hits
        super().__init__("该行已被其他表引用，禁止删除")


class ConflictError(RuntimeError):
    """唯一约束 / 外键 / CHECK 冲突：插入或改名撞了已有数据。"""


@dataclass(frozen=True)
class TableSpec:
    table: str
    label: str
    model: type
    columns: tuple[str, ...]
    editable: tuple[str, ...]
    required: tuple[str, ...]
    search: tuple[str, ...]
    order: str
    int_columns: tuple[str, ...]
    nullable: tuple[str, ...]
    global_filters: tuple[tuple[str, str], ...]


SPECS: dict[str, TableSpec] = {
    "dict_subjects": TableSpec(
        table="dict_subjects", label="学科", model=Subject,
        columns=("id", "name", "code", "sort_order"),
        editable=("name", "code", "sort_order"), required=("name", "code"),
        search=("name", "code"), order="sort_order, id",
        int_columns=("sort_order",), nullable=(),
        global_filters=(("subject_id", "id"),),
    ),
    "dict_grades": TableSpec(
        table="dict_grades", label="年级", model=Grade,
        columns=("id", "name", "code", "sort_order", "stage"),
        editable=("name", "code", "sort_order", "stage"), required=("name", "code"),
        search=("name", "code", "stage"), order="sort_order, id",
        int_columns=("sort_order",), nullable=("stage",),
        global_filters=(("stage", "stage"),),
    ),
    "dict_exam_types": TableSpec(
        table="dict_exam_types", label="考试类型", model=ExamType,
        columns=("id", "name", "code", "sort_order"),
        editable=("name", "code", "sort_order"), required=("name", "code"),
        search=("name", "code"), order="sort_order, id",
        int_columns=("sort_order",), nullable=(), global_filters=(),
    ),
    "dim_regions": TableSpec(
        table="dim_regions", label="行政区划", model=Region,
        columns=("id", "name", "code", "level", "parent_id", "sort_order"),
        editable=("name", "code", "level", "parent_id", "sort_order"),
        required=("name", "code", "level"), search=("name", "code"),
        order="level, sort_order, id", int_columns=("level", "parent_id", "sort_order"),
        nullable=("parent_id",), global_filters=(),
    ),
    "dim_schools": TableSpec(
        table="dim_schools", label="学校", model=School,
        columns=("id", "name", "short_name", "code", "region", "region_id", "textbook_id"),
        editable=("name", "short_name", "code", "region", "region_id", "textbook_id"),
        required=("name", "short_name", "code"),
        search=("name", "short_name", "code", "region"), order="id",
        int_columns=("region_id", "textbook_id"), nullable=("region", "region_id", "textbook_id"),
        global_filters=(("textbook_id", "textbook_id"),),
    ),
    # 阶段三：四栏联动的双击改名复用这套规格驱动 CRUD（新增走联动专用口）。
    "dim_knowledge_points": TableSpec(
        table="dim_knowledge_points", label="知识点", model=KnowledgePoint,
        columns=("id", "name", "code", "sort_order", "subject_id", "parent_id"),
        editable=("name", "code", "sort_order"), required=("name", "code"),
        search=("name", "code"), order="sort_order, id",
        int_columns=("sort_order", "subject_id", "parent_id"), nullable=("parent_id",),
        global_filters=(("subject_id", "subject_id"),),
    ),
    "dim_exam_directions": TableSpec(
        table="dim_exam_directions", label="考向", model=ExamDirection,
        columns=("id", "name", "code", "sort_order", "subject_id", "chapter_id", "description"),
        editable=("name", "code", "sort_order", "description"), required=("name", "code"),
        search=("name", "code"), order="sort_order, id",
        int_columns=("sort_order", "subject_id", "chapter_id"),
        nullable=("chapter_id", "description"),
        global_filters=(("subject_id", "subject_id"),),
    ),
    # 二级标签补齐的只读字典：同一套规格驱动，editable 留空，前端只渲染平铺表格。
    "dict_question_types": TableSpec(
        table="dict_question_types", label="题型", model=QuestionType,
        columns=("id", "name", "code", "sort_order"),
        editable=(), required=(), search=("name", "code"), order="sort_order, id",
        int_columns=("sort_order",), nullable=(), global_filters=(),
    ),
    "dict_difficulties": TableSpec(
        table="dict_difficulties", label="难度", model=Difficulty,
        columns=("id", "name", "code", "sort_order", "level", "description"),
        editable=(), required=(), search=("name", "code", "description"),
        order="level, sort_order, id", int_columns=("sort_order", "level"),
        nullable=("description",), global_filters=(),
    ),
    "dict_question_qualities": TableSpec(
        table="dict_question_qualities", label="题目质量", model=Quality,
        columns=("id", "name", "code", "sort_order"),
        editable=(), required=(), search=("name", "code"), order="sort_order, id",
        int_columns=("sort_order",), nullable=(), global_filters=(),
    ),
    "dim_textbook_versions": TableSpec(
        table="dim_textbook_versions", label="教材版本", model=TextbookVersion,
        columns=("id", "name", "code", "sort_order", "publisher", "subject_id"),
        editable=(), required=(), search=("name", "code", "publisher"),
        order="sort_order, id", int_columns=("sort_order", "subject_id"),
        nullable=("publisher",), global_filters=(("subject_id", "subject_id"),),
    ),
    "dim_textbook_chapters": TableSpec(
        table="dim_textbook_chapters", label="教材章节", model=Chapter,
        columns=("id", "name", "code", "sort_order", "textbook_id", "parent_id"),
        editable=(), required=(), search=("name", "code"),
        order="textbook_id, sort_order, id",
        int_columns=("sort_order", "textbook_id", "parent_id"),
        nullable=("parent_id",), global_filters=(("textbook_id", "textbook_id"),),
    ),
    "dict_subject_thoughts": TableSpec(
        table="dict_subject_thoughts", label="学科思想", model=SubjectThought,
        columns=("id", "name", "code", "sort_order", "subject_id", "stage"),
        editable=(), required=(), search=("name", "code"), order="sort_order, id",
        int_columns=("sort_order", "subject_id"), nullable=("stage",),
        global_filters=(("subject_id", "subject_id"), ("stage", "stage")),
    ),
    "dict_solution_methods": TableSpec(
        table="dict_solution_methods", label="解题方法", model=SolutionMethod,
        columns=("id", "name", "code", "sort_order", "subject_id", "stage"),
        editable=(), required=(), search=("name", "code"), order="sort_order, id",
        int_columns=("sort_order", "subject_id"), nullable=("stage",),
        global_filters=(("subject_id", "subject_id"), ("stage", "stage")),
    ),
    "dict_core_competencies": TableSpec(
        table="dict_core_competencies", label="核心素养", model=CoreCompetency,
        columns=("id", "name", "code", "sort_order", "subject_id", "stage"),
        editable=(), required=(), search=("name", "code"), order="sort_order, id",
        int_columns=("sort_order", "subject_id"), nullable=("stage",),
        global_filters=(("subject_id", "subject_id"), ("stage", "stage")),
    ),
}

COLUMN_LABELS: dict[str, str] = {
    "id": "ID", "name": "名称", "code": "编码", "sort_order": "排序",
    "stage": "学段", "level": "层级", "parent_id": "父级ID", "short_name": "简称",
    "region": "地区", "region_id": "区划ID", "textbook_id": "教材ID",
    "subject_id": "学科ID", "chapter_id": "章节ID", "description": "说明",
    "publisher": "出版社",
}

# 子表中文名：删除防呆对话框给老师看的人话，未收录的退回表名。
TABLE_LABELS: dict[str, str] = {
    "dict_subjects": "学科", "dict_grades": "年级", "dict_exam_types": "考试类型",
    "dict_question_types": "题型", "dict_difficulties": "难度",
    "dict_question_qualities": "题目质量", "dim_textbook_versions": "教材版本",
    "dim_regions": "行政区划", "dim_schools": "学校", "dim_textbooks": "教材版本",
    "dim_textbook_chapters": "教材章节", "dim_knowledge_points": "知识点",
    "dim_exam_directions": "考向", "exams": "试卷", "questions": "题目",
    "exam_school_map": "试卷—学校关联", "chapter_knowledge_map": "章节—知识点关联",
    "knowledge_exam_map": "知识点—考向关联", "question_exam_map": "题目—考向关联",
    "question_knowledge_map": "题目—知识点关联", "question_exams": "题目—试卷关联",
    "dict_subject_thoughts": "学科思想", "dict_solution_methods": "解题方法",
    "dict_core_competencies": "核心素养",
}


def get_spec(table: str) -> TableSpec:
    spec = SPECS.get(table)
    if spec is None:
        raise ConsoleLookupError("未知的字典表：" + str(table))
    return spec


def fields_meta(spec: TableSpec) -> tuple[dict[str, Any], ...]:
    """给前端表格的列描述：列名、中文名、是否可编辑、值类型。"""
    return tuple(
        {
            "key": col,
            "label": COLUMN_LABELS.get(col, col),
            "editable": col in spec.editable,
            "kind": "int" if col in spec.int_columns else "text",
        }
        for col in spec.columns
    )


def _model(spec: TableSpec, row: sqlite3.Row) -> Any:
    return spec.model(**{col: row[col] for col in spec.columns})


def _filters(
    spec: TableSpec, keyword: str | None, filters: dict[str, Any]
) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if keyword:
        like = "%" + keyword + "%"
        clauses.append("(" + " OR ".join(col + " LIKE ?" for col in spec.search) + ")")
        params.extend(like for _ in spec.search)
    for param, col in spec.global_filters:
        value = filters.get(param)
        if value is not None and value != "":
            clauses.append(col + " = ?")
            params.append(value)
    return clauses, params


def _where(clauses: list[str]) -> str:
    return "" if not clauses else " WHERE " + " AND ".join(clauses)


def list_rows(
    conn: sqlite3.Connection,
    table: str,
    *,
    keyword: str | None = None,
    filters: dict[str, Any] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[tuple[Any, ...], int]:
    spec = get_spec(table)
    clauses, params = _filters(spec, keyword, filters or {})
    where = _where(clauses)
    total = int(conn.execute("SELECT COUNT(*) FROM " + table + where, params).fetchone()[0])
    sql = (
        "SELECT " + ", ".join(spec.columns) + " FROM " + table + where
        + " ORDER BY " + spec.order + " LIMIT ? OFFSET ?"
    )
    rows = conn.execute(sql, params + [limit, offset]).fetchall()
    return tuple(_model(spec, row) for row in rows), total


def get_row(conn: sqlite3.Connection, table: str, row_id: int) -> Any:
    spec = get_spec(table)
    row = conn.execute(
        "SELECT " + ", ".join(spec.columns) + " FROM " + table + " WHERE id = ?",
        (row_id,),
    ).fetchone()
    if row is None:
        raise ConsoleLookupError("行不存在：" + table + "#" + str(row_id))
    return _model(spec, row)


def _clean_values(
    spec: TableSpec, values: dict[str, Any], *, for_insert: bool
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in spec.editable:
        label = COLUMN_LABELS.get(col, col)
        if col not in values:
            if for_insert and col in spec.required:
                raise ValueError("缺少必填字段：" + label)
            continue
        raw = values[col]
        empty = raw is None or (isinstance(raw, str) and raw.strip() == "")
        if empty and col in spec.nullable:
            out[col] = None
            continue
        if empty and col in spec.required:
            raise ValueError("必填字段不能为空：" + label)
        if col in spec.int_columns:
            if empty:
                raise ValueError("字段需要整数：" + label)
            try:
                out[col] = int(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("字段需要整数：" + label) from exc
        else:
            out[col] = str(raw).strip()
    return out


def _conflict(exc: sqlite3.IntegrityError) -> ConflictError:
    text = str(exc)
    if "UNIQUE" in text:
        friendly = "名称或编码已存在，唯一约束冲突"
    elif "FOREIGN KEY" in text:
        friendly = "外键约束冲突：引用的上级行不存在"
    elif "CHECK" in text:
        friendly = "取值违反约束（如区划层级与父级不匹配）"
    elif "NOT NULL" in text:
        friendly = "必填字段不能为空"
    else:
        friendly = "数据约束冲突"
    return ConflictError(friendly + "（" + text + "）")


def insert_row(conn: sqlite3.Connection, table: str, values: dict[str, Any]) -> Any:
    spec = get_spec(table)
    clean = _clean_values(spec, values, for_insert=True)
    if not clean:
        raise ValueError("没有可写入的字段")
    cols = list(clean.keys())
    sql = (
        "INSERT INTO " + table + " (" + ", ".join(cols) + ") VALUES ("
        + ", ".join("?" for _ in cols) + ")"
    )
    try:
        cursor = conn.execute(sql, [clean[col] for col in cols])
    except sqlite3.IntegrityError as exc:
        raise _conflict(exc) from exc
    conn.commit()
    return get_row(conn, table, int(cursor.lastrowid))


def update_row(
    conn: sqlite3.Connection, table: str, row_id: int, values: dict[str, Any]
) -> Any:
    spec = get_spec(table)
    get_row(conn, table, row_id)
    clean = _clean_values(spec, values, for_insert=False)
    if not clean:
        return get_row(conn, table, row_id)
    cols = list(clean.keys())
    sql = (
        "UPDATE " + table + " SET " + ", ".join(col + " = ?" for col in cols)
        + " WHERE id = ?"
    )
    try:
        conn.execute(sql, [clean[col] for col in cols] + [row_id])
    except sqlite3.IntegrityError as exc:
        raise _conflict(exc) from exc
    conn.commit()
    return get_row(conn, table, row_id)


def find_references(
    conn: sqlite3.Connection,
    table: str,
    row_id: int,
    *,
    exclude: dict[str, tuple[str, Any]] | None = None,
) -> tuple[ReferenceHit, ...]:
    """逐张子表单表计数：谁的外键指向这一行。不做连级 JOIN。

    exclude 给联动删除用：{子表: (列, 值)}，计数时排除该列等于此值的行
    （例如删考向时不算当前知识点自己的关联行）；列名只来自内部白名单调用方。
    """
    get_spec(table)
    children = [
        str(row["name"])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    hits: list[ReferenceHit] = []
    for child in children:
        for fk in conn.execute("PRAGMA foreign_key_list(" + child + ")"):
            if str(fk["table"]) != table:
                continue
            column = str(fk["from"])
            sql = "SELECT COUNT(*) FROM " + child + " WHERE " + column + " = ?"
            params: list[Any] = [row_id]
            if exclude and child in exclude:
                ex_col, ex_val = exclude[child]
                sql += " AND " + ex_col + " <> ?"
                params.append(ex_val)
            count = int(conn.execute(sql, params).fetchone()[0])
            if count > 0:
                hits.append(ReferenceHit(
                    table=child, label=TABLE_LABELS.get(child, child),
                    column=column, count=count,
                ))
    return tuple(hits)


def delete_row(conn: sqlite3.Connection, table: str, row_id: int) -> None:
    get_row(conn, table, row_id)
    hits = find_references(conn, table, row_id)
    if hits:
        raise ReferencedError(hits)
    conn.execute("DELETE FROM " + get_spec(table).table + " WHERE id = ?", (row_id,))
    conn.commit()


def import_rows(conn: sqlite3.Connection, data: dict[str, Any]) -> ImportReport:
    """TOML 批量导入：顶层键是表名，值是行表数组。重复行跳过，坏行记错不中断。"""
    inserted: dict[str, int] = {}
    skipped: dict[str, int] = {}
    errors: list[str] = []
    for table, rows in data.items():
        if table not in SPECS:
            errors.append("未知表，已跳过：" + str(table))
            continue
        if not isinstance(rows, list):
            errors.append("表 " + table + " 的内容必须是行数组（[[表名]]）")
            continue
        inserted.setdefault(table, 0)
        skipped.setdefault(table, 0)
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                errors.append(table + " 第 " + str(index) + " 行不是表结构")
                continue
            try:
                insert_row(conn, table, row)
                inserted[table] += 1
            except ConflictError:
                skipped[table] += 1
            except ValueError as exc:
                errors.append(table + " 第 " + str(index) + " 行：" + str(exc))
    return ImportReport(inserted=inserted, skipped=skipped, errors=tuple(errors))


__all__ = [
    "COLUMN_LABELS",
    "ConflictError",
    "ConsoleLookupError",
    "ReferencedError",
    "SPECS",
    "TABLE_LABELS",
    "TableSpec",
    "delete_row",
    "fields_meta",
    "find_references",
    "get_row",
    "get_spec",
    "import_rows",
    "insert_row",
    "list_rows",
    "update_row",
]