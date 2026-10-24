"""题库 CRUD、Schema 校验与插件资产契约。

运行：``.venv/Scripts/python.exe -m unittest tests.test_questions_api``
"""

from __future__ import annotations

import json
import os
import socket
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
TOKEN = "contract-test-token"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _header(headers: dict[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


class QuestionsApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = cls.tmp.name
        env["JZO_LOCAL_TOKEN"] = TOKEN
        cls.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
                "--log-level",
                "warning",
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

    def call(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        token: str | None = None,
    ) -> tuple[int, object, dict[str, str]]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = response.read()
                return response.status, self._decode(raw), dict(response.headers)
        except urllib.error.HTTPError as error:
            try:
                raw = error.read()
                return error.code, self._decode(raw), dict(error.headers)
            finally:
                error.close()

    @staticmethod
    def _decode(raw: bytes):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode("utf-8", errors="replace")

    def create(self, stem: str, **overrides) -> dict:
        payload = {"type": "fill_blank", "stem": stem, "difficulty": "basic"}
        payload.update(overrides)
        status, document, _ = self.call("POST", "/api/questions", payload, token=TOKEN)
        self.assertEqual(status, 201, document)
        return document

    def test_01_writes_require_token(self) -> None:
        payload = {"type": "fill_blank", "stem": "令牌测试", "difficulty": "basic"}
        status, _, _ = self.call("POST", "/api/questions", payload)
        self.assertEqual(status, 401)
        status, _, _ = self.call("POST", "/api/questions", payload, token="wrong-token")
        self.assertEqual(status, 401)

    def test_02_create_fills_server_fields_and_reads_back(self) -> None:
        document = self.create("写入并读取：$x+1=2$")
        self.assertTrue(document["id"].startswith("q_"))
        self.assertEqual(document["schema_version"], "2.0")
        self.assertEqual(document["meta"]["revision"], 1)
        self.assertEqual(document["meta"]["status"], "draft")
        self.assertIn("created_at", document["meta"])

        status, fetched, _ = self.call("GET", "/api/questions/" + document["id"])
        self.assertEqual(status, 200)
        self.assertEqual(fetched["stem"], document["stem"])
        self.assertEqual(fetched["meta"]["revision"], 1)

    def test_03_rejects_schema_violations(self) -> None:
        payload = {
            "type": "single_choice",
            "stem": "缺少选项",
            "difficulty": "basic",
            "options": [{"key": "A", "content": "1"}],
        }
        status, body, _ = self.call("POST", "/api/questions", payload, token=TOKEN)
        self.assertEqual(status, 400)
        self.assertTrue(body["detail"]["errors"])

        status, _, _ = self.call("GET", "/api/questions/q_not_found_0000")
        self.assertEqual(status, 404)

    def test_04_update_increments_revision_and_rejects_stale_write(self) -> None:
        document = self.create("更新前题干")
        document["stem"] = "更新后题干"
        document["meta"]["revision"] = 1

        status, updated, _ = self.call(
            "PUT", "/api/questions/" + document["id"], document, token=TOKEN
        )
        self.assertEqual(status, 200, updated)
        self.assertEqual(updated["meta"]["revision"], 2)
        self.assertEqual(updated["stem"], "更新后题干")
        self.assertEqual(updated["meta"]["created_at"], document["meta"]["created_at"])

        stale = dict(updated)
        stale["meta"] = dict(updated["meta"])
        stale["meta"]["revision"] = 1
        status, _, _ = self.call("PUT", "/api/questions/" + document["id"], stale, token=TOKEN)
        self.assertEqual(status, 409)

    def test_05_delete_is_final_and_id_cannot_be_reused(self) -> None:
        question_id = "q_delete_contract_0001"
        document = self.create("删除契约测试", id=question_id)
        self.assertEqual(document["id"], question_id)

        status, _, _ = self.call("DELETE", "/api/questions/" + question_id, token=TOKEN)
        self.assertEqual(status, 204)
        status, _, _ = self.call("GET", "/api/questions/" + question_id)
        self.assertEqual(status, 404)

        status, body, _ = self.call(
            "POST",
            "/api/questions",
            {"id": question_id, "type": "fill_blank", "stem": "复用已删除 ID", "difficulty": "basic"},
            token=TOKEN,
        )
        self.assertEqual(status, 409, body)

    def test_06_pagination_and_filters(self) -> None:
        marker = "分页契约_" + str(int(time.time() * 1000))
        for index in range(3):
            self.create(f"{marker}_{index}")

        status, page_one, _ = self.call(
            "GET", "/api/questions?q=" + urllib.parse.quote(marker) + "&page=1&page_size=2"
        )
        self.assertEqual(status, 200)
        self.assertEqual(page_one["total"], 3)
        self.assertEqual(page_one["total_pages"], 2)
        self.assertEqual(len(page_one["items"]), 2)

        status, page_two, _ = self.call(
            "GET", "/api/questions?q=" + urllib.parse.quote(marker) + "&page=2&page_size=2"
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(page_two["items"]), 1)

        solution = self.create("筛选契约", type="solution", difficulty="hard")
        status, filtered, _ = self.call(
            "GET", "/api/questions?q=" + urllib.parse.quote("筛选契约") + "&type=solution&difficulty=hard"
        )
        self.assertEqual(status, 200)
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["items"][0]["id"], solution["id"])

    def test_06b_choice_options_stay_an_array_through_read_models(self) -> None:
        """回归：options 是数组（schemas/question.json 的口径），响应模型不得按 dict 校验。

        曾经 ``app/core/models.Question.options`` 声明为 dict[str, str]，写入侧按 Schema
        放行了数组，读取侧 ResponseValidationError 直接把 500 打到 GET /api/questions
        与单题详情上——只要库里有一道选择题，整个题库列表就整页挂掉。
        """
        options = [
            {"key": "A", "content": "$0$"},
            {"key": "B", "content": "$1$"},
            {"key": "C", "content": "$2$"},
            {"key": "D", "content": "$3$"},
        ]
        marker = "选项数组契约_" + str(int(time.time() * 1000))
        document = self.create(
            marker + "：集合 $A=\\{0,1,2\\}$ 的元素个数为（　　）",
            type="single_choice",
            options=options,
            answer={"kind": "choice", "choice_keys": ["C"]},
        )

        status, detail, _ = self.call("GET", "/api/questions/" + document["id"])
        self.assertEqual(status, 200, detail)
        self.assertIsInstance(detail["options"], list)
        self.assertEqual(detail["options"], options)
        self.assertEqual(detail["answer"]["choice_keys"], ["C"])

        status, page, _ = self.call(
            "GET", "/api/questions?q=" + urllib.parse.quote(marker) + "&page=1&page_size=10"
        )
        self.assertEqual(status, 200, page)
        self.assertEqual(page["total"], 1)
        self.assertIsInstance(page["items"][0]["options"], list)
        self.assertEqual([item["key"] for item in page["items"][0]["options"]], ["A", "B", "C", "D"])

    def test_07_plugin_discovery_and_scoped_assets(self) -> None:
        status, discovery, _ = self.call("GET", "/api/plugins")
        self.assertEqual(status, 200)
        plugin_ids = [plugin["id"] for plugin in discovery["plugins"]]
        self.assertIn("org.jiuzhang.core-bank", plugin_ids)
        self.assertEqual(discovery["protocol"], "jzo-plugin/1")

        plugin = next(item for item in discovery["plugins"] if item["id"] == "org.jiuzhang.core-bank")
        status, _, headers = self.call("GET", plugin["entry_url"])
        self.assertEqual(status, 200)
        self.assertIn("text/html", _header(headers, "content-type"))
        self.assertIn("default-src 'none'", _header(headers, "content-security-policy"))

        status, _, _ = self.call(
            "GET", "/plugin-assets/org.jiuzhang.core-bank/%2e%2e/plugin.json"
        )
        self.assertEqual(status, 404)

        status, _, _ = self.call(
            "GET", "/plugin-assets/org.jiuzhang.core-bank/dist/plugin.js"
        )
        self.assertEqual(status, 200)


class OneTimeTokenTest(unittest.TestCase):
    """一次性令牌机制测试：令牌用后即焚，二次使用必被拦截。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        # Use file-based one-time tokens: pin empty so the repo .env can't refill it
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = cls.tmp.name
        env["JZO_LOCAL_TOKEN"] = ""
        cls.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
            ],
            env=env,
            cwd=str(ROOT),
        )
        for _ in range(30):
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=1):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("Server did not start")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        cls.process.wait(timeout=5)
        cls.tmp.cleanup()

    def call(self, method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, bytes, dict]:
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-JZO-Token"] = token
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req)
            return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), dict(exc.headers)

    def test_01_token_rotation_after_use(self) -> None:
        """令牌使用后必须轮换，旧令牌失效。"""
        # Get initial token from settings
        status, body, _ = self.call("GET", "/api/settings")
        self.assertEqual(status, 200)
        settings = json.loads(body)
        token1 = settings["local_token"]
        self.assertTrue(len(token1) > 20)

        # Use token for write operation (minimal payload as per existing tests)
        payload = {"type": "fill_blank", "stem": "令牌测试1", "difficulty": "basic"}
        status, _, _ = self.call("POST", "/api/questions", payload, token=token1)
        self.assertEqual(status, 201, f"First use should succeed, got {status}")

        # Try to reuse the same token - should be rejected
        payload2 = {"type": "fill_blank", "stem": "令牌测试2", "difficulty": "basic"}
        status, body2, _ = self.call("POST", "/api/questions", payload2, token=token1)
        self.assertEqual(status, 401, "Second use of same token should be rejected")
        error = json.loads(body2)
        # Error message contains "失效" or "过期" indicating token is consumed
        detail = error["detail"]
        self.assertTrue("已失效" in detail or "已过期" in detail or "用后即焚" in detail,
                       f"Expected token expired message, got: {detail}")

    def test_02_new_token_after_rotation(self) -> None:
        """令牌轮换后应能获取新令牌并成功写入。"""
        # Get new token after first rotation
        status, body, _ = self.call("GET", "/api/settings")
        self.assertEqual(status, 200)
        settings = json.loads(body)
        token2 = settings["local_token"]

        # Use new token - should succeed
        payload = {"type": "fill_blank", "stem": "新令牌测试", "difficulty": "medium"}
        status, _, _ = self.call("POST", "/api/questions", payload, token=token2)
        self.assertEqual(status, 201, "New token should work")

    def test_03_rejected_write_still_consumes_the_token(self) -> None:
        """令牌在鉴权那一刻就烧掉，与业务成没成功无关。

        前端如果只在 2xx 清缓存，用户在界面上改坏一次写法（400）之后，
        下一次点【确认入库】必然 401，只能刷新页面——这条把前提钉死。
        """
        status, body, _ = self.call("GET", "/api/settings")
        token = json.loads(body)["local_token"]

        bad = {"type": "single_choice", "difficulty": "basic"}  # 缺 stem，Schema 拒
        status, rejected, _ = self.call("POST", "/api/questions", bad, token=token)
        self.assertEqual(status, 400, rejected)

        good = {"type": "fill_blank", "stem": "同一枚令牌第二次", "difficulty": "basic"}
        status, reused, _ = self.call("POST", "/api/questions", good, token=token)
        self.assertEqual(status, 401, "被 400 拒掉的写入也必须已经用完这枚令牌")

        status, fresh, _ = self.call("GET", "/api/settings")
        self.assertEqual(status, 200)
        new_token = json.loads(fresh)["local_token"]
        self.assertNotEqual(new_token, token)
        status, _, _ = self.call("POST", "/api/questions", good, token=new_token)
        self.assertEqual(status, 201, "换到新令牌后写入应当立即恢复")


class MultiWorkspaceIsolationTest(unittest.TestCase):
    """多工作区隔离测试：不同工作区的数据完全独立，互不干扰。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp_base = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        
        # Use single server with workspace switching capability
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = cls.tmp_base.name
        # Use file-based tokens for workspace tests: pin empty so .env can't refill it
        env["JZO_LOCAL_TOKEN"] = ""
        
        cls.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
            ],
            env=env,
            cwd=str(ROOT),
        )
        
        # Wait longer for server startup (60 attempts * 0.5s = 30s max)
        for _ in range(60):
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=1):
                    # Additional wait to ensure app is fully initialized
                    time.sleep(1)
                    break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError(f"Server did not start on port {cls.port}")
        
        # Get initial token from settings endpoint
        cls.token = cls._get_initial_token(cls.port)
    
    @classmethod
    def _get_initial_token(cls, port: int) -> str:
        """Get initial token from settings endpoint."""
        url = f"http://127.0.0.1:{port}/api/settings"
        req = urllib.request.Request(url)
        try:
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())
            return data.get("local_token", "")
        except Exception:
            return ""

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        cls.process.wait(timeout=5)
        cls.tmp_base.cleanup()

    def call(self, method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, bytes, dict]:
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-JZO-Token"] = token
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req)
            return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), dict(exc.headers)

    def test_01_workspace_isolation_via_switching(self) -> None:
        """通过切换工作区验证数据隔离。"""
        # Create workspace A
        status, body, _ = self.call("POST", "/api/workspaces", {"name": "测试工作区A"}, token=self.token)
        self.assertIn(status, [200, 201], f"Should create workspace A, got {status}: {body}")
        ws_a = json.loads(body)
        
        # Create workspace B
        status, body, _ = self.call("POST", "/api/workspaces", {"name": "测试工作区B"}, token=self.token)
        self.assertIn(status, [200, 201], f"Should create workspace B, got {status}: {body}")
        ws_b = json.loads(body)
        
        # Switch to workspace A and get new token
        status, _, _ = self.call("POST", "/api/workspaces/switch", {"workspace_id": ws_a["id"]}, token=self.token)
        self.assertEqual(status, 200, f"Should switch to workspace A")
        self.token = self._get_current_token()
        
        payload_a = {"type": "fill_blank", "stem": "工作区A专属题目", "difficulty": "basic"}
        status, _, _ = self.call("POST", "/api/questions", payload_a, token=self.token)
        self.assertEqual(status, 201, f"Should create question in workspace A, got {status}")
        
        # Switch to workspace B and get new token
        status, _, _ = self.call("POST", "/api/workspaces/switch", {"workspace_id": ws_b["id"]}, token=self.token)
        self.assertEqual(status, 200, f"Should switch to workspace B")
        self.token = self._get_current_token()
        
        # List questions in workspace B - should be empty
        status, body_b, _ = self.call("GET", "/api/questions")
        self.assertEqual(status, 200)
        data_b = json.loads(body_b)
        questions_b = data_b.get("items", []) if isinstance(data_b, dict) else data_b
        self.assertEqual(len(questions_b), 0, "Workspace B should have no questions from A")
        
        # Switch back to workspace A and verify question exists
        status, _, _ = self.call("POST", "/api/workspaces/switch", {"workspace_id": ws_a["id"]}, token=self.token)
        self.assertEqual(status, 200, f"Should switch back to workspace A")
        self.token = self._get_current_token()
        
        status, body_a, _ = self.call("GET", "/api/questions")
        self.assertEqual(status, 200)
        data_a = json.loads(body_a)
        questions_a = data_a.get("items", []) if isinstance(data_a, dict) else data_a
        self.assertTrue(len(questions_a) >= 1, "Workspace A should have at least one question")
        self.assertEqual(questions_a[0]["stem"], "工作区A专属题目")
    
    def _get_current_token(self) -> str:
        """Get current token from settings endpoint."""
        status, body, _ = self.call("GET", "/api/settings")
        if status == 200:
            data = json.loads(body)
            return data.get("local_token", "")
        return ""
    
    def test_02_token_refresh_on_workspace_switch(self) -> None:
        """切换工作区后令牌应刷新。"""
        # Get initial token
        status, body, _ = self.call("GET", "/api/settings")
        self.assertEqual(status, 200)
        initial_settings = json.loads(body)
        token_before = initial_settings["local_token"]
        
        # Create and switch to new workspace
        status, ws_body, _ = self.call("POST", "/api/workspaces", {"name": "令牌测试工作区"}, token=self.token)
        self.assertIn(status, [200, 201])
        ws = json.loads(ws_body)
        
        status, _, _ = self.call("POST", "/api/workspaces/switch", {"workspace_id": ws["id"]}, token=self.token)
        self.assertEqual(status, 200)
        
        # Get new token
        status, body, _ = self.call("GET", "/api/settings")
        self.assertEqual(status, 200)
        new_settings = json.loads(body)
        token_after = new_settings["local_token"]
        
        # Token should be different after workspace switch
        self.assertNotEqual(token_before, token_after, "Token should change after workspace switch")
        
        # Old token should be invalid
        payload = {"type": "fill_blank", "stem": "旧令牌测试", "difficulty": "basic"}
        status, _, _ = self.call("POST", "/api/questions", payload, token=token_before)
        self.assertEqual(status, 401, "Old token should be rejected after workspace switch")

    def test_03_list_marks_single_active_and_honest_db_path(self) -> None:
        """列表必须逐项标注 is_active，恰好一个命中 current；default 库名要真实。

        回归：后端曾只回顶层 current，前端逐项查 ws.is_active，导致下拉框
        永远选不中当前库；且 default 登记的是虚构的 questions.db。
        """
        # 回到 default，保证干净起点
        status, _, _ = self.call(
            "POST", "/api/workspaces/switch", {"workspace_id": "default"}, token=self.token
        )
        self.assertEqual(status, 200)
        self.token = self._get_current_token()

        status, body, _ = self.call("GET", "/api/workspaces")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["current"], "default")

        actives = [w for w in data["workspaces"] if w.get("is_active")]
        self.assertEqual(len(actives), 1, "恰好一个工作区被标为活跃")
        self.assertEqual(actives[0]["id"], data["current"])

        default_entry = next(w for w in data["workspaces"] if w["id"] == "default")
        self.assertTrue(
            default_entry["database"].endswith("jiuzhang.db"),
            f"default 库路径应为真实的 jiuzhang.db，实为 {default_entry['database']}",
        )

    def test_04_switch_returns_workspace_name(self) -> None:
        """切换响应要带 name，前端 toast 才不至于只显示裸 id。"""
        status, body, _ = self.call(
            "POST", "/api/workspaces", {"name": "名字回传工作区"}, token=self.token
        )
        self.assertIn(status, [200, 201])
        ws = json.loads(body)
        self.token = self._get_current_token()

        status, body, _ = self.call(
            "POST", "/api/workspaces/switch", {"workspace_id": ws["id"]}, token=self.token
        )
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result["name"], "名字回传工作区")
        self.assertEqual(result["workspace_id"], ws["id"])
        self.assertTrue(result["is_active"])
        self.token = self._get_current_token()

        # 切回 default 也要回传规范名，而不是裸 id
        status, body, _ = self.call(
            "POST", "/api/workspaces/switch", {"workspace_id": "default"}, token=self.token
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["name"], "默认工作区")
        self.token = self._get_current_token()


if __name__ == "__main__":
    unittest.main(verbosity=2)
