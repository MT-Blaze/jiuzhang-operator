"""军令 #16 模块二契约：控制台插件面板的显示、排序与时间口径。

只钉结构与口径（不启浏览器，真机证据走 tools/console_probe.py）：

1. **大字昵称 / 小字官方原名**，且**坚决不设「恢复默认名」按钮**；
2. 列表**平铺不折叠**，分组只以卡片尾部小标签出现；
3. 「已启用」顺序与左栏导航读**同一棵后端树**，「已停用」按停用时间先后排；
4. 相对时间**只在渲染那一瞬算一次**，全页不许有定时器；
5. 底座键位在系统设置里逐条可改绑/回到默认，走同一个写口，不另存一份默认值。

运行：``.venv/Scripts/python.exe -m unittest tests.test_console_plugin_panel``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
HTML = (STATIC / "settings.html").read_text(encoding="utf-8")
JS = (STATIC / "js" / "settings.js").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "settings.css").read_text(encoding="utf-8")
PREFS_JS = (STATIC / "js" / "prefs.js").read_text(encoding="utf-8")
WORKSPACE_JS = (STATIC / "js" / "workspace.js").read_text(encoding="utf-8")


def body_of(source: str, signature: str) -> str:
    """取某个顶层函数（两空格缩进）的函数体，用于按函数切片断言。"""
    match = re.search(re.escape(signature) + r"\s*\{(.*?)\n  \}", source, re.S)
    assert match, f"找不到函数体：{signature}"
    return match.group(1)


class NicknameCardTest(unittest.TestCase):
    """大字只属于昵称，小字才是官方原名与版本。"""

    def test_01_big_name_is_display_name(self) -> None:
        block = body_of(JS, "function renderInstalled(plugins, body)")
        self.assertIn("window.JzoPrefs.displayName(plugin)", block, "大字没走昵称优先的口径")
        self.assertIn('el("span", "mg-card-name"', block)

    def test_02_official_name_and_version_share_the_small_line(self) -> None:
        block = body_of(JS, "function renderInstalled(plugins, body)")
        self.assertIn("官方原名：", block)
        self.assertIn('mg-card-official', block)
        self.assertIn('plugin.version', block)

    def test_03_no_restore_default_button_anywhere(self) -> None:
        """军令逐字：坚决不设「恢复默认名」按钮——连这个词都不许出现在控制台。"""
        for text, name in ((JS, "settings.js"), (HTML, "settings.html"), (CSS, "settings.css")):
            self.assertNotIn("恢复默认名", text, f"{name} 出现了被禁的按钮文案")

    def test_04_rename_goes_through_the_same_host_api(self) -> None:
        block = body_of(JS, "function setNickname(plugin, nickname)")
        self.assertIn('/nickname", "POST"', block)
        self.assertIn("{ nickname: nickname }", block)
        self.assertIn("tellWorkspacePrefs()", block, "改完昵称左栏要当场跟上")


class FlatListTest(unittest.TestCase):
    """平铺不折叠：一屏出全部卡片，分组只是尾部小标签。"""

    def test_01_one_loop_renders_every_card(self) -> None:
        block = body_of(JS, "function renderInstalled(plugins, body)")
        self.assertEqual(block.count("mgList.appendChild(li)"), 1)
        self.assertIn("ordered.forEach(function (plugin)", block)
        self.assertNotIn("<details", block)
        self.assertNotIn("collapsed", block, "控制台不许自己造折叠态")

    def test_02_folder_shows_as_tail_tag(self) -> None:
        block = body_of(JS, "function renderInstalled(plugins, body)")
        self.assertIn("folderKeyOf(tree", block)
        self.assertIn("folderName(tree, homeKey)", block)
        self.assertIn("mg-tag-folder", block)
        self.assertIn('"未分组"', block, "没分组也要明说，不留猜谜空间")
        self.assertRegex(CSS, r"\.mg-tag-folder\s*\{[^}]*margin-left:\s*auto")

    def test_03_html_has_no_folding_container(self) -> None:
        manage = HTML.split('id="stPluginPanelManage"', 1)[1].split('id="stPluginPanelUpdate"', 1)[0]
        self.assertIn('id="mgList"', manage)
        self.assertNotIn("<details", manage)


class OrderTest(unittest.TestCase):
    """绝对排序：已启用对齐左栏，已停用按停用时间先后。"""

    def test_01_enabled_order_reads_the_same_backend_tree(self) -> None:
        block = body_of(JS, "function renderInstalled(plugins, body)")
        self.assertIn("window.JzoPrefs.readTree(body)", block)
        self.assertIn("enabledFirst(plugins, tree)", block)
        flat = body_of(JS, "function flattenTree(tree)")
        self.assertIn('item.kind === "folder"', flat)
        self.assertIn("item.children.forEach", flat, "文件夹要摊平成左栏的可见顺序")

    def test_02_enabled_before_disabled_and_nothing_lost(self) -> None:
        block = body_of(JS, "function renderInstalled(plugins, body)")
        self.assertIn(".concat(disabledByTime(plugins))", block)
        enabled = body_of(JS, "function enabledFirst(plugins, tree)")
        self.assertIn("plugin.enabled === false", enabled, "已启用段要把停用的剔出去")
        self.assertIn("ordered.indexOf(plugin) < 0", enabled, "树上没有的新插件要补在末尾而不是插队")

    def test_03_disabled_sorted_by_time_with_unknown_last(self) -> None:
        block = body_of(JS, "function disabledByTime(plugins)")
        self.assertIn("Date.parse(a.disabled_at", block)
        self.assertIn("Number.MAX_SAFE_INTEGER", block, "没记下时间的排最后")
        self.assertIn("plugin.enabled === false", block)

    def test_04_disabled_card_shows_relative_time(self) -> None:
        block = body_of(JS, "function renderInstalled(plugins, body)")
        self.assertIn("relTime(plugin.disabled_at, now)", block)
        self.assertIn("本机未记录", block)


class RelativeTimeTest(unittest.TestCase):
    """GitHub 相对时间：只在点开面板那一瞬算一次，绝不后台跑。"""

    def test_01_single_now_per_render(self) -> None:
        block = body_of(JS, "function renderInstalled(plugins, body)")
        self.assertIn("var now = new Date();", block)
        self.assertEqual(block.count("new Date("), 1, "一次渲染只取一次当前时间")

    def test_02_no_wall_clock_timer_anywhere(self) -> None:
        # setTimeout 只允许出现在「等底座重启」与「回收 blob」这类一次性延时里，
        # 周期性的墙钟定时器才是「后台实时跑」，一个都不许有。
        for token in ("setInterval", "requestAnimationFrame"):
            self.assertNotIn(token, JS, f"控制台用了 {token}，相对时间会变成后台实时跑")
        render = body_of(JS, "function renderInstalled(plugins, body)")
        self.assertNotIn("setTimeout", render, "渲染函数自己不许排任何延时")

    def test_03_rel_time_units_are_github_calibre(self) -> None:
        block = body_of(PREFS_JS, "function relTime(iso, now)")
        self.assertIn("刚刚", block)
        for unit in ("分钟", "小时", "天", "周", "月", "年"):
            self.assertIn(f'"{unit}"', block)
        self.assertIn("base - then", block, "基准必须由调用方传入，才谈得上算一次")


class ShortcutCustomisationTest(unittest.TestCase):
    """模块一欠的账记在模块二还：底座键位在系统设置里逐条可改。"""

    def test_01_section_exists_with_status_and_list(self) -> None:
        self.assertIn('id="keyList"', HTML)
        self.assertIn('id="keyStatus"', HTML)
        self.assertIn("全局快捷键", HTML)
        self.assertIn('role="status" aria-live="polite"', HTML.split('id="keyStatus"', 1)[1][:80])

    def test_02_catalogue_is_not_duplicated_into_settings(self) -> None:
        block = body_of(JS, "function renderShortcuts(body)")
        self.assertIn("window.JzoKeys.catalogue()", block, "键位表只许有 shortcuts.js 那一份")
        self.assertNotIn("sidebar.toggle", block, "这里不许再抄一遍 action 名")

    def test_03_write_goes_through_the_single_endpoint(self) -> None:
        block = body_of(JS, "function saveShortcut(action, combo, button)")
        self.assertIn('apiCall("/api/plugins/shortcuts", "POST"', block)
        self.assertIn("{ action: action, combo: combo }", block)
        self.assertIn('"aria-busy"', block, "写操作中的按钮必须同步 aria-busy（AGENTS §6）")

    def test_04_plugin_declared_keys_are_visible_but_readonly(self) -> None:
        block = body_of(JS, "function renderShortcuts(body)")
        self.assertIn("plugin.shortcuts", block)
        self.assertIn("撞车时底座动作优先", JS)

    def test_05_hit_areas_and_scripts_loaded(self) -> None:
        self.assertRegex(CSS, r"\.key-input\s*\{[^}]*min-height:\s*44px")
        self.assertRegex(CSS, r"\.key-row \.q-button\s*\{[^}]*min-height:\s*44px")
        self.assertIn("/static/js/prefs.js", HTML)
        self.assertIn("/static/js/shortcuts.js", HTML)
        self.assertLess(HTML.index("/static/js/prefs.js"), HTML.index("/static/js/settings.js"))


class LiveSyncTest(unittest.TestCase):
    """控制台改完偏好，工作台必须当场跟上，而不是等下一次轮询。"""

    def test_01_settings_announces_pref_changes(self) -> None:
        block = body_of(JS, "function tellWorkspacePrefs()")
        self.assertIn('jzo: "prefs.changed"', block)
        self.assertIn("window.location.origin", block, "同源定向投递，不许用 *")
        self.assertEqual(JS.count("tellWorkspacePrefs()"), 4, "昵称/启停/键位三处写口加函数本体")

    def test_02_workspace_reloads_the_left_rail_on_message(self) -> None:
        self.assertIn('data.jzo === "prefs.changed"', WORKSPACE_JS)
        listener = WORKSPACE_JS.split('data.jzo === "prefs.changed"', 1)[1].split("\n", 1)[0]
        self.assertIn("loadPlugins(", listener)


class SafetyTest(unittest.TestCase):
    def test_01_no_innerhtml_in_console_layer(self) -> None:
        self.assertNotIn("innerHTML", JS)
        self.assertNotIn("innerHTML", PREFS_JS)

    def test_02_text_only_helpers_still_used(self) -> None:
        self.assertIn("function el(tag, className, text)", JS)
        self.assertIn("textContent", body_of(JS, "function renderInstalled(plugins, body)"))


if __name__ == "__main__":
    unittest.main()
