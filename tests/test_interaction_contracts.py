"""军令 #16 模块一契约（#18 第二步裁剪后）：右键分工、输入铁律与左栏树算法。

快捷键整层已在 #18 第二步删除；本模块只保留与文件键位无关的交互契约：

1. **右键菜单感应**——左栏给新建文件夹/停用插件/重命名，底栏只给复制且**绝不给清空**，
   中间画布一个监听都不挂（右键完全交给插件）；
2. **弹出层可访问性**——菜单与弹窗都能键盘操作，焦点被捕陷，代码里不拼 `innerHTML`；
3. **左栏树与旧顺序迁移**——树算法的边界（文件夹不嵌套、掏空即消失）与 localStorage 一次性搬迁。

运行：``.venv/Scripts/python.exe -m unittest tests.test_interaction_contracts``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
HTML = (STATIC / "workspace.html").read_text(encoding="utf-8")
WORKSPACE_JS = (STATIC / "js" / "workspace.js").read_text(encoding="utf-8")
STAGE_JS = (STATIC / "js" / "stage.js").read_text(encoding="utf-8")
PREFS_JS = (STATIC / "js" / "prefs.js").read_text(encoding="utf-8")
MENU_JS = (STATIC / "js" / "contextmenu.js").read_text(encoding="utf-8")
DIALOG_JS = (STATIC / "js" / "dialogs.js").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "workspace.css").read_text(encoding="utf-8")


def body_of(source: str, signature: str) -> str:
    """取某个顶层函数（两空格缩进）的函数体，用于按函数切片断言。"""
    match = re.search(re.escape(signature) + r"\s*\{(.*?)\n  \}", source, re.S)
    assert match, f"找不到函数体：{signature}"
    return match.group(1)


def code_only(source: str) -> str:
    """剥掉注释，只留可执行代码。

    「绝不出现清空」「不许拼 innerHTML」这类字面禁令，管的是用户看得见的菜单项与
    真正写进 DOM 的代码；注释里复述禁令不该被自己的探针打死。
    """
    return re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", source), flags=re.S)


class ScriptLayerTest(unittest.TestCase):
    """偏好层三个模块必须先于拖拽与舞台加载，且不引第三方依赖。"""

    def test_01_load_order(self) -> None:
        order = [
            HTML.index("/static/js/bus.js"),
            HTML.index("/static/js/prefs.js"),
            HTML.index("/static/js/dialogs.js"),
            HTML.index("/static/js/contextmenu.js"),
            HTML.index("/static/js/splitpane.js"),
            HTML.index("/static/js/stage.js"),
            HTML.index("/static/js/workspace.js"),
        ]
        self.assertEqual(order, sorted(order), "偏好层要在拖拽与舞台之前就位")

    def test_02_no_third_party_and_no_network(self) -> None:
        for source, name in ((PREFS_JS, "prefs.js"), (MENU_JS, "contextmenu.js"),
                             (DIALOG_JS, "dialogs.js")):
            for token in ("fetch(", "XMLHttpRequest", "localStorage.setItem", "require("):
                if name == "prefs.js" and token == "localStorage.setItem":
                    continue   # prefs.js 只写「已迁移」标记，这是宿主自己的浏览器存储
                self.assertNotIn(token, source, f"{name} 越界：{token}")

    def test_03_globals_are_namespaced(self) -> None:
        for source, name, global_name in (
            (PREFS_JS, "prefs.js", "JzoPrefs"),
            (MENU_JS, "contextmenu.js", "JzoMenu"),
            (DIALOG_JS, "dialogs.js", "JzoDialogs"),
        ):
            self.assertIn(f"window.{global_name} = ", source, f"{name} 没交出门面")


class LeftMenuTest(unittest.TestCase):
    """左栏右键＝新建文件夹、停用插件、重命名（+ 改组的可逆项）。"""

    def test_01_three_required_items(self) -> None:
        block = body_of(WORKSPACE_JS, "function wireSidebarMenu()")
        for label in ('"新建文件夹"', '"停用插件"', '"重命名"'):
            self.assertIn(label, block)

    def test_02_folder_items_are_reversible(self) -> None:
        block = body_of(WORKSPACE_JS, "function wireSidebarMenu()")
        self.assertIn('"解散文件夹"', block)
        self.assertIn('"移出文件夹"', block)
        self.assertIn("isFolderKey(key)", block)

    def test_03_the_write_goes_to_the_host_api(self) -> None:
        self.assertIn('postJson("/api/plugins/sidebar", { sidebar: next })',
                      body_of(WORKSPACE_JS, "function commitTree(next)"))
        self.assertIn('/nickname", { nickname: text })',
                      body_of(WORKSPACE_JS, "function renamePlugin(plugin, anchor)"))
        self.assertIn('/enabled", { enabled: false })',
                      body_of(WORKSPACE_JS, "function disablePlugin(plugin, anchor)"))

    def test_04_canvas_has_no_host_context_menu(self) -> None:
        # 全仓只允许两处宿主右键：左栏清单与底栏输出区。中栏画布一律不拦。
        self.assertEqual(WORKSPACE_JS.count('addEventListener("contextmenu"'), 2)
        self.assertNotIn('wsCanvasBody.addEventListener("contextmenu"', WORKSPACE_JS)
        self.assertNotIn('addEventListener("contextmenu"', STAGE_JS)


class DockMenuTest(unittest.TestCase):
    """底栏右键只提供复制，绝不提供清空（军令逐字）。"""

    def test_01_copy_only(self) -> None:
        block = code_only(body_of(WORKSPACE_JS, "function wireDockMenu()"))
        self.assertIn('"复制本条"', block)
        self.assertIn('"复制全部（当前视图）"', block)
        self.assertNotIn("清空", block, "底栏右键菜单项里不许出现清空")
        self.assertNotIn("dockClearBtn", block, "清空按钮本体不许进右键菜单")

    def test_02_clear_button_stays_out_of_the_menu(self) -> None:
        # 清空只归头部那颗按钮，且它不在右键菜单的构造路径上
        block = body_of(WORKSPACE_JS, "function wireDock()")
        self.assertIn("dockClearBtn", block)
        self.assertNotIn("JzoMenu", block)

    def test_03_double_click_copy_is_untouched(self) -> None:
        self.assertIn('dockLog.addEventListener("dblclick"', WORKSPACE_JS)
        self.assertIn('data-copy', WORKSPACE_JS)


class MenuLayerTest(unittest.TestCase):
    def test_01_menu_is_keyboard_reachable(self) -> None:
        self.assertIn('role', MENU_JS)
        self.assertIn('"menu"', MENU_JS)
        self.assertIn('menuitem', MENU_JS)
        self.assertIn('event.key === "Escape"', MENU_JS)
        self.assertIn("ArrowDown", MENU_JS)
        self.assertIn("owner.anchor", body_of(MENU_JS, "function closeMenu(restoreFocus)"))

    def test_02_menu_never_touches_innerhtml(self) -> None:
        for source, name in ((MENU_JS, "contextmenu.js"), (DIALOG_JS, "dialogs.js"),
                             (WORKSPACE_JS, "workspace.js"), (PREFS_JS, "prefs.js")):
            self.assertNotIn("innerHTML", code_only(source), f"{name} 的代码里出现 innerHTML")

    def test_03_dialog_has_focus_trap_and_esc(self) -> None:
        self.assertIn('aria-modal', DIALOG_JS)
        self.assertIn('event.key === "Escape"', DIALOG_JS)
        self.assertIn('event.key !== "Tab"', DIALOG_JS)
        self.assertIn("focusables", DIALOG_JS)

    def test_04_hit_area_is_44px(self) -> None:
        block = re.search(r"\.ws-menu-item\s*\{([^}]*)\}", CSS)
        self.assertIsNotNone(block)
        self.assertRegex(block.group(1), r"min-height:\s*44px")


class LegacyOrderTest(unittest.TestCase):
    """浏览器 localStorage 不再是左栏顺序的落点，只留一次性迁移。"""

    def test_01_order_helpers_are_retired(self) -> None:
        for token in ("PLUGIN_ORDER_KEY", "readPluginOrder", "savePluginOrder"):
            self.assertNotIn(token, WORKSPACE_JS)

    def test_02_migration_runs_once_and_only_when_the_tree_is_empty(self) -> None:
        block = body_of(WORKSPACE_JS, "function migrateLegacySidebar(data)")
        self.assertIn("if (legacyOrderMigrated || !window.JzoPrefs) return;", block)
        self.assertIn("legacyOrderMigrated = true;", block)
        self.assertIn("data.sidebar_customized", block)
        self.assertIn("JzoPrefs.legacyTree()", block)
        self.assertIn('"sidebar_customized": bool(sidebar)',
                      (ROOT / "app" / "core" / "plugins.py").read_text(encoding="utf-8"))

    def test_03_prefs_layer_carries_the_migration_keys(self) -> None:
        self.assertIn('var LEGACY_ORDER_KEY = "jzo.sidebar.order";', PREFS_JS)
        self.assertIn('var MIGRATED_KEY = "jzo.sidebar.migrated";', PREFS_JS)


class TreeAlgorithmsTest(unittest.TestCase):
    def test_01_folders_do_not_nest(self) -> None:
        block = body_of(PREFS_JS, "function moveEntry(tree, key, target)")
        self.assertIn('if (holder.extracted.kind === "folder" && mode === "into") mode = "after";', block)

    def test_02_empty_folders_disappear_on_extract(self) -> None:
        block = body_of(PREFS_JS, "function extract(rows, key)")
        self.assertIn('item.kind === "folder" && !item.children.length', block)

    def test_03_display_name_prefers_the_nickname(self) -> None:
        block = body_of(PREFS_JS, "function displayName(plugin)")
        self.assertIn("plugin.nickname", block)
        self.assertIn("未命名插件", block)

    def test_04_rel_time_is_computed_from_a_borrowed_now(self) -> None:
        """只在点开面板那一瞬算一次：基准由调用方传入，模块内部不许自取当前时间。"""
        block = body_of(PREFS_JS, "function relTime(iso, now)")
        self.assertIn("Number(now) || Date.now()", block)
        self.assertIn("for (var i = 0; i < units.length; i += 1)", block)


if __name__ == "__main__":
    unittest.main()
