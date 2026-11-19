# -*- coding: utf-8 -*-
"""国内镜像测速选路（2.20.0 卡§7）：fake urlopen，绝不真出网。

覆盖：通的按延迟排前／不通垫后／全不通人话／pip 四家国内禁 GitHub／
测速异常只记不通不抛。
运行：``.venv/Scripts/python.exe -m unittest tests.test_mirrors``
"""

from __future__ import annotations

import time
import unittest
from unittest import mock

from app.core.ingest import mirrors


class _FakeResponse:
    status = 200

    def read(self, _size: int = -1) -> bytes:
        return b"x"

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc) -> None:
        return None


class RaceTest(unittest.TestCase):
    def test_reachable_sorted_by_latency_unreachable_last(self) -> None:
        def urlopen(request, timeout):
            url = request.full_url
            if "slow" in url:
                time.sleep(0.05)
                return _FakeResponse()
            if "fast" in url:
                return _FakeResponse()
            raise OSError("connection refused")

        with mock.patch.object(mirrors.urllib.request, "urlopen",
                               side_effect=urlopen):
            rows = mirrors.race([("慢家", "https://slow.test/"),
                                 ("快家", "https://fast.test/"),
                                 ("死家", "https://dead.test/")])
        self.assertEqual([row["name"] for row in rows], ["快家", "慢家", "死家"])
        self.assertTrue(rows[0]["ok"])
        self.assertFalse(rows[2]["ok"])

    def test_empty_candidates_returns_empty(self) -> None:
        self.assertEqual(mirrors.race([]), [])

    def test_pick_note_names_the_fastest_reachable(self) -> None:
        rows = [{"name": "阿里云", "url": "u", "ok": True, "ms": 90},
                {"name": "清华", "url": "u", "ok": True, "ms": 150}]
        note = mirrors.pick_note(rows)
        self.assertIn("阿里云", note)
        self.assertIn("90ms", note)
        self.assertIn("2 家可达", note)

    def test_pick_note_all_dead_is_explicit(self) -> None:
        rows = [{"name": "甲", "url": "u", "ok": False, "ms": 2000},
                {"name": "乙", "url": "u", "ok": False, "ms": 2000}]
        note = mirrors.pick_note(rows)
        self.assertIn("全不通", note)
        self.assertIn("甲", note)

    def test_pip_candidates_are_four_domestic_no_github(self) -> None:
        candidates = mirrors.pip_candidates("mineru-llama-cpp")
        self.assertEqual(len(candidates), 4)
        joined = " ".join(url for _name, url in candidates)
        for host in ("aliyun", "tsinghua", "tencent", "ustc"):
            self.assertIn(host, joined)
        self.assertNotIn("github", joined.lower())
        self.assertNotIn("pypi.org", joined)
        for _name, url in candidates:
            self.assertTrue(url.endswith("/mineru-llama-cpp/"))

    def test_probe_http_error_is_not_ok_and_never_raises(self) -> None:
        with mock.patch.object(mirrors.urllib.request, "urlopen",
                               side_effect=ValueError("bad status")):
            rows = mirrors.race([("坏家", "https://bad.test/")])
        self.assertFalse(rows[0]["ok"])


if __name__ == "__main__":
    unittest.main()