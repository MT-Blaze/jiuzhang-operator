"""MinerU 云端整批（mineru-batch 卡 §4）：mock 钉死映射/账本/时限，回环钉死线上头。

覆盖：N 份映射同序／部分 failed 逐份账本／到点部分回填／并行 PUT 零
Content-Type（回环实收头断言，test_mineru_extract 先例）／单题 extract 回归不动／
run() 整批发送与「已回 N/M 题」进度。
运行：``.venv/Scripts/python.exe -m unittest tests.test_mineru_batch``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

import io
import threading
import unittest
import urllib.error
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from app.core import wire
from app.core.ai.platform import center as ai_center
from app.core.ingest.recognize import mineru, mineru_extract
from app.core.ingest.recognize import shared as recognize_shared

BASE = "https://mineru.test"
TOKEN = "fixture-key"
SIGNED_QUERY = "Expires=1795171953&OSSAccessKeyId=TESTKEY&Signature=abc%2Fdef%3D"


def _zip_with_markdown(text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("full.md", text)
    return buffer.getvalue()


def _json(payload: dict) -> bytes:
    return wire.dumps(payload, ensure_ascii=False).encode("utf-8")


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def clock(self) -> float:
        return self.now


def _binding() -> ai_center.TaskBinding:
    return ai_center.TaskBinding(task="recognize", account_id="a1", name="MinerU",
                                 base_url=BASE, api_key=TOKEN, model="mineru")


class _BatchServer:
    """mock _request 的调度台：按 URL 与方法派发预设响应，记录全部调用。"""

    def __init__(self, files_count: int, *, rows_plan: list[list[dict]],
                 zip_text: dict[int, str] | None = None,
                 put_error_indexes: set[int] | None = None,
                 poll_error_at: int | None = None) -> None:
        self.files_count = files_count
        self.rows_plan = rows_plan
        self.zip_text = zip_text or {}
        self.put_error_indexes = put_error_indexes or set()
        self.poll_error_at = poll_error_at
        self.posts: list[dict] = []
        self.puts: list[tuple[str, bytes]] = []
        self.polls: list[str] = []
        self.zip_gets: list[str] = []
        self.data_ids: list[str] = []
        self.batch_ids: list[str] = []

    def request(self, url: str, *, method: str = "GET", token: str = "",
                payload: dict | None = None, timeout: float = 30) -> bytes:
        if method == "POST" and url.endswith("/file-urls/batch"):
            self.posts.append(payload)
            names = payload["files"]
            self.data_ids.extend(str(item["data_id"]) for item in names)
            batch_id = "batch-%d" % len(self.posts)
            self.batch_ids.append(batch_id)
            start = sum(len(post["files"]) for post in self.posts[:-1])
            return _json({"code": 0, "data": {
                "batch_id": batch_id,
                "file_urls": ["%s/upload/%d?%s" % (BASE, start + i, SIGNED_QUERY)
                              for i in range(len(names))],
            }})
        if "/extract-results/batch/" in url:
            self.polls.append(url)
            if self.poll_error_at == len(self.polls):
                raise urllib.error.URLError("poll connection reset")
            plan_index = min(len(self.polls) - 1, len(self.rows_plan) - 1)
            rows = []
            for row in self.rows_plan[plan_index]:
                if int(row["data_id"]) >= len(self.data_ids):
                    continue
                row = dict(row)
                row["data_id"] = self.data_ids[int(row["data_id"])]
                if row.get("state") == "done" and "full_zip_url" not in row:
                    row["full_zip_url"] = "%s/zip/%s" % (
                        BASE, row["data_id"].rsplit("-", 2)[-2])
                rows.append(row)
            return _json({"code": 0, "data": {"extract_result": rows}})
        if "/zip/" in url:
            self.zip_gets.append(url)
            index = int(url.rsplit("/", 1)[-1])
            return _zip_with_markdown(self.zip_text.get(index, "# 第%d题" % index))
        raise AssertionError("unexpected request %s %s" % (method, url))

    def put(self, url: str, data: bytes, timeout: float) -> None:
        self.puts.append((url, data))
        index = int(url.split("/upload/", 1)[1].split("?", 1)[0])
        if index in self.put_error_indexes:
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)


def _files(count: int) -> list[tuple[str, bytes]]:
    return [("第%d题.png" % (i + 1), b"PNG-BYTES-%d" % i) for i in range(count)]


class BatchMockTest(unittest.TestCase):
    def _run(self, count: int, server: _BatchServer, *, wait: float = 900.0,
             on_progress=None) -> list[dict]:
        clock = _FakeClock()
        with mock.patch.object(mineru_extract, "_request",
                               side_effect=server.request), \
                mock.patch.object(mineru_extract, "_put_raw",
                                  side_effect=server.put):
            return mineru_extract.extract_batch(
                _files(count), BASE, TOKEN, wait=wait,
                sleep=clock.sleep, clock=clock.clock, on_progress=on_progress)

    def test_01_n_files_map_back_in_input_order(self) -> None:
        server = _BatchServer(3, rows_plan=[[
            {"data_id": "2", "state": "done"},
            {"data_id": "0", "state": "done"},
            {"data_id": "1", "state": "done"},
        ]], zip_text={0: "# 甲", 1: "# 乙", 2: "# 丙"})
        outcomes = self._run(3, server)
        self.assertEqual([outcome["ok"] for outcome in outcomes], [True] * 3)
        self.assertEqual([outcome["markdown"] for outcome in outcomes],
                         ["# 甲", "# 乙", "# 丙"])
        self.assertEqual(len(server.posts), 1)
        self.assertEqual(len(server.posts[0]["files"]), 3)
        self.assertEqual(len(set(server.data_ids)), 3)
        self.assertEqual(len(server.puts), 3)
        self.assertEqual({url for url, _data in server.puts},
                         {"%s/upload/%d?%s" % (BASE, i, SIGNED_QUERY) for i in range(3)})
        for url, data in server.puts:
            index = int(url.split("/upload/", 1)[1].split("?", 1)[0])
            self.assertEqual(data, b"PNG-BYTES-%d" % index)
        self.assertTrue(all(url.endswith("/extract-results/batch/batch-1")
                            for url in server.polls))

    def test_02_partial_failed_keeps_per_item_ledger(self) -> None:
        server = _BatchServer(3, rows_plan=[[
            {"data_id": "0", "state": "done"},
            {"data_id": "1", "state": "failed", "err_msg": "文件格式不支持"},
            {"data_id": "2", "state": "done"},
        ]])
        outcomes = self._run(3, server)
        self.assertTrue(outcomes[0]["ok"])
        self.assertFalse(outcomes[1]["ok"])
        self.assertIn("文件格式不支持", outcomes[1]["detail"])
        self.assertTrue(outcomes[2]["ok"])
        self.assertEqual(len(server.posts), 1)

    def test_03_deadline_fills_done_rows_and_fails_rest(self) -> None:
        server = _BatchServer(2, rows_plan=[[
            {"data_id": "0", "state": "done"},
            {"data_id": "1", "state": "running"},
        ]])
        outcomes = self._run(2, server, wait=5.0)
        self.assertTrue(outcomes[0]["ok"])
        self.assertFalse(outcomes[1]["ok"])
        self.assertIn("没有返回结果", outcomes[1]["detail"])
        self.assertIn("running", outcomes[1]["detail"])
        self.assertEqual(len(server.zip_gets), 1)

    def test_04_put_failure_is_per_item(self) -> None:
        server = _BatchServer(3, rows_plan=[[
            {"data_id": "0", "state": "done"},
            {"data_id": "2", "state": "done"},
        ]], put_error_indexes={1})
        outcomes = self._run(3, server)
        self.assertTrue(outcomes[0]["ok"])
        self.assertFalse(outcomes[1]["ok"])
        self.assertIn("上传原文件失败", outcomes[1]["detail"])
        self.assertIn("403", outcomes[1]["detail"])
        self.assertTrue(outcomes[2]["ok"])

    def test_05_poll_error_keeps_already_done_rows(self) -> None:
        server = _BatchServer(2, rows_plan=[[
            {"data_id": "0", "state": "done"},
            {"data_id": "1", "state": "running"},
        ]], poll_error_at=2)
        outcomes = self._run(2, server)
        self.assertTrue(outcomes[0]["ok"])
        self.assertFalse(outcomes[1]["ok"])
        self.assertIn("查询结果失败", outcomes[1]["detail"])

    def test_06_progress_reports_settled_counts(self) -> None:
        seen: list[tuple[int, int]] = []
        server = _BatchServer(3, rows_plan=[[
            {"data_id": "0", "state": "done"},
            {"data_id": "1", "state": "failed", "err_msg": "坏图"},
            {"data_id": "2", "state": "running"},
        ], [
            {"data_id": "0", "state": "done"},
            {"data_id": "1", "state": "failed", "err_msg": "坏图"},
            {"data_id": "2", "state": "done"},
        ]])
        outcomes = self._run(3, server, on_progress=lambda done, total: seen.append((done, total)))
        self.assertEqual([outcome["ok"] for outcome in outcomes], [True, False, True])
        self.assertEqual(seen[-1], (3, 3))
        self.assertEqual(seen, sorted(seen))
        self.assertTrue(all(total == 3 for _done, total in seen))

    def test_07_over_50_files_splits_into_chunks(self) -> None:
        count = mineru_extract.BATCH_MAX_FILES + 1
        server = _BatchServer(count, rows_plan=[[
            {"data_id": str(i), "state": "done"} for i in range(count)
        ]])
        outcomes = self._run(count, server)
        self.assertEqual(len(outcomes), count)
        self.assertTrue(all(outcome["ok"] for outcome in outcomes))
        self.assertEqual([len(post["files"]) for post in server.posts],
                         [mineru_extract.BATCH_MAX_FILES, 1])
        self.assertEqual(len(set(server.batch_ids)), 2)
        self.assertEqual(len(server.puts), count)

    def test_08_single_file_batch_works(self) -> None:
        server = _BatchServer(1, rows_plan=[[{"data_id": "0", "state": "done"}]],
                              zip_text={0: "# 单题"})
        outcomes = self._run(1, server)
        self.assertEqual(outcomes, [{"ok": True, "markdown": "# 单题",
                                     "detail": "MinerU 已识别"}])

    def test_09_empty_input_returns_empty(self) -> None:
        self.assertEqual(mineru_extract.extract_batch([], BASE, TOKEN), [])

    def test_10_missing_token_fails_every_item(self) -> None:
        outcomes = mineru_extract.extract_batch(_files(2), BASE, "")
        self.assertEqual(len(outcomes), 2)
        self.assertTrue(all(not outcome["ok"] for outcome in outcomes))
        self.assertIn("API Key", outcomes[0]["detail"])

    def test_11_post_rejection_fails_every_item(self) -> None:
        with mock.patch.object(mineru_extract, "_request",
                               return_value=_json({"code": -60005, "msg": "文件超限"})):
            outcomes = mineru_extract.extract_batch(_files(2), BASE, TOKEN)
        self.assertTrue(all(not outcome["ok"] for outcome in outcomes))
        self.assertIn("文件超限", outcomes[0]["detail"])

    def test_12_url_count_mismatch_fails_every_item(self) -> None:
        with mock.patch.object(mineru_extract, "_request",
                               return_value=_json({"code": 0, "data": {
                                   "batch_id": "b", "file_urls": ["u"]}})):
            outcomes = mineru_extract.extract_batch(_files(2), BASE, TOKEN)
        self.assertTrue(all(not outcome["ok"] for outcome in outcomes))
        self.assertIn("数量与文件数不符", outcomes[0]["detail"])

    def test_13_single_extract_regression_untouched(self) -> None:
        """单题重认路仍走 extract()：一次 POST 单元素、urls[0]、单份轮询。"""
        clock = _FakeClock()
        calls: list[tuple[str, dict | None]] = []

        def request(url, *, method="GET", token="", payload=None, timeout=30):
            calls.append((url, payload))
            if method == "POST":
                return _json({"code": 0, "data": {
                    "batch_id": "solo", "file_urls": [BASE + "/upload/0?" + SIGNED_QUERY]}})
            if "/extract-results/" in url:
                return _json({"code": 0, "data": {"extract_result": [
                    {"state": "done", "full_zip_url": BASE + "/zip/0"}]}})
            return _zip_with_markdown("# 单题回归")

        with mock.patch.object(mineru_extract, "_request", side_effect=request), \
                mock.patch.object(mineru_extract, "_put_raw") as put:
            outcome = mineru_extract.extract("卷.png", b"PNG", BASE, TOKEN,
                                             wait=10, sleep=clock.sleep, clock=clock.clock)
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["markdown"], "# 单题回归")
        self.assertEqual(len(calls[0][1]["files"]), 1)
        put.assert_called_once()


class _WireHandler(BaseHTTPRequestHandler):
    legs: list[dict] = []
    barrier: threading.Barrier | None = None
    data_ids: list[str] = []

    def _record(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        _WireHandler.legs.append({
            "method": self.command, "path": self.path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": body,
        })
        return body

    def _json(self, payload: dict) -> None:
        body = wire.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - http.server 命名约定
        payload = wire.loads(self._record().decode("utf-8"))
        _WireHandler.data_ids = [str(item["data_id"]) for item in payload["files"]]
        port = self.server.server_address[1]
        self._json({"code": 0, "data": {
            "batch_id": "batch-wire",
            "file_urls": ["http://127.0.0.1:%d/upload/%d?%s" % (port, i, SIGNED_QUERY)
                          for i in range(len(payload["files"]))],
        }})

    def do_PUT(self) -> None:  # noqa: N802
        self._record()
        if _WireHandler.barrier is not None:
            try:
                _WireHandler.barrier.wait(timeout=10)
            except threading.BrokenBarrierError:
                self.send_response(500)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._record()
        if self.path.startswith("/api/v4/extract-results/batch/"):
            port = self.server.server_address[1]
            self._json({"code": 0, "data": {"extract_result": [
                {"data_id": data_id, "state": "done",
                 "full_zip_url": "http://127.0.0.1:%d/zip/%d" % (port, i)}
                for i, data_id in enumerate(_WireHandler.data_ids)
            ]}})
            return
        index = int(self.path.rsplit("/", 1)[-1])
        blob = _zip_with_markdown("# 第%d题\n求 $x+%d=2$ 的解。" % (index + 1, index))
        self.send_response(200)
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def log_message(self, *args) -> None:
        pass


class BatchWireTest(unittest.TestCase):
    """回环实收头断言：整批并行 PUT 线上零 Content-Type、签名 query 不被污染。"""

    def setUp(self) -> None:
        _WireHandler.legs = []
        _WireHandler.data_ids = []
        _WireHandler.barrier = threading.Barrier(4)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _WireHandler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _legs(self, method: str) -> list[dict]:
        return [leg for leg in _WireHandler.legs if leg["method"] == method]

    def test_01_batch_put_parallel_and_no_content_type(self) -> None:
        clock = _FakeClock()
        outcomes = mineru_extract.extract_batch(
            _files(4), self.base, TOKEN, wait=10,
            sleep=clock.sleep, clock=clock.clock)
        self.assertEqual([outcome["ok"] for outcome in outcomes], [True] * 4)
        self.assertEqual([outcome["markdown"].splitlines()[0] for outcome in outcomes],
                         ["# 第%d题" % (i + 1) for i in range(4)])
        self.assertEqual(len(self._legs("POST")), 1)
        puts = self._legs("PUT")
        self.assertEqual(len(puts), 4)
        for leg in puts:
            self.assertNotIn("content-type", leg["headers"])
            index = int(leg["path"].split("/upload/", 1)[1].split("?", 1)[0])
            self.assertEqual(leg["body"], b"PNG-BYTES-%d" % index)
            self.assertEqual(leg["path"], "/upload/%d?%s" % (index, SIGNED_QUERY))
        polls = self._legs("GET")
        poll_paths = {leg["path"] for leg in polls
                      if leg["path"].startswith("/api/v4/extract-results/batch/")}
        self.assertEqual(poll_paths, {"/api/v4/extract-results/batch/batch-wire"})


class RunBatchTest(unittest.IsolatedAsyncioTestCase):
    """run() 整批：一次 extract_batch、进度「已回 N/M 题」、失败逐题账本照旧形状。"""

    items = [{"id": "p%d" % i, "question": {"stem": "旧题干"}} for i in range(3)]

    def _patches(self, outcomes, *, image_bytes=None, save_ok=True):
        def fake_batch(files, base_url, token, *, model="", wait=900.0,
                       on_progress=None, **_kwargs):
            fake_batch.files = files
            if on_progress is not None:
                for settled in range(1, len(files) + 1):
                    on_progress(settled, len(files))
            return outcomes

        fake_batch.files = None
        return fake_batch, [
            mock.patch.object(recognize_shared, "item_image_bytes",
                              side_effect=image_bytes or [b"png"] * len(self.items)),
            mock.patch.object(mineru_extract, "extract_batch", side_effect=fake_batch),
            mock.patch("app.core.ingest.service.build_documents",
                       return_value=([{"stem": "新题干"}], [])),
            mock.patch.object(recognize_shared, "merge_local",
                              side_effect=lambda doc, question: {"merged": True}),
            mock.patch.object(recognize_shared, "save_back", return_value=save_ok),
        ]

    async def _run(self, outcomes, indexes=None, **kwargs) -> dict:
        route: dict = {}
        notes: list[str] = []
        fake_batch, patches = self._patches(outcomes, **kwargs)
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        result = await mineru.run(
            "B-001", self.items, indexes if indexes is not None else [0, 1, 2],
            _binding(), route,
            on_progress=lambda snapshot: notes.append(str(snapshot.get("note") or "")))
        return {"result": result, "route": route, "notes": notes,
                "files": fake_batch.files}

    async def test_01_one_batch_send_and_fill_all(self) -> None:
        ok = {"ok": True, "markdown": "# 题干", "detail": ""}
        outcome = await self._run([ok, ok, ok])
        result = outcome["result"]
        self.assertTrue(result["ok"])
        self.assertEqual(result["filled_indexes"], [0, 1, 2])
        self.assertEqual([name for name, _data in outcome["files"]],
                         ["第1题.png", "第2题.png", "第3题.png"])
        self.assertTrue(any("整批发送" in note for note in outcome["notes"]))
        self.assertTrue(any("已回 1/3 题" in note for note in outcome["notes"]))
        self.assertTrue(any("已回 3/3 题" in note for note in outcome["notes"]))
        save = recognize_shared.save_back
        self.assertEqual(save.call_count, 3)
        self.assertEqual(save.call_args.args[3], "ingest.mineru")

    async def test_02_partial_failure_ledger_keeps_old_shape(self) -> None:
        ok = {"ok": True, "markdown": "# 题干", "detail": ""}
        bad = {"ok": False, "detail": "MinerU 解析失败：坏图"}
        outcome = await self._run([ok, bad, ok])
        result = outcome["result"]
        self.assertTrue(result["ok"])
        self.assertEqual(result["filled_indexes"], [0, 2])
        self.assertIn("只有 2/3", result["detail"])
        self.assertTrue(any("第 2/3 题 MinerU 没成功" in note and "坏图" in note
                            for note in outcome["notes"]))

    async def test_03_missing_image_skips_before_send(self) -> None:
        ok = {"ok": True, "markdown": "# 题干", "detail": ""}
        outcome = await self._run([ok, ok], image_bytes=[b"", b"png", b"png"])
        result = outcome["result"]
        self.assertEqual(result["attempted"], 3)
        self.assertEqual(result["filled_indexes"], [1, 2])
        self.assertEqual([name for name, _data in outcome["files"]],
                         ["第2题.png", "第3题.png"])

    async def test_04_all_images_missing_never_sends(self) -> None:
        outcome = await self._run([], image_bytes=[b"", b"", b""])
        self.assertFalse(outcome["result"]["ok"])
        self.assertIn("只有 0/3", outcome["result"]["detail"])
        self.assertIsNone(outcome["files"])

    async def test_05_empty_indexes_is_noop(self) -> None:
        outcome = await self._run([], indexes=[])
        self.assertTrue(outcome["result"]["ok"])
        self.assertEqual(outcome["result"]["attempted"], 0)
        self.assertIsNone(outcome["files"])

    async def test_06_no_binding_is_explicit(self) -> None:
        route: dict = {}
        result = await mineru.run("B-001", self.items, [0], None, route)
        self.assertFalse(result["ok"])
        self.assertIn("没有可用的 MinerU 账号", result["detail"])


if __name__ == "__main__":
    unittest.main()