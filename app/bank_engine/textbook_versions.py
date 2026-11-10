"""教材版本维度：版本名与册次名解耦的唯一口径。

版本（人教A版 / 统编版（2019）…）是独立一等实体，活在 dim_textbook_versions；
册次（必修一 / 七年级上册）活在 dim_textbooks.volume_name。
新建库的 seeding 与老库的 migrate_v9 共用本模块，保证两边切出同一套版本行。
"""

from __future__ import annotations

from typing import Any, Iterable

# 前缀顺序即匹配优先级：长前缀在前，避免「人教A版」吞掉「人教A版·」。
VERSION_PREFIXES: tuple[tuple[str, str, str], ...] = (
    ("人教A版·", "人教A版", "rja"),
    ("人教B版·", "人教B版", "rjb"),
    ("人教A版", "人教A版", "rja"),
    ("人教B版", "人教B版", "rjb"),
    ("统编版（2019）", "统编版（2019）", "tb2019"),
    ("人教版（2019）", "人教版（2019）", "rj2019"),
    ("人教版PEP", "人教版PEP", "rjpep"),
    ("统编版", "统编版", "tb"),
    ("人教版", "人教版", "rj"),
    ("北师大版", "北师大版", "bsd"),
    ("苏教版", "苏教版", "sj"),
    ("沪教版", "沪教版", "hj"),
    ("湘教版", "湘教版", "xj"),
    ("外研版", "外研版", "wy"),
    ("教科版", "教科版", "jk"),
    ("岳麓版", "岳麓版", "yl"),
)

FALLBACK_NAME = "其他版本"
FALLBACK_SLUG = "other"

BookRow = tuple[Any, ...]


def split_title(title: str) -> tuple[str, str, str]:
    """完整书名 → (版本名, 版本编码片段, 纯册次名)。识别不了前缀时归入「其他版本」。"""
    text = str(title or "").strip()
    for prefix, version, slug in VERSION_PREFIXES:
        if text.startswith(prefix):
            volume = text[len(prefix):].strip(" ·　")
            return version, slug, volume or text
    return FALLBACK_NAME, FALLBACK_SLUG, text


def version_code(slug: str, subject_id: int) -> str:
    """版本编码按学科隔离：dim_textbooks 的 code 全局唯一，版本表同理。"""
    return f"tv_{slug}_{int(subject_id)}"


def build_version_rows(
    book_rows: Iterable[BookRow],
) -> tuple[tuple[tuple[Any, ...], ...], dict[int, tuple[int, str]]]:
    """按 (学科, 版本) 归组版本行，并给出每册的 (version_id, volume_name)。

    book_rows 行序：id, name, code, sort_order, publisher, subject_id, grade_id。
    版本 id 按 (subject_id, 首册 sort_order, 首册 id) 递增签发，新建库与迁移结果一致。
    """
    groups: dict[tuple[int, str], dict[str, Any]] = {}
    order: list[tuple[int, str]] = []
    for row in sorted(book_rows, key=lambda item: (int(item[5]), int(item[3]), int(item[0]))):
        book_id = int(row[0])
        subject_id = int(row[5])
        version, slug, volume = split_title(str(row[1]))
        key = (subject_id, version)
        if key not in groups:
            groups[key] = {
                "slug": slug,
                "publisher": row[4],
                "sort_order": len(order) + 1,
                "books": [],
            }
            order.append(key)
        groups[key]["books"].append((book_id, volume))

    version_rows: list[tuple[Any, ...]] = []
    mapping: dict[int, tuple[int, str]] = {}
    for index, key in enumerate(order, start=1):
        subject_id, version = key
        meta = groups[key]
        version_rows.append((
            index,
            version,
            version_code(str(meta["slug"]), subject_id),
            int(meta["sort_order"]),
            meta["publisher"],
            subject_id,
        ))
        for book_id, volume in meta["books"]:
            mapping[book_id] = (index, volume)
    return tuple(version_rows), mapping
