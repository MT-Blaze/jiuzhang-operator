# -*- coding: utf-8 -*-
"""工作台左栏折叠状态机：真机取证脚本（Playwright + Chromium）。

用法：python tools/fold_probe.py <out_dir_tag>
产出：截图 png + probe.json（结构化度量与 console 错误）

判据来自 10.24 军令：
  - 折叠/展开 5 轮，grid 轨道必须随之在 240px/0 之间切换，不得残留空列
  - 展开入口（#wsOpenSidebar）在收起态必须可见、命中测试必须落在自己身上
  - 侧栏收起时其内部按钮/长文本不得越过左边界进入主对话区（溢出检查）
  - 360px 窄屏抽屉必须能滑出、能收起，且收起时不可命中
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8777/workspace"

# 舞台头里除「任务」钮之外的兄弟，用来判断按钮是否被遮挡
JS_STATE = """
() => {
  const page = document.querySelector('.ws-page');
  const sb = document.getElementById('wsSidebar');
  const drawer = document.getElementById('wsOpenSidebar');
  const toggle = document.getElementById('wsToggleSidebar');
  const center = document.querySelector('.ws-center');
  const ctx = document.getElementById('wsContext');
  const ctxTask = document.getElementById('ctxTask');
  const rect = el => {
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return {x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height)};
  };
  const box = rect(drawer);
  let hit = null;
  if (box && box.w > 0 && box.h > 0) {
    const el = document.elementFromPoint(box.x + box.w / 2, box.y + box.h / 2);
    hit = el ? (el.id || el.className || el.tagName) : 'none';
  }
  const tbox = rect(toggle);
  let thit = null;
  if (tbox && tbox.w > 0 && tbox.h > 0 && tbox.x >= 0) {
    const el = document.elementFromPoint(tbox.x + tbox.w / 2, tbox.y + tbox.h / 2);
    thit = el ? (el.id || el.className || el.tagName) : 'none';
  }
  // 侧栏内容是否溢出到主区：取侧栏内所有可绘元素的最右边界
  let rightmost = null;
  if (sb && getComputedStyle(sb).display !== 'none') {
    let max = -Infinity;
    sb.querySelectorAll('*').forEach(n => {
      const b = n.getBoundingClientRect();
      if (b.width > 0 && b.right > max) max = b.right;
    });
    rightmost = isFinite(max) ? Math.round(max) : null;
  }
  const csb = getComputedStyle(sb);
  return {
    vw: window.innerWidth,
    vh: window.innerHeight,
    dataSide: page.getAttribute('data-side'),
    dataCtx: page.getAttribute('data-ctx'),
    grid: getComputedStyle(page).gridTemplateColumns,
    sidebarDisplay: csb.display,
    sidebarTransform: csb.transform,
    sidebarRect: rect(sb),
    sidebarVisible: rect(sb).w > 1 && csb.display !== 'none',
    drawerDisplay: getComputedStyle(drawer).display,
    drawerRect: box,
    drawerHit: hit,
    drawerClickable: hit === 'wsOpenSidebar',
    toggleRect: tbox,
    toggleHit: thit,
    toggleReachable: thit === 'wsToggleSidebar',
    hOverflow: document.documentElement.scrollWidth - window.innerWidth,
    centerRect: rect(center),
    ctxRect: rect(ctx),
    ctxDisplay: getComputedStyle(ctx).display,
    ctxTaskRect: rect(ctxTask),
    toggleText: toggle ? toggle.textContent.trim() : null,
    sidebarRightmost: rightmost,
    overflowIntoCenter: (rightmost !== null && center && rect(center).w > 0)
      ? rightmost > Math.round(rect(center).x + 1)
      : false
  };
}
"""


def run(tag: str) -> dict:
    out = Path(__file__).resolve().parent.parent / ".system_generated" / "fold" / tag
    out.mkdir(parents=True, exist_ok=True)
    report = {"tag": tag, "shots": [], "states": [], "console": [], "errors": [], "deadlock": []}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height, label in (
            (1440, 900, "desktop"),
            (375, 780, "narrow"),   # AGENTS §6：375px 不得横向溢出
            (360, 740, "mobile"),
        ):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.on("console", lambda m, w=width: report["console"].append(
                {"vw": w, "type": m.type, "text": m.text[:300]}))
            page.on("pageerror", lambda e, w=width: report["errors"].append(
                {"vw": w, "text": str(e)[:300]}))
            page.goto(BASE, wait_until="networkidle")

            def snap(step):
                st = page.evaluate(JS_STATE)
                st["step"] = step
                st["label"] = label
                report["states"].append(st)
                png = out / f"{label}-{step}.png"
                page.screenshot(path=str(png))
                report["shots"].append(str(png))
                return st

            def real_click(sel, step):
                """真·指针点击：Playwright 会做命中测试，被遮挡即超时。
                超时 = 用户点不到 = 死锁，如实记录后用合成点击让流程继续。"""
                try:
                    page.locator(sel).click(timeout=2500)
                    return "pointer"
                except Exception as exc:  # noqa: BLE001
                    report["deadlock"].append(
                        {"label": label, "step": step, "selector": sel,
                         "msg": str(exc).splitlines()[0][:200]})
                    page.evaluate(
                        "s => document.querySelector(s).dispatchEvent("
                        "new MouseEvent('click', {bubbles:true, cancelable:true, view:window}))", sel)
                    return "synthetic-after-deadlock"

            snap("00-initial")
            for i in range(1, 6):
                # 状态机事实来源 = data-side；收起态点「任务」，展开态点「折叠」
                opening = report["states"][-1]["dataSide"] != "open"
                sel = "#wsOpenSidebar" if opening else "#wsToggleSidebar"
                real_click(sel, f"{i:02}-{'show' if opening else 'hide'}")
                page.wait_for_timeout(320)
                snap(f"{i:02}-{'show' if opening else 'hide'}")

            # 收尾：强制两种终态各测一次（纯 CSS 判据，不经 JS）
            page.evaluate("() => document.querySelector('.ws-page').setAttribute('data-side','hidden')")
            page.wait_for_timeout(320)
            snap("90-forced-hidden")
            if label == "desktop":
                # 双栏同时收起：自动定位时代中栏会被挤进 0px 轨道，这里单独验一次
                page.evaluate("() => document.querySelector('.ws-page').setAttribute('data-ctx','hidden')")
                page.wait_for_timeout(320)
                snap("91-forced-both-hidden")
                page.evaluate("() => document.querySelector('.ws-page').setAttribute('data-ctx','open')")
                page.wait_for_timeout(320)
            page.evaluate("() => document.querySelector('.ws-page').setAttribute('data-side','open')")
            page.wait_for_timeout(320)
            snap("92-forced-open")

            # 跨断点：窄屏收起的抽屉拖宽 / 桌面展开态拖窄，必须由状态机重算
            target = (500, 740) if label == "desktop" else (1000, 800)
            page.set_viewport_size({"width": target[0], "height": target[1]})
            page.wait_for_timeout(400)
            snap(f"93-resize-{target[0]}")
            page.close()
        browser.close()

    (out / "probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["probe_json"] = str(out / "probe.json")
    return report


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    rep = run(tag)
    print("probe_json:", rep["probe_json"])
    print("states:", len(rep["states"]), "pageerrors:", len(rep["errors"]),
          "deadlock:", len(rep["deadlock"]))
    for st in rep["states"]:
        def fmt(r):
            return "-" if not r else f"{r['x']},{r['y']} {r['w']}x{r['h']}"
        print(
            f"[{st['label']:>7}] {st['step']:<13} side={st['dataSide'] or '-':<6} "
            f"grid={st['grid']:<32} sbDisp={st['sidebarDisplay']:<6} sbT={st['sidebarTransform'][:14]:<14} "
            f"drawer={st['drawerDisplay']:<5} hit={str(st['drawerHit'])[:18]:<18} ok={st['drawerClickable']} "
            f"ovf={st['overflowIntoCenter']}"
        )
        print(f"           sb={fmt(st['sidebarRect'])} center={fmt(st['centerRect'])} "
              f"ctx[{st['ctxDisplay']}]={fmt(st['ctxRect'])} ctxTask={fmt(st['ctxTaskRect'])} "
              f"toggle='{st['toggleText']}'")
    if rep["errors"]:
        print("PAGE ERRORS:", json.dumps(rep["errors"], ensure_ascii=False))
    if rep["deadlock"]:
        print("DEADLOCK:")
        for d in rep["deadlock"]:
            print("  ", json.dumps(d, ensure_ascii=False))
