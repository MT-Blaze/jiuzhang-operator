"""MinerU 超量自动分批（2026-11-20 拍板）：按单批上限顺序拆批、批间不并发、失败即停。

全用假客户端：调度层假提交记录调用时间线与在途峰值；HTTP 层假 _request/_put_raw
数 POST/PUT 次数——绝不出网、不耗云额度。
运行：``.venv/Scripts/python.exe -m unittest tests.test_mineru_auto_batch``
"""

from __future__ import annotations

import io
import unittest
import zipfile
from unittest import mock

from app.core import wire
from app.core.ai.platform import center as ai_center
from app.core.ingest.recognize import (mineru, mineru_batching, mineru_extract,
                                       shared as recognize_shared)

BASE = "https://mineru.test"
TOKEN = "fixture-key"
SIZE = mineru_extract.BATCH_MAX_FILES


def _files(count: int) -> list[tuple[str, bytes]]:
    return [("第%d题.png" % (index + 1), b"PNG-%d" % index) for index in range(count)]


def _json(payload: dict) -> bytes:
    return wire.dumps(payload, ensure_ascii=False).encode("utf-8")


def _zip(markdown: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("full.md", markdown)
    return buffer.getvalue()


class _Recorder:
    """调度层假提交：记录批大小/时间线/在途峰值，按 plan 返回逐份结果。"""

    def __init__(self, plan=None) -> None:
        self.plan = plan or (lambda _index, files: [
            {"ok": True, "markdown": name, "detail": "MinerU 已识别"}
            for name, _data in files])
        self.batches: list[list[str]] = []
        self.timeline: list[str] = []
        self.active = 0
        self.max_active = 0
        self.progress: list[tuple[int, int]] = []

    def __call__(self, files, base_url, token, *, model="", wait=900.0,
                 sleep=None, clock=None, on_progress=None) -> list[dict]:
        index = len(self.batches)
        self.batches.append([name for name, _data in files])
        self.timeline.append("batch-%d" % index)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if on_progress is not None:
                for settled in range(1, len(files) + 1):
                    on_progress(settled, len(files))
                    self.progress.append((settled, len(files)))
            return self.plan(index, files)
        finally:
            self.active -= 1


def _run(count: int, recorder: _Recorder, **kwargs) -> list[dict]:
    with mock.patch.object(mineru_extract, "extract_batch", side_effect=recorder):
        return mineru_batching.extract_in_batches(
            _files(count), BASE, TOKEN, **kwargs)


class SplitCountTest(unittest.TestCase):
    """页数 0/1/40/41/80/81：提交次数、每批页数、批间顺序。"""

    def test_00_empty_never_submits(self) -> None:
        recorder = _Recorder()
        self.assertEqual(_run(0, recorder), [])
        self.assertEqual(recorder.batches, [])

    def test_01_up_to_limit_is_single_submit(self) -> None:
        for count in (1, SIZE):
            with self.subTest(count=count):
                recorder = _Recorder()
                batches = []
                outcomes = _run(count, recorder, on_batch=lambda *args: batches.append(args))
                self.assertEqual(len(recorder.batches), 1)
                self.assertEqual(len(recorder.batches[0]), count)
                self.assertEqual(len(outcomes), count)
                self.assertEqual(batches, [], "单批不报分批进度")

    def test_02_over_limit_splits_in_order(self) -> None:
        cases = {
            SIZE + 1: [SIZE, 1],
            SIZE * 2: [SIZE, SIZE],
            SIZE * 2 + 1: [SIZE, SIZE, 1],
        }
        for count, expected in cases.items():
            with self.subTest(count=count):
                recorder = _Recorder()
                labels: list[tuple[int, int, int, int]] = []
                outcomes = _run(count, recorder,
                                on_batch=lambda *args: labels.append(args))
                self.assertEqual([len(batch) for batch in recorder.batches], expected)
                rounds = len(expected)
                self.assertEqual(labels, [
                    (number, rounds, (number - 1) * SIZE + 1,
                     (number - 1) * SIZE + expected[number - 1])
                    for number in range(1, rounds + 1)
                ])
                self.assertEqual(recorder.timeline,
                                 ["batch-%d" % index for index in range(rounds)])
                self.assertEqual(len(outcomes), count)

    def test_03_pages_per_batch_never_exceed_limit(self) -> None:
        recorder = _Recorder()
        _run(SIZE * 3 + 7, recorder)
        self.assertTrue(all(len(batch) <= SIZE for batch in recorder.batches))
        self.assertEqual([len(batch) for batch in recorder.batches],
                         [SIZE, SIZE, SIZE, 7])


class MergeOrderTest(unittest.TestCase):
    def test_merged_outcomes_follow_input_order(self) -> None:
        recorder = _Recorder()
        outcomes = _run(SIZE * 2 + 1, recorder)
        self.assertEqual([outcome["markdown"] for outcome in outcomes],
                         [name for name, _data in _files(SIZE * 2 + 1)])


class FailureStopTest(unittest.TestCase):
    def _failing_second(self, _index: int, files) -> list[dict]:
        if _index == 1:
            return [{"ok": False, "detail": "MinerU 查询结果失败：connection reset"}
                    for _ in files]
        return [{"ok": True, "markdown": name, "detail": "MinerU 已识别"}
                for name, _data in files]

    def test_second_batch_failure_stops_third_and_keeps_first(self) -> None:
        recorder = _Recorder(self._failing_second)
        outcomes = _run(SIZE * 2 + 1, recorder)
        self.assertEqual([len(batch) for batch in recorder.batches], [SIZE, SIZE],
                         "第 2 批整批失败后不得再发第 3 批")
        self.assertEqual(len(outcomes), SIZE * 2 + 1)
        first = outcomes[:SIZE]
        self.assertTrue(all(outcome["ok"] for outcome in first), "第 1 批结果不丢")
        self.assertEqual(first[0]["markdown"], "第1题.png")
        for outcome in outcomes[SIZE:SIZE * 2]:
            self.assertFalse(outcome["ok"])
            self.assertIn("第 2/3 批失败", outcome["detail"])
            self.assertIn("connection reset", outcome["detail"], "原有失败文案保留")
        self.assertFalse(outcomes[SIZE * 2]["ok"])
        self.assertIn("第 3/3 批未发送", outcomes[SIZE * 2]["detail"])
        self.assertIn("第 2/3 批识别失败", outcomes[SIZE * 2]["detail"])

    def test_single_item_failure_does_not_stop_next_batch(self) -> None:
        def plan(_index: int, files) -> list[dict]:
            if _index == 0:
                results = [{"ok": True, "markdown": name, "detail": "ok"}
                           for name, _data in files]
                results[0] = {"ok": False, "detail": "MinerU 解析失败：坏图"}
                return results
            return [{"ok": True, "markdown": name, "detail": "ok"}
                    for name, _data in files]

        recorder = _Recorder(plan)
        outcomes = _run(SIZE + 1, recorder)
        self.assertEqual(len(recorder.batches), 2, "批内个别题失败不算整批失败")
        self.assertFalse(outcomes[0]["ok"])
        self.assertTrue(outcomes[SIZE]["ok"])


class NonConcurrentTest(unittest.TestCase):
    def test_at_most_one_submission_in_flight(self) -> None:
        recorder = _Recorder()
        _run(SIZE * 2 + 1, recorder)
        self.assertEqual(recorder.max_active, 1)
        self.assertEqual(len(recorder.timeline), 3, "顺序发送：前一提交返回后才发下一批")


class ProgressTest(unittest.TestCase):
    def test_progress_is_cumulative_across_batches(self) -> None:
        recorder = _Recorder()
        seen: list[tuple[int, int]] = []
        _run(SIZE * 2 + 1, recorder, on_progress=lambda done, total: seen.append((done, total)))
        self.assertEqual(seen[0], (1, SIZE * 2 + 1))
        self.assertEqual(seen[-1], (SIZE * 2 + 1, SIZE * 2 + 1))
        self.assertEqual(seen, sorted(seen), "已回份数只增不减")
        self.assertEqual(len(seen), SIZE * 2 + 1)
        self.assertTrue(all(total == SIZE * 2 + 1 for _done, total in seen))

    def test_single_batch_progress_is_unchanged(self) -> None:
        recorder = _Recorder()
        seen: list[tuple[int, int]] = []
        _run(SIZE, recorder, on_progress=lambda done, total: seen.append((done, total)))
        self.assertEqual(seen[-1], (SIZE, SIZE))


class _Cloud:
    """HTTP 层假云端：记录 POST 批、PUT 次数；轮询全 done、zip 即回。"""

    def __init__(self) -> None:
        self.posts: list[list[str]] = []
        self.batches: dict[str, list[str]] = {}
        self.puts = 0

    def request(self, url: str, *, method: str = "GET", token: str = "",
                payload: dict | None = None, timeout: float = 30) -> bytes:
        if method == "POST":
            ids = [str(item["data_id"]) for item in payload["files"]]
            batch_id = "b%d" % len(self.posts)
            self.posts.append(ids)
            self.batches[batch_id] = ids
            return _json({"code": 0, "data": {
                "batch_id": batch_id,
                "file_urls": ["%s/upload/%s?x=1" % (BASE, data_id) for data_id in ids],
            }})
        if "/extract-results/batch/" in url:
            ids = self.batches[url.rsplit("/", 1)[-1]]
            return _json({"code": 0, "data": {"extract_result": [
                {"data_id": data_id, "state": "done",
                 "full_zip_url": "%s/zip/%s" % (BASE, data_id)}
                for data_id in ids
            ]}})
        if "/zip/" in url:
            return _zip("# " + url.rsplit("/", 1)[-1])
        raise AssertionError("unexpected request %s %s" % (method, url))

    def put(self, url: str, data: bytes, timeout: float) -> None:
        self.puts += 1


class HttpRequestCountTest(unittest.TestCase):
    """真提交函数 + 假 HTTP：每批恰好一次 POST，页数切分与调度一致。"""

    def _run(self, count: int) -> dict:
        cloud = _Cloud()
        with mock.patch.object(mineru_extract, "_request", side_effect=cloud.request), \
                mock.patch.object(mineru_extract, "_put_raw", side_effect=cloud.put):
            outcomes = mineru_batching.extract_in_batches(
                _files(count), BASE, TOKEN, wait=10,
                sleep=lambda _seconds: None, clock=lambda: 0.0)
        return {"outcomes": outcomes, "cloud": cloud}

    def test_40_pages_one_post(self) -> None:
        result = self._run(SIZE)
        self.assertEqual([len(post) for post in result["cloud"].posts], [SIZE])
        self.assertEqual(result["cloud"].puts, SIZE)
        self.assertTrue(all(outcome["ok"] for outcome in result["outcomes"]))

    def test_41_pages_two_posts_sequentially(self) -> None:
        result = self._run(SIZE + 1)
        self.assertEqual([len(post) for post in result["cloud"].posts], [SIZE, 1])
        self.assertEqual(result["cloud"].puts, SIZE + 1)

    def test_81_pages_three_posts(self) -> None:
        result = self._run(SIZE * 2 + 1)
        self.assertEqual([len(post) for post in result["cloud"].posts], [SIZE, SIZE, 1])
        self.assertEqual(result["cloud"].puts, SIZE * 2 + 1)
        self.assertEqual(len(result["outcomes"]), SIZE * 2 + 1)


def _binding() -> ai_center.TaskBinding:
    return ai_center.TaskBinding(task="recognize", account_id="a1", name="MinerU",
                                 base_url=BASE, api_key=TOKEN, model="mineru")


class RunBatchNoticeTest(unittest.IsolatedAsyncioTestCase):
    """run() 接上分批：多批有「分 X 批」与「分批识别中（第 X/Y 批）」，单批口径不变。"""

    async def _run(self, count: int) -> dict:
        items = [{"id": "p%d" % index, "question": {"stem": "旧题干"}}
                 for index in range(count)]
        notes: list[str] = []
        sizes: list[int] = []

        def fake_batch(files, base_url, token, *, model="", wait=900.0,
                       on_progress=None, **_kwargs):
            sizes.append(len(files))
            if on_progress is not None:
                for settled in range(1, len(files) + 1):
                    on_progress(settled, len(files))
            return [{"ok": True, "markdown": "# 题干", "detail": ""} for _ in files]

        with mock.patch.object(recognize_shared, "item_image_bytes",
                               side_effect=[b"png"] * count), \
                mock.patch.object(mineru_extract, "extract_batch",
                                  side_effect=fake_batch), \
                mock.patch("app.core.ingest.service.build_documents",
                           return_value=([{"stem": "新题干"}], [])), \
                mock.patch.object(recognize_shared, "merge_local",
                                  side_effect=lambda doc, question: {"merged": True}), \
                mock.patch.object(recognize_shared, "save_back", return_value=True):
            result = await mineru.run(
                "B-001", items, list(range(count)), _binding(), {},
                on_progress=lambda snapshot: notes.append(str(snapshot.get("note") or "")))
        return {"result": result, "notes": notes, "sizes": sizes}

    async def test_multi_batch_notices(self) -> None:
        outcome = await self._run(SIZE + 1)
        self.assertEqual(outcome["sizes"], [SIZE, 1])
        self.assertEqual(outcome["result"]["filled"], SIZE + 1)
        self.assertTrue(any("分 2 批发送" in note for note in outcome["notes"]))
        self.assertTrue(any("分批识别中（第 1/2 批）" in note for note in outcome["notes"]))
        self.assertTrue(any("分批识别中（第 2/2 批）" in note for note in outcome["notes"]))
        self.assertTrue(any("已回 %d/%d 题" % (SIZE + 1, SIZE + 1) in note
                            for note in outcome["notes"]))

    async def test_single_batch_notice_unchanged(self) -> None:
        outcome = await self._run(SIZE)
        self.assertEqual(outcome["sizes"], [SIZE])
        self.assertTrue(any("整批发送" in note for note in outcome["notes"]))
        self.assertFalse(any("分批识别中" in note for note in outcome["notes"]))


if __name__ == "__main__":
    unittest.main()
