"""core-bank 引擎的写路径：收题、落库、批量导入与建题。

进来的每一条都先过 ``_intake_document``（契约校验 + 归一），不过就整批回滚——
「一题不过、整批不入库」是录题端敢让老师批量拖文件的前提。
``sources`` 最多 8 条、学校与来源按需 upsert、考向链接与 FTS 索引同步维护；
时间戳与题目 id 由底座签发，插件给什么都不作数（AGENTS §3 题库主权）。"""

from __future__ import annotations

import hashlib
import sqlite3
from app.core import question_parser, questions as question_contract, wire
from app.core.bank_codec import _grade_from, answer_to_storage, extensions_to_array
from app.core.bank_query import _fts_clear, _fts_upsert, get_question
from app.core.bank_schema import (
    BLOCKING_ISSUES,
    BankConflict,
    BankError,
    BankImportError,
    CHOICE_TYPES,
    EXT_GRADE_KEY,
    EXT_IMAGES_KEY,
    EXT_TAGS_KEY,
    EXT_TAXONOMY_KEY,
    MAX_QUESTION_SOURCES,
    MAX_TOPIC_IDS,
    REQUIRED_TABLES,
    STORAGE_TYPES,
    STORAGE_YEAR_MAX,
    STORAGE_YEAR_MIN,
    TOPIC_ID_RE,
    _encode,
    _now,
    bank_db_path,
    connect,
    init_bank,
)
from app.core.contract import normalize_contract_version, normalize_difficulty
from pathlib import Path
from typing import Any, Iterable



# ---------------------------------------------------------------- 写入路径

def _storage_ready(document: dict[str, Any]) -> dict[str, Any]:
    """写入前的口径归一：版本号与难度按契约 2.0 归一，超出存储题型的如实拒绝。"""
    document = dict(document)
    document["schema_version"] = normalize_contract_version(document.get("schema_version"))
    document["difficulty"] = normalize_difficulty(document.get("difficulty"))
    if document.get("type") not in STORAGE_TYPES:
        raise question_contract.QuestionValidationError([
            f"type: core-bank 存储层只收 {'/'.join(STORAGE_TYPES)}，"
            f"不收 {document.get('type')!r}（契约里的 proof/unknown 需要先在表结构上解冻）。"
        ])
    return document


def _grade_of(document: dict[str, Any]) -> str:
    """年级的读序：契约根字段优先，再退到扩展字段。

    根字段是契约里的一等事实（录题端与批次公共元数据都写它），旧库只把年级
    塞在 extensions 里，所以扩展字段继续兜底——两条通道都不会静默丢年级。
    """
    root = str(document.get("grade") or "").strip()[:20]
    return root or _grade_from(document.get("extensions") or {})


def _question_row(document: dict[str, Any], now: str) -> list[Any]:
    meta = document.get("meta") or {}
    created = str(meta.get("created_at") or now)
    updated = str(meta.get("updated_at") or created)
    if updated < created:  # ck_questions_updated：updated_at 不得早于 created_at
        updated = created

    extensions = dict(document.get("extensions") or {})
    grade = _grade_of(document)
    if grade:
        extensions[EXT_GRADE_KEY] = {"grade": grade}
    if document.get("images"):
        extensions[EXT_IMAGES_KEY] = {"images": document["images"]}
    else:
        # 老师把配图删光后，旧 extensions 里的图片组不能阴魂不散。
        extensions.pop(EXT_IMAGES_KEY, None)
    tags = [item for item in (document.get("tags") or []) if isinstance(item, str) and item][:32]
    if tags:
        # 七表结构里没有 tags 列；沿用 grade/taxonomy/images 的既有做法，
        # 落在 core-bank 自己的 extensions 键上，读路径再还原成契约的根字段。
        extensions[EXT_TAGS_KEY] = {"tags": tags}
    else:
        extensions.pop(EXT_TAGS_KEY, None)
    taxonomy = document.get("taxonomy") or {}
    if not taxonomy.get("topic_ids"):
        names = {
            key: taxonomy[key]
            for key in ("textbook", "chapter", "section", "topic")
            if taxonomy.get(key)
        }
        if names:
            extensions[EXT_TAXONOMY_KEY] = names
        else:
            extensions.pop(EXT_TAXONOMY_KEY, None)

    question_type = document["type"]
    # 存储层强制「无选项题型 options 必须是空数组」，因此非选择题不带选项
    options = (document.get("options") or []) if question_type in CHOICE_TYPES else []
    return [
        document["id"],
        question_type,
        document["stem"],
        _encode(options),
        answer_to_storage(document.get("answer"), question_type),
        document.get("solution") or None,
        _encode(extensions_to_array(extensions)),
        document["difficulty"],
        created,
        updated,
    ]


