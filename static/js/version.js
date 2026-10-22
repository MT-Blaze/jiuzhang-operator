(function () {
  "use strict";

  // 版本号的唯一事实来源是底座：/healthz 回的 version（即 app/__init__.py 的
  // __version__）。页面里写死的 v0.x.y 只是「无 JS / 底座离线」时的兜底文案，
  // 由 tests/test_version_consistency.py 锁死，防止两处再次跑偏。
  //
  // 为什么要有这个文件：曾经右上角徽章被一个陈留的旧服务进程盖成旧版本号，
  // 页面写死的文案与真实底座各说各话。改成一律以底座为准，谁在跑就显示谁。

  function stampAll(version) {
    if (!version) return;
    var text = "v" + version;
    var nodes = document.querySelectorAll("[data-app-version]");
    for (var i = 0; i < nodes.length; i += 1) {
      if (nodes[i].textContent !== text) nodes[i].textContent = text;
    }
  }

  async function refresh() {
    try {
      var response = await fetch("/healthz", {
        cache: "no-store",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) return;
      var data = await response.json();
      stampAll(data.version);
    } catch (error) {
      // 底座离线：保留页面里的兜底文案，不闪空、不报错。
    }
  }

  refresh();
  window.setInterval(refresh, 30000);
})();
