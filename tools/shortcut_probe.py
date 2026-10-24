# -*- coding: utf-8 -*-
"""军令 #16 模块一真机取证：全局快捷键、右键分工与输入铁律。

用法：``python tools/shortcut_probe.py <out_dir_tag>``
产出：截图 png + probe.json（结构化判据与 console/pageerror）

判据逐条对应军令原文：
  - 「Enter 换行，Ctrl+Enter 发送」——助手输入框裸 Enter 不发送、Ctrl+Enter 走同一出口；
  - 左栏右键＝新建文件夹/停用插件/重命名；底栏右键**只有复制、绝不出现清空**；
    中间画布右键宿主一个监听都不挂；
  - 底座与插件撞车时底座最高权限优先，插件那条键进【报错诊断】红字且双击可复制。

跑之前底座必须在 8765 端口起来（``.venv/Scripts/python.exe -m uvicorn app.main:app --port 8765``）。
"""
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/static/workspace.html"
ORIGIN = "http://127.0.0.1:8765"
TOKEN = "dev-token-2026"

# 判据里刻意用 page.route 掐掉 /api/agent/chat（不许真呼模型），
# 浏览器会为此记一条 ERR_FAILED 资源错误——那是探针自己造的，不算底座故障。
NOISE = ("ERR_FAILED", "Failed to load resource")


def is_noise(text):
    return any(n in text for n in NOISE)


