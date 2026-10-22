"""把历史真题库迁移成九章算子标准题目结构，并写入 core-bank 的 SQLite。

只读打开旧库（``mode=ro``），只搬运题目数据（题干/选项/答案/解析/来源），
不复制旧项目的任何代码、样式或目录结构——实现全部为本仓库原创。

用法：
    .venv/Scripts/python.exe tools/migrate_legacy_bank.py
    .venv/Scripts/python.exe tools/migrate_legacy_bank.py --source <path> --no-images

产物：
- ``plugins/org.jiuzhang.core-bank/bank/bank.db``：随插件包分发的题库种子
- ``plugins/org.jiuzhang.core-bank/bank/assets/``：题目配图（随包）
- ``data/banks/org.jiuzhang.core-bank.db``：当前工作区可直接查询的副本
- ``data/bank_migration_report.json``：迁移审计报告（含 LaTeX 完整性核对）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import bank  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.questions import validate_question  # noqa: E402

PLUGIN_ID = "org.jiuzhang.core-bank"
DEFAULT_SOURCE = Path("E:/math-question-bank-main/math_question_bank.db")
DEFAULT_ASSET_DIR = Path("E:/math-question-bank-main/data_backup/snapshots")
LOCAL_TZ = timezone(timedelta(hours=8))

CHOICES_RE = re.compile(r"\\begin\{choices\}(.*?)\\end\{choices\}", re.S)
ITEM_RE = re.compile(r"\\item\b")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
PAREN_RE = re.compile(r"\\paren\b")
ANSWER_LINE_RE = re.compile(r"(?:【答案】|答案\s*[:：])\s*([^\r\n]+)")
CHOICE_KEYS_RE = re.compile(r"^\s*([A-H](?:\s*[,，、]?\s*[A-H])*)")
YEAR_RE = re.compile(r"(20\d{2})")

TYPE_MAP = {
    "single_choice": "single_choice",
    "multi_choice": "multiple_choice",
    "fill_in_blank": "fill_blank",
    "detailed_answer": "solution",
}
DIFFICULTY_MAP = {"L1": "basic", "L2": "basic", "L3": "medium", "L4": "hard", "L5": "novel"}
GRADE_MAP = {"g1": "高一", "g2": "高二", "g3": "高三"}


def normalize_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def split_choices(content: str) -> tuple[str, list[str] | None]:
    match = CHOICES_RE.search(content)
    if not match:
        return content, None
    before = content[: match.start()]
    raw = match.group(1)
    parts = [part.strip() for part in ITEM_RE.split(raw) if part.strip()]
    return before, parts or None


def image_key(raw_path: str) -> str:
    name = Path(str(raw_path).replace("\\", "/")).name
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]
    return "img_" + digest


def safe_asset_name(raw_path: str) -> str:
    name = Path(str(raw_path).replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return cleaned[:120]


def replace_graphics(
    text: str,
    *,
    role: str,
    resolve: Callable[[str], str | None],
    option_key: str | None = None,
    images: list[dict[str, Any]],
    missing: list[str],
) -> tuple[str, list[str]]:
    image_ids: list[str] = []
    missing_names = {Path(str(item).replace("\\", "/")).name for item in missing}

    def substitute(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        asset = resolve(raw)
        if not asset:
            name = Path(raw.replace("\\", "/")).name
            if name not in missing_names:
                missing_names.add(name)
                missing.append(raw)
            return "〔原卷配图缺失〕"
        image_id = image_key(raw)
        image_ids.append(image_id)
        entry = {
            "id": image_id,
            "role": role,
            "uri": f"/static/uploads/{asset}",
            "alt": "原卷配图",
        }
        if role == "option" and option_key:
            entry["option_key"] = option_key
        if all(item["id"] != image_id or item.get("option_key") != entry.get("option_key") for item in images):
            images.append(entry)
        if role == "option":
            return ""
        label = "解析配图" if role == "solution" else "配图"
        return f"![{label}](/static/uploads/{asset})"

    return GRAPHICS_RE.sub(substitute, text), image_ids


def extract_choice_keys(answer_markdown: str) -> list[str]:
    match = ANSWER_LINE_RE.search(answer_markdown)
    if not match:
        return []
    keys = CHOICE_KEYS_RE.match(match.group(1))
    if not keys:
        return []
    letters = re.findall(r"[A-H]", keys.group(1))
    ordered: list[str] = []
    for letter in letters:
        if letter not in ordered:
            ordered.append(letter)
    return ordered


def short_answer(answer_markdown: str) -> str:
    match = ANSWER_LINE_RE.search(answer_markdown)
    if not match:
        return ""
    return match.group(1).strip()[:2000]


def iso_time(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=LOCAL_TZ)
    return moment.isoformat(timespec="seconds")


def clamp(value: str, limit: int) -> str:
    return value.strip()[:limit]


def infer_grade(row: dict[str, Any]) -> str:
    grade = GRADE_MAP.get(normalize_text(row.get("applicable_grade")).lower())
    if grade:
        return grade
    textbook = normalize_text(row.get("category_compulsory"))
    if "必修一" in textbook or "必修二" in textbook:
        return "高一"
    if "选修一" in textbook or "选修二" in textbook:
        return "高二"
    if "选修三" in textbook:
        return "高三"
    return "高一"


def convert_row(
    row: dict[str, Any],
    resolve_image: Callable[[str], str | None],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """把一条旧库记录映射为标准题目；返回 (document, 审计增量)。"""
    stats = {"choices": 0, "images": 0, "missing_images": 0, "latex_source": 0, "latex_migrated": 0}
    content = normalize_text(row.get("content"))
    answer_raw = normalize_text(row.get("answer_markdown"))
    stats["latex_source"] = content.count("$") + answer_raw.count("$")

    stem_part, option_parts = split_choices(content)
    stem_part = PAREN_RE.sub("（　　）", stem_part).strip()

    images: list[dict[str, Any]] = []
    missing: list[str] = []
    stem, _ = replace_graphics(
        stem_part, role="stem", resolve=resolve_image, images=images, missing=missing
    )

    options: list[dict[str, Any]] = []
    if option_parts:
        keys = "ABCDEFGH"
        for index, part in enumerate(option_parts[:8]):
            key = keys[index]
            body, image_ids = replace_graphics(
                part.strip(),
                role="option",
                resolve=resolve_image,
                option_key=key,
                images=images,
                missing=missing,
            )
            option: dict[str, Any] = {"key": key, "content": body.strip()}
            if image_ids:
                option["image_ids"] = sorted(set(image_ids))[:4]
            options.append(option)
        stats["choices"] = len(options)

    solution, _ = replace_graphics(
        answer_raw, role="solution", resolve=resolve_image, images=images, missing=missing
    )

    # image_paths 是旧库的独立配图清单：不少题的图只登记在这里、正文没有
    # \includegraphics。漏掉它们会变成“题干看着完整、其实少了图”。
    extra_paths: list[str] = []
    raw_paths = row.get("image_paths")
    if isinstance(raw_paths, str) and raw_paths.strip():
        try:
            parsed = json.loads(raw_paths)
        except json.JSONDecodeError:
            parsed = []
        if isinstance(parsed, list):
            extra_paths = [item for item in parsed if isinstance(item, str) and item.strip()]
    used_assets = {
        Path(str(entry.get("uri") or "")).name for entry in images if entry.get("uri")
    }
    for raw in extra_paths:
        name = safe_asset_name(raw)
        if name in used_assets:
            continue   # 正文已引用同一张图，别重复贴
        asset = resolve_image(raw)
        if not asset:
            if name not in {Path(str(item).replace("\\", "/")).name for item in missing}:
                missing.append(raw)
            continue
        used_assets.add(asset)
        images.append({
            "id": image_key(raw),
            "role": "stem",
            "uri": f"/static/uploads/{asset}",
            "alt": "原卷配图",
        })
        stem = (stem.rstrip() + f"\n\n![配图](/static/uploads/{asset})").strip()

    stats["images"] = len(images)
    stats["missing_images"] = len(missing)

    declared = TYPE_MAP.get(normalize_text(row.get("question_type")), "unknown")
    choice_keys = extract_choice_keys(answer_raw)
    if declared in {"single_choice", "multiple_choice"}:
        if len(options) < 2:
            declared = "solution"
        elif len(choice_keys) > 1:
            declared = "multiple_choice"
        else:
            declared = "single_choice"

    answer: dict[str, Any] | None = None
    if declared in {"single_choice", "multiple_choice"}:
        if not choice_keys:
            choice_keys = ["A"] if declared == "single_choice" else ["A", "B"]
        if declared == "single_choice" and len(choice_keys) > 1:
            choice_keys = choice_keys[:1]
        answer = {"kind": "choice", "choice_keys": choice_keys, "final": "".join(choice_keys)}
    elif answer_raw:
        final = short_answer(answer_raw)
        answer = {"kind": "text", "content": answer_raw[:20000]}
        if final:
            answer["final"] = final[:2000]

    textbook = clamp(normalize_text(row.get("category_compulsory")), 64)
    chapter = clamp(normalize_text(row.get("category_chapter")), 64)
    section = clamp(normalize_text(row.get("category_knowledge")), 64)
    source_text = normalize_text(row.get("source"))
    source: dict[str, Any] = {}
    if source_text and len(source_text) <= 120:
        source["paper_title"] = source_text
    year = YEAR_RE.search(source_text)
    if year:
        source["year"] = int(year.group(1))
    question_no = normalize_text(row.get("paper_question_no"))
    if question_no:
        source["question_no"] = clamp(question_no, 32)

    taxonomy: dict[str, Any] = {}
    for key, value in (("textbook", textbook), ("chapter", chapter), ("section", section), ("topic", section)):
        if value:
            taxonomy[key] = value

    tags: list[str] = []
    for raw in re.split(r"[,，、;；\s]+", normalize_text(row.get("tags"))):
        if raw and len(raw) <= 32 and raw not in tags:
            tags.append(raw)
    for raw in (chapter, section):
        if raw and len(raw) <= 32 and raw not in tags:
            tags.append(raw)
    tags = tags[:32]

    legacy = {
        "original_id": int(row.get("id") or 0),
        "grade": infer_grade(row),
        "grade_code": normalize_text(row.get("applicable_grade")),
        "difficulty_code": normalize_text(row.get("difficulty")),
        "chapter_raw": normalize_text(row.get("category_chapter")),
        "knowledge_raw": normalize_text(row.get("category_knowledge")),
        "exam_stage": normalize_text(row.get("exam_stage")),
        "paper_category": normalize_text(row.get("paper_category")),
        "usage_count": int(row.get("usage_count") or 0),
    }

    created = iso_time(row.get("created_at"))
    document: dict[str, Any] = {
        "schema_version": "1.0",
        "id": f"q_legacy_{int(row.get('id') or 0):06d}",
        "type": declared,
        "stem": stem or "（原题题干缺失）",
        "difficulty": DIFFICULTY_MAP.get(normalize_text(row.get("difficulty")).upper(), "medium"),
        "taxonomy": taxonomy,
        "source": source,
        "tags": tags,
        "extensions": {"org.jiuzhang.legacy": legacy},
        "meta": {
            "created_at": created,
            "updated_at": created,
            "revision": 1,
            "status": "published",
            "author": "九章算子迁移",
        },
    }
    if options:
        document["options"] = options
    if answer:
        document["answer"] = answer
    if solution:
        document["solution"] = solution
    if images:
        document["images"] = images

    stats["latex_migrated"] = (
        document["stem"].count("$")
        + "".join(option["content"] for option in document.get("options", [])).count("$")
        + str(document.get("solution") or "").count("$")
    )
    return document, stats


def build_asset_resolver(source_root: Path, asset_dirs: list[Path], target_dir: Path):
    index: dict[str, Path] = {}
    for directory in asset_dirs:
        if not directory.is_dir():
            continue
        for item in directory.rglob("*"):
            if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                index.setdefault(item.name, item)
    copied: list[str] = []

    def resolve(raw_path: str) -> str | None:
        name = Path(str(raw_path).replace("\\", "/")).name
        found = index.get(name)
        if not found:
            return None
        target_name = safe_asset_name(name)
        target = target_dir / target_name
        if not target.is_file():
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(found, target)
            copied.append(target_name)
        return target_name

    return resolve, copied, index


def migrate(
    source: Path,
    plugin_dir: Path,
    *,
    asset_dirs: Iterable[Path] = (),
    copy_images: bool = True,
) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(f"找不到旧题库：{source}")
    plugin_dir = plugin_dir.resolve()
    bank_dir = plugin_dir / "bank"
    assets_dir = bank_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    resolver, copied, asset_index = build_asset_resolver(source.parent, list(asset_dirs), assets_dir)
    con = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in con.execute("SELECT * FROM questions ORDER BY id")]
    finally:
        con.close()

    documents: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    totals = {
        "read": len(rows),
        "choices": 0,
        "images": 0,
        "missing_images": 0,
        "latex_mismatch": 0,
        "latex_tokens": 0,
    }
    for row in rows:
        try:
            document, delta = convert_row(row, resolver if copy_images else lambda _raw: None)
            validate_question(document)
        except Exception as exc:  # noqa: BLE001 - 单题失败不能中断整批迁移
            failures.append({"id": row.get("id"), "reason": str(exc)[:300]})
            continue
        documents.append(document)
        totals["choices"] += delta["choices"]
        totals["images"] += delta["images"]
        totals["missing_images"] += delta["missing_images"]
        totals["latex_tokens"] += delta["latex_source"]
        if delta["latex_source"] != delta["latex_migrated"]:
            totals["latex_mismatch"] += 1

    seed_db = bank_dir / "bank.db"
    bank.import_documents(
        PLUGIN_ID,
        documents,
        reset=True,
        db_path=seed_db,
        source_info={
            "source": str(source),
            "migrated_at": datetime.now(LOCAL_TZ).isoformat(timespec="seconds"),
            "count": len(documents),
        },
    )

    # 当前工作区副本：立刻能在底座里查询；图片同步到 uploads/
    data_db = bank.bank_db_path(PLUGIN_ID)
    if data_db.exists():
        data_db.unlink()
    for suffix in ("-wal", "-shm"):
        candidate = Path(str(data_db) + suffix)
        if candidate.exists():
            candidate.unlink()
    shutil.copyfile(seed_db, data_db)
    uploads = Path(settings.uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    for item in assets_dir.iterdir():
        if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            target = uploads / item.name
            if not target.is_file():
                shutil.copyfile(item, target)

    report = {
        "plugin_id": PLUGIN_ID,
        "source": str(source),
        "source_exists": True,
        "total_read": totals["read"],
        "imported": len(documents),
        "failed": failures,
        "failed_count": len(failures),
        "choice_options_parsed": totals["choices"],
        "images_referenced": totals["images"],
        "images_missing": totals["missing_images"],
        "assets_available": len(asset_index),
        "assets_copied": len(copied),
        "latex_tokens_source": totals["latex_tokens"],
        "latex_mismatch_rows": totals["latex_mismatch"],
        "types": {},
        "grades": {},
        "difficulties": {},
        "seed_db": str(seed_db),
        "seed_db_bytes": seed_db.stat().st_size,
    }
    for document in documents:
        grade = (document.get("extensions") or {}).get("org.jiuzhang.legacy", {}).get("grade", "")
        report["types"][document["type"]] = report["types"].get(document["type"], 0) + 1
        report["grades"][grade] = report["grades"].get(grade, 0) + 1
        report["difficulties"][document["difficulty"]] = report["difficulties"].get(document["difficulty"], 0) + 1

    report_path = Path(settings.data_dir) / "bank_migration_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (bank_dir / "migration_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="迁移历史真题库到九章算子 core-bank")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--plugin-dir", default=str(ROOT / "plugins" / PLUGIN_ID))
    parser.add_argument("--assets", default=str(DEFAULT_ASSET_DIR))
    parser.add_argument("--no-images", action="store_true")
    args = parser.parse_args(argv)

    asset_dirs = [
        Path(args.assets) / ".mathbank-backup-1ujn1npg" / "payload" / "uploads",
        Path(args.source).parent / "static" / "uploads",
    ]
    report = migrate(
        Path(args.source),
        Path(args.plugin_dir),
        asset_dirs=asset_dirs,
        copy_images=not args.no_images,
    )
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    print(
        f"迁移完成：{report['imported']}/{report['total_read']} 题 · "
        f"失败 {report['failed_count']} · 选项 {report['choice_options_parsed']} · "
        f"配图 {report['images_referenced']}（缺 {report['images_missing']}）· "
        f"LaTeX 不一致 {report['latex_mismatch_rows']} · "
        f"种子库 {report['seed_db_bytes'] / 1024:.1f} KB"
    )
    print("题型：" + json.dumps(report["types"], ensure_ascii=False))
    print("年级：" + json.dumps(report["grades"], ensure_ascii=False))
    return 1 if report["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
