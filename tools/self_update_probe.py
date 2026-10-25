# -*- coding: utf-8 -*-
"""底座自更新真机全流程压测（军令 #14 阶段五）。

用法：``.venv/Scripts/python.exe tools/self_update_probe.py <tag>``

这一支不替底座「演」一遍流程，而是在一份**装好的发行版**副本上真跑：

1. 造沙箱发行版（``.system_generated/self_update_probe/<tag>/install/``）：
   没有 ``.git``（所以底座不会以「开发工作树」为由拒绝自动覆盖重启），
   ``.venv`` 用目录联接指向本机 venv（发行版里就是自带 venv 的样子），
   里面塞进老师的资产（``data/``）与本地插件（``plugins/``）。
2. 合成一份 99.0.0 的底座包：真代码 + 假版本号，并**故意夹带**
   ``data/``、``plugins/``、``dist/``、``.system_generated/`` 四个目录的载荷。
3. 起本地 HTTP 服托管这份包与带 ``host`` 块的索引，在真浏览器里点
   【检查更新】→【更新并重启】→【确认：覆盖并重启】。
4. 底座真的自杀、真的跑 ``update.bat``、真的 robocopy 覆盖、真的重启。
5. 核验：老师资产与本地插件逐字节未变；夹带载荷一个都没落地；新版本真的在跑
   （``/healthz`` 与界面徽章都是 99.0.0）；一次性脚本自删；暂存区清空。

本机 ``data/`` 与仓库 ``plugins/`` 一律不碰：底座进程、插件目录、题库全在沙箱里。
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import __version__  # noqa: E402

HOST_VERSION = "99.0.0"
MARKER_NAME = "HOST_PACKAGE_MARKER.txt"
MARKER_TEXT = "jiuzhang-host-package-99-ok"
TOKEN = "jzo-self-update-probe-token"

# 复制进沙箱发行版的程序文件（够跑起来即可，不搬测试与工具目录）
COPY_ITEMS = ("app", "static", "schemas", "examples", "docs", "index.html", "LICENSE",
              "PLUGIN_SPEC.md", "AGENTS.md", "README.md", "plugins.json",
              "requirements.txt", "start.bat", "build_release.bat")
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")

# 运行期自己会变的文件：不算「老师资产」，逐字节对比时排除。
# 底座每次启动都会重写自己的库、索引缓存、工作区登记与更新状态，
# 这些变化是应用自己写的，不是自更新干的。
RUNTIME_FILES = {".local_token", "plugin_index_cache.json", "plugin_state.json",
                 "jiuzhang.db", "jiuzhang.db-wal", "jiuzhang.db-shm",
                 "update_state.json", "workspaces.json"}
RUNTIME_PREFIXES = ("banks/", "uploads/")


def is_runtime_file(relative: str) -> bool:
    # 军令 #18 起续更清单按工作区落位（data/workspaces/<id>/update_state.json），
    # 只比全路径的旧口径会把这份底座自己写的文件误判成「被动过的老师资产」。
    name = relative.rsplit("/", 1)[-1]
    return name in RUNTIME_FILES or relative.startswith(RUNTIME_PREFIXES)

# 夹带载荷：这些目录名都在 robocopy 的排除清单里，一个都不许落地
SMUGGLED = {
    "data/EVIL_DATA.txt": "包里夹带的假 data\n",
    "plugins/org.probe.local/EVIL_PLUGIN.txt": "包里夹带的假插件\n",
    "plugins/evil.plugin/plugin.json": '{"id": "org.evil.plugin"}\n',
    "dist/EVIL_DIST.txt": "包里夹带的假 dist\n",
    ".system_generated/EVIL_SYSGEN.txt": "包里夹带的假暂存\n",
}


# ------------------------------------------------------------------ 小工具
def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path, skip: set[str] | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for item in sorted(root.rglob("*")):
        if not item.is_file():
            continue
        relative = item.relative_to(root).as_posix()
        if skip and relative in skip:
            continue
        out[relative] = sha256_file(item)
    return out


def health_version(base: str) -> str:
    try:
        with urllib.request.urlopen(base + "/healthz", timeout=2) as response:
            return str(json.loads(response.read().decode("utf-8")).get("version") or "")
    except Exception:  # noqa: BLE001 - 探针只关心拿不拿得到版本号
        return ""


def wait_health(base: str, process: subprocess.Popen, log_path: Path,
                timeout: float = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            output = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
            raise RuntimeError("底座进程提前退出：\n" + output[-3000:])
        if health_version(base):
            return True
        time.sleep(0.2)
    raise RuntimeError("底座未在 %d 秒内就绪" % timeout)


def wait_version(base: str, expected: str, timeout: float = 180) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if health_version(base) == expected:
            return True
        time.sleep(0.4)
    return False


def pid_on_port(port: int) -> int:
    completed = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
    for line in (completed.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[1].endswith(":%d" % port) \
                and parts[3].upper() == "LISTENING":
            try:
                return int(parts[4])
            except ValueError:
                return 0
    return 0


def kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)


def pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    completed = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
    return str(pid) in (completed.stdout or "")


def server_pid(log_path: Path) -> int:
    """底座真正的服务进程 PID。

    venv 里的 ``python.exe`` 会带一个转发子进程：Popen 拿到的是转发者，
    跑业务的是它的儿子——``os.getpid()``（也就是一次性脚本里等的那个 PID）
    记的是后者，所以必须从 uvicorn 的启动日志里读。
    """
    if not log_path.is_file():
        return 0
    text = log_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Started server process \[(\d+)\]", text)
    return int(match.group(1)) if match else 0


def kill_sandbox_processes(marker: Path) -> list[int]:
    """把还在跑这个沙箱底座的进程全部收掉（含重启后那个 wait 不到的儿子）。"""
    script = (
        "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' "
        "-and $_.CommandLine -like '*%s*' }; $ids = @(); $p | ForEach-Object { "
        "$ids += $_.ProcessId; Stop-Process -Id $_.ProcessId -Force }; $ids -join ' '"
        % marker
    )
    completed = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [int(item) for item in (completed.stdout or "").split() if item.isdigit()]


def purge_dir(path: Path) -> None:
    """删干净一个沙箱目录：先收进程（有进程把目录当 cwd 时删不掉）。"""
    for _ in range(5):
        if not path.exists():
            return
        kill_sandbox_processes(path)
        time.sleep(0.4)
        try:
            shutil.rmtree(path)
            return
        except OSError:
            continue
    shutil.rmtree(path, ignore_errors=True)


# ------------------------------------------------------------ 沙箱发行版
def make_junction(link: Path, target: Path, work: Path) -> None:
    """目录联接（非管理员可用）：发行版里的 ``.venv`` 就长这样。"""
    bat = work / "mklink.bat"
    bat.write_text('@echo off\r\nmklink /J "%s" "%s"\r\n' % (link, target),
                   encoding="utf-8", newline="")
    completed = subprocess.run(["cmd.exe", "/c", str(bat)], capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError("mklink 失败：%s%s" % (completed.stdout, completed.stderr))


def build_installation(install: Path, work: Path) -> None:
    install.mkdir(parents=True, exist_ok=True)
    for name in COPY_ITEMS:
        source = ROOT / name
        if not source.exists():
            continue
        target = install / name
        if source.is_dir():
            shutil.copytree(source, target, ignore=IGNORE)
        else:
            shutil.copy2(source, target)
    make_junction(install / ".venv", ROOT / ".venv", work)


def seed_teacher_assets(install: Path) -> None:
    """老师的私有资产与本地插件：自更新全程必须逐字节不变。"""
    data = install / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "teacher_notes.txt").write_text("老师的私有笔记：自更新不许碰\n", encoding="utf-8")
    (data / "teacher_bank.db").write_bytes(b"TEACHER-BANK-BYTES-0001")
    (data / "config.json").write_text(
        json.dumps({"theme": "ink", "paper": "a4"}, ensure_ascii=False), encoding="utf-8")

    plugin = install / "plugins" / "org.probe.local"
    (plugin / "dist").mkdir(parents=True, exist_ok=True)
    (plugin / "bank").mkdir(parents=True, exist_ok=True)
    (plugin / "plugin.json").write_text(json.dumps({
        "schema_version": "1.0",
        "id": "org.probe.local",
        "name": "本地插件",
        "version": "0.1.0",
        "api_version": "1.0",
        "kind": "renderer",
        "description": "自更新真机探针的本地插件",
        "license": "Apache-2.0",
        "slots": ["question.card"],
        "capabilities": ["question.render"],
        "permissions": ["questions:read"],
        "entry": {"frontend": "dist/index.html"},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (plugin / "LICENSE").write_text("Apache-2.0 probe fixture\n", encoding="utf-8")
    (plugin / "dist" / "index.html").write_text("<!doctype html><p>本地插件</p>\n", encoding="utf-8")
    (plugin / "bank" / "bank.db").write_bytes(b"LOCAL-PLUGIN-BANK-BYTES")


def install_minimal_core_bank(install: Path) -> None:
    """装一份「空壳」题库插件（只要清单 + 表结构，不要真题库）。

    发行版就是这样发的：题库是空壳，老师在工作区里自己录。沙箱里少了它，
    工作区的「教材版本」接口会 400，探针的控制台错误判据就会被这条噪声污染。
    """
    source = ROOT / "plugins" / "org.jiuzhang.bank-engine"
    target = install / "plugins" / "org.jiuzhang.bank-engine"
    (target / "bank").mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "plugin.json", target / "plugin.json")
    shutil.copy2(source / "LICENSE", target / "LICENSE")
    shutil.copy2(source / "bank" / "schema.sql", target / "bank" / "schema.sql")
    # 军令 #20：引擎是无界面插件，没有 dist/；有才复制，避免拿旧布局去猜。
    if (source / "dist").is_dir():
        shutil.copytree(source / "dist", target / "dist", ignore=IGNORE)


def build_host_package(install: Path, version: str) -> bytes:
    """合成一份 99.0.0 底座包：真代码 + 假版本号，并夹带四个危险目录的载荷。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        prefix = "jiuzhang-operator-%s/" % version
        for folder in ("app", "static", "schemas"):
            base = install / folder
            if not base.is_dir():
                continue
            for item in sorted(base.rglob("*")):
                if item.is_dir() or "__pycache__" in item.parts:
                    continue
                relative = item.relative_to(install).as_posix()
                if relative == "app/__init__.py":
                    text = item.read_text(encoding="utf-8")
                    archive.writestr(prefix + relative,
                                     re.sub(r'__version__\s*=\s*"[^"]*"',
                                            '__version__ = "%s"' % version, text, count=1))
                    continue
                archive.writestr(prefix + relative, item.read_bytes())
        for name in ("index.html", "LICENSE"):
            path = install / name
            if path.is_file():
                archive.writestr(prefix + name, path.read_bytes())
        archive.writestr(prefix + MARKER_NAME, MARKER_TEXT)
        for name, text in SMUGGLED.items():
            archive.writestr(prefix + name, text)
    return buffer.getvalue()


