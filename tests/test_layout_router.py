"""版面调度矩阵（2026-11-18 拍板）：自动走瀑布，具体档只走选中一级。

具体档队列与旧名兼容全由插件 catalog 数据声明（配置归插件卡）：
夹具见 tests/catalog_fixture.py；目录缺失时具体档一律归自动。

运行：``.venv/Scripts/python.exe -m unittest tests.test_layout_router``
"""

from __future__ import annotations

import asyncio
import shutil
import unittest
from unittest import mock

from app.core.ingest.layout import python as layout_python, router as layout_router
from tests.catalog_fixture import CatalogIsolated


def line(text: str, left: float, top: float, right: float) -> dict:
    return {"text": text, "left": left, "right": right,
            "top": top, "bottom": top - 10.0}


def two_column_info() -> dict:
    width, height = 600.0, 800.0
    return {
        "page": 1,
        "width_pt": width,
        "height_pt": height,
        "lines": [
            line("1. 第一题", 40.0, 700.0, 260.0),
            line("第一题正文", 40.0, 680.0, 260.0),
            line("2. 第二题", 40.0, 400.0, 260.0),
            line("第二题正文", 40.0, 380.0, 260.0),
            line("3. 第三题", 330.0, 700.0, 560.0),
            line("第三题正文", 330.0, 680.0, 560.0),
            line("4. 第四题", 330.0, 400.0, 560.0),
            line("第四题正文", 330.0, 380.0, 560.0),
        ],
    }


class LayoutPlanTest(CatalogIsolated):
    def test_auto_waterfall_starts_with_python(self) -> None:
        self.assertEqual(layout_router.plan("auto")[0], "python")

    def test_matrix(self) -> None:
        self.assertEqual(layout_router.plan("auto"), ("python", "yolo", "cloud"))
        self.assertEqual(layout_router.plan("rapidocr_fast"), ("ocr",))
        self.assertEqual(layout_router.plan("yolo"), ("yolo",))
        self.assertEqual(layout_router.plan("cloud_vision"), ("cloud",))

    def test_legacy_aliases_stay_compatible(self) -> None:
        self.assertEqual(layout_router.normalize_engine("cloud"), "cloud_vision")
        self.assertEqual(layout_router.normalize_engine("ocr"), "rapidocr_fast")
        self.assertEqual(layout_router.plan("cloud"), ("cloud",))

    def test_unknown_engine_falls_back_to_auto(self) -> None:
        self.assertEqual(layout_router.normalize_engine("乱填"), "auto")
        self.assertEqual(layout_router.normalize_engine(None), "auto")


class LayoutRunTest(CatalogIsolated, unittest.IsolatedAsyncioTestCase):
    def _provider(self, calls: list[str], key: str, ok: bool = True):
        def run(request: dict) -> dict:
            calls.append(key)
            self.assertIn("data", request)
            self.assertIn("pages", request)
            if not ok:
                return {"ok": False, "detail": key + " 没探到"}
            return {"ok": True, "pages": {1: [{"no": 1, "x": 10, "y": 20}]},
                    "columns": {1: 1}, "detail": key + " 成功"}
        return run

    async def test_auto_tries_yolo_after_python(self) -> None:
        calls: list[str] = []
        outcome = await layout_router.run("卷.pdf", b"%PDF", [{"page": 1}], "auto", {
            "python": self._provider(calls, "python", ok=False),
            "yolo": self._provider(calls, "yolo"),
            "cloud": self._provider(calls, "cloud"),
        })
        self.assertEqual(calls, ["python", "yolo"])
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["engine"], "yolo")
        self.assertEqual(outcome["requested"], "auto")
        self.assertEqual([step["engine"] for step in outcome["attempts"]],
                         ["python", "yolo"])

    async def test_yolo_only_runs_yolo_and_fails_honestly(self) -> None:
        calls: list[str] = []
        outcome = await layout_router.run("卷.pdf", b"%PDF", [{"page": 1}], "yolo", {
            "python": self._provider(calls, "python"),
            "yolo": self._provider(calls, "yolo", ok=False),
            "cloud": self._provider(calls, "cloud"),
        })
        self.assertEqual(calls, ["yolo"])
        self.assertFalse(outcome["ok"])
        self.assertEqual([step["engine"] for step in outcome["attempts"]], ["yolo"])
        self.assertIn("只走选中引擎，不降级", outcome["detail"])

    async def test_cloud_only_runs_cloud(self) -> None:
        calls: list[str] = []

        def forbidden(request: dict) -> dict:
            raise AssertionError("云端档不许碰文本层与 YOLO")

        async def cloud(request: dict) -> dict:
            calls.append("cloud")
            return {"ok": True, "pages": {1: [{"no": 1}]}, "columns": {}, "detail": ""}

        outcome = await layout_router.run("卷.pdf", b"%PDF", [{"page": 1}], "cloud", {
            "python": forbidden,
            "yolo": forbidden,
            "cloud": cloud,
        })
        self.assertEqual(calls, ["cloud"])
        self.assertEqual(outcome["engine"], "cloud")
        self.assertEqual(outcome["requested"], "cloud_vision")

    async def test_rapidocr_fast_single_level_forwards_lines(self) -> None:
        calls: list[str] = []

        def ocr(request: dict) -> dict:
            calls.append("ocr")
            return {"ok": True, "pages": {1: [{"no": 8}]}, "columns": {1: 1},
                    "lines_by_page": {1: [{"text": "8. 设数集 M"}]}, "detail": ""}

        outcome = await layout_router.run("卷.pdf", b"%PDF", [{"page": 1}],
                                          "rapidocr_fast", {"ocr": ocr})
        self.assertEqual(calls, ["ocr"])
        self.assertEqual(outcome["engine"], "ocr")
        self.assertEqual(outcome["lines_by_page"][1][0]["text"], "8. 设数集 M")

    async def test_auto_python_success_stops_the_waterfall(self) -> None:
        calls: list[str] = []
        outcome = await layout_router.run("卷.pdf", b"%PDF", [{"page": 1}], "auto", {
            "python": self._provider(calls, "python"),
            "yolo": self._provider(calls, "yolo"),
            "cloud": self._provider(calls, "cloud"),
        })
        self.assertEqual(calls, ["python"])
        self.assertEqual(outcome["engine"], "python")

    async def test_provider_exception_degrades(self) -> None:
        calls: list[str] = []

        def broken(request: dict) -> dict:
            calls.append("python")
            raise RuntimeError("文本层坏了")

        outcome = await layout_router.run("卷.pdf", b"%PDF", [{"page": 1}], "auto", {
            "python": broken,
            "yolo": self._provider(calls, "yolo"),
        })
        self.assertEqual(outcome["engine"], "yolo")
        self.assertIn("探路异常", outcome["attempts"][0]["detail"])

    async def test_unregistered_engine_is_recorded(self) -> None:
        outcome = await layout_router.run("卷.pdf", b"%PDF", [{"page": 1}], "cloud", {})
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["engine"], "")
        self.assertIn("没有注册", outcome["attempts"][0]["detail"])

    async def test_all_fail_is_honest(self) -> None:
        calls: list[str] = []
        outcome = await layout_router.run("卷.pdf", b"%PDF", [{"page": 1}], "auto", {
            "python": self._provider(calls, "python", ok=False),
            "yolo": self._provider(calls, "yolo", ok=False),
            "cloud": self._provider(calls, "cloud", ok=False),
        })
        self.assertFalse(outcome["ok"])
        self.assertEqual(len(outcome["attempts"]), 3)
        self.assertIn("都没找到题块", outcome["detail"])


