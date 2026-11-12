#!/usr/bin/env python3
"""字典反向固化：以当前活跃题库为唯一事实源，重写出厂种子模块。

只读 ``dict_*`` / ``dim_*`` 纯字典表；题目、解析、试卷等业务表一概不碰。
写回后由 ``tools/verify_dict_seeds.py`` 临时重建新库并逐表比对。

用法：
    .venv\\Scripts\\python.exe tools\\export_dict_seeds.py
    .venv\\Scripts\\python.exe tools\\export_dict_seeds.py --db data/banks/xxx.db
"""

from __future__ import annotations

import argparse
import ast
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bank_engine import paths  # noqa: E402

SEEDS = ROOT / "app" / "bank_engine" / "seeds"

STAGE_CONST = {
    "小学": "STAGE_PRIMARY",
    "初中": "STAGE_JUNIOR",
    "高中": "STAGE_SENIOR",
    "全学段": "STAGE_ALL",
}


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(conn: sqlite3.Connection, sql: str) -> list[tuple]:
    return [tuple(row) for row in conn.execute(sql)]


def _lit(value: object) -> str:
    if value is None:
        return "None"
    if isinstance(value, int):
        return str(value)
    return repr(str(value))


def _tuple_lit(row: tuple) -> str:
    return "(" + ", ".join(_lit(value) for value in row) + ")"


def _assignment_span(source: str, name: str) -> tuple[int, int]:
    for node in ast.parse(source).body:
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id == name and value is not None:
            return node.lineno, node.end_lineno or node.lineno
    raise KeyError(f"找不到赋值：{name}")


def _replace_block(path: Path, name: str, lines_of: list[str]) -> int:
    source = path.read_text(encoding="utf-8")
    start, end = _assignment_span(source, name)
    lines = source.splitlines()
    header = lines[start - 1]
    if not header.rstrip().endswith("("):
        raise ValueError(f"{path.name} 的 {name} 不是元组块")
    lines[start - 1:end] = [header, *lines_of, ")"]
    path.write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )
    return len(lines_of)


def _replace_row_line(path: Path, row_id: int, body: str) -> None:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    pattern = re.compile(rf"^(\s*)\(\s*{row_id}\s*,")
    hits = [index for index, line in enumerate(lines) if pattern.match(line)]
    if len(hits) != 1:
        raise ValueError(f"{path.name} 中 id={row_id} 命中 {len(hits)} 行")
    indent = pattern.match(lines[hits[0]]).group(1)
    lines[hits[0]] = f"{indent}({body}),"
    path.write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )


def export_regions(rows: list[tuple]) -> int:
    provinces = [row for row in rows if row[3] == 1]
    blocks: list[str] = []
    for province in provinces:
        children = [
            row for row in rows
            if row[3] == 2 and row[4] == province[0]
            and str(row[2]).endswith("00")
        ]
        if not children:
            blocks.append(
                f"    ({_lit(province[1])}, {_lit(province[2])}, ()),"
            )
            continue
        blocks.append(f"    ({_lit(province[1])}, {_lit(province[2])}, (")
        for index in range(0, len(children), 2):
            pair = ", ".join(
                f"({_lit(row[1])}, {_lit(row[2])})"
                for row in children[index:index + 2]
            )
            blocks.append(f"        {pair},")
        blocks.append("    )),")
    index = _replace_block(SEEDS / "region_seed.py", "PROVINCE_TREE", blocks)

    province_name = {row[0]: row[1] for row in provinces}
    extras = [
        row for row in rows
        if row[3] == 2 and not str(row[2]).endswith("00")
    ]
    extra_blocks = [
        f"    ({_lit(province_name[row[4]])}, {_lit(row[1])}, "
        f"{_lit(row[2])}, {row[5]}),"
        for row in extras
    ]
    _replace_block(SEEDS / "region_seed.py", "EXTRA_CITIES", extra_blocks)
    return index


def export_schools(rows: list[tuple]) -> int:
    body = [f"    {_tuple_lit(row)}," for row in rows]
    header = '''"""学校字典出厂基线：id / name / short_name / code / region / textbook_id。

由 ``tools/export_dict_seeds.py`` 从活跃库反向固化（2026-11-12），
老师在前端精修过的简称以此为准；请勿再手工改写。
"""

from __future__ import annotations

SCHOOL_ROWS: tuple[tuple[int, str, str, str, str, int | None], ...] = (
'''
    (SEEDS / "school_seed.py").write_text(
        header + "\n".join(body) + "\n)\n", encoding="utf-8", newline="\n"
    )
    return len(body)


def export_exam_types(rows: list[tuple]) -> int:
    lines = [f"    {_tuple_lit(row)}," for row in rows]
    return _replace_block(SEEDS / "exam_seed.py", "EXAM_TYPE_ROWS", lines)


def export_methods(rows: list[tuple]) -> int:
    lines = []
    for row_id, code, name, sort_order, subject_id, stage in rows:
        subject = "SUBJECT_MATH_ID" if subject_id == 2 else str(subject_id)
        level = STAGE_CONST.get(stage, _lit(stage))
        lines.append(
            f"    ({row_id}, {_lit(code)}, {_lit(name)}, {sort_order}, "
            f"{subject}, {level}),"
        )
    return _replace_block(SEEDS / "curriculum.py", "SOLUTION_METHOD_ROWS", lines)


