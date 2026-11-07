"""全域数据字典 Host API：``/api/meta/*`` 的契约。

钉住五件事：
- 11 个主场景按主公裁定的次序返回，场景名就是题目的 ``source.scene_type``；
- 学校简称唯一：冲突时按裁定原话回 409，前端才敢把输入框标红；
- 新建学校幂等（同全称不重复签发 ID），AI 补全只给建议、不落库；
- 交叉标签先按当前场景权重排序：外国题 AMC/A-Level/IB、校考题 9月月考/一模；
- 打一个「模」字，零到七模一次带出来；手打的新标签回车即入本地标签库。

运行：``.venv/Scripts/python.exe -m unittest tests.test_meta_api``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import wire  # noqa: E402

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
TOKEN = "meta-dict-contract-token"

# 主公裁定的场景顺序，一个字都不许挪。
SCENES = (
    "高考题", "联考题", "区域统考题", "校考题", "机构题", "汇编题",
    "自编题", "强基题", "竞赛题", "自主招生题", "外国题",
)

CONFLICT_ID = "哈尔滨师范大学附属中学"
CONFLICT_TEXT = "❌ 简称冲突，已被【哈尔滨师范大学附属中学】占用"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class MetaDictApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.data_dir = root / "data"
        cls.plugins_dir = root / "plugins"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        cls.plugins_dir.mkdir(parents=True, exist_ok=True)
        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        # AI 走 Mock：本测试不出网，也不许读老师本机的真密钥。
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

    def _request(self, path: str, method: str = "GET", body=None,
                 token: str | None = TOKEN) -> tuple[int, object]:
        data = None
        # 查询串里全是中文：不先做百分号编码，urllib 会在客户端直接抛编码错。
        request = urllib.request.Request(
            self.base + urllib.parse.quote(path, safe="/?=&"), method=method
        )
        if body is not None:
            data = wire.dumps(body, ensure_ascii=False).encode("utf-8")
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, data=data, timeout=30) as response:
                raw = response.read()
                return response.status, (wire.loads(raw.decode("utf-8")) if raw else None)
        except urllib.error.HTTPError as error:
            try:
                raw = error.read()
                return error.code, (wire.loads(raw.decode("utf-8")) if raw else None)
            finally:
                error.close()

    def _create_school(self, full_name: str, short_name: str = "") -> tuple[int, object]:
        return self._request("/api/meta/schools", "POST",
                             {"full_name": full_name, "short_name": short_name})

    # ---------- 场景 ----------

    def test_01_scenes_are_the_eleven_in_the_reviewed_order(self) -> None:
        status, body = self._request("/api/meta/scenes")
        self.assertEqual(status, 200, body)
        names = [item["name"] for item in body["scenes"]]
        self.assertEqual(tuple(names), SCENES)
        self.assertEqual(len(names), len(set(names)), "场景不许重复播种")

    # ---------- 学校 ----------

    def test_02_school_writes_require_the_write_token(self) -> None:
        status, body = self._request("/api/meta/schools", "POST",
                                     {"full_name": "哈尔滨市第三中学校", "short_name": "哈三中"},
                                     token=None)
        self.assertEqual(status, 401, body)

    def test_03_school_create_is_idempotent_and_searchable(self) -> None:
        status, body = self._create_school("哈尔滨市第三中学校", "哈三中")
        self.assertEqual(status, 201, body)
        school = body["school"]
        self.assertTrue(school["id"].startswith("sch_"), school)
        self.assertEqual(school["short_name"], "哈三中")
        # 同全称再来一次：200、同一个 ID，绝不重复签发
        status, again = self._create_school("哈尔滨市第三中学校", "哈三中")
        self.assertEqual(status, 200, again)
        self.assertEqual(again["school"]["id"], school["id"])
        status, found = self._request("/api/meta/schools?q=哈三")
        self.assertEqual(status, 200, found)
        self.assertIn(school["id"], [item["id"] for item in found["schools"]])

    def test_04_short_name_conflict_blocks_with_the_exact_sentence(self) -> None:
        status, body = self._create_school(CONFLICT_ID, "师大附中")
        self.assertEqual(status, 201, body)
        status, body = self._create_school("哈尔滨市第九中学校", "师大附中")
        self.assertEqual(status, 409, body)
        detail = body["detail"]
        self.assertEqual(detail["code"], "short_name_conflict")
        self.assertEqual(detail["message"], CONFLICT_TEXT,
                         "拦截原话是主公钦定的，一个字都不许改")
        self.assertEqual(detail["existing_full_name"], CONFLICT_ID)

    def test_05_ai_suggestion_only_proposes_and_never_writes(self) -> None:
        status, body = self._request("/api/meta/schools/suggest", "POST",
                                     {"short_name": "师大附中", "region": "黑龙江"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["full_name"], CONFLICT_ID)
        self.assertTrue(body["mock"], "测试环境必须走 Mock，不许真联网")
        # 只是一个建议：字典里不应该多出一所「北师大附中」之类
        status, found = self._request("/api/meta/schools?q=北师大")
        self.assertEqual(status, 200, found)
        self.assertEqual(found["schools"], [])

    def test_06_suggestion_needs_a_short_name(self) -> None:
        status, body = self._request("/api/meta/schools/suggest", "POST", {"short_name": "  "})
        self.assertEqual(status, 400, body)
        self.assertIn("简称", wire.dumps(body, ensure_ascii=False))

    # ---------- 交叉标签 ----------

    def test_07_foreign_questions_float_amc_a_level_and_ib(self) -> None:
        status, body = self._request("/api/meta/tags?scene=外国题&limit=3")
        self.assertEqual(status, 200, body)
        self.assertEqual([item["name"] for item in body["tags"]], ["AMC", "A-Level", "IB"])

    def test_08_school_questions_float_monthly_and_mock_exams(self) -> None:
        status, body = self._request("/api/meta/tags?scene=校考题&limit=2")
        self.assertEqual(status, 200, body)
        self.assertEqual([item["name"] for item in body["tags"]], ["9月月考", "一模"])

    def test_09_typing_mo_brings_out_all_eight_mock_exams(self) -> None:
        status, body = self._request("/api/meta/tags?scene=校考题&q=模&limit=8")
        self.assertEqual(status, 200, body)
        names = [item["name"] for item in body["tags"]]
        for expected in ("零模", "一模", "二模", "三模", "四模", "五模", "六模", "七模"):
            self.assertIn(expected, names)
        self.assertEqual(names[0], "一模", "当前场景权重最高的先冒头")

    def test_10_a_hand_typed_tag_is_remembered_and_rises(self) -> None:
        status, body = self._request("/api/meta/tags", "POST",
                                     {"name": "百日誓师考", "scene": "校考题"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["tag"]["weight"], 1)
        status, body = self._request("/api/meta/tags", "POST",
                                     {"name": "百日誓师考", "scene": "校考题"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["tag"]["weight"], 2, "同一标签同场景再记一笔，权重加一")
        status, body = self._request("/api/meta/tags?scene=校考题&q=百日")
        self.assertEqual(status, 200, body)
        self.assertEqual(body["tags"][0]["name"], "百日誓师考")
        self.assertGreaterEqual(body["tags"][0]["scene_weight"], 2)

    def test_11_unknown_scene_and_empty_tag_are_rejected(self) -> None:
        status, body = self._request("/api/meta/tags", "POST",
                                     {"name": "联考", "scene": "星座题"})
        self.assertEqual(status, 400, body)
        self.assertIn("不认识的场景", wire.dumps(body, ensure_ascii=False))
        status, body = self._request("/api/meta/tags", "POST", {"name": "   "})
        self.assertEqual(status, 400, body)


if __name__ == "__main__":
    unittest.main()
