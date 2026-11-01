/**
 * ui_boot.js —— plugin.js 的「819」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var GHOST_SCROLL_MS = coreState.GHOST_SCROLL_MS;
    var applySwap = deps.applySwap;
    var applyWidths = deps.applyWidths;
    var bindSplit = deps.bindSplit;
    var flushLayout = deps.flushLayout;
    var flushMetaDraft = deps.flushMetaDraft;
    var flushWorklist = deps.flushWorklist;
    var noteActivity = deps.noteActivity;
    var noteFieldNode = deps.noteFieldNode;
    var scheduleRender = deps.scheduleRender;
    var setFormatButtons = deps.setFormatButtons;
    var signalCanvasScroll = deps.signalCanvasScroll;
    var stashOnUnload = deps.stashOnUnload;
    var state = coreState.state;
    var syncScroll = deps.syncScroll;
    var wireLamp = deps.wireLamp;
    var colsEl = deps.dom.colsEl;
    var imageBodyEl = deps.dom.imageBodyEl;
    var renderBodyEl = deps.dom.renderBodyEl;
    var sourceBodyEl = deps.dom.sourceBodyEl;

  /** 幽灵滚动条：只在真滚动时让滚动条浮出来，停手就淡回去（纯样式行为，不参与业务）。 */
  function wireGhost(node) {
    if (!node) return;
    var timer = 0;
    node.addEventListener("scroll", function () {
      node.classList.add("is-scrolling");
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { node.classList.remove("is-scrolling"); }, GHOST_SCROLL_MS);
    }, { passive: true });
  }

  function bind() {
    bindSplit(document.getElementById("edSplitImage"), "image");
    bindSplit(document.getElementById("edSplitSource"), "source");
    document.addEventListener("focusin", function (event) {
      var node = event.target;
      if (node && node.getAttribute && node.getAttribute("data-field") != null) noteFieldNode(node);
    });
    applySwap(state.swap, false);
    setFormatButtons(state.format);
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (node) {
      if (!node) return;
      wireGhost(node);
      node.addEventListener("scroll", function () {
        syncScroll(node);
        if (state.slot === "stage.center") signalCanvasScroll();
      });
    });
    wireLamp();
    // 三分钟没人碰就静默存回中转池：任何一次动手都算「有人在」，这里只做记账。
    ["pointerdown", "keydown", "wheel", "input"].forEach(function (type) {
      window.addEventListener(type, noteActivity, { passive: true, capture: true });
    });
    if (window.ResizeObserver && colsEl) {
      var observer = new window.ResizeObserver(function () {
        applyWidths();
        scheduleRender();
      });
      observer.observe(colsEl);
    }
    window.addEventListener("beforeunload", function () {
      stashOnUnload();
      flushLayout();
      flushWorklist();
      flushMetaDraft();
    });
  }

    return {
      bind: bind,
      wireGhost: wireGhost,
    };
  }

  global.JzoEditorBoot = { create: create };
})(window);