def _ensure_school(con: sqlite3.Connection, name: Any, now: str, region: str = "") -> str | None:
    """学校按全称/简称查档，查无则建；只登记办学实体本身，与哪张卷子无关。

    ``region``（地区，如「黑吉辽」）落在 ``schools.city`` 这一列上：读路径的
    ``source.region`` 就是从这儿取的，不写就等于白填。
    """
    text = str(name or "").strip()
    if not text:
        return None
    row = con.execute(
        "SELECT id, city FROM schools WHERE full_name = ? OR short_name = ? LIMIT 1",
        (text[:120], text[:60]),
    ).fetchone()
    if row:
        # 位置取值：批量导入的连接不一定带 row_factory
        if region and not str(row[1] or ""):
            con.execute(
                "UPDATE schools SET city = ?, updated_at = ? WHERE id = ?",
                (region[:64], now, row[0]),
            )
        return row[0]
    uid = "sch_" + hashlib.sha256(("school:" + text).encode("utf-8")).hexdigest()[:11]
    con.execute(
        "INSERT INTO schools (id, full_name, short_name, province, city, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid, text[:120], text[:60], "", region[:64], now, now),
    )
    return uid


def _ensure_source(con: sqlite3.Connection, document: dict[str, Any], grade: str,
                   now: str) -> str | None:
    """来源表一张卷一行；拆不出的字段一律留 NULL，不猜。"""
    source = document.get("source") or {}
    paper = str(source.get("paper_title") or "").strip()[:200]
    if not paper:
        return None
    school_id = str(source.get("school_id") or "").strip()
    if school_id and con.execute(
        "SELECT 1 FROM schools WHERE id = ?", (school_id,)
    ).fetchone() is None:
        # 字典 ID 还没登记进这个题库：退回按校名查档，宁可新建也不把来源挂空。
        school_id = ""
    if not school_id:
        school_id = _ensure_school(con, source.get("school"), now,
                                   str(source.get("region") or "")) or ""
    year = source.get("year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError) as exc:
            raise question_contract.QuestionValidationError(
                ["source.year: 年份必须是整数"]
            ) from exc
        if not STORAGE_YEAR_MIN <= year <= STORAGE_YEAR_MAX:
            raise question_contract.QuestionValidationError([
                f"source.year: 存储层只收 {STORAGE_YEAR_MIN}–{STORAGE_YEAR_MAX}，收到 {year}。"
            ])
    exam_type = str(source.get("exam_type") or "")[:40]
    key = "\x1f".join([paper, school_id or "", str(year or ""), exam_type, grade])
    uid = "src_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:11]
    con.execute(
        "INSERT OR IGNORE INTO sources"
        " (id, school_id, year, exam_type, grade, paper_name, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, school_id or None, year, exam_type, grade, paper, now, now),
    )
    return uid


def upsert_school(plugin_id: str, school: dict[str, Any], region: str = "") -> dict[str, Any]:
    """把工作区字典里的学校登记进题库（ID 原样沿用）。

    题库自己的 ``schools`` 表是来源表的落点；字典与题库各存一份名字，
    但 ID 相同——题目文档里只认 ID，改名时两边按 ID 对齐即可。
    """
    school_id = str(school.get("id") or "").strip()
    full_name = str(school.get("full_name") or "").strip()
    short_name = str(school.get("short_name") or "").strip() or full_name[:60]
    if not school_id or not full_name:
        raise BankError("学校记录缺少 id 或全称")
    now = _now()
    con = connect(plugin_id)
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT id FROM schools WHERE id = ?", (school_id,)).fetchone()
        if row is None:
            # 老题库可能先按校名建过档（ID 是另一套摘要）。同名不同号时认老档，
            # 不再硬插——插入会撞 uq_schools_full_name，把整道题的入库打断。
            clash = con.execute(
                "SELECT id FROM schools WHERE full_name = ?", (full_name[:120],)
            ).fetchone()
            if clash is not None:
                con.execute(
                    "UPDATE schools SET short_name = ?, updated_at = ? WHERE id = ?",
                    (short_name[:60], now, clash["id"]),
                )
            else:
                con.execute(
                    "INSERT INTO schools"
                    " (id, full_name, short_name, province, city, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (school_id, full_name[:120], short_name[:60], "", str(region or "")[:64],
                     now, now),
                )
        else:
            con.execute(
                "UPDATE schools SET full_name = ?, short_name = ?, updated_at = ?"
                " WHERE id = ?",
                (full_name[:120], short_name[:60], now, school_id),
            )
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return {"id": school_id, "full_name": full_name, "short_name": short_name}


