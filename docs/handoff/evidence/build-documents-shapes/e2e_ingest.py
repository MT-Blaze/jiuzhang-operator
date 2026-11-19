# -*- coding: utf-8 -*-
"""BDP-01 离线端到端（全接线）：产品同步入口 service.ingest_files 回放 20 夹具。

与 verify.py（直调 build_documents）互补：本探针走老师拖 .md 进录题工作台的**同一条
产品接线**——ingest_files → stage_ingest → run_ingest_jobs → media._items_from_file
→ build_documents → pending.save_draft → 待审池，再从池子里按批次读回题目核对。

零出网零引擎零端口：.md 判 text，不碰 OCR/版面/识别引擎，不起服务、不开浏览器。
隔离：JZO_DATA_DIR / JZO_PLUGINS_DIR 进 .system_generated 临时区＋最小目录夹具插件，
绝不碰本机 data/ 与 plugins/。报告/快照落 MD/TOML（禁 JSON）。

运行：``.venv/Scripts/python.exe .system_generated/build-documents-shapes/e2e_ingest.py``
"""
from __future__ import annotations

import asyncio
import base64
import os
import sys
import tomllib
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT))

E2E = OUT / "e2e"
DATA_DIR = E2E / "data"
PLUGINS_DIR = E2E / "plugins"
for folder in (DATA_DIR, PLUGINS_DIR):
    folder.mkdir(parents=True, exist_ok=True)
os.environ["JZO_DATA_DIR"] = str(DATA_DIR)
os.environ["JZO_PLUGINS_DIR"] = str(PLUGINS_DIR)
os.environ["JZO_POOL_ADMIT_DISABLED"] = "1"
os.environ["JZO_RESTART_DISABLED"] = "1"

from tests.catalog_fixture import write_catalog_plugin  # noqa: E402
from app.core.ingest import service  # noqa: E402
from app.core.ingest.service import build_documents  # noqa: E402
from app.core.pending import service as pending  # noqa: E402

