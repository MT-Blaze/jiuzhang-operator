"""题号链信任门禁：跨页回跳与整卷密度下限（台账:141 欠账，2026-11-18 实测定标）。

两条机械不变量，只判「链可不可信」，不判答案区从哪行开始（T7 仍欠）：
- 跨页回跳：本页最小题号 ≤ 上一页已切最大题号 ⇒ 答案区重复编号冒充题号，
  该页不自动切，逐页记失败（定位原卷页据此点亮），老师可框选。
- 密度下限：整卷切出块数 / 页数 低于 MIN_QUESTION_DENSITY ⇒ 链基本拿不到，
  整份不自动切，只留页图＋框选。实测见 biz 记录 20261118_a2-image-ingest。
"""

from __future__ import annotations

from typing import Any

# 块/页。2026-11-18 实测：好卷 3.4–10.0（哈九中扣答案页后 3.4、师大附中 6.67、
# 一中 6.33、庆中 10.0）；台账:141 坏卷 0.1/0.4/0.6。1.0 居中且容得下一页一题。
MIN_QUESTION_DENSITY = 1.0


def _numbers(regions: list[dict[str, Any]]) -> list[int]:
    out = []
    for region in regions or []:
        try:
            out.append(int(region.get("no")))
        except (TypeError, ValueError):
            continue
    return out


def apply_chain_guards(page_images: list[dict[str, Any]],
                       lines_by_page: dict[int, list[dict[str, Any]]] | None = None,
                       ledger: dict[str, Any] | None = None,
                       file: str = "") -> list[str]:
    """就地清掉不可信题块；返回批级如实说明。逐页失败走显性化账本。"""
    from app.core.ingest.route import ledger_failure  # 延迟导入：route 反过来引用本模块
    notes: list[str] = []
    lines_by_page = lines_by_page or {}
    previous_max = 0
    for entry in sorted(page_images or [], key=lambda e: int(e.get("page") or 0)):
        try:
            page_no = int(entry.get("page") or 0)
        except (TypeError, ValueError):
            continue
        numbers = _numbers(entry.get("regions") or [])
        if not numbers:
            if lines_by_page.get(page_no) and ledger is not None:
                reason = ("OCR 认出 %d 行但题号链没命中，本页未自动切题，可在左栏框选切题"
                          % len(lines_by_page[page_no]))
                ledger_failure(ledger, file=file, page_no=page_no,
                               step=f"自动切题·P{page_no}", reason=reason, detail=reason)
            continue
        if previous_max and min(numbers) <= previous_max:
            reason = ("本页题号从 %d 回跳（上一页已切到 %d），疑似答案区重复编号，"
                      "未自动切题，可在左栏框选切题" % (min(numbers), previous_max))
            entry["regions"] = []
            if ledger is not None:
                ledger_failure(ledger, file=file, page_no=page_no,
                               step=f"自动切题·P{page_no}", reason=reason, detail=reason)
            notes.append(f"第 {page_no} 页{reason}")
            continue
        previous_max = max(previous_max, max(numbers))
    total = sum(len(entry.get("regions") or []) for entry in page_images or [])
    pages = len(page_images or [])
    if pages and total and total / pages < MIN_QUESTION_DENSITY:
        for entry in page_images:
            entry["regions"] = []
        notes.append("题号密度 %d 块 / %d 页 = %.2f 低于下限 %.1f，题号链不可信，"
                     "未自动切题，可在左栏框选切题"
                     % (total, pages, total / pages, MIN_QUESTION_DENSITY))
    return notes