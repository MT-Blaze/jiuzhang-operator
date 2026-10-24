"""题库 provider 路由契约：v0.8.2 追加令「第三方题库可热插拔替换」。

守的是四条不读代码就想不到的底线：

1. **官方库只是默认值**：默认 provider id 只允许出现在 ``bank_provider.DEFAULT_PROVIDER_ID``
   一处，宿主与其余模块一律走解析结果；
2. **不合规的插件选不上题库**：必须已安装**且**声明 ``bank.provider`` 能力；
3. **配置失效要回退且要说人话**：被选中的库卸载后，读取回退默认库并带 ``fallback_reason``，
   绝不静默换成第三个插件（AGENTS「插件坏了，底座还能用」）；
4. **写接口必须鉴权**：切换 provider 是修改类操作，没写令牌进不来。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_provider``
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.core import bank_provider
from app.core.config import settings

ROOT = Path(__file__).resolve().parents[1]
BANK = "org.jiuzhang.core-bank"
PAPER = "org.jiuzhang.paper-gen"


class _Isolated(unittest.TestCase):
    """把 plugins_dir 与 root data 目录都搬进临时区，绝不碰本机 plugins/ 与 data/。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.plugins_dir = base / "plugins"
        self.plugins_dir.mkdir()
        self._saved = (os.environ.get("JZO_PLUGINS_DIR"), os.environ.get("JZO_DATA_DIR"))
        for name in (BANK, PAPER):
            shutil.copytree(ROOT / "plugins" / name, self.plugins_dir / name)
        os.environ["JZO_PLUGINS_DIR"] = str(self.plugins_dir)
        os.environ["JZO_DATA_DIR"] = str(base / "data")
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        plugins, data = self._saved
        for key, value in (("JZO_PLUGINS_DIR", plugins), ("JZO_DATA_DIR", data)):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _strip_capability(self, plugin_id: str) -> None:
        manifest = self.plugins_dir / plugin_id / "plugin.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["capabilities"] = [c for c in data["capabilities"] if c != bank_provider.PROVIDER_CAPABILITY]
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class ProviderResolutionTest(_Isolated):
    def test_01_default_is_core_bank_and_says_so(self) -> None:
        info = bank_provider.resolve()
        self.assertEqual(BANK, info["plugin_id"])
        self.assertTrue(info["is_default"])
        self.assertTrue(info["installed"])
        self.assertEqual("", info["fallback_reason"], "没配置过时不该编造回退原因")

    def test_02_default_id_is_never_a_routing_target_elsewhere(self) -> None:
        """官方库 id 只许当「默认值/文案」，不许再出现在任何拼 URL 的行里。

        判据按语义而不是按字符串出现次数：workspace.js 的左栏副标题表、
        宿主取不到配置时的兜底默认值都是合法的，只有把 id 拼进
        ``/api/bank/plugins/…`` 才算写死路由目标。
        """
        literal = "org.jiuzhang.core-bank"
        offenders = []
        targets = list((ROOT / "app").rglob("*.py")) + list((ROOT / "static" / "js").rglob("*.js"))
        for path in targets:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if literal not in line:
                    continue
                if "/api/bank/plugins" in line or ("encodeURIComponent" in line and "bank" in line):
                    offenders.append(f"{path.relative_to(ROOT)}:{number}")
        self.assertEqual([], offenders, "这些行把官方题库 id 写死成了路由目标：" + ", ".join(offenders))
        # 默认值的唯一出处必须在 provider 解析器里
        source = (ROOT / "app" / "core" / "bank_provider.py").read_text(encoding="utf-8")
        self.assertIn(f'DEFAULT_PROVIDER_ID = "{literal}"', source)

    def test_03_declared_capability_is_required_to_be_eligible(self) -> None:
        ids = [item["id"] for item in bank_provider.candidates()]
        self.assertIn(BANK, ids, "官方 core-bank 必须自己声明 bank.provider，否则默认库都选不上")
        self.assertNotIn(PAPER, ids, "组卷是消费端，不该出现在候选里")

    def test_04_set_and_read_back(self) -> None:
        info = bank_provider.set_provider(BANK)
        self.assertEqual(BANK, info["plugin_id"])
        self.assertTrue(bank_provider.state_path().is_file())
        self.assertEqual(BANK, bank_provider.configured_id())

    def test_05_rejects_uninstalled_and_undeclared(self) -> None:
        with self.assertRaises(bank_provider.ProviderRejected):
            bank_provider.set_provider("com.example.never-installed")
        self._strip_capability(BANK)
        with self.assertRaises(bank_provider.ProviderRejected):
            bank_provider.set_provider(BANK)
        with self.assertRaises(bank_provider.ProviderRejected):
            bank_provider.set_provider("../escape")     # 非法 id 也要拒，不能落盘

    def test_06_stale_config_falls_back_to_default_with_reason(self) -> None:
        """被选中的库卸载后：回退默认库 + 如实报原因，不静默换成别的插件。"""
        bank_provider.set_provider(BANK)
        shutil.rmtree(self.plugins_dir / BANK)
        info = bank_provider.resolve()
        self.assertEqual(BANK, info["plugin_id"], "回退目标只能是默认 provider")
        self.assertFalse(info["installed"], "官方库自己也没装时要如实报未安装")
        self.assertIn("未安装", info["fallback_reason"])

    def test_07_uninstalled_provider_falls_back_not_to_another_plugin(self) -> None:
        """配置指向一个已卸载的第三方库：必须回默认库，而不是随便挑一个装着的。"""
        third = self.plugins_dir / "com.example.bank"
        shutil.copytree(self.plugins_dir / BANK, third)
        manifest = third / "plugin.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["id"] = "com.example.bank"
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        bank_provider.set_provider("com.example.bank")
        shutil.rmtree(third)
        info = bank_provider.resolve()
        self.assertEqual(BANK, info["plugin_id"])
        self.assertIn("com.example.bank", info["fallback_reason"])

    def test_08_corrupt_config_is_treated_as_unset(self) -> None:
        bank_provider.state_path().parent.mkdir(parents=True, exist_ok=True)
        bank_provider.state_path().write_text("{ 这不是 JSON", encoding="utf-8")
        info = bank_provider.resolve()
        self.assertEqual(BANK, info["plugin_id"])
        self.assertEqual("", info["fallback_reason"])


