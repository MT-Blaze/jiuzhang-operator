# -*- coding: utf-8 -*-
"""座1 yolo（YOLO·版面 满血版）安装＋版面冒烟真机探针（全模型安装接线卡§2）。

用法：``.venv/Scripts/python.exe tools/yolo_install_probe.py [tag]``

隔离：两仓 git archive HEAD 解包副本（禁抄工作树）＋独立 JZO_DATA_DIR／
JZO_PLUGINS_DIR＋动态空闲端口＋每次随机令牌；服务 cwd＝副本，权重落副本插件
models/——不碰用户 data/、真机 plugins/models 与 65496。出网只由模型配置中心
【下载】点击发起（model_config.toml 写死国内镜像，75MB，sha256 逐字校验）。
停跑令合规：prefs auto_image_seat=cloud_vision（未指派＝显性失败零引擎），
版面冒烟显式 layout_engine=yolo，识别 auto 不触 MinerU 本地 CPU／VLM CPU。

判据：
1. 未安装三态：YOLO·版面 行未就绪＋【下载】钮（副本无权重）；
2. 下载真证：真点→POST 真请求→75MB 落地 sha256 逐字一致→就绪；
3. 版面冒烟：4 页纯图真卷 layout_engine=yolo→layout_status 含「已启用本地 YOLO」
   ＋layout_model.kind=full＋题块裁成待审题 items≥3（3–5 页真跑）；
4. 零 JS 异常、零 HTTP 失败、三查 0、收口端口闭＋孤儿零。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402

import base64
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
SAMPLE_SCAN = ROOT / "test_papers" / "C1_2026年佛山市高中数学教师解题能力比赛(1).pdf"
WEIGHT_NAME = "doclayout_yolo_full_v1.0.onnx"
WEIGHT_SIZE = 75324598
WEIGHT_SHA = "fece9af02f618b603ff7921ccec6861d13e7e1f9830e091dfb7e8ad9311e5b21"
YOLO_LINE = "已启用本地 YOLO"
DOWNLOAD_CAP, LAYOUT_CAP = 300, 240


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


def http_json(base: str, path: str, token: str = "", payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"X-JZO-Token": token} if token else {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base + path, data=body, headers=headers,
                                     method="POST" if body is not None else "GET")
    with urllib.request.urlopen(request, timeout=120) as response:
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
    work = ROOT / ".system_generated" / "yolo-install" / tag
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
    weight_path = plugin_dir / "models" / WEIGHT_NAME

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
                    "page_errors": [], "http_failures": [], "download_requests": [],
                    "dialogs": [], "deviations": [
                        "权重落点是插件目录 models/（yolo 既有 wiring 固有路径），非 engines/<store>/",
                        "prefs auto_image_seat=cloud_vision（未指派）：识别 auto 显性失败零引擎，"
                        "避 MinerU 本地 CPU／VLM CPU 停跑令；版面 yolo 真跑不受影响"]}

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
        yolo = by_id.get("yolo") or {}
        check("初始 YOLO 未就绪＋download（副本无权重）",
              yolo.get("state") == "degraded" and yolo.get("action") == "download", yolo)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type in {"error", "warning"} else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.on("response", lambda r: result["http_failures"].append(
                "%s %s" % (r.status, r.url)) if r.status >= 400 else None)
            page.on("request", lambda r: result["download_requests"].append(r.url)
                    if "/api/layout/models/download" in r.url else None)
            page.on("dialog", lambda d: (result["dialogs"].append(d.message), d.accept()))
            page.goto(base + "/workspace", wait_until="networkidle")
            page.locator(".ws-plugin-item", has_text="录题工作台").first.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            # ---------- ① 未安装三态 ----------
            canvas.locator("#epModelConfigList").click()
            expect(canvas.locator(".ep-mt-table").first).to_be_visible(timeout=15000)
            row = canvas.locator(".ep-mt-row", has_text="YOLO·版面")
            expect(row.locator(".ep-mt-badge")).to_have_text("未就绪", timeout=15000)
            check("未安装行：未就绪＋【下载】钮",
                  row.locator(".ep-mt-act", has_text="下载").count() == 1)
            page.screenshot(path=str(shots / "01-not-installed.png"))
            # ---------- ② 下载真证（75MB 国内镜像，sha256 逐字） ----------
            with page.expect_request(
                    lambda r: "/api/layout/models/download" in r.url and r.method == "POST",
                    timeout=30000) as req_info:
                row.locator(".ep-mt-act", has_text="下载").click()
            result["download_requests"].append(req_info.value.url)
            status: dict = {}
            deadline = time.time() + DOWNLOAD_CAP
            while time.time() < deadline:
                status = http_json(base, "/api/layout/models/status", token)
                dl = status.get("download") or {}
                if dl.get("state") in ("done", "error"):
                    break
                time.sleep(3)
            result["download_status"] = status.get("download")
            check("下载请求确由界面点击发起", bool(result["download_requests"]),
                  result["download_requests"])
            check("下载收口 done", (status.get("download") or {}).get("state") == "done",
                  status.get("download"))
            got = sha256_of(weight_path) if weight_path.is_file() else ""
            result["weight"] = {"name": WEIGHT_NAME,
                                "bytes": weight_path.stat().st_size if weight_path.is_file() else 0,
                                "sha256": got, "match": got == WEIGHT_SHA}
            check("75MB 权重落地 sha256 逐字一致",
                  weight_path.is_file() and weight_path.stat().st_size == WEIGHT_SIZE
                  and got == WEIGHT_SHA, result["weight"])
            expect(row.locator(".ep-mt-badge")).to_have_text("就绪", timeout=30000)
            check("已安装行：就绪", True)
            page.screenshot(path=str(shots / "02-installed.png"))
            canvas.locator("#edModelConfigBack").click()
            browser.close()
        # ---------- ③ 版面冒烟：4 页纯图真卷 layout_engine=yolo ----------
        payload = {
            "files": [{"name": SAMPLE_SCAN.name, "data_url":
                       "data:application/pdf;base64,"
                       + base64.b64encode(SAMPLE_SCAN.read_bytes()).decode()}],
            "layout_engine": "yolo", "recognize_engine": "auto",
        }
        staged = http_json(base, "/api/ingest/files", token, payload)
        batch = str(staged.get("batch_id") or "")
        result["batch"] = batch
        check("纯图真卷立批次（layout_engine=yolo）", bool(batch), {"batch": batch})
        detail: dict = {}
        deadline = time.time() + LAYOUT_CAP
        while time.time() < deadline:
            detail = http_json(base, "/api/pending/batches/%s/questions" % batch, token)
            if (detail.get("route") or {}).get("done"):
                break
            time.sleep(4)
        route = detail.get("route") or {}
        items = detail.get("items") or []
        result["layout_route"] = {k: route.get(k) for k in
                                  ("layout_status", "layout_model", "mode", "done")}
        texts = [str(s.get("text") or "") for s in route.get("layout_status") or []]
        check("版面冒烟：layout_status 含「已启用本地 YOLO」",
              any(YOLO_LINE in t for t in texts), {"texts": texts})
        check("版面冒烟：满血版落地（layout_model.kind=full）",
              (route.get("layout_model") or {}).get("kind") == "full",
              route.get("layout_model"))
        result["layout_items"] = len(items)
        check("版面冒烟：4 页真卷题块裁成待审题 items≥3（3–5 页真跑）",
              len(items) >= 3, {"items": len(items)})
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