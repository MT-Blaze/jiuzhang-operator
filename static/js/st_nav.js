/**
 * st_nav.js —— settings.js 的「分区导航」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var loadBackup = deps.loadBackup;

  // ============ 左菜单 + 右面板：分区导航 ============
  var PANEL_KEYS = ["workspace", "plugin", "backup", "system"];
  var navItems = {};
  var panelEls = {};
  PANEL_KEYS.forEach(function (key) {
    navItems[key] = document.getElementById("stNav" + key.charAt(0).toUpperCase() + key.slice(1));
    panelEls[key] = document.getElementById("stPanel" + key.charAt(0).toUpperCase() + key.slice(1));
  });
  var activePanel = "workspace";

  function selectPanel(key, focusNav) {
    if (PANEL_KEYS.indexOf(key) === -1) return;
    activePanel = key;
    PANEL_KEYS.forEach(function (name) {
      var tab = navItems[name];
      var panel = panelEls[name];
      var on = name === key;
      if (tab) {
        tab.classList.toggle("is-active", on);
        tab.setAttribute("aria-selected", on ? "true" : "false");
        tab.tabIndex = on ? 0 : -1;
        if (on && focusNav) tab.focus();
      }
      if (panel) panel.hidden = !on;
    });
    if (key === "backup") loadBackup();
  }

  PANEL_KEYS.forEach(function (name) {
    var tab = navItems[name];
    if (!tab) return;
    tab.addEventListener("click", function () { selectPanel(name, false); });
    tab.addEventListener("keydown", function (event) {
      var index = PANEL_KEYS.indexOf(name);
      var step = (event.key === "ArrowDown" || event.key === "ArrowRight") ? 1
        : (event.key === "ArrowUp" || event.key === "ArrowLeft") ? -1 : 0;
      if (event.key === "Home") step = -PANEL_KEYS.length;
      if (event.key === "End") step = PANEL_KEYS.length - index;
      if (!step) return;
      event.preventDefault();
      var next = PANEL_KEYS[(index + step + PANEL_KEYS.length) % PANEL_KEYS.length];
      selectPanel(next, true);
    });
  });

  // ============ 插件分区：左菜单下的二级菜单（页签，不做弹窗） ============
  var PLUGIN_TABS = ["manage", "update", "index", "install"];
  var pluginTabButtons = {};
  var pluginTabPanels = {};
  PLUGIN_TABS.forEach(function (key) {
    var suffix = key.charAt(0).toUpperCase() + key.slice(1);
    pluginTabButtons[key] = document.getElementById("stPluginTab" + suffix);
    pluginTabPanels[key] = document.getElementById("stPluginPanel" + suffix);
  });

  function selectPluginTab(key, focusTab) {
    if (PLUGIN_TABS.indexOf(key) === -1) return;
    PLUGIN_TABS.forEach(function (name) {
      var tab = pluginTabButtons[name];
      var panel = pluginTabPanels[name];
      var on = name === key;
      if (tab) {
        tab.classList.toggle("is-active", on);
        tab.setAttribute("aria-selected", on ? "true" : "false");
        tab.tabIndex = on ? 0 : -1;
        if (on && focusTab) tab.focus();
      }
      if (panel) panel.hidden = !on;
    });
  }

  PLUGIN_TABS.forEach(function (name) {
    var tab = pluginTabButtons[name];
    if (!tab) return;
    tab.addEventListener("click", function () { selectPluginTab(name, false); });
    tab.addEventListener("keydown", function (event) {
      var index = PLUGIN_TABS.indexOf(name);
      var step = (event.key === "ArrowRight" || event.key === "ArrowDown") ? 1
        : (event.key === "ArrowLeft" || event.key === "ArrowUp") ? -1 : 0;
      if (event.key === "Home") step = -PLUGIN_TABS.length;
      if (event.key === "End") step = PLUGIN_TABS.length - index;
      if (!step) return;
      event.preventDefault();
      var next = PLUGIN_TABS[(index + step + PLUGIN_TABS.length) % PLUGIN_TABS.length];
      selectPluginTab(next, true);
    });
  });

  // 宿主页签可以指定落在哪一区、哪一二级页签：
  // 首次用地址参数 ?panel=plugin&tab=update，后续用同源 postMessage。
  function requestPanelFromHost(key, sub) {
    if (PANEL_KEYS.indexOf(key) === -1) return;
    selectPanel(key, false);
    if (key === "plugin" && sub) selectPluginTab(String(sub), false);
  }

  var urlPanel = /[?&]panel=([^&]+)/.exec(window.location.search);
  var urlTab = /[?&]tab=([^&]+)/.exec(window.location.search);
  if (urlPanel) {
    try {
      requestPanelFromHost(decodeURIComponent(urlPanel[1]), urlTab ? decodeURIComponent(urlTab[1]) : "");
    } catch (error) { /* 非法参数回落默认区 */ }
  }
  window.addEventListener("message", function (event) {
    if (event.origin !== window.location.origin) return;
    var data = event.data;
    if (data && data.jzo === "console.panel") {
      requestPanelFromHost(String(data.panel || ""), data.tab ? String(data.tab) : "");
    }
  });

    return {
      PANEL_KEYS: PANEL_KEYS,
      PLUGIN_TABS: PLUGIN_TABS,
      activePanel: activePanel,
      navItems: navItems,
      panelEls: panelEls,
      pluginTabButtons: pluginTabButtons,
      pluginTabPanels: pluginTabPanels,
      requestPanelFromHost: requestPanelFromHost,
      selectPanel: selectPanel,
      selectPluginTab: selectPluginTab,
      urlPanel: urlPanel,
      urlTab: urlTab,
    };
  }

  global.JzoStNav = { create: create };
})(window);
