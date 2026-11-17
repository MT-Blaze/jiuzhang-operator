# -*- coding: utf-8 -*-
"""文字层 PDF 真卷复验：页脚、裸页码与题号取顶改动的回归探针。

链路严格照生产：``pypdfium2`` 取字 → ``_pdf_text_lines`` 行清单 →
``page_render_regions._question_regions``。不跑 OCR，不写 ``data/``。

产物：``.system_generated/textlayer_probe/<tag>/``
- ``regions.toml``：每页每题的 (no, x, y, w, h) 与 label；
- ``probe.toml``：§7.1 五项、四条判据、改前/改后逐题差异；
- ``q01_p1.png`` / ``q19_p4.png`` / ``q_last_p5.png``：真截图。

用法：``.venv/Scripts/python.exe tools/textlayer_probe.py [tag]``

判据（与任务卡一致，不放宽）：
a) 题号主链从 1 开始且无断号；与台账 26 个命中不等时逐项说明差额。
b) 「第N页（共M页）」「第N页/共M页」与页底裸数字页码都不进任何题 text/框。
c) 框顶覆盖同段最高行（题号行与公式/上标同视觉行时不被裁掉）。
d) 任一题 text 不含下一题题干开头。
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pypdfium2 as pdfium  # noqa: E402

from app.core import toml_io  # noqa: E402
from app.core.page_render_common import PDF_RENDER_DPI  # noqa: E402
from app.core.page_render_regions import (  # noqa: E402
    _PDF_FOOTER, _PDF_HEAD, _PDF_INSTRUCTION, _PDF_SECTION, _ink_rows,
    _longest_number_run, _pdf_text_lines, _question_regions,
)

PAPER_ROOT = Path(r"E:/Math/高中/题库/期中期末真题")
PAPER_REL = "高一/上/期末/【数学】哈九中2024-2025学年高一上学期期末考试试题（含答案）.pdf"
LEDGER_CHARS = 4118
LEDGER_HEADS = 26
LEDGER_PAGES = 5
BASELINE_COMMIT = "6d2832e"  # 改动前：页脚只认括号式、题号行不取顶
OUT_ROOT = ROOT / ".system_generated" / "textlayer_probe"
SCALE = PDF_RENDER_DPI / 72.0
BARE_PAGE_ZONE = 0.08
BARE_PAGE_HEIGHT_RATIO = 0.85

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def _crop_png(raw: bytes, width: int, height: int, stride: int, channels: int,
              rev: bool, region: dict[str, Any]) -> bytes:
    x0 = max(0, int(round(region["x"])))
    y0 = max(0, int(round(region["y"])))
    x1 = min(width, int(round(region["x"] + region["w"])))
    y1 = min(height, int(round(region["y"] + region["h"])))
    x1 = max(x0 + 1, x1)
    y1 = max(y0 + 1, y1)
    crop_width = x1 - x0
    rows: list[bytes] = []
    for y in range(y0, y1):
        start = y * stride + x0 * channels
        line = raw[start:start + crop_width * channels]
        rgb = bytearray(crop_width * 3)
        if rev:
            rgb[0::3] = line[0::3]
            rgb[1::3] = line[1::3]
            rgb[2::3] = line[2::3]
        else:
            rgb[0::3] = line[2::3]
            rgb[1::3] = line[1::3]
            rgb[2::3] = line[0::3]
        rows.append(b"\x00" + bytes(rgb))
    return (_PNG_SIGNATURE
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", crop_width, y1 - y0,
                                               8, 2, 0, 0, 0))
            + _png_chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
            + _png_chunk(b"IEND", b""))


def _render_raw(document: Any, index: int) -> tuple[bytes, int, int, int, int, bool]:
    page = document[index]
    try:
        bitmap = page.render(scale=SCALE)
        try:
            return (bytes(bitmap.buffer), int(bitmap.width), int(bitmap.height),
                    int(bitmap.stride), int(bitmap.n_channels),
                    bool(bitmap.rev_byteorder))
        finally:
            bitmap.close()
    finally:
        page.close()


def _load_baseline(out_dir: Path) -> Any | None:
    """从基线提交取出改动前的模块，落在产物目录里导入；不碰工作树。"""
    try:
        source = subprocess.run(
            ["git", "show", BASELINE_COMMIT + ":app/core/page_render_regions.py"],
            cwd=ROOT, capture_output=True, check=True).stdout
    except Exception:  # noqa: BLE001 - 没 git 就只跑现行版本
        return None
    path = out_dir / "_baseline_page_render_regions.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("_baseline_regions", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _page_view(lines: list[dict[str, Any]], first_page: bool) -> dict[str, Any]:
    """复现 ``_question_regions`` 的行过滤与题号链，供判据取证。"""
    footer_top = min((line["top"] for line in lines if _PDF_FOOTER.search(line["text"])),
                     default=None)
    content = [line for line in lines if not _PDF_FOOTER.search(line["text"])]
    start_at = 0
    if first_page:
        section = next((index for index, line in enumerate(content)
                        if _PDF_SECTION.match(line["text"])), None)
        if section is not None:
            start_at = section
    heads: list[tuple[int, int]] = []
    for position, line in enumerate(content):
        if position < start_at:
            continue
        matched = _PDF_HEAD.match(line["text"])
        if not matched or _PDF_INSTRUCTION.search(line["text"]):
            continue
        heads.append((position, int(matched.group(1))))
    return {"footer_top": footer_top, "content": content, "heads": heads,
            "run": _longest_number_run(heads), "start_at": start_at}


def _overlap_top(content: list[dict[str, Any]], head: dict[str, Any]) -> float:
    """与题号行纵向重叠的行里最高的上沿（切题取顶的依据）。"""
    top = head["top"]
    for other in content:
        if other is head:
            continue
        overlap = min(other["top"], head["top"]) - max(other["bottom"],
                                                       head["bottom"])
        if overlap > 0:
            top = max(top, other["top"])
    return top


def _first_ink_row(ink: bytearray, row_top: float, row_bottom: float,
                   page_height: float) -> int | None:
    start = max(0, int(round((page_height - row_top) * SCALE)))
    stop = min(len(ink), int(round((page_height - row_bottom) * SCALE)) + 1)
    for row in range(start, stop):
        if ink[row]:
            return row
    return None


def _inject_footer(lines: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """把本页最底下那行的文字换成页脚（坐标不动），只做内存注入。"""
    copied = [dict(line) for line in lines]
    lowest = min(range(len(copied)), key=lambda index: copied[index]["bottom"])
    copied[lowest]["text"] = text
    return copied


def _normalise(text: str) -> str:
    return "".join(char for char in text if not char.isspace())


def _has_hanzi(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    return (ordered[middle] if len(ordered) % 2
            else (ordered[middle - 1] + ordered[middle]) / 2)


def _bare_footer_lines(lines: list[dict[str, Any]], page_height: float) -> list[dict[str, Any]]:
    """独立复核裸页码三判据；与生产实现分开写，避免用被测代码自证。"""
    zone = page_height * BARE_PAGE_ZONE
    median = _median([line["top"] - line["bottom"] for line in lines
                      if _has_hanzi(line["text"])])
    if median <= 0:
        return []
    limit = median * BARE_PAGE_HEIGHT_RATIO
    return [line for line in lines
            if line["top"] <= zone
            and re.fullmatch(r"\s*\d{1,3}\s*", line["text"])
            and line["top"] - line["bottom"] < limit]


def _stem_prefix(region: dict[str, Any], length: int = 12) -> str:
    lines = [line for line in region.get("text", "").splitlines() if line.strip()]
    if len(lines) < 2:
        return ""
    return _normalise(lines[1])[:length]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", nargs="?", default="h9z2024-a1")
    args = parser.parse_args()
    tag = args.tag
    out_dir = OUT_ROOT / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = PAPER_ROOT / PAPER_REL
    if not pdf_path.is_file():
        print("找不到素材：" + str(pdf_path))
        return 2

    baseline = _load_baseline(out_dir)
    document = pdfium.PdfDocument(pdf_path.read_bytes())
    page_count = len(document)
    pages: list[dict[str, Any]] = []
    chars_raw = 0
    head_hits: list[dict[str, Any]] = []
    try:
        for index in range(page_count):
            page = document[index]
            try:
                page_width, page_height = (float(value) for value in page.get_size())
                textpage = page.get_textpage()
                try:
                    chars_raw += len(textpage.get_text_range())
                finally:
                    textpage.close()
                lines = _pdf_text_lines(page)
            finally:
                page.close()
            raw, width, height, stride, channels, rev = _render_raw(document, index)
            ink = _ink_rows(raw, width, height, stride, channels)
            first_page = index == 0
            regions = _question_regions(lines, page_width, page_height, width, height,
                                        ink_rows=ink, first_page=first_page)
            regions_noink = _question_regions(lines, page_width, page_height, width,
                                              height, first_page=first_page)
            old_regions = (baseline._question_regions(
                lines, page_width, page_height, width, height, ink_rows=ink,
                first_page=first_page) if baseline is not None else None)
            old_noink = (baseline._question_regions(
                lines, page_width, page_height, width, height,
                first_page=first_page) if baseline is not None else None)
            view = _page_view(lines, first_page)
            bare_footer = _bare_footer_lines(lines, page_height)
            for position, number in view["heads"]:
                head_hits.append({"page": index + 1, "no": number,
                                  "text": view["content"][position]["text"][:40]})
            pages.append({
                "page": index + 1, "width": width, "height": height,
                "page_width": page_width, "page_height": page_height,
                "lines": lines, "ink": ink, "regions": regions,
                "regions_noink": regions_noink, "view": view,
                "bare_footer": bare_footer,
                "old_regions": old_regions, "old_noink": old_noink,
            })
    finally:
        document.close()

    # ---------- a) 题号主链 ----------
    ordered_heads = [(hit["page"], hit["no"], hit["text"]) for hit in head_hits]
    used: set[int] = set()
    expected = 1
    primary: list[tuple[int, int]] = []
    for index, (page_no, number, _text) in enumerate(ordered_heads):
        if number == expected:
            used.add(index)
            primary.append((page_no, number))
            expected += 1
    extras = [ordered_heads[index] for index in range(len(ordered_heads))
              if index not in used]
    main_numbers = [number for _page, number in primary]
    main_last_page = primary[-1][0] if primary else 0
    chain_ok = (bool(primary) and main_numbers[0] == 1
                and main_numbers == list(range(1, len(main_numbers) + 1)))
    page_region_numbers = [region["no"] for page in pages for region in page["regions"]]
    main_page_regions = [region["no"] for page in pages
                         if page["page"] <= main_last_page
                         for region in page["regions"]]
    chain_matches_regions = main_page_regions == list(range(1, len(main_numbers) + 1))
    ledger_delta = len(ordered_heads) - LEDGER_HEADS
    criterion_a = chain_ok and chain_matches_regions and ledger_delta == 0

    # ---------- b) 两种页脚注入 ----------
    footer_cases: list[dict[str, Any]] = []
    for page in pages:
        page_no = page["page"]
        for form in ("paren", "slash"):
            text = ("第%d页（共%d页）" % (page_no, page_count) if form == "paren"
                    else "第%d页/共%d页" % (page_no, page_count))
            injected = _inject_footer(page["lines"], text)
            regions = _question_regions(
                injected, page["page_width"], page["page_height"], page["width"],
                page["height"], ink_rows=page["ink"], first_page=page_no == 1)
            footer_line = min(injected, key=lambda line: line["bottom"])
            footer_top_px = (page["page_height"] - footer_line["top"]) * SCALE
            leaked_text = [region["no"] for region in regions
                           if _normalise(text) in _normalise(region["text"])]
            leaked_box = ([regions[-1]["no"]] if regions and
                          regions[-1]["y"] + regions[-1]["h"] > footer_top_px + 0.6
                          else [])
            old_flags: dict[str, Any] = {}
            if baseline is not None and page["old_regions"] is not None:
                old_regions = baseline._question_regions(
                    injected, page["page_width"], page["page_height"], page["width"],
                    page["height"], ink_rows=page["ink"], first_page=page_no == 1)
                old_flags = {
                    "old_text_leak": [region["no"] for region in old_regions
                                      if _normalise(text) in _normalise(region["text"])],
                    "old_box_leak": (old_regions[-1]["no"] if old_regions and
                                     old_regions[-1]["y"] + old_regions[-1]["h"]
                                     > footer_top_px + 0.6 else None),
                }
            footer_cases.append({"page": page_no, "form": form, "text": text,
                                 "text_leak": leaked_text, "box_leak": leaked_box,
                                 "old": old_flags})
    criterion_b = all(not case["text_leak"] and not case["box_leak"]
                      for case in footer_cases)

    # 本卷真实页脚是裸页码（页底真图 foot_p*.png 已证），不是两种中文写法。
    # 逐页核验：底边那行若是水印，还要把夹在其上方、满足三判据的裸页码一并取来。
    real_footer_rows: list[dict[str, Any]] = []
    for page in pages:
        if not page["regions"]:
            continue
        last = page["regions"][-1]
        lowest = min(page["lines"], key=lambda line: (line["bottom"], line["left"]))
        candidates = [lowest]
        candidates.extend(line for line in page["bare_footer"] if line is not lowest)
        footer_top_pt = max(line["top"] for line in candidates)
        top_px = (page["page_height"] - footer_top_pt) * SCALE
        norm_last = _normalise(last["text"])
        norm_lines = {_normalise(item) for item in last["text"].splitlines()}
        for line in candidates:
            text = line["text"].strip()
            page_digit = bool(re.search(r"(?:^|\s)%d$" % page["page"], text))
            norm_text = _normalise(text)
            in_text = bool(norm_text) and (
                norm_text in norm_lines
                or (len(norm_text) < 8 and norm_last.endswith(norm_text)))
            in_box = last["y"] + last["h"] > top_px + 0.6
            real_footer_rows.append({
                "page": page["page"], "lowest_text": text[:60],
                "page_digit": page_digit,
                "recognised": bool(_PDF_FOOTER.search(text)),
                "in_last_text": in_text, "in_last_box": in_box,
                "last_no": last["no"], "last_bottom": round(last["y"] + last["h"], 1),
                "footer_top_px": round(top_px, 1),
            })
    real_footer_bad = [row["page"] for row in real_footer_rows
                       if row["page_digit"] and not row["recognised"]
                       and (row["in_last_text"] or row["in_last_box"])]
    criterion_b_real = not real_footer_bad

    # ---------- c) 取顶覆盖同段最高行 ----------
    head_checks: list[dict[str, Any]] = []
    for page in pages:
        content = page["view"]["content"]
        run = page["view"]["run"]
        scale_y = page["height"] / page["page_height"]
        for index, (position, number) in enumerate(run):
            head = content[position]
            stop = run[index + 1][0] if index + 1 < len(run) else len(content)
            body = content[position:stop]
            highest_body = max(line["top"] for line in body)
            top_row_top = _overlap_top(content, head)
            region = page["regions"][index]
            region_pre = page["regions_noink"][index]
            old_pre = (page["old_noink"][index] if page["old_noink"] is not None
                       else None)
            expected_pre_y = (page["page_height"] - (top_row_top + 1.5)) * scale_y
            first_ink = _first_ink_row(page["ink"], top_row_top,
                                       head["bottom"] if top_row_top == head["top"]
                                       else _row_bottom_at(content, top_row_top),
                                       page["page_height"])
            head_checks.append({
                "page": page["page"], "no": number,
                "head_top": round(head["top"], 1),
                "top_row_top": round(top_row_top, 1),
                "highest_body_top": round(highest_body, 1),
                "pre_y": region_pre["y"], "y": region["y"],
                "expected_pre_y": round(expected_pre_y, 2),
                "first_ink": first_ink,
                "old_pre_y": None if old_pre is None else old_pre["y"],
                "old_missed_row": bool(old_pre is not None and
                                       old_pre["y"] > (page["page_height"]
                                                       - top_row_top) * scale_y + 0.6),
                "covers_row": region_pre["y"] <= expected_pre_y + 0.6,
                "covers_ink": (first_ink is None or region["y"] <= first_ink + 0.6),
            })
    criterion_c = all(check["covers_row"] and check["covers_ink"]
                      for check in head_checks)

    # ---------- d) 不混入下一题题干开头 ----------
    flat: list[tuple[dict[str, Any], dict[str, Any]]] = [
        (page, region) for page in pages for region in page["regions"]]
    cross_failures: list[dict[str, Any]] = []
    for index, (page, region) in enumerate(flat):
        same_page_next = (flat[index + 1][1] if index + 1 < len(flat)
                          and flat[index + 1][0] is page else None)
        if same_page_next is None:
            continue
        next_label = _normalise(same_page_next.get("label") or "")
        prefix = _stem_prefix(same_page_next)
        body = _normalise(region.get("text") or "")
        hit_label = bool(next_label) and next_label in body
        hit_prefix = len(prefix) >= 6 and prefix in body
        if hit_label or hit_prefix:
            cross_failures.append({"page": page["page"], "no": region["no"],
                                   "next_no": same_page_next["no"],
                                   "hit_label": hit_label, "hit_prefix": hit_prefix,
                                   "prefix": prefix})
    # 跨页：上一页末题不得含下一页首题题干
    page_tail_failures: list[dict[str, Any]] = []
    for left, right in zip(pages, pages[1:]):
        if not left["regions"] or not right["regions"]:
            continue
        tail = left["regions"][-1]
        head = right["regions"][0]
        next_label = _normalise(head.get("label") or "")
        prefix = _stem_prefix(head)
        body = _normalise(tail.get("text") or "")
        if (next_label and next_label in body) or (len(prefix) >= 6 and prefix in body):
            page_tail_failures.append({"page": left["page"], "no": tail["no"],
                                       "next_page": right["page"],
                                       "next_no": head["no"]})
    criterion_d = not cross_failures and not page_tail_failures

    # ---------- 改前/改后逐题差异 ----------
    diffs: list[dict[str, Any]] = []
    for page in pages:
        if page["old_regions"] is None:
            continue
        scale_y = page["height"] / page["page_height"]
        bare_top = max((line["top"] for line in page["bare_footer"]), default=None)
        bare_top_px = ((page["page_height"] - bare_top) * scale_y
                       if bare_top is not None else None)
        content = page["view"]["content"]
        run = page["view"]["run"]
        for index, (position, number) in enumerate(run):
            old = page["old_regions"][index]
            new = page["regions"][index]
            if all(abs(float(old[key]) - float(new[key])) < 0.05
                   for key in ("x", "y", "w", "h")):
                continue
            head = content[position]
            top_row_top = _overlap_top(content, head)
            expansion_px = max(0.0, (top_row_top - head["top"]) * scale_y)
            old_pre = (page["old_noink"][index] if page["old_noink"] is not None
                       else None)
            new_pre = page["regions_noink"][index]
            old_bottom = float(old["y"]) + float(old["h"])
            new_bottom = float(new["y"]) + float(new["h"])
            if (old_pre is not None and expansion_px > 0.5
                    and abs((old_pre["y"] - new_pre["y"]) - expansion_px) <= 2.0):
                cause = "取顶"
            elif (bare_top_px is not None
                  and abs(float(old["y"]) - float(new["y"])) < 0.05
                  and new_bottom < old_bottom - 0.5
                  and old_bottom > bare_top_px
                  and new_bottom <= bare_top_px + 0.6):
                cause = "裸页码"
            else:
                cause = "未解释"
            diffs.append({
                "page": page["page"], "no": number, "cause": cause,
                "expansion_px": round(expansion_px, 1),
                "old": {key: old[key] for key in ("x", "y", "w", "h")},
                "new": {key: new[key] for key in ("x", "y", "w", "h")},
                "old_pre_y": None if old_pre is None else old_pre["y"],
                "new_pre_y": new_pre["y"],
            })
    unexplained = [item for item in diffs if item["cause"] == "未解释"]
    footer_diffs: list[dict[str, Any]] = []
    for case in footer_cases:
        if case["form"] != "slash" or baseline is None:
            continue
        if case["old"].get("old_text_leak") or case["old"].get("old_box_leak"):
            footer_diffs.append({"page": case["page"], "no": case["old"].get(
                "old_box_leak") or case["old"].get("old_text_leak"),
                "cause": "页脚", "form": "slash"})
    all_diffs_explained = not unexplained

    # ---------- 截图 ----------
    shots: list[str] = []
    shot_document = pdfium.PdfDocument(pdf_path.read_bytes())
    try:
        if pages and pages[0]["regions"]:
            first = pages[0]["regions"][0]
            raw, width, height, stride, channels, rev = _render_raw(shot_document, 0)
            (out_dir / "q01_p1.png").write_bytes(
                _crop_png(raw, width, height, stride, channels, rev, first))
            shots.append("q01_p1.png")
        paper_last = None
        last_number = main_numbers[-1] if main_numbers else None
        for page in pages:
            if page["page"] != main_last_page:
                continue
            for region in page["regions"]:
                if region["no"] == last_number:
                    paper_last = region
        if paper_last is not None and main_last_page:
            raw, width, height, stride, channels, rev = _render_raw(
                shot_document, main_last_page - 1)
            name = "q%02d_p%d.png" % (paper_last["no"], main_last_page)
            (out_dir / name).write_bytes(
                _crop_png(raw, width, height, stride, channels, rev, paper_last))
            shots.append(name)
        last_page = next(page for page in pages if page["page"] == page_count)
        if last_page["regions"]:
            last = last_page["regions"][-1]
            raw, width, height, stride, channels, rev = _render_raw(
                shot_document, page_count - 1)
            name = "q_last_p%d.png" % page_count
            (out_dir / name).write_bytes(
                _crop_png(raw, width, height, stride, channels, rev, last))
            shots.append(name)
    finally:
        shot_document.close()

    # ---------- 落盘 ----------
    region_rows: list[dict[str, Any]] = []
    for page in pages:
        for region in page["regions"]:
            region_rows.append({
                "page": page["page"], "no": region["no"], "x": region["x"],
                "y": region["y"], "w": region["w"], "h": region["h"],
                "label": region.get("label") or "",
            })
    regions_doc = {
        "meta": {
            "paper": PAPER_REL,
            "tag": tag,
            "pdf_pages": page_count,
            "render_dpi": PDF_RENDER_DPI,
            "baseline_commit": BASELINE_COMMIT,
            "region_count": len(region_rows),
            "generated_by": "tools/textlayer_probe.py",
        },
        "region": region_rows,
    }
    toml_io.write(out_dir / "regions.toml", regions_doc)

    criteria = {
        "a_question_chain": criterion_a,
        "b_footer_two_forms": criterion_b,
        "b_real_footer_clean": criterion_b_real,
        "c_head_top_covers_formula": criterion_c,
        "d_no_next_stem_bleed": criterion_d,
        "diffs_all_explained": all_diffs_explained,
    }
    probe_doc = {
        "meta": {
            "paper": PAPER_REL,
            "tag": tag,
            "pdf_pages": page_count,
            "render_dpi": PDF_RENDER_DPI,
            "baseline_commit": BASELINE_COMMIT,
            "pypdfium2": "5.9.0",
            "python": sys.version.split()[0],
        },
        "ledger_7_1": {
            "pages": {"measured": page_count, "ledger": LEDGER_PAGES},
            "text_chars": {"measured_raw": chars_raw,
                           "ledger": LEDGER_CHARS,
                           "note": "台账 4118 = 4114 正文 + 4 个跨页换行"},
            "head_hits": {"measured": len(ordered_heads), "ledger": LEDGER_HEADS},
            "path": PAPER_REL,
        },
        "chain": {
            "primary": [{"page": page, "no": number} for page, number in primary],
            "primary_numbers": main_numbers,
            "extras": [{"page": page, "no": number, "text": text}
                       for page, number, text in extras],
            "page_region_numbers": page_region_numbers,
        },
        "criteria": criteria,
        "footer_cases": footer_cases,
        "real_footer": {"bad_pages": real_footer_bad, "rows": real_footer_rows},
        "head_checks": head_checks,
        "stem_failures": {"same_page": cross_failures,
                          "cross_page": page_tail_failures},
        "diffs": diffs,
        "footer_diffs": footer_diffs,
        "screenshots": shots,
    }
    (out_dir / "probe.toml").write_text(
        toml_io.dumps(probe_doc, default=str), encoding="utf-8")

    # ---------- 终端摘要 ----------
    print("== 文字层真卷复验 %s ==" % tag)
    print("素材: %s" % PAPER_REL)
    print("§7.1 页=%d 字=%d(台账 %d) 题号命中=%d(台账 %d)"
          % (page_count, chars_raw, LEDGER_CHARS, len(ordered_heads), LEDGER_HEADS))
    print("主链: %s .. %s (%d 个) 额外命中 %d 个: %s"
          % (main_numbers[0] if main_numbers else "-",
             main_numbers[-1] if main_numbers else "-", len(main_numbers),
             len(extras), [number for _page, number, _text in extras]))
    print("题块: %d 个（每页 %s）" % (len(region_rows), page_region_numbers))
    for key, value in criteria.items():
        print("判据 %-28s %s" % (key, "PASS" if value else "FAIL"))
    print("差异: %d 条（取顶 %d / 页脚 %d / 裸页码 %d / 未解释 %d）"
          % (len(diffs), len([item for item in diffs if item["cause"] == "取顶"]),
             len(footer_diffs),
             len([item for item in diffs if item["cause"] == "裸页码"]),
             len(unexplained)))
    print("真实页脚漏页: %s（页底裸页码）" % (real_footer_bad or "无"))
    print("产物: %s" % out_dir)
    ok = all(criteria.values())
    print("RESULT: %s" % ("GREEN" if ok else "RED"))
    return 0 if ok else 1


def _row_bottom_at(content: list[dict[str, Any]], top: float) -> float:
    """找上沿等于给定 top 的那一行的下沿（多条时取最低），供墨行定位。"""
    candidates = [line["bottom"] for line in content
                  if abs(line["top"] - top) < 0.01]
    return min(candidates) if candidates else top


if __name__ == "__main__":
    sys.exit(main())