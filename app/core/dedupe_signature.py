"""查重判据的纯函数层：归一、四要素指纹、正文骨架、公式签名、置信度档位（军令 #32 · S5b 拆出）。

**来源**：本模块整块搬自 ``app/core/bank_dedupe.py``（原 914 行撞破 800 行上限），
搬运动作为纯 extract-module——函数体、常量值、注释、判据口径逐字未改，
``bank_dedupe`` 原位 re-export 全部名字，所有调用点（``api/pending.py``、``pending_pool.py``、
``pending_dedupe.py``、``tests/*``）语义不变。

**边界**：这里只有**字符串与结构**的比对，不碰数据库、不起事务、不认识「批次」或「池子」。
读库扫描与收敛合并事务仍住 ``bank_dedupe``；中转站侧的配图内容哈希住 ``pending_compare``。

**禁区**：
- 指纹口径的唯一事实来源在这里（题型 ‖ 归一题干 ‖ 归一选项 ‖ 归一配图），别处不得另说一套；
- **绝不去括号、运算符与任何 ASCII 标点**，宁可漏报不可误报——误报的下一站是删数据；
- 百分比只是档位内排序的刻度，措辞只说「很像」，不许说「98% 是同一道题」（台账第 52 条）；
- 骨架只负责召回，签名全等才判重；语义等价（``0.5`` vs ``rac{1}{2}``）这里抓不到，交给池内肉眼。
"""

from __future__ import annotations

import difflib
import hashlib
import json
import unicodedata
from typing import Any, Iterable

from app.core import bank
from app.core import latex_style_dict
from app.core.question_parser import normalize_latex


# 只收「排版级」中文标点，且必须在 NFKC 之前删：NFKC 会把「，」变成「,」，
# 而 ASCII 逗号在 $\{a,b\}$ 里是有含义的，删不得。
_LAYOUT_PUNCT = "，。、；：！？“”‘’"


# ------------------------------------------------------------------ 归一与指纹

def _compare_form(value: Any) -> str:
    """比对态归一后的题面：先旧口径（定界符＋等价记号），再写法字典的比对尺子。

    顺序不能反——``normalize_for_compare`` 只认 ``$`` 定界符，``\\(x\\)`` 要先由
    ``normalize_latex`` 换成 ``$x$``。军令 #32 · S2 起，指纹算的就是这一层的产物：
    ``\\dfrac``/``\\frac``、``x^2``/``x^{2}``、``\\frac12``/``\\frac{1}{2}``、
    ``\\left(``/``(\\,`` 这类同义写法从此撞进同一个指纹（判据 2.1、2.6）。
    """
    if not isinstance(value, str) or not value:
        return ""
    return latex_style_dict.normalize_for_compare(normalize_latex(value))["text"]


def normalize_text(value: Any) -> str:
    """题面文本的排版级归一；非字符串一律归成空串，不猜内容。"""
    if not isinstance(value, str) or not value:
        return ""
    text = _compare_form(value)
    for junk in _LAYOUT_PUNCT:
        text = text.replace(junk, "")
    text = unicodedata.normalize("NFKC", text)
    return "".join(text.split())


def _json_list(raw: Any) -> list[Any]:
    """库内 JSON 列 → Python 数组。坏 JSON 按空数组处理：归一不许让扫描崩在一条脏行上。"""
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def normalized_options(raw: Any) -> list[str]:
    """选项内容归一后**排序**：字母顺序不同、正文相同 ⇒ 同一个指纹。"""
    bodies: list[str] = []
    for item in _json_list(raw):
        bodies.append(normalize_text(item.get("content")) if isinstance(item, dict) else normalize_text(item))
    return sorted(bodies)


def image_uris(extensions_raw: Any) -> list[str]:
    """配图 URI 列表。``core-bank.images`` 是底座自己的条目，可以读；入指纹前排序。"""
    entry = bank.extensions_to_object(extensions_raw).get(bank.EXT_IMAGES_KEY)
    images = entry.get("images") if isinstance(entry, dict) else None
    if not isinstance(images, list):
        return []
    out: list[str] = []
    for image in images:
        if isinstance(image, dict):
            out.append(normalize_text(image.get("uri")))
        elif isinstance(image, str):
            out.append(normalize_text(image))
    return out


