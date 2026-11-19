"""MinerU 本地逐题引擎（任务卡 §3/§5）：fake 客户端，绝不起真服务不出网。

覆盖：/v1/tasks 四步回填／部分失败不级联／全失败 ok=False 显性／
等待时限／结果包异常／逐题进度注记。
运行：``.venv/Scripts/python.exe -m unittest tests.test_mineru_local_run``
"""

from __future__ import annotations

import io
import json
import unittest
import zipfile
from unittest import mock

from app.core.ingest.recognize import mineru_local, shared as recognize_shared

ENDPOINT = {"base_url": "http://127.0.0.1:43210", "token": "tok"}
ITEMS = [{"id": "p%d" % index, "question": {"stem": "旧题干"}} for index in range(3)]


def _json(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _zip(markdown: str, name: str = "out/markdown.md") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, markdown)
    return buffer.getvalue()


def _created() -> bytes:
    return _json({"task_id": "t1", "status": "waiting-file", "files": [{
        "file_id": "f1", "file_name": "第1题.png", "status": "waiting-file",
        "upload": {"url": ENDPOINT["base_url"] + "/v1/tasks/t1/uploads/f1",
                   "headers": {"Content-Type": "application/octet-stream"},
                   "expires_at": 9999999999},
    }]})


def _detail(status: str, **extra) -> bytes:
    row = {"file_id": "f1", "status": status, **extra}
    return _json({"task_id": "t1", "status": status, "files": [row]})


def _clock(values: list[float]):
    iterator = iter(values)
    return lambda: next(iterator)


class ParseImageTest(unittest.TestCase):
    def _parse(self, responses, *, wait: float = 900.0,
               clock_values: list[float] | None = None) -> dict:
        clock = _clock(clock_values or [0.0] + [float(i) for i in range(1, 50)])
        with mock.patch.object(mineru_local, "_request",
                               side_effect=responses) as request:
            result = mineru_local.parse_image(
                "第1题.png", b"png-bytes", ENDPOINT,
                wait=wait, sleep=lambda _s: None, clock=clock)
        return {"result": result, "request": request}

    def test_four_step_flow_returns_markdown(self) -> None:
        outcome = self._parse([
            _created(), b"{}",
            _detail("completed",
                    result_url=ENDPOINT["base_url"] + "/v1/files/f1/content"),
            _zip("# 题干\n\n公式 $x^2$"),
        ])
        result = outcome["result"]
        self.assertTrue(result["ok"])
        self.assertIn("$x^2$", result["markdown"])
        calls = outcome["request"].call_args_list
        self.assertEqual(calls[0].kwargs["method"], "POST")
        self.assertEqual(calls[1].kwargs["method"], "PUT")
        self.assertEqual(calls[1].kwargs["raw"], b"png-bytes")
        self.assertIn("/v1/tasks/t1", calls[2].args[0])

    def test_create_failure_is_explicit(self) -> None:
        import urllib.error
        with mock.patch.object(mineru_local, "_request",
                               side_effect=urllib.error.URLError("connection refused")):
            result = mineru_local.parse_image("x.png", b"png", ENDPOINT)
        self.assertFalse(result["ok"])
        self.assertIn("建任务失败", result["detail"])

    def test_missing_upload_url_is_explicit(self) -> None:
        outcome = self._parse([_json({"task_id": "t1", "files": [{"file_id": "f1"}]})])
        self.assertFalse(outcome["result"]["ok"])
        self.assertIn("没有返回上传地址", outcome["result"]["detail"])

    def test_failed_task_carries_server_reason(self) -> None:
        outcome = self._parse([
            _created(), b"{}",
            _detail("failed", error={"code": "parse_error", "message": "模型加载失败"}),
        ])
        result = outcome["result"]
        self.assertFalse(result["ok"])
        self.assertIn("模型加载失败", result["detail"])

    def test_wait_deadline_is_explicit(self) -> None:
        outcome = self._parse([_created(), b"{}", _detail("running")],
                              wait=10.0, clock_values=[0.0, 5.0, 100.0])
        result = outcome["result"]
        self.assertFalse(result["ok"])
        self.assertIn("没有返回结果", result["detail"])
        self.assertIn("running", result["detail"])

    def test_result_zip_without_markdown_is_explicit(self) -> None:
        outcome = self._parse([
            _created(), b"{}",
            _detail("completed", result_url=ENDPOINT["base_url"] + "/r"),
            _zip("x", name="out/image.png"),
        ])
        self.assertFalse(outcome["result"]["ok"])
        self.assertIn("没有 Markdown", outcome["result"]["detail"])

    def test_bad_zip_is_explicit(self) -> None:
        outcome = self._parse([
            _created(), b"{}",
            _detail("completed", result_url=ENDPOINT["base_url"] + "/r"),
            b"not-a-zip",
        ])
        self.assertFalse(outcome["result"]["ok"])
        self.assertIn("结果包下载/解压失败", outcome["result"]["detail"])

    def test_missing_endpoint_is_explicit(self) -> None:
        result = mineru_local.parse_image("x.png", b"png", {"base_url": "", "token": ""})
        self.assertFalse(result["ok"])
        self.assertIn("服务地址缺失", result["detail"])


