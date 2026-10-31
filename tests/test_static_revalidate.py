"""静态资源新鲜度契约：界面修复必须能在一次普通刷新后到达老师眼前。

2026-10-31 真机回归的背景：工作台的折叠修复已经进了仓库，但浏览器按
Starlette 默认的启发式保鲜期缓存着旧版 splitpane.js——那版把折叠尺寸以内联
变量写死，于是「修好的 CSS」照样被旧脚本压回去，用户看到的仍是折叠后留白。
这里钉死两件事：``/static`` 一律回源校验，工作台 HTML 也不许被长缓存。

运行：``.venv/Scripts/python.exe -m unittest tests.test_static_revalidate``
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "app" / "main.py").read_text(encoding="utf-8")


class StaticRevalidateTest(unittest.TestCase):
    def test_01_static_mount_revalidates_every_request(self) -> None:
        self.assertIn("class RevalidatingStaticFiles(StaticFiles)", MAIN)
        self.assertIn('response.headers["Cache-Control"] = "no-cache"', MAIN)
        self.assertIn("RevalidatingStaticFiles(directory=settings.static_dir)", MAIN)
        self.assertNotIn(
            'app.mount("/static", StaticFiles(',
            MAIN,
            "又挂回了默认 StaticFiles：启发式缓存会让旧脚本继续服役",
        )

    def test_02_html_pages_are_not_long_cached(self) -> None:
        for name in ("workspace.html", "index.html", "plugins.html", "settings.html"):
            at = MAIN.index(name)
            window = MAIN[at:at + 200]
            self.assertIn('"Cache-Control": "no-cache"', window,
                          f"{name} 的响应没有 no-cache，页面换版后仍可能加载旧入口")


if __name__ == "__main__":
    unittest.main()
