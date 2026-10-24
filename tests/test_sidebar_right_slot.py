"""右栏辅助面板（sidebar.right）契约：军令 #13 任务 3 + 军令 #15 任务 4。

三件事必须同时成立，右栏才算「插件化」而不是换个地方写死：
1. 清单侧：``slots`` 接受 ``sidebar.right``，未知插槽照旧拒装；
2. 宿主侧：右栏默认由助手插件（org.jiuzhang.chat）入住；当前画布页签的插件自己声明
   ``sidebar.right`` 时暂时接管，切走或关掉就归还助手——底座不再自带副驾对话；
3. 数据侧：面板 iframe 与画布页签共用同一套 Host API 转发（写令牌不落插件手里）。

运行：``.venv/Scripts/python.exe -m unittest tests.test_sidebar_right_slot``
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from app.api.plugins import InstalledPlugin
from app.core.plugins import PluginRejected, validate_plugin

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "workspace.html").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "css" / "workspace.css").read_text(encoding="utf-8")
STAGE_JS = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
PANEL_JS = (ROOT / "static" / "js" / "context_panel.js").read_text(encoding="utf-8")
WORKSPACE_JS = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")
SPEC = (ROOT / "PLUGIN_SPEC.md").read_text(encoding="utf-8")

PLUGIN_ID = "com.example.side-probe"

BASE_MANIFEST = {
    "schema_version": "1.0",
    "id": PLUGIN_ID,
    "name": "右栏契约探针",
    "version": "1.0.0",
    "api_version": "1.0",
    "kind": "renderer",
    "description": "只用于右栏插槽校验的最小插件",
    "license": "Apache-2.0",
    "entry": {"frontend": "dist/index.html"},
    "slots": ["sidebar.right"],
    "capabilities": ["question.render"],
    "permissions": ["questions:read"],
}


def build_plugin_dir(root: Path, manifest: dict) -> Path:
    plugin_dir = root / manifest["id"]
    (plugin_dir / "dist").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "LICENSE").write_text("Apache License 2.0 (fixture)", encoding="utf-8")
    (plugin_dir / "dist" / "index.html").write_text("<!doctype html><title>p</title>", encoding="utf-8")
    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return plugin_dir


class ManifestSlotTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def validate(self, **overrides) -> dict:
        manifest = json.loads(json.dumps(BASE_MANIFEST))
        manifest.update(overrides)
        return validate_plugin(build_plugin_dir(self.root, manifest), manifest)

    def test_01_sidebar_right_is_accepted(self) -> None:
        info = self.validate()
        self.assertEqual(info["slots"], ["sidebar.right"])

    def test_02_sidebar_right_needs_no_stage_declaration(self) -> None:
        info = self.validate()
        self.assertIsNone(info["stage"], "右栏面板不该被逼着认领中央舞台")

    def test_03_combined_with_stage_slot_is_allowed(self) -> None:
        info = self.validate(slots=["sidebar.right", "stage.center"])
        self.assertEqual(info["stage"]["mode"], "embed")

    def test_04_typo_slot_is_still_rejected(self) -> None:
        with self.assertRaises(PluginRejected) as caught:
            self.validate(slots=["sidebar.left"])
        self.assertIn("slots", str(caught.exception))

    def test_05_api_model_exposes_slots(self) -> None:
        self.assertIn("slots", InstalledPlugin.model_fields)


class HostSlotTest(unittest.TestCase):
    def test_01_right_sidebar_has_a_dedicated_slot(self) -> None:
        self.assertIn('id="wsContextSlot"', HTML)
        self.assertIn('id="wsContextSlotBody"', HTML)
        self.assertIn('id="wsContextSlotTitle"', HTML)

    def test_02_right_slot_is_visible_by_default_and_host_copilot_is_gone(self) -> None:
        """军令 #15 任务 4：右栏默认不折叠、默认住助手插件。

        底座自带的 AI 副驾（wsCopilot）必须一起删掉——右栏再留一份宿主私有对话，
        等于给 AI 开一条不经 Host API 的后门（任务 1）。
        """
        slot = re.search(r'<section[^>]*id="wsContextSlot"[^>]*>', HTML).group(0)
        self.assertNotIn("hidden", slot, "右栏默认必须展开，否则开场就是折叠态")
        self.assertNotIn('id="wsCopilot"', HTML, "宿主私有副驾已随对话一起插件化")
        self.assertIn('id="wsContextSlotBadge"', HTML, "主权归属要在标题上看得见")

    def test_03_panel_script_is_loaded_after_stage(self) -> None:
        stage_at = HTML.index("/static/js/stage.js")
        panel_at = HTML.index("/static/js/context_panel.js")
        workspace_at = HTML.index("/static/js/workspace.js")
        self.assertLess(stage_at, panel_at, "面板要复用 stage 的 Host API 转发，必须先于它加载")
        self.assertLess(panel_at, workspace_at, "workspace 刷新清单时要叫得动 JzoContextPanel")

    def test_04_plugin_list_refresh_reruns_the_slot(self) -> None:
        # 主权交替后 sync 多带一个「当前画布页签」参数，插槽才知道该归谁
        self.assertIn("JzoContextPanel.sync(installedPlugins, activeCanvasPluginId)", WORKSPACE_JS)
        self.assertIn("stage.tab.activated", WORKSPACE_JS, "页签换主人必须驱动右栏对账")
        self.assertIn("stage.tab.closed", WORKSPACE_JS, "关掉页签后主权要归还助手")

    def test_05_panel_frame_is_sandboxed(self) -> None:
        sandbox = re.search(r'var SANDBOX = "([^"]+)"', PANEL_JS).group(1)
        self.assertEqual(sandbox, "allow-scripts allow-modals")
        self.assertIn('frame.setAttribute("sandbox", SANDBOX)', PANEL_JS)
        self.assertNotIn("allow-same-origin", sandbox, "插件面板不得同时开 allow-same-origin")

    def test_06_panel_activates_on_the_right_slot(self) -> None:
        self.assertIn('var SLOT = "sidebar.right"', PANEL_JS)
        self.assertIn('handle.request("plugin.activate", { slot: SLOT })', PANEL_JS)

    def test_07_panel_falls_back_when_activation_fails(self) -> None:
        self.assertIn("showFallback()", PANEL_JS)
        self.assertIn("context.panel.error", PANEL_JS)
        self.assertRegex(PANEL_JS, r"unmount\(\);\s*\n\s*showFallback\(\);")

    def test_08_only_one_panel_at_a_time(self) -> None:
        self.assertIn("return usable(plugin) ? plugin : null", PANEL_JS)
        self.assertIn("enabled !== false", PANEL_JS, "停用的插件不许继续占右栏")
        # 换主人前先 unmount：插槽里同一时刻只能有一个 iframe
        self.assertRegex(PANEL_JS, r"unmount\(\);\s*\n\s*if \(!window\.JzoStage")

    def test_09_stage_forwards_host_api_for_panels(self) -> None:
        self.assertIn("function attachPanel(frame, plugin)", STAGE_JS)
        self.assertIn("attachPanel: attachPanel", STAGE_JS)
        self.assertIn("panels[p].frame.contentWindow === event.source", STAGE_JS)
        self.assertIn("panels.push(handle)", STAGE_JS)

    def test_10_panel_css_lets_the_slot_scroll(self) -> None:
        self.assertIn(".ws-context-slot-body", CSS)
        self.assertRegex(CSS, r"\.ws-context-slot-body\s*\{[^}]*min-height:\s*300px")
        self.assertRegex(CSS, r"\.ws-context-frame\s*\{[^}]*height:\s*100%")

    def test_11_spec_documents_the_slot(self) -> None:
        self.assertIn("`sidebar.right`", SPEC)
        self.assertIn("### 2.9 右栏辅助面板", SPEC)
        self.assertIn("`region.right`", SPEC)

    def test_12_sovereignty_follows_only_the_active_canvas_tab(self) -> None:
        """接管者只认「当前画布页签」那一个插件，不是所有声明了槽的插件。"""
        self.assertIn("function claimant(plugins, activePluginId)", PANEL_JS)
        self.assertIn(
            "if (!activePluginId || activePluginId === ASSISTANT_PLUGIN_ID) return null",
            PANEL_JS,
        )

    def test_13_assistant_is_the_default_resident(self) -> None:
        """军令 #15 任务 4：右栏默认住户是助手插件，切走业务页签就归还它。"""
        self.assertIn('var ASSISTANT_PLUGIN_ID = "org.jiuzhang.chat"', PANEL_JS)
        self.assertIn("assistant.chat", PANEL_JS)
        self.assertIn("function reclaim()", PANEL_JS)

    def test_14_no_claimant_gives_a_readable_note_not_a_blank(self) -> None:
        self.assertIn('className = "ws-context-slot-note"', PANEL_JS)
        self.assertIn("slotEl.hidden = false", PANEL_JS)
        self.assertNotIn("copilotEl", PANEL_JS, "兜底不许再回到宿主私有副驾那条捷径")


if __name__ == "__main__":
    unittest.main()
