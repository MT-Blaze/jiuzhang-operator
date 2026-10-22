"""v0.4.0 伪桌面契约：可安装清单、根作用域 SW、老内核探针、启动器等健康检查。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pwa_contract``
"""

from __future__ import annotations

import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
PAGES = ("index.html", "workspace.html", "plugins.html", "settings.html")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class PwaManifestTest(unittest.TestCase):
    def test_01_manifest_has_installable_fields(self) -> None:
        data = json.loads(_read(STATIC / "manifest.json"))
        self.assertTrue(data["name"])
        self.assertTrue(data["short_name"])
        self.assertEqual(data["start_url"], "/")
        self.assertEqual(data["scope"], "/")
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["theme_color"], "#a63b2b")
        sizes = {icon["sizes"] for icon in data["icons"]}
        self.assertTrue({"192x192", "512x512"} <= sizes, sizes)

    def test_02_icons_are_real_png_at_declared_size(self) -> None:
        for size in (192, 512):
            path = STATIC / "icons" / f"icon-{size}.png"
            raw = path.read_bytes()
            self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n", f"{path.name} 不是 PNG")
            width, height = struct.unpack(">II", raw[16:24])
            self.assertEqual((width, height), (size, size), path.name)

    def test_03_pages_advertise_manifest_and_register_sw(self) -> None:
        for name in PAGES:
            text = _read(STATIC / name)
            self.assertIn('rel="manifest"', text, f"{name} 没挂 PWA 清单")
            self.assertIn("/static/manifest.json", text, name)
            self.assertIn("/static/js/pwa.js", text, f"{name} 没注册 SW")

    def test_04_service_worker_is_root_scoped_and_cache_free(self) -> None:
        from app.main import app

        paths = {getattr(route, "path", None) for route in app.routes}
        self.assertIn("/sw.js", paths, "缺少根路径 SW 路由，scope 会被 /static/ 卡住")
        script = _read(STATIC / "sw.js")
        self.assertIn('addEventListener("fetch"', script)
        self.assertNotIn("caches.open", script, "SW 不许缓存，避免旧页面被锁死")
        self.assertIn('"Service-Worker-Allowed": "/"', _read(ROOT / "app" / "main.py"))


class BrowserProbeTest(unittest.TestCase):
    def test_01_probe_runs_before_app_styles_and_warns(self) -> None:
        text = _read(STATIC / "index.html")
        probe_at = text.index("请使用现代浏览器")
        self.assertLess(probe_at, text.index("app.css"), "探针必须在页面样式之前")
        probe = text[text.index("<script>") : text.index("</script>")]
        for marker in ("MSIE", "Trident", "noModule", "CSS.supports", "DOMContentLoaded"):
            self.assertIn(marker, probe, f"探针缺少 {marker}")


class LauncherHealthWaitTest(unittest.TestCase):
    def test_01_opens_browser_only_after_healthz(self) -> None:
        text = (ROOT / "start.bat").read_bytes().decode("ascii")
        self.assertNotIn("timeout /t 4", text, "固定等待已删除")
        self.assertIn("/healthz", text, "启动器必须等健康检查应答")
        self.assertIn("Start-Process", text, "必须交给系统默认浏览器")
        self.assertLess(text.index(":port_set"), text.index("Start-Process"))
        self.assertLess(text.index("Start-Process"), text.index("-m uvicorn"))


if __name__ == "__main__":
    unittest.main()
