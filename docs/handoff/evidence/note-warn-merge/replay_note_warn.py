# -*- coding: utf-8 -*-
"""note-warn-merge 侦查回放（自包含）：剥图警告在全接线里的真实去向。

三路回放＋一路边界对照，全部走老师拖 .md 的同一同步入口 service.ingest_files：
1. LF 带卷首图夹具 → 池内 route.note 是否带剥图警告（dedupe 抽走启用态）；
2. CRLF 同文夹具 → 同上（BDP-01 e2e 用的就是 CRLF 原件）；
3. LF 无图夹具 → note 现状基线；
4. shapes.normalize 边界对照：read_text（通用换行）vs decode_text（产品口径）。

给 pending.service.set_batch_route 打桩，录下每一次 route 写盘的 note 与调用栈，
证明 dedupe 族有没有第二笔 route 重写。零出网零引擎零端口；隔离 JZO_DATA_DIR /
JZO_PLUGINS_DIR 进 .system_generated 临时区＋最小目录夹具插件，绝不碰本机 data/。
报告落 MD（禁 JSON）。

运行：``.venv/Scripts/python.exe docs/handoff/evidence/note-warn-merge/replay_note_warn.py``
"""
from __future__ import annotations

import asyncio
import base64
import os
import sys
import threading
import traceback
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
sys.path.insert(0, str(ROOT))

E2E = ROOT / ".system_generated" / "note-warn-merge" / "e2e"
DATA_DIR = E2E / "data"
PLUGINS_DIR = E2E / "plugins"
for folder in (DATA_DIR, PLUGINS_DIR):
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

WRITES: list[str] = []
_orig = pending.set_batch_route


def _spy(batch_id, payload):
    note = str((payload or {}).get("note") or "")
    stack = "".join(traceback.format_stack()[-5:-1])
    WRITES.append(f"--- write batch={batch_id} note={note!r}\n{stack}")
    return _orig(batch_id, payload)


pending.set_batch_route = _spy


def _url(text: str) -> str:
    return "data:text/markdown;base64," + base64.b64encode(
        text.encode("utf-8")).decode("ascii")


def _join_dedupe() -> None:
    for thread in threading.enumerate():
        if thread.name.startswith("jzo-dedupe-warm"):
            thread.join(timeout=10)


def _ingest(name: str, text: str) -> tuple[str, str, int]:
    before = len(WRITES)
    result = asyncio.run(service.ingest_files([{"name": name, "data_url": _url(text)}]))
    _join_dedupe()
    bid = result["batch_ids"][0]
    rows = pending.list_batch_questions(bid)
    note = str((rows.get("route") or {}).get("note") or "")
    return note, bid, len(WRITES) - before


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    write_catalog_plugin(PLUGINS_DIR)
    lines = ["# note-warn-merge 侦查回放报告（全接线 service.ingest_files）", "",
             "- 入口：ingest_files → stage_ingest → run_ingest_jobs → media._items_from_file",
             "  → build_documents → shapes.normalize → pending.save_draft → 待审池读回",
             "- dedupe 抽走**启用态**（未设 JZO_POOL_ADMIT_DISABLED），后台初查线程 join 后再读",
             f"- 隔离底座：data={DATA_DIR} plugins={PLUGINS_DIR}", ""]

    note_lf, bid_lf, writes_lf = _ingest("lf_warn.md", WARN_MD)
    note_crlf, bid_crlf, writes_crlf = _ingest("crlf_warn.md", WARN_MD.replace("\n", "\r\n"))
    note_plain, bid_plain, writes_plain = _ingest("lf_plain.md", PLAIN_MD)

    lines.extend(["## 池内 route.note 实测", "",
                  f"- LF 带卷首图（batch={bid_lf}）：note={note_lf!r}",
                  f"  - 含剥图警告：{'是' if '题干图片行已剥离' in note_lf else '否'}；route 写盘笔数={writes_lf}",
                  f"- CRLF 同文（batch={bid_crlf}）：note={note_crlf!r}",
                  f"  - 含剥图警告：{'是' if '题干图片行已剥离' in note_crlf else '否'}；route 写盘笔数={writes_crlf}",
                  f"- LF 无图（batch={bid_plain}）：note={note_plain!r}；route 写盘笔数={writes_plain}", ""])

    lines.extend(["## shapes.normalize 边界对照（警告来源口径）", ""])
    norm_lf, warns_lf = shapes.normalize(WARN_MD)
    crlf_text = decode_text(WARN_MD.replace("\n", "\r\n").encode("utf-8"))
    norm_crlf, warns_crlf = shapes.normalize(crlf_text)
    lines.extend([f"- LF 文本直喂：警告 {len(warns_lf)} 条，图片行被剥={'是' if '![](images/header_photo.jpg)' not in norm_lf else '否'}",
                  f"- CRLF 经产品 decode_text：警告 {len(warns_crlf)} 条，"
                  f"图片行原样留存={'是' if '![](images/header_photo.jpg)' in norm_crlf else '否'}"
                  "（剥行未生效；normalize 若改写文本只是文末选项并段，与剥图无关）",
                  "- 口径：decode_text（text.py:117-124）不做换行归一，\\r 原样进解析；",
                  "  shapes._IMAGE_LINE（shapes.py:37）行尾只认 `[ \\t]*$`，\\r 不在其中 → CRLF 图片行不匹配。", ""])

    lines.extend(["## set_batch_route 全部写盘记录（含调用栈）", ""])
    lines.extend(WRITES)
    (OUT / "replay_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:16]))
    print("total route writes:", len(WRITES))


if __name__ == "__main__":
    main()