# -*- coding: utf-8 -*-
"""BDP-01 离线复现：20 份真实 MinerU 夹具直调产品入口 service.build_documents。

零出网、零引擎、零额度。只读夹具，钉住修前现状（7 题＝0 文档）。
快照落 TOML（禁 JSON）。运行：.venv/Scripts/python.exe .system_generated/build-documents-shapes/repro.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.ingest.service import build_documents  # noqa: E402

WIRE = ROOT / ".system_generated" / "typst-bench" / "wire"
OUT = Path(__file__).resolve().parent


def esc(value: str) -> str:
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
        elif ch == "\r":
            out.append("\\r")
        elif ord(ch) < 0x20:
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def dump_value(value) -> str:
    if isinstance(value, str):
        return esc(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value) and value:
            return "ARRAY_OF_TABLES"
        return "[" + ", ".join(dump_value(item) for item in value) + "]"
    raise TypeError(type(value))


def dump_table(table: dict, prefix: str, lines: list[str]) -> None:
    scalars = {k: v for k, v in table.items() if not isinstance(v, (dict, list))}
    arrays = {k: v for k, v in table.items()
              if isinstance(v, list) and not (v and all(isinstance(i, dict) for i in v))}
    tables = {k: v for k, v in table.items() if isinstance(v, dict)}
    aot = {k: v for k, v in table.items()
           if isinstance(v, list) and v and all(isinstance(i, dict) for i in v)}
    for key, value in scalars.items():
        lines.append(f"{key} = {dump_value(value)}")
    for key, value in arrays.items():
        lines.append(f"{key} = {dump_value(value)}")
    for key, value in tables.items():
        lines.append("")
        lines.append(f"[{prefix}.{key}]")
        dump_table(value, f"{prefix}.{key}", lines)
    for key, value in aot.items():
        for item in value:
            lines.append("")
            lines.append(f"[[{prefix}.{key}]]")
            dump_table(item, f"{prefix}.{key}", lines)


def main() -> None:
    snapshot: list[str] = ["# BDP-01 修前基线快照（产品入口 service.build_documents 直调）", ""]
    summary: list[str] = ["# BDP-01 离线复现摘要", "",
                          "| 题号 | 文档数 | type | 题号(source) | 选项数 | stem 头 | warnings |",
                          "|---|---|---|---|---|---|---|"]
    zero = []
    for no in range(1, 21):
        text = (WIRE / f"full_md_fix_{no:02d}.md").read_text(encoding="utf-8")
        documents, warnings = build_documents(text)
        if not documents:
            zero.append(no)
        head = documents[0] if documents else {}
        stem = str(head.get("stem") or "")
        stem_head = stem[:34].replace("\n", " ").replace("|", "/")
        qno = str((head.get("source") or {}).get("question_no") or "")
        summary.append(
            f"| {no} | {len(documents)} | {head.get('type', '')} | {qno} | "
            f"{len(head.get('options') or [])} | {stem_head} | {'; '.join(warnings)} |")
        snapshot.append(f"[[fixture]]")
        snapshot.append(f"no = {no}")
        snapshot.append(f"doc_count = {len(documents)}")
        snapshot.append(f"warnings = {dump_value(warnings)}")
        for doc in documents:
            snapshot.append("")
            snapshot.append(f"[[fixture.documents]]")
            dump_table(doc, "fixture.documents", snapshot)
        snapshot.append("")
    (OUT / "before_snapshot.toml").write_text("\n".join(snapshot) + "\n", encoding="utf-8")
    (OUT / "repro_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    print()
    print("0 文档题号:", zero)
    print("快照:", OUT / "before_snapshot.toml")


if __name__ == "__main__":
    main()