"""契约字段校验原语：题目契约与来源契约共用，只产出可读错误、不抛异常。"""

from __future__ import annotations

import re
from typing import Any, Iterable

MAX_ERRORS = 20


class ContractError(ValueError):
    """题目不符合契约；``errors`` 是逐条可读原因。"""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("题目不符合契约")


def text(value: Any, path: str, errors: list[str], *, minimum: int = 0,
         maximum: int | None = None, pattern: re.Pattern[str] | None = None) -> str | None:
    if not isinstance(value, str):
        errors.append(f"{path}: 必须是字符串")
        return None
    if len(value) < minimum:
        errors.append(f"{path}: 至少 {minimum} 个字符")
    if maximum is not None and len(value) > maximum:
        errors.append(f"{path}: 最多 {maximum} 个字符")
    if pattern is not None and not pattern.match(value):
        errors.append(f"{path}: 格式不合法（{value!r}）")
    return value


def integer(value: Any, path: str, errors: list[str], *, minimum: int | None = None,
            maximum: int | None = None) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{path}: 必须是整数")
        return None
    if minimum is not None and value < minimum:
        errors.append(f"{path}: 不得小于 {minimum}")
    if maximum is not None and value > maximum:
        errors.append(f"{path}: 不得大于 {maximum}")
    return value


def enum(value: Any, path: str, errors: list[str], allowed: tuple[str, ...]) -> str | None:
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{path}: 取值必须是 {'/'.join(allowed)} 之一")
        return None
    return value


def sequence(value: Any, path: str, errors: list[str], *, minimum: int | None = None,
             maximum: int | None = None) -> list[Any] | None:
    if not isinstance(value, list):
        errors.append(f"{path}: 必须是数组")
        return None
    if minimum is not None and len(value) < minimum:
        errors.append(f"{path}: 至少 {minimum} 项")
    if maximum is not None and len(value) > maximum:
        errors.append(f"{path}: 最多 {maximum} 项")
    return value


def mapping(value: Any, path: str, errors: list[str], allowed: set[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{path}: 必须是对象")
        return None
    for key in value:
        if key not in allowed:
            errors.append(f"{path}.{key}: 不允许的字段")
    return value


def unique(values: list[Any], path: str, errors: list[str]) -> None:
    seen: list[Any] = []
    for item in values:
        if item in seen:
            errors.append(f"{path}: 存在重复值 {item!r}")
            return
        seen.append(item)


def present(mapping: dict[str, Any], path: str, required: tuple[str, ...],
            errors: list[str]) -> None:
    for key in required:
        if key not in mapping:
            errors.append(f"{path}.{key}: 必填字段缺失")


__all__ = [
    "MAX_ERRORS", "ContractError", "enum", "integer", "mapping", "present",
    "sequence", "text", "unique",
]
