# -*- coding: utf-8 -*-
"""MinerU 本地逐题接线 e2e 探针（任务卡 §5）：隔离服＋真点＋3 题回填＋负向显性＋收口零孤儿。

动线：模型配置页确认就绪（未装则真点【安装本地 MinerU】并轮询到 done）→
UI 投卷扫描（auto，本地切题不出网）→ UI 下拉真选 MinerU·本地 → 进程内对前 3 题
跑真 fill_batch（真服务＋真引擎＋真回填，权重已预取故无下载，出网铁律不触发；
权重缺失则改走 UI 真点整批解析，懒下载发生在用户点击的作业里）→ 断言 filled≥2
且≥1 题含 $...$ 公式 → 负向：停服＋ temporarily 挪开服务入口 → 再选本地＝显性
失败清单、不偷换 → 收口显式 stop＋端口复验＋孤儿清点。

偏离如实记 probe.toml：B-001 样本不在 test_papers/manifest.toml（卡口径与样本库
现状不一致），用 A2 取证留存的同卷副本；3 题子集由探针进程内驱动（无逐批重识别
端点）；负向用挪开 mineru-api.exe 制造真起服失败（懒起服设计下单纯 stop 会被复用）。

运行：.venv/Scripts/python.exe tools/mineru_local_probe.py
"""
from __future__ import annotations

import asyncio
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".system_generated" / "mineru-local" / "run1"
DATA = WORK / "data"
PLUGINS = WORK / "plugins"
SHOTS = WORK / "shots"
for _folder in (DATA, PLUGINS, SHOTS):
    _folder.mkdir(parents=True, exist_ok=True)
TOKEN = "probe-" + secrets.token_hex(8)
# 隔离 env 必须先于任何 app 导入：进程内数据层与服务进程共用同一隔离库。
os.environ["JZO_DATA_DIR"] = str(DATA)
os.environ["JZO_PLUGINS_DIR"] = str(PLUGINS)
os.environ["JZO_LOCAL_TOKEN"] = TOKEN
os.environ["JZO_RESTART_DISABLED"] = "1"
os.environ["JZO_POOL_ADMIT_DISABLED"] = "1"
sys.path.insert(0, str(ROOT))

from app.core import toml_io, wire  # noqa: E402
from app.core.config import plugin_source_root  # noqa: E402
from app.core.ingest import mineru_setup  # noqa: E402
from app.core.ingest.recognize import mineru_service  # noqa: E402
from app.core.ingest.recognize import router as recognize_router  # noqa: E402
from app.core.ingest.route import save_route  # noqa: E402
from app.core.pending import service as pending_service  # noqa: E402

from playwright.sync_api import expect, sync_playwright  # noqa: E402

EDITOR_ID = "org.jiuzhang.editor"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
SAMPLE = (ROOT / ".system_generated" / "a2_image_ingest" / "ev1" / "data"
          / "pending_sources"
          / "20261118-193020_220dac_东北师大附中2023-2024高一上学期第一次月考试题.pdf")
MAX_INSTALL = 2400
MAX_PARSE = 2400
FORMULA = re.compile(r"\$[^$\n]+\$")


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


def batch_detail(base: str, batch_id: str) -> dict:
    return http_json(base, "/api/pending/batches/%s/questions" % batch_id)


def wait_route_done(base: str, batch_id: str, cap: int) -> dict:
    deadline = time.time() + cap
    detail: dict = {}
    while time.time() < deadline:
        detail = batch_detail(base, batch_id)
        if (detail.get("route") or {}).get("done"):
            return detail
        time.sleep(3)
    return detail


def fill_local(batch_id: str, items: list[dict], route: dict) -> dict:
    """进程内真调度：真服务＋真引擎＋真回填，进度照生产口径写回批次。

    Playwright sync 在主线程养着事件循环，asyncio.run 必须另起线程跑。
    """
    report = {"total": len(items), "bad": len(items), "rate": 1.0,
              "bad_indexes": list(range(len(items)))}

    def progress(snapshot: dict) -> None:
        save_route(pending_service, batch_id, snapshot)

    box: dict = {}

    def worker() -> None:
        try:
            box["route"] = asyncio.run(recognize_router.fill_batch(
                batch_id, items, "mineru_local", report, route, progress))
        except BaseException as exc:  # noqa: BLE001 - 带回主线程显性化
            box["error"] = exc

    thread = threading.Thread(target=worker, name="probe-fill-local")
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    save_route(pending_service, batch_id, box["route"])
    return box["route"]


