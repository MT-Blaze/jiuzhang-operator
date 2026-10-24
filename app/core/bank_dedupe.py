"""core-bank 查重引擎：只读扫描 + 收敛合并事务（军令 #18-终 阶段四）。

为什么写在底座而不是插件里：插件跑在沙箱 iframe，拿不到数据库（AGENTS §2）；
而查重要读全库、合并要在 questions / question_topics / question_sources 之间搬挂载关系，
还得保证「一次合并要么全成、要么一条不动」。这类跨表事务只能是底座的一等能力，
插件只经 Host API 申请两个口子：扫描（只读）与合并（带写令牌）。

指纹口径（唯一事实来源，别处不得另说一套）：

- **指纹 = SHA-256(题型 ‖ 归一题干 ‖ 归一选项 ‖ 归一配图)**。归一只做**排版级**处理：
  ① 复用录题入口那套 LaTeX 归一（``\\(\\)``→``$``、``\\leq``→``\\le``…），
     保证「同一句话两种打法」撞成同一个指纹；② 去掉中文句读与引号；
  ③ 全角转半角；④ 去掉所有空白（LaTeX 与中文排版都不靠空格表意）。
- **绝不去括号、运算符与任何 ASCII 标点**：``!`` 是阶乘、``:`` 是比、``;`` 是数组分隔符、
  ``()`` 是分组——删掉任何一类都会把两道不同的题并成一道。查重宁可漏报不可误报，
  因为误报的下一站是删数据。
- 选项**按内容排序**后入指纹：A/B 顺序被打乱的同款题算重复（答案字母随之失配，
  由老师在双栏面板里选定保留项）；选项正文不同就不算重复。
- 配图 URI 入指纹：题干一字不差但配了两张不同的图，是两道题。
- **不比**答案、解析、难度、年级、考向挂载与来源：那些是「录了两遍」的差异，
  不是「题面是否相同」的判据；差异只在出参里逐组列给老师看。

合并口径：老师选定保留项的那一刻，那条就是事实来源——题干、选项、答案、难度、题型
一律原样保留，只把副本的**大纲挂载 / 来源关系 / 单题备注（extensions）**并过来，
解析不同的副本按「解法二/三…」追加。副本行随整事务真删除（存储层没有软删列），
核对不过就回滚。
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime
from typing import Any, Iterable

from app.core import bank
from app.core import bank_fts
from app.core.question_parser import normalize_latex

MAX_GROUPS = 200      # 一次最多回多少组：再多就该分页看，不许把全库倒进 iframe
MAX_GROUP_SIZE = 20   # 单组最多装配多少条全文；正常不会触及，触及说明库里有一大坨同款
MAX_COPIES = 20       # 一次合并最多吸收多少条副本
QUESTION_ID_MAX_LEN = 80   # 与 schema 的 ck_questions_id 长度上限一致

# 只收「排版级」中文标点，且必须在 NFKC 之前删：NFKC 会把「，」变成「,」，
# 而 ASCII 逗号在 $\{a,b\}$ 里是有含义的，删不得。
_LAYOUT_PUNCT = "，。、；：！？“”‘’"

# 「解法」的中文序号：第 1 次追加叫解法二（保留项自带的那段就是解法一）。
_CN_NUMERALS = "二三四五六七八九十"


class MergeRejected(bank.BankConflict):
    """合并被拒：入参校验没过，或提交前的行数核对对不上。两种情况都已整事务回滚。"""


def _encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _stamp() -> str:
    return datetime.now(bank.LOCAL_TZ).isoformat(timespec="seconds")


# ------------------------------------------------------------------ 归一与指纹

def normalize_text(value: Any) -> str:
    """题面文本的排版级归一；非字符串一律归成空串，不猜内容。"""
    if not isinstance(value, str) or not value:
        return ""
    text = normalize_latex(value)
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


# ------------------------------------------------------------------ 只读扫描

def duplicate_groups(plugin_id: str) -> dict[str, Any]:
    """全库只读扫描：标准化 → 指纹 → 返回 ≥2 题的重复组，每组带**全量标准结构**。

    出参口径：
    - ``groups[].documents`` 走 ``bank`` 的读路径装配，与题库浏览器/组卷插件同源；
    - ``groups[].differing_fields`` 从存储行算，含读路径不展示的考向挂载与来源关系；
    - ``redundant`` = Σ(组内条数 − 1)，即「全清完能少多少行」，给页签角标用；
    - 组数超 ``MAX_GROUPS`` 时 ``truncated`` 报出被截掉的组数，不静默少给。
    """
    bank.validate_plugin_id(plugin_id)
    con = bank.connect(plugin_id)
    try:
        buckets: dict[str, list[str]] = {}
        rows_by_id: dict[str, Any] = {}
        for row in con.execute(
            "SELECT id, type, stem, options, answer, solution, extensions, difficulty"
            " FROM questions ORDER BY id"
        ):
            mark = _mark_of(row)
            buckets.setdefault(mark, []).append(row["id"])
            rows_by_id[row["id"]] = row
        grouped = sorted(
            (mark for mark, ids in buckets.items() if len(ids) >= 2),
            key=lambda mark: (-len(buckets[mark]), buckets[mark][0]),
        )
        picked = grouped[:MAX_GROUPS]
        members = {mark: buckets[mark][:MAX_GROUP_SIZE] for mark in picked}
        wanted = [qid for ids in members.values() for qid in ids]
        mounts = _topic_ids_from(con, wanted)
        links = _source_keys_from(con, wanted)
        documents = {doc["id"]: doc for doc in bank.assemble_ids(plugin_id, wanted)}
        groups = []
        for mark in picked:
            ids = members[mark]
            fields: dict[str, set[str]] = {}
            for row in (rows_by_id[qid] for qid in ids):
                _diff_fields(row, fields, mounts, links)
            groups.append({
                "fingerprint": mark,
                "count": len(buckets[mark]),
                "type": rows_by_id[ids[0]]["type"],
                "ids": list(ids),
                "differing_fields": sorted(key for key, seen in fields.items() if len(seen) > 1),
                "documents": [documents[qid] for qid in ids if qid in documents],
            })
        return {
            "plugin_id": plugin_id,
            "scanned": len(rows_by_id),
            "group_count": len(grouped),
            "redundant": sum(len(ids) - 1 for ids in buckets.values() if len(ids) >= 2),
            "truncated": max(0, len(grouped) - MAX_GROUPS),
            "groups": groups,
        }
    finally:
        con.close()


# ------------------------------------------------------------------ 收敛合并

def _question_id(value: Any, label: str) -> str:
    """ID 口径与 ``bank.get_question`` 一致：真实库里有 ``q_legacy_000006`` 这种下划线。"""
    if (not isinstance(value, str) or not value.startswith("q_")
            or len(value) > QUESTION_ID_MAX_LEN):
        raise MergeRejected(f"{label} {value!r} 不是合法题目 ID")
    return value


def _solution_label(ordinal: int) -> str:
    return f"解法{_CN_NUMERALS[ordinal - 1]}" if 1 <= ordinal <= len(_CN_NUMERALS) else f"解法{ordinal + 1}"


def append_solution(primary: str, copy: str, ordinal: int) -> str:
    """把副本解析并进保留项。

    保留项原本没有解析时，副本那段直接就是「解法一」，不该顶着「解法二」的标题；
    已有解析时才按序号追加。文本用原始写法而不是归一结果——归一只为比对服务。
    """
    body = str(copy or "").strip()
    if not body:
        return primary
    if not primary.strip():
        return body
    return f"{primary.rstrip()}\n\n**{_solution_label(ordinal)}**\n\n{body}"


def _next_sort_order(con: Any, question_id: str) -> int:
    """搬过来的考向排到保留项现有挂载之后，展示序不至于插进原序中间。"""
    return int(con.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM question_topics WHERE question_id = ?",
        (question_id,),
    ).fetchone()[0])


def _image_uri(image: Any) -> str:
    return normalize_text(image.get("uri")) if isinstance(image, dict) else normalize_text(image)


def _row_images(row: Any) -> list[Any]:
    entry = bank.extensions_to_object(row["extensions"]).get(bank.EXT_IMAGES_KEY)
    images = entry.get("images") if isinstance(entry, dict) else None
    return images if isinstance(images, list) else []


def _union_extensions(rows: list[Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    """单题备注（extensions）并集：保留项的键与取值一律不动，只搬副本独有的键。

    底座不解释插件私有数据（AGENTS §3），所以同名键取值不同时**不做合成**，
    只把冲突键如实报出去——老师得看到「副本有条备注被舍了」，而不是事后发现少了东西。
    例外是 ``core-bank.images``：配图已进指纹，属底座自己的条目，强制合并不同指纹时
    按 URI 去重并全，不让老师的图随副本一起消失。
    """
    merged = dict(bank.extensions_to_object(rows[0]["extensions"]))
    taken: list[str] = []
    conflicts: list[str] = []
    for row in rows[1:]:
        for key, value in bank.extensions_to_object(row["extensions"]).items():
            if key == bank.EXT_IMAGES_KEY:
                continue
            if key not in merged:
                merged[key] = value
                taken.append(key)
            elif merged[key] != value:
                conflicts.append(key)
    images: list[Any] = list(_row_images(rows[0]))
    seen = {_image_uri(item) for item in images}
    added = False
    for row in rows[1:]:
        for item in _row_images(row):
            if _image_uri(item) in seen:
                continue
            seen.add(_image_uri(item))
            images.append(item)
            added = True
    if images and added:
        merged[bank.EXT_IMAGES_KEY] = {"images": images}
        if bank.EXT_IMAGES_KEY not in taken:
            taken.append(bank.EXT_IMAGES_KEY)
    return merged, taken, conflicts


def _mounted(con: Any, question_id: str) -> list[str]:
    return _topic_ids_from(con, [question_id]).get(question_id, [])


def _linked(con: Any, question_id: str) -> list[str]:
    return _source_keys_from(con, [question_id]).get(question_id, [])


def _move_topics(con: Any, primary: str, copies: list[str], now: str) -> list[str]:
    """大纲挂载搬迁：副本独有的考向并到保留项上，返回搬过去的节点 id。

    ``uq_question_topics_primary`` 只许一个主考向：副本的主挂载搬来时一律降级为 0，
    保留项自己的主挂载点不许被顶掉——那是老师选定保留项时默许的事实来源。
    """
    existing = set(_mounted(con, primary))
    moved: list[str] = []
    for topic_map in _topic_ids_from(con, copies).items():
        for topic_id in topic_map[1]:
            if topic_id in existing:
                continue
            existing.add(topic_id)
            moved.append(topic_id)
            con.execute(
                "INSERT INTO question_topics (question_id, topic_id, is_primary, sort_order, created_at)"
                " VALUES (?, ?, 0, ?, ?)", (primary, topic_id, _next_sort_order(con, primary), now),
            )
    return sorted(moved)


def _move_sources(con: Any, primary: str, copies: list[str], now: str) -> list[str]:
    """来源关系搬迁：同一张卷子的同一个题号并成一行（表上 UNIQUE(question_id, source_id, question_no)）。"""
    existing = set(_linked(con, primary))
    moved: list[str] = []
    for qid in copies:
        for row in con.execute(
            "SELECT source_id, question_no FROM question_sources WHERE question_id = ? ORDER BY id",
            (qid,),
        ):
            key = f"{row['source_id']}#{row['question_no']}"
            if key in existing:
                continue
            existing.add(key)
            moved.append(key)
            con.execute(
                "INSERT INTO question_sources (question_id, source_id, question_no, created_at)"
                " VALUES (?, ?, ?, ?)", (primary, row["source_id"], row["question_no"], now),
            )
    return sorted(moved)


def _verify(con: Any, *, primary: str, copies: list[str], before: int, solution: str,
            extensions: dict[str, Any], topics_expect: list[str],
            sources_expect: list[str]) -> None:
    """提交前核对。不核对就提交，等于把「题删了、挂载还挂着」的风险丢给老师的库。"""
    marks = ", ".join("?" for _ in copies)
    problems: list[str] = []
    after = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
    if after != before - len(copies):
        problems.append(f"题目行数 {before} → {after}，期望掉 {len(copies)} 行")
    kept = con.execute("SELECT solution, extensions FROM questions WHERE id = ?", (primary,)).fetchone()
    if kept is None:
        problems.append(f"保留项 {primary} 不见了")
    else:
        if normalize_text(kept["solution"]) != normalize_text(solution):
            problems.append("保留项的解析没落到合并后的文本")
        if bank.extensions_to_object(kept["extensions"]) != extensions:
            problems.append("保留项的单题备注没落到合并后的并集")
    for table, column in (("questions", "id"), ("question_topics", "question_id"),
                          ("question_sources", "question_id")):
        left = int(con.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {column} IN ({marks})", copies
        ).fetchone()[0])
        if left:
            problems.append(f"{table} 里还残留 {left} 行副本数据")
    got_topics = _mounted(con, primary)
    if got_topics != topics_expect:
        problems.append(f"保留项考向 {len(got_topics)} 个，期望 {len(topics_expect)} 个")
    got_sources = _linked(con, primary)
    if got_sources != sources_expect:
        problems.append(f"保留项来源 {len(got_sources)} 条，期望 {len(sources_expect)} 条")
    if con.execute("PRAGMA foreign_key_check").fetchall():
        problems.append("外键自检有违规")
    if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        problems.append("integrity_check 非 ok")
    if problems:
        raise MergeRejected("；".join(problems))


def merge_questions(plugin_id: str, primary_id: Any, copy_ids: Any) -> dict[str, Any]:
    """把副本收敛进保留项：搬大纲/来源/备注、追加解法二、删副本，核对无误才提交。

    入参不要求指纹相同：双栏面板里老师可能确认一组「近似重复」。指纹不一致时用
    ``fingerprint_mismatch`` 如实报出来，不静默替老师做主。
    备注同名键冲突时保留项赢，冲突键进 ``moved.conflict_extensions``——底座不解释
    插件私有数据（AGENTS §3），不合成、也不假装搬走了。
    """
    bank.validate_plugin_id(plugin_id)
    primary = _question_id(primary_id, "保留项")
    if not isinstance(copy_ids, (list, tuple)):
        raise MergeRejected("副本列表必须是题目 ID 数组")
    if not copy_ids:
        raise MergeRejected("副本列表为空：合并至少要有一条被吸收的题")
    copies: list[str] = []
    for item in copy_ids:
        value = _question_id(item, "副本")
        if value == primary:
            raise MergeRejected(f"保留项 {primary} 不能同时出现在副本列表里")
        if value in copies:
            raise MergeRejected(f"副本 {value} 重复出现")
        copies.append(value)
    if len(copies) > MAX_COPIES:
        raise MergeRejected(f"一次最多合并 {MAX_COPIES} 条副本")

    con = bank.connect(plugin_id)
    holders = [primary, *copies]
    marks = ", ".join("?" for _ in holders)
    copy_marks = ", ".join("?" for _ in copies)
    try:
        rows = {row["id"]: row for row in con.execute(
            f"SELECT * FROM questions WHERE id IN ({marks})", holders
        )}
        missing = [qid for qid in holders if qid not in rows]
        if missing:
            raise bank.BankNotFound(f"题库里没有这些题目：{'、'.join(missing)}")

        primary_row = rows[primary]
        base_mark = _mark_of(primary_row)
        mismatch = [qid for qid in copies
                    if _mark_of(rows[qid]) != base_mark]

        # 备注并集与解法追加先在事务外算成纯值：计算阶段抛错时库连碰都没碰过。
        merged_ext, taken_keys, conflict_keys = _union_extensions([primary_row, *[rows[qid] for qid in copies]])
        solution = str(primary_row["solution"] or "")
        # 已经收进保留项的解法文本。比对用归一结果：排版差异不该在保留项里堆出重复解析，
        # 但也不能拿「整段累加文本」去比——那样第三份与第二份同解法时会被误当成新解法。
        used = {normalize_text(solution)} - {""}
        appended: list[str] = []
        for qid in copies:
            text = str(rows[qid]["solution"] or "")
            mark = normalize_text(text)
            if not mark or mark in used:
                continue
            used.add(mark)
            appended.append(qid)
            solution = append_solution(solution, text, len(appended))

        before = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        topics_before = _mounted(con, primary)
        sources_before = _linked(con, primary)
        now = _stamp()

        con.execute("BEGIN IMMEDIATE")
        try:
            moved_topics = _move_topics(con, primary, copies, now)
            moved_sources = _move_sources(con, primary, copies, now)
            con.execute(
                "UPDATE questions SET solution = ?, extensions = ?, updated_at = ? WHERE id = ?",
                (solution or None, _encode(bank.extensions_to_array(merged_ext)), now, primary),
            )
            con.execute(f"DELETE FROM questions WHERE id IN ({copy_marks})", copies)
            if bank_fts.available():
                for qid in copies:
                    bank_fts.remove(con, qid)
            _verify(con, primary=primary, copies=copies, before=before, solution=solution,
                    extensions=merged_ext,
                    topics_expect=sorted(set(topics_before) | set(moved_topics)),
                    sources_expect=sorted(set(sources_before) | set(moved_sources)))
            con.commit()
        except MergeRejected:
            if con.in_transaction:
                con.rollback()
            raise
        except BaseException as exc:
            if con.in_transaction:
                con.rollback()
            raise MergeRejected(f"合并已整事务回滚：{exc}") from exc
    finally:
        con.close()

    documents = bank.assemble_ids(plugin_id, [primary])
    return {
        "plugin_id": plugin_id,
        "primary_id": primary,
        "merged": copies,
        "same_fingerprint": not mismatch,
        "fingerprint_mismatch": mismatch,
        "moved": {"topics": moved_topics, "sources": moved_sources,
                  "extensions": sorted(set(taken_keys)),
                  "conflict_extensions": sorted(set(conflict_keys))},
        "solution_appended_from": appended,
        "questions_before": before,
        "questions_after": before - len(copies),
        "primary": documents[0] if documents else {},
    }
