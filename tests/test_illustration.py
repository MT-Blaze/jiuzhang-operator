"""源码栏【添加配图】契约（终极军令 任务四）。

真机框选与像素落点由浏览器探针取证；这里钉住可静态判定的部分：

- 入口只有一颗：源码栏头部 ``#edAddIllustration``，逻辑住在独立模块
  ``ui_illustration.js``（整块可下架，不污染三栏与切图台）；
- 画板复用切图台底层（取图 / 坐标 / 裁像素），拖框后**保留选框**，
  双击才确认，Esc 取消；确认上传仍走宿主 ``asset.upload``；
- 插入遵守格式宪法：题干/解析 = ``\\vspace{1ex}`` + ``\\begin{center}`` 环境；
  ``\\item`` 选项 = 纯 ``\\includegraphics[width=0.2\\textwidth]{...}``，
  绝不补 ``\\\\``，也不补 ``A.`` 之类的前缀；
- 落点来自源码 textarea / 卡片输入框最后一次光标，点按钮不丢位置。

运行：``.venv/Scripts/python.exe -m unittest tests.test_illustration``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
DIST = PLUGIN_SOURCE_DIR / "org.jiuzhang.editor" / "dist"
HTML = (DIST / "index.html").read_text(encoding="utf-8")
JS = (DIST / "ui_illustration.js").read_text(encoding="utf-8")
CSS = (DIST / "illustration.css").read_text(encoding="utf-8")
PLUGIN_JS = (DIST / "plugin.js").read_text(encoding="utf-8")
DOM_JS = (DIST / "ui_dom.js").read_text(encoding="utf-8")


def function_body(name: str) -> str:
    """取一个具名函数的源码块（到下一个同缩进的 ``function``/``return`` 为止）。"""
    start = JS.index("function " + name + "(")
    rest = JS[start:]
    depth = 0
    for index, char in enumerate(rest):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return rest[: index + 1]
    raise AssertionError(f"function {name} 没有收口")


class IllustrationEntryTest(unittest.TestCase):
    def test_01_button_sits_at_the_source_pane_head(self) -> None:
        head = HTML[HTML.index('id="edPaneSource"'):HTML.index('id="edPaneRender"')]
        self.assertIn('id="edAddIllustration"', head, "【添加配图】必须住在源码栏头部")
        self.assertIn("添加配图", head)
        self.assertNotIn('id="edSourceHint"', head, "提示文字已撤，工具条从最左侧起步")
        # 头部现在两颗：【添加配图】与悬浮画板的【重新切题】，各司其职。
        self.assertEqual(head.count("<button"), 2, "源码栏头部只留配图与重新切题两颗钮")

    def test_02_module_is_loaded_and_wired(self) -> None:
        self.assertIn('<script src="ui_illustration.js"></script>', HTML)
        self.assertIn("JzoEditorIllustration.create", PLUGIN_JS)
        self.assertIn("cropApi: uiCrop", PLUGIN_JS, "画板必须复用切图台的取图/坐标底层")
        self.assertIn("onSourceInput: uiColumns.onSourceInput", PLUGIN_JS)
        self.assertIn("onBoxInput: uiColumns.onBoxInput", PLUGIN_JS)
        self.assertIn("addIllustrationEl", DOM_JS)

    def test_03_no_fetch_token_or_storage(self) -> None:
        for needle in ("fetch(", "X-JZO-Token", "localStorage", "sessionStorage",
                       "indexedDB", "parent.document", "/api/"):
            self.assertNotIn(needle, JS, f"配图模块不许出现 {needle}")
        self.assertIn('hostCall("asset.upload"', JS, "上传只能经宿主")

    def test_04_style_is_a_removable_block(self) -> None:
        self.assertIn(".ed-pane-insert-illustration", CSS)
        self.assertIn(".ed-illustration-canvas", CSS)
        self.assertIn("cursor: crosshair", CSS, "画板必须是十字准心")


class IllustrationBoardTest(unittest.TestCase):
    def test_01_board_reuses_crop_geometry(self) -> None:
        for call in ("cropApi.loadPageBitmap", "cropApi.layoutCrop",
                     "cropApi.cropPoint", "cropApi.cropRegionToDataUrl"):
            self.assertIn(call, JS, f"画板应复用 {call}，不许另造一套坐标")

    def test_02_mouse_up_keeps_the_selection(self) -> None:
        body = function_body("bindCanvas")
        self.assertIn('canvas.addEventListener("dblclick"', body, "双击才是确认")
        self.assertIn("confirmSelection(session)", body)
        # 松手只报尺寸，不许直接落刀——确认权在双击。
        on_up = body[body.index("session.onUp"):body.index("session.onCancel")]
        self.assertNotIn("confirmSelection(", on_up, "mouseup 不得直接确认")
        self.assertIn("双击确认", on_up)

    def test_03_double_click_does_not_wipe_the_rect(self) -> None:
        body = function_body("bindCanvas")
        self.assertIn("pointInRect(session.rect, point)", body,
                      "双击的前两下落在框内，必须放过，不能清框")
        self.assertIn("event.detail > 1", body)

    def test_04_escape_cancels_the_board(self) -> None:
        body = function_body("bindCanvas")
        self.assertIn('event.key !== "Escape"', body)
        self.assertIn("closeBoard()", body)

    def test_05_close_restores_the_original_image(self) -> None:
        body = function_body("closeBoard")
        self.assertIn("session.img.hidden = false", body)
        self.assertIn("session.box.hidden = false", body)
        self.assertNotIn("autoBoxes", body, "绿框已整个下架，收起画板不再有第三样东西要还原")


class IllustrationInsertTest(unittest.TestCase):
    def test_01_centered_environment_for_stem_and_solution(self) -> None:
        body = function_body("centeredSnippet")
        self.assertIn(r'"\\vspace{1ex}\n\\begin{center}\n"', body)
        self.assertIn(r'"\\includegraphics[width=" + CENTER_WIDTH', body)
        self.assertIn(r'"\\end{center}\n"', body)

    def test_02_option_snippet_is_pure_graphics(self) -> None:
        body = function_body("optionSnippet")
        self.assertIn(r'"\\includegraphics[width=" + OPTION_WIDTH', body)
        self.assertIn('OPTION_WIDTH = "0.2\\\\textwidth"', JS)
        # 运行时绝不允许出现 LaTeX 换行（源码里会写成四个反斜杠）
        self.assertNotIn("\\\\\\\\", body, "选项里绝不能补 \\\\")
        self.assertNotIn("A.", body, "选项字母由 \\item 自己长，不许前缀 A.")
        self.assertNotIn("\\\\item", body)

    def test_03_choices_environment_counts_as_option(self) -> None:
        body = function_body("sourceContext")
        self.assertIn('"\\\\begin{choices}"', body)
        self.assertIn('"\\\\end{choices}"', body)
        self.assertIn('? "choice" : "body"', body)

    def test_04_insert_routes_through_the_column_handlers(self) -> None:
        body = function_body("insertAsset")
        self.assertIn('info.field === "source"', body)
        self.assertIn("onSourceInput(info.index, next.text)", body)
        self.assertIn("onBoxInput(info.index, info.field, info.pos, next.text)", body)
        self.assertIn('info.field === "choice" ? "choice" : "body"', body)

    def test_05_caret_is_remembered_before_the_button_click(self) -> None:
        body = function_body("trackEvents")
        for event in ("focusin", "click", "keyup", "select", "input"):
            self.assertIn(event, body, f"漏记 {event} 会让点按钮时丢掉光标")
        self.assertIn("selectionStart", function_body("rememberCaret"))


if __name__ == "__main__":
    unittest.main()
