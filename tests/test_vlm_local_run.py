# -*- coding: utf-8 -*-
"""本地 VLM 逐题识别（T6 §3）：fake 传输层，绝不起真服务不出网。

覆盖：提示词钉题目契约（$...$/$$...$$、绝不编造）／单图请求形状
（image base64 内联＋Bearer 令牌＋900s 等待）／JSON 解不出显性失败／
公式模式剥 $／逐题进度 note＋部分成功不级联／空题图跳过不编图。
运行：``.venv/Scripts/python.exe -m unittest tests.test_vlm_local_run``
"""

from __future__ import annotations

import unittest
import urllib.error
from unittest import mock

from app.core import wire
from app.core.ingest.recognize import vlm_local

ENDPOINT = {"base_url": "http://127.0.0.1:43210", "token": "tok"}


def _item(pid: str = "p_test0001") -> dict:
    return {"id": pid, "page_no": 1,
            "question": {"type": "solution", "stem": "旧题干",
                         "source": {"question_no": "1"},
                         "images": [{"id": "img_" + pid, "role": "stem",
                                     "uri": "/static/pending/" + pid + ".png"}]},
            "assets": [{"name": pid + ".png"}]}


class _FakeResponse:
    def __init__(self, body: dict) -> None:
        self._body = wire.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc) -> None:
        return None


class PromptContractTest(unittest.TestCase):
    def test_question_prompt_pins_the_contract(self) -> None:
        for token in ("$...$", "$$...$$", "绝不编造", r"\( \)", "single_choice",
                      "question_no", "difficulty"):
            self.assertIn(token, vlm_local.QUESTION_PROMPT)

    def test_formula_prompt_is_bare_latex(self) -> None:
        self.assertIn("不要包 $ 或 $$", vlm_local.FORMULA_PROMPT)
        self.assertIn(r"\square", vlm_local.FORMULA_PROMPT)

    def test_single_question_wait_is_900_seconds(self) -> None:
        self.assertEqual(vlm_local.VLM_LOCAL_WAIT_SECONDS, 900.0)


class ChatTransportTest(unittest.TestCase):
    def test_missing_base_url_is_honest_failure(self) -> None:
        outcome = vlm_local._chat(b"png", "p", {"base_url": "", "token": ""})
        self.assertFalse(outcome["ok"])
        self.assertIn("地址缺失", outcome["detail"])

    def test_request_shape_is_openai_compatible_single_image(self) -> None:
        body = {"choices": [{"message": {"content": '{"stem":"求 $x$"}'}}]}
        with mock.patch.object(vlm_local.urllib.request, "urlopen",
                               return_value=_FakeResponse(body)) as urlopen:
            outcome = vlm_local._chat(b"\x89PNG", vlm_local.QUESTION_PROMPT, ENDPOINT)
        self.assertTrue(outcome["ok"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url,
                         "http://127.0.0.1:43210/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer tok")
        payload = wire.loads(request.data.decode("utf-8"))
        content = payload["messages"][0]["content"]
        self.assertTrue(content[0]["image_url"]["url"].startswith(
            "data:image/png;base64,"))
        self.assertEqual(content[1]["text"], vlm_local.QUESTION_PROMPT)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 900.0)

    def test_http_error_is_explicit_not_raised(self) -> None:
        error = urllib.error.HTTPError("http://x", 500, "boom", None, None)
        with mock.patch.object(vlm_local.urllib.request, "urlopen",
                               side_effect=error):
            outcome = vlm_local._chat(b"png", "p", ENDPOINT)
        self.assertFalse(outcome["ok"])
        self.assertIn("HTTP 500", outcome["detail"])

    def test_empty_content_is_failure(self) -> None:
        body = {"choices": [{"message": {"content": "  "}}]}
        with mock.patch.object(vlm_local.urllib.request, "urlopen",
                               return_value=_FakeResponse(body)):
            outcome = vlm_local._chat(b"png", "p", ENDPOINT)
        self.assertFalse(outcome["ok"])
        self.assertIn("没有返回正文", outcome["detail"])


