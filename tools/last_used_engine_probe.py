# -*- coding: utf-8 -*-
"""默认引擎记上次＋识别下拉分组全组合真机探针（last-used-engine 卡§4）。

用法：``.venv/Scripts/python.exe tools/last_used_engine_probe.py [tag]``

隔离：插件副本走 ``git archive HEAD``（禁抄工作树，models/ 与 model_prefs.toml
天然不入副本）＋独立 JZO_DATA_DIR / JZO_PLUGINS_DIR＋动态空闲端口＋每次随机
本地令牌（不写死端口与令牌），不碰用户 data/ 与正式服务（65496 零接触）。
engines/ 只读体检走本机真实权重（装了几座公式/VLM 座就认几座，底组不写死）；
云端 AI OCR 座由宿主写口本地种一个 dummy 账号（base_url 用 .invalid 域，零出网）使
combo_cloud 就绪。收口点杀进程并复验端口关闭＋孤儿零。产物落
.system_generated/last-used-engine/<tag>/，证据另拷 docs/handoff/evidence/last-used-engine/。

八项判据（只验本卡契约，不跑识别、不出网）：
1. 配置页①自动设置在、②默认引擎整行已砍；
2. 识别下拉自动单独置顶＋两条禁用表头（—— 整题OCR ——／—— 文字直取＋公式 ——）
   全平铺，底组＝registry 实际就绪组合（本机装几座 VLM 就几条）；版面下拉平铺无组；
3. 停用组合座→下拉摘除→启用恢复；
4. 画布选座→回写上次→刷新初值＝上次；版面/识别各记各的；归自动；
5. 存过的座被停用→初值归自动但 prefs 不擦→启用后刷新恢复；
6. 首次干净＝自动；
7. 纯图卷进筐→组合项置灰＋人话；
8. 零 JS 异常、零 HTTP 失败、三查=0、收口端口关闭、孤儿零。

截图另拷 ``.system_generated/engine-dropdown/<tag>/``（只作证据，git 忽略）。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402
from app.core.config import plugin_source_root  # noqa: E402

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
PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
PLUGINS_REPO = PLUGIN_SOURCE_DIR.parent
EDITOR_ID = "org.jiuzhang.editor"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
GROUP_HEADS = ["—— 整题OCR ——", "—— 文字直取＋公式 ——"]
EXPECTED_ENTRIES = 21
EXPECTED_COMBOS = 8
# 1×1 透明 PNG（纯图卷进筐触组合路置灰，零出网）。
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082")


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


def http_json(base: str, path: str, payload: dict | None = None,
              token: str | None = None) -> tuple[int, dict]:
    import json
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-JZO-Token"] = token
    request = urllib.request.Request(
        base + path, data=body, method="POST" if payload is not None else "GET",
        headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, json.loads(raw or "{}")
        except ValueError:
            return error.code, {"raw": raw}


def archive_plugin(plugin_dir: Path) -> None:
    """从 plugins 仓 HEAD 归档干净插件代码（禁抄工作树；未跟踪 models/prefs 不入副本）。"""
    tar_path = plugin_dir.parent / "editor-head.tar"
    subprocess.run(
        ["git", "-C", str(PLUGINS_REPO), "archive", "--format=tar",
         "-o", str(tar_path), "HEAD:src/" + EDITOR_ID],
        check=True, capture_output=True)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path) as tar:
        tar.extractall(plugin_dir, filter="data")
    tar_path.unlink(missing_ok=True)


def seed_cloud_account(base: str, token: str) -> None:
    """本地种一个 dummy 云端 AI OCR 账号＋指派 ocr 任务（.invalid 域零出网），使 combo_cloud 就绪。"""
    code, body = http_json(base, "/api/ai-center/accounts",
                           {"name": "探针云端 AI OCR", "base_url": "https://probe.invalid/v1",
                            "api_key": "probe-dummy-key"}, token=token)
    if code != 200:
        raise RuntimeError("种云账号失败：%s %s" % (code, body))
    account_id = body.get("id") or (body.get("account") or {}).get("id")
    code, body = http_json(base, "/api/ai-center/assign",
                           {"task": "ocr", "account_id": account_id,
                            "model": "probe-vlm"}, token=token)
    if code != 200:
        raise RuntimeError("指派 ocr 任务失败：%s %s" % (code, body))


def preset_yolo(plugin_dir: Path) -> None:
    """隔离副本内造满血 YOLO 假权重，让版面下拉有就绪座可供记上次取证。"""
    config = toml_io.load(plugin_dir / "model_config.toml", {})
    full = (config.get("models") or {}).get("full") or {}
    min_bytes = int(full.get("min_bytes") or full.get("size_bytes") or 70000000)
    models_dir = plugin_dir / "models"
    models_dir.mkdir(exist_ok=True)
    (models_dir / str(full.get("filename") or "doclayout_yolo_full_v1.0.onnx")).write_bytes(
        b"0" * (min_bytes + 1))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    token = "probe-" + secrets.token_hex(8)
    work = ROOT / ".system_generated" / "last-used-engine" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir, shots = work / "data", work / "plugins", work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    plugin_dir = plugins_dir / EDITOR_ID
    archive_plugin(plugin_dir)
    preset_yolo(plugin_dir)
    png_file = work / "pure.png"
    png_file.write_bytes(PNG_BYTES)

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

    result: dict = {"tag": tag, "base": base, "viewport": "1440x900",
                    "checks": [], "console_errors": [], "page_errors": [],
                    "http_failures": [], "install_requests": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    prefs_file = plugin_dir / "model_prefs.toml"

    def wait_prefs(key: str, want, timeout: float = 15.0):
        deadline = time.time() + timeout
        got = None
        while time.time() < deadline:
            got = toml_io.load(prefs_file, {}).get(key)
            if got == want:
                return got
            time.sleep(0.2)
        return got

    def open_plugin(page):
        page.goto(base + "/workspace", wait_until="networkidle")
        item = page.locator(".ws-plugin-item", has_text="录题工作台").first
        expect(item).to_be_visible(timeout=10000)
        item.click()
        canvas = page.frame_locator(CANVAS)
        expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
        expect(canvas.locator("#edRecognizeEngine")).to_be_visible(timeout=20000)
        page.wait_for_timeout(600)
        return canvas

    def set_prefs(patch: dict) -> None:
        code, body = http_json(base, "/api/models/prefs?plugin_id=" + EDITOR_ID,
                               patch, token=token)
        if code != 200:
            raise RuntimeError("写 prefs 失败：%s %s" % (code, body))

    try:
        wait_health(base, process, server_log)
        seed_cloud_account(base, token)
        _, reg = http_json(base, "/api/models/registry?probe=0")
        entries = reg.get("entries") or []
        by_id = {str(e.get("id")): e for e in entries}

        def _combos(rows):
            return [str(e.get("id")) for e in rows
                    if "combo" in (e.get("plan_recognize") or [])]

        declared_combos = _combos(entries)
        ready_combos = [c for c in declared_combos
                        if (by_id.get(c) or {}).get("state") == "ready"
                        and (by_id.get(c) or {}).get("enabled") is not False]
        whole_ready = [str(e.get("id")) for e in entries
                       if "combo" not in (e.get("plan_recognize") or [])
                       and e.get("capability") in ("recognize", "both")
                       and e.get("state") == "ready"
                       and e.get("enabled") is not False]
        pick = ("combo_pp_l" if "combo_pp_l" in ready_combos
                else (ready_combos[0] if ready_combos else ""))
        check("隔离副本 %d 条目＋%d 条组合声明（底组按本机就绪事实）"
              % (EXPECTED_ENTRIES, EXPECTED_COMBOS),
              len(entries) == EXPECTED_ENTRIES and len(declared_combos) == EXPECTED_COMBOS
              and bool(pick),
              {"count": len(entries), "declared_combos": declared_combos,
               "ready_combos": ready_combos, "pick": pick})

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type in {"error", "warning"} else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.on("response", lambda r: result["http_failures"].append(
                "%s %s" % (r.status, r.url)) if r.status >= 400 else None)
            page.on("request", lambda r: result["install_requests"].append(r.url)
                    if "/install" in r.url and "/api/models/" in r.url else None)
            page.on("dialog", lambda d: d.dismiss())
            canvas = open_plugin(page)

            # ---------- 项6：首次干净＝自动（prefs 未落盘） ----------
            check("项6 首次干净识别＝自动",
                  canvas.locator("#edRecognizeEngine").input_value() == "auto")
            check("项6 首次干净版面＝自动",
                  canvas.locator("#edLayoutEngine").input_value() == "auto")
            check("项6 首次 prefs 未落盘", not prefs_file.exists())

            # ---------- 项1：配置页①在②砍 ----------
            canvas.locator("#epModelConfigList").click()
            view = canvas.locator("#edModelConfigModal")
            expect(view).to_be_visible(timeout=10000)
            expect(canvas.locator(".ep-mt-row").first).to_be_visible(timeout=15000)
            auto_box = canvas.locator(".ep-model-config-auto-seats")
            expect(auto_box).to_be_visible(timeout=10000)
            auto_label = auto_box.locator(".ep-model-config-defaults-label").inner_text()
            check("项1 ①自动设置上页（改名成功）", "自动设置" in auto_label, auto_label)
            check("项1 ②默认引擎整行已砍（无独立默认组）",
                  canvas.locator(".ep-model-config-defaults:not(.ep-model-config-auto-seats)").count() == 0)
            config_text = canvas.locator("#edModelConfigModal").inner_text()
            check("项1 配置页无「默认引擎」字样", "默认引擎" not in config_text)
            page.screenshot(path=str(shots / "01-config-auto-seats.png"))
            canvas.locator("#edModelConfigBack").click()
            expect(view).to_be_hidden(timeout=5000)

            # ---------- 项2：自动置顶＋两条禁用表头＋全平铺；版面平铺 ----------
            rec = canvas.locator("#edRecognizeEngine").evaluate("""
                sel => {
                  const opts = Array.from(sel.options);
                  const heads = [];
                  opts.forEach((o, i) => {
                    if (o.disabled && o.textContent.startsWith("——")) {
                      heads.push({index: i, text: o.textContent});
                    }
                  });
                  const groups = heads.map((h, k) => ({
                    head: h.text,
                    values: opts.slice(
                      h.index + 1,
                      k + 1 < heads.length ? heads[k + 1].index : opts.length
                    ).map(o => o.value)
                  }));
                  return {
                    values: opts.map(o => o.value),
                    texts: opts.map(o => o.textContent),
                    heads: heads.map(h => ({index: h.index, text: h.text})),
                    groups: groups
                  };
                }
            """)
            header_texts = [h["text"] for h in rec["heads"]]
            check("项2 两条禁用表头＝—— 整题OCR ——／—— 文字直取＋公式 ——",
                  header_texts == GROUP_HEADS, header_texts)
            check("项2 识别下拉零 optgroup（全平铺）",
                  canvas.locator("#edRecognizeEngine optgroup").count() == 0)
            check("项2 自动单独置顶（第 0 项且在任何表头之前）",
                  bool(rec["values"]) and rec["values"][0] == "auto"
                  and all(h["index"] > 0 for h in rec["heads"]), rec["values"][:3])
            combo_vals = rec["groups"][1]["values"] if len(rec["groups"]) > 1 else []
            whole_vals = rec["groups"][0]["values"] if rec["groups"] else []
            check("项2 底组＝registry 实际就绪组合（本机装几座 VLM 就几条）",
                  sorted(combo_vals) == sorted(ready_combos),
                  {"dropdown": combo_vals, "registry_ready": ready_combos})
            check("项2 顶组＝就绪整题座（不含 auto／组合）",
                  sorted(whole_vals) == sorted(whole_ready)
                  and "auto" not in whole_vals and not (set(whole_vals) & set(declared_combos)),
                  {"dropdown": whole_vals, "registry_ready": whole_ready})
            check("项2 条目无「组合路」与「文字直取＋公式·」前缀",
                  not any("组合路" in t or "文字直取＋公式·" in t for t in rec["texts"]),
                  [t for t in rec["texts"] if "组合路" in t or "文字直取＋公式·" in t])
            check("项2 版面下拉平铺无 optgroup",
                  canvas.locator("#edLayoutEngine optgroup").count() == 0)
            # 原生下拉展开层抓不到，克隆到固定浮层拉成 listbox 截图（内容仍来自真 select）。
            def listbox_shot(select_id: str, name: str) -> None:
                canvas.locator("#" + select_id).evaluate("""
                    sel => {
                      const clone = sel.cloneNode(true);
                      clone.id = "edProbeListbox";
                      clone.size = clone.options.length;
                      clone.style.cssText = "position:fixed;left:24px;top:24px;width:360px;"
                        + "height:auto;z-index:99999;background:#fff;border:1px solid #888;"
                        + "box-shadow:0 4px 18px rgba(0,0,0,.25);font-size:14px;";
                      document.body.appendChild(clone);
                    }
                """)
                page.screenshot(path=str(shots / name))
                canvas.locator("#edProbeListbox").evaluate("node => node.remove()")

            listbox_shot("edRecognizeEngine", "02-recognize-flat.png")
            listbox_shot("edLayoutEngine", "02b-layout-flat.png")

            # ---------- 项7：纯图卷进筐→组合项置灰＋人话 ----------
            canvas.locator("#edBasketFile").set_input_files(str(png_file))
            expect(canvas.locator("#edBasketList li").first).to_be_visible(timeout=10000)
            page.wait_for_timeout(400)
            gray = canvas.locator("#edRecognizeEngine option[value='%s']" % pick).evaluate(
                "n => ({disabled: n.disabled, title: n.title})")
            check("项7 纯图卷组合路置灰", gray["disabled"] is True, gray)
            check("项7 置灰带人话（纯图卷·文字直取无从谈起）",
                  "纯图卷" in gray["title"] and "文字直取" in gray["title"], gray["title"])
            whole_gray = canvas.locator("#edRecognizeEngine option[value='mineru_local']").evaluate(
                "n => n.disabled") if canvas.locator(
                    "#edRecognizeEngine option[value='mineru_local']").count() else False
            check("项7 整题座不受纯图卷置灰", whole_gray is False, whole_gray)
            listbox_shot("edRecognizeEngine", "03-pure-image-gray.png")
            page.reload(wait_until="networkidle")
            canvas = open_plugin(page)

            # ---------- 项3：停用组合座→下拉摘除→启用恢复 ----------
            # 组合条目不进配置四栏表（ui_model_table 滤 combo），老师经勾选代笔停用；
            # applyRegistry 按 entry.enabled 摘除（§0 保持现行隐藏语义）。
            set_prefs({"disabled": [pick]})
            check("项3 停用组合座经代笔落隔离插件目录",
                  pick in toml_io.load(prefs_file, {}).get("disabled", []))
            check("项3 data/ 全树无 model_prefs.toml",
                  not list(data_dir.rglob("model_prefs.toml")))
            page.reload(wait_until="networkidle")
            canvas = open_plugin(page)
            expect(canvas.locator("#edRecognizeEngine option[value='%s']" % pick)).to_have_count(
                0, timeout=15000)
            check("项3 停用后识别下拉摘除 %s" % pick, True)
            page.screenshot(path=str(shots / "03-combo-disabled.png"))
            set_prefs({"disabled": []})
            page.reload(wait_until="networkidle")
            canvas = open_plugin(page)
            expect(canvas.locator("#edRecognizeEngine option[value='%s']" % pick)).to_have_count(
                1, timeout=15000)
            check("项3 启用后识别下拉恢复 %s" % pick, True)

            # ---------- 项4：选座→回写上次→刷新初值＝上次；版面独立；归自动 ----------
            canvas.locator("#edRecognizeEngine").select_option(pick)
            got = wait_prefs("default_recognize", pick)
            check("项4 画布选识别座回写上次（default_recognize）", got == pick, got)
            page.reload(wait_until="networkidle")
            canvas = open_plugin(page)
            check("项4 刷新后识别初值＝上次 %s" % pick,
                  canvas.locator("#edRecognizeEngine").input_value() == pick,
                  canvas.locator("#edRecognizeEngine").input_value())
            canvas.locator("#edLayoutEngine").select_option("yolo")
            got_l = wait_prefs("default_layout", "yolo")
            check("项4 画布选版面座回写上次（default_layout）", got_l == "yolo", got_l)
            check("项4 版面/识别各记各的（改版面不擦识别记忆）",
                  toml_io.load(prefs_file, {}).get("default_recognize") == pick)
            page.reload(wait_until="networkidle")
            canvas = open_plugin(page)
            check("项4 刷新后版面初值＝上次 yolo（独立）",
                  canvas.locator("#edLayoutEngine").input_value() == "yolo")
            check("项4 刷新后识别初值仍＝%s（独立）" % pick,
                  canvas.locator("#edRecognizeEngine").input_value() == pick)
            canvas.locator("#edRecognizeEngine").select_option("auto")
            got_a = wait_prefs("default_recognize", "auto")
            check("项4 识别归自动回写 auto", got_a == "auto", got_a)
            check("项4 归自动不擦版面记忆",
                  toml_io.load(prefs_file, {}).get("default_layout") == "yolo")
            page.screenshot(path=str(shots / "04-last-used.png"))

            # ---------- 项5：存过的座被停用→初值归自动 prefs 不擦→启用恢复 ----------
            set_prefs({"default_recognize": pick, "disabled": [pick]})
            page.reload(wait_until="networkidle")
            canvas = open_plugin(page)
            check("项5 存过的座被停用→识别初值归自动",
                  canvas.locator("#edRecognizeEngine").input_value() == "auto",
                  canvas.locator("#edRecognizeEngine").input_value())
            check("项5 归自动不擦 prefs 记忆（default_recognize 仍 %s）" % pick,
                  toml_io.load(prefs_file, {}).get("default_recognize") == pick,
                  toml_io.load(prefs_file, {}))
            set_prefs({"disabled": []})
            page.reload(wait_until="networkidle")
            canvas = open_plugin(page)
            check("项5 启用后刷新识别初值恢复 %s" % pick,
                  canvas.locator("#edRecognizeEngine").input_value() == pick,
                  canvas.locator("#edRecognizeEngine").input_value())
            page.screenshot(path=str(shots / "05-stored-disabled.png"))
            browser.close()

        # ---------- 项8：三查＋零异常＋零出网 ----------
        counts = {"fetch(": 0, "parent.document": 0, "localStorage": 0}
        for script in sorted((plugin_dir / "dist").glob("*.js")):
            text = script.read_text(encoding="utf-8", errors="replace")
            for needle in counts:
                counts[needle] += text.count(needle)
        check("项8 三查 fetch(/parent.document/localStorage=0",
              all(v == 0 for v in counts.values()), counts)
        check("项8 页面零 JS 异常", not result["page_errors"], result["page_errors"][:5])
        check("项8 全程零 HTTP 失败", not result["http_failures"], result["http_failures"][:5])
        check("项8 零安装请求（出网只由点头发起，本卡零出网）",
              not result["install_requests"], result["install_requests"])
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
        check("项8 收口端口复验关闭", closed, {"port": port})
        orphans = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' "
             "-and $_.CommandLine -like '*--port %s*' } "
             "| Measure-Object | Select-Object -ExpandProperty Count" % port],
            capture_output=True, text=True)
        orphan_count = (orphans.stdout or "").strip()
        check("项8 收口孤儿进程零", orphan_count in ("0", ""), {"port": port, "count": orphan_count})

    evidence = ROOT / ".system_generated" / "engine-dropdown" / tag
    if evidence.exists():
        shutil.rmtree(evidence)
    if shots.exists():
        shutil.copytree(shots, evidence)
        result["evidence"] = str(evidence)

    failed = [c for c in result["checks"] if not c["ok"]]
    result["ok"] = not failed and not result.get("error")
    report = work / "probe.toml"
    report.write_text(toml_io.dumps(result, default=str), encoding="utf-8")
    for c in result["checks"]:
        print("[%s] %s" % ("PASS" if c["ok"] else "FAIL", c["name"]))
    print("ok=%s checks=%d failed=%d" % (result["ok"], len(result["checks"]), len(failed)))
    print("probe:", report)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())