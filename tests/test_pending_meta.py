"""批次公共元数据与拖入文件的分拣契约：``/api/pending/*/meta`` 与 ``/api/ingest/files``。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pending_meta``

钉住十条口径：
- 标准名一律由底座按 ``年份-地区-主体-类型-学科`` 拼出来，客户端说了不算；
- 改一次公共字段，这一批**池子里**的所有题立刻同步 ``sources``；
- 明细学校拆成隐藏标签（井号开头），老师的可见标签一个都不许挤掉；
- 主体 → 明细名单记在历史里，下次填同一主体自动带出；
- **搜「哈三中」要能搜出「三省六校」那道题**；
- 拖进来的文件按后缀分拣，``.zip`` 静默忽略（不提示、不建批次）；
- 文本类走轻量解析，解析不出题就如实说，不许编；
- 年份不是数字、批次不存在，一律拒；
- 同一批里的题按**录入先后**排，审核台看到的次序就是卷面次序；
- 老库（结构 v3）升上来时次序原样保留，不在老师脚下重排。
"""

from __future__ import annotations

import base64
import json
import os
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
TOKEN = "pending-meta-contract-token"
PLUGIN_ID = "org.jiuzhang.bank-engine"

EXAM_ZH_MD = """# 2024 三省六校 联考（节选）

\\begin{question}
已知 $f(x)=x^2-2x+3$，求 $f(x)$ 的最小值。
\\begin{choices}
\\item $1$
\\item $2$
\\item $3$
\\item $4$
\\end{choices}
\\end{question}
\\begin{solution}
答案：A

由配方得 $f(x)=(x-1)^2+2$，当 $x=1$ 时取最小值 $2$。
\\end{solution}
"""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _question(index: int = 1, stem: str = "", tags: list | None = None) -> dict:
    """一道合契约的选择题（契约 2.0 难度 L1–L4）。"""
    text = stem or f"第 {index} 题：已知 $x^2 + {index} = 0$，求 $x$ 的值（$x>0$）。"
    document = {
        "type": "single_choice",
        "stem": text,
        "difficulty": "L2",
        "options": [
            {"key": "A", "content": "$1$"},
            {"key": "B", "content": "$2$"},
            {"key": "C", "content": "$3$"},
            {"key": "D", "content": "$4$"},
        ],
        "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
        "solution": "由 $x^2+1=0$ 得 $x=\\pm i$，取正根。",
    }
    if tags:
        document["tags"] = list(tags)
    return document


class PendingMetaContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tmp_root = Path(cls.tmp.name)
        cls.data_dir = cls.tmp_root / "data"
        cls.plugins_dir = cls.tmp_root / "plugins"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        seed_dir = cls.plugins_dir / PLUGIN_ID / "bank"
        seed_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql",
                        seed_dir / "schema.sql")
        cls._seed_v3_pool()
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        cls.process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", str(cls.port),
                "--log-level", "warning",
            ],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
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

    # ---------- 老库（结构 v3）预置 ----------

    V3_POOL_IDS = ("p_zzz111", "p_aaa222", "p_mmm333")

    @classmethod
    def _seed_v3_pool(cls) -> None:
        """服务起来之前先摆一个结构 v3 的中转站：三道题同一时刻入池。

        题号故意与入池先后对不上（入池是 zzz/aaa/mmm，旧口径按号排就是 aaa/mmm/zzz），
        这样「升级后次序原样保留」和「升级后按号重排」两件事才分得开。
        """
        path = cls.data_dir / "pending.db"
        con = sqlite3.connect(path)
        try:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS batches (
                    batch_id      TEXT PRIMARY KEY,
                    label         TEXT NOT NULL,
                    created_at    TEXT NOT NULL,
                    updated_at    TEXT NOT NULL,
                    source_backup TEXT NOT NULL DEFAULT '',
                    source_name   TEXT NOT NULL DEFAULT '',
                    meta_json     TEXT NOT NULL DEFAULT '{}',
                    approved_json TEXT NOT NULL DEFAULT '[]',
                    total         INTEGER NOT NULL DEFAULT 0,
                    pending_count INTEGER NOT NULL DEFAULT 0,
                    assets_json   TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS pending_questions (
                    id          TEXT PRIMARY KEY,
                    batch_id    TEXT NOT NULL,
                    doc_json    TEXT NOT NULL,
                    assets_json TEXT NOT NULL,
                    origin      TEXT NOT NULL DEFAULT '',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                );
                """
            )
            con.execute(
                "INSERT INTO batches (batch_id, label, created_at, updated_at, total,"
                " pending_count, assets_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("B-001", "老批次", "2026-01-01T00:00:00+08:00",
                 "2026-01-01T00:00:00+08:00", 3, 3, "[]"),
            )
            for pending_id in cls.V3_POOL_IDS:
                con.execute(
                    "INSERT INTO pending_questions (id, batch_id, doc_json, assets_json,"
                    " origin, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (pending_id, "B-001", json.dumps(_question(1), ensure_ascii=False),
                     "[]", "old.pool", "2026-01-01T00:00:00+08:00",
                     "2026-01-01T00:00:00+08:00"),
                )
            con.execute("PRAGMA user_version = 3")
            con.commit()
        finally:
            con.close()

    # ---------- HTTP 小工具 ----------

    def _request(self, path: str, method: str = "GET", body: dict | None = None,
                 token: str | None = TOKEN) -> tuple[int, object]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                return response.status, (json.loads(raw.decode("utf-8")) if raw else None)
        except urllib.error.HTTPError as error:
            try:
                raw = error.read()
                return error.code, (json.loads(raw.decode("utf-8")) if raw else None)
            finally:
                error.close()

    def _save(self, questions: list, **kwargs) -> tuple[int, object]:
        body = {"questions": questions}
        body.update(kwargs)
        return self._request("/api/pending/batches", "POST", body)

    def _set_meta(self, batch_id: str, meta: dict) -> tuple[int, object]:
        return self._request(f"/api/pending/batches/{batch_id}/meta", "PATCH", meta)

    def _batch_items(self, batch_id: str) -> list[dict]:
        status, body = self._request(f"/api/pending/batches/{batch_id}/questions")
        self.assertEqual(status, 200, body)
        return body["items"]

    # ---------- 判据 ----------

    def test_01_standard_name_is_built_by_the_backend(self) -> None:
        status, body = self._save([{"question": _question(201)}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        status, result = self._set_meta(batch_id, {
            "year": 2024,
            "region": "黑吉辽",
            "body": "三省六校",
            "exam_type": "高三联考",
            "subject": "数学",
            "schools": ["哈三中"],
        })
        self.assertEqual(status, 200, result)
        self.assertEqual(result["meta"]["standard_name"], "2024-黑吉辽-三省六校-高三联考-数学")

    def test_02_client_cannot_hand_edit_the_standard_name(self) -> None:
        status, body = self._save([{"question": _question(211)}])
        self.assertEqual(status, 201, body)
        status, result = self._set_meta(body["batch_id"], {
            "year": 2023,
            "region": "黑龙江",
            "body": "哈三中",
            "exam_type": "一模",
            "subject": "数学",
            "standard_name": "我手改的标准名",
        })
        self.assertEqual(status, 200, result)
        self.assertEqual(result["meta"]["standard_name"], "2023-黑龙江-哈三中-一模-数学",
                         "标准名是底座拼的，客户端带来的那一版一律作废")

    def test_03_every_question_in_the_batch_gets_the_sources(self) -> None:
        status, body = self._save([{"question": _question(221)}, {"question": _question(222)}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        status, result = self._set_meta(batch_id, {
            "year": 2024,
            "region": "黑吉辽",
            "body": "三省六校",
            "exam_type": "高三联考",
            "subject": "数学",
        })
        self.assertEqual(status, 200, result)
        self.assertEqual(result["synced"], 2, "这一批的两道题都要同步")
        for item in self._batch_items(batch_id):
            source = item["question"]["source"]
            self.assertEqual(source["year"], 2024)
            self.assertEqual(source["region"], "黑吉辽")
            self.assertEqual(source["school"], "三省六校")
            self.assertEqual(source["exam_type"], "高三联考")
            self.assertEqual(source["paper_title"], "2024-黑吉辽-三省六校-高三联考-数学")

    def test_04_detail_schools_become_hidden_tags(self) -> None:
        status, body = self._save([{"question": _question(231, tags=["联考"])}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        status, result = self._set_meta(batch_id, {
            "body": "三省六校",
            "schools": ["哈三中", "哈师大附中"],
        })
        self.assertEqual(status, 200, result)
        tags = self._batch_items(batch_id)[0]["question"]["tags"]
        self.assertIn("#哈三中", tags)
        self.assertIn("#哈师大附中", tags)
        self.assertIn("联考", tags, "可见标签一个都不许被挤掉")
        self.assertEqual([tag for tag in tags if tag.startswith("#")],
                         ["#哈三中", "#哈师大附中"])

    def test_05_history_remembers_body_and_school_group(self) -> None:
        status, body = self._save([{"question": _question(241)}])
        self.assertEqual(status, 201, body)
        status, _ = self._set_meta(body["batch_id"], {
            "region": "黑吉辽",
            "body": "三省六校",
            "exam_type": "高三联考",
            "subject": "数学",
            "schools": ["哈三中", "哈师大附中"],
        })
        self.assertEqual(status, 200)
        status, history = self._request("/api/pending/meta/history")
        self.assertEqual(status, 200, history)
        self.assertIn("三省六校", history["history"]["body"])
        self.assertIn("黑吉辽", history["history"]["region"])
        self.assertIn("数学", history["history"]["subject"])
        self.assertEqual(history["groups"].get("三省六校"), ["哈三中", "哈师大附中"],
                         "主体 → 明细名单要能自动带出来")

    def test_06_search_by_school_finds_the_group_question(self) -> None:
        """搜「哈三中」要能搜出「三省六校」那道题——明细学校是隐藏标签。"""
        stem = "三省六校那道题：已知 $g(x)=\\ln x$，求 $g'(1)$ 的值（　　）。"
        status, body = self._save([{"question": _question(251, stem=stem)}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        status, _ = self._set_meta(batch_id, {
            "year": 2024, "region": "黑吉辽", "body": "三省六校",
            "exam_type": "高三联考", "subject": "数学", "schools": ["哈三中"],
        })
        self.assertEqual(status, 200)
        pending_id = self._batch_items(batch_id)[0]["id"]
        status, approved = self._request(
            f"/api/pending/items/{pending_id}/approve", "POST", {})
        self.assertEqual(status, 200, approved)
        question_id = approved["question_id"]

        status, found = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions?q=" + urllib.parse.quote("哈三中"))
        self.assertEqual(status, 200, found)
        ids = [item["id"] for item in found["items"]]
        self.assertIn(question_id, ids, "搜「哈三中」要能搜出「三省六校」那道题")
        self.assertGreaterEqual(found["total"], 1)

    def test_07_text_file_becomes_a_batch(self) -> None:
        payload = "data:text/markdown;base64," + base64.b64encode(
            EXAM_ZH_MD.encode("utf-8")).decode("ascii")
        status, body = self._request("/api/ingest/files", "POST", {
            "files": [{"name": "2024三省六校.md", "data_url": payload}],
        })
        self.assertEqual(status, 201, body)
        self.assertTrue(body["batch_id"], "文本类走轻量解析，要建出批次")
        self.assertTrue(body["saved_ids"], "解析出的题要进池子")
        self.assertEqual(body["kinds"], ["text"])
        items = self._batch_items(body["batch_id"])
        self.assertTrue(items)
        self.assertIn("f(x)", items[0]["question"]["stem"])
        card = None
        status, listing = self._request("/api/pending/batches")
        for entry in listing["batches"]:
            if entry["batch_id"] == body["batch_id"]:
                card = entry
        self.assertIsNotNone(card)
        self.assertEqual(card["source_name"], "2024三省六校.md",
                         "原文件名要留在批次卡片上，辅助栏顶部那行灰字就靠它")

    def test_08_zip_is_ignored_silently(self) -> None:
        status, before = self._request("/api/pending/batches")
        self.assertEqual(status, 200)
        payload = "data:application/zip;base64," + base64.b64encode(b"PK\x03\x04rest").decode("ascii")
        status, body = self._request("/api/ingest/files", "POST", {
            "files": [{"name": "插件包.zip", "data_url": payload}],
        })
        self.assertEqual(status, 201, body)
        self.assertEqual(body["batch_id"], "", ".zip 静默忽略：不建批次")
        self.assertEqual(body["saved_ids"], [])
        self.assertEqual(body["ignored"], ["插件包.zip"])
        status, after = self._request("/api/pending/batches")
        self.assertEqual(len(after["batches"]), len(before["batches"]),
                         ".zip 不许凭空多出一个批次")

    def test_09_bad_meta_is_rejected(self) -> None:
        status, body = self._save([{"question": _question(261)}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        status, _ = self._set_meta(batch_id, {"year": "二四"})
        self.assertEqual(status, 400, "年份只能填数字")
        status, _ = self._set_meta(batch_id, {"year": 1200})
        self.assertEqual(status, 400, "年份要落在 1900–2100 之间")
        status, _ = self._set_meta("B-999", {"subject": "数学"})
        self.assertEqual(status, 404, "批次不存在就 404")

    def test_10_meta_write_needs_the_write_token(self) -> None:
        status, body = self._save([{"question": _question(271)}])
        self.assertEqual(status, 201, body)
        status, _ = self._request(
            f"/api/pending/batches/{body['batch_id']}/meta", "PATCH",
            {"subject": "数学"}, token=None)
        self.assertEqual(status, 401, "改公共元数据是写操作，必须带一次性写令牌")

    def test_11_batch_questions_keep_entry_order(self) -> None:
        """一批题是一次写进去的，时间戳全一样——次序必须由次序号说了算。

        早先只能按「时间 + 随机号」排，于是同一批题在审核台里是乱的：
        老师按卷面顺序核题，屏幕上的顺序却随缘。
        """
        questions = [{"question": _question(281 + n)} for n in range(6)]
        status, body = self._save(questions)
        self.assertEqual(status, 201, body)
        items = self._batch_items(body["batch_id"])
        self.assertEqual(len(items), 6)
        stems = [str(item["question"]["stem"]) for item in items]
        expected = [str(item["question"]["stem"]) for item in questions]
        self.assertEqual(stems, expected, "同一批里的题必须按录入先后排")
        # 之后再往这一批里加题，新题排在队尾，原来的次序不动。
        status, body = self._save([{"question": _question(299)}],
                                  batch_id=body["batch_id"])
        self.assertEqual(status, 201, body)
        stems = [str(item["question"]["stem"]) for item in self._batch_items(body["batch_id"])]
        self.assertEqual(stems, expected + [str(_question(299)["stem"])])

    def test_12_old_v3_pool_upgrades_without_reshuffling(self) -> None:
        """老库升到新结构：次序原样保留，题一条不少。"""
        con = sqlite3.connect(self.data_dir / "pending.db")
        try:
            self.assertEqual(int(con.execute("PRAGMA user_version").fetchone()[0]), 4)
            columns = {str(row[1]) for row in con.execute("PRAGMA table_info(pending_questions)")}
            self.assertIn("seq", columns, "结构 v4 必须有次序号这一列")
            rows = con.execute(
                "SELECT id, seq FROM pending_questions WHERE batch_id = 'B-001'"
                " ORDER BY seq ASC").fetchall()
        finally:
            con.close()
        self.assertEqual([str(row[0]) for row in rows],
                         ["p_aaa222", "p_mmm333", "p_zzz111"],
                         "升级前的次序（按时间 + 号）要原样固化成次序号")
        self.assertEqual([int(row[1]) for row in rows], [1, 2, 3])
        items = self._batch_items("B-001")
        self.assertEqual([str(item["id"]) for item in items],
                         ["p_aaa222", "p_mmm333", "p_zzz111"],
                         "升级不许在老师脚下重排这一批题")


if __name__ == "__main__":
    unittest.main()
