# -*- coding: utf-8 -*-
"""字典页「画布原地切换 + 点两下回归」真机取证。

用法：``.venv/Scripts/python.exe tools/dict_inplace_probe.py <tag>``

环境口径同阶段四探针：free_port() 动态端口、令牌 secrets 随机、``JZO_DATA_DIR`` 与
``JZO_PLUGINS_DIR`` 指向 ``.system_generated/dict-inplace-probe/<tag>/``，
绝不碰开发者本机 ``data/``、仓库 ``plugins/`` 与端口 8000 的旧进程。

判据（老师三条诉求逐条落地）：
  1. 右栏是极简 Chips：``.db-chip`` 铺满 16 张表，旧的分类卡 ``.db-dict-cat*`` 一个不剩；
  2. 点【学科】→ 画布原地长出字典层、看板插件帧让位隐藏，**顶部页签数一枚不增**；
  3. 再点【学科】→ 字典层收起、看板帧回位（点两下回归）；
  4. 点【年级】/【题型】→ 原地换表；同分类换表走 DcEmbedded.go，**文档不重载**（帧内标记存活）；
  5. 跨分类点【行政区划】→ 照样原地显示；
  6. 全过程右栏 iframe 不重绘：帧内标记与 chips 节点身份始终存活，只有 aria-pressed 变；
  7. 宿主页零未捕获 JS 错误。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402

import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "org.jiuzhang.dashboard"
ENGINE_ID = "org.jiuzhang.bank-engine"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 60
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("服务提前退出：" + (process.stdout.read() if process.stdout else "")[:2000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 60 秒内就绪")


def frame_of(page, needle: str, owner_class: str = ""):
    """看板插件在画布与右栏各有一帧、URL 一模一样，只能靠承载它的 iframe 类名分辨。"""
    for frame in page.frames:
        if needle not in (frame.url or ""):
            continue
        if not owner_class:
            return frame
        element = frame.frame_element()
        if element is not None and owner_class in (element.get_attribute("class") or ""):
            return frame
    return None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "dict-inplace-probe" / tag
    if work.exists():
        shutil.rmtree(work)
    (work / "shots").mkdir(parents=True)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    data_dir.mkdir(parents=True)
    for plugin_id in (PLUGIN_ID, ENGINE_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_LOCAL_TOKEN"] = secrets.token_hex(16)
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env.pop("JZO_AI_API_KEY", None)
    env.pop("JZO_AI_BASE_URL", None)
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    result: dict = {"tag": tag, "base_url": base, "checks": [], "notes": {},
                    "console_errors": [], "page_errors": [],
                    "viewport": {"width": 1440, "height": 900}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    def snap(name: str) -> None:
        page.screenshot(path=str(work / "shots" / (name + ".png")))

    try:
        wait_health(base, process)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type == "error" else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.goto(base + "/workspace", wait_until="domcontentloaded")
            expect(page.locator("#wsPluginList .ws-plugin-item").first).to_be_visible(timeout=60000)

            page.locator("#wsPluginList .ws-plugin-item", has_text="数据看板").click()
            panel = page.locator(f'.ws-tab-panel[data-tab="plugin:{PLUGIN_ID}"]')
            expect(panel).to_be_visible(timeout=30000)
            rail = page.locator("#wsContextSlotBody .ws-context-frame")
            expect(rail).to_be_attached(timeout=30000)
            rail_frame = frame_of(page, "/plugin-assets/" + PLUGIN_ID + "/", "ws-context-frame")
            check("定位到右栏看板沙箱帧", rail_frame is not None,
                  [f.url for f in page.frames][:6])
            if rail_frame is None:
                raise RuntimeError("右栏帧没起来，后续判据无从取证")
            expect(rail_frame.locator(".db-chip").first).to_be_visible(timeout=30000)

            chips = rail_frame.evaluate("""() => ({
              count: document.querySelectorAll('.db-chip').length,
              groups: document.querySelectorAll('.db-chip-group').length,
              legacy: document.querySelectorAll('[class*="db-dict-cat"], .db-dict-head, .db-dict-hint').length,
              labels: Array.from(document.querySelectorAll('.db-chip')).map(b => b.textContent.trim())
            })""")
            result["notes"]["chips"] = chips
            check("右栏铺出 16 张表的极简 Chips（3 组）",
                  chips["count"] == 16 and chips["groups"] == 3, chips["count"])
            check("旧的分类卡/描述文字一个不剩", chips["legacy"] == 0, chips["legacy"])
            snap("01-rail-chips")

            # 右栏不重绘的基线：帧内标记 + chips 节点身份 + 画布页签清单
            rail_frame.evaluate("""() => {
              window.__probeMark = 'rail-alive';
              document.querySelectorAll('.db-chip').forEach((b, i) => { b.dataset.probeIdx = String(i); });
            }""")
            tabs_before = page.evaluate(
                """() => Array.from(document.querySelectorAll('#wsTabs .ws-tab')).map(t => t.dataset.tab)""")
            result["notes"]["tabs_before"] = tabs_before

            def rail_intact() -> dict:
                return rail_frame.evaluate("""() => ({
                  mark: window.__probeMark || '',
                  indexed: document.querySelectorAll('.db-chip[data-probe-idx]').length,
                  pressed: Array.from(document.querySelectorAll('.db-chip[aria-pressed="true"]'))
                    .map(b => b.textContent.trim())
                })""")

            def canvas_state() -> dict:
                return page.evaluate("""() => {
                  const panel = document.querySelector('.ws-tab-panel[data-tab="plugin:%ID%"]');
                  const layer = panel.querySelector('.ws-dict-inplace');
                  const plug = panel.querySelector('.ws-plugin-frame');
                  const frame = layer ? layer.querySelector('.ws-dict-inplace-frame') : null;
                  return {
                    tabs: Array.from(document.querySelectorAll('#wsTabs .ws-tab')).map(t => t.dataset.tab),
                    layerExists: !!layer,
                    layerVisible: !!layer && !layer.hidden && layer.getBoundingClientRect().height > 40,
                    pluginHidden: !!plug && plug.hidden,
                    src: frame ? (frame.getAttribute('src') || '') : ''
                  };
                }""".replace("%ID%", PLUGIN_ID))

            def chip(name: str):
                return rail_frame.locator(".db-chip", has_text=name).first

            def dict_frame():
                return frame_of(page, "/dict?embedded=1")

            def active_sub() -> str:
                """分类面板切换后旧面板仍常驻 DOM，只认可见那一枚子页签。"""
                frame = dict_frame()
                if frame is None:
                    return ""
                return frame.evaluate(
                    """() => {
                      const on = Array.from(document.querySelectorAll('.dc-subtab[aria-selected="true"]'))
                        .filter(b => b.offsetParent !== null);
                      return on.length ? on[0].id : '';
                    }""")

            # ---- 点【学科】：原地长出字典层 ----
            chip("学科").click()
            expect(page.locator(".ws-dict-inplace")).to_be_visible(timeout=30000)
            expect(page.locator(".ws-dict-inplace-frame")).to_be_attached(timeout=30000)
            page.wait_for_timeout(1200)
            state = canvas_state()
            result["notes"]["after_subject"] = state
            check("点【学科】画布原地长出字典层，看板插件帧让位隐藏",
                  state["layerVisible"] and state["pluginHidden"], state)
            check("顶部页签一枚不增（不新开字典页签）", state["tabs"] == tabs_before,
                  {"before": tabs_before, "after": state["tabs"]})
            check("字典层加载的是内嵌学科表", "cat=foundation" in state["src"]
                  and "sub=dict_subjects" in state["src"], state["src"])
            check("右栏未重绘且【学科】按下", rail_intact() == {
                "mark": "rail-alive", "indexed": 16, "pressed": ["学科"]}, rail_intact())
            snap("02-subject-inplace")

            # ---- 点两下回归 ----
            chip("学科").click()
            page.wait_for_timeout(800)
            back = canvas_state()
            result["notes"]["after_second_click"] = back
            check("再点【学科】字典层收起、数据看板回位",
                  back["layerExists"] and not back["layerVisible"] and not back["pluginHidden"], back)
            check("回归后页签仍是一枚不增", back["tabs"] == tabs_before, back["tabs"])
            check("回归后右栏仍未重绘且按键弹起", rail_intact() == {
                "mark": "rail-alive", "indexed": 16, "pressed": []}, rail_intact())
            snap("03-back-to-dashboard")

            # ---- 点【年级】：原地换表 ----
            chip("年级").click()
            page.wait_for_timeout(1200)
            grade = canvas_state()
            result["notes"]["after_grade"] = grade
            check("点【年级】原地切到年级表", grade["layerVisible"] and grade["pluginHidden"]
                  and active_sub().endswith("-dict_grades"), {"state": grade, "sub": active_sub()})
            check("切表后页签仍是一枚不增", grade["tabs"] == tabs_before, grade["tabs"])
            snap("04-grade-inplace")

            # ---- 同分类换表：文档不重载 ----
            dict_frame().evaluate("""() => { window.__docMark = 'same-document'; }""")
            chip("题型").click()
            page.wait_for_timeout(1200)
            same_doc = dict_frame().evaluate("""() => ({
              mark: window.__docMark || '',
              sub: (Array.from(document.querySelectorAll('.dc-subtab[aria-selected="true"]'))
                .filter(b => b.offsetParent !== null)[0] || {}).id || ''
            })""")
            result["notes"]["same_category_switch"] = same_doc
            check("同分类换表走 DcEmbedded.go，文档不重载（帧内标记存活）",
                  same_doc["mark"] == "same-document" and same_doc["sub"].endswith("-dict_question_types"),
                  same_doc)
            check("换表后右栏仍未重绘且【题型】按下", rail_intact() == {
                "mark": "rail-alive", "indexed": 16, "pressed": ["题型"]}, rail_intact())
            snap("05-qtype-same-document")

            # ---- 跨分类：实体维度 ----
            chip("行政区划").click()
            page.wait_for_timeout(1500)
            entity = canvas_state()
            result["notes"]["after_entity"] = entity
            check("跨分类点【行政区划】照样原地显示",
                  entity["layerVisible"] and entity["pluginHidden"]
                  and active_sub().endswith("-regions-schools"),
                  {"state": entity, "sub": active_sub()})
            check("跨分类也走内嵌路由，文档同样不重载",
                  dict_frame().evaluate("""() => window.__docMark || ''""") == "same-document",
                  active_sub())
            check("跨分类后页签仍是一枚不增", entity["tabs"] == tabs_before, entity["tabs"])
            check("跨分类后右栏仍未重绘", rail_intact()["mark"] == "rail-alive"
                  and rail_intact()["indexed"] == 16, rail_intact())
            snap("06-entity-inplace")

            # ---- 跨分类再点两下回归 ----
            chip("行政区划").click()
            page.wait_for_timeout(800)
            final = canvas_state()
            check("跨分类也支持点两下回归看板",
                  not final["layerVisible"] and not final["pluginHidden"]
                  and final["tabs"] == tabs_before, final)
            snap("07-final-dashboard")

            check("宿主页零未捕获 JS 错误", not result["page_errors"], result["page_errors"][:5])
            check("宿主页零控制台报错", not result["console_errors"], result["console_errors"][:5])
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = all(item["ok"] for item in result["checks"])
    (work / "probe.toml").write_text(toml_io.dumps(result), encoding="utf-8")
    passed = sum(1 for item in result["checks"] if item["ok"])
    print(("PASS" if result["ok"] else "FAIL") + f" · {passed}/{len(result['checks'])} 项 · {work}")
    for item in result["checks"]:
        print(("  ok " if item["ok"] else "  XX ") + item["name"]
              + ("" if item["ok"] else " :: " + str(item["detail"])[:200]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())