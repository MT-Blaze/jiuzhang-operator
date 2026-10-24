# -*- coding: utf-8 -*-
"""启动行为真机取证（军令 #11 阶段三）：老师选的默认界面能不能真的落地。

用法：``.venv/Scripts/python.exe tools/startup_probe.py <out_dir_tag>``
（脚本自己在 8782 起隔离服务，跑完关掉）

隔离口径：``JZO_DATA_DIR`` 与 ``JZO_PLUGINS_DIR`` 指向
``.system_generated/startup-probe/<tag>/``，不碰开发者本机 ``data/`` 与仓库 ``plugins/``
（数据看板插件只读复制进隔离目录）。

判据：
  1. 未配置时默认落在欢迎页；POST 无令牌 401、指向不存在插件 400（写入严格）；
  2. 配好「数据看板」后打开工作台，**自动**进入看板页签、左栏对应项高亮；
  3. 插件被停用 → 后端回退 chat 并给原因；刷新页面停在自由对话，
     对话区出现 warn 气泡、右栏操作历史记一笔（不许静默）；
  4. 插件被卸载（目录移走）→ 同款优雅回退，配置原地保留，装回即自动恢复；
  5. 设置页「系统设置」分区可选可存：下拉列出已启用插件，点保存真的落盘；
  6. 全程宿主页无未捕获 JS 错误。
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8782
BASE = f"http://127.0.0.1:{PORT}/workspace"
SETTINGS = f"http://127.0.0.1:{PORT}/settings?panel=system"
PLUGIN_ID = "org.jiuzhang.dashboard"
TOKEN = "startup-probe-token"

JS_STATE = """
() => {
  const tabs = Array.from(document.querySelectorAll('#wsTabs .ws-tab'))
    .map(t => t.getAttribute('data-tab'));
  const title = document.getElementById('wsStageTitle');
  const active = document.querySelector('#wsPluginList .ws-plugin-item[aria-current="true"]');
  const thread = document.getElementById('wsThread');
  // data-tone 挂在气泡本体上（外层 .ws-msg-sys 只是行容器），别选错层级
  const warns = thread
    ? Array.from(thread.querySelectorAll('[data-tone="warn"]'))
        .map(n => n.textContent.replace(/\\s+/g, ' ').trim())
    : [];
  const dock = document.getElementById('wsDockLog');
  return {
    tabs: tabs,
    stageTitle: title ? title.textContent.replace(/\\s+/g, ' ').trim() : '',
    activePluginId: active ? active.getAttribute('data-plugin-id') : null,
    warns: warns,
    dockText: dock ? dock.textContent.replace(/\\s+/g, ' ') : ''
  };
}
"""


def wait_port(deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.5)
    return False


def call(method: str, path: str, body=None, token: bool = False):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, method=method)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("X-JZO-Token", TOKEN)
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, json.loads(payload or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": payload}


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "startup-probe" / tag
    data_dir = out / "data"
    plugins_dir = out / "plugins"
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)

    report = {"tag": tag, "checks": [], "console": [], "errors": [], "shots": [], "notes": {}}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
        return bool(ok)

    shutil.copytree(ROOT / "plugins" / PLUGIN_ID, plugins_dir / PLUGIN_ID)
    check("数据看板插件复制进隔离目录", (plugins_dir / PLUGIN_ID / "plugin.json").is_file())

    env = dict(os.environ)
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env.pop("JZO_AI_API_KEY", None)
    env.pop("JZO_AI_BASE_URL", None)

    # 服务日志必须落文件而不是 PIPE：PIPE 没人读，写满管道缓冲后 uvicorn 会
    # 整体阻塞在 write() 上——表现是「所有请求（含 /healthz）一起超时」，
    # 看着像底座死锁，其实是探针自己掐住了服务的喉咙（p3b/p3c 两轮假失败就是这么来的）。
    server_log_path = out / "server.log"
    server_log = open(server_log_path, "w", encoding="utf-8", errors="replace")
    server = subprocess.Popen(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT), env=env,
        stdout=server_log, stderr=subprocess.STDOUT)

    try:
        if not wait_port(40):
            check("隔离服务起在 8782", False, "服务未在 40 秒内监听")
            return finish(report, out)
        check("隔离服务起在 8782", True, f"data={data_dir}")
        time.sleep(1.5)

        # ---------- 后端契约：默认态、守门、写入严格 ----------
        status, body = call("GET", "/api/startup")
        check("未配置时默认落欢迎页", status == 200 and body.get("effective") == "chat",
              json.dumps({k: body.get(k) for k in ("target", "effective", "fallback_reason")}, ensure_ascii=False))
        check("候选清单遍历已启用插件", PLUGIN_ID in [c.get("id") for c in (body.get("candidates") or [])],
              json.dumps(body.get("candidates"), ensure_ascii=False)[:200])

        status, _ = call("POST", "/api/startup", {"target": "plugin:" + PLUGIN_ID})
        check("保存启动行为不带令牌必被拦（401）", status == 401, f"status={status}")
        status, body = call("POST", "/api/startup", {"target": "plugin:org.example.gone"}, token=True)
        check("指向未安装插件必被拒（400，不落盘）", status == 400,
              f"status={status} detail={json.dumps(body, ensure_ascii=False)[:160]}")
        check("被拒的目标没有污染配置文件", not (data_dir / "startup.json").is_file())

        status, body = call("POST", "/api/startup", {"target": "plugin:" + PLUGIN_ID}, token=True)
        check("带令牌保存成功并落盘",
              status == 200 and body.get("effective") == "plugin:" + PLUGIN_ID
              and (data_dir / "startup.json").is_file(),
              json.dumps({k: body.get(k) for k in ("target", "effective", "plugin_name")}, ensure_ascii=False))
        report["notes"]["startup_json"] = (data_dir / "startup.json").read_text(encoding="utf-8").strip()

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: report["console"].append({"type": m.type, "text": m.text[:300]}))
            page.on("pageerror", lambda e: report["errors"].append(str(e)[:300]))

            def snap(step, target=None):
                shot_page = target or page
                png = out / f"{step}.png"
                shot_page.screenshot(path=str(png))
                report["shots"].append(str(png))

            # ---------- 黄金路径：开机直接落在老师选的界面 ----------
            page.goto(BASE, wait_until="networkidle")
            page.wait_for_timeout(2500)
            state = page.evaluate(JS_STATE)
            report["notes"]["boot_into_plugin"] = state
            check("启动自动进入所选插件页签（无需手点）", f"plugin:{PLUGIN_ID}" in state["tabs"],
                  json.dumps(state["tabs"]))
            check("舞台标题就是所选插件", "数据看板" in state["stageTitle"], state["stageTitle"])
            check("左栏对应条目高亮（aria-current）", state["activePluginId"] == PLUGIN_ID,
                  str(state["activePluginId"]))
            snap("10-boot-into-dashboard")

            # ---------- 失效回退：停用 ----------
            call("POST", f"/api/plugins/{PLUGIN_ID}/enabled", {"enabled": False}, token=True)
            status, body = call("GET", "/api/startup")
            check("插件停用后后端回退欢迎页并说明原因",
                  status == 200 and body.get("effective") == "chat" and "已停用" in body.get("fallback_reason", ""),
                  json.dumps({k: body.get(k) for k in ("target", "effective", "fallback_reason")}, ensure_ascii=False))
            page.goto(BASE, wait_until="networkidle")
            page.wait_for_timeout(2000)
            state = page.evaluate(JS_STATE)
            report["notes"]["fallback_disabled"] = state
            check("停用后启动停在自由对话（不开失效插件）",
                  f"plugin:{PLUGIN_ID}" not in state["tabs"] and "自由对话" in state["stageTitle"],
                  f"tabs={state['tabs']} title={state['stageTitle']}")
            check("回退原因在对话区如实播报（warn 气泡）",
                  any("已停用" in w for w in state["warns"]), json.dumps(state["warns"], ensure_ascii=False)[:200])
            check("回退落到底栏输出日志区（不静默）", "启动行为回退" in state["dockText"],
                  state["dockText"][-260:])
            snap("20-fallback-disabled")

            call("POST", f"/api/plugins/{PLUGIN_ID}/enabled", {"enabled": True}, token=True)
            status, body = call("GET", "/api/startup")
            check("重新启用后原配置自动恢复生效",
                  body.get("effective") == "plugin:" + PLUGIN_ID and not body.get("fallback_reason"),
                  json.dumps({k: body.get(k) for k in ("effective", "fallback_reason")}, ensure_ascii=False))

            # ---------- 失效回退：卸载（目录移走） ----------
            backup = out / "backup-dashboard"
            shutil.move(str(plugins_dir / PLUGIN_ID), str(backup))
            try:
                status, body = call("GET", "/api/startup")
                check("插件被卸载后回退欢迎页并说明原因",
                      status == 200 and body.get("effective") == "chat" and "已卸载" in body.get("fallback_reason", "")
                      and body.get("target") == "plugin:" + PLUGIN_ID,
                      json.dumps({k: body.get(k) for k in ("target", "effective", "fallback_reason")}, ensure_ascii=False))
                page.goto(BASE, wait_until="networkidle")
                page.wait_for_timeout(2000)
                state = page.evaluate(JS_STATE)
                report["notes"]["fallback_uninstalled"] = state
                check("卸载后启动不炸、停在自由对话",
                      "自由对话" in state["stageTitle"] and len(report["errors"]) == 0,
                      f"title={state['stageTitle']} errors={report['errors'][:2]}")
                check("卸载回退同样如实播报",
                      any("已卸载" in w for w in state["warns"]), json.dumps(state["warns"], ensure_ascii=False)[:200])
                snap("30-fallback-uninstalled")
            finally:
                shutil.move(str(backup), str(plugins_dir / PLUGIN_ID))

            # ---------- 设置页：系统设置分区可选可存 ----------
            call("POST", "/api/startup", {"target": "chat"}, token=True)
            # 工作台那个页面已经注册了 service worker，同一页再导航去 /settings 会被
            # sw 拖到 goto 超时（实测：干净上下文里同一 URL 秒开）。设置页取证因此
            # 换一个全新的浏览器上下文——sw 注册按上下文隔离，互不干扰。
            settings_ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            spage = settings_ctx.new_page()
            spage.on("pageerror", lambda e: report["errors"].append("settings: " + str(e)[:260]))
            try:
                spage.goto(SETTINGS, wait_until="domcontentloaded", timeout=20000)
            except Exception as exc:  # noqa: BLE001
                # 先取证再重试：到底是服务端卡死，还是浏览器导航事件没等到
                report["notes"]["settings_goto_error"] = repr(exc)[:300]
                alive = {}
                for probe_path in ("/healthz", "/api/startup", "/settings", "/static/js/settings.js"):
                    started = time.time()
                    try:
                        with urllib.request.urlopen(
                                f"http://127.0.0.1:{PORT}{probe_path}", timeout=10) as resp:
                            alive[probe_path] = f"{resp.status} in {time.time() - started:.2f}s"
                    except Exception as probe_exc:  # noqa: BLE001
                        alive[probe_path] = f"ERR after {time.time() - started:.2f}s: {probe_exc!r}"[:140]
                report["notes"]["backend_alive_after_timeout"] = alive
                spage.goto(SETTINGS, wait_until="commit", timeout=20000)
                spage.wait_for_timeout(3000)
            spage.wait_for_timeout(1500)
            panel = spage.evaluate("""
            () => {
              const nav = document.getElementById('stNavSystem');
              const panel = document.getElementById('stPanelSystem');
              const select = document.getElementById('startupTarget');
              const now = document.getElementById('startupNow');
              return {
                navExists: !!nav,
                navActive: nav ? nav.classList.contains('is-active') : false,
                panelVisible: panel ? !panel.hidden : false,
                options: select ? Array.from(select.options).map(o => ({ v: o.value, t: o.textContent.trim() })) : [],
                value: select ? select.value : null,
                nowText: now ? now.textContent.replace(/\\s+/g, ' ').trim() : ''
              };
            }
            """)
            report["notes"]["settings_panel"] = panel
            check("设置页有「系统设置」分区且被 ?panel=system 选中",
                  panel["navExists"] and panel["navActive"] and panel["panelVisible"],
                  json.dumps({k: panel[k] for k in ("navExists", "navActive", "panelVisible")}))
            values = [o["v"] for o in panel["options"]]
            check("下拉数据源含默认欢迎页与已启用插件",
                  "chat" in values and ("plugin:" + PLUGIN_ID) in values, json.dumps(values, ensure_ascii=False))
            check("下拉恰为「欢迎页 + 隔离目录里那一个已启用插件」",
                  values == ["chat", "plugin:" + PLUGIN_ID], json.dumps(values, ensure_ascii=False))
            check("当前生效状态如实回显", bool(panel["nowText"]), panel["nowText"][:160])
            snap("40-settings-system", spage)

            spage.select_option("#startupTarget", "plugin:" + PLUGIN_ID)
            spage.click("#startupSaveBtn")
            spage.wait_for_timeout(1500)
            saved = spage.evaluate("""
            () => {
              const status = document.getElementById('startupStatus');
              const now = document.getElementById('startupNow');
              return { status: status ? status.textContent.replace(/\\s+/g, ' ').trim() : '',
                       tone: status ? status.getAttribute('data-tone') : '',
                       now: now ? now.textContent.replace(/\\s+/g, ' ').trim() : '' };
            }
            """)
            report["notes"]["settings_saved"] = saved
            check("点【保存启动行为】成功回显", "已保存" in saved["status"] and saved["tone"] == "ok",
                  json.dumps(saved, ensure_ascii=False)[:200])
            snap("50-settings-saved", spage)
            settings_ctx.close()

            status, body = call("GET", "/api/startup")
            check("UI 保存真的落盘（后端读到同一目标）",
                  body.get("effective") == "plugin:" + PLUGIN_ID,
                  json.dumps({k: body.get(k) for k in ("target", "effective")}, ensure_ascii=False))

            # 保存后再开一次工作台，闭环验证「设置页选的 = 下次启动落地的」
            page.goto(BASE, wait_until="networkidle")
            page.wait_for_timeout(2500)
            state = page.evaluate(JS_STATE)
            check("设置页保存后启动即落在所选插件",
                  f"plugin:{PLUGIN_ID}" in state["tabs"] and state["activePluginId"] == PLUGIN_ID,
                  f"tabs={state['tabs']} active={state['activePluginId']}")
            snap("60-boot-after-save")

            check("宿主页无未捕获 JS 错误", len(report["errors"]) == 0, report["errors"][:3])
            browser.close()
    except Exception as exc:  # noqa: BLE001
        # 探针自己出意外也要把已跑完的判据落盘，不让人只看到 traceback
        report["fatal"] = repr(exc)[:600]
        check("探针自身未崩溃", False, repr(exc)[:300])
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:  # noqa: BLE001
            server.kill()
        server_log.close()
        try:
            tail = server_log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            tail = ""
        report["notes"]["server_log_tail"] = tail[-2000:]
        report["notes"]["server_log"] = str(server_log_path)

    return finish(report, out)


def finish(report: dict, out: Path) -> dict:
    total = len(report["checks"])
    passed = sum(1 for c in report["checks"] if c["ok"])
    report["summary"] = {"total": total, "passed": passed, "failed": total - passed,
                         "pageErrors": len(report["errors"])}
    out.mkdir(parents=True, exist_ok=True)
    (out / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["out_dir"] = str(out)
    return report


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    result = run(tag)
    print(json.dumps(result["summary"], ensure_ascii=False))
    for c in result["checks"]:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + " :: " + c["detail"][:180])
    print("out_dir:", result.get("out_dir"))
    sys.exit(0 if result["summary"]["failed"] == 0 else 1)
