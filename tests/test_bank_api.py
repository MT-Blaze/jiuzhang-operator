"""core-bank 题库 Host API：筛选、分页、注入、并发、题篮鉴权与配图边界。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_api``
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "bank-contract-token"
PLUGIN_ID = "org.jiuzhang.core-bank"
GRADES = ("高一", "高二", "高三")
LEVELS = ("basic", "medium", "hard")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _document(index: int, grade: str, difficulty: str) -> dict:
    kind = "single_choice" if index % 3 else "fill_blank"
    document = {
        "schema_version": "1.0",
        "id": f"q_test_{index:06d}",
        "type": kind,
        "stem": f"第 {index} 题：已知 $x^2 + {index} = 0$，求 $x$ 的值（$x>0$）。",
        "difficulty": difficulty,
        "tags": ["压测题", grade],
        "taxonomy": {"textbook": "人教A版", "chapter": "集合与常用逻辑用语"},
        "source": {"paper_title": "契约测试卷", "question_no": str(index)},
        "extensions": {"org.jiuzhang.legacy": {"grade": grade}},
        "meta": {
            "created_at": "2026-10-22T20:00:00+08:00",
            "updated_at": "2026-10-22T20:00:00+08:00",
            "revision": 1,
            "status": "published",
        },
    }
    if kind == "single_choice":
        document["options"] = [
            {"key": "A", "content": "$1$"},
            {"key": "B", "content": "$2$"},
            {"key": "C", "content": "$3$"},
            {"key": "D", "content": "$4$"},
        ]
        document["answer"] = {"kind": "choice", "choice_keys": ["A"], "final": "A"}
    else:
        document["answer"] = {"kind": "text", "content": "$x=1$", "final": "1"}
    document["solution"] = "由 $x^2+1=0$ 得 $x=\\pm i$，取正根。"
    return document


class BankApiContractTest(unittest.TestCase):
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
        cls.seed_path = seed_dir / "bank.db"

        sys.path.insert(0, str(ROOT))
        from app.core import bank  # noqa: PLC0415

        documents = []
        for index in range(1, 121):
            grade = GRADES[(index - 1) % 3]
            difficulty = LEVELS[(index - 1) // 40 % 3]
            documents.append(_document(index, grade, difficulty))
        bank.import_documents(
            PLUGIN_ID,
            documents,
            reset=True,
            db_path=cls.seed_path,
            source_info={"count": len(documents)},
        )

        # 配图路由用的真实文件
        uploads = cls.data_dir / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        (uploads / "probe.png").write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        cls.process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", str(cls.port), "--log-level", "warning",
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
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

    # ---------- HTTP 辅助 ----------
    def _request(self, path: str, method: str = "GET", body: dict | None = None,
                 token: bool = False) -> tuple[int, dict]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", TOKEN)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as error:
            try:
                payload = error.read().decode("utf-8")
            finally:
                error.close()
            try:
                parsed = json.loads(payload or "{}")
            except json.JSONDecodeError:
                parsed = {"raw": payload}
            return error.code, parsed

    def _query(self, **params) -> str:
        return urllib.parse.urlencode(params, encoding="utf-8")

    # ---------- 统计与筛选 ----------
    def test_stats_counts(self) -> None:
        status, data = self._request(f"/api/bank/plugins/{PLUGIN_ID}/stats")
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 120)
        grades = {item["name"]: item["count"] for item in data["grades"]}
        self.assertEqual(grades, {"高一": 40, "高二": 40, "高三": 40})
        self.assertEqual(data["meta"]["count"], 120)

    def test_grade_filter_matches_exactly(self) -> None:
        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(grade="高一", page_size=100)
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 40)
        self.assertTrue(all(item["grade"] == "高一" for item in data["items"]))

    def test_filters_combine_and_paginate(self) -> None:
        url = f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(
            grade="高二", difficulty="medium", page=2, page_size=5
        )
        status, data = self._request(url)
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 14)   # 高二 & medium：41..80 中 ≡2 (mod 3) 的 14 题
        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["total_pages"], 3)
        self.assertTrue(all(item["grade"] == "高二" for item in data["items"]))
        self.assertTrue(all(item["difficulty"] == "medium" for item in data["items"]))

    def test_chinese_search(self) -> None:
        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(q="第 7 题", page_size=50)
        )
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["total"], 1)
        self.assertTrue(any("第 7 题" in item["stem"] for item in data["items"]))

    def test_sql_injection_is_a_literal_search(self) -> None:
        for payload in ("' OR 1=1 --", "%' OR '1'='1", "'; DROP TABLE bank_questions; --", "%", "_"):
            status, data = self._request(
                f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(q=payload)
            )
            self.assertEqual(status, 200, payload)
            self.assertEqual(data["total"], 0, payload)
        status, data = self._request(f"/api/bank/plugins/{PLUGIN_ID}/stats")
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 120)   # 表还在

    def test_illegal_plugin_id(self) -> None:
        status, data = self._request("/api/bank/plugins/../../etc/questions")
        self.assertIn(status, (400, 404))

    def test_get_question_and_404(self) -> None:
        status, data = self._request(f"/api/bank/plugins/{PLUGIN_ID}/questions/q_test_000001")
        self.assertEqual(status, 200)
        self.assertEqual(data["id"], "q_test_000001")
        status, _ = self._request(f"/api/bank/plugins/{PLUGIN_ID}/questions/q_missing_0001")
        self.assertEqual(status, 404)

    def test_random_respects_filter(self) -> None:
        for _ in range(10):
            status, data = self._request(
                f"/api/bank/plugins/{PLUGIN_ID}/random?" + self._query(grade="高三", difficulty="hard")
            )
            self.assertEqual(status, 200)
            self.assertEqual(data["grade"], "高三")
            self.assertEqual(data["difficulty"], "hard")

    def test_concurrent_reads_no_deadlock(self) -> None:
        grades = ["高一", "高二", "高三", ""]

        def hit(index: int) -> int:
            status, data = self._request(
                f"/api/bank/plugins/{PLUGIN_ID}/questions?"
                + self._query(grade=grades[index % 4], page=(index % 3) + 1, page_size=12)
            )
            if status != 200:
                raise AssertionError(f"HTTP {status}: {data}")
            return data["total"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(hit, range(96)))
        self.assertEqual(len(results), 96)
        self.assertTrue(all(isinstance(value, int) for value in results))

    # ---------- 题篮 ----------
    def test_basket_requires_token(self) -> None:
        status, _ = self._request(
            "/api/basket", "POST", {"plugin_id": PLUGIN_ID, "ids": ["q_test_000001"]}
        )
        self.assertEqual(status, 401)
        status, _ = self._request("/api/basket/q_test_000001", "DELETE")
        self.assertEqual(status, 401)
        status, _ = self._request("/api/basket", "DELETE")
        self.assertEqual(status, 401)

    def test_basket_lifecycle(self) -> None:
        self._request("/api/basket", "DELETE", token=True)
        status, data = self._request("/api/basket")
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 0)

        status, data = self._request(
            "/api/basket", "POST",
            {"plugin_id": PLUGIN_ID, "ids": ["q_test_000001", "q_test_000002"]},
            token=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 2)

        # 重复加不重复计数
        status, data = self._request(
            "/api/basket", "POST", {"plugin_id": PLUGIN_ID, "id": "q_test_000001"}, token=True
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 2)

        status, data = self._request("/api/basket?expand=true")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["items"]), 2)
        self.assertIn("stem", data["items"][0]["question"])

        status, data = self._request("/api/basket/q_test_000001", "DELETE", token=True)
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 1)

        status, data = self._request("/api/basket", "DELETE", token=True)
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 0)

    def test_basket_rejects_unknown_and_oversize(self) -> None:
        self._request("/api/basket", "DELETE", token=True)
        status, _ = self._request(
            "/api/basket", "POST", {"plugin_id": PLUGIN_ID, "ids": ["q_nope_000001"]}, token=True
        )
        self.assertEqual(status, 400)
        status, _ = self._request(
            "/api/basket", "POST",
            {"plugin_id": PLUGIN_ID, "ids": [f"q_test_{index:06d}" for index in range(1, 202)]},
            token=True,
        )
        self.assertEqual(status, 400)
        status, data = self._request("/api/basket")
        self.assertEqual(data["total"], 0)

    # ---------- 录题写入（v0.6.2） ----------
    def _editor_question(self, **overrides) -> dict:
        document = {
            "schema_version": "1.0",
            "type": "fill_blank",
            "stem": "录题契约题：已知 $x^2-5x+6=0$，则 $x=$ ＿＿＿＿。",
            "answer": {"kind": "expression", "content": "$x=2$ 或 $x=3$", "final": "2,3"},
            "solution": "因式分解得 $(x-2)(x-3)=0$。",
            "difficulty": "basic",
            "tags": ["一元二次方程", "因式分解"],
            "extensions": {"org.jiuzhang.editor": {"grade": "高一"}},
            "meta": {"status": "published", "author": "录题工作台"},
        }
        document.update(overrides)
        return document

    def test_z1_create_requires_token(self) -> None:
        status, _ = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST", {"question": self._editor_question()}
        )
        self.assertEqual(status, 401)

    def test_z2_create_roundtrip(self) -> None:
        status, created = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST",
            {"question": self._editor_question(stem="录题契约题：往返校验唯一题干 $\\dfrac{1}{2}$。")},
            token=True,
        )
        self.assertEqual(status, 201, created)
        self.assertRegex(created["id"], r"^q_[A-Za-z0-9_-]{8,64}$")
        self.assertEqual(created["meta"]["status"], "published")
        self.assertEqual(created["difficulty"], "basic")

        status, fetched = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions/{created['id']}"
        )
        self.assertEqual(status, 200)
        self.assertEqual(fetched["stem"], created["stem"])
        self.assertEqual(fetched["answer"]["content"], "$x=2$ 或 $x=3$")
        self.assertEqual(fetched["grade"], "高一")   # 年级由录题扩展字段落库

        status, listed = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions?"
            + self._query(q="往返校验唯一题干", page_size=10)
        )
        self.assertEqual(status, 200)
        self.assertTrue(any(item["id"] == created["id"] for item in listed["items"]))

    def test_z3_create_ignores_supplied_id_and_rejects_bad_schema(self) -> None:
        status, created = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST",
            {"question": self._editor_question(id="q_hijack_00000001")},
            token=True,
        )
        self.assertEqual(status, 201, created)
        self.assertNotEqual(created["id"], "q_hijack_00000001")

        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST",
            {"question": self._editor_question(stem="")}, token=True,
        )
        self.assertEqual(status, 422)
        self.assertIn("errors", data["detail"])

        status, _ = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST",
            {"question": self._editor_question(difficulty="impossible")}, token=True,
        )
        self.assertEqual(status, 422)

    def test_z4_create_multiple_choice_options(self) -> None:
        question = self._editor_question(
            type="multiple_choice",
            stem="录题契约题：下列各数中，哪些是有理数？",
            options=[
                {"key": "A", "content": "$\\dfrac{1}{2}$"},
                {"key": "B", "content": "$\\sqrt{2}$"},
                {"key": "C", "content": "$0.\\overline{3}$"},
                {"key": "D", "content": "$\\pi$"},
            ],
            answer={"kind": "choice", "choice_keys": ["A", "C"], "final": "AC"},
        )
        status, created = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST",
            {"question": question}, token=True,
        )
        self.assertEqual(status, 201, created)
        self.assertEqual([item["key"] for item in created["options"]], ["A", "B", "C", "D"])
        self.assertEqual(created["answer"]["choice_keys"], ["A", "C"])

    # ---------- 配图边界 ----------
    def test_upload_serving_and_traversal(self) -> None:
        with urllib.request.urlopen(self.base + "/static/uploads/probe.png", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")

        for path in (
            "/static/uploads/%2e%2e%2Fjiuzhang.db",
            "/static/uploads/..%2F..%2Fjiuzhang.db",
            "/static/uploads/%2e%2e/%2e%2e/data/jiuzhang.db",
            "/static/uploads/probe.exe",
        ):
            try:
                with urllib.request.urlopen(self.base + path, timeout=5) as response:
                    self.fail(f"{path} 不应可读（HTTP {response.status}）")
            except urllib.error.HTTPError as error:
                self.assertIn(error.code, (403, 404), path)


class MigratedBankIntegrityTest(unittest.TestCase):
    """真实迁移产物：456 道真题必须结构完整、LaTeX 配平、图片路径受控。"""

    seed = ROOT / "plugins" / PLUGIN_ID / "bank" / "bank.db"

    def test_seed_exists(self) -> None:
        self.assertTrue(self.seed.is_file(), "缺少迁移种子库，请先运行 tools/migrate_legacy_bank.py")

    def test_all_rows_are_schema_sound(self) -> None:
        sys.path.insert(0, str(ROOT))
        from app.core.questions import validate_question  # noqa: PLC0415

        con = sqlite3.connect(f"file:{self.seed.as_posix()}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute("SELECT * FROM bank_questions").fetchall()
        finally:
            con.close()
        self.assertEqual(len(rows), 456)
        ids = set()
        for row in rows:
            self.assertRegex(row["id"], r"^q_[A-Za-z0-9_-]{8,64}$")
            self.assertNotIn(row["id"], ids)
            ids.add(row["id"])
            stem = row["stem"]
            self.assertNotIn("\\begin{choices}", stem)
            self.assertNotIn("\\includegraphics", stem)
            self.assertNotIn("\\paren", stem)
            self.assertEqual(stem.count("$") % 2, 0, row["id"])
            options = json.loads(row["options_json"]) if row["options_json"] else []
            answer = json.loads(row["answer_json"]) if row["answer_json"] else None
            images = json.loads(row["images_json"]) if row["images_json"] else []
            document = {
                "schema_version": "1.0",
                "id": row["id"],
                "type": row["type"],
                "stem": stem,
                "difficulty": row["difficulty"],
                "meta": json.loads(row["meta_json"]),
                "extensions": json.loads(row["extensions_json"]) if row["extensions_json"] else {},
            }
            if options:
                document["options"] = options
                keys = [option["key"] for option in options]
                self.assertEqual(keys, list("ABCDEFGH")[: len(keys)], row["id"])
            if answer:
                document["answer"] = answer
            if row["solution"]:
                document["solution"] = row["solution"]
                self.assertEqual(row["solution"].count("$") % 2, 0, row["id"])
            if images:
                document["images"] = images
                for image in images:
                    self.assertRegex(image["id"], r"^img_[A-Za-z0-9_-]{1,63}$")
                    self.assertTrue(image["uri"].startswith("/static/uploads/"), image)
            validate_question(document)

    def test_filters_return_expected_populations(self) -> None:
        con = sqlite3.connect(f"file:{self.seed.as_posix()}?mode=ro", uri=True)
        try:
            g1 = con.execute("SELECT COUNT(*) FROM bank_questions WHERE grade='高一'").fetchone()[0]
            hard = con.execute("SELECT COUNT(*) FROM bank_questions WHERE difficulty='hard'").fetchone()[0]
            chapter = con.execute(
                "SELECT COUNT(*) FROM bank_questions WHERE chapter='1. 集合与常用逻辑用语'"
            ).fetchone()[0]
        finally:
            con.close()
        self.assertEqual(g1, 420)
        self.assertEqual(hard, 140)
        self.assertGreater(chapter, 100)


class StageRelayContractTest(unittest.TestCase):
    """插件数据通道必须白名单化，且插件自报的 plugin_id 不被采信。"""

    def test_stage_relay_whitelist_and_plugin_scoping(self) -> None:
        source = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        for method in ("bank.list", "bank.stats", "bank.get", "bank.random", "bank.create",
                       "basket.list", "basket.add", "basket.remove", "basket.clear"):
            self.assertIn(f'"{method}"', source)
        self.assertNotIn('payload.plugin_id', source)
        self.assertIn("/api/bank/plugins/\" + encodeURIComponent(pluginId)", source)
        self.assertIn('"X-JZO-Token": token', source)
        self.assertIn("RELAY_MAX_PER_WINDOW", source)

    def test_bank_create_is_scoped_and_permission_checked(self) -> None:
        source = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        self.assertIn('CANONICAL_BANK_ID = "org.jiuzhang.core-bank"', source)
        self.assertIn('permissions.indexOf("questions:write")', source)
        self.assertIn('emit("question.updated"', source)


if __name__ == "__main__":
    unittest.main()
