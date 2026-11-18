"""OMML（Office Math Markup Language）→ LaTeX，只用标准库 ElementTree。

覆盖分式、上下标、根式、括号、求和/积分、重音与希腊字母。认不出的节点
不做结构猜测：把其中出现的文本原样拼回并返回 warning，宁可难看也不丢内容。
"""

from __future__ import annotations

import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

__all__ = ["OmmlResult", "omml_to_latex"]

_GREEK = {
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta",
    "ε": r"\varepsilon", "ϵ": r"\epsilon", "ζ": r"\zeta", "η": r"\eta",
    "θ": r"\theta", "ϑ": r"\vartheta", "ι": r"\iota", "κ": r"\kappa",
    "λ": r"\lambda", "μ": r"\mu", "ν": r"\nu", "ξ": r"\xi", "π": r"\pi",
    "ρ": r"\rho", "σ": r"\sigma", "τ": r"\tau", "υ": r"\upsilon",
    "φ": r"\varphi", "ϕ": r"\phi", "χ": r"\chi", "ψ": r"\psi", "ω": r"\omega",
    "Γ": r"\Gamma", "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda",
    "Ξ": r"\Xi", "Π": r"\Pi", "Σ": r"\Sigma", "Υ": r"\Upsilon",
    "Φ": r"\Phi", "Ψ": r"\Psi", "Ω": r"\Omega",
}
_SYMBOLS = {
    "≤": r"\le", "≥": r"\ge", "⩽": r"\le", "⩾": r"\ge", "≠": r"\ne",
    "≈": r"\approx", "≡": r"\equiv", "∼": r"\sim", "±": r"\pm", "∓": r"\mp",
    "×": r"\times", "÷": r"\div", "·": r"\cdot", "⋅": r"\cdot", "∗": r"\ast",
    "∘": r"\circ", "∞": r"\infty", "∈": r"\in", "∉": r"\notin",
    "⊂": r"\subset", "⊆": r"\subseteq", "⊃": r"\supset", "⊇": r"\supseteq",
    "∪": r"\cup", "∩": r"\cap", "∅": r"\emptyset", "∀": r"\forall",
    "∃": r"\exists", "¬": r"\neg", "∧": r"\wedge", "∨": r"\vee",
    "→": r"\to", "←": r"\leftarrow", "⇒": r"\Rightarrow", "⇔": r"\Leftrightarrow",
    "↔": r"\leftrightarrow", "↦": r"\mapsto", "∂": r"\partial", "∇": r"\nabla",
    "∠": r"\angle", "△": r"\triangle", "∴": r"\therefore", "∵": r"\because",
    "∥": r"\parallel", "⊥": r"\perp", "ℝ": r"\mathbb{R}", "ℕ": r"\mathbb{N}",
    "ℤ": r"\mathbb{Z}", "ℚ": r"\mathbb{Q}", "ℂ": r"\mathbb{C}",
    "…": r"\ldots", "⋯": r"\cdots", "°": r"^\circ",
}
_NARY = {
    "∑": r"\sum", "∏": r"\prod", "∐": r"\coprod", "∫": r"\int",
    "∬": r"\iint", "∭": r"\iiint", "∮": r"\oint", "⋃": r"\bigcup",
    "⋂": r"\bigcap",
}
_DELIMS = {
    "{": r"\{", "}": r"\}", "⟨": r"\langle", "⟩": r"\rangle", "‖": r"\|",
    "⌈": r"\lceil", "⌉": r"\rceil", "⌊": r"\lfloor", "⌋": r"\rfloor",
}
_ACCENTS = {
    "̂": r"\hat", "̄": r"\bar", "→": r"\vec", "̇": r"\dot", "̈": r"\ddot",
    "̃": r"\tilde", "̌": r"\check", "̆": r"\breve",
}
_ESCAPES = {
    "\\": r"\backslash ", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&",
    "#": r"\#", "%": r"\%", "_": r"\_", "^": r"\^{}", "~": r"\~{}",
}
_PROPERTY_SUFFIX = "Pr"
_PASS_THROUGH = frozenset({
    "oMath", "oMathPara", "e", "num", "den", "sub", "sup", "deg", "fName",
    "lim", "groupChr", "box", "borderBox", "phant",
})


