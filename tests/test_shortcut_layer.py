"""军令 #16 模块一契约：全局快捷键、右键菜单与输入铁律。

三条口径逐条钉住（都只钉结构，不启浏览器；真机证据走探针）：

1. **输入铁律**——聊天/输入框统一 Enter 换行、Ctrl+Enter 发送；单行搜索框不是聊天框，
   保留 Enter 检索（同一次按键两种写法都接受）；
2. **右键菜单感应**——左栏给新建文件夹/停用插件/重命名，底栏只给复制且**绝不给清空**，
   中间画布一个监听都不挂（右键完全交给插件）；
3. **快捷键冲突与优先级**——键位全部可自定义；装配时底座动作先占位，
   插件自报键位撞上即作废，并逐条写进【报错诊断】红字（该视图本就支持双击复制）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_shortcut_layer``
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
KEYS_JS = (STATIC / "js" / "shortcuts.js").read_text(encoding="utf-8")
MENU_JS = (STATIC / "js" / "contextmenu.js").read_text(encoding="utf-8")
DIALOG_JS = (STATIC / "js" / "dialogs.js").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "workspace.css").read_text(encoding="utf-8")
CHAT_JS = (ROOT / "plugins" / "org.jiuzhang.chat" / "dist" / "plugin.js").read_text(
    encoding="utf-8"
)
CHAT_HTML = (ROOT / "plugins" / "org.jiuzhang.chat" / "dist" / "index.html").read_text(
    encoding="utf-8"
)
CHAT_JSON = (ROOT / "plugins" / "org.jiuzhang.chat" / "plugin.json").read_text(
    encoding="utf-8"
)


def body_of(source: str, signature: str) -> str:
    """取某个顶层函数（两空格缩进）的函数体，用于按函数切片断言。"""
    match = re.search(re.escape(signature) + r"\s*\{(.*?)\n  \}", source, re.S)
    assert match, f"找不到函数体：{signature}"
    return match.group(1)


def handler_body(source: str, signature: str) -> str:
    """取回调式监听器（四空格缩进闭合）的函数体。"""
    match = re.search(re.escape(signature) + r"\s*\{(.*?)\n    \}\);", source, re.S)
    assert match, f"找不到回调体：{signature}"
    return match.group(1)


def code_only(source: str) -> str:
    """剥掉注释，只留可执行代码。

    「绝不出现清空」「不许拼 innerHTML」这类字面禁令，管的是用户看得见的菜单项与
    真正写进 DOM 的代码；注释里复述禁令不该被自己的探针打死。
    """
    return re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", source), flags=re.S)


class ScriptLayerTest(unittest.TestCase):
    """偏好层四个模块必须先于拖拽与舞台加载，且不引第三方依赖。"""

    def test_01_load_order(self) -> None:
        order = [
            HTML.index("/static/js/bus.js"),
            HTML.index("/static/js/prefs.js"),
            HTML.index("/static/js/dialogs.js"),
            HTML.index("/static/js/contextmenu.js"),
            HTML.index("/static/js/shortcuts.js"),
            HTML.index("/static/js/splitpane.js"),
            HTML.index("/static/js/stage.js"),
            HTML.index("/static/js/workspace.js"),
        ]
        self.assertEqual(order, sorted(order), "偏好层要在拖拽与舞台之前就位")

    def test_02_no_third_party_and_no_network(self) -> None:
        for source, name in ((PREFS_JS, "prefs.js"), (KEYS_JS, "shortcuts.js"),
                             (MENU_JS, "contextmenu.js"), (DIALOG_JS, "dialogs.js")):
            for token in ("fetch(", "XMLHttpRequest", "localStorage.setItem", "require("):
                if name == "prefs.js" and token == "localStorage.setItem":
                    continue   # prefs.js 只写「已迁移」标记，这是宿主自己的浏览器存储
                self.assertNotIn(token, source, f"{name} 越界：{token}")

    def test_03_globals_are_namespaced(self) -> None:
        for source, name, global_name in (
            (PREFS_JS, "prefs.js", "JzoPrefs"),
            (KEYS_JS, "shortcuts.js", "JzoKeys"),
            (MENU_JS, "contextmenu.js", "JzoMenu"),
            (DIALOG_JS, "dialogs.js", "JzoDialogs"),
        ):
            self.assertIn(f"window.{global_name} = ", source, f"{name} 没交出门面")


class CanonicalComboTest(unittest.TestCase):
    """前端与后端同一口径：至少一枚修饰键 + 一枚主键，裸键不进快捷键表。"""

    def test_01_bare_keys_are_not_shortcuts(self) -> None:
        self.assertIn("if (!key || !modifiers.length) return \"\";", PREFS_JS)
        self.assertIn("if (!modifiers.length) return \"\";",
                       body_of(PREFS_JS, "function comboFromEvent(event)"))

    def test_02_modifier_order_is_fixed(self) -> None:
        block = body_of(PREFS_JS, "function canonicalCombo(raw)")
        self.assertIn('var ordered = MODIFIER_ORDER.filter', block)
        self.assertIn('["Ctrl", "Alt", "Shift", "Meta"]', PREFS_JS)

    def test_03_backend_and_frontend_share_the_shape(self) -> None:
        # 后端 canonical_combo 是唯一裁决口，前端只是当场反馈，两边键集必须同源口径
        self.assertIn("def canonical_combo(", (ROOT / "app" / "core" / "plugin_state.py").read_text(encoding="utf-8"))
        self.assertIn("_COMBO_RE", (ROOT / "app" / "core" / "plugin_state.py").read_text(encoding="utf-8"))
        self.assertIn("COMBO.test(combo)", PREFS_JS)


class HostKeyArbitrationTest(unittest.TestCase):
    """底座最高权限优先：装配顺序就是权重顺序，插件撞车即作废。"""

    def test_01_host_actions_are_declared(self) -> None:
        for action in ("sidebar.toggle", "context.toggle", "dock.toggle",
                       "assistant.focus", "console.open"):
            self.assertIn(f'action: "{action}"', KEYS_JS)
        self.assertIn("Ctrl+B", KEYS_JS, "军令逐字：全屏时按 Ctrl+B 呼叫左侧栏")

    def test_02_host_claims_before_plugins(self) -> None:
        block = body_of(KEYS_JS, "function collect(plugins)")
        self.assertIn("var owner = ownerOf(combo);", block)
        self.assertIn("conflicts.push({", block)
        self.assertIn("pluginRows.push({", block)
        # 撞上已占位的键位：只记冲突，绝不注册（不存在“静音共存”）
        self.assertLess(block.index("conflicts.push"), block.index("pluginRows.push"))

    def test_03_conflict_carries_the_owner_for_the_error_line(self) -> None:
        block = body_of(KEYS_JS, "function collect(plugins)")
        self.assertIn("takenBy: owner.owner === \"host\" ? \"底座动作 \"", block)
        self.assertIn("takenAction: owner.action", block)

    def test_04_press_is_the_sandbox_path(self) -> None:
        block = body_of(KEYS_JS, "function press(combo)")
        self.assertIn("BAD_COMBO", block)
        self.assertIn("UNBOUND", block)
        self.assertIn("owner: \"host\"", block)

    def test_05_listener_is_installed_once_in_capture(self) -> None:
        block = body_of(KEYS_JS, "function install(options)")
        self.assertIn("if (installed) return;", block)
        self.assertIn('document.addEventListener("keydown"', block)
        self.assertTrue(block.rstrip().endswith(", true);"), "必须 capture：输入框先吃掉冒泡阶段的键")

    def test_06_menu_and_dialog_hold_the_keys(self) -> None:
        block = body_of(KEYS_JS, "function dispatch(event)")
        self.assertIn("JzoMenu.isOpen()", block)
        self.assertIn("JzoDialogs.isOpen()", block)
        self.assertIn("event.repeat", block, "按住不放不许连发底座动作")


class HostKeyWiringTest(unittest.TestCase):
    """workspace.js 把五个底座动作接上执行体，并把裁决结果如实播报。"""

    def test_01_every_host_action_has_a_runner(self) -> None:
        block = body_of(WORKSPACE_JS, "function wireShortcuts()")
        for action in ("sidebar.toggle", "context.toggle", "dock.toggle",
                       "assistant.focus", "console.open"):
            self.assertIn(f'defineHost("{action}"', block)
        self.assertIn("JzoKeys.install", block)

    def test_02_assemble_and_collect_run_on_every_listing(self) -> None:
        block = body_of(WORKSPACE_JS, "function applyPrefsLayer(data, plugins)")
        self.assertIn("assemble((data && data.shortcuts) || {})", block)
        self.assertIn("reportConflicts(window.JzoKeys.collect(plugins))", block)
        self.assertIn("applyPrefsLayer(data, plugins)", WORKSPACE_JS)

    def test_03_conflicts_land_in_error_view_as_red_lines(self) -> None:
        block = body_of(WORKSPACE_JS, "function reportConflicts(list)")
        self.assertIn('"shortcut.conflict", "error")', block)
        self.assertIn("底座已禁用该键位", block)
        # 清单每 5 秒轮询一次：同一批冲突只播一次
        self.assertIn("if (signature === lastConflictSignature) return;", block)

    def test_04_plugin_keys_are_delivered_not_executed(self) -> None:
        block = body_of(WORKSPACE_JS, "function deliverShortcut(pluginId, info)")
        self.assertIn('notifyPlugin(pluginId, "shortcut.invoke"', block)
        self.assertNotIn("eval(", block)
        self.assertNotIn("document.querySelector", block, "宿主不替插件点它的按钮")

    def test_05_stage_exposes_relay_and_direct_delivery(self) -> None:
        self.assertIn('"shortcut.press"', STAGE_JS)
        block = body_of(STAGE_JS, 'if (method === "shortcut.press")')
        self.assertNotIn("block", block)   # 占位：见下方显式断言
        self.assertIn("JzoKeys.press(", STAGE_JS)
        self.assertIn("notifyPlugin: function (pluginId, event, payload)", STAGE_JS)


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


class InputIronRuleTest(unittest.TestCase):
    """聊天框：Enter 换行、Ctrl+Enter 发送。"""

    def test_01_bare_enter_no_longer_sends(self) -> None:
        self.assertNotIn('event.key === "Enter" && !event.shiftKey', CHAT_JS)
        self.assertNotIn('if (event.key === "Enter" && !event.shiftKey) {', CHAT_JS)

    def test_02_ctrl_enter_sends_through_the_same_exit(self) -> None:
        block = handler_body(
            CHAT_JS, 'promptInput.addEventListener("keydown", function (event)'
        )
        self.assertIn('if (event.key !== "Enter") return;', block)
        self.assertIn("if (event.ctrlKey || event.metaKey) {", block)
        self.assertIn("submitFromComposer();", block, "发送只能走同一个出口")
        self.assertNotIn("if (event.shiftKey)", block, "裸 Enter 就是换行，不许再被拦截")

    def test_03_placeholder_tells_the_rule(self) -> None:
        self.assertIn("Enter 换行", CHAT_HTML)
        self.assertIn("Ctrl+Enter 发送", CHAT_HTML)

    def test_04_plugin_declares_and_forwards_its_own_key(self) -> None:
        self.assertIn('"chat.focus"', CHAT_JSON)
        self.assertIn("Ctrl+Shift+K", CHAT_JSON)
        self.assertIn('MY_KEYS = { "Ctrl+Shift+K": "chat.focus" }', CHAT_JS)
        self.assertIn('hostCall("shortcut.press", { combo: combo }', CHAT_JS)
        self.assertIn('message.event === "shortcut.invoke"', CHAT_JS)
        # 插件不许自称执行底座的动作：只认 owner === "plugin"
        self.assertIn('verdict.owner === "plugin"', CHAT_JS)

    def test_05_single_line_search_boxes_keep_enter(self) -> None:
        """口径：铁律管的是聊天/多行输入框；单行搜索框 Enter 即检索，仍照常接受。"""
        for name in ("org.jiuzhang.core-bank", "org.jiuzhang.bank-browser"):
            source = (ROOT / "plugins" / name / "dist" / "plugin.js").read_text(encoding="utf-8")
            self.assertIn('event.key === "Enter"', source, f"{name} 的单行搜索丢了 Enter 检索")


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
