"""行政区划的落库、匹配与学校回填：只做单表读写与 Python 层字符串匹配。

匹配口径与 ``dim_schools.region`` 一致：省级核心名 + 地级核心名，如“黑龙江哈尔滨”。
匹配不到地级时退到省级；连省级都认不出才留空，绝不瞎猜。
"""

from __future__ import annotations

import sqlite3

from app.bank_engine.seeds.region_seed import REGION_ROWS

REGION_DDL = """
CREATE TABLE IF NOT EXISTS dim_regions (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    code       TEXT NOT NULL UNIQUE,
    level      INTEGER NOT NULL CHECK (level IN (1, 2)),
    parent_id  INTEGER REFERENCES dim_regions(id) ON DELETE RESTRICT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    CHECK ((level = 1 AND parent_id IS NULL) OR (level = 2 AND parent_id IS NOT NULL))
)
"""

_PROVINCES: tuple[tuple[int, str], ...] = tuple(
    (row[0], row[1]) for row in REGION_ROWS if row[3] == 1
)
_CHILDREN: dict[int, tuple[tuple[int, str], ...]] = {
    province_id: tuple(
        (row[0], row[1]) for row in REGION_ROWS if row[3] == 2 and row[4] == province_id
    )
    for province_id, _ in _PROVINCES
}
_SUFFIXES = ("特别行政区", "自治区", "自治州", "地区", "省", "市", "盟")


def _strip_suffix(text: str) -> str:
    for suffix in _SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            return text[: -len(suffix)]
    return text


def match_region_id(text: str | None) -> int | None:
    value = str(text or "").strip()
    if not value:
        return None
    if value in {name for _, name in _PROVINCES}:
        return next(pid for pid, name in _PROVINCES if name == value)
    province = max(
        ((pid, name) for pid, name in _PROVINCES if value.startswith(name)),
        key=lambda item: len(item[1]),
        default=None,
    )
    if province is not None:
        rest = _strip_suffix(value[len(province[1]):].strip())
        if not rest:
            return province[0]
        for city_id, city_name in _CHILDREN[province[0]]:
            if rest == city_name:
                return city_id
        for city_id, city_name in _CHILDREN[province[0]]:
            if rest.startswith(city_name) or city_name.startswith(rest):
                return city_id
        return province[0]
    bare = _strip_suffix(value)
    hits = [
        city_id
        for children in _CHILDREN.values()
        for city_id, city_name in children
        if city_name == bare
    ]
    return hits[0] if len(hits) == 1 else None


def ensure_regions(conn: sqlite3.Connection) -> int:
    conn.execute(REGION_DDL)
    count = int(conn.execute("SELECT COUNT(*) FROM dim_regions").fetchone()[0])
    if count == 0:
        conn.executemany(
            "INSERT INTO dim_regions (id, name, code, level, parent_id, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            REGION_ROWS,
        )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_regions_sibling_name "
        "ON dim_regions (COALESCE(parent_id, 0), name)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_dim_regions_parent ON dim_regions (parent_id)"
    )
    return int(conn.execute("SELECT COUNT(*) FROM dim_regions").fetchone()[0])


def backfill_schools(conn: sqlite3.Connection) -> dict[str, object]:
    """按学校现有 region 文本回填 region_id，返回总数 / 命中数 / 未识别地区。"""
    cache: dict[str, int | None] = {}
    total = 0
    filled = 0
    unmatched: set[str] = set()
    updates: list[tuple[int | None, int]] = []
    for school_id, region in conn.execute(
        "SELECT id, region FROM dim_schools ORDER BY id"
    ):
        total += 1
        text = str(region or "").strip()
        if text and text not in cache:
            cache[text] = match_region_id(text)
        region_id = cache.get(text)
        updates.append((region_id, int(school_id)))
        if region_id is not None:
            filled += 1
        elif text:
            unmatched.add(text)
    conn.executemany("UPDATE dim_schools SET region_id = ? WHERE id = ?", updates)
    return {
        "total": total,
        "filled": filled,
        "unmatched": sorted(unmatched),
    }


__all__ = ["REGION_DDL", "backfill_schools", "ensure_regions", "match_region_id"]
