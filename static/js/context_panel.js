/**
 * ContextPanel：右栏插槽的插件宿主（sidebar.right，军令 #13 + #15）。
 *
 * 主权交替（军令 #15 任务 4）：
 *   - 右栏默认由 AI 助手插件（org.jiuzhang.chat）入住，不再折叠；
 *   - 当前画布页签的插件若自己声明了 sidebar.right，右栏暂时由它接管；
 *   - 切走该页签（或关掉它），插槽自动归还助手。
 * 插槽里永远只有一个 iframe：同一时刻只有一个主人，避免两个插件抢同一块 DOM。
 *
 * 边界与画布页签一致：iframe 给 allow-scripts + allow-modals（后者只为插件里
 * 用户当场点下的 window.print()；Chromium 会静默丢弃缺 allow-modals 的沙箱打印），
 * 不给 allow-same-origin（不透明源），协议走 jzo-plugin/1，
 * Host API 由 stage.js 统一转发，写令牌与数据库都不落到插件手里。
 */
(function () {
  "use strict";

  var SLOT = "sidebar.right";
  var SANDBOX = "allow-scripts allow-modals";
  // 底座出厂随包的 AI 助手插件：右栏的默认住户。清单里查不到它时插槽给出可读兜底，
  // 底座不再自带对话流——那等于给 AI 留一条绕过 Host API 的捷径（军令 #15 任务 1）。
  var ASSISTANT_PLUGIN_ID = "org.jiuzhang.chat";

  var slotEl = document.getElementById("wsContextSlot");
  var bodyEl = document.getElementById("wsContextSlotBody");
  var titleEl = document.getElementById("wsContextSlotTitle");
  var badgeEl = document.getElementById("wsContextSlotBadge");

  var mounted = null;   // { plugin, handle, frame }
  var mountedKey = "";

  function dockError(text) {
    if (window.JzoBus && typeof window.JzoBus.emit === "function") {
      window.JzoBus.emit("region.dock", { text: text, topic: "context.panel.error" }, { source: "host" });
    }
  }

  function usable(plugin) {
    return Boolean(plugin && plugin.enabled !== false && plugin.entry_url
      && Array.isArray(plugin.slots) && plugin.slots.indexOf(SLOT) >= 0);
  }

  function byId(plugins, id) {
    return (plugins || []).filter(function (plugin) {
      return plugin && plugin.id === id;
    })[0] || null;
  }

  /** 助手不抢自己的插槽：它本来就是默认住户。 */
  function assistantPlugin(plugins) {
    var byName = byId(plugins, ASSISTANT_PLUGIN_ID);
    if (byName && byName.enabled !== false && byName.entry_url) return byName;
    return (plugins || []).filter(function (plugin) {
      return plugin && Array.isArray(plugin.capabilities)
        && plugin.capabilities.indexOf("assistant.chat") >= 0 && plugin.enabled !== false;
    })[0] || null;
  }

  /** 接管者只认「当前画布页签」那一个插件，不是「所有声明了槽的插件」。 */
  function claimant(plugins, activePluginId) {
    if (!activePluginId || activePluginId === ASSISTANT_PLUGIN_ID) return null;
    var plugin = byId(plugins, activePluginId);
    return usable(plugin) ? plugin : null;
  }

  function showFallback(reason) {
    if (!slotEl || !bodyEl) return;
    bodyEl.textContent = "";
    var note = document.createElement("p");
    note.className = "ws-context-slot-note";
    note.textContent = reason || "AI 助手插件未安装或被停用：右栏暂时没有住户。在左下【设置与控制台】装回 org.jiuzhang.chat 即可恢复。";
    bodyEl.appendChild(note);
    if (titleEl) titleEl.textContent = "AI 助手";
    if (badgeEl) badgeEl.textContent = "右栏待认领";
    slotEl.hidden = false;
  }

  function unmount() {
    if (mounted) {
      if (mounted.handle) {
        mounted.handle.notify("plugin.deactivate", { reason: "panel.unmount" });
        mounted.handle.detach();
      }
      if (mounted.frame && mounted.frame.parentNode) mounted.frame.parentNode.removeChild(mounted.frame);
    }
    mounted = null;
    mountedKey = "";
    if (bodyEl) bodyEl.textContent = "";
  }

  function mount(plugin, isAssistant) {
    var key = plugin.id + "@" + plugin.version;
    if (mounted && mountedKey === key) return;
    unmount();
    if (!window.JzoStage || typeof window.JzoStage.attachPanel !== "function") {
      // 舞台脚本没就位时宁可不挂：没有 Host API 的面板只是个空壳
      showFallback("底座舞台脚本未就位，右栏暂不挂载插件。");
      return;
    }

    var frame = document.createElement("iframe");
    frame.className = "ws-context-frame";
    frame.setAttribute("sandbox", SANDBOX);
    frame.setAttribute("title", (plugin.name || plugin.id) + " 右栏面板");
    frame.setAttribute("loading", "lazy");
    frame.src = plugin.entry_url;

    var handle = window.JzoStage.attachPanel(frame, plugin);
    mounted = { plugin: plugin, handle: handle, frame: frame };
    mountedKey = key;

    if (titleEl) titleEl.textContent = plugin.name || plugin.id;
    if (badgeEl) badgeEl.textContent = isAssistant ? "右栏助手" : "插件接管";
    if (slotEl) slotEl.hidden = false;
    if (bodyEl) {
      bodyEl.textContent = "";
      bodyEl.appendChild(frame);
    }

    frame.addEventListener("load", function () {
      handle.request("plugin.activate", { slot: SLOT }).then(function (result) {
        if (mounted && mounted.frame !== frame) return;
        if (result && result.ready) return;
        dockError("右栏插件「" + (plugin.name || plugin.id) + "」已挂载但未回 ready，右栏保留其界面。");
      }, function (error) {
        if (!mounted || mounted.frame !== frame) return;
        dockError("右栏插件「" + (plugin.name || plugin.id) + "」激活失败：" + error.message
          + "，右栏暂不挂载。");
        unmount();
        showFallback("右栏插件「" + (plugin.name || plugin.id) + "」激活失败：" + error.message);
      });
    });
  }

  var lastPlugins = [];

  /**
   * 由 workspace.js 调用：插件清单刷新、画布页签切换、页签关闭后都要重新对账。
   * @param {Array} plugins /api/plugins 的清单
   * @param {string} activePluginId 当前激活画布页签绑定的插件 id（原生页签传空）
   */
  function sync(plugins, activePluginId) {
    if (!slotEl || !bodyEl) return;
    lastPlugins = plugins || [];
    var target = claimant(lastPlugins, activePluginId);
    var isAssistant = false;
    if (!target) {
      target = assistantPlugin(lastPlugins);
      isAssistant = Boolean(target);
    }
    if (!target) {
      unmount();
      showFallback();
      return;
    }
    mount(target, isAssistant);
  }

  /** 左栏点「AI 助手」那一行：展开右栏并把主权归还助手。 */
  function reclaim() {
    var assistant = assistantPlugin(lastPlugins);
    if (!assistant) {
      showFallback();
      return false;
    }
    mount(assistant, true);
    return true;
  }

  window.JzoContextPanel = {
    sync: sync,
    reclaim: reclaim,
    slot: SLOT,
    assistantId: ASSISTANT_PLUGIN_ID,
    activeId: function () { return mounted ? mounted.plugin.id : null; }
  };
})();
