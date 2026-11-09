"""自动发现 books/book_*.py 数据模块，汇总并校验教材册与章节树。"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

PACKAGE = __name__.rsplit(".", 1)[0]
MODULE_NAMES: tuple[str, ...] = tuple(
    sorted(path.stem for path in Path(__file__).parent.glob("book_*.py"))
)
MODULES = tuple(import_module(f"{PACKAGE}.{name}") for name in MODULE_NAMES)

BOOK_ROWS: tuple[tuple[int, str, str, int, str, int, int], ...] = tuple(
    module.BOOK_ROW for module in MODULES
)
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = tuple(
    row for module in MODULES for row in module.CHAPTER_ROWS
)
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = tuple(
    row for module in MODULES for row in module.KNOWLEDGE_ROWS
)


def validate_book_rows() -> None:
    book_ids: set[int] = set()
    book_codes: set[str] = set()
    book_names: set[tuple[int, str]] = set()
    for book_id, name, code, _sort, _publisher, subject_id, _grade in BOOK_ROWS:
        if book_id in book_ids:
            raise ValueError(f"教材册 ID 重复：{book_id}")
        if code in book_codes:
            raise ValueError(f"教材册编码重复：{code}")
        if (subject_id, name) in book_names:
            raise ValueError(f"同学科教材册重名：{subject_id}/{name}")
        book_ids.add(book_id)
        book_codes.add(code)
        book_names.add((subject_id, name))

    chapter_ids: set[int] = set()
    chapter_codes: set[str] = set()
    chapter_book: dict[int, int] = {}
    chapter_siblings: set[tuple[int, int, str]] = set()
    for chapter_id, name, code, _sort, textbook_id, parent_id in CHAPTER_ROWS:
        if chapter_id in chapter_ids:
            raise ValueError(f"章节 ID 重复：{chapter_id}")
        if code in chapter_codes:
            raise ValueError(f"章节编码重复：{code}")
        if textbook_id not in book_ids:
            raise ValueError(f"章节 {chapter_id} 挂到不存在的教材册 {textbook_id}")
        if parent_id is not None:
            parent_book = chapter_book.get(parent_id)
            if parent_book is None:
                raise ValueError(f"章节 {chapter_id} 的父章节 {parent_id} 尚未登记")
            if parent_book != textbook_id:
                raise ValueError(f"章节 {chapter_id} 与父章节不属于同一册教材")
        key = (textbook_id, parent_id or 0, name)
        if key in chapter_siblings:
            raise ValueError(f"同册同父章节重名：{textbook_id}/{parent_id}/{name}")
        chapter_ids.add(chapter_id)
        chapter_codes.add(code)
        chapter_book[chapter_id] = textbook_id
        chapter_siblings.add(key)


validate_book_rows()
