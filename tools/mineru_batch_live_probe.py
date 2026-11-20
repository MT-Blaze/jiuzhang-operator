# -*- coding: utf-8 -*-
"""MinerU 云整批提速真机探针（任务卡 §5）：隔离副本＋真点＋微批 4 题整批＋失败注入＋收口零孤儿。

隔离：两仓 git archive HEAD 解包（禁抄工作树）＋独立 JZO_DATA_DIR／JZO_PLUGINS_DIR＋
动态空闲端口＋每次随机令牌；服务 cwd＝副本，PYTHONPATH＝副本根（载入 wiretap
sitecustomize）。云账号用隔离 data 副本里已指派绑定（只读复制用户 MinerU 绑定，
禁碰用户 data/、真机 engines/ 与 65496）。出网只由 UI 投卷解析点击发起（真 MinerU 云）。

wiretap 只观测＋委托 HEAD 原函数（批量逻辑一字不动），落四段真_wire：POST file-urls/batch
（files=N/data_ids）／PUT×N（OSS 200⇒零 Content-Type）／单 batch_id 轮询（states）／zip×N。

判据：
Run A 顺风：UI 选 MinerU 云座→投 4 题纯图夹具→解析；一次 POST files=4、4 PUT ok、
一个 batch_id、4 份 full.md 映射回填（路由 4/4＋failures 空）；进度「已回 N/M」真出现截图。
Run B 失败注入：控制文件 corrupt_last 把最后一份 PUT 换坏字节（真上传 OSS→MinerU 解析
失败）；3/4 回填＋1 逐题失败账本显性、不级联不偷换。
额度实耗页数如实披露；零 JS 异常零 HTTP 失败；收口端口闭＋孤儿零。

运行：.venv/Scripts/python.exe tools/mineru_batch_live_probe.py [tag]
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402

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

from playwright.sync_api import expect, sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLUGINS_REPO = ROOT.parent / "jiuzhang-plugins"
EDITOR_ID = "org.jiuzhang.editor"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
EVIDENCE = ROOT / "docs" / "handoff" / "evidence" / "mineru-batch-live"
FIXTURE = ROOT / ".system_generated" / "mineru-batch-live" / "fixture_4q.pdf"
USER_CONFIG = ROOT / "data" / "config.toml"
USER_ENV = ROOT / "data" / "workspaces" / "default" / ".env"
MINERU_ACCOUNT = "acc_7ae191d903"
MINERU_ENV_PREFIX = "JZO_AIPOOL_7AE191D903_"
PARSE_CAP = 900
N_EXPECT = 4


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


def seed_binding(data_dir: Path) -> dict:
    """只读复制用户 MinerU 绑定进隔离 data：assignment＋账号＋.env 密钥（仅 MinerU）。"""
    user = toml_io.load(USER_CONFIG, {})
    center = user.get("ai_center") or {}
    accounts = [a for a in (center.get("accounts") or [])
                if a.get("id") == MINERU_ACCOUNT]
    assignment = (center.get("assignments") or {}).get("mineru") or {}
    isolated_center = {"accounts": accounts, "assignments": {"mineru": assignment}}
    toml_io.write(data_dir / "config.toml", {"ai_center": isolated_center})
    env_lines = []
    if USER_ENV.is_file():
        for line in USER_ENV.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(MINERU_ENV_PREFIX):
                env_lines.append(line)
    env_dir = data_dir / "workspaces" / "default"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    return {"account": accounts[0] if accounts else {},
            "assignment": assignment, "env_keys": [l.split("=", 1)[0] for l in env_lines]}


def read_wire(wire_path: Path) -> list[dict]:
    if not wire_path.is_file():
        return []
    rows = []
    for line in wire_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    started = time.time()
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    work = ROOT / ".system_generated" / "mineru-batch-live" / tag
    if work.exists():
        shutil.rmtree(work)
    shots = work / "shots"
    shots.mkdir(parents=True)
    op_dir, plugins_src = work / "operator", work / "plugins-src"
    op_head = git_archive(ROOT, op_dir)
    pl_head = git_archive(PLUGINS_REPO, plugins_src)
    plugin_dir = plugins_src / "src" / EDITOR_ID
    shutil.copy(EVIDENCE / "wiretap_sitecustomize.py", op_dir / "sitecustomize.py")
    toml_io.write(plugin_dir / "model_prefs.toml", {
        "disabled": [], "default_layout": "auto", "default_recognize": "auto",
        "auto_image_seat": "mineru_local", "auto_text_formula_seat": "auto"})
    data_dir = work / "data"
    data_dir.mkdir(parents=True)
    binding = seed_binding(data_dir)
    if not FIXTURE.is_file():
        subprocess.run([sys.executable, str(EVIDENCE / "make_fixture.py")],
                       capture_output=True, timeout=300)
    wire_path = work / "wire.jsonl"
    inject_path = work / "inject.txt"
    inject_path.write_text("", encoding="utf-8")

    token = "probe-" + secrets.token_hex(8)
    port = free_port()
    base = "http://127.0.0.1:%d" % port
    env = os.environ.copy()
    env.update({"JZO_DATA_DIR": str(data_dir),
                "JZO_PLUGINS_DIR": str(plugins_src / "src"),
                "JZO_LOCAL_TOKEN": token, "JZO_RESTART_DISABLED": "1",
                "JZO_POOL_ADMIT_DISABLED": "1",
                "JZO_PROBE_WIRE": str(wire_path), "JZO_PROBE_INJECT": str(inject_path),
                "PYTHONPATH": str(op_dir)})
    server_log = work / "server.log"
    handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = None
    result: dict = {"tag": tag, "base": base, "operator_head": op_head,
                    "plugins_head": pl_head, "checks": [], "console_errors": [],
                    "page_errors": [], "http_failures": [], "deviations": [
                        "微批夹具＝A1 纯图真卷第 2 页管线题块裁 4 道（题 6–9）成 4 页纯图 PDF，"
                        "每页一题，ocr.detect 复核 4 题；make_fixture.py 可复现",
                        "wiretap＝sitecustomize 导入钩子包 _request/_put_raw，只观测＋委托 HEAD 原函数，"
                        "批量逻辑一字不动；OSS PUT 200 即证零 Content-Type（带任何值都 403）",
                        "Run B 失败注入＝控制文件 corrupt_last 把最后一份 PUT body 换坏字节真上传 OSS，"
                        "MinerU 解析失败→逐题账本（卡允许 mock/坏图）",
                        "云账号只读复制用户 MinerU 绑定进隔离 data（assignment＋账号＋.env 密钥），禁碰用户 data/"]}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, detail or ""), flush=True)

    def wait_done(batch_id: str, cap: int, progress_shots: str) -> dict:
        detail: dict = {}
        seen_notes = set()
        deadline = time.time() + cap
        while time.time() < deadline:
            detail = http_json(base, "/api/pending/batches/%s/questions" % batch_id, token)
            note = str((detail.get("route") or {}).get("note") or "")
            m = re.search(r"已回 (\d+)/(\d+) 题", note)
            if note and note not in seen_notes and (m or "没成功" in note):
                seen_notes.add(note)
                result.setdefault("progress_notes", []).append(note)
                tag_m = m.group(1) if m else "fail"
                page.screenshot(path=str(shots / ("%s-progress-%s.png" % (progress_shots, tag_m))))
            if (detail.get("route") or {}).get("done"):
                return detail
            time.sleep(2)
        return detail

    def existing_batches() -> set[str]:
        cards = http_json(base, "/api/pending/batches", token).get("batches") or []
        return {str(c.get("batch_id")) for c in cards if c.get("batch_id")}

    def upload_and_parse(label: str, fixture: Path) -> str:
        before = existing_batches()
        canvas.locator("#edRecognizeEngine").select_option("mineru")
        page.wait_for_timeout(300)
        canvas.locator("#edBasketFile").set_input_files(str(fixture))
        go = canvas.locator("#edBasketGo")
        expect(go).to_be_enabled(timeout=30000)
        page.wait_for_timeout(800)
        go.click()
        deadline = time.time() + 120
        new_id = ""
        while time.time() < deadline:
            fresh = existing_batches() - before
            if fresh:
                new_id = sorted(fresh)[0]
                break
            time.sleep(1)
        if not new_id:
            raise RuntimeError("%s：投卷后 120 秒未见新批次（before=%s）" % (label, sorted(before)))
        expect(canvas.locator(".ed-batch-row[data-batch='%s']" % new_id)).to_be_visible(timeout=30000)
        result[label + "_batch"] = new_id
        return new_id

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
        registry = http_json(base, "/api/models/registry", token)
        by_id = {str(e.get("id")): e for e in registry.get("entries") or []}
        mineru = by_id.get("mineru") or {}
        check("隔离绑定 MinerU 云座 ready", mineru.get("state") == "ready",
              {"detail": mineru.get("detail"), "binding": binding["assignment"]})
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type in {"error", "warning"} else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.on("response", lambda r: result["http_failures"].append(
                "%s %s" % (r.status, r.url)) if r.status >= 400 else None)
            page.on("dialog", lambda d: d.accept())
            page.goto(base + "/workspace", wait_until="networkidle")
            page.locator(".ws-plugin-item", has_text="录题工作台").first.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=30000)
            # ---------- Run A 顺风：4 题整批 ----------
            wire_path.write_text("", encoding="utf-8")
            batch_a = upload_and_parse("runA", FIXTURE)
            page.screenshot(path=str(shots / "runA-uploaded.png"))
            detail_a = wait_done(batch_a, PARSE_CAP, "runA")
            route_a = detail_a.get("route") or {}
            items_a = detail_a.get("items") or []
            note_a = str(route_a.get("note") or "")
            page.screenshot(path=str(shots / "runA-done.png"))
            wire_a = read_wire(wire_path)
            (work / "wireA.jsonl").write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in wire_a), encoding="utf-8")
            (work / "wireA.toml").write_text(
                toml_io.dumps({"tag": tag, "run": "A", "exchanges": wire_a}, default=str),
                encoding="utf-8")
            posts_a = [r for r in wire_a if r.get("fn") == "_request"
                       and "/file-urls/batch" in r.get("url", "") and r.get("method") == "POST"]
            puts_a = [r for r in wire_a if r.get("fn") == "_put_raw"]
            polls_a = [r for r in wire_a if r.get("fn") == "_request"
                       and "/extract-results/batch/" in r.get("url", "")]
            zips_a = [r for r in wire_a if r.get("fn") == "_request"
                      and r.get("method") == "GET" and "/file-urls/batch" not in r.get("url", "")
                      and "/extract-results/batch/" not in r.get("url", "")]
            batch_ids_a = {r.get("poll_batch_id") for r in polls_a}
            files_n_a = len((posts_a[0].get("payload") or {}).get("files") or []) if posts_a else 0
            result["runA"] = {"batch": batch_a, "note": note_a,
                              "filled_note": re.findall(r"(\d+)/(\d+) 道回填成功", note_a),
                              "failures": route_a.get("failures") or [],
                              "items": len(items_a),
                              "posts": len(posts_a), "files_n": files_n_a,
                              "puts": len(puts_a), "puts_ok": sum(1 for r in puts_a if r.get("ok")),
                              "poll_batch_ids": sorted(batch_ids_a), "zips": len(zips_a)}
            check("RunA 一次 POST file-urls/batch files=4", len(posts_a) == 1 and files_n_a == N_EXPECT,
                  {"posts": len(posts_a), "files_n": files_n_a})
            check("RunA 4 次 PUT 全 ok（OSS 200⇒零 Content-Type）",
                  len(puts_a) == N_EXPECT and all(r.get("ok") for r in puts_a),
                  {"puts": len(puts_a), "ok": sum(1 for r in puts_a if r.get("ok"))})
            check("RunA 单 batch_id 轮询", len(batch_ids_a) == 1, {"batch_ids": sorted(batch_ids_a)})
            check("RunA 4 份结果包 zip 取回", len(zips_a) == N_EXPECT, {"zips": len(zips_a)})
            check("RunA 路由 4/4 回填＋failures 空",
                  ("4/4 道回填成功" in note_a) and not (route_a.get("failures") or []),
                  {"note": note_a[:200], "failures": route_a.get("failures") or []})
            stems_a = [str((it.get("question") or {}).get("stem") or "") for it in items_a]
            nonempty_a = sum(1 for s in stems_a if len(s.strip()) > 10)
            result["runA"]["stem_lengths"] = [len(s) for s in stems_a]
            check("RunA 4 题题干均回填非空", nonempty_a == N_EXPECT,
                  {"nonempty": nonempty_a, "lengths": [len(s) for s in stems_a]})
            check("RunA 进度「已回 N/M」真出现", bool(result.get("progress_notes")),
                  {"notes": result.get("progress_notes", [])[:6]})
            # ---------- Run B 失败注入：坏图最后一份 ----------
            inject_path.write_text("corrupt_last", encoding="utf-8")
            wire_path.write_text("", encoding="utf-8")
            result["progress_notes"] = []
            fixture_b = work / "fixture_4q_b.pdf"
            shutil.copy(FIXTURE, fixture_b)
            batch_b = upload_and_parse("runB", fixture_b)
            detail_b = wait_done(batch_b, PARSE_CAP, "runB")
            route_b = detail_b.get("route") or {}
            note_b = str(route_b.get("note") or "")
            page.screenshot(path=str(shots / "runB-done.png"))
            wire_b = read_wire(wire_path)
            (work / "wireB.jsonl").write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in wire_b), encoding="utf-8")
            (work / "wireB.toml").write_text(
                toml_io.dumps({"tag": tag, "run": "B", "exchanges": wire_b}, default=str),
                encoding="utf-8")
            inject_path.write_text("", encoding="utf-8")
            puts_b = [r for r in wire_b if r.get("fn") == "_put_raw"]
            corrupted_b = [r for r in puts_b if r.get("corrupted")]
            progress_b = [str(r.get("note") or "") for r in wire_b if r.get("fn") == "_progress"]
            fail_notes_b = [n for n in progress_b if "没成功" in n]
            polls_b = [r for r in wire_b if r.get("fn") == "_request"
                       and "/extract-results/batch/" in r.get("url", "")]
            failed_states = [s for r in polls_b for s in (r.get("states") or [])
                             if s.get("state") in ("failed", "error")]
            failures_b = route_b.get("failures") or []
            notes_b = list(result.get("progress_notes") or [])
            result["runB"] = {"batch": batch_b, "note": note_b,
                              "failures": failures_b, "puts": len(puts_b),
                              "corrupted": len(corrupted_b),
                              "corrupted_index": [r.get("file_index") for r in corrupted_b],
                              "failed_states": failed_states[:3],
                              "note_progression": notes_b,
                              "per_item_fail_notes": fail_notes_b}
            check("RunB 坏图注入恰一份 PUT", len(corrupted_b) == 1,
                  {"corrupted": len(corrupted_b), "index": [r.get("file_index") for r in corrupted_b]})
            check("RunB MinerU 真返 failed 态（坏图解析失败）", bool(failed_states),
                  {"failed_states": failed_states[:3]})
            check("RunB 3/4 回填＋1 逐题失败账本显性",
                  ("3/4 道回填成功" in note_b or "只有 3/4" in note_b) and len(failures_b) >= 1,
                  {"note": note_b[:200], "failures_n": len(failures_b)})
            check("RunB 失败不级联不偷换（其余 3 题照回填）",
                  sum(1 for it in (detail_b.get("items") or [])
                      if len(str((it.get("question") or {}).get("stem") or "").strip()) > 10) >= 3,
                  {"failures": [str(f.get("reason"))[:80] for f in failures_b][:3]})
            check("RunB 逐题失败注记显性（第 X/N 题没成功，wiretap 录 _progress 注记）",
                  bool(fail_notes_b),
                  {"fail_notes": fail_notes_b[:3], "progress_writes": len(progress_b)})
            # 失败清单 UI 可见：批次徽标只在 refreshBatches 重渲染时挂上，
            # 解析完成后用探针调试面（dev_probe_api）真刷一次列表再核徽标＋点开清单。
            canvas.locator("#edRoot").evaluate("el => window.__jzoEditorV2.refreshBatches()")
            badge = canvas.locator(".ed-batch-row[data-batch='%s'] .ed-batch-failbadge" % batch_b)
            try:
                expect(badge).to_be_visible(timeout=15000)
                badge.click()
                expect(canvas.locator(".ed-fail-item").first).to_be_visible(timeout=15000)
                page.screenshot(path=str(shots / "runB-failure-list.png"))
                check("RunB 失败清单 UI 可见（徽标＋点开清单）", True)
            except Exception as exc:  # noqa: BLE001
                check("RunB 失败清单 UI 可见（徽标＋点开清单）", False, {"reason": str(exc)[:160]})
            browser.close()
        result["quota_pages"] = {"runA_submitted": N_EXPECT, "runB_submitted": N_EXPECT,
                                 "runB_parsed_ok": N_EXPECT - 1,
                                 "total_submitted": 2 * N_EXPECT,
                                 "note": "每份单题截图＝1 页；两批共提交 8 页，成功解析 7 页（坏图 1 页失败）"}
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