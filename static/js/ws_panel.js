/**
 * ws_panel.js —— 工作台右栏的「插件参数账本」与右栏主权对账。
 *
 * 右栏不再画「插件快捷操作」面板：面板一律由声明 sidebar.right 的页签插件自带。
 * 参数账本保留——录题辅助栏等插件仍经 Host API 的 ui.params.set 跨帧改参数，
 * 宿主继续负责「人改过的字段优先于 AI」的仲裁，只是不再多画一套同名控件。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var dockLine = deps.dockLine;
    var getCtxRail = deps.getCtxRail;
    var loadPlugins = deps.loadPlugins;
    var publishUiParams = deps.publishUiParams;
    var stageTitle = deps.stageTitle;
    var wsState = deps.wsState;

  // ============ 右栏插件参数账本 ============
  // 控件由 plugin.json 的 ui 字段下发。人类在插件自带面板里改下拉 → revisions[key] 加一；
  // AI 改参数时用发送时的快照比对，只要人类在请求飞行期间动过同一字段，AI 的设定就让位。
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
    wsState.uiPanelControls = controls;
    wsState.uiState = { pluginId: plugin ? plugin.id : null, values: values, revisions: {} };
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

  function resetUiState() {
    wsState.uiPanelControls = [];
    wsState.uiState = { pluginId: null, values: {}, revisions: {} };
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
      applied.push({ label: control.label, value: incoming });
    });
    if (applied.length) {
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
  }

  // 助手插件向底座要服务的唯一门面：白名单在 stage.js，能力在这里。
  window.JzoWorkspace = {
    stateSnapshot: stateSnapshot,
    applyAiParams: applyAiParams,
    syncContextSlot: syncContextSlot,
    openContextRail: function () {
      var rail = typeof getCtxRail === "function" ? getCtxRail() : null;
      if (rail && typeof rail.openCtx === "function") rail.openCtx();
    },
    refreshPlugins: function () { return loadPlugins({ announce: true }); },
    activeCanvasPlugin: function () { return wsState.activeCanvasPluginId; }
  };

    return {
      applyAiParams: applyAiParams,
      applyUiParams: applyUiParams,
      compactControls: compactControls,
      currentUiValues: currentUiValues,
      findUiControl: findUiControl,
      initUiState: initUiState,
      panelControls: panelControls,
      resetUiState: resetUiState,
      snapshotRevisions: snapshotRevisions,
      stateSnapshot: stateSnapshot,
      syncContextSlot: syncContextSlot,
      syncRightSlotUiState: syncRightSlotUiState,
      syncUiState: syncUiState,
    };
  }

  global.JzoWsPanel = { create: create };
})(window);
