# -*- coding: utf-8 -*-
"""军令 #16 模块三真机取证：画布页签的沉浸全屏、溢出横滚、分组合并与休眠分层。

用法：``.venv/Scripts/python.exe tools/tab_group_probe.py <out_dir_tag>``
产出：截图 png + probe.json（结构化判据与 pageerror）

判据逐条对应军令原文：
  - 「双击任意 Tab 进入全屏（干碎浏览器地址栏），左侧导航栏自动折叠，右侧和底部保留」，
    「再次双击或按 Esc 退出」，「全屏时按 Ctrl+B 呼叫左侧栏」；
  - 「超过 10 个 Tab 固定宽度 120px、滚轮滑动或左右小箭头」；
  - 「属于文件夹的插件在顶部合并为分组名 Tab（单击下拉展开子 Tab）」，
    「未分组插件统一放进【未分组】集合 Tab」；
  - 「轻量插件后台暂停定时器（浅休眠），重型插件超过 3 个强制 LRU 深休眠」。

跑之前底座必须在 8765 端口起来。探针会临时安装并随后卸载取证夹具插件
（``examples/stage_weight_probe_plugin``），并临时改写 ``data/plugin_state.json``——
两者都在收尾还原，判据 22 专门复核还原结果。
探针中途炸裂时不写「全绿」假象：炸点本身记成一条失败判据，已跑到的判据照常落盘。
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8765/static/workspace.html"
ORIGIN = "http://127.0.0.1:8765"
TOKEN = "dev-token-2026"
FIXTURE_ID = "org.example.stage-weight"
FIXTURE_ZIP = ROOT / "examples" / "stage_weight_probe_plugin.zip"
STATE_FILE = ROOT / "data" / "plugin_state.json"
NOISE = ("ERR_FAILED", "Failed to load resource")

JS_BAR = """
() => {
  const page = document.querySelector('.ws-page');
  const bar = document.getElementById('wsTabs');
  const top = bar ? Array.from(bar.querySelectorAll(':scope > .ws-tab, :scope > .ws-tab-group')) : [];
  const groups = bar ? Array.from(bar.querySelectorAll(':scope > .ws-tab-group')) : [];
  const first = top.filter(n => n.classList.contains('ws-tab'))[0];
  const left = document.querySelector('.ws-tab-scroll-btn');
  const right = Array.from(document.querySelectorAll('.ws-tab-scroll-btn')).pop();
  const side = document.querySelector('.ws-sidebar');
  return {
    many: page ? page.classList.contains('ws-tabs-many') : null,
    immersive: page ? page.getAttribute('data-immersive') : null,
    side: page ? page.getAttribute('data-side') : null,
    fullscreen: Boolean(document.fullscreenElement),
    topCount: top.length,
    groupCount: groups.length,
    firstWidth: first ? Math.round(first.getBoundingClientRect().width) : null,
    scrollLeft: bar ? Math.round(bar.scrollLeft) : null,
    arrows: left && right ? [left.hidden === false, right.hidden === false] : null,
    sidebarWidth: side ? Math.round(side.getBoundingClientRect().width) : null,
    sidebarPos: side ? getComputedStyle(side).position : null,
  };
}
"""

JS_REGIONS = """
() => {
  const vis = (sel) => {
    const n = document.querySelector(sel);
    if (!n) return false;
    const r = n.getBoundingClientRect();
    return r.width > 40 && r.height > 40;
  };
  return {
    context: vis('.ws-context'),
    dock: vis('.ws-dock'),
  };
}
"""

JS_TABS = "() => window.JzoStage.tabs()"


def is_noise(text):
    return any(n in text for n in NOISE)


def api_get(path):
    with urllib.request.urlopen(ORIGIN + path, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_send(path, body, method="POST"):
    req = urllib.request.Request(
        ORIGIN + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-JZO-Token": TOKEN},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_upload(path, blob):
    req = urllib.request.Request(
        ORIGIN + path,
        data=blob,
        headers={"Content-Type": "application/zip", "X-JZO-Token": TOKEN},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_delete(path):
    req = urllib.request.Request(ORIGIN + path, headers={"X-JZO-Token": TOKEN}, method="DELETE")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(tag: str) -> dict:
    out = Path(".system_generated") / "tab_group_probe" / tag
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    errors = []
    state_backup = STATE_FILE.read_bytes() if STATE_FILE.exists() else None
    STATE_FILE.write_text(json.dumps({"disabled": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    def check(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": str(detail)[:500]})

    # 夹具插件：light 权重 + singleton=false，能把宿主的休眠通知原话带回底栏
    try:
        subprocess.run([sys.executable, str(ROOT / "examples" / "build_stage_weight_probe_plugin.py")],
                       check=True, capture_output=True)
        install = api_upload("/api/plugins/install?replace=true", FIXTURE_ZIP.read_bytes())
        installed = install.get("installed") is True
        detail = install.get("plugin", {}).get("id")
    except Exception as exc:  # noqa: BLE001 - 夹具装不上就是一条红判据，别抛出去
        installed, detail = False, repr(exc)
    check("00 取证夹具插件安装成功", installed, detail)

    def drive(pw):
        browser = pw.chromium.launch()
        # 沉浸全屏要有真实视口；headless Chromium 同样支持 Fullscreen API
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE)
        page.wait_for_timeout(2600)

        def snap(name):
            page.screenshot(path=str(out / ("%s.png" % name)))

        def bar():
            return page.evaluate(JS_BAR)

        def open_plugin(plugin_id, index=None):
            """直接走宿主开页签口（左栏没有该插件行时的稳妥路径）。"""
            script = "() => {" \
                "return fetch('/api/plugins').then(r => r.json()).then(data => {" \
                "const p = data.plugins.filter(x => x.id === '%s')[0];" \
                "if (!p) return null;" \
                "const t = window.JzoStage.openPlugin(p);" \
                "return t ? t.key : null;});}" % plugin_id
            key = page.evaluate(script)
            page.wait_for_timeout(1800 if index is None else 1200)
            return key

        # --- 1. 平铺基线：没挤爆就一插件一页，不许出现分组页签 --------------------
        ids = [p["id"] for p in api_get("/api/plugins")["plugins"] if p.get("enabled") is not False]
        heavy_ids = [i for i in ids if i != FIXTURE_ID]
        for i in range(3):
            open_plugin(heavy_ids[i])
        state = bar()
        check("01 未挤爆时页签逐个平铺（无分组页签）",
              state["groupCount"] == 0 and state["topCount"] >= 4
              and state["many"] is False, state)
        snap("01-flat")

        # --- 2. 双击页签 → 沉浸全屏 ----------------------------------------------
        first_key = page.evaluate("() => window.JzoStage.tabs()[1].key")
        sel = '#wsTabs > .ws-tab[data-tab="%s"]' % first_key
        page.locator(sel).dblclick()
        page.wait_for_timeout(900)
        state = bar()
        regions = page.evaluate(JS_REGIONS)
        check("02 双击页签进入真全屏（document.fullscreenElement 在场）",
              state["fullscreen"] is True, state["fullscreen"])
        check("03 沉浸中底座状态位 data-immersive=on", state["immersive"] == "on", state["immersive"])
        check("04 沉浸中左侧导航栏收起（宽度 0）", state["sidebarWidth"] == 0, state["sidebarWidth"])
        check("05 沉浸中右栏与输出日志仍在场",
              regions["context"] and regions["dock"], regions)
        snap("02-immersive")

        # --- 3. 全屏中 Ctrl+B 唤出左栏（覆盖层） -----------------------------------
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.keyboard.press("Control+b")
        page.wait_for_timeout(700)
        state = bar()
        check("06 全屏中 Ctrl+B 把左栏以覆盖层唤出（position:fixed、非零宽、仍在全屏）",
              state["side"] == "open" and state["sidebarPos"] == "fixed"
              and state["sidebarWidth"] >= 200 and state["fullscreen"] is True, state)
        snap("03-immersive-rail")
        page.keyboard.press("Control+b")
        page.wait_for_timeout(700)
        state = bar()
        check("06b 再按一次 Ctrl+B 把浮层收回（左栏让位、全屏不退）",
              state["sidebarWidth"] == 0 and state["fullscreen"] is True, state)

        # --- 4. 再次双击退出 / Esc 退出 -------------------------------------------
        page.locator(sel).dblclick()
        page.wait_for_timeout(900)
        state = bar()
        check("07 再次双击同页签退出沉浸（属性与全屏一起退）",
              state["immersive"] is None and state["fullscreen"] is False, state)
        page.locator(sel).dblclick()
        page.wait_for_timeout(800)
        entered = bar()
        page.keyboard.press("Escape")
        page.wait_for_timeout(900)
        state = bar()
        check("08 Esc 也退出沉浸（不留半吊子状态）",
              entered["immersive"] == "on" and state["immersive"] is None
              and state["fullscreen"] is False, (entered, state))

        # --- 5. 浅休眠：light 插件切后台收定时器，切回补唤醒 ------------------------
        light_first = open_plugin(FIXTURE_ID)
        page.wait_for_timeout(1200)
        light_second = open_plugin(FIXTURE_ID, index=1)
        page.wait_for_timeout(1400)
        dock_texts = page.evaluate(
            "() => Array.from(document.querySelectorAll('#wsDockLog .ws-dock-item'))"
            ".map(x => x.textContent || '')"
        )
        tabs_state = page.evaluate(JS_TABS)
        suspended = [t for t in tabs_state if t["key"] == light_first and t.get("suspended")]
        echoed = any("plugin.suspend" in t for t in dock_texts)
        check("09 light 页签切后台被标浅休眠，且插件自己承认收到 plugin.suspend",
              bool(suspended) and echoed, (suspended, [t for t in dock_texts if "stage-weight" in t][:2]))
        page.evaluate("() => window.JzoStage.activate('%s')" % light_first)
        page.wait_for_timeout(1200)
        dock_texts = page.evaluate(
            "() => Array.from(document.querySelectorAll('#wsDockLog .ws-dock-item'))"
            ".map(x => x.textContent || '')"
        )
        tabs_state = page.evaluate(JS_TABS)
        resumed = [t for t in tabs_state if t["key"] == light_first and not t.get("suspended")]
        check("10 切回前台补发 plugin.resume（沙箱确实收到）",
              bool(resumed) and any("plugin.resume" in t for t in dock_texts),
              [t for t in dock_texts if "plugin.resume" in t][:1])

        # --- 6. 深休眠名额只数重型 -------------------------------------------------
        for i in range(3, 6):
            open_plugin(heavy_ids[i])
        tabs_state = page.evaluate(JS_TABS)
        heavy_live = [t for t in tabs_state if t["kind"] == "plugin"
                      and t.get("weight") == "heavy" and t["state"] == "live"]
        heavy_sleep = [t for t in tabs_state if t["kind"] == "plugin"
                       and t.get("weight") == "heavy" and t["state"] == "sleep"]
        light_live = [t for t in tabs_state if t.get("weight") == "light" and t["state"] == "live"]
        check("11 重型页签超过 3 个即强制 LRU 深休眠",
              len(heavy_live) <= 3 and len(heavy_sleep) >= 1, (len(heavy_live), len(heavy_sleep)))
        check("12 轻量页签不占深休眠名额（全在场，只浅休眠）",
              len(light_live) >= 2, [t["key"] for t in light_live])
        snap("04-lru")

        # --- 7. 挤爆：超过 10 个插件页签 → 固定 120px + 分组合并 ----------------------
        # 全屏窗口改不了尺寸，先把沉浸退干净再动视口。
        page.evaluate("() => { if (document.fullscreenElement) document.exitFullscreen(); }")
        page.wait_for_timeout(700)
        if bar()["immersive"] == "on":
            page.locator(sel).dblclick()
            page.wait_for_timeout(700)
        page.set_viewport_size({"width": 1120, "height": 800})
        page.wait_for_timeout(400)
        for i in range(6, len(heavy_ids)):
            open_plugin(heavy_ids[i])
        state = bar()
        check("13 超过 10 个页签后固定宽度 120px 并进入横滚态",
              state["many"] is True and state["firstWidth"] == 120, state)

        def read_groups():
            return page.evaluate(
                "() => Array.from(document.querySelectorAll('#wsTabs > .ws-tab-group')).map(g => ({"
                "key: g.getAttribute('data-group'),"
                "label: (g.querySelector('.ws-tab-group-chip .ws-tab-label') || {}).textContent,"
                "count: (g.querySelector('.ws-tab-count') || {}).textContent,"
                "kids: Array.from(g.querySelectorAll('.ws-tab-group-list .ws-tab')).map(t => t.getAttribute('data-tab')),"
                "open: (g.querySelector('.ws-tab-group-list') || {}).hidden === false,"
                "}))"
            )

        groups = read_groups()
        check("17 挤爆后同组页签收成分组名页签，未分组的进【未分组】",
              len(groups) >= 1 and any(g["label"] == "未分组" and int(g["count"]) >= 2 for g in groups),
              [(g["key"], g["label"], g["count"]) for g in groups])
        ungrouped = [g for g in groups if g["label"] == "未分组"][0] if groups else None
        check("18 成员页签不再占顶层，收进各自的下拉里",
              ungrouped and all(k not in
                                page.evaluate("() => Array.from(document.querySelectorAll('#wsTabs > .ws-tab'))"
                                              ".map(t => t.getAttribute('data-tab'))")
                                for k in ungrouped["kids"]), ungrouped)
        snap("05-overflow")

        # --- 8. 文件夹分组：树一改，组名页签跟着换成文件夹名 --------------------------
        tree = api_get("/api/plugins")["sidebar"]
        plugin_keys = [n["id"] for n in tree if n.get("kind") != "folder"]
        # 六箱，每箱至少 2 个已开页签才收成组名页签；剩下的留给【未分组】
        buckets = [plugin_keys[i:i + 2] for i in range(0, len(plugin_keys) - 2, 2)]
        folder_tree = [{"kind": "folder", "id": "folder:probe-%d" % i,
                        "name": "探针组%d" % (i + 1), "children": chunk}
                       for i, chunk in enumerate(buckets)] + \
            [{"kind": "plugin", "id": k} for k in plugin_keys[len(buckets) * 2:]]
        api_send("/api/plugins/sidebar", {"sidebar": folder_tree})
        page.wait_for_timeout(1600)
        labels = page.evaluate(
            "() => Array.from(document.querySelectorAll('#wsTabs > .ws-tab-group .ws-tab-label'))"
            ".map(x => x.textContent)"
        )
        check("21 文件夹那组用文件夹名当分组页签（左栏树是唯一事实来源）",
              "探针组1" in labels, labels)
        snap("06-groups")

        # --- 9. 组名页签也多到一排放不下 → 左右小箭头 + 滚轮横滑 ----------------------
        state = bar()
        check("14 左右小箭头在场", state["arrows"] == [True, True], state)
        before_scroll = state["scrollLeft"]
        page.locator(".ws-tab-scroll-btn >> nth=-1").click()
        page.wait_for_timeout(700)
        after_arrow = bar()["scrollLeft"]
        page.evaluate(
            "() => { const b = document.getElementById('wsTabs');"
            "b.dispatchEvent(new WheelEvent('wheel', {deltaY: 240, bubbles: true, cancelable: true})); }"
        )
        page.wait_for_timeout(400)
        after_wheel = bar()["scrollLeft"]
        check("15 点小箭头真的横滚", after_arrow > before_scroll, (before_scroll, after_arrow))
        check("16 滚轮滑动同样生效", after_wheel > after_arrow, (after_arrow, after_wheel))
        snap("07-scroll")

        # --- 10. 单击组名 → 下拉摊开子页签 → 点子页签切页并收摊 -----------------------
        page.evaluate("() => { document.getElementById('wsTabs').scrollLeft = 0; }")
        page.wait_for_timeout(300)
        groups = read_groups()
        target = [g for g in groups if g["label"] == "探针组1"][0] if groups else None
        check("19a 每个文件夹各自收成一个组名页签（计数对上）",
              target and int(target["count"]) == len(target["kids"]) >= 2,
              [(g["label"], g["count"]) for g in groups])

        chip = page.locator('.ws-tab-group[data-group="%s"] .ws-tab-group-chip' % target["key"])
        chip.click()
        page.wait_for_timeout(500)
        opened = page.evaluate(
            "() => { const g = document.querySelector('.ws-tab-group[data-group=\"%s\"]');"
            "const list = g.querySelector('.ws-tab-group-list');"
            "const r = list.getBoundingClientRect();"
            "return {hidden: list.hidden, expanded: g.querySelector('.ws-tab-group-chip')"
            ".getAttribute('aria-expanded'), kids: list.querySelectorAll('.ws-tab').length,"
            "inView: r.top >= 0 && r.height > 40};}" % target["key"]
        )
        check("19 单击组名摊开子页签（可见、不被页签栏裁掉）",
              opened["hidden"] is False and opened["expanded"] == "true"
              and opened["kids"] >= 2 and opened["inView"], opened)
        snap("08-dropdown")

        # 点下拉里的子页签 → 切页 + 收摊
        kid = target["kids"][-1]
        page.locator('#wsTabs .ws-tab-group-list .ws-tab[data-tab="%s"]' % kid).click()
        page.wait_for_timeout(1200)
        after = page.evaluate(
            "() => { const g = document.querySelector('.ws-tab-group[data-group=\"%s\"]');"
            "return {hidden: g.querySelector('.ws-tab-group-list').hidden,"
            "selected: g.querySelector('.ws-tab-group-chip').classList.contains('is-active'),"
            "aria: document.querySelector('#wsTabs .ws-tab[data-tab=\"%s\"]').getAttribute('aria-selected')};}"
            % (target["key"], kid)
        )
        check("20 点子页签即切页并收摊，组名页签标明当前在这一组",
              after["hidden"] is True and after["aria"] == "true" and after["selected"], after)
        snap("09-after-kid-click")

        browser.close()

    try:
        with sync_playwright() as pw:
            drive(pw)
    except Exception as exc:  # noqa: BLE001 - 炸了也要落盘，不然证据全丢
        check("99 探针中途炸裂（下面这些判据只跑到炸点为止）", False, repr(exc))

    # --- 收尾：卸载夹具、还原本机偏好 ------------------------------------------------
    try:
        api_delete("/api/plugins/%s" % FIXTURE_ID)
        removed = True
    except Exception as exc:  # noqa: BLE001 - 收尾失败只记账，不许盖掉前面的证据
        removed = False
        print("夹具卸载失败：%s" % exc)
    if state_backup is not None:
        STATE_FILE.write_bytes(state_backup)
    try:
        remaining = [p["id"] for p in api_get("/api/plugins")["plugins"]]
        leftover = json.loads(STATE_FILE.read_text(encoding="utf-8") or "{}")
        restored = (FIXTURE_ID not in remaining and not leftover.get("shortcuts")
                    and not leftover.get("nicknames")
                    and not [n for n in leftover.get("sidebar", [])
                             if str(n.get("id", "")).startswith("folder:")])
        detail = (FIXTURE_ID in remaining, json.dumps(leftover, ensure_ascii=False)[:200])
    except Exception as exc:  # noqa: BLE001
        restored, detail = False, repr(exc)
    check("22 夹具已卸载且本机偏好还原", removed and restored, detail)

    report = {
        "tag": tag,
        "passed": sum(1 for c in checks if c["passed"]),
        "total": len(checks),
        "pageerrors": [e for e in errors if not is_noise(e)],
        "raw_pageerrors": len(errors),
        "checks": checks,
    }
    (out / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["probe_json"] = str(out / "probe.json")
    return report


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    rep = run(tag)
    print("probe_json:", rep["probe_json"])
    print("passed: %d/%d  pageerrors: %d" % (rep["passed"], rep["total"], len(rep["pageerrors"])))
    for c in rep["checks"]:
        print("%s %-52s %s" % ("PASS" if c["passed"] else "FAIL", c["name"], c["detail"]))
    if rep["pageerrors"]:
        print("PAGE ERRORS:", json.dumps(rep["pageerrors"], ensure_ascii=False)[:800])
