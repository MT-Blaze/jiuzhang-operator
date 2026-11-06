"""重题池的源码回写：老师在新题源码区的编辑只改题面四件。

从 ``pending_pool.py`` 拆出来的独立舱位（单文件 800 行红线）：这一支只管
「池内文档里的题面字段怎么被安全改写」，裁决动作仍归 ``pending_pool``。
"""

from __future__ import annotations

import copy
import json
from typing import Any

from app.core import questions
from app.core.pending_db import PendingError, PendingNotFound, connect

_EDITABLE_FIELDS = ("type", "stem", "options", "answer", "solution")
_QUESTION_TYPES = ("single_choice", "multiple_choice", "fill_blank", "solution",
                   "proof", "unknown")
_OPTION_KEYS = "ABCDEFGH"
_MAX_STEM = 50000
_MAX_OPTION_CONTENT = 5000
_MAX_ANSWER_CONTENT = 20000
_MAX_FINAL = 2000


def _checked_text(value: Any, field: str, limit: int, *, empty: bool = True) -> str:
    if not isinstance(value, str):
        raise PendingError(f"{field} 必须是文本")
    if len(value) > limit:
        raise PendingError(f"{field} 过长（上限 {limit} 字）")
    if not empty and not value.strip():
        raise PendingError(f"{field} 不能为空")
    return value


def _checked_options(raw: Any, base_doc: dict[str, Any]) -> list[dict[str, Any]]:
    """源码里的选项 → 契约口径的选项；同键旧选项的配图引用原样保留。"""
    if not isinstance(raw, list):
        raise PendingError("options 必须是数组")
    if len(raw) > 12:
        raise PendingError("选项最多 12 项")
    old_images: dict[str, Any] = {}
    for item in base_doc.get("options") or []:
        if isinstance(item, dict) and item.get("key") and "image_ids" in item:
            old_images[str(item["key"])] = item["image_ids"]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise PendingError("每个选项必须是对象")
        key = str(item.get("key") or "")
        if len(key) != 1 or key not in _OPTION_KEYS:
            raise PendingError(f"选项标号不合法：{key or '（空）'}")
        if key in seen:
            raise PendingError(f"选项标号重复：{key}")
        seen.add(key)
        option = {
            "key": key,
            "content": _checked_text(item.get("content"), f"选项 {key}", _MAX_OPTION_CONTENT),
        }
        images = item.get("image_ids", old_images.get(key))
        if images is not None:
            if not isinstance(images, list) or len(images) > 4 \
                    or not all(isinstance(one, str) for one in images):
                raise PendingError(f"选项 {key} 的配图引用不合法")
            option["image_ids"] = list(dict.fromkeys(images))
        out.append(option)
    return out


def _checked_answer(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise PendingError("answer 必须是对象")
    kind = str(raw.get("kind") or "")
    if kind not in ("choice", "text", "expression", "proof", "unknown"):
        raise PendingError(f"答案形态不合法：{kind or '（空）'}")
    out: dict[str, Any] = {"kind": kind}
    keys = raw.get("choice_keys")
    if keys is not None:
        if not isinstance(keys, list) or not keys or len(keys) > 8:
            raise PendingError("choice_keys 必须是 1–8 个选项标号")
        cleaned: list[str] = []
        for key in keys:
            text = str(key)
            if len(text) != 1 or text not in _OPTION_KEYS:
                raise PendingError(f"答案标号不合法：{text or '（空）'}")
            if text not in cleaned:
                cleaned.append(text)
        out["choice_keys"] = cleaned
    if kind == "choice" and not out.get("choice_keys"):
        raise PendingError("选择题答案缺少 choice_keys")
    content = raw.get("content")
    if content is not None:
        out["content"] = _checked_text(content, "答案内容", _MAX_ANSWER_CONTENT)
    if kind in ("text", "expression", "proof") and "content" not in out:
        raise PendingError("文字/表达式答案缺少 content")
    final = raw.get("final")
    if final is not None:
        out["final"] = _checked_text(final, "答案短文本", _MAX_FINAL)
    return out


def update_document(pool_id: str, patch: Any) -> dict[str, Any]:
    """把老师在新题源码区的修改静默写回池内文档。

    只收题面四件（``type`` / ``stem`` / ``options`` / ``answer`` / ``solution``）：
    来源、标签、考向、配图、难度这些不归源码区管，传了也一律拒绝，绝不静默丢弃。
    池内文档可能还没补齐入库要件，所以这里只做**字段级**校验，不跑整份 Schema——
    补齐欠项仍是老师点裁决时的事。
    """
    # 迟到的导入：pending_pool 在模块顶部引本函数，这里反过来引它会成环。
    from app.core import pending_pool

    row = pending_pool._pool_row(pool_id)
    if not isinstance(patch, dict) or not patch:
        raise PendingError("没有要保存的字段")
    unknown = [key for key in patch if key not in _EDITABLE_FIELDS]
    if unknown:
        raise PendingError("源码区不能改这些字段：" + "、".join(sorted(unknown)))
    document = copy.deepcopy(pending_pool._json_object(row["doc_json"]))
    before = copy.deepcopy(document)
    if "type" in patch:
        value = str(patch["type"] or "")
        if value not in _QUESTION_TYPES:
            raise PendingError(f"题型不合法：{value or '（空）'}")
        document["type"] = value
    if "stem" in patch:
        document["stem"] = _checked_text(patch["stem"], "题干", _MAX_STEM, empty=False)
    if "options" in patch:
        options = _checked_options(patch["options"], before)
        if options:
            document["options"] = options
        else:
            document.pop("options", None)
    if "answer" in patch:
        answer = _checked_answer(patch["answer"])
        if answer is None:
            document.pop("answer", None)
        else:
            document["answer"] = answer
    if "solution" in patch:
        solution = _checked_text(patch["solution"], "解析", _MAX_STEM)
        if solution.strip():
            document["solution"] = solution
        else:
            document.pop("solution", None)
    if document == before:
        return {"ok": True, "pool_id": str(row["pool_id"]), "changed": [],
                "message": "源码没有变化，未写池。"}
    stamp = questions.now_iso()
    con = connect()
    try:
        cursor = con.execute(
            "UPDATE duplicate_pool SET doc_json = ?, updated_at = ? WHERE pool_id = ?",
            (json.dumps(document, ensure_ascii=False), stamp, str(row["pool_id"])),
        )
        if cursor.rowcount == 0:
            raise PendingNotFound("重题池里没有这一条")
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return {
        "ok": True,
        "pool_id": str(row["pool_id"]),
        "updated_at": stamp,
        "changed": [key for key in _EDITABLE_FIELDS if document.get(key) != before.get(key)],
        "message": "源码已回写池内。",
    }
