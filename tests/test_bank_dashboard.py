"""数据看板只读 API（军令 #11 阶段一）：/api/bank/dashboard/stats 与 /heatmap。

守住的口径：
- 四个数的定义（总题数 / 今日入库 / 待审核 / 已落库 = 总数 − 待审核）；
- 热力图返回裸数组、含今天、逐日补零、长度恰为 days；
- 两条接口都是只读开放（本机口径，不占写令牌），且不回任何令牌信息。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_dashboard``
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "dashboard-contract-token"
PLUGIN_ID = "org.jiuzhang.core-bank"
LOCAL_TZ = timezone(timedelta(hours=8))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _iso(day_offset: int, hour: int = 12) -> str:
    day = datetime.now(LOCAL_TZ).date() - timedelta(days=day_offset)
    return f"{day.isoformat()}T{hour:02d}:00:00+08:00"


def _document(index: int, created_at: str, flagged: bool = False) -> dict:
    document = {
        "schema_version": "2.0",
        "id": f"q_dash_{index:06d}",
        "type": "fill_blank",
        "stem": f"看板测试第 {index} 题：求 $x$。",
        "difficulty": "L1",
        "answer": {"kind": "text", "content": "$x=1$", "final": "1"},
        "extensions": {},
        "meta": {"created_at": created_at, "updated_at": created_at,
                 "revision": 1, "status": "published"},
    }
    if flagged:
        document["extensions"]["org.jiuzhang.core-bank.migration"] = {
            "flags": ["answer_absent"], "run_at": created_at,
        }
    return document


class DashboardApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tmp_root = Path(cls.tmp.name)
        cls.data_dir = cls.tmp_root / "data"
        cls.plugins_dir = cls.tmp_root / "plugins"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        cls.plugins_dir.mkdir(parents=True, exist_ok=True)

        seed_dir = cls.plugins_dir / PLUGIN_ID / "bank"
        seed_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql",
                        seed_dir / "schema.sql")
        cls.seed_path = seed_dir / "bank.db"

        sys.path.insert(0, str(ROOT))
        from app.core import bank  # noqa: PLC0415

        # 3 题今天、2 题昨天、5 题更早；其中 2 题带待审标记（1 今天 + 1 早期）
        documents = [
            _document(1, _iso(0, 9)),
            _document(2, _iso(0, 10), flagged=True),
            _document(3, _iso(0, 11)),
            _document(4, _iso(1, 8)),
            _document(5, _iso(1, 9)),
            _document(6, _iso(10, 8), flagged=True),
            _document(7, _iso(10, 9)),
            _document(8, _iso(400, 8)),   # 365 天窗口之外，热力图不得计入
            _document(9, _iso(200, 8)),
            _document(10, _iso(100, 8)),
        ]
        bank.import_documents(
            PLUGIN_ID, documents, reset=True, db_path=cls.seed_path,
            source_info={"count": len(documents)},
        )

        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(cls.port), "--log-level", "warning"],
            cwd=str(ROOT), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        deadline = time.time() + 20
        while time.time() < deadline:
            if cls.process.poll() is not None:
                output = cls.process.stdout.read() if cls.process.stdout else ""
                raise RuntimeError("服务提前退出：\n" + output)
            try:
                with urllib.request.urlopen(cls.base + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("服务未在 20 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        cls.tmp.cleanup()

    def _get(self, path: str):
        request = urllib.request.Request(self.base + path, method="GET")
        request.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            payload = error.read().decode("utf-8")
            error.close()
            try:
                return error.code, json.loads(payload or "{}")
            except json.JSONDecodeError:
                return error.code, {"raw": payload}

    # ---------- /api/bank/dashboard/stats ----------
    def test_stats_four_numbers(self) -> None:
        status, data = self._get("/api/bank/dashboard/stats")
        self.assertEqual(status, 200)
        self.assertEqual(data["plugin_id"], PLUGIN_ID)
        self.assertEqual(data["total_questions"], 10)
        self.assertEqual(data["today_added"], 3)
        self.assertEqual(data["pending_review"], 2)
        self.assertEqual(data["stored_total"], 8)   # 已落库 = 总数 − 待审核
        self.assertEqual(data["date"], datetime.now(LOCAL_TZ).date().isoformat())

    def test_stats_recent_five_sorted_desc(self) -> None:
        _, data = self._get("/api/bank/dashboard/stats")
        recent = data["recent"]
        self.assertEqual(len(recent), 5)
        stamps = [item["created_at"] for item in recent]
        self.assertEqual(stamps, sorted(stamps, reverse=True))
        for item in recent:
            self.assertTrue(item["id"].startswith("q_"))
            self.assertIn(item["type"], ("single_choice", "multiple_choice",
                                         "fill_blank", "solution"))
            self.assertLessEqual(len(item["stem"]), 80)
        self.assertEqual(recent[0]["id"], "q_dash_000003")   # 今天 11 点那条最新

    def test_stats_is_readonly_no_token_needed(self) -> None:
        status, _ = self._get("/api/bank/dashboard/stats")
        self.assertEqual(status, 200)

    # ---------- /api/bank/dashboard/heatmap ----------
    def test_heatmap_is_bare_array_365_days_zero_filled(self) -> None:
        status, data = self._get("/api/bank/dashboard/heatmap")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 365)
        today = datetime.now(LOCAL_TZ).date()
        self.assertEqual(data[-1]["date"], today.isoformat())
        self.assertEqual(data[-1]["count"], 3)                       # 今天 3 题
        self.assertEqual(data[-2]["count"], 2)                       # 昨天 2 题
        self.assertEqual(data[-11]["count"], 2)                      # 10 天前 2 题
        for cell in data:
            self.assertEqual(set(cell), {"date", "count"})
            self.assertIsInstance(cell["count"], int)
        # 400 天前那题在窗口外：全窗口合计 = 10 − 1 = 9
        self.assertEqual(sum(cell["count"] for cell in data), 9)

    def test_heatmap_dates_are_consecutive(self) -> None:
        _, data = self._get("/api/bank/dashboard/heatmap")
        days = [datetime.strptime(cell["date"], "%Y-%m-%d").date() for cell in data]
        for previous, current in zip(days, days[1:]):
            self.assertEqual((current - previous).days, 1)

    def test_heatmap_days_param(self) -> None:
        status, data = self._get("/api/bank/dashboard/heatmap?days=7")
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 7)
        self.assertEqual(sum(cell["count"] for cell in data), 5)   # 今天3 + 昨天2
        status, _ = self._get("/api/bank/dashboard/heatmap?days=0")
        self.assertEqual(status, 422)
        status, _ = self._get("/api/bank/dashboard/heatmap?days=99999")
        self.assertEqual(status, 422)


if __name__ == "__main__":
    unittest.main()