def api_post(path, body):
    req = urllib.request.Request(
        ORIGIN + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-JZO-Token": TOKEN},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_get(path):
    with urllib.request.urlopen(ORIGIN + path, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


JS_ENV = """
() => {
  const page = document.querySelector('.ws-page');
  const menu = document.querySelector('.ws-menu');
  const items = menu ? Array.from(menu.querySelectorAll('.ws-menu-item')).map(b => ({
    label: b.textContent.trim(),
    h: Math.round(b.getBoundingClientRect().height),
  })) : [];
  return {
    side: page ? page.getAttribute('data-side') : null,
    menuOpen: !!menu,
    menuItems: items,
    menuText: menu ? menu.textContent : '',
    consoleVisible: (() => {
      const c = document.getElementById('wsPanelConsole');
      return c ? !c.hidden : false;
    })(),
    rows: Array.from(document.querySelectorAll('#wsPluginList .ws-plugin-row'))
      .map(r => r.getAttribute('data-key')),
    folderRows: Array.from(document.querySelectorAll('#wsPluginList .ws-plugin-folder'))
      .map(r => r.textContent.trim().slice(0, 30)),
    focusIn: document.activeElement
      ? (document.activeElement.id || document.activeElement.className || document.activeElement.tagName)
      : null,
  };
}
"""


def run(tag: str) -> dict:
    out = Path(".system_generated") / "shortcut_probe" / tag
    out.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": str(detail)[:400]})
        return bool(passed)

    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text)
                if m.type == "error" and not is_noise(m.text) else None)
        page.goto(BASE)
        page.wait_for_timeout(2500)

        def env():
            return page.evaluate(JS_ENV)

        def snap(name):
            page.screenshot(path=str(out / ("%s.png" % name)), full_page=False)

        # --- 1. 键位表装配：五个底座动作全部就位 -----------------------------
        bindings = page.evaluate("() => window.JzoKeys.bindings()")
        check(
            "01 底座五个动作默认键位装配",
            bindings.get("sidebar.toggle") == "Ctrl+B"
            and bindings.get("console.open") == "Ctrl+Shift+S"
            and len(bindings) == 5,
            bindings,
        )
        snap("01-loaded")

        # --- 2. Ctrl+B 折叠/展开左栏 -----------------------------------------
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        before = env()["side"]
        page.keyboard.press("Control+b")
        page.wait_for_timeout(350)
        hidden = env()["side"]
        page.keyboard.press("Control+b")
        page.wait_for_timeout(350)
        back = env()["side"]
        check("02 Ctrl+B 折叠再展开左栏", hidden == "hidden" and back == before,
              "%s -> %s -> %s" % (before, hidden, back))

        # --- 3. 左栏插件行右键：三项必备 --------------------------------------
        page.locator("#wsPluginList .ws-plugin-row").first.click(button="right")
        page.wait_for_timeout(250)
        menu = env()
        labels = [i["label"] for i in menu["menuItems"]]
        check("03 左栏右键含新建文件夹/停用插件/重命名",
              all(k in " ".join(labels) for k in ("新建文件夹", "停用插件", "重命名")), labels)
        check("04 菜单项触控高度 ≥44px",
              all(i["h"] >= 44 for i in menu["menuItems"]),
              [i["h"] for i in menu["menuItems"]])
        snap("03-sidebar-menu")

        # --- 4. 新建文件夹（走弹窗，落后端树） --------------------------------
        page.get_by_role("menuitem", name="新建文件夹").click()
        page.wait_for_timeout(250)
        dialog = page.locator(".ws-dialog")
        check("05 新建文件夹弹窗接管（不再用原生 prompt）", dialog.count() == 1)
        page.locator("input.ws-dialog-field").fill("探针组")
        page.get_by_role("button", name="确定").click()
        page.wait_for_timeout(900)
        tree = api_get("/api/plugins")["sidebar"]
        folders = [n for n in tree if str(n.get("id", "")).startswith("folder:")]
        check("06 文件夹写进后端树并收编成员",
              len(folders) == 1 and len(folders[0].get("children", [])) == 1, folders)
        env4 = env()
        check("07 左栏出现文件夹行", bool(env4["folderRows"]), env4["folderRows"])
        snap("04-folder-created")

        # --- 5. 文件夹行右键：重命名 / 解散 -----------------------------------
        page.locator("#wsPluginList .ws-plugin-folder-head").first.click(button="right")
        page.wait_for_timeout(250)
        labels2 = [i["label"] for i in env()["menuItems"]]
        check("08 文件夹右键含重命名与解散文件夹",
              any("重命名" in l for l in labels2) and any("解散" in l for l in labels2), labels2)
        snap("05-folder-menu")

        # --- 6. 解散文件夹（回到干净树） --------------------------------------
        page.get_by_role("menuitem", name="解散文件夹").click()
        page.wait_for_timeout(900)
        tree2 = api_get("/api/plugins")["sidebar"]
        check("09 解散后树回到扁平且插件一个不少",
              not [n for n in tree2 if str(n.get("id", "")).startswith("folder:")]
              and len(tree2) == len(tree), tree2)

        # --- 7. 底栏右键：只有复制，绝不出现清空 -------------------------------
        page.evaluate("""() => {
          const li = document.createElement('li');
          li.className = 'ws-dock-item';
          li.setAttribute('data-copy', '探针行');
          li.textContent = '00:00:00 探针行';
          document.getElementById('wsDockLog').appendChild(li);
        }""")
        page.locator("#wsDockLog .ws-dock-item").last.click(button="right")
        page.wait_for_timeout(250)
        dock_menu = env()
        dock_labels = [i["label"] for i in dock_menu["menuItems"]]
        check("10 底栏右键只有复制两项",
              len(dock_labels) == 2 and all("复制" in l for l in dock_labels), dock_labels)
        check("11 底栏右键菜单里不出现「清空」", "清空" not in dock_menu["menuText"],
              dock_menu["menuText"])
        snap("06-dock-menu")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # --- 8. 中间画布：宿主一个右键监听都不挂 -------------------------------
        page.locator(".ws-tab-panel:not([hidden]) iframe").first.click(button="right")
        page.wait_for_timeout(300)
        check("12 画布右键不弹宿主菜单", env()["menuOpen"] is False)

        # --- 9. 插件自报键位先归自己所有 --------------------------------------
        owner = page.evaluate("() => window.JzoKeys.ownerOf('Ctrl+Shift+K')")
        check("13 未撞车时 Ctrl+Shift+K 归助手插件",
              owner and owner.get("owner") == "plugin"
              and owner.get("action") == "chat.focus", owner)
        snap("07-plugin-owner")

        # --- 10. 撞车裁决：把底座 console.open 抢过来 --------------------------
        api_post("/api/plugins/shortcuts", {"action": "console.open", "combo": "Ctrl+Shift+K"})
        page.reload()
        page.wait_for_timeout(2600)
        owner2 = page.evaluate("() => window.JzoKeys.ownerOf('Ctrl+Shift+K')")
        check("14 撞车后底座最高权限优先",
              owner2 and owner2.get("owner") == "host"
              and owner2.get("action") == "console.open", owner2)
        page.get_by_role("tab", name="报错诊断").click()
        page.wait_for_timeout(300)
        conflict = page.evaluate("""() => {
          const rows = Array.from(document.querySelectorAll('#wsDockLog .ws-dock-item'))
            .filter(li => li.getAttribute('data-level') === 'error');
          return rows.map(li => ({
            text: li.textContent,
            copy: li.getAttribute('data-copy') || '',
            topic: (li.querySelector('.ws-dock-topic') || {}).textContent || '',
          }));
        }""")
        hit = [c for c in conflict if c["topic"] == "shortcut.conflict"]
        check("15 撞车记进【报错诊断】红字（error 级）",
              len(hit) == 1 and "底座已禁用该键位" in hit[0]["text"], hit)
        check("16 红字挂 data-copy 供双击复制",
              bool(hit) and "快捷键撞车" in hit[0]["copy"]
              and "[shortcut.conflict]" in hit[0]["copy"], hit[:1])
        snap("08-conflict-redline")

        # 双击复制这条红字
        if hit:
            page.locator("#wsDockLog .ws-dock-item").filter(
                has_text="快捷键撞车").first.dblclick()
            page.wait_for_timeout(300)
            copied = page.evaluate("""() => {
              const li = Array.from(document.querySelectorAll('#wsDockLog .ws-dock-item'))
                .find(x => (x.textContent || '').includes('快捷键撞车'));
              return li ? li.getAttribute('data-copied') || li.className : null;
            }""")
            check("17 双击红字有复制反馈", bool(copied), copied)
            snap("09-conflict-copied")

        # 该键现在归底座：按下去开控制台，助手输入框不许抢
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.keyboard.press("Control+Shift+k")
        page.wait_for_timeout(700)
        check("18 撞车后该键由底座执行（控制台页签起来）", env()["consoleVisible"])
        snap("10-conflict-host-wins")

        # 恢复默认键位
        api_post("/api/plugins/shortcuts", {"action": "console.open", "combo": "Ctrl+Shift+S"})
        page.reload()
        page.wait_for_timeout(2400)
        owner3 = page.evaluate("() => window.JzoKeys.ownerOf('Ctrl+Shift+K')")
        check("19 键位还原后插件自动拿回（不留静音表）",
              owner3 and owner3.get("owner") == "plugin", owner3)

        # --- 11. 输入铁律：Enter 换行 / Ctrl+Enter 发送 ------------------------
        sent = {"n": 0}

        def note_route(route):
            sent["n"] += 1
            route.abort()

        page.route("**/api/agent/chat", note_route)
        frame = page.frame_locator("#wsContextSlotBody iframe")
        prompt = frame.locator("#chatPrompt")
        check("20 助手输入框在场", prompt.count() == 1)
        placeholder = prompt.get_attribute("placeholder") or ""
        check("21 输入框文案写明铁律", "Enter 换行" in placeholder
              and "Ctrl+Enter 发送" in placeholder, placeholder)
        bubbles_before = frame.locator(".jzochat-msg").count()
        prompt.click()
        prompt.type("第一行")
        page.keyboard.press("Enter")
        page.keyboard.type("第二行")
        page.wait_for_timeout(400)
        value = prompt.input_value()
        check("22 裸 Enter 只换行、没发送",
              "\n" in value and sent["n"] == 0 and bubbles_before == frame.locator(".jzochat-msg").count(),
              {"value": value, "sent": sent["n"]})
        snap("11-enter-newline")
        page.keyboard.press("Control+Enter")
        page.wait_for_timeout(900)
        check("23 Ctrl+Enter 才发送（走同一出口）", sent["n"] == 1, sent["n"])
        snap("12-ctrl-enter-send")
        page.unroute("**/api/agent/chat")

        # --- 12. 沙箱双向键路：焦点在宿主 / 焦点在插件，两条腿都要通 ------------
        chat_frame = None
        for f in page.frames:
            if "org.jiuzhang.chat" in (f.url or ""):
                chat_frame = f
        check("24 助手 iframe 在场（opaque-origin 沙箱）", chat_frame is not None,
              [f.url for f in page.frames][:4])
        if chat_frame:
            def active_in_frame():
                return chat_frame.evaluate(
                    "() => document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : ''"
                )

            # 腿一：焦点在宿主 → 宿主派发 shortcut.invoke
            page.locator(".ws-context-head").first.click()
            page.wait_for_timeout(200)
            page.keyboard.press("Control+Shift+k")
            page.wait_for_timeout(500)
            check("25 焦点在宿主时该键送达插件并聚焦输入框", active_in_frame() == "chatPrompt",
                  active_in_frame())

            # 腿二：焦点在插件 → 插件上报 shortcut.press，由宿主裁归属
            chat_frame.locator("#chatThread").click()
            page.wait_for_timeout(200)
            check("26 起点不在输入框（否则测不出转发）", active_in_frame() != "chatPrompt",
                  active_in_frame())
            chat_frame.locator("#chatThread").click()
            page.keyboard.press("Control+Shift+k")
            page.wait_for_timeout(500)
            check("27 焦点在插件时经 shortcut.press 拿回归属并执行",
                  active_in_frame() == "chatPrompt", active_in_frame())
            snap("13-sandbox-key-path")

        bad = page.evaluate("() => JSON.stringify(window.JzoKeys.press('K'))")
        check("28 裸键/未申报键位一律被拒", "BAD_COMBO" in bad or "UNBOUND" in bad, bad)

        browser.close()

    report = {
        "tag": tag,
        "base": BASE,
        "passed": sum(1 for c in checks if c["passed"]),
        "total": len(checks),
        "pageerrors": errors,
        "checks": checks,
    }
    (out / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
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
        print("%s %-46s %s" % ("PASS" if c["passed"] else "FAIL", c["name"], c["detail"]))
    if rep["pageerrors"]:
        print("PAGE ERRORS:", json.dumps(rep["pageerrors"], ensure_ascii=False)[:800])
