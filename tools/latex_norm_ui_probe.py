# -*- coding: utf-8 -*-
"""记号标准字典 UI 探针（2.21.0 卡 §4/§6 探针②）：宿主字典族真人路径取证。

用法：``.venv/Scripts/python.exe tools/latex_norm_ui_probe.py <tag>``

隔离：JZO_DATA_DIR/JZO_PLUGINS_DIR 指证据目录下空副本，启动钩子幂等播种闭集；
随机令牌（secrets，禁写死）＋动态端口（free_port）；AI key 全清空＝零引擎零出网。
Playwright 自驱 chromium（非内置浏览器，绕开隐藏 surface 坑），宿主 /dict 同源页
直接 page.locator（norm UI 住宿主字典控制台，不经沙箱 iframe）。

走用户路径：五列对照＋八族筹码过滤＋名称/代码搜索＋选默认 radio＋恢复出厂（对话框
Esc/焦点归位/确认）＋开集待审收编（须目标＋预览）/驳回（黑名单对话框）＋375px 零横溢。
判据落 probe.toml，关键态截图存 shots/；收口点杀进程＋端口复验关闭。
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

import os
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from app.core import toml_io, wire
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(url: str, token: str | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(url)
    if token:
        request.add_header("X-JZO-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, wire.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        return error.code, wire.loads(payload or "{}")


def http_post(url: str, payload: dict, token: str) -> tuple[int, dict]:
    body = wire.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-JZO-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, wire.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        return error.code, wire.loads(payload or "{}")


def wait_health(base: str, process: subprocess.Popen, log_path: Path) -> None:
    deadline = time.time() + 40
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("服务提前退出：\n" + log_path.read_text(
                encoding="utf-8", errors="replace")[:3000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 40 秒内就绪")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "latex-norm" / "ui" / tag
    shots = work / "shots"
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    for folder in (shots, data_dir, plugins_dir):
        folder.mkdir(parents=True, exist_ok=True)

    token = secrets.token_hex(16)
    nonce = secrets.token_hex(8)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = token
    env["JZO_RESTART_DISABLED"] = "1"
    for key in ("JZO_AI_API_KEY", "JZO_BAILIAN_API_KEY",
                "JZO_SILICONFLOW_API_KEY", "JZO_OLLAMA_API_KEY"):
        env[key] = ""
    server_log = work / "server.log"
    log_handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True)

    result: dict = {"probe": "latex_norm_ui", "tag": tag, "nonce": nonce, "base": base,
                    "port": port, "checks": [], "console_errors": [], "page_errors": [],
                    "http_failures": [], "engine_calls": [], "metrics": {}, "shots": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    def shot(name: str) -> Path:
        path = shots / name
        result["shots"].append(str(path))
        return path

    try:
        wait_health(base, process, server_log)
        # 真实产品路径造两条开集待审候选（清洗写路 unknown → record_unknown pending）。
        for code in ("zqprobe", "zqreject"):
            status, _ = http_post(base + "/api/agent/clean_latex",
                                  {"text": "$\\%s$" % code}, token)
            if status != 200:
                raise RuntimeError("造待审候选失败 status=%s" % status)
        _, pend = http_json(base + "/api/norm/corrections?status=pending")
        pending_codes = [c["raw_code"] for c in pend["corrections"]]
        check("清洗写路真实落两条开集待审候选", pend["counts"]["pending"] >= 2
              and "zqprobe" in pending_codes and "zqreject" in pending_codes,
              {"pending": pending_codes})
        _, ent = http_json(base + "/api/norm/entries")
        le = next(e for e in ent["entries"] if e["entry_key"] == "le")
        le_name = le["name"]
        upright_id = next(v["id"] for v in le["variants"] if v["latex_code"] == r"\le")
        factory_id = le["factory_default_variant_id"]

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type == "error" else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.on("response", lambda r: result["http_failures"].append(
                "%s %s" % (r.status, r.url)) if r.status >= 400 else None)
            page.on("request", lambda r: result["engine_calls"].append(r.url)
                    if re.search(r"/api/(agent/recognize|models/|ingest)", r.url) else None)
            page.goto(base + "/dict?cat=notation&sub=norm-dict", wait_until="networkidle")

            expect(page.locator(".dc-norm-head h2.dc-panel-title")).to_be_visible(timeout=20000)
            expect(page.locator(".dc-norm-entry").first).to_be_visible(timeout=20000)
            page.wait_for_function("document.querySelectorAll('mjx-container').length > 0",
                                   timeout=60000)
            entry_count = page.locator(".dc-norm-entry").count()
            chip_count = page.locator(".dc-norm-chip").count()
            mjx = page.locator("mjx-container").count()
            result["metrics"]["desktop"] = {"entries": entry_count, "chips": chip_count,
                                            "mjx": mjx, "viewport": [1440, 900]}
            check("闭集全量 223 条目渲染＋八族筹码（含全部＝9）＋MathJax 真渲染",
                  entry_count == 223 and chip_count == 9 and mjx > 0,
                  result["metrics"]["desktop"])
            page.screenshot(path=str(shot("01-desktop-five-col.png")), full_page=True)

            first = page.locator(".dc-norm-entry").first
            five = {
                "family": first.locator(".dc-norm-family").count(),
                "name": first.locator(".dc-norm-name").count(),
                "vhead": first.locator(".dc-norm-vhead > span").count(),
                "code_label": first.locator(".dc-norm-vrow .dc-norm-vcode .dc-norm-label").count(),
                "render": first.locator(".dc-norm-vrow .dc-norm-vrender").count(),
                "radio": first.locator(".dc-norm-vrow .dc-norm-vpick input[type=radio]").count(),
            }
            check("五列齐全：①记号族②名称③代码＋来源筹码④逐行渲染⑤默认 radio",
                  five["family"] == 1 and five["name"] == 1 and five["vhead"] == 3
                  and five["code_label"] >= 1 and five["render"] >= 1 and five["radio"] >= 1,
                  five)
            badge_panel = page.locator(".dc-norm-machine-badge").inner_text()
            badge_nav = page.locator(".dc-cat-machine").count()
            check("整机生效徽标：面板头＋左栏导航各一处",
                  badge_panel == "整机生效" and badge_nav >= 1,
                  {"panel": badge_panel, "nav": badge_nav})

            # 单轴过滤：记号族筹码
            page.locator(".dc-norm-chip", has_text="关系不等").click()
            page.wait_for_timeout(300)
            fams = page.locator(".dc-norm-entry .dc-norm-family").all_inner_texts()
            shown = page.locator(".dc-norm-entry").count()
            on_chip = page.locator(".dc-norm-chip.is-on").inner_text()
            pressed = page.locator(".dc-norm-chip.is-on").get_attribute("aria-pressed")
            check("记号族筹码过滤「关系不等」：19 条全族一致＋选中态不只靠颜色（aria-pressed）",
                  shown == 19 and all(f == "关系不等" for f in fams)
                  and on_chip == "关系不等" and pressed == "true",
                  {"shown": shown, "on": on_chip, "pressed": pressed})
            page.screenshot(path=str(shot("02-filter-family.png")), full_page=True)

            # 名称/代码搜索
            page.locator(".dc-norm-search").fill("leqslant")
            page.wait_for_timeout(300)
            search_shown = page.locator(".dc-norm-entry").count()
            check("代码搜索 leqslant：命中收窄（少于全族 19、大于 0）",
                  0 < search_shown < 19, {"shown": search_shown})
            page.locator(".dc-norm-search").fill("")
            page.locator(".dc-norm-chip", has_text="全部").click()
            page.wait_for_timeout(300)
            check("清空搜索＋回「全部」：恢复 223 条",
                  page.locator(".dc-norm-entry").count() == 223,
                  {"shown": page.locator(".dc-norm-entry").count()})

            # 选默认 radio（le 条目，选非出厂的 \le 直立形）
            le_sec = page.locator('section.dc-norm-entry[aria-label="%s"]' % le_name)
            expect(le_sec).to_be_visible(timeout=10000)
            le_sec.locator('input.dc-norm-radio[value="%d"]' % upright_id).click()
            expect(le_sec.locator(".dc-norm-default-state")).to_have_text(
                "当前：老师已选默认", timeout=10000)
            expect(le_sec.locator(".dc-norm-reset")).to_be_enabled(timeout=10000)
            _, ent2 = http_json(base + "/api/norm/entries")
            le2 = next(e for e in ent2["entries"] if e["entry_key"] == "le")
            check("点选默认 radio：状态翻「老师已选默认」＋恢复出厂键启用＋库 chosen 落值",
                  le2["chosen_default_variant_id"] == upright_id,
                  {"chosen": le2["chosen_default_variant_id"], "upright": upright_id})
            page.screenshot(path=str(shot("03-chosen-default.png")), full_page=True)

            # 恢复出厂：先 Esc 验焦点陷阱＋归位，再确认回退
            le_sec.locator(".dc-norm-reset").click()
            dialog = page.locator(".dc-dialog")
            expect(dialog).to_be_visible(timeout=10000)
            dlg_title = dialog.locator(".dc-dialog-title").inner_text()
            page.screenshot(path=str(shot("04-reset-dialog.png")))
            page.keyboard.press("Escape")
            expect(dialog).to_have_count(0, timeout=10000)
            restored = page.evaluate(
                "() => String(document.activeElement && document.activeElement.className || '')")
            check("恢复出厂对话框：Esc 收窗＋焦点归位到恢复出厂键（焦点陷阱）",
                  dlg_title == "恢复出厂默认" and "dc-norm-reset" in restored,
                  {"title": dlg_title, "activeElement": restored})
            le_sec.locator(".dc-norm-reset").click()
            expect(page.locator(".dc-dialog")).to_be_visible(timeout=10000)
            page.locator(".dc-dialog .dc-btn-primary").click()
            expect(le_sec.locator(".dc-norm-default-state")).to_have_text(
                "当前：出厂默认", timeout=10000)
            expect(le_sec.locator(".dc-norm-reset")).to_be_disabled(timeout=10000)
            _, ent3 = http_json(base + "/api/norm/entries")
            le3 = next(e for e in ent3["entries"] if e["entry_key"] == "le")
            check("确认恢复出厂：选择回退出厂（chosen=NULL）＋出厂默认不动＋键禁用",
                  le3["chosen_default_variant_id"] is None
                  and le3["effective_default_variant_id"] == factory_id,
                  {"chosen": le3["chosen_default_variant_id"],
                   "effective": le3["effective_default_variant_id"], "factory": factory_id})

            # 开集待审区
            expect(page.locator(".dc-norm-inbox-badge")).to_have_text("待审 2", timeout=10000)
            inbox_rows = page.locator(".dc-norm-inbox-row").count()
            compare_cells = page.locator(".dc-norm-inbox-row .dc-norm-compare-cell").count()
            check("开集待审区：徽标「待审 2」＋两行＋原始/收编后对照格",
                  inbox_rows == 2 and compare_cells == 4,
                  {"rows": inbox_rows, "compare_cells": compare_cells})
            page.screenshot(path=str(shot("05-inbox-pending.png")), full_page=True)

            # 收编 zqprobe → leqslant（须目标＋预览渲染＋按钮启用）
            row = page.locator("section.dc-norm-inbox-row").filter(
                has=page.locator("code.dc-norm-code", has_text=re.compile(r"^\\zqprobe$")))
            expect(row).to_be_visible(timeout=10000)
            expect(row.locator(".dc-norm-confirm")).to_be_disabled()
            row.locator(".dc-norm-target-input").fill("leqslant")
            expect(row.locator(".dc-norm-preview mjx-container")).to_have_count(1, timeout=10000)
            expect(row.locator(".dc-norm-confirm")).to_be_enabled(timeout=10000)
            page.screenshot(path=str(shot("06-inbox-confirm-preview.png")))
            row.locator(".dc-norm-confirm").click()
            expect(page.locator(".dc-norm-inbox-badge")).to_have_text("待审 1", timeout=10000)
            _, corr = http_json(base + "/api/norm/corrections?status=confirmed")
            conf_codes = [c["raw_code"] for c in corr["corrections"]]
            check("收编 zqprobe→leqslant：预览渲染＋按钮由禁转启＋行移除＋库 confirmed",
                  "zqprobe" in conf_codes and corr["counts"]["confirmed"] >= 1,
                  {"confirmed": conf_codes})

            # 驳回 zqreject（黑名单对话框）
            row2 = page.locator("section.dc-norm-inbox-row").filter(
                has=page.locator("code.dc-norm-code", has_text=re.compile(r"^\\zqreject$")))
            expect(row2).to_be_visible(timeout=10000)
            row2.locator(".dc-norm-reject").click()
            expect(page.locator(".dc-dialog")).to_be_visible(timeout=10000)
            rej_title = page.locator(".dc-dialog .dc-dialog-title").inner_text()
            page.locator(".dc-dialog .dc-btn-primary").click()
            expect(page.locator(".dc-norm-inbox-badge")).to_have_text("待审 0", timeout=10000)
            _, corr2 = http_json(base + "/api/norm/corrections?status=rejected")
            rej_codes = [c["raw_code"] for c in corr2["corrections"]]
            check("驳回 zqreject：黑名单对话框确认＋待审归零＋库 rejected",
                  rej_title == "驳回进黑名单" and "zqreject" in rej_codes,
                  {"title": rej_title, "rejected": rej_codes})
            page.screenshot(path=str(shot("07-inbox-empty.png")), full_page=True)

            # 375px 窄屏零横溢
            page.set_viewport_size({"width": 375, "height": 812})
            page.wait_for_timeout(500)
            narrow = page.evaluate("""() => {
              const de = document.documentElement, b = document.body;
              const panel = document.querySelector('.dc-norm-head').closest('.dc-subpanel');
              const entries = Array.from(document.querySelectorAll('.dc-norm-entry'));
              const rows = Array.from(document.querySelectorAll('.dc-norm-inbox-row'));
              const over = (el) => el ? el.scrollWidth - el.clientWidth : 0;
              return {
                doc: Math.max(de.scrollWidth, b.scrollWidth),
                panel: panel ? panel.scrollWidth - panel.clientWidth : null,
                maxEntry: Math.max(0, ...entries.map(over)),
                maxRow: Math.max(0, ...rows.map(over)),
                familyStacked: getComputedStyle(document.querySelector('.dc-norm-family')).gridColumn
              };
            }""")
            result["metrics"]["narrow"] = dict(narrow, viewport=[375, 812])
            check("375px 零横溢：文档≤375＋面板/条目/待审行无内部横溢＋族筹码堆叠",
                  narrow["doc"] <= 376 and (narrow["panel"] or 0) <= 1
                  and narrow["maxEntry"] <= 1 and narrow["maxRow"] <= 1
                  and "1 / -1" in str(narrow["familyStacked"]),
                  result["metrics"]["narrow"])
            page.screenshot(path=str(shot("08-narrow-375.png")), full_page=True)

            check("全程零引擎请求（无 recognize/models/ingest 调用）",
                  not result["engine_calls"], {"engine_calls": result["engine_calls"][:5]})
            check("宿主页零未捕获 JS 错误", not result["page_errors"],
                  {"page_errors": result["page_errors"][:5]})
            check("全程零 4xx/5xx 响应", not result["http_failures"],
                  {"http_failures": result["http_failures"][:6]})
            check("零控制台报错", not result["console_errors"],
                  {"console_errors": result["console_errors"][:5]})
            browser.close()
    except Exception as exc:  # noqa: BLE001 - 探针把异常也写进回单
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log_handle.close()
        port_closed = False
        for _ in range(25):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                if sock.connect_ex(("127.0.0.1", port)) != 0:
                    port_closed = True
                    break
            time.sleep(0.2)
        result["metrics"]["port_closed_after_kill"] = port_closed

    passed = sum(1 for c in result["checks"] if c["ok"])
    total = len(result["checks"])
    result["passed"] = passed
    result["total"] = total
    report = work / "probe.toml"
    report.write_text(toml_io.dumps(result), encoding="utf-8")
    print(wire.dumps({"tag": tag, "passed": passed, "total": total,
                      "port_closed": result["metrics"].get("port_closed_after_kill"),
                      "error": result.get("error"), "report": str(report)},
                     ensure_ascii=False))
    for c in result["checks"]:
        if not c["ok"]:
            print("FAIL:", c["name"], wire.dumps(c["detail"], ensure_ascii=False)[:320])
    return 0 if passed == total and total > 0 and not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())