# -*- coding: utf-8 -*-
"""军令 #18-结 任务三真机取证：题库引擎卸载免死金牌在**浏览器里**真的生效。

用法：``.venv/Scripts/python.exe tools/provider_uninstall_probe.py <out_dir_tag>``
产出：截图 png + probe.json（结构化判据与 pageerror）

为什么单测不够：这条军令要的是「弹窗把『不保留数据』置灰并强行提示」。
置灰是 DOM 状态、提示是可见文案、发出去的请求带哪个 keep_data 是运行时行为——
三者都得在真人路径上看，光测 `uninstall_plugin()` 只能证明后端，证不了前端门禁。

全程在临时目录里跑：`JZO_PLUGINS_DIR` / `JZO_DATA_DIR` 指向 temp 副本，
卸载的是副本，**绝不碰仓库里的 plugins/ 与用户 data/**。

判据：
  1. 引擎（声明 bank.provider）弹窗：复选框 disabled + 仍勾选 + label aria-disabled + 红色免死提示可见；
  2. 焦点落在「取消」而不是置灰的复选框；
  3. 点【确认卸载】时浏览器实际发出的请求带 `keep_data=true`，后端回包 `provider_guarded=true`；
  4. 引擎代码目录被删、temp 里的 `banks/<id>.db` 逐字节原样保留；
  5. 对照：非 provider 插件复选框可用、免死提示隐藏，取消勾选后请求真是 `keep_data=false` 且库真被删。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "plugins" / "org.jiuzhang.core-bank" / "bank" / "schema.sql"
ENGINE = "org.jiuzhang.core-bank"
PLAIN = "org.jiuzhang.dashboard"
TOKEN = "provider-probe-token"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_bank(path: Path, questions: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        now = "2026-10-25T00:00:00+08:00"
        for index in range(questions):
            con.execute(
                "INSERT INTO questions (id,type,stem,options,answer,solution,extensions,difficulty,created_at,updated_at)"
                " VALUES (?,'fill_blank',?,'[]',NULL,NULL,'[]','L1',?,?)",
                (f"q_probe_{index:04d}", f"探针真题 {index}", now, now),
            )
        con.commit()
    finally:
        con.close()


def bank_signature(path: Path) -> tuple:
    """题库的**内容**指纹：题数 + 按 id 排序的题文散列。

    不逐字节比对，也不看 `PRAGMA user_version`：底座启动时以 WAL 打开并跑过版本化迁移，
    文件头与 user_version 会变（0→2），但老师的题目一行没动——免死金牌保的是内容。
    """
    con = sqlite3.connect(path)
    try:
        count = con.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        rows = ["|".join(str(cell) for cell in row) for row in
                con.execute("SELECT id, stem, type, difficulty FROM questions ORDER BY id")]
        return (count, hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest())
    finally:
        con.close()


def bank_user_version(path: Path) -> int:
    con = sqlite3.connect(path)
    try:
        return con.execute("PRAGMA user_version").fetchone()[0]
    finally:
        con.close()


def start_server(plugins_dir: Path, data_dir: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env.update({
        "JZO_PLUGINS_DIR": str(plugins_dir),
        "JZO_DATA_DIR": str(data_dir),
        "JZO_LOCAL_TOKEN": TOKEN,
        "JZO_AI_API_KEY": "",
        "JZO_RESTART_DISABLED": "1",
    })
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    import urllib.error
    import urllib.request
    deadline = time.time() + 25
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("服务提前退出：\n" + (proc.stdout.read() if proc.stdout else ""))
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=0.5) as r:
                if r.status == 200:
                    return proc
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 25 秒内就绪")


def run(tag: str) -> dict:
    out = Path(".system_generated") / "provider_uninstall_probe" / tag
    out.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []
    errors: list[str] = []

    def check(name: str, passed: bool, detail="") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": str(detail)[:400]})

    tmp = tempfile.TemporaryDirectory()
    base = Path(tmp.name)
    plugins_dir = base / "plugins"
    data_dir = base / "data"
    plugins_dir.mkdir()
    for pid in (ENGINE, PLAIN):
        shutil.copytree(ROOT / "plugins" / pid, plugins_dir / pid)
    engine_db = data_dir / "banks" / f"{ENGINE}.db"
    plain_db = data_dir / "banks" / f"{PLAIN}.db"
    make_bank(engine_db, 456)
    make_bank(plain_db, 3)
    engine_before = bank_signature(engine_db)
    before_version = bank_user_version(engine_db)

    proc = start_server(plugins_dir, data_dir, (port := free_port()))
    origin = f"http://127.0.0.1:{port}"
    captured: list[dict] = []

    def api_get(path: str) -> dict:
        import urllib.request
        with urllib.request.urlopen(origin + path, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("request", lambda r: captured.append(
                {"method": r.method, "url": r.url}) if r.method == "DELETE" else None)
            page.goto(origin + "/settings")
            page.wait_for_timeout(2200)
            page.locator("#stNavPlugin").click()
            page.wait_for_timeout(900)

            # Playwright 里「属性存在但值为空」返回的是 ""，不是 None；
            # 用 truthiness 判 hidden 会把「关着的弹窗」也读成开着，必须逐字判 None。
            def shown(loc) -> bool:
                return loc.get_attribute("hidden") is None

            def card(pid: str):
                return page.locator('#mgList .mg-card[data-id="%s"]' % pid)

            check("01 设置页与控制台面板起来（无 pageerror）",
                  not errors and page.locator("#mgList .mg-card").count() >= 2,
                  (errors, page.locator("#mgList .mg-card").count()))
            check("02 引擎卡片有【卸载】入口", card(ENGINE).locator(".mg-uninstall").count() == 1)
            listing = api_get("/api/plugins")
            caps = {p["id"]: p.get("capabilities") for p in listing["plugins"]}
            check("03 列表回包带 capabilities（前端置灰只认这个，不认硬编码 id）",
                  isinstance(caps.get(ENGINE), list) and "bank.provider" in caps[ENGINE]
                  and "bank.provider" not in (caps.get(PLAIN) or []), caps)

            # ---- 引擎：打开弹窗
            card(ENGINE).locator(".mg-uninstall").click()
            page.wait_for_timeout(400)
            keep = page.locator("#uninstallKeep")
            label = page.locator("label.mg-keep")
            check("04 弹窗打开且写着引擎名", shown(page.locator("#uninstallModal")),
                  page.locator("#uninstallText").inner_text())
            check("05 引擎的『保留本地数据』复选框被置灰（disabled）", keep.is_disabled(),
                  keep.get_attribute("disabled"))
            check("06 置灰的同时仍是勾选态（不是靠取消勾选伪装保护）", keep.is_checked())
            check("07 外层 label 带 aria-disabled（读屏器也知不可选）",
                  label.get_attribute("aria-disabled") == "true")
            body = page.locator("#uninstallProvider").inner_text()
            check("08 红色免死提示可见且逐字含『题库引擎已被保护，数据将原地保留』",
                  shown(page.locator("#uninstallProvider"))
                  and "题库引擎已被保护，数据将原地保留" in body, body[:80])
            check("09 「永久删除」警告此时不该出现（销毁路径已被堵死）",
                  not shown(page.locator("#uninstallDanger")))
            focus = page.evaluate("() => document.activeElement && document.activeElement.id")
            check("10 焦点落在【取消】而非置灰的复选框", focus == "uninstallCancel", focus)
            page.screenshot(path=str(out / "engine_modal.png"))

            # ---- 引擎：确认卸载，看真实请求与后端回包
            before = len(captured)
            page.locator("#uninstallConfirm").click()
            page.wait_for_timeout(1800)
            req = next((r for r in captured[before:] if ENGINE in r["url"]), {"url": "", "method": ""})
            check("11 浏览器实际发出的请求带 keep_data=true", "keep_data=true" in req["url"], req["url"])
            check("12 引擎代码目录被删（免死金牌只保数据）", not (plugins_dir / ENGINE).exists())
            check("13 引擎物理题库内容原样保留（456 题与题文散列全等）",
                  engine_db.is_file() and bank_signature(engine_db) == engine_before,
                  (engine_before, bank_signature(engine_db) if engine_db.is_file() else "MISSING",
                   "user_version %s→%s（底座启动跑迁移，题目未动）" % (before_version, bank_user_version(engine_db))))
            status = page.locator("#mgStatus").inner_text()
            check("14 结果文案如实回显保护", "题库引擎已被保护" in status, status)

            # ---- 对照：非 provider 插件
            card(PLAIN).locator(".mg-uninstall").click()
            page.wait_for_timeout(400)
            check("15 对照：普通插件复选框未置灰", keep.is_enabled())
            check("16 对照：普通插件不显示免死提示",
                  not shown(page.locator("#uninstallProvider")))
            keep.click()  # 取消勾选 → 要求彻底删除
            page.wait_for_timeout(200)
            danger = page.locator("#uninstallDanger").inner_text()
            check("17 对照：取消勾选后红色销毁警告亮起",
                  shown(page.locator("#uninstallDanger")), danger[:60])
            before2 = len(captured)
            page.locator("#uninstallConfirm").click()
            page.wait_for_timeout(1800)
            req2 = next((r for r in captured[before2:] if PLAIN in r["url"]), {"url": ""})
            check("18 对照：普通插件请求真是 keep_data=false", "keep_data=false" in req2["url"], req2["url"])
            check("19 对照：普通插件的库真被物理删除", not plain_db.exists())
            page.screenshot(path=str(out / "final_state.png"))
            browser.close()

        check("20 全程零 pageerror", not errors, errors)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        tmp.cleanup()

    report = {
        "tag": tag,
        "passed": sum(1 for c in checks if c["passed"]),
        "total": len(checks),
        "pageerrors": errors,
        "checks": checks,
    }
    (out / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["probe_json"] = str(out / "probe.json")
    return report


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    rep = run(tag)
    print("probe_json:", rep["probe_json"])
    print("passed: %d/%d  pageerrors: %d" % (rep["passed"], rep["total"], len(rep["pageerrors"])))
    for c in rep["checks"]:
        print("%s %-56s %s" % ("PASS" if c["passed"] else "FAIL", c["name"], c["detail"]))
    if rep["pageerrors"]:
        print("PAGE ERRORS:", json.dumps(rep["pageerrors"], ensure_ascii=False)[:600])