# -------------------------------------------------------------- 本地索引服
class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - 基类签名
        return


def start_server(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = lambda *args, **kwargs: SilentHandler(*args, directory=str(directory), **kwargs)  # noqa: E731
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d" % port


def write_index(serve_dir: Path, base: str, version: str) -> None:
    payload = {
        "index_version": "1.0",
        "name": "自更新真机探针索引",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entries": [],
        "host": {
            "version": version,
            "zip_url": base + "/host-%s.zip" % version,
            "mirrors": [],
            "notes": "自更新真机探针：假版本号 + 真代码",
        },
    }
    (serve_dir / "plugins.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ 起底座
def start_app(install: Path, port: int, log_path: Path) -> subprocess.Popen:
    env = dict(os.environ)
    env["JZO_DATA_DIR"] = str(install / "data")
    env["JZO_PLUGINS_DIR"] = str(install / "plugins")
    env["JZO_PORT"] = str(port)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("PYTHONPATH", None)
    python_exe = install / ".venv" / "Scripts" / "python.exe"
    handle = log_path.open("w", encoding="utf-8")
    return subprocess.Popen(
        [str(python_exe), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port)],
        cwd=str(install), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)


# -------------------------------------------------------------------- 主流程
def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "self_update_probe" / tag
    purge_dir(work)
    shots = work / "shots"
    shots.mkdir(parents=True)
    install = work / "install"
    serve = work / "serve"
    serve.mkdir(parents=True)

    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str = "") -> bool:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + ("｜" + detail if detail else ""), flush=True)
        return bool(ok)

    server, base = start_server(serve)
    port = free_port()
    app_base = "http://127.0.0.1:%d" % port
    launcher_pid = 0
    app_pid = 0
    new_pid = 0
    browser_errors: list[str] = []
    page_errors: list[str] = []
    bad_responses: list[tuple[int, str]] = []
    noise: list[str] = []

    try:
        build_installation(install, work)
        seed_teacher_assets(install)
        install_minimal_core_bank(install)
        package = build_host_package(install, HOST_VERSION)
        (serve / ("host-%s.zip" % HOST_VERSION)).write_bytes(package)
        write_index(serve, base, HOST_VERSION)

        log_path = work / "app.log"
        process = start_app(install, port, log_path)
        launcher_pid = process.pid
        wait_health(app_base, process, log_path)
        app_pid = server_pid(log_path)
        record("沙箱发行版启动并通过健康检查", health_version(app_base) == __version__,
               "底座版本 %s（仓库当前 %s），服务进程 %d" % (health_version(app_base),
                                                          __version__, app_pid))

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            page = context.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("console", lambda message: browser_errors.append(message.text)
                    if message.type == "error" else None)
            page.on("response", lambda response: bad_responses.append(
                (response.status, response.url.split("127.0.0.1:%d" % port)[-1]))
                if response.status >= 400 else None)

            page.goto(app_base + "/settings?panel=plugin&tab=index", wait_until="networkidle")
            page.fill("#plIndexUrl", base + "/plugins.json")
            # 插件分区是二级页签（管理 / 检查更新 / 在线索引 / 手动安装）：
            # 索引地址在「在线索引」页签，检查更新在「检查更新」页签。
            page.click("#stPluginTabUpdate")
            page.click("#upCheckBtn")
            expect(page.locator("#upHostText")).to_contain_text(HOST_VERSION)
            expect(page.locator("#upHostBtn")).to_be_enabled()
            page.screenshot(path=str(shots / "10-checked.png"), full_page=True)
            record("界面按索引报出底座新版本", True, "发现底座新版本 " + HOST_VERSION)

            # 快照取在「更新之前」：底座启动与首屏加载会建自己的库与索引缓存，
            # 那不是老师的资产，更新过程也不许动它们。
            before_plugins = tree_hashes(install / "plugins")
            before_data = tree_hashes(install / "data")

            page.click("#upHostBtn")
            expect(page.locator("#upLog")).to_contain_text("一次性脚本已生成")
            expect(page.locator("#upHostBtn")).to_have_text("确认：覆盖并重启")
            page.screenshot(path=str(shots / "20-prepared.png"), full_page=True)
            record("第一下只下载校验、生成脚本，不动正在跑的底座", True,
                   "一次性脚本已生成，按钮转为「确认：覆盖并重启」")

            page.click("#upHostBtn")
            page.wait_for_timeout(500)

            deadline = time.time() + 30
            exited = False
            while time.time() < deadline:
                if app_pid and not pid_exists(app_pid):
                    exited = True
                    break
                time.sleep(0.2)
            record("底座进程真的自己退出了", exited, "服务进程 %d 已结束" % app_pid)

            record("新版本真的起来了", wait_version(app_base, HOST_VERSION, timeout=180),
                   "/healthz 版本 %s" % health_version(app_base))
            new_pid = pid_on_port(port)
            record("确实是另一个进程接管了端口", new_pid not in (0, app_pid, launcher_pid),
                   "新进程 %d 接管 %d（旧服务进程 %d）" % (new_pid, port, app_pid))

            fresh = context.new_page()
            fresh_errors: list[str] = []
            fresh.on("pageerror", lambda error: fresh_errors.append(str(error)))
            fresh.on("console", lambda message: fresh_errors.append(message.text)
                     if message.type == "error" else None)
            fresh.goto(app_base + "/", wait_until="networkidle")
            fresh.screenshot(path=str(shots / "30-new-workspace.png"), full_page=True)
            fresh.goto(app_base + "/about", wait_until="networkidle")
            expect(fresh.locator("#version")).to_have_text("v" + HOST_VERSION)
            fresh.screenshot(path=str(shots / "40-new-version.png"), full_page=True)
            record("重启后的新界面可用、版本徽章已是新版", True,
                   "界面徽章 v%s" % HOST_VERSION)
            record("新界面零 console/page 错误", not fresh_errors,
                   "；".join(fresh_errors[:3]))
            browser.close()

        noise = [text for text in browser_errors
                 if "ERR_CONNECTION_REFUSED" in text or "net::" in text
                 or "Failed to load resource" in text]
        real_errors = [text for text in browser_errors if text not in noise]
        record("更新期间除重启断连外无其他控制台错误", not real_errors,
               "；".join(real_errors[:3]))
        record("无未捕获页面异常", not page_errors, "；".join(page_errors[:3]))

        after_plugins = tree_hashes(install / "plugins")
        after_data = tree_hashes(install / "data")

        record("本地插件目录逐字节未变", before_plugins == after_plugins,
               "%d 个文件" % len(after_plugins))
        teacher = ("teacher_notes.txt", "teacher_bank.db", "config.json")
        record("data/ 里老师的资产逐字节未变",
               all(before_data.get(name) == after_data.get(name) for name in teacher),
               "、".join(teacher))
        stable_before = {k: v for k, v in before_data.items() if not is_runtime_file(k)}
        stable_after = {k: v for k, v in after_data.items() if not is_runtime_file(k)}
        changed = sorted(k for k in stable_before.keys() & stable_after.keys()
                         if stable_before[k] != stable_after[k])
        touched = sorted(stable_after.keys() ^ stable_before.keys())
        record("data/ 全树未被改动（运行期文件除外）",
               not changed and not touched,
               "改动 %d 个、新增/缺失 %d 个%s"
               % (len(changed), len(touched),
                  ("：" + "、".join(changed + touched)) if (changed or touched) else ""))

        for name in SMUGGLED:
            record("包里的载荷没落地：" + name, not (install / name).exists())
        record("包里没带来新的插件目录", not (install / "plugins" / "evil.plugin").exists())

        record("新包真的落地了", (install / MARKER_NAME).is_file()
               and (install / MARKER_NAME).read_text(encoding="utf-8") == MARKER_TEXT,
               MARKER_NAME)
        version_text = (install / "app" / "__init__.py").read_text(encoding="utf-8")
        record("底座版本文件已是新版本", ('__version__ = "%s"' % HOST_VERSION) in version_text,
               HOST_VERSION)

        script_path = Path(tempfile.gettempdir()) / ("jzo_update_%d.bat" % app_pid)
        stage_path = Path(tempfile.gettempdir()) / ("jzo_host_update_%d" % app_pid)
        record("一次性 update.bat 已自删", not script_path.exists(), str(script_path))
        record("暂存目录已清理", not stage_path.exists(), str(stage_path))

        # 一次性脚本的日志：批处理的输出接的是文件而不是控制台（没有控制台时
        # cmd 的 echo 会失败并终止整篇脚本），四步进度都留在这儿。
        log_source = script_path.with_name(script_path.stem + ".log")
        log_text = ""
        if log_source.is_file():
            raw_log = log_source.read_bytes()
            # 没有控制台时 cmd 的输出走 UTF-8；老系统也有走 ANSI 码页的
            try:
                log_text = raw_log.decode("utf-8")
            except UnicodeDecodeError:
                log_text = raw_log.decode("cp936", errors="replace")
            (work / "update.log").write_text(log_text, encoding="utf-8")
        steps = ["[1/4]", "[2/4]", "[3/4]", "[4/4]"]
        record("一次性脚本四步都跑完（日志为证）",
               all(step in log_text for step in steps),
               "日志：%s" % log_source.name)

        # 续更清单从军令 #18 起属于当前工作区；根 data/ 下再出现同名文件就是落错了地方。
        state_path = install / "data" / "workspaces" / "default" / "update_state.json"
        state = {}
        if state_path.is_file():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except ValueError:
                state = {}
        record("续更清单按工作区落位且版本号正确",
               not (install / "data" / "update_state.json").exists()
               and str(state.get("host_version") or "") == HOST_VERSION,
               "host_version=%s，路径=%s" % (state.get("host_version") or "", state_path.relative_to(install)))

        log_text = (work / "app.log").read_text(encoding="utf-8", errors="replace")
        (work / "app.log").write_text(log_text, encoding="utf-8")
    finally:
        kill_pid(new_pid)
        kill_sandbox_processes(install)
        server.shutdown()

    passed = sum(1 for item in checks if item["ok"])
    result = {
        "tag": tag,
        "host_version": HOST_VERSION,
        "install": str(install),
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "shots": sorted(str(item.relative_to(work)) for item in shots.glob("*.png")),
        "expected_noise": noise,
    }
    (work / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print("----")
    print("自更新真机压测：%d/%d 通过" % (passed, len(checks)))
    print("产物：%s" % (work / "result.json"))
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
