# -*- coding: utf-8 -*-
"""S9b · 真浏览器验收（Playwright chromium 真点真截，不是 DOM 口头账）。

复用 tools/pool_canvas_probe.py 的现成起服务与帧定位助法（隔离 JZO_DATA_DIR、
随机端口、自带一次性令牌、不碰真实 data/）。三个验收面：
  B1 启动即看：AI 帮改区默认展开（body 非背景像素占比）＋说明区可见；
  B2 池子有货默认展开：不点入口钮，池段可见且条目数>=2；空池半边仍隐藏（判据 5.3）；
  B3 回归：手动点收 body 真不占位；再点开恢复。
发现现象只记录不修：本脚本不写 dist/、app/。
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import pool_canvas_probe as pcp  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402


def decode_png(png: Path):
    """极简 PNG 解码（标准库 zlib，.venv 里没有 PIL）：仅支持 Playwright 截图
    的 8bit 非隔行 RGBA/RGB/灰度，返回 (width, height, rows)，行为 bytes。"""
    import struct
    import zlib
    data = png.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a png"
    pos, idat, meta = 8, b"", None
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, color, _comp, _filt, interlace = struct.unpack(">IIBBBBB", chunk[:13])
            assert depth == 8 and interlace == 0, f"unsupported png {depth}/{interlace}"
            ch = {0: 1, 2: 3, 4: 2, 6: 4}[color]
            meta = (w, h, ch)
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    w, h, ch = meta
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytes(stride)
    rows = []
    i = 0
    for _ in range(h):
        ft = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        if ft == 1:
            for x in range(ch, stride):
                line[x] = (line[x] + line[x - ch]) & 255
        elif ft == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif ft == 3:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif ft == 4:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                b = prev[x]
                c = prev[x - ch] if x >= ch else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, ch, rows


def nonbg_ratio(png: Path, box) -> dict:
    """在截图 png 的 box=[l,t,r,b] 区域里量「非背景像素占比」。

    背景色＝区域四角 16px 众数；非背景＝与该色逐通道最大差 >24 的像素。
    """
    w, h, ch, rows = decode_png(png)
    if box is None:
        box = [0, 0, w, h]
    l, t, r, b = [int(v) for v in box]
    l, t = max(0, l), max(0, t)
    r, b = min(w, r), min(h, b)
    if r <= l or b <= t:
        return {"box": box, "area": 0, "nonbg": 0, "ratio": 0.0, "degenerate": True}
    corners = []
    for cx, cy in ((l, t), (r - 1, t), (l, b - 1), (r - 1, b - 1)):
        for dy in range(cy - 4, cy + 4):
            if 0 <= dy < h:
                for dx in range(cx - 4, cx + 4):
                    if 0 <= dx < w:
                        px = rows[dy][dx * ch:dx * ch + 3]
                        corners.append(tuple(px))
    bg = Counter(corners).most_common(1)[0][0]
    area = hits = 0
    for y in range(t, b):
        row = rows[y]
        for x in range(l, r):
            px = row[x * ch:x * ch + 3]
            area += 1
            if max(abs(px[0] - bg[0]), abs(px[1] - bg[1]), abs(px[2] - bg[2])) > 24:
                hits += 1
    return {"box": [l, t, r, b], "area": area, "nonbg": hits,
            "ratio": round(hits / max(1, area), 4), "bg": list(bg)}

EVIDENCE = (ROOT / ".qoder" / "records" / "biz" / "2026-11" /
            "20261103_order32-s6-evidence")


def fold_state(frame):
    return frame.evaluate("""() => {
        const sec=document.getElementById('epAiSec');
        const fold=document.getElementById('epAiFold');
        const body=document.getElementById('epAiFoldBody');
        if(body && body.scrollIntoView){body.scrollIntoView({block:'center'});}
        const root=document.querySelector('.ep-root')||document.body;
        const rr=root.getBoundingClientRect();
        const br=body?body.getBoundingClientRect():null;
        const cs=body?getComputedStyle(body):null;
        const sum=fold?fold.querySelector('.ep-fold-summary'):null;
        const ssum=sum?sum.getBoundingClientRect():null;
        return {dataFold: sec?sec.getAttribute('data-fold'):null,
                aria: fold?fold.getAttribute('aria-expanded'):null,
                bodyDisplay: cs?cs.display:null, bodyVisibility: cs?cs.visibility:null,
                bodyH: br?Math.round(br.height):null,
                bodyBox: br?[br.left-rr.left, br.top-rr.top, br.right-rr.left, br.bottom-rr.top]:null,
                summaryVisible: Boolean(sum && ssum && ssum.width>0 && ssum.height>0
                    && getComputedStyle(sum).display!=='none'),
                summaryText: sum?(sum.innerText||'').trim():null};}""")


def pool_state(frame):
    return frame.evaluate("""() => {
        const sec=document.getElementById('epPoolSec');
        const cs=sec?getComputedStyle(sec):null;
        const rows=sec?sec.querySelectorAll('.ep-pool-row').length:null;
        const trig=sec?sec.querySelectorAll('.ep-pool-trigger').length:null;
        const entry=document.getElementById('epPoolEntry');
        const er=entry?entry.getBoundingClientRect():null;
        const rr=(document.querySelector('.ep-root')||document.body).getBoundingClientRect();
        const sr=sec?sec.getBoundingClientRect():null;
        return {present: Boolean(sec), hidden: sec?sec.hidden:null,
                display: cs?cs.display:null,
                rows: rows, triggers: trig,
                entryPresent: Boolean(entry),
                entryAria: entry?entry.getAttribute('aria-expanded'):null,
                entryVisible: Boolean(er && er.width>0 && er.height>0),
                secBox: sr?[Math.round(sr.left-rr.left),Math.round(sr.top-rr.top),
                            Math.round(sr.right-rr.left),Math.round(sr.bottom-rr.top)]:null,
                text: sec?(sec.innerText||'').trim().slice(0,140):null};}""")


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("s9b%H%M%S")
    pcp.NOTES["tag"] = tag
    work = ROOT / ".system_generated" / "s9b" / tag
    if work.exists():
        shutil.rmtree(work)
    pcp.SHOTS = work / "shots"
    pcp.PANELS = work / "panels"
    data_dir, plugins_dir = work / "data", work / "plugins"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    for pid in (pcp.EDITOR_ID, pcp.BANK_ID, pcp.BANK_UI_ID, pcp.CHAT_ID):
        shutil.copytree(ROOT / "plugins" / pid, plugins_dir / pid)
    port = pcp.free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.pop("JZO_POOL_ADMIT_DISABLED", None)
    env.update(JZO_DATA_DIR=str(data_dir), JZO_PLUGINS_DIR=str(plugins_dir),
               JZO_LOCAL_TOKEN=pcp.TOKEN, JZO_RESTART_DISABLED="1")
    log_path = work / "server.log"
    handle = log_path.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "info",
         "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)
    try:
        pcp.wait_health(base, proc, log_path)
        _, tt = pcp.GET(base + f"/api/bank/plugins/{pcp.BANK_ID}/topics")
        items = (tt.get("items") if isinstance(tt, dict) else tt) or []
        first = items[0] if items else {}
        pcp.LIVE_TOPIC["id"] = str((first or {}).get("id")
                                   or (first or {}).get("topic_id") or "") or None

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(base + "/workspace", wait_until="networkidle")
            pcp.reopen_editor(page)
            panel = pcp.frame_with(page, "#epRoot")
            if panel is None:
                pcp.check("S9b 开机进画布", False, {"panel": None})
                browser.close()
                return 1

            # ---- B0 空池半边：判据 5.3 留白不许被默认展开弄没 ----
            empty = pool_state(panel)
            s0 = pcp.shot(panel.locator(".ep-root"), f"panel{tag}-00-emptypool.png", page=page)
            pcp.check("B0 空池仍整段隐藏（默认展开只作用于有货）",
                      empty.get("present") and (empty.get("hidden") or empty.get("display") == "none"),
                      {"state": empty, "shot": s0.name if s0 else None})

            # ---- B1 AI 帮改：启动即展开，非背景像素实量 ----
            st1 = fold_state(panel)
            page.wait_for_timeout(250)
            s1 = pcp.shot(panel.locator("#epAiFoldBody"), f"panel{tag}-01-ai-default-open-body.png", page=page)
            pix1 = nonbg_ratio(s1, None) if s1 else {"missing": True}
            pcp.check("B1 默认展开：open/true，body 有占位且量到非背景像素，说明区可见",
                      st1.get("dataFold") == "open" and st1.get("aria") == "true"
                      and (st1.get("bodyH") or 0) > 0 and pix1.get("nonbg", 0) > 0
                      and st1.get("summaryVisible"),
                      {"fold": st1, "pixel": pix1, "shot": s1.name if s1 else None})

            # ---- B3 回归：点收→不占位；点开→恢复 ----
            panel.locator("#epAiFold").click()
            page.wait_for_timeout(250)
            st2 = fold_state(panel)
            s2 = pcp.shot(panel.locator(".ep-root"), f"panel{tag}-02-ai-manual-close.png", page=page)
            pcp.check("B3a 手动点收：closed/false，body 真的不占位",
                      st2.get("dataFold") == "closed" and st2.get("aria") == "false"
                      and (st2.get("bodyH") == 0 or st2.get("bodyDisplay") == "none"),
                      {"fold": st2, "shot": s2.name if s2 else None})
            panel.locator("#epAiFold").click()
            page.wait_for_timeout(250)
            st3 = fold_state(panel)
            pcp.check("B3b 再点开恢复：open/true，body 重新占位",
                      st3.get("dataFold") == "open" and st3.get("aria") == "true"
                      and (st3.get("bodyH") or 0) > 0,
                      {"fold": st3})

            # ---- 造池内现场：主库 3 道 → 重题批 2 条 certain/very ----
            _, b_orig = pcp.POST(base + "/api/pending/batches",
                                 {"questions": [pcp.doc(pcp.S1), pcp.doc(pcp.S2), pcp.doc(pcp.S3)]})
            orig_batch = str(b_orig.get("batch_id") or "")
            ids = [it.get("id") for it in (pcp.GET(base + f"/api/pending/batches/{orig_batch}/questions")[1]
                                           .get("items") or [])]
            for pid in ids:
                pcp.POST(base + f"/api/pending/items/{pid}/approve", {})
            _, b_dup = pcp.POST(base + "/api/pending/batches", {"questions": [
                pcp.doc(pcp.S1),
                pcp.doc(pcp.S2.replace("$\\{a_n\\}$", "$\\{ a_n \\}$"))]})
            deadline = time.time() + 90
            pool_total = 0
            while time.time() < deadline:
                pool_total = (pcp.GET(base + "/api/pending/pool")[1].get("total") or 0)
                if pool_total >= 2:
                    break
                time.sleep(0.5)
            pcp.NOTES["pool_total_seeded"] = pool_total

            # ---- B2 有货默认展开：reload 重进，不点入口钮 ----
            page.reload(wait_until="networkidle")
            pcp.reopen_editor(page)
            panel2 = pcp.frame_with(page, "#epRoot")
            got = pool_state(panel2)
            s3_ = pcp.shot(panel2.locator(".ep-root"), f"panel{tag}-03-pool-default-expanded.png", page=page)
            pix2 = nonbg_ratio(s3_, got["secBox"]) if (s3_ and got.get("secBox")) else {"missing": True}
            pcp.check("B2 池子有货默认展开：不点 #epPoolEntry，段可见、行数>=2、量到非背景像素",
                      pool_total >= 2 and not (got.get("hidden") or got.get("display") == "none")
                      and (got.get("rows") or 0) >= 2 and pix2.get("nonbg", 0) > 0,
                      {"seeded_total": pool_total, "state": got, "pixel": pix2,
                       "shot": s3_.name if s3_ else None,
                       "entry_touched": False})
            browser.close()

        ok = sum(1 for c in pcp.CHECKS if c["ok"])
        body = {"tag": tag, "checks": pcp.CHECKS, "notes": pcp.NOTES,
                "all_pass": ok == len(pcp.CHECKS)}
        (EVIDENCE / f"s9b_browser_proof_{tag}.toml").write_text(
            toml_io.dumps(body), encoding="utf-8")
        for src in sorted(list(pcp.SHOTS.glob("*.png")) + list(pcp.PANELS.glob("*.png"))):
            shutil.copy2(src, EVIDENCE / f"s9b_shot_{src.stem}{src.suffix}".replace("panel", ""))
        print("=" * 60)
        print(f"S9b 浏览器验收 {len(pcp.CHECKS)} 项，通过 {ok}，失败 {len(pcp.CHECKS) - ok}，tag={tag}")
        return 0 if ok == len(pcp.CHECKS) else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        handle.close()


if __name__ == "__main__":
    sys.exit(main())
