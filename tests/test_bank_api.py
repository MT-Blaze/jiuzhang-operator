"""core-bank 题库 Host API：七表筛选、分页、注入、并发、题篮鉴权与配图边界。

存储层是 v0.6.3 冻结的 7 张关系表，出参是 schemas/question.json 的标准文档；
本测同时守住两条口径：契约 2.0 的难度 L1–L4，以及 1.0 旧值的归一（basic→L1…）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_api``
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import shutil
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
LEVELS = ("L1", "L2", "L3")


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
    # 每 17 题造一道带灌库审核标记的题，供「待审任务」页签取数
    if index % 17 == 3:
        flag = "answer_absent" if (index // 17) % 2 == 0 else "structure_conflict"
        document["extensions"]["org.jiuzhang.core-bank.migration"] = {
            "flags": [flag], "run_at": "2026-10-23T10:00:00+08:00"
        }
    return document


def _seed_outline(db_path: Path) -> dict:
    """往测试库里插一条 册→章→节→考向 的物化路径，并挂一题 + 两条教研笔记。"""
    now = "2026-10-23T20:00:00+08:00"
    book, chapter, section, kx = "tp_bo00000001", "tp_ch00000002", "tp_se00000003", "tp_kx00000004"
    path_of = {
        book: book,
        chapter: f"{book}/{chapter}",
        section: f"{book}/{chapter}/{section}",
        kx: f"{book}/{chapter}/{section}/{kx}",
    }
    names = {book: "人教A版·必修第一册", chapter: "1. 集合与常用逻辑用语",
             section: "1.1 集合的概念", kx: "集合中元素的个数"}
    con = sqlite3.connect(db_path)
    try:
        for order, node in enumerate([book, chapter, section, kx]):
            parent = None if node == book else [book, chapter, section][order - 1]
            con.execute(
                "INSERT INTO topics (id, parent_id, name, path, sort_order, status,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (node, parent, names[node], path_of[node], order, "active", now, now),
            )
        con.execute(
            "INSERT INTO question_topics (question_id, topic_id, is_primary, sort_order, created_at)"
            " VALUES (?, ?, 1, 0, ?)", ("q_test_000001", kx, now)
        )
        for order, note_type in enumerate(("method", "pitfall")):
            con.execute(
                "INSERT INTO topic_notes (topic_id, note_type, content, sort_order,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (kx, note_type, f"第 {order + 1} 条教研笔记", order, now, now),
            )
        con.commit()
    finally:
        con.close()
    return {"book": book, "chapter": chapter, "section": section, "kx": kx}


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
        # 建库只认插件包里的冻结 schema.sql，测试沙箱必须带上同一份
        shutil.copyfile(ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql",
                        seed_dir / "schema.sql")
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
        cls.outline = _seed_outline(cls.seed_path)

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

    def test_topics_channel_lazy_expands(self) -> None:
        """大纲树通道：不给 parent 出册层，给 parent 出一层子节点，带子树题量。"""
        status, data = self._request(f"/api/bank/plugins/{PLUGIN_ID}/topics")
        self.assertEqual(status, 200)
        self.assertEqual([item["name"] for item in data["items"]], ["人教A版·必修第一册"])
        book = data["items"][0]
        self.assertEqual(book["layer"], "textbook")
        self.assertTrue(book["has_children"])
        self.assertEqual(book["question_count"], 1)
        self.assertEqual(book["note_count"], 0)

        status, kids = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/topics?" + self._query(parent_id=book["id"])
        )
        self.assertEqual(status, 200)
        self.assertEqual([item["name"] for item in kids["items"]], ["1. 集合与常用逻辑用语"])
        self.assertEqual(kids["items"][0]["parent_id"], book["id"])

        status, _data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/topics?" + self._query(parent_id="tp_zz00000000")
        )
        self.assertEqual(status, 400)

    def test_topic_notes_channel(self) -> None:
        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/topics/{self.outline['kx']}/notes"
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["topic"]["name"], "集合中元素的个数")
        self.assertEqual([item["note_type"] for item in data["notes"]], ["method", "pitfall"])
        status, _data = self._request(f"/api/bank/plugins/{PLUGIN_ID}/topics/tp_zz00000000/notes")
        self.assertEqual(status, 400)

    def test_list_and_random_by_topic_subtree(self) -> None:
        """点册/考向都要能取到挂在末级节点上的题，且出参 taxonomy 来自路径树。"""
        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(topic=self.outline["book"])
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 1)
        item = data["items"][0]
        self.assertEqual(item["id"], "q_test_000001")
        self.assertEqual(item["taxonomy"]["topic_ids"], [self.outline["kx"]])
        self.assertEqual(item["taxonomy"]["textbook"], "人教A版·必修第一册")
        self.assertEqual(item["taxonomy"]["section"], "1.1 集合的概念")

        status, one = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/random?" + self._query(topic=self.outline["kx"])
        )
        self.assertEqual(status, 200)
        self.assertEqual(one["id"], "q_test_000001")

    # 写路径会往同一份夹具里加题，因此一律取 z_ 前缀排在只读断言之后（本文件既有约定）
    def test_z5_extensions_round_trip_keeps_reverse_domain_object(self) -> None:
        """写入端收对象态、库里存数组态、读回来必须还是对象态（AGENTS §3）。"""
        question = self._editor_question(
            stem="扩展往返题：求 $\\varnothing$ 的子集个数。",
            extensions={
                "org.jiuzhang.editor": {"grade": "高一"},
                "com.example.handwriting": {"stroke": 2},
            },
        )
        status, created = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST",
            {"question": question}, token=True,
        )
        self.assertEqual(status, 201, created)
        self.assertEqual(created["extensions"]["com.example.handwriting"], {"stroke": 2})
        self.assertEqual(created["extensions"]["org.jiuzhang.editor"], {"grade": "高一"})

        con = sqlite3.connect(self.data_dir / "banks" / f"{PLUGIN_ID}.db")
        try:
            raw = con.execute(
                "SELECT extensions FROM questions WHERE id = ?", (created["id"],)
            ).fetchone()[0]
        finally:
            con.close()
        stored = json.loads(raw)
        self.assertIsInstance(stored, list)
        self.assertTrue(all({"key", "label", "value"} == set(item) for item in stored))
        self.assertIn("录题插件私有数据", [item["label"] for item in stored])

    def test_z6_create_rejects_types_the_storage_table_cannot_hold(self) -> None:
        """存储层 CHECK 不收 proof/unknown：如实 422，不静默折叠成 solution。"""
        for question_type in ("proof", "unknown"):
            status, data = self._request(
                f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST",
                {"question": self._editor_question(
                    stem=f"存储层不收的题型 {question_type}：$x^2$ 的证明题", type=question_type)},
                token=True,
            )
            self.assertEqual(status, 422, (question_type, data))
            self.assertIn("core-bank 存储层只收", json.dumps(data, ensure_ascii=False))

    def test_z7_create_links_known_topic_and_rejects_unknown_one(self) -> None:
        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST",
            {"question": self._editor_question(
                stem="挂纲失败题：$\\mathbb{R}$ 上的恒等式",
                taxonomy={"topic_ids": ["tp_kxdeadc0de"]})},
            token=True,
        )
        self.assertEqual(status, 422, data)
        self.assertIn("大纲里没有节点", json.dumps(data, ensure_ascii=False))

        status, created = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions", "POST",
            {"question": self._editor_question(
                stem="挂纲成功题：$\\varnothing$ 与 $\\{\\varnothing\\}$ 的区别",
                taxonomy={"topic_ids": [self.outline["kx"]]})},
            token=True,
        )
        self.assertEqual(status, 201, created)
        self.assertEqual(created["taxonomy"]["topic_ids"], [self.outline["kx"]])

    def test_grade_filter_matches_exactly(self) -> None:
        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(grade="高一", page_size=100)
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 40)
        self.assertTrue(all(item["grade"] == "高一" for item in data["items"]))

    def test_filters_combine_and_paginate(self) -> None:
        url = f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(
            grade="高二", difficulty="L2", page=2, page_size=5
        )
        status, data = self._request(url)
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 14)   # 高二 & L2：41..80 中 ≡2 (mod 3) 的 14 题
        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["total_pages"], 3)
        self.assertTrue(all(item["grade"] == "高二" for item in data["items"]))
        self.assertTrue(all(item["difficulty"] == "L2" for item in data["items"]))

    def test_legacy_difficulty_alias_is_normalized(self) -> None:
        """1.0 的旧难度值仍能筛，但出参只给 L 码（契约 2.0 口径）。"""
        url = f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(
            difficulty="medium", page_size=20
        )
        status, data = self._request(url)
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 40)   # medium→L2：20..40 与 60..79 各半
        self.assertTrue(all(item["difficulty"] == "L2" for item in data["items"]))

    def test_chinese_search(self) -> None:
        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(q="第 7 题", page_size=50)
        )
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["total"], 1)
        self.assertTrue(any("第 7 题" in item["stem"] for item in data["items"]))

    def test_sql_injection_is_a_literal_search(self) -> None:
        for payload in ("' OR 1=1 --", "%' OR '1'='1", "'; DROP TABLE questions; --", "%", "_"):
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
            self.assertEqual(data["difficulty"], "L3")

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
        self.assertEqual(created["schema_version"], "2.0")
        self.assertEqual(created["difficulty"], "L1")   # 1.0 的 basic 由底座归一成 L1

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

    # ---------- 人工审核（P0#3） ----------
    def test_z8_review_queue_groups_and_filters(self) -> None:
        """不给 flag 就是整条待审队列；分组计数必须与逐题标记自洽。"""
        status, data = self._request(f"/api/bank/plugins/{PLUGIN_ID}/review?page_size=50")
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], data["summary"]["total"])
        self.assertGreaterEqual(data["total"], 1)
        for item in data["items"]:
            flags = (item["extensions"].get("org.jiuzhang.core-bank.migration") or {}).get("flags")
            self.assertTrue(flags, item["id"])
        counts = {item["name"]: item["count"] for item in data["summary"]["flags"]}
        self.assertEqual(sum(counts.values()), data["total"])   # 夹具里每题只带一个标记
        self.assertIn("answer_absent", counts)

        status, only = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/review?" + self._query(flag="answer_absent", page_size=50)
        )
        self.assertEqual(status, 200)
        self.assertEqual(only["total"], counts["answer_absent"])
        self.assertTrue(all(
            "answer_absent" in item["extensions"]["org.jiuzhang.core-bank.migration"]["flags"]
            for item in only["items"]
        ))

        status, bad = self._request(f"/api/bank/plugins/{PLUGIN_ID}/review?flag=nonsense")
        self.assertEqual(status, 400, bad)

    def test_z9_update_requires_token_and_clears_flags(self) -> None:
        target = "q_test_000037"   # 夹具里带 answer_absent 标记的单选题
        status, _ = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions/{target}", "PATCH",
            {"question": {"answer": {"kind": "choice", "choice_keys": ["C"], "final": "C"}}},
        )
        self.assertEqual(status, 401)

        status, before = self._request(f"/api/bank/plugins/{PLUGIN_ID}/questions/{target}")
        self.assertEqual(status, 200)
        self.assertIn("answer_absent",
                      before["extensions"]["org.jiuzhang.core-bank.migration"]["flags"])
        status, queue_before = self._request(f"/api/bank/plugins/{PLUGIN_ID}/review?page_size=1")
        total_before = queue_before["summary"]["total"]

        status, fixed = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions/{target}", "PATCH",
            {"question": {
                "answer": {"kind": "choice", "choice_keys": ["C"], "final": "C"},
                "clear_flags": ["answer_absent"],
            }},
            token=True,
        )
        self.assertEqual(status, 200, fixed)
        self.assertEqual(fixed["answer"]["choice_keys"], ["C"])
        self.assertNotIn("org.jiuzhang.core-bank.migration", fixed["extensions"])
        self.assertGreaterEqual(fixed["meta"]["updated_at"], before["meta"]["updated_at"])

        status, listed = self._request(f"/api/bank/plugins/{PLUGIN_ID}/questions/{target}")
        self.assertEqual(status, 200)
        self.assertNotIn("org.jiuzhang.core-bank.migration", listed["extensions"])
        self.assertEqual(listed["answer"]["final"], "C")
        status, queue_after = self._request(f"/api/bank/plugins/{PLUGIN_ID}/review?page_size=1")
        self.assertEqual(queue_after["summary"]["total"], total_before - 1)   # 修一条少一条

    def test_z10_update_rejects_unknown_flag_and_keeps_row_intact(self) -> None:
        target = "q_test_000020"
        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions/{target}", "PATCH",
            {"question": {"clear_flags": ["definitely_not_a_flag"]}}, token=True,
        )
        self.assertEqual(status, 422, data)
        self.assertIn("未知审核标记", json.dumps(data, ensure_ascii=False))
        status, listed = self._request(f"/api/bank/plugins/{PLUGIN_ID}/questions/{target}")
        self.assertIn("structure_conflict",
                      listed["extensions"]["org.jiuzhang.core-bank.migration"]["flags"])

        # 清一个该题没有的合法标记 = 幂等空操作，不报错也不动数据
        status, idempotent = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions/{target}", "PATCH",
            {"question": {"clear_flags": ["answer_absent"]}}, token=True,
        )
        self.assertEqual(status, 200, idempotent)
        self.assertIn("structure_conflict",
                      idempotent["extensions"]["org.jiuzhang.core-bank.migration"]["flags"])

        status, missing = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions/q_does_not_exist", "PATCH",
            {"question": {"stem": "越权改题"}}, token=True,
        )
        self.assertEqual(status, 404, missing)

    def test_z11_update_can_change_type_for_structure_conflict(self) -> None:
        target = "q_test_000020"   # 选项拆不出来的那道：改判成解答题
        status, fixed = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions/{target}", "PATCH",
            {"question": {"type": "solution", "clear_flags": ["structure_conflict"]}},
            token=True,
        )
        self.assertEqual(status, 200, fixed)
        self.assertEqual(fixed["type"], "solution")
        self.assertNotIn("options", fixed)   # 存储层强制「无选项题型 options 为空数组」
        self.assertNotIn("org.jiuzhang.core-bank.migration", fixed["extensions"])
        status, listed = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions?" + self._query(q="第 20 题", page_size=20)
        )
        self.assertTrue(any(item["id"] == target and item["type"] == "solution"
                            for item in listed["items"]))

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
    """真实迁移产物：456 道真题在新表上必须装配得回来、过得了 Schema、不造假。"""

    migrated = ROOT / "plugins" / PLUGIN_ID / "bank" / "v063_migrated.db"

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name) / "data"
        (data_dir / "banks").mkdir(parents=True)
        shutil.copyfile(cls.migrated, data_dir / "banks" / f"{PLUGIN_ID}.db")
        cls.previous = os.environ.get("JZO_DATA_DIR")
        os.environ["JZO_DATA_DIR"] = str(data_dir)
        sys.path.insert(0, str(ROOT))
        from app.core import bank  # noqa: PLC0415

        cls.bank = bank

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.previous is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = cls.previous
        cls.tmp.cleanup()

    def _documents(self) -> list[dict]:
        collected: list[dict] = []
        page = 1
        while True:
            items, _total = self.bank.list_questions(PLUGIN_ID, page=page, page_size=100)
            if not items:
                return collected
            collected.extend(items)
            page += 1

    def test_seven_tables_hold_the_migrated_population(self) -> None:
        con = sqlite3.connect(f"file:{self.migrated.as_posix()}?mode=ro", uri=True)
        try:
            tables = {
                row[0] for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            self.assertNotIn("bank_questions", tables)
            self.assertEqual(tables, {
                "schools", "topics", "questions", "topic_notes", "sources",
                "question_topics", "question_sources", "bank_meta",
            })
            counts = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
            self.assertEqual(counts["questions"], 456)
            self.assertEqual(counts["question_topics"], 456)
            self.assertEqual(counts["question_sources"], 456)
            self.assertEqual(counts["topic_notes"], 150)
            self.assertEqual(list(con.execute("PRAGMA foreign_key_check")), [])
        finally:
            con.close()

    def test_every_document_survives_the_round_trip_and_passes_schema(self) -> None:
        from app.core.questions import validate_question  # noqa: PLC0415

        documents = self._documents()
        self.assertEqual(len(documents), 456)
        self.assertEqual(len({item["id"] for item in documents}), 456)
        for document in documents:
            validate_question(document)
            self.assertEqual(document["schema_version"], "2.0")
            self.assertIn(document["difficulty"], ("L1", "L2", "L3", "L4"))
            self.assertEqual(document["stem"].count("$") % 2, 0, document["id"])
            self.assertNotIn("\\includegraphics", document["stem"])
            if document["type"] in ("single_choice", "multiple_choice"):
                keys = [option["key"] for option in document.get("options") or []]
                self.assertEqual(keys, list("ABCDEFGH")[: len(keys)], document["id"])
            for image in document.get("images") or []:
                self.assertTrue(image["uri"].startswith("/static/uploads/"), image)

    def test_answers_without_evidence_are_omitted_not_fabricated(self) -> None:
        """31 道选择题在旧库只有硬编码 A：新库置 NULL，出参必须整个省略 answer。"""
        con = sqlite3.connect(f"file:{self.migrated.as_posix()}?mode=ro", uri=True)
        try:
            empty_choice = con.execute(
                "SELECT COUNT(*) FROM questions WHERE type IN ('single_choice','multiple_choice')"
                " AND answer IS NULL"
            ).fetchone()[0]
            empty_any = con.execute("SELECT COUNT(*) FROM questions WHERE answer IS NULL").fetchone()[0]
        finally:
            con.close()
        self.assertEqual(empty_choice, 31)
        self.assertEqual(empty_any, 53)
        missing = [item for item in self._documents() if "answer" not in item]
        self.assertEqual(len(missing), 53)

    def test_grade_and_outline_populations_match_the_legacy_wide_table(self) -> None:
        _items, g1 = self.bank.list_questions(PLUGIN_ID, grade="高一", page_size=1)
        self.assertEqual(g1, 420)
        _items, l3 = self.bank.list_questions(PLUGIN_ID, difficulty="L3", page_size=1)
        self.assertEqual(l3, 134)
        _items, chapter = self.bank.list_questions(
            PLUGIN_ID, chapter="1. 集合与常用逻辑用语", page_size=1
        )
        self.assertGreater(chapter, 100)
        stats = self.bank.stats(PLUGIN_ID)
        self.assertEqual(stats["total"], 456)
        self.assertEqual({g["name"]: g["count"] for g in stats["grades"]},
                         {"高一": 420, "高三": 36})
        self.assertEqual({d["name"]: d["count"] for d in stats["difficulties"]},
                         {"L1": 42, "L2": 140, "L3": 134, "L4": 140})

    def test_outline_tree_expends_lazily_and_carries_question_counts(self) -> None:
        books = self.bank.topics(PLUGIN_ID)
        self.assertEqual(len(books), 5)
        self.assertTrue(all(book["layer"] == "textbook" for book in books))
        book_one = next(book for book in books if book["name"] == "必修一")
        self.assertEqual(book_one["question_count"], 428)
        _items, subtree_total = self.bank.list_questions(PLUGIN_ID, topic=book_one["id"], page_size=1)
        self.assertEqual(subtree_total, 428)
        chapters = self.bank.topics(PLUGIN_ID, parent_id=book_one["id"])
        self.assertTrue(chapters)
        sections = self.bank.topics(PLUGIN_ID, parent_id=chapters[0]["id"])
        self.assertTrue(all(section["parent_id"] == chapters[0]["id"] for section in sections))

    def test_topic_notes_channel_returns_teaching_notes(self) -> None:
        con = sqlite3.connect(f"file:{self.migrated.as_posix()}?mode=ro", uri=True)
        try:
            topic_id = con.execute(
                "SELECT topic_id FROM topic_notes GROUP BY topic_id ORDER BY COUNT(*) DESC LIMIT 1"
            ).fetchone()[0]
        finally:
            con.close()
        payload = self.bank.topic_notes(PLUGIN_ID, topic_id)
        self.assertTrue(payload["notes"])
        self.assertIn(payload["notes"][0]["note_type"], ("method", "pitfall", "knowledge", "insight"))
        with self.assertRaises(self.bank.BankError):
            self.bank.topic_notes(PLUGIN_ID, "tp_zzzzzzzzzz")


class LegacyWideTableSeedTest(unittest.TestCase):
    """v0.6.2 的 bank_questions 宽表库必须被拒读并给出可操作提示，不许静默读空。

    注意注入点：``JZO_DATA_DIR`` 每次调用都重读，``settings.plugins_dir`` 却是导入期
    一次性求值的类属性——所以这里直接铺工作区库文件，不靠环境变量换插件目录。
    """

    def test_wide_table_database_is_rejected_with_actionable_message(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data_dir = Path(tmp.name) / "data"
        (data_dir / "banks").mkdir(parents=True)

        stale = data_dir / "banks" / f"{PLUGIN_ID}.db"
        con = sqlite3.connect(stale)
        try:
            con.execute("CREATE TABLE bank_questions (id TEXT PRIMARY KEY, stem TEXT NOT NULL)")
            con.execute("INSERT INTO bank_questions (id, stem) VALUES ('q_legacy_000001', '旧宽表题')")
            con.commit()
        finally:
            con.close()

        previous = os.environ.get("JZO_DATA_DIR")
        os.environ["JZO_DATA_DIR"] = str(data_dir)

        def restore() -> None:
            if previous is None:
                os.environ.pop("JZO_DATA_DIR", None)
            else:
                os.environ["JZO_DATA_DIR"] = previous

        self.addCleanup(restore)

        from app.core import bank  # noqa: PLC0415

        with self.assertRaises(bank.BankError) as ctx:
            bank.stats(PLUGIN_ID)
        message = str(ctx.exception)
        self.assertIn("bank_questions", message)
        self.assertIn("migrate_bank_v063", message)


class StageRelayContractTest(unittest.TestCase):
    """插件数据通道必须白名单化，且插件自报的 plugin_id 不被采信。"""

    def test_stage_relay_whitelist_and_plugin_scoping(self) -> None:
        source = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        for method in ("bank.list", "bank.stats", "bank.get", "bank.random", "bank.create",
                       "bank.topics", "bank.topic_notes", "bank.review", "bank.update",
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