class EquationBoxesTest(unittest.TestCase):
    def _blob(self, middle: dict) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("out/middle_json.json", _json(middle))
        return buffer.getvalue()

    def test_display_equation_blocks_extract_normalized_bbox(self) -> None:
        middle = {"pages": [{"para_blocks": [
            {"type": "text", "bbox": [0.1, 0.1, 0.9, 0.2], "lines": [
                {"spans": [{"type": "equation_inline", "content": "x^2"}]}]},
            {"type": "interline_equation", "bbox": [0.2, 0.3, 0.8, 0.45],
             "content": "\\frac{1}{a}+\\frac{4}{b}=1"},
            {"type": "equation", "bbox": [0.2, 0.5, 0.8, 0.6], "content": "a+b"},
        ]}]}
        boxes = mineru_local._equation_boxes(self._blob(middle))
        self.assertEqual(len(boxes), 2)
        self.assertEqual(boxes[0]["bbox"], [0.2, 0.3, 0.8, 0.45])
        self.assertIn("\\frac", boxes[0]["latex"])

    def test_inline_equations_without_bbox_are_skipped(self) -> None:
        middle = {"pages": [{"para_blocks": [
            {"type": "text", "bbox": [0.1, 0.1, 0.9, 0.9], "lines": [
                {"spans": [{"type": "equation_inline", "content": "a>0"}]}]},
        ]}]}
        self.assertEqual(mineru_local._equation_boxes(self._blob(middle)), [])

    def test_missing_middle_json_returns_empty(self) -> None:
        self.assertEqual(mineru_local._equation_boxes(_zip("# 题干")), [])


class RunTest(unittest.IsolatedAsyncioTestCase):
    def _patches(self, outcomes, *, save_ok: bool = True,
                 image_bytes: list[bytes] | None = None):
        documents = ([{"stem": "新题干"}], [])
        return [
            mock.patch.object(recognize_shared, "item_image_bytes",
                              side_effect=image_bytes or [b"png"] * len(ITEMS)),
            mock.patch.object(mineru_local, "parse_image", side_effect=outcomes),
            mock.patch("app.core.ingest.service.build_documents",
                       return_value=documents),
            mock.patch.object(recognize_shared, "merge_local",
                              side_effect=lambda doc, question: {"merged": True}),
            mock.patch.object(recognize_shared, "save_back", return_value=save_ok),
        ]

    async def _run(self, outcomes, indexes=None, **kwargs) -> dict:
        route: dict = {}
        notes: list[str] = []
        patches = self._patches(outcomes, **kwargs)
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        result = await mineru_local.run(
            "B-001", ITEMS, indexes if indexes is not None else [0, 1, 2],
            ENDPOINT, route,
            on_progress=lambda snapshot: notes.append(str(snapshot.get("note") or "")))
        return {"result": result, "route": route, "notes": notes}

    async def test_per_item_fill_all_success(self) -> None:
        ok = {"ok": True, "markdown": "# 题干", "detail": ""}
        outcome = await self._run([ok, ok, ok])
        result = outcome["result"]
        self.assertTrue(result["ok"])
        self.assertEqual(result["filled"], 3)
        self.assertEqual(result["filled_indexes"], [0, 1, 2])
        self.assertTrue(any("第 1/3 题" in note for note in outcome["notes"]))
        save = recognize_shared.save_back
        self.assertEqual(save.call_count, 3)
        self.assertEqual(save.call_args.args[3], "ingest.mineru_local")

    async def test_partial_failure_keeps_going_without_cascade(self) -> None:
        ok = {"ok": True, "markdown": "# 题干", "detail": ""}
        bad = {"ok": False, "detail": "本地 MinerU 解析失败：模型加载失败"}
        outcome = await self._run([ok, bad, ok])
        result = outcome["result"]
        self.assertTrue(result["ok"])
        self.assertEqual(result["filled"], 2)
        self.assertEqual(result["filled_indexes"], [0, 2])
        self.assertIn("只有 2/3", result["detail"])
        self.assertTrue(any("没成功" in note for note in outcome["notes"]))

    async def test_all_failure_is_ok_false_explicit(self) -> None:
        bad = {"ok": False, "detail": "服务不可用"}
        outcome = await self._run([bad, bad, bad])
        result = outcome["result"]
        self.assertFalse(result["ok"])
        self.assertEqual(result["filled"], 0)
        self.assertEqual(result["filled_indexes"], [])
        self.assertIn("只有 0/3", result["detail"])

    async def test_empty_indexes_is_noop(self) -> None:
        outcome = await self._run([], indexes=[])
        self.assertTrue(outcome["result"]["ok"])
        self.assertEqual(outcome["result"]["attempted"], 0)
        mineru_local.parse_image.assert_not_called()

    async def test_missing_image_skips_item(self) -> None:
        ok = {"ok": True, "markdown": "# 题干", "detail": ""}
        outcome = await self._run([ok, ok], image_bytes=[b"", b"png", b"png"])
        result = outcome["result"]
        self.assertEqual(result["attempted"], 3)
        self.assertEqual(result["filled"], 2)
        self.assertEqual(result["filled_indexes"], [1, 2])

    async def test_save_back_failure_is_not_counted(self) -> None:
        ok = {"ok": True, "markdown": "# 题干", "detail": ""}
        outcome = await self._run([ok, ok, ok], save_ok=False)
        self.assertFalse(outcome["result"]["ok"])
        self.assertEqual(outcome["result"]["filled"], 0)


if __name__ == "__main__":
    unittest.main()