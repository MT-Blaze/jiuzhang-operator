# -*- coding: utf-8 -*-
"""种子渲染探针（2.21.0 卡 §2/§6 探针①）：MathJax 逐条过闭集种子变体。

用法：``.venv/Scripts/python.exe tools/latex_norm_render_probe.py <tag> [--live]``

隔离：JZO_DATA_DIR 指临时目录，种子导入副本；localhost 动态端口伺服渲染页，
MathJax 用仓内 vendor  bundle——零引擎、零出网。不认的命令显性 render_supported=0
＋原因（全量红线不静默丢），不进清洗改写。``--live`` 另把结论回写真实整机库
（卡 §1 白名单 data/latex_norm.db），幂等导入不覆盖老师选择。

渲染判据沿用宿主公式桥 JzoMath.render：失败（抛错／merror／红字）返空串＝不支持。
需参数才有意义的单命令码由探针补样例参数（不改种子码本身）。
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

import argparse
import html
import http.server
import os
import secrets
import shutil
import tempfile
import threading
from pathlib import Path

from app.core import toml_io
from app.core.content import latex_norm
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "static" / "vendor" / "mathjax"

_ARG_WRAPPER = {
    "frac": "{a}{b}", "dfrac": "{a}{b}", "tfrac": "{a}{b}",
    "binom": "{n}{k}", "dbinom": "{n}{k}", "tbinom": "{n}{k}", "sqrt": "{x}",
    "hat": "{a}", "widehat": "{a}", "tilde": "{a}", "widetilde": "{a}",
    "bar": "{a}", "overline": "{a}", "vec": "{a}", "dot": "{a}", "ddot": "{a}",
    "dddot": "{a}", "acute": "{a}", "grave": "{a}", "check": "{a}", "breve": "{a}",
    "mathring": "{a}", "underline": "{a}", "overrightarrow": "{a}",
    "overleftarrow": "{a}", "overleftrightarrow": "{a}",
    "overbrace": "{a+b}", "underbrace": "{a+b}",
    "mathbb": "{R}", "mathbf": "{R}", "mathrm": "{R}", "mathcal": "{R}",
    "mathit": "{R}", "mathsf": "{R}", "mathtt": "{R}", "boldsymbol": "{R}",
    "operatorname": "{sin}", "overset": "{a}{b}", "underset": "{a}{b}", "stackrel": "{a}{b}",
}


def _render_code(code: str) -> str:
    name = latex_norm._command_name(code)
    return code + _ARG_WRAPPER[name] if name in _ARG_WRAPPER else code


def _build_page(variants: list[dict]) -> str:
    cells = []
    for item in variants:
        cells.append(
            f'<div class="cell" data-idx="{item["idx"]}" '
            f'data-code="{html.escape(item["render_code"], quote=True)}">'
            f'<span class="tag">{html.escape(item["entry_key"])}·{item["row_order"]}</span></div>')
    return """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>记号标准字典·种子渲染探针</title>
