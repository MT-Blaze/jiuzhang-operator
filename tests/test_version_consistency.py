"""版本号一致性契约：页面文案、启动脚本与 ``app.__version__`` 不许各说各话。

背景（第七令 P0-1）：内测首日主公实测截图显示页面写着 v0.2.0。根因不是「文案没改」，
而是版本号有两个来源——静态 HTML 里写死一份，``/healthz`` 又回一份；当时 8000 端口上
还挂着一个升版之前启动的陈留进程，``/healthz`` 回 0.2.0，前端脚本便拿旧值盖掉了徽章。

修法：页面上一切版本号改为由 ``static/js/version.js`` 读 ``/healthz`` 盖章（唯一事实来源
是 ``app/__init__.py`` 的 ``__version__``），HTML 里写死的那份降级为「无 JS / 底座离线」
时的兜底文案；``start.bat`` 固定 65496，并按「端口 PID + 身份签名」清理旧实例（跨安装目录也认），
不再让人对着旧进程发愣。
本测试把兜底文案钉死在 ``__version__`` 上——下次升版忘了同步，这里立刻红。

运行：``.venv/Scripts/python.exe -m unittest tests.test_version_consistency``
"""

from __future__ import annotations

import base64
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
    """start.bat 的自愈台阶：pip 缺失能修、端口占用有明确出口。"""

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

    def test_03_cross_folder_kill_is_port_and_identity_scoped(self) -> None:
        """按端口找 PID，校验身份后才杀：别的安装目录留下的九章进程也能被认出来。"""
        self.assertIn("Get-NetTCPConnection -LocalPort $port -State Listen", self.text)
        self.assertIn("Select-String (':' + $port + '\\s')", self.text, "缺少 netstat 兜底取 PID")
        self.assertIn("jiuzhang-operator", self.text, "缺少 /healthz 服务名签名")
        self.assertIn("app.main:app", self.text, "缺少命令行签名")
        self.assertIn("taskkill /F /T /PID", self.text, "九章旧进程必须按 PID 连树杀掉")
        self.assertIn("IndexOf('--port ' + $port)", self.text, "同族进程也必须绑在同一端口，避免误杀别的实例")
        self.assertIn("Start-Sleep -Milliseconds 500", self.text, "杀完必须轮询等端口真正释放")
        self.assertIn(":kill_port_owner", self.text)
        self.assertNotIn("GetFullPath", self.text, "按当前路径匹配的旧逻辑必须删干净")
        self.assertNotIn("kill_project_servers", self.text)
        self.assertLess(
            self.text.index(":deps_ok"),
            self.text.index("call :kill_port_owner", self.text.index(":deps_ok")),
        )

    def test_05_single_instance_lock_reuses_or_cleans(self) -> None:
        """单实例锁：先探 65496..65505（含 .current_port），同目录复用、异目录清理。"""
        self.assertIn("for ($p=65496; $p -le 65505; $p++)", self.text, "缺少端口上探")
        self.assertIn("Test-Path 'data\\.current_port'", self.text, "缺少上次端口读取")
        self.assertIn("Set-Content -Path 'data\\.current_port'", self.text, "缺少实际端口写入")
        self.assertIn("Remove-Item 'data\\.current_port'", self.text, "--stop 必须清掉端口记录")
        self.assertIn("$root='%~dp0'", self.text, "缺少本目录身份基准")
        self.assertIn("$_.SameDir", self.text)
        self.assertIn("$reuse.Port", self.text, "缺少同目录实例复用")
        self.assertIn("exit 10", self.text, "复用后必须直接退出，绝不启动第二个进程")
        self.assertIn("$foreign", self.text)
        self.assertIn("exit 2", self.text, "65496 被陌生程序占用时必须报错退出")
        # 门卫必须发生在建 venv / 装依赖之前，否则「已在运行」也要空等几分钟。
        self.assertLess(
            self.text.index("call :instance_gate", self.text.index(":run")),
            self.text.index(":pipcheck"),
        )
        # --stop 走同一个门卫的 stop 分支，全局清场。
        stop_block = self.text[self.text.index(":stop"):self.text.index(":run")]
        self.assertIn("call :instance_gate stop", stop_block)

    def test_06_same_folder_reuse_requires_matching_version(self) -> None:
        """同目录旧版本进程不许复用：文件已升版时，双击 start.bat 必须真重启。"""
        self.assertIn('set "LOCALVER="', self.text, "缺少本目录期望版本读取")
        self.assertIn('findstr /b /c:"__version__"', self.text)
        self.assertIn("$localVer='%LOCALVER%';", self.text)
        self.assertIn("RunVer=$runVer", self.text, "缺少实例 /healthz 版本采集")
        self.assertIn("$_.SameDir -and (-not $localVer -or $_.RunVer -eq $localVer)", self.text,
                      "同目录复用必须比对版本")

    def test_04_port_busy_reports_pid_and_process_name(self) -> None:
        """占用者身份不明时不许武断说「不是九章算子」，必须报 PID / 进程名并给中文指引。"""
        self.assertNotIn("NOT Jiuzhang Operator", self.text)
        block = self.text[self.text.index(":port_busy"):self.text.index(":no_python")]
        self.assertIn("data\\port-owner.pid", block)
        self.assertIn("data\\port-owner.name", block)
        payload = re.search(r"FromBase64String\('([A-Za-z0-9+/=]+)'\)", block)
        self.assertIsNotNone(payload, "中文提示必须由 base64 承载以保持纯 ASCII")
        assert payload is not None
        message = base64.b64decode(payload.group(1)).decode("utf-8")
        self.assertIn("{PID}", message)
        self.assertIn("{NAME}", message)
        self.assertIn("请手动结束该进程", message)


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


