/**
 * 工作台宿主壳：左栏入口、右侧插槽主权交替、面板参数仲裁、底栏输出区与插件生命周期。
 *
 * 边界：宿主不带常驻助手。中栏是通用舞台，右栏只住「当前页签插件自己声明的
 * sidebar.right」——插件想看什么、想改什么、想去哪个页签，都得经 stage.js 的
 * Host API 白名单向底座申请，由本文件把状态快照与仲裁结果交出去（window.JzoWorkspace）。
 *
 * 安全：所有写接口由宿主代取一次性令牌；不可信文本一律走 textContent，不拼 innerHTML。
 */
(function () {
  "use strict";

  // --- State ---
  // 跨模块共享的可变态：拆文件后依赖按值传，只有挂在同一个对象上才写得到同一份账。
  var wsState = {
    installedPlugins: [],
    writeToken: null,
    // 老师亲手点过左栏没有？启动行为要等 /api/startup 回来才动手，
    // 网络慢时它会晚于第一次点击落地——那时绝不许再把画布抢去默认页。
    userPickedPlugin: false,
    // 左栏视图签名：清单、树、折叠态都没变就不动 DOM。整栏重建会把
    // mousedown 与 mouseup 之间的按钮换掉，点击就被浏览器吞成一次空点。
    pluginViewSignature: null,
    currentTask: "",
    activePlugin: null,
    // 右侧面板状态：values 是当前参数，revisions 记录人类
    // 手改次数。发请求时拍快照，AI 回来要改参数时只改「人没同时动过」的字段——
    // 人类的主动点击永远覆盖 AI 的自动设定。
    uiState: { pluginId: null, values: {}, revisions: {} },
    uiPanelControls: [],
    // 右栏主权：当前画布页签绑定的插件 id。
    // 它若声明了 sidebar.right 就接管右栏，否则右栏留空（默认折叠）。
    activeCanvasPluginId: "",
    // 输出日志区两本账：业务操作进运行日志，底座/内核事件进系统终端，互不串台。
    runtimeEntries: [],
    sysEntries: [],
    dockView: "log",
    // 底座被改坏时仍可直连 /settings 强制进同一套面板（防变砖兜底，见军令例外条款）。
    consoleFrameLoaded: false,
    consolePanelPending: null,
    updateNoticeCount: 0,
    legacyOrderMigrated: false,
    // data/plugin_state.json 里的那棵树同时供左栏与设置面板读取，
    // 「已启用列表顺序 100% 对齐左栏」因此由构造成立，不再靠浏览器 localStorage 记账。
    sidebarTree: [],
    collapsedFolders: {},   // 折叠只是视图态：留在内存，不落盘
    pluginSignature: null,
    knownPluginIds: {},
    dragDepth: 0,
  };

  // 录题工作台：它的收集筐是文件唯一的暂存处（军令 #27）。
  var EDITOR_PLUGIN_ID = "org.jiuzhang.editor";

  // --- DOM refs ---
  var stageTitle = document.getElementById("wsStageTitle");
  var pluginListEl = document.getElementById("wsPluginList");
  var pluginCountEl = document.getElementById("wsPluginCount");
  var dockToggle = document.getElementById("wsToggleDock");
  var dockClearBtn = document.getElementById("wsDockClear");
  var dockLog = document.getElementById("wsDockLog");
  var dockTabs = document.getElementById("wsDockTabs");


  // ---------- 拆出去的模块（PLUGIN_SPEC §2.8.1：单文件不超 800 行） ----------
  var wsDock = window.JzoWsDock.create({
    dockClearBtn: dockClearBtn,
    dockLog: dockLog,
    // 循环引用：dockOpen 归更下面的 wsRail，本块排得靠前，只能等它就位后再取。
    dockOpen: function () { return wsRail.dockOpen.apply(wsRail, arguments); },
    dockTabs: dockTabs,
    wsState: wsState,
  });
  var copyPlainText = wsDock.copyPlainText;
  var dockLine = wsDock.dockLine;
  var entriesForView = wsDock.entriesForView;
  var entryVisible = wsDock.entryVisible;
  var wireDock = wsDock.wireDock;
  var wsCtxmenu = window.JzoWsCtxmenu.create({
    addBubble: addBubble,
    applyPrefsLayer: applyPrefsLayer,
    // 循环引用：resetUiState 归更下面的 wsPanel，本块排得靠前，只能等它就位后再取。
    resetUiState: function () { return wsPanel.resetUiState.apply(wsPanel, arguments); },
    // 循环引用：commitTree 归更下面的 wsSidebar，本块排得靠前，只能等它就位后再取。
    commitTree: function () { return wsSidebar.commitTree.apply(wsSidebar, arguments); },
    copyPlainText: copyPlainText,
    dockLine: dockLine,
    dockLog: dockLog,
    entriesForView: entriesForView,
    entryVisible: entryVisible,
    // 循环引用：findInstalled 归更下面的 wsSidebar，本块排得靠前，只能等它就位后再取。
    findInstalled: function () { return wsSidebar.findInstalled.apply(wsSidebar, arguments); },
    // 循环引用：keyPluginId 归更下面的 wsSidebar，本块排得靠前，只能等它就位后再取。
    keyPluginId: function () { return wsSidebar.keyPluginId.apply(wsSidebar, arguments); },
    markActiveEntry: markActiveEntry,
    // 循环引用：notifyConsolePrefs 归更下面的 wsSidebar，本块排得靠前，只能等它就位后再取。
    notifyConsolePrefs: function () { return wsSidebar.notifyConsolePrefs.apply(wsSidebar, arguments); },
    pluginListEl: pluginListEl,
    // 循环引用：postJson 归更下面的 wsSidebar，本块排得靠前，只能等它就位后再取。
    postJson: function () { return wsSidebar.postJson.apply(wsSidebar, arguments); },
    // 循环引用：renderPlugins 归更下面的 wsSidebar，本块排得靠前，只能等它就位后再取。
    renderPlugins: function () { return wsSidebar.renderPlugins.apply(wsSidebar, arguments); },
    // 循环引用：rowTitle 归更下面的 wsSidebar，本块排得靠前，只能等它就位后再取。
    rowTitle: function () { return wsSidebar.rowTitle.apply(wsSidebar, arguments); },
    setStage: setStage,
    // 循环引用：syncContextSlot 归更下面的 wsPanel，本块排得靠前，只能等它就位后再取。
    syncContextSlot: function () { return wsPanel.syncContextSlot.apply(wsPanel, arguments); },
    // 循环引用：syncStageTree 归更下面的 wsSidebar，本块排得靠前，只能等它就位后再取。
    syncStageTree: function () { return wsSidebar.syncStageTree.apply(wsSidebar, arguments); },
    // 循环引用：syncUiState 归更下面的 wsPanel，本块排得靠前，只能等它就位后再取。
    syncUiState: function () { return wsPanel.syncUiState.apply(wsPanel, arguments); },
    wsState: wsState,
  });
  var loadPlugins = wsCtxmenu.loadPlugins;
  var wireDockMenu = wsCtxmenu.wireDockMenu;
  var wireSidebarMenu = wsCtxmenu.wireSidebarMenu;


  var wsPanel = window.JzoWsPanel.create({
    dockLine: dockLine,
    // 右栏折叠策略归 wsRail；它晚于本模块创建，用取值器推迟到调用时才拿。
    getCtxRail: function () { return wsRail; },
    loadPlugins: loadPlugins,
    publishUiParams: publishUiParams,
    stageTitle: stageTitle,
    wsState: wsState,
  });
  var initUiState = wsPanel.initUiState;
  var syncContextSlot = wsPanel.syncContextSlot;
  var wsRail = window.JzoWsRail.create({
    dockToggle: dockToggle,
  });
  var setCtx = wsRail.setCtx;
  var wsSidebar = window.JzoWsSidebar.create({
    dockLine: dockLine,
    enterPluginMode: enterPluginMode,
    fetchWriteToken: fetchWriteToken,
    pluginCountEl: pluginCountEl,
    pluginListEl: pluginListEl,
    wsState: wsState,
  });
  var commitTree = wsSidebar.commitTree;
  var wirePluginClicks = wsSidebar.wirePluginClicks;
  var wirePluginDrag = wsSidebar.wirePluginDrag;
  var wsDropzone = window.JzoWsDropzone.create({
    EDITOR_PLUGIN_ID: EDITOR_PLUGIN_ID,
    addBubble: addBubble,
    fetchWriteToken: fetchWriteToken,
    loadPlugins: loadPlugins,
    wsState: wsState,
  });


  // ---------- 拆出去的模块：以上每块都只经 deps 拿依赖 ----------

  // ============ 宿主提示统一落底栏 ============
  // 宿主不带任何对话界面，也不再直接调 /api/agent/*；系统提示一律进底栏输出日志区。
  function clampText(value, limit) {
    return String(value == null ? "" : value).trim().slice(0, limit);
  }

  function addBubble(role, text, opts) {
    if (role !== "sys") return null;
    var line = clampText(text, 300);
    if (!line) return null;
    var warn = Boolean(opts && opts.tone === "warn");
    // 启动/兜底这类底座自己的动静归【系统终端】；老师亲手触发的插件操作留在【运行日志】。
    var system = Boolean(opts && opts.scope === "system");
    dockLine(line, system ? "system.notice" : (warn ? "host.warn" : "host.notice"),
      warn ? "warn" : "", "", system ? "system" : "runtime");
    return null;
  }

  // ============ 当前任务舞台 ============
  function setStage(taskName) {
    wsState.currentTask = taskName || "";
    if (stageTitle) stageTitle.textContent = wsState.currentTask || "新会话";
  }

  // ============ 入口切换：插件工作模式 ============
  // 左栏不再写死业务任务；条目完全由 /api/plugins 动态渲染，常驻对话入口已下架。
  // 点插件只切换工作模式与上下文，不做任何页面跳转（军令 2.3）。
  function markActiveEntry(activeEl) {
    var items = document.querySelectorAll(".ws-plugin-item");
    for (var i = 0; i < items.length; i += 1) {
      items[i].setAttribute("aria-current", String(items[i] === activeEl));
    }
  }

  function enterPluginMode(plugin, item) {
    wsState.activePlugin = plugin;
    // 记住老师停在哪：刷新后优先回到这里，不再每次都被默认页拽走。
    if (window.JzoWsStartup) window.JzoWsStartup.remember(plugin.id);
    markActiveEntry(item);
    var name = plugin.name || plugin.id || "插件";
    setStage(name);
    initUiState(plugin);
    // 中栏是通用舞台：只有清单里声明了 stage（slots 带 stage.center）的插件才开画布页。
    // 没声明的插件照旧只切工作模式 + 右栏面板，不给它一块它没要过的地方。
    if (plugin.stage && window.JzoStage && typeof window.JzoStage.openPlugin === "function") {
      window.JzoStage.openPlugin(plugin);
    }
  }


  /**
   * 启动行为（军令 #11 阶段三）：老师选了「打开软件默认进入某插件」，这里执行它。
   *
   * 失效判定不在前端重做一遍——后端 /api/startup 已经把卸载/停用的目标
   * 回落到默认启动页（数据看板），再不行才留空，并给了 fallback_reason，
   * 前端只负责照办与如实播报（落底栏）。
   * 读不到配置就按后端给的默认走，任何异常都不许挡住启动。
   */
  function applyStartupBehavior(plugins) {
    // 本地缓存优先：上次停在哪，刷新后就回哪；缓存的插件已失效才往下走启动行为。
    if (!wsState.userPickedPlugin && !wsState.activePlugin && window.JzoWsStartup &&
        window.JzoWsStartup.restore(plugins, enterPluginMode, pluginListEl)) {
      return Promise.resolve();
    }
    return fetch("/api/startup", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (body) {
        if (!body) return;
        if (body.fallback_reason) {
          addBubble("sys", String(body.fallback_reason), { tone: "warn", scope: "system" });
        }
        // 老师已经亲手点了左栏（或画布已有主）：启动页不再抢画布。
        if (wsState.userPickedPlugin || wsState.activePlugin) return;
        var effective = String(body.effective || "");
        // 后端没给可落地目标（如配置的插件刚被卸掉）时，按默认页数据看板再试一次；
        // 看板也不在就留白，不拿别的插件顶包。
        if (effective.indexOf("plugin:") !== 0 && window.JzoWsStartup) {
          effective = "plugin:" + window.JzoWsStartup.DEFAULT_PLUGIN_ID;
        }
        if (effective.indexOf("plugin:") !== 0) return;
        var wantedId = effective.slice("plugin:".length);
        var target = null;
        (plugins || []).forEach(function (plugin) {
          if (!target && plugin.id === wantedId && plugin.enabled !== false) target = plugin;
        });
        if (!target) return;
        var item = null;
        var buttons = pluginListEl ? pluginListEl.querySelectorAll(".ws-plugin-item") : [];
        for (var i = 0; i < buttons.length; i += 1) {
          if (buttons[i].getAttribute("data-plugin-id") === wantedId) { item = buttons[i]; break; }
        }
        enterPluginMode(target, item);
      })
      .catch(function () {
        // 配置读不到也不影响开机：没有缓存时至少把默认页数据看板落上。
        if (wsState.userPickedPlugin || wsState.activePlugin || !window.JzoWsStartup) return;
        window.JzoWsStartup.enter(
          plugins, window.JzoWsStartup.DEFAULT_PLUGIN_ID, enterPluginMode, pluginListEl);
      });
  }




  // ============ 面板参数 → EventBus（右栏改一个值，中栏插件立刻知道） ============
  function uiValuesCopy() {
    var copy = {};
    Object.keys(wsState.uiState.values).forEach(function (key) { copy[key] = wsState.uiState.values[key]; });
    return copy;
  }

  function publishUiParams(source, changedKey) {
    if (!window.JzoBus || typeof window.JzoBus.emit !== "function") return;
    window.JzoBus.emit("ui.params.changed", {
      pluginId: wsState.uiState.pluginId,
      key: changedKey || null,
      values: uiValuesCopy(),
      revisions: JSON.parse(JSON.stringify(wsState.uiState.revisions)),
      by: source
    }, { source: "workspace" });
  }

  // 舞台挂载/唤醒插件时要补发一次当前参数，插件不必等下一次改动才对齐
  window.JzoUiState = { snapshot: function () {
    return { pluginId: wsState.uiState.pluginId, values: uiValuesCopy(), by: "snapshot" };
  } };

  // ============ 写令牌（一次性，用后即焚） ============
  function fetchWriteToken() {
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (r) {
        return window.JzoHttp.readText(r, function (text, data) {
          if (!r.ok) {
            throw window.JzoHttp.fromResponse(r, text, data, { method: "GET", url: "/api/settings" });
          }
          return data || {};
        });
      })
      .then(function (data) {
        var token = data && data.local_token ? String(data.local_token) : "";
        if (!token) {
          throw new Error("本机未生成就绪令牌：GET /api/settings 返回里没有 local_token，请先启动服务再试");
        }
        wsState.writeToken = token;
        return token;
      });
  }

  // --- 控制台页签：全仓唯一的「配置现场」 ---
  var UPDATE_NOTICE_KEY = "jzo.updateNotice";
  var consoleDot = document.getElementById("wsConsoleDot");

  function readUpdateNotice() {
    try {
      var raw = localStorage.getItem(UPDATE_NOTICE_KEY);
      if (!raw) return 0;
      var data = JSON.parse(raw);
      return data && Number(data.count) > 0 ? Number(data.count) : 0;
    } catch (error) {
      return 0;
    }
  }

  function renderUpdateNotice(count) {
    wsState.updateNoticeCount = Number(count) > 0 ? Number(count) : 0;
    var label = wsState.updateNoticeCount > 0 ? "有 " + wsState.updateNoticeCount + " 项更新" : "";
    if (consoleDot) {
      consoleDot.hidden = wsState.updateNoticeCount <= 0;
      consoleDot.textContent = wsState.updateNoticeCount > 0 ? String(wsState.updateNoticeCount) : "";
    }
    var btn = document.getElementById("wsConsoleBtn");
    if (btn) {
      btn.setAttribute("aria-label", wsState.updateNoticeCount > 0
        ? "打开设置与控制台（" + label + "待处理）"
        : "打开设置与控制台");
      btn.title = wsState.updateNoticeCount > 0 ? "设置与控制台 · " + label : "设置与控制台";
    }
  }

  function postConsolePanel(frame, panel, tab) {
    var message = { jzo: "console.panel", panel: panel };
    if (tab) message.tab = tab;
    try {
      frame.contentWindow.postMessage(message, window.location.origin);
    } catch (error) {
      /* 内嵌面板还没起来：等 load 事件补发，不拿异常打死点击 */
    }
  }

  function openConsoleTab(panel, tab) {
    var frame = document.getElementById("wsConsoleFrame");
    if (frame) {
      if (!wsState.consoleFrameLoaded) {
        frame.addEventListener("load", function () {
          wsState.consoleFrameLoaded = true;
          if (wsState.consolePanelPending) {
            postConsolePanel(frame, wsState.consolePanelPending.panel, wsState.consolePanelPending.tab);
            wsState.consolePanelPending = null;
          }
        }, { once: true });
        // 首次水合：直接把目标面板写进地址，省一次「先开默认页再跳面板」的闪动。
        var src = frame.getAttribute("src") || "about:blank";
        if (src === "about:blank" && panel) {
          var target = "/settings?embedded=1&panel=" + encodeURIComponent(panel);
          if (tab) target += "&tab=" + encodeURIComponent(tab);
          frame.setAttribute("src", target);
          wsState.consolePanelPending = { panel: panel, tab: tab || "" };
        } else if (panel) {
          wsState.consolePanelPending = { panel: panel, tab: tab || "" };
        }
      } else if (panel) {
        postConsolePanel(frame, panel, tab);
      }
    }
    if (window.JzoStage && typeof window.JzoStage.activate === "function") {
      window.JzoStage.activate("console");
    }
  }

  // 定调令：工作台不许再有弹窗。左栏入口只把老师带进页签；
  // 有更新待办时直接落到「插件 · 检查更新」。
  (function wireConsoleEntry() {
    renderUpdateNotice(readUpdateNotice());
    var btn = document.getElementById("wsConsoleBtn");
    if (btn) {
      btn.addEventListener("click", function () {
        if (wsState.updateNoticeCount > 0) openConsoleTab("plugin", "update");
        else openConsoleTab();
      });
    }
    window.addEventListener("message", function (event) {
      if (event.origin !== window.location.origin) return;
      var data = event.data;
      if (data && data.jzo === "updates.available") {
        renderUpdateNotice(data.count);
        return;
      }
      // 控制台里改了昵称/启停/分组 → 左栏当场跟上，不等 5 秒轮询。
      if (data && data.jzo === "prefs.changed") loadPlugins({ announce: false }).catch(function () {});
    });
    // 控制台里热更了插件（PLUGIN_SPEC §1.7）→ 左栏、页签与画布立刻接上新代码，
    // 全程不刷新浏览器、不重启底座。宿主自己在总线上广播 plugin.updated。
    window.addEventListener("message", function (event) {
      if (event.origin !== window.location.origin) return;
      var data = event.data;
      if (!data || data.jzo !== "plugins.updated") return;
      var updated = Array.isArray(data.updated) ? data.updated : [];
      loadPlugins({ announce: false }).then(function () {
        updated.forEach(function (row) {
          var id = row && row.id;
          if (!id) return;
          if (window.JzoBus && typeof window.JzoBus.emit === "function") {
            window.JzoBus.emit("plugin.updated", {
              id: id, from: String(row.from || ""), to: String(row.to || "")
            });
          }
          if (window.JzoStage && typeof window.JzoStage.rehydratePlugin === "function") {
            window.JzoStage.rehydratePlugin(id);
          }
        });
      }).catch(function () {});
    });
  })();

  // ============ 左栏顺序迁移（一次性） ============

  /** 把早期存在浏览器里的拖拽顺序一次性搬进后端树（搬完打标记，绝不双向同步）。 */
  function migrateLegacySidebar(data) {
    if (wsState.legacyOrderMigrated || !window.JzoPrefs) return;
    wsState.legacyOrderMigrated = true;
    if (data && data.sidebar_customized) return;
    var legacy = window.JzoPrefs.legacyTree();
    if (!legacy.length) return;
    window.JzoPrefs.markLegacyMigrated();
    dockLine("把你以前在浏览器里排好的左栏顺序搬进了本机设置文件（此后分组随底座走）。", "prefs.sidebar");
    commitTree(legacy);
  }

  function applyPrefsLayer(data) {
    migrateLegacySidebar(data);
  }




  // ============ 右栏主权监听：画布页签换主人，插槽跟着换 ============
  function wireStageSovereignty() {
    if (!window.JzoBus || typeof window.JzoBus.on !== "function") return;
    window.JzoBus.on("stage.tab.activated", function (event) {
      var payload = (event && event.payload) || {};
      wsState.activeCanvasPluginId = typeof payload.pluginId === "string" ? payload.pluginId : "";
      // 页签栏切页也算「上次停留的页」；控制台没有 pluginId，不参与记账。
      if (payload.pluginId && window.JzoWsStartup) window.JzoWsStartup.remember(payload.pluginId);
      syncContextSlot();
    });
    // 关掉页签后 stage 会自己 emit 一次 activated；这里先清账，避免主权挂在已关插件上
    window.JzoBus.on("stage.tab.closed", function () {
      wsState.activeCanvasPluginId = "";
      syncContextSlot();
    });
  }

  // ============ 幽灵滚动条：真滚动时浮出来，停手 900ms 后淡回去 ============
  // scroll 事件不冒泡，但捕获阶段能拿到；只认标了 .ws-ghost-scroll 的宿主滚动区，
  // iframe 插件内部的滚动条由插件自己的样式负责。
  function wireGhostScroll() {
    var timers = typeof WeakMap === "function" ? new WeakMap() : null;
    document.addEventListener("scroll", function (event) {
      var node = event.target;
      if (!node || !node.classList || !node.classList.contains("ws-ghost-scroll")) return;
      node.classList.add("is-scrolling");
      if (!timers) return;
      var previous = timers.get(node);
      if (previous) window.clearTimeout(previous);
      timers.set(node, window.setTimeout(function () {
        node.classList.remove("is-scrolling");
      }, 900));
    }, true);
  }

  // ============ 初始化 ============
  // 中栏启动时留白（不预开兜底页），右栏默认折叠；左栏条目完全由 /api/plugins 渲染。
  wireDock();
  wireDockMenu();
  wireGhostScroll();
  wirePluginClicks();
  wirePluginDrag();
  wireSidebarMenu();
  wireStageSovereignty();
  setStage("工作台");
  markActiveEntry(null);
  addBubble("sys", "九章算子工作台已就绪 · 插件按需占用中栏与右栏", { scope: "system" });

  loadPlugins()
    .then(function (plugins) {
      // 启动行为在插件清单渲染完之后执行：左栏条目已就位，进去才能高亮对应项
      return applyStartupBehavior(plugins);
    })
    .catch(function () { /* 探测失败保留「暂无插件」空态，不打扰用户 */ });
})();