@dataclass
class OmmlResult:
    """一次 OMML 转换的结果；``warnings`` 只描述认不出的节点。"""

    latex: str
    warnings: list[str] = field(default_factory=list)


class _Context:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warn(self, text: str) -> None:
        if text not in self.warnings:
            self.warnings.append(text)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _attr(node: ET.Element, name: str) -> str:
    for key, value in node.attrib.items():
        if _local(key) == name:
            return value
    return ""


def _val(node: ET.Element | None) -> str:
    return _attr(node, "val") if node is not None else ""


def _child(node: ET.Element, name: str) -> ET.Element | None:
    for child in node:
        if _local(child.tag) == name:
            return child
    return None


def _children(node: ET.Element, name: str | None = None) -> list[ET.Element]:
    return [child for child in node if name is None or _local(child.tag) == name]


def _flag(node: ET.Element | None) -> bool:
    """OMML 的开关值：1/on/true/yes 都算开。"""
    return _val(node).strip().lower() in {"1", "on", "true", "yes"}


def _fold(char: str) -> str:
    code = ord(char)
    if 0x1D400 <= code <= 0x1D7FF:
        folded = unicodedata.normalize("NFKC", char)
        if len(folded) == 1:
            return folded
    return char


def _map_text(text: str) -> str:
    """一段公式文字 → LaTeX：希腊字母与运算符折算，控制词后补词边界。"""
    out: list[str] = []
    for char in text:
        folded = _fold(char)
        mapped = _GREEK.get(folded) or _SYMBOLS.get(folded) or _ESCAPES.get(folded)
        if mapped is None:
            out.append(folded.replace("\n", " "))
            continue
        out.append(mapped)
        if mapped.startswith("\\") and mapped[-1:].isalpha():
            out.append(" ")
    return "".join(out)


def _raw_text(node: ET.Element) -> str:
    texts: list[str] = []
    for element in node.iter():
        if _local(element.tag) == "t" and element.text:
            texts.append(element.text)
    return " ".join(texts)


def _run(node: ET.Element, ctx: _Context) -> str:
    parts = [_map_text(child.text or "") for child in _children(node, "t")]
    if parts:
        return "".join(parts)
    return _raw_text(node)


def _converted_children(node: ET.Element, ctx: _Context) -> str:
    return "".join(_convert(child, ctx) for child in node)


def _fraction(node: ET.Element, ctx: _Context) -> str:
    num = _child(node, "num")
    den = _child(node, "den")
    return r"\frac{%s}{%s}" % (
        _converted_children(num, ctx) if num is not None else "",
        _converted_children(den, ctx) if den is not None else "",
    )


def _scripts(node: ET.Element, ctx: _Context, mode: str) -> str:
    base = _child(node, "e")
    sub = _child(node, "sub")
    sup = _child(node, "sup")
    text = _converted_children(base, ctx) if base is not None else ""
    if mode in ("sub", "subsup") and sub is not None:
        text += "_{%s}" % _converted_children(sub, ctx)
    if mode in ("sup", "subsup") and sup is not None:
        text += "^{%s}" % _converted_children(sup, ctx)
    return text


def _pre_script(node: ET.Element, ctx: _Context) -> str:
    base_node = _child(node, "e")
    base = _converted_children(base_node, ctx) if base_node is not None else ""
    sub = _child(node, "sub")
    sup = _child(node, "sup")
    head = ""
    if sub is not None:
        head += "_{%s}" % _converted_children(sub, ctx)
    if sup is not None:
        head += "^{%s}" % _converted_children(sup, ctx)
    return "{}" + head + " " + base


def _root(node: ET.Element, ctx: _Context) -> str:
    base = _child(node, "e")
    body = _converted_children(base, ctx) if base is not None else ""
    deg = _child(node, "deg")
    prop = _child(node, "radPr")
    hide = _flag(_child(prop, "degHide")) if prop is not None else False
    if deg is not None and not hide:
        degree = _converted_children(deg, ctx).strip()
        if degree:
            return r"\sqrt[%s]{%s}" % (degree, body)
    return r"\sqrt{%s}" % body


