"""JS 语法体检：用 Playwright 的 chromium 真解析一遍，省得本机没 node 时干等。

用法： .venv\\Scripts\\python.exe tools\\js_syntax_check.py <file.js> [...]
"""
from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

CHECK_JS = """
(source) => {
  try {
    // eslint-disable-next-line no-new-func
    new Function(source);
    return { ok: true, message: "" };
  } catch (error) {
    return { ok: false, message: String(error && error.message || error) };
  }
}
"""


def main() -> int:
    files = [pathlib.Path(p) for p in sys.argv[1:]]
    if not files:
        print("用法：js_syntax_check.py <file.js> [...]")
        return 2
    failed = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for path in files:
            text = path.read_text(encoding="utf-8")
            result = page.evaluate(CHECK_JS, text)
            if result["ok"]:
                print(f"OK   {path}")
            else:
                failed += 1
                print(f"FAIL {path}: {result['message']}")
        browser.close()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
