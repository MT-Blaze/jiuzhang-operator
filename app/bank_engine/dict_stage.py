"""教研字典的学段口径：只有 小学 / 初中 / 高中 / 全学段 四个明码值。

空值不再兼容：跨学段通用条目写「全学段」，按学段检索时与具体学段并集返回。
"""

from __future__ import annotations

STAGE_VALUES: tuple[str, ...] = ("小学", "初中", "高中", "全学段")
STAGE_ALL = "全学段"
STAGE_HINT = "学段只能是：小学 / 初中 / 高中 / 全学段"


def clean_stage(raw: object, *, required: bool) -> str:
    """校验学段并返回明码值；非必填表遇到空值回落「全学段」。"""
    empty = raw is None or (isinstance(raw, str) and raw.strip() == "")
    if empty:
        if required:
            raise ValueError("必填字段不能为空：学段")
        return STAGE_ALL
    text = str(raw).strip()
    if text not in STAGE_VALUES:
        raise ValueError(STAGE_HINT)
    return text


def filter_pair(shared_stage: bool, column: str, value: object) -> tuple[str, tuple]:
    """跨学段通用字典按学段检索时，把「全学段」行一起带上。"""
    if shared_stage and column == "stage":
        return (column + " IN (?, ?)", (value, STAGE_ALL))
    return (column + " = ?", (value,))