def _delimiter(node: ET.Element, ctx: _Context) -> str:
    prop = _child(node, "dPr")
    begin = (_val(_child(prop, "begChr")) if prop is not None else "") or "("
    end = (_val(_child(prop, "endChr")) if prop is not None else "") or ")"
    begin = _DELIMS.get(begin, begin) or "."
    end = _DELIMS.get(end, end) or "."
    parts = [_converted_children(item, ctx) for item in _children(node, "e")]
    sep = (_val(_child(prop, "sepChr")) if prop is not None else "") or "|"
    content = sep.join(parts)
    return r"\left%s %s \right%s" % (begin, content, end)


def _nary(node: ET.Element, ctx: _Context) -> str:
    prop = _child(node, "naryPr")
    char = _val(_child(prop, "chr")) if prop is not None else ""
    operator = _NARY.get(char) or _map_text(char) or r"\int"
    sub = _child(node, "sub")
    sup = _child(node, "sup")
    sub_hidden = _flag(_child(prop, "subHide")) if prop is not None else False
    sup_hidden = _flag(_child(prop, "supHide")) if prop is not None else False
    text = operator
    if sub is not None and not sub_hidden:
        text += "_{%s}" % _converted_children(sub, ctx)
    if sup is not None and not sup_hidden:
        text += "^{%s}" % _converted_children(sup, ctx)
    body = _child(node, "e")
    if body is not None:
        text += " " + _converted_children(body, ctx)
    return text


def _function(node: ET.Element, ctx: _Context) -> str:
    name = _child(node, "fName")
    body = _child(node, "e")
    head = _converted_children(name, ctx).strip() if name is not None else ""
    tail = _converted_children(body, ctx) if body is not None else ""
    return (head + " " + tail).strip()


def _limit(node: ET.Element, ctx: _Context, mode: str) -> str:
    base = _child(node, "e")
    lim = _child(node, "lim")
    text = _converted_children(base, ctx) if base is not None else ""
    mark = "_{%s}" if mode == "low" else "^{%s}"
    if lim is not None:
        text += mark % _converted_children(lim, ctx)
    return text


def _bar(node: ET.Element, ctx: _Context) -> str:
    prop = _child(node, "barPr")
    position = _val(_child(prop, "pos")).lower() if prop is not None else ""
    body = _converted_children(node, ctx)
    if "bot" in position:
        return r"\underline{%s}" % body
    return r"\overline{%s}" % body


def _accent(node: ET.Element, ctx: _Context) -> str:
    prop = _child(node, "accPr")
    char = _val(_child(prop, "chr")) if prop is not None else ""
    command = _ACCENTS.get(char, r"\hat")
    base = _child(node, "e")
    body = _converted_children(base, ctx) if base is not None else ""
    return "%s{%s}" % (command, body)


def _fallback(node: ET.Element, ctx: _Context) -> str:
    name = _local(node.tag)
    ctx.warn("未识别的 OMML 节点 m:%s，已原样保留文本" % name)
    return _raw_text(node)


def _convert(node: ET.Element, ctx: _Context) -> str:
    name = _local(node.tag)
    if name == "r":
        return _run(node, ctx)
    if name == "t":
        return _map_text(node.text or "")
    if name in _PASS_THROUGH:
        return _converted_children(node, ctx)
    if name == "f":
        return _fraction(node, ctx)
    if name == "sSup":
        return _scripts(node, ctx, "sup")
    if name == "sSub":
        return _scripts(node, ctx, "sub")
    if name == "sSubSup":
        return _scripts(node, ctx, "subsup")
    if name == "sPre":
        return _pre_script(node, ctx)
    if name == "rad":
        return _root(node, ctx)
    if name == "d":
        return _delimiter(node, ctx)
    if name == "nary":
        return _nary(node, ctx)
    if name == "func":
        return _function(node, ctx)
    if name == "limLow":
        return _limit(node, ctx, "low")
    if name == "limUpp":
        return _limit(node, ctx, "up")
    if name == "bar":
        return _bar(node, ctx)
    if name == "acc":
        return _accent(node, ctx)
    if name.endswith(_PROPERTY_SUFFIX) or name == "ctrlPr":
        return ""
    return _fallback(node, ctx)


def omml_to_latex(node: ET.Element) -> OmmlResult:
    """一个 ``m:oMath``（或其子节点）→ LaTeX；未知节点保留文本并给 warning。"""
    ctx = _Context()
    latex = " ".join(_convert(node, ctx).split())
    return OmmlResult(latex=latex, warnings=ctx.warnings)
