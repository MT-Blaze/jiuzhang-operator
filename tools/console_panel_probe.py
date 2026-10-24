# -*- coding: utf-8 -*-
"""军令 #16 模块二真机取证：控制台插件面板的显示、排序、时间与实时对齐。

用法：``python tools/console_panel_probe.py <out_dir_tag>``
产出：截图 png + probe.json（结构化判据与 pageerror）

判据逐条对应军令原文：
  - 卡片大字＝自定义昵称，小字＝官方原名与版本，且**没有**「恢复默认名」那类按钮；
  - 列表平铺不折叠，分组以卡片尾部小标签出现；
  - 「已启用」顺序与左栏导航 100% 对齐，「已停用」按停用时间先后；
  - 相对时间只在点开面板那一瞬算一次（隔 3 秒重读文本必须一字不变）；
  - 键位改绑走控制台那一个写口，改完工作台左栏当场跟上（不刷新浏览器）。

跑之前底座必须在 8765 端口起来。
"""
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/static/workspace.html"
ORIGIN = "http://127.0.0.1:8765"
TOKEN = "dev-token-2026"

JS_CARDS = """
() => Array.from(document.querySelectorAll('#mgList .mg-card')).map(li => ({
  id: li.getAttribute('data-id'),
  state: li.getAttribute('data-state') || 'on',
  big: (li.querySelector('.mg-card-name') || {}).textContent || '',
  small: (li.querySelector('.mg-card-official') || {}).textContent || '',
  sub: (li.querySelector('.mg-card-sub') || {}).textContent || '',
  folder: (li.querySelector('.mg-tag-folder') || {}).textContent || '',
  buttons: Array.from(li.querySelectorAll('button')).map(b => b.textContent.trim()),
}))
"""

JS_RAIL = """
() => Array.from(document.querySelectorAll('#wsPluginList .ws-plugin-row'))
  .map(r => r.getAttribute('data-key'))
"""


def rail_order(tree, plugins):
    """左栏 DOM 的真实行序：文件夹行紧接它的子插件行。

    与 workspace.js 的 pluginVisible 同口径——停用或不占位的插件根本不上栏，全员出局的
    文件夹也不留空壳；判据比的是「上栏的那些行」，不是整棵树。
    """
    def plugin_id(key):
        return str(key or "").split(":", 1)[1]

    visible = {p.get("id") for p in plugins
               if p.get("enabled") is not False and p.get("show_in_sidebar") is not False}
    out = []
    for node in tree:
        key = str(node.get("id", ""))
        if key.startswith("folder:"):
            kids = [k for k in node.get("children", []) if plugin_id(k) in visible]
            if kids:
                out.append(key)
                out.extend(kids)
        elif plugin_id(key) in visible:
            out.append(key)
    return out


