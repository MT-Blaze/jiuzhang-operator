"""扫描卷文字层 → 可渲染的 Markdown + LaTeX（纯函数，无 IO）。

PDF 文本层给的是**字形顺序**，不是 TeX 源码：数学字母多半是 Unicode 数学
斜体（``𝐴``、``𝑥``、``𝜋``），上下标被拆成独立的小字，选项和题干可能挤在
同一行。这里只做三件事：

- 把 Unicode 数学字符折回 LaTeX 记号（``𝐴`` → ``A``、``𝜋`` → ``\\pi``、
  ``⩾`` → ``\\ge``、``√2`` → ``\\sqrt{2}``）；
- 把连续的数学片段包进 ``$...$``，中文正文原样保留；
- 从题块文字里剥出题号、题干、选项、答案与解析。

认不出的字符原样保留，**绝不猜测**：拿不准的片段宁可留在正文里，也不
伪造公式或答案。口径与 ``app/core/question_contract.py`` 一致（行内 ``$...$``）。
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.core import question_parser

__all__ = ["text_to_latex", "parse_scan_text"]

# ---------------------------------------------------------------- Unicode → LaTeX

# 只收「字形即含义」的数学符号；函数名与括号类写法留给正文。
_SYMBOLS = {
    "≤": r"\le", "≥": r"\ge", "⩽": r"\le", "⩾": r"\ge",
    "≠": r"\ne", "≈": r"\approx", "≡": r"\equiv", "≃": r"\simeq",
    "≅": r"\cong", "∼": r"\sim",
    "±": r"\pm", "∓": r"\mp", "×": r"\times", "÷": r"\div",
    "·": r"\cdot", "⋅": r"\cdot", "∗": r"\ast", "∘": r"\circ",
    "∞": r"\infty", "∈": r"\in", "∉": r"\notin", "∋": r"\ni",
    "⊂": r"\subset", "⊆": r"\subseteq", "⊃": r"\supset", "⊇": r"\supseteq",
    "∪": r"\cup", "∩": r"\cap", "∅": r"\emptyset", "∖": r"\setminus",
    "∀": r"\forall", "∃": r"\exists", "¬": r"\neg", "∧": r"\wedge", "∨": r"\vee",
    "→": r"\to", "←": r"\leftarrow", "⇒": r"\Rightarrow", "⇐": r"\Leftarrow",
    "⇔": r"\Leftrightarrow", "↔": r"\leftrightarrow", "↦": r"\mapsto",
    "∂": r"\partial", "∇": r"\nabla", "∑": r"\sum", "∏": r"\prod",
    "∫": r"\int", "∬": r"\iint", "∣": r"\mid", "∥": r"\parallel",
    "⊥": r"\perp", "∠": r"\angle", "△": r"\triangle", "∴": r"\therefore",
    "∵": r"\because", "∁": r"\complement", "∶": ":",
    "ℝ": r"\mathbb{R}", "ℕ": r"\mathbb{N}", "ℤ": r"\mathbb{Z}",
    "ℚ": r"\mathbb{Q}", "ℂ": r"\mathbb{C}",
    "…": r"\ldots", "⋯": r"\cdots", "°": r"^\circ",
}

_GREEK = {
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta",
    "ε": r"\varepsilon", "ϵ": r"\epsilon", "ζ": r"\zeta", "η": r"\eta",
    "θ": r"\theta", "ϑ": r"\vartheta", "ι": r"\iota", "κ": r"\kappa",
    "λ": r"\lambda", "μ": r"\mu", "ν": r"\nu", "ξ": r"\xi", "ο": "o",
    "π": r"\pi", "ρ": r"\rho", "ϱ": r"\varrho", "σ": r"\sigma",
    "ς": r"\varsigma", "τ": r"\tau", "υ": r"\upsilon", "φ": r"\varphi",
    "ϕ": r"\phi", "χ": r"\chi", "ψ": r"\psi", "ω": r"\omega",
    "Γ": r"\Gamma", "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda",
    "Ξ": r"\Xi", "Π": r"\Pi", "Σ": r"\Sigma", "Υ": r"\Upsilon",
    "Φ": r"\Phi", "Ψ": r"\Psi", "Ω": r"\Omega",
}

_SUPERSCRIPTS = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
                 "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
_SUBSCRIPTS = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
               "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9"}
_MINUSES = frozenset("\u2212\uff0d\u2010")

# 参与数学片段判定的 ASCII：字母数字、运算符、括号与上下标。
_MATH_ASCII = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "+-*/=<>()[]{}|,.'^_:"
)
_STRONG = frozenset("=<>+-*/|{}[]^_")
_TEXT_ESCAPES = {
    "\\": r"\textbackslash{}", "%": r"\%", "&": r"\&", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "$": r"\$", "^": r"\^{}",
    "~": r"\~{}",
}


def _math_alnum(char: str) -> str | None:
    """Unicode 数学字母数字区段 → 普通字符；不是这一区段就返回 None。"""
    code = ord(char)
    if 0x1D400 <= code <= 0x1D7FF:
        folded = unicodedata.normalize("NFKC", char)
        if len(folded) == 1:
            return folded
    return None


def _is_cjk(char: str) -> bool:
    return unicodedata.east_asian_width(char) in ("W", "F")


def _is_math_char(char: str) -> bool:
    if char.isspace():
        return True
    if char in _MATH_ASCII or char in _SYMBOLS or char in _GREEK:
        return True
    if char in _MINUSES:
        return True
    if char in _SUPERSCRIPTS or char in _SUBSCRIPTS or char == "√":
        return True
    return _math_alnum(char) is not None


def _escape_text(text: str) -> str:
    return "".join(_TEXT_ESCAPES.get(char, char) for char in text)


def _map_char(char: str) -> str:
    folded = _math_alnum(char)
    if folded is not None:
        return _GREEK.get(folded, folded)
    if char in _SYMBOLS:
        return _SYMBOLS[char]
    if char in _GREEK:
        return _GREEK[char]
    if char in _MINUSES:
        return "-"
    if char == "′":
        return "'"
    if char == "″":
        return "''"
    return char


def _sqrt_arg(chars: list[str], start: int) -> tuple[list[str], int]:
    """``√`` 后面的参数：括号组、连续字母数字或单个数学字母；认不出就返回空。"""
    index = start
    while index < len(chars) and chars[index] == " ":
        index += 1
    if index >= len(chars):
        return [], start
    if chars[index] == "(":
        depth = 1
        cursor = index + 1
        while cursor < len(chars) and depth:
            if chars[cursor] == "(":
                depth += 1
            elif chars[cursor] == ")":
                depth -= 1
            cursor += 1
        return chars[index + 1:cursor - 1], cursor
    if _sqrt_atom(chars[index]):
        cursor = index + 1
        while cursor < len(chars) and _sqrt_atom(chars[cursor]):
            cursor += 1
        return chars[index:cursor], cursor
    return [], start


def _sqrt_atom(char: str) -> bool:
    """能直接吃进 ``\\sqrt{}`` 的单个原子：ASCII 字母数字、数学字母或希腊字母。"""
    if char.isascii() and char.isalnum():
        return True
    return _math_alnum(char) is not None or char in _GREEK


def _run_to_latex(chars: list[str]) -> str:
    """一段数学字符 → LaTeX。

    裸花括号按集合/分组括号转义成 ``\\{`` / ``\\}``；但紧跟在 ``^`` / ``_``
    后面的那对花括号是上下标分组（``x^{2}`` 由扫描层自己补），原样留下。
    """
    out: list[str] = []
    index = 0
    script_depth = 0
    pending_script = False
    while index < len(chars):
        char = chars[index]
        if char == "√":
            argument, end = _sqrt_arg(chars, index + 1)
            out.append(r"\sqrt{" + _run_to_latex(argument) + "}")
            index = end
            pending_script = False
            continue
        if char in _SUPERSCRIPTS:
            out.append("^{" + _SUPERSCRIPTS[char] + "}")
            index += 1
            pending_script = False
            continue
        if char in _SUBSCRIPTS:
            out.append("_{" + _SUBSCRIPTS[char] + "}")
            index += 1
            pending_script = False
            continue
        if char == "{":
            if pending_script:
                script_depth += 1
                out.append("{")
            else:
                out.append(r"\{")
            pending_script = False
            index += 1
            continue
        if char == "}":
            if script_depth:
                script_depth -= 1
                out.append("}")
            else:
                out.append(r"\}")
            pending_script = False
            index += 1
            continue
        mapped = _map_char(char)
        out.append(mapped)
        # 控制词后面紧跟字母会被吞成 \forallm：映射改写过就补一个词边界。
        # 原样搬运的 ASCII 字母不动，``ab`` 仍是 ``ab``。
        if (mapped != char and mapped[-1].isascii() and mapped[-1].isalpha()
                and index + 1 < len(chars) and _is_letter_atom(chars[index + 1])):
            out.append(" ")
        pending_script = char in "^_"
        index += 1
    return re.sub(r"[ \t]+", " ", "".join(out)).strip()


def _is_letter_atom(char: str) -> bool:
    """会以字母形态接在控制词后面的字符（含 Unicode 数学字母与希腊字母）。"""
    if char.isascii():
        return char.isalpha()
    folded = _math_alnum(char)
    if folded is not None:
        return folded.isalpha()
    return char in _GREEK


def _is_strong_math(chars: list[str]) -> bool:
    """至少要有一个「像公式」的原子，才值得包 ``$...$``。"""
    for char in chars:
        if char in _SYMBOLS or char in _GREEK or char in _MINUSES:
            return True
        if char in _SUPERSCRIPTS or char in _SUBSCRIPTS or char == "√":
            return True
        if _math_alnum(char) is not None:
            return True
        if char.isascii() and char in _STRONG:
            return True
    return False


def _line_to_latex(line: str) -> str:
    out: list[str] = []
    index = 0
    length = len(line)
    while index < length:
        char = line[index]
        if not _is_math_char(char) or _is_cjk(char):
            out.append(_escape_text(char))
            index += 1
            continue
        end = index
        while end < length and _is_math_char(line[end]) and not _is_cjk(line[end]):
            end += 1
        run = line[index:end]
        core = run.strip(" \t")
        if core and _is_strong_math(core):
            lead = run[:len(run) - len(run.lstrip(" \t"))]
            trail = run[len(run.rstrip(" \t")):]
            out.append(lead + "$" + _run_to_latex(core) + "$" + trail)
        else:
            out.append(_escape_text(run))
        index = end
    return "".join(out)


def text_to_latex(text: Any) -> str:
    """一段扫描文字 → Markdown + LaTeX；中文原样，公式包 ``$...$``。"""
    if not isinstance(text, str):
        return ""
    return "\n".join(_line_to_latex(line) for line in text.split("\n"))


# ---------------------------------------------------------------- 题块文字解析

_LEADING_NUMBER = re.compile(r"^\s*\d{1,2}\s*[.．、]\s*")
_SECTION_HEAD = re.compile(r"^\s*[一二三四五六七八九十]+\s*[、.．]")
# 题干自带作答括号时别再补：全角/半角、括号中间有没有空格都算。
_EMPTY_BRACKET = re.compile(r"[（(][ \t\u3000]*[）)]")
# 旧路径可能已经写出连体空括号（「（ ）（  ）」）：并成一个，只留一处作答位。
_DUP_EMPTY_BRACKET = re.compile(
    r"([（(][ \t\u3000]*[）)])(?:[ \t]*[（(][ \t\u3000]*[）)])+"
)
_ANSWER = re.compile(r"(?:【\s*答\s*案\s*】|(?:^|\n)\s*答\s*案\s*[：:])\s*([^\n【]*)")
_SOLUTION = re.compile(
    r"【\s*(?:解析|分析|详解|点睛|点评)\s*】|(?:^|\n)\s*(?:解析|分析|详解)\s*[：:]"
)


def _strip_number(text: str) -> str:
    return _LEADING_NUMBER.sub("", text, count=1)


def _dedupe_empty_brackets(text: str) -> str:
    """原卷题干自带作答括号时，连体空括号只留一个，不再追加第二个。"""
    if not _EMPTY_BRACKET.search(text):
        return text
    return _DUP_EMPTY_BRACKET.sub(r"\1", text)


def _cut_section_tail(text: str) -> str:
    """题块尾巴常粘着下一大节的说明（如「二、多选题：…」），切题时一并去掉。"""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if index > 0 and _SECTION_HEAD.match(line):
            return "\n".join(lines[:index])
    return text


def _split_answer(text: str) -> tuple[str, str, str]:
    """(答案, 解析, 剩余正文)；没有标记就原样返回正文。"""
    solution = ""
    match = _SOLUTION.search(text)
    if match:
        solution = text[match.end():].strip()
        text = text[:match.start()].rstrip()
    answer = ""
    match = _ANSWER.search(text)
    if match:
        answer = match.group(1).strip(" ：:，,。;；\t")
        text = (text[:match.start()] + text[match.end():]).strip()
    if solution:
        inner = _ANSWER.search(solution)
        if inner:
            answer = answer or inner.group(1).strip(" ：:，,。;；\t")
            solution = (solution[:inner.start()] + solution[inner.end():]).strip()
    return answer, solution, text


def _empty() -> dict[str, Any]:
    return {"stem": "", "options": [], "answer": "", "solution": "", "blanks": 0}


def parse_scan_text(raw: Any, label: str = "") -> dict[str, Any]:
    """题块文字 → 题干 / 选项 / 答案 / 解析（已折成 Markdown + LaTeX）。

    题号只属于来源关系，题干里不再重复；题块完全没字就返回空，由调用方
    决定要不要落占位提示。
    """
    text = str(raw or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return _empty()
    text = _strip_number(text)
    text = _cut_section_tail(text).strip()
    answer, solution, text = _split_answer(text)
    split = question_parser.split_options(text)
    if split["split"]:
        stem_raw = split["stem"]
        options_raw = split["options"]
        tail = split.get("tail") or ""
        if tail:
            extra_answer, extra_solution, rest = _split_answer(tail)
            answer = answer or extra_answer
            solution = solution or extra_solution
            if rest:
                stem_raw = (stem_raw + "\n" + rest).strip()
    else:
        stem_raw = text
        options_raw = []
    stem = text_to_latex(_dedupe_empty_brackets(stem_raw)).strip()
    if not stem:
        return _empty()
    options = [
        {"key": str(option.get("label") or key),
         "content": text_to_latex(option.get("text") or "")}
        for key, option in zip("ABCDEFGH", options_raw)
    ]
    options = [option for option in options if option["content"]]
    if len(options) < 2:
        options = []
    return {
        "stem": stem,
        "options": options,
        "answer": text_to_latex(answer),
        "solution": text_to_latex(solution),
        "blanks": question_parser.count_blanks(stem_raw),
    }
