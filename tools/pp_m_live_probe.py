# -*- coding: utf-8 -*-
"""PP-FormulaNet·M 单座安装＋推理真机探针（2.22.0 卡§4）。

用法：``.venv/Scripts/python.exe tools/pp_m_live_probe.py [tag]``

隔离：两仓 git archive HEAD 解包副本（禁抄工作树）＋独立 JZO_DATA_DIR／
JZO_PLUGINS_DIR＋动态空闲端口＋每次随机令牌；服务 cwd＝副本，PROJECT_ROOT
锚副本根，engines/formula 落副本内——不碰用户 data/、真机 engines/ 与 65496。
出网只由配置中心【安装】点击＋确认弹窗 accept 发起（modelscope 主源，596MB）。
停跑令合规：prefs auto_image_seat=cloud_vision（未指派＝显性失败零引擎），
组合路无坐标整题兜底绝不触 MinerU 本地 CPU／VLM CPU；偏离登记 probe.toml。

判据：
1. 未安装三态：PP-M 行未就绪＋【安装】钮（含 375px）；
2. 安装真证：真点→596MB 弹窗 accept→POST 真请求→双件 sha256 逐字落地→就绪＋【卸载】钮；
3. 组合文字卷一卷真路：combo_pp_m 显式选→文字直取＋公式裁图 PP-M 原位回填；
4. 重认微批 3–5 块真路：公式重认→选 PP-M→原位替换存回；整题选 PP-M 显性拒绝；
5. 卸载真证：【卸载】确认→engines/formula 删净→回到未就绪＋【安装】钮；
6. 零 JS 异常、零 HTTP 失败、三查 0、收口端口闭＋孤儿零。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402

import hashlib
import io
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PLUGINS_REPO = ROOT.parent / "jiuzhang-plugins"
EDITOR_ID = "org.jiuzhang.editor"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
SAMPLE_TXT = ROOT / "test_papers" / "A3_2027【绵阳一诊】.pdf"
INSTALL_CAP, COMBO_CAP, SEAT_CAP = 900, 600, 180
WEIGHTS = {
    "pp_formulanet_plus_m.onnx": (593908338,
        "52afa60ff51ad66cd7840a74188a058fe99081e617d3bd780117a2d67d94f50d"),
    "pp_formulanet_plus_m_inference.yml": (2244564,
        "87b5f3d7f2b2fe553627d77b37f496608ca150ebd0ef62d362591edca47b5538"),
}


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def port_closed(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def git_archive(repo: Path, dest: Path) -> str:
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=30).stdout.strip()
    blob = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", "HEAD"],
                          capture_output=True, timeout=180).stdout
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        tar.extractall(dest, filter="data")
    return head


def http_json(base: str, path: str, token: str = "") -> dict:
    request = urllib.request.Request(base + path,
                                     headers={"X-JZO-Token": token} if token else {})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    started = time.time()
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    work = ROOT / ".system_generated" / "pp-m-live" / tag
    if work.exists():
        shutil.rmtree(work)
    shots = work / "shots"
    shots.mkdir(parents=True)
    op_dir, plugins_src = work / "operator", work / "plugins-src"
    op_head = git_archive(ROOT, op_dir)
    pl_head = git_archive(PLUGINS_REPO, plugins_src)
    plugin_dir = plugins_src / "src" / EDITOR_ID
    toml_io.write(plugin_dir / "model_prefs.toml", {
        "disabled": [], "default_layout": "auto", "default_recognize": "auto",
        "auto_image_seat": "cloud_vision", "auto_text_formula_seat": "auto"})
    engines_formula = op_dir / "engines" / "formula"

    token = "probe-" + secrets.token_hex(8)
    port = free_port()
    base = "http://127.0.0.1:%d" % port
    env = os.environ.copy()
    env.update({"JZO_DATA_DIR": str(work / "data"),
                "JZO_PLUGINS_DIR": str(plugins_src / "src"),
                "JZO_LOCAL_TOKEN": token, "JZO_RESTART_DISABLED": "1",
                "JZO_POOL_ADMIT_DISABLED": "1"})
    server_log = work / "server.log"
    handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = None
    result: dict = {"tag": tag, "base": base, "operator_head": op_head,
                    "plugins_head": pl_head, "checks": [], "console_errors": [],
                    "page_errors": [], "http_failures": [], "install_requests": [],
                    "dialogs": [], "deviations": [
                        "prefs auto_image_seat=cloud_vision（未指派）：组合路无坐标整题兜底走显性失败，"
                        "避 MinerU 本地 CPU 停跑令；公式步真跑不受影响",
                        "原串批次经自动分流默认公式座（PP-M 未装）显性标待核产出，先于安装跑——"
                        "引擎下拉只列就绪且启用座，未装座无从直选；run2 选 ai 超时即此因"]}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, detail or ""), flush=True)

    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "info", "--no-server-header"],
            cwd=str(op_dir), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)
        deadline = time.time() + 60
        while time.time() < deadline:
            if process.poll() is not None:
                raise RuntimeError("服务提前退出：" + server_log.read_text(
                    encoding="utf-8", errors="replace")[:2000])
            try:
                if urllib.request.urlopen(base + "/healthz", timeout=1).status == 200:
                    break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.2)
        else:
            raise RuntimeError("服务 60 秒未就绪")
        check("隔离副本起服务（git archive HEAD，非工作树）", True,
              {"operator": op_head[:8], "plugins": pl_head[:8]})
        registry = http_json(base, "/api/models/registry")
        by_id = {str(e.get("id")): e for e in registry.get("entries") or []}
        pp = by_id.get("formula_pp_m") or {}
        check("初始 PP-M 未就绪＋install_formula（副本无权重）",
              pp.get("state") == "degraded" and pp.get("action") == "install_formula", pp)
        check("其余五座口径不动（三专科 blocked／两 VLM 硬件门）",
              all((by_id.get(k) or {}).get("state") == "blocked"
                  for k in ("formula_pp_l", "formula_p2t", "formula_texify"))
              and all((by_id.get(k) or {}).get("rule") == "vram_gate"
                      for k in ("vlm_intern", "vlm_minicpm")),
              {k: (by_id.get(k) or {}).get("state") for k in
               ("formula_pp_l", "formula_p2t", "formula_texify", "vlm_intern", "vlm_minicpm")})
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type in {"error", "warning"} else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.on("response", lambda r: result["http_failures"].append(
                "%s %s" % (r.status, r.url)) if r.status >= 400 else None)
            page.on("request", lambda r: result["install_requests"].append(r.url)
                    if "/api/models/formula/install" in r.url else None)
            page.on("dialog", lambda d: (result["dialogs"].append(d.message), d.accept()))
            page.goto(base + "/workspace", wait_until="networkidle")
            page.locator(".ws-plugin-item", has_text="录题工作台").first.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            # ---------- ① 未安装三态＋375px ----------
            canvas.locator("#epModelConfigList").click()
            expect(canvas.locator(".ep-mt-table").first).to_be_visible(timeout=15000)
            row = canvas.locator(".ep-mt-row", has_text="PP-FormulaNet·M")
            expect(row.locator(".ep-mt-badge")).to_have_text("未就绪", timeout=15000)
            check("未安装行：未就绪＋【安装】钮",
                  row.locator(".ep-mt-act", has_text="安装").count() == 1)
            page.screenshot(path=str(shots / "01-not-installed.png"))
            page.set_viewport_size({"width": 375, "height": 720})
            overflow = canvas.locator(".ep-mt-table").first.evaluate(
                "node => node.scrollWidth - node.clientWidth")
            check("375px 模型表不横向溢出（未安装态）", overflow <= 0, {"overflow_px": overflow})
            page.screenshot(path=str(shots / "02-mobile-not-installed.png"))
            page.set_viewport_size({"width": 1440, "height": 900})
            canvas.locator("#edModelConfigBack").click()
            # ---------- ①b 原串批次：自动文字卷＋默认公式座 PP-M 未装 → 公式显性标待核、正文留文字直取原串 ----------
            # 下拉只列就绪且启用座（ui_intake applyRegistry），未装座选不到；
            # 原串批次只能经自动分流的默认公式座闸口产出，故放在安装之前。
            canvas.locator("#edRecognizeEngine").select_option("auto")
            canvas.locator("#edBasketFile").set_input_files(str(SAMPLE_TXT))
            go = canvas.locator("#edBasketGo")
            expect(go).to_be_enabled(timeout=30000)
            go.click()
            expect(canvas.locator(".ed-batch-row").first).to_be_visible(timeout=180000)
            raw_batch = str(canvas.locator(".ed-batch-row").first.get_attribute("data-batch"))
            result["raw_batch"] = raw_batch
            check("原串批次立起（自动文字卷，PP-M 未装）", bool(raw_batch), {"raw": raw_batch})
            raw_detail: dict = {}
            deadline = time.time() + COMBO_CAP
            while time.time() < deadline:
                raw_detail = http_json(base, "/api/pending/batches/%s/questions" % raw_batch)
                if (raw_detail.get("route") or {}).get("done"):
                    break
                time.sleep(5)
            raw_route = raw_detail.get("route") or {}
            check("公式座未装显性标待核（零 MinerU/VLM 引擎、零出网）",
                  any("未就绪" in str(f.get("reason")) for f in raw_route.get("failures") or []),
                  {"failures": [str(f.get("reason"))[:80] for f in raw_route.get("failures") or []][:3]})
            raw_note = str(raw_route.get("note") or "")
            check("原串批次公式显性标待核零回填（正文留文字直取）",
                  "0 道原位回填" in raw_note and "标待核" in raw_note,
                  {"note": raw_note[:300]})
            page.screenshot(path=str(shots / "02b-raw-batch.png"))
            canvas.locator("#epModelConfigList").click()
            expect(canvas.locator(".ep-mt-table").first).to_be_visible(timeout=15000)
            # ---------- ② 安装真证 ----------
            row.locator(".ep-mt-act", has_text="安装").click()
            page.wait_for_timeout(500)
            check("596MB 成本确认弹窗已摆并 accept",
                  bool(result["dialogs"]) and "596MB" in result["dialogs"][-1],
                  result["dialogs"][-1:])
            status: dict = {}
            deadline = time.time() + INSTALL_CAP
            while time.time() < deadline:
                status = http_json(base, "/api/models/formula/status", token)
                if status.get("state") in ("done", "error"):
                    break
                time.sleep(3)
            result["install_status"] = status
            check("安装请求确由界面点击发起", bool(result["install_requests"]),
                  result["install_requests"])
            check("安装收口 done", status.get("state") == "done", status)
            models_dir = engines_formula / "models"
            landed = []
            for name, (size, sha) in WEIGHTS.items():
                path = models_dir / name
                got = sha256_of(path) if path.is_file() else ""
                landed.append({"name": name, "bytes": path.stat().st_size if path.is_file() else 0,
                               "sha256": got, "match": got == sha})
            result["weights"] = landed
            check("双件权重落地 sha256 逐字一致", all(w["match"] for w in landed), landed)
            expect(row.locator(".ep-mt-badge")).to_have_text("就绪", timeout=30000)
            check("已安装行：就绪＋【卸载】钮",
                  row.locator(".ep-mt-act", has_text="卸载").count() == 1)
            page.screenshot(path=str(shots / "03-installed.png"))
            page.set_viewport_size({"width": 375, "height": 720})
            overflow = canvas.locator(".ep-mt-table").first.evaluate(
                "node => node.scrollWidth - node.clientWidth")
            check("375px 模型表不横向溢出（已安装态）", overflow <= 0, {"overflow_px": overflow})
            page.screenshot(path=str(shots / "04-mobile-installed.png"))
            page.set_viewport_size({"width": 1440, "height": 900})
            canvas.locator("#edModelConfigBack").click()
            # ---------- ③ 组合文字卷一卷真路 ----------
            canvas.locator("#edRecognizeEngine").select_option("combo_pp_m")
            canvas.locator("#edBasketFile").set_input_files(str(SAMPLE_TXT))
            expect(go).to_be_enabled(timeout=30000)
            go.click()
            rows = canvas.locator(".ed-batch-row")
            batch, deadline = "", time.time() + 180
            while time.time() < deadline and not batch:
                batch = next((str(rows.nth(i).get_attribute("data-batch"))
                              for i in range(rows.count())
                              if str(rows.nth(i).get_attribute("data-batch") or "")
                              not in ("", raw_batch)), "")
                if not batch:
                    page.wait_for_timeout(2000)
            result["batch"] = batch
            check("组合路第二卷立批次", bool(batch), {"batch": batch})
            detail: dict = {}
            deadline = time.time() + COMBO_CAP
            while time.time() < deadline:
                detail = http_json(base, "/api/pending/batches/%s/questions" % batch)
                if (detail.get("route") or {}).get("done"):
                    break
                time.sleep(5)
            route = detail.get("route") or {}
            items = detail.get("items") or []
            result["combo_route"] = route
            note = str(route.get("note") or "")
            check("组合路 combo_pp_m 文字卷真路（text_layer＋mode）",
                  route.get("text_layer") is True and route.get("mode") == "combo_pp_m",
                  {"mode": route.get("mode"), "text_layer": route.get("text_layer")})
            check("组合路注记：文字直取＋公式裁图交 PP-M", "组合路" in note and "文字直取" in note,
                  {"note": note[:300]})
            filled = len(re.findall(r"\$\$?[^$]+\$\$?", " ".join(
                str((it.get("question") or {}).get("stem") or "") for it in items)))
            result["combo_filled_spans"] = filled
            backfilled = re.search(r"(\d+) 道原位回填", note)
            check("公式原位回填有实证（路由注记 N 道原位回填 ≥1）",
                  bool(backfilled) and int(backfilled.group(1)) >= 1,
                  {"backfilled_items": backfilled.group(1) if backfilled else None,
                   "dollar_spans": filled, "items": len(items)})
            check("文字直取正文非空", all(len(str((it.get("question") or {}).get("stem") or "")) > 10
                                        for it in items[:5]), {"items": len(items)})
            fallback = [f for f in route.get("failures") or [] if "自动分流" in str(f.get("step"))]
            check("无坐标整题兜底显性失败（云未指派，零 MinerU/VLM 引擎）",
                  not fallback or all("未就绪" in str(f.get("reason")) for f in fallback),
                  {"fallback_failures": len(fallback)})
            page.screenshot(path=str(shots / "05-combo-batch.png"))
            # ---------- ④ 重认微批 3–5 块真路（原串题面，D12 原位替换） ----------
            canvas.locator(".ed-batch-row[data-batch='%s'] .ed-batch-open" % raw_batch).click()
            page.wait_for_timeout(2500)
            bars = canvas.locator(".ed-reidentify")
            expect(bars.first).to_be_visible(timeout=20000)
            targets: list[dict] = []
            for i in range(min(bars.count(), 12)):
                pid = str(bars.nth(i).get_attribute("data-pending-id") or "")
                spans = http_json(base, "/api/pending/reidentify/spans?pending_id=" + pid).get("spans") or []
                if spans:
                    targets.append({"pid": pid, "index": 0, "preview": spans[0].get("preview")})
                if len(targets) >= 5:
                    break
            result["reidentify_targets"] = targets
            check("公式坐标上页（文字层 span，≥3 题可供微批）", len(targets) >= 3,
                  {"targets": len(targets)})
            done = 0
            for target in targets:
                pid = target["pid"]
                bar = canvas.locator(".ed-reidentify[data-pending-id='%s']" % pid)
                before = next((str((it.get("question") or {}).get("stem") or "")
                               for it in raw_detail.get("items") or []
                               if str(it.get("id")) == pid), "")
                fbtn = bar.locator(".ed-reidentify-btn", has_text="公式重认")
                expect(fbtn).to_be_visible(timeout=15000)
                fbtn.click()
                span_line = bar.locator(".ed-reidentify-span").nth(target["index"])
                expect(span_line).to_be_visible(timeout=10000)
                span_line.locator(".ed-reidentify-btn", has_text="重认此块").click()
                seats = bar.locator(".ed-reidentify-seats")
                expect(seats).to_be_visible(timeout=20000)
                seats.locator(".ed-reidentify-seat", has_text="PP-FormulaNet·M").click()
                note_el = bar.locator(".ed-reidentify-note")
                outcome, deadline = "TIMEOUT", time.time() + SEAT_CAP
                while time.time() < deadline:
                    if "is-error" in str(note_el.get_attribute("class") or ""):
                        outcome = "FAIL:" + note_el.inner_text()
                        break
                    if not note_el.inner_text().strip():
                        outcome = "OK"
                        break
                    page.wait_for_timeout(1000)
                after_items = http_json(base, "/api/pending/batches/%s/questions" % raw_batch).get("items") or []
                after = next((str((it.get("question") or {}).get("stem") or "")
                              for it in after_items if str(it.get("id")) == pid), "")
                target.update({"outcome": outcome, "before": before[:120], "after": after[:120]})
                if outcome == "OK" and after != before:
                    done += 1
                if done == 1:
                    page.screenshot(path=str(shots / "06-reidentify-formula.png"))
            result["reidentify_filled"] = done
            check("重认微批 3–5 块真跑原位替换", done >= 3,
                  {"done": done, "targets": targets})
            # ---------- ④b 整题选 PP-M 显性拒绝 ----------
            bar = canvas.locator(".ed-reidentify[data-pending-id='%s']" % targets[0]["pid"])
            bar.locator(".ed-reidentify-btn", has_text="整题重认").click()
            seats = bar.locator(".ed-reidentify-seats")
            expect(seats).to_be_visible(timeout=20000)
            seats.locator(".ed-reidentify-seat", has_text="PP-FormulaNet·M").click()
            note_el = bar.locator(".ed-reidentify-note")
            expect(note_el).to_have_class(re.compile("is-error"), timeout=60000)
            refused = note_el.inner_text()
            check("整题重认选 PP-M 显性拒绝（公式专科座只认裁图）",
                  "公式专科座" in refused and "整题座" in refused, {"note": refused})
            page.screenshot(path=str(shots / "07-whole-refused.png"))
            page.set_viewport_size({"width": 375, "height": 720})
            overflow = bar.evaluate("node => node.scrollWidth - node.clientWidth")
            check("375px 重认工具行不横向溢出", overflow <= 0, {"overflow_px": overflow})
            page.screenshot(path=str(shots / "08-mobile-reidentify.png"))
            page.set_viewport_size({"width": 1440, "height": 900})
            # ---------- ⑤ 卸载真证（reload 回批次视图，模型配置入口才可见） ----------
            page.reload(wait_until="networkidle")
            page.locator(".ws-plugin-item", has_text="录题工作台").first.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            canvas.locator("#epModelConfigList").click()
            expect(canvas.locator(".ep-mt-table").first).to_be_visible(timeout=15000)
            row = canvas.locator(".ep-mt-row", has_text="PP-FormulaNet·M")
            row.locator(".ep-mt-act", has_text="卸载").click()
            page.wait_for_timeout(500)
            check("卸载确认弹窗已摆并 accept", bool(result["dialogs"]), result["dialogs"][-1:])
            deadline = time.time() + 60
            while time.time() < deadline and engines_formula.exists():
                time.sleep(1)
            check("卸载删净 engines/formula（副本内）", not engines_formula.exists())
            expect(row.locator(".ep-mt-badge")).to_have_text("未就绪", timeout=30000)
            check("卸载后回到未就绪＋【安装】钮",
                  row.locator(".ep-mt-act", has_text="安装").count() == 1)
            page.screenshot(path=str(shots / "09-uninstalled.png"))
            browser.close()
        counts = {"fetch(": 0, "parent.document": 0, "localStorage": 0}
        for script in sorted((plugin_dir / "dist").glob("*.js")):
            text = script.read_text(encoding="utf-8", errors="replace")
            counts = {k: v + text.count(k) for k, v in counts.items()}
        check("三查 fetch(/parent.document/localStorage=0",
              all(v == 0 for v in counts.values()), counts)
        check("页面零 JS 异常", not result["page_errors"], result["page_errors"][:5])
        check("全程零 HTTP 失败", not result["http_failures"], result["http_failures"][:5])
    except Exception as error:  # noqa: BLE001 - 探针把现场带回去
        result["error"] = "%s: %s" % (type(error).__name__, error)
        print("ERROR", result["error"], flush=True)
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
        handle.close()
        time.sleep(1)
        check("收口服务端口复验关闭", port_closed(port), {"port": port})
        out = subprocess.run(["wmic", "process", "where", "name='python.exe'",
                              "get", "ProcessId,CommandLine", "/FORMAT:CSV"],
                             capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
        orphans = [line.rsplit(",", 1)[-1].strip() for line in out.splitlines()
                   if str(work) in line and line.strip()]
        for pid in orphans:
            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True, timeout=30)
        check("副本服务孤儿零", not orphans, {"pids": orphans})
    failed = [c for c in result["checks"] if not c["ok"]]
    result["ok"] = not failed and not result.get("error")
    result["elapsed_s"] = round(time.time() - started, 1)
    (work / "probe.toml").write_text(toml_io.dumps(result, default=str), encoding="utf-8")
    print("ok=%s checks=%d failed=%d elapsed=%.1fs" % (
        result["ok"], len(result["checks"]), len(failed), result["elapsed_s"]), flush=True)
    print("probe:", work / "probe.toml", flush=True)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())