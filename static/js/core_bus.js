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
    "editor.canvas_state",
    // 军令 #31：查重命中后的裁决请求。辅助栏拿不到渲染能力（它那帧按军令 #23
    // 绝不放预览），只能把「两侧文档」递给画布，由画布弹对比窗、亮红灯。
    // 画布裁决完再把结果回投给辅助栏，两帧之间始终隔着宿主这一跳。
    "editor.dup_review",
    // 4.3 LaTeX 清洗：辅助栏把「开/收预览」递进画布，画布回执 opened/closed/tab_not_live。
    // 正文对照只在画布与宿主中继之间走，不进 system.* 广播。
    "editor.clean_review",
    "editor.clean_review_state",
    // 军令 #32 · 第五步：重题池的左右渲染对比住画布那帧，四个动作住辅助栏；
    // 【全部入库】前的整批扫琥珀灯同样要指挥画布跳题。两条都是辅助栏→画布的单向指令。
    "editor.pool_review",
    "editor.batch_review",
    // 查重三栏：辅助栏裁判台发令变身、决断后换题、画布 Esc 收窗——双向各投对方一帧。
    "editor.dup_compare"
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
