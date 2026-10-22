# -*- coding: utf-8 -*-
"""四区拖拽调尺寸：真机取证脚本（Playwright + Chromium）。

用法：先在 8777 起服务，再跑 ``python tools/split_probe.py <out_dir_tag>``

    .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8777
    .venv/Scripts/python.exe tools/split_probe.py v060

产出：截图 png + probe.json（结构化度量、mousemove 计数、console 错误）。

判据来自 2026-10-26 军令：
  1. 三条分隔条都能用**真鼠标**拖动，CSS 变量与栅格轨道同步变化（不许只动一本账）；
  2. 拖拽经过插件 iframe 时鼠标**不被吞**：拖拽期 iframe 的 pointer-events 必须是 none，
     宿主 window 必须持续收到 mousemove（这是军令点名的纯原生暗坑）；
  3. 拖完写 localStorage，刷新后原样还原；
  4. 「恢复默认布局」按钮一键回 240 / 300 / 190 并清掉记忆；
  5. 手柄可键盘操作（方向键 8px、Shift 32px、Home 复位）；
  6. 375px 窄屏不横向溢出，分隔条按约定隐藏。
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8777/workspace"
STORAGE_KEY = "jzo.workspace.layout.v1"
DEFAULTS = {"side": 240, "context": 300, "dock": 190}

JS_STATE = """
() => {
  const page = document.querySelector('.ws-page');
  const cs = getComputedStyle(page);
  const rect = el => {
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return {x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height)};
  };
  const num = v => Math.round(parseFloat(v));
  const handles = {};
  document.querySelectorAll('.ws-resizer[data-resize]').forEach(h => {
    handles[h.getAttribute('data-resize')] = {
      rect: rect(h),
      display: getComputedStyle(h).display,
      cursor: getComputedStyle(h).cursor,
      valuenow: h.getAttribute('aria-valuenow'),
      rolenow: h.getAttribute('role')
    };
  });
  const frame = document.querySelector('.ws-plugin-frame');
  return {
    vw: window.innerWidth,
    vh: window.innerHeight,
    vars: {
      side: num(cs.getPropertyValue('--sidebar-width')),
      context: num(cs.getPropertyValue('--context-width')),
      dock: num(cs.getPropertyValue('--dock-height')),
      gutterSide: cs.getPropertyValue('--gutter-side').trim(),
      gutterDock: cs.getPropertyValue('--gutter-dock').trim()
    },
    api: window.JzoSplitPane ? window.JzoSplitPane.sizes() : null,
    grid: cs.gridTemplateColumns,
    rows: cs.gridTemplateRows,
    resizing: page.getAttribute('data-resizing'),
    htmlDragClass: document.documentElement.className,
    rects: {
      sidebar: rect(document.getElementById('wsSidebar')),
      center: rect(document.querySelector('.ws-center')),
      context: rect(document.getElementById('wsContext')),
      dock: rect(document.getElementById('wsDock')),
      tabs: rect(document.getElementById('wsTabs'))
    },
    handles: handles,
    frame: frame ? {rect: rect(frame), pointerEvents: getComputedStyle(frame).pointerEvents} : null,
    frameCount: document.querySelectorAll('.ws-plugin-frame').length,
    storage: window.localStorage.getItem('""" + STORAGE_KEY + """'),
    hOverflow: document.documentElement.scrollWidth - window.innerWidth
  };
}
"""


def run(tag: str) -> dict:
    out = Path(__file__).resolve().parent.parent / ".system_generated" / "split" / tag
    out.mkdir(parents=True, exist_ok=True)
    report = {"tag": tag, "base": BASE, "shots": [], "states": [], "checks": [],
              "console": [], "errors": [], "dragRuns": []}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: report["console"].append({"type": m.type, "text": m.text[:300]}))
        page.on("pageerror", lambda e: report["errors"].append(str(e)[:300]))

        # 干净起点：清掉布局记忆再进页面
        page.goto(BASE, wait_until="networkidle")
        page.evaluate("k => window.localStorage.removeItem(k)", STORAGE_KEY)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(400)

        def snap(step):
            st = page.evaluate(JS_STATE)
            st["step"] = step
            report["states"].append(st)
            png = out / f"{step}.png"
            page.screenshot(path=str(png))
            report["shots"].append(str(png))
            return st

        base = snap("00-initial")
        check("初始即默认 240/300/190",
              base["vars"]["side"] == 240 and base["vars"]["context"] == 300 and base["vars"]["dock"] == 190,
              json.dumps(base["vars"]))
        check("变量与 JzoSplitPane.sizes() 同源", base["api"] == {"side": 240, "context": 300, "dock": 190},
              json.dumps(base["api"]))
        check("栅格五列（左右栏 + 三条 gutter + 画布）", len(base["grid"].split()) == 5, base["grid"])
        check("三条分隔条可见且指针为 resize 光标",
              all(h["display"] != "none" and "resize" in (h["cursor"] or "")
                  for h in base["handles"].values()),
              json.dumps({k: v["cursor"] for k, v in base["handles"].items()}, ensure_ascii=False))
        check("手柄带 separator 语义与当前值",
              all(h["rolenow"] == "separator" and h["valuenow"] for h in base["handles"].values()),
              json.dumps({k: (v["rolenow"], v["valuenow"]) for k, v in base["handles"].items()}))
        check("初始无横向溢出", base["hOverflow"] <= 0, str(base["hOverflow"]))

        # ---------- 打开插件画布页签，让 iframe 真的在场 ----------
        opened = page.evaluate("""
        () => {
          const items = Array.from(document.querySelectorAll('#wsPluginList .ws-plugin-item'));
          const target = items.find(b => /示例题库/.test(b.textContent)) || items[0];
          if (!target) return null;
          target.click();
          return target.textContent.trim().slice(0, 40);
        }
        """)
        page.wait_for_timeout(1800)
        st = snap("01-plugin-tab")
        check("点插件后画布出现沙箱 iframe 页签", st["frameCount"] >= 1 and opened is not None,
              f"clicked={opened} frames={st['frameCount']}")

        # ---------- 逐条分隔条真鼠标拖拽 ----------
        drags = [
            ("side", 60, 0, "side"),
            ("context", -70, 0, "context"),
            ("dock", 0, -80, "dock"),
        ]
        for index, (handle_key, dx, dy, var_key) in enumerate(drags, start=1):
            handle = page.locator(f'.ws-resizer[data-resize="{handle_key}"]')
            box = handle.bounding_box()
            if not box:
                check(f"{handle_key} 手柄可命中", False, "bounding_box 为空")
                continue
            start_x = box["x"] + box["width"] / 2
            start_y = box["y"] + box["height"] / 2

            # 宿主 window 的 mousemove 计数器：iframe 吞鼠标时这个数会停在个位数
            page.evaluate("""
            () => {
              window.__probe = {moves: 0, frames: 0, pointerEventsDuringDrag: [], resizingFlags: []};
              window.addEventListener('mousemove', () => {
                window.__probe.moves += 1;
                const f = document.querySelector('.ws-plugin-frame');
                const pg = document.querySelector('.ws-page');
                if (window.__probe.moves % 4 === 0) {
                  window.__probe.pointerEventsDuringDrag.push(f ? getComputedStyle(f).pointerEvents : 'no-frame');
                  window.__probe.resizingFlags.push(pg.getAttribute('data-resizing'));
                }
              }, true);
            }
            """)
            before = page.evaluate(JS_STATE)
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            steps = 14
            for s in range(1, steps + 1):
                page.mouse.move(start_x + dx * s / steps, start_y + dy * s / steps)
                if s == steps // 2:
                    # 拖到一半时把鼠标明确压到 iframe 身上（军令点名的暗坑）
                    mid = page.evaluate("""
                    () => {
                      const f = document.querySelector('.ws-plugin-frame');
                      if (!f) return null;
                      const b = f.getBoundingClientRect();
                      return {x: b.x + b.width / 2, y: b.y + b.height / 2};
                    }
                    """)
                    if mid:
                        page.mouse.move(mid["x"], mid["y"])
                        page.mouse.move(start_x + dx * s / steps, start_y + dy * s / steps)
            page.mouse.up()
            page.wait_for_timeout(300)
            after = snap(f"1{index}-drag-{handle_key}")
            probe = page.evaluate("() => window.__probe")

            delta_var = after["vars"][var_key] - before["vars"][var_key]
            expected = dx if var_key != "context" else -dx
            if var_key == "dock":
                expected = -dy
            run = {
                "handle": handle_key,
                "varBefore": before["vars"][var_key],
                "varAfter": after["vars"][var_key],
                "delta": delta_var,
                "expectedSign": (expected > 0) - (expected < 0),
                "moves": probe["moves"],
                "pointerEventsSeen": sorted(set(probe["pointerEventsDuringDrag"])),
                "resizingFlagsSeen": sorted(set(str(f) for f in probe["resizingFlags"])),
                "gridBefore": before["grid"],
                "gridAfter": after["grid"],
                "rectBefore": before["rects"][var_key if var_key != "side" else "sidebar"],
                "rectAfter": after["rects"][var_key if var_key != "side" else "sidebar"],
                "storageAfter": after["storage"],
            }
            report["dragRuns"].append(run)

            same_sign = (delta_var > 0) == (expected > 0) and delta_var != 0
            check(f"拖 {handle_key}：变量随鼠标方向变化", same_sign,
                  f"{run['varBefore']} → {run['varAfter']}（期望方向 {expected}）")
            # 横向拖拽动列轨道，纵向拖拽动行轨道——各查各的账
            if var_key == "dock":
                track_changed = before["rows"] != after["rows"]
                track_detail = f"{before['rows']} → {after['rows']}"
            else:
                track_changed = before["grid"] != after["grid"]
                track_detail = f"{before['grid']} → {after['grid']}"
            check(f"拖 {handle_key}：栅格轨道跟着变量走", track_changed, track_detail)
            rect_key = "sidebar" if var_key == "side" else var_key
            check(f"拖 {handle_key}：区域实际尺寸改变",
                  before["rects"][rect_key] != after["rects"][rect_key],
                  f"{before['rects'][rect_key]} → {after['rects'][rect_key]}")
            check(f"拖 {handle_key}：拖拽结束后 data-resizing 已摘除", after["resizing"] is None,
                  str(after["resizing"]))
            if st["frameCount"] >= 1:
                check(f"拖 {handle_key}：iframe 全程 pointer-events=none（不吃鼠标）",
                      set(probe["pointerEventsDuringDrag"]) == {"none"},
                      json.dumps(sorted(set(probe["pointerEventsDuringDrag"]))))
                check(f"拖 {handle_key}：宿主 window 持续收到 mousemove", probe["moves"] >= steps,
                      f"moves={probe['moves']} steps={steps}")
                check(f"拖 {handle_key}：拖拽期 data-resizing 标志在场",
                      handle_key in run["resizingFlagsSeen"], json.dumps(run["resizingFlagsSeen"]))
            saved = json.loads(after["storage"]) if after["storage"] else {}
            check(f"拖 {handle_key}：尺寸已写 localStorage",
                  saved.get(var_key) == after["vars"][var_key], json.dumps(saved))

        dragged = snap("19-after-drags")
        check("拖拽后三区都不是默认值",
              all(dragged["vars"][k] != DEFAULTS[k] for k in ("side", "context", "dock")),
              json.dumps(dragged["vars"]))

        # ---------- 刷新还原 ----------
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(500)
        restored = snap("20-after-reload")
        check("刷新后尺寸原样还原",
              all(restored["vars"][k] == dragged["vars"][k] for k in ("side", "context", "dock")),
              f"{json.dumps(dragged['vars'])} → {json.dumps(restored['vars'])}")
        check("还原不刷底栏（by=restore 静默）",
              page.evaluate("() => document.querySelectorAll('#wsDockLog li').length") <= 2,
              str(page.evaluate("() => document.querySelectorAll('#wsDockLog li').length")))

        # ---------- 一键恢复默认 ----------
        page.locator("#wsResetLayout").click(timeout=2500)
        page.wait_for_timeout(400)
        reset = snap("21-after-reset")
        check("复位按钮回默认 240/300/190",
              all(reset["vars"][k] == DEFAULTS[k] for k in ("side", "context", "dock")),
              json.dumps(reset["vars"]))
        check("复位后 localStorage 记忆被清掉", not reset["storage"], str(reset["storage"]))
        check("复位按钮命中区 ≥44×44",
              reset["handles"] and page.evaluate("""
              () => { const b = document.getElementById('wsResetLayout').getBoundingClientRect();
                      return b.width >= 44 && b.height >= 44; }
              """), "")
        dock_text = page.evaluate("() => document.getElementById('wsDockLog').textContent")
        check("复位在底栏留痕", "恢复默认布局" in dock_text, dock_text.strip()[:80])

        # ---------- 键盘可达 ----------
        page.locator('.ws-resizer[data-resize="side"]').focus()
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(150)
        keyed = page.evaluate("() => window.JzoSplitPane.sizes().side")
        check("手柄方向键步进 8px", keyed == 256, str(keyed))
        page.keyboard.down("Shift")
        page.keyboard.press("ArrowRight")
        page.keyboard.up("Shift")
        page.wait_for_timeout(150)
        fast = page.evaluate("() => window.JzoSplitPane.sizes().side")
        check("Shift 加速步进 32px", fast == 288, str(fast))
        page.keyboard.press("Home")
        page.wait_for_timeout(150)
        home = page.evaluate("() => window.JzoSplitPane.sizes().side")
        check("Home 回该区默认", home == 240, str(home))
        snap("22-after-keyboard")

        # ---------- 越界夹紧 ----------
        page.evaluate("() => window.JzoSplitPane.set('side', 9999)")
        clamped = page.evaluate("() => window.JzoSplitPane.sizes().side")
        check("超上限被夹紧到 480", clamped == 480, str(clamped))
        page.evaluate("() => window.JzoSplitPane.set('side', 1)")
        clamped_low = page.evaluate("() => window.JzoSplitPane.sizes().side")
        check("低于下限被夹紧到 180", clamped_low == 180, str(clamped_low))
        page.locator("#wsResetLayout").click()
        page.wait_for_timeout(200)

        # ---------- 脏数据不炸 ----------
        page.evaluate("k => window.localStorage.setItem(k, '{{{坏数据')", STORAGE_KEY)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(400)
        corrupt = snap("23-corrupt-storage")
        check("localStorage 脏数据回落默认且不白屏",
              all(corrupt["vars"][k] == DEFAULTS[k] for k in ("side", "context", "dock")),
              json.dumps(corrupt["vars"]))

        # ---------- 窄屏 ----------
        page.set_viewport_size({"width": 375, "height": 780})
        page.wait_for_timeout(500)
        narrow = snap("24-narrow-375")
        check("375px 无横向溢出", narrow["hOverflow"] <= 0, str(narrow["hOverflow"]))
        check("375px 分隔条按约定隐藏",
              all(h["display"] == "none" for h in narrow["handles"].values()),
              json.dumps({k: v["display"] for k, v in narrow["handles"].items()}))

        page.close()
        browser.close()

    total = len(report["checks"])
    passed = sum(1 for c in report["checks"] if c["ok"])
    report["summary"] = {"total": total, "passed": passed, "failed": total - passed,
                         "pageErrors": len(report["errors"])}
    (out / "probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["probe_json"] = str(out / "probe.json")
    report["out_dir"] = str(out)
    return report


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    rep = run(tag)
    print("out_dir:", rep["out_dir"])
    print("summary:", json.dumps(rep["summary"], ensure_ascii=False))
    for c in rep["checks"]:
        print(("  PASS  " if c["ok"] else "  FAIL  ") + c["name"] + ("  | " + c["detail"] if c["detail"] else ""))
    for r in rep["dragRuns"]:
        print(f"  drag {r['handle']:<8} {r['varBefore']}→{r['varAfter']} moves={r['moves']} "
              f"pointerEvents={r['pointerEventsSeen']} flags={r['resizingFlagsSeen']}")
    if rep["errors"]:
        print("PAGE ERRORS:", json.dumps(rep["errors"], ensure_ascii=False))
    bad_console = [c for c in rep["console"] if c["type"] == "error"]
    if bad_console:
        print("CONSOLE ERRORS:", json.dumps(bad_console, ensure_ascii=False))
