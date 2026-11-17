"""LaTeX 写法字典与两把尺子（军令 #32 · S1，底座纯函数，无 IO 无网络）。

同一记号体系内的同义写法只允许一种落笔形态。本模块是**唯一一份**写法字典
``SYMBOL_ALIASES``（及由它派生的表），三个 AI 槽、编辑器清洗与查重链都从这里取口径：

- ``clean_for_write(text)``——**写库清洗**：改正文，保守。只在数学段
  （``$...$`` / ``$$...$$``）内按 LaTeX 命令切词改写，不碰 ``\\left`` /
  ``\\right``，不动间距命令与空格。
- ``normalize_for_compare(text)``——**比对归一**：只用来算指纹。在写库清洗的
  全部规则之上，再把排版命令（``\\left`` / ``\\right`` / ``\\quad`` / ``\\,``）
  与数学段内的空白视为透明。返回的是**新字符串**，调用方拿它算指纹，
  绝不回填原文。

三条硬规矩（台账第 49 条）：

1. **按命令切词改写，不做字符串替换**——``\\left`` 不会被当成 ``\\le`` 改坏，
   ``\\text{}`` 里的汉字、``\\begin{cases}`` 的环境名一个字都不动。
2. **幂等**——洗一遍与洗十遍结果逐字相同。
3. **不认识就不动**——原样保留，并把命令名记进返回值的 ``unknown`` 清单；
   清单只随返回值交给调用方，不落盘、不打印、不进日志。
"""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "SYMBOL_ALIASES",
    "MINUS_VARIANTS",
    "MAX_UNKNOWN",
    "math_spans",
    "contains_alias",
    "rewrite_alias_spans",
    "clean_for_write",
    "normalize_for_compare",
    # 分词器：查重侧（``bank_dedupe.formula_signature``）要「逐段扫描」而不是「整句改写」，
    # 用的就是这两个游标级原语——它们是本模块唯一的命令切分口径，别再另写一份。
    "read_command",
    "match_group",
]

# ── 唯一一份写法字典：只收「同一记号体系内的同义写法」 ──────────────────────
# 键是不带反斜杠的命令名，值是统一写法。\times 与 \cdot（叉积／点积）、
# \{\} 与 () 与 []（集合／开区间／闭区间）含义不同，一律不进这张表。
SYMBOL_ALIASES: dict[str, str] = {
    "dfrac": "frac",
    "tfrac": "frac",
    "leq": "le",
    "leqslant": "le",
    "geq": "ge",
    "geqslant": "ge",
    "neq": "ne",
}

# 三种长相互异的减号：U+2212 数学减号／U+FF0D 全角连字符-减号／U+2010 连字符 → 半角 -。
MINUS_VARIANTS = frozenset("\u2212\uff0d\u2010")

# 需要显式花括号参数的命令：\frac12 → \frac{1}{2}（命令名 → 参数个数）。
_GROUP_ARG_COMMANDS = {"frac": 2}

# 花括号组属于「文字」或「环境名」的命令：组内一个字都不动。
_PROTECTED_GROUP_COMMANDS = frozenset({
    "text", "textrm", "textsf", "texttt", "textmd", "mbox", "hbox", "operatorname",
    "textbf", "textit", "emph", "begin", "end", "includegraphics", "label", "ref",
})

# 比对态额外视为透明的排版命令（写库态全部原样保留）。
_COMPARE_TRANSPARENT_COMMANDS = frozenset({
    "left", "right", "quad", "qquad", "thinspace", "negthinspace", "displaystyle",
})

# 控制符号里的间距命令（\, \; \: \! 与 \ 空格）；换行 \\ 与 \{ \} 不在列。
_COMPARE_TRANSPARENT_CONTROLS = frozenset({",", ";", ":", "!", " "})

# unknown 清单的条数上限：只作诊断，不许撑爆返回体。
MAX_UNKNOWN = 50

