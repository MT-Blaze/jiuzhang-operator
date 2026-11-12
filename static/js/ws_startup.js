/**
 * 启动落脚点：上次停留的插件页签 → 启动行为设置 → 数据看板。
 *
 * 老师的手停在哪，下次打开就还在哪；只有首次打开（本地还没记账），
 * 或者缓存的插件已被卸载/停用，才轮到启动行为设置里的目标——
 * 后端没给可落地目标时，默认页就是数据看板。
 *
 * 只记插件 id，不记页签 DOM：页签由 stage 每次按插件清单重建。
 */
(function () {
  "use strict";

  var LAST_PLUGIN_KEY = "jzo.workspace.lastPlugin.v1";
  var DEFAULT_PLUGIN_ID = "org.jiuzhang.dashboard";

  function readLast() {
    try {
      return String(window.localStorage.getItem(LAST_PLUGIN_KEY) || "").trim();
    } catch (error) {
      return "";
    }
  }

  function remember(pluginId) {
    var id = String(pluginId || "").trim();
    if (!id) return;
    try {
      window.localStorage.setItem(LAST_PLUGIN_KEY, id);
    } catch (error) {
      /* 隐私模式不让写：记不住就按默认页走，不拿异常打断启动 */
    }
  }

  function forget() {
    try {
      window.localStorage.removeItem(LAST_PLUGIN_KEY);
    } catch (error) {
      /* 同上：清不掉也不影响页面继续用 */
    }
  }

  function findEnabled(plugins, pluginId) {
    var list = plugins || [];
    for (var i = 0; i < list.length; i += 1) {
      if (list[i] && list[i].id === pluginId && list[i].enabled !== false) return list[i];
    }
    return null;
  }

  function buttonFor(pluginListEl, pluginId) {
    if (!pluginListEl) return null;
    var buttons = pluginListEl.querySelectorAll(".ws-plugin-item");
    for (var i = 0; i < buttons.length; i += 1) {
      if (buttons[i].getAttribute("data-plugin-id") === pluginId) return buttons[i];
    }
    return null;
  }

  /** 进插件页；插件已不在（卸载/停用）返回 false，交给启动行为与默认页兜底。 */
  function enter(plugins, pluginId, enterPluginMode, pluginListEl) {
    var plugin = findEnabled(plugins, pluginId);
    if (!plugin) return false;
    enterPluginMode(plugin, buttonFor(pluginListEl, pluginId));
    return true;
  }

  function restore(plugins, enterPluginMode, pluginListEl) {
    var last = readLast();
    return last ? enter(plugins, last, enterPluginMode, pluginListEl) : false;
  }

  window.JzoWsStartup = {
    DEFAULT_PLUGIN_ID: DEFAULT_PLUGIN_ID,
    LAST_PLUGIN_KEY: LAST_PLUGIN_KEY,
    readLast: readLast,
    remember: remember,
    forget: forget,
    enter: enter,
    restore: restore
  };
})();
