"""批次公共元数据与拖入文件的分拣契约：``/api/pending/*/meta`` 与 ``/api/ingest/files``。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pending_meta``

钉住十二条口径：
- 标准名一律由底座按 ``年份-地区-主体-类型-学科`` 拼出来，客户端说了不算；
- 改一次公共字段，这一批**池子里**的所有题立刻同步 ``sources``；
- 明细学校拆成隐藏标签（井号开头），老师的可见标签一个都不许挤掉；
- 主体 → 明细名单记在历史里，下次填同一主体自动带出；
- **搜「哈三中」要能搜出「三省六校」那道题**；
- 拖进来的文件按后缀分拣，``.zip`` 静默忽略（不提示、不建批次）；
- 文本类走轻量解析，解析不出题就如实说，不许编；
- 年份不是数字、批次不存在，一律拒；
- 同一批里的题按**录入先后**排，审核台看到的次序就是卷面次序；
- 老库（结构 v3）升上来时次序原样保留，不在老师脚下重排；
- 入库是**两段式**：响应先把批次立起来，识别在后台跑，占位题**就地**换成真题；
- 认不出内容就如实留一条「待识别」，不许编题。
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
        # AI 一律走 Mock：这些测试不许真联网，也不许读老师本机的密钥。
        for key in ("JZO_AI_API_KEY", "JZO_BAILIAN_API_KEY",
                    "JZO_SILICONFLOW_API_KEY", "JZO_OLLAMA_API_KEY"):
            env[key] = ""
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

    def _wait_parsed(self, batch_id: str, needle: str, timeout: float = 30.0) -> list[dict]:
        """等后台解析把占位题换成真题。

        入库是两段式：响应先把批次立起来，识别在后台任务里跑完再就地替换占位题。
        所以「解析完了没有」只能轮询，不许假设响应回来时就已经解析完。
        """
        deadline = time.time() + timeout
        items: list[dict] = []
        while time.time() < deadline:
            items = self._batch_items(batch_id)
            for item in items:
                if needle in str(item["question"].get("stem") or ""):
                    return items
            time.sleep(0.2)
        self.fail(f"等了 {timeout}s，批次 {batch_id} 里还是没解析出含「{needle}」的题："
                  f"{[item['question'].get('stem') for item in items]}")
        return items

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
            self.assertEqual(source["body"], "三省六校")
            self.assertEqual(source["exam_type"], "高三联考")
            self.assertEqual(source["paper_title"], "2024-黑吉辽-三省六校-高三联考-数学")

    def test_04_detail_schools_are_stored_as_ids_not_names(self) -> None:
        """明细学校只落字典 ID：题目文档里一个校名字节都不许出现。"""
        status, body = self._save([{"question": _question(231, tags=["联考"])}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        status, result = self._set_meta(batch_id, {
            "body": "三省六校",
            "schools": ["哈三中", "哈师大附中"],
        })
        self.assertEqual(status, 200, result)
        item = self._batch_items(batch_id)[0]
        source = item["question"]["source"]
        self.assertEqual(len(source["school_ids"]), 2)
        self.assertEqual(source["school_id"], source["school_ids"][0])
        for school_id in source["school_ids"]:
            self.assertRegex(school_id, r"^sch_[A-Za-z0-9_-]{4,40}$")
        self.assertIn("联考", item["question"]["tags"], "可见标签一个都不许被挤掉")
        self.assertFalse([tag for tag in item["question"]["tags"] if tag.startswith("#")],
                         "校名不再拆成隐藏标签")
        document = json.dumps(item["question"], ensure_ascii=False)
        self.assertNotIn("哈三中", document)
        self.assertNotIn("哈师大附中", document)
        self.assertEqual([s["short_name"] for s in result["meta"]["school_details"]],
                         ["哈三中", "哈师大附中"])

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
        self.assertTrue(body["saved_ids"], "批次里先要有一条款")
        self.assertEqual(body["kinds"], ["text"])
        items = self._wait_parsed(body["batch_id"], "f(x)")
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
            self.assertEqual(int(con.execute("PRAGMA user_version").fetchone()[0]), 5)
            columns = {str(row[1]) for row in con.execute("PRAGMA table_info(pending_questions)")}
            self.assertIn("seq", columns, "结构 v4 必须有次序号这一列")
            tables = {str(row[0]) for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")}
            for table in ("schools", "scene_types", "exam_types"):
                self.assertIn(table, tables, f"结构 v5 必须有 {table} 字典表")
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

    def test_13_batch_appears_first_and_parsing_runs_in_background(self) -> None:
        """入库是两段式：批次先立起来，识别在后台跑，占位题就地换成真题。

        早先是一条道走到底：先把文件解析完（图片要等 OCR）才建批次。
        老师粘贴完只能对着空屏等模型转写。
        """
        payload = "data:text/markdown;base64," + base64.b64encode(
            EXAM_ZH_MD.encode("utf-8")).decode("ascii")
        status, body = self._request("/api/ingest/files", "POST", {
            "files": [{"name": "两段式.md", "data_url": payload}],
        })
        self.assertEqual(status, 201, body)
        self.assertTrue(body["batch_id"], "响应回来时批次就该立起来了")
        self.assertEqual(body["parsing"], True, "响应里要说明识别还在后台跑")
        self.assertEqual(len(body["saved_ids"]), 1, "一个文件先留一条占位题")
        pending_id = str(body["saved_ids"][0])

        items = self._wait_parsed(body["batch_id"], "f(x)")
        self.assertEqual(len(items), 1, "占位题要被就地替换，不许多出一道重影")
        self.assertEqual(str(items[0]["id"]), pending_id,
                         "替换要占原来的号：号一变，老师手里那条就断了")
        self.assertNotIn("正在解析", str(items[0]["question"]["stem"]))
        self.assertIn("f(x)", str(items[0]["question"]["stem"]))

    def test_14_unparsable_file_keeps_an_honest_placeholder(self) -> None:
        """认不出内容就如实留一条「待识别」，不许编题，也不许把批次丢掉。"""
        payload = "data:text/markdown;base64," + base64.b64encode(
            "这只是一段没有题号的散文。".encode("utf-8")).decode("ascii")
        status, body = self._request("/api/ingest/files", "POST", {
            "files": [{"name": "散文.md", "data_url": payload}],
        })
        self.assertEqual(status, 201, body)
        self.assertTrue(body["batch_id"], "认不出也要有批次")
        items = self._batch_items(body["batch_id"])
        self.assertTrue(items, "批次里至少留一条")
        stems = [str(item["question"]["stem"]) for item in items]
        self.assertTrue(any("待识别" in stem for stem in stems),
                        f"认不出就要写明「待识别」，实际是：{stems}")

    # ---------- 全域数据字典（结构 v5） ----------

    def test_15_school_short_name_conflict_is_blocked_with_exact_message(self) -> None:
        status, created = self._request("/api/meta/schools", "POST", {
            "full_name": "哈尔滨师范大学附属中学", "short_name": "师大附中",
        })
        self.assertEqual(status, 201, created)
        self.assertRegex(created["school"]["id"], r"^sch_[A-Za-z0-9_-]{4,40}$")

        status, conflict = self._request("/api/meta/schools", "POST", {
            "full_name": "另一所师范大学附属中学", "short_name": "师大附中",
        })
        self.assertEqual(status, 409, conflict)
        detail = conflict["detail"]
        self.assertEqual(detail["code"], "short_name_conflict")
        self.assertEqual(detail["message"], "❌ 简称冲突，已被【哈尔滨师范大学附属中学】占用",
                         "拦截文案按主公裁定的原话，一字不改")
        self.assertEqual(detail["existing_full_name"], "哈尔滨师范大学附属中学")

    def test_16_school_dictionary_ids_flow_into_meta_and_questions(self) -> None:
        status, found = self._request(
            "/api/meta/schools?q=" + urllib.parse.quote("哈三中"))
        self.assertEqual(status, 200, found)
        self.assertTrue(found["schools"], "字典里已经该有哈三中")
        school_id = found["schools"][0]["id"]

        status, body = self._save([{"question": _question(301)}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        status, result = self._set_meta(batch_id, {
            "year": 2024, "region": "黑吉辽", "body": "三省六校",
            "exam_type": "高三联考", "subject": "数学",
            "school_ids": [school_id],
        })
        self.assertEqual(status, 200, result)
        self.assertEqual(result["meta"]["school_ids"], [school_id])
        self.assertEqual(result["meta"]["school_details"][0]["short_name"], "哈三中",
                         "写只写 ID，读的时候把名字查回来给老师看")

        source = self._batch_items(batch_id)[0]["question"]["source"]
        self.assertEqual(source["school_ids"], [school_id])
        self.assertEqual(source["school_id"], school_id)
        self.assertNotIn("哈三中", json.dumps(source, ensure_ascii=False),
                         "题目文档只存 school_id，校名一个字节都不许进去")

    def test_17_scenes_are_the_eleven_ruled_ones(self) -> None:
        status, body = self._request("/api/meta/scenes")
        self.assertEqual(status, 200, body)
        names = [scene["name"] for scene in body["scenes"]]
        self.assertEqual(names, [
            "高考题", "联考题", "区域统考题", "校考题", "机构题", "汇编题",
            "自编题", "强基题", "竞赛题", "自主招生题", "外国题",
        ])

        status, saved = self._save([{"question": _question(311)}])
        self.assertEqual(status, 201, saved)
        batch_id = saved["batch_id"]
        status, result = self._set_meta(batch_id, {
            "year": 2025, "scene_type": "高考题", "subject": "数学",
        })
        self.assertEqual(status, 200, result)
        self.assertEqual(result["meta"]["standard_name"], "2025-高考题-数学",
                         "标准名里要有场景这一段")
        source = self._batch_items(batch_id)[0]["question"]["source"]
        self.assertEqual(source["scene_type"], "高考题")

        status, _ = self._set_meta(batch_id, {"scene_type": "野题"})
        self.assertEqual(status, 400, "场景只收 11 个主场景之一")

    def test_18_tag_weights_follow_scene_and_fuzzy_match_remembers(self) -> None:
        status, foreign = self._request(
            "/api/meta/tags?scene=" + urllib.parse.quote("外国题"))
        self.assertEqual(status, 200, foreign)
        names = [tag["name"] for tag in foreign["tags"][:3]]
        self.assertEqual(names, ["AMC", "A-Level", "IB"],
                         "选【外国题】，下拉优先显示 AMC、A-Level、IB")

        status, school = self._request(
            "/api/meta/tags?scene=" + urllib.parse.quote("校考题"))
        self.assertEqual(status, 200, school)
        names = [tag["name"] for tag in school["tags"][:2]]
        self.assertEqual(names, ["9月月考", "一模"],
                         "选【校考题】，下拉优先显示 9月月考、一模")

        status, fuzzy = self._request(
            "/api/meta/tags?scene=" + urllib.parse.quote("校考题") + "&q="
            + urllib.parse.quote("模"))
        self.assertEqual(status, 200, fuzzy)
        names = [tag["name"] for tag in fuzzy["tags"]]
        for expected in ("零模", "一模", "二模", "三模", "四模", "五模", "六模", "七模"):
            self.assertIn(expected, names, "打一个「模」字，零到七模一次带出来")
        self.assertEqual(len(names), 8, f"模糊匹配只该出这 8 个，实际：{names}")

        status, kept = self._request("/api/meta/tags", "POST", {
            "name": "百日誓师考", "scene": "校考题",
        })
        self.assertEqual(status, 200, kept)
        status, again = self._request(
            "/api/meta/tags?scene=" + urllib.parse.quote("校考题") + "&q="
            + urllib.parse.quote("百日"))
        self.assertEqual(status, 200, again)
        self.assertEqual([tag["name"] for tag in again["tags"]], ["百日誓师考"],
                         "老师手打的新标签回车即入本地库，下次自动弹出")

    def test_19_manual_standard_name_pauses_and_metadata_resumes_auto(self) -> None:
        status, saved = self._save([{"question": _question(321)}])
        self.assertEqual(status, 201, saved)
        batch_id = saved["batch_id"]
        base = {
            "year": 2024, "region": "黑吉辽", "body": "三省六校",
            "exam_type": "高三联考", "subject": "数学",
        }
        status, auto = self._set_meta(batch_id, base)
        self.assertEqual(status, 200, auto)
        self.assertEqual(auto["meta"]["name_mode"], "auto")
        self.assertEqual(auto["meta"]["standard_name"], "2024-黑吉辽-三省六校-高三联考-数学")

        status, manual = self._set_meta(batch_id, {
            "name_mode": "manual", "standard_name": "老师自己起的卷名",
        })
        self.assertEqual(status, 200, manual)
        self.assertEqual(manual["meta"]["name_mode"], "manual")
        self.assertEqual(manual["meta"]["standard_name"], "老师自己起的卷名",
                         "手动改名后自动拼接暂停，手改名要留得住")

        # 老师接着改元数据（前端会把整份元数据连同 name_mode=manual 一起送来）：
        # 自动拼接立刻恢复，手改名让位。
        status, resumed = self._set_meta(batch_id, dict(
            base, region="黑龙江", name_mode="manual",
            standard_name="老师自己起的卷名",
        ))
        self.assertEqual(status, 200, resumed)
        self.assertEqual(resumed["meta"]["name_mode"], "auto")
        self.assertEqual(resumed["meta"]["standard_name"],
                         "2024-黑龙江-三省六校-高三联考-数学",
                         "元数据再改，标准名继续自动重拼")

    def test_20_ai_school_suggestion_only_suggests(self) -> None:
        status, before = self._request(
            "/api/meta/schools?q=" + urllib.parse.quote("工大附中"))
        self.assertEqual(status, 200, before)
        status, body = self._request("/api/meta/schools/suggest", "POST", {
            "short_name": "师大附中", "region": "黑龙江",
        })
        self.assertEqual(status, 200, body)
        self.assertEqual(body["full_name"], "哈尔滨师范大学附属中学")
        self.assertTrue(body["mock"], "测试环境走 Mock，不许真联网")
        status, after = self._request(
            "/api/meta/schools?q=" + urllib.parse.quote("工大附中"))
        self.assertEqual(status, 200, after)
        self.assertEqual(before["schools"], after["schools"],
                         "AI 只给建议，老师确认前不许偷偷建档")

    def test_21_bank_schools_keep_dictionary_ids_after_approval(self) -> None:
        status, created = self._request("/api/meta/schools", "POST", {
            "full_name": "哈尔滨市第三中学校", "short_name": "哈三中校本部",
        })
        self.assertIn(status, (200, 201), created)
        school = created["school"]

        status, saved = self._save([{"question": _question(331)}])
        self.assertEqual(status, 201, saved)
        batch_id = saved["batch_id"]
        status, result = self._set_meta(batch_id, {
            "year": 2024, "region": "黑龙江", "body": "哈三中",
            "exam_type": "一模", "subject": "数学", "school_ids": [school["id"]],
        })
        self.assertEqual(status, 200, result)
        pending_id = self._batch_items(batch_id)[0]["id"]
        status, approved = self._request(
            f"/api/pending/items/{pending_id}/approve", "POST", {})
        self.assertEqual(status, 200, approved)

        con = sqlite3.connect(self.data_dir / "banks" / f"{PLUGIN_ID}.db")
        try:
            row = con.execute(
                "SELECT id, full_name, short_name FROM schools WHERE id = ?",
                (school["id"],),
            ).fetchone()
            link = con.execute(
                "SELECT school_id FROM sources WHERE paper_name = ?",
                ("2024-黑龙江-哈三中-一模-数学",),
            ).fetchone()
        finally:
            con.close()
        self.assertIsNotNone(row, "入库时字典 ID 要原样登记进题库")
        self.assertEqual(row[1], "哈尔滨市第三中学校")
        self.assertEqual(row[2], "哈三中校本部")
        self.assertIsNotNone(link)
        self.assertEqual(link[0], school["id"], "来源表按字典 ID 关联学校")

    def test_22_resaving_a_draft_keeps_batch_meta_in_its_source(self) -> None:
        """老师改一道题的源码再存回池子：这一批的公共元数据不许被抹掉。

        插件只报它看得见的题级字段（年份、题型……），场景、学校 ID 与标准名
        全在批次上；暂存时必须按批次重写一遍，否则一道题存一次就丢一段出处。
        """
        status, created = self._request("/api/meta/schools", "POST", {
            "full_name": "哈尔滨市第九中学校", "short_name": "哈九中",
        })
        self.assertIn(status, (200, 201), created)
        school_id = created["school"]["id"]

        status, saved = self._save([{"question": _question(341)}])
        self.assertEqual(status, 201, saved)
        batch_id = saved["batch_id"]
        status, result = self._set_meta(batch_id, {
            "year": 2024, "region": "黑龙江", "body": "哈九中",
            "scene_type": "校考题", "exam_type": "一模", "subject": "数学",
            "school_ids": [school_id],
        })
        self.assertEqual(status, 200, result)

        item = self._batch_items(batch_id)[0]
        doc = json.loads(json.dumps(item["question"], ensure_ascii=False))
        doc["source"] = {"year": 2024, "question_no": "12"}
        status, re_saved = self._save(
            [{"pending_id": item["id"], "question": doc}], batch_id=batch_id)
        self.assertEqual(status, 201, re_saved)

        source = self._batch_items(batch_id)[0]["question"]["source"]
        self.assertEqual(source["scene_type"], "校考题", source)
        self.assertEqual(source["body"], "哈九中", source)
        self.assertEqual(source["school_ids"], [school_id], source)
        self.assertEqual(source["paper_title"], "2024-黑龙江-哈九中-校考题-一模-数学",
                         "标准名要按批次重写回原卷名")


if __name__ == "__main__":
    unittest.main()
