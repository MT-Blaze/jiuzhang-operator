/**
 * 控制台装配：全局设置 → 页签管理器 → 辅助栏 → 默认【数据看板】。
 * 分类页签经 openCategory 统一开口：已存在直接激活，不存在才新开（阶段一交互核心）。
 */
(function () {
  "use strict";

  function boot() {
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

    window.DcSidebar.init(ctx, {
      navList: document.getElementById("dcNavList"),
      backupBtn: document.getElementById("dcBackupBtn"),
      importBtn: document.getElementById("dcImportBtn"),
      opsState: document.getElementById("dcOpsState")
    });

    tabs.open("dashboard", "数据看板", function (panel, tab) {
      window.DcPanels.renderDashboard(panel, tab, ctx);
    }, { pinned: true });

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