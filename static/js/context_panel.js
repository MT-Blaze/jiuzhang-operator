/**
 * ContextPanel：右栏辅助面板的插件宿主（sidebar.right，军令 #13）。
 *
 * 契约（PLUGIN_SPEC §2.9）：插件在 plugin.json 的 slots 里声明 sidebar.right，
 * 底座就在右栏给它一个沙箱 iframe；没有插件认领时整块插槽隐藏，
 * 露出底座自带的「AI 副驾」——插件坏了/卸了，右栏也不会变成空白。
 *
 * 边界与画布页签一致：iframe 给 allow-scripts + allow-modals（后者只为插件里
 * 用户当场点下的 window.print()；Chromium 会静默丢弃缺 allow-modals 的沙箱打印），
 * 不给 allow-same-origin（不透明源），协议走 jzo-plugin/1，
 * Host API（bank.* / basket.* / draft.*）由 stage.js 统一转发，写令牌不落到插件手里。
 * 同一时刻只挂一个面板：多个插件都声明时，按 canvas 同一套排序取第一个。
 */
(function () {
  "use strict";

  var SLOT = "sidebar.right";
  var SANDBOX = "allow-scripts allow-modals";

  var slotEl = document.getElementById("wsContextSlot");
  var bodyEl = document.getElementById("wsContextSlotBody");
  var titleEl = document.getElementById("wsContextSlotTitle");
  var copilotEl = document.getElementById("wsCopilot");

  var mounted = null;   // { plugin, handle, frame }
  var mountedKey = "";

  function dockError(text) {
    if (window.JzoBus && typeof window.JzoBus.emit === "function") {
      window.JzoBus.emit("region.dock", { text: text, topic: "context.panel.error" }, { source: "host" });
    }
  }

  function priorityOf(plugin) {
    var value = plugin && plugin.stage && plugin.stage.priority;
    return typeof value === "number" ? value : 0;
  }

  function pick(plugins) {
    var list = (plugins || []).filter(function (plugin) {
      return plugin && plugin.enabled !== false && plugin.entry_url
        && Array.isArray(plugin.slots) && plugin.slots.indexOf(SLOT) >= 0;
    });
    list.sort(function (a, b) {
      var delta = priorityOf(b) - priorityOf(a);
      if (delta !== 0) return delta;
      return String(a.name || a.id || "").localeCompare(String(b.name || b.id || ""), "zh-CN");
    });
    return list[0] || null;
  }

  function showFallback() {
    if (slotEl) slotEl.hidden = true;
    if (copilotEl) copilotEl.hidden = false;
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

  function mount(plugin) {
    var key = plugin.id + "@" + plugin.version;
    if (mounted && mountedKey === key) return;
    unmount();
    if (!window.JzoStage || typeof window.JzoStage.attachPanel !== "function") {
      // 舞台脚本没就位时宁可不挂：没有 Host API 的面板只是个空壳
      showFallback();
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
    if (slotEl) slotEl.hidden = false;
    if (copilotEl) copilotEl.hidden = true;
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
          + "，已回退到 AI 副驾。");
        unmount();
        showFallback();
      });
    });
  }

  /** 由 workspace.js 在每次 /api/plugins 刷新后调用：清单变了就跟着换。 */
  function sync(plugins) {
    if (!slotEl || !bodyEl) return;
    var plugin = pick(plugins);
    if (!plugin) {
      unmount();
      showFallback();
      return;
    }
    mount(plugin);
  }

  window.JzoContextPanel = {
    sync: sync,
    slot: SLOT,
    activeId: function () { return mounted ? mounted.plugin.id : null; }
  };
})();