def _link_topics(con: sqlite3.Connection, question_id: str, document: dict[str, Any],
                 now: str) -> None:
    """考点挂载只认大纲里真实存在的节点，查无即拒——不允许静默挂到别处。"""
    taxonomy = document.get("taxonomy") or {}
    for index, topic_id in enumerate([
        item for item in (taxonomy.get("topic_ids") or []) if isinstance(item, str)
    ][:MAX_TOPIC_IDS]):
        if TOPIC_ID_RE.fullmatch(topic_id) is None or con.execute(
            "SELECT 1 FROM topics WHERE id = ?", (topic_id,)
        ).fetchone() is None:
            raise question_contract.QuestionValidationError(
                [f"taxonomy.topic_ids: 大纲里没有节点 {topic_id!r}，请先把考向补进大纲树。"]
            )
        con.execute(
            "INSERT OR IGNORE INTO question_topics"
            " (question_id, topic_id, is_primary, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
            (question_id, topic_id, 1 if index == 0 else 0, index, now),
        )


SOURCE_FIELDS = ("paper_title", "school", "year", "exam_type", "question_no")


def _clean_source_entry(entry: Any, index: int) -> dict[str, Any]:
    """一条「额外来源卷」的入参归一；不认识的字段直接拒，避免老师以为写进去了。"""
    if not isinstance(entry, dict):
        raise question_contract.QuestionValidationError(
            [f"sources[{index}]: 每条来源必须是 JSON 对象"]
        )
    unknown = sorted(set(entry) - set(SOURCE_FIELDS))
    if unknown:
        raise question_contract.QuestionValidationError([
            f"sources[{index}]: 不认识的字段 {', '.join(unknown)}"
            f"（只收 {', '.join(SOURCE_FIELDS)}）"
        ])
    paper = str(entry.get("paper_title") or "").strip()
    if not paper:
        raise question_contract.QuestionValidationError(
            [f"sources[{index}].paper_title: 原卷标题不能为空"]
        )
    if len(paper) > 120:
        raise question_contract.QuestionValidationError(
            [f"sources[{index}].paper_title: 原卷标题最长 120 字符"]
        )
    cleaned: dict[str, Any] = {"paper_title": paper}
    year = entry.get("year")
    if year not in (None, ""):
        try:
            year = int(year)
        except (TypeError, ValueError) as exc:
            raise question_contract.QuestionValidationError(
                [f"sources[{index}].year: 年份必须是整数"]
            ) from exc
        if not STORAGE_YEAR_MIN <= year <= STORAGE_YEAR_MAX:
            raise question_contract.QuestionValidationError([
                f"sources[{index}].year: 存储层只收 {STORAGE_YEAR_MIN}–{STORAGE_YEAR_MAX}，收到 {year}。"
            ])
        cleaned["year"] = year
    for field, limit in (("school", 64), ("exam_type", 64), ("question_no", 20)):
        value = str(entry.get(field) or "").strip()
        if len(value) > limit:
            raise question_contract.QuestionValidationError(
                [f"sources[{index}].{field}: 最长 {limit} 字符"]
            )
        if value:
            cleaned[field] = value
    return cleaned


