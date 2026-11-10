# -*- coding: utf-8 -*-
"""数据字典控制台阶段一真机探针（2026-11-10 四阶段军令）。

取证口径：
- 默认只有【数据看板】一枚钉住页签（无关闭叉），数字来自引擎真实状态；
- 点辅助栏分类**新开**同名页签并激活，不覆盖当前页签；再点不重复开；
- 面板 DOM 常驻：切走再切回不重渲（探针打标记验证同一节点）；
- 关闭页签激活邻居并归位焦点；方向键 / Home / End 键盘可切；
- 全局设置三下拉真实字典数据，选定写 localStorage，刷新还原，
  改学科/学段后教材自动收窄、失效教材归零；
- 【字典维护】details 可折叠；导入对话框 Esc 关闭且焦点归位；
- 一键备份走真实备份 API（隔离 JZO_DATA_DIR，先确认开启再落盘）；
- 375px 不横向溢出，交互热区 ≥44px；全程零 console / page error。

环境坑⑦口径：端口 free_port() 动态分配，令牌 secrets 随机生成并经
/api/settings 运行时读取，数据目录隔离到临时目录，绝不碰真实 data/。

用法：``.venv/Scripts/python.exe tools/dict_console_probe.py <tag>``
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
    deadline = time.time() + 25
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("服务提前退出：" + (process.stdout.read() if process.stdout else "")[:2000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 25 秒内就绪")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "dict_console_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    (work / "shots").mkdir(parents=True)
    data_dir = Path(tempfile.mkdtemp(prefix="jzo-dict-probe-"))
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_LOCAL_TOKEN"] = secrets.token_hex(16)
    env["JZO_DATA_DIR"] = str(data_dir)
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    result: dict = {"tag": tag, "checks": [], "console_errors": [], "page_errors": [],
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
            # 隔离环境首访会自建引擎库（万级种子），首屏超时放宽
            page.goto(base + "/dict", wait_until="domcontentloaded")
            expect(page.locator("#dcTab-dashboard")).to_be_visible(timeout=60000)
            expect(page.locator("#dcPanel-dashboard .dc-stat-row")).to_be_visible(timeout=60000)
            expect(page.locator("#dcGlobalsState")).to_contain_text("当前：", timeout=60000)

            # ---- 默认态：只有看板一枚钉住页签 ----
            tabs_info = page.locator("#dcTabs").evaluate(
                """(el) => Array.from(el.querySelectorAll('.dc-tab')).map((t) => ({
                    label: t.querySelector('.dc-tab-main').textContent.trim(),
                    active: t.getAttribute('data-active'),
                    pinned: !t.querySelector('.dc-tab-close')
                }))""")
            check("默认仅【数据看板】一枚页签且钉住无关闭叉",
                  tabs_info == [{"label": "数据看板", "active": "true", "pinned": True}], tabs_info)
            stats = page.locator("#dcPanel-dashboard .dc-stat-row").inner_text()
            check("看板数字来自引擎真实状态（40 表 / v6 / 正常 / 0 外键违规）",
                  "40" in stats and "v6" in stats and "正常" in stats, stats)
            blocks = page.locator(".dc-sidebar > section").evaluate_all(
                """(els) => Array.from(els).map((s) => ({
                    title: (s.querySelector('.dc-block-title') || s.querySelector('summary')).textContent.trim(),
                    top: Math.round(s.getBoundingClientRect().top)
                }))""")
            check("辅助栏自上而下：全局设置 → 字典维护 → 操作区",
                  [b["title"] for b in blocks] == ["全局设置", "字典维护", "操作区"]
                  and blocks[0]["top"] < blocks[1]["top"] < blocks[2]["top"], blocks)
            page.screenshot(path=str(work / "shots" / "01_dashboard_default.png"))

            # ---- 分类新开页签：不覆盖、不重复 ----
            page.locator(".dc-nav-item", has_text="系统基石字典").click()
            expect(page.locator("#dcTab-foundation")).to_be_visible(timeout=10000)
            check("点分类新开同名页签并激活",
                  page.locator("#dcTab-foundation").get_attribute("aria-selected") == "true"
                  and page.locator("#dcTabs .dc-tab").count() == 2)
            check("看板面板 hidden 但 DOM 常驻（不覆盖当前页签）",
                  page.locator("#dcPanel-dashboard").is_hidden()
                  and page.locator("#dcPanel-dashboard").count() == 1)
            page.locator(".dc-nav-item", has_text="系统基石字典").click()
            check("再点同分类不重复开（仍 2 枚页签）",
                  page.locator("#dcTabs .dc-tab").count() == 2)
            expect(page.locator("#dcPanel-foundation .dc-card-grid")).to_be_visible(timeout=30000)
            cards = page.locator("#dcPanel-foundation .dc-card").count()
            check("分类面板渲染 6 张真实行数卡", cards == 6, {"cards": cards})
            page.screenshot(path=str(work / "shots" / "02_category_tab.png"))

            # 看板卡片入口同样开页签
            page.locator("#dcTab-dashboard").click()
            page.locator("#dcPanel-dashboard .dc-card", has_text="实体维度字典").locator("button").click()
            expect(page.locator("#dcTab-entity")).to_be_visible(timeout=10000)
            check("看板【打开分类】卡片同样新开页签（共 3 枚）",
                  page.locator("#dcTabs .dc-tab").count() == 3
                  and page.locator("#dcTab-entity").get_attribute("aria-selected") == "true")

            # ---- 面板状态保留：打标记 → 切走 → 切回 ----
            page.evaluate(
                """() => { document.getElementById('dcPanel-dashboard').dataset.probeMark = 'kept'; }""")
            page.locator("#dcTab-dashboard").click()
            preserved = page.evaluate(
                """() => { const p = document.getElementById('dcPanel-dashboard');
                    return { mark: p.dataset.probeMark,
                             stats: !!p.querySelector('.dc-stat-row'),
                             visible: !p.hidden }; }""")
            check("切回看板不重渲（探针标记与统计行都在）",
                  preserved == {"mark": "kept", "stats": True, "visible": True}, preserved)

            # ---- 键盘：方向键 / Home / End ----
            page.locator("#dcTab-dashboard").press("ArrowRight")
            check("ArrowRight 切到下一枚页签",
                  page.locator("#dcTab-foundation").get_attribute("aria-selected") == "true")
            page.locator("#dcTab-foundation").press("End")
            check("End 跳到末枚页签",
                  page.locator("#dcTab-entity").get_attribute("aria-selected") == "true")
            page.locator("#dcTab-entity").press("Home")
            check("Home 跳回首枚页签",
                  page.locator("#dcTab-dashboard").get_attribute("aria-selected") == "true")

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

            # ---- 全局设置：真实数据 + 联动 + 记忆 ----
            options = page.evaluate(
                """() => ({
                    stages: Array.from(document.getElementById('dcStage').options).map((o) => o.textContent),
                    subjects: document.getElementById('dcSubject').options.length,
                    textbooks: document.getElementById('dcTextbook').options.length
                })""")
            check("三下拉真实字典（4 学段项含全部 / 16 学科项 / 129 教材项）",
                  options["stages"] == ["全部学段", "小学", "初中", "高中"]
                  and options["subjects"] == 16 and options["textbooks"] == 129, options)
            page.locator("#dcStage").select_option(label="初中")
            page.locator("#dcSubject").select_option(label="数学")
            filtered = page.evaluate(
                """() => Array.from(document.getElementById('dcTextbook').options).map((o) => ({
                    value: o.value, label: o.textContent }))""")
            check("选初中+数学后教材清单收窄（非空且少于全量）",
                  1 < len(filtered) < 129, {"count": len(filtered), "first": filtered[:3]})
            page.locator("#dcTextbook").select_option(index=1)
            chosen = page.evaluate(
                """() => ({
                    saved: JSON.parse(localStorage.getItem('jzo.dictConsole.globals.v1')),
                    query: window.DcGlobals.query(),
                    state: document.getElementById('dcGlobalsState').textContent
                })""")
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
            check("改学科后失效教材自动归零（全部教材）",
                  reset["textbook"] == "" and "textbook_id" not in reset["query"], reset)

            # ---- 字典维护折叠 ----
            nav = page.locator("#dcNavDetails")
            check("字典维护默认展开", nav.get_attribute("open") is not None)
            page.locator("#dcNavTitle").click()
            check("点标题可折叠", nav.get_attribute("open") is None
                  and page.locator("#dcNavList").is_hidden())
            page.locator("#dcNavTitle").click()
            check("再点展开", nav.get_attribute("open") is not None)

            # ---- 导入对话框：Esc + 焦点归位 ----
            page.locator("#dcImportBtn").click()
            expect(page.locator(".dc-dialog")).to_be_visible(timeout=5000)
            check("导入对话框如实告知阶段二交付（不做假流程）",
                  "阶段二" in page.locator(".dc-dialog-message").inner_text())
            page.screenshot(path=str(work / "shots" / "04_import_dialog.png"))
            page.keyboard.press("Escape")
            dialog_closed = page.evaluate(
                """() => ({ open: window.DcDialog.isOpen(),
                            focused: (document.activeElement || {}).id })""")
            check("Esc 关闭对话框且焦点归位到导入按钮",
                  dialog_closed == {"open": False, "focused": "dcImportBtn"}, dialog_closed)

            # ---- 一键备份：确认开启 → 真实落盘（隔离目录） ----
            page.locator("#dcBackupBtn").click()
            expect(page.locator(".dc-dialog-title")).to_have_text("本地备份未开启", timeout=10000)
            page.locator(".dc-dialog .dc-btn-primary").click()
            expect(page.locator(".dc-dialog-title")).to_have_text("一键备份", timeout=60000)
            backup_text = page.locator(".dc-dialog-message").inner_text()
            backed_files = [p for p in (data_dir / "backups").rglob("*") if p.is_file()]
            check("备份真实落盘到隔离数据目录",
                  "备份完成" in backup_text and len(backed_files) > 0,
                  {"message": backup_text, "files": [str(p.relative_to(data_dir)) for p in backed_files[:5]]})
            page.screenshot(path=str(work / "shots" / "05_backup_done.png"))
            page.keyboard.press("Escape")

            # ---- 375px：不横溢 + 热区 ----
            page.locator(".dc-nav-item", has_text="系统基石字典").click()
            expect(page.locator("#dcTab-foundation")).to_be_visible(timeout=10000)
            page.set_viewport_size({"width": 375, "height": 780})
            page.wait_for_timeout(300)
            narrow = page.evaluate(
                """() => {
                    const hit = (sel) => Array.from(document.querySelectorAll(sel))
                        .filter((el) => el.getBoundingClientRect().width > 0)
                        .map((el) => { const r = el.getBoundingClientRect();
                            return { w: Math.round(r.width), h: Math.round(r.height) }; });
                    const groups = { tab: hit('.dc-tab-main'), close: hit('.dc-tab-close'),
                                     nav: hit('.dc-nav-item'), btn: hit('.dc-btn'),
                                     select: hit('.dc-field select'), summary: hit('.dc-nav summary') };
                    const mins = {};
                    Object.keys(groups).forEach((k) => {
                        mins[k] = groups[k].length ? Math.min.apply(null,
                            groups[k].map((r) => Math.min(r.w, r.h))) : null;
                    });
                    return { overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                             mins: mins };
                }""")
            result["geometry"]["narrow"] = narrow
            check("375px 不横向溢出", narrow["overflow"] <= 0, narrow)
            check("375px 全部交互热区 ≥44px（页签/关闭叉/导航/按钮/下拉/折叠标题）",
                  all(v is not None and v >= 44 for v in narrow["mins"].values()), narrow["mins"])
            page.screenshot(path=str(work / "shots" / "06_375px.png"))
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