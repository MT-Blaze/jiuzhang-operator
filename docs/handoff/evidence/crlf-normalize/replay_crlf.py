# -*- coding: utf-8 -*-
"""crlf-normalize 卡⑤离线回放（自包含）：真 CRLF 字节走 read_bytes 落池路。

复用剥图②（note-warn-merge）与 BDP-01 的落池路口径：夹具以**真实字节**落盘
（CRLF / lone \\r / LF），read_bytes 原样读 → data_url → 产品同步入口
service.ingest_files → 落池 → dedupe（抽走启用态，真跑）→ 读回 route.note。
治后预期：CRLF 与 lone \\r 也剥卷首图行、产且只产一条警告，与 LF 同文逐字同语义；
无警告夹具 note 仍为空串。另做 decode_text 边界对照（归一后逐字等于 LF 原文）。
零出网零引擎零端口；隔离 JZO_DATA_DIR / JZO_PLUGINS_DIR 进 .system_generated
临时区＋最小目录夹具插件，绝不碰本机 data/。报告落 MD＋TOML（禁 JSON）。

运行：``.venv/Scripts/python.exe docs/handoff/evidence/crlf-normalize/replay_crlf.py``
"""
from __future__ import annotations

import asyncio
import base64
import os
import sys
import threading
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
sys.path.insert(0, str(ROOT))

E2E = ROOT / ".system_generated" / "crlf-normalize" / "e2e"
DATA_DIR = E2E / "data"
PLUGINS_DIR = E2E / "plugins"
FIXTURES = E2E / "fixtures"
for folder in (DATA_DIR, PLUGINS_DIR, FIXTURES):
    folder.mkdir(parents=True, exist_ok=True)
os.environ["JZO_DATA_DIR"] = str(DATA_DIR)
os.environ["JZO_PLUGINS_DIR"] = str(PLUGINS_DIR)
os.environ["JZO_RESTART_DISABLED"] = "1"
os.environ.pop("JZO_POOL_ADMIT_DISABLED", None)  # 抽走启用态：真让 dedupe 跑

from tests.catalog_fixture import write_catalog_plugin  # noqa: E402
from app.core.ingest import service  # noqa: E402
from app.core.ingest.intake import shapes  # noqa: E402
from app.core.ingest.intake.text import decode_text  # noqa: E402
from app.core.pending import service as pending  # noqa: E402

WARN_MD = (
    "![](images/header_photo.jpg)\n"
    "\n"
    "10. 已知集合 $A=\\{x \\mid 0<x<a\\}$，则下列结论正确的是（ ）\n"
    "\n"
    "A. $a>0$ B. $a<0$ C. $a=0$ D. 无法确定\n"
)
PLAIN_MD = "1. 求 $x+1=2$ 的解。\n"
WARN_PHRASE = "题干图片行已剥离"


def _join_dedupe() -> None:
    for thread in threading.enumerate():
        if thread.name.startswith("jzo-dedupe-warm"):
            thread.join(timeout=10)


