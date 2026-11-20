# -*- coding: utf-8 -*-
"""本地 VLM 书生/面壁双座安装＋推理＋切座＋按件卸载真机探针（安装接线卡座5/6）。

用法：``.venv/Scripts/python.exe tools/vlm_live_probe.py [tag]``

隔离：两仓 git archive HEAD 解包副本（禁抄工作树）＋独立 JZO_DATA_DIR／
JZO_PLUGINS_DIR＋动态空闲端口＋每次随机令牌；服务 cwd＝副本，engines/vlm 落副本内
——不碰用户 data/、真机 engines/ 与 65496 暖驻留。出网只由配置中心【安装】点击＋
确认弹窗 accept 发起（发动机 pip 四家测速、GGUF 三源测速，hf-mirror 主源）。
GPU 纪律：起 llama-server 前查 gpu-seat.lock＋查无其他探针 llama-server，自持锁用完删。
停跑令合规：prefs auto_image_seat=cloud_vision；冒烟走纯图小题（720×160，远低于
RDNA1 Vulkan 批宽阈值），显式选座，绝不触 MinerU/VLM CPU 耗时基准。

判据：
1. 初始 intern/minicpm 未就绪＋install_vlm_intern/minicpm（rule=vlm_local、can_cpu）；
2. 书生安装真证：真点→1.74GB 弹窗 accept→POST→两件 sha256 逐字落地→就绪＋卸载钮；
3. 书生冒烟：显式选 vlm_intern→3 张小题各 1 道非占位待审题、零失败；llama-server 挂书生权重；
4. 面壁安装真证：4.85GB＋MiniCPM Model License 弹窗→两件 sha256→就绪；书生两件仍在（共享目录）；
5. 面壁冒烟＋切座真证：选 vlm_minicpm→3 道非占位；llama-server 改挂面壁权重、书生进程已停；
6. 按件卸载：卸书生只删两件、面壁两件与发动机目录不动且仍就绪；再卸面壁（在跑先停服）目录删净；
7. 零 JS 异常、零 HTTP 失败、三查 0、收口端口闭＋llama-server/python 孤儿零。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402
from app.core.ingest.vlm_weights import SEATS  # noqa: E402

import hashlib
import io
import json
import os
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
GPU_LOCK = ROOT / ".system_generated" / "gpu-seat.lock"
INSTALL_CAP = {"intern": 1800, "minicpm": 2400}
SMOKE_CAP = 1200
QUESTIONS = ["1. 解方程：x + 3 = 7，求 x 的值。",
             "2. 解方程：2x - 5 = 9，求 x 的值。",
             "3. 若 3x = 12，求 x 的值。"]
WEIGHTS = {seat: {name: (size, sha) for name, size, sha in SEATS[seat]["files"]}
           for seat in ("intern", "minicpm")}


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


def llama_procs() -> list[dict]:
    out = subprocess.run(["wmic", "process", "where", "name='llama-server.exe'",
                          "get", "ProcessId,ParentProcessId,CommandLine", "/FORMAT:CSV"],
                         capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
    rows = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4 and parts[-1].isdigit():
            rows.append({"pid": int(parts[-1]), "parent": parts[-2],
                         "cmdline": ",".join(parts[1:-2])})
    return rows


def make_inputs(folder: Path, prefix: str) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 30)
    paths = []
    for index, text in enumerate(QUESTIONS, start=1):
        image = Image.new("RGB", (720, 160), "white")
        ImageDraw.Draw(image).text((32, 62), text, font=font, fill="black")
        path = folder / ("%s小题%d.png" % (prefix, index))
        image.save(path)
        paths.append(path)
    return paths


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    started = time.time()
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    work = ROOT / ".system_generated" / "vlm-live" / tag
    if work.exists():
        shutil.rmtree(work)
    shots, inputs = work / "shots", work / "inputs"
    shots.mkdir(parents=True)
    inputs.mkdir()
    op_dir, plugins_src = work / "operator", work / "plugins-src"
    op_head = git_archive(ROOT, op_dir)
    pl_head = git_archive(PLUGINS_REPO, plugins_src)
    plugin_dir = plugins_src / "src" / EDITOR_ID
    toml_io.write(plugin_dir / "model_prefs.toml", {
        "disabled": [], "default_layout": "auto", "default_recognize": "auto",
        "auto_image_seat": "cloud_vision", "auto_text_formula_seat": "auto"})
    engines_vlm = op_dir / "engines" / "vlm"
    models_dir = engines_vlm / "models"
    inputs_intern = make_inputs(inputs, "书生")
    inputs_minicpm = make_inputs(inputs, "面壁")
    # 复现真机前置：py3.14 无 mineru-llama-cpp 0.2.3 预编译轮，真机 VLM 发动机本就走
    # engines/mineru 离线迁移（engine.toml origin=迁移，不算出网）。副本预置同款迁移源，
    # UI 点击仍真跑 pip 测速→全败→迁移链；GGUF 权重照旧由点击真下载＋sha256 校验。
    mig_src = ROOT / "engines" / "mineru" / "Lib" / "site-packages"
    mig_dst = op_dir / "engines" / "mineru" / "Lib" / "site-packages"
    mig_bin = mig_src / "mineru_llama_cpp" / "bin"
    mig_seeded = (mig_bin / "llama-server.exe").is_file()
    if mig_seeded:
        (mig_dst / "mineru_llama_cpp").mkdir(parents=True, exist_ok=True)
        shutil.copytree(mig_bin, mig_dst / "mineru_llama_cpp" / "bin", dirs_exist_ok=True)
        for info in mig_src.glob("mineru_llama_cpp-*.dist-info"):
            shutil.copytree(info, mig_dst / info.name, dirs_exist_ok=True)

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
    lock_owned = False
    before_llama = llama_procs()
    result: dict = {"tag": tag, "base": base, "operator_head": op_head,
                    "plugins_head": pl_head, "checks": [], "console_errors": [],
                    "page_errors": [], "http_failures": [], "install_requests": [],
                    "dialogs": [], "timing": {}, "servers": {}, "deviations": [
                        "prefs auto_image_seat=cloud_vision：冒烟显式选座，自动兜底不触 CPU 停跑令",
                        "冒烟用 720×160 渲染小题（远低于 RDNA1 Vulkan 批宽阈值），非耗时基准",
                        "发动机：py3.14 无 mineru-llama-cpp 0.2.3 预编译轮，pip 测速全败后走 engines/mineru "
                        "离线迁移（真机同款，不算出网）；副本预置迁移源复现真机前置（mineru 本地座已装），非抄代码",
                        "GGUF 权重资产住副本 engines/vlm/models/（真机暖驻留零接触）"] + (
                            [] if mig_seeded else ["警告：真机 engines/mineru 迁移源不在，发动机安装可能全败"])}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, detail or ""), flush=True)

    def wait_install(seat: str) -> dict:
        status: dict = {}
        deadline = time.time() + INSTALL_CAP[seat]
        while time.time() < deadline:
            status = http_json(base, "/api/models/vlm_%s/status" % seat, token)
            if status.get("state") in ("done", "error"):
                break
            time.sleep(3)
        return status

    def landed(seat: str) -> list:
        rows = []
        for name, (size, sha) in WEIGHTS[seat].items():
            path = models_dir / name
            got = sha256_of(path) if path.is_file() else ""
            rows.append({"name": name, "bytes": path.stat().st_size if path.is_file() else 0,
                         "sha256": got, "match": got == sha})
        return rows

    def probe_servers() -> list[dict]:
        return [p for p in llama_procs() if str(op_dir) in p["cmdline"]]

    def acquire_lock() -> None:
        nonlocal lock_owned
        if GPU_LOCK.exists():
            data = toml_io.load(GPU_LOCK, {})
            age = time.time() - float(data.get("started") or 0)
            if age <= 1800:
                deadline = time.time() + 60
                while GPU_LOCK.exists() and time.time() < deadline:
                    time.sleep(2)
                if GPU_LOCK.exists():
                    raise RuntimeError("GPU 锁被他人活锁占用（%s），等待 60s 仍在" % data)
            else:
                result["deviations"].append("夺锁登记：旧锁龄 %.0fs>30min（%s）" % (age, data))
        toml_io.write(GPU_LOCK, {"session": "install-all-8058810e", "seat": "vlm_intern+minicpm",
                                 "pid": os.getpid(), "started": time.time()})
        lock_owned = True

    def smoke(seat: str, prefix: str, paths: list[Path], canvas, page) -> dict:
        select = canvas.locator("#edRecognizeEngine")
        deadline = time.time() + 30
        options: list = []
        while time.time() < deadline:
            options = select.evaluate("node => Array.from(node.options).map(o => o.value)")
            if "vlm_" + seat in options:
                break
            page.wait_for_timeout(300)
        check("就绪后 vlm_%s 进识别下拉" % seat, "vlm_" + seat in options, options)
        select.select_option("vlm_" + seat)
        cards: dict[str, dict] = {}
        notes: list = []
        ok_docs, done_at, t0 = False, {}, time.monotonic()
        # 枢纽规则②：RDNA1 掉设备后 /health 仍 200 但 /v1 mtmd-500，产品会复用死实例。
        # 冒烟红则只杀自起实例（probe_servers 限本副本 cmdline）逼产品重起，再试一轮；
        # 两轮按 batch_id 隔离，避免旧失败批次混入计数。整页大图红＝如实记，不赌参数。
        for attempt in range(1, 3):
            existing = {str(c.get("batch_id")) for c in
                        http_json(base, "/api/pending/batches", token).get("batches", [])}
            canvas.locator("#edBasketFile").set_input_files([str(p) for p in paths])
            expect(canvas.locator(".ed-basket-item")).to_have_count(3, timeout=10000)
            t0 = time.monotonic()
            with page.expect_response(lambda r: "/api/ingest/files" in r.url, timeout=30000) as resp:
                canvas.locator("#edBasketGo").click()
            if attempt == 1:
                check("%s 三图一批次各立（解析请求 201）" % prefix,
                      resp.value.status == 201, resp.value.status)
            done_at, cards = {}, {}
            deadline = time.time() + SMOKE_CAP
            while time.time() < deadline and len(done_at) < 3:
                for card in http_json(base, "/api/pending/batches", token).get("batches", []):
                    name = str(card.get("source_name") or "")
                    bid = str(card.get("batch_id"))
                    if (bid not in existing and name.startswith(prefix)
                            and (card.get("route") or {}).get("done") and name not in done_at):
                        done_at[name] = time.monotonic() - t0
                        cards[name] = card
                if len(done_at) < 3:
                    time.sleep(2)
            ok_docs, notes = True, []
            for name, card in sorted(cards.items()):
                failures = (card.get("route") or {}).get("failures") or []
                items = http_json(base, "/api/pending/batches/%s/questions" % card["batch_id"],
                                  token).get("items") or []
                stem = str((items[0].get("question") or {}).get("stem") or "") if items else ""
                good = (len(items) == 1 and not failures and "正在识别" not in stem
                        and "待识别" not in stem and len(stem.strip()) > 3)
                ok_docs = ok_docs and good
                notes.append({"name": name, "items": len(items),
                              "failures": failures[:1], "stem": stem[:160]})
            if ok_docs and len(done_at) == 3:
                break
            if attempt < 2:
                for proc in probe_servers():
                    subprocess.run(["taskkill", "/PID", str(proc["pid"]), "/T", "/F"],
                                   capture_output=True, timeout=30)
                result["deviations"].append(
                    "%s 冒烟第1轮红（疑 RDNA1 掉设备 mtmd-500），杀自起实例重起再试（枢纽规则②）：%s"
                    % (prefix, notes))
                page.wait_for_timeout(2000)
        check("%s 三批全部识别收口" % prefix, len(done_at) == 3,
              {"done": sorted(done_at), "elapsed_s": round(time.monotonic() - t0, 1)})
        result["timing"][seat] = {"per_question_wall_s": {n: round(s, 1) for n, s in sorted(done_at.items())},
                                  "total_wall_s": round(time.monotonic() - t0, 1)}
        check("%s 各批 1 道非占位待审题＋零失败清单" % prefix, ok_docs, notes)
        result["smoke_" + seat] = notes
        page.screenshot(path=str(shots / ("smoke-%s.png" % seat)))
        srv = probe_servers()
        result["servers"][seat] = srv
        return {"cards": cards, "servers": srv}

    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "info", "--no-server-header"],
            cwd=str(op_dir), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
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
        check("起服前无其他探针 llama-server（暖驻留父=65496 零接触）",
              not [p for p in before_llama if str(work) in p["cmdline"]],
              {"before_pids": [p["pid"] for p in before_llama]})
        registry = http_json(base, "/api/models/registry")
        by_id = {str(e.get("id")): e for e in registry.get("entries") or []}
        for seat in ("intern", "minicpm"):
            entry = by_id.get("vlm_" + seat) or {}
            check("初始 vlm_%s 未就绪＋install_vlm_%s（vlm_local/can_cpu）" % (seat, seat),
                  entry.get("state") == "degraded" and entry.get("action") == "install_vlm_" + seat
                  and entry.get("rule") == "vlm_local" and entry.get("can_cpu") is True, entry)
        check("千问座/千问组合未装引导＋texify 登记跳过不动",
              (by_id.get("vlm_qwen") or {}).get("action") == "install_vlm"
              and (by_id.get("combo_vlm_qwen") or {}).get("state") == "degraded"
              and (by_id.get("formula_texify") or {}).get("state") == "blocked",
              {k: (by_id.get(k) or {}).get("state") for k in ("vlm_qwen", "combo_vlm_qwen", "formula_texify")})
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type in {"error", "warning"} else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.on("response", lambda r: result["http_failures"].append(
                "%s %s" % (r.status, r.url)) if r.status >= 400 else None)
            page.on("dialog", lambda d: (result["dialogs"].append(d.message), d.accept()))
            page.goto(base + "/workspace", wait_until="networkidle")
            page.locator(".ws-plugin-item", has_text="录题工作台").first.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            canvas.locator("#epModelConfigList").click()
            expect(canvas.locator(".ep-mt-table").first).to_be_visible(timeout=15000)
            row_in = canvas.locator(".ep-mt-row", has_text="书生 InternVL3-2B")
            row_mc = canvas.locator(".ep-mt-row", has_text="面壁 MiniCPM-V-2.6")
            expect(row_in.locator(".ep-mt-badge")).to_have_text("未安装", timeout=15000)
            expect(row_mc.locator(".ep-mt-badge")).to_have_text("未安装", timeout=15000)
            check("未安装行：书生/面壁 未就绪＋【安装】钮",
                  row_in.locator(".ep-mt-act", has_text="安装").count() == 1
                  and row_mc.locator(".ep-mt-act", has_text="安装").count() == 1)
            page.screenshot(path=str(shots / "01-not-installed.png"))
            page.set_viewport_size({"width": 375, "height": 720})
            overflow = canvas.locator(".ep-mt-table").first.evaluate(
                "node => node.scrollWidth - node.clientWidth")
            check("375px 模型表不横向溢出（未安装态）", overflow <= 0, {"overflow_px": overflow})
            page.set_viewport_size({"width": 1440, "height": 900})
            # ---------- 书生安装真证 ----------
            with page.expect_request(
                    lambda r: "/api/models/vlm_intern/install" in r.url and r.method == "POST",
                    timeout=30000) as req_in:
                row_in.locator(".ep-mt-act", has_text="安装").click()
            result["install_requests"].append(req_in.value.url)
            page.wait_for_timeout(500)
            check("书生 1.74GB＋共享发动机确认弹窗已摆并 accept",
                  bool(result["dialogs"]) and "1.74GB" in result["dialogs"][-1]
                  and "共享" in result["dialogs"][-1], result["dialogs"][-1:])
            status_in = wait_install("intern")
            result["install_status_intern"] = status_in
            check("书生安装收口 done", status_in.get("state") == "done", status_in)
            landed_in = landed("intern")
            result["weights_intern"] = landed_in
            check("书生两件 GGUF 落地 sha256 逐字一致", all(w["match"] for w in landed_in), landed_in)
            expect(row_in.locator(".ep-mt-badge")).to_contain_text("就绪", timeout=30000)
            check("书生已安装行：就绪＋【卸载】钮",
                  row_in.locator(".ep-mt-act", has_text="卸载").count() == 1)
            pip_bin = engines_vlm / "Lib" / "site-packages" / "mineru_llama_cpp" / "bin"
            mig_bin_out = engines_vlm / "llama-bin"
            engine_bin = next((b for b in (pip_bin, mig_bin_out)
                               if (b / "llama-server.exe").is_file()), mig_bin_out)
            check("发动机真二进制现算＝Vulkan（副本内 ggml-vulkan.dll）",
                  (engine_bin / "ggml-vulkan.dll").is_file() and (engine_bin / "llama-server.exe").is_file(),
                  {"bin": str(engine_bin), "origin": "迁移" if engine_bin == mig_bin_out else "pip"})
            page.screenshot(path=str(shots / "02-intern-installed.png"))
            canvas.locator("#edModelConfigBack").click()
            # ---------- 书生冒烟（起 llama-server 前持 GPU 锁） ----------
            acquire_lock()
            check("GPU 锁自持（起 llama-server 前）", lock_owned and GPU_LOCK.is_file())
            smoke("intern", "书生", inputs_intern, canvas, page)
            srv_in = result["servers"]["intern"]
            check("书生冒烟时 llama-server 挂书生权重（InternVL3-2B.Q4_K_M）",
                  any("InternVL3-2B.Q4_K_M.gguf" in p["cmdline"] for p in srv_in),
                  [{"pid": p["pid"], "model": p["cmdline"].split("--model ")[-1].split(" ")[0]} for p in srv_in])
            intern_pids = {p["pid"] for p in srv_in}
            # ---------- 面壁安装真证 ----------
            canvas.locator("#epModelConfigList").click()
            expect(canvas.locator(".ep-mt-table").first).to_be_visible(timeout=15000)
            row_mc = canvas.locator(".ep-mt-row", has_text="面壁 MiniCPM-V-2.6")
            with page.expect_request(
                    lambda r: "/api/models/vlm_minicpm/install" in r.url and r.method == "POST",
                    timeout=30000) as req_mc:
                row_mc.locator(".ep-mt-act", has_text="安装").click()
            result["install_requests"].append(req_mc.value.url)
            page.wait_for_timeout(500)
            check("面壁 4.85GB＋MiniCPM Model License 确认弹窗已摆并 accept",
                  bool(result["dialogs"]) and "4.85GB" in result["dialogs"][-1]
                  and "MiniCPM Model License" in result["dialogs"][-1], result["dialogs"][-1:])
            status_mc = wait_install("minicpm")
            result["install_status_minicpm"] = status_mc
            check("面壁安装收口 done", status_mc.get("state") == "done", status_mc)
            landed_mc = landed("minicpm")
            result["weights_minicpm"] = landed_mc
            check("面壁两件 sha256 逐字一致且书生两件仍在（共享目录共存）",
                  all(w["match"] for w in landed_mc)
                  and all((models_dir / n).is_file() for n in WEIGHTS["intern"]),
                  {"minicpm": landed_mc, "intern_present": [n for n in WEIGHTS["intern"] if (models_dir / n).is_file()]})
            expect(row_mc.locator(".ep-mt-badge")).to_contain_text("就绪", timeout=30000)
            page.screenshot(path=str(shots / "03-minicpm-installed.png"))
            canvas.locator("#edModelConfigBack").click()
            # ---------- 面壁冒烟＋切座真证 ----------
            smoke("minicpm", "面壁", inputs_minicpm, canvas, page)
            srv_mc = result["servers"]["minicpm"]
            check("面壁冒烟时 llama-server 改挂面壁权重（ggml-model-Q3_K_M）",
                  any("ggml-model-Q3_K_M.gguf" in p["cmdline"] for p in srv_mc),
                  [{"pid": p["pid"], "model": p["cmdline"].split("--model ")[-1].split(" ")[0]} for p in srv_mc])
            check("切座真证：书生 llama-server 进程已停（单活座）",
                  not (intern_pids & {p["pid"] for p in srv_mc}),
                  {"intern_pids": sorted(intern_pids), "minicpm_pids": [p["pid"] for p in srv_mc]})
            log_text = server_log.read_text(encoding="utf-8", errors="replace")
            result["switch_log"] = [ln for ln in log_text.splitlines() if "切座" in ln][:3]
            # ---------- 按件卸载：卸书生保面壁→卸面壁目录删净 ----------
            page.reload(wait_until="networkidle")
            page.locator(".ws-plugin-item", has_text="录题工作台").first.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            canvas.locator("#epModelConfigList").click()
            expect(canvas.locator(".ep-mt-table").first).to_be_visible(timeout=15000)
            row_in = canvas.locator(".ep-mt-row", has_text="书生 InternVL3-2B")
            row_mc = canvas.locator(".ep-mt-row", has_text="面壁 MiniCPM-V-2.6")
            row_in.locator(".ep-mt-act", has_text="卸载").click()
            page.wait_for_timeout(500)
            check("卸载确认弹窗摆明本座两件（其他座不受影响）",
                  bool(result["dialogs"]) and "本座两件权重" in result["dialogs"][-1]
                  and "其他座不受影响" in result["dialogs"][-1], result["dialogs"][-1:])
            deadline = time.time() + 60
            while time.time() < deadline and any((models_dir / n).exists() for n in WEIGHTS["intern"]):
                time.sleep(1)
            check("卸书生只删两件", not any((models_dir / n).exists() for n in WEIGHTS["intern"]))
            check("面壁两件与发动机目录原样保留（互不误删）",
                  all((models_dir / n).is_file() for n in WEIGHTS["minicpm"]) and engines_vlm.is_dir(),
                  {"minicpm_present": [n for n in WEIGHTS["minicpm"] if (models_dir / n).is_file()]})
            expect(row_mc.locator(".ep-mt-badge")).to_contain_text("就绪", timeout=30000)
            expect(row_in.locator(".ep-mt-badge")).to_have_text("未安装", timeout=30000)
            check("卸书生后面壁仍就绪、书生回未就绪＋【安装】钮",
                  row_in.locator(".ep-mt-act", has_text="安装").count() == 1)
            page.screenshot(path=str(shots / "04-intern-uninstalled-minicpm-kept.png"))
            row_mc.locator(".ep-mt-act", has_text="卸载").click()
            page.wait_for_timeout(500)
            check("面壁卸载弹窗摆明在跑先停服",
                  bool(result["dialogs"]) and "在跑本座会先停服" in result["dialogs"][-1],
                  result["dialogs"][-1:])
            deadline = time.time() + 120
            while time.time() < deadline and engines_vlm.exists():
                time.sleep(1)
            check("再卸面壁目录删净（全空才连发动机删）＋在跑服务已停",
                  not engines_vlm.exists() and not probe_servers(),
                  {"engines_vlm_exists": engines_vlm.exists(), "servers": probe_servers()})
            expect(row_mc.locator(".ep-mt-badge")).to_have_text("未安装", timeout=30000)
            page.screenshot(path=str(shots / "05-all-uninstalled.png"))
            browser.close()
        counts = {"fetch(": 0, "parent.document": 0, "localStorage": 0}
        for script in sorted((plugin_dir / "dist").glob("*.js")):
            text = script.read_text(encoding="utf-8", errors="replace")
            counts = {k: v + text.count(k) for k, v in counts.items()}
        check("三查 fetch(/parent.document/localStorage=0", all(v == 0 for v in counts.values()), counts)
        check("页面零 JS 异常", not result["page_errors"], result["page_errors"][:5])
        check("全程零 HTTP 失败", not result["http_failures"], result["http_failures"][:5])
    except Exception as error:  # noqa: BLE001 - 探针把现场带回去
        result["error"] = "%s: %s" % (type(error).__name__, error)
        print("ERROR", result["error"], flush=True)
    finally:
        if process is not None:
            if sys.platform == "win32":
                import signal
                try:
                    os.kill(process.pid, signal.CTRL_BREAK_EVENT)
                except OSError:
                    process.terminate()
            else:
                process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
        handle.close()
        if lock_owned and GPU_LOCK.exists():
            data = toml_io.load(GPU_LOCK, {})
            if int(data.get("pid") or 0) == os.getpid():
                GPU_LOCK.unlink(missing_ok=True)
                lock_owned = False
        time.sleep(1)
        check("收口服务端口复验关闭", port_closed(port), {"port": port})
        check("GPU 锁用完已删", not GPU_LOCK.exists() or not lock_owned)
        after_llama = llama_procs()
        orphans = [p for p in after_llama if str(work) in p["cmdline"]]
        for p in orphans:
            subprocess.run(["taskkill", "/PID", str(p["pid"]), "/T", "/F"], capture_output=True, timeout=30)
        check("llama-server 零孤儿（lifespan 停服）", not orphans, {"pids": [p["pid"] for p in orphans]})
        out = subprocess.run(["wmic", "process", "where", "name='python.exe'",
                              "get", "ProcessId,CommandLine", "/FORMAT:CSV"],
                             capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
        py_orphans = [line.rsplit(",", 1)[-1].strip() for line in out.splitlines()
                      if str(work) in line and line.strip()]
        for pid in py_orphans:
            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True, timeout=30)
        check("副本服务 python 孤儿零", not py_orphans, {"pids": py_orphans})
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