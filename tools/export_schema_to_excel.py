"""把题库 schema 的文字内容同步到桌面「数据库表结构一览表」的 sheet1。

只换文字：表名、功能说明、字段名与字段中文标签、批注正文。
列宽、行高、合并单元格、字体样式全部按下面硬编码的常量校验后原样保留，
脚本不计算、不重排、不新增任何版式；文件里的其它工作表与样式字节不动。

用法：
    .venv/Scripts/python.exe tools/export_schema_to_excel.py --workbook <xlsx 路径>
    .venv/Scripts/python.exe tools/export_schema_to_excel.py --workbook <路径> --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from html import unescape
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"

SHEET1 = "xl/worksheets/sheet1.xml"
SHARED = "xl/sharedStrings.xml"
COMMENTS1 = "xl/comments1.xml"
VML1 = "xl/drawings/vmlDrawing1.vml"

# ---- 手工调好的版式，硬编码后只校验不回写（改这里等于改版式，必须人工确认）----
TABLE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("主表(3张)", ("questions", "ingest_batches", "raw_questions")),
    (
        "从表(8张)",
        (
            "question_options",
            "question_images",
            "question_answers",
            "question_remarks",
            "question_solutions",
            "question_supplements",
            "question_statistics",
            "exams",
        ),
    ),
    (
        "系统基石字典(4张)",
        ("dict_subjects", "dict_grades", "dim_regions", "dict_exam_types"),
    ),
    (
        "实体维度字典(3张)",
        ("dim_textbooks", "dim_textbook_chapters", "dim_schools"),
    ),
    (
        "教研属性字典(8张)",
        (
            "dict_question_types",
            "dict_difficulties",
            "dict_question_qualities",
            "dim_knowledge_points",
            "dim_exam_directions",
            "dict_subject_thoughts",
            "dict_solution_methods",
            "dict_core_competencies",
        ),
    ),
    (
        "关系表(9张)",
        (
            "question_exam_map",
            "question_knowledge_map",
            "knowledge_exam_map",
            "question_exams",
            "exam_school_map",
            "solution_thought_map",
            "solution_method_map",
            "solution_competency_map",
            "chapter_knowledge_map",
        ),
    ),
)

# (min, max, 列宽, 列样式)
COLUMN_WIDTHS: tuple[tuple[int, int, str, str | None], ...] = (
    (1, 1, "4", "9"),
    (2, 2, "6.25", None),
    (3, 3, "24", None),
    (4, 4, "38", None),
    (5, 5, "14", None),
    (6, 6, "20", None),
    (7, 7, "16", None),
    (8, 8, "18", None),
    (9, 9, "17", None),
    (10, 10, "12.75", None),
    (11, 11, "16", None),
    (12, 12, "14", None),
)
MERGES: tuple[str, ...] = ("A2:A4", "A5:A12", "A13:A16", "A17:A19", "A20:A27", "A28:A36")
# 旧版式仅用于校验旧文件后升级到 MERGES：
# V7 = exams 在主表、字典未拆三系列（主表4/从表7/字典15/关系9，exams 在第 5 行）
LEGACY_MERGES_V7: tuple[str, ...] = ("A2:A5", "A6:A12", "A13:A27", "A28:A36")
# V6~V3 = exams 误放字典区的 35 / 33 / 32 / 31 表版式（exams 在字典区第 20 行）
LEGACY_MERGES_V6: tuple[str, ...] = ("A2:A4", "A5:A11", "A12:A27", "A28:A36")
LEGACY_MERGES_V5: tuple[str, ...] = ("A2:A4", "A5:A11", "A12:A26", "A27:A34")
LEGACY_MERGES_V4: tuple[str, ...] = ("A2:A4", "A5:A11", "A12:A25", "A26:A33")
LEGACY_MERGES_V3: tuple[str, ...] = ("A2:A4", "A5:A11", "A12:A25", "A26:A32")
NEW_LAST_ROW = 36
HEADER_HEIGHT = "26.1"
ROW_HEIGHT = "33.950000000000003"
# 长说明的试卷行加高：exams 现归从表第 12 行；V7 旧版式在第 5 行，V6~V3 在字典区第 20 行
ROW_HEIGHT_OVERRIDES: dict[int, str] = {12: "48.95"}
LEGACY_ROW_HEIGHT_OVERRIDES_V7: dict[int, str] = {5: "48.95"}
LEGACY_ROW_HEIGHT_OVERRIDES: dict[int, str] = {20: "48.95"}

HEADERS: tuple[str, ...] = (
    "表分类",
    "序号",
    "表名",
    "表功能说明",
    *[f"第{i}个字段" for i in range(1, 11)],
)
FIRST_FIELD_COL = 4  # E 列，0 基下标
MAX_FIELDS = 10

TABLE_LABELS: dict[str, str] = {
    "questions": "题目主表",
    "ingest_batches": "导入批次表",
    "raw_questions": "原始题目表",
    "question_options": "选项从表",
    "question_images": "图片从表",
    "question_answers": "答案从表",
    "question_remarks": "题目备注从表",
    "question_solutions": "解析从表",
    "question_supplements": "题目补充从表",
    "question_statistics": "题目统计从表",
    "dict_subjects": "学科字典",
    "dict_grades": "年级字典",
    "dict_question_types": "题型字典",
    "dict_difficulties": "难度字典",
    "dict_question_qualities": "题目质量字典",
    "dict_exam_types": "考试类型字典",
    "dim_textbooks": "教材字典",
    "dim_textbook_chapters": "教材章节字典",
    "dim_schools": "学校字典",
    "exams": "试卷主表",
    "dim_knowledge_points": "知识点字典",
    "dim_exam_directions": "考向字典",
    "dim_regions": "行政区划字典",
    "dict_subject_thoughts": "学科思想字典",
    "dict_solution_methods": "解题方法字典",
    "dict_core_competencies": "核心素养字典",
    "question_exam_map": "题目与考向关联表",
    "question_knowledge_map": "题目与知识点关联表",
    "knowledge_exam_map": "知识点与考向关联表",
    "question_exams": "题目与试卷关联表",
    "exam_school_map": "试卷与学校关联表",
    "solution_thought_map": "解析与学科思想关联表",
    "solution_method_map": "解析与解题方法关联表",
    "solution_competency_map": "解析与核心素养关联表",
    "chapter_knowledge_map": "章节与知识点关联表",
}

FIELD_LABELS: dict[str, str] = {
    "id": "主键",
    "name": "名称",
    "code": "编码",
    "sort_order": "排序序号",
    "stage": "学段",
    "stem": "题干",
    "subject_id": "学科外键",
    "question_type_id": "题型外键",
    "difficulty_id": "难度外键",
    "quality_id": "题目质量外键（需显式提供）",
    "raw_id": "原始题目表外键",
    "deleted_at": "软删除时间",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "pipeline_version": "流水线版本",
    "started_at": "开始时间",
    "finished_at": "结束时间",
    "status": "状态",
    "note": "备注",
    "batch_id": "导入批次表外键",
    "raw_content": "原始文本",
    "content_hash": "内容哈希",
    "error": "错误信息",
    "question_id": "题目外键",
    "option_label": "选项标号",
    "content": "内容",
    "is_correct": "是否正确",
    "belongs_to": "图片归属",
    "option_id": "选项外键",
    "path": "文件路径",
    "tikz_code": "TikZ 源码",
    "alt": "替代文本",
    "answer_content": "答案内容",
    "is_primary": "是否主项",
    "remark": "备注原文",
    "namespace": "命名空间",
    "field_key": "补充字段名",
    "field_value": "补充字段值",
    "reference_count": "被题目来源引用次数",
    "level": "难度等级（1-5）",
    "description": "难度说明",
    "ai_prompt": "AI 判定提示词",
    "publisher": "出版社",
    "grade_id": "年级外键",
    "textbook_id": "教材外键",
    "parent_id": "父节点外键",
    "short_name": "学校简称",
    "region": "地区",
    "region_id": "行政区划外键",
    "exam_type": "考试类型",
    "exam_type_id": "考试类型外键",
    "exam_subject": "试卷主体",
    "exam_id": "试卷外键",
    "month": "月份",
    "year": "年份",
    "chapter_id": "章节外键",
    "school_id": "学校外键",
    "exam_direction_id": "考向外键",
    "knowledge_point_id": "知识点外键",
    "source_id": "题目来源外键",
    "question_no": "题号",
    "score": "分值",
    "solution_id": "解析外键",
    "thought_id": "学科思想外键",
    "method_id": "解题方法外键",
    "competency_id": "核心素养外键",
}
TABLE_FIELD_LABELS: dict[tuple[str, str], str] = {
    ("exams", "exam_subject"): "试卷主体（联考/考区/学校）",
    ("dim_exam_directions", "description"): "考向说明",
    ("dim_regions", "name"): "行政区划名称",
    ("dim_regions", "code"): "国标代码（GB/T 2260）",
    ("dim_regions", "level"): "层级（1省2市）",
    ("dim_regions", "parent_id"): "父级区划外键",
}
STAGE_COMMENT = "所属学段（小学/初中/高中/通用）"
# 表改名后仍带着旧表口径的批注：这些格子按 schema 的 [字段注释] 重写正文，其余批注原样保留
COMMENT_TEXT_SYNC: frozenset[tuple[str, str]] = frozenset(
    {
        ("exams", "code"),
        ("exams", "year"),
        ("question_exams", "question_no"),
        ("question_exams", "score"),
    }
)

SKIP_FIELD = re.compile(r"^(PRIMARY KEY|UNIQUE|FOREIGN KEY|REFERENCES|CHECK|CONSTRAINT)\b", re.I)
COLUMN_DEF = re.compile(r"^([a-z_][a-z0-9_]*)\s+(INTEGER|TEXT|REAL|BLOB|NUMERIC)\b")


class ExportError(RuntimeError):
    pass


def _column_letter(index: int) -> str:
    return chr(ord("A") + index)


def _column_index(letter: str) -> int:
    return ord(letter) - ord("A")


def _ref_row(ref: str) -> int:
    return int(re.match(r"[A-Z]+(\d+)$", ref).group(1))  # type: ignore[union-attr]


def _ref_col(ref: str) -> int:
    return _column_index(re.match(r"([A-Z]+)", ref).group(1))  # type: ignore[union-attr]


def parse_schema(path: Path) -> dict[str, dict]:
    """DDL → {表名: {comment, fields:[{name, comment}]}}，只认 [功能注释] / [字段注释]。"""
    tables: dict[str, dict] = {}
    pending_feature: str | None = None
    pending_field: str | None = None
    current: dict | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        feature = re.match(r"--\s*\[功能注释\]\s*(.+)$", line)
        if feature:
            pending_feature = feature.group(1).strip()
            continue
        field = re.match(r"--\s*\[字段注释\]\s*(.+)$", line)
        if field:
            pending_field = field.group(1).strip()
            continue
        create = re.match(r"CREATE TABLE (\w+)\s*\(", line)
        if create:
            current = {"comment": pending_feature or "", "fields": []}
            tables[create.group(1)] = current
            pending_feature = None
            pending_field = None
            continue
        if current is None:
            continue
        if line.startswith(")"):
            current = None
            pending_field = None
            continue
        if not line or line.startswith("--") or SKIP_FIELD.match(line):
            continue
        column = COLUMN_DEF.match(line)
        if column:
            current["fields"].append({"name": column.group(1), "comment": pending_field or ""})
            pending_field = None
    return tables


def _shared_strings(xml: str) -> list[str]:
    entries = re.findall(r"<si>(.*?)</si>", xml, re.S)
    return [
        unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", entry, re.S)))
        for entry in entries
    ]


def _cell_texts(sheet_xml: str, strings: list[str]) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for row in re.finditer(r"<row\b[^>]*\br=\"(\d+)\"[^>]*>(.*?)</row>", sheet_xml, re.S):
        number = int(row.group(1))
        cells: dict[str, str] = {}
        for cell in re.finditer(r"<c\b([^>]*)>(.*?)</c>", row.group(2), re.S):
            attrs, body = cell.group(1), cell.group(2)
            ref = re.search(r'\br="([A-Z]+\d+)"', attrs)
            value = re.search(r"<v>(.*?)</v>", body, re.S)
            if ref is None or value is None:
                continue
            text = value.group(1)
            if 't="s"' in attrs:
                text = strings[int(text)]
            cells[re.match(r"([A-Z]+)", ref.group(1)).group(1)] = text  # type: ignore[union-attr]
        out[number] = cells
    return out


def _cell_styles(sheet_xml: str) -> dict[str, str]:
    styles: dict[str, str] = {}
    for attrs in re.findall(r"<c\b([^>]*?)(?:/>|>)", sheet_xml):
        ref = re.search(r'\br="([A-Z]+\d+)"', attrs)
        style = re.search(r'\bs="(\d+)"', attrs)
        if ref and style:
            styles[ref.group(1)] = style.group(1)
    return styles


def _layout_rows(schema: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []
    number = 0
    for category, names in TABLE_GROUPS:
        for first, name in enumerate(names):
            number += 1
            if name not in schema:
                raise ExportError(f"schema 缺表：{name}")
            fields = schema[name]["fields"]
            if len(fields) > MAX_FIELDS:
                raise ExportError(f"{name} 字段数 {len(fields)} 超过 {MAX_FIELDS} 列")
            rows.append(
                {
                    "row": number + 1,
                    "index": number,
                    "category": category if first == 0 else None,
                    "name": name,
                    "comment": schema[name]["comment"],
                    "fields": fields,
                }
            )
    extra = sorted(set(schema) - {row["name"] for row in rows})
    if extra:
        raise ExportError("schema 多出未登记的表：" + "、".join(extra))
    return rows


def _field_label(table: str, field: str) -> str:
    override = TABLE_FIELD_LABELS.get((table, field))
    if override:
        return override
    label = FIELD_LABELS.get(field)
    if not label:
        raise ExportError(f"缺字段中文标签：{table}.{field}")
    return label


def _cell(ref: str, style: int, text: str | None, strings: list[str], index: dict[str, int]) -> str:
    if text is None:
        return f'<c r="{ref}" s="{style}"/>'
    if text not in index:
        index[text] = len(strings)
        strings.append(text)
    return f'<c r="{ref}" s="{style}" t="s"><v>{index[text]}</v></c>'


def _render_sheet_data(
    rows: list[dict],
    strings: list[str],
    index: dict[str, int],
    old_styles: dict[str, str],
) -> str:
    def style_of(letter: str, old_row: int | None, default: int) -> int:
        ref = f"{letter}{old_row}" if old_row is not None else ""
        return int(old_styles[ref]) if ref in old_styles else default

    out: list[str] = []
    header = "".join(
        _cell(
            f"{_column_letter(col)}1",
            style_of(_column_letter(col), 1, 8 if col == 0 else 1),
            text,
            strings,
            index,
        )
        for col, text in enumerate(HEADERS)
    )
    out.append(
        '<row r="1" spans="1:14" ht="26.1" customHeight="1" x14ac:dyDescent="0.15">'
        + header
        + "</row>"
    )
    for row in rows:
        number = row["row"]
        old_row = row.get("old_row")
        height = ROW_HEIGHT_OVERRIDES.get(number, ROW_HEIGHT)
        cells = [
            # A 列竖排分类标签：锚点格居中竖排(样式10)，合并区身体格竖排(样式11)
            _cell(
                f"A{number}",
                10 if row["category"] else 11,
                row["category"],
                strings,
                index,
            ),
            _cell(
                f"B{number}", style_of("B", old_row, 2),
                f"表{row['index']}", strings, index,
            ),
            _cell(
                f"C{number}", style_of("C", old_row, 3),
                row["name"] + "\r\n" + TABLE_LABELS[row["name"]], strings, index,
            ),
            _cell(
                f"D{number}", style_of("D", old_row, 3),
                row["comment"], strings, index,
            ),
        ]
        for offset in range(MAX_FIELDS):
            column = FIRST_FIELD_COL + offset
            ref = f"{_column_letter(column)}{number}"
            if offset < len(row["fields"]):
                field = row["fields"][offset]
                text = field["name"] + "\r\n" + _field_label(row["name"], field["name"])
            else:
                text = None
            default_style = 4 if row["name"] == "dict_difficulties" and offset in (5, 6) else 3
            cells.append(
                _cell(
                    ref,
                    style_of(_column_letter(column), old_row, default_style),
                    text,
                    strings,
                    index,
                )
            )
        out.append(
            f'<row r="{number}" spans="1:14" ht="{height}" customHeight="1" '
            'x14ac:dyDescent="0.15">' + "".join(cells) + "</row>"
        )
    return "".join(out)


def _check_layout(
    sheet_xml: str,
    *,
    merges: tuple[str, ...] = MERGES,
    last_row: int = NEW_LAST_ROW,
    overrides: dict[int, str] = ROW_HEIGHT_OVERRIDES,
) -> None:
    cols = {
        (int(minimum), int(maximum)): (width, style or None)
        for minimum, maximum, width, style in re.findall(
            r'<col min="(\d+)" max="(\d+)" width="([\d.]+)"(?: style="(\d+)")? customWidth="1"/>',
            sheet_xml,
        )
    }
    expected = {(minimum, maximum): (width, style) for minimum, maximum, width, style in COLUMN_WIDTHS}
    if cols != expected:
        raise ExportError(f"列宽与硬编码版式不一致：\n实际 {cols}\n期望 {expected}")
    actual_merges = set(re.findall(r'<mergeCell ref="([^"]+)"/>', sheet_xml))
    if actual_merges != set(merges):
        raise ExportError(f"合并单元格与硬编码版式不一致：实际 {sorted(actual_merges)}")
    heights = {
        int(number): height
        for number, height in re.findall(r'<row r="(\d+)"[^>]*\bht="([\d.]+)"', sheet_xml)
    }
    expected_heights = {1: HEADER_HEIGHT}
    expected_heights.update({row: ROW_HEIGHT for row in range(2, last_row + 1)})
    expected_heights.update({row: height for row, height in overrides.items() if row <= last_row})
    if {key: value for key, value in heights.items() if key <= last_row} != expected_heights:
        raise ExportError(f"行高与硬编码版式不一致：实际 {heights}")


def _rewrite_merges(sheet_xml: str, merges: tuple[str, ...]) -> str:
    block = re.search(r"<mergeCells\b[^>]*>.*?</mergeCells>", sheet_xml, re.S)
    if block is None:
        raise ExportError("工作簿缺少合并单元格声明")
    body = "".join(f'<mergeCell ref="{ref}"/>' for ref in merges)
    new_block = f'<mergeCells count="{len(merges)}">{body}</mergeCells>'
    return sheet_xml[: block.start()] + new_block + sheet_xml[block.end():]


def _rewrite_dimension(sheet_xml: str, last_row: int) -> str:
    pattern = re.compile(r'<dimension ref="([A-Z]+)1:([A-Z]+)\d+"/>')
    if not pattern.search(sheet_xml):
        raise ExportError("工作簿缺少 dimension 声明")
    return pattern.sub(
        lambda match: f'<dimension ref="{match.group(1)}1:{match.group(2)}{last_row}"/>',
        sheet_xml,
        count=1,
    )


def _update_shared(xml: str, strings: list[str], sheet_refs: int) -> str:
    head = re.search(r"<sst\b[^>]*>", xml).group(0)  # type: ignore[union-attr]
    body = "".join(f"<si><t>{escape(text)}</t></si>" for text in strings)
    new_head = re.sub(r'\bcount="\d+"', f'count="{sheet_refs}"', head)
    new_head = re.sub(r'\buniqueCount="\d+"', f'uniqueCount="{len(strings)}"', new_head)
    return xml[: xml.index(head)] + new_head + body + "</sst>"


STRING_CELL = re.compile(r'(<c\b[^>]*\bt="s"[^>]*>\s*<v>)(\d+)(</v></c>)')


def _compact_strings(
    sheets: tuple[str, ...], strings: list[str]
) -> tuple[tuple[str, ...], list[str]]:
    """按单元格实际引用重排共享字符串，把已删表留下的孤儿文本彻底剔除。"""
    order: dict[int, int] = {}
    kept: list[str] = []

    def swap(match: re.Match[str]) -> str:
        old = int(match.group(2))
        if old not in order:
            order[old] = len(kept)
            kept.append(strings[old])
        return f"{match.group(1)}{order[old]}{match.group(3)}"

    return tuple(STRING_CELL.sub(swap, sheet) for sheet in sheets), kept



def _comment_plan(
    rows: list[dict],
    old_cells: dict[int, dict[str, str]],
    comments_xml: str,
) -> tuple[list[tuple[str, str, int]], str]:
    """返回 [(新 ref, 批注 XML 块, 旧 shape 序号)] 与原 XML 的头部/尾部。"""
    blocks = re.findall(r"<comment\b.*?</comment>", comments_xml, re.S)
    by_cell: dict[tuple[int, str], int] = {}
    for index, block in enumerate(blocks):
        ref = re.search(r'\bref="([A-Z]+\d+)"', block).group(1)  # type: ignore[union-attr]
        by_cell[(_ref_row(ref), re.match(r"[A-Z]+", ref).group(0))] = index  # type: ignore[union-attr]
    plan: list[tuple[str, str, int]] = []
    for row in rows:
        number = row.get("old_row")
        if number is None:
            continue
        old_fields: dict[str, str] = {}
        for column in range(FIRST_FIELD_COL, FIRST_FIELD_COL + MAX_FIELDS):
            text = old_cells.get(number, {}).get(_column_letter(column))
            if text:
                old_fields[text.splitlines()[0]] = _column_letter(column)
        for offset, field in enumerate(row["fields"]):
            ref = f"{_column_letter(FIRST_FIELD_COL + offset)}{row['row']}"
            source = by_cell.get((number, old_fields.get(field["name"], "")))
            block = blocks[source] if source is not None else None
            if block is None and field["name"] == "stage":
                source = by_cell.get((number, old_fields.get("grade_id", "")))
                if source is not None:
                    block = re.sub(
                        r"<t>.*?</t>", "<t>" + escape(STAGE_COMMENT) + "</t>",
                        blocks[source], count=1, flags=re.S,
                    )
            if block is None:
                continue
            if (row["name"], field["name"]) in COMMENT_TEXT_SYNC and field["comment"]:
                block = re.sub(
                    r"<t(?:\s[^>]*)?>.*?</t>",
                    "<t>" + escape(field["comment"]) + "</t>",
                    block, count=1, flags=re.S,
                )
            block = re.sub(r'\bref="[A-Z]+\d+"', f'ref="{ref}"', block, count=1)
            plan.append((ref, block, source if source is not None else -1))
    head = comments_xml[: comments_xml.index("<commentList>") + len("<commentList>")]
    tail = comments_xml[comments_xml.index("</commentList>"):]
    return plan, head + "".join(block for _, block, _ in plan) + tail


def _update_vml(vml: str, plan: list[tuple[str, str, int]], old_comments: int) -> str:
    shapes = re.findall(r"<v:shape\b.*?</v:shape>", vml, re.S)
    if len(shapes) != old_comments:
        # 批注与形状按顺序一一配对，数量不等说明文件已被外部改动，不能盲改
        raise ExportError(f"VML 形状数 {len(shapes)} 与旧批注数 {old_comments} 不一致")
    first = re.search(r"<v:shape[\s>]", vml).start()
    last = vml.rindex("</v:shape>") + len("</v:shape>")
    built: list[str] = []
    for ref, _block, source in plan:
        if source < 0 or source >= len(shapes):
            raise ExportError(f"批注 {ref} 缺少可复用的批注形状")
        shape = shapes[source]
        shape = re.sub(r"<x:Row>\d+</x:Row>", f"<x:Row>{_ref_row(ref) - 1}</x:Row>", shape, count=1)
        shape = re.sub(
            r"<x:Column>\d+</x:Column>", f"<x:Column>{_ref_col(ref)}</x:Column>", shape, count=1
        )
        built.append(shape)
    return vml[:first] + "".join(built) + vml[last:]


def _rewrite(path: Path, replacements: dict[str, bytes]) -> None:
    source = zipfile.ZipFile(path, "r")
    infos = source.infolist()
    payload = {info.filename: source.read(info.filename) for info in infos}
    source.close()
    payload.update(replacements)
    temp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as target:
        for info in infos:
            target.writestr(info, payload[info.filename])
    temp.replace(path)


def export(workbook: Path, schema_path: Path, *, dry_run: bool = False) -> dict:
    schema = parse_schema(schema_path)
    rows = _layout_rows(schema)
    with zipfile.ZipFile(workbook, "r") as archive:
        sheet_xml = archive.read(SHEET1).decode("utf-8")
        shared_xml = archive.read(SHARED).decode("utf-8")
        comments_xml = archive.read(COMMENTS1).decode("utf-8")
        vml = archive.read(VML1).decode("utf-8")
        sheet2_xml = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")

    actual_merges = set(re.findall(r'<mergeCell ref="([^"]+)"/>', sheet_xml))
    if actual_merges == set(MERGES):
        layout_merges, old_last_row = MERGES, NEW_LAST_ROW
        old_overrides = ROW_HEIGHT_OVERRIDES
    elif actual_merges == set(LEGACY_MERGES_V7):
        layout_merges, old_last_row = LEGACY_MERGES_V7, 36
        old_overrides = LEGACY_ROW_HEIGHT_OVERRIDES_V7
    elif actual_merges == set(LEGACY_MERGES_V6):
        layout_merges, old_last_row = LEGACY_MERGES_V6, 36
        old_overrides = LEGACY_ROW_HEIGHT_OVERRIDES
    elif actual_merges == set(LEGACY_MERGES_V5):
        layout_merges, old_last_row = LEGACY_MERGES_V5, 34
        old_overrides = LEGACY_ROW_HEIGHT_OVERRIDES
    elif actual_merges == set(LEGACY_MERGES_V4):
        layout_merges, old_last_row = LEGACY_MERGES_V4, 33
        old_overrides = LEGACY_ROW_HEIGHT_OVERRIDES
    elif actual_merges == set(LEGACY_MERGES_V3):
        layout_merges, old_last_row = LEGACY_MERGES_V3, 32
        old_overrides = LEGACY_ROW_HEIGHT_OVERRIDES
    else:
        raise ExportError(f"工作簿合并区不属于已知版式：{sorted(actual_merges)}")
    _check_layout(
        sheet_xml, merges=layout_merges, last_row=old_last_row, overrides=old_overrides
    )

    strings = _shared_strings(shared_xml)
    index = {text: position for position, text in enumerate(strings)}
    old_cells = _cell_texts(sheet_xml, strings)
    old_name_rows: dict[str, int] = {}
    for number, cells in old_cells.items():
        text = cells.get("C")
        if number >= 2 and text:
            old_name_rows[text.splitlines()[0]] = number
    known = {row["name"] for row in rows}
    orphaned = sorted(set(old_name_rows) - known)
    if orphaned:
        raise ExportError("工作簿仍有 schema 已删除的表：" + "、".join(orphaned))
    for row in rows:
        old_row = old_name_rows.get(row["name"])
        row["old_row"] = old_row
        if old_row is None:
            continue
        actual = old_cells[old_row].get("C")
        if actual is None or actual.splitlines()[0] != row["name"]:
            raise ExportError(f"第 {old_row} 行表名与版式不符：{actual!r}")

    data = _render_sheet_data(rows, strings, index, _cell_styles(sheet_xml))
    start = sheet_xml.index("<sheetData>") + len("<sheetData>")
    end = sheet_xml.index("</sheetData>")
    new_sheet = sheet_xml[:start] + data + sheet_xml[end:]
    new_sheet = _rewrite_merges(new_sheet, MERGES)
    new_sheet = _rewrite_dimension(new_sheet, rows[-1]["row"])
    (new_sheet, sheet2_xml), strings = _compact_strings((new_sheet, sheet2_xml), strings)
    plan, new_comments = _comment_plan(rows, old_cells, comments_xml)
    new_vml = _update_vml(vml, plan, len(re.findall(r"<comment\b", comments_xml)))
    refs = len(re.findall(r'<c\b[^>]*\bt="s"', new_sheet)) + len(
        re.findall(r'<c\b[^>]*\bt="s"', sheet2_xml)
    )
    new_shared = _update_shared(shared_xml, strings, refs)

    changes = [
        {
            "table": row["name"],
            "old": [
                old_cells[row["old_row"]][_column_letter(column)].splitlines()[0]
                for column in range(FIRST_FIELD_COL, FIRST_FIELD_COL + MAX_FIELDS)
                if row["old_row"] is not None
                and old_cells.get(row["old_row"], {}).get(_column_letter(column))
            ],
            "new": [field["name"] for field in row["fields"]],
        }
        for row in rows
    ]
    changed = [item for item in changes if item["old"] != item["new"]]
    if not dry_run:
        _rewrite(
            workbook,
            {
                SHEET1: new_sheet.encode("utf-8"),
                SHARED: new_shared.encode("utf-8"),
                COMMENTS1: new_comments.encode("utf-8"),
                VML1: new_vml.encode("utf-8"),
            },
        )
    return {
        "workbook": str(workbook),
        "tables": len(rows),
        "fields": sum(len(row["fields"]) for row in rows),
        "comments": len(plan),
        "changed": changed,
        "dry_run": dry_run,
    }


def verify(workbook: Path) -> None:
    with zipfile.ZipFile(workbook, "r") as archive:
        sheet_xml = archive.read(SHEET1).decode("utf-8")
        comments_xml = archive.read(COMMENTS1).decode("utf-8")
        vml = archive.read(VML1).decode("utf-8")
    _check_layout(sheet_xml)
    refs = set(re.findall(r'<comment\b[^>]*\bref="([A-Z]+\d+)"', comments_xml))
    shapes = {
        (_ref_row(ref), _ref_col(ref))
        for ref in refs
    }
    pairs = [
        (int(row) + 1, int(column))
        for row, column in re.findall(r"<x:Row>(\d+)</x:Row>\s*<x:Column>(\d+)</x:Column>", vml)
    ]
    if shapes != set(pairs):
        raise ExportError(f"批注与 VML 锚点不匹配：批注 {len(shapes)}，形状 {len(pairs)}")
    if len(pairs) != len(refs):
        raise ExportError(f"批注数量与形状数量不一致：{len(refs)} / {len(pairs)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="把 schema 文字同步进数据库表结构一览表")
    parser.add_argument("--workbook", type=Path, required=True, help="目标 xlsx 路径")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="schema.sql 路径")
    parser.add_argument("--dry-run", action="store_true", help="只打印将变化的表，不写文件")
    args = parser.parse_args(argv)
    if not args.workbook.is_file():
        print(f"找不到工作簿：{args.workbook}", file=sys.stderr)
        return 2
    result = export(args.workbook, args.schema, dry_run=args.dry_run)
    print(f"{'试运行' if result['dry_run'] else '已写入'}：{result['workbook']}")
    print(f"表 {result['tables']} 张，字段 {result['fields']} 个，批注 {result['comments']} 条")
    for item in result["changed"]:
        print(f"  {item['table']}: {'、'.join(item['old'])} → {'、'.join(item['new'])}")
    if not result["dry_run"]:
        verify(args.workbook)
        print("版式校验：列宽 / 行高 / 合并区域与硬编码常量一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
