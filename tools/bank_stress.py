"""真题题库压测：456 道真实题目的批量写入、并发读取、注入尝试与 LaTeX 核对。

用法：
    .venv/Scripts/python.exe tools/bank_stress.py            # 默认 12 线程
    .venv/Scripts/python.exe tools/bank_stress.py --threads 16 --rounds 6

隔离：脚本把 ``JZO_DATA_DIR`` 指到临时目录后再导入应用模块，不碰开发者的 data/；
种子库只读复制，原库与插件包不改。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "org.jiuzhang.bank-engine"
SEED = ROOT / "plugins" / PLUGIN_ID / "bank" / "bank.db"
LEGACY = Path("E:/math-question-bank-main/math_question_bank.db")
TOKEN = "stress-token-local"

TMP = Path(tempfile.mkdtemp(prefix="jzo-bank-stress-"))
os.environ["JZO_DATA_DIR"] = str(TMP)
os.environ["JZO_LOCAL_TOKEN"] = TOKEN

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import bank, basket  # noqa: E402
from app.core.questions import validate_question  # noqa: E402


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def rows_as_documents() -> list[dict]:
    """压测语料走底座读路径装配（v0.6.3 起种子库是 7 张关系表，不再拼宽表列）。"""
    documents: list[dict] = []
    page = 1
    while True:
        items, _total = bank.list_questions(PLUGIN_ID, page=page, page_size=100)
        if not items:
            return documents
        documents.extend(items)
        page += 1


def latex_audit(documents: list[dict]) -> dict:
    mismatches = []
    odd_rows = []
    for document in documents:
        options = "".join(option.get("content", "") for option in document.get("options", []))
        digits = document["stem"].count("$") + options.count("$") + str(document.get("solution") or "").count("$")
        if digits % 2:
            odd_rows.append({"id": document["id"], "dollars": digits})
    if LEGACY.is_file():
        con = sqlite3.connect(f"file:{LEGACY.as_posix()}?mode=ro", uri=True)
        try:
            source = {
                f"q_legacy_{int(row[0]):06d}": ((row[1] or "").count("$") + (row[2] or "").count("$"))
                for row in con.execute("SELECT id, content, answer_markdown FROM questions")
            }
        finally:
            con.close()
        for document in documents:
            options = "".join(option.get("content", "") for option in document.get("options", []))
            migrated = (
                document["stem"].count("$") + options.count("$")
                + str(document.get("solution") or "").count("$")
            )
            expected = source.get(document["id"])
            if expected is not None and expected != migrated:
                mismatches.append(
                    {"id": document["id"], "source": expected, "migrated": migrated}
                )
    return {
        "source": str(LEGACY) if LEGACY.is_file() else "",
        "checked": len(documents),
        "mismatches": mismatches,
        "odd_dollar_rows": odd_rows,
    }


def insert_phase(documents: list[dict], threads: int, rounds: int) -> dict:
    errors: list[str] = []
    lock = threading.Lock()
    counter = {"writes": 0}

    def worker(worker_id: int) -> None:
        chunk = documents[worker_id::threads]
        for _ in range(rounds):
            try:
                bank.import_documents(PLUGIN_ID, chunk)
                with lock:
                    counter["writes"] += len(chunk)
            except Exception as exc:  # noqa: BLE001 - 压测要把失败类型收集回来
                with lock:
                    errors.append(f"{type(exc).__name__}: {exc}")
                return

    started = time.perf_counter()
    pool = [threading.Thread(target=worker, args=(index,)) for index in range(threads)]
    for thread in pool:
        thread.start()
    for thread in pool:
        thread.join()
    elapsed = time.perf_counter() - started
    con = sqlite3.connect(bank.bank_db_path(PLUGIN_ID), timeout=10.0)
    try:
        count = bank.import_count(PLUGIN_ID)
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        con.close()
    return {
        "threads": threads,
        "rounds": rounds,
        "writes": counter["writes"],
        "errors": errors[:20],
        "error_count": len(errors),
        "final_count": count,
        "integrity": integrity,
        "seconds": round(elapsed, 3),
        "writes_per_second": round(counter["writes"] / elapsed, 1) if elapsed else None,
    }


def http_get(base: str, path: str, token: bool = False) -> tuple[int, dict]:
    request = urllib.request.Request(base + path)
    if token:
        request.add_header("X-JZO-Token", TOKEN)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        try:
            body = error.read().decode("utf-8")
        finally:
            error.close()
        try:
            return error.code, json.loads(body or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": body}


def http_phase(threads: int) -> dict:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(TMP)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        deadline = time.time() + 20
        while time.time() < deadline:
            if process.poll() is not None:
                raise RuntimeError((process.stdout.read() if process.stdout else "")[:2000])
            try:
                status, _ = http_get(base, "/healthz")
                if status == 200:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.1)
        else:
            raise RuntimeError("服务未就绪")

        errors: list[str] = []
        latencies: list[float] = []
        lock = threading.Lock()
        paths = [
            f"/api/bank/plugins/{PLUGIN_ID}/questions?" + urllib.parse.urlencode(
                {"grade": "高一", "page": 1, "page_size": 100}, encoding="utf-8"
            ),
            f"/api/bank/plugins/{PLUGIN_ID}/questions?" + urllib.parse.urlencode(
                {"difficulty": "hard", "page": 2, "page_size": 20}, encoding="utf-8"
            ),
            f"/api/bank/plugins/{PLUGIN_ID}/questions?" + urllib.parse.urlencode(
                {"q": "' OR 1=1 --"}, encoding="utf-8"
            ),
            f"/api/bank/plugins/{PLUGIN_ID}/questions?q=%25",
            f"/api/bank/plugins/{PLUGIN_ID}/stats",
            f"/api/bank/plugins/{PLUGIN_ID}/random?grade=%E9%AB%98%E4%B8%89",
        ]

        def worker(worker_id: int) -> None:
            for index in range(40):
                path = paths[(worker_id + index) % len(paths)]
                start = time.perf_counter()
                try:
                    status, _ = http_get(base, path)
                    if status != 200:
                        with lock:
                            errors.append(f"{path} -> HTTP {status}")
                except Exception as exc:  # noqa: BLE001
                    with lock:
                        errors.append(f"{type(exc).__name__}: {exc}")
                with lock:
                    latencies.append(time.perf_counter() - start)

        started = time.perf_counter()
        pool = [threading.Thread(target=worker, args=(index,)) for index in range(threads)]
        for thread in pool:
            thread.start()
        for thread in pool:
            thread.join()
        elapsed = time.perf_counter() - started

        # 分页完整性：7 页 × 70 题应覆盖全部 456
        covered = 0
        for page in range(1, 8):
            status, data = http_get(
                base,
                f"/api/bank/plugins/{PLUGIN_ID}/questions?"
                + urllib.parse.urlencode({"page": page, "page_size": 70}, encoding="utf-8"),
            )
            if status == 200:
                covered += len(data.get("items", []))
            else:
                errors.append(f"page {page} -> HTTP {status}")

        # 题篮：50 道真实长题
        status, page = http_get(
            base,
            f"/api/bank/plugins/{PLUGIN_ID}/questions?"
            + urllib.parse.urlencode({"page_size": 50, "difficulty": "hard"}, encoding="utf-8"),
        )
        basket_total = 0
        if status == 200:
            ids = [item["id"] for item in page.get("items", [])][:50]
            request = urllib.request.Request(
                base + "/api/basket",
                data=json.dumps({"plugin_id": PLUGIN_ID, "ids": ids, "mode": "replace"}).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json", "X-JZO-Token": TOKEN},
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    basket_total = json.loads(response.read().decode("utf-8"))["total"]
            except urllib.error.HTTPError as error:
                error.close()
                errors.append(f"basket add -> HTTP {error.code}")

        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else None
        return {
            "threads": threads,
            "requests": len(latencies),
            "errors": errors[:20],
            "error_count": len(errors),
            "seconds": round(elapsed, 3),
            "p95_ms": round(p95 * 1000, 1) if p95 else None,
            "pages_covered": covered,
            "basket_total": basket_total,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    parser = argparse.ArgumentParser(description="core-bank 题库压测")
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--rounds", type=int, default=5)
    args = parser.parse_args(argv)

    if not SEED.is_file():
        print("缺少迁移种子库，请先运行 tools/migrate_legacy_bank.py")
        return 2
    if not LEGACY.is_file():
        print("提示：旧库不在默认路径，LaTeX 源文对比将跳过。")

    target = bank.bank_db_path(PLUGIN_ID)
    shutil.copyfile(SEED, target)
    documents = rows_as_documents()

    latex = latex_audit(documents)
    insert = insert_phase(documents, max(2, args.threads // 3), args.rounds)
    http = http_phase(args.threads)

    # 写后逐题抽检：schema 仍然合法，且筛选真的能按年级取到（一律走底座读路径）
    sample, _sample_total = bank.list_questions(PLUGIN_ID, page=1, page_size=40)
    grade_totals = {
        item["name"]: item["count"] for item in bank.stats(PLUGIN_ID)["grades"]
    }
    schema_errors = []
    for document in sample:
        try:
            validate_question(document)
        except Exception as exc:  # noqa: BLE001
            schema_errors.append({"id": document["id"], "reason": str(exc)[:200]})

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seed_bytes": SEED.stat().st_size,
        "questions": len(documents),
        "latex": latex,
        "insert": insert,
        "http": http,
        "grade_totals": grade_totals,
        "schema_errors": schema_errors,
        "temp_dir": str(TMP),
    }
    out = ROOT / "data" / "bank_stress_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = (
        insert["error_count"] == 0
        and insert["integrity"] == "ok"
        and http["error_count"] == 0
        and http["pages_covered"] == 456
        and http["basket_total"] == 50
        and not latex["mismatches"]
        and not latex["odd_dollar_rows"]
        and not schema_errors
    )
    print(
        f"{'PASS' if ok else 'FAIL'} · 写入 {insert['writes']} 次/{insert['seconds']}s "
        f"({insert['writes_per_second']}/s) · HTTP {http['requests']} 请求/{http['seconds']}s "
        f"(p95 {http['p95_ms']}ms) · 分页覆盖 {http['pages_covered']}/456 · "
        f"题篮 {http['basket_total']} · LaTeX 差异 {len(latex['mismatches'])} · "
        f"结构错误 {len(schema_errors)}"
    )
    print(f"报告：{out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