# 认识但不需要改写的常见命令——只为给 unknown 降噪，不参与任何改写决策。
_KNOWN_COMMANDS = frozenset({
    # 函数与对数
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan",
    "sinh", "cosh", "tanh", "log", "ln", "lg", "exp", "arg", "deg",
    # 极限、求和、积分与上下界
    "lim", "limsup", "liminf", "max", "min", "sup", "inf", "det", "dim", "gcd",
    "lcm", "Pr", "ker", "mod", "bmod", "pmod", "sum", "prod", "int", "iint",
    "iiint", "oint",
    # 希腊字母
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
    "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron",
    "pi", "varrho", "sigma", "varsigma", "tau", "upsilon", "phi", "varphi",
    "chi", "psi", "omega", "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi",
    "Sigma", "Upsilon", "Phi", "Psi", "Omega",
    # 运算符与关系符
    "pm", "mp", "cdot", "times", "div", "ast", "star", "circ", "bullet",
    "oplus", "ominus", "otimes", "odot", "oslash", "surd", "infty", "partial",
    "nabla", "equiv", "sim", "simeq", "approx", "cong", "ne", "le", "lt", "ge",
    "gt", "ll", "gg", "prec", "succ", "subset", "subseteq", "subsetneq",
    "supset", "supseteq", "supsetneq", "in", "notin", "ni", "cup", "cap",
    "setminus", "emptyset", "varnothing", "forall", "exists", "nexists", "neg",
    "land", "lor", "wedge", "vee", "to", "gets", "rightarrow", "leftarrow",
    "Rightarrow", "Leftarrow", "leftrightarrow", "Leftrightarrow", "mapsto",
    "implies", "iff", "uparrow", "downarrow",
    # 结构、定界与字体
    "frac", "binom", "dbinom", "sqrt", "root", "atop", "over", "choose",
    "stackrel", "overset", "underset", "hat", "check", "acute", "grave",
    "dot", "ddot", "tilde", "widehat", "widetilde", "bar", "overline",
    "underline", "vec", "mathbb", "mathbf", "mathit", "mathrm", "mathsf",
    "mathtt", "mathcal", "boldsymbol", "left", "right", "bigl", "bigr",
    "Bigl", "Bigr", "bigm", "Bigm", "big", "Big", "bigg", "Bigg", "middle",
    "braket", "abs", "norm",
    # 环境与排版
    "matrix", "pmatrix", "bmatrix", "vmatrix", "Vmatrix", "smallmatrix",
    "cases", "dcases", "array", "tabular", "aligned", "align", "alignat",
    "gather", "equation", "split", "displaystyle", "quad", "qquad",
    "thinspace", "negthinspace", "item", "nonumber", "notag", "tag",
    "centering", "nonegthinspace",
}) | frozenset(SYMBOL_ALIASES) | frozenset(SYMBOL_ALIASES.values()) | \
    _PROTECTED_GROUP_COMMANDS | frozenset(_GROUP_ARG_COMMANDS) | \
    _COMPARE_TRANSPARENT_COMMANDS

# 由字典派生的别名扫描器：与表内容一一对应，长式在前保证 \leqslant 不被 \leq 抢先。
_ALIAS_PATTERN = re.compile(
    r"\\(" + "|".join(sorted(SYMBOL_ALIASES, key=len, reverse=True)) + r")(?![A-Za-z])"
)

# 「单字母 + 下标」变量：m_{1}、a_{ij}。只对这类相邻变量补视觉细空格。
_SCRIPT_VAR = re.compile(r"([A-Za-z])_\{([^{}]*)\}")


