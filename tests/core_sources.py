"""底座与模板源码的「微内核 + 组合根」拼接读取（军令 #30 拆解后）。

舞台、工作台、设置页都按各自加载页的 <script> 次序拆成了微内核，切片清单不再手写，
一律从页面上现读——页面一改，判据跟着改，不会出现「测试还在拼五个早就不存在的文件」：

    workspace.html: core_bus → core_tabs → stage_* → stage.js
    workspace.html: core_log → ws_* → workspace.js
    settings.html:  st_* → settings.js

examples/template-plugin 是模块化多文件骨架（PLUGIN_SPEC §2.8.1）：

    core_host.js → ui_render.js → plugin.js

测试里的结构断言要看到完整语义，必须按加载页面上的同一顺序把内核拼回组合根前面。
集中放在这里，免得二十多个测试各写一套拼接顺序、日后又漂移。
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.config import plugin_source_root

ROOT = Path(__file__).resolve().parents[1]
# 插件源码在兄弟仓库；发行包（无源码仓）退回包内 plugins/。
PLUGINS_DIR = plugin_source_root() or (ROOT / "plugins")
JS_DIR = ROOT / "static" / "js"
TEMPLATE_DIST = ROOT / "examples" / "template-plugin" / "dist"

WORKSPACE_HTML = ROOT / "static" / "workspace.html"


def _loaded_scripts(page: Path, keep) -> list[str]:
    """按加载页真实 <script> 次序挑出属于某一群组的本地脚本。

    次序写在页面里，判据就跟着页面走；再维护一份手工清单，早晚会和页面对不上。
    """
    html = page.read_text(encoding="utf-8")
    names: list[str] = []
    for value in re.findall(r"<script[^>]*src=\"([^\"]+)\"", html):
        # 缓存版本号（?v=20261113）只属于浏览器，落盘文件名不带它。
        value = value.split("?", 1)[0].split("#", 1)[0]
        if not value.startswith("/static/js/"):
            continue
        name = value.rsplit("/", 1)[-1]
        if not keep(name):
            continue
        if not (JS_DIR / name).is_file():
            raise AssertionError(f"{page.name} 引了不存在的脚本：{value}")
        names.append(name)
    if not names:
        raise AssertionError(f"{page.name} 没挂任何脚本")
    return names


def _group_parts(page: Path, root_name: str, starts: tuple[str, ...], alone: tuple[str, ...]) -> tuple[str, ...]:
    names = _loaded_scripts(page, lambda n: n == root_name or n.startswith(starts) or n in alone)
    if root_name not in names:
        raise AssertionError(f"{page.name} 没挂 {root_name}")
    return tuple(names)


def stage_parts() -> tuple[str, ...]:
    return _group_parts(WORKSPACE_HTML, "stage.js", ("stage_",), ("core_bus.js", "core_tabs.js"))


def workspace_parts() -> tuple[str, ...]:
    return _group_parts(WORKSPACE_HTML, "workspace.js", ("ws_",), ("core_log.js",))


def stage_source() -> str:
    return "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in stage_parts())


def workspace_source() -> str:
    return "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in workspace_parts())


def settings_source() -> str:
    """设置页整包源码：st_*.js 模块 + 组合根 settings.js，按 settings.html 的真实次序。

    settings.js 拆到 800 行以下后，只读组合根的断言会漏掉大半语义（工作区、切库重启、
    备份恢复都在模块里）；次序取自页面，页面一改判据跟着变，不会各说各话。
    http.js / prefs.js / plugins.js / pwa.js 不是设置页自己的逻辑，不参与拼接。
    """
    parts = _group_parts(ROOT / "static" / "settings.html", "settings.js", ("st_",), ())
    return "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in parts)


def bundle_local_assets(html_path: Path, tag: str) -> str:
    """按加载页面上 `<script src>` / `<link href>` 的次序拼「整包源码」。

    `/static/` 前缀的是底座公共资产（PLUGIN_SPEC §2.8.3），不属于插件源码，跳过。
    顺带钉住一件事：加载页引了的本地资源必须真的在盘上，否则整包判据会悄悄漏掉一块。
    """
    attr = {"script": "src", "link": "href"}[tag]
    directory = html_path.parent
    html = html_path.read_text(encoding="utf-8")
    pattern = r"<%s[^>]*%s=\"([^\"]+)\"" % (tag, attr)
    parts: list[str] = []
    for value in re.findall(pattern, html):
        if value.startswith("/static/"):
            continue
        path = directory / value.split("?", 1)[0].split("#", 1)[0]
        if not path.is_file():
            raise AssertionError(f"{html_path.name} 引了不存在的{('样式' if tag == 'link' else '脚本')}：{value}")
        parts.append(path.read_text(encoding="utf-8"))
    if not parts:
        raise AssertionError(f"{html_path.name} 没有任何本地{'样式' if tag == 'link' else '脚本'}")
    return "\n".join(parts)


def bundle_local_scripts(html_path: Path) -> str:
    return bundle_local_assets(html_path, "script")


def plugin_entry(plugin_id: str) -> Path:
    """插件入口页：路径以清单的 ``entry.frontend`` 为准（dist/ 或 webui/）。"""
    from app.core import manifests

    manifest = manifests.load_manifest(PLUGINS_DIR / plugin_id)
    frontend = (manifest.get("entry") or {}).get("frontend") or "dist/index.html"
    return PLUGINS_DIR / plugin_id / frontend


def plugin_bundle(plugin_id: str, tag: str = "script") -> str:
    """官方插件的「整包源码」：按入口页的加载次序拼本地 JS（或 CSS）。

    插件按 PLUGIN_SPEC §2.8.1/§2.8.2 拆成多文件后，任何只读入口页附近的断言
    都会悄悄缩小覆盖面——安全三查、总线事件名、渲染契约都在别的文件里也有。
    凡是要对「插件写了什么」下结论的测试，一律读本函数。
    """
    return bundle_local_assets(plugin_entry(plugin_id), tag)



def template_source() -> str:
    return bundle_local_scripts(TEMPLATE_DIST / "index.html")


def workspace_css() -> str:
    """底座工作台的样式整包：workspace.css 已按域拆成几份（PLUGIN_SPEC §2.8.2 同款口径）。

    切片次序直接取自 workspace.html 的真实 <link> 次序——同特异度的覆盖关系靠次序活着，
    测试与页面因此不可能各说各话。app.css / MathJax 不属于工作台样式，不参与拼接。
    """
    html = WORKSPACE_HTML.read_text(encoding="utf-8")
    parts: list[str] = []
    for value in re.findall(r"<link[^>]*href=\"([^\"]+)\"", html):
        value = value.split("?", 1)[0].split("#", 1)[0]
        if not value.startswith("/static/css/") or "workspace" not in value:
            continue
        path = ROOT / "static" / value[len("/static/"):]
        if not path.is_file():
            raise AssertionError(f"workspace.html 引了不存在的样式：{value}")
        parts.append(path.read_text(encoding="utf-8"))
    if not parts:
        raise AssertionError("workspace.html 没挂任何工作台样式")
    return "\n".join(parts)