def _ingest_bytes(name: str, raw: bytes) -> tuple[str, str, list[dict]]:
    """read_bytes 落池路（BDP e2e:67 同款）：裸字节 → data_url → ingest_files。"""
    url = "data:text/markdown;base64," + base64.b64encode(raw).decode("ascii")
    result = asyncio.run(service.ingest_files([{"name": name, "data_url": url}]))
    _join_dedupe()
    bid = result["batch_ids"][0]
    rows = pending.list_batch_questions(bid)
    note = str((rows.get("route") or {}).get("note") or "")
    questions = [{k: v for k, v in row["question"].items() if k != "id"}
                 for row in rows["items"]]
    return note, bid, questions


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    write_catalog_plugin(PLUGINS_DIR)

    fixtures = {
        "lf_warn.md": WARN_MD.encode("utf-8"),
        "crlf_warn.md": WARN_MD.replace("\n", "\r\n").encode("utf-8"),
        "cr_warn.md": WARN_MD.replace("\n", "\r").encode("utf-8"),
        "crlf_plain.md": PLAIN_MD.replace("\n", "\r\n").encode("utf-8"),
    }
    results: dict[str, tuple[str, str, list[dict]]] = {}
    for name, raw in fixtures.items():
        path = FIXTURES / name
        path.write_bytes(raw)
        results[name] = _ingest_bytes(name, path.read_bytes())

    note_lf, bid_lf, q_lf = results["lf_warn.md"]
    note_crlf, bid_crlf, q_crlf = results["crlf_warn.md"]
    note_cr, bid_cr, q_cr = results["cr_warn.md"]
    note_plain, bid_plain, q_plain = results["crlf_plain.md"]

    crlf_decoded = decode_text(fixtures["crlf_warn.md"])
    cr_decoded = decode_text(fixtures["cr_warn.md"])
    norm_crlf, warns_crlf = shapes.normalize(crlf_decoded)

    checks = {
        "crlf_note_has_warning": WARN_PHRASE in note_crlf,
        "crlf_warning_exactly_one": note_crlf.count(WARN_PHRASE) == 1,
        "cr_note_has_warning": WARN_PHRASE in note_cr,
        "cr_warning_exactly_one": note_cr.count(WARN_PHRASE) == 1,
        "lf_note_has_warning": WARN_PHRASE in note_lf,
        "crlf_note_equals_lf": note_crlf == note_lf,
        "cr_note_equals_lf": note_cr == note_lf,
        "crlf_questions_equal_lf": q_crlf == q_lf,
        "cr_questions_equal_lf": q_cr == q_lf,
        "plain_note_empty": note_plain == "",
        "decode_crlf_verbatim_lf": crlf_decoded == WARN_MD,
        "decode_cr_verbatim_lf": cr_decoded == WARN_MD,
        "shapes_strips_after_decode": "![](images/header_photo.jpg)" not in norm_crlf
        and len(warns_crlf) == 1,
        "crlf_one_question": len(q_crlf) == 1,
        "cr_one_question": len(q_cr) == 1,
    }
    passed = sum(1 for ok in checks.values() if ok)
    total = len(checks)

    lines = ["# crlf-normalize 卡⑤离线回放报告（read_bytes 落池路全接线）", "",
             "- 入口：夹具真实字节落盘 → read_bytes → data_url → ingest_files →",
             "  media._items_from_file → decode_text（归一 LF）→ build_documents →",
             "  shapes.normalize → 落池 → dedupe（启用态真跑，join 后读回）",
             f"- 隔离底座：data={DATA_DIR} plugins={PLUGINS_DIR}",
             f"- 夹具字节：{FIXTURES}", "",
             "## 池内 route.note 实测", ""]
    for name, (note, bid, questions) in results.items():
        lines.append(f"- {name}（batch={bid}）：note={note!r}；题目数={len(questions)}")
    lines.extend(["", "## decode_text 边界对照（治后口径）", "",
                  f"- CRLF 字节经 decode_text 逐字等于 LF 原文：{crlf_decoded == WARN_MD}",
                  f"- lone \\r 字节经 decode_text 逐字等于 LF 原文：{cr_decoded == WARN_MD}",
                  f"- 归一后 shapes.normalize：警告 {len(warns_crlf)} 条，"
                  f"图片行被剥={'是' if '![](images/header_photo.jpg)' not in norm_crlf else '否'}",
                  "", "## 判据", ""])
    for key, ok in checks.items():
        lines.append(f"- {key}: {'PASS' if ok else 'FAIL'}")
    lines.extend(["", f"**passed/total = {passed}/{total}**", ""])
    (OUT / "replay_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    toml = ["# crlf-normalize 卡⑤离线回放判据（read_bytes 落池路，零端口零引擎）",
            f'passed = {passed}', f'total = {total}', "", "[checks]"]
    for key, ok in checks.items():
        toml.append(f"{key} = {'true' if ok else 'false'}")
    toml.extend(["", "[batches]", f'lf_warn = "{bid_lf}"', f'crlf_warn = "{bid_crlf}"',
                 f'cr_warn = "{bid_cr}"', f'crlf_plain = "{bid_plain}"'])
    (OUT / "probe.toml").write_text("\n".join(toml) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"passed/total = {passed}/{total}")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()