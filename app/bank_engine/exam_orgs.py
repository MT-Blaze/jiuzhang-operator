"""考试主体：按名字懒创建 ``dict_exam_orgs`` 行，并推断主体类型。

不预建 347 所学校：老师第一次填到哪个主体，库里才落哪一行；
主体若是真实学校，顺手回挂 ``dim_schools`` 外键。
"""

from __future__ import annotations

import sqlite3

ORG_TYPES = ("学校", "联考联盟", "地市级", "省级", "国家级", "区县级", "其他")

_SCHOOL_HINTS = ("中学", "小学", "学校", "附中", "高中", "初中", "职高", "中专")


def infer_org_type(name: str) -> str:
    text = str(name or "").strip()
    if not text:
        return "其他"
    if "教育部" in text or text.startswith("全国"):
        return "国家级"
    if any(hint in text for hint in ("联盟", "联合体", "协作体", "共同体")):
        return "联考联盟"
    if "省" in text and any(hint in text for hint in ("教育厅", "考试院", "教科院", "教研室")):
        return "省级"
    if any(hint in text for hint in ("市教育局", "市考试院", "市教科院", "市教研室")):
        return "地市级"
    if any(hint in text for hint in ("区教育局", "县教育局", "区教研室", "县教研室")):
        return "区县级"
    if any(hint in text for hint in _SCHOOL_HINTS):
        return "学校"
    if "市" in text:
        return "地市级"
    return "其他"


def _school_id(conn: sqlite3.Connection, name: str, school_ids: tuple[int, ...]) -> int | None:
    for school_id in school_ids:
        row = conn.execute("SELECT id FROM dim_schools WHERE id = ?", (school_id,)).fetchone()
        if row is not None:
            return int(row[0])
    row = conn.execute(
        "SELECT id FROM dim_schools WHERE name = ? OR short_name = ? ORDER BY id LIMIT 1",
        (name, name),
    ).fetchone()
    return None if row is None else int(row[0])


def ensure_exam_org(
    conn: sqlite3.Connection,
    name: str | None,
    org_type: str | None = None,
    school_ids: tuple[int, ...] = (),
) -> int | None:
    text = str(name or "").strip()[:120]
    if not text:
        return None
    row = conn.execute("SELECT id FROM dict_exam_orgs WHERE name = ?", (text,)).fetchone()
    if row is not None:
        return int(row[0])
    kind = org_type if org_type in ORG_TYPES else infer_org_type(text)
    linked_school = _school_id(conn, text, school_ids) if kind == "学校" else None
    cursor = conn.execute(
        "INSERT INTO dict_exam_orgs (name, org_type, school_id) VALUES (?, ?, ?)",
        (text, kind, linked_school),
    )
    return int(cursor.lastrowid)


__all__ = ["ORG_TYPES", "ensure_exam_org", "infer_org_type"]