def export_thoughts(rows: list[tuple]) -> int:
    lines = [f"    {_tuple_lit(row)}," for row in rows]
    return _replace_block(
        SEEDS / "curriculum_standards.py", "SUBJECT_THOUGHT_ROWS", lines
    )


def export_textbook_snapshot(versions: list[tuple], books: list[tuple]) -> int:
    def pack(rows: list[tuple]) -> str:
        chunks = []
        for index in range(0, len(rows), 2):
            chunks.append(
                "    " + ", ".join(_tuple_lit(row) for row in rows[index:index + 2]) + ","
            )
        return "\n".join(chunks)

    text = (
        '"""教材版本与册次出厂快照：由 tools/export_dict_seeds.py 从活跃库固化。\n\n'
        "2026-11-12 固化。库里沿用了历史签发顺序（自动版本号 8 号位已删除、\n"
        "全国目录锚点册按当年目录落号），spec 重新推演无法复刻该编号，\n"
        "故直接以本快照为出厂基线。\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "SNAPSHOT_VERSION_ROWS: tuple[tuple[int, str, str, int, str, int], ...] = (\n"
        + pack(versions) + "\n)\n\n"
        "SNAPSHOT_BOOK_ROWS: tuple[\n"
        "    tuple[int, str, str, int, str, int, int, int, str], ...\n"
        "] = (\n"
        + pack(books) + "\n)\n"
    )
    (SEEDS / "textbook_snapshot.py").write_text(
        text, encoding="utf-8", newline="\n"
    )
    return len(versions) + len(books)


def main() -> int:
    parser = argparse.ArgumentParser(description="从活跃库反向固化字典种子")
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args()
    db_path = args.db or paths.engine_db_path()
    if not Path(db_path).is_file():
        raise SystemExit(f"库不存在：{db_path}")
    conn = _connect(Path(db_path))
    try:
        regions = _rows(
            conn,
            "SELECT id, name, code, level, parent_id, sort_order "
            "FROM dim_regions ORDER BY id",
        )
        schools = _rows(
            conn,
            "SELECT id, name, short_name, code, region, textbook_id "
            "FROM dim_schools ORDER BY id",
        )
        exam_types = _rows(
            conn,
            "SELECT id, name, code, sort_order FROM dict_exam_types ORDER BY id",
        )
        methods = _rows(
            conn,
            "SELECT id, code, name, sort_order, subject_id, stage "
            "FROM dict_solution_methods ORDER BY id",
        )
        thoughts = _rows(
            conn,
            "SELECT id, code, name, sort_order, subject_id, stage "
            "FROM dict_subject_thoughts ORDER BY id",
        )
        competencies = _rows(
            conn,
            "SELECT id, code, name, sort_order, subject_id, stage "
            "FROM dict_core_competencies ORDER BY id",
        )
        versions = _rows(
            conn,
            "SELECT id, name, code, sort_order, publisher, subject_id "
            "FROM dim_textbook_versions ORDER BY id",
        )
        books = _rows(
            conn,
            "SELECT id, name, code, sort_order, publisher, subject_id, "
            "grade_id, version_id, volume_name FROM dim_textbooks ORDER BY id",
        )
        knowledge = _rows(
            conn,
            "SELECT id, code, name, sort_order, subject_id, parent_id "
            "FROM dim_knowledge_points WHERE id = 960028",
        )
        chapter = _rows(
            conn,
            "SELECT id, name, code, sort_order, textbook_id, parent_id "
            "FROM dim_textbook_chapters WHERE id = 930027",
        )
    finally:
        conn.close()

    from app.bank_engine.seeds import curriculum_standards

    if list(curriculum_standards.CORE_COMPETENCY_ROWS) != competencies:
        raise SystemExit("核心素养字典与种子不一致：请先人工核对 curriculum_standards")

    counts = {
        "PROVINCE_TREE": export_regions(regions),
        "SCHOOL_ROWS": export_schools(schools),
        "EXAM_TYPE_ROWS": export_exam_types(exam_types),
        "SOLUTION_METHOD_ROWS": export_methods(methods),
        "SUBJECT_THOUGHT_ROWS": export_thoughts(thoughts),
        "textbook_snapshot": export_textbook_snapshot(versions, books),
    }
    if knowledge:
        row = knowledge[0]
        body = ", ".join(
            [str(row[0]), _lit(row[1]), _lit(row[2]), str(row[3]), str(row[4]),
             _lit(row[5])]
        )
        _replace_row_line(
            SEEDS / "math_required1" / "knowledge.py", int(row[0]), body
        )
    if chapter:
        row = chapter[0]
        body = ", ".join(
            [str(row[0]), _lit(row[1]), _lit(row[2]), str(row[3]), str(row[4]),
             _lit(row[5])]
        )
        _replace_row_line(
            SEEDS / "migrated_textbook_seed.py", int(row[0]), body
        )
    for table, size in counts.items():
        print(f"{table}: {size}")
    print(f"db: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
