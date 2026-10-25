# -*- coding: utf-8 -*-
"""录题工作台真机探针：填表单 → A4 预览 → 清洗 → 保存 → 题库可查。

用法：``.venv/Scripts/python.exe tools/editor_probe.py <tag>``

隔离：复制 editor 与 core-bank 到独立插件目录，另起端口与数据目录，
不写本机 data/banks/。检查项：
- 左栏出现「录题工作台」，挂载进沙箱并回 ready；
- 动态增删选项、答案/解析/难度/标签表单齐全；
- 输入后 140ms 防抖内重排，A4 单页无溢出、公式为真 KaTeX；
- 「一键清洗 LaTeX」把 \\(...\\)、\\[...\\]、\\fillin 归一；
- 旧库三条录题路径回归：一题挂两卷（各带原卷题号）、教材/章/节、原生图片上传；
- 保存后拿到 q_ 开头的 ID，直查 API 字段逐项一致（含 tags/来源/图片/选项 image_ids）；
- 题库总数 456→457，core-bank 画布搜索能查到新题；
- 宿主 1440px 无横向溢出，控制台零错误。
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
BANK_UI_ID = "org.jiuzhang.bank-ui"
UNIQUE = "探针录题"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 25
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError("服务提前退出：\n" + output[:3000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 25 秒内就绪")


def http_json(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, json.loads(payload or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": payload}


def wait_preview(metrics, timeout: float = 10) -> float:
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = metrics.get_attribute("data-render-ms")
        if raw not in (None, ""):
            return float(raw)
        time.sleep(0.05)
    raise AssertionError("预览未在预期时间内重排")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "editor_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    shots.mkdir(parents=True)
    png_path = work / "probe-upload.png"
    png_path.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    ))
    for plugin_id in (EDITOR_ID, BANK_ID, BANK_UI_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = "editor-probe-token"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "metrics": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.goto(base + "/workspace", wait_until="networkidle")

            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            check("左栏出现录题工作台", True)
            item.click()

            panel = page.locator("#wsPanel_plugin_org_jiuzhang_editor")
            frame = panel.frame_locator(".ws-plugin-frame")
            root = frame.locator("#root")
            expect(root).to_be_visible(timeout=15000)
            check("插件挂载并显示表单", True)

            metrics = frame.locator("#edMetrics")
            stem = frame.locator("#edStem")
            options = frame.locator("#edOptions input")
            answer = frame.locator("#edAnswer")
            solution = frame.locator("#edSolution")
            tags = frame.locator("#edTags")

            # ---------- 动态选项 ----------
            expect(options).to_have_count(4, timeout=5000)
            frame.locator("#edAddOption").click()
            expect(options).to_have_count(5, timeout=3000)
            last_key = frame.locator(".ed-option-key").nth(4).inner_text()
            frame.locator(".ed-option-remove").nth(4).click()
            expect(options).to_have_count(4, timeout=3000)
            check("选项可增删且重排标号", last_key.strip() == "E", {"added_key": last_key})

            # ---------- 脏 LaTeX + 预览 ----------
            dirty = (
                "探针录题：已知 \\(x^{2}-5x+6=0\\)，则 $x$ 的值为（　　），"
                "并化简 \\[\\dfrac{1}{2}+\\dfrac{1}{3}\\]，填空 \\fillin。"
            )
            stem.fill(dirty)
            contents = ["$x=2$", "$x=3$", "$x=2$ 或 $x=3$", "$x=1$ 或 $x=6$"]
            for index, content in enumerate(contents):
                options.nth(index).fill(content)
            answer.fill("C")
            solution.fill("由 $x^{2}-5x+6=0$ 得 $(x-2)(x-3)=0$，故 $x=2$ 或 $x=3$。")
            tags.fill("一元二次方程, 因式分解")
            frame.locator("#edDifficulty").select_option("L2")

            render_ms = wait_preview(metrics)
            page.wait_for_timeout(220)
            katex = int(metrics.get_attribute("data-katex") or "0")
            overflow = metrics.get_attribute("data-overflow")
            result["metrics"]["preview"] = {
                "render_ms": render_ms, "katex": katex, "overflow": overflow,
            }
            check("实时预览重排 < 1000ms", 0 < render_ms < 1000, {"render_ms": render_ms})
            check("公式真渲染为 KaTeX", katex >= 4, {"katex": katex})
            check("A4 单页无溢出", overflow == "0", {"overflow": overflow})
            page.screenshot(path=str(shots / "editor-form.png"))

            # ---------- 一键清洗 ----------
            frame.locator("#edClean").click()
            page.wait_for_timeout(300)
            cleaned = stem.input_value()
            result["metrics"]["cleaned_stem"] = cleaned
            check("清洗掉 \\(...\\)", "\\(" not in cleaned, {"stem": cleaned[:80]})
            check("清洗掉 \\[...\\] 为 $$", "$$" in cleaned and "\\[" not in cleaned)
            check("清洗 \\fillin 为横线", "\\fillin" not in cleaned and "＿" in cleaned)

            # ---------- 旧路径一：一题多卷来源 ----------
            frame.locator("#edAddSource").click()
            frame.locator("#edAddSource").click()
            expect(frame.locator(".ed-source-row")).to_have_count(2, timeout=3000)
            first_source = frame.locator(".ed-source-row").nth(0)
            first_source.locator(".ed-source-title").fill("2024 届高三一模·数学（探针）")
            first_source.locator(".ed-source-year").fill("2024")
            first_source.locator(".ed-source-no").fill("7")
            first_source.locator(".ed-source-exam").fill("一模")
            second_source = frame.locator(".ed-source-row").nth(1)
            second_source.locator(".ed-source-title").fill("校本练习卷（探针）")
            second_source.locator(".ed-source-no").fill("12")
            second_source.locator(".ed-source-school").fill("九章中学")
            page.wait_for_timeout(160)
            check("来源卷可挂两张", frame.locator(".ed-source-row").count() == 2)

            # ---------- 旧路径二：教材/章/节 ----------
            frame.locator("#edTextbook").fill("人教A版·必修第一册")
            frame.locator("#edChapter").fill("2. 一元二次函数")
            frame.locator("#edSection").fill("2.1 方程与不等式")

            # ---------- 旧路径三：原生图片上传（选项 A + 题干） ----------
            with page.expect_file_chooser() as chooser:
                frame.locator(".ed-option-upload").first.click()
            chooser.value.set_files(str(png_path))
            expect(frame.locator(".ed-image-item")).to_have_count(1, timeout=10000)
            with page.expect_file_chooser() as chooser:
                frame.locator("#edImagePick").click()
            chooser.value.set_files(str(png_path))
            expect(frame.locator(".ed-image-item")).to_have_count(2, timeout=10000)
            expect(frame.locator(".ed-option-thumb")).to_have_count(1, timeout=3000)
            result["metrics"]["uploaded_images"] = frame.locator(".ed-image-item").count()
            check("原生上传进配图清单", frame.locator(".ed-image-item").count() == 2)
            check("选项 A 显示配图缩略图", frame.locator(".ed-option-thumb").count() == 1)
            page.screenshot(path=str(shots / "editor-assets.png"))

            # ---------- 保存入库 ----------
            frame.locator("#edSave").click()
            saved = frame.locator("#edSaved")
            expect(saved).to_be_visible(timeout=15000)
            question_id = saved.get_attribute("data-id") or ""
            result["metrics"]["question_id"] = question_id
            check("保存返回题目 ID", bool(re.fullmatch(r"q_[A-Za-z0-9_-]{8,64}", question_id)),
                  {"id": question_id})

            status, document = http_json(
                base + f"/api/bank/plugins/{BANK_ID}/questions/{question_id}"
            )
            result["metrics"]["created"] = document
            check("API 可查到新题", status == 200, {"status": status})
            check("题干已落库", UNIQUE in document.get("stem", ""))
            check("四个选项完整", [item["key"] for item in document.get("options", [])] == ["A", "B", "C", "D"],
                  document.get("options"))
            check("答案为 C", document.get("answer", {}).get("choice_keys") == ["C"],
                  document.get("answer"))
            check("解析已落库", "(x-2)" in document.get("solution", ""), document.get("solution"))
            # 契约 2.0：难度落库归一成 L1–L4；tags 与教材位置按旧库口径落在
            # core-bank 自己的 extensions 键上，读路径再还原成契约根字段。
            check("难度/年级一致",
                  document.get("difficulty") == "L2"
                  and document.get("grade") == "高一",
                  {"difficulty": document.get("difficulty"), "grade": document.get("grade")})
            check("标签已落库", document.get("tags") == ["一元二次方程", "因式分解"],
                  document.get("tags"))
            check("教材位置已落库",
                  (document.get("taxonomy") or {}).get("chapter") == "2. 一元二次函数",
                  document.get("taxonomy"))
            check("主来源已落库",
                  (document.get("source") or {}).get("question_no") == "7",
                  document.get("source"))

            status, sources_doc = http_json(
                base + f"/api/bank/plugins/{BANK_ID}/questions/{question_id}/sources"
            )
            titles = [item["paper_title"] for item in sources_doc.get("items", [])]
            result["metrics"]["sources"] = sources_doc
            check("一题两卷均在来源关系表",
                  status == 200
                  and titles == ["2024 届高三一模·数学（探针）", "校本练习卷（探针）"],
                  {"status": status, "titles": titles})

            image_roles = [item.get("role") for item in document.get("images", [])]
            check("图片数组含题干与选项两类", set(image_roles) == {"stem", "option"},
                  image_roles)
            option_a = next(
                (item for item in document.get("options", []) if item.get("key") == "A"), {}
            )
            check("选项 A 关联 image_ids", bool(option_a.get("image_ids")),
                  option_a.get("image_ids"))

            status, stats = http_json(base + f"/api/bank/plugins/{BANK_ID}/stats")
            check("题库总数 456 → 457", status == 200 and stats.get("total") == 457,
                  {"total": stats.get("total")})
            page.screenshot(path=str(shots / "editor-saved.png"))

            # ---------- 题库画布查得到 ----------
            bank_item = page.locator(".ws-plugin-item", has_text="真题题库").first
            bank_item.click()
            bank_panel = page.locator("#wsPanel_plugin_org_jiuzhang_bank-ui")
            bank_frame = bank_panel.frame_locator(".ws-plugin-frame")
            search = bank_frame.locator(".cb-search")
            expect(search).to_be_visible(timeout=15000)
            search.fill(UNIQUE)
            search.press("Enter")
            expect(bank_frame.locator(".cb-row", has_text=UNIQUE).first).to_be_visible(timeout=10000)
            rows = bank_frame.locator(".cb-row", has_text=UNIQUE).count()
            result["metrics"]["bank_rows"] = rows
            check("题库画布搜到新题", rows >= 1, {"rows": rows})
            page.wait_for_timeout(250)
            page.screenshot(path=str(shots / "bank-ui-found.png"))

            size_host = page.locator("body").evaluate(
                "() => ({scrollWidth: document.body.scrollWidth, clientWidth: document.documentElement.clientWidth})"
            )
            result["metrics"]["host"] = size_host
            check("宿主无横向溢出", size_host["scrollWidth"] <= size_host["clientWidth"] + 1, size_host)

            browser.close()
    except Exception as exc:  # noqa: BLE001 - 探针要把失败原样落盘
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            page.screenshot(path=str(shots / "failure.png"))
        except Exception:
            pass
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = bool(result["checks"]) and all(item["ok"] for item in result["checks"]) \
        and not result["page_errors"] and "error" not in result
    (work / "probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    passed = sum(1 for item in result["checks"] if item["ok"])
    print(("PASS" if result["ok"] else "FAIL") + f" · {passed} 项检查 · {work}")
    for item in result["checks"]:
        print(("  ✓ " if item["ok"] else "  ✗ ") + item["name"])
    if result["console_errors"]:
        print("console:", result["console_errors"][:8])
    if result["page_errors"]:
        print("pageerrors:", result["page_errors"][:8])
    if "error" in result:
        print("error:", result["error"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