def math_spans(text: str) -> list[tuple[int, int, bool]]:
    """返回各数学段 (起, 止, 是否未闭合)；未闭合段延到文末。"""
    spans: list[tuple[int, int, bool]] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "\\" and i + 1 < n:
            i += 2
            continue
        if text.startswith("$$", i):
            end = text.find("$$", i + 2)
            if end < 0:
                spans.append((i, n, True))
                break
            spans.append((i, end + 2, False))
            i = end + 2
            continue
        if text[i] == "$":
            end = i + 1
            while end < n:
                if text[end] == "\\":
                    end += 2
                    continue
                if text[end] == "$":
                    break
                end += 1
            if end >= n:
                spans.append((i, n, True))
                break
            spans.append((i, end + 1, False))
            i = end + 1
            continue
        i += 1
    return spans


def contains_alias(text: str) -> bool:
    """文中有没有等价写法（含数学段外的裸命令，口径与旧 ``_SYMBOLS.search`` 一致）。"""
    if not isinstance(text, str):
        return False
    return bool(_ALIAS_PATTERN.search(text))


def rewrite_alias_spans(text: str) -> str:
    """只在数学段内把等价写法收敛到统一写法；段外原样。

    这是 ``normalize_latex`` 沿用的旧口径，逐字保持不变——查重指纹链（
    ``app/core/bank_dedupe.py``）直接依赖它的输出。
    """
    if not isinstance(text, str):
        return ""
    pieces: list[str] = []
    cursor = 0
    for start, end, _unclosed in math_spans(text):
        pieces.append(text[cursor:start])
        pieces.append(_ALIAS_PATTERN.sub(
            lambda m: "\\" + SYMBOL_ALIASES[m.group(1)], text[start:end]))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def clean_for_write(text: Any) -> dict[str, Any]:
    """写库清洗：改正文，保守——不碰 ``\\left``/``\\right``，不动间距与空格。

    返回 ``{"text", "changed", "rules", "unknown"}``；``rules`` 是命中的规则名，
    ``unknown`` 是没认得的命令名（原样保留，只回给调用方）。
    """
    return _rewrite(text, compare=False)


def normalize_for_compare(text: Any) -> dict[str, Any]:
    """比对归一：只供算指纹。排版命令与段内空白视为透明，返回**副本**不改原文。"""
    return _rewrite(text, compare=True)


def _rewrite(text: Any, *, compare: bool) -> dict[str, Any]:
    if not isinstance(text, str):
        return {"text": "", "changed": False, "rules": [], "unknown": []}
    pieces: list[str] = []
    rules: list[str] = []
    unknown: list[str] = []
    cursor = 0
    spans = math_spans(text)
    for start, end, _unclosed in spans:
        pieces.append(_collapse_prose_whitespace(text[cursor:start]) if compare
                      else text[cursor:start])
        segment, hits, missing = _rewrite_span(text[start:end], compare)
        if not compare:
            segment, spaced = _thin_space_scripts(segment)
            if spaced:
                _note(rules, "var_space")
        pieces.append(segment)
        for name in hits:
            _note(rules, name)
        for name in missing:
            _note(unknown, name)
        cursor = end
    pieces.append(_collapse_prose_whitespace(text[cursor:]) if compare else text[cursor:])
    cleaned = "".join(pieces)
    if compare:
        cleaned = cleaned.strip()
    return {
        "text": cleaned,
        "changed": cleaned != text,
        "rules": rules,
        "unknown": unknown[:MAX_UNKNOWN],
    }


def _note(items: list[str], name: str) -> None:
    if name not in items:
        items.append(name)


