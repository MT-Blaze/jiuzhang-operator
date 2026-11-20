"""末题框底方向修正卡⑥：真卷离线回放（零出网零额度零识别引擎零端口）。

原件只读复制到隔离目录 .system_generated/last-region-bottom/，渲染＋切框
全走 CPU 内置 PDFium；JZO_DATA_DIR 指向隔离目录，绝不碰本机 data/。
判据（§5）：
  C1 每页末题框底 ≥ 该页最低 kept 正文行墨迹底像素（选项全进框）；
  C2 每页末题框底 ≤ 页脚上沿像素（原件有页脚行才判）；
  C3 第 1 页 region6 bottom ∈ [1827, 1831]；
  C4 第 1 页 region1–5 的 y/h 与钉死值逐字同；
  C5 每页题号链连续递增且末题号＝该页最大题号。
产出：replay_report.md ＋ probe.toml（passed/total＋逐判据 true）。

运行：.venv/Scripts/python.exe docs/handoff/evidence/last-region-bottom/replay_last_region.py
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / ".system_generated" / "last-region-bottom"
SOURCE_NAME = "哈尔滨市第六中学校2026-2027年高三学年阶段性测试（一） 数学.pdf"
DESKTOP_SOURCE = Path("E:/15972/Desktop") / SOURCE_NAME

sys.path.insert(0, str(ROOT))
os.environ["JZO_DATA_DIR"] = str(OUT / "data")

from app.core.ingest.render import furniture  # noqa: E402
from app.core.ingest.render import pdf as render_pdf  # noqa: E402
from app.core.ingest.render.regions import (  # noqa: E402
    _PDF_HEAD, _PDF_INSTRUCTION, _PDF_EMBEDDED_HEAD, _ink_rows, _pdf_text_lines)
import pypdfium2 as pdfium  # noqa: E402

# §1 钉死值：修前基线第 1 页 region1–5 的 (y, h)，邻居坐标必须一字不动。
PINNED_PAGE1 = [(612.0, 196.0), (801.0, 185.0), (984.0, 198.0),
                (1210.0, 260.0), (1464.0, 179.0)]


def prepare_source() -> Path:
    local = OUT / "source.pdf"
    if not local.is_file():
        if not DESKTOP_SOURCE.is_file():
            raise SystemExit(f"原件缺席：{DESKTOP_SOURCE}")
        OUT.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DESKTOP_SOURCE, local)
    return local


def page_heads(lines: list[dict]) -> list[int]:
    numbers = []
    for line in lines:
        matched = _PDF_HEAD.match(line["text"])
        if matched and not _PDF_INSTRUCTION.search(line["text"]):
            numbers.append(int(matched.group(1)))
            continue
        embedded = _PDF_EMBEDDED_HEAD.search(line["text"])
        if embedded:
            numbers.append(int(embedded.group(1)))
    return numbers


def main() -> int:
    source = prepare_source()
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()

    entries, warnings = render_pdf._pdf_pages_builtin(data)
    if warnings or len(entries) != 4:
        raise SystemExit(f"渲染异常：warnings={warnings} pages={len(entries)}")

    document = pdfium.PdfDocument(data)
    scanned = []
    for index in range(len(document)):
        page = document[index]
        width, height = (float(value) for value in page.get_size())
        lines = _pdf_text_lines(page)
        page.close()
        scanned.append({"width": width, "height": height, "lines": lines})
    kept = furniture.filter_pages(scanned)

    checks: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append((name, bool(ok), detail))

    record("render_4_pages_no_warning", not warnings and len(entries) == 4,
           f"pages={len(entries)} warnings={warnings}")

    for index, entry in enumerate(entries):
        page_no = index + 1
        info = scanned[index]
        height_pt = info["height"]
        pixel_height = int(entry["height"])
        scale_y = pixel_height / height_pt
        regions = entry.get("regions") or []
        last = regions[-1]
        last_bottom = last["y"] + last["h"]

        kept_lines = kept[index]
        lowest = min(kept_lines, key=lambda line: line["bottom"])
        page = document[index]
        bitmap = page.render(scale=200 / 72.0)
        ink = _ink_rows(bytes(bitmap.buffer), bitmap.width, bitmap.height,
                        int(bitmap.stride), int(bitmap.n_channels))
        bitmap.close()
        page.close()
        target = int((height_pt - lowest["bottom"]) * scale_y)
        window = [row for row in range(max(0, target - 30),
                                       min(pixel_height, target + 30)) if ink[row]]
        ink_bottom = (max(window) + 1) if window else target
        record(f"p{page_no}_C1_last_bottom_covers_lowest_ink",
               last_bottom >= ink_bottom,
               f"last_bottom={last_bottom:.1f} ink_bottom={ink_bottom} "
               f"lowest_line={lowest['text'][:24]!r}")

        kept_ids = {id(line) for line in kept_lines}
        footer_candidates = [line for line in info["lines"]
                             if id(line) not in kept_ids and line["bottom"] >= 0]
        if footer_candidates:
            footer_top_px = (height_pt - max(line["top"]
                                             for line in footer_candidates)) * scale_y
            record(f"p{page_no}_C2_last_bottom_above_footer",
                   last_bottom <= footer_top_px,
                   f"last_bottom={last_bottom:.1f} footer_top_px={footer_top_px:.1f}")
        else:
            record(f"p{page_no}_C2_last_bottom_above_footer", True,
                   "该页原件无页脚行，判据空真")

        numbers = [region["no"] for region in regions]
        heads = page_heads(kept_lines)
        chain_ok = (numbers == list(range(numbers[0], numbers[0] + len(numbers)))
                    and numbers[-1] == max(heads))
        record(f"p{page_no}_C5_number_chain", chain_ok,
               f"regions={numbers} max_head={max(heads)}")

    document.close()

    page1 = entries[0].get("regions") or []
    region6 = page1[5]
    bottom6 = region6["y"] + region6["h"]
    record("p1_C3_region6_bottom_in_1827_1831", 1827 <= bottom6 <= 1831,
           f"region6 y={region6['y']} h={region6['h']} bottom={bottom6:.1f}")
    pinned_ok = len(page1) >= 6
    details = []
    for position, (want_y, want_h) in enumerate(PINNED_PAGE1):
        region = page1[position]
        same = (region["y"], region["h"]) == (want_y, want_h)
        pinned_ok = pinned_ok and same
        details.append(f"r{position + 1}=({region['y']},{region['h']})"
                       f"{'==' if same else '!='}({want_y},{want_h})")
    record("p1_C4_regions1to5_pinned", pinned_ok, " ".join(details))

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)

    OUT.mkdir(parents=True, exist_ok=True)
    toml_lines = [
        "# 末题框底方向修正卡⑥ 离线回放判据（当次实跑）",
        f'source_sha256 = "{digest}"',
        f"passed = {passed}",
        f"total = {total}",
        "",
        "[criteria]",
    ]
    for name, ok, _detail in checks:
        toml_lines.append(f"{name} = {str(ok).lower()}")
    (OUT / "probe.toml").write_text("\n".join(toml_lines) + "\n", encoding="utf-8")

    report = [
        "# 末题框底方向修正卡⑥ 真卷离线回放报告",
        "",
        f"- 原件：`{DESKTOP_SOURCE}`（只读复制，sha256 `{digest}`）",
        f"- 隔离目录：`{OUT}`（JZO_DATA_DIR 同指此处，本机 data/ 零接触）",
        "- 通道：内置 PDFium 渲染＋切框，CPU 离线；零出网零额度零识别引擎零端口",
        f"- 判据：**{passed}/{total}** 通过",
        "",
        "## 修前基线（2026-11-20 开工复核，baseline_probe.py 当次实测）",
        "",
        "- 第 1 页 region6：y=1638.0 h=171.0 bottom=**1809.0**，压在选项墨迹 1802–1822 上半截",
        "- 选项行「A．13 B．9 C．7 D．3」charbox bottom=72.38 top=79.71（pt）",
        "- 页脚「第 N 页 共 4 页」被全卷剥离（furniture，4 页≥3），单页兜底 apply_fallbacks=False 关闭",
        "- region1–5 (y,h)：(612,196)(801,185)(984,198)(1210,260)(1464,179)",
        "",
        "## 修后逐判据",
        "",
        "| 判据 | 结果 | 实测 |",
        "|---|---|---|",
    ]
    for name, ok, detail in checks:
        report.append(f"| {name} | {'true' if ok else 'FALSE'} | {detail} |")
    report += ["", "## 修后第 1 页全框", ""]
    for region in page1:
        report.append(f"- no={region['no']} y={region['y']} h={region['h']} "
                      f"bottom={round(region['y'] + region['h'], 1)}")
    (OUT / "replay_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"replay: {passed}/{total} passed")
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())