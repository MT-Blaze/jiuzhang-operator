# -*- coding: utf-8 -*-
"""题库图片资产校验：找出引用了却不在 uploads 里的图，能补的当场补上。

用法::

    .venv/Scripts/python.exe tools/check_image_assets.py            # 只读报表
    .venv/Scripts/python.exe tools/check_image_assets.py --apply    # 用本地同名文件补齐
    .venv/Scripts/python.exe tools/check_image_assets.py --json .system_generated/image_assets.json

排查口径：
- 引用来源四处——题干/解析里的 ``![...](...)`` 与 ``\\includegraphics{...}``、
  ``images`` 数组的 ``uri``、选项的 ``image_ids``（并核对 id 是否真在 images 里）；
- 只认 ``/static/uploads/`` 是本地文件引用，``asset://`` / 远程 URL / ``data:`` 单列，
  不当缺失；
- 迁移器留下的「〔原卷配图缺失〕」占位符单列统计：这类图已不在 uri 里，
  只扫引用会假报「零缺失」；
- ``--apply`` 只往 uploads 里**新增**同名文件，绝不覆盖已有文件、绝不改数据库；
  补图来源默认是 ``data/`` 下其它工作区的 uploads（本机已有副本），也可用 ``--source`` 指定。
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UPLOAD_PREFIX = "/static/uploads/"
IMAGE_REF = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)|\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
LOCAL_IMAGE = re.compile(r"^/static/uploads/[^\s]+$")
NON_LOCAL_PREFIXES = ("asset://", "http://", "https://", "//", "data:", "file:")
# 迁移器把找不到的原卷配图写成占位符，图便不再出现在 uri 里；
# 只扫 uri 会误报「零缺失」，所以占位符必须单列一项。
PLACEHOLDER = "〔原卷配图缺失〕"


def discover_databases(data_dir: Path) -> list[Path]:
    found: list[Path] = []
    for path in sorted(data_dir.rglob("*.db")):
        if path.name.endswith(("-wal", "-shm")):
            continue
        found.append(path)
    return found


def uploads_for(db: Path) -> Path | None:
    for parent in db.parents:
        candidate = parent / "uploads"
        if candidate.is_dir():
            return candidate
    return None


def _loads(raw: Any, fallback: Any) -> Any:
    if not isinstance(raw, str) or not raw.strip():
        return fallback
    try:
        return json.loads(raw)
    except ValueError:
        return fallback


def _images_from_row(row: sqlite3.Row, seven_table: bool) -> list[dict[str, Any]]:
    if not seven_table:
        images = _loads(row["images_json"], [])
        return [item for item in images if isinstance(item, dict)] if isinstance(images, list) else []
    images: list[dict[str, Any]] = []
    for entry in _loads(row["extensions"], []):
        if not isinstance(entry, dict) or not str(entry.get("key") or "").endswith(".images"):
            continue
        value = entry.get("value")
        if isinstance(value, dict):
            images.extend(item for item in value.get("images") or [] if isinstance(item, dict))
    return images


def scan_database(db: Path, sources: list[Path]) -> dict[str, Any] | None:
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in con.execute("select name from sqlite_master where type='table'")}
        if "questions" not in tables:
            return None
        columns = {row[1] for row in con.execute("PRAGMA table_info(questions)")}
        seven_table = "extensions" in columns
        options_column = "options" if seven_table else "options_json"
        extra_column = "extensions" if seven_table else "images_json"
        rows = con.execute(
            f"select id, stem, solution, {options_column} as options, {extra_column} as {extra_column}"
            f" from questions"
        ).fetchall()
    finally:
        con.close()

    uploads = uploads_for(db)
    uri_counts: collections.Counter[str] = collections.Counter()
    id_counts: collections.Counter[str] = collections.Counter()
    roles: collections.Counter[str] = collections.Counter()
    dangling: list[dict[str, str]] = []
    placeholder_rows: list[str] = []
    placeholder_count = 0

    for row in rows:
        row_placeholders = 0
        for text in (row["stem"] or "", row["solution"] or ""):
            row_placeholders += text.count(PLACEHOLDER)
            for match in IMAGE_REF.finditer(text):
                uri = (match.group(1) or match.group(2) or "").strip()
                if uri:
                    uri_counts[uri] += 1
        if row_placeholders:
            placeholder_count += row_placeholders
            placeholder_rows.append(str(row["id"]))
        images = _images_from_row(row, seven_table)
        known_ids = set()
        for image in images:
            uri = str(image.get("uri") or "")
            image_id = str(image.get("id") or "")
            if uri:
                uri_counts[uri] += 1
            if image_id:
                id_counts[image_id] += 1
                known_ids.add(image_id)
            roles[str(image.get("role") or "?")] += 1
        options = _loads(row["options"], [])
        for option in options if isinstance(options, list) else []:
            if not isinstance(option, dict):
                continue
            for image_id in option.get("image_ids") or []:
                id_counts["option:" + str(image_id)] += 1
                if str(image_id) not in known_ids:
                    dangling.append({"question": str(row["id"]), "image_id": str(image_id)})

    missing: dict[str, int] = {}
    non_local: collections.Counter[str] = collections.Counter()
    for uri, count in uri_counts.items():
        if uri.startswith(NON_LOCAL_PREFIXES):
            non_local[uri] += count
            continue
        if not LOCAL_IMAGE.match(uri):
            non_local[uri] += count
            continue
        if uploads is None or not (uploads / Path(uri).name).is_file():
            missing[uri] = count

    restored: list[dict[str, str]] = []
    if uploads is not None:
        for uri in list(missing):
            name = Path(uri).name
            for source in sources:
                candidate = source / name
                if not candidate.is_file():
                    continue
                if (uploads / name).exists():
                    break
                uploads.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, uploads / name)
                restored.append({"uri": uri, "from": str(candidate)})
                break
    for item in restored:
        missing.pop(item["uri"], None)

    return {
        "db": str(db),
        "uploads": str(uploads) if uploads else "",
        "questions": len(rows),
        "references": sum(uri_counts.values()),
        "distinct_uris": len(uri_counts),
        "image_entries": sum(roles.values()),
        "roles": dict(roles),
        "option_links": sum(v for k, v in id_counts.items() if k.startswith("option:")),
        "dangling_option_links": dangling,
        "non_local": dict(non_local),
        "missing": missing,
        "restored": restored,
        "placeholder_count": placeholder_count,
        "placeholder_rows": placeholder_rows,
    }


def default_sources(data_dir: Path) -> list[Path]:
    return sorted({path for path in data_dir.rglob("uploads") if path.is_dir()})


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    parser = argparse.ArgumentParser(description="题库图片资产校验与本地补齐")
    parser.add_argument("--data-dir", default=str(ROOT / "data"), help="工作区根目录（默认 data/）")
    parser.add_argument("--source", action="append", default=[], help="补图来源目录，可重复")
    parser.add_argument("--apply", action="store_true", help="把找到的同名文件复制进 uploads")
    parser.add_argument("--json", default="", help="报表落盘路径")
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir).resolve()
    if not data_dir.is_dir():
        print("找不到数据目录：" + str(data_dir))
        return 2
    sources = [Path(item).resolve() for item in args.source] or default_sources(data_dir)

    reports: list[dict[str, Any]] = []
    for db in discover_databases(data_dir):
        try:
            report = scan_database(db, sources if args.apply else [])
        except sqlite3.DatabaseError as exc:
            print("跳过不可读数据库：%s（%s）" % (db, exc))
            continue
        if not report:
            continue
        reports.append(report)

    total_missing = total_restored = total_placeholders = 0
    for report in reports:
        total_missing += len(report["missing"])
        total_restored += len(report["restored"])
        total_placeholders += report["placeholder_count"]
        print("=" * 78)
        print(report["db"])
        print("  uploads: %s" % (report["uploads"] or "（未找到 uploads 目录）"))
        print("  题目 %d · 引用 %d 处 / %d 个地址 · images %d 条 / 角色 %s"
              % (report["questions"], report["references"], report["distinct_uris"],
                 report["image_entries"], report["roles"] or "{}"))
        print("  选项关联 %d 条 · 悬空 id %d 条"
              % (report["option_links"], len(report["dangling_option_links"])))
        if report["non_local"]:
            print("  非本地地址 %d 个（asset:// 或远程，不计缺失）" % len(report["non_local"]))
        if report["restored"]:
            print("  已补齐 %d 张：" % len(report["restored"]))
            for item in report["restored"]:
                print("    + %s  ←  %s" % (item["uri"], item["from"]))
        if report["missing"]:
            print("  缺失 %d 张：" % len(report["missing"]))
            for uri, count in sorted(report["missing"].items()):
                print("    - %s（被引用 %d 次）" % (uri, count))
        else:
            print("  缺失 0 张")
        if report["placeholder_rows"]:
            print("  未落位占位符 %d 处 / %d 题：%s"
                  % (report["placeholder_count"], len(report["placeholder_rows"]),
                     "、".join(report["placeholder_rows"])))

    print("=" * 78)
    print("合计：数据库 %d 个 · 缺失 %d 张 · 补齐 %d 张 · 未落位占位符 %d 处"
          % (len(reports), total_missing, total_restored, total_placeholders))
    if args.json:
        target = Path(args.json)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"reports": reports}, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print("报表已写入 " + str(target))
    if not args.apply:
        print("（只读模式；加 --apply 才把本机已有的同名图片复制进 uploads）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
