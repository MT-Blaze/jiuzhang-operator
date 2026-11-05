/**
 * stage_frame.js —— stage.js 的「页签按钮」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var MAX_LIVE_FRAMES = deps.MAX_LIVE_FRAMES;
    var PROTOCOL = deps.PROTOCOL;
    var REQUEST_TIMEOUT_MS = deps.REQUEST_TIMEOUT_MS;
    var SANDBOX = deps.SANDBOX;
    var applySleepPolicy = deps.applySleepPolicy;
    var bodyEl = deps.bodyEl;
    var deliverBankQuery = deps.deliverBankQuery;
    var deliverEditorIntent = deps.deliverEditorIntent;
    var dismissGroup = deps.dismissGroup;
    var dock = deps.dock;
    var emit = deps.emit;
    var findTab = deps.findTab;
    var heavyLiveFrames = deps.heavyLiveFrames;
    var hydrateConsole = deps.hydrateConsole;
    var liveFrames = deps.liveFrames;
    var orderPluginTabs = deps.orderPluginTabs;
    var paintGroupStates = deps.paintGroupStates;
    var priorityOf = deps.priorityOf;
    var pushParams = deps.pushParams;
    var setImmersive = deps.setImmersive;
    var stageState = deps.stageState;
    var tabsCore = deps.tabsCore;
    var tabsEl = deps.tabsEl;
    var toggleImmersive = deps.toggleImmersive;
    var touch = deps.touch;

  // ---------- 页签按钮 ----------
  function buildTabButton(tab) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "ws-tab";
    button.id = "wsTab_" + tab.key.replace(/[^a-zA-Z0-9_-]/g, "_");
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", "false");
    button.setAttribute("aria-controls", tab.panel.id);
    button.setAttribute("data-tab", tab.key);

    var label = document.createElement("span");
    label.className = "ws-tab-label";
    label.textContent = tab.title;   // 插件名是不可信清单内容，只能 textContent
    button.appendChild(label);

    var state = document.createElement("span");
    state.className = "ws-tab-state";
    state.setAttribute("aria-hidden", "true");
    button.appendChild(state);
    tab.stateEl = state;

    if (tab.closable) {
      var close = document.createElement("span");
      close.className = "ws-tab-close";
      close.setAttribute("role", "button");
      close.setAttribute("tabindex", "0");
      close.setAttribute("aria-label", "关闭" + tab.title);
      close.textContent = "\u00d7";
      close.addEventListener("click", function (event) {
        event.stopPropagation();
        closeTab(tab.key);
      });
      close.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          event.stopPropagation();
          closeTab(tab.key);
        }
      });
      button.appendChild(close);
      tab.closeEl = close;
    }

    button.addEventListener("click", function () { activate(tab.key); });
    // 双击页签=沉浸全屏（军令 #16 模块三第 1 条）。单击仍照常切页，两次手势互不牺牲。
    button.addEventListener("dblclick", function (event) {
      if (event.target && event.target.closest && event.target.closest(".ws-tab-close")) return;
      event.preventDefault();
      toggleImmersive(tab.key);
    });
    tab.button = button;
    return button;
  }

  function paintTabState(tab) {
    if (!tab.stateEl) return;
    if (tab.kind !== "plugin") {
      tab.stateEl.textContent = "";
      return;
    }
    tab.stateEl.textContent = tab.state === "live" ? "" : "休眠";
    tab.button.setAttribute("data-state", tab.state);
    tab.button.setAttribute("title", tab.state === "live" ? tab.title : tab.title + "（已休眠，点击唤醒）");
  }

  // ---------- iframe 挂载与协议 ----------
  function mountFrame(tab) {
    if (tab.state === "live") return Promise.resolve(tab);
    var panel = tab.panel;
    panel.textContent = "";

    var frame = document.createElement("iframe");
    frame.className = "ws-plugin-frame";
    frame.setAttribute("sandbox", SANDBOX);
    frame.setAttribute("title", (tab.plugin.name || tab.plugin.id) + " 画布");
    frame.setAttribute("loading", "lazy");
    frame.src = tab.plugin.entry_url;
    tab.frame = frame;
    tab.pending = new Map();
    panel.appendChild(frame);

    tab.state = "live";
    paintTabState(tab);

    return new Promise(function (resolve) {
      var settled = false;
      var timer = window.setTimeout(function () {
        if (settled) return;
        settled = true;
        dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」激活超时（30s），已保留页签但不再等待。", "plugin.timeout");
        resolve(tab);
      }, REQUEST_TIMEOUT_MS);

      frame.addEventListener("load", function () {
        request(tab, "plugin.activate", { slot: "stage.center" })
          .then(function (result) {
            if (settled) return;
            settled = true;
            window.clearTimeout(timer);
            tab.ready = Boolean(result && result.ready);
            dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」已挂载" + (tab.ready ? "并就绪。" : "，但未回 ready。"), "plugin.mounted");
            pushParams(tab);
            deliverEditorIntent(tab);
            deliverBankQuery(tab);
            resolve(tab);
          })
          .catch(function (error) {
            if (settled) return;
            settled = true;
            window.clearTimeout(timer);
            tab.ready = false;
            dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」激活失败：" + error.message, "plugin.error");
            resolve(tab);
          });
      });

      frame.addEventListener("error", function () {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        showFrameError(tab, "插件入口加载失败：" + String(tab.plugin.entry_url || ""));
        resolve(tab);
      });
    });
  }

  function showFrameError(tab, message) {
    tab.state = "error";
    tab.frame = null;
    tab.panel.textContent = "";
    var box = document.createElement("div");
    box.className = "ws-frame-error";
    box.setAttribute("role", "alert");
    box.textContent = message + "（其余页签不受影响，可关闭本页重试）";
    tab.panel.appendChild(box);
    paintTabState(tab);
  }

  function hibernate(tab, reason) {
    if (tab.kind !== "plugin" || tab.state !== "live") return;
    // 尽力通知，不等回复：休眠不能被一个装死的插件拖住
    notify(tab, "plugin.deactivate", { reason: reason || "lru" });
    if (tab.frame && tab.frame.parentNode) tab.frame.parentNode.removeChild(tab.frame);
    tab.frame = null;
    tab.state = "sleep";
    tab.ready = false;
    if (tab.pending) tab.pending.clear();
    tab.panel.textContent = "";
    var note = document.createElement("p");
    note.className = "ws-frame-note";
    note.textContent = "此页签已休眠（同时存活的插件页最多 " + MAX_LIVE_FRAMES + " 个）。点页签即唤醒。";
    tab.panel.appendChild(note);
    paintTabState(tab);
    dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」已休眠" + (reason ? "（" + reason + "）" : "") + "。", "stage.tab.sleep");
    emit("stage.tab.sleep", { key: tab.key, pluginId: tab.plugin.id });
  }

  /** 深休眠名额只数重型页签：light 插件后台只是浅休眠，不挤这 3 个常驻位。 */
  function enforceLru() {
    var live = heavyLiveFrames();
    while (live.length > MAX_LIVE_FRAMES) {
      var oldest = tabsCore.lruVictim(live, stageState.activeKey);
      if (!oldest) break;   // 全是活动页：不硬摘，宁可多留一个也不打断用户
      hibernate(oldest, "LRU");
      live = heavyLiveFrames();
    }
  }

  function request(tab, method, payload) {
    return new Promise(function (resolve, reject) {
      if (!tab.frame || !tab.frame.contentWindow) {
        reject(new Error("插件页未在运行"));
        return;
      }
      stageState.requestSeq += 1;
      var id = "r" + stageState.requestSeq + "_" + Date.now().toString(36);
      var timer = window.setTimeout(function () {
        if (!tab.pending || !tab.pending.has(id)) return;
        tab.pending.delete(id);
        reject(new Error("插件响应超时（" + Math.round(REQUEST_TIMEOUT_MS / 1000) + "s）"));
      }, REQUEST_TIMEOUT_MS);

      tab.pending.set(id, {
        resolve: function (result) { window.clearTimeout(timer); resolve(result); },
        reject: function (error) { window.clearTimeout(timer); reject(error); }
      });

      try {
        tab.frame.contentWindow.postMessage({
          protocol: PROTOCOL,
          id: id,
          kind: "request",
          method: method,
          payload: payload || {}
        }, "*");
      } catch (error) {
        tab.pending.delete(id);
        window.clearTimeout(timer);
        reject(error);
      }
    });
  }

  function notify(tab, event, payload) {
    if (!tab.frame || !tab.frame.contentWindow) return;
    try {
      tab.frame.contentWindow.postMessage({
        protocol: PROTOCOL,
        kind: "notification",
        event: event,
        payload: payload || null
      }, "*");
    } catch (error) {
      // 通知丢了不致命，记一笔就够
      dock("向插件「" + (tab.plugin.name || tab.plugin.id) + "」发通知失败：" + error.message, "plugin.error");
    }
  }

  /** 广播覆盖中栏活页签与右栏面板：选区、回流与参数变化都得收到。 */
  function broadcast(event, payload) {
    var targets = liveFrames().concat(stageState.panels.filter(function (panel) { return panel.frame; }));
    targets.forEach(function (tab) { notify(tab, event, payload); });
  }

  // ---------- 页签生命周期 ----------
  function addTab(tab) {
    tab.order = tab.order == null ? ++stageState.openSeq : tab.order;
    stageState.tabs.push(tab);
    if (tabsEl) tabsEl.appendChild(buildTabButton(tab));
    if (bodyEl) bodyEl.appendChild(tab.panel);
    tab.panel.hidden = true;
    orderPluginTabs();
    return tab;
  }

  function activate(key) {
    var tab = findTab(key) || ensureNative(key);
    if (!tab) return;
    stageState.tabs.forEach(function (item) {
      var on = item.key === key;
      item.panel.hidden = !on;
      item.button.setAttribute("aria-selected", String(on));
      item.button.setAttribute("tabindex", on ? "0" : "-1");
    });
    stageState.activeKey = key;
    touch(tab);
    dismissGroup(tab);
    paintGroupStates();
    hydrateConsole(key);
    applyFullscreen(tab);
    if (tab.kind === "plugin" && tab.state !== "live") {
      dock("唤醒插件「" + (tab.plugin.name || tab.plugin.id) + "」…", "stage.tab.wake");
      mountFrame(tab).then(function () {
        enforceLru();
        applySleepPolicy();
        deliverEditorIntent(tab);
      });
    } else {
      enforceLru();
      applySleepPolicy();
      deliverEditorIntent(tab);
    }
    emit("stage.tab.activated", { key: key, pluginId: tab.plugin ? tab.plugin.id : null });
  }

  /**
   * fullscreen 模式：收掉左、右、下三区，让插件独占视口。
   * 只翻 data-fullscreen 属性，绝不动 data-side/data-ctx——用户的折叠偏好
   * 是另一本账，退出全屏时必须原样还在。
   */
  function applyFullscreen(tab) {
    var page = document.querySelector(".ws-page");
    if (!page) return;
    // tab 可能是 null（例如最后一枚全屏页签被关掉）：必须退出全屏，否则空画布还压着三区
    var want = Boolean(tab && tab.plugin && tab.plugin.stage && tab.plugin.stage.mode === "fullscreen");
    if (want) page.setAttribute("data-fullscreen", "on");
    else page.removeAttribute("data-fullscreen");
  }

  function closeTab(key) {
    var index = -1;
    for (var i = 0; i < stageState.tabs.length; i += 1) {
      if (stageState.tabs[i].key === key) { index = i; break; }
    }
    if (index < 0) return;
    var tab = stageState.tabs[index];
    if (!tab.closable) return;
    if (stageState.immersiveKey === key) setImmersive(false, "");   // 沉浸的那页被关，全屏也一起退
    if (tab.kind === "plugin" && tab.state === "live") hibernate(tab, "close");
    if (tab.button.parentNode) tab.button.parentNode.removeChild(tab.button);
    // 原生页签只关页签、面板留在 DOM 里（hidden）：重建时复用同一块面板，
    // 控制台 iframe 不必重新加载；插件页签则整块摘走，后台不留文档。
    if (tab.kind === "native") tab.panel.hidden = true;
    else if (tab.panel.parentNode) tab.panel.parentNode.removeChild(tab.panel);
    stageState.tabs.splice(index, 1);
    // 画布允许彻底空着：不补任何兜底页、也不写占位字，中栏保持纯净留白
    orderPluginTabs();   // 组里少了一页，下拉与计数必须当场跟上
    dock("已关闭页签「" + (tab.title || key) + "」。", "stage.tab.closed");
    emit("stage.tab.closed", { key: key });
    if (stageState.activeKey === key) {
      var next = stageState.tabs[index] || stageState.tabs[index - 1] || stageState.tabs[0];
      if (next) {
        activate(next.key);
      } else {
        stageState.activeKey = null;
        applyFullscreen(null);
      }
    }
  }

  function registerNative(options, spawn) {
    var panel = document.getElementById(options.panelId);
    if (!panel) return null;
    stageState.nativeDefs[options.key] = options;
    // lazy：只登记定义、不建页签。启动时控制台绝不许自己冒出来（主公 2026-11-01），
    // 老师点「设置与控制台」或 ensureNative 时才按同一份定义现场建。
    if (options.lazy && spawn !== true) return null;
    var tab = {
      key: options.key,
      kind: "native",
      title: options.title,
      closable: options.closable !== false,
      panel: panel,
      state: "live",
      lastUsed: Date.now()
    };
    addTab(tab);
    return tab;
  }

  /** 原生页签被关掉后按登记表重建；控制台的左栏入口因此关掉也能再打开。 */
  function ensureNative(key) {
    var existing = findTab(key);
    if (existing) return existing;
    var def = stageState.nativeDefs[key];
    return def ? registerNative(def, true) : null;
  }

  /** 打开（或唤醒）一个插件页签；singleton=false 时允许同一插件开多个页签。 */
  function openPlugin(plugin) {
    if (!plugin || !plugin.entry_url) return null;
    var singleton = !(plugin.stage && plugin.stage.singleton === false);
    var baseKey = "plugin:" + plugin.id;
    var key = baseKey;
    var existing = findTab(key);
    if (singleton && existing) {
      existing.plugin = plugin;   // 覆盖安装后清单可能变了
      existing.button.querySelector(".ws-tab-label").textContent = plugin.name || plugin.id;
      activate(key);
      return existing;
    }

    var serial = 1;
    if (!singleton) {
      while (findTab(key)) {
        serial += 1;
        key = baseKey + "#" + serial;
      }
    }
    var title = plugin.name || plugin.id;
    if (!singleton && serial > 1) title += " #" + serial;

    var panel = document.createElement("section");
    panel.className = "ws-tab-panel";
    panel.id = "wsPanel_" + key.replace(/[^a-zA-Z0-9_-]/g, "_");
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-label", title + " 画布");
    panel.setAttribute("data-tab", key);

    var tab = {
      key: key,
      kind: "plugin",
      title: title,
      closable: true,
      panel: panel,
      plugin: plugin,
      state: "sleep",
      ready: false,
      pending: new Map(),
      lastUsed: Date.now(),
      priority: priorityOf({ plugin: plugin })
    };
    addTab(tab);
    activate(key);
    dock("已为插件「" + title + "」开一个画布页。", "stage.tab.opened");
    emit("stage.tab.opened", { key: key, pluginId: plugin.id });
    return tab;
  }

  /**
   * 覆盖安装 / 热插拔后刷新已打开页签的清单数据。
   * 运行中的 iframe 不主动重载（规范 §4：新代码要刷新页面才加载），只更新标题与
   * 优先级；页签位置随之重排，避免“装完还挂在旧坑位”的错觉。
   */
  function updatePlugin(plugin) {
    if (!plugin || !plugin.id) return;
    stageState.tabs.forEach(function (tab) {
      if (tab.kind !== "plugin" || !tab.plugin || tab.plugin.id !== plugin.id) return;
      tab.plugin = plugin;
      var suffix = tab.key.indexOf("#") >= 0 ? tab.key.slice(tab.key.indexOf("#")) : "";
      tab.title = (plugin.name || plugin.id) + suffix;
      var label = tab.button && tab.button.querySelector(".ws-tab-label");
      if (label) label.textContent = tab.title;
      tab.priority = priorityOf(tab);
    });
    orderPluginTabs();
  }

  /**
   * 插件热更新后重新水合（PLUGIN_SPEC §1.7）——这是「运行中的 iframe 不主动重载」
   * 那条默认规则的唯一例外：代码目录已被新版本覆盖，旧脚本必须退场。
   * 正占据中央画布的那个：休眠 → 立刻重挂，加载新代码；其余页签只摘掉旧 iframe，
   * 下次点开自然加载新代码。全程无需刷新浏览器、无需重启底座。
   */
  function rehydratePlugin(pluginId) {
    if (!pluginId) return false;
    var touched = false;
    stageState.tabs.forEach(function (tab) {
      if (tab.kind !== "plugin" || !tab.plugin || tab.plugin.id !== pluginId) return;
      touched = true;
      if (tab.state === "live" || tab.state === "error") hibernate(tab, "plugin.updated");
      if (tab.key === stageState.activeKey) {
        mountFrame(tab).then(function () {
          dock("插件「" + (tab.plugin.name || tab.plugin.id) + "」已按新版本重新水合。",
            "plugin.updated");
        });
      }
    });
    if (touched) orderPluginTabs();
    return touched;
  }

  // ---------- 右栏辅助面板（sidebar.right） ----------
  // 面板与画布页签共用同一套 jzo-plugin/1 协议和 Host API：插件只交出一个 iframe，
  // 身份由宿主按清单绑定，bank.* / basket.* / draft.* 的写令牌仍留在宿主侧。
  function attachPanel(frame, plugin) {
    var handle = {
      kind: "panel",
      key: "panel:" + ((plugin && plugin.id) || "unknown"),
      plugin: plugin,
      frame: frame,
      pending: new Map(),
      relayWindow: 0,
      relayCount: 0
    };
    stageState.panels.push(handle);
    return {
      request: function (method, payload) { return request(handle, method, payload); },
      notify: function (event, payload) { return notify(handle, event, payload); },
      detach: function () {
        var index = stageState.panels.indexOf(handle);
        if (index >= 0) stageState.panels.splice(index, 1);
        if (handle.pending) handle.pending.clear();
      }
    };
  }

    return {
      activate: activate,
      addTab: addTab,
      applyFullscreen: applyFullscreen,
      attachPanel: attachPanel,
      broadcast: broadcast,
      buildTabButton: buildTabButton,
      closeTab: closeTab,
      enforceLru: enforceLru,
      ensureNative: ensureNative,
      hibernate: hibernate,
      mountFrame: mountFrame,
      notify: notify,
      openPlugin: openPlugin,
      paintTabState: paintTabState,
      registerNative: registerNative,
      rehydratePlugin: rehydratePlugin,
      request: request,
      showFrameError: showFrameError,
      updatePlugin: updatePlugin,
    };
  }

  global.JzoStageFrame = { create: create };
})(window);