def _normalize_sources(sources: Any) -> list[dict[str, Any]] | None:
    """``None`` = 调用方没提供来源列表（保持原挂载）；数组 = 整组替换。"""
    if sources is None:
        return None
    if not isinstance(sources, list):
        raise question_contract.QuestionValidationError(["sources: 必须是来源对象数组"])
    if len(sources) > MAX_QUESTION_SOURCES:
        raise question_contract.QuestionValidationError(
            [f"sources: 一道题最多再挂 {MAX_QUESTION_SOURCES} 份原卷"]
        )
    return [_clean_source_entry(item, index) for index, item in enumerate(sources)]


def _link_sources(con: sqlite3.Connection, document: dict[str, Any], now: str,
                  extra_sources: list[dict[str, Any]] | None = None) -> None:
    """挂主来源（契约 ``source``）与额外原卷；同一份卷同一题号只记一次。

    一题多卷是关系数据，不进题目文档：契约根对象的 ``source`` 仍是单值，
    完整列表由 ``question_sources()`` 单独读出。
    """
    grade = _grade_of(document)
    primary = document.get("source")
    entries: list[dict[str, Any]] = []
    if isinstance(primary, dict) and str(primary.get("paper_title") or "").strip():
        entries.append(primary)
    entries.extend(extra_sources or [])
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        source_id = _ensure_source(con, {"source": entry}, grade, now)
        if not source_id:
            continue
        question_no = str(entry.get("question_no") or "")[:20]
        slot = (source_id, question_no)
        if slot in seen:
            continue
        seen.add(slot)
        con.execute(
            "INSERT OR IGNORE INTO question_sources"
            " (question_id, source_id, question_no, created_at) VALUES (?, ?, ?, ?)",
            (document["id"], source_id, question_no, now),
        )


def _intake_document(
    document: Any, *, strict: bool = True, baseline: Any = None
) -> dict[str, Any]:
    """录题入口统一清洗与防呆。

    ``strict`` 时只拦**本次新引入**的致命问题：``baseline`` 传改题前的旧文档，
    旧数据里本来就有的坏公式不挡老师改其它字段，但改坏了必须当场报错。
    批量导入走非严格清洗：旧题库的脏文本要归一，但不能因为个别题把整批吞掉。
    """
    cleaned, issues = question_parser.clean_question(document)
    if not isinstance(cleaned, dict):
        raise question_contract.QuestionValidationError(["(root): 请求体必须是 JSON 对象"])
    if strict:
        known: set[str] = set()
        if baseline is not None:
            known = {item["code"] for item in question_parser.clean_question(baseline)[1]}
        blocking = [
            item for item in issues
            if item["code"] in BLOCKING_ISSUES and item["code"] not in known
        ]
        if blocking:
            raise question_contract.QuestionValidationError(
                [f"{item['code']}: {item['message']}" for item in blocking]
            )
    return cleaned


def _write_document(con: sqlite3.Connection, document: dict[str, Any], now: str,
                    *, upsert: bool = False,
                    sources: list[dict[str, Any]] | None = None) -> None:
    row = _question_row(document, now)
    columns = ("type", "stem", "options", "answer", "solution", "extensions", "difficulty", "updated_at")
    if upsert:
        con.execute(
            "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
            " difficulty, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET " + ", ".join(f"{name} = excluded.{name}" for name in columns),
            row,
        )
    else:
        con.execute(
            "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
            " difficulty, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            row,
        )
    if upsert:
        # 重复导入必须幂等：整组重挂，否则 ON CONFLICT 之后挂载关系会越滚越多
        con.execute("DELETE FROM question_sources WHERE question_id = ?", (row[0],))
    _link_sources(con, document, now, sources)
    if upsert:
        _remount_topics(con, row[0], document.get("taxonomy") or {}, now)
    else:
        _link_topics(con, row[0], document, now)
    _fts_upsert(con, row[0], document["stem"])


