"""比对归一入口：先把只圈数字的 ``$`` 拆成裸数字，再交冻结模块同一套比对规则。

台账第 56 条把 ``latex_style_dict`` 冻结为 506 行只减不增，而第 57 条要求比对态
与写路同函数同口径拆 ``$``（写路在 ``question_parser`` 已拆）。拆包逻辑只能住在
冻结模块之外，所以比对入口住在这里；冻结模块本身一行不动。
"""

from __future__ import annotations

from typing import Any

from app.core.content import dollar_number, latex_style_dict

__all__ = ["normalize_for_compare"]


def normalize_for_compare(text: Any, aliases: dict | None = None) -> dict[str, Any]:
    """拆裸数字 ``$`` 后走冻结模块比对归一；非字符串原样交冻结模块。"""
    if not isinstance(text, str):
        return latex_style_dict.normalize_for_compare(text, aliases)
    unwrapped_text, unwrapped = dollar_number.unwrap_bare_number_dollars(text)
    out = latex_style_dict.normalize_for_compare(unwrapped_text, aliases)
    if unwrapped:
        if "dollar_number" not in out["rules"]:
            out["rules"].append("dollar_number")
        out["changed"] = True
    return out