<script src="jzo_mathjax.js"></script><script src="tex-svg-full.js"></script>
<style>body{font-family:sans-serif;margin:12px}
.grid{display:flex;flex-wrap:wrap;gap:8px}
.cell{border:1px solid #ccc;border-radius:6px;padding:6px 8px;min-width:90px;text-align:center}
.cell.bad{border-color:#c00;background:#fff0f0}
.tag{display:block;font-size:10px;color:#888;margin-bottom:2px}
h1{font-size:16px}#status{font-size:12px;color:#555}</style></head>
<body><h1>闭集种子变体·MathJax 逐条渲染</h1><p id="status">渲染中…</p>
<div class="grid">__CELLS__</div>
<script>
window.__results = []; window.__done = false;
JzoMath.onReady(function () {
  var cells = document.querySelectorAll(".cell");
  for (var i = 0; i < cells.length; i++) {
    var cell = cells[i];
    var code = cell.getAttribute("data-code");
    var svg = JzoMath.render(code, true);
    var ok = svg !== "";
    if (ok) { cell.insertAdjacentHTML("beforeend", svg); }
    else { cell.classList.add("bad"); cell.insertAdjacentHTML("beforeend", "<code>" + code + "</code>"); }
    window.__results.push({ idx: Number(cell.getAttribute("data-idx")), supported: ok });
  }
  var bad = window.__results.filter(function (r) { return !r.supported; }).length;
  document.getElementById("status").textContent =
    "共 " + window.__results.length + " 条，支持 " + (window.__results.length - bad) + "，不支持 " + bad;
  window.__done = true;
});
</script></body></html>""".replace("__CELLS__", "".join(cells))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag")
    parser.add_argument("--live", action="store_true", help="另把结论回写真实整机库（卡白名单）")
    args = parser.parse_args()

    out = ROOT / ".system_generated" / "latex-norm" / "render" / args.tag
    out.mkdir(parents=True, exist_ok=True)
    nonce = secrets.token_hex(8)

    tmp = tempfile.TemporaryDirectory()
    old_data = os.environ.get("JZO_DATA_DIR")
    os.environ["JZO_DATA_DIR"] = str(Path(tmp.name) / "data")
    Path(os.environ["JZO_DATA_DIR"]).mkdir()
    rc = 0
    try:
        report = latex_norm.import_seed()
        variants = []
        idx = 0
        for entry in latex_norm.list_entries():
            for variant in entry["variants"]:
                variants.append({
                    "idx": idx, "entry_key": entry["entry_key"],
                    "row_order": variant["row_order"], "latex_code": variant["latex_code"],
                    "render_code": _render_code(variant["latex_code"]),
                })
                idx += 1

        serve = Path(tmp.name) / "serve"
        serve.mkdir()
        shutil.copy(VENDOR / "jzo_mathjax.js", serve / "jzo_mathjax.js")
        shutil.copy(VENDOR / "tex-svg-full.js", serve / "tex-svg-full.js")
        (serve / "probe.html").write_text(_build_page(variants), encoding="utf-8")

        handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(serve), **kw)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        page_errors: list[str] = []
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                page.goto(f"http://127.0.0.1:{port}/probe.html", wait_until="load", timeout=60000)
                page.wait_for_function("window.__done === true", timeout=120000)
                results = page.evaluate("window.__results")
                page.screenshot(path=str(out / "render-grid.png"), full_page=True)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

        by_idx = {r["idx"]: r["supported"] for r in results}
        for item in variants:
            item["supported"] = bool(by_idx.get(item["idx"], False))
            item["note"] = "" if item["supported"] else "MathJax 渲染失败（未定义命令或 merror／红字）"
        supported = sum(1 for v in variants if v["supported"])
        unsupported = len(variants) - supported

        applied = latex_norm.apply_render_report(variants)
        if len(results) != len(variants) or applied != len(variants):
            rc = 1
        if page_errors:
            rc = 1

        probe_report = {
            "probe": "latex_norm_render", "tag": args.tag, "nonce": nonce, "port": port,
            "engine": "MathJax tex-svg-full（仓内 vendor，localhost 静态页）",
            "outbound": "零出网", "seed_version": report["seed_version"],
            "variant_total": len(variants), "supported": supported, "unsupported": unsupported,
            "applied_to_isolated_db": applied, "page_errors": page_errors,
            "screenshot": str(out / "render-grid.png"),
            "variants": [{k: v for k, v in item.items() if k != "idx"} for item in variants],
        }
        (out / "probe.toml").write_text(toml_io.dumps(probe_report), encoding="utf-8")
        shutil.copy(serve / "probe.html", out / "probe.html")

        print(f"种子变体 {len(variants)} 条：支持 {supported}／不支持 {unsupported}；回写副本 {applied} 条")
        for item in variants:
            if not item["supported"]:
                print(f"  [unsupported] {item['entry_key']}·{item['row_order']}  {item['latex_code']}")
        if page_errors:
            print("  [pageerror]", page_errors)
        print(f"证据：{out / 'probe.toml'}")

        if args.live:
            if old_data is None:
                os.environ.pop("JZO_DATA_DIR", None)
            else:
                os.environ["JZO_DATA_DIR"] = old_data
            live_seed = latex_norm.import_seed()
            live_applied = latex_norm.apply_render_report(variants)
            print(f"[live] 真实整机库 {latex_norm.settings.latex_norm_db_path}")
            print(f"[live] 种子 added={live_seed['entries_added']} skipped={live_seed['entries_skipped']}；渲染回写 {live_applied} 条")
    finally:
        if old_data is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = old_data
        tmp.cleanup()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())