def _wipe(con: sqlite3.Connection) -> None:
    """整库清空：只用于 reset，按常量表删，删完再开外键。"""
    con.execute("PRAGMA foreign_keys = OFF")
    for table in REQUIRED_TABLES:
        con.execute(f'DELETE FROM "{table}"')
    con.execute("PRAGMA foreign_keys = ON")
    _fts_clear(con)


def import_documents(
    plugin_id: str,
    documents: Iterable[dict[str, Any]],
    *,
    reset: bool = False,
    source_info: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    """批量写入题库（迁移、灌库与测试共用），单事务，失败整体回滚。"""
    path = db_path or bank_db_path(plugin_id)
    if reset and path.exists():
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(path) + suffix)
            if candidate.exists():
                candidate.unlink()
    # 冻结的 schema.sql 没有 IF NOT EXISTS：只有缺库（或明确要求重建）时才建，
    # 否则重放 DDL 必然炸在第二张表上。
    if not path.exists():
        init_bank(plugin_id, path)

    prepared = [_storage_ready(_intake_document(document, strict=False)) for document in documents]
    for document in prepared:
        question_contract.validate_question(document)
    con = sqlite3.connect(path, timeout=10.0)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA busy_timeout = 5000")
        con.execute("BEGIN IMMEDIATE")
        if reset:
            _wipe(con)
        now = _now()
        for document in prepared:
            _write_document(con, document, now, upsert=True)
        if source_info:
            for key, value in source_info.items():
                con.execute(
                    "INSERT INTO bank_meta (key, value) VALUES (?, ?)"
                    " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (str(key), wire.dumps(value, ensure_ascii=False)),
                )
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return len(prepared)


def _with_default_meta(document: Any) -> Any:
    """补齐审计字段：外部题目包常缺 meta，底座按契约补上。

    补的全是审计字段，不动题干、答案与结构——好题不该因为缺一个时间戳被整包拒收。
    """
    if not isinstance(document, dict):
        return document
    stamp = _now()
    meta = document.get("meta")
    filled = dict(meta) if isinstance(meta, dict) else {}
    filled.setdefault("created_at", stamp)
    filled.setdefault("updated_at", stamp)
    filled.setdefault("revision", 1)
    filled.setdefault("status", "published")
    return {**document, "meta": filled}