def parse_fill(note: str) -> tuple[int, int]:
    """从路由注记认回填账：全成功与部分成功两种口径都认得。"""
    m = re.search(r"(\d+)/(\d+) 道回填成功", note)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"只有 (\d+)/(\d+) 道回来了", note)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def formula_evidence(items: list[dict], indexes: list[int]) -> dict:
    stems = [str((items[i].get("question") or {}).get("stem") or "")
             for i in indexes if i < len(items)]
    hits = [i for i, stem in zip(indexes, stems) if FORMULA.search(stem)]
    return {"stems": stems, "formula_indexes": hits,
            "nonempty": [len(stem.strip()) for stem in stems]}


def kill_service_by_log(server_log: Path) -> dict:
    """路径 B 服务归服务进程：从日志认端口→netstat 认 PID→点杀（禁 /IM）。"""
    text = server_log.read_text(encoding="utf-8", errors="replace")
    ports = re.findall(r"端口 (\d+)", text)
    if not ports:
        return {"killed": False, "reason": "日志里没有服务端口"}
    port = int(ports[-1])
    listing = subprocess.run(["netstat", "-ano"], capture_output=True,
                             timeout=30).stdout.decode("utf-8", "replace")
    pid = ""
    for line in listing.splitlines():
        if "127.0.0.1:%d" % port in line and "LISTENING" in line:
            pid = line.split()[-1]
            break
    if not pid:
        return {"killed": False, "port": port, "reason": "端口没有监听进程"}
    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"],
                   capture_output=True, timeout=30)
    return {"killed": True, "port": port, "pid": pid}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    started = time.time()
    result: dict = {"sample": SAMPLE.name, "checks": [], "deviations": [
        "B-001 样本不在 test_papers/manifest.toml，用 A2 取证留存的同卷副本",
        "3 题子集由探针进程内驱动真 fill_batch（无逐批重识别端点）",
        "负向用挪开 mineru-api.exe 制造真起服失败（懒起服下单纯 stop 会被复用）",
    ]}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, detail or ""),
              flush=True)

    free_gb = shutil.disk_usage(ROOT).free / (1024 ** 3)
    check("磁盘自由≥8GB", free_gb >= 8, {"free_gb": round(free_gb, 1)})
    if free_gb < 8:
        return finish(result, started, 1)
    plugin_dir = PLUGINS / EDITOR_ID
    if not plugin_dir.exists():
        shutil.copytree(plugin_source_root() / EDITOR_ID, plugin_dir)
        shutil.rmtree(plugin_dir / "models", ignore_errors=True)
    port = free_port()
    base = "http://127.0.0.1:%d" % port
    server_log = WORK / "server.log"
    handle = server_log.open("w", encoding="utf-8", errors="replace")
    env = os.environ.copy()
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)
    api_exe = mineru_setup.engine_dir() / "Scripts" / "mineru-api.exe"
    api_bak = api_exe.with_suffix(".exe.probe-bak")
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            if process.poll() is not None:
                raise RuntimeError("服务提前退出：" + server_log.read_text(
                    encoding="utf-8", errors="replace")[:2000])
            try:
                with urllib.request.urlopen(base + "/healthz", timeout=1) as resp:
                    if resp.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.2)
        else:
            raise RuntimeError("服务 60 秒未就绪")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=15000)
            item.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            # —— 安装/就绪 ——
            canvas.locator("#epModelConfigList").click()
            modal = canvas.locator("#edModelConfigModal")
            expect(modal).to_be_visible(timeout=15000)
            row = canvas.locator(".ep-model-config-row", has_text="MinerU·本地")
            expect(row).to_be_visible(timeout=15000)
            button = row.locator(".ep-model-config-act")
            if button.count() and button.inner_text() in ("安装本地 MinerU", "重试安装"):
                button.click()  # 出网铁律合规：界面当场真点
                expect(button).to_have_text("安装中…", timeout=15000)
                page.screenshot(path=str(SHOTS / "install-progress.png"))
                last_step, step_shots, state = "", 0, ""
                deadline = time.time() + MAX_INSTALL
                while time.time() < deadline:
                    status = http_json(base, "/api/models/mineru/status")
                    state = str(status.get("state") or "")
                    step = str(status.get("step") or "")
                    if step != last_step:
                        last_step, step_shots = step, step_shots + 1
                        page.screenshot(path=str(SHOTS / ("install-step-%d.png" % step_shots)))
                    if state in ("done", "error"):
                        break
                    time.sleep(5)
                check("真点安装到 done", state == "done",
                      http_json(base, "/api/models/mineru/status"))
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
                canvas.locator("#epModelConfigList").click()
                expect(modal).to_be_visible(timeout=15000)
                row = canvas.locator(".ep-model-config-row", has_text="MinerU·本地")
            expect(row.locator(".ep-model-config-state")).to_have_text(
                "就绪", timeout=60000)
            page.screenshot(path=str(SHOTS / "mineru-ready.png"))
            registry = http_json(base, "/api/models/registry")
            entry = next((e for e in registry.get("entries") or []
                          if e.get("id") == "mineru_local"), {})
            result["mineru_local_entry"] = entry
            check("registry mineru_local ready", entry.get("state") == "ready",
                  {"detail": entry.get("detail")})
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            weights = mineru_setup.weights_ready()
            result["weights_ready_before_parse"] = weights
            check("权重就绪探查（只读）", True, {"weights_ready": weights})
            # —— UI 投卷扫描（auto，本地切题不出网）——
            canvas.locator("#edBasketFile").set_input_files(str(SAMPLE))
            go = canvas.locator("#edBasketGo")
            expect(go).to_be_enabled(timeout=15000)
            go.click()
            batch_row = canvas.locator(".ed-batch-row").first
            expect(batch_row).to_be_visible(timeout=60000)
            batch_id = str(batch_row.get_attribute("data-batch") or "")
            result["batch_id"] = batch_id
            detail = wait_route_done(base, batch_id, 300)
            items = detail.get("items") or []
            page.screenshot(path=str(SHOTS / "scan-batch.png"))
            check("扫描切题≥3 道", len(items) >= 3,
                  {"items": len(items), "route_note": (detail.get("route") or {}).get("note")})
            # —— UI 真选 MinerU·本地 ——
            canvas.locator("#edRecognizeEngine").select_option("mineru_local")
            page.wait_for_timeout(500)
            page.screenshot(path=str(SHOTS / "engine-selected.png"))
            check("下拉真选 MinerU·本地", True)
            # —— 逐题回填 ——
            parse_started = time.time()
            if weights:
                three = pending_service.list_batch_questions(batch_id).get("items")[:3]
                route = fill_local(batch_id, three, {"note": "探针：前 3 题交 MinerU·本地"})
                local_note = str(route.get("note") or "")
                filled, attempted = parse_fill(local_note)
                attempted = attempted or 3
                result["parse"] = {"path": "in_process_3_items",
                                   "filled": filled, "attempted": attempted,
                                   "note": local_note,
                                   "failures": route.get("failures") or []}
                detail = batch_detail(base, batch_id)
                evidence = formula_evidence(detail.get("items") or [], [0, 1, 2])
            else:
                # 权重缺失：UI 真点整批解析，懒下载发生在用户点击的作业里（合规）。
                canvas.locator("#edBasketFile").set_input_files(str(SAMPLE))
                expect(go).to_be_enabled(timeout=15000)
                go.click()
                rows = canvas.locator(".ed-batch-row")
                expect(rows.first).to_be_visible(timeout=60000)
                batch_id = str(rows.first.get_attribute("data-batch") or "")
                result["batch_id"] = batch_id
                detail = wait_route_done(base, batch_id, MAX_PARSE)
                route = detail.get("route") or {}
                local_note = str(route.get("note") or "")
                filled, attempted = parse_fill(local_note)
                attempted = attempted or len(detail.get("items") or [])
                result["parse"] = {"path": "ui_full_batch_lazy_download",
                                   "filled": filled, "attempted": attempted,
                                   "note": local_note,
                                   "failures": route.get("failures") or []}
                evidence = formula_evidence(detail.get("items") or [],
                                            list(range(min(3, len(detail.get("items") or [])))))
            result["parse"]["elapsed_s"] = round(time.time() - parse_started, 1)
            result["formula_evidence"] = evidence
            check("回填 filled≥2", filled >= 2, result["parse"])
            has_formula = bool(evidence["formula_indexes"])
            check("≥1 题含 $...$ 公式（无公式则非空正文＋说明）",
                  has_formula or all(n > 20 for n in evidence["nonempty"]),
                  {"formula_indexes": evidence["formula_indexes"],
                   "stem_lengths": evidence["nonempty"]})
            if not has_formula:
                result["deviations"].append("3 题正文均无 $...$ 公式，按卡口径断言非空正文")
            # 服务现场侦查（只读）：tiers/models + 令牌鉴权形状
            endpoint = mineru_service.endpoint()
            if endpoint:
                try:
                    req = urllib.request.Request(
                        endpoint["base_url"] + "/v1/tiers",
                        headers={"Authorization": "Bearer " + endpoint["token"]})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        result["live_tiers"] = wire.loads(resp.read().decode("utf-8"))
                except (urllib.error.URLError, OSError, ValueError) as exc:
                    result["live_tiers_error"] = str(exc)
            # 回填截图：点开批次看题干与路由注记
            canvas.locator(".ed-batch-row[data-batch='%s'] .ed-batch-open" % batch_id).click()
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SHOTS / "fill-result.png"))
            # —— 负向：停服＋挪开入口 → 再选本地＝显性失败，不偷换 ——
            stop_one = mineru_service.stop()
            result["stop_before_negative"] = stop_one
            if not stop_one.get("was_running"):
                result["negative_kill"] = kill_service_by_log(server_log)
            api_exe.rename(api_bak)
            try:
                one = pending_service.list_batch_questions(batch_id).get("items")[:1]
                bad_route = fill_local(batch_id, one, {"note": "探针负向：服务入口挪开"})
            finally:
                api_bak.rename(api_exe)
            result["negative"] = {"note": bad_route.get("note"),
                                  "mode": bad_route.get("mode"),
                                  "failures": bad_route.get("failures") or []}
            steps = [str(f.get("step") or "") for f in bad_route.get("failures") or []]
            check("负向显性失败清单（识别·MinerU本地）",
                  "识别·MinerU本地" in steps and bad_route.get("mode") == "mineru_local"
                  and "不降级" in str(bad_route.get("note") or ""),
                  result["negative"])
            # 失败清单截图：重进插件刷批次卡徽标→点开内联清单
            page.reload(wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=15000)
            item.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            badge = canvas.locator(".ed-batch-row[data-batch='%s'] .ed-batch-failbadge" % batch_id)
            expect(badge).to_be_visible(timeout=30000)
            badge.click()
            expect(canvas.locator(".ed-fail-item").first).to_be_visible(timeout=15000)
            page.screenshot(path=str(SHOTS / "failure-list.png"))
            check("失败清单 UI 可见", True)
            browser.close()
        # —— 收口：显式 stop＋端口复验＋孤儿清点 ——
        stop_two = mineru_service.stop()
        result["stop_final"] = stop_two
        check("收口显式 stop＋端口复验", stop_two.get("port_closed", True), stop_two)
        listing = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq mineru-api.exe", "/NH"],
            capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
        orphans = [line for line in listing.splitlines() if "mineru-api" in line.lower()]
        result["orphan_mineru_api"] = orphans
        check("mineru-api 孤儿零", not orphans, {"lines": orphans})
    except Exception as error:  # noqa: BLE001 - 现场带回
        result["error"] = "%s: %s" % (type(error).__name__, error)
        print("ERROR", result["error"], flush=True)
    finally:
        if api_bak.exists() and not api_exe.exists():
            api_bak.rename(api_exe)
        try:
            mineru_service.stop()
        except Exception:  # noqa: BLE001 - 收口尽力而为
            pass
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
        handle.close()
        time.sleep(0.5)
        check("服务进程端口复验关闭", port_closed(port), {"port": port})
    return finish(result, started, 0 if result.get("ok") else 1)


def finish(result: dict, started: float, code: int) -> int:
    failed = [c for c in result["checks"] if not c["ok"]]
    result["ok"] = not failed and not result.get("error")
    result["elapsed_s"] = round(time.time() - started, 1)
    (WORK / "probe.toml").write_text(toml_io.dumps(result, default=str),
                                     encoding="utf-8")
    print("ok=%s elapsed=%.1fs" % (result["ok"], result["elapsed_s"]), flush=True)
    return 0 if result["ok"] else code


if __name__ == "__main__":
    raise SystemExit(main())