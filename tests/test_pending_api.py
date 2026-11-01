"""中转站（待审核池）批次契约：``/api/pending/*``。

运行：``.venv/Scripts/python.exe -m unittest tests.test_pending_api``

钉住七条口径：
- 写接口必须带一次性写令牌；
- 批次号从 ``B-001`` 起递增，题目走 ``p_`` 号段，绝不碰主库的 ``q_``；
- 批次卡片给出时间、编号、未审数 / 总题数；未审数归零的批次沉底、标完成；
- **存入主库要查重**：主库已有同题就拦下来并报出那道题的 id，强行覆盖才放行；
- 配图在池子期间只落 ``pending_assets/``，入库那一刻才搬进 ``uploads/``；
- 彻底删除连图一起删，主库一个字节都不碰；
- 批次未审数归零时，原文件副本**物理删除**（磁盘不留废纸）。
"""

from __future__ import annotations

import base64
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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "pending-contract-token"
PLUGIN_ID = "org.jiuzhang.bank-engine"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _question(index: int = 1, stem: str = "", images: list | None = None) -> dict:
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
    if images:
        document["images"] = images
    return document


class PendingApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tmp_root = Path(cls.tmp.name)
        cls.data_dir = cls.tmp_root / "data"
        cls.plugins_dir = cls.tmp_root / "plugins"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        seed_dir = cls.plugins_dir / PLUGIN_ID / "bank"
        seed_dir.mkdir(parents=True, exist_ok=True)
        # 建库只认插件包里的冻结 schema.sql，测试沙箱必须带上同一份
        shutil.copyfile(ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql",
                        seed_dir / "schema.sql")
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

    def _save(self, questions: list, *, token: str | None = TOKEN,
              **kwargs) -> tuple[int, object]:
        body = {"questions": questions}
        body.update(kwargs)
        return self._request("/api/pending/batches", "POST", body, token=token)

    def _batches(self) -> list[dict]:
        status, body = self._request("/api/pending/batches")
        self.assertEqual(status, 200, body)
        return body["batches"]

    def _card(self, batch_id: str) -> dict:
        for card in self._batches():
            if card["batch_id"] == batch_id:
                return card
        raise AssertionError(f"批次列表里没有 {batch_id}")

    # ---------- 判据 ----------

    def test_01_write_token_is_required(self) -> None:
        status, _ = self._save([{"question": _question(91)}], token=None)
        self.assertEqual(status, 401, "存草稿必须带一次性写令牌")
        status, _ = self._request("/api/pending/items/p_abcdefgh12345678/approve", "POST", {},
                                  token=None)
        self.assertEqual(status, 401)
        status, _ = self._request("/api/pending/items/p_abcdefgh12345678/delete", "POST", {},
                                  token=None)
        self.assertEqual(status, 401)

    def test_02_batch_numbering_and_p_prefix(self) -> None:
        status, body = self._save([{"question": _question(101)}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        self.assertRegex(batch_id, r"^B-\d{3,}$")
        item_id = body["saved_ids"][0]
        self.assertRegex(item_id, r"^p_[A-Za-z0-9_-]{8,64}$", "池子里的题走 p_ 号段")
        self.assertNotIn(str(item_id), json.dumps(body["batch"], ensure_ascii=False))
        # 第二批的号必须比第一批大：号段只增不复用
        status, second = self._save([{"question": _question(102)}])
        self.assertEqual(status, 201, second)
        self.assertGreater(second["batch_id"], batch_id)

    def test_03_batch_card_reports_time_and_counts(self) -> None:
        status, body = self._save([
            {"question": _question(111)},
            {"question": _question(112)},
        ])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        card = self._card(batch_id)
        self.assertEqual(card["pending_count"], 2)
        self.assertEqual(card["total"], 2)
        self.assertFalse(card["done"])
        self.assertRegex(card["label"], r"^\d{4}-\d{2}-\d{2}-星期[一二三四五六日]-\d{2}:\d{2}$",
                         "批次标签形如 2026-11-01-星期日-15:30")

    def test_04_list_returns_questions_of_that_batch(self) -> None:
        status, body = self._save([{"question": _question(121)}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        status, listing = self._request(f"/api/pending/batches/{batch_id}/questions")
        self.assertEqual(status, 200, listing)
        self.assertEqual(listing["batch_id"], batch_id)
        self.assertGreaterEqual(listing["pending_count"], 1)
        item = listing["items"][-1]
        self.assertEqual(item["batch_id"], batch_id)
        self.assertRegex(item["id"], r"^p_")
        self.assertIn("stem", item["question"])
        status, missing = self._request("/api/pending/batches/B-999/questions")
        self.assertEqual(status, 404, missing)

    def test_05_approve_moves_question_into_main_bank(self) -> None:
        status, body = self._save([{"question": _question(131)}])
        self.assertEqual(status, 201, body)
        pending_id = body["saved_ids"][0]
        batch_id = body["batch_id"]
        status, result = self._request(
            f"/api/pending/items/{pending_id}/approve", "POST", {})
        self.assertEqual(status, 200, result)
        self.assertRegex(result["question_id"], r"^q_", "入库后走主库 q_ 号段")
        self.assertTrue(result["created"])
        # 池子里这一条没了，批次的未审数跟着减
        status, listing = self._request(f"/api/pending/batches/{batch_id}/questions")
        self.assertEqual(status, 200, listing)
        self.assertNotIn(pending_id, [item["id"] for item in listing["items"]])
        self.assertEqual(self._card(batch_id)["pending_count"], listing["pending_count"])

    def test_06_duplicate_is_blocked_then_force_overwrites(self) -> None:
        stem = "查重口径题：已知 $f(x)=x^2-5x+6$，求它的零点个数（　　）。"
        status, first = self._save([{"question": _question(141, stem=stem)}])
        self.assertEqual(status, 201, first)
        status, result = self._request(
            f"/api/pending/items/{first['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(status, 200, result)
        existing_id = result["question_id"]

        # 同一道题再进池子：入库必须被拦下来，并把主库那道题的 id 报回去
        status, second = self._save([{"question": _question(142, stem=stem)}])
        self.assertEqual(status, 201, second)
        status, body = self._request(
            f"/api/pending/items/{second['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(status, 409, body)
        self.assertEqual(body["detail"]["existing_id"], existing_id)
        self.assertTrue(body["detail"]["duplicate"])

        # 强行覆盖：以池子里这条为准，主库那道题的 id 不变
        status, forced = self._request(
            f"/api/pending/items/{second['saved_ids'][0]}/approve", "POST", {"force": True})
        self.assertEqual(status, 200, forced)
        self.assertEqual(forced["question_id"], existing_id, "强行覆盖不改题目 id")
        self.assertFalse(forced["created"])
        self.assertTrue(forced["overwritten"])

    def test_07_delete_removes_item_and_counts_down(self) -> None:
        status, body = self._save([{"question": _question(151)}])
        self.assertEqual(status, 201, body)
        pending_id = body["saved_ids"][0]
        batch_id = body["batch_id"]
        status, deleted = self._request(f"/api/pending/items/{pending_id}/delete", "POST", {})
        self.assertEqual(status, 200, deleted)
        status, listing = self._request(f"/api/pending/batches/{batch_id}/questions")
        self.assertEqual(status, 200, listing)
        self.assertNotIn(pending_id, [item["id"] for item in listing["items"]])
        card = self._card(batch_id)
        self.assertEqual(card["pending_count"], listing["pending_count"])

    def test_08_batch_turns_grey_when_nothing_is_left(self) -> None:
        status, body = self._save([{"question": _question(161)}])
        self.assertEqual(status, 201, body)
        pending_id = body["saved_ids"][0]
        batch_id = body["batch_id"]
        status, _ = self._request(f"/api/pending/items/{pending_id}/delete", "POST", {})
        self.assertEqual(status, 200)
        card = self._card(batch_id)
        self.assertEqual(card["pending_count"], 0)
        self.assertTrue(card["done"], "未审数归零的批次要标完成")
        # 已完成的批次沉底：有未审的排在它前面
        cards = self._batches()
        self.assertEqual(cards[-1]["batch_id"], batch_id, "清零的批次沉在列表最底")

    def test_09_source_backup_is_deleted_when_batch_finishes(self) -> None:
        backup = self.data_dir / "pending_assets" / "原卷备份.png"
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(PNG)
        status, body = self._save(
            [{"question": _question(171)}],
            source_backup="pending_assets/原卷备份.png",
        )
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        self.assertTrue(backup.is_file(), "暂存期间原文件副本在原地")
        status, _ = self._request(
            f"/api/pending/items/{body['saved_ids'][0]}/delete", "POST", {})
        self.assertEqual(status, 200)
        self.assertFalse(backup.exists(), "未审数归零时原文件副本必须物理删除")

    def test_10_assets_stay_pending_until_approved(self) -> None:
        status, body = self._save([{
            "question": _question(181, images=[{
                "id": "img_pending_probe", "role": "stem",
                "uri": "/static/uploads/img_pending_probe.png", "alt": "题图",
            }]),
            "assets": [{
                "id": "img_pending_probe",
                "data_url": "data:image/png;base64," + base64.b64encode(PNG).decode(),
            }],
        }])
        self.assertEqual(status, 201, body)
        pending_assets = list((self.data_dir / "pending_assets").glob("pimg_*.png"))
        self.assertEqual(len(pending_assets), 1, "池子里的配图只落 pending_assets/")
        self.assertFalse((self.data_dir / "uploads" / pending_assets[0].name).exists(),
                         "入库前配图不许出现在 uploads/")
        status, listing = self._request(f"/api/pending/batches/{body['batch_id']}/questions")
        item = listing["items"][-1]
        self.assertTrue(item["question"]["images"][0]["uri"].startswith("/static/pending/"))

        status, result = self._request(
            f"/api/pending/items/{item['id']}/approve", "POST", {})
        self.assertEqual(status, 200, result)
        moved = self.data_dir / "uploads" / ("img_" + pending_assets[0].name[len("pimg_"):])
        self.assertTrue(moved.is_file(), "入库那一刻配图搬进 uploads/")
        self.assertFalse(pending_assets[0].exists(), "搬走就是搬走，池子里不留副本")
        self.assertTrue(result["question"]["images"][0]["uri"].startswith("/static/uploads/"))

    def test_11_pending_db_is_a_file_of_its_own(self) -> None:
        self.assertTrue((self.data_dir / "pending.db").is_file())
        bank_db = self.data_dir / "banks" / f"{PLUGIN_ID}.db"
        self.assertTrue(bank_db.is_file(), "主库另起一个文件")
        self.assertNotEqual(self.data_dir / "pending.db", bank_db)

    def test_12_rejects_broken_payloads(self) -> None:
        status, _ = self._save([])
        self.assertEqual(status, 400)
        status, _ = self._save([{"question": {"type": "single_choice"}}])
        self.assertEqual(status, 422, "缺 stem 的题不合契约")
        status, _ = self._request("/api/pending/items/not-an-id/approve", "POST", {})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