def api_get(path):
    with urllib.request.urlopen(ORIGIN + path, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(tag: str) -> dict:
    out = Path(".system_generated") / "console_panel_probe" / tag
    out.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": str(detail)[:500]})

    errors = []
    prompt_answer = {"text": ""}

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept(prompt_answer["text"]))
        page.goto(BASE)
        page.wait_for_timeout(2500)

        def snap(name):
            page.screenshot(path=str(out / ("%s.png" % name)))

        # --- 1. 用底座键位打开控制台页签（顺带证明模块一的键活着） --------------
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.keyboard.press("Control+Shift+s")
        page.wait_for_timeout(1800)
        console_tab = page.evaluate(
            "() => { const c = document.getElementById('wsPanelConsole');"
            " return c ? !c.hidden : false; }"
        )
        check("01 Ctrl+Shift+S 打开控制台页签", console_tab, console_tab)
        frame = page.frame_locator("#wsConsoleFrame")
        # 控制台默认落在「工作区」分区，插件卡片与键位区各自要点开才可见
        frame.locator("#stNavPlugin").click()
        page.wait_for_timeout(600)
        cards = frame.locator("#mgList .mg-card")
        cards.first.wait_for(timeout=8000, state="visible")
        snap("01-console-open")

        # --- 2. 大字昵称 / 小字官方原名 / 无「恢复默认名」 ----------------------
        before = api_get("/api/plugins")
        rail_before = page.evaluate(JS_RAIL)
        first_id = cards.first.get_attribute("data-id")
        check("02 控制台首卡与左栏首行同插件",
              first_id == rail_before[0].replace("plugin:", ""), (first_id, rail_before[:2]))
        rows = frame.locator("#mgList .mg-card")
        big0 = rows.nth(0).locator(".mg-card-name").inner_text()
        small0 = rows.nth(0).locator(".mg-card-official").inner_text()
        check("03 小字写着官方原名与版本", "官方原名：" in small0 and "v" in small0, small0)
        check("04 未起昵称时大字回落官方原名", big0 and big0 in small0, (big0, small0))
        labels = []
        for i in range(rows.count()):
            for b in rows.nth(i).locator("button").all_inner_texts():
                labels.append(b)
        check("05 全表按钮里没有「恢复默认名」那类按钮",
              not any("恢复默认" in b or "默认名" in b for b in labels), sorted(set(labels)))
        check("06 卡片平铺：一卡一插件，无折叠容器",
              rows.count() == len([p for p in before["plugins"]]) and
              frame.locator("#mgList details").count() == 0, rows.count())

        # --- 3. 改昵称：大字跟着换，小字不动 -----------------------------------
        prompt_answer["text"] = "探针别名"
        rows.nth(0).locator(".mg-rename").click()
        page.wait_for_timeout(1500)
        big_after = frame.locator("#mgList .mg-card").nth(0).locator(".mg-card-name").inner_text()
        small_after = frame.locator("#mgList .mg-card").nth(0).locator(".mg-card-official").inner_text()
        check("07 改完昵称大字立即变、小字仍是官方原名",
              big_after == "探针别名" and "官方原名：" in small_after, (big_after, small_after))
        rail_title = page.locator("#wsPluginList .ws-plugin-item-name").first.inner_text()
        check("08 左栏同一行也跟着改名（prefs.changed 实时对齐，不刷新浏览器）",
              rail_title == "探针别名", rail_title)
        snap("02-renamed")

        # --- 4. 分组小标签：在左栏建一个文件夹，控制台卡片尾部要标出来 -----------
        page.locator("#wsPluginList .ws-plugin-row").first.click(button="right")
        page.wait_for_timeout(250)
        page.get_by_role("menuitem", name="新建文件夹").click()
        page.wait_for_timeout(300)
        prompt_answer["text"] = "探针组"
        page.locator(".ws-dialog input.ws-dialog-field").fill("探针组")
        page.get_by_role("button", name="确定").click()
        page.wait_for_timeout(1500)
        tree = api_get("/api/plugins")["sidebar"]
        folders = [n for n in tree if str(n.get("id", "")).startswith("folder:")]
        tag_text = frame.locator("#mgList .mg-card").nth(0).locator(".mg-tag-folder").inner_text()
        check("09 卡片尾部小标签显示所属文件夹",
              len(folders) == 1 and "探针组" in tag_text, (folders, tag_text))
        untagged = [
            frame.locator("#mgList .mg-card").nth(i).locator(".mg-tag-folder").inner_text()
            for i in range(1, min(3, rows.count()))
        ]
        check("10 没分组的明写「未分组」", any("未分组" in t for t in untagged), untagged)
        snap("03-folder-tag")

        # --- 5. 已启用顺序 100% 对齐左栏 ---------------------------------------
        rail_keys = page.evaluate(JS_RAIL)
        flat_rail = []
        for n in tree:
            if n.get("kind") == "folder":
                flat_rail.extend(n.get("children", []))
            else:
                flat_rail.append(n.get("id"))
        card_ids = ["plugin:" + cards.nth(i).get_attribute("data-id")
                    for i in range(rows.count())]
        enabled_cards = [k for k in card_ids if k in flat_rail]
        check("11 控制台「已启用」段与左栏树逐条同序",
              enabled_cards == [k for k in flat_rail if k in card_ids],
              list(zip(enabled_cards, flat_rail))[:4])
        body_now = api_get("/api/plugins")
        expect_rail = rail_order(body_now["sidebar"], body_now["plugins"])
        check("12 控制台读的是同一棵后端树（左栏行序 == 树序）",
              rail_keys == expect_rail, list(zip(rail_keys, expect_rail))[:5])

        # --- 6. 停用 → 落到末尾并显示相对时间；再启用 → 回到原位 -----------------
        victim = rows.nth(1)
        victim_id = victim.get_attribute("data-id")
        victim.locator(".mg-toggle").click()
        page.wait_for_timeout(1800)
        cards2 = frame.locator("#mgList .mg-card")
        order2 = [cards2.nth(i).get_attribute("data-id") for i in range(cards2.count())]
        off_state = cards2.nth(order2.index(victim_id)).get_attribute("data-state")
        sub = cards2.nth(order2.index(victim_id)).locator(".mg-card-sub").inner_text()
        check("13 停用卡沉到「已停用」段", off_state == "disabled"
              and order2.index(victim_id) > order2.index(first_id), (order2[:4], off_state))
        check("14 停用卡写明相对时间", "停用时间：" in sub and "前" in sub or "刚刚" in sub, sub)
        snap("04-disabled")

        # 相对时间不许后台跑：隔 3 秒重读同一张卡的文案必须一字不变
        again = cards2.nth(order2.index(victim_id)).locator(".mg-card-sub").inner_text()
        page.wait_for_timeout(3000)
        later = frame.locator('#mgList .mg-card[data-id="%s"]' % victim_id).locator(".mg-card-sub").inner_text()
        check("15 相对时间只在渲染那一瞬算一次（3 秒后原样不动）", again == later, (again, later))

        # 重新启用（把状态还回去）
        frame.locator('#mgList .mg-card[data-id="%s"] .mg-toggle' % victim_id).click()
        page.wait_for_timeout(1800)

        # --- 7. 键位自定义区：改绑 → 工作台当场生效 -----------------------------
        frame.locator("#stNavSystem").click()
        page.wait_for_timeout(600)
        key_rows = frame.locator("#keyList .key-row")
        check("16 系统设置里五条底座键位", key_rows.count() == 5, key_rows.count())
        first_key = key_rows.nth(2)
        first_key.locator(".key-input").fill("Ctrl+Shift+Q")
        first_key.locator(".key-save").click()
        page.wait_for_timeout(2000)
        saved = api_get("/api/plugins")["shortcuts"]
        bound = page.evaluate("() => window.JzoKeys.bindings()")
        check("17 改绑写进本机偏好且工作台当场接上（无需刷新）",
              "Ctrl+Shift+Q" in json.dumps(saved, ensure_ascii=False)
              and bound.get("dock.toggle") == "Ctrl+Shift+Q", (saved, bound))
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.keyboard.press("Control+Shift+q")
        page.wait_for_timeout(400)
        side = page.evaluate("() => document.querySelector('.ws-page').getAttribute('data-dock')")
        check("18 新键位真的能按动底座动作", side in ("hidden", "open"), side)
        snap("05-keybound")

        # 还原键位与昵称、解散分组
        first_key.locator(".key-reset").click()
        page.wait_for_timeout(1800)
        frame.locator("#stNavPlugin").click()
        page.wait_for_timeout(600)
        prompt_answer["text"] = ""
        frame.locator("#mgList .mg-card").nth(0).locator(".mg-rename").click()
        page.wait_for_timeout(1500)
        page.locator("#wsPluginList .ws-plugin-folder-head").first.click(button="right")
        page.wait_for_timeout(250)
        page.get_by_role("menuitem", name="解散文件夹").click()
        page.wait_for_timeout(1200)
        restored = api_get("/api/plugins")
        check("19 探针自造的偏好全部还原",
              not restored["shortcuts"]
              and not [p for p in restored["plugins"] if p.get("nickname")]
              and not [n for n in restored["sidebar"] if str(n.get("id", "")).startswith("folder:")],
              (restored["shortcuts"], [p.get("nickname") for p in restored["plugins"] if p.get("nickname")]))

        browser.close()

    report = {
        "tag": tag,
        "passed": sum(1 for c in checks if c["passed"]),
        "total": len(checks),
        "pageerrors": errors,
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
        print("PAGE ERRORS:", json.dumps(rep["pageerrors"], ensure_ascii=False)[:600])
