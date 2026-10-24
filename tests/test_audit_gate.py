"""审计闸门的闸门：`tools/audit_code.py` 的 except-shadow 规则本身必须可测。

军令 #18-终 阶段六在 `/api/bank/textbooks` 抓到「父类分支在前、子类在后」——这类写法
不报错、单测全绿，只有静态判据钉得住。规则进了工具，就得有测试钉住规则本身，
否则下一次有人把它删掉或写宽，没人知道。

运行：``.venv/Scripts/python.exe -m unittest tests.test_audit_gate``
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_code import scan  # noqa: E402 - 审计工具不是包，按路径导入

SHADOW = '''
class BankError(Exception):
    pass


class BankNotFound(BankError):
    pass


def handler_that_looks_fine():
    try:
        do_something()
    except BankError as exc:
        return 400
    except BankNotFound as exc:
        return 404
'''

# 同一个 handler 里并列捕获两种异常是合法写法，不该被判成顺序问题
TUPLE_FORM = '''
class BankError(Exception):
    pass


class BankNotFound(BankError):
    pass


def legal():
    try:
        do_something()
    except (BankNotFound, BankError) as exc:
        return str(exc)
'''


def _shadow_findings(source: str) -> list:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "bad.py").write_text(source, encoding="utf-8")
        return [item for item in scan(Path(tmp)) if item.rule == "except-shadow"]


class ExceptShadowRuleTest(unittest.TestCase):
    def test_01_parent_before_child_is_an_error(self) -> None:
        found = _shadow_findings(SHADOW)
        self.assertEqual(len(found), 1, f"父类在前应报一条，实到 {len(found)}")
        self.assertEqual(found[0].level, "ERROR")
        self.assertEqual(found[0].line, 15, "要指到子类那一行，改起来才找得着")

    def test_02_tuple_handler_is_not_a_sequence(self) -> None:
        self.assertEqual(_shadow_findings(TUPLE_FORM), [], "并列捕获不是顺序问题")

    def test_03_repository_is_clean_of_this_bug_class(self) -> None:
        """全仓当前不许有 except-shadow——新代码再犯，这条立刻红。"""
        found = [item for item in scan(ROOT) if item.rule == "except-shadow"]
        self.assertEqual(found, [], f"以下位置子类分支不可达：{[(i.path, i.line) for i in found]}")


if __name__ == "__main__":
    unittest.main()
