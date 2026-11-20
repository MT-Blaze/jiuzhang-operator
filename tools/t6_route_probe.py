# -*- coding: utf-8 -*-
"""T6 转码七链路路由与审核重认真机探针（卡 §6）：``.venv/Scripts/python.exe tools/t6_route_probe.py [tag]``。
隔离 JZO_DATA_DIR/JZO_PLUGINS_DIR 副本＋动态端口＋随机令牌，不碰用户 data/ 与正式服务；
六步取证（两卷分流、重认三席、prefs 键盘、375px、收口孤儿零）＋VLM 安装加演；视觉真回填留欠账（卡 §7）。证据落 .system_generated/t6-route/<tag>/。
"""
from __future__ import annotations

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

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".system_generated" / "t6-route" / (sys.argv[1] if len(sys.argv) > 1 else "run1")
DATA, PLUGINS, SHOTS = WORK / "data", WORK / "plugins", WORK / "shots"
TOKEN = "probe-" + secrets.token_hex(8)
os.environ["JZO_DATA_DIR"] = str(DATA)
os.environ["JZO_PLUGINS_DIR"] = str(PLUGINS)
os.environ["JZO_LOCAL_TOKEN"] = TOKEN
os.environ["JZO_RESTART_DISABLED"] = "1"
os.environ["JZO_POOL_ADMIT_DISABLED"] = "1"
sys.path.insert(0, str(ROOT))
from app.core import toml_io, wire  # noqa: E402
from app.core.config import plugin_source_root  # noqa: E402
from app.core.ingest import vlm_setup  # noqa: E402
from app.core.ingest.recognize import vlm_service  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402
EDITOR_ID = "org.jiuzhang.editor"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
SAMPLE_IMG = (ROOT / ".system_generated" / "a2_image_ingest" / "ev1" / "data" / "pending_sources"
              / "20261118-193020_220dac_东北师大附中2023-2024高一上学期第一次月考试题.pdf")
SAMPLE_TXT = ROOT / "test_papers" / "A3_2027【绵阳一诊】.pdf"
IMG_CAP, TXT_CAP, SEAT_CAP, INSTALL_CAP = 7200, 3600, 900, 2400  # 单并发逐题约300s，20题纯图卷须宽限；wait_done 就绪即返不空等
def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
def port_closed(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) != 0
def http_json(base: str, path: str) -> dict:
    with urllib.request.urlopen(base + path, timeout=60) as response:
        return wire.loads(response.read().decode("utf-8") or "{}")
def wait_done(base: str, batch_id: str, cap: int) -> dict:
    deadline, detail = time.time() + cap, {}
    while time.time() < deadline:
        detail = http_json(base, "/api/pending/batches/%s/questions" % batch_id)
        if (detail.get("route") or {}).get("done"):
            return detail
        time.sleep(8)
    return detail
def kill_service_by_log(server_log: Path) -> dict:
    ports = re.findall(r"端口 (\d+)", server_log.read_text(encoding="utf-8", errors="replace"))
    if not ports:
        return {"killed": False, "reason": "日志里没有服务端口"}
    port = int(ports[-1])
    listing = subprocess.run(["netstat", "-ano"], capture_output=True,
                             timeout=30).stdout.decode("utf-8", "replace")
    pid = next((line.split()[-1] for line in listing.splitlines()
                if "127.0.0.1:%d" % port in line and "LISTENING" in line), "")
    if not pid:
        return {"killed": False, "port": port, "reason": "端口没有监听进程"}
    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True, timeout=30)
    return {"killed": True, "port": port, "pid": pid}