class LayoutNoCatalogTest(CatalogIsolated):
    """目录缺失/未声明步骤：具体档归自动或诚实失败，底座不猜模型。"""

    def test_missing_catalog_normalizes_specific_pick_to_auto(self) -> None:
        shutil.rmtree(self.plugin)
        self.assertEqual(layout_router.normalize_engine("yolo"), "auto")
        self.assertEqual(layout_router.normalize_engine("cloud"), "auto")
        self.assertEqual(layout_router.plan("auto"), ("python", "yolo", "cloud"))

    def test_entry_without_plan_fails_honestly(self) -> None:
        (self.plugin / "catalog.toml").write_text(
            '[[entry]]\nid = "planless"\nname = "没写队列"\n'
            'capability = "layout"\nrule = "blocked"\n', encoding="utf-8")
        self.assertEqual(layout_router.normalize_engine("planless"), "planless")
        self.assertEqual(layout_router.plan("planless"), ())

        async def scenario() -> dict:
            return await layout_router.run("卷.pdf", b"%PDF", [{"page": 1}],
                                           "planless", {})

        outcome = asyncio.run(scenario())
        self.assertFalse(outcome["ok"])
        self.assertIn("只走选中引擎，不降级", outcome["detail"])


class LayoutPythonTest(unittest.TestCase):
    def test_two_column_split_is_detected(self) -> None:
        info = two_column_info()
        split = layout_python._column_split(info)
        self.assertIsNotNone(split)
        self.assertGreater(split, 260.0)
        self.assertLess(split, 330.0)

    def test_two_column_regions_are_read_left_then_right(self) -> None:
        info = two_column_info()
        split = layout_python._column_split(info)
        entry = {"page": 1, "width": 1200, "height": 1600}
        regions = layout_python._column_regions(info, entry, split)
        self.assertEqual([region["no"] for region in regions], [1, 2, 3, 4])
        self.assertLess(regions[0]["x"], regions[2]["x"],
                        "左栏两道题必须排在右栏前面")
        self.assertTrue(all(region["w"] > 0 and region["h"] > 0 for region in regions))

    def test_single_column_orders_by_y_then_x(self) -> None:
        regions = layout_python._ordered([
            {"no": 2, "x": 40, "y": 500},
            {"no": 1, "x": 40, "y": 100},
            {"no": 3, "x": 10, "y": 100},
        ])
        self.assertEqual([region["no"] for region in regions], [3, 1, 2])

    def test_detect_uses_text_layer_and_reports_columns(self) -> None:
        info = two_column_info()
        with mock.patch.object(layout_python.page_render, "pdf_page_lines",
                               return_value=[info]):
            outcome = layout_python.detect({
                "name": "双栏.pdf", "data": b"%PDF",
                "pages": [{"page": 1, "width": 1200, "height": 1600}],
            })
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["engine"], "python")
        self.assertEqual(outcome["columns"][1], 2)
        self.assertEqual(len(outcome["pages"][1]), 4)

    def test_no_text_layer_is_an_honest_failure(self) -> None:
        with mock.patch.object(layout_python.page_render, "pdf_page_lines",
                               return_value=[]):
            outcome = layout_python.detect({
                "name": "扫描.pdf", "data": b"%PDF",
                "pages": [{"page": 1, "width": 1200, "height": 1600}],
            })
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["pages"], {})


if __name__ == "__main__":
    unittest.main()
