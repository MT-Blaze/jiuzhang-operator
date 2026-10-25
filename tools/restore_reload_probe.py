# -*- coding: utf-8 -*-
"""恢复覆盖插件代码后、**不重启底座**的实际加载效果取证（#18-结 第七条遗留）。

用法：``.venv/Scripts/python.exe tools/restore_reload_probe.py <out_dir_tag>``
（脚本自己在 8784 起隔离服务，跑完关掉）

场景是老师最容易踩空的一格：#17 的备份把 ``plugins/`` 代码一起打包（#18-终 阶段二），
恢复也就真的会把代码盖回去；而恢复端点不像切库/导入那样调度真重启——底座一直在跑。
「盖回去之后界面到底加载什么」当时只验了 UI 提示与重启后的清单，这一支把它量出来。

夹具 ``org.example.restore-reload`` 有两个构建：v1 / v2 的 ``plugin.json``（名字、版本号）
与 ``dist/plugin.js`` 都不同，脚本一执行就把 ``RUN:v1`` / ``RUN:v2`` 写进自己的 DOM
并借底栏带回——**标记来自 JS 执行，不来自 HTML 文本**，所以「旧脚本还在跑」骗不了人。

判据：
  1. 端口独占、隔离底座自起；备份真的把夹具代码收进 ``plugins`` 分组；
  2. v1/v2 盘上指纹不同（否则整轮判据没有意义）；标记随盘上代码走（先自证通道有效）；
  3. 现役页签跑 v2 时走 check/confirm 恢复到 v1：同 PID 同 ``boot_id``（真没重启）、
     盘上逐字节回 v1、``/api/plugins`` 当场回 v1 版本与名字、清单签名变化；
  4. **现役 iframe 仍跑 v2**——旧脚本不主动退场，这是「不重启」的核心实况；
     而 5 秒轮询已把页签标题换成 v1 名：清单是新的、执行的是旧的，两件事同时成立；
  5. 对照通道：现役页签调用宿主自己的 ``JzoStage.rehydratePlugin`` → 当场换成 v1，
     说明让旧脚本退场的是热更新通道，恢复通道并不调它；
  6. 关掉再开同样回到 v1；资源响应头 ``no-cache``（排除浏览器缓存造出的假旧代码）；
  7. 全程宿主页零未捕获 JS 错误；夹具卸载、隔离目录不留插件。
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8784
ORIGIN = f"http://127.0.0.1:{PORT}"
WORKSPACE = f"{ORIGIN}/workspace"
TOKEN = "restore-reload-probe-token"
PLUGIN_ID = "org.example.restore-reload"
NAME_V1 = "恢复覆盖取证"
NAME_V2 = "恢复覆盖取证·改"
LABEL_RE = re.compile(r"RUN:(v\d)")
# 夹具的 engine.host_version 跟着底座真实版本走，免得下次升版这里又变陈旧字面量。
HOST_VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")).group(1)

JS_STATE = """
() => ({
  labels: Array.from(document.querySelectorAll('#wsTabs .ws-tab-label'))
    .map(el => el.textContent.trim()),
  dock: Array.from(document.querySelectorAll('#wsDockLog li')).map(li => li.textContent)
})
"""

JS_OPEN = """
async (pluginId) => {
  const resp = await fetch('/api/plugins', {cache: 'no-store'});
  const data = await resp.json();
  const plugin = (data.plugins || []).find(item => item.id === pluginId);
  if (!plugin || !window.JzoStage || typeof window.JzoStage.openPlugin !== 'function') return false;
  window.JzoStage.openPlugin(plugin);
  return true;
}
"""

JS_CLOSE_FIXTURE = """
(pluginId) => {
  const keys = Array.from(document.querySelectorAll('#wsTabs .ws-tab[data-tab]'))
    .map(el => el.getAttribute('data-tab'))
    .filter(key => key && key.indexOf(pluginId) >= 0);
  keys.forEach(key => window.JzoStage.close(key));
  return keys;
}
"""

JS_REHYDRATE = """
(pluginId) => {
  if (!window.JzoStage || typeof window.JzoStage.rehydratePlugin !== 'function') return 'NO_API';
  return window.JzoStage.rehydratePlugin(pluginId) ? 'TOUCHED' : 'NO_TAB';
}
"""

# 标记由脚本自己写：HTML 里永远只有 INIT，读到 RUN:* 就说明这一版 JS 真的执行过
FIXTURE_JS = (
    '(function(){"use strict";'
    'var P="jzo-plugin/1";'
    'var text="RUN:%s";'
    'document.getElementById("mark").textContent=text;'
    'try{window.parent.postMessage({protocol:P,kind:"notification",event:"region.dock",'
    'payload:{text:"[restore] "+text}},"*");}catch(e){}'
    'window.addEventListener("message",function(e){'
    'var m=e.data;if(!m||m.protocol!==P||m.kind!=="request")return;'
    'try{e.source.postMessage({protocol:P,id:m.id,kind:"response",ok:true,'
    'result:{ready:true,plugin_id:"%s"}},"*");}catch(x){}'
    '});})();'
)


def build_zip(label: str, version: str, name: str) -> bytes:
    """造一个「执行到就把自己是第几版写出来」的夹具包（zip 最外层目录名 == id）。"""
    manifest = {
        "schema_version": "1.0",
        "id": PLUGIN_ID,
        "name": name,
        "version": version,
        "api_version": "1.0",
        "kind": "tool",
        "description": f"军令 #18-结 第七条取证夹具 {label}：只为自己回显「我这一版正在跑」。",
        "author": "九章算子",
        "license": "Apache-2.0",
        "entry": {"frontend": "dist/index.html"},
        "slots": ["stage.center"],
        "capabilities": ["question.render"],
        "permissions": [],
        "stage": {"region": "center", "mode": "takeover", "title": name,
                  "priority": 5, "singleton": False, "weight": "heavy"},
        "bus": {"subscribe": [], "publish": ["region.dock"]},
        "min_host_version": "0.9.0",
        "engine": {"host_version": HOST_VERSION},
    }
    html = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        f"<title>{name}</title></head><body><p id=\"mark\">INIT</p>"
        '<script src="./plugin.js"></script></body></html>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{PLUGIN_ID}/plugin.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr(f"{PLUGIN_ID}/dist/index.html", html)
        zf.writestr(f"{PLUGIN_ID}/dist/plugin.js", FIXTURE_JS % (label, PLUGIN_ID))
        zf.writestr(f"{PLUGIN_ID}/LICENSE", (ROOT / "LICENSE").read_text(encoding="utf-8"))
    return buf.getvalue()


def api(method: str, path: str, body=None, blob: bytes | None = None):
    data = blob if blob is not None else (
        json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None)
    request = urllib.request.Request(ORIGIN + path, data=data, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("X-JZO-Token", TOKEN)
    if data is not None and blob is None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=120) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8") or "{}")


def api_status(method: str, path: str, body=None, blob: bytes | None = None) -> tuple[int, dict]:
    try:
        return api(method, path, body=body, blob=blob)
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, {"detail": raw}


def fingerprint(plugin_dir: Path) -> dict[str, str]:
    """盘上指纹：只用来证明「代码真的被盖回去了」，不经 HTTP、不混入缓存变量。"""
    out = {}
    for relative in ("plugin.json", "dist/plugin.js", "dist/index.html"):
        path = plugin_dir / relative
        out[relative] = (hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                         if path.is_file() else "missing")
    return out


def wait_port(deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.5)
    return False


def marker(page) -> str:
    frame = page.frame_locator(".ws-plugin-frame")
    try:
        text = (frame.locator("#mark").text_content(timeout=15000) or "").strip()
    except Exception as exc:  # noqa: BLE001 - 读不到标记本身就是一条红判据，别把整轮炸掉
        return f"ERR:{type(exc).__name__}"
    match = LABEL_RE.search(text)
    return match.group(1) if match else text


def dump(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "restore_reload_probe" / tag
    out.mkdir(parents=True, exist_ok=True)
    work = out / "isolated"
    data_dir, plugins_dir = work / "data", work / "plugins"
    fixture_dir = plugins_dir / PLUGIN_ID
    for path in (data_dir, plugins_dir):
        path.mkdir(parents=True, exist_ok=True)

    checks: list[dict] = []
    evidence: dict = {}
    raw: dict = {}
    crashed: list[str] = []

    def call(method: str, path: str, body=None, blob: bytes | None = None, key: str = ""):
        """所有 HTTP 都过这一手：判据打在猜想的字段上，等于没取证——先把回包留下。"""
        status, payload = api_status(method, path, body=body, blob=blob)
        raw[key or f"{method} {path}"] = {"status": status, "payload": payload}
        return status, payload

    def check(name: str, passed, detail="") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": str(detail)[:400]})

    def open_fixture(page) -> bool:
        if not page.evaluate(JS_OPEN, PLUGIN_ID):
            return False
        deadline = time.time() + 15
        while time.time() < deadline:
            if page.evaluate("() => document.querySelectorAll('.ws-plugin-frame').length") >= 1:
                page.wait_for_timeout(700)
                return True
            page.wait_for_timeout(400)
        return False

    server = None
    browser = None
    try:
        with socket.socket() as probe:
            occupied = probe.connect_ex(("127.0.0.1", PORT)) == 0
        check("00 端口 8784 空闲（本探针独占，绝不打到别人的底座）", not occupied,
              "端口已被占用：上一轮孤儿进程还在，本轮红绿都不算数" if occupied else "OK")
        if occupied:
            raise RuntimeError("port occupied")

        env = dict(os.environ)
        env["JZO_DATA_DIR"] = str(data_dir)
        env["JZO_PLUGINS_DIR"] = str(plugins_dir)
        env["JZO_STATE_FILE"] = str(data_dir / "workspaces" / "default" / "plugin_state.json")
        env["JZO_LOCAL_TOKEN"] = TOKEN
        env["JZO_RESTART_DISABLED"] = "1"
        env.pop("JZO_AI_API_KEY", None)
        env.pop("JZO_AI_BASE_URL", None)
        log_path = out / "host.log"
        server = subprocess.Popen(
            [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(PORT)],
            cwd=str(ROOT), env=env, stdout=log_path.open("wb"), stderr=subprocess.STDOUT)

        check("01 隔离底座起来了", wait_port(60), f"log={log_path}")
        health = api("GET", "/healthz")[1]
        boot_before, pid_before = health.get("boot_id"), server.pid
        check("02 记下恢复前的进程身份（同 PID 同 boot_id 才叫没重启）",
              bool(boot_before) and server.poll() is None, f"boot={boot_before} pid={pid_before}")

        status, install_v1 = call("POST", "/api/plugins/install?replace=true",
                             blob=build_zip("v1", "1.0.0", NAME_V1), key="install_v1")
        check("03 夹具 v1 装上", status == 200 and install_v1.get("installed") is True,
              install_v1.get("detail") or install_v1.get("plugin", {}).get("id"))
        fp_v1 = fingerprint(fixture_dir)
        evidence["fingerprint_v1"] = fp_v1

        status, config = call("POST", "/api/settings/backup/config", {"local_enabled": True}, key="backup_config")
        check("04 本区开启本地备份", status == 200 and config.get("local_enabled") is True,
              config.get("detail", ""))
        status, backup_run = call("POST", "/api/settings/backup/run", key="backup_run")
        local = backup_run.get("local") or {}
        stem_match = re.match(r"backup_(.+)\.zst$", str(local.get("package_name") or ""))
        stem = stem_match.group(1) if stem_match else ""
        check("05 备份真的产出包", status == 200 and backup_run.get("ok") is True and bool(stem),
              local.get("package_name") or backup_run.get("detail"))

        manifest_path = Path(str(local.get("manifest") or "")) if local.get("manifest") else None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path else {}
        fixture_paths = [item.get("path") for item in (manifest.get("files") or [])
                         if item.get("category") == "plugins"
                         and str(item.get("path", "")).find(PLUGIN_ID) >= 0]
        check("06 备份清单把夹具代码收进 plugins 分组（阶段二的扩容真覆盖代码）",
              len(fixture_paths) >= 3, f"{len(fixture_paths)} 条：{fixture_paths}")

        pw = sync_playwright().start()
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 860})
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(WORKSPACE, wait_until="networkidle")
        page.wait_for_timeout(1500)

        check("07 打开 v1 页签：沙箱里执行的是 v1 代码", open_fixture(page) and marker(page) == "v1",
              marker(page))
        dock = page.evaluate(JS_STATE)["dock"]
        check("08 底栏带回夹具自报的 RUN:v1（第二通道，不靠读 iframe）",
              any("RUN:v1" in line for line in dock), dock[-1] if dock else "")

        status, install_v2 = call("POST", "/api/plugins/install?replace=true",
                             blob=build_zip("v2", "2.0.0", NAME_V2), key="install_v2")
        check("09 夹具 v2 覆盖安装（replace）", status == 200 and install_v2.get("installed") is True,
              install_v2.get("detail", ""))
        fp_v2 = fingerprint(fixture_dir)
        evidence["fingerprint_v2"] = fp_v2
        check("10 v1/v2 盘上指纹不同（否则整轮判据没有意义）",
              fp_v1 != fp_v2, f"v1={list(fp_v1.values())} v2={list(fp_v2.values())}")

        closed = page.evaluate(JS_CLOSE_FIXTURE, PLUGIN_ID)
        page.wait_for_timeout(900)
        evidence["closed_tabs_1"] = closed
        check("11 重开页签后沙箱跑 v2（标记随盘上代码走，自证取证通道有效）",
              open_fixture(page) and marker(page) == "v2", marker(page))
        page.wait_for_timeout(6500)
        labels = page.evaluate(JS_STATE)["labels"]
        check("12 不刷新页面，5 秒轮询把页签标题带到 v2 名", any(NAME_V2 in t for t in labels), labels)

        sig_before = api("GET", "/api/plugins")[1].get("signature")
        status, plan = call("POST", "/api/settings/backup/restore/check",
                    {"source": "local", "stem": stem, "files": fixture_paths}, key="restore_check")
        plan_id, selected = plan.get("plan_id", ""), plan.get("selection") or []
        check("13 恢复前校验通过并选中夹具代码条目",
              status == 200 and bool(plan_id) and any(PLUGIN_ID in str(rel) for rel in selected),
              f"selection={len(selected)} 条 · {plan.get('detail', '')}")

        status, confirmed = call("POST", "/api/settings/backup/restore/confirm",
                         {"plan_id": plan_id, "confirm": "确认恢复"}, key="restore_confirm")
        check("14 二次确认后恢复执行成功", status == 200 and confirmed.get("ok") is True,
              confirmed.get("detail") or f"restored={confirmed.get('restored')}")

        health_after = api("GET", "/healthz")[1]
        check("15 恢复后底座没重启：同 PID、同 boot_id（第七条要的就是这一格）",
              server.poll() is None and health_after.get("boot_id") == boot_before,
              f"pid {pid_before}->{server.pid} boot {boot_before}->{health_after.get('boot_id')}")
        check("16 盘上代码逐字节回到 v1", fingerprint(fixture_dir) == fp_v1,
              str(fingerprint(fixture_dir)))

        listing = api("GET", "/api/plugins")[1]
        entry = next((item for item in listing.get("plugins", []) if item.get("id") == PLUGIN_ID), {})
        check("17 清单当场回 v1：/api/plugins 每次读盘，不必重启",
              entry.get("version") == "1.0.0" and entry.get("name") == NAME_V1,
              f"{entry.get('name')}@{entry.get('version')}")
        check("18 清单签名与 v2 时期已换（热插拔判据按 mtime/size 生效）",
              bool(listing.get("signature")) and listing.get("signature") != sig_before,
              f"{sig_before} -> {listing.get('signature')}")

        check("19 现役 iframe 仍在跑 v2：旧脚本不主动退场（不重启的真实后果）",
              marker(page) == "v2", marker(page))
        page.wait_for_timeout(6500)
        labels = page.evaluate(JS_STATE)["labels"]
        check("20 轮询后标题当场回 v1 名而代码还是旧的（清单新、执行旧同时成立）",
              any(t == NAME_V1 for t in labels) and marker(page) == "v2", f"{labels} 标记={marker(page)}")

        rehydrated = page.evaluate(JS_REHYDRATE, PLUGIN_ID)
        page.wait_for_timeout(3500)
        after = marker(page) if rehydrated == "TOUCHED" else ""
        dock = page.evaluate(JS_STATE)["dock"]
        check("21 对照：宿主 rehydratePlugin 让现役页当场换成 v1（恢复通道不调它）",
              rehydrated == "TOUCHED" and after == "v1",
              f"返回={rehydrated} 现标记={after} 末行底栏={dock[-1] if dock else ''}")

        evidence["closed_tabs_2"] = page.evaluate(JS_CLOSE_FIXTURE, PLUGIN_ID)
        page.wait_for_timeout(900)
        check("22 关掉再开同样回到 v1（重挂走磁盘直读）",
              open_fixture(page) and marker(page) == "v1", marker(page))

        with urllib.request.urlopen(f"{ORIGIN}/plugin-assets/{PLUGIN_ID}/dist/plugin.js",
                                    timeout=20) as response:
            head = {k.lower(): v for k, v in response.headers.items()}
        check("23 插件资源响应头 no-cache（浏览器不会拿缓存冒充旧代码）",
              head.get("cache-control") == "no-cache",
              f"cache-control={head.get('cache-control')} etag={head.get('etag')}")

        page.screenshot(path=str(out / "final_state.png"), full_page=True)
        check("24 全程宿主页零未捕获 JS 错误", not errors, errors[:2])
        evidence["dock_tail"] = dock[-4:]
        pw.stop()
        browser = None

        status, uninstalled = call("DELETE", f"/api/plugins/{PLUGIN_ID}?keep_data=true", key="uninstall")
        check("25 夹具卸载、隔离目录不留插件",
              status == 200 and not fixture_dir.exists(), uninstalled.get("detail", ""))
    except Exception as exc:  # noqa: BLE001 - 崩了也要把已有判据带出去
        crashed.append(repr(exc))
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()

    passed = sum(1 for item in checks if item["passed"])
    result = {"tag": tag, "total": len(checks), "passed": passed,
              "crashed": crashed, "checks": checks, "evidence": evidence, "raw_api": raw}
    dump(out / "probe.json", result)
    print(json.dumps({"total": result["total"], "passed": passed}, ensure_ascii=False))
    for item in checks:
        print(("PASS " if item["passed"] else "FAIL ") + item["name"] + " | " + item["detail"])
    if crashed:
        print("CRASHED " + " ; ".join(crashed))
    return result


if __name__ == "__main__":
    outcome = run(sys.argv[1] if len(sys.argv) > 1 else "run")
    sys.exit(0 if outcome["passed"] == outcome["total"] and not outcome["crashed"] else 1)
