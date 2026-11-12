"""版本号一致性契约：页面文案、启动脚本与 ``app.__version__`` 不许各说各话。

背景（第七令 P0-1）：内测首日主公实测截图显示页面写着 v0.2.0。根因不是「文案没改」，
而是版本号有两个来源——静态 HTML 里写死一份，``/healthz`` 又回一份；当时 8000 端口上
还挂着一个升版之前启动的陈留进程，``/healthz`` 回 0.2.0，前端脚本便拿旧值盖掉了徽章。

修法：页面上一切版本号改为由 ``static/js/version.js`` 读 ``/healthz`` 盖章（唯一事实来源
是 ``app/__init__.py`` 的 ``__version__``），HTML 里写死的那份降级为「无 JS / 底座离线」
时的兜底文案；``start.bat`` 固定 65496 并先杀本项目旧进程，不再让人对着旧进程发愣。
本测试把兜底文案钉死在 ``__version__`` 上——下次升版忘了同步，这里立刻红。

运行：``.venv/Scripts/python.exe -m unittest tests.test_version_consistency``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app import __version__

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"

# 兜底文案形如 <span data-app-version>v0.3.1</span>；分组只取标签内文本。
SLOT_RE = re.compile(r"data-app-version[^>]*>\s*([^<]*?)\s*<", re.S)
ANY_VERSION_RE = re.compile(r"v\d+\.\d+\.\d+")

# 展示版本号的前端页面（橱窗 index.html 是零脚本静态页，单独一条测试管；
# 题库列表页已于 10.24 军令废弃删除，对话工作台不写死版本号兜底位）。
VERSIONED_PAGES = ("index.html",)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class VersionSingleSourceTest(unittest.TestCase):
    """页面兜底文案必须与底座版本号逐字相同。"""

    def test_01_version_slots_match_backend(self) -> None:
        expected = "v" + __version__
        checked = 0
        for name in VERSIONED_PAGES:
            text = _read(STATIC / name)
            slots = SLOT_RE.findall(text)
            self.assertTrue(slots, f"{name} 里找不到 data-app-version 兜底位")
            for slot in slots:
                self.assertEqual(
                    slot,
                    expected,
                    f"{name} 的兜底版本号写成 {slot!r}，底座是 {expected!r}",
                )
                checked += 1
        self.assertGreaterEqual(checked, 2, "徽章 + 页脚至少两个兜底位")

    def test_02_version_script_wired_into_pages(self) -> None:
        """有兜底位的页面必须挂上 version.js，否则兜底会永远停在旧值。"""
        for name in VERSIONED_PAGES:
            text = _read(STATIC / name)
            self.assertIn("/static/js/version.js", text, f"{name} 没有引入 version.js")

    def test_03_no_stale_version_string_in_frontend(self) -> None:
        """前端任何写死的 vX.Y.Z 都必须等于当前版本（历史叙述只留在 Markdown）。"""
        expected = "v" + __version__
        offenders: list[str] = []
        targets = [ROOT / "index.html", STATIC / "index.html"]
        targets += sorted((STATIC / "js").glob("*.js"))
        for path in targets:
            for found in ANY_VERSION_RE.findall(_read(path)):
                if found != expected:
                    offenders.append(f"{path.relative_to(ROOT)}: {found}")
        self.assertEqual(offenders, [], "前端存在过期版本号：" + ", ".join(offenders))

    def test_04_version_js_does_not_hardcode_a_version(self) -> None:
        """盖章脚本自身不许写死版本号，只能信 /healthz。"""
        text = _read(STATIC / "js" / "version.js")
        self.assertEqual(ANY_VERSION_RE.findall(text), [])
        self.assertIn("/healthz", text)
        self.assertIn("data-app-version", text)

    def test_05_app_js_no_longer_writes_version(self) -> None:
        """同一段文案只能有一个写入者：app.js 退出盖章，只管健康灯与时间。"""
        text = _read(STATIC / "js" / "app.js")
        self.assertNotIn("status-version", text)
        self.assertNotIn("data-app-version", text)


class DocsVersionTest(unittest.TestCase):
    """橱窗与 README 是发放时用户第一眼看到的东西，口径必须跟上。"""

    def test_01_showcase_mentions_current_version(self) -> None:
        text = _read(ROOT / "index.html")
        # 只钉版本号，不钉「内测/正式版」这类渠道措辞——升版时措辞要跟着改，钉死会把判据打成假红。
        self.assertIn(f"v{__version__}", text)
        self.assertIn(f"Jiuzhang Operator v{__version__}", text)
        self.assertIn(f"九章算子 v{__version__} 技术栈与约束", text)

    def test_02_readme_healthz_example_matches(self) -> None:
        text = _read(ROOT / "README.md")
        self.assertIn(f'"version": "{__version__}"', text)


class LauncherSelfHealTest(unittest.TestCase):
    """start.bat 的自愈台阶：pip 缺失能修、端口被占能换。"""

    def setUp(self) -> None:
        self.raw = (ROOT / "start.bat").read_bytes()
        self.text = self.raw.decode("ascii")  # 非 ASCII 直接抛错，见 test_03

    def test_01_pip_probe_and_ensurepip_repair(self) -> None:
        self.assertIn('-m pip --version', self.text, "缺少 pip 可用性探测")
        self.assertIn("-m ensurepip --upgrade", self.text, "缺少 ensurepip 自愈")
        self.assertIn("rmdir /s /q .venv", self.text, "缺少重建 venv 的最后一级兜底")
        # 探测必须发生在装依赖之前，否则照样死在 No module named pip 上。
        self.assertLess(self.text.index(":pipcheck"), self.text.index(":deps"))

    def test_02_single_fixed_port_by_design(self) -> None:
        """专属端口时代不再换口：固定 65496，端口被外程序占用时必须报错退出。"""
        self.assertIn("netstat -ano -p TCP", self.text, "缺少端口占用自检")
        self.assertIn("LISTENING", self.text)
        self.assertIn('set "PORT=65496"', self.text)
        self.assertNotIn("FREEPORT", self.text, "专属端口模式不允许再顺延换口")
        self.assertIn(":port_busy", self.text, "端口被外程序占用时必须有明确出口")
        # 服务必须绑在 65496，且入口固定为 /e。
        self.assertIn("'--port','65496'", self.text)
        self.assertIn('set "ENTRY=%URL%/e"', self.text)

    def test_03_package_sources_keep_version_pins(self) -> None:
        """三级取包：默认源 -> 国内镜像 -> 官方源；版本钉子一个都不许松。"""
        self.assertIn("https://pypi.tuna.tsinghua.edu.cn/simple", self.text)
        self.assertIn("--index-url https://pypi.org/simple", self.text)
        for line in self.text.splitlines():
            if "pip install" in line:
                self.assertIn("-r requirements.txt", line)
                self.assertNotIn("--upgrade-strategy", line)

    def test_04_ascii_only_with_crlf(self) -> None:
        """双击即跑的批处理：纯 ASCII + 全 CRLF，避免编码与换行两类哑弹。"""
        self.assertEqual(self.text.count("\r\n"), self.text.count("\n"))
        self.assertGreater(self.text.count("\r\n"), 100)

    def test_05_every_goto_has_a_label(self) -> None:
        labels = set(re.findall(r"(?m)^:([A-Za-z_][A-Za-z0-9_]*)", self.text))
        gotos = set(re.findall(r"goto\s+([A-Za-z_][A-Za-z0-9_]*)", self.text))
        self.assertEqual(gotos - labels, set(), "存在跳不到的标签")


class SilentLauncherTest(unittest.TestCase):
    """双击即用且不弹黑框：start.bat 自隐藏重启，VBS 启动器已废弃删除。"""

    def setUp(self) -> None:
        self.text = (ROOT / "start.bat").read_bytes().decode("ascii")

    def test_01_launcher_relaunches_itself_hidden(self) -> None:
        self.assertIn('if /i "%~1"=="--run"', self.text)
        self.assertIn("Start-Process -FilePath '%~f0' -ArgumentList '--run'", self.text)
        self.assertIn("-WindowStyle Hidden", self.text)

    def test_02_vbs_launchers_are_gone(self) -> None:
        self.assertFalse((ROOT / "启动九章算子.vbs").exists(), "VBS 启动器必须物理删除")
        self.assertFalse((ROOT / "停止九章算子.vbs").exists(), "VBS 停止脚本必须物理删除")

    def test_03_kill_is_scoped_to_this_project(self) -> None:
        """只杀 CommandLine 含本项目绝对路径的 python/uvicorn，绝不碰别的 Python。"""
        self.assertIn("CommandLine.IndexOf($root", self.text)
        self.assertIn("python|pythonw|uvicorn", self.text)
        self.assertNotIn("taskkill /F /IM python.exe", self.text)


class ProbeVersionContractTest(unittest.TestCase):
    """探针不许写死插件版本号：插件一升号，判据就变假红（军令 #21 全量回归实测）。

    2026-10-25 那轮 command_contract_probe 的 06 号判据把五个插件的版本抄成字面量，
    bank-ui 0.2.1、editor 0.6.1 落地后当场红掉——红的是探针自己，不是底座。
    """

    LITERAL_MAP_RE = re.compile(r'"org\.jiuzhang\.[a-z0-9-]+"\s*:\s*"\d+\.\d+\.\d+"')

    def test_01_no_probe_hardcodes_plugin_versions(self) -> None:
        for probe in sorted((ROOT / "tools").glob("*_probe.py")):
            hits = self.LITERAL_MAP_RE.findall(_read(probe))
            self.assertEqual(hits, [], f"{probe.name} 里写死了插件版本字面量：{hits}")

    def test_02_command_contract_reads_manifest_versions(self) -> None:
        text = _read(ROOT / "tools" / "command_contract_probe.py")
        self.assertIn("def manifest_versions()", text)
        self.assertIn('== manifest_versions()', text)


if __name__ == "__main__":
    unittest.main()
