# -*- coding: utf-8 -*-
"""数据看板插件真机取证（军令 #11 阶段二）：装进去能不能跑通看板全链路。

用法：``.venv/Scripts/python.exe tools/dashboard_probe.py <out_dir_tag>``
（脚本自己在 8781 起隔离服务，跑完关掉）

隔离口径：``JZO_DATA_DIR`` 与 ``JZO_PLUGINS_DIR`` 指向 ``.system_generated/dashboard-probe/<tag>/``，
不碰开发者本机的 ``data/`` 与 ``plugins/``。官方 core-bank（含本机种子题库）只读复制进隔离目录，
供「点击最近题目 → 跳转题库」的黄金路径取证。

判据：
  1. 底座发现 org.jiuzhang.dashboard、零拒收；左栏列出「数据看板」入口（顺序按发现序，不锁第一位）；
  2. 点入口开画布页签，iframe 沙箱为 allow-scripts allow-modals，activate 回 ready（底栏 plugin.mounted）；
  3. 四张卡片渲染出真实数字，且总题数与后端 /api/bank/dashboard/stats 逐字一致；
  4. 热力图是 CSS Grid 绿格子：格子总数 = 365 + 周对齐补位，非零格数与后端按日计数一致；
  5. 最近录入 ≤5 条；点击第一条 → 宿主打开活跃题库（core-bank）页签（system.open_bank 走白名单）；
  6. 底栏出现「数据看板已就绪」；全程宿主页无未捕获 JS 错误。
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8781
BASE = f"http://127.0.0.1:{PORT}/workspace"
PLUGIN_ID = "org.jiuzhang.dashboard"
BANK_ID = "org.jiuzhang.core-bank"


def wait_port(deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.5)
    return False


def http_get(path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=20) as resp:
        return json.loads(resp.read())


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "dashboard-probe" / tag
    data_dir = out / "data"
    plugins_dir = out / "plugins"
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)

    report = {"tag": tag, "checks": [], "console": [], "errors": [], "shots": [], "notes": {}}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
        return bool(ok)

    # 只读复制两个插件进隔离目录：看板本体 + 官方题库（跳转目标与真实数据源）
    shutil.copytree(ROOT / "plugins" / PLUGIN_ID, plugins_dir / PLUGIN_ID)
    source_bank = ROOT / "plugins" / BANK_ID
    if source_bank.is_dir():
        shutil.copytree(source_bank, plugins_dir / BANK_ID)
        report["notes"]["core_bank_copied"] = True
    check("看板与题库插件复制进隔离目录", (plugins_dir / PLUGIN_ID / "plugin.json").is_file())

    env = dict(os.environ)
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_PORT"] = str(PORT)
    env.pop("JZO_AI_API_KEY", None)
    env.pop("JZO_AI_BASE_URL", None)

    server = subprocess.Popen(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

    try:
        if not wait_port(40):
            check("隔离服务起在 8781", False, "服务未在 40 秒内监听")
            return finish(report, out)
        check("隔离服务起在 8781", True, f"data={data_dir}")
        time.sleep(1.5)

        discovery = http_get("/api/plugins")
        plugins = discovery.get("plugins") or []
        entry = next((p for p in plugins if p.get("id") == PLUGIN_ID), None)
        check("底座发现数据看板（未拒收）", entry is not None,
              f"count={len(plugins)} rejected={json.dumps(discovery.get('rejected'), ensure_ascii=False)}")

        backend_stats = http_get("/api/bank/dashboard/stats")
        backend_heat = http_get("/api/bank/dashboard/heatmap")
        report["notes"]["backend_stats"] = {k: backend_stats.get(k) for k in
                                            ("total_questions", "today_added", "pending_review", "stored_total")}
        nonzero_days = sum(1 for cell in backend_heat if cell.get("count", 0) > 0)
        report["notes"]["nonzero_days"] = nonzero_days

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: report["console"].append({"type": m.type, "text": m.text[:300]}))
            page.on("pageerror", lambda e: report["errors"].append(str(e)[:300]))
            page.goto(BASE, wait_until="networkidle")
            page.wait_for_timeout(1000)

            def snap(step):
                png = out / f"{step}.png"
                page.screenshot(path=str(png))
                report["shots"].append(str(png))

            sidebar_first = page.evaluate("""
            () => {
              const items = Array.from(document.querySelectorAll('#wsPluginList .ws-plugin-item'));
              return items.map(b => b.textContent.replace(/\\s+/g, ' ').trim().slice(0, 30));
            }
            """)
            report["notes"]["sidebar_order"] = sidebar_first
            # 左栏顺序 = 用户排的序 + 树上还没有的按发现顺序追加（app/core/plugins.py
            # _sidebar_with_unlisted 的既有设计），空树首启时 core-bank 天然排在 dashboard 前；
            # 本判据只验「看板入口在不在、能不能点开」，不锁死第一位。
            check("左栏列出数据看板", any("数据看板" in text for text in sidebar_first),
                  json.dumps(sidebar_first, ensure_ascii=False))
            snap("00-sidebar")

            page.evaluate("""
            () => {
              const t = Array.from(document.querySelectorAll('#wsPluginList .ws-plugin-item'))
                .find(b => b.textContent.indexOf('数据看板') >= 0);
              if (t) t.click();
            }
            """)
            page.wait_for_timeout(2500)

            tabs = page.evaluate("""
            () => Array.from(document.querySelectorAll('#wsTabs .ws-tab')).map(t => t.getAttribute('data-tab'))
            """)
            frame_info = page.evaluate("""
            () => {
              const panel = document.querySelector('.ws-tab-panel[data-tab="plugin:%ID%"]');
              const frame = panel ? panel.querySelector('.ws-plugin-frame') : null;
              return {
                sandbox: frame ? frame.getAttribute('sandbox') : null,
                src: frame ? (frame.getAttribute('src') || '').slice(0, 90) : null,
                panelError: panel ? ((panel.querySelector('.ws-frame-error') || {}).textContent || '') : '无面板'
              };
            }
            """.replace("%ID%", PLUGIN_ID))
            check("点入口开出画布页签", f"plugin:{PLUGIN_ID}" in tabs, json.dumps(tabs))
            check("iframe 沙箱为 allow-scripts allow-modals", frame_info["sandbox"] == "allow-scripts allow-modals",
                  str(frame_info["sandbox"]))
            check("挂载无故障框", not frame_info["panelError"], frame_info["panelError"])
            snap("10-opened")

            dock_text = page.evaluate("""
            () => {
              const dock = document.getElementById('wsDockLog');
              return dock ? dock.textContent.replace(/\\s+/g, ' ') : '';
            }
            """)
            check("底栏记 plugin.mounted / 已就绪",
                  ("已挂载并就绪" in dock_text) or ("数据看板已就绪" in dock_text), dock_text[-300:])

            # 进沙箱帧取渲染证据（Playwright 走 CDP，可跨不透明源帧 evaluate）
            real_frame = None
            for f in page.frames:
                if "/plugin-assets/" + PLUGIN_ID + "/" in (f.url or ""):
                    real_frame = f
                    break
            check("定位到看板沙箱帧", real_frame is not None, [f.url for f in page.frames][:4])
            if real_frame is None:
                return finish(report, out)

            # 等数据往返完成：卡片值离开占位符「—」
            ui = {}
            for _ in range(20):
                ui = real_frame.evaluate("""
                () => {
                  const cards = Array.from(document.querySelectorAll('.db-card')).map(c => ({
                    kind: c.getAttribute('data-kind'),
                    label: (c.querySelector('.db-card-label') || {}).textContent || '',
                    value: (c.querySelector('.db-card-value') || {}).textContent || ''
                  }));
                  const cells = Array.from(document.querySelectorAll('#dbHeatmap .db-cell'));
                  const visible = cells.filter(c => c.style.visibility !== 'hidden');
                  const nonzero = visible.filter(c => c.getAttribute('data-level') !== '0');
                  const recent = Array.from(document.querySelectorAll('.db-recent-link')).map(b =>
                    (b.querySelector('.db-recent-stem') || {}).textContent || '');
                  const heatDisplay = getComputedStyle(document.getElementById('dbHeatmap')).display;
                  return { cards, totalCells: cells.length, visibleCells: visible.length,
                           nonzeroCells: nonzero.length, recent, heatDisplay,
                           error: (document.querySelector('.db-error') || {}).textContent || '' };
                }
                """)
                if ui.get("cards") and all(c["value"] != "—" for c in ui["cards"]):
                    break
                page.wait_for_timeout(500)
            report["notes"]["ui"] = {k: ui.get(k) for k in
                                     ("totalCells", "visibleCells", "nonzeroCells", "heatDisplay", "error")}
            report["notes"]["cards"] = ui.get("cards")
            report["notes"]["recent"] = ui.get("recent")
            check("沙箱内无错误框", not ui.get("error"), ui.get("error", ""))

            card_map = {c["kind"]: c["value"] for c in (ui.get("cards") or [])}
            check("四张卡片渲染出数字", len(card_map) == 4 and all(v not in ("", "—") for v in card_map.values()),
                  json.dumps(card_map, ensure_ascii=False))
            check("总题数与后端逐字一致",
                  card_map.get("total") == str(backend_stats.get("total_questions")),
                  f"ui={card_map.get('total')} backend={backend_stats.get('total_questions')}")
            check("待审核与后端逐字一致",
                  card_map.get("pending") == str(backend_stats.get("pending_review")),
                  f"ui={card_map.get('pending')} backend={backend_stats.get('pending_review')}")

            check("热力图是 CSS Grid", ui.get("heatDisplay") == "grid", str(ui.get("heatDisplay")))
            check("热力图格子恰为 365 天 + 周对齐补位",
                  ui.get("visibleCells") == 365 and (ui.get("totalCells") or 0) >= 365
                  and (ui.get("totalCells") or 0) <= 365 + 6,
                  f"visible={ui.get('visibleCells')} total={ui.get('totalCells')}")
            check("非零格子数与后端按日计数一致",
                  ui.get("nonzeroCells") == nonzero_days,
                  f"ui={ui.get('nonzeroCells')} backend={nonzero_days}")

            recent = ui.get("recent") or []
            check("最近录入 ≤5 条且已渲染", 0 < len(recent) <= 5, json.dumps(recent, ensure_ascii=False)[:200])
            snap("20-dashboard")

            # 点击第一条最近题目 → system.open_bank → 宿主打开活跃题库页签
            real_frame.evaluate("""
            () => {
              const b = document.querySelector('.db-recent-link');
              if (b) b.click();
            }
            """)
            page.wait_for_timeout(2500)
            tabs_after = page.evaluate("""
            () => Array.from(document.querySelectorAll('#wsTabs .ws-tab')).map(t => t.getAttribute('data-tab'))
            """)
            check("点击最近题目跳转到题库页签（system.open_bank 走白名单）",
                  f"plugin:{BANK_ID}" in tabs_after, json.dumps(tabs_after))
            dock_after = page.evaluate("""
            () => {
              const dock = document.getElementById('wsDockLog');
              return dock ? dock.textContent.replace(/\\s+/g, ' ') : '';
            }
            """)
            check("底栏记了跳转/未授权丢弃不得出现",
                  ("已跳转到题库" in dock_after or "正在打开题库" in dock_after)
                  and "未授权事件" not in dock_after, dock_after[-300:])
            snap("30-jumped-to-bank")

            check("宿主页无未捕获 JS 错误", len(report["errors"]) == 0, report["errors"][:3])
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:  # noqa: BLE001
            server.kill()

    return finish(report, out)


def finish(report: dict, out: Path) -> dict:
    total = len(report["checks"])
    passed = sum(1 for c in report["checks"] if c["ok"])
    report["summary"] = {"total": total, "passed": passed, "failed": total - passed,
                         "pageErrors": len(report["errors"])}
    out.mkdir(parents=True, exist_ok=True)
    (out / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["out_dir"] = str(out)
    return report


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    result = run(tag)
    print(json.dumps(result["summary"], ensure_ascii=False))
    for c in result["checks"]:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + " :: " + c["detail"][:160])
    print("out_dir:", result.get("out_dir"))
    sys.exit(0 if result["summary"]["failed"] == 0 else 1)
