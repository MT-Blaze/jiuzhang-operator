# -*- coding: utf-8 -*-
"""数据字典控制台阶段四封版走查探针：只覆盖阶段一尚缺独立复跑证据的交互。

阶段二/三探针已覆盖五表 CRUD、防呆 409、TOML 导入与四栏联动；
本探针补「多标签新开/激活/关闭」「全局设置 localStorage 记忆」「辅助栏折叠」
三条主路径，避免沿用阶段一旧探针里已过时的断言（基石 6 卡等）。

环境口径同其它探针：free_port() 动态端口、JZO_DATA_DIR 隔离、令牌 secrets 随机，
绝不碰端口 8000 的用户旧进程。证据落 .system_generated/acceptance_stage4/<tag>/。

用法：``.venv/Scripts/python.exe tools/dict_console_probe_stage4.py <tag>``
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
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


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


def selected(page, tab_id: str) -> str | None:
    return page.locator(f"#{tab_id}").get_attribute("aria-selected")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "acceptance_stage4" / tag
    if work.exists():
        shutil.rmtree(work)
    (work / "shots").mkdir(parents=True)
    data_dir = Path(tempfile.mkdtemp(prefix="jzo-stage4-probe-"))
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_LOCAL_TOKEN"] = secrets.token_hex(16)
    env["JZO_DATA_DIR"] = str(data_dir)
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    result: dict = {"tag": tag, "base_url": base, "checks": [],
                    "console_errors": [], "page_errors": [],
                    "viewport": {"width": 1440, "height": 900}, "geometry": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type in {"error", "warning"} else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.goto(base + "/dict", wait_until="domcontentloaded")
            expect(page.locator("#dcTab-dashboard")).to_be_visible(timeout=60000)
            expect(page.locator("#dcGlobalsState")).to_contain_text("当前：", timeout=60000)

            tabs = page.locator("#dcTabs .dc-tab")
            check("默认仅【数据看板】一枚钉住页签",
                  tabs.count() == 1 and selected(page, "dcTab-dashboard") == "true"
                  and page.locator("#dcTab-dashboard .dc-tab-close").count() == 0,
                  {"count": tabs.count()})
            page.screenshot(path=str(work / "shots" / "01_dashboard_default.png"))

            # ---- 多标签：新开 / 激活 / 不重复 ----
            page.locator(".dc-nav-item", has_text="系统基石字典").click()
            expect(page.locator("#dcTab-foundation")).to_be_visible(timeout=10000)
            check("分类新开页签并激活，看板面板 hidden 但 DOM 常驻",
                  selected(page, "dcTab-foundation") == "true" and tabs.count() == 2
                  and page.locator("#dcPanel-dashboard").is_hidden()
                  and page.locator("#dcPanel-dashboard").count() == 1,
                  {"count": tabs.count()})
            page.locator(".dc-nav-item", has_text="系统基石字典").click()
            check("再点同分类不重复开", tabs.count() == 2, {"count": tabs.count()})
            page.locator("#dcTab-dashboard").click()
            page.locator("#dcPanel-dashboard .dc-card", has_text="实体维度字典").locator("button").click()
            expect(page.locator("#dcTab-entity")).to_be_visible(timeout=10000)
            check("看板卡片入口新开实体页签（共 3 枚）",
                  tabs.count() == 3 and selected(page, "dcTab-entity") == "true",
                  {"count": tabs.count()})
            page.screenshot(path=str(work / "shots" / "02_three_tabs.png"))

            # ---- 面板状态常驻 + 键盘切签 ----
            page.evaluate("""() => { document.getElementById('dcPanel-dashboard').dataset.probeMark = 'kept'; }""")
            page.locator("#dcTab-dashboard").click()
            kept = page.evaluate(
                """() => { const p = document.getElementById('dcPanel-dashboard');
                    return { mark: p.dataset.probeMark, stats: !!p.querySelector('.dc-stat-row'),
                             visible: !p.hidden }; }""")
            check("切回看板不重渲（标记与统计行都在）",
                  kept == {"mark": "kept", "stats": True, "visible": True}, kept)
            page.locator("#dcTab-dashboard").press("ArrowRight")
            check("ArrowRight 切到下一枚页签", selected(page, "dcTab-foundation") == "true")
            page.locator("#dcTab-foundation").press("End")
            check("End 跳到末枚页签", selected(page, "dcTab-entity") == "true")
            page.locator("#dcTab-entity").press("Home")
            check("Home 跳回首枚页签", selected(page, "dcTab-dashboard") == "true")

            # ---- 关闭页签：激活邻居 + 焦点归位 ----
            page.locator("#dcTab-entity").click()
            page.locator(".dc-tab", has_text="实体维度字典").locator(".dc-tab-close").click()
            closed = page.evaluate(
                """() => ({ count: document.querySelectorAll('#dcTabs .dc-tab').length,
                            active: (document.querySelector('.dc-tab-main[aria-selected="true"]') || {}).textContent,
                            focused: (document.activeElement || {}).textContent })""")
            check("关闭当前页签激活左邻并把焦点交给它",
                  closed["count"] == 2 and closed["active"] == "系统基石字典"
                  and closed["focused"] == "系统基石字典", closed)

            # ---- 全局设置：真实字典 + localStorage 记忆 + 刷新还原 ----
            options = page.evaluate(
                """() => ({
                    stages: Array.from(document.getElementById('dcStage').options).map((o) => o.textContent),
                    subjects: document.getElementById('dcSubject').options.length,
                    textbooks: document.getElementById('dcTextbook').options.length })""")
            check("全局三下拉为真实字典（4 学段项 / 16 学科 / 129 教材）",
                  options["stages"] == ["全部学段", "小学", "初中", "高中"]
                  and options["subjects"] == 16 and options["textbooks"] == 129, options)
            page.locator("#dcStage").select_option(label="初中")
            page.locator("#dcSubject").select_option(label="数学")
            narrowed = page.evaluate(
                """() => document.getElementById('dcTextbook').options.length""")
            check("选初中+数学后教材清单收窄", 1 < narrowed < 129, {"count": narrowed})
            page.locator("#dcTextbook").select_option(index=1)
            chosen = page.evaluate(
                """() => ({
                    saved: JSON.parse(localStorage.getItem('jzo.dictConsole.globals.v1')),
                    query: window.DcGlobals.query() })""")
            check("选定即写 localStorage 且 query() 携带三参数",
                  chosen["saved"]["stage"] == "初中" and chosen["query"]["stage"] == "初中"
                  and isinstance(chosen["query"]["subject_id"], int)
                  and isinstance(chosen["query"]["textbook_id"], int), chosen)
            page.screenshot(path=str(work / "shots" / "03_globals_set.png"))
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#dcGlobalsState")).to_contain_text("当前：", timeout=60000)
            restored = page.evaluate(
                """() => ({ stage: document.getElementById('dcStage').value,
                            subject: document.getElementById('dcSubject').selectedOptions[0].textContent,
                            textbook: document.getElementById('dcTextbook').value })""")
            check("刷新后三下拉按记忆还原",
                  restored["stage"] == "初中" and restored["subject"] == "数学"
                  and restored["textbook"] == str(chosen["query"]["textbook_id"]), restored)
            page.locator("#dcSubject").select_option(label="语文")
            reset = page.evaluate(
                """() => ({ textbook: document.getElementById('dcTextbook').value,
                            query: window.DcGlobals.query() })""")
            check("改学科后失效教材自动归零",
                  reset["textbook"] == "" and "textbook_id" not in reset["query"], reset)
            page.screenshot(path=str(work / "shots" / "04_globals_restored.png"))

            # ---- 辅助栏字典维护折叠 ----
            nav = page.locator("#dcNavDetails")
            check("字典维护默认展开", nav.get_attribute("open") is not None)
            page.locator("#dcNavTitle").click()
            check("点标题可折叠且列表隐藏",
                  nav.get_attribute("open") is None and page.locator("#dcNavList").is_hidden())
            page.screenshot(path=str(work / "shots" / "05_sidebar_collapsed.png"))
            page.locator("#dcNavTitle").click()
            check("再点展开", nav.get_attribute("open") is not None
                  and page.locator("#dcNavList").is_visible())
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        shutil.rmtree(data_dir, ignore_errors=True)

    result["ok"] = (all(item["ok"] for item in result["checks"])
                    and not result["page_errors"] and not result["console_errors"])
    (work / "probe.toml").write_text(toml_io.dumps(result), encoding="utf-8")
    print(("PASS" if result["ok"] else "FAIL") + f" · {len(result['checks'])} 项 · {work}")
    for item in result["checks"]:
        print(("  ok " if item["ok"] else "  XX ") + item["name"])
    if result["page_errors"]:
        print("页面异常：" + " | ".join(result["page_errors"][:5]))
    if result["console_errors"]:
        print("控制台报错：" + " | ".join(result["console_errors"][:5]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
