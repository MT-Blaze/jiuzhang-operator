/**
 * 全局快捷键派发与撞车裁决（军令 #16 模块一）。
 *
 * 三条口径，逐条对应军令原文：
 * 1. 「全部开放自定义」——底座侧的动作键位存在 data/plugin_state.json，
 *    设置页当场改、当场生效（清单签名一变就重装配）；
 * 2. 「冲突时底座最高权限优先」——装配顺序决定权重：底座动作先占位，
 *    插件自报的键位撞上任何已占位组合（底座或其他插件先到先得）就当场作废；
 * 3. 「撞车记红字、支持双击复制」——作废结果由调用方投进【报错诊断】，
 *    该视图本就逐条挂 data-copy 并带双击复制。
 *
 * 沙箱边界（AGENTS 铁律二）：插件跑在 opaque-origin iframe 里，它内部的按键
 * 永远不会冒泡到宿主文档。所以全局键有两条路——
 * 焦点在宿主：本模块直接派发，命中插件动作时用 deliver() 投 shortcut.invoke；
 * 焦点在插件：插件经 Host API 发 shortcut.press{combo}，由 press() 裁决归属。
 * 裸键（不带修饰键的 Esc/Enter/方向键）不进这张表：那是输入框与控件的地盘。
 */
(function () {
  "use strict";

  var HOST_ACTIONS = [
    { action: "sidebar.toggle", combo: "Ctrl+B", label: "折叠/展开左侧插件栏" },
    { action: "context.toggle", combo: "Ctrl+I", label: "折叠/展开右侧助手栏" },
    { action: "dock.toggle", combo: "Ctrl+J", label: "折叠/展开输出日志区" },
    { action: "assistant.focus", combo: "Ctrl+Shift+A", label: "唤起右栏 AI 助手" },
    { action: "console.open", combo: "Ctrl+Shift+S", label: "打开设置与控制台" }
  ];

  var runners = {};          // action -> function（底座动作的执行体）
  var bindings = {};         // action -> 当前生效组合键（用户改绑后的结果）
  var pluginRows = [];       // [{combo, action, label, pluginId, pluginName}]
  var conflicts = [];        // 本轮裁决判废的插件键位
  var deliver = null;        // 宿主 → 插件投递器（由 workspace.js 注入）
  var installed = false;     // 监听只挂一次：轮询重建键位表时不能叠 listener

  function canonical(combo) {
    return window.JzoPrefs ? window.JzoPrefs.canonicalCombo(combo) : "";
  }

  function defaults() {
    var out = {};
    HOST_ACTIONS.forEach(function (row) { out[row.action] = row.combo; });
    return out;
  }

  function catalogue() {
    return HOST_ACTIONS.map(function (row) {
      return { action: row.action, label: row.label, combo: row.combo };
    });
  }

  /** 定义一个底座动作的执行体；动作名与键位清单以 catalogue 为准。 */
  function defineHost(action, run) {
    if (typeof run === "function") runners[action] = run;
  }

  /**
   * 装配本轮生效的键位表。
   * @param {Object} overrides 用户改绑（action -> combo，空串表示解绑）；缺省回落默认值
   */
  function assemble(overrides) {
    bindings = {};
    var map = overrides && typeof overrides === "object" ? overrides : {};
    HOST_ACTIONS.forEach(function (row) {
      var has = Object.prototype.hasOwnProperty.call(map, row.action);
      var value = canonical(has ? map[row.action] : row.combo);
      if (has && !String(map[row.action] || "").trim()) value = "";
      if (value) bindings[row.action] = value;
    });
    return bindings;
  }

  function ownerOf(combo) {
    var key = canonical(combo);
    if (!key) return null;
    for (var action in bindings) {
      if (Object.prototype.hasOwnProperty.call(bindings, action) && bindings[action] === key) {
        return { owner: "host", action: action, combo: key };
      }
    }
    for (var i = 0; i < pluginRows.length; i += 1) {
      if (pluginRows[i].combo === key) return pluginRows[i];
    }
    return null;
  }

  /**
   * 登记插件自报的键位并当场裁决撞车。
   * @param {Array} plugins /api/plugins 回的插件条目（含 shortcuts / nickname / enabled）
   * @returns {Array} 本轮被判废的键位（调用方负责写进报错诊断）
   */
  function collect(plugins) {
    pluginRows = [];
    conflicts = [];
    (plugins || []).forEach(function (plugin) {
      if (!plugin || plugin.enabled === false) return;
      (plugin.shortcuts || []).forEach(function (row) {
        var combo = canonical(row.combo);
        if (!combo) return;
        var owner = ownerOf(combo);
        var name = plugin.nickname || plugin.name || plugin.id;
        if (owner) {
          conflicts.push({
            combo: combo,
            pluginId: plugin.id,
            pluginName: name,
            action: row.action,
            label: row.label || row.action,
            takenBy: owner.owner === "host" ? "底座动作 " + owner.action : "插件 " + owner.pluginName,
            takenAction: owner.action
          });
          return;
        }
        pluginRows.push({
          owner: "plugin",
          combo: combo,
          action: row.action,
          label: row.label || row.action,
          pluginId: plugin.id,
          pluginName: name
        });
      });
    });
    return conflicts;
  }

  /** 焦点在宿主时的派发；返回 true 表示这一键已被底座消费。 */
  function dispatch(event) {
    if (!event || event.defaultPrevented || event.repeat) return false;
    if (window.JzoMenu && typeof window.JzoMenu.isOpen === "function" && window.JzoMenu.isOpen()) {
      return false;
    }
    if (window.JzoDialogs && typeof window.JzoDialogs.isOpen === "function"
      && window.JzoDialogs.isOpen()) return false;
    var combo = window.JzoPrefs ? window.JzoPrefs.comboFromEvent(event) : "";
    if (!combo) return false;
    var owner = ownerOf(combo);
    if (!owner) return false;
    event.preventDefault();
    if (owner.owner === "host") {
      var run = runners[owner.action];
      if (typeof run === "function") run();
      return true;
    }
    if (typeof deliver === "function") {
      deliver(owner.pluginId, { action: owner.action, combo: owner.combo, via: "host" });
    }
    return true;
  }

  /**
   * 焦点在插件里时，插件经 Host API 上报的组合键裁决。
   * 底座占位 → 底座执行；插件自己占位 → 回给它自己；无人占位 → 交回插件自行处理。
   */
  function press(combo) {
    var key = canonical(combo);
    if (!key) return { handled: false, owner: "", action: "", reason: "BAD_COMBO" };
    var owner = ownerOf(key);
    if (!owner) return { handled: false, owner: "", action: "", reason: "UNBOUND" };
    if (owner.owner === "host") {
      var run = runners[owner.action];
      if (typeof run === "function") run();
      return { handled: true, owner: "host", action: owner.action, combo: key };
    }
    return { handled: true, owner: "plugin", action: owner.action, combo: key, pluginId: owner.pluginId };
  }

  function install(options) {
    var opts = options || {};
    if (typeof opts.deliver === "function") deliver = opts.deliver;
    if (installed) return;
    installed = true;
    document.addEventListener("keydown", function (event) { dispatch(event); }, true);
  }

  window.JzoKeys = {
    catalogue: catalogue,
    defaults: defaults,
    defineHost: defineHost,
    assemble: assemble,
    collect: collect,
    conflicts: function () { return conflicts.slice(); },
    pluginBindings: function () { return pluginRows.slice(); },
    ownerOf: ownerOf,
    dispatch: dispatch,
    press: press,
    install: install,
    bindings: function () {
      var copy = {};
      Object.keys(bindings).forEach(function (key) { copy[key] = bindings[key]; });
      return copy;
    }
  };
})();