def fingerprint(question_type: Any, stem: Any, options_raw: Any,
                extensions_raw: Any = "[]") -> str:
    """题面指纹。题型也入摘要：题干相同但一为选择一为填空是两种用法，不并。"""
    parts = [
        str(question_type or ""),
        normalize_text(stem),
        "\x1e".join(normalized_options(options_raw)),
        "\x1e".join(sorted(image_uris(extensions_raw))),
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _mark_of(row: Any) -> str:
    return fingerprint(row["type"], row["stem"], row["options"], row["extensions"])


# ---------------------------------------------------------- 骨架 / 签名 / 置信度
#
# 军令 #32 · S2（台账第 51、52 条）。跨来源同一题是漏报主因：中文正文认得最准、
# 公式最容易认岔，所以反过来用证据——
#   · **正文骨架**：数学段整段挖掉、按顺序留一个占位符，只留中文与标点，比相似度；
#     骨架只负责**召回**，不负责判重。
#   · **公式签名**：数学段里按顺序抽数字／单字母／运算符与关系符，排版命令透明，
#     但**符号一个都不省**（``\\cap`` 与 ``\\cup`` 必须分得开）；签名全等才判重。
#   · **置信度**：由确定信号加权，出「确定／很像／较像／可能」＋百分比与信号明细。
#     百分比只是排序用的刻度，措辞只说「很像」，不说「98% 是同一道题」。
# 分数归一形（判据 2.1）：``\\frac12`` 经写法字典已是 ``\\frac{1}{2}``，签名再把
# ``\\frac`` 读成中缀 ``/``，于是 ``\\frac12`` / ``\\frac{1}{2}`` / ``1/2`` 三者全等。
# 语义等价仍抓不到（``0.5`` vs ``\\frac{1}{2}``）——台账第 50 条写明的死线，交给池内肉眼。

SKELETON_PLACEHOLDER = "\x11"        # 一个数学段 = 一个占位符，只保顺序与个数
FRACTION_OPERATOR = "/"              # \frac{a}{b} 与 a/b 的公共签名形
COMMAND_MARK = "\x1c"                # 命令名前缀：把 \cap 与 c-a-p 三个字母分开
SEGMENT_MARK = "\x1e"                # 被正文隔开的两串数学之间：$a$ 且 $b$ ≠ $ab$
GROUP_OPEN = "("                     # \frac 分子/分母（多 token 时）的显式分组
GROUP_CLOSE = ")"
MAX_FRACTION_DEPTH = 6               # 分数嵌套上限：超过就按「读不动」处理，不递归到底

# 门槛表＝唯一一把尺子（旧 0.92 的「高度相似」并入这里的 very_similar 档）。
SKELETON_LEVELS = {
    "certain": 1.0,          # 确定：四要素指纹全等，骨架门槛只是形式
    "very_similar": 0.92,    # 很像：骨架高度相似且签名全等
    "fairly_similar": 0.75,  # 较像：骨架像但签名差在符号或数字上
    "possible": 0.55,        # 可能：只当召回提示，永不据此判重
}
LEVEL_LABELS = {
    "certain": "确定",
    "very_similar": "很像",
    "fairly_similar": "较像",
    "possible": "可能",
}
LEVEL_ORDER = ("certain", "very_similar", "fairly_similar", "possible")
# 百分比只是**档位内排序**的刻度：每档一个区间，命中信号的权重和在区间里插值。
# 上限的存在是为了让「很像」永远不可能显示成 95%——措辞只能说写法像，不能说
# 「98% 是同一道题」（台账第 52 条）。
LEVEL_CEILING = {"certain": 100, "very_similar": 89, "fairly_similar": 69, "possible": 49}
LEVEL_FLOOR = {"certain": 90, "very_similar": 75, "fairly_similar": 55, "possible": 30}

# 三档门槛：严＝只收指纹全等；标准＝另加「骨架高相似且签名全等」；宽＝较像/可能也进池。
TIER_LEVELS = {
    "strict": ("certain",),
    "standard": ("certain", "very_similar"),
    "loose": LEVEL_ORDER,
}
TIER_LABELS = {"strict": "严", "standard": "标准", "loose": "宽"}
DEFAULT_TIER = "loose"        # 判据 3.2：初查默认停在最宽档，宁可多收

# 置信度权重：只由确定信号加权。四项「比对侧」信号加起来正好 100，用来在档位区间里
# 插值出百分比；`mark`（四要素指纹全等）是另一把尺子——它自己就是「确定」，不参与插值。
SIGNAL_WEIGHTS = {"mark": 100, "signature": 40, "skeleton": 30, "numbers": 20, "answer": 10}
CALIBRATED_TOTAL = SIGNAL_WEIGHTS["signature"] + SIGNAL_WEIGHTS["skeleton"] \
    + SIGNAL_WEIGHTS["numbers"] + SIGNAL_WEIGHTS["answer"]
SIGNAL_LABELS = {
    "mark": "四要素指纹全等",
    "signature": "公式签名全等",
    "skeleton": "正文骨架相似",
    "numbers": "数字序列一致",
    "answer": "答案一致",
}

# 签名里当透明的东西：排版命令与文字命令（文字命令的内容仍按字符进签名）。
_SIGN_TRANSPARENT = frozenset({
    "left", "right", "displaystyle", "quad", "qquad", "thinspace", "negthinspace",
    "nonumber", "notag", "label", "tag", "mathrm", "mathit", "mathsf", "mathtt",
    "text", "mbox", "textrm", "operatorname",
})
_SIGN_TEXT_COMMANDS = frozenset({"text", "mbox", "textrm", "operatorname"})
# 签名里丢掉的字符：花括号与波浪号只是分组，比对态已由写法字典补齐括号。
_SIGN_DROP = frozenset("{}~")
_SIGN_DROP_CONTROLS = frozenset({",", ";", ":", "!", " ", "\t"})


def text_similarity(left: str, right: str) -> float:
    """两段归一文本的相似比（0~1）；长度差一倍以上直接归零，省下一次逐字比对。"""
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    shorter, longer = sorted((len(left), len(right)))
    if not longer or shorter / longer < 0.5:
        return 0.0
    return difflib.SequenceMatcher(None, left, right).ratio()


def surface_text(stem: Any, options_raw: Any = None) -> str:
    """题面文本（题干 ‖ 选项正文）：骨架与签名都算在这个上面，不含答案与解析。"""
    parts = [str(stem or "")]
    for item in _json_list(options_raw):
        body = item.get("content") if isinstance(item, dict) else item
        parts.append(str(body or ""))
    return "\n".join(part for part in parts if part)


def skeleton(value: Any) -> str:
    """正文骨架：数学段换成一个占位符，段外只留中文与标点（骨架只负责召回）。"""
    text = _compare_form(value)
    if not text:
        return ""
    pieces: list[str] = []
    cursor = 0
    for start, end, _unclosed in latex_style_dict.math_spans(text):
        pieces.append(_skeleton_prose(text[cursor:start]))
        pieces.append(SKELETON_PLACEHOLDER)
        cursor = end
    pieces.append(_skeleton_prose(text[cursor:]))
    return "".join(pieces)


def _skeleton_prose(segment: str) -> str:
    """非数学段：**只留汉字与字母**——标点（中英文一视同仁）、数字、符号全丢。

    台账第 51 条写的是「只留中文与标点」，落地时按「只留汉字与字母」执行，理由两条：

    ① NFKC 会把全角标点折成 ASCII（「，」→「,」、「（）」→「()」、「１」→「1」），
      「先删中文标点」那条规矩拦不住手打英文逗号的老师，两套归一各走各路；
    ② 标点是誊抄噪声里最多的那一类，而骨架只负责**按中文表述召回**，区分度全在
      公式签名那一层——让「a<b」和「a>b」长出两个骨架是帮倒忙。
    「（个）」这种括注里的**汉字**照留（「个」是量词，不是噪声），只有括号本身消失。

    顺序：NFKC（全角折半角）→ 删空白（NFKC 把 U+3000 折成半角空格，必须在这之后）
    → 丢 ASCII → 按 Unicode 类别丢掉仍在非 ASCII 区的标点/符号/数字（○、√、±、２ 这些）。
    """
    if not segment:
        return ""
    segment = unicodedata.normalize("NFKC", segment)
    segment = "".join(char for char in segment if not char.isspace())
    kept: list[str] = []
    for char in segment:
        if char.isascii() or char.isspace():
            continue
        # ○（So，几何里表示圆）、√（So）、±（Sm）这类符号不算正文；NFKC 后仍留在
        # 非 ASCII 区的标点/符号（如「、」以外的少数）在这里按 Unicode 类别兜一道。
        if unicodedata.category(char)[0] in ("P", "S", "N"):
            continue
        kept.append(char)
    return "".join(kept)


def _math_runs(text: str) -> list[str]:
    """把**相邻的**数学段并成一段：``$a$$b$`` 与 ``$ab$`` 写的是一回事，不分边界。

    签名与数字序列共用这一个口径。段与段之间只有正文时留下一个 ``SEGMENT_MARK``
    空位——否则 ``$a$ 且 $b$`` 与 ``$ab$``（两个变量挨着写）会长出同一个签名。
    """
    pieces: list[str] = []
    cursor = 0
    for start, end, _unclosed in latex_style_dict.math_spans(text):
        if start > cursor:
            pieces.append(SEGMENT_MARK)
        pieces.append(text[start:end])
        cursor = end
    return [piece for piece in "".join(pieces).split(SEGMENT_MARK) if piece]


def _scan_runs(value: Any) -> tuple[list[str], list[str]]:
    """一个题面 → ``(签名 token 序列, 数字序列)``。"""
    tokens: list[str] = []
    numbers: list[str] = []
    text = _compare_form(value)
    for run in _math_runs(text):
        _scan_math(run, tokens, numbers)
    return tokens, numbers


def formula_signature(value: Any) -> str:
    """公式签名：**只由数学段组成**（正文的活儿归骨架），按顺序的空格分隔 token 串。"""
    return " ".join(_scan_runs(value)[0])


def number_sequence(value: Any) -> list[str]:
    """数学段里按顺序出现的数字（含小数），用来出「数字是否一致」这个确定信号。"""
    return _scan_runs(value)[1]

def _scan_math(segment: str, tokens: list[str], numbers: list[str], depth: int = 0) -> None:
    """把一个数学段拆成签名 token；``tokens``/``numbers`` 由调用方提供，按顺序追加。

    ``depth`` 是 ``\\frac`` 的嵌套层数：每往分子/分母里钻一层就 +1，超过
    ``MAX_FRACTION_DEPTH`` 直接按「读不动」处理（命令名进签名，不猜）。
    """
    i = 0
    n = len(segment)
    while i < n:
        char = segment[i]
        if char == "$" or char in _SIGN_DROP:
            i += 1
            continue
        if char == "\\":
            name, tail = latex_style_dict.read_command(segment, i)
            if name is None:
                control = segment[i + 1:tail]
                if control not in _SIGN_DROP_CONTROLS:
                    tokens.append(COMMAND_MARK + control)
                i = tail
                continue
            if name == "frac":
                groups, end = (_frac_groups(segment, tail)
                               if depth < MAX_FRACTION_DEPTH else (None, tail))
                if groups is not None:
                    for index, inner in enumerate(groups):
                        if index:
                            tokens.append(FRACTION_OPERATOR)
                        # 分子/分母**整串**先扫成一个子签名，多于一个 token 时用括号
                        # 包住：\frac{a+b}{2} → ( a + b ) / 2，既和 (a+b)/2 撞上，
                        # 又和 a + b / 2 分开——摊平会丢结合关系，那是误报的源头。
                        inner_tokens: list[str] = []
                        _scan_math(inner, inner_tokens, numbers, depth + 1)
                        if len(inner_tokens) > 1:
                            tokens.extend([GROUP_OPEN, *inner_tokens, GROUP_CLOSE])
                        else:
                            tokens.extend(inner_tokens)
                    i = end
                    continue
                # 参数不是花括号形（写法字典没认下来的怪写法）：命令名进签名，不猜
                tokens.append(COMMAND_MARK + name)
                i = tail
                continue
                # 参数不是花括号形（写法字典没认下来的怪写法）：命令名进签名，不猜
                tokens.append(COMMAND_MARK + name)
                i = tail
                continue
            if name in _SIGN_TRANSPARENT:
                if name in _SIGN_TEXT_COMMANDS and tail < n and segment[tail] == "{":
                    end = latex_style_dict.match_group(segment, tail)
                    tokens.extend(_skeleton_prose(segment[tail + 1:end - 1]))
                    i = end
                    continue
                i = tail
                continue
            tokens.append(COMMAND_MARK + name)
            i = tail
            continue
        if char.isdigit():
            j = i
            while j < n and (segment[j].isdigit()
                             or (segment[j] == "." and j + 1 < n and segment[j + 1].isdigit())):
                j += 1
            number = segment[i:j]
            numbers.append(number)
            tokens.append(number)
            i = j
            continue
        if char.isascii() and char.isalpha():
            tokens.append(char)
            i += 1
            continue
        if not char.isascii():
            tokens.append(char)
            i += 1
            continue
        tokens.append(char)
        i += 1


def _frac_groups(segment: str, start: int) -> tuple[list[str] | None, int]:
    """读 ``\\frac`` 的两个花括号参数；读不齐就回 ``(None, start)``，绝不猜。"""
    groups: list[str] = []
    i = start
    n = len(segment)
    for _ in range(2):
        while i < n and segment[i] == " ":
            i += 1
        if i >= n or segment[i] != "{":
            return None, start
        end = latex_style_dict.match_group(segment, i)
        if end >= n and segment[end - 1] != "}":
            return None, start
        groups.append(segment[i + 1:end - 1])
        i = end
    return groups, i


def confidence(left: Any, right: Any, *, mark_equal: bool = False,
               answer_state: "bool | None" = None) -> dict[str, Any]:
    """两个题面之间的可解释置信度（判据 2.5）：档位＋百分比＋逐条信号明细。

    ``left``/``right`` 传**原始题面文本**（骨架与签名自己会先过比对归一）；
    ``answer_state`` 是 ``True``/``False``/``None``（``None``＝有一边没表态，
    只登记信号，绝不当成「答案不同」）。
    """
    skeleton_left, skeleton_right = skeleton(left), skeleton(right)
    ratio = text_similarity(skeleton_left, skeleton_right)
    signature_left, signature_right = formula_signature(left), formula_signature(right)
    numbers_left, numbers_right = number_sequence(left), number_sequence(right)
    signature_equal = bool(signature_left or signature_right) and signature_left == signature_right
    numbers_equal = number_sequence_equal(numbers_left, numbers_right)

    if mark_equal:
        level = "certain"
    elif signature_equal and ratio >= SKELETON_LEVELS["very_similar"]:
        level = "very_similar"
    elif ratio >= SKELETON_LEVELS["fairly_similar"]:
        level = "fairly_similar"
    elif ratio >= SKELETON_LEVELS["possible"]:
        level = "possible"
    else:
        level = ""

    raw = 0.0
    if signature_equal:
        raw += SIGNAL_WEIGHTS["signature"]
    raw += SIGNAL_WEIGHTS["skeleton"] * ratio
    if numbers_equal:
        raw += SIGNAL_WEIGHTS["numbers"]
    if answer_state is True:
        raw += SIGNAL_WEIGHTS["answer"]
    if level == "certain":
        percent = LEVEL_CEILING["certain"]
    elif level:
        floor, ceiling = LEVEL_FLOOR[level], LEVEL_CEILING[level]
        span = ceiling - floor
        scaled = 100.0 * raw / CALIBRATED_TOTAL
        percent = floor + min(span, round(span * scaled / 100.0))
    else:
        percent = 0

    signals = [
        _signal("mark", mark_equal, "指纹全等" if mark_equal else "指纹不等"),
        _signal("signature", signature_equal,
                "签名全等" if signature_equal else f"签名差异：{signature_left[:60]} ↔ {signature_right[:60]}"),
        _signal("skeleton", ratio >= SKELETON_LEVELS["possible"], f"骨架相似度 {round(ratio * 100)}%"),
        _signal("numbers", numbers_equal,
                "数字序列一致" if numbers_equal else f"数字差异：{' '.join(numbers_left[:12])} ↔ {' '.join(numbers_right[:12])}"),
    ]
    if answer_state is None:
        signals.append(_signal("answer", False, "有一边没写答案，无法比较"))
    else:
        signals.append(_signal("answer", answer_state,
                               "答案一致" if answer_state else "答案明确不同"))
    return {
        "level": level,
        "label": LEVEL_LABELS.get(level, ""),
        "percent": percent,
        "similarity": round(ratio, 4),
        "signature_equal": signature_equal,
        "numbers_equal": numbers_equal,
        "mark_equal": bool(mark_equal),
        "answer_state": answer_state,
        "signals": signals,
        "note": "档位只表示写法像不像，不表示是不是同一道题；最终由老师肉眼定。",
    }


def _signal(key: str, hit: bool, detail: str) -> dict[str, Any]:
    return {"key": key, "label": SIGNAL_LABELS[key], "hit": bool(hit),
            "weight": SIGNAL_WEIGHTS[key], "detail": detail}


def number_sequence_equal(left: list[str], right: list[str]) -> bool:
    """数字序列是否一致；两边都没有数字时算「无法比较」，不给这一票。"""
    if not left and not right:
        return False
    return list(left) == list(right)


def level_rank(level: str) -> int:
    """档位排序键：越像越靠前；空档（没达门槛）排最后。"""
    return LEVEL_ORDER.index(level) if level in LEVEL_ORDER else len(LEVEL_ORDER)


def accepts(level: str, tier: Any = None) -> bool:
    """这一档在给定门槛下进不进池；不认识的门限一律按默认最宽档处理。"""
    key = str(tier or DEFAULT_TIER)
    return level in TIER_LEVELS.get(key, TIER_LEVELS[DEFAULT_TIER])


def normalize_tier(tier: Any) -> str:
    """把外面递进来的档位名收进三档之一；不认识的落默认最宽档，不自造第四档。

    门槛只认这张表里的键（``strict`` / ``standard`` / ``loose``）：API 层、池子层
    各自「猜一个档」就是第二套尺子，判据 2.6 不允许。
    """
    key = str(tier or "").strip().lower()
    return key if key in TIER_LEVELS else DEFAULT_TIER


# ------------------------------------------------------------------ 组内差异

def _topic_ids_from(con: Any, question_ids: Iterable[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    ids = list(question_ids)
    if not ids:
        return result
    for row in con.execute(
        f"SELECT question_id, topic_id FROM question_topics"
        f" WHERE question_id IN ({', '.join('?' for _ in ids)}) ORDER BY question_id, topic_id", ids
    ):
        result.setdefault(row["question_id"], []).append(str(row["topic_id"]))
    return {key: sorted(value) for key, value in result.items()}


def _source_keys_from(con: Any, question_ids: Iterable[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    ids = list(question_ids)
    if not ids:
        return result
    for row in con.execute(
        f"SELECT qs.question_id AS qid, qs.source_id, qs.question_no FROM question_sources qs"
        f" WHERE qs.question_id IN ({', '.join('?' for _ in ids)}) ORDER BY qs.id", ids
    ):
        result.setdefault(row["qid"], []).append(f"{row['source_id']}#{row['question_no']}")
    return {key: sorted(value) for key, value in result.items()}


def _grade_of(row: Any) -> str:
    entry = bank.extensions_to_object(row["extensions"]).get(bank.EXT_GRADE_KEY)
    return normalize_text(entry.get("grade")) if isinstance(entry, dict) else ""


def _diff_fields(row: Any, fields: dict[str, str], mounts: dict[str, list[str]],
                 links: dict[str, list[str]]) -> None:
    """把一行的各维度取值塞进 ``fields``；同一维度出现两种取值，出参就点亮这个字段。"""
    values = {
        "answer": normalize_text(row["answer"]),
        "solution": normalize_text(row["solution"]),
        "difficulty": str(row["difficulty"] or ""),
        "grade": _grade_of(row),
        "topics": ",".join(mounts.get(row["id"], [])),
        "sources": ",".join(links.get(row["id"], [])),
        "extensions": ",".join(sorted(bank.extensions_to_object(row["extensions"]))),
    }
    for key, value in values.items():
        seen = fields.setdefault(key, {value})
        seen.add(value)
