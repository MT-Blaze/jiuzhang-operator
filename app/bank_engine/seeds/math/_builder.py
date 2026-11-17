"""按册生成高中数学「章 → 节 → 知识点 → 考向」与两张桥表。

每个数据册只声明教研结构，ID、code、桥表与排序全部由本模块派生：
知识点号段由 ``knowledge_base`` 起顺序占用，考向号段由 ``exam_base`` 起顺序占用；
两个号段都按册隔离，越界直接报错，避免与既有种子撞号。
"""

from __future__ import annotations

from dataclasses import dataclass

SUBJECT_ID = 2
KNOWLEDGE_CAPACITY = 1000
EXAM_CAPACITY = 800


@dataclass(frozen=True)
class BookSpec:
    code: str
    book_id: int
    knowledge_base: int
    exam_base: int
    chapters: tuple[tuple[str, int, tuple[tuple[int, str, tuple[tuple[str, tuple[str, ...]], ...]], ...]], ...]


def build(spec: BookSpec) -> tuple[tuple[tuple, ...], ...]:
    """返回知识点、考向、知识点-考向、节-知识点四张表的行。"""
    knowledge_rows: list[tuple] = []
    exam_rows: list[tuple] = []
    knowledge_exam_rows: list[tuple[int, int, int]] = []
    chapter_rows: list[tuple[int, int, int]] = []

    kp_seq = 0
    exam_seq = 0
    covered_chapters: set[int] = set()

    for chapter_index, (chapter_title, headline_id, sections) in enumerate(
        spec.chapters, start=1
    ):
        chapter_point = spec.knowledge_base + kp_seq
        knowledge_rows.append(_knowledge_row(spec, kp_seq, chapter_title, chapter_index, headline_id))
        kp_seq += 1

        for section_index, (chapter_id, section_title, points) in enumerate(sections, start=1):
            if chapter_id in covered_chapters:
                raise ValueError(f"{spec.code} 教材节重复：{chapter_id}")
            if not points:
                raise ValueError(f"{spec.code}/{section_title} 没有知识点")
            covered_chapters.add(chapter_id)

            section_point = spec.knowledge_base + kp_seq
            knowledge_rows.append(
                _knowledge_row(spec, kp_seq, section_title, section_index, chapter_point)
            )
            kp_seq += 1

            bridge_order = 0
            for point_index, (point_name, exams) in enumerate(points, start=1):
                if not exams:
                    raise ValueError(f"{spec.code}/{section_title}/{point_name} 没有考向")
                point_id = spec.knowledge_base + kp_seq
                knowledge_rows.append(
                    _knowledge_row(spec, kp_seq, point_name, point_index, section_point)
                )
                kp_seq += 1
                chapter_rows.append((chapter_id, point_id, bridge_order))
                bridge_order += 1

                for exam_name in exams:
                    direction_id = spec.exam_base + exam_seq
                    exam_rows.append((
                        direction_id,
                        exam_name,
                        f"ED_MATH_{spec.code}_{exam_seq + 1:03d}",
                        exam_seq + 1,
                        SUBJECT_ID,
                        chapter_id,
                        None,
                    ))
                    knowledge_exam_rows.append((point_id, direction_id, 0))
                    exam_seq += 1

    if kp_seq > KNOWLEDGE_CAPACITY:
        raise ValueError(f"{spec.code} 知识点超出号段容量：{kp_seq}")
    if exam_seq > EXAM_CAPACITY:
        raise ValueError(f"{spec.code} 考向超出号段容量：{exam_seq}")
    return (
        tuple(knowledge_rows),
        tuple(exam_rows),
        tuple(knowledge_exam_rows),
        tuple(chapter_rows),
    )


def _knowledge_row(
    spec: BookSpec, offset: int, name: str, sort_order: int, parent_id: int | None
) -> tuple[int, str, str, int, int, int | None]:
    return (
        spec.knowledge_base + offset,
        f"KP_MATH_{spec.code}_{offset + 1:03d}",
        name,
        sort_order,
        SUBJECT_ID,
        parent_id,
    )
