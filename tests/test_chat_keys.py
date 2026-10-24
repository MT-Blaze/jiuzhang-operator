"""军令 #16-R 第一步契约：聊天输入框 Enter 发送、Shift+Enter 换行。

只钉插件源码结构，不启浏览器；真机路径由 tools/chat_keys_probe.py 取证。

运行：``.venv/Scripts/python.exe -m unittest tests.test_chat_keys``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAT_JS = (ROOT / "plugins" / "org.jiuzhang.chat" / "dist" / "plugin.js").read_text(
    encoding="utf-8"
)
CHAT_HTML = (ROOT / "plugins" / "org.jiuzhang.chat" / "dist" / "index.html").read_text(
    encoding="utf-8"
)


def body_of(source: str, signature: str) -> str:
    match = re.search(re.escape(signature) + r"\s*\{(.*?)\n  \}", source, re.S)
    assert match, f"找不到函数体：{signature}"
    return match.group(1)


def composer_keydown() -> str:
    match = re.search(
        r'promptInput\.addEventListener\("keydown", function \(event\) \{(.*?)\n    \}\);',
        CHAT_JS,
        re.S,
    )
    assert match, "找不到输入框 keydown 监听"
    return match.group(1)


class ChatComposerKeyTest(unittest.TestCase):
    def test_01_enter_sends_through_the_shared_exit(self) -> None:
        block = composer_keydown()
        self.assertIn('if (event.key !== "Enter") return;', block)
        self.assertIn("event.preventDefault();", block)
        self.assertIn("submitFromComposer();", block)
        self.assertLess(
            block.index("event.preventDefault();"),
            block.index("submitFromComposer();"),
            "必须先拦掉换行，再从唯一出口发送",
        )

    def test_02_shift_enter_keeps_native_newline(self) -> None:
        block = composer_keydown()
        self.assertIn("if (event.shiftKey) return;", block)
        self.assertLess(
            block.index("if (event.shiftKey) return;"),
            block.index("event.preventDefault();"),
            "Shift+Enter 必须原样交回浏览器换行",
        )

    def test_03_empty_content_sends_nothing_and_keeps_focus(self) -> None:
        block = body_of(CHAT_JS, "function submitFromComposer()")
        self.assertIn(".trim()", block)
        self.assertIn("if (!prompt)", block)
        self.assertIn("promptInput.focus();", block)
        self.assertLess(
            block.index("if (!prompt)"),
            block.index("sendPrompt("),
            "空内容必须在发送之前掉头",
        )
        self.assertNotIn("alert(", block, "空内容不许弹提示")

    def test_04_ime_composition_enter_never_sends(self) -> None:
        block = composer_keydown()
        for token in ("event.isComposing", "composing", "event.keyCode === 229"):
            self.assertIn(token, block, f"组合态缺少防护：{token}")
        self.assertIn('addEventListener("compositionstart"', CHAT_JS)
        self.assertIn('addEventListener("compositionend"', CHAT_JS)
        guard = block.index("event.isComposing")
        self.assertLess(
            guard,
            block.index("event.preventDefault();"),
            "组合态判断必须先于拦截与发送",
        )

    def test_05_focus_outside_composer_does_not_send(self) -> None:
        self.assertEqual(
            1,
            CHAT_JS.count('event.key !== "Enter"'),
            "Enter 只许在输入框监听器里裁决",
        )
        self.assertEqual(1, CHAT_JS.count('promptInput.addEventListener("keydown"'))
        marker = 'document.addEventListener("keydown"'
        if marker in CHAT_JS:
            tail = CHAT_JS[CHAT_JS.index(marker):]
            self.assertNotIn("submitFromComposer", tail, "宿主文档层不许代发聊天")

    def test_06_placeholder_documents_the_rule(self) -> None:
        self.assertIn("Enter 发送", CHAT_HTML)
        self.assertIn("Shift+Enter 换行", CHAT_HTML)

    def test_07_single_line_search_boxes_keep_enter(self) -> None:
        """铁律只管聊天/多行输入框；单行搜索框 Enter 即检索。"""
        for name in ("org.jiuzhang.core-bank", "org.jiuzhang.bank-browser"):
            source = (ROOT / "plugins" / name / "dist" / "plugin.js").read_text(
                encoding="utf-8"
            )
            self.assertIn('event.key === "Enter"', source, f"{name} 的单行搜索丢了 Enter 检索")


if __name__ == "__main__":
    unittest.main()
