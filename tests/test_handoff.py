"""交接协议的机械判据：五项齐全、三查重算、假绿拦截、绕过路径封堵。

这一组测的不是「工具能跑」，而是**工具会不会放过假证据**。
每条用例都对应一条真实的伪造手法（多数由审查席实测打出），
所以判据必须做到：改坏一处就判废，而且要在测试里复现那次改坏。
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import handoff  # noqa: E402


def _marker(**overrides) -> str:
    payload = {
        "kind": "receipt",
        "order_id": 31,
        "modules": {"tests.test_pending_api": {"ran": 16, "ok": True}},
        "probe": {"exists": True, "passed": 40, "total": 40},
        "three_checks": {"fetch(": 0, "parent.document": 0, "localStorage": 0},
    }
    payload.update(overrides)
    return "<!-- handoff:" + json.dumps(payload, ensure_ascii=False) + " -->"


def _receipt(*, test_line: str = "| `tests.test_pending_api` | Ran 16 tests | 绿 |",
             forbidden: str = "禁改区自查：未触碰。",
             open_issues: str = "无",
             probe_line: str = "探针：`probe.json` · passed 40/40",
             marker: str = "") -> str:
    return f"""# 回传单

## 【改动清单】

{forbidden}

```
 M app/core/pending_dedupe.py
```

## 【包结构自检】

本次不涉及插件

## 【三查结果】

`fetch(` 0 · `parent.document` 0 · `localStorage` 0

## 【测试与探针】

{test_line}

```
tests.test_pending_api → Ran 16 tests / OK
```

{probe_line}

## 【未决问题与偏离】

{open_issues}