class RecognizeImageTest(unittest.TestCase):
    def test_empty_png_never_fabricates(self) -> None:
        outcome = vlm_local.recognize_image(b"", ENDPOINT)
        self.assertFalse(outcome["ok"])
        self.assertIn("题图为空", outcome["detail"])

    def test_question_json_survives_code_fence(self) -> None:
        text = '```json\n{"type":"solution","stem":"求 $x+1=2$ 的解。"}\n```'
        with mock.patch.object(vlm_local, "_chat",
                               return_value={"ok": True, "text": text}):
            outcome = vlm_local.recognize_image(b"png", ENDPOINT)
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["question"]["stem"], "求 $x+1=2$ 的解。")

    def test_unparseable_or_stemless_json_is_failure(self) -> None:
        for text in ("这不是 JSON", '{"answer":"A"}', '{"stem":"  "}'):
            with self.subTest(text=text):
                with mock.patch.object(vlm_local, "_chat",
                                       return_value={"ok": True, "text": text}):
                    outcome = vlm_local.recognize_image(b"png", ENDPOINT)
                self.assertFalse(outcome["ok"])
                self.assertIn("不是可解析的题目 JSON", outcome["detail"])

    def test_formula_mode_strips_dollars(self) -> None:
        with mock.patch.object(vlm_local, "_chat",
                               return_value={"ok": True, "text": " $$x^2$$ "}):
            outcome = vlm_local.recognize_image(b"png", ENDPOINT, kind="formula")
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["latex"], "x^2")


class RunTest(unittest.IsolatedAsyncioTestCase):
    async def test_partial_success_keeps_going_and_saves_origin(self) -> None:
        items = [_item("p_test0001"), _item("p_test0002")]
        good = {"ok": True, "question": {
            "type": "solution", "stem": "求 $x+1=2$ 的解。", "options": [],
            "answer": "x=1", "solution": "移项得 $x=1$。",
            "question_no": "1", "difficulty": "L2"}}
        snapshots: list[dict] = []
        with mock.patch.object(vlm_local.recognize_shared, "item_image_bytes",
                               return_value=b"png"), \
                mock.patch.object(vlm_local, "recognize_image",
                                  side_effect=[good, {"ok": False, "detail": "超时"}]) as recognize, \
                mock.patch.object(vlm_local.recognize_shared, "save_back",
                                  return_value=True) as save_back:
            route: dict = {}
            result = await vlm_local.run(
                "B-001", items, [0, 1], ENDPOINT, route,
                lambda snapshot: snapshots.append(dict(snapshot)))
        self.assertEqual(recognize.call_count, 2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["filled_indexes"], [0])
        self.assertEqual(result["attempted"], 2)
        self.assertIn("只有 1/2", result["detail"])
        self.assertEqual(save_back.call_count, 1)
        self.assertEqual(save_back.call_args.args[3], "ingest.vlm_local")
        document = save_back.call_args.args[1]
        self.assertEqual(document["stem"], "求 $x+1=2$ 的解。")
        self.assertEqual(document["images"], items[0]["question"]["images"],
                         "题图沿用本地切题那一条，绝不丢")
        self.assertIn("没成功", route["note"])
        self.assertTrue(any("正在将第 1/2 题" in str(s.get("note"))
                            for s in snapshots))

    async def test_all_fail_is_ok_false_no_cascade(self) -> None:
        with mock.patch.object(vlm_local.recognize_shared, "item_image_bytes",
                               return_value=b"png"), \
                mock.patch.object(vlm_local, "recognize_image",
                                  return_value={"ok": False, "detail": "超时"}), \
                mock.patch.object(vlm_local.recognize_shared, "save_back") as save_back:
            result = await vlm_local.run("B-001", [_item()], [0], ENDPOINT, {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["filled_indexes"], [])
        save_back.assert_not_called()

    async def test_empty_indexes_is_noop(self) -> None:
        with mock.patch.object(vlm_local, "recognize_image") as recognize:
            result = await vlm_local.run("B-001", [], [], ENDPOINT, {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["attempted"], 0)
        recognize.assert_not_called()

    async def test_missing_image_is_skipped_not_fabricated(self) -> None:
        with mock.patch.object(vlm_local.recognize_shared, "item_image_bytes",
                               return_value=b""), \
                mock.patch.object(vlm_local, "recognize_image") as recognize:
            result = await vlm_local.run("B-001", [_item()], [0], ENDPOINT, {})
        recognize.assert_not_called()
        self.assertEqual(result["filled"], 0)


if __name__ == "__main__":
    unittest.main()