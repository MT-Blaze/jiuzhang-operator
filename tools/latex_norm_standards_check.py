"""记号标准字典卡（2.21.0）施工前标准原文核验：浏览器真人路径读公开页。

卡面 §2：写来源标签前必须核 GB 3102.11-1993《物理科学和技术中使用的数学符号》
与 ISO 80000-2（前身 ISO 31-11）的标准号/名称/状态；只许浏览器真人路径
（Playwright 真点击公开页），不许程序静默抓取；核不到＝显性欠账不编。

路径：
- GB：国家标准全文公开系统 openstd.samr.gov.cn 首页搜索框输 3102.11 → 点「检索」
  → 点结果行 → 详情页读标准号/名称/状态/采标关系；
- ISO：iso.org 站内搜索 80000-2 → 点 ISO 80000-2 结果 → 详情页读版本/替代关系。

产物落 .system_generated/latex-norm/standards/（截图＋页面文本＋standards.toml），不进 git。
运行：.venv/Scripts/python.exe tools/latex_norm_standards_check.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from app.core import toml_io  # noqa: E402

OUT = ROOT / ".system_generated" / "latex-norm" / "standards"
GB_HOME = "https://openstd.samr.gov.cn/bzgk/gb/"
ISO_HOME = "https://www.iso.org/standards.html"


def save_text(name: str, text: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(text, encoding="utf-8")
    return path


def shot(page, name: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def check_gb(browser) -> dict:
    """GB 3102.11：首页搜索 → 点检索 → 点结果行 → 详情页。"""
    result = {"ok": False, "steps": [], "url": "", "title": "", "detail_text": ""}
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    try:
        try:
            page.goto(GB_HOME, wait_until="domcontentloaded", timeout=90000)
        except Exception:
            page.wait_for_timeout(3000)
            page.goto(GB_HOME, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(2500)
        result["steps"].append("goto " + page.url)
        shot(page, "gb-01-home.png")
        save_text("gb-01-inputs.txt", page.eval_on_selector_all(
            "input", "els => els.map(e => e.outerHTML.slice(0, 300)).join('\\n')"))
        box = page.locator("input[type='text']:visible").first
        box.click()
        box.fill("3102.11")
        page.locator("#searchBtn").click()
        page.wait_for_timeout(4000)
        if len(page.context.pages) > 1:
            page = page.context.pages[-1]
            page.wait_for_load_state("domcontentloaded")
        result["steps"].append("search -> " + page.url)
        shot(page, "gb-02-results.png")
        save_text("gb-02-results.txt", page.inner_text("body"))
        row = page.locator("a", has_text="3102.11").first
        row.click()
        page.wait_for_timeout(3500)
        # 详情页可能开新标签
        if len(page.context.pages) > 1:
            page = page.context.pages[-1]
        page.wait_for_load_state("domcontentloaded")
        result["url"] = page.url
        result["title"] = page.title()
        result["steps"].append("detail -> " + page.url)
        shot(page, "gb-03-detail.png")
        body = page.inner_text("body")
        save_text("gb-03-detail.txt", body)
        result["detail_text"] = body[:4000]
        result["ok"] = "3102.11" in body
    except Exception as exc:  # noqa: BLE001 - 核验失败如实记欠账，不编结论
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            shot(page, "gb-error.png")
            save_text("gb-error.txt", page.inner_text("body"))
        except Exception:
            pass
    finally:
        page.close()
    return result


def check_iso(browser) -> dict:
    """ISO 80000-2：站内搜索 → 点结果 → 详情页读替代关系。"""
    result = {"ok": False, "steps": [], "url": "", "title": "", "detail_text": ""}
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    try:
        page.goto(ISO_HOME, wait_until="domcontentloaded", timeout=60000)
        # Cloudflare 盾：等它自己过（有头真浏览器通常几秒内放行），过不了如实记欠账
        for _ in range(20):
            page.wait_for_timeout(2000)
            if "security verification" not in page.inner_text("body").lower():
                break
        page.wait_for_timeout(2000)
        result["steps"].append("goto " + page.url)
        shot(page, "iso-01-home.png")
        save_text("iso-01-home.txt", page.inner_text("body")[:6000])
        save_text("iso-01-inputs.txt", page.eval_on_selector_all(
            "input, button[type='submit'], [role='searchbox']",
            "els => els.map(e => e.outerHTML.slice(0, 300)).join('\\n')"))
        # cookie consent（Usercentrics）挡点击：真人路径先点同意
        cmp = page.locator("#usercentrics-cmp-ui")
        if cmp.count():
            save_text("iso-01-cmp.txt", cmp.first.evaluate("e => e.innerHTML.slice(0, 4000)"))
        save_text("iso-01-frames.txt", "\n".join(f.url for f in page.frames))
        consent_clicked = False
        for frame in [page.main_frame, *page.frames]:
            for selector in ("#uc-center-btn", "[data-testid='uc-accept-all-button']",
                             "button#uc-accept-all", "aside button"):
                btn = frame.locator(selector)
                if btn.count() and btn.first.is_visible():
                    btn.first.click()
                    page.wait_for_timeout(1500)
                    result["steps"].append("consent clicked via " + selector)
                    consent_clicked = True
                    break
            if consent_clicked:
                break
        if not consent_clicked:
            for frame in [page.main_frame, *page.frames]:
                btn = frame.get_by_role("button", name="Accept All")
                if btn.count() and btn.first.is_visible():
                    btn.first.click()
                    page.wait_for_timeout(1500)
                    result["steps"].append("consent clicked via role Accept All")
                    break
        # 站内检索入口：顶部搜索图标/输入框，形态随版本变，逐个候选试
        opened = False
        for selector in ("input[type='search']", "input[name='q']", "#search-input",
                         "input[placeholder*='earch']", "[data-testid='search-input']"):
            loc = page.locator(selector)
            if loc.count() and loc.first.is_visible():
                loc.first.click()
                loc.first.fill("ISO 80000-2")
                loc.first.press("Enter")
                opened = True
                break
        if not opened:
            for name in ("Search", "搜索"):
                btn = page.get_by_role("button", name=name)
                if btn.count() and btn.first.is_visible():
                    btn.first.click()
                    page.wait_for_timeout(1200)
                    box = page.locator("input[type='search'], input[name='q']").first
                    box.click()
                    box.fill("ISO 80000-2")
                    box.press("Enter")
                    opened = True
                    break
        result["steps"].append("search opened=" + str(opened))
        page.wait_for_timeout(4500)
        shot(page, "iso-02-results.png")
        save_text("iso-02-results.txt", page.inner_text("body")[:8000])
        link = page.get_by_role("link", name="ISO 80000-2", exact=False).first
        link.click()
        page.wait_for_timeout(4000)
        if len(page.context.pages) > 1:
            page = page.context.pages[-1]
        page.wait_for_load_state("domcontentloaded")
        result["url"] = page.url
        result["title"] = page.title()
        result["steps"].append("detail -> " + page.url)
        shot(page, "iso-03-detail.png")
        body = page.inner_text("body")
        save_text("iso-03-detail.txt", body)
        result["detail_text"] = body[:4000]
        result["ok"] = "80000-2" in body
        # 前身链：2019 页生命周期点 2009 版 → 2009 页再点 ISO 31-11（卡面「前身 ISO 31-11」须实证）
        lineage = []
        for want, tag in (("ISO 80000-2:2009", "iso-04-2009"), ("ISO 31-11", "iso-05-31-11")):
            link = page.get_by_role("link", name=want, exact=False).first
            if not link.count():
                lineage.append(want + ": link not found")
                break
            link.click()
            page.wait_for_timeout(3500)
            if len(page.context.pages) > 1:
                page = page.context.pages[-1]
            page.wait_for_load_state("domcontentloaded")
            shot(page, tag + ".png")
            text = page.inner_text("body")
            save_text(tag + ".txt", text)
            lineage.append(want + " -> " + page.url)
            result["steps"].append("lineage " + want + " -> " + page.url)
        result["lineage"] = lineage
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            shot(page, "iso-error.png")
            save_text("iso-error.txt", page.inner_text("body")[:8000])
        except Exception:
            pass
    finally:
        page.close()
    return result


def main() -> int:
    started = time.time()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        try:
            gb = check_gb(browser)
            iso = check_iso(browser)
        finally:
            browser.close()
    report = {
        "card": "记号标准字典（闭集＋开集）2.21.0",
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": round(time.time() - started, 1),
        "method": "Playwright 真人路径：公开页搜索框输入→真点击检索→真点击结果行→读详情页",
        "gb_3102_11": gb,
        "iso_80000_2": iso,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "standards.toml").write_text(toml_io.dumps(report), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(toml_io.dumps(report))
    return 0 if (gb["ok"] and iso["ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())