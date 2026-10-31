"""静态资源新鲜度契约：界面修复必须能在一次普通刷新后到达老师眼前。

2026-10-31 真机回归的背景：工作台的折叠修复已经进了仓库，但浏览器按
Starlette 默认的启发式保鲜期缓存着旧版 splitpane.js——那版把折叠尺寸以内联
变量写死，于是「修好的 CSS」照样被旧脚本压回去，用户看到的仍是折叠后留白。
同一天又出现「F5 刷新丢页签关闭叉、Ctrl+F5 才好」：只写 no-cache 时
Chrome 的软刷新仍会复用内存缓存。这里钉死：宿主壳（HTML/JS/CSS/SW）
一律 ``no-cache, no-store, must-revalidate`` + ``Pragma: no-cache``。

运行：``.venv/Scripts/python.exe -m unittest tests.test_static_revalidate``
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
SW = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")


class StaticRevalidateTest(unittest.TestCase):
    def test_01_static_mount_forbids_browser_caching(self) -> None:
        self.assertIn("class RevalidatingStaticFiles(StaticFiles)", MAIN)
        self.assertIn('"Cache-Control": "no-cache, no-store, must-revalidate"', MAIN)
        self.assertIn('"Pragma": "no-cache"', MAIN)
        self.assertIn("NO_CACHE_HEADERS", MAIN)
        self.assertIn("RevalidatingStaticFiles(directory=settings.static_dir)", MAIN)
        self.assertIn("for name, value in NO_CACHE_HEADERS.items()", MAIN)
        self.assertNotIn(
            'app.mount("/static", StaticFiles(',
            MAIN,
            "又挂回了默认 StaticFiles：启发式缓存会让旧脚本继续服役",
        )

    def test_02_html_pages_are_not_long_cached(self) -> None:
        for name in ("workspace.html", "index.html", "plugins.html", "settings.html"):
            at = MAIN.index(name)
            window = MAIN[at:at + 200]
            self.assertIn("headers=NO_CACHE_HEADERS", window,
                          f"{name} 的响应没有禁用缓存，页面换版后仍可能加载旧入口")

    def test_03_service_worker_is_never_cached_and_purges_old_caches(self) -> None:
        at = MAIN.index("/sw.js")
        self.assertIn("NO_CACHE_HEADERS", MAIN[at:at + 900])
        self.assertIn("caches.delete", SW, "旧 SW 留下的 Cache Storage 必须清空")
        self.assertIn('cache: "no-store"', SW, "同源导航与脚本样式必须绕过 HTTP 缓存")


if __name__ == "__main__":
    unittest.main()
