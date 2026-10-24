/**
 * 工作台宿主壳：左栏入口、右侧插槽主权交替、面板参数仲裁、底栏输出区与插件生命周期。
 *
 * 军令 #15 的边界：对话流不再住在这里。中栏是通用舞台，右栏助手是
 * plugins/org.jiuzhang.chat 这个普通插件——它想看什么、想改什么、想去哪个页签，
 * 都得经 stage.js 的 Host API 白名单向底座申请，由本文件把状态快照与仲裁结果交出去
 * （window.JzoWorkspace）。底座自身不再直接调 /api/agent/*。
 *
 * 安全：所有写接口由宿主代取一次性令牌；不可信文本一律走 textContent，不拼 innerHTML。
 */
(function () {
  "use strict";

  // --- State ---
  var providerList = [];
  var installedPlugins = [];
  var writeToken = null;
  var currentTask = "";
  var activePlugin = null;
  // 右侧面板状态：values 是当前参数，revisions 记录人类
  // 手改次数。发请求时拍快照，AI 回来要改参数时只改「人没同时动过」的字段——
  // 人类的主动点击永远覆盖 AI 的自动设定。
  var uiState = { pluginId: null, values: {}, revisions: {} };
  var uiPanelControls = [];
  // 右栏主权（军令 #15 任务 4）：当前画布页签绑定的插件 id。
  // 它若声明了 sidebar.right 就暂时接管右栏，否则右栏归还 AI 助手插件。
  var activeCanvasPluginId = "";
  var ASSISTANT_PLUGIN_ID = "org.jiuzhang.chat";

  // --- DOM refs ---
  var sidebarToggle = document.getElementById("wsToggleSidebar");
  var stageTitle = document.getElementById("wsStageTitle");
  var ctxTask = document.getElementById("ctxTask");
  var ctxModel = document.getElementById("ctxModel");
  var ctxHistory = document.getElementById("ctxHistory");
  var pluginListEl = document.getElementById("wsPluginList");
  var pluginCountEl = document.getElementById("wsPluginCount");
  var pluginPanel = document.getElementById("wsPluginPanel");
  var pluginPanelTitle = document.getElementById("wsPluginPanelTitle");
  var pluginPanelDesc = document.getElementById("wsPluginPanelDesc");
  var pluginControlsEl = document.getElementById("wsPluginControls");
  var pluginPanelHint = document.getElementById("wsPluginPanelHint");
  var uiStateSummary = document.getElementById("wsUiStateSummary");
  var dockToggle = document.getElementById("wsToggleDock");
  var dockClearBtn = document.getElementById("wsDockClear");
  var dockLog = document.getElementById("wsDockLog");
  var dockTabs = document.getElementById("wsDockTabs");


  // ============ 对话流已整体迁出（军令 #15） ============
  // 气泡、题卡、安装卡、确认卡与 KaTeX 渲染都搬进了右栏的 org.jiuzhang.chat 插件，
  // 宿主不再自带任何对话界面，也不再直接调 /api/agent/*。
  // 原先「往对话区说一句」的提示改落底栏输出日志区——同一段话，换个不越权的地方说。
  function clampText(value, limit) {
    return String(value == null ? "" : value).trim().slice(0, limit);
  }

  function addBubble(role, text, opts) {
    if (role !== "sys") return null;
    var line = clampText(text, 300);
    if (line) dockLine(line, opts && opts.tone === "warn" ? "host.warn" : "host.notice");
    return null;
  }

  function logHistory(text) {
    if (!ctxHistory) return;
    var placeholder = ctxHistory.querySelector(".ws-placeholder");
    if (placeholder) placeholder.remove();
    var li = document.createElement("li");
    var time = new Date();
    var hh = String(time.getHours()).padStart(2, "0");
    var mm = String(time.getMinutes()).padStart(2, "0");
    li.textContent = hh + ":" + mm + " · " + text;
    ctxHistory.insertBefore(li, ctxHistory.firstChild);
    // 只留最近 8 条，避免无限增长
    while (ctxHistory.children.length > 8) {
      ctxHistory.removeChild(ctxHistory.lastChild);
    }
  }

  // ============ 当前任务舞台 ============
  function setStage(taskName) {
    currentTask = taskName || "";
    if (stageTitle) stageTitle.textContent = currentTask || "新会话";
    if (ctxTask) ctxTask.textContent = currentTask || "未选择";
  }

  // ============ 入口切换：插件工作模式 ============
  // 左栏不再写死业务任务；条目完全由 /api/plugins 动态渲染（军令 #15 之后，
  // 「自由对话」这条底座内置入口也撤了——AI 助手只是清单里的一个普通插件）。
  // 点插件只切换工作模式与上下文，不做任何页面跳转（军令 2.3）。
  function markActiveEntry(activeEl) {
    var items = document.querySelectorAll(".ws-plugin-item");
    for (var i = 0; i < items.length; i += 1) {
      items[i].setAttribute("aria-current", String(items[i] === activeEl));
    }
  }

  function enterPluginMode(plugin, item) {
    activePlugin = plugin;
    markActiveEntry(item);
    var name = plugin.name || plugin.id || "插件";
    setStage(name);
    initUiState(plugin);
    renderPluginPanel(plugin);
    // 中栏是通用舞台：只有清单里声明了 stage（slots 带 stage.center）的插件才开画布页。
    // 没声明的插件照旧只切工作模式 + 右栏面板，不给它一块它没要过的地方。
    if (plugin.id === ASSISTANT_PLUGIN_ID) {
      // 助手不开画布页：点它这一行等于「把右栏还给我」，并顺手展开右栏。
      setCtx(true);
      if (window.JzoContextPanel && typeof window.JzoContextPanel.reclaim === "function") {
        window.JzoContextPanel.reclaim();
      }
    } else if (plugin.stage && window.JzoStage && typeof window.JzoStage.openPlugin === "function") {
      window.JzoStage.openPlugin(plugin);
    }
    logHistory("进入插件「" + name + "」");
  }


  /**
   * 启动行为（军令 #11 阶段三）：老师选了「打开软件默认进入某插件」，这里执行它。
   * 失效判定不在前端重做一遍——后端 /api/startup 已经把卸载/停用的目标回落成
   * chat 并给了 fallback_reason，前端只负责照办与如实播报（底栏 + 对话区都记一笔）。
   * 读不到配置就停在默认欢迎页，任何异常都不许挡住启动。
   */
  function applyStartupBehavior(plugins) {
    return fetch("/api/startup", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (body) {
        if (!body) return;
        if (body.fallback_reason) {
          addBubble("sys", String(body.fallback_reason), { tone: "warn" });
          logHistory("启动行为回退：" + body.fallback_reason);
        }
        var effective = String(body.effective || "chat");
        if (effective.indexOf("plugin:") !== 0) return;
        var wantedId = effective.slice("plugin:".length);
        var target = null;
        (plugins || []).forEach(function (plugin) {
          if (!target && plugin.id === wantedId && plugin.enabled !== false) target = plugin;
        });
        if (!target) {
          logHistory("启动插件不在场，停在引导页：" + wantedId);
          return;
        }
        var item = null;
        var buttons = pluginListEl ? pluginListEl.querySelectorAll(".ws-plugin-item") : [];
        for (var i = 0; i < buttons.length; i += 1) {
          if (buttons[i].getAttribute("data-plugin-id") === wantedId) { item = buttons[i]; break; }
        }
        enterPluginMode(target, item);
      })
      .catch(function () { /* 配置读不到就当没配过，默认欢迎页照旧 */ });
  }

  // ============ 右侧插件面板（双向操控） ============
  // 控件由 plugin.json 的 ui 字段（或底座按能力生成的默认面板）下发。
  // 人类改下拉 → revisions[key] 加一；AI 改参数时用发送时的快照比对，
  // 只要人类在请求飞行期间动过同一字段，AI 的设定就让位。
  function panelControls(plugin) {
    var ui = plugin && plugin.ui;
    return ui && Array.isArray(ui.controls) ? ui.controls : [];
  }

  function initUiState(plugin) {
    var controls = panelControls(plugin);
    var values = {};
    controls.forEach(function (control) {
      if (control.type !== "select") return;
      var options = Array.isArray(control.options) ? control.options : [];
      var fallback = options.length ? options[0].value : "";
      values[control.key] = control.default || fallback;
    });
    uiPanelControls = controls;
    uiState = { pluginId: plugin ? plugin.id : null, values: values, revisions: {} };
    updateUiStateSummary();
  }

  function syncUiState(plugin) {
    var controls = panelControls(plugin);
    var next = {};
    controls.forEach(function (control) {
      if (control.type !== "select") return;
      var options = Array.isArray(control.options) ? control.options : [];
      var fallback = options.length ? options[0].value : "";
      var previous = uiState.values[control.key];
      var valid = options.some(function (option) { return option.value === previous; });
      next[control.key] = valid ? previous : (control.default || fallback);
    });
    uiPanelControls = controls;
    uiState.pluginId = plugin ? plugin.id : null;
    uiState.values = next;
  }

  function clearPluginPanel() {
    uiPanelControls = [];
    uiState = { pluginId: null, values: {}, revisions: {} };
    if (pluginPanel) pluginPanel.hidden = true;
    if (pluginControlsEl) pluginControlsEl.textContent = "";
    if (uiStateSummary) uiStateSummary.textContent = "";
  }

  function renderPluginPanel(plugin) {
    if (!pluginPanel || !pluginControlsEl) return;
    var controls = panelControls(plugin);
    if (!controls.length) {
      clearPluginPanel();
      return;
    }
    var ui = plugin.ui || {};
    if (pluginPanelTitle) pluginPanelTitle.textContent = ui.title || ((plugin.name || "插件") + "快捷操作");
    if (pluginPanelDesc) {
      pluginPanelDesc.textContent = plugin.description || "该插件未提供说明。";
    }
    if (pluginPanelHint) {
      pluginPanelHint.textContent = ui.hint || "点按钮等于发送对应指令；你手动改过的参数优先于 AI 的自动设定。";
    }
    pluginControlsEl.textContent = "";

    controls.forEach(function (control) {
      if (control.type === "select") {
        var field = document.createElement("label");
        field.className = "ws-ui-field";
        var label = document.createElement("span");
        label.className = "ws-ui-field-label";
        label.textContent = control.label || control.key;
        var select = document.createElement("select");
        select.className = "ws-ui-select";
        select.setAttribute("data-ui-key", control.key);
        (control.options || []).forEach(function (option) {
          var item = document.createElement("option");
          item.value = option.value;
          item.textContent = option.label || option.value;
          if (uiState.values[control.key] === option.value) item.selected = true;
          select.appendChild(item);
        });
        select.addEventListener("change", function () {
          uiState.values[control.key] = select.value;
          uiState.revisions[control.key] = (uiState.revisions[control.key] || 0) + 1;
          updateUiStateSummary();
          logHistory("面板调整：" + (control.label || control.key) + " = " + select.value);
          publishUiParams("human", control.key);
        });
        field.appendChild(label);
        field.appendChild(select);
        pluginControlsEl.appendChild(field);
        return;
      }
      if (control.type === "button") {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ws-btn ws-btn-sm ws-ui-action";
        btn.setAttribute("data-ui-button", control.id);
        btn.textContent = control.label || "执行";
        btn.addEventListener("click", function () {
          publishPanelButton(control.command, control.label || "面板按钮");
        });
        pluginControlsEl.appendChild(btn);
      }
    });

    pluginPanel.hidden = false;
    updateUiStateSummary();
  }

  function updateUiStateSummary() {
    if (!uiStateSummary) return;
    var parts = [];
    uiPanelControls.forEach(function (control) {
      if (control.type !== "select") return;
      var value = uiState.values[control.key];
      if (value == null || value === "") return;
      var edited = uiState.revisions[control.key] ? "（你已改）" : "";
      parts.push((control.label || control.key) + "：" + value + edited);
    });
    uiStateSummary.textContent = parts.length
      ? "当前参数 " + parts.join(" · ")
      : "面板操作会实时同步给 AI。";
  }

  function currentUiValues() {
    var values = {};
    Object.keys(uiState.values).forEach(function (key) {
      values[key] = uiState.values[key];
    });
    return values;
  }

  function compactControls() {
    return uiPanelControls.map(function (control) {
      if (control.type === "select") {
        return {
          id: control.id,
          type: "select",
          key: control.key,
          label: control.label,
          options: (control.options || []).map(function (option) {
            return { value: option.value, label: option.label };
          }),
          default: control.default,
        };
      }
      return { id: control.id, type: "button", label: control.label };
    });
  }

  function expandCommand(template) {
    return String(template || "").replace(/\{([a-z][a-z0-9_]{0,15})\}/g, function (whole, key) {
      var value = uiState.values[key];
      return value == null ? whole : String(value);
    });
  }

  /**
   * 人点面板按钮 = 请右栏的 AI 助手把这句话发出去（军令 #15）。
   * 宿主不再自己调对话接口：按钮只把「指令模板 + 当前参数」交给助手插件，
   * 由它经 Host API 申请一次对话——对话的入口收在插件手里，底座不再代笔。
   */
  function publishPanelButton(command, label) {
    var text = clampText(expandCommand(command), 400);
    if (!text) {
      dockLine("面板按钮「" + clampText(label, 40) + "」没有可用的指令模板。", "host.warn");
      return;
    }
    if (window.JzoStage && typeof window.JzoStage.broadcast === "function") {
      window.JzoStage.broadcast("panel.button.click", {
        plugin_id: uiState.pluginId,
        command: text,
        label: clampText(label, 40)
      });
    }
    logHistory("面板按钮：" + (label || text));
  }

  function findUiControl(id, type) {
    for (var i = 0; i < uiPanelControls.length; i += 1) {
      var control = uiPanelControls[i];
      if (control.id === id && control.type === type) return control;
    }
    return null;
  }

  function snapshotRevisions() {
    var snapshot = {};
    Object.keys(uiState.revisions).forEach(function (key) {
      snapshot[key] = uiState.revisions[key];
    });
    return snapshot;
  }

  // 应用 AI 的 update_params：只改「人没在本轮同时动过」且值合法的字段。
  function applyUiParams(params, snapshot) {
    var applied = [];
    var skipped = [];
    if (!params || typeof params !== "object") return { applied: applied, skipped: skipped };
    Object.keys(params).forEach(function (key) {
      var control = findUiControl(key, "select");
      if (!control) return;
      var incoming = params[key];
      var valid = (control.options || []).some(function (option) { return option.value === incoming; });
      if (!valid) {
        skipped.push({ label: control.label, value: incoming, reason: "不是可选值" });
        return;
      }
      if (snapshot && snapshot[key] !== uiState.revisions[key]) {
        skipped.push({ label: control.label, value: incoming, reason: "你刚手动改过" });
        return;
      }
      uiState.values[key] = incoming;
      var select = pluginControlsEl
        ? pluginControlsEl.querySelector('[data-ui-key="' + key + '"]')
        : null;
      if (select) select.value = incoming;
      applied.push({ label: control.label, value: incoming });
    });
    if (applied.length) {
      updateUiStateSummary();
      // AI 代人改参数同样要广播：中栏插件看到的参数必须和右栏一致
      publishUiParams("ai", null);
    }
    return { applied: applied, skipped: skipped };
  }

  /**
   * AI 助手插件申请设面板参数（军令 #15 任务 1、2）。
   * 助手交出「目标插件 + 发送时拍的修订号快照」：目标不对整批拒，
   * 快照对不上（人在请求飞行期间手改过同一字段）单字段跳过——AI 永远赢不过人的手。
   */
  function applyAiParams(params, snapshot, targetPluginId) {
    if (!uiState.pluginId) {
      return { error: { code: "NO_PANEL", message: "当前右栏没有可调参数的插件面板" } };
    }
    var wanted = String(targetPluginId || "");
    if (wanted && wanted !== uiState.pluginId) {
      return { error: { code: "PANEL_MOVED", message: "面板已切到「" + uiState.pluginId + "」，本次设定作废" } };
    }
    var outcome = applyUiParams(params, snapshot);
    dockLine("AI 助手经宿主设定面板参数：应用 " + outcome.applied.length
      + " 项、跳过 " + outcome.skipped.length + " 项。", "agent.params");
    if (outcome.applied.length) {
      logHistory("AI 设定参数：" + outcome.applied.map(function (item) {
        return item.label + "=" + item.value;
      }).join("、"));
    }
    return outcome;
  }

  /**
   * 宿主工作区快照（window.JzoWorkspace 的服务面之一）：
   * 助手插件能看见的全部世界就是这一份 JSON——没有 DOM、没有令牌、没有库连接。
   */
  function stateSnapshot() {
    var active = findActiveProvider();
    var snapshot = {
      current_task: currentTask || "未选择",
      stage: (stageTitle && stageTitle.textContent) || currentTask || "工作台",
      textbook: "未选择",
      model: active ? (active.model || active.label || "未知") : "未就绪",
      mock: active ? Boolean(active.mock || !active.configured) : true,
      provider: active || null,
      right_slot: window.JzoContextPanel ? window.JzoContextPanel.activeId() : null,
      tabs: window.JzoStage && typeof window.JzoStage.tabs === "function" ? window.JzoStage.tabs() : []
    };
    if (activePlugin) {
      snapshot.plugin = {
        id: activePlugin.id,
        name: activePlugin.name,
        version: activePlugin.version,
        kind: activePlugin.kind,
        description: activePlugin.description,
        capabilities: activePlugin.capabilities || []
      };
      if (uiPanelControls.length) {
        snapshot.ui = {
          plugin_id: activePlugin.id,
          values: currentUiValues(),
          controls: compactControls(),
          revisions: snapshotRevisions()
        };
      }
    }
    return snapshot;
  }

  /** 右栏主权对账：画布页签换了主人，插槽跟着换（军令 #15 任务 4）。 */
  function syncContextSlot() {
    if (window.JzoContextPanel && typeof window.JzoContextPanel.sync === "function") {
      window.JzoContextPanel.sync(installedPlugins, activeCanvasPluginId);
    }
  }

  // 助手插件向底座要服务的唯一门面：白名单在 stage.js，能力在这里。
  window.JzoWorkspace = {
    stateSnapshot: stateSnapshot,
    applyAiParams: applyAiParams,
    syncContextSlot: syncContextSlot,
    refreshPlugins: function () { return loadPlugins({ announce: true }); },
    activeCanvasPlugin: function () { return activeCanvasPluginId; }
  };

  // ============ 折叠：左栏 / 右栏（data 属性驱动，桌面收轨道、移动滑抽屉） ============
  // 状态机只有一个事实来源：.ws-page 上的 data-side / data-ctx。
  // 样式按这两枚属性钉轨切轨（见 workspace.css 折叠态一节），脚本只负责翻属性，
  // 绝不再往元素上补 style，避免「属性说收起、内联样式说展开」的两本账。
  var wsPage = document.querySelector(".ws-page");
  var mqMobile = window.matchMedia("(max-width: 768px)");
  var openSidebarBtn = document.getElementById("wsOpenSidebar");

  function sideOpen() {
    return !!wsPage && wsPage.getAttribute("data-side") === "open";
  }

  function setSide(open) {
    if (!wsPage) return;
    wsPage.setAttribute("data-side", open ? "open" : "hidden");
    if (sidebarToggle) {
      sidebarToggle.setAttribute("aria-expanded", String(open));
      sidebarToggle.textContent = open ? "折叠" : "展开";
    }
    if (openSidebarBtn) openSidebarBtn.setAttribute("aria-expanded", String(open));
  }

  function setCtx(open) {
    if (!wsPage) return;
    wsPage.setAttribute("data-ctx", open ? "open" : "hidden");
  }

  function dockOpen() {
    return !!wsPage && wsPage.getAttribute("data-dock") === "open";
  }

  function setDock(open) {
    if (!wsPage) return;
    wsPage.setAttribute("data-dock", open ? "open" : "hidden");
    if (dockToggle) {
      dockToggle.setAttribute("aria-expanded", String(open));
      dockToggle.textContent = open ? "折叠" : "展开";
    }
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function () {
      setSide(!sideOpen());
    });
  }

  if (openSidebarBtn) {
    openSidebarBtn.addEventListener("click", function () {
      setSide(!sideOpen());
    });
  }

  if (dockToggle) {
    dockToggle.addEventListener("click", function () {
      setDock(!dockOpen());
    });
  }

  // 默认态：桌面两栏展开、底栏展开；窄屏抽屉与底栏都收起，避免一进来就糊在中栏上。
  setSide(!mqMobile.matches);
  setCtx(!mqMobile.matches);
  setDock(!mqMobile.matches);

  // 跨断点时必须重算：窄屏收起的抽屉拖宽到桌面会留下「轨道已收起、属性仍写 open」
  // 的错位；反过来桌面展开态拉到窄屏则会让抽屉直接糊住对话流。
  function onBreakpoint(matched) {
    setSide(!matched);
    setCtx(!matched);
    setDock(!matched);
  }
  if (typeof mqMobile.addEventListener === "function") {
    mqMobile.addEventListener("change", function (e) { onBreakpoint(e.matches); });
  } else if (typeof mqMobile.addListener === "function") {
    mqMobile.addListener(function (e) { onBreakpoint(e.matches); });
  }

  // ============ 底栏输出区：EventBus 的 region.dock 落点 ============
  // 四区里左、右、下都由底座托管。插件想往底栏写字，只能发 region.dock 事件，
  // 底座收到后一律 textContent 落 DOM（AGENTS §5：不可信输入进 DOM 前必须净化）。
  var DOCK_MAX = 120;
  var dockEntries = [];
  var dockView = "log";
  var DOCK_VIEWS = { log: true, error: true, terminal: true };
  var DOCK_EMPTY = {
    log: "暂无输出。插件与面板事件会出现在这里。",
    error: "没有报错。插件与底座的事件流一切正常。",
    terminal: "暂无系统事件。",
  };

  // 三级分类只按事件主题与关键词判，不做内容猜谜：
  // error 进【报错诊断】，宿主生命周期进【系统终端】，其余留在【运行日志】。
  function dockLevel(topic, text) {
    var name = String(topic || "");
    if (/(^|[._-])(error|failed|failure|timeout)([._-]|$)/i.test(name) ||
      /失败|错误|异常|超时/.test(text)) {
      return "error";
    }
    if (/^(plugin|workspace|system|stage|layout|provider)\./.test(name)) return "system";
    return "info";
  }

  function stamp() {
    var now = new Date();
    return String(now.getHours()).padStart(2, "0") + ":" +
      String(now.getMinutes()).padStart(2, "0") + ":" +
      String(now.getSeconds()).padStart(2, "0");
  }

  function copyPlainText(value) {
    var text = String(value == null ? "" : value);
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(text).catch(function () { fallbackCopy(text); });
    }
    fallbackCopy(text);
    return Promise.resolve();
  }

  // http 下 navigator.clipboard 不可用（非安全上下文），回落老办法。
  function fallbackCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); } catch (error) { /* 浏览器连老办法也不给，保持静默 */ }
    document.body.removeChild(area);
  }

  function entryVisible(entry) {
    if (dockView === "error") return entry.level === "error";
    if (dockView === "terminal") return entry.level === "system";
    return true;
  }

  function renderDock() {
    if (!dockLog) return;
    dockLog.setAttribute("data-view", dockView);
    dockLog.textContent = "";
    var shown = dockEntries.filter(entryVisible);
    if (!shown.length) {
      var empty = document.createElement("li");
      empty.className = "ws-dock-empty";
      empty.textContent = DOCK_EMPTY[dockView] || DOCK_EMPTY.log;
      dockLog.appendChild(empty);
      return;
    }
    shown.forEach(function (entry) {
      var item = document.createElement("li");
      item.className = "ws-dock-item";
      item.setAttribute("data-level", entry.level);
      item.setAttribute("data-copy", entry.line);
      var time = document.createElement("span");
      time.className = "ws-dock-time";
      time.textContent = entry.time;
      item.appendChild(time);
      if (entry.topic) {
        var tag = document.createElement("span");
        tag.className = "ws-dock-topic";
        tag.textContent = entry.topic;
        item.appendChild(tag);
      }
      var body = document.createElement("span");
      body.className = "ws-dock-text";
      body.textContent = entry.text;
      item.appendChild(body);
      if (dockView === "error") {
        var hint = document.createElement("span");
        hint.className = "ws-dock-copy";
        hint.setAttribute("aria-hidden", "true");
        hint.textContent = "双击复制";
        item.appendChild(hint);
      }
      dockLog.appendChild(item);
    });
    if (dockOpen()) {
      var dockBody = document.getElementById("wsDockBody");
      if (dockBody) dockBody.scrollTop = dockBody.scrollHeight;
    }
  }

  function setDockView(view) {
    dockView = DOCK_VIEWS[view] ? view : "log";
    if (dockTabs) {
      var buttons = dockTabs.querySelectorAll(".ws-dock-tab");
      for (var i = 0; i < buttons.length; i += 1) {
        buttons[i].setAttribute("aria-selected", String(buttons[i].getAttribute("data-view") === dockView));
      }
    }
    renderDock();
  }

  // 报错诊断的双击复制：原位闪绿底 + 变字，不弹 Toast、不选中文本、不抢焦点。
  if (dockLog) {
    dockLog.addEventListener("dblclick", function (event) {
      if (dockView !== "error") return;
      var item = event.target && event.target.closest ? event.target.closest(".ws-dock-item") : null;
      if (!item) return;
      event.preventDefault();
      var selection = window.getSelection ? window.getSelection() : null;
      if (selection) selection.removeAllRanges();
      var hint = item.querySelector(".ws-dock-copy");
      copyPlainText(item.getAttribute("data-copy") || "").then(function () {
        item.classList.add("is-copied");
        if (hint) hint.textContent = "已复制";
        window.setTimeout(function () {
          item.classList.remove("is-copied");
          if (hint) hint.textContent = "双击复制";
        }, 1200);
      });
    });
  }

  if (dockTabs) {
    dockTabs.addEventListener("click", function (event) {
      var button = event.target && event.target.closest ? event.target.closest(".ws-dock-tab") : null;
      if (button) setDockView(button.getAttribute("data-view"));
    });
    dockTabs.addEventListener("keydown", function (event) {
      var keys = { ArrowLeft: -1, ArrowRight: 1 };
      if (!(event.key in keys)) return;
      var buttons = Array.prototype.slice.call(dockTabs.querySelectorAll(".ws-dock-tab"));
      var index = buttons.indexOf(document.activeElement);
      if (index < 0) return;
      event.preventDefault();
      var next = buttons[(index + keys[event.key] + buttons.length) % buttons.length];
      next.focus();
      setDockView(next.getAttribute("data-view"));
    });
  }

  function dockLine(text, topic, level) {
    var body = String(text == null ? "" : text).slice(0, 400);
    var name = String(topic || "");
    var at = stamp();
    dockEntries.push({
      time: at,
      topic: name,
      text: body,
      level: level || dockLevel(name, body),
      line: at + (name ? " [" + name + "] " : " ") + body,
    });
    while (dockEntries.length > DOCK_MAX) dockEntries.shift();
    renderDock();
  }

  function wireDock() {
    if (!window.JzoBus || typeof window.JzoBus.on !== "function") return;
    window.JzoBus.on("region.dock", function (event) {
      var payload = event.payload || {};
      dockLine(payload.text || "（空消息）", payload.topic || event.topic);
    });
    window.JzoBus.on("layout.changed", function (event) {
      var payload = event.payload || {};
      if (payload.by === "restore") return;   // 刷新恢复不必刷屏
      var sizes = payload.sizes || {};
      dockLine("布局已调整（" + (payload.by || "drag") + "）：左 " + sizes.side +
        " / 右 " + sizes.context + " / 下 " + sizes.dock, "layout.changed");
    });
    if (dockClearBtn) {
      dockClearBtn.addEventListener("click", function () {
        dockEntries = [];
        renderDock();
      });
    }
  }

  // ============ 面板参数 → EventBus（右栏改一个值，中栏插件立刻知道） ============
  function uiValuesCopy() {
    var copy = {};
    Object.keys(uiState.values).forEach(function (key) { copy[key] = uiState.values[key]; });
    return copy;
  }

  function publishUiParams(source, changedKey) {
    if (!window.JzoBus || typeof window.JzoBus.emit !== "function") return;
    window.JzoBus.emit("ui.params.changed", {
      pluginId: uiState.pluginId,
      key: changedKey || null,
      values: uiValuesCopy(),
      revisions: JSON.parse(JSON.stringify(uiState.revisions)),
      by: source
    }, { source: "workspace" });
  }

  // 舞台挂载/唤醒插件时要补发一次当前参数，插件不必等下一次改动才对齐
  window.JzoUiState = { snapshot: function () {
    return { pluginId: uiState.pluginId, values: uiValuesCopy(), by: "snapshot" };
  } };

  // ============ 写令牌（一次性，用后即焚） ============
  function fetchWriteToken() {
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("读取本机令牌失败（HTTP " + r.status + "）");
        return r.json();
      })
      .then(function (data) {
        var token = data && data.local_token ? String(data.local_token) : "";
        if (!token) throw new Error("本机未生成就绪令牌，请先启动服务后再试");
        writeToken = token;
        return token;
      });
  }

  function readErrorDetail(response, body) {
    var detail = body && body.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail.message === "string") return detail.message;
    return "HTTP " + response.status;
  }

  // ============ 模型 Provider：加载 / 切换 / 配置 ============
  function findActiveProvider() {
    for (var i = 0; i < providerList.length; i += 1) {
      if (providerList[i].active) return providerList[i];
    }
    return null;
  }

  // 顶栏模型胶囊已随舞台头一起退役：模型状态只在右栏「模型」一节如实显示。
  function renderModelChip() {
    var active = findActiveProvider();
    if (!ctxModel) return;
    if (!active) {
      ctxModel.textContent = "未就绪";
      return;
    }
    if (!active.configured || active.mock) {
      ctxModel.textContent = active.label + " · Mock 降级（未配置密钥）";
      return;
    }
    ctxModel.textContent = active.label + " · " + (active.model || "已配置");
  }

  function loadProviders() {
    return fetch("/api/providers", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        providerList = data.providers || [];
        renderModelChip();
        return data;
      });
  }

  // --- 控制台页签：全仓唯一的「配置现场」 ---
  // 底座被改坏时仍可直连 /settings 强制进同一套面板（防变砖兜底，见军令例外条款）。
  var consoleFrameLoaded = false;
  var consolePanelPending = null;
  var UPDATE_NOTICE_KEY = "jzo.updateNotice";
  var updateNoticeCount = 0;
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
    updateNoticeCount = Number(count) > 0 ? Number(count) : 0;
    var label = updateNoticeCount > 0 ? "有 " + updateNoticeCount + " 项更新" : "";
    if (consoleDot) {
      consoleDot.hidden = updateNoticeCount <= 0;
      consoleDot.textContent = label;
    }
    var btn = document.getElementById("wsConsoleBtn");
    if (btn) {
      btn.setAttribute("aria-label", updateNoticeCount > 0
        ? "打开设置与控制台（" + label + "待处理）"
        : "打开设置与控制台");
      btn.title = updateNoticeCount > 0 ? "设置与控制台 · " + label : "设置与控制台";
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
      if (!consoleFrameLoaded) {
        frame.addEventListener("load", function () {
          consoleFrameLoaded = true;
          if (consolePanelPending) {
            postConsolePanel(frame, consolePanelPending.panel, consolePanelPending.tab);
            consolePanelPending = null;
          }
        }, { once: true });
        // 首次水合：直接把目标面板写进地址，省一次「先开默认页再跳面板」的闪动。
        var src = frame.getAttribute("src") || "about:blank";
        if (src === "about:blank" && panel) {
          var target = "/settings?embedded=1&panel=" + encodeURIComponent(panel);
          if (tab) target += "&tab=" + encodeURIComponent(tab);
          frame.setAttribute("src", target);
          consolePanelPending = { panel: panel, tab: tab || "" };
        } else if (panel) {
          consolePanelPending = { panel: panel, tab: tab || "" };
        }
      } else if (panel) {
        postConsolePanel(frame, panel, tab);
      }
    }
    if (window.JzoStage && typeof window.JzoStage.activate === "function") {
      window.JzoStage.activate("console");
    }
  }

  // 定调令：工作台不许再有弹窗。左栏入口只把老师带进页签，
  // 模型配置表单在控制台里只有那一份；有更新待办时直接落到「插件 · 检查更新」。
  (function wireConsoleEntry() {
    renderUpdateNotice(readUpdateNotice());
    var btn = document.getElementById("wsConsoleBtn");
    if (btn) {
      btn.addEventListener("click", function () {
        if (updateNoticeCount > 0) openConsoleTab("plugin", "update");
        else openConsoleTab();
      });
    }
    // 控制台里改了模型配置 → 顶栏胶囊立即重拉状态，不让老师对着旧标签发愣。
    window.addEventListener("message", function (event) {
      if (event.origin !== window.location.origin) return;
      var data = event.data;
      if (data && data.jzo === "updates.available") {
        renderUpdateNotice(data.count);
        return;
      }
      if (data && data.jzo === "providers.changed") loadProviders().catch(function () {});
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
          logHistory("插件热更新：" + id + " " + (row.from || "?") + " → " + (row.to || "?"));
        });
      }).catch(function () {});
    });
  })();

  // ============ 已安装插件：动态渲染左栏插件区 ============
  var KIND_LABELS = { renderer: "渲染", importer: "导入", exporter: "导出", tool: "工具" };

  function pluginPriority(plugin) {
    var stage = plugin && plugin.stage;
    var value = stage && typeof stage.priority === "number" ? stage.priority : 0;
    return Math.max(-100, Math.min(100, value));
  }

  // 左栏插件的直白功能副标题：优先用 curated 文案，
  // 其次回落插件 description，最后才是类型标签——老师一眼看懂这插件干什么，而不是版本加点类型。
  var PLUGIN_TAGLINES = {
    "org.jiuzhang.core-bank": "内置大纲与题库引擎",
    "org.jiuzhang.editor": "录题、改题、删题工作台",
    "org.jiuzhang.paper-gen": "题篮排成 A4 练习卷",
    "org.jiuzhang.handout": "Markdown 讲义实时排 A4"
  };

  function pluginSidebarSubtitle(plugin) {
    var tagline = PLUGIN_TAGLINES[plugin.id];
    if (tagline) return tagline;
    var desc = String(plugin.description || "").trim();
    if (desc) return desc.split(/[：:。\n]/)[0].slice(0, 24);
    return KIND_LABELS[plugin.kind] || "插件";
  }

  // 拖拽排序的落盘键：只存条目 key 的顺序，不存任何业务数据。
  var PLUGIN_ORDER_KEY = "jzo.sidebar.order";

  function readPluginOrder() {
    try {
      var parsed = JSON.parse(window.localStorage.getItem(PLUGIN_ORDER_KEY) || "[]");
      return Array.isArray(parsed) ? parsed.filter(function (key) {
        return typeof key === "string";
      }) : [];
    } catch (error) {
      return [];   // 隐私模式或脏数据：按默认顺序渲染，绝不抛到调用点
    }
  }

  function savePluginOrder(keys) {
    try {
      window.localStorage.setItem(PLUGIN_ORDER_KEY, JSON.stringify(keys));
    } catch (error) {
      /* 写不进去只影响“记住顺序”，不影响本次拖拽结果 */
    }
  }

  function buildPluginRow(plugin) {
    var li = document.createElement("li");
    li.className = "ws-plugin-row";
    li.setAttribute("data-key", "plugin:" + String(plugin.id || ""));
    li.setAttribute("draggable", "true");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ws-plugin-item";
    btn.setAttribute("data-plugin-id", String(plugin.id || ""));
    btn.setAttribute("aria-current", String(Boolean(activePlugin && activePlugin.id === plugin.id)));
    var name = document.createElement("span");
    name.className = "ws-plugin-item-name";
    name.textContent = plugin.name || plugin.id || "未命名插件";
    var meta = document.createElement("span");
    meta.className = "ws-plugin-item-meta";
    meta.textContent = pluginSidebarSubtitle(plugin);
    btn.title = "v" + (plugin.version || "?");
    btn.appendChild(name);
    btn.appendChild(meta);
    btn.addEventListener("click", function () { enterPluginMode(plugin, btn); });
    li.appendChild(btn);
    return li;
  }

  function clearDropMarks() {
    if (!pluginListEl) return;
    var rows = pluginListEl.querySelectorAll(".ws-plugin-row[data-drop]");
    for (var i = 0; i < rows.length; i += 1) rows[i].removeAttribute("data-drop");
  }

  // 原生 HTML5 拖拽：拖起一行，落在目标行的上半/下半决定插前还是插后，
  // 顺序只写 localStorage（宿主自有），插件代码一律碰不到浏览器存储。
  function wirePluginDrag() {
    if (!pluginListEl) return;
    var draggingKey = "";
    pluginListEl.addEventListener("dragstart", function (event) {
      var row = event.target && event.target.closest ? event.target.closest(".ws-plugin-row") : null;
      if (!row) return;
      draggingKey = row.getAttribute("data-key") || "";
      row.classList.add("is-dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        try { event.dataTransfer.setData("text/plain", draggingKey); } catch (error) { /* 旧浏览器忽略 */ }
      }
    });
    pluginListEl.addEventListener("dragover", function (event) {
      if (!draggingKey) return;
      var row = event.target && event.target.closest ? event.target.closest(".ws-plugin-row") : null;
      clearDropMarks();
      if (!row || row.getAttribute("data-key") === draggingKey) return;
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
      var rect = row.getBoundingClientRect();
      row.setAttribute("data-drop", event.clientY < rect.top + rect.height / 2 ? "before" : "after");
    });
    pluginListEl.addEventListener("drop", function (event) {
      if (!draggingKey) return;
      var row = event.target && event.target.closest ? event.target.closest(".ws-plugin-row") : null;
      if (!row || row.getAttribute("data-key") === draggingKey) { draggingKey = ""; clearDropMarks(); return; }
      event.preventDefault();
      var targetKey = row.getAttribute("data-key") || "";
      var position = row.getAttribute("data-drop") || "before";
      var keys = [];
      var rows = pluginListEl.querySelectorAll(".ws-plugin-row");
      for (var i = 0; i < rows.length; i += 1) {
        var key = rows[i].getAttribute("data-key") || "";
        if (key && key !== draggingKey) keys.push(key);
      }
      var at = keys.indexOf(targetKey);
      if (at < 0) at = keys.length;
      if (position === "after") at += 1;
      keys.splice(at, 0, draggingKey);
      savePluginOrder(keys);
      draggingKey = "";
      clearDropMarks();
      renderPlugins(installedPlugins);
    });
    pluginListEl.addEventListener("dragend", function () {
      draggingKey = "";
      clearDropMarks();
      var dragging = pluginListEl.querySelectorAll(".ws-plugin-row.is-dragging");
      for (var i = 0; i < dragging.length; i += 1) dragging[i].classList.remove("is-dragging");
    });
  }

  function renderPlugins(plugins) {
    if (!pluginListEl) return;
    // 三态管理落到导航：停用的（enabled=false）与不占位的（show_in_sidebar=false）都不进左栏。
    var list = (plugins || []).filter(function (plugin) {
      return plugin.enabled !== false && plugin.show_in_sidebar !== false;
    });
    // 默认顺序：stage.priority 高者在前，同优先级按名称稳定排序；
    // 老师拖过之后，以 localStorage 里的顺序为唯一事实来源。
    list.sort(function (a, b) {
      var delta = pluginPriority(b) - pluginPriority(a);
      if (delta !== 0) return delta;
      return String(a.name || a.id || "").localeCompare(String(b.name || b.id || ""), "zh-CN");
    });
    var saved = readPluginOrder();
    function rank(key) {
      var index = saved.indexOf(key);
      return index < 0 ? Number.MAX_SAFE_INTEGER : index;
    }
    var chatRow = pluginListEl.querySelector('.ws-plugin-row[data-key="chat"]');
    var rows = [];
    if (chatRow) {
      var chatButton = chatRow.querySelector(".ws-plugin-item");
      if (chatButton) chatButton.setAttribute("aria-current", String(!activePlugin));
      rows.push(chatRow);
    }
    list.forEach(function (plugin) { rows.push(buildPluginRow(plugin)); });
    rows.sort(function (a, b) {
      return rank(a.getAttribute("data-key")) - rank(b.getAttribute("data-key"));
    });
    pluginListEl.textContent = "";
    rows.forEach(function (row) { pluginListEl.appendChild(row); });
    if (!list.length) {
      var empty = document.createElement("li");
      empty.className = "ws-plugin-empty";
      empty.textContent = "暂无插件";
      pluginListEl.appendChild(empty);
    }
    if (pluginCountEl) {
      pluginCountEl.hidden = false;
      pluginCountEl.textContent = String(list.length);
    }
  }

  var pluginSignature = null;
  var knownPluginIds = {};

  function pluginSignatureOf(data, plugins) {
    if (data && typeof data.signature === "string" && data.signature) return data.signature;
    return plugins.map(function (p) { return p.id + "@" + p.version; }).join("|");
  }

  /**
   * 热插拔：/api/plugins 每次请求都重新扫描 plugins/，后端另回一份清单签名。
   * 页面只需定时比对签名，用户往 plugins/ 里解压一个新目录（或拖装成功）后，
   * 左栏与画布无需重启即可看到变化。运行中的 iframe 代码不热替换——规范 §4
   * 明确要求刷新页面才加载新代码，这里只负责“发现与接入”。
   */
  function loadPlugins(options) {
    var opts = options || {};
    return fetch("/api/plugins", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var plugins = (data && data.plugins) || [];
        var signature = pluginSignatureOf(data, plugins);
        var changed = pluginSignature !== null && signature !== pluginSignature;
        var added = [];
        plugins.forEach(function (plugin) {
          if (!knownPluginIds[plugin.id]) added.push(plugin);
        });

        installedPlugins = plugins;
        if (activePlugin) {
          var still = null;
          for (var i = 0; i < plugins.length; i += 1) {
            if (plugins[i].id === activePlugin.id) { still = plugins[i]; break; }
          }
          if (still) {
            activePlugin = still;
            syncUiState(still);
            renderPluginPanel(still);
          } else {
            activePlugin = null;
            clearPluginPanel();
            setStage("工作台");
            markActiveEntry(null);
          }
        }
        renderPlugins(plugins);
        // 右栏主权跟着同一份清单刷新：插件装/卸/停用、画布页签换主人都不必刷新页面
        syncContextSlot();
        if (window.JzoStage && typeof window.JzoStage.updatePlugin === "function") {
          plugins.forEach(function (plugin) { window.JzoStage.updatePlugin(plugin); });
        }

        if (opts.announce !== false && changed) {
          if (added.length) {
            addBubble("sys", "检测到新插件 " + added.map(function (p) {
              return "「" + (p.name || p.id) + "」";
            }).join("、") + "，已热接入左栏，无需重启。");
          } else {
            addBubble("sys", "插件清单已更新（覆盖安装或卸载）。左栏与页签已刷新。");
          }
          logHistory("插件热刷新：" + (added.length ? added.map(function (p) { return p.id; }).join(",") : signature));
        }

        pluginSignature = signature;
        knownPluginIds = {};
        plugins.forEach(function (plugin) { knownPluginIds[plugin.id] = true; });
        return plugins;
      });
  }

  function pollPlugins() {
    if (document.hidden) return;
    loadPlugins({ announce: true }).catch(function () { /* 轮询失败保持现状，下次再试 */ });
  }
  window.setInterval(pollPlugins, 5000);
  window.addEventListener("focus", pollPlugins);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) pollPlugins();
  });

  // ============ 插件拖拽装：工作台全局兜底（选文件与索引入口在 /settings） ============
  var dropOverlay = document.getElementById("wsDropOverlay");
  var dragDepth = 0;

  function installPluginZip(file, replace) {
    if (!file) return Promise.resolve();
    if (!/\.zip$/i.test(file.name || "")) {
      addBubble("sys", "只接受 .zip 插件包（标准 zip，解压即用）。", { tone: "warn" });
      return Promise.resolve();
    }
    if (file.size > 50 * 1024 * 1024) {
      addBubble("sys", "zip 包超过 50 MB 上限。", { tone: "warn" });
      return Promise.resolve();
    }
    addBubble("sys", "正在安装 " + file.name + " …");
    return fetchWriteToken()
      .then(function (token) {
        return fetch("/api/plugins/install" + (replace ? "?replace=true" : ""), {
          method: "POST",
          headers: { "Content-Type": "application/zip", "X-JZO-Token": token },
          body: file,
        });
      })
      .then(function (r) {
        return r.json().catch(function () { return null; }).then(function (body) {
          if (r.status === 409 && !replace) {
            var question = readErrorDetail(r, body) + " 覆盖升级会先删除旧目录，继续吗？";
            if (window.confirm(question)) return installPluginZip(file, true);
            return null;
          }
          if (!r.ok) throw new Error(readErrorDetail(r, body));
          var plugin = body && body.plugin ? body.plugin : {};
          addBubble("sys", "插件已安装：" + (plugin.name || plugin.id) + " v" + (plugin.version || "?"));
          logHistory("安装插件 " + (plugin.name || plugin.id));
          // 装完立即刷新插件区；刷新失败不回滚安装结果，也不谎报安装失败。
          return loadPlugins().catch(function () { return null; });
        });
      })
      .catch(function (err) {
        addBubble("sys", "插件安装失败：" + err.message, { tone: "warn" });
      })
      .finally(function () {
        writeToken = null;
      });
  }

  function pickFirstZip(fileList) {
    for (var i = 0; i < (fileList || []).length; i += 1) {
      if (/\.zip$/i.test(fileList[i].name || "")) return fileList[i];
    }
    return null;
  }

  function hasFiles(event) {
    var types = (event.dataTransfer && event.dataTransfer.types) || [];
    return Array.prototype.indexOf.call(types, "Files") !== -1;
  }

  function showDropOverlay(show) {
    if (!dropOverlay) return;
    dropOverlay.hidden = !show;
  }

  window.addEventListener("dragenter", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    dragDepth += 1;
    showDropOverlay(true);
  });
  window.addEventListener("dragover", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
  });
  window.addEventListener("dragleave", function (event) {
    if (!hasFiles(event)) return;
    dragDepth -= 1;
    if (dragDepth <= 0) {
      dragDepth = 0;
      showDropOverlay(false);
    }
  });
  window.addEventListener("drop", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    dragDepth = 0;
    showDropOverlay(false);
    var file = pickFirstZip(event.dataTransfer && event.dataTransfer.files);
    if (!file) {
      addBubble("sys", "没看到 .zip 文件：插件包必须是标准 zip。", { tone: "warn" });
      return;
    }
    installPluginZip(file, false);
  });

  // ============ 右栏主权监听：画布页签换主人，插槽跟着换 ============
  function wireStageSovereignty() {
    if (!window.JzoBus || typeof window.JzoBus.on !== "function") return;
    window.JzoBus.on("stage.tab.activated", function (event) {
      var payload = (event && event.payload) || {};
      activeCanvasPluginId = typeof payload.pluginId === "string" ? payload.pluginId : "";
      syncContextSlot();
    });
    // 关掉页签后 stage 会自己 emit 一次 activated；这里先清账，避免主权挂在已关插件上
    window.JzoBus.on("stage.tab.closed", function () {
      activeCanvasPluginId = "";
      syncContextSlot();
    });
  }

  // ============ 初始化 ============
  // 中栏默认停在原生引导页，右栏默认住 AI 助手插件；左栏条目完全由 /api/plugins 渲染。
  wireDock();
  wirePluginDrag();
  wireStageSovereignty();
  setStage("工作台");
  markActiveEntry(null);
  addBubble("sys", "九章算子工作台已就绪 · 已装插件会自动接入 AI 助手的工具表（tool_calls），结果以「已调用插件」标识回显");

  loadPlugins()
    .then(function (plugins) {
      // 启动行为在插件清单渲染完之后执行：左栏条目已就位，进去才能高亮对应项
      return applyStartupBehavior(plugins).then(function () {
        var hasAssistant = plugins.some(function (p) { return p.id === ASSISTANT_PLUGIN_ID && p.enabled !== false; });
        if (!hasAssistant) {
          addBubble("sys", "右栏的 AI 助手插件（org.jiuzhang.chat）不在场：装回它才能用自然语言驱动底座。", { tone: "warn" });
        }
      });
    })
    .catch(function () { /* 探测失败保留「暂无插件」空态，不打扰用户 */ });

  loadProviders().catch(function () {
    renderModelChip();
  });
})();