class ProviderChannelTest(unittest.TestCase):
    def test_09_shared_and_per_tab_channels_are_split(self) -> None:
        """跨页签共享的通道走 provider；题篮与浏览类按页签自身 id 走，天然多库并存。"""
        self.assertIn("bank.get", bank_provider.SHARED_METHODS)
        self.assertIn("bank.create", bank_provider.SHARED_METHODS)
        self.assertIn("bank.list", bank_provider.PER_TAB_METHODS)
        self.assertIn("basket.add", bank_provider.PER_TAB_METHODS)
        self.assertFalse(set(bank_provider.SHARED_METHODS) & set(bank_provider.PER_TAB_METHODS),
                         "一个方法不能既走 provider 又走页签自身 id")

    def test_10_host_relay_uses_the_resolved_provider(self) -> None:
        source = (ROOT / "static" / "js" / "stage.js").read_text(encoding="utf-8")
        self.assertIn("fetchJson(\"/api/bank/provider\")", source, "宿主没向底座取 provider")
        self.assertIn("function bankProviderBase()", source)
        self.assertIn("var sharedBase = bankProviderBase();", source)
        # 取不到配置也要能用：默认值留在宿主侧兜底
        self.assertIn('var BANK_PROVIDER_DEFAULT = "org.jiuzhang.core-bank"', source)

    def test_11_switching_provider_requires_a_write_token(self) -> None:
        from app.api import bank as bank_api
        from app.core.security import require_write_token

        def route_for(path: str, method: str):
            # 同一路径上 GET 与 POST 是两条 route：按方法挑，挑错了断言就成了永真/永假
            for item in bank_api.router.routes:
                if item.path == path and method in (item.methods or set()):
                    return item
            return None

        read = route_for("/api/bank/provider", "GET")
        write = route_for("/api/bank/provider", "POST")
        candidates = route_for("/api/bank/provider/candidates", "GET")
        self.assertIsNotNone(read)
        self.assertIsNotNone(candidates)

        def guards(route) -> list:
            return [dep.call for dep in route.dependant.dependencies if hasattr(dep, "call")]

        self.assertIn(require_write_token, guards(write),
                      "切换活跃题库是修改类操作，必须鉴权")
        self.assertNotIn(require_write_token, guards(read), "只读当前 provider 不该要令牌")
        self.assertNotIn(require_write_token, guards(candidates), "只读候选清单不该要令牌")


if __name__ == "__main__":
    unittest.main()
