# -*- coding: utf-8 -*-
"""单文件体积门禁（最高铁律【500行红线】/ 军令任务四、五）：巨无霸文件一律不许存在。

PLUGIN_SPEC §2.8.1 与根 ``AGENTS.md`` 的最高铁律都写死了「单文件不超过 500 行」，
光写在文档里守不住：录题插件曾经一份 plugin.js 冲到 5876 行。这个测试把红线变成机械判据，
覆盖四处：

1. 发行包内的 JS 与 CSS（``plugins/*/dist``）、底座静态资源（``static/js``、``static/css``）、
   模板插件（``examples/template-plugin``）——**每份都不许超过 500 行**；
2. 插件 ``dist`` 里的每个本地 JS/CSS 都必须被 ``index.html`` 引到，写了不引等于没发货；
   底座同样：``static/js``、``static/css`` 里的每一份都得有加载页引它（HostAssetWiringTest）；
3. 按 ``create(deps)`` 拆模块后，被依赖的命名空间必须**在加载次序里排在前面**，
   否则组合根执行时 ``window.Jzo*`` 还不存在，白屏都算轻的——插件与底座两条链都钉这条；
4. 底座 Python（``app/**``）同样 500 行封死——拆库时留下的教训：2226 行的
   ``app/core/bank.py`` 让契约测试无处下手。

``LEGACY_OVER_CEILING`` 是迁移冻结台账：本版之前已经超限的存量文件登记实测行数，
**只许减不许增**，拆分达标后必须从台账删除；任何不在台账里的文件越过 500 行直接判红。
这样既不让存量债把门禁逼回 800，也不为赶门禁在夜里盲拆大文件引入回归。

运行：``.venv/Scripts/python.exe -m unittest tests.test_file_size_contract``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from app.core import manifests  # noqa: E402
CEILING = 500
# 开发期脚本不在发行范围里，探针本身就是要一口气跑完一条链，不套 500 行。
DEV_ONLY = ("tools",)
# 存量超限冻结台账（路径 → 本版实测行数）。只减不增；达标即删行。
LEGACY_OVER_CEILING = {
    "plugins/org.jiuzhang.editor/dist/ui_ai_copilot.js": 800,
    "plugins/org.jiuzhang.editor/dist/plugin.js": 808,
    "plugins/org.jiuzhang.editor/dist/layout_canvas.css": 791,
    "plugins/org.jiuzhang.editor/dist/ui_batches.js": 795,
    "plugins/org.jiuzhang.editor/dist/ui_columns.js": 786,
    "app/core/pending_dedupe.py": 783,
    "plugins/org.jiuzhang.editor/dist/ui_split_board.js": 779,
    "app/core/pending_pool.py": 773,
    "plugins/org.jiuzhang.editor/dist/ui_crop.js": 771,
    "static/js/stage.js": 775,
    "static/css/settings.css": 748,
    "plugins/org.jiuzhang.editor/dist/layout.css": 746,
    "app/core/plugin_update.py": 742,
    "app/core/plugins.py": 729,
    "plugins/org.jiuzhang.paper-gen/dist/core_layout.js": 695,
    "static/js/stage_relay_io.js": 689,
    "app/core/pending_db.py": 676,
    "app/core/pending_bank.py": 631,
    "app/core/bank_schema.py": 624,
    "app/core/bank_write.py": 623,
    "plugins/org.jiuzhang.editor/dist/ui_intake.js": 595,
    "app/core/bank_query.py": 593,
    "static/js/st_workspace.js": 564,
    "plugins/org.jiuzhang.paper-gen/dist/plugin.css": 563,
    "app/core/dedupe_signature.py": 540,
    "static/js/stage_command.js": 540,
    "static/js/st_backup.js": 537,
    "app/core/restore.py": 532,
    "plugins/org.jiuzhang.editor/dist/ui_ai.js": 529,
    "plugins/org.jiuzhang.editor/dist/ui_school_dict.js": 521,
    "static/js/stage_frame.js": 521,
    "plugins/org.jiuzhang.paper-gen/dist/plugin.js": 520,
    "app/api/bank.py": 516,
    "plugins/org.jiuzhang.handout/dist/plugin.js": 515,
    "app/core/latex_style_dict.py": 506,
    "static/css/workspace.css": 504,
}


def lines_of(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def tracked(globs: tuple[str, ...]) -> list[Path]:
    out = []
    for pattern in globs:
        for path in ROOT.glob(pattern):
            if path.is_file():
                out.append(path)
    return sorted(out)


class ScriptSizeCeilingTest(unittest.TestCase):
    """发行资产（插件 dist、底座 static、模板插件）单文件不超 500 行。"""

    GLOBS = (
        "plugins/*/dist/**/*.js",
        "plugins/*/dist/**/*.css",
        "plugins/*/webui/**/*.js",
        "plugins/*/webui/**/*.css",
        "static/js/**/*.js",
        "static/css/**/*.css",
        "examples/template-plugin/**/dist/**/*.js",
        "examples/template-plugin/**/dist/**/*.css",
    )

    @staticmethod
    def violations(paths) -> list[str]:
        out = []
        for path in paths:
            count = lines_of(path)
            rel = path.relative_to(ROOT).as_posix()
            frozen = LEGACY_OVER_CEILING.get(rel)
            if frozen is None:
                if count > CEILING:
                    out.append(f"{rel}（{count} 行；新文件上限 {CEILING}）")
            elif count > frozen:
                out.append(f"{rel}（{count} 行；冻结上限 {frozen}，只许减不许增）")
        return out

    def test_01_no_oversized_ship_file(self) -> None:
        oversized = self.violations(tracked(self.GLOBS))
        self.assertEqual(
            oversized, [],
            "以下文件越过 500 行红线，按功能拆小再交：%s" % ", ".join(oversized))

    def test_02_no_oversized_host_python(self) -> None:
        oversized = self.violations(tracked(("app/**/*.py",)))
        self.assertEqual(
            oversized, [],
            "底座 Python 越过 500 行红线：[%s]" % ", ".join(oversized))

    def test_03_probe_scripts_are_dev_only(self) -> None:
        """开发期探针不参与门禁，但必须只待在 tools/ 里，不许混进发行目录。"""
        for path in ROOT.glob("plugins/**/tools/**/*.py"):
            self.fail(f"探针 {path} 混进了插件发行目录")
        for path in ROOT.glob("app/**/*probe*.py"):
            self.fail(f"探针 {path} 混进了底座")

    def test_04_legacy_ledger_stays_honest(self) -> None:
        """冻结台账只减不增：达标即删行，行数变了也要同步，防止拿旧额度偷偷长胖。"""
        stale = []
        for rel, frozen in sorted(LEGACY_OVER_CEILING.items()):
            path = ROOT / rel
            if not path.is_file():
                stale.append(f"{rel} 已不存在，删台账")
                continue
            count = lines_of(path)
            if count <= CEILING:
                stale.append(f"{rel} 已降到 {count} 行（≤{CEILING}），删台账")
            elif count != frozen:
                stale.append(f"{rel} 实测 {count} 行，与冻结值 {frozen} 不符，更新台账")
        self.assertEqual(stale, [], "存量台账失效：" + "；".join(stale))


class PluginAssetWiringTest(unittest.TestCase):
    """拆出去的模块必须真的被 index.html 加载，且加载次序满足依赖方向。"""

    NAMESPACE_RE = re.compile(r"global\.([A-Za-z_$][\w$]*) = \{ create")
    USE_RE = re.compile(r"window\.([A-Za-z_$][\w$]*)\.create")

    @staticmethod
    def local(src: str) -> Path:
        """``./plugin.js`` 与 ``plugin.js`` 是同一个文件；``/static/...`` 归底座。"""
        name = src[2:] if src.startswith("./") else src
        return (ROOT / "static" / name[len("/static/"):]) if name.startswith("/static/") \
            else None

    def plugins(self) -> list[Path]:
        return sorted(p for p in (ROOT / "plugins").iterdir() if p.is_dir() and manifests.manifest_path(p) is not None)

    @staticmethod
    def _entry(plugin: Path) -> Path:
        manifest = manifests.load_manifest(plugin)
        frontend = (manifest.get("entry") or {}).get("frontend") or "dist/index.html"
        return plugin / frontend

    def test_01_every_local_asset_is_loaded(self) -> None:
        for plugin in self.plugins():
            html = self._entry(plugin)
            if not html.is_file():
                continue
            text = html.read_text(encoding="utf-8")
            listed = {v[2:] if v.startswith("./") else v for v in
                      re.findall(r'<script src="([^"]+)"', text)
                      + re.findall(r'<link rel="stylesheet" href="([^"]+)"', text)}
            for asset in sorted(html.parent.glob("*.*")):
                if asset.suffix not in (".js", ".css") or asset == html:
                    continue
                self.assertIn(
                    asset.name, listed,
                    f"{asset.name} 在入口目录里却没人加载——要么写进 index.html，要么删掉")

    def test_02_namespace_defined_before_first_use(self) -> None:
        for plugin in self.plugins():
            html = self._entry(plugin)
            if not html.is_file():
                continue
            raw = re.findall(r'<script src="([^"]+)"', html.read_text(encoding="utf-8"))
            order = [s[2:] if s.startswith("./") else s for s in raw]
            seq = {}
            for pos, src in enumerate(order):
                path = self.local(src) or html.parent / src
                if not path.is_file():
                    continue
                for name in self.NAMESPACE_RE.findall(path.read_text(encoding="utf-8")):
                    seq.setdefault(name, pos)
            for pos, src in enumerate(order):
                path = self.local(src) or html.parent / src
                if not path.is_file():
                    continue
                for name in self.USE_RE.findall(path.read_text(encoding="utf-8")):
                    if name not in seq:
                        continue  # 别的插件/宿主提供的命名空间不在本包检查范围
                    self.assertLess(
                        seq[name], pos,
                        f"{name} 在 {src} 使用时还没定义：加载次序要调整")


class HostAssetWiringTest(unittest.TestCase):
    """底座拆出去的模块同样要挂在页面上，且命名空间先定义后使用（PLUGIN_SPEC §2.8.3）。

    军令任务四把 stage.js / settings.js / workspace.js 也按功能拆开了，
    光有 800 行门禁守不住「新文件写了没挂」和「挂在用它的脚本之后」这两件事。
    """

    PAGES = ("static/index.html", "static/workspace.html", "static/settings.html", "static/plugins.html")

    def page_assets(self) -> tuple[set, list]:
        listed = set()
        order = []
        for page in self.PAGES:
            text = (ROOT / page).read_text(encoding="utf-8")
            listed |= set(re.findall(r'<script src="/static/js/([^"]+)"', text))
            listed |= set(re.findall(r'<link rel="stylesheet" href="/static/css/([^"]+)"', text))
            order.append([s for s in re.findall(r'<script src="/static/js/([^"]+)"', text)])
        return listed, order

    def test_01_every_host_asset_is_loaded(self) -> None:
        listed, _ = self.page_assets()
        for folder in ("js", "css"):
            for asset in sorted((ROOT / "static" / folder).glob("*." + folder)):
                self.assertIn(
                    asset.name, listed,
                    f"{asset.name} 躺在 static/{folder} 里却没有页面加载它")

    def test_02_namespace_defined_before_first_use(self) -> None:
        _, orders = self.page_assets()
        for order in orders:
            seq = {}
            for pos, name in enumerate(order):
                path = ROOT / "static" / "js" / name
                if not path.is_file():
                    continue
                for ns in PluginAssetWiringTest.NAMESPACE_RE.findall(path.read_text(encoding="utf-8")):
                    seq.setdefault(ns, pos)
            for pos, name in enumerate(order):
                path = ROOT / "static" / "js" / name
                if not path.is_file():
                    continue
                for ns in PluginAssetWiringTest.USE_RE.findall(path.read_text(encoding="utf-8")):
                    if ns not in seq:
                        continue  # vendor 与页面内联脚本提供的命名空间不在本包检查范围
                    self.assertLess(
                        seq[ns], pos,
                        f"{ns} 在 {name} 使用时还没定义：加载页的脚本次序要调整")


if __name__ == "__main__":
    unittest.main()
