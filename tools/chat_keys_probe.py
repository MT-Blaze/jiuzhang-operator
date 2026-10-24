# -*- coding: utf-8 -*-
"""军令 #16-R 第一步真机取证：聊天框 Enter 发送、Shift+Enter 换行。

用法：``python tools/chat_keys_probe.py <out_dir_tag>``
判据：
  1. 空内容按 Enter：不发、不提示、焦点仍在输入框；
  2. Shift+Enter 只换行、不发送；
  3. 裸 Enter 发送，且走同一个出口（请求体就是输入框内容）；
  4. 组合态 Enter 不误发（composition 标志与 isComposing 两条都拦）；
  5. 焦点不在输入框时 Enter 不触发发送。

输入法组合态用合成 CompositionEvent / KeyboardEvent 验证监听逻辑，
真实输入法上屏仍由人工复核（回执里如实标注）。

跑之前底座必须在 8765 端口起来。
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/static/workspace.html"
NOISE = ("ERR_FAILED", "Failed to load resource")


def is_noise(text):
    return any(n in text for n in NOISE)


def find_chat_frame(page):
    for _ in range(48):
        for frame in page.frames:
            if "org.jiuzhang.chat" in (frame.url or ""):
                try:
                    if frame.locator("#chatPrompt").count() == 1:
                        return frame
                except Exception:
                    pass
        page.wait_for_timeout(250)
    return None


def run(tag: str) -> dict:
    out = Path(".system_generated") / "chat_keys_probe" / tag
    out.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": str(detail)[:400]})
        return bool(passed)

    errors = []
    sent = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text)
                if m.type == "error" and not is_noise(m.text) else None)
        page.goto(BASE)
        page.wait_for_timeout(2200)

        frame = find_chat_frame(page)
        check("01 助手输入框在场", frame is not None,
              [f.url for f in page.frames][:5])
        if frame is None:
            browser.close()
        else:
            prompt = frame.locator("#chatPrompt")
            placeholder = prompt.get_attribute("placeholder") or ""
            check("02 输入框文案写明 Enter 发送 / Shift+Enter 换行",
                  "Enter 发送" in placeholder and "Shift+Enter 换行" in placeholder,
                  placeholder)

            def capture(route):
                sent.append(route.request.post_data or "")
                route.abort()

            page.route("**/api/agent/chat", capture)

            def active_in_chat():
                return frame.evaluate(
                    "() => document.activeElement ? (document.activeElement.id "
                    "|| document.activeElement.tagName) : ''"
                )

            # --- 1. 空内容按 Enter ---
            bubbles_before = frame.locator(".jzochat-msg").count()
            prompt.click()
            prompt.fill("")
            page.keyboard.press("Enter")
            page.wait_for_timeout(400)
            check("03 空内容 Enter 不发送", len(sent) == 0, sent)
            check("04 空内容 Enter 后焦点仍在输入框", active_in_chat() == "chatPrompt",
                  active_in_chat())
            check("05 空内容 Enter 没有弹提示",
                  frame.locator(".jzochat-msg").count() == bubbles_before,
                  {"before": bubbles_before,
                   "after": frame.locator(".jzochat-msg").count()})
            page.screenshot(path=str(out / "01-empty-enter.png"))

            # --- 2. Shift+Enter 换行 ---
            prompt.type("第一行")
            page.keyboard.press("Shift+Enter")
            page.keyboard.type("第二行")
            page.wait_for_timeout(300)
            value_shift = prompt.input_value()
            check("06 Shift+Enter 只换行不发送",
                  "\n" in value_shift and len(sent) == 0 and "第二行" in value_shift,
                  {"value": value_shift, "sent": len(sent)})
            page.screenshot(path=str(out / "02-shift-enter.png"))

            # --- 3. 裸 Enter 发送 ---
            page.keyboard.press("Enter")
            page.wait_for_timeout(900)
            check("07 裸 Enter 发送一次", len(sent) == 1, len(sent))
            check("08 发送后输入框清空", prompt.input_value() == "", prompt.input_value())
            if sent:
                check("09 发送请求体就是输入框内容",
                      "第一行" in sent[0] and "第二行" in sent[0], sent[0][:200])
            page.screenshot(path=str(out / "03-enter-send.png"))

            # --- 4. 组合态 Enter 不误发 ---
            comp = frame.evaluate("""() => {
              const el = document.getElementById('chatPrompt');
              el.focus();
              el.value = '导数';
              el.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }));
              el.dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Enter', bubbles: true, cancelable: true
              }));
              return { value: el.value, focused: document.activeElement === el };
            }""")
            page.wait_for_timeout(400)
            check("10 compositionstart 后的 Enter 不发送",
                  len(sent) == 1 and comp["value"] == "导数", {"comp": comp, "sent": len(sent)})

            iso = frame.evaluate("""() => {
              const el = document.getElementById('chatPrompt');
              el.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true }));
              el.dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Enter', bubbles: true, cancelable: true, isComposing: true
              }));
              return { value: el.value, focused: document.activeElement === el };
            }""")
            page.wait_for_timeout(400)
            check("11 isComposing=true 的 Enter 不发送",
                  len(sent) == 1 and iso["value"] == "导数", {"iso": iso, "sent": len(sent)})
            page.screenshot(path=str(out / "04-composing.png"))

            # 组合态结束后，再按 Enter 应恢复发送
            prompt.click()
            page.keyboard.press("Enter")
            page.wait_for_timeout(900)
            check("12 组合结束后 Enter 恢复发送", len(sent) == 2, len(sent))

            # --- 5. 焦点不在输入框 ---
            frame.locator("#chatThread").click()
            page.wait_for_timeout(200)
            check("13 起点不在输入框", active_in_chat() != "chatPrompt", active_in_chat())
            page.keyboard.press("Enter")
            page.wait_for_timeout(400)
            check("14 焦点不在输入框时 Enter 不发送", len(sent) == 2, len(sent))

            page.locator(".ws-context-head").first.click()
            page.wait_for_timeout(200)
            page.keyboard.press("Enter")
            page.wait_for_timeout(400)
            check("15 焦点在宿主时 Enter 不代发聊天", len(sent) == 2, len(sent))
            page.screenshot(path=str(out / "05-focus-outside.png"))

            page.unroute("**/api/agent/chat")

        browser.close()

    report = {
        "tag": tag,
        "base": BASE,
        "passed": sum(1 for c in checks if c["passed"]),
        "total": len(checks),
        "pageerrors": errors,
        "checks": checks,
    }
    (out / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
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
        print("%s %-46s %s" % ("PASS" if c["passed"] else "FAIL", c["name"], c["detail"]))
    if rep["pageerrors"]:
        print("PAGE ERRORS:", json.dumps(rep["pageerrors"], ensure_ascii=False)[:800])