def _rewrite_span(segment: str, compare: bool) -> tuple[str, list[str], list[str]]:
    """在一个数学段内按命令切词改写；段外的正文由调用方原样搬运。

    ``compare`` 态丢空白时会在「字母命令 + 紧随的字母或数字」之间补回一个空格——
    否则 ``\\le x`` 会被粘成 ``\\lex``，把词边界吃掉。同一处无论原文有没有空格，
    归一结果都相同，幂等且不受原始间距影响。
    """
    out: list[str] = []
    rules: list[str] = []
    unknown: list[str] = []
    i = 0
    n = len(segment)
    after_command = False
    while i < n:
        char = segment[i]
        if char == "\\":
            name, tail = read_command(segment, i)
            if name is None:
                # 控制符号：\{ \} \% \, 与换行 \\，整串原样走。
                token = segment[i:tail]
                if compare and token[1:2] in _COMPARE_TRANSPARENT_CONTROLS:
                    _note(rules, "compare_spacing")
                    i = tail
                    continue
                out.append(token)
                after_command = False
                i = tail
                continue
            if name in _PROTECTED_GROUP_COMMANDS:
                # 文字与环境名：命令连同紧随的花括号组一起搬运，组内不动一个字。
                end = tail
                if end < n and segment[end] == "{":
                    end = match_group(segment, end)
                out.append(segment[i:end])
                after_command = False
                i = end
                continue
            if compare and name in _COMPARE_TRANSPARENT_COMMANDS:
                _note(rules, "compare_layout")
                i = tail
                continue
            alias = SYMBOL_ALIASES.get(name)
            if alias is not None:
                _note(rules, "symbols")
                # 别名改写后立刻按统一写法继续补显式参数，否则 \dfrac12 要两轮才收敛。
                parsed = _read_args(segment, tail, _GROUP_ARG_COMMANDS.get(alias, 0)) \
                    if alias in _GROUP_ARG_COMMANDS else None
                if parsed is not None:
                    args, end, added = parsed
                    if added:
                        _note(rules, "frac_args")
                    out.append("\\" + alias + "".join(args))
                    i = end
                else:
                    out.append("\\" + alias)
                    i = tail
                after_command = True
                continue
            arity = _GROUP_ARG_COMMANDS.get(name)
            if arity is not None:
                parsed = _read_args(segment, tail, arity)
                if parsed is not None:
                    args, end, added = parsed
                    if added:
                        _note(rules, "frac_args")
                    out.append("\\" + name + "".join(args))
                    after_command = True
                    i = end
                    continue
            if name not in _KNOWN_COMMANDS:
                _note(unknown, name)
            out.append(segment[i:tail])
            after_command = True
            i = tail
            continue
        if char in "^_":
            probe = _skip_spaces(segment, i + 1) if compare else i + 1
            atom = _single_atom(segment, probe)
            if atom is not None:
                _note(rules, "script_braces")
                out.append(char + "{" + atom[0] + "}")
                after_command = False
                i = atom[1]
                continue
            out.append(char)
            after_command = False
            i += 1
            continue
        if char in MINUS_VARIANTS:
            _note(rules, "minus")
            out.append("-")
            after_command = False
            i += 1
            continue
        if compare and (char.isspace() or char == "~"):
            _note(rules, "compare_spacing")
            i += 1
            continue
        if compare and after_command and char.isascii() and char.isalpha():
            # 只在「命令名字母 ↔ 变量字母」之间补词边界（\le x 不许粘成 \lex）。
            # 数字**不**补：补了会把 x^2y 这类「幂后紧跟变量」切成多一个 token，
            # 让 x²y 与 xy² 只差一个 token 边界——签名要认写法，更要分表达式。
            if not out or out[-1] != " ":
                out.append(" ")
        out.append(char)
        after_command = False
        i += 1
    return "".join(out), rules, unknown


def read_command(text: str, start: int) -> tuple[str | None, int]:
    """``\\alpha`` → ("alpha", 尾后)；``\\{`` / ``\\ `` / ``\\`` → (None, 尾后)。"""
    index = start + 1
    if index >= len(text):
        return None, index
    char = text[index]
    if char.isascii() and char.isalpha():
        end = index
        while end < len(text) and text[end].isascii() and text[end].isalpha():
            end += 1
        return text[index:end], end
    return None, index + 1


