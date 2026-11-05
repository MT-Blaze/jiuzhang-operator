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
import inspect
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
        # S6m·夹具起动竞态修法（同 PoolEvictionHttpTest.setUpClass 的现成先例）：主库
        # 由**测试自己**在 Popen 之前按冻结 schema 建好。后台初查线程会先把
        # ``banks/<id>.db`` 落成没有表的空文件，随后 approve 的结构守卫报 400
        # 「题库 … 缺表：bank_meta」（S6k 十跑第 5 跑实证）。这是夹具时序，
        # 不是产品要判的账（不改产品读路径）。
        from app.core import bank_schema

        (cls.data_dir / "banks").mkdir(parents=True, exist_ok=True)
        bank_schema.init_bank(PLUGIN_ID, db_path=cls.data_dir / "banks" / f"{PLUGIN_ID}.db")
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        # 这批契约用例的前提是「导入的题一直留在待审批次里」，判据 3.5 的自动抽走会把
        # 判成重题的那几行搬进重题池（重复题的 force 覆盖、就地更新、删题等路径就此
        # 撞 404）。抽走与原子搬移由 tests/test_pending_pool.py 的 PoolEvictionTest
        # 六条在服务层盯死，这台测试服务关掉自动抽走，只保留接口契约本身。
        env["JZO_POOL_ADMIT_DISABLED"] = "1"
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
        try:
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
        except BaseException:
            # P1④：``setUpClass`` 抛异常时 unittest **不会**跑 ``tearDownClass``——
            # 进程不收就留下一座攥着临时目录句柄的孤儿服务，下一个用例撞 WinError 32，
            # 而且报错地点离真因隔了几个模块。就绪段的任何失败都就地收干净再原样抛。
            cls._stop_process()
            cls._cleanup_tmp()
            raise

    @classmethod
    def _stop_process(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            # kill() 之后必须再 wait()：不等它就删目录，等于跟 Windows 抢句柄。
            try:
                cls.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop_process()
        cls._cleanup_tmp()

    @classmethod
    def _cleanup_tmp(cls) -> None:
        """删临时目录，给后台线程留一段有界的收尾时间。

        落池即扫的后台线程（``jzo-dedupe-warm``）正在读主库时被 ``TerminateProcess``
        打断，Windows 会在**很短**的一段时间里继续攥着那个库文件句柄——真人等它释放
        是毫秒级，直接删就撞 WinError 32/5。这里按 0.2s 退避重试，最多 5s：
        句柄真漏了（连接没关）就照样把最后一个错误原样抛出去，绝不静默吞掉。
        """
        deadline = time.time() + 5.0
        while True:
            try:
                cls.tmp.cleanup()
                return
            except (PermissionError, OSError) as error:
                if time.time() >= deadline:
                    raise
                time.sleep(0.2)
                del error

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

    def test_06_precheck_reports_both_documents(self) -> None:
        """入库前的后台查重：命中要把**两侧完整文档**一起回，插件才能做渲染对比。"""
        stem = "查重预检题：已知 $g(x)=x^3-2x$，求它的导函数（　　）。"
        status, first = self._save([{"question": _question(143, stem=stem)}])
        self.assertEqual(status, 201, first)
        status, stored = self._request(
            f"/api/pending/items/{first['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(status, 200, stored)
        existing_id = stored["question_id"]

        status, second = self._save([{"question": _question(144, stem=stem)}])
        self.assertEqual(status, 201, second)
        status, report = self._request(
            f"/api/pending/items/{second['saved_ids'][0]}/duplicate")
        self.assertEqual(status, 200, report)
        self.assertTrue(report["hit"], report)
        self.assertEqual(report["level"], "identical")
        self.assertEqual(report["existing_id"], existing_id)
        self.assertEqual(report["incoming"]["stem"], stem, "要回池子里这一条的文档")
        self.assertEqual(report["existing"]["id"], existing_id, "要回主库那一条的文档")
        self.assertIs(report["answer"]["same"], True, "两边答案一致")
        self.assertFalse(report["blocked"])

    def test_06_merge_solution_appends_the_second_solution(self) -> None:
        """合并为解析二：主库那题一字不动，只把池子里这条的解析并成「解法二」。"""
        stem = "合并解析二题：已知 $h(x)=2x+1$，求 $h(3)$（　　）。"
        status, first = self._save([{"question": _question(145, stem=stem)}])
        self.assertEqual(status, 201, first)
        status, stored = self._request(
            f"/api/pending/items/{first['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(status, 200, stored)
        existing_id = stored["question_id"]
        base_solution = stored["question"]["solution"]

        second_doc = _question(146, stem=stem)
        second_doc["solution"] = r"直接把 $x=3$ 代入：$2\times3+1=7$。"
        status, second = self._save([{"question": second_doc}])
        self.assertEqual(status, 201, second)
        pending_id = second["saved_ids"][0]
        batch_id = second["batch_id"]
        status, merged = self._request(
            f"/api/pending/items/{pending_id}/approve", "POST", {"action": "merge_solution"})
        self.assertEqual(status, 200, merged)
        self.assertEqual(merged["question_id"], existing_id, "合并改的是主库那道题，id 不变")
        self.assertTrue(merged["merged_solution"])
        self.assertFalse(merged["overwritten"], "合并不是覆盖")
        solution = merged["question"]["solution"]
        self.assertIn("解法二", solution, "第二段解析必须顶着「解法二」")
        self.assertIn("2\\times3+1=7", solution, "池子里那段解析要真并进去")
        self.assertIn(base_solution.strip(), solution, "主库原来的解析一段都不许丢")
        # 池子里这条已经消化掉，批次未审数跟着减
        status, listing = self._request(f"/api/pending/batches/{batch_id}/questions")
        self.assertEqual(status, 200, listing)
        self.assertNotIn(pending_id, [item["id"] for item in listing["items"]])

    def test_06_different_answer_blocks_overwrite_and_merge(self) -> None:
        """答案不同则红字拦截：覆盖与合并两条路都封死，只留「放弃」。"""
        stem = "答案不同题：已知 $k(x)=x+1$，求 $k(1)$（　　）。"
        first_doc = _question(147, stem=stem)
        first_doc["answer"] = {"kind": "choice", "choice_keys": ["A"], "final": "A"}
        status, first = self._save([{"question": first_doc}])
        self.assertEqual(status, 201, first)
        status, stored = self._request(
            f"/api/pending/items/{first['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(status, 200, stored)

        second_doc = _question(148, stem=stem)
        second_doc["answer"] = {"kind": "choice", "choice_keys": ["C"], "final": "C"}
        status, second = self._save([{"question": second_doc}])
        self.assertEqual(status, 201, second)
        pending_id = second["saved_ids"][0]
        batch_id = second["batch_id"]

        status, report = self._request(f"/api/pending/items/{pending_id}/duplicate")
        self.assertEqual(status, 200, report)
        self.assertIs(report["answer"]["same"], False)
        self.assertTrue(report["blocked"], "答案不同必须报 blocked，界面据此锁死两颗钮")

        for action in ("overwrite", "merge_solution"):
            status, body = self._request(
                f"/api/pending/items/{pending_id}/approve", "POST", {"action": action})
            self.assertEqual(status, 409, body)
            self.assertTrue(body["detail"]["answer_mismatch"], "答案不同就该拦，不分动作")
            self.assertEqual(body["detail"]["existing_id"], stored["question_id"])
        # 两条路都被拦下之后，池子里这一条**原样还在**，主库也没被改。
        status, listing = self._request(f"/api/pending/batches/{batch_id}/questions")
        self.assertEqual(status, 200, listing)
        self.assertIn(pending_id, [item["id"] for item in listing["items"]])

    def test_06_unknown_action_is_rejected(self) -> None:
        """动作白名单只有两个写库动作：别的名字一律不许猜着执行。"""
        status, body = self._save([{"question": _question(149)}])
        self.assertEqual(status, 201, body)
        status, refused = self._request(
            f"/api/pending/items/{body['saved_ids'][0]}/approve", "POST",
            {"action": "force_overwrite"})
        self.assertEqual(status, 400, refused)

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

    def test_13_stash_with_pending_id_updates_in_place(self) -> None:
        """存为待审带 pending_id：池子里不许多出一道重影，题号与总数都不许变。"""
        status, body = self._save([{"question": _question(191)}])
        self.assertEqual(status, 201, body)
        pending_id = body["saved_ids"][0]
        batch_id = body["batch_id"]
        card = self._card(batch_id)
        self.assertEqual(card["total"], 1)

        changed = _question(191, stem="改过之后的题干：已知 $x^2+191=0$，求 $x$（$x>0$）。")
        status, updated = self._save([{"pending_id": pending_id, "question": changed}],
                                     batch_id=batch_id)
        self.assertEqual(status, 201, updated)
        self.assertEqual(updated["saved_ids"], [pending_id], "原地更新，题号不许另发")
        self.assertEqual(updated["batch_id"], batch_id)

        card = self._card(batch_id)
        self.assertEqual(card["total"], 1, "就地更新不许把总数撑大")
        self.assertEqual(card["pending_count"], 1)

        status, listing = self._request(f"/api/pending/batches/{batch_id}/questions")
        self.assertEqual(status, 200, listing)
        ids = [item["id"] for item in listing["items"]]
        self.assertEqual(ids.count(pending_id), 1, "池子里只该有一条")
        self.assertEqual(len(ids), 1)
        self.assertIn("改过之后的题干", listing["items"][0]["question"]["stem"])

    def test_14_stash_with_pending_id_keeps_its_own_id_prefix(self) -> None:
        """带 pending_id 存回去的题，号段必须还是 p_——不许混进主库的 q_ 号段。"""
        status, body = self._save([{"question": _question(195)}])
        self.assertEqual(status, 201, body)
        pending_id = body["saved_ids"][0]
        self.assertRegex(pending_id, r"^p_[A-Za-z0-9_-]{8,64}$")
        status, updated = self._save(
            [{"pending_id": pending_id, "question": _question(196)}], batch_id=body["batch_id"])
        self.assertEqual(status, 201, updated)
        self.assertRegex(updated["saved_ids"][0], r"^p_")
        self.assertEqual(updated["saved_ids"][0], pending_id)

    def test_15_batch_totals_only_grow_on_new_rows(self) -> None:
        """新题进池总数 +1；就地更新总数不变；入库只减未审数，删题连总数一起减。

    分母是「这一批还剩几道有效题」：入库只是把它挪进主库，题还在这一批的名下，
    所以总数不变（审完是「未审：0 / 50 ✅」）；彻底删除是把它从这一批里剔掉，
    总数跟着减一。
    """
        status, body = self._save([{"question": _question(197)}, {"question": _question(198)}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        first_id = body["saved_ids"][0]
        self.assertEqual(self._card(batch_id)["total"], 2)

        status, _ = self._save([{"pending_id": first_id, "question": _question(199)}],
                               batch_id=batch_id)
        self.assertEqual(status, 201)
        self.assertEqual(self._card(batch_id)["total"], 2, "就地更新不涨总数")

        status, _ = self._request(f"/api/pending/items/{first_id}/approve", "POST", {})
        self.assertEqual(status, 200)
        card = self._card(batch_id)
        self.assertEqual(card["pending_count"], 1, "入库只减未审数")
        self.assertEqual(card["total"], 2, "入库不缩分母：这一批还是那两道题")

        status, _ = self._save([{"question": _question(200)}], batch_id=batch_id)
        self.assertEqual(status, 201)
        self.assertEqual(self._card(batch_id)["total"], 3, "新题进池总数 +1")

    def test_16_save_draft_echoes_the_real_asset_address(self) -> None:
        """军令 #26：插件在左栏切完图，得知道底座把字节写到哪个地址去了。

        题面里挂的是 /static/uploads/ 的猜测地址，而字节实际落在 pending_assets/；
        存草稿的回执必须把真实地址递回来，否则题里挂着一张取不到的图。
        """
        status, body = self._save([{
            "question": _question(201, images=[{
                "id": "img_crop_probe", "role": "stem",
                "uri": "/static/uploads/img_crop_probe.png", "alt": "切出来的题图",
            }]),
            "assets": [{
                "id": "img_crop_probe",
                "data_url": "data:image/png;base64," + base64.b64encode(PNG).decode(),
            }],
        }])
        self.assertEqual(status, 201, body)
        self.assertIn("saved_assets", body, "存草稿必须回显配图清单")
        saved = body["saved_assets"][0]
        self.assertEqual(saved["pending_id"], body["saved_ids"][0])
        asset = saved["assets"][0]
        self.assertTrue(asset["uri"].startswith("/static/pending/"),
                        f"池子里的配图地址必须是 /static/pending/，实际是 {asset['uri']}")
        self.assertTrue(asset["name"].startswith("pimg_"), asset)
        self.assertGreater(asset["bytes"], 0)

        # 回执给的地址必须真的能取到那张图。
        name = asset["uri"].rsplit("/", 1)[-1]
        self.assertTrue((self.data_dir / "pending_assets" / name).is_file(),
                        "回执指的地址背后必须有真文件")

    def test_17_set_pages_persists_regions_and_pending_links(self) -> None:
        """老师拖绿框微调后回写坐标：页图尺寸、题块与「框→待审题」的绑定都保住。"""
        status, body = self._save([{"question": _question(202)}])
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        pending_id = body["saved_ids"][0]
        name = "pimg_" + "a" * 16 + ".png"
        (self.data_dir / "pending_assets").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "pending_assets" / name).write_bytes(PNG)
        pages = [{
            "name": name, "page": 1, "width": 1000, "height": 1400,
            "regions": [
                {"no": 1, "x": 10, "y": 20, "w": 300, "h": 400,
                 "label": "1. 第一题", "text": "1. 第一题题干",
                 "pending_id": pending_id},
                {"no": 2, "x": 10, "y": 500, "w": 300, "h": 120,
                 "pending_id": "p_bad"},
            ],
        }]
        status, _ = self._request(f"/api/pending/batches/{batch_id}/pages", "POST",
                                  {"page_images": pages}, token=None)
        self.assertEqual(status, 401, "回写坐标必须带一次性写令牌")

        status, saved = self._request(f"/api/pending/batches/{batch_id}/pages", "POST",
                                      {"page_images": pages})
        self.assertEqual(status, 200, saved)
        self.assertEqual(saved["page_images"][0]["uri"], "/static/pending/" + name)
        listed = self._request(f"/api/pending/batches/{batch_id}/questions")[1]
        page = listed["page_images"][0]
        self.assertEqual((page["width"], page["height"]), (1000, 1400))
        self.assertEqual(page["regions"][0]["pending_id"], pending_id)
        self.assertEqual(page["regions"][0]["y"], 20.0)
        self.assertNotIn("pending_id", page["regions"][1],
                         "号段不合法的绑定一律丢掉，不让前端画出假关联")

        status, _ = self._request(f"/api/pending/batches/{batch_id}/pages", "POST",
                                  {"page_images": []})
        self.assertEqual(status, 400)
        status, _ = self._request("/api/pending/batches/B-999/pages", "POST",
                                  {"page_images": pages})
        self.assertEqual(status, 404)


class PoolEvictionHttpTest(unittest.TestCase):
    """军令 #32 · G2 欠账 6：``test_46``／``test_47`` 的形状搬到 **HTTP 真实路径**。

    服务层那两条走的是「直调函数＋线程代理＋间谍」：``save_draft`` → 收口线程 →
    ``scan_state``，全程零 HTTP 往返，抽走线程也不是底座真起的那一台。本类自起一台
    **开着自动抽走**的服务（显式把 ``JZO_POOL_ADMIT_DISABLED`` 从子进程环境里摘掉），
    题从 ``POST /api/pending/batches`` 进、原答案 ``POST /api/pending/items/{id}/approve``
    入主库、账从 ``GET /api/pending/batches`` 读、池从 ``GET /api/pending/pool`` 数。
    判据 3.5（命中的题一条不留）与 5.4（未审＋池内＝总数）至此**第一次由真机协议端到端
    钉住**，不再只能靠探针。
    """

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
        # 主库由**测试自己**按冻结 schema 建出来。上一台服务不需要这一步：它关着自动抽走，
        # 库是 ``approve`` 那一次「缺库才建」顺手建起来的；这一台开着抽走，
        # 后台初查线程会抢先把 ``banks/<id>.db`` 落成一个**没有表的空文件**，
        # 于是随后 ``approve`` 的结构守卫报 400「库缺少 questions/topic_notes/…」。
        # 这是夹具的时序，不是产品要判的账，所以先把库摆正（不改产品读路径）。
        from app.core import bank_schema

        (cls.data_dir / "banks").mkdir(parents=True, exist_ok=True)
        bank_schema.init_bank(PLUGIN_ID, db_path=cls.data_dir / "banks" / f"{PLUGIN_ID}.db")
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        env.pop("JZO_POOL_ADMIT_DISABLED", None)
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
        try:
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
        except BaseException:
            # 同 P1④：``setUpClass`` 抛异常时 ``tearDownClass`` 不会跑，进程必须就地收掉。
            cls.process.terminate()
            try:
                cls.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.process.kill()
            cls.tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            try:
                cls.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        deadline = time.time() + 5.0
        while True:
            try:
                cls.tmp.cleanup()
                return
            except (PermissionError, OSError):
                if time.time() >= deadline:
                    raise
                time.sleep(0.2)

    def _request(self, path: str, method: str = "GET",
                 body: dict | None = None) -> tuple[int, object]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        request.add_header("X-JZO-Token", TOKEN)
        if data is not None:
            request.add_header("Content-Type", "application/json")
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

    def _card(self, batch_id: str) -> dict:
        status, body = self._request("/api/pending/batches")
        self.assertEqual(status, 200, body)
        for card in body["batches"]:
            if card["batch_id"] == batch_id:
                return card
        raise AssertionError(f"批次列表里没有 {batch_id}")

    def _settle(self, batch_id: str, timeout: float = 20.0) -> list[dict]:
        """轮询到初查出结论为止，把**每一拍**原样记下来（判据 5.4 看的正是中间拍）。"""
        frames: list[dict] = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            card = self._card(batch_id)
            dedupe = card.get("dedupe") or {}
            frames.append({"status": dedupe.get("status"), "pooled": dedupe.get("pooled"),
                           "pending_count": card.get("pending_count"),
                           "total": card.get("total")})
            if dedupe.get("status") in ("done", "failed"):
                return frames
            time.sleep(0.15)
        raise AssertionError(f"{batch_id} 未在 {timeout} 秒内出结论，读到的帧：{frames}")

    def setUp(self) -> None:
        self._wait_bank_ready()

    def _wait_bank_ready(self, timeout: float = 20.0) -> None:
        """等子进程真的把主库建出来再动手。

        ``save_draft`` 甩出的后台初查线程是**第一个**解析 provider、建出
        ``data/banks/*.db`` 的人。``approve`` 抢在它前面时读到的是刚被
        ``sqlite3.connect`` 落出来的空文件，报 400「库缺少 questions/topic_notes/…」
        ——那是本夹具的时序问题，不是本用例要判的账目同源。
        """
        path = self.data_dir / "banks" / f"{PLUGIN_ID}.db"
        deadline = time.time() + timeout
        last = "文件还不存在"
        while time.time() < deadline:
            if path.is_file():
                con = sqlite3.connect(str(path))
                try:
                    have = {str(row[0]) for row in con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")}
                finally:
                    con.close()
                if "questions" in have:
                    return
                last = f"表清单={sorted(have)}"
            time.sleep(0.1)
        raise AssertionError(f"主库未在 {timeout} 秒内建出来：{last}")

    def test_46_http_four_identical_hits_are_all_pooled_not_one(self) -> None:
        """判据 3.5（HTTP 真机）：主库有原题，再导入 4 道同题面＋1 道独题 → 抽走 4 留 1。"""
        first = self._request("/api/pending/batches", "POST",
                              {"questions": [{"question": _question(1)}],
                               "origin": "g2.http.46"})
        self.assertEqual(first[0], 201, first[1])
        original_id = first[1]["saved_ids"][0]
        approved = self._request(f"/api/pending/items/{original_id}/approve", "POST", {})
        self.assertEqual(approved[0], 200, approved[1])
        self.assertTrue((approved[1] or {}).get("question_id")
                        or (approved[1] or {}).get("id"), "原题必须真的进了主库")

        second = self._request("/api/pending/batches", "POST", {"questions": [
            {"question": _question(1)} for _ in range(4)
        ] + [{"question": _question(9, stem="第 9 题：圆台的上底半径为 $2$，下底半径为 $4$，求母线长。")}],
            "origin": "g2.http.46"})
        self.assertEqual(second[0], 201, second[1])
        batch_id = second[1]["batch_id"]
        frames = self._settle(batch_id)
        self.assertEqual(frames[-1]["status"], "done", frames)
        self.assertEqual(frames[-1]["pooled"], 4, "四道命中一条不留（真机协议读到的数）")
        self.assertEqual(frames[-1]["pending_count"], 1, "留在待审里的只有那道独题")
        self.assertEqual(frames[-1]["pending_count"] + frames[-1]["pooled"],
                         frames[-1]["total"], "5.4 的账在 HTTP 这一侧也对平")
        pool = self._request("/api/pending/pool")
        self.assertEqual(pool[0], 200, pool[1])
        # 只数**本批**那四条：整池总数不在本用例口径里。
        # 顺带记下这一台真机观察到的事（不改产品，交 PM 定性）：第一批那道题
        # ``approve`` 进主库后，它自己那条待审行也在**同一秒**进了一层池
        # （``batch_id`` 是 B-001、``main_id`` 正是刚入库的那道）——
        # 即「抽走认刚入库的原题」这条链在真机 HTTP 上同样成立，与 S5f 普查结论一致。
        mine = [item for item in pool[1]["items"] if item.get("batch_id") == batch_id]
        self.assertEqual(len(mine), 4, pool[1])
        self.assertEqual({str(item["level"]) for item in mine}, {"certain"}, mine)
        self.assertEqual({str(item["main_id"]) for item in mine},
                         {str(approved[1].get("question_id") or approved[1].get("id"))}, mine)

    def test_47_http_done_first_frame_already_has_pooled(self) -> None:
        """判据 5.4／S6 缺陷 2（HTTP 真机）：读到 ``done`` 的第一帧就带着 ``pooled``。

        旧的空窗是 ``status=done`` 而 ``pooled=0``、卡片还说题全在待审——老师在那一拍
        看到的是「扫完了、没有重题」。修法把四件事塞进同一条事务之后，
        **对外可见的第一帧 ``done`` 必须同时给出抽完的池内数**；这里逐帧检查，
        任何一帧 ``done`` 配 ``pooled=0`` 都是 FAIL。

        **夹具确定性（S6k·PM 定性）**：类级共享服务里 ``test_46`` 已把 ``_question(1)``
        真 approve 进主库；旧夹具第一题用 ``_question(2)``，两题只差一个数字，
        ``bank_dedupe.confidence`` 实测 ``fairly_similar``／59%，loose 档（默认，全档抽）
        后台抽走线程**有权**在 approve 之前把它抽进池并删待审行——负载高时抽走先提交，
        ``approve`` 就拿到 404「中转站里没有这一条」（S6j 全量并跑实证）。改法只动题干：
        第一题换成与 ``_question(1)`` **不同骨架**的圆台题（confidence 实测 level 空串／
        0，不会被抽走），第二批两题仍用**同一题干**——对刚入库那条仍是 certain，
        末帧 ``pooled=2`` 的账一字不动。断言、sleep、env、产品文件全未碰。
        """
        stem_47 = "第 2 题：圆台的上底半径为 $2$，下底半径为 $4$，求母线长。"
        first = self._request("/api/pending/batches", "POST",
                              {"questions": [{"question": _question(2, stem=stem_47)}],
                               "origin": "g2.http.47"})
        self.assertEqual(first[0], 201, first[1])
        approved = self._request(
            f"/api/pending/items/{first[1]['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(approved[0], 200, approved[1])
        second = self._request("/api/pending/batches", "POST", {"questions": [
            {"question": _question(2, stem=stem_47)},
            {"question": _question(2, stem=stem_47)}],
            "origin": "g2.http.47"})
        self.assertEqual(second[0], 201, second[1])
        batch_id = second[1]["batch_id"]
        frames = self._settle(batch_id)
        for frame in frames:
            if frame["status"] == "done":
                self.assertNotEqual(frame["pooled"], 0,
                                    f"done 第一帧没带池内数，空窗回来了：{frames}")
                self.assertEqual(frame["pending_count"], 0, frames)
        self.assertEqual(frames[-1], {"status": "done", "pooled": 2,
                                      "pending_count": 0, "total": 2}, frames)



    def test_48_http_pool_never_holds_the_page_basemap(self) -> None:
        """判据 4.3（HTTP 真机＋数据层直查）：池里只有题自己的成品图，整页底图不进池。

        不拿「审计没报错」冒充「没存」：逐条池行直读 ``duplicate_pool.assets_json``／
        ``doc_json`` 与 ``pool_assets/`` 目录实况（文件名＋字节数），三件事同时钉——
        ① 池账里每个名字都是 ``cimg_`` 号段、字节数等于题图那份；
        ② ``pool_assets/`` 目录里**不多不少**就是池账点名的这几张（页图混进来就炸）；
        ③ 池行的溯源字段 ``source_name`` 只是字符串，池侧没有任何 ``source_backup`` 列、
        文档里也没有底图地址。整页底图的字节只认**批次**名下的 ``source_backup``
        （服务层由 ``test_pending_pool`` 钉），判据 4.3 的「不进池」由这一条守住。
        """
        import re as _re

        stem = "底图探针题：直角三角形两直角边为 $3$ 与 $4$，求斜长。"
        img = {"id": "img_43_probe", "role": "stem",
               "uri": "/static/uploads/img_43_probe.png", "alt": "题图"}
        asset = {"id": "img_43_probe",
                 "data_url": "data:image/png;base64," + base64.b64encode(PNG).decode()}
        original = self.data_dir / "probe_page_original.png"
        # 一份「整页底图」：与原文件同名同字节的一份大页图（2 页拼出来的假卷面）。
        page_bytes = PNG + b"\x00" * 4096
        original.write_bytes(page_bytes)

        # 主库先有原题（带同一张题图）：池行才有「配一条主库原题」这张入场券
        status, first = self._request("/api/pending/batches", "POST",
                                      {"questions": [{"question": _question(71, stem=stem,
                                                                            images=[img]),
                                                     "assets": [asset]}],
                                       "origin": "g2.http.48"})
        self.assertEqual(status, 201, first)
        approved = self._request(
            f"/api/pending/items/{first['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(approved[0], 200, approved[1])

        payload = {"questions": [{"question": _question(71, stem=stem, images=[img]),
                                  "assets": [asset]} for _ in range(2)],
                   "origin": "g2.http.48"}
        status, body = self._request("/api/pending/batches", "POST", payload)
        self.assertEqual(status, 201, body)
        batch_id = body["batch_id"]
        frames = self._settle(batch_id)
        self.assertEqual(frames[-1]["status"], "done", frames)
        self.assertEqual(frames[-1]["pooled"], 2, "两条命中都进了池（本用例的入场券）")

        con = sqlite3.connect(self.data_dir / "pending.db", timeout=10.0)
        try:
            con.row_factory = sqlite3.Row
            rows = list(con.execute(
                "SELECT pool_id, assets_json, source_name, doc_json FROM duplicate_pool"
                " WHERE batch_id = ?", (batch_id,)))
        finally:
            con.close()
        self.assertEqual(len(rows), 2, [dict(r) for r in rows])
        con = sqlite3.connect(self.data_dir / "pending.db", timeout=10.0)
        try:
            columns = {str(r[1]) for r in con.execute("PRAGMA table_info(duplicate_pool)")}
        finally:
            con.close()
        self.assertNotIn("source_backup", columns,
                         f"池表压根不许有底图列：{sorted(columns)}")
        pool_dir = self.data_dir / "pool_assets"
        listing = {p.name: p.stat().st_size for p in pool_dir.glob("*")} if pool_dir.is_dir() else {}
        cimg_re = _re.compile(r"^cimg_[0-9a-f]{16}\.png$")
        for row in rows:
            names = [str(a.get("name") or "") for a in json.loads(row["assets_json"] or "[]")]
            self.assertTrue(names, f"池行 {row['pool_id']} 该带着题自己的成品图")
            for name in names:
                self.assertRegex(name, cimg_re,
                                 f"池内配图只认 cimg_ 号段，出现了 {name}")
                self.assertNotEqual(name, original.name, "底图文件名不许混进池账")
                self.assertEqual(listing.get(name), PNG.__len__(),
                                 f"池文件 {name} 应当与题图字节等大（{len(PNG)}B），实际 {listing.get(name)}")
            self.assertNotIn("pimg_", row["assets_json"], "待审号段的图不许记进池账")
            self.assertNotIn("page_original", row["doc_json"], "文档里不许留底图地址")
            # 题面 uri 必须已经改写到 /static/pool/（图跟题走的另一半）
            doc = json.loads(row["doc_json"])
            for image in doc.get("images") or []:
                self.assertTrue(str(image.get("uri") or "").startswith("/static/pool/"), doc)
            self.assertEqual(row["source_name"], "", "没传原文件名时溯源字段为空串")
        # 池目录与池账一一对应：多出来的任何一张页图都会在这条上炸；底图文件本身
        # 躺在 data/ 根（夹具自放），目录里不许出现同名者。
        rows_assets = {n for row in rows for n in
                       [str(a.get("name") or "") for a in json.loads(row["assets_json"] or "[]")]}
        self.assertEqual(set(listing), rows_assets,
                         f"pool_assets/ 目录里出现了池账之外的文件：{set(listing) - rows_assets}")
        self.assertNotIn(original.name, listing, "整页底图不许被复制进 pool_assets/")

    def test_49_http_batch_close_keeps_pool_rows_readable(self) -> None:
        """判据 6.2「删批次后池仍在」（HTTP 真机，能证的那半）。

        批次**没有删除接口**（S0 落盘事实），但审完归零就是「批次消失」的现实形态：
        ``pending_count`` 归零、``_settle_batch`` 清残留切图之后，池里那一条必须
        仍可读（``GET /api/pending/pool/{id}`` 200、``incoming.stem`` 逐字对得上）。
        """
        stem = "收口后仍读题：等差首项 $1$、公差 $2$，求第 $5$ 项。"
        status, body = self._request("/api/pending/batches", "POST",
                                     {"questions": [{"question": _question(72, stem=stem)}],
                                      "origin": "g2.http.49"})
        self.assertEqual(status, 201, body)
        status, main_body = self._request(
            f"/api/pending/items/{body['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(status, 200, main_body)

        status, dup = self._request("/api/pending/batches", "POST",
                                    {"questions": [{"question": _question(72, stem=stem)}],
                                     "origin": "g2.http.49"})
        self.assertEqual(status, 201, dup)
        dup_batch = dup["batch_id"]
        dup_item = dup["saved_ids"][0]
        frames = self._settle(dup_batch)
        self.assertEqual(frames[-1]["pooled"], 1, frames)
        pool = self._request("/api/pending/pool")[1]["items"]
        mine = [p for p in pool if p["batch_id"] == dup_batch]
        self.assertEqual(len(mine), 1, pool)

        # 把这条批次审到归零：池里的行不许跟着批次一起消失（题在池里，不在待审里）
        status, done_body = self._request(
            f"/api/pending/items/{dup_item}/approve", "POST", {"force": True})
        self.assertIn(status, (200, 404), done_body)  # 已被抽走则 404，也是「题在池不在待审」
        card = self._card(dup_batch)
        self.assertEqual(card["pending_count"], 0, card)
        self.assertTrue(card["done"], "未审数归零，批次进入完成态（批次消失的现实形态）")
        status, entry = self._request(f"/api/pending/pool/{mine[0]['pool_id']}")
        self.assertEqual(status, 200, entry)
        self.assertEqual(entry["incoming"]["stem"], stem,
                         "批次收口后池内这条的题面必须逐字还在")
        self.assertEqual(entry["batch_id"], dup_batch, "溯源字段留着但不作外键")


    def test_52_keep_separate_lives_only_on_the_explicit_act(self) -> None:
        """判据 5.5-② 的另一半：``keep_separate`` 真身挂在 ``pool/{id}/act`` 显式动作上。

        开着自动抽走这台服务上：主库先有原题，再导入同题面两条 → 都进池；对池行直调
        ``approve`` 只会 404（题已不在待审），走 ``POST /api/pending/pool/{id}/act``
        带 ``{"action": "keep_separate"}`` 才真的**另立一题**（``written=true``、
        新 ``q_`` 号、该池行退场、另一条仍在池里）。
        考向要落真号：主库 ``topics`` 表先插一个叶子（契约 422 认的就是这张表）。
        """
        topic_id = "tp_kx0000006c"
        bank_db = self.data_dir / "banks" / f"{PLUGIN_ID}.db"
        con = sqlite3.connect(bank_db, timeout=10.0)
        try:
            con.execute("INSERT OR IGNORE INTO topics (id, parent_id, textbook_id, name, path,"
                        " sort_order, status, created_at, updated_at)"
                        " VALUES (?, NULL, NULL, ?, ?, 0, 'active', ?, ?)",
                        (topic_id, "考向S6g", topic_id, "2026-11-03T00:00:00+08:00",
                         "2026-11-03T00:00:00+08:00"))
            con.commit()
        finally:
            con.close()

        stem = "分开存探针题：底面半径 $1$、高 $3$ 的圆锥，求体积。"
        doc = _question(83, stem=stem)
        doc["taxonomy"] = {"topic_ids": [topic_id]}
        status, first = self._request("/api/pending/batches", "POST",
                                      {"questions": [{"question": doc}],
                                       "origin": "g2.gate.52"})
        self.assertEqual(status, 201, first)
        status, approved = self._request(
            f"/api/pending/items/{first['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(status, 200, approved)

        status, dup = self._request("/api/pending/batches", "POST",
                                    {"questions": [{"question": doc}, {"question": doc}],
                                     "origin": "g2.gate.52"})
        self.assertEqual(status, 201, dup)
        frames = self._settle(dup["batch_id"])
        self.assertEqual(frames[-1]["pooled"], 2, frames)
        pool = self._request("/api/pending/pool")[1]["items"]
        mine = [p for p in pool if p["batch_id"] == dup["batch_id"]]
        self.assertEqual(len(mine), 2, pool)

        # 抽走之后待审行已经没了：绕过前端直调 approve 只会撞 404，碰不到闸门
        status, body = self._request(
            f"/api/pending/items/{mine[0]['item_id']}/approve", "POST", {})
        self.assertEqual(status, 404, body)

        status, act = self._request(
            f"/api/pending/pool/{mine[0]['pool_id']}/act", "POST", {"action": "keep_separate"})
        self.assertEqual(status, 200, act)
        self.assertTrue(act["ok"] and act["written"], act)
        self.assertTrue(act["removed_from_pool"], act)
        created_id = str(act["created_id"])
        self.assertTrue(created_id.startswith("q_"), act)
        self.assertNotEqual(created_id, str(mine[0]["main_id"]))
        # 新题真落了主库、题面逐字对得上
        con = sqlite3.connect(bank_db, timeout=10.0)
        try:
            new_stem = con.execute("SELECT stem FROM questions WHERE id = ?",
                                   (created_id,)).fetchone()
        finally:
            con.close()
        self.assertIsNotNone(new_stem, created_id)
        self.assertEqual(str(new_stem[0]), stem)
        status, pool_after = self._request("/api/pending/pool")
        left = [p for p in pool_after["items"] if p["batch_id"] == dup["batch_id"]]
        self.assertEqual(len(left), 1, "裁决过的那条退场，另一条还在池里")
        self.assertEqual(left[0]["pool_id"], mine[1]["pool_id"], left)


class FinalGateHttpTest(PoolEvictionHttpTest):
    """军令 #32 · S6g 判据 5.5：**绕过前端直调** ``pending.approve`` 也过不去终局闸门。

    复用 ``PoolEvictionHttpTest`` 的夹具与助手，只把 ``setUpClass`` 换掉：这台服务
    **关着自动抽走**（``JZO_POOL_ADMIT_DISABLED=1``，与 :class:`PendingApiContractTest`
    同一开关、同一段理由）——抽走与闸门互斥：开着抽走时，重题在 ``approve`` 之前就被
    搬进池里，``approve`` 只会撞 404，闸门根本没机会出手（S6g 侦察实测：单题批次
    approve 前扫不动、收口后又被抽回池）。要看住的是 ``pending_bank.approve`` 里
    ``find_duplicate`` 那一闸本身，它跟抽走无关，关掉抽走只是把待审行留在原地。

    本类**不继承**父类那两条用例（``unittest`` 只收集类自己定义的 ``test_*``），
    ``tearDownClass`` 沿用父类。
    """

    @classmethod
    def setUpClass(cls) -> None:
        """夹具＝父类那台（自起服务＋自己按冻结 schema 建主库），**但不摘抽走开关**。

        父类在起子进程前会 ``env.pop("JZO_POOL_ADMIT_DISABLED")``；本类要的正是
        按下抽走（S6g 侦察实测：开着抽走时，重题在 ``approve`` 之前就被搬进池里，
        ``approve`` 只会撞 404，闸门根本没机会出手）。所以这里整段照抄父类的
        就绪流程、只删掉那一行 ``pop``——环境变量取进程现有值，父类用例（开着抽走）
        的进程环境不受影响。``tearDownClass`` 沿用父类。
        """
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tmp_root = Path(cls.tmp.name)
        cls.data_dir = cls.tmp_root / "data"
        cls.plugins_dir = cls.tmp_root / "plugins"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        seed_dir = cls.plugins_dir / PLUGIN_ID / "bank"
        seed_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql",
                        seed_dir / "schema.sql")
        from app.core import bank_schema

        (cls.data_dir / "banks").mkdir(parents=True, exist_ok=True)
        bank_schema.init_bank(PLUGIN_ID, db_path=cls.data_dir / "banks" / f"{PLUGIN_ID}.db")
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        env["JZO_POOL_ADMIT_DISABLED"] = "1"
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
        try:
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
        except BaseException:
            cls.process.terminate()
            try:
                cls.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.process.kill()
            cls.tmp.cleanup()
            raise

    def setUp(self) -> None:
        pass  # 主库在 setUpClass 就按冻结 schema 建好了，不必等后台线程

    # 继承来的父类用例在本类不适用（本类关着自动抽走，池内数永远是 0），逐条显式跳过，
    # 真正开着抽走的那一台由 PoolEvictionHttpTest 自己跑它们。
    def test_46_http_four_identical_hits_are_all_pooled_not_one(self) -> None:
        self.skipTest("抽走类用例：本类夹具关着自动抽走，不适用")

    def test_47_http_done_first_frame_already_has_pooled(self) -> None:
        self.skipTest("抽走类用例：本类夹具关着自动抽走，不适用")

    def test_48_http_pool_never_holds_the_page_basemap(self) -> None:
        self.skipTest("抽走类用例：本类夹具关着自动抽走，不适用")

    def test_49_http_batch_close_keeps_pool_rows_readable(self) -> None:
        self.skipTest("抽走类用例：本类夹具关着自动抽走，不适用")

    def test_52_keep_separate_lives_only_on_the_explicit_act(self) -> None:
        self.skipTest("抽走类用例：本类夹具关着自动抽走，不适用")

    def test_50_direct_approve_exact_duplicate_is_blocked(self) -> None:
        """判据 5.5-①：主库已有逐字同题时，直调 approve（不带任何 action/force）必须 409。

        贴真机回执：``detail`` 逐字为
        ``{"message": "主库已有该题（<qid>），可返回修改或强行覆盖。", "existing_id": <qid>, "duplicate": true}``。
        拦截后主库题数不变、待审行原样留在批次里。
        """
        stem = "闸门题：已知 $2x+1=5$，求 $x$。"
        status, first = self._request("/api/pending/batches", "POST",
                                      {"questions": [{"question": _question(81, stem=stem)}],
                                       "origin": "g2.gate.50"})
        self.assertEqual(status, 201, first)
        approved = self._request(
            f"/api/pending/items/{first['saved_ids'][0]}/approve", "POST", {})
        self.assertEqual(approved[0], 200, approved[1])
        main_id = str(approved[1].get("question_id") or approved[1].get("id"))
        bank_db = self.data_dir / "banks" / f"{PLUGIN_ID}.db"
        con = sqlite3.connect(bank_db, timeout=10.0)
        try:
            count_before = con.execute(
                "SELECT COUNT(*) FROM questions WHERE stem LIKE ?",
                (f"%{stem[:8]}%",)).fetchone()[0]
        finally:
            con.close()

        status, second = self._request("/api/pending/batches", "POST",
                                       {"questions": [{"question": _question(81, stem=stem)}],
                                        "origin": "g2.gate.50"})
        self.assertEqual(status, 201, second)
        dup_item = second["saved_ids"][0]
        status, body = self._request(f"/api/pending/items/{dup_item}/approve", "POST", {})
        self.assertEqual(status, 409, body)
        detail = body["detail"]
        self.assertIs(detail["duplicate"], True, detail)
        self.assertEqual(str(detail["existing_id"]), main_id, detail)
        self.assertEqual(detail["message"],
                         f"主库已有该题（{main_id}），可返回修改或强行覆盖。", detail)
        # 拦下来＝真没写库：主库同题面还是一道，待审行还在批次里
        con = sqlite3.connect(bank_db, timeout=10.0)
        try:
            count_after = con.execute(
                "SELECT COUNT(*) FROM questions WHERE stem LIKE ?",
                (f"%{stem[:8]}%",)).fetchone()[0]
        finally:
            con.close()
        self.assertEqual(count_after, count_before, "409 之后主库不许多出一道")
        card = self._card(second["batch_id"])
        self.assertEqual(card["pending_count"], 1, "被拦的题留在待审，不许静默蒸发")

    def test_51_keep_separate_is_not_an_approve_action(self) -> None:
        """判据 5.5-②：``keep_separate`` 不是 approve 的动作，只能走池的显式动作。

        同一条被拦的待审行上：``{"action": "keep_separate"}`` → **400**，``detail`` 逐字
        「不认识的入库动作：keep_separate（只收 overwrite / merge_solution）」——动作校验
        在判重**之前**，连闸门都不给碰。旁证两条：源码里 ``approve`` 只收
        ``DERIVED_ACTIONS``；``pending_pool.ACTIONS`` 才是含 ``keep_separate`` 的那张名单，
        且它只挂在 ``POST /api/pending/pool/{id}/act`` 显式动作上。
        """
        stem = "闸门口径题：已知 $3x-2=7$，求 $x$。"
        status, first = self._request("/api/pending/batches", "POST",
                                      {"questions": [{"question": _question(82, stem=stem)}],
                                       "origin": "g2.gate.51"})
        self.assertEqual(status, 201, first)
        self.assertEqual(self._request(
            f"/api/pending/items/{first['saved_ids'][0]}/approve", "POST", {})[0], 200)
        status, second = self._request("/api/pending/batches", "POST",
                                       {"questions": [{"question": _question(82, stem=stem)}],
                                        "origin": "g2.gate.51"})
        dup_item = second["saved_ids"][0]

        status, body = self._request(f"/api/pending/items/{dup_item}/approve", "POST",
                                     {"action": "keep_separate"})
        self.assertEqual(status, 400, body)
        self.assertEqual(body["detail"],
                         "不认识的入库动作：keep_separate（只收 overwrite / merge_solution）")

        from app.core import pending_bank as _bank
        from app.core import pending_pool as _pool
        source = inspect.getsource(_bank.approve)
        self.assertIn("DERIVED_ACTIONS", source,
                      "approve 的动作白名单必须写在闸门函数里")
        self.assertNotIn("keep_separate", source,
                         "approve 源码里不许出现 keep_separate")
        self.assertEqual(_pool.ACTIONS,
                         ("merge_metadata", "add_solution", "keep_separate", "delete"))
        # 400 之后主库没多出第二道同题面的题——这条才是「拒动作」的真身。
        # （待审行数**不钉**：本类只关了自动「抽走」，自动初查照跑，S6g 实测这台服务上
        #  单题行会在扫描里被搬出待审；行数归 3.5 那条链管，不归这道闸门。）
        con = sqlite3.connect(self.data_dir / "banks" / f"{PLUGIN_ID}.db", timeout=10.0)
        try:
            same = con.execute("SELECT COUNT(*) FROM questions WHERE stem LIKE ?",
                               (f"%{stem[:8]}%",)).fetchone()[0]
        finally:
            con.close()
        self.assertEqual(same, 1, f"拒动作不该写库，主库同题面应只有一道，实际 {same}")


class BatchCardSnapshotTest(unittest.TestCase):
    """军令 #32 · G5：一张卡片的三个计数出自**同一份读快照**。

    不跑 HTTP——要钉的是 ``batch_list()`` 的取数方式，走真服务只能靠轮询撞窗口，
    撞中了才算数、撞不中就是假绿。中间态用「确定性注入」制造：在卡片数池内条数
    那一刻（此时 ``batches`` 行与待审行数**已经读完**），另开一条连接把一次抽走
    事务整份提交（池行 2 条 ＋ 删掉那 2 行待审）。
    同一读快照 ⇒ 卡片只能落在事务的一边：抽走前 ``(pending=2, pooled=0)``
    或抽走后 ``(0, 2)``；逐卡自开连接 ⇒ 必然混出 ``(2, 2)``，而 ``total`` 只有 2，
    正是判据 5.4 上的重复计数（也是 ``test_47`` 那帧 16 跑 4 红的来路）。
    """

    STAMP = "2026-01-15T09:00:00+08:00"

    def setUp(self) -> None:
        from unittest import mock
        from app.core.config import settings
        from app.core import pending_batches, pending_db, pending_dedupe

        self.mock = mock
        self.settings = settings
        self.pending_batches = pending_batches
        self.pending_db = pending_db
        self.pending_dedupe = pending_dedupe
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (os.environ.get("JZO_DATA_DIR"), os.environ.get("JZO_PLUGINS_DIR"),
                       settings.workspace_id)
        self.addCleanup(self._restore_env)
        os.environ["JZO_DATA_DIR"] = self.tmp.name
        settings.workspace_id = None
        con = self.pending_db.connect()          # 建库并把结构迁到当前版本
        try:
            con.execute("INSERT INTO batches (batch_id, label, created_at, updated_at, total)"
                        " VALUES ('B-001', '快照卡', ?, ?, 2)", (self.STAMP, self.STAMP))
            for index in (1, 2):
                con.execute(
                    "INSERT INTO pending_questions (id, batch_id, doc_json, assets_json,"
                    " origin, created_at, updated_at, seq)"
                    " VALUES (?, 'B-001', '{}', '[]', 'ingest', ?, ?, ?)",
                    (f"p_g5{index:04d}", self.STAMP, self.STAMP, index))
            con.commit()
        finally:
            con.close()

    def tearDown(self) -> None:
        self.pending_dedupe._scan_cache.clear()

    def _restore_env(self) -> None:
        for key, value in zip(("JZO_DATA_DIR", "JZO_PLUGINS_DIR"), self._saved[:2]):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.settings.workspace_id = self._saved[2]

    def _evict_like_commit(self) -> None:
        """另一条连接里把一次抽走事务整份提交＝写池行＋删待审行＋落 ``done``。"""
        con = sqlite3.connect(self.pending_db.pending_db_path(), timeout=10.0)
        try:
            for index in (1, 2):
                con.execute(
                    "INSERT INTO duplicate_pool (pool_id, item_id, batch_id, source_name,"
                    " provider_id, main_id, level, percent, similarity, signals_json,"
                    " doc_json, assets_json, created_at, updated_at)"
                    " VALUES (?, ?, 'B-001', '卷.docx', 'org.jiuzhang.bank-engine',"
                    " 'q_g5_main', 'certain', 100, 1.0, '[]', '{}', '[]', ?, ?)",
                    (f"p_g5pool{index}", f"p_g5{index:04d}", self.STAMP, self.STAMP))
            con.execute("DELETE FROM pending_questions WHERE batch_id = 'B-001'")
            con.execute(
                "INSERT OR REPLACE INTO dedupe_scans (batch_id, provider_id, status,"
                " scanned, redundant, batch_redundant, bank_redundant, main_scanned,"
                " tier, truncated, code, retryable, message, finished_at, generation)"
                " VALUES ('B-001', 'org.jiuzhang.bank-engine', 'done', 2, 2, 0, 2, 1,"
                " 'loose', 0, '', 0, '', ?, 1)", (self.STAMP,))
            con.commit()
        finally:
            con.close()

    def test_52_g5_card_counts_share_one_read_snapshot(self) -> None:
        calls: list[object] = []
        mutated = [False]
        original = self.pending_dedupe.pooled_counts

        def hooked(con=None):
            if not mutated[0]:
                mutated[0] = True
                self._evict_like_commit()   # 落在卡片读完待审数之后、数池内数之前
            calls.append(con)
            return original(con)

        with self.mock.patch.object(self.pending_dedupe, "pooled_counts", side_effect=hooked):
            card = next(item for item in self.pending_batches.batch_list()["batches"]
                        if item["batch_id"] == "B-001")
        pooled = card["dedupe"]["pooled"]
        status = str(card["dedupe"]["status"])
        self.assertIn((status, card["pending_count"], pooled),
                      [("pending", 2, 0), ("done", 0, 2)],
                      f"卡片跨过了提交点：状态 {status}／待审 {card['pending_count']}"
                      f"／池内 {pooled} 不是同一代")
        self.assertLessEqual(card["pending_count"] + pooled + card["approved_count"],
                             card["total"],
                             "5.4 的账：未审＋池内＋已存不许超过总数（重复计数就在这儿露出）")
        self.assertEqual(len(calls), 1, f"整批卡片只该数一次池内条数，实际 {len(calls)} 次")
        self.assertIsNotNone(calls[0], "池内条数必须复用 batch_list 那条连接，不许自开")
        self.assertEqual(card["done"], card["pending_count"] == 0)