def engine_pids() -> list:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq mineru-api.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
    pids = [line.split('","')[1] for line in out.splitlines() if line.startswith('"mineru-api')]
    w = subprocess.run(["wmic", "process", "where", "name='python.exe'",
                        "get", "ProcessId,CommandLine", "/FORMAT:CSV"],
                       capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
    pids += [line.rsplit(",", 1)[-1].strip() for line in w.splitlines()
             if "mineru" in line.lower() and line.strip()]
    return sorted(set(pids))
def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    started = time.time()
    if WORK.exists():
        shutil.rmtree(WORK)
    for folder in (DATA, PLUGINS, SHOTS):
        folder.mkdir(parents=True)
    plugin_dir = PLUGINS / EDITOR_ID
    shutil.copytree(plugin_source_root() / EDITOR_ID, plugin_dir)
    shutil.rmtree(plugin_dir / "models", ignore_errors=True)
    prefs_file = plugin_dir / "model_prefs.toml"
    result: dict = {"checks": [], "console_errors": [], "page_errors": [],
                    "http_failures": [], "deviations": [
                        "B-001 样本不在 test_papers/manifest.toml，用 A2 取证留存的同卷副本（沿 B 卡口径）",
                        "云端无账号：云 VLM 重认只取显性失败证据，真回填未实测",
                        "席位未就绪类重认失败只进 UI 显性提示（未动引擎）；识别/替换/存回失败才进失败清单（单测已钉）"]}
    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, detail or ""), flush=True)

    free_gb = shutil.disk_usage(ROOT).free / (1024 ** 3)
    check("磁盘自由≥8GB（GGUF 约 3.2GB）", free_gb >= 8, {"free_gb": round(free_gb, 1)})
    pre = engine_pids()
    check("MinerU 预态干净（无在跑引擎进程）", not pre, {"pids": pre})
    if pre:
        (WORK / "probe.toml").write_text(toml_io.dumps(result, default=str), encoding="utf-8")
        return 1
    port = free_port()
    base = "http://127.0.0.1:%d" % port
    server_log = WORK / "server.log"
    handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port",
         str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=os.environ.copy(), stdout=handle, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            if process.poll() is not None:
                raise RuntimeError("服务提前退出：" + server_log.read_text(encoding="utf-8", errors="replace")[:2000])
            try:
                if urllib.request.urlopen(base + "/healthz", timeout=1).status == 200: break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.2)
        else:
            raise RuntimeError("服务 60 秒未就绪")
        # ---------- registry：七链路目录＋自动默认座＋专科 blocked ----------
        registry = http_json(base, "/api/models/registry")
        entries = registry.get("entries") or []
        by_id = {str(e.get("id")): e for e in entries}
        result["hardware"] = registry.get("hardware") or {}
        check("registry 18 条目", len(entries) == 18, {"count": len(entries)})
        check("auto 默认座＝mineru_local/formula_pp_m",
              (registry.get("auto_seats") or {}) == {
                  "auto_image_seat": "mineru_local", "auto_text_formula_seat": "formula_pp_m"},
              registry.get("auto_seats"))
        check("MinerU 本地就绪", (by_id.get("mineru_local") or {}).get("state") == "ready")
        check("公式专科 blocked＋下一卡开",
              (by_id.get("formula_pp_m") or {}).get("state") == "blocked"
              and "下一卡开" in str((by_id.get("formula_pp_m") or {}).get("detail")))
        vlm0 = by_id.get("vlm_qwen") or {}
        fresh = vlm0.get("state") == "degraded" and vlm0.get("action") == "install_vlm"
        check("本地 VLM 初始态（未装 install_vlm 或已装显存门）",
              fresh or (vlm0.get("state") == "blocked" and "显存" in str(vlm0.get("detail"))),
              vlm0)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type in {"error", "warning"} else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.on("response", lambda r: result["http_failures"].append(
                "%s %s" % (r.status, r.url)) if r.status >= 400 else None)
            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=15000)
            item.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            expect(canvas.locator("#edRecognizeEngine")).to_have_value("auto", timeout=15000)
            title = canvas.locator('#edRecognizeEngine option[value="auto"]').get_attribute("title")
            check("识别自动档文案＝按卷型分流", "按卷型分流" in str(title), {"title": title})
            # ---------- ① 纯图卷 UI auto（后台整批回填）＋② 文字卷 UI auto ----------
            canvas.locator("#edBasketFile").set_input_files(str(SAMPLE_IMG))
            go = canvas.locator("#edBasketGo")
            expect(go).to_be_enabled(timeout=15000)
            go.click()
            expect(canvas.locator(".ed-batch-row").first).to_be_visible(timeout=180000)
            img_batch = str(canvas.locator(".ed-batch-row").first.get_attribute("data-batch"))
            canvas.locator("#edBasketFile").set_input_files(str(SAMPLE_TXT))
            expect(go).to_be_enabled(timeout=30000)
            go.click()
            rows, txt_batch, deadline = canvas.locator(".ed-batch-row"), "", time.time() + 180
            while time.time() < deadline and not txt_batch:
                txt_batch = next((str(rows.nth(i).get_attribute("data-batch"))
                                  for i in range(rows.count())
                                  if str(rows.nth(i).get_attribute("data-batch") or "")
                                  not in ("", img_batch)), "")
                if not txt_batch: page.wait_for_timeout(2000)
            result["img_batch"], result["txt_batch"] = img_batch, txt_batch
            check("两卷各立批次", bool(img_batch and txt_batch), {"img": img_batch, "txt": txt_batch})
            page.screenshot(path=str(SHOTS / "two-batches.png"))
            # ---------- 本地 VLM 真点安装（出网合规：界面当场真点）＋④ 自动分流默认 ----------
            canvas.locator("#epModelConfigList").click()
            view = canvas.locator("#edModelConfigModal")
            expect(view).to_be_visible(timeout=15000)
            vlm_row = canvas.locator(".ep-model-config-row", has_text="千问 Qwen2.5-VL")
            expect(vlm_row).to_be_visible(timeout=15000)
            check("硬件快照上页", "显存" in canvas.locator(".ep-model-config-hw-line").inner_text())
            if fresh:
                vlm_row.locator(".ep-model-config-act").click()
                expect(vlm_row.locator(".ep-model-config-act")).to_have_text("安装中…", timeout=20000)
                page.screenshot(path=str(SHOTS / "vlm-install-click.png"))
            auto_box = canvas.locator(".ep-model-config-auto-seats")
            expect(auto_box).to_be_visible(timeout=15000)
            selects = auto_box.locator("select")
            check("自动分流默认两下拉", selects.count() == 2, {"count": selects.count()})
            img_select, formula_select = selects.nth(0), selects.nth(1)
            check("纯图卷下拉只列就绪座＋自动",
                  [img_select.locator("option").nth(i).get_attribute("value") for i in
                   range(img_select.locator("option").count())] == ["auto", "mineru_local"])
            f_opts = formula_select.locator("option")
            check("公式座下拉只自动＋现默认未就绪标注", f_opts.count() == 1
                  and "现默认" in f_opts.first.inner_text() and "未就绪" in f_opts.first.inner_text(),
                  {"label": f_opts.first.inner_text()})
            page.screenshot(path=str(SHOTS / "config-auto-seats.png"))
            def wait_pref(want: str) -> str:
                deadline, val = time.time() + 15, ""
                while time.time() < deadline:
                    val = str(toml_io.load(prefs_file, {}).get("auto_image_seat") or "")
                    if val == want: break
                    page.wait_for_timeout(300)
                return val
            img_select.click()
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            check("键盘改纯图卷默认座落插件 prefs", wait_pref("mineru_local") == "mineru_local")
            img_select.select_option("auto")
            check("改回自动＝沿用 catalog 默认", wait_pref("auto") == "auto")
            check("data/ 全树无 model_prefs.toml", not list(DATA.rglob("model_prefs.toml")))
            canvas.locator("#edModelConfigBack").click()
            expect(view).to_be_hidden(timeout=10000)
            check("返回批次焦点还原入口按钮", canvas.locator("#epModelConfigList").evaluate(
                "node => node === document.activeElement"))
            # ---------- ⑤ 375px 配置视图不横向溢出 ----------
            page.set_viewport_size({"width": 375, "height": 720})
            canvas.locator("#epModelConfigList").click()
            expect(view).to_be_visible(timeout=10000)
            overflow = canvas.locator(".ep-model-config-card").evaluate(
                "node => node.scrollWidth - node.clientWidth")
            check("375px 配置视图不横向溢出", overflow <= 0, {"overflow_px": overflow})
            page.screenshot(path=str(SHOTS / "mobile-config.png"))
            canvas.locator("#edModelConfigBack").click()
            page.set_viewport_size({"width": 1440, "height": 900})
            # ---------- ② 文字卷组合路注记＋公式待核显性 ----------
            txt = wait_done(base, txt_batch, TXT_CAP)
            troute = txt.get("route") or {}
            result["txt_route"] = troute
            titems = txt.get("items") or []
            pending_count = sum(1 for it in titems if ((it.get("question") or {}).get("extensions")
                                or {}).get("org.jiuzhang.editor", {}).get("formula_pending"))
            tnote = str(troute.get("note") or "")
            check("文字卷 auto→组合路（text_layer＋auto_combo）",
                  troute.get("text_layer") is True and troute.get("mode") == "auto_combo",
                  {"mode": troute.get("mode"), "text_layer": troute.get("text_layer")})
            check("组合路注记：文字直取＋公式裁图交默认公式座", "组合路" in tnote
                  and "文字直取" in tnote and troute.get("auto_formula_seat") == "formula_pp_m",
                  {"note": tnote})
            check("公式待核显性（专科 blocked，正文不整题降级）",
                  pending_count >= 1 and "待核" in tnote and "下一卡开" in tnote,
                  {"pending_count": pending_count, "note": tnote})
            check("文字直取正文非空", all(len(str((it.get("question") or {}).get("stem") or "")) > 10
                                        for it in titems[:5]), {"items": len(titems)})
            page.screenshot(path=str(SHOTS / "combo-batch.png"))
            # ---------- 本地 VLM 安装收账＋显存门 blocked 披露 ----------
            deadline, last_step, step_shots, vstate, status = time.time() + INSTALL_CAP, "", 0, "", {}
            while time.time() < deadline:
                status = http_json(base, "/api/models/vlm/status")
                vstate, step = str(status.get("state") or ""), str(status.get("step") or "")
                if step != last_step:
                    last_step, step_shots = step, step_shots + 1
                    page.screenshot(path=str(SHOTS / ("vlm-install-step-%d.png" % step_shots)))
                if vstate in ("done", "error") or not fresh: break
                time.sleep(8)
            result["vlm_install"] = status
            if not fresh:
                result["deviations"].append("本地 VLM 已于前轮真点装成（run1-failed-claim 证据留存），本轮复验已装态，不重复下载")
            check("本地 VLM 安装收账（真点 done 或已装复验 idle）",
                  vstate == "done" or (not fresh and vstate == "idle"),
                  {"fresh": fresh, "state": vstate, "step": status.get("step")})
            registry = http_json(base, "/api/models/registry")
            vlm = {str(e.get("id")): e for e in registry.get("entries") or []}.get("vlm_qwen") or {}
            result["vlm_entry"], result["hardware"] = vlm, registry.get("hardware") or {}
            check("装后显存门 blocked＋人话披露（WMI 低估照念，不静默）",
                  vlm.get("state") == "blocked" and "不支持" in str(vlm.get("detail"))
                  and "显存" in str(vlm.get("detail")),
                  {"state": vlm.get("state"), "detail": vlm.get("detail")})
            health = vlm_setup.health()
            result["llama_cpp_health"], result["weights_ready"] = health, vlm_setup.weights_ready()
            check("llama-cpp import 体检＋GGUF 权重就绪",
                  health.get("ok") is True and result["weights_ready"] is True, health)
            canvas.locator("#epModelConfigList").click()
            expect(view).to_be_visible(timeout=15000)
            vlm_row = canvas.locator(".ep-model-config-row", has_text="千问 Qwen2.5-VL")
            expect(vlm_row.locator(".ep-model-config-state")).to_have_text("暂不可用", timeout=30000)
            check("VLM 行显存门披露上页",
                  "显存" in vlm_row.locator(".ep-model-config-detail").inner_text())
            page.screenshot(path=str(SHOTS / "vlm-gate-blocked.png"))
            canvas.locator("#edModelConfigBack").click()
            # ---------- ① 纯图卷整批回填收账 ----------
            img = wait_done(base, img_batch, IMG_CAP)
            iroute = img.get("route") or {}
            result["img_route"] = iroute
            iitems = img.get("items") or []
            inode = str(iroute.get("note") or "")
            m = re.search(r"(\d+)/(\d+) 道(?:回填成功|回来了)", inode)
            filled = int(m.group(1)) if m else 0
            check("纯图卷 auto→默认整题座 MinerU 本地（分流字段）",
                  iroute.get("text_layer") is False and iroute.get("recognize_engine") == "auto"
                  and iroute.get("auto_image_seat") == "mineru_local",
                  {"auto_image_seat": iroute.get("auto_image_seat"), "mode": iroute.get("mode")})
            check("纯图卷注记实证＋整批回填账",
                  "自动分流（纯图卷）" in inode and "默认座「MinerU·本地」" in inode
                  and filled >= max(1, len(iitems) // 2),
                  {"filled": filled, "total": len(iitems), "note": inode})
            page.reload(wait_until="networkidle")
            page.locator(".ws-plugin-item", has_text="录题工作台").first.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            canvas.locator(".ed-batch-row[data-batch='%s'] .ed-batch-open" % img_batch).click()
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SHOTS / "fill-result.png"))
            # ---------- ③ 审核重认：云显性失败／VLM 门披露／MinerU 真回填 ----------
            bar = canvas.locator(".ed-reidentify").first
            expect(bar).to_be_visible(timeout=20000)
            pid = str(bar.get_attribute("data-pending-id"))
            result["reidentify_pid"] = pid
            bar.locator(".ed-reidentify-btn", has_text="整题重认").click()
            seats = canvas.locator(".ed-reidentify-seats").first
            expect(seats).to_be_visible(timeout=20000)
            page.screenshot(path=str(SHOTS / "reidentify-seats.png"))
            note = bar.locator(".ed-reidentify-note")
            def open_whole_seats() -> None:
                if seats.is_hidden():
                    bar.locator(".ed-reidentify-btn", has_text="整题重认").click()
                expect(seats).to_be_visible(timeout=20000)
            seats.locator(".ed-reidentify-seat", has_text="云端视觉").click()
            expect(note).to_have_class(re.compile("is-error"), timeout=60000)
            cloud_text = note.inner_text()
            check("云 VLM 无账号＝显性失败不偷换", "指派" in cloud_text, {"note": cloud_text})
            page.screenshot(path=str(SHOTS / "reidentify-cloud-fail.png"))
            open_whole_seats()
            seats.locator(".ed-reidentify-seat", has_text="千问 Qwen2.5-VL").click()
            expect(note).to_have_class(re.compile("is-error"), timeout=60000)
            vlm_text = note.inner_text()
            check("本地 VLM 显存门＝显性披露（未就绪照念）",
                  "未就绪" in vlm_text and "显存" in vlm_text, {"note": vlm_text})
            page.screenshot(path=str(SHOTS / "reidentify-vlm-gate.png"))
            lroute = http_json(base, "/api/pending/batches/%s/questions" % img_batch).get("route") or {}
            result["ledger_steps"] = [str(f.get("step") or "") for f in lroute.get("failures") or []]
            check("重认失败不偷换（批次路由仍 mineru_local 完成态）",
                  lroute.get("mode") == "mineru_local" and lroute.get("done") is True,
                  {"mode": lroute.get("mode"), "steps": result["ledger_steps"]})
            def wait_note(shot: str) -> str:
                deadline = time.time() + SEAT_CAP
                while time.time() < deadline:
                    if "is-error" in str(note.get_attribute("class") or ""):
                        return "FAIL:" + note.inner_text()
                    if not note.inner_text().strip():
                        page.screenshot(path=str(SHOTS / shot))
                        return "OK"
                    page.wait_for_timeout(2000)
                return "TIMEOUT"
            def run_seat(seat_name: str, shot: str) -> str:
                open_whole_seats()
                seats.locator(".ed-reidentify-seat", has_text=seat_name).click()
                expect(bar).to_have_attribute("aria-busy", "true", timeout=10000)
                return wait_note(shot)
            # 先公式后整题：整题重认经 merge_local 会丢 formula_boxes，坐标证据须先取
            span_rows = http_json(base, "/api/pending/reidentify/spans?pending_id=" + pid).get("spans") or []
            result["formula_spans"] = span_rows[:5]
            fbtn = bar.locator(".ed-reidentify-btn", has_text="公式重认")
            if span_rows:
                expect(fbtn).to_be_visible(timeout=15000)
                check("公式坐标上页（MinerU 公式块）", "块" in fbtn.inner_text()
                      and any(s.get("origin") == "mineru" for s in span_rows),
                      {"count": len(span_rows), "origins": [s.get("origin") for s in span_rows[:5]]})
                fbtn.click()
                span_line = canvas.locator(".ed-reidentify-span").first
                expect(span_line).to_be_visible(timeout=10000)
                page.screenshot(path=str(SHOTS / "formula-spans.png"))
                span_line.locator(".ed-reidentify-btn", has_text="重认此块").click()
                expect(seats).to_be_visible(timeout=20000)
                seats.locator(".ed-reidentify-seat", has_text="MinerU·本地").click()
                expect(bar).to_have_attribute("aria-busy", "true", timeout=10000)
                formula_outcome = wait_note("formula-backfill.png")
                check("公式裁块重认真回填（同张题图按坐标裁）",
                      formula_outcome == "OK", {"outcome": formula_outcome})
            else:
                check("无坐标只给题级（公式重认隐藏）", fbtn.is_hidden(), {"spans": 0})
                result["deviations"].append("首题无公式坐标，公式裁块重认未取到真回填证据")
            stem_before = str(((iitems[0].get("question") or {}).get("stem") or ""))
            whole = run_seat("MinerU·本地", "reidentify-backfill.png")
            after = http_json(base, "/api/pending/batches/%s/questions" % img_batch).get("items") or []
            stem_after = str(((after[0].get("question") or {}).get("stem") or "")) if after else ""
            result["reidentify_whole"] = {"outcome": whole, "stem_before": stem_before[:120],
                                          "stem_after": stem_after[:120]}
            check("MinerU 本地整题重认真回填（原位替换）",
                  whole == "OK" and len(stem_after) > 10, result["reidentify_whole"])
            page.set_viewport_size({"width": 375, "height": 720})
            overflow = bar.evaluate("node => node.scrollWidth - node.clientWidth")
            check("375px 重认工具行不横向溢出", overflow <= 0, {"overflow_px": overflow})
            page.screenshot(path=str(SHOTS / "mobile-reidentify.png"))
            page.set_viewport_size({"width": 1440, "height": 900})
            page.locator("#wsOpenCtx").click()
            panel = page.frame_locator(".ws-context-frame")
            panel.locator("#epBackList").click()
            page.wait_for_timeout(1500)
            badge = canvas.locator(".ed-batch-row[data-batch='%s'] .ed-batch-failbadge" % txt_batch)
            expect(badge).to_be_visible(timeout=20000)
            badge.click()
            expect(canvas.locator(".ed-fail-item").first).to_be_visible(timeout=15000)
            page.screenshot(path=str(SHOTS / "failure-list.png"))
            check("失败清单 UI 可见（公式裁图失败可重试）", True)
            browser.close()
        # ---------- 三查＋页面健康 ----------
        counts = {"fetch(": 0, "parent.document": 0, "localStorage": 0}
        for script in sorted((plugin_dir / "dist").glob("*.js")):
            text = script.read_text(encoding="utf-8", errors="replace")
            counts = {k: v + text.count(k) for k, v in counts.items()}
        check("三查 fetch(/parent.document/localStorage=0",
              all(v == 0 for v in counts.values()), counts)
        check("页面零 JS 异常", not result["page_errors"], result["page_errors"][:5])
        check("UI 阶段零 HTTP 失败", not result["http_failures"], result["http_failures"][:5])
    except Exception as error:  # noqa: BLE001 - 探针把现场带回去
        result["error"] = "%s: %s" % (type(error).__name__, error)
        print("ERROR", result["error"], flush=True)
    finally:
        result["mineru_kill"] = kill_service_by_log(server_log)
        try:
            vlm_service.stop()
        except Exception:  # noqa: BLE001 - 收口尽力而为
            pass
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
        handle.close()
        time.sleep(1)
        check("收口服务端口复验关闭", port_closed(port), {"port": port})
        for pid in engine_pids():
            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True, timeout=30)
        time.sleep(1)
        orphans = engine_pids()
        check("mineru-api 孤儿零", not orphans, {"pids": orphans})
    failed = [c for c in result["checks"] if not c["ok"]]
    result["ok"] = not failed and not result.get("error")
    result["elapsed_s"] = round(time.time() - started, 1)
    (WORK / "probe.toml").write_text(toml_io.dumps(result, default=str), encoding="utf-8")
    print("ok=%s checks=%d failed=%d elapsed=%.1fs" % (
        result["ok"], len(result["checks"]), len(failed), result["elapsed_s"]), flush=True)
    print("probe:", WORK / "probe.toml", flush=True)
    return 0 if result["ok"] else 1
if __name__ == "__main__":
    raise SystemExit(main())