def match_group(text: str, start: int) -> int:
    """``text[start] == "{"`` 时返回配对右括号之后的位置；未闭合就延到文末。"""
    depth = 0
    i = start
    n = len(text)
    while i < n:
        if text[i] == "\\" and i + 1 < n:
            i += 2
            continue
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _protected_spans(text: str) -> list[tuple[int, int]]:
    """文字/环境名命令连同花括号组的区间——组内一个字都不许改。"""
    spans: list[tuple[int, int]] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "\\":
            i += 1
            continue
        name, tail = read_command(text, i)
        if name in _PROTECTED_GROUP_COMMANDS:
            end = tail
            if end < n and text[end] == "{":
                end = match_group(text, end)
            spans.append((i, end))
            i = end
            continue
        i = tail
    return spans


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < span_end and end > span_start for span_start, span_end in spans)


def _thin_space_scripts(segment: str) -> tuple[str, bool]:
    """相邻两个「字母 + 下标」变量之间补 ``\\,``：``m_{1}m_{2}`` → ``m_{1}\\,m_{2}``。

    只加排版细空格，不改乘除关系；逗号、运算符、幂次隔开的变量都不碰，
    ``\\text{}`` / ``\\operatorname{}`` 等文字组内原样保留。已有 ``\\,`` 的
    不再重复补，保证洗十遍与洗一遍逐字相同。
    """
    spans = _protected_spans(segment)
    tokens = [match for match in _SCRIPT_VAR.finditer(segment)
              if not _overlaps(match.start(), match.end(), spans)]
    if len(tokens) < 2:
        return segment, False
    pieces: list[str] = []
    cursor = 0
    changed = False
    for previous, current in zip(tokens, tokens[1:]):
        gap = segment[previous.end():current.start()]
        if gap.strip() or _overlaps(previous.end(), current.start(), spans):
            continue
        pieces.append(segment[cursor:previous.end()])
        pieces.append("\\,")
        cursor = current.start()
        changed = True
    if not changed:
        return segment, False
    pieces.append(segment[cursor:])
    return "".join(pieces), True


def _collapse_prose_whitespace(segment: str) -> str:
    """比对态正文段：连续空白压成一个空格，段与段之间不留双空白。

    老师从 PDF 里粘出来的题干常带「已 知 向 量」这种字间空格；比对态必须把它
    当成同一种写法，否则骨架相似度会平白掉几个点。写入态（``clean_for_write``）
    **不走这里**——那是会改正文的，保守口径不许动正文的空格。
    """
    if not segment:
        return ""
    collapsed = " ".join(segment.split())
    return collapsed


def _skip_spaces(text: str, index: int) -> int:
    i = index
    while i < len(text) and text[i] == " ":
        i += 1
    return i


def _single_atom(text: str, index: int) -> tuple[str, int] | None:
    """单个字母或数字才补花括号；``x^{-1}``、``x^\\alpha`` 这类不动。"""
    if index >= len(text):
        return None
    char = text[index]
    if char.isascii() and char.isalnum():
        return char, index + 1
    return None


def _read_args(text: str, start: int, count: int) -> tuple[list[str], int, bool] | None:
    """读 ``count`` 个参数并补上花括号；读不干净就返回 None（原样不动）。

    返回 ``(参数列表, 结束位置, 是否补过花括号)``——已有花括号的参数逐字搬运。
    """
    args: list[str] = []
    added = False
    i = start
    for _ in range(count):
        i = _skip_spaces(text, i)
        if i >= len(text):
            return None
        char = text[i]
        if char == "{":
            end = match_group(text, i)
            if end >= len(text) and text[end - 1] != "}":
                return None
            args.append(text[i:end])
            i = end
            continue
        if char == "\\":
            name, end = read_command(text, i)
            if name is None:
                return None
            args.append(text[i:end])
            i = end
            continue
        if char.isascii() and char.isalnum():
            args.append("{" + char + "}")
            added = True
            i += 1
            continue
        return None
    return args, i, added
