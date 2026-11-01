/**
 * 底座微内核之一：总线出口与主题白名单（从 stage.js 拆出）。
 *
 * 插件能主动发的事件主题只许是这里列的这些：三区、舞台选区与三条跨端跳转口。
 * 不许发 layout.* / ui.params.*（那是底座与人的地盘，防插件反向操控面板）。
 *
 *   var busCore = JzoCoreBus.create({ bus: window.JzoBus });
 *   busCore.emit("region.dock", { text: "…" });   // 带 source: "stage"
 *   busCore.denies("layout.left");                // true → 插件越权，丢弃
 */
(function (global) {
  "use strict";

  var PUBLISH_ALLOW = [
    "region.dock", "region.left", "region.right", "stage.selection",
    "system.open_editor", "system.return_from_editor", "system.editor_close",
    "system.open_bank",
    // 军令 #27：录题插件在辅助栏那张 iframe 里收到的文件，转交给宿主，
    // 由宿主送进画布的收集筐（插件两帧之间不直连）。
    "editor.collect_files",
    // 军令 #29：画布的悬停与滚动信号，投给右栏辅助栏（呼吸灯 + 批次折叠）。
    "editor.canvas_state"
  ];

  function create(ctx) {
    var bus = ctx && ctx.bus;

    function emit(topic, payload) {
      if (bus && typeof bus.emit === "function") bus.emit(topic, payload, { source: "stage" });
    }

    function dock(text, topic) {
      emit("region.dock", { text: text, topic: topic || "" });
    }

    /** 插件想发这个主题？true = 越权，调用方必须丢弃并记一笔。 */
    function denies(topic) {
      return PUBLISH_ALLOW.indexOf(topic) < 0;
    }

    return { allow: PUBLISH_ALLOW, emit: emit, dock: dock, denies: denies };
  }

  global.JzoCoreBus = { PUBLISH_ALLOW: PUBLISH_ALLOW, create: create };
})(window);
