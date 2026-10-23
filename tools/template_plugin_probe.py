# -*- coding: utf-8 -*-
"""第三方模板插件真机取证：装进去能不能跑通宿主 API 与事件总线。

用法：``.venv/Scripts/python.exe tools/template_plugin_probe.py <out_dir_tag>``
（脚本自己在 8779 起隔离服务，跑完关掉）

隔离口径：``JZO_DATA_DIR`` 与 ``JZO_PLUGINS_DIR`` 指向 ``.system_generated/template-probe/<tag>/``，
不碰开发者本机的 ``data/`` 与 ``plugins/``。插件本体从 ``examples/template-plugin.zip`` 解出，
验的就是老师手里那份包。

判据来自 2026-10-23 军令 #06 与 #07：
  1. 模板 zip 解进插件目录后被底座发现、零拒收；
  2. 点左栏入口开画布页签，iframe 沙箱只有 allow-scripts，``plugin.activate`` 30s 内回 ready；
  3. 沙箱内点【取一页公共真题】→ ``bank.review`` 请求真的走到宿主并拿到同 id 回执（不是超时）；
  4. 沙箱内点【向底栏广播】→ ``region.dock`` 经 bus.publish 白名单落进底栏日志；
  5. 全程宿主页无未捕获 JS 错误；
  6.（#07 批复 2）从沙箱手造一条带点号 id 的 request：宿主必须**当场**回 ``ok:false`` +
     ``code:"BAD_REQUEST_ID"``，并在底栏记一笔 ``plugin.error``——不再静默丢弃。

``PROBE_CORE_BANK=1`` 时把本机官方题库插件复制进隔离目录，多一条「真取到题目并渲染卡片」的黄金路径判据。
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8779
BASE = f"http://127.0.0.1:{PORT}/workspace"
PLUGIN_ID = "org.example.template"
ZIP_PATH = ROOT / "examples" / "template-plugin.zip"

JS_STATE = """
() => {
  const frame = document.querySelector('.ws-plugin-frame');
  const panel = document.querySelector('.ws-tab-panel[data-tab="plugin:%ID%"]');
  const dock = document.getElementById('wsDockLog');
  return {
    tabs: Array.from(document.querySelectorAll('#wsTabs .ws-tab')).map(t => t.getAttribute('data-tab')),
    sidebarHasTemplate: Array.from(document.querySelectorAll('#wsPluginList .ws-plugin-item'))
      .some(b => b.textContent.indexOf('模板') >= 0),
    frameSandbox: frame ? frame.getAttribute('sandbox') : null,
    frameSrc: frame ? (frame.getAttribute('src') || '').slice(0, 90) : null,
    panelError: panel ? ((panel.querySelector('.ws-frame-error') || {}).textContent || '') : '无页签面板',
    panelNote: panel ? ((panel.querySelector('.ws-frame-note') || {}).textContent || '') : '',
    dockText: dock ? dock.textContent.replace(/\\s+/g, ' ').slice(-600) : ''
  };
}
""".replace("%ID%", PLUGIN_ID)


def wait_port(deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.5)
    return False


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "template-probe" / tag
    data_dir = out / "data"
    plugins_dir = out / "plugins"
    data_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)

    report = {"tag": tag, "checks": [], "console": [], "errors": [], "shots": [], "notes": {}}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
        return bool(ok)

    with zipfile.ZipFile(ZIP_PATH) as zf:
        zf.extractall(plugins_dir)
    check("模板 zip 解出 plugin.json", (plugins_dir / PLUGIN_ID / "plugin.json").is_file(),
          str(plugins_dir / PLUGIN_ID))

    # PROBE_CORE_BANK=1 时把本机官方题库插件复制进隔离目录，验「取到 N 题」的黄金路径；
    # 只读复制，不碰开发者本机 data/ 与 plugins/。
    if os.environ.get("PROBE_CORE_BANK") == "1":
        source_bank = ROOT / "plugins" / "org.jiuzhang.core-bank"
        if source_bank.is_dir():
            shutil.copytree(source_bank, plugins_dir / "org.jiuzhang.core-bank")
            report["notes"]["core_bank_copied"] = True

    env = dict(os.environ)
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_PORT"] = str(PORT)
    env.pop("JZO_AI_API_KEY", None)
    env.pop("JZO_AI_BASE_URL", None)

    server = subprocess.Popen(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

    try:
        if not wait_port(40):
            check("隔离服务起在 8779", False, "服务未在 40 秒内监听")
            return finish(report, out)
        check("隔离服务起在 8779", True, f"data={data_dir} plugins={plugins_dir}")
        time.sleep(1.5)

        with urllib_stub() as http:
            discovery = http(f"http://127.0.0.1:{PORT}/api/plugins")
        plugins = discovery.get("plugins") or []
        entry = next((p for p in plugins if p.get("id") == PLUGIN_ID), None)
        check("底座发现模板插件（未拒收）", entry is not None,
              f"count={len(plugins)} rejected={json.dumps(discovery.get('rejected'), ensure_ascii=False)}")
        check("清单里的 bus/stage/min_host_version 原样回传",
              bool(entry and entry.get("bus", {}).get("publish") == ["region.dock"]
                   and entry.get("stage") and entry.get("min_host_version") == "0.8.2"),
              json.dumps({k: (entry or {}).get(k) for k in ("bus", "stage", "min_host_version")},
                         ensure_ascii=False))

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: report["console"].append({"type": m.type, "text": m.text[:300]}))
            page.on("pageerror", lambda e: report["errors"].append(str(e)[:300]))
            page.goto(BASE, wait_until="networkidle")
            page.wait_for_timeout(800)

            def snap(step):
                st = page.evaluate(JS_STATE)
                png = out / f"{step}.png"
                page.screenshot(path=str(png))
                report["shots"].append(str(png))
                return st

            first = snap("00-initial")
            check("左栏出现模板入口", first["sidebarHasTemplate"], first["tabs"])

            clicked = page.evaluate("""
            () => {
              const t = Array.from(document.querySelectorAll('#wsPluginList .ws-plugin-item'))
                .find(b => b.textContent.indexOf('模板') >= 0);
              if (!t) return null;
              t.click();
              return t.textContent.trim().slice(0, 40);
            }
            """)
            page.wait_for_timeout(2000)
            st = snap("10-opened")
            check("点入口开出画布页签", clicked is not None and f"plugin:{PLUGIN_ID}" in st["tabs"],
                  f"clicked={clicked} tabs={st['tabs']}")
            check("iframe 沙箱只有 allow-scripts", st["frameSandbox"] == "allow-scripts", st["frameSandbox"])
            check("入口页由宿主托管", "/plugin-assets/" in (st["frameSrc"] or ""), st["frameSrc"])
            check("挂载无故障框（activate 30s 内回 ready）", not st["panelError"], st["panelError"])

            frame = page.frame_locator(f".ws-plugin-frame")
            status_sel = frame.locator("#status")
            report["notes"]["status_after_activate"] = status_sel.inner_text()
            # 沙箱内状态行只有一枚，可能被宿主随后下发的 ui.params.changed 覆盖，
            # 因此激活握手的权威证据取底栏的 plugin.mounted（宿主收到 ready 才写这行）。
            check("宿主收到 ready 并记 plugin.mounted", "plugin.mounted" in st["dockText"]
                  or "已挂载并就绪" in st["dockText"], st["dockText"][-300:])

            frame.locator("#load-btn").click()
            # bank.list 要等 provider 解析 + HTTP 往返，轮询到状态行离开「正在请求」为止
            bank_status = ""
            for _ in range(24):
                page.wait_for_timeout(500)
                bank_status = status_sel.inner_text()
                if "正在向宿主请求" not in bank_status:
                    break
            report["notes"]["status_after_bank_list"] = bank_status
            report["notes"]["questions_rendered"] = frame.locator(".item").count()
            check("bank.list 拿到宿主回执（非 20s 超时）",
                  "超时" not in bank_status and "正在向宿主请求" not in bank_status, bank_status)
            got = "取到" in bank_status
            check("回执可读：取到题目或如实报错，不静默吞掉",
                  got or ("失败" in bank_status), bank_status)
            if report["notes"].get("core_bank_copied"):
                check("带官方题库时真取到题目并渲染卡片", got and report["notes"]["questions_rendered"] > 0,
                      f"{bank_status} / 渲染 {report['notes']['questions_rendered']} 张")

            frame.locator("#dock-btn").click()
            page.wait_for_timeout(1500)
            st2 = snap("20-docked")
            dock = st2["dockText"]
            report["notes"]["dock_text"] = dock
            check("region.dock 经白名单落进底栏日志", "模板插件向底栏问了一声好" in dock, dock[-300:])
            check("沙箱内状态同步为已广播", "已广播" in status_sel.inner_text(), status_sel.inner_text())

            # ---------- 军令 #07 批复 2：坏 id 的请求必须「当场有回执 + 底栏记账」 ----------
            # 模板自身不再发带点号的 id，这里直接从沙箱帧里手造一条历史坑写法（org.example.template_99），
            # 验宿主不再静默丢弃。回执靠插件自己收得到才算数，故先在帧里挂一个监听记账。
            real_frame = None
            for f in page.frames:
                if "/plugin-assets/" + PLUGIN_ID + "/" in (f.url or ""):
                    real_frame = f
                    break
            check("定位到沙箱帧对象（跨 OOPIF 取证）", real_frame is not None,
                  [f.url for f in page.frames][:4])
            if real_frame is not None:
                bad_reply = real_frame.evaluate("""
                () => new Promise(function (resolve) {
                  var badId = 'org.example.template_99';       // 带点号：正是踩坑的老写法
                  var timer = setTimeout(function () { resolve({ timedOut: true }); }, 6000);
                  window.addEventListener('message', function (ev) {
                    var m = ev.data;
                    if (m && m.protocol === 'jzo-plugin/1' && m.kind === 'response' && m.id === badId) {
                      clearTimeout(timer);
                      resolve({ timedOut: false, ok: m.ok, code: (m.error || {}).code || '',
                                message: (m.error || {}).message || '' });
                    }
                  });
                  window.parent.postMessage({ protocol: 'jzo-plugin/1', id: badId, kind: 'request',
                                              method: 'bank.get', payload: { id: 'q_x' } }, '*');
                })
                """)
                report["notes"]["bad_id_reply"] = bad_reply
                check("坏 id 请求当场拿到宿主错误回执（不再等超时）",
                      bool(bad_reply) and bad_reply.get("timedOut") is False
                      and bad_reply.get("ok") is False and bad_reply.get("code") == "BAD_REQUEST_ID",
                      json.dumps(bad_reply, ensure_ascii=False))
                page.wait_for_timeout(1200)
                st3 = snap("30-bad-id")
                report["notes"]["dock_text_after_bad_id"] = st3["dockText"]
                check("底栏「输出日志区」记了这笔拒发", "请求 id 不合法" in st3["dockText"],
                      st3["dockText"][-300:])

            check("宿主页无未捕获 JS 错误", len(report["errors"]) == 0, report["errors"][:3])
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:  # noqa: BLE001
            server.kill()

    return finish(report, out)


def urllib_stub():
    """带 Bearer 无关的极简 GET 上下文（/api/plugins 是只读接口，不需要令牌）。"""
    import contextlib
    import urllib.request

    @contextlib.contextmanager
    def _ctx():
        def get(url):
            with urllib.request.urlopen(url, timeout=20) as resp:
                return json.loads(resp.read())
        yield get

    return _ctx()


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
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + " :: " + c["detail"][:160])
    print("out_dir:", result.get("out_dir"))
    sys.exit(0 if result["summary"]["failed"] == 0 else 1)
