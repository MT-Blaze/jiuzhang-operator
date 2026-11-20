"""短卷页脚统一卡 #SHORT-FOOTER-UNIFY-01：真卷离线回放（零出网零额度）。

原件只读复制到隔离目录 .system_generated/short-footer-unify/，渲染＋切框全走
CPU 内置 PDFium；JZO_DATA_DIR 指向隔离目录，绝不碰本机 data/。

判据：
  J1 零漂移：四页每页 region 的 (x,y,w,h,label,text) 与改动前模块逐字相同；
     第 1 页六框 (y,h) 与⑥已交 probe.toml／回放报告钉死值逐字相同。
  J2 题号链：[1-6][7-11][12-16][17-19]；第 4 页 3 块、末框底 1565、
     孤字「2」仍在第 19 题题干内。
  J3 页脚洁净：四页页脚行（正则与裸页码三判据）都不在任何 region 题干 text 内。

产出：probe.toml ＋ replay_report.md（落本目录）；运行副本与基线模块落
.system_generated/short-footer-unify/（git 忽略）。

运行：.venv/Scripts/python.exe docs/handoff/evidence/short-footer-unify/replay_short_footer.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / ".system_generated" / "short-footer-unify"
SOURCE_NAME = "哈尔滨市第六中学校2026-2027年高三学年阶段性测试（一） 数学.pdf"
DESKTOP_SOURCE = Path("E:/15972/Desktop") / SOURCE_NAME
EXPECTED_SHA256 = "a65347866e545a01cb8633518b907b632ae33bc53582f74328eeaba12f6d6b0f"
# 基线钉死 3f7f3e6 不随 HEAD 漂移：该版本仍带 apply_fallbacks 参数，
# 提交后回放测的永远是「本刀之前」的模块。
BASELINE_COMMIT = "3f7f3e6"

# ⑥（af069bf）已交证据的钉死值：第 1 页六框 (y, h) 与四页链、末框底。
PINNED_PAGE1 = [(612.0, 196.0), (801.0, 185.0), (984.0, 198.0),
                (1210.0, 260.0), (1464.0, 179.0), (1638.0, 191.0)]
PINNED_CHAINS = [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11],
                 [12, 13, 14, 15, 16], [17, 18, 19]]
PINNED_LAST_BOTTOM = [1829.0, 1845.0, 1563.0, 1565.0]

sys.path.insert(0, str(ROOT))
os.environ["JZO_DATA_DIR"] = str(OUT / "data")

from app.core.ingest.render import furniture  # noqa: E402
from app.core.ingest.render import pdf as render_pdf  # noqa: E402
from app.core.ingest.render.regions import (  # noqa: E402
    _PDF_BARE_PAGE, _PDF_FOOTER, _bare_page_footer_lines, _ink_rows, _pdf_text_lines)
import pypdfium2 as pdfium  # noqa: E402


def prepare_source() -> Path:
    local = OUT / "source.pdf"
    if not local.is_file():
        if not DESKTOP_SOURCE.is_file():
            raise SystemExit(f"原件缺席：{DESKTOP_SOURCE}")
        OUT.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DESKTOP_SOURCE, local)
    return local


def load_old_regions() -> Any:
    """改动前（钉死 3f7f3e6，不随 HEAD 漂移）的 regions 模块，落在产物目录里导入。"""
    baseline = OUT / "baseline"
    baseline.mkdir(parents=True, exist_ok=True)
    source = subprocess.run(
        ["git", "show", BASELINE_COMMIT + ":app/core/ingest/render/regions.py"],
        cwd=ROOT, capture_output=True, check=True).stdout
    path = baseline / "regions_head.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("_regions_head", path)
    if spec is None or spec.loader is None:
        raise SystemExit("基线模块导入失败")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _flat(regions: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [(region["no"], region["x"], region["y"], region["w"], region["h"],
             region["label"], region["text"]) for region in regions]


def main() -> int:
    source = prepare_source()
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()

    entries, warnings = render_pdf._pdf_pages_builtin(data)
    if warnings or len(entries) != 4:
        raise SystemExit(f"渲染异常：warnings={warnings} pages={len(entries)}")

    old = load_old_regions()
    document = pdfium.PdfDocument(data)
    scanned: list[dict[str, Any]] = []
    for index in range(len(document)):
        page = document[index]
        try:
            width, height = (float(value) for value in page.get_size())
            lines = _pdf_text_lines(page)
            bitmap = page.render(scale=200 / 72.0)
            try:
                ink = _ink_rows(bytes(bitmap.buffer), int(bitmap.width),
                                int(bitmap.height), int(bitmap.stride),
                                int(bitmap.n_channels))
            finally:
                bitmap.close()
        finally:
            page.close()
        scanned.append({"width": width, "height": height, "lines": lines,
                        "ink": ink})
    kept = furniture.filter_pages(scanned)

    checks: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append((name, bool(ok), detail))

    record("sha256_matches_previous_card", digest == EXPECTED_SHA256, digest)
    record("render_4_pages_no_warning", not warnings and len(entries) == 4,
           f"pages={len(entries)} warnings={warnings}")

    new_by_page = [entry.get("regions") or [] for entry in entries]

    # J1：与改动前模块逐字比对（同一条 kept 行清单、同样的 ⑥ 调用口径）。
    drift_ok = True
    drift_detail: list[str] = []
    for index, regions in enumerate(new_by_page):
        before = old._question_regions(
            kept[index], scanned[index]["width"], scanned[index]["height"],
            int(entries[index]["width"]), int(entries[index]["height"]),
            ink_rows=scanned[index]["ink"], first_page=index == 0,
            apply_fallbacks=False)
        same = _flat(regions) == _flat(before)
        drift_ok = drift_ok and same
        drift_detail.append(f"p{index + 1}:{'same' if same else 'DRIFT'}")
    record("J1a_no_coordinate_drift_vs_head", drift_ok, " ".join(drift_detail))

    pinned_ok = len(new_by_page[0]) == len(PINNED_PAGE1)
    pinned_detail: list[str] = []
    for position, (want_y, want_h) in enumerate(PINNED_PAGE1):
        got = ((new_by_page[0][position]["y"], new_by_page[0][position]["h"])
               if position < len(new_by_page[0]) else None)
        same = got == (want_y, want_h)
        pinned_ok = pinned_ok and same
        pinned_detail.append(f"r{position + 1}={got}{'==' if same else '!='}"
                             f"({want_y},{want_h})")
    record("J1b_page1_boxes_match_previous_evidence", pinned_ok,
           " ".join(pinned_detail))

    # J2：题号链、第 4 页 3 块、末框底 1565、孤字「2」仍在第 19 题题干。
    chain_detail: list[str] = []
    chain_ok = True
    for index, regions in enumerate(new_by_page):
        numbers = [region["no"] for region in regions]
        want = PINNED_CHAINS[index]
        same = numbers == want
        chain_ok = chain_ok and same
        bottom = round(regions[-1]["y"] + regions[-1]["h"], 1) if regions else None
        bottom_ok = bottom == PINNED_LAST_BOTTOM[index]
        chain_ok = chain_ok and bottom_ok
        chain_detail.append(f"p{index + 1}={numbers} bottom={bottom}"
                            f"{'==' if bottom_ok else '!='}{PINNED_LAST_BOTTOM[index]}")
    record("J2a_question_chains_and_last_bottoms", chain_ok, " ".join(chain_detail))

    q19 = new_by_page[3][-1] if len(new_by_page[3]) == 3 else {}
    q19_lines = [line.strip() for line in str(q19.get("text") or "").splitlines()]
    record("J2b_page4_three_regions_and_lone_two_kept",
           len(new_by_page[3]) == 3 and "2" in q19_lines,
           f"p4_regions={len(new_by_page[3])} q19_tail={q19_lines[-3:]}")

    # J3：四页页脚（两种判据）都不进任何 region 题干。
    footer_ok = True
    footer_detail: list[str] = []
    for index, regions in enumerate(new_by_page):
        lines = scanned[index]["lines"]
        height = scanned[index]["height"]
        kept_ids = {id(line) for line in kept[index]}
        footers = [line for line in lines if _PDF_FOOTER.search(line["text"])]
        footers.extend(_bare_page_footer_lines(lines, height))
        # 跨页判据剥掉的贴底行同样是页脚：并进洁净度核查。
        footers.extend(line for line in lines
                       if id(line) not in kept_ids and line["bottom"] >= 0
                       and line["bottom"] < height * 0.10)
        footers = list({id(line): line for line in footers}.values())
        texts = [str(region.get("text") or "") for region in regions]
        leaked = [line["text"] for line in footers
                  if any(line["text"].strip() in text for text in texts)]
        footer_ok = footer_ok and not leaked
        kinds = sorted({("regex" if _PDF_FOOTER.search(line["text"])
                         else ("bare" if _PDF_BARE_PAGE.match(line["text"])
                               else "removed"))
                        for line in footers})
        footer_detail.append(f"p{index + 1} footers={len(footers)} kinds={kinds}"
                             f" leaked={leaked or 'none'}")
    record("J3_no_footer_text_in_any_region", footer_ok, " ".join(footer_detail))

    document.close()

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)

    toml_lines = [
        "# 短卷页脚统一卡 #SHORT-FOOTER-UNIFY-01 离线回放判据（当次实跑）",
        f'source_sha256 = "{digest}"',
        f"passed = {passed}",
        f"total = {total}",
        "",
        "[criteria]",
    ]
    for name, ok, _detail in checks:
        toml_lines.append(f"{name} = {str(ok).lower()}")
    (HERE / "probe.toml").write_text("\n".join(toml_lines) + "\n", encoding="utf-8")

    report = [
        "# 短卷页脚统一卡 #SHORT-FOOTER-UNIFY-01 真卷离线回放报告",
        "",
        f"- 原件：`{DESKTOP_SOURCE}`（只读复制，sha256 `{digest}`）",
        f"- 隔离目录：`{OUT}`（JZO_DATA_DIR 同指此处，本机 data/ 零接触）",
        "- 通道：内置 PDFium 渲染＋切框，CPU 离线；零出网零额度零识别引擎零端口",
        f"- 判据：**{passed}/{total}** 通过",
        "- 基线对照：`git show HEAD:app/core/ingest/render/regions.py` 载入改动前模块，"
        "同一 kept 行清单、同 ⑥ 调用口径（apply_fallbacks=False）逐字比对",
        "",
        "## 逐判据",
        "",
        "| 判据 | 结果 | 实测 |",
        "|---|---|---|",
    ]
    for name, ok, detail in checks:
        report.append(f"| {name} | {'true' if ok else 'FALSE'} | {detail} |")
    report += ["", "## 四页全框（新语义）", ""]
    for index, regions in enumerate(new_by_page):
        report.append(f"### 第 {index + 1} 页")
        report.append("")
        for region in regions:
            report.append(f"- no={region['no']} x={region['x']} y={region['y']} "
                          f"w={region['w']} h={region['h']} "
                          f"bottom={round(region['y'] + region['h'], 1)}")
        report.append("")
    (HERE / "replay_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"replay: {passed}/{total} passed")
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
