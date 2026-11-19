# -*- coding: utf-8 -*-
"""模型配置四栏表重做真机探针（2.20.0 卡§1/§5）。

用法：``.venv/Scripts/python.exe tools/model_table_probe.py [tag]``

隔离：独立 JZO_DATA_DIR / JZO_PLUGINS_DIR 副本＋动态空闲端口＋每次随机令牌，
不碰用户 data/ 与正式服务；engines/ 只读体检（本机 MinerU 已装＝卸载弹窗分支，
VLM 缺 llama-server＝安装弹窗分支），弹窗一律 dismiss，绝不真装真删。
收口点杀进程并复验端口关闭。产物落 .system_generated/model-table/<tag>/。

判据：
1. 启动注入下拉 registry?probe=0（不跑硬件探针）；点进配置中心那一刻 probe=1；
2. 四栏表上屏：名称/简要/状态/操作；三工种分组；自动分流默认组置顶；
3. §5 活字：vlm 徽章「未安装」、简要带本机显存现算（你这台 X G）；
4. 宽屏左列表＋右详情：点名称出详情，先简要用法，「详细说明」再点才出；
5. 键盘：Tab 摸到名称钮，Enter 展开/收起，收起焦点还原；
6. 安装确认弹窗摆 3.3GB 成本，dismiss 后零安装请求（出网铁律）；
7. MinerU 已装行出【卸载】，确认弹窗点目录名，dismiss 后零卸载请求、目录仍在；
8. 停用经 relay 落隔离插件目录、下拉同步摘除；启用恢复；
9. 375px 零横溢、详情内联行下；
10. 零 JS 异常、零 HTTP 失败、三查=0、收口端口关闭。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402
from app.core.config import plugin_source_root  # noqa: E402

import os
import re
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
PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
EDITOR_ID = "org.jiuzhang.editor"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen, log_path: Path) -> None:
    deadline = time.time() + 40
    while time.time() < deadline:
        if process.poll() is not None:
            output = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            raise RuntimeError("服务提前退出：\n" + output[:3000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 40 秒内就绪")


def seed_batch(base: str, token: str, no: int) -> int:
    import json
    doc = {"schema_version": "2.0", "type": "single_choice",
           "stem": "探针表卷第 %d 题：$x+%d=%d$ 的解是（  ）" % (no, no, no + 1),
           "options": [{"key": "A", "content": "$1$"}, {"key": "B", "content": "$2$"}],
           "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
           "solution": "解析：移项即得。", "difficulty": "L1", "grade": "高一",
           "tags": ["探针表"], "source": {"paper_title": "探针表卷", "question_no": str(no),
                                          "year": 2026, "exam_type": "一模"}}
    body = json.dumps({"questions": [{"question": doc}],
                       "source_name": "探针表卷%d.pdf" % no,
                       "origin": "probe.table"}).encode("utf-8")
    request = urllib.request.Request(
        base + "/api/pending/batches", data=body, method="POST",
        headers={"Content-Type": "application/json", "X-JZO-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status
    except urllib.error.HTTPError as error:
        error.close()
        return error.code


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    token = "probe-" + secrets.token_hex(8)
    work = ROOT / ".system_generated" / "model-table" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir, shots = work / "data", work / "plugins", work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    plugin_dir = plugins_dir / EDITOR_ID
    shutil.copytree(PLUGIN_SOURCE_DIR / EDITOR_ID, plugin_dir)
    shutil.rmtree(plugin_dir / "models", ignore_errors=True)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = token
    env["JZO_RESTART_DISABLED"] = "1"
    env["JZO_POOL_ADMIT_DISABLED"] = "1"
    server_log = work / "server.log"
    handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)

    result: dict = {"tag": tag, "base": base, "viewport": "1920x1080",
                    "checks": [], "console_errors": [], "page_errors": [],
                    "http_failures": [], "registry_requests": [],
                    "install_requests": [], "uninstall_requests": [],
                    "dialogs": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    prefs_file = plugin_dir / "model_prefs.toml"
    mineru_dir = ROOT / "engines" / "mineru"
    try:
        wait_health(base, process, server_log)
        seeded = sum(1 for no in (1, 2) if seed_batch(base, token, no) == 201)
        check("宿主写口种 2 批（列表非空）", seeded == 2, {"seeded": seeded})
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("response", lambda response: result["http_failures"].append(
                "%s %s" % (response.status, response.url)) if response.status >= 400 else None)

            def on_request(request) -> None:
                url = request.url
                if "/api/models/registry" in url:
                    result["registry_requests"].append(url)
                if "/api/models/vlm/install" in url or "/api/models/mineru/install" in url \
                        or "/api/models/ocr/install" in url:
                    result["install_requests"].append(url)
                if "/uninstall" in url and "/api/models/" in url:
                    result["uninstall_requests"].append(url)

            page.on("request", on_request)
            page.on("dialog", lambda dialog: (result["dialogs"].append(dialog.message),
                                              dialog.dismiss()))
            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
            expect(canvas.locator(".ed-batch-row").first).to_be_visible(timeout=20000)
            page.wait_for_timeout(800)
            boot = [u for u in result["registry_requests"] if "probe=0" in u]
            check("启动注入下拉走 probe=0（不跑硬件探针）", bool(boot),
                  {"registry_requests": result["registry_requests"][:4]})

            # ---------- 点进配置中心：probe=1 真测＋四栏表＋分组置顶 ----------
            # 等 probe=1 响应落地再断言：启动 probe=0 的渲染先上屏，体检含子进程约 1–2s。
            with page.expect_response(
                    lambda r: "/api/models/registry?probe=1" in r.url,
                    timeout=20000) as resp_info:
                canvas.locator("#epModelConfigList").click()
            entered_payload = resp_info.value.json()
            hw_label = str(entered_payload["hardware"]["vram_label"])
            view = canvas.locator("#edModelConfigModal")
            expect(view).to_be_visible(timeout=10000)
            expect(canvas.locator(".ep-mt-table").first).to_be_visible(timeout=15000)
            expect(canvas.locator(".ep-model-config-hw-line")).to_contain_text(
                hw_label, timeout=10000)
            check("点进配置中心那一刻 probe=1 真测",
                  hw_label not in ("未检测", ""), entered_payload["hardware"])
            heads = canvas.locator(".ep-mt-table thead").first.evaluate(
                "node => Array.from(node.querySelectorAll('th')).map(n => n.textContent)")
            check("四栏表头：名称/简要/状态/操作",
                  heads == ["名称", "简要（点击展开）", "状态", "操作"], heads)
            groups = canvas.locator(".ep-mt-group-title").all_text_contents()
            check("三工种分组上屏", groups == ["切题定位", "整题转写", "公式专科"], groups)
            top = canvas.locator("#edModelConfigList").evaluate(
                """node => { var seats = node.querySelector('.ep-model-config-auto-seats');
                     var firstGroup = node.querySelector('.ep-mt-group');
                     return !!(seats && firstGroup &&
                       (seats.compareDocumentPosition(firstGroup) & Node.DOCUMENT_POSITION_FOLLOWING)); }""")
            check("自动分流默认组置顶（在首个工种组之前）", bool(top))

            # ---------- §6 名单：VLM 六→三、Pix2Text 改名、准档解锁 ----------
            vlm_count = canvas.locator(".ep-mt-row", has_text="（本地）").count()
            check("VLM 六→三（千问/面壁/书生）", vlm_count == 3, vlm_count)
            for gone in ("SmolVLM", "Phi 视觉", "Gemma 视觉"):
                check("剔座不再上屏：%s" % gone,
                      canvas.locator(".ep-mt-row", has_text=gone).count() == 0)
            check("Pix2Text·MFR 改名上屏",
                  canvas.locator(".ep-mt-row", has_text="Pix2Text·MFR").count() == 1)
            check("旧名 pix2tex 不再上屏（大小写敏感）",
                  canvas.locator(".ep-mt-row", has_text=re.compile("pix2tex")).count() == 0)
            acc_row = canvas.locator(".ep-mt-row", has_text="RapidOCR·准")
            check("准档解锁：未就绪徽章＋真安装按钮",
                  acc_row.locator(".ep-mt-badge").text_content() == "未就绪"
                  and acc_row.locator(".ep-mt-act", has_text="安装").count() == 1)
            acc_row.locator(".ep-mt-act", has_text="安装").click()
            page.wait_for_timeout(400)
            check("准档安装确认弹窗摆 139MB 成本",
                  bool(result["dialogs"]) and "139MB" in result["dialogs"][-1],
                  result["dialogs"][-1:])
            check("dismiss 后零准档安装请求（出网只由点头发起）",
                  not [u for u in result["install_requests"] if "/ocr/install" in u],
                  result["install_requests"])
            page.screenshot(path=str(shots / "01-table-wide.png"))

            # ---------- §5 活字：徽章＋简要带本机显存 ----------
            vlm_row = canvas.locator(".ep-mt-row", has_text="千问 Qwen2.5-VL")
            badge = vlm_row.locator(".ep-mt-badge").text_content()
            brief = vlm_row.locator(".ep-mt-cell-brief").text_content()
            check("VLM 未安装徽章（本机缺 llama-server）", badge == "未安装", badge)
            check("简要活字带本机显存现算", "你这台" in brief and hw_label in brief
                  and "显存" in brief, brief)
            hw_line = canvas.locator(".ep-model-config-hw-line").text_content()
            check("硬件行现测标注＋真值上屏", "现测" in hw_line and hw_label in hw_line,
                  hw_line)

            # ---------- 宽屏右详情：先简要，详细说明再点才出 ----------
            vlm_row.locator(".ep-mt-name").click()
            panel = canvas.locator(".ep-mt-detail")
            expect(panel.locator(".ep-mt-detail-box")).to_be_visible(timeout=5000)
            usage = panel.locator(".ep-mt-detail-usage").text_content()
            more = panel.locator(".ep-mt-detail-more")
            check("详情先给简要用法", "干啥" in usage, usage[:60])
            check("详细说明默认收起", more.evaluate("node => !node.open"))
            more.locator("summary").click()
            expect(panel.locator(".ep-mt-detail-text")).to_be_visible(timeout=3000)
            detail_text = panel.locator(".ep-mt-detail-text").text_content()
            check("再点才出体检详情（安装引导）", "安装本地 VLM" in detail_text,
                  detail_text[:80])
            page.screenshot(path=str(shots / "02-detail-wide.png"))

            # ---------- 键盘：Enter 展开/收起＋焦点还原 ----------
            name_btn = vlm_row.locator(".ep-mt-name")
            name_btn.click()  # 收起（再点同名＝收）
            page.wait_for_timeout(200)
            name_btn.focus()
            page.keyboard.press("Enter")
            page.wait_for_timeout(200)
            expanded = name_btn.get_attribute("aria-expanded")
            page.keyboard.press("Enter")
            page.wait_for_timeout(200)
            collapsed = canvas.locator(".ep-mt-row", has_text="千问 Qwen2.5-VL").locator(
                ".ep-mt-name").get_attribute("aria-expanded")
            refocused = canvas.locator("#edRoot").evaluate(
                """() => { var a = document.activeElement;
                     return a.classList.contains('ep-mt-name') &&
                       a.textContent.indexOf('千问') >= 0; }""")
            check("键盘 Enter 展开/收起＋收起焦点还原",
                  expanded == "true" and collapsed == "false" and bool(refocused),
                  {"expanded": expanded, "collapsed": collapsed, "refocused": refocused})

            # ---------- 安装确认弹窗：摆成本，dismiss 零出网 ----------
            vlm_row = canvas.locator(".ep-mt-row", has_text="千问 Qwen2.5-VL")
            vlm_row.locator(".ep-mt-act", has_text="安装").click()
            page.wait_for_timeout(400)
            install_dialogs = [m for m in result["dialogs"] if "3.3GB" in m]
            check("安装确认弹窗摆 3.3GB 成本", bool(install_dialogs),
                  result["dialogs"][-1:])
            check("dismiss 后零安装请求（出网只由点头发起）",
                  not result["install_requests"], result["install_requests"])

            # ---------- MinerU 已装行：卸载弹窗点目录，dismiss 零删 ----------
            mineru_row = canvas.locator(".ep-mt-row", has_text="MinerU·本地")
            uninstall_btn = mineru_row.locator(".ep-mt-act", has_text="卸载")
            expect(uninstall_btn).to_be_visible(timeout=5000)
            uninstall_btn.click()
            page.wait_for_timeout(400)
            uninstall_dialogs = [m for m in result["dialogs"] if "engines/mineru/" in m]
            check("卸载确认弹窗点目录名", bool(uninstall_dialogs), result["dialogs"][-1:])
            check("dismiss 后零卸载请求、目录仍在",
                  not result["uninstall_requests"] and mineru_dir.is_dir(),
                  result["uninstall_requests"])
            page.screenshot(path=str(shots / "03-actions.png"))

            # ---------- 停用/启用：落隔离插件目录＋下拉同步 ----------
            vlm_row = canvas.locator(".ep-mt-row", has_text="千问 Qwen2.5-VL")
            vlm_row.locator(".ep-mt-toggle").click()
            deadline = time.time() + 15
            disabled: list = []
            while time.time() < deadline:
                disabled = toml_io.load(prefs_file, {}).get("disabled", [])
                if "vlm_qwen" in disabled:
                    break
                page.wait_for_timeout(300)
            check("停用经 relay 落隔离插件目录", "vlm_qwen" in disabled, disabled)
            check("data/ 全树无 model_prefs.toml",
                  not list(data_dir.rglob("model_prefs.toml")))
            vlm_row = canvas.locator(".ep-mt-row", has_text="千问 Qwen2.5-VL")
            expect(vlm_row.locator(".ep-mt-off-tag")).to_have_count(1, timeout=15000)
            check("停用行标已停用", True)
            vlm_row.locator(".ep-mt-toggle", has_text="启用").click()
            deadline = time.time() + 15
            while time.time() < deadline:
                disabled = toml_io.load(prefs_file, {}).get("disabled", [])
                if "vlm_qwen" not in disabled:
                    break
                page.wait_for_timeout(300)
            check("启用恢复", "vlm_qwen" not in disabled, disabled)

            # ---------- 375px：零横溢＋详情内联 ----------
            page.set_viewport_size({"width": 375, "height": 720})
            page.wait_for_timeout(400)
            overflow = canvas.locator("#edRoot").evaluate(
                """() => { var v = document.getElementById('edModelConfigModal');
                     var card = document.querySelector('.ep-model-config-card');
                     return Math.max(v.scrollWidth - v.clientWidth,
                       card.scrollWidth - card.clientWidth); }""")
            check("375px 模型视图零横溢", overflow <= 0, {"overflow_px": overflow})
            narrow_row = canvas.locator(".ep-mt-row", has_text="千问 Qwen2.5-VL")
            narrow_row.locator(".ep-mt-name").click()
            expect(canvas.locator(".ep-mt-detail-row")).to_be_visible(timeout=5000)
            check("窄屏详情内联行下（右面板不渲染）",
                  canvas.locator(".ep-mt-detail").count() == 0)
            page.screenshot(path=str(shots / "04-mobile-375.png"))
            browser.close()

        counts = {"fetch(": 0, "parent.document": 0, "localStorage": 0}
        for script in sorted((plugin_dir / "dist").glob("*.js")):
            text = script.read_text(encoding="utf-8", errors="replace")
            for needle in counts:
                counts[needle] += text.count(needle)
        check("三查 fetch(/parent.document/localStorage=0",
              all(value == 0 for value in counts.values()), counts)
        check("页面零 JS 异常", not result["page_errors"], result["page_errors"][:5])
        check("全程零 HTTP 失败", not result["http_failures"], result["http_failures"][:5])
    except Exception as error:  # noqa: BLE001 - 探针要把现场带回去
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        handle.close()
        time.sleep(0.5)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            closed = sock.connect_ex(("127.0.0.1", port)) != 0
        check("收口端口复验关闭", closed, {"port": port})

    failed = [item for item in result["checks"] if not item["ok"]]
    result["ok"] = not failed and not result.get("error")
    report = work / "probe.toml"
    report.write_text(toml_io.dumps(result, default=str), encoding="utf-8")
    for item in result["checks"]:
        print("[%s] %s" % ("PASS" if item["ok"] else "FAIL", item["name"]))
    print("ok=%s checks=%d failed=%d" % (result["ok"], len(result["checks"]), len(failed)))
    print("probe:", report)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())