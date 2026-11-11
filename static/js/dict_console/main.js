/**
 * 控制台装配：全局设置 → 页签管理器 → 辅助栏 → 默认【数据看板】。
 * 分类页签经 openCategory 统一开口：已存在直接激活，不存在才新开（阶段一交互核心）。
 * 内嵌模式（?embedded=1&cat=xxx）：作为工作台画布页签时只渲染指定分类，
 * 顶栏/辅助栏/页签条由工作台接管，这里不再重复画一份。
 */
(function () {
  "use strict";

  function boot() {
    var params = new URLSearchParams(window.location.search);
    var embedded = params.get("embedded") === "1";
    if (embedded) document.body.classList.add("dc-embedded");

    var tabs = new window.DcTabs(
      document.getElementById("dcTabs"),
      document.getElementById("dcPanels"),
      { onChange: function (key) { window.DcSidebar.syncNav(key); } }
    );

    var ctx = {
      globals: window.DcGlobals,
      openCategory: function (key) {
        var category = window.DcCatalog.byKey(key);
        if (!category) return;
        tabs.open(category.key, category.title, function (panel, tab) {
          window.DcPanels.renderCategory(panel, tab, ctx, category);
        });
      }
    };

    if (!embedded) {
      window.DcSidebar.init(ctx, {
        navList: document.getElementById("dcNavList"),
        backupBtn: document.getElementById("dcBackupBtn"),
        importBtn: document.getElementById("dcImportBtn"),
        opsState: document.getElementById("dcOpsState")
      });
    }

    var wanted = embedded ? String(params.get("cat") || "") : "";
    if (embedded && wanted && window.DcCatalog.byKey(wanted)) {
      ctx.openCategory(wanted);
    } else {
      tabs.open("dashboard", "数据看板", function (panel, tab) {
        window.DcPanels.renderDashboard(panel, tab, ctx);
      }, { pinned: true });
    }

    window.DcGlobals.init({
      stage: document.getElementById("dcStage"),
      subject: document.getElementById("dcSubject"),
      textbook: document.getElementById("dcTextbook")
    }, document.getElementById("dcGlobalsState")).catch(function () {
      /* 失败原因已写进辅助栏状态行，画布照常可用 */
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();