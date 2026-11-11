/**
 * 控制台装配：全局设置 → 页签管理器 → 辅助栏 → 默认【数据看板】。
 * 分类页签经 openCategory 统一开口：已存在直接激活，不存在才新开（阶段一交互核心）。
 * 内嵌模式（?embedded=1&cat=xxx）：作为工作台画布页签时只渲染指定分类，
 * 顶栏/辅助栏/页签条由工作台接管，这里不再重复画一份。
 * 二级标签状态：URL 的 cat/sub 参数 + localStorage 双写，刷新后停在原标签。
 */
(function () {
  "use strict";

  var SUB_STORE_KEY = "jzo.dictConsole.subtabs.v1";

  function readSubMemory() {
    try {
      var raw = window.localStorage.getItem(SUB_STORE_KEY);
      var saved = raw ? JSON.parse(raw) : {};
      return saved && typeof saved === "object" ? saved : {};
    } catch (error) {
      return {};
    }
  }

  function writeSubMemory(memory) {
    try {
      window.localStorage.setItem(SUB_STORE_KEY, JSON.stringify(memory));
    } catch (error) { /* 隐私模式写不进去也不挡切换 */ }
  }

  function defaultSub(category) {
    var subs = window.DcCatalog.subsOf(category);
    return subs.length ? subs[0].key : "";
  }

  function replaceRoute(catKey, subKey) {
    try {
      var url = new URL(window.location.href);
      if (catKey) url.searchParams.set("cat", catKey);
      else url.searchParams.delete("cat");
      if (subKey) url.searchParams.set("sub", subKey);
      else url.searchParams.delete("sub");
      window.history.replaceState(null, "", url.pathname + url.search + url.hash);
    } catch (error) { /* 老浏览器不支持 URL 时退回纯 localStorage 记忆 */ }
  }

  function boot() {
    var params = new URLSearchParams(window.location.search);
    var embedded = params.get("embedded") === "1";
    if (embedded) document.body.classList.add("dc-embedded");

    var subMemory = readSubMemory();

    var ctx = {
      globals: window.DcGlobals,
      subFor: function (categoryKey) {
        var routed = params.get("cat") === categoryKey ? params.get("sub") : "";
        return routed || subMemory[categoryKey] || "";
      },
      rememberSub: function (categoryKey, subKey) {
        if (!subKey) return;
        subMemory[categoryKey] = subKey;
        writeSubMemory(subMemory);
        params.set("cat", categoryKey);
        params.set("sub", subKey);
        replaceRoute(categoryKey, subKey);
      },
      openCategory: function (key) {
        var category = window.DcCatalog.byKey(key);
        if (!category) return;
        tabs.open(category.key, category.title, function (panel, tab) {
          window.DcPanels.renderCategory(panel, tab, ctx, category);
        });
      },
      openDict: function (categoryKey, table) {
        var category = window.DcCatalog.byKey(categoryKey);
        var sub = window.DcCatalog.subOf(category, table);
        if (!category || !sub) return;
        tabs.open("dict:" + sub.key, sub.label, function (panel, tab) {
          window.DcPanels.renderDict(panel, tab, ctx, category, sub);
        });
      }
    };

    var tabs = new window.DcTabs(
      document.getElementById("dcTabs"),
      document.getElementById("dcPanels"),
      { onChange: function (key) {
        var category = window.DcCatalog.byKey(key);
        if (category) {
          replaceRoute(key, subMemory[key] || defaultSub(category));
        } else {
          params.delete("cat");
          params.delete("sub");
          replaceRoute(null, null);
        }
      } }
    );

    if (!embedded) {
      window.DcSidebar.init(ctx, {
        navList: document.getElementById("dcNavList"),
        backupBtn: document.getElementById("dcBackupBtn"),
        importBtn: document.getElementById("dcImportBtn"),
        opsState: document.getElementById("dcOpsState")
      });
    }

    var wanted = String(params.get("cat") || "");
    if (window.DcCatalog.byKey(wanted)) {
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
    }, document.getElementById("dcGlobalsState"), {
      toggle: document.getElementById("dcGlobalsToggle"),
      panel: document.getElementById("dcGlobalsPanel"),
      confirm: document.getElementById("dcGlobalsConfirm"),
      label: document.getElementById("dcGlobalsToggleLabel")
    }).catch(function () {
      /* 失败原因已写进辅助栏状态行，画布照常可用 */
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
