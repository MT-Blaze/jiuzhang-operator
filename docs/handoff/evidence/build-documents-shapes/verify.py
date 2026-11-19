# -*- coding: utf-8 -*-
"""BDP-01 离线端到端复验：产品入口 service.build_documents 回放 20 夹具。

绿口径：20/20 出文档；7 题 stem 非空＋题号对＋选项/blanks 按形状；对照 13 题与修前
快照逐字段一致；归一＋解析幂等。零出网零引擎。快照/报告落 TOML/MD（禁 JSON）。
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.ingest.service import build_documents  # noqa: E402
from app.core.ingest.intake import shapes  # noqa: E402

WIRE = ROOT / ".system_generated" / "typst-bench" / "wire"
OUT = Path(__file__).resolve().parent
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


def texts() -> dict[int, str]:
    return {n: (WIRE / f"full_md_fix_{n:02d}.md").read_text(encoding="utf-8")
            for n in range(1, 21)}


def main() -> None:
    before = tomllib.loads((OUT / "before_snapshot.toml").read_text(encoding="utf-8"))
    before_by_no = {f["no"]: f for f in before["fixture"]}
    src = texts()
    lines = ["# BDP-01 离线复验报告（产品入口 service.build_documents）", ""]
    failures: list[str] = []
    after_fixtures: list[dict] = []

    # 1) 20/20 出文档
    results = {n: build_documents(src[n]) for n in range(1, 21)}
    zero = [n for n, (docs, _w) in results.items() if not docs]
    lines.append(f"- 20/20 出文档：{'绿' if not zero else '红 ' + str(zero)}（0 文档题号={zero}）")
    if zero:
        failures.append(f"仍有 0 文档: {zero}")

    # 2) 对照 13 题逐字段一致
    lines.extend(["", "## 对照 13 题不回归（逐字段）", "",
                  "| 题号 | 修前文档数 | 修后文档数 | 逐字段一致 | warnings 一致 |",
                  "|---|---|---|---|---|"])
    for n in CONTROLS:
        docs, warns = results[n]
        b = before_by_no[n]
        same_docs = docs == b["documents"]
        same_warns = warns == b["warnings"]
        ok = same_docs and same_warns and len(docs) == b["doc_count"]
        lines.append(f"| {n} | {b['doc_count']} | {len(docs)} | {'✓' if same_docs else '✗'} | "
                     f"{'✓' if same_warns else '✗'} |")
        if not ok:
            failures.append(f"对照题 {n} 回归")
            if not same_docs:
                lines.append(f"  - 修前: {b['documents']}")
                lines.append(f"  - 修后: {docs}")

    # 3) 7 题形状
    lines.extend(["", "## 7 题形状修实（题号以 stem 头号承载，source 与对照同口径为空）", "",
                  "| 题号 | 文档数 | type | stem 头号 | source | 选项数 | stem 非空 | 形状期望 | warnings |",
                  "|---|---|---|---|---|---|---|---|---|"])
    for n in sorted(SEVEN):
        docs, warns = results[n]
        exp_type, exp_opts, exp_blanks = EXPECT[n]
        head = docs[0] if docs else {}
        stem = str(head.get("stem") or "")
        qno = str((head.get("source") or {}).get("question_no") or "")
        stem_no = stem.lstrip().split(" ")[0] if stem.strip() else ""
        opts = head.get("options") or []
        checks = [
            len(docs) == 1,
            bool(stem.strip()),
            stem.lstrip().startswith(f"{n}."),
            qno == "",
            head.get("type") == exp_type,
            len(opts) == exp_opts,
        ]
        if exp_blanks:
            checks.append(head.get("type") == "fill_blank")
        if n in (13, 15):
            checks.append("$$" not in stem)
        if n == 14:
            checks.append("\\_" not in stem)
        if n in (10, 11):
            checks.append(any("图片行已剥离" in w for w in warns))
        ok = all(checks)
        lines.append(f"| {n} | {len(docs)} | {head.get('type','')} | {stem_no} | {qno or '空'} | "
                     f"{len(opts)} | {'✓' if stem.strip() else '✗'} | {'✓' if ok else '✗ ' + str(checks)} | "
                     f"{'; '.join(warns)} |")
        if not ok:
            failures.append(f"题 {n} 形状不符: {checks}")
            lines.append(f"  - stem: {stem[:120]}")
            lines.append(f"  - doc: {head}")

    # 4) 幂等：归一文本两遍＝＝一遍，且解析文档稳定（警告是剥行动作的产物，二遍无行可剥）
    lines.extend(["", "## 幂等（归一文本稳定＋解析文档稳定）", ""])
    idem_ok = True
    for n in range(1, 21):
        once_docs, _once_warns = results[n]
        normalized, _w = shapes.normalize(src[n])
        renormalized, _w2 = shapes.normalize(normalized)
        twice_docs, _twice_warns = build_documents(normalized)
        if renormalized != normalized or once_docs != twice_docs:
            idem_ok = False
            failures.append(f"题 {n} 幂等失败")
            lines.append(f"- 题 {n}：✗")
    lines.append(f"- 20 题幂等：{'绿' if idem_ok else '红'}")

    # 5) 落 after 快照（TOML）
    snap = ["# BDP-01 修后快照（产品入口 service.build_documents）", ""]
    for n in range(1, 21):
        docs, warns = results[n]
        snap.append("[[fixture]]")
        snap.append(f"no = {n}")
        snap.append(f"doc_count = {len(docs)}")
        snap.append("warnings = [" + ", ".join('"' + w.replace('\\', '\\\\').replace('"', '\\"') + '"' for w in warns) + "]")
        for doc in docs:
            snap.append("")
            snap.append("[[fixture.documents]]")
            _dump(doc, "fixture.documents", snap)
        snap.append("")
    (OUT / "after_snapshot.toml").write_text("\n".join(snap) + "\n", encoding="utf-8")

    lines.extend(["", "## 判定", "",
                  f"-  failures：{failures if failures else '无'}",
                  f"-  结论：{'绿（20/20＋对照一致＋形状对＋幂等）' if not failures else '红'}"])
    (OUT / "verify_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
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