{marker or _marker()}
"""


class VerifySectionsTest(unittest.TestCase):
    """五项齐全才算回传单。"""

    def test_01_clean_receipt_passes(self):
        self.assertEqual(handoff.verify_text(_receipt()), [])

    def test_02_missing_section_is_rejected(self):
        text = _receipt().replace("## 【包结构自检】", "## 包结构自检")
        problems = handoff.verify_text(text)
        self.assertTrue(any("缺项：【包结构自检】" in item for item in problems))

    def test_03_empty_section_is_rejected(self):
        problems = handoff.verify_text(_receipt(open_issues=""))
        self.assertTrue(any("空项：【未决问题与偏离】" in item for item in problems))

    def test_04_missing_marker_makes_numbers_uncheckable(self):
        problems = handoff.verify_text(_receipt().replace(_marker(), ""))
        self.assertTrue(any("机器可读标记" in item for item in problems))


class ForgedThreeChecksTest(unittest.TestCase):
    """审查席打出的第一号洞：回传单自己写 `three_checks: 0` 就能变绿。

    修法：判据改用**当场重算**的真值，自报只作为比对对象。
    """

    def test_05_forged_zero_is_caught_by_recount(self):
        dirty = {"three_checks": {"fetch(": 3, "parent.document": 0, "localStorage": 0},
                 "head": "abc1234"}
        problems = handoff.verify_text(_receipt(), actual=dirty)
        self.assertTrue(any("当场重算命中 3" in item for item in problems), problems)

    def test_06_claim_mismatch_is_reported_even_when_clean(self):
        actual = {"three_checks": {"fetch(": 0, "parent.document": 0, "localStorage": 0},
                  "head": "abc1234"}
        marker = _marker(three_checks={"fetch(": 2, "parent.document": 0, "localStorage": 0})
        problems = handoff.verify_text(_receipt(marker=marker), actual=actual)
        self.assertTrue(any("自报与实测不符" in item for item in problems), problems)

    def test_07_real_repo_plugins_are_clean(self):
        self.assertEqual(handoff.three_checks(),
                         {"fetch(": 0, "parent.document": 0, "localStorage": 0})


class ZeroEvidenceTest(unittest.TestCase):
    """审查席打出的第二号洞：一个模块都不点名 + 正文写「未跑单测」就能过。

    修法：缺证据默认判废，必须由人当场在命令行显式豁免。
    """

    def test_08_no_modules_is_rejected_by_default(self):
        marker = _marker(modules={})
        problems = handoff.verify_text(_receipt(marker=marker))
        self.assertTrue(any("没有任何单测模块" in item for item in problems), problems)

    def test_09_no_modules_passes_only_with_explicit_exemption(self):
        marker = _marker(modules={})
        problems = handoff.verify_text(_receipt(marker=marker), allow_no_tests=True)
        self.assertEqual(problems, [])


class ProbeEvidenceTest(unittest.TestCase):
    """审查席打出的第三号洞：探针写 `exists:false` 就能跳过红探针。"""

    def test_10_missing_probe_is_rejected_by_default(self):
        marker = _marker(probe={"exists": False})
        problems = handoff.verify_text(_receipt(marker=marker))
        self.assertTrue(any("没有探针证据" in item for item in problems), problems)

    def test_11_missing_probe_passes_with_explicit_exemption(self):
        marker = _marker(probe={"exists": False})
        problems = handoff.verify_text(_receipt(marker=marker), allow_no_probe=True)
        self.assertEqual(problems, [])

    def test_12_red_probe_is_rejected(self):
        marker = _marker(probe={"exists": True, "passed": 38, "total": 40})
        problems = handoff.verify_text(_receipt(marker=marker))
        self.assertTrue(any("探针未全绿：38/40" in item for item in problems))

    def test_13_probe_without_counts_is_rejected(self):
        marker = _marker(probe={"exists": True})
        problems = handoff.verify_text(_receipt(marker=marker))
        self.assertTrue(any("取不到 passed/total" in item for item in problems))


class FakeGreenTest(unittest.TestCase):
    """嘴上「全绿」却拿不出实测行——本项目历史上最贵的教训。"""

    def test_14_bare_all_green_without_numbers_is_rejected(self):
        text = _receipt(test_line="全部通过，全绿。").replace("Ran 16 tests", "已核验")
        problems = handoff.verify_text(text)
        self.assertTrue(any("假绿" in item for item in problems), problems)

    def test_15_all_green_with_real_numbers_is_accepted(self):
        problems = handoff.verify_text(_receipt(test_line="全绿：Ran 16 tests，OK。"))
        self.assertEqual(problems, [])

    def test_16_failed_module_blocks_delivery(self):
        marker = _marker(modules={"tests.test_x": {"ran": 6, "ok": False}})
        problems = handoff.verify_text(_receipt(marker=marker))
        self.assertTrue(any("test_x" in item and "未通过" in item for item in problems))

    def test_17_zero_tests_is_not_evidence(self):
        marker = _marker(modules={"tests.test_y": {"ran": 0, "ok": True}})
        problems = handoff.verify_text(_receipt(marker=marker))
        self.assertTrue(any("没跑出用例数" in item for item in problems))


class SectionInjectionTest(unittest.TestCase):
    """审查席打出的第四号洞：正文里补一段同名标题把真段顶掉。"""

    def test_18_fenced_section_lookalike_is_ignored(self):
        text = _receipt() + "\n\n```\n## 【未决问题与偏离】\n\n假的\n```\n"
        self.assertEqual(handoff.verify_text(text), [])

    def test_19_duplicate_section_later_loses(self):
        # 在末尾追加一段假的「测试与探针」，真段（在前）必须仍被采用
        text = _receipt() + "\n\n## 【测试与探针】\n\n全部通过，无需证据。\n"
        self.assertEqual(handoff.verify_text(text), [])

    def test_20_empty_real_section_cannot_be_filled_by_injection(self):
        # 真段是空的，末尾注入非空假段也不能把它救活
        text = _receipt(open_issues="") + "\n\n## 【未决问题与偏离】\n\n补一段假的\n"
        problems = handoff.verify_text(text)
        self.assertTrue(any("空项：【未决问题与偏离】" in item for item in problems), problems)


class ForbiddenZoneTest(unittest.TestCase):
    """禁改区自查是硬字段：没写就等于没自查。"""

    def test_21_missing_self_check_is_rejected(self):
        problems = handoff.verify_text(_receipt(forbidden="本次改了三个文件。"))
        self.assertTrue(any("禁改区自查" in item for item in problems))


class InterpreterTest(unittest.TestCase):
    """AGENTS §7：必须用 .venv 解释器，**不许退回系统 Python**。"""

    def test_22_missing_venv_fails_loudly(self):
        import tempfile

        original = handoff.ROOT
        with tempfile.TemporaryDirectory() as tmp:
            handoff.ROOT = Path(tmp)
            try:
                with self.assertRaises(SystemExit):
                    handoff._require_python()
            finally:
                handoff.ROOT = original

    def test_23_current_repo_has_venv(self):
        self.assertIsNotNone(handoff.python_exe())


class ProbeClassifyTest(unittest.TestCase):
    """探针产物的形状有两种：汇总字段，或 checks 数组。"""

    def test_24_reads_checks_array(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe.json"
            path.write_text(json.dumps({"checks": [
                {"ok": True}, {"ok": True}, {"ok": False},
            ]}), encoding="utf-8")
            info = handoff.classify_probe(path)
        self.assertEqual(info["total"], 3)
        self.assertEqual(info["passed"], 2)

    def test_25_missing_probe_is_recorded_honestly(self):
        info = handoff.classify_probe(Path("no-such-probe.json"))
        self.assertFalse(info["exists"])


class SeatConfigTest(unittest.TestCase):
    """席位与模型解耦：三席同模型必须在检查里被点名（防近亲审查）。"""

    def test_26_same_model_is_flagged(self):
        rows = [
            {"seat": "brain", "name": "主脑", "base_url": "http://x", "model": "m1"},
            {"seat": "review", "name": "审查", "base_url": "http://x", "model": "m1"},
            {"seat": "worker", "name": "干活", "base_url": "http://x", "model": "m2"},
        ]
        groups = handoff.inbreeding_groups(rows)
        self.assertEqual(groups, [["主脑", "审查"]])

    def test_27_distinct_models_are_not_flagged(self):
        rows = [
            {"seat": "brain", "name": "主脑", "base_url": "http://x", "model": "m1"},
            {"seat": "review", "name": "审查", "base_url": "http://y", "model": "m2"},
        ]
        self.assertEqual(handoff.inbreeding_groups(rows), [])


class RedactTest(unittest.TestCase):
    """复审包会离开本机，密钥形态的字符串必须先抹掉。"""

    def test_29_bearer_and_sk_keys_are_masked(self):
        text = "Authorization: Bearer abcdef123456\napi_key=sk-verysecret123456"
        masked = handoff.redact(text)
        self.assertNotIn("abcdef123456", masked)
        self.assertNotIn("verysecret123456", masked)

    def test_30_short_numbers_survive(self):
        # 超时 120 这种短值不能被当成密钥全文替换掉
        self.assertIn("120", handoff.redact("超时 120 秒"))


class OrderTest(unittest.TestCase):
    """军令卡是下行唯一载体：标题必须能被机器读回。"""

    def test_28_order_round_trips_through_marker(self):
        import tempfile

        original = (handoff.ORDERS, handoff.RECEIPTS, handoff.VERDICTS, handoff.STATE)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            handoff.ORDERS = base / "orders"
            handoff.RECEIPTS = base / "receipts"
            handoff.VERDICTS = base / "verdicts"
            handoff.STATE = base / "state.json"
            try:
                self.assertEqual(handoff.main(["order", "--id", "77", "--title", "查重拦截"]), 0)
                text = (handoff.ORDERS / "077.md").read_text(encoding="utf-8")
                match = handoff.MARKER_RE.search(text)
                self.assertIsNotNone(match)
                payload = json.loads(match.group(1))
                self.assertEqual(payload["order_id"], 77)
                self.assertEqual(payload["title"], "查重拦截")
            finally:
                (handoff.ORDERS, handoff.RECEIPTS, handoff.VERDICTS,
                 handoff.STATE) = original


if __name__ == "__main__":
    unittest.main()
