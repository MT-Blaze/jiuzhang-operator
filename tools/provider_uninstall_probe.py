# -*- coding: utf-8 -*-
"""军令 #20 真机取证：题库引擎的免死金牌升级为「整包不可卸载」。

用法：``.venv/Scripts/python.exe tools/provider_uninstall_probe.py <out_dir_tag>``
产出：截图 png + probe.json（结构化判据与 pageerror）

军令 #18-结 时代的口径是「弹窗把『不保留数据』置灰、点确认仍保数据」；
军令 #20 拆出无界面的 bank-engine 后，引擎连代码目录都不许删：设置页不再给
【卸载】按钮，后端 DELETE 一律 409。本探针在真人路径上同时验证前后端。

全程在临时目录里跑：`JZO_PLUGINS_DIR` / `JZO_DATA_DIR` 指向 temp 副本，
卸载的是副本，**绝不碰仓库里的 plugins/ 与用户 data/**。

判据：
  1. 引擎卡片没有【卸载】按钮，改成「受保护·不可卸载」标签；
  2. /api/plugins 回包带 capabilities 与 uninstallable=false（前端不靠硬编码 id）；
  3. 绕过 UI 直接 DELETE（带合法写令牌）→ 409，引擎代码目录与物理题库都在；
  4. 题库内容指纹（题数 + 题文散列）逐项不变；
  5. 对照：普通插件仍有卸载按钮，取消保留后库真被删。
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
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"
ENGINE = "org.jiuzhang.bank-engine"
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

    proc = start_server(plugins_dir, data_dir, (port := free_port()))
    origin = f"http://127.0.0.1:{port}"
    captured: list[dict] = []

    def api_get(path: str) -> dict:
        with urllib.request.urlopen(origin + path, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def api_delete(plugin_id: str) -> tuple[int, dict]:
        request = urllib.request.Request(
            origin + f"/api/plugins/{plugin_id}?keep_data=false",
            method="DELETE",
            headers={"X-JZO-Token": TOKEN},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")
            try:
                payload = json.loads(body or "{}")
            except ValueError:
                payload = {"detail": body}
            return error.code, payload

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

            def card(pid: str):
                return page.locator('#mgList .mg-card[data-id="%s"]' % pid)

            check("01 设置页与控制台面板起来（无 pageerror）",
                  not errors and page.locator("#mgList .mg-card").count() >= 2,
                  (errors, page.locator("#mgList .mg-card").count()))

            engine_card = card(ENGINE)
            check("02 引擎卡片没有【卸载】按钮", engine_card.locator(".mg-uninstall").count() == 0)
            tags = engine_card.locator(".mg-tag").all_inner_texts()
            check("03 引擎卡片标出『受保护·不可卸载』", "受保护·不可卸载" in tags, tags)
            check("04 引擎卡片标出『不占左栏』（无界面数据端）", "不占左栏" in tags, tags)
            page.screenshot(path=str(out / "engine_card.png"))

            listing = api_get("/api/plugins")
            entries = {p["id"]: p for p in listing["plugins"]}
            check("05 回包带 capabilities 与 uninstallable=false",
                  "bank.provider" in (entries.get(ENGINE, {}).get("capabilities") or [])
                  and entries.get(ENGINE, {}).get("uninstallable") is False
                  and entries.get(PLAIN, {}).get("uninstallable") is True,
                  {pid: {"caps": entries.get(pid, {}).get("capabilities"),
                         "uninstallable": entries.get(pid, {}).get("uninstallable")}
                   for pid in (ENGINE, PLAIN)})

            # ---- 绕过 UI 直接发 DELETE：后端必须 409，代码与数据都原地不动
            status, payload = api_delete(ENGINE)
            check("06 直接 DELETE 引擎返回 409", status == 409, {"status": status, "body": payload})
            check("07 拒绝理由说人话", "受保护不可卸载" in str(payload.get("detail", "")),
                  payload.get("detail"))
            check("08 引擎代码目录仍在", (plugins_dir / ENGINE / "plugin.json").is_file())
            check("09 引擎物理题库内容原样保留（456 题与题文散列全等）",
                  engine_db.is_file() and bank_signature(engine_db) == engine_before,
                  (engine_before, bank_signature(engine_db) if engine_db.is_file() else "MISSING"))

            # ---- 对照：普通插件照常可卸载（取消勾选保留 → 物理删除）
            plain_card = card(PLAIN)
            check("10 对照：普通插件仍有【卸载】按钮",
                  plain_card.locator(".mg-uninstall").count() == 1)
            plain_card.locator(".mg-uninstall").click()
            page.wait_for_timeout(400)
            keep = page.locator("#uninstallKeep")
            check("11 对照：普通插件复选框可用", keep.is_enabled())
            check("12 对照：普通插件不显示免死提示",
                  page.locator("#uninstallProvider").get_attribute("hidden") is not None)
            keep.click()  # 取消勾选 → 要求彻底删除
            page.wait_for_timeout(200)
            check("13 对照：取消勾选后红色销毁警告亮起",
                  page.locator("#uninstallDanger").get_attribute("hidden") is None,
                  page.locator("#uninstallDanger").inner_text()[:60])
            before2 = len(captured)
            page.locator("#uninstallConfirm").click()
            page.wait_for_timeout(1800)
            req2 = next((r for r in captured[before2:] if PLAIN in r["url"]), {"url": ""})
            check("14 对照：普通插件请求真是 keep_data=false", "keep_data=false" in req2["url"], req2["url"])
            check("15 对照：普通插件的库真被物理删除", not plain_db.exists())
            page.screenshot(path=str(out / "final_state.png"))
            browser.close()

        check("16 全程零 pageerror", not errors, errors)
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