class InstallerContractTest(unittest.TestCase):
    """install.bat 是首发入口：纯 ASCII + CRLF、只走镜像、双文件夹布局。

    2026-11-13 第十令：底座改从 Releases 的纯净发行包下载，插件仓库仍是
    main 分支源码；装完必须是两个平级文件夹 ``jiuzhang-operator`` 与
    ``jiuzhang-plugins``，底座靠 ``../jiuzhang-plugins/src`` 自动发现插件。
    """

    def setUp(self) -> None:
        self.raw = (ROOT / "install.bat").read_bytes()
        self.text = self.raw.decode("ascii")

    def test_01_ascii_only_with_crlf(self) -> None:
        self.assertEqual(self.text.count("\r\n"), self.text.count("\n"))
        self.assertGreater(self.text.count("\r\n"), 100)

    def test_02_mirror_fallback_order_and_no_bare_github(self) -> None:
        first = self.text.index("https://ghproxy.net/https://github.com/")
        second = self.text.index("https://github.kkgithub.com/")
        self.assertLess(first, second, "主镜像必须先于备用镜像")
        # 任何下载 URL 都必须以镜像主机开头，不允许直接以 github.com 起头。
        self.assertNotIn('"https://github.com/', self.text, "install.bat 不许直连 github.com")

    def test_03_base_uses_release_asset_plugins_use_main_zip(self) -> None:
        self.assertIn("releases/latest/download/jiuzhang-operator.zip", self.text)
        self.assertNotIn("MT-Blaze/jiuzhang-operator/archive/refs/heads/main.zip", self.text,
                         "底座不许再拉 main 分支源码 zip")
        self.assertIn("archive/refs/heads/main.zip", self.text, "插件仓库仍拉 main 分支源码")
        self.assertIn('if /i "%KIND%"=="plugins" set "REL=jiuzhang-plugins"', self.text)
        self.assertIn('set "ASSET=releases/latest/download/jiuzhang-operator.zip"', self.text)

    def test_04_sibling_folder_layout_and_content_probe(self) -> None:
        self.assertIn('set "OP_DST=%~dp0jiuzhang-operator"', self.text)
        self.assertIn('set "PL_DST=%~dp0jiuzhang-plugins"', self.text)
        self.assertIn('xcopy "%OP_SRC%\\*" "%OP_DST%\\"', self.text)
        self.assertIn('xcopy "%PL_SRC%\\*" "%PL_DST%\\"', self.text)
        self.assertIn("org.jiuzhang.bank-engine\\plugin.toml", self.text,
                      "插件包必须按内容探测顶层目录，不能写死 zip 内目录名")
        self.assertNotIn('xcopy "%PL_SRC%\\*" "%~dp0plugins\\"', self.text,
                         "插件源码不许再摊平进底座 plugins/")

    def test_05_calls_nested_start_and_writes_migration_guide(self) -> None:
        self.assertIn('call "%~dp0jiuzhang-operator\\start.bat"', self.text)
        self.assertNotIn('call "%~dp0start.bat"', self.text, "旧根目录入口必须换掉")
        self.assertIn("FromBase64String", self.text, "中文迁移说明必须由 PowerShell 解码写出")
        self.assertIn("5aaC5L2V6L+B56e75pen5pWw5o2uLnR4dA==", self.text)

    def test_06_migration_guide_points_at_new_data_dir(self) -> None:
        blobs = re.findall(r"FromBase64String\('([A-Za-z0-9+/=]+)'\)", self.text)
        decoded = [base64.b64decode(blob).decode("utf-8") for blob in blobs if len(blob) > 40]
        guide = next(text for text in decoded if "迁移步骤" in text)
        self.assertIn("jiuzhang-operator\\data", guide)
        self.assertIn("jiuzhang-plugins\\src", guide)

    def test_07_every_goto_has_a_label(self) -> None:
        labels = set(re.findall(r"(?m)^:([A-Za-z_][A-Za-z0-9_]*)", self.text))
        gotos = set(re.findall(r"goto\s+([A-Za-z_][A-Za-z0-9_]*)", self.text))
        self.assertEqual(gotos - labels, set(), "存在跳不到的标签")

    def test_08_download_uses_curl_with_progress_bar(self) -> None:
        """下载必须交给 Windows 自带 curl.exe 并强制 --progress-bar。"""
        self.assertIn("where curl.exe", self.text, "缺少 curl.exe 可用性探测")
        self.assertIn("curl.exe -f -L --progress-bar", self.text, "缺少带进度条的 curl 下载命令")
        self.assertIn('-o "%DEST%" "%URL%"', self.text, "curl 必须把文件写到临时路径")
        self.assertNotIn("Invoke-WebRequest", self.text, "下载不许再退回 Invoke-WebRequest")

    def test_09_curl_exit_code_drives_four_mirror_fallback(self) -> None:
        """非 0 返回码即判该镜像失败并落到下一个，四个都挂则显式报错退出。"""
        block = self.text[self.text.index(":download"):self.text.index("rem ---------- unicode console output ----------")]
        self.assertEqual(block.count("call :try_mirror"), 4, "必须依次尝试四个镜像节点")
        self.assertLess(block.index("ghproxy.net"), block.index("github.kkgithub.com"))
        self.assertLess(block.index("github.kkgithub.com"), block.index("gh-proxy.com"))
        self.assertLess(block.index("gh-proxy.com"), block.index("ghfast.top"))
        self.assertIn("if errorlevel 1 exit /b 1", block, "curl 非 0 返回码必须判失败")
        self.assertIn("if not errorlevel 1 exit /b 0", block)
        self.assertIn("if errorlevel 1 goto download_failed", self.text, "四镜像全挂必须显式报错退出")
        self.assertIn(":download_failed", self.text)


if __name__ == "__main__":
    unittest.main()
