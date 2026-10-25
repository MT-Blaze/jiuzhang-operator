# -*- coding: utf-8 -*-
"""把 456 道真题灌进 v0.6.3 的 7 张关系表（结构冻结后的首轮迁移）。

三份数据源，各取所长（全部只读）：
- ``plugins/.../bank/bank.db`` 的 ``bank_questions``：题面正文、选项、解析、配图、来源标题
  （v0.6.1 已按 schemas/question.json 洗过一轮，正文里的 ``\\includegraphics`` 已换成图片语法）；
- 旧库快照：``difficulty`` 的 L1–L4 原码、``question_topics`` 的考向挂载、``lecture_notes`` 的教研笔记；
- 旧项目 resources：``curriculums/A.json`` 的册/章/节/考向中文名、``schools.json`` 的学校全称简称。
  按主公裁定「最小事实抽取 + 全量导入 A 版大纲」——只取名称类客观事实与 592 考向，
  不搬 JSON 结构、不搬 source 外链、tier/nature 等描述性字段一律不入表。

字段落位（主公 18:50 裁定）：
- tags（含「疑似变式#N」查重噪声）：**丢弃**，不写入新库任何位置；
- grade：落 ``sources.grade``（schema.sql 已含该列与 CHECK，与 year/exam_type 同级），不污染 exam_type 语义；
- 章/节、images、option_columns、tikz：进 ``questions.extensions`` 有序数组；
- 题型纠偏：按《v0.6.3-题型纠偏清单》以答案字母为准，答案区取不到时退到正文尾句「故选：XX」。

用法：
    .venv/Scripts/python.exe tools/migrate_bank_v063.py                 # 只建迁移库并出报告
    .venv/Scripts/python.exe tools/migrate_bank_v063.py --promote       # 另写一份新结构种子库

安全：默认绝不覆盖现网 ``data/banks/*.db`` 与在用的 ``bank/bank.db`` 种子。
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_mod
import io
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_PATH = ROOT / "plugins/org.jiuzhang.bank-engine/bank/schema.sql"
DOC_DB = ROOT / "plugins/org.jiuzhang.bank-engine/bank/bank.db"
LEGACY_DB = ROOT / ".scratch-recon-063/legacy.db"
SCHOOLS_JSON = Path("E:/math-question-bank-main/mathbank/resources/schools.json")
OUTLINE_JSON = Path("E:/math-question-bank-main/mathbank/resources/curriculums/A.json")
MIGRATED_DB = ROOT / "plugins/org.jiuzhang.bank-engine/bank/v063_migrated.db"
SEED_NEW_DB = ROOT / "plugins/org.jiuzhang.bank-engine/bank/bank_v063.db"
REPORT_JSON = ROOT / "data/bank_v063_migration_report.json"
REPORT_MD = ROOT / "docs/v0.6.3-灌库校验.md"

LOCAL_TZ_NOW = datetime.now().astimezone().isoformat(timespec="seconds")
LAYER_CODE = {"book": "bo", "chapter": "ch", "section": "se", "topic": "kx"}
NOTE_TYPE_MAP = {"method": "method", "pit": "pitfall", "knowledge": "knowledge"}
CHOICE_TYPES = ("single_choice", "multiple_choice")

YEAR_RE = re.compile(r"(20\d{2})")
GRADE_RE = re.compile("(高一|高二|高三)")
EXAM_RE = re.compile(
    r"(上学期|下学期)?\s*(\d{1,2}月)?\s*(月考|期中考试|期中考试|期中|期末考试|期末考试|期末|模考|模拟|联考|竞赛|测验|暑假作业|寒假作业)"
)
TAG_RE = re.compile(r"<[^>]+>")
ANSWER_MARK = re.compile(r"【答案】|答案\s*[:：]")
SPLIT_MARK = re.compile(r"【解析】|【详解】|解析\s*[:：]|详解\s*[:：]")
TEXTBF = re.compile(r"\\(?:textbf|text|mathrm|mathbf|bm|emph)\s*\{([^{}]*)\}")
SEPARATORS = re.compile(r"[\s　、，,./·;；:：（）()【】]+")
LETTER_RUN = re.compile(r"[A-H]{1,5}")
TAIL_ANSWER = re.compile(r"(?:故选|因此选|故选择|正确答案[是为]|答案[是为])\s*[:：]?\s*([A-H]{2,4})")


def topic_uid(layer: str, *parts: str) -> str:
    """本仓库自定义的考向节点 ID：tp_ + 层别字母 + sha256(路径明文)[:9]。

    不复用旧项目的 id 生成式；层别字母让长度恒定 12，满足表上的 CHECK。
    """
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:8]
    uid = "tp_%s%s" % (LAYER_CODE[layer], digest)
    if len(uid) != 13:
        raise AssertionError("节点 ID 长度非法：%r（层 %s）" % (uid, layer))
    return uid


def legacy_topic_id(kid: str) -> str:
    """旧库考向 id（k_xxxxxxxxxx）→ 新表 id 的稳定映射。"""
    digest = hashlib.sha256(("legacy-topic:" + kid).encode("utf-8")).hexdigest()[:8]
    return "tp_kx" + digest


def school_uid(raw_id: str) -> str:
    digest = hashlib.sha256(("school:" + raw_id).encode("utf-8")).hexdigest()[:11]
    return "sch_" + digest[:11]


def source_uid(paper_name: str, school_id: str, year: Any, exam_type: str, grade: str) -> str:
    key = "\x1f".join([paper_name, school_id, str(year or ""), exam_type, grade])
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:11]
    return "src_" + digest[:11]


def letters_from_answer_region(markdown: str) -> list[str]:
    raw = markdown or ""
    if not ANSWER_MARK.search(raw):
        return []
    head = SPLIT_MARK.split(raw, maxsplit=1)[0] if SPLIT_MARK.search(raw) else raw
    head = head.split("】", 1)[-1] if "】" in head else ANSWER_MARK.split(head, maxsplit=1)[-1]
    body = TEXTBF.sub(lambda m: m.group(1), head)
    body = re.sub(r"\$[^$]*\$", " ", body)
    found: list[str] = []
    for token in SEPARATORS.split(body):
        if LETTER_RUN.fullmatch(token):
            for ch in token:
                if ch not in found:
                    found.append(ch)
    return found


def letters_from_tail(markdown: str) -> list[str]:
    hits = TAIL_ANSWER.findall(markdown or "")
    out: list[str] = []
    for hit in hits[-1:]:
        for ch in hit:
            if ch not in out:
                out.append(ch)
    return out


def strip_html(content: str) -> str:
    text = TAG_RE.sub("", content or "")
    text = html_mod.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()[:20000]


def parse_source_title(title: str) -> tuple[int | None, str, str]:
    """从原卷标题里拆出 (年份, 考型, 年级)；拆不出的留空，不猜。"""
    year_match = YEAR_RE.search(title or "")
    year = int(year_match.group(1)) if year_match else None
    exam_match = EXAM_RE.search(title or "")
    exam_type = exam_match.group(3) if exam_match else ""
    grade_match = GRADE_RE.search(title or "")
    return year, exam_type[:40], grade_match.group(1) if grade_match else ""


def read_doc_bank() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    con = sqlite3.connect(f"file:{DOC_DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    docs: dict[str, dict[str, Any]] = {}
    for row in con.execute("SELECT * FROM bank_questions"):
        document = {
            "id": row["id"],
            "legacy_id": int(re.search(r"(\d+)$", row["id"]).group(1)),
            "type": row["type"],
            "stem": row["stem"],
            "options": json.loads(row["options_json"] or "[]"),
            "answer": json.loads(row["answer_json"]) if row["answer_json"] else None,
            "solution": row["solution"] or "",
            "grade": row["grade"],
            "chapter": row["chapter"],
            "textbook": row["textbook"],
            "tags": json.loads(row["tags_json"] or "[]"),
            "images": json.loads(row["images_json"] or "[]") if row["images_json"] else [],
            "extensions": json.loads(row["extensions_json"] or "{}"),
            "source": json.loads(row["source_json"] or "{}"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        docs[document["id"]] = document
    con.close()
    return docs, {"doc_rows": len(docs)}


def read_legacy(legacy_ids: set[int]) -> dict[str, Any]:
    con = sqlite3.connect(f"file:{LEGACY_DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    out: dict[str, Any] = {
        "difficulty": {}, "topic_link": {}, "answer_raw": {}, "option_columns": {},
        "tikz": {}, "school_id": {}, "notes": [], "legacy_missing": [],
    }
    for row in con.execute(
        "SELECT id, difficulty, source_school_id, option_columns, tikz_code, answer_markdown "
        "FROM questions"
    ):
        if row["id"] not in legacy_ids:
            continue
        out["difficulty"][row["id"]] = (row["difficulty"] or "").strip().upper()
        out["school_id"][row["id"]] = row["source_school_id"]
        out["option_columns"][row["id"]] = row["option_columns"]
        out["tikz"][row["id"]] = row["tikz_code"] or ""
        out["answer_raw"][row["id"]] = row["answer_markdown"] or ""
    for row in con.execute(
        "SELECT question_id, version_code, compulsory, chapter, knowledge, topic_id, sort_order "
        "FROM question_topics"
    ):
        if row["question_id"] in legacy_ids:
            out["topic_link"][row["question_id"]] = {
                "legacy_id": row["question_id"],
                "version": row["version_code"], "book": row["compulsory"],
                "chapter": row["chapter"], "section": row["knowledge"],
                "topic_id": (row["topic_id"] or "").strip(), "sort": row["sort_order"],
            }
    for row in con.execute("SELECT note_key, note_type, content FROM lecture_notes"):
        out["notes"].append({"key": row["note_key"], "type": row["note_type"], "content": row["content"]})
    found = {row["id"] for row in con.execute("SELECT id FROM questions")}
    out["legacy_missing"] = sorted(legacy_ids - found)
    con.close()
    return out


def build_topics(legacy_topic_ids: set[str], section_index: dict[tuple[str, str, str], str],
                 link_by_legacy: dict[int, dict[str, Any]]) -> tuple[
    list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    """从 A.json 建 册/章/节/考向 四级节点；旧库用到但大纲查无的考向补 draft 节点。"""
    raw = json.loads(OUTLINE_JSON.read_text(encoding="utf-8"))
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    kx_map: dict[str, str] = {}
    chapter_by_name: dict[tuple[str, str], str] = {}
    stats = {"books": 0, "chapters": 0, "sections": 0, "topics": 0, "orphans": 0}

    def push(node: dict[str, Any]) -> None:
        if node["id"] in seen:
            return
        seen.add(node["id"])
        nodes.append(node)
        by_id[node["id"]] = node

    for book_order, (book_name, chapters) in enumerate(raw.items()):
        book_id = topic_uid("book", book_name)
        push({"id": book_id, "parent_id": None, "name": book_name, "path": book_id,
              "sort_order": book_order, "status": "active"})
        stats["books"] += 1
        for chapter_order, (chapter_name, sections) in enumerate(chapters.items()):
            chapter_id = topic_uid("chapter", book_name, chapter_name)
            chapter_by_name[(book_name, chapter_name)] = chapter_id
            push({"id": chapter_id, "parent_id": book_id, "name": chapter_name,
                  "path": "%s/%s" % (book_id, chapter_id), "sort_order": chapter_order,
                  "status": "active"})
            stats["chapters"] += 1
            for section_order, section in enumerate(sections):
                section_name = section["name"]
                section_id = topic_uid("section", book_name, chapter_name, section_name)
                push({"id": section_id, "parent_id": chapter_id, "name": section_name,
                      "path": "%s/%s/%s" % (book_id, chapter_id, section_id),
                      "sort_order": section_order, "status": "active"})
                stats["sections"] += 1
                section_index[(book_name, chapter_name, section_name)] = section_id
                for topic_order, topic in enumerate(section.get("topics") or []):
                    topic_id = topic_uid("topic", book_name, chapter_name, section_name, topic["name"])
                    push({"id": topic_id, "parent_id": section_id, "name": topic["name"],
                          "path": "%s/%s/%s/%s" % (book_id, chapter_id, section_id, topic_id),
                          "sort_order": topic_order, "status": "active"})
                    stats["topics"] += 1
                    if topic.get("id"):
                        kx_map[topic["id"]] = topic_id

    # 大纲查无的旧考向：按旧库登记的 (册,章,节) 挂到节下，名字留待补录
    unknown = sorted({link["topic_id"] for link in link_by_legacy.values()
                      if link["topic_id"] and link["topic_id"] not in kx_map})
    used_slots = {(n["parent_id"], n["sort_order"]) for n in nodes}
    for kid in unknown:
        link = next((l for l in link_by_legacy.values() if l["topic_id"] == kid), None)
        section_id = section_index.get((link["book"], link["chapter"], link["section"])) if link else None
        parent_id = section_id or (chapter_by_name.get((link["book"], link["chapter"])) if link else None)
        parent = by_id.get(parent_id)
        node_id = legacy_topic_id(kid)
        order = 0
        probe_parent = parent_id
        while (probe_parent, order) in used_slots:
            order += 1
        used_slots.add((probe_parent, order))
        node = {"id": node_id, "parent_id": probe_parent, "name": "待补录考向 %s" % kid,
                "path": ("%s/%s" % (parent["path"], node_id)) if parent else node_id,
                "sort_order": order, "status": "draft"}
        push(node)
        kx_map[kid] = node_id
        stats["orphans"] += 1
        if parent is None:
            stats["orphans_unplaced"] = stats.get("orphans_unplaced", 0) + 1

    # 旧库把「章名当节名」登记、但大纲里没有同名节：补 draft 节节点，保证题能挂到节层
    for link in link_by_legacy.values():
        book, chapter, section = link["book"], link["chapter"], link["section"]
        if not (book and chapter and section) or (book, chapter, section) in section_index:
            continue
        chapter_id = chapter_by_name.get((book, chapter))
        if not chapter_id:
            stats["sections_unresolved"] = stats.get("sections_unresolved", 0) + 1
            continue
        order = 0
        while (chapter_id, order) in used_slots:
            order += 1
        used_slots.add((chapter_id, order))
        node_id = topic_uid("section", book, chapter, section)
        parent = by_id[chapter_id]
        push({"id": node_id, "parent_id": chapter_id, "name": section,
              "path": "%s/%s" % (parent["path"], node_id), "sort_order": order, "status": "draft"})
        section_index[(book, chapter, section)] = node_id
        stats["sections_drafted"] = stats.get("sections_drafted", 0) + 1
    return nodes, kx_map, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="core-bank v0.6.3 全量灌库")
    parser.add_argument("--promote", action="store_true",
                        help="额外写一份新结构种子库 bank/bank_v063.db（仍不动现网库）")
    parser.add_argument("--out", default=str(MIGRATED_DB))
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    out_path = Path(args.out)
    docs, stats = read_doc_bank()
    legacy_ids = {d["legacy_id"] for d in docs.values()}
    leg = read_legacy(legacy_ids)

    schools_raw = json.loads(SCHOOLS_JSON.read_text(encoding="utf-8"))
    schools = {}
    for item in schools_raw:
        schools[item["id"]] = {
            "id": school_uid(item["id"]),
            "full_name": (item.get("full_name") or item.get("name") or "")[:120],
            "short_name": (item.get("short_name") or item.get("name") or "")[:60],
            "province": (item.get("province") or "")[:40],
            "city": (item.get("city") or "")[:40],
        }

    section_index: dict[tuple[str, str, str], str] = {}
    used_kids = {link["topic_id"] for link in leg["topic_link"].values() if link["topic_id"]}
    link_by_legacy = {link["legacy_id"]: link for link in leg["topic_link"].values()}
    nodes, kx_map, topic_stats = build_topics(used_kids, section_index, link_by_legacy)
    orphan_attached = topic_stats["orphans"] - topic_stats.get("orphans_unplaced", 0)

    # ---- 建空库 ----
    for suffix in ("", "-wal", "-shm"):
        stale = Path(str(out_path) + suffix)
        if stale.exists():
            stale.unlink()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(out_path)
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    con.executemany(
        "INSERT INTO schools (id, full_name, short_name, province, city, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [[s["id"], s["full_name"], s["short_name"], s["province"], s["city"],
          LOCAL_TZ_NOW, LOCAL_TZ_NOW] for s in schools.values()],
    )
    bad = [n for n in nodes if not re.fullmatch(r"tp_(bo|ch|se|kx)[0-9a-f]{8}", n["id"])
           or not n["path"].startswith("tp_") or not (1 <= len(n["name"]) <= 120)]
    if bad:
        raise AssertionError("节点违反表约束：%s" % json.dumps(bad[:3], ensure_ascii=False)[:400])
    con.executemany(
        "INSERT INTO topics (id, parent_id, name, path, sort_order, status, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [[n["id"], n["parent_id"], n["name"], n["path"], n["sort_order"], n["status"],
          LOCAL_TZ_NOW, LOCAL_TZ_NOW] for n in nodes],
    )

    sources: dict[str, dict[str, Any]] = {}
    questions: list[list[Any]] = []
    question_topics: list[list[Any]] = []
    question_sources: list[list[Any]] = []
    type_fix = {"single_to_multiple": 0, "letters_from_tail": 0, "answer_absent": 0,
               "manual_review": 0, "structure_conflict": 0}
    audit_rows: list[dict[str, Any]] = []
    layer_hits: dict[str, int] = {}

    for qid in sorted(docs):
        doc = docs[qid]
        legacy_id = doc["legacy_id"]
        answer_raw = leg["answer_raw"].get(legacy_id, "")
        current_answer = doc["answer"] or {}
        letters = letters_from_answer_region(answer_raw)
        source_of_letters = "答案区"
        if not letters and doc["type"] in CHOICE_TYPES:
            letters = letters_from_tail(answer_raw)
            if letters:
                source_of_letters = "正文尾句"
                type_fix["letters_from_tail"] += 1

        final_type = doc["type"]
        if doc["type"] in CHOICE_TYPES and letters:
            final_type = "multiple_choice" if len(letters) > 1 else "single_choice"
            if final_type != doc["type"]:
                type_fix["single_to_multiple"] += 1
                audit_rows.append({
                    "id": qid, "from": doc["type"], "to": final_type,
                    "letters": "".join(letters), "evidence": source_of_letters,
                })
        is_choice = doc["type"] in CHOICE_TYPES
        answer_value: str | None
        if is_choice and letters:
            answer_value = ",".join(letters)
        elif is_choice:
            answer_value = None          # 选择题取不到字母：如实留 NULL，不拿现库硬编码 A 冒充
        elif isinstance(current_answer, dict) and current_answer.get("kind") == "choice":
            keys = current_answer.get("choice_keys") or []
            answer_value = ",".join(keys) if keys else None
        elif isinstance(current_answer, dict) and current_answer.get("final"):
            answer_value = str(current_answer["final"])[:2000]
        else:
            answer_value = None

        old_link = leg["topic_link"].get(legacy_id) or {}
        extensions: list[dict[str, Any]] = []
        legacy_ext = (doc["extensions"] or {}).get("org.jiuzhang.legacy") or {}
        if doc["grade"]:
            extensions.append({"key": "org.jiuzhang.core-bank.grade", "label": "年级",
                               "value": {"grade": doc["grade"]}})
        if doc["textbook"] or doc["chapter"]:
            extensions.append({"key": "org.jiuzhang.core-bank.taxonomy", "label": "教材章节",
                               "value": {"textbook": doc["textbook"], "chapter": doc["chapter"],
                                         "section": old_link.get("section") or ""}})
        if doc["images"]:
            extensions.append({"key": "org.jiuzhang.core-bank.images", "label": "配图",
                               "value": {"images": doc["images"]}})
        option_columns = leg["option_columns"].get(legacy_id)
        if option_columns:
            extensions.append({"key": "org.jiuzhang.core-bank.option_columns", "label": "选项列数",
                               "value": {"columns": option_columns}})
        tikz_code = leg["tikz"].get(legacy_id) or legacy_ext.get("tikz_code", "")
        if tikz_code:
            extensions.append({"key": "org.jiuzhang.core-bank.tikz", "label": "TikZ 原码",
                               "value": {"code": tikz_code[:20000]}})
        flags: list[str] = []
        has_marker = bool(re.search(r"【答案】|答案\s*[:：]", answer_raw))
        if not answer_raw.strip():
            # 旧库连答案正文都没有：现库此前拿硬编码 A 兜底，属伪造，一律置 NULL 并标记
            flags.append("answer_absent" if is_choice else "solution_absent")
            if is_choice:
                type_fix["answer_absent"] += 1
        elif is_choice and not letters and has_marker:
            flags.append("answer_region_empty")   # 有【答案】标记但标记后是空白
        elif is_choice and not letters:
            flags.append("type_manual_review")    # 通篇解析、无结论标记
            type_fix["manual_review"] += 1
        if is_choice and not letters:
            type_fix["letters_absent"] = type_fix.get("letters_absent", 0) + 1
        if not is_choice and "\n" in str((doc["answer"] or {}).get("content") or ""):
            flags.append("needs_conclusion")   # 结论没单独成字段，整段解析当答案了
        if not is_choice and legacy_id in (421, 483):
            flags.append("structure_conflict")
            type_fix["structure_conflict"] += 1
        if not old_link.get("topic_id"):
            flags.append("topic_unmapped")     # 旧库没登记考向 id，本轮只挂到节/章
        if flags:
            extensions.append({"key": "org.jiuzhang.core-bank.migration", "label": "迁移标记",
                               "value": {"flags": flags, "run_at": LOCAL_TZ_NOW}})
        if (doc["extensions"] or {}).get("org.jiuzhang.editor"):
            extensions.append({"key": "org.jiuzhang.editor", "label": "录题插件私有数据",
                               "value": doc["extensions"]["org.jiuzhang.editor"]})

        questions.append([qid, final_type, doc["stem"],
                          json.dumps(doc["options"], ensure_ascii=False), answer_value,
                          doc["solution"] or None, json.dumps(extensions, ensure_ascii=False),
                          leg["difficulty"].get(legacy_id) or "L3",
                          doc["created_at"] or LOCAL_TZ_NOW, doc["updated_at"] or LOCAL_TZ_NOW])

        link = old_link
        if link:
            node_id = kx_map.get(link["topic_id"]) if link["topic_id"] else None
            layer = "kx"
            if not node_id:
                node_id = section_index.get((link["book"], link["chapter"], link["section"]))
                layer = "se"
            if not node_id:
                node_id = chapter_by_name.get((link["book"], link["chapter"]))
                layer = "ch"
            if node_id:
                question_topics.append([qid, node_id, 1, link["sort"] or 0, LOCAL_TZ_NOW])
                layer_hits[layer] = layer_hits.get(layer, 0) + 1
            else:
                layer_hits["none"] = layer_hits.get("none", 0) + 1

        title = str(doc["source"].get("paper_title") or "").strip()[:200]
        if not title:
            continue
        year, exam_type, grade_parsed = parse_source_title(title)
        school_id = leg["school_id"].get(legacy_id)
        school_uid_value = schools.get(school_id, {}).get("id") if school_id else None
        grade = grade_parsed or doc["grade"] or ""
        key = (school_uid_value or "", title, year, exam_type, grade)
        uid = source_uid(title, school_uid_value or "", year, exam_type, grade)
        if uid not in sources:
            sources[uid] = {"id": uid, "school_id": school_uid_value, "year": year,
                            "exam_type": exam_type, "paper_name": title, "grade": grade[:20]}
        question_sources.append([qid, uid, str(doc["source"].get("question_no") or "")[:20],
                                 LOCAL_TZ_NOW])
        _ = key

    con.executemany(
        "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
        " difficulty, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", questions)
    con.executemany(
        "INSERT INTO sources (id, school_id, year, exam_type, paper_name, grade, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [[s["id"], s["school_id"], s["year"], s["exam_type"], s["paper_name"], s["grade"],
          LOCAL_TZ_NOW, LOCAL_TZ_NOW] for s in sources.values()])
    con.executemany(
        "INSERT INTO question_topics (question_id, topic_id, is_primary, sort_order, created_at)"
        " VALUES (?, ?, ?, ?, ?)", question_topics)
    con.executemany(
        "INSERT INTO question_sources (question_id, source_id, question_no, created_at)"
        " VALUES (?, ?, ?, ?)", question_sources)

    notes: list[list[Any]] = []
    note_slot: dict[tuple[str, str], int] = {}
    dropped_notes = 0
    for note in leg["notes"]:
        parts = (note["key"] or "").split(":")
        note_type = NOTE_TYPE_MAP.get(note["type"])
        if not note_type:
            dropped_notes += 1
            continue
        if note_type == "knowledge":
            dropped_notes += 1
            continue      # knowledge 正文是导图 DSL（@mindmap/{...}），不是笔记散文，本轮不入表
        if len(parts) != 5:
            dropped_notes += 1
            continue
        _, book, chapter, section, kid = parts
        topic_id = kx_map.get(kid)
        if not topic_id:
            dropped_notes += 1
            continue
        slot_key = (topic_id, note_type)
        note_slot[slot_key] = note_slot.get(slot_key, -1) + 1
        body = strip_html(note["content"])
        if not body:
            dropped_notes += 1
            continue
        notes.append([topic_id, note_type, body, note_slot[slot_key], LOCAL_TZ_NOW, LOCAL_TZ_NOW])
    con.executemany(
        "INSERT INTO topic_notes (topic_id, note_type, content, sort_order, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?)", notes)
    con.execute("INSERT INTO bank_meta (key, value) VALUES (?, ?)",
                ("migrated_v063_at", json.dumps(LOCAL_TZ_NOW)))
    con.execute("INSERT INTO bank_meta (key, value) VALUES (?, ?)",
                ("sources_files", json.dumps([str(SCHOOLS_JSON), str(OUTLINE_JSON),
                                              str(LEGACY_DB), str(DOC_DB)])))
    con.execute("PRAGMA user_version = 1")
    con.commit()
    violations = list(con.execute("PRAGMA foreign_key_check"))
    counts = {t: con.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] for t in
              ("schools", "topics", "topic_notes", "sources", "questions",
               "question_topics", "question_sources", "bank_meta")}
    tree_sample = [tuple(r) for r in con.execute(
        "SELECT t.name, COUNT(q.question_id) FROM topics t"
        " LEFT JOIN question_topics q ON q.topic_id = t.id"
        " WHERE t.parent_id IS NULL GROUP BY t.id ORDER BY t.sort_order")]
    deep = [tuple(r) for r in con.execute(
        "SELECT p.name AS book, c.name AS chapter, s.name AS section, x.name AS topic,"
        " (SELECT COUNT(*) FROM question_topics q WHERE q.topic_id = x.id) AS hits"
        " FROM topics x JOIN topics s ON s.id = x.parent_id"
        " JOIN topics c ON c.id = s.parent_id JOIN topics p ON p.id = c.parent_id"
        " ORDER BY hits DESC, x.name LIMIT 5")]
    join_ok = con.execute(
        "SELECT COUNT(DISTINCT q.id) FROM questions q"
        " JOIN question_topics qt ON qt.question_id = q.id").fetchone()[0]
    src_ok = con.execute(
        "SELECT COUNT(DISTINCT q.id) FROM questions q"
        " JOIN question_sources qs ON qs.question_id = q.id").fetchone()[0]
    con.close()

    report = {
        "run_at": LOCAL_TZ_NOW,
        "target_db": str(out_path),
        "documents_in": stats["doc_rows"],
        "questions_written": counts["questions"],
        "legacy_rows_missing": leg["legacy_missing"],
        "counts": counts,
        "fk_violations": violations,
        "topic_stats": topic_stats,
        "orphans_attached": orphan_attached,
        "orphans_unplaced": topic_stats.get("orphans_unplaced", 0),
        "notes_written": len(notes),
        "notes_dropped": dropped_notes,
        "type_fix": type_fix,
        "type_audit": audit_rows,
        "schools_total": len(schools_raw),
        "outline_source": "A 版（人教A版 5 册）",
        "questions_with_topic": join_ok,
        "questions_with_source": src_ok,
        "mount_layer_hits": layer_hits,
        "sections_drafted": topic_stats.get("sections_drafted", 0),
        "sections_unresolved": topic_stats.get("sections_unresolved", 0),
        "outline_root_counts": tree_sample,
        "top_topics": deep,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    buf = io.StringIO()
    buf.write("# v0.6.3 灌库校验报告\n\n")
    buf.write("- 迁移时间：%s（本机本地钟）\n" % LOCAL_TZ_NOW)
    buf.write("- 目标库：`%s`\n" % out_path.relative_to(ROOT).as_posix())
    buf.write("- 现网库与在用种子**未改动**\n\n")
    buf.write("| 表 | 行数 |\n|---|---|\n")
    for name, value in counts.items():
        buf.write("| %s | %d |\n" % (name, value))
    buf.write("\n- 题目入表：%d / 文档读入 %d；外键违规 %s\n" % (
        counts["questions"], stats["doc_rows"], violations or "无"))
    buf.write("- 挂到考向的题目：%d 道；挂到来源的题目：%d 道\n" % (join_ok, src_ok))
    buf.write("- 大纲：册 %d / 章 %d / 节 %d / 考向 %d；大纲查无的旧考向 %d 个；"
              "按旧库节名补的 draft 节 %d 个（章查无 %d 个）\n" % (
                  topic_stats["books"], topic_stats["chapters"], topic_stats["sections"],
                  topic_stats["topics"], topic_stats["orphans"],
                  topic_stats.get("sections_drafted", 0), topic_stats.get("sections_unresolved", 0)))
    buf.write("- 题目挂载层别：%s\n" % json.dumps(layer_hits, ensure_ascii=False))
    buf.write("- 学校建档导入 %d 所；教研笔记入表 %d 条（丢弃 %d 条：knowledge 导图 DSL 与悬空键）\n" % (
        len(schools_raw), len(notes), dropped_notes))
    buf.write("- 题型纠偏：改判多选 %d 题（其中尾句补判 %d 题）；选择题答案全空 %d 题；题型待人工 %d 题；结构冲突 %d 题\n" % (
        type_fix["single_to_multiple"], type_fix["letters_from_tail"], type_fix["answer_absent"],
        type_fix["manual_review"], type_fix["structure_conflict"]))
    buf.write("\n## 大纲树首层（册 → 题数）\n\n```\n")
    for name, hits in tree_sample:
        buf.write("%s：%s 题挂载\n" % (name, hits))
    buf.write("```\n\n## 挂载最密的考向（前 5）\n\n| 册 | 章 | 节 | 考向 | 题数 |\n|---|---|---|---|---|\n")
    for row in deep:
        buf.write("| %s | %s | %s | %s | %s |\n" % row)
    if leg["legacy_missing"]:
        buf.write("\n## 旧库快照里找不到的题（%d）\n\n%s\n" % (
            len(leg["legacy_missing"]), leg["legacy_missing"]))
    REPORT_MD.write_text(buf.getvalue(), encoding="utf-8")

    print(json.dumps({"counts": counts, "fk_violations": violations, "type_fix": type_fix,
                      "questions_with_topic": join_ok, "questions_with_source": src_ok,
                      "notes_written": len(notes), "orphans_attached": orphan_attached,
                      "report_md": str(REPORT_MD)}, ensure_ascii=False, indent=2))

    if args.promote:
        import shutil
        SEED_NEW_DB.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out_path, SEED_NEW_DB)
        print("种子新库已写入：%s（%d B）" % (SEED_NEW_DB.name, SEED_NEW_DB.stat().st_size))
    return 1 if violations or counts["questions"] != stats["doc_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