def prepare_import_documents(
    documents: Iterable[Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """批量导入前的逐题清洗与校验。

    返回 (可写入的题目, 错误清单)。错误清单每项带序号、题目 ID 与 Schema 报错：
    老师能一眼看出包里第几道题坏了，而不是只看到一句「导入失败」。
    """
    prepared: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, document in enumerate(documents, start=1):
        try:
            cleaned = _storage_ready(
                _intake_document(_with_default_meta(document), strict=False)
            )
            question_contract.validate_question(cleaned)
        except question_contract.QuestionValidationError as exc:
            errors.append({
                "index": index,
                "id": str(document.get("id") or "") if isinstance(document, dict) else "",
                "errors": exc.errors[:5],
            })
            continue
        prepared.append(cleaned)
    return prepared, errors


def import_questions(
    plugin_id: str, documents: Iterable[Any], *, mode: str = "upsert"
) -> dict[str, Any]:
    """批量导入题目包：逐题校验 → 摘掉本库没有的考向节点 → 单事务写入。

    ``mode="upsert"`` 同 ID 覆盖（重复导入幂等，导出再导入能还原原状）；
    ``mode="skip"`` 同 ID 跳过。导入包里带的考向节点若本库没有就忽略并如实计数——
    别人的题包带着别人的大纲，硬挂到自己树上才是错挂。
    """
    if mode not in ("upsert", "skip"):
        raise BankError(f"未知导入模式 {mode!r}，只认 upsert / skip")
    prepared, errors = prepare_import_documents(documents)
    if errors:
        raise BankImportError(errors)
    if not prepared:
        raise BankImportError([{"index": 0, "id": "", "errors": ["题目包里没有题目"]}])

    con = connect(plugin_id)
    try:
        known_topics = {row[0] for row in con.execute("SELECT id FROM topics")}
        existing = {row[0] for row in con.execute("SELECT id FROM questions")}
    finally:
        con.close()

    dropped = 0
    kept: list[dict[str, Any]] = []
    for document in prepared:
        taxonomy = document.get("taxonomy") or {}
        wanted = [item for item in (taxonomy.get("topic_ids") or []) if isinstance(item, str)]
        allowed = [item for item in wanted if item in known_topics]
        dropped += len(wanted) - len(allowed)
        if len(allowed) != len(wanted):
            document = {**document, "taxonomy": {**taxonomy, "topic_ids": allowed}}
        kept.append(document)

    if mode == "skip":
        todo = [document for document in kept if document["id"] not in existing]
        skipped = len(kept) - len(todo)
    else:
        todo = kept
        skipped = 0
    written = import_documents(plugin_id, todo) if todo else 0
    return {
        "imported": written,
        "updated": sum(1 for document in todo if document["id"] in existing),
        "skipped": skipped,
        "dropped_topics": dropped,
        "total": len(kept),
    }


def create_question(plugin_id: str, payload: Any, *, sources: Any = None) -> dict[str, Any]:
    """往指定插件题库新增一道题，返回按读路径装配后的标准结构。

    录题插件不碰数据库：它把表单整理成 ``app/core/question_contract.py`` 结构，经宿主
    带一次性令牌转到这里。校验与底座 ``questions`` 表共用同一份 Schema，
    避免两份存储对同一道题各说各话。ID 由底座生成，插件不得指定历史 ID。

    ``sources`` 是主来源之外的额外原卷（一题多卷，各自带原卷题号）。它不属于
    题目文档本身，单独走 ``question_sources`` 关系表；``None`` 表示没有额外原卷。
    """
    if isinstance(payload, dict) and "id" in payload:
        # 旧 ID 可能是历史题目或他人题目：一律作废，由底座重新签发
        payload = {key: value for key, value in payload.items() if key != "id"}
    extra_sources = _normalize_sources(sources)
    payload = _intake_document(payload)
    document = question_contract.prepare_new_question(payload)
    question_contract.validate_question(document)
    document = _storage_ready(document)

    con = connect(plugin_id)
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            _write_document(con, document, _now(), sources=extra_sources)
        except sqlite3.IntegrityError as exc:
            raise BankConflict(f"题目 ID {document['id']} 已存在，请重试。") from exc
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return get_question(plugin_id, document["id"])


def _remount_topics(con: sqlite3.Connection, question_id: str, taxonomy: dict[str, Any],
                    now: str) -> None:
    """重挂考向：整组换掉 ``question_topics`` 的挂载关系（录题插件改题专用）。

    只认大纲里真实存在的节点；一个都不给就清空挂载——清空后这道题在树上查无，
    比挂在错误节点上诚实。
    """
    wanted = [item for item in (taxonomy.get("topic_ids") or []) if isinstance(item, str)]
    if len(wanted) > MAX_TOPIC_IDS:
        raise question_contract.QuestionValidationError(
            [f"taxonomy.topic_ids: 一题最多挂 {MAX_TOPIC_IDS} 个考向"]
        )
    for topic_id in wanted:
        if TOPIC_ID_RE.fullmatch(topic_id) is None or con.execute(
            "SELECT 1 FROM topics WHERE id = ?", (topic_id,)
        ).fetchone() is None:
            raise question_contract.QuestionValidationError(
                [f"taxonomy.topic_ids: 大纲里没有节点 {topic_id!r}，请先把考向补进大纲树。"]
            )
    con.execute("DELETE FROM question_topics WHERE question_id = ?", (question_id,))
    for index, topic_id in enumerate(wanted):
        con.execute(
            "INSERT INTO question_topics (question_id, topic_id, is_primary, sort_order, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (question_id, topic_id, 1 if index == 0 else 0, index, now),
        )