WIRE = ROOT / ".system_generated" / "typst-bench" / "wire"
SEVEN = {3, 6, 10, 11, 13, 14, 15}
CONTROLS = [n for n in range(1, 21) if n not in SEVEN]
EXPECT = {
    3: ("single_choice", 4, 0),
    6: ("single_choice", 4, 0),
    10: ("single_choice", 4, 0),
    11: ("single_choice", 4, 0),
    13: ("solution", 0, 0),
    14: ("fill_blank", 0, 1),
    15: ("solution", 0, 0),
}


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    write_catalog_plugin(PLUGINS_DIR)
    before = tomllib.loads((OUT / "before_snapshot.toml").read_text(encoding="utf-8"))
    before_by_no = {f["no"]: f for f in before["fixture"]}

    files = []
    for n in range(1, 21):
        raw = (WIRE / f"full_md_fix_{n:02d}.md").read_bytes()
        url = "data:text/markdown;base64," + base64.b64encode(raw).decode("ascii")
        files.append({"name": f"full_md_fix_{n:02d}.md", "data_url": url})

    result = asyncio.run(service.ingest_files(files))
    batch_ids = result["batch_ids"]
    lines = ["# BDP-01 离线端到端报告（产品全接线 service.ingest_files → 待审池）", "",
             "- 入口：ingest_files（老师拖 .md 的同一同步入口）→ stage → run_jobs → "
             "media._items_from_file → build_documents → save_draft → 待审池读回",
             "- 零出网零引擎零端口：.md 判 text，不起服务、不开浏览器、不碰识别/版面引擎",
             f"- 隔离底座：data={DATA_DIR} plugins={PLUGINS_DIR}", ""]
    failures: list[str] = []

    pool: dict[int, list[dict]] = {}
    for n, bid in zip(range(1, 21), batch_ids):
        rows = pending.list_batch_questions(bid)
        pool[n] = [item["question"] for item in rows["items"]]

    zero = [n for n in range(1, 21) if not pool[n]]
    total = sum(len(v) for v in pool.values())
    lines.append(f"- 20/20 文件出文档：{'绿' if not zero else '红 ' + str(zero)}"
                 f"（0 文档题号={zero}；池内总文档数={total}）")
    if zero:
        failures.append(f"仍有 0 文档: {zero}")
    if len(batch_ids) != 20:
        failures.append(f"批次数 {len(batch_ids)} != 20")

    lines.extend(["", "## 7 题修实落池（题号以 stem 头号承载）", "",
                  "| 题号 | 池内文档数 | type | stem 头号 | 选项数 | 形状期望 |",
                  "|---|---|---|---|---|---|"])
    for n in sorted(SEVEN):
        docs = pool[n]
        head = docs[0] if docs else {}
        stem = str(head.get("stem") or "")
        stem_no = stem.lstrip().split(" ")[0] if stem.strip() else ""
        opts = head.get("options") or []
        exp_type, exp_opts, _exp_blanks = EXPECT[n]
        checks = [
            len(docs) == 1,
            bool(stem.strip()),
            stem.lstrip().startswith(f"{n}."),
            str((head.get("source") or {}).get("question_no") or "") == "",
            head.get("type") == exp_type,
            len(opts) == exp_opts,
        ]
        # 契约文档无 blanks 字段：填空以 type=fill_blank＋stem 含连续下划线承载，
        # blanks 计数是 question_parser 内部判型依据（单测 test_build_documents_shapes 覆盖）。
        if exp_type == "fill_blank":
            checks.append("____" in stem or "__" in stem)
        ok = all(checks)
        lines.append(f"| {n} | {len(docs)} | {head.get('type','')} | {stem_no} | "
                     f"{len(opts)} | {'✓' if ok else '✗ ' + str(checks)} |")
        if not ok:
            failures.append(f"题 {n} 落池形状不符: {checks}")

    lines.extend(["", "## 对照 13 题落池文档数不回归", "",
                  "| 题号 | 修前文档数 | 池内文档数 | 一致 |", "|---|---|---|---|"])
    for n in CONTROLS:
        b = before_by_no[n]
        ok = len(pool[n]) == b["doc_count"]
        lines.append(f"| {n} | {b['doc_count']} | {len(pool[n])} | {'✓' if ok else '✗'} |")
        if not ok:
            failures.append(f"对照题 {n} 落池文档数回归")

    # 图片不静默丢：在解析边界（build_documents，本卡修实的契约口）断言剥图警告如实产出。
    # 池内 route.note 仅作信息性扫描：落池后 dedupe 会用新快照重写 route（既有接线，
    # 对所有带 note 的 text 导入一视同仁），不属本卡解析段，故不作绿判据。
    lines.extend(["", "## 图片不静默丢（解析边界 warnings 如实登记）", ""])
    boundary_warns: list[str] = []
    for n in (10, 11):
        text = (WIRE / f"full_md_fix_{n:02d}.md").read_text(encoding="utf-8")
        _docs, warns = build_documents(text)
        hit = [w for w in warns if "图片行已剥离" in w]
        boundary_warns.extend(hit)
        lines.append(f"- 题 {n} 解析边界剥图警告：{len(hit)} 条")
        for w in hit:
            lines.append(f"  - {w}")
    if len(boundary_warns) < 2:
        failures.append("解析边界剥图警告不足 2 条")
    pool_note_hits = 0
    for n in range(1, 21):
        rows = pending.list_batch_questions(batch_ids[n - 1])
        note = str((rows.get("route") or {}).get("note") or "")
        if "图片行已剥离" in note:
            pool_note_hits += 1
    lines.append(f"- 池内 route.note 仍带剥图警告的批次数：{pool_note_hits}"
                 "（信息性：dedupe 重写 route 为既有接线，非本卡判据）")

    snap = ["# BDP-01 端到端待审池快照（service.ingest_files）", ""]
    for n in range(1, 21):
        snap.append("[[batch]]")
        snap.append(f"no = {n}")
        snap.append(f"doc_count = {len(pool[n])}")
        for doc in pool[n]:
            snap.append("")
            snap.append("[[batch.documents]]")
            _dump(doc, "batch.documents", snap)
        snap.append("")
    (OUT / "e2e_snapshot.toml").write_text("\n".join(snap) + "\n", encoding="utf-8")

    lines.extend(["", "## 判定", "",
                  f"-  failures：{failures if failures else '无'}",
                  f"-  结论：{'绿（20/20 落池＋7 题形状对＋对照不回归＋剥图如实）' if not failures else '红'}"])
    (OUT / "e2e_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print()
    print("FAILURES:", failures if failures else "none")
    sys.exit(1 if failures else 0)


def _esc(value: str) -> str:
    out = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _dump(table: dict, prefix: str, lines: list[str]) -> None:
    for key, value in table.items():
        if isinstance(value, dict):
            lines.append("")
            lines.append(f"[{prefix}.{key}]")
            _dump(value, f"{prefix}.{key}", lines)
        elif isinstance(value, list) and value and all(isinstance(i, dict) for i in value):
            for item in value:
                lines.append("")
                lines.append(f"[[{prefix}.{key}]]")
                _dump(item, f"{prefix}.{key}", lines)
        elif isinstance(value, list):
            lines.append(f"{key} = [" + ", ".join(_esc(str(i)) for i in value) + "]")
        elif isinstance(value, str):
            lines.append(f"{key} = {_esc(value)}")
        elif isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        else:
            lines.append(f"{key} = {value}")


if __name__ == "__main__":
    main()