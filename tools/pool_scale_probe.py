# -*- coding: utf-8 -*-
"""军令 #32 · S6d P0：重题池规模与耗时实测（测试工程师，产品代码只读）。

要回答的问题（主公原话「300 题进去，池子取数没取出来」）：
1. 老师点下【开始解析】到批次纸带出现，这段 HTTP 时长随题数怎么长（100/200/300 三档曲线）；
2. 落池后的**首次读取**耗时是否 ≤5s（判据 3.1 的真机口径）；
3. 后台链实况：线程起来 → 首行 `dedupe_scans` 落库 → done → `admit_into_pool` 抽走，各段多久；
4. 扫的过程中再读一次会不会被拖住（纸带卡「查询中」与读侧延迟的最大值）；
5. 进程中途被杀（切页/重启）后台链会不会一起死、死后重启还能不能对上账（判据 3.3/3.4）；
6. 断账量化：未审 + 池内 与 本批总数 到底差几条。

隔离：随机端口 + 独立 JZO_DATA_DIR/JZO_PLUGINS_DIR + 自带一次性令牌 + JZO_RESTART_DISABLED=1；
显式删除 JZO_POOL_ADMIT_DISABLED（要测的就是生产那条自动抽走链）；
只读自己那份临时 pending.db，绝不碰仓库 data/ 里的真实库。

用法：.venv\\Scripts\\python.exe tools\\pool_scale_probe.py <tag>
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / ".qoder" / "records" / "biz" / "2026-11" / "20261103_order32-s6-evidence"
EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
TOKEN = "s6d-scale-probe-token"
N_ORIGINALS = 200
SCALES = (100, 200, 300)
DUP_RATIO = 0.6
RESULT: dict[str, object] = {"checks": [], "scales": [], "timeline": [], "kill_test": {}}


def check(name: str, ok: object, detail: object = None) -> None:
    RESULT["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " | "
          + wire.dumps(detail, ensure_ascii=False, default=str)[:600], flush=True)


def mark(event: str, **extra: object) -> None:
    row = {"t": round(time.time(), 3), "clock": time.strftime("%H:%M:%S"), "event": event}
    row.update(extra)
    RESULT["timeline"].append(row)
    print("-- " + wire.dumps(row, ensure_ascii=False, default=str)[:400], flush=True)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _decode(resp: object) -> tuple[int, dict]:
    body = resp.read().decode("utf-8", errors="replace")  # type: ignore[attr-defined]
    try:
        return int(getattr(resp, "status", 200)), wire.loads(body or "{}")
    except wire.JSONDecodeError:
        return int(getattr(resp, "status", 200)), {"raw": body[:400]}


def GET(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return _decode(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        e.close()
        try:
            return e.code, wire.loads(body or "{}")
        except wire.JSONDecodeError:
            return e.code, {"raw": body[:400]}


def POST(url: str, payload: object) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=wire.dumps(payload, ensure_ascii=False).encode(),
                                 method="POST",
                                 headers={"Content-Type": "application/json", "X-JZO-Token": TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return _decode(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        e.close()
        try:
            return e.code, wire.loads(body or "{}")
        except wire.JSONDecodeError:
            return e.code, {"raw": body[:400]}


def doc(stem: str, answer: str = "A") -> dict:
    return {"type": "single_choice", "stem": stem, "difficulty": "L2",
            "options": [{"key": "A", "content": "$2$"}, {"key": "B", "content": "$3$"},
                        {"key": "C", "content": "$5$"}, {"key": "D", "content": "$6$"}],
            "answer": {"kind": "choice", "choice_keys": [answer], "final": answer},
            "solution": "由韦达定理，两根之和为 $5$。", "tags": ["基础"],
            "source": {"paper_title": "S6d 规模探针卷", "question_no": "1", "year": 2024,
                       "exam_type": "一模"},
            "taxonomy": {"topic": "S6d 考向", "topic_ids": ["t_s6d_scale"]}}


def original_stem(i: int) -> str:
    s = 5 + i
    p = 6 + (i % 7)
    return (f"S6d 原题 {i:04d}：已知 $x^2-{s}x+{p}=0$，求两根之和（　　）。"
            f"选项 A ${s}$，编号 {i:04d}，用于规模实测。")


def unique_stem(scale: int, i: int) -> str:
    return (f"S6d 新题 {scale}-{i:04d}：等差 $a_n={scale}n+{i}$ 的前三项和是（　　）。"
            f"这一条主库里没有，档位 {scale}。")


def wait_health(base: str, proc: subprocess.Popen, log: Path) -> None:
    end = time.time() + 90
    while time.time() < end:
        if proc.poll() is not None:
            raise RuntimeError("服务早退：" + log.read_text(encoding="utf-8", errors="replace")[-2000:])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.6) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("服务未就绪")


def start_server(data_dir: Path, plugins_dir: Path, log: Path) -> tuple[subprocess.Popen, str, object]:
    port = free_port()
    env = os.environ.copy()
    RESULT["pool_admit_var_in_parent_env"] = env.pop("JZO_POOL_ADMIT_DISABLED", None)
    env.update(JZO_DATA_DIR=str(data_dir), JZO_PLUGINS_DIR=str(plugins_dir),
               JZO_LOCAL_TOKEN=TOKEN, JZO_RESTART_DISABLED="1")
    handle = log.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen([str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn",
                             "app.main:app", "--host", "127.0.0.1", "--port", str(port),
                             "--log-level", "info", "--no-server-header"],
                            cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)
    wait_health(f"http://127.0.0.1:{port}", proc, log)
    mark("server_up", port=port)
    return proc, f"http://127.0.0.1:{port}", handle


def find_pending_db(data_dir: Path) -> Path | None:
    hits = sorted(data_dir.rglob("pending.db"))
    return hits[0] if hits else None


def scan_row(db: Path | None, batch_id: str) -> dict | None:
    """只读临时库的那一行初查结论；库还没建或表没建都回 None。"""
    if db is None or not db.is_file():
        return None
    try:
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=1.0)
    except sqlite3.Error:
        return None
    try:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM dedupe_scans WHERE batch_id = ?", (batch_id,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        return None
    finally:
        con.close()


def card_of(base: str, batch_id: str) -> dict:
    rows = (GET(base + "/api/pending/batches")[1].get("batches") or [])
    return next((r for r in rows if str(r.get("batch_id")) == batch_id), {})


def poll_until_done(base: str, db: Path | None, batch_id: str, budget: float,
                    probe_reads: bool) -> dict:
    """轮询到 done/failed 为止；probe_reads 时每次都顺带量一次读侧延迟（看会不会被扫拖住）。"""
    t0 = time.perf_counter()
    first_row_ms: float | None = None
    reads: list[float] = []
    row: dict | None = None
    polls = 0
    while time.perf_counter() - t0 < budget:
        polls += 1
        if first_row_ms is None:
            row = scan_row(db, batch_id)
            if row is not None:
                first_row_ms = round((time.perf_counter() - t0) * 1000, 1)
                mark("first_dedupe_scans_row", batch_id=batch_id, ms_since_post=first_row_ms,
                     status=row.get("status"))
        row = scan_row(db, batch_id) or row
        if probe_reads:
            r0 = time.perf_counter()
            GET(base + f"/api/pending/batches/{batch_id}/questions")
            reads.append(round((time.perf_counter() - r0) * 1000, 1))
        if row and str(row.get("status")) in ("done", "failed"):
            break
        time.sleep(0.05 if first_row_ms is None else 0.2)
    return {"done_after_post_s": round(time.perf_counter() - t0, 2),
            "first_row_ms": first_row_ms, "polls": polls, "row": row,
            "read_ms_max": max(reads) if reads else None,
            "read_ms_p95": sorted(reads)[int(len(reads) * 0.95) - 1] if reads else None,
            "read_ms_avg": round(sum(reads) / len(reads), 1) if reads else None,
            "read_samples": len(reads)}


def seed_bank(base: str, data_dir: Path) -> dict:
    """主库先躺 200 道原题：走老师真实那条链（落待审 → 逐条入库）。"""
    docs = [doc(original_stem(i)) for i in range(N_ORIGINALS)]
    t0 = time.perf_counter()
    status, body = POST(base + "/api/pending/batches", {"questions": docs})
    seed_post_ms = round((time.perf_counter() - t0) * 1000, 1)
    batch_id = str(body.get("batch_id") or "")
    items = (GET(base + f"/api/pending/batches/{batch_id}/questions")[1].get("items") or [])
    t1 = time.perf_counter()
    ok = 0
    for it in items:
        s, _b = POST(base + f"/api/pending/items/{it.get('id')}/approve", {})
        ok += 1 if s == 200 else 0
    approve_ms = round((time.perf_counter() - t1) * 1000, 1)
    mark("bank_seeded", batch_id=batch_id, status=status, approve_ok=ok,
         seed_post_ms=seed_post_ms, approve_all_ms=approve_ms)
    return {"seed_batch": batch_id, "post_status": status, "approve_ok": ok,
            "seed_post_ms": seed_post_ms, "approve_all_ms": approve_ms,
            "per_approve_ms": round(approve_ms / max(1, ok), 1)}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%H%M%S")
    RESULT["tag"] = tag
    work = ROOT / ".system_generated" / "pool_scale" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir = work / "data", work / "plugins"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    for pid in (EDITOR_ID, BANK_ID):
        shutil.copytree(ROOT / "plugins" / pid, plugins_dir / pid)
    log_path = work / "server.log"
    proc, base, handle = start_server(data_dir, plugins_dir, log_path)
    db = find_pending_db(data_dir)
    RESULT["pending_db"] = str(db)
    killed = False
    try:
        RESULT["seed"] = seed_bank(base, data_dir)
        pool_before = GET(base + "/api/pending/pool")[1].get("total")

        for scale in SCALES:
            dups = int(scale * DUP_RATIO)
            docs = ([doc(original_stem(i)) for i in range(dups)]
                    + [doc(unique_stem(scale, i)) for i in range(scale - dups)])
            t0 = time.perf_counter()
            status, body = POST(base + "/api/pending/batches", {"questions": docs})
            post_ms = round((time.perf_counter() - t0) * 1000, 1)
            batch_id = str(body.get("batch_id") or "")
            mark("batch_posted", scale=scale, batch_id=batch_id, status=status,
                 post_ms=post_ms, dup=dups, uniq=scale - dups)
            t1 = time.perf_counter()
            card = card_of(base, batch_id)
            card_ms = round((time.perf_counter() - t1) * 1000, 1)
            t2 = time.perf_counter()
            items = (GET(base + f"/api/pending/batches/{batch_id}/questions")[1].get("items") or [])
            first_read_ms = round((time.perf_counter() - t2) * 1000, 1)
            # 扫的过程中继续读：量读侧最坏延迟（「卡在查询中」的那一段就藏在这里）
            prof = poll_until_done(base, db, batch_id, 240.0, True)
            card_after = card_of(base, batch_id)
            ded = card_after.get("dedupe") or {}
            pending_count = card_after.get("pending_count")
            total = card_after.get("total")
            pooled = ded.get("pooled")
            pool_now = GET(base + "/api/pending/pool")[1]
            ledger = {"pending_count": pending_count, "total": total, "dedupe_pooled": pooled,
                      "items_len": len(items), "pool_total_global": pool_now.get("total"),
                      "sum_pending_plus_pooled": (pending_count or 0) + (pooled or 0)}
            RESULT["scales"].append({
                "scale": scale, "batch_id": batch_id, "post_status": status,
                "post_ms": post_ms, "per_question_ms": round(post_ms / scale, 2),
                "first_card_ms": card_ms, "first_items_read_ms": first_read_ms,
                "scan": {k: v for k, v in prof.items() if k != "row"},
                "scan_row": prof["row"], "card_after": card_after, "ledger": ledger,
            })
            check(f"{scale} 题·点下【开始解析】到纸带出现（POST 往返）≤5s", post_ms <= 5000,
                  {"post_ms": post_ms, "per_question_ms": round(post_ms / scale, 2)})
            check(f"{scale} 题·落池后首次读取批次题目 ≤5s（判据 3.1 真机口径）",
                  first_read_ms <= 5000 and (prof["read_ms_max"] or 0) <= 5000,
                  {"first_items_read_ms": first_read_ms, "scan_done_after_post_s": prof["done_after_post_s"],
                   "read_ms_max_during_scan": prof["read_ms_max"], "read_ms_avg": prof["read_ms_avg"],
                   "read_samples": prof["read_samples"]})
            check(f"{scale} 题·后台初查在落池后自己跑完（无红按钮、无失败码）",
                  prof["row"] and prof["row"].get("status") == "done",
                  {"first_row_ms": prof["first_row_ms"], "done_after_post_s": prof["done_after_post_s"],
                   "row": prof["row"]})
            check(f"{scale} 题·账对平：未审 + 池内 = 本批总数（判据 3.5 主公口径）",
                  ledger["sum_pending_plus_pooled"] == (total or 0)
                  and (pooled or 0) == int(scale * DUP_RATIO), ledger)

        # ---------- 中途杀进程：后台链会不会被一起杀掉（判据 3.3/3.4） ----------
        docs = [doc(original_stim) for original_stim in [original_stem(i) for i in range(150)]]
        t0 = time.perf_counter()
        status, body = POST(base + "/api/pending/batches", {"questions": docs})
        kill_batch = str(body.get("batch_id") or "")
        mark("kill_test_posted", batch_id=kill_batch, status=status,
             post_ms=round((time.perf_counter() - t0) * 1000, 1))
        row_before = scan_row(db, kill_batch)
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()
        killed = True
        handle.close()
        mark("server_killed_mid_scan", row_before_status=(row_before or {}).get("status"))
        time.sleep(1.0)
        proc2, base2, handle2 = start_server(data_dir, plugins_dir, work / "server2.log")
        card = card_of(base2, kill_batch)
        ded = card.get("dedupe") or {}
        row_after = scan_row(db, kill_batch)
        ledger2 = {"pending_count": card.get("pending_count"), "total": card.get("total"),
                   "dedupe_pooled": ded.get("pooled"), "dedupe_status": ded.get("status"),
                   "row_status": (row_after or {}).get("status"),
                   "row_code": (row_after or {}).get("code")}
        RESULT["kill_test"] = {"batch_id": kill_batch, "row_before": row_before,
                               "row_after": row_after, "card_after_restart": card,
                               "ledger": ledger2,
                               "pool_total": GET(base2 + "/api/pending/pool")[1].get("total")}
        check("杀进程后重启：初查结论要么已落库、要么如实回退成可重试（不许假装扫过）",
              (row_after or {}).get("status") in ("done", "failed") or ded.get("retryable") is True
              or str(ded.get("status") or "").lower() in ("pending", "running", "failed"),
              ledger2)
        proc = proc2
        handle = handle2
        killed = False
    except Exception as exc:
        import traceback
        check("S6d 规模探针整体执行", False,
              {"exception": f"{type(exc).__name__}: {exc}",
               "trace": traceback.format_exc().splitlines()[-5:]})
    finally:
        if not killed:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()
        try:
            handle.close()
        except Exception:
            pass
        EVID.mkdir(parents=True, exist_ok=True)
        out_json = EVID / f"s6d-scale-{tag}.toml"
        n = 1
        while out_json.exists():
            out_json = EVID / f"s6d-scale-{tag}-{n}.toml"
            n += 1
        out_json.write_text(toml_io.dumps(RESULT, default=str),
                           encoding="utf-8")
        print(f"证据：{out_json}", flush=True)
    ok = sum(1 for c in RESULT["checks"] if c["ok"])
    print("=" * 60)
    print(f"规模探针 {len(RESULT['checks'])} 条，通过 {ok}，失败 {len(RESULT['checks']) - ok}")
    return 0 if ok == len(RESULT["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
