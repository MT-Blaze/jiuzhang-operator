/**
 * ws_panel.js —— workspace.js 的「右侧插件面板」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1 同款口径：底座 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var clampText = deps.clampText;
    var dockLine = deps.dockLine;
    var getCtxRail = deps.getCtxRail;
    var loadPlugins = deps.loadPlugins;
    var pluginControlsEl = deps.pluginControlsEl;
    var pluginPanel = deps.pluginPanel;
    var pluginPanelDesc = deps.pluginPanelDesc;
    var pluginPanelHint = deps.pluginPanelHint;
    var pluginPanelTitle = deps.pluginPanelTitle;
    var publishUiParams = deps.publishUiParams;
    var stageTitle = deps.stageTitle;
    var uiStateSummary = deps.uiStateSummary;
    var wsState = deps.wsState;

  // ============ 右侧插件面板（双向操控） ============
  // 控件由 plugin.json 的 ui 字段（或底座按能力生成的默认面板）下发。
  // 人类改下拉 → revisions[key] 加一；AI 改参数时用发送时的快照比对，
  // 只要人类在请求飞行期间动过同一字段，AI 的设定就让位。
  function panelControls(plugin) {
    var ui = plugin && plugin.ui;
    return ui && Array.isArray(ui.controls) ? ui.controls : [];
  }

  /**
   * 插件自带整块右栏面板吗？
   *
   * 声明了 sidebar.right 的插件，它的面板就住在这栏里（比如录题辅助栏）。
   * 住进右栏时宿主再画一遍同名快捷按钮就成了两套，老师会以为有一个是坏的。
   *
   * 判据只认插槽本身，不用清单里的 ui.panel 开关：那个开关只管「画不画」，
   * 管不了「插件住不住」，字面上却像后者，早年被误读成「关掉辅助栏」。
   */
  function ownsOwnRightPanel(plugin) {
    if (!plugin || !Array.isArray(plugin.slots)) return false;
    return plugin.slots.indexOf("sidebar.right") >= 0;
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
    wsState.uiPanelControls = controls;
    wsState.uiState = { pluginId: plugin ? plugin.id : null, values: values, revisions: {} };
    updateUiStateSummary();
  }

  function syncUiState(plugin) {
    var controls = panelControls(plugin);
    var next = {};
    controls.forEach(function (control) {
      if (control.type !== "select") return;
      var options = Array.isArray(control.options) ? control.options : [];
      var fallback = options.length ? options[0].value : "";
      var previous = wsState.uiState.values[control.key];
      var valid = options.some(function (option) { return option.value === previous; });
      next[control.key] = valid ? previous : (control.default || fallback);
    });
    wsState.uiPanelControls = controls;
    wsState.uiState.pluginId = plugin ? plugin.id : null;
    wsState.uiState.values = next;
  }

  function clearPluginPanel() {
    wsState.uiPanelControls = [];
    wsState.uiState = { pluginId: null, values: {}, revisions: {} };
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
    // 插件自带的整块面板（如录题辅助栏）已经住进右栏插槽时，
    // 宿主这层「人机共设」快捷操作只会重复一遍，不画。
    if (ui.panel === false || ownsOwnRightPanel(plugin)) {
      pluginControlsEl.textContent = "";
      if (pluginPanel) pluginPanel.hidden = true;
      updateUiStateSummary();
      return;
    }
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
          if (wsState.uiState.values[control.key] === option.value) item.selected = true;
          select.appendChild(item);
        });
        select.addEventListener("change", function () {
          wsState.uiState.values[control.key] = select.value;
          wsState.uiState.revisions[control.key] = (wsState.uiState.revisions[control.key] || 0) + 1;
          updateUiStateSummary();
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
    wsState.uiPanelControls.forEach(function (control) {
      if (control.type !== "select") return;
      var value = wsState.uiState.values[control.key];
      if (value == null || value === "") return;
      var edited = wsState.uiState.revisions[control.key] ? "（你已改）" : "";
      parts.push((control.label || control.key) + "：" + value + edited);
    });
    uiStateSummary.textContent = parts.length
      ? "当前参数 " + parts.join(" · ")
      : "面板操作会实时同步给 AI。";
  }

  function currentUiValues() {
    var values = {};
    Object.keys(wsState.uiState.values).forEach(function (key) {
      values[key] = wsState.uiState.values[key];
    });
    return values;
  }

  function compactControls() {
    return wsState.uiPanelControls.map(function (control) {
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
      var value = wsState.uiState.values[key];
      return value == null ? whole : String(value);
    });
  }

  /**
   * 人点面板按钮 = 请右栏的插件面板把这句话发出去。
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
        plugin_id: wsState.uiState.pluginId,
        command: text,
        label: clampText(label, 40)
      });
    }
  }

  function findUiControl(id, type) {
    for (var i = 0; i < wsState.uiPanelControls.length; i += 1) {
      var control = wsState.uiPanelControls[i];
      if (control.id === id && control.type === type) return control;
    }
    return null;
  }

  function snapshotRevisions() {
    var snapshot = {};
    Object.keys(wsState.uiState.revisions).forEach(function (key) {
      snapshot[key] = wsState.uiState.revisions[key];
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
      if (snapshot && snapshot[key] !== wsState.uiState.revisions[key]) {
        skipped.push({ label: control.label, value: incoming, reason: "你刚手动改过" });
        return;
      }
      wsState.uiState.values[key] = incoming;
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
   * 插件申请设面板参数（军令 #15 任务 1、2）。
   * 助手交出「目标插件 + 发送时拍的修订号快照」：目标不对整批拒，
   * 快照对不上（人在请求飞行期间手改过同一字段）单字段跳过——AI 永远赢不过人的手。
   */
  function applyAiParams(params, snapshot, targetPluginId) {
    if (!wsState.uiState.pluginId) {
      return { error: { code: "NO_PANEL", message: "当前右栏没有可调参数的插件面板" } };
    }
    var wanted = String(targetPluginId || "");
    if (wanted && wanted !== wsState.uiState.pluginId) {
      return { error: { code: "PANEL_MOVED", message: "面板已切到「" + wsState.uiState.pluginId + "」，本次设定作废" } };
    }
    var outcome = applyUiParams(params, snapshot);
    dockLine("插件经宿主设定面板参数：应用 " + outcome.applied.length
      + " 项、跳过 " + outcome.skipped.length + " 项。", "agent.params");
    return outcome;
  }

  /**
   * 宿主工作区快照（window.JzoWorkspace 的服务面之一）：
   * 助手插件能看见的全部世界就是这一份 JSON——没有 DOM、没有令牌、没有库连接。
   */
  function stateSnapshot() {
    var snapshot = {
      current_task: wsState.currentTask || "未选择",
      stage: (stageTitle && stageTitle.textContent) || wsState.currentTask || "工作台",
      textbook: "未选择",
      right_slot: window.JzoContextPanel ? window.JzoContextPanel.activeId() : null,
      tabs: window.JzoStage && typeof window.JzoStage.tabs === "function" ? window.JzoStage.tabs() : []
    };
    if (wsState.activePlugin) {
      snapshot.plugin = {
        id: wsState.activePlugin.id,
        name: wsState.activePlugin.name,
        version: wsState.activePlugin.version,
        kind: wsState.activePlugin.kind,
        description: wsState.activePlugin.description,
        capabilities: wsState.activePlugin.capabilities || []
      };
      if (wsState.uiPanelControls.length) {
        snapshot.ui = {
          plugin_id: wsState.activePlugin.id,
          values: currentUiValues(),
          controls: compactControls(),
          revisions: snapshotRevisions()
        };
      }
    }
    return snapshot;
  }

  /** 右栏主权对账：画布页签换了主人，插槽跟着换；折叠随住户有无自动跟一次。 */
  function syncContextSlot() {
    if (window.JzoContextPanel && typeof window.JzoContextPanel.sync === "function") {
      window.JzoContextPanel.sync(wsState.installedPlugins, wsState.activeCanvasPluginId);
    }
    syncRightSlotUiState();
    var rail = typeof getCtxRail === "function" ? getCtxRail() : null;
    if (!rail) return;
    var occupied = !!(window.JzoContextPanel && typeof window.JzoContextPanel.activeId === "function"
      && window.JzoContextPanel.activeId());
    if (occupied) rail.autoOpenCtx();
    else rail.collapseCtxIfAuto();
  }

  /**
   * 面板参数账本跟着右栏主人走：入住插件若带 select 控件（录题辅助栏的格式/互换），
   * 它就是当前 uiState 的主人，插件的 ui.params.set 才不会被宿主判成 PANEL_MOVED。
   * 没有 select 控件的插件（只有按钮）不抢账本，只保留在左栏点击时的那份。
   */
  function syncRightSlotUiState() {
    var id = window.JzoContextPanel && typeof window.JzoContextPanel.activeId === "function"
      ? window.JzoContextPanel.activeId() : "";
    if (!id || id === wsState.uiState.pluginId) return;
    var claimant = null;
    for (var i = 0; i < wsState.installedPlugins.length; i += 1) {
      if (wsState.installedPlugins[i].id === id) { claimant = wsState.installedPlugins[i]; break; }
    }
    if (!claimant) return;
    var hasSelect = panelControls(claimant).some(function (control) {
      return control.type === "select";
    });
    if (!hasSelect) return;
    syncUiState(claimant);
    renderPluginPanel(claimant);
  }

  // 助手插件向底座要服务的唯一门面：白名单在 stage.js，能力在这里。
  window.JzoWorkspace = {
    stateSnapshot: stateSnapshot,
    applyAiParams: applyAiParams,
    syncContextSlot: syncContextSlot,
    refreshPlugins: function () { return loadPlugins({ announce: true }); },
    activeCanvasPlugin: function () { return wsState.activeCanvasPluginId; }
  };

    return {
      applyAiParams: applyAiParams,
      applyUiParams: applyUiParams,
      clearPluginPanel: clearPluginPanel,
      compactControls: compactControls,
      currentUiValues: currentUiValues,
      expandCommand: expandCommand,
      findUiControl: findUiControl,
      initUiState: initUiState,
      ownsOwnRightPanel: ownsOwnRightPanel,
      panelControls: panelControls,
      publishPanelButton: publishPanelButton,
      renderPluginPanel: renderPluginPanel,
      snapshotRevisions: snapshotRevisions,
      stateSnapshot: stateSnapshot,
      syncContextSlot: syncContextSlot,
      syncRightSlotUiState: syncRightSlotUiState,
      syncUiState: syncUiState,
      updateUiStateSummary: updateUiStateSummary,
    };
  }

  global.JzoWsPanel = { create: create };
})(window);
