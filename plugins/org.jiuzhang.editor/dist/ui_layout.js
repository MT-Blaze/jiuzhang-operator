/**
 * ui_layout.js —— plugin.js 的「三栏拖宽」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var DEFAULT_IMAGE_RATIO = coreState.DEFAULT_IMAGE_RATIO;
    var DEFAULT_SOURCE_RATIO = coreState.DEFAULT_SOURCE_RATIO;
    var DRAFT_LAYOUT_KEY = coreState.DRAFT_LAYOUT_KEY;
    var LAYOUT_DRAFT_MS = coreState.LAYOUT_DRAFT_MS;
    var PANE_MIN = coreState.PANE_MIN;
    var SPLIT_W = coreState.SPLIT_W;
    var hostCall = deps.hostCall;
    var scheduleRender = deps.scheduleRender;
    var state = coreState.state;
    var colsEl = deps.dom.colsEl;
    var metricsEl = deps.dom.metricsEl;

  // ---------- 三栏拖宽（比例记账，像素只在下鼠标那一刻出现） ----------
  var layoutTimer = 0;

  /** 夹比例：留一份极窄缝，其余全给弹性栏。 */
  function clampRatio(value, fallback) {
    var number = Number(value);
    if (!isFinite(number) || number <= 0) return fallback;
    return Math.min(0.9, Math.max(0.02, number));
  }

  /** 当前画布的可用宽度：总宽与「中右两栏合起来」的那一段。 */
  function paneMetrics() {
    var total = colsEl ? colsEl.clientWidth : 0;
    var image = state.widths.image * total;
    var workbench = total - image - SPLIT_W;
    if (workbench < PANE_MIN * 2) workbench = PANE_MIN * 2;
    return { total: total, workbench: workbench };
  }

  /**
   * 把比例写进 CSS 变量：原图栏按总宽算比例，源码栏按中右两栏合起来的宽度算比例。
   * 画布变窄时两个比例都不动，三栏一起等比缩放。
   */
  function applyWidths() {
    var metrics = paneMetrics();
    if (metrics.total <= 0) return;
    state.widths.image = clampRatio(state.widths.image, DEFAULT_IMAGE_RATIO);
    state.widths.source = clampRatio(state.widths.source, DEFAULT_SOURCE_RATIO);
    colsEl.style.setProperty("--w-image", (state.widths.image * 100).toFixed(3) + "%");
    colsEl.style.setProperty("--w-source", (state.widths.source * 100).toFixed(3) + "%");
    if (metricsEl) metricsEl.setAttribute("data-pane-w", String(metrics.total));
  }

  /**
   * 老草稿记的是像素（260/360 那一版）：读回来时按当时的画布宽换算成比例，
   * 免得老布局一恢复就把原图栏撑成整幅画布。
   */
  function normalizeWidths(value) {
    var metrics = paneMetrics();
    var raw = (value && typeof value === "object") ? value : {};
    var image = Number(raw.image);
    var source = Number(raw.source);
    if (isFinite(image) && image > 1) {
      image = metrics.total > 0 ? image / metrics.total : DEFAULT_IMAGE_RATIO;
    }
    if (isFinite(source) && source > 1) {
      source = metrics.workbench > 0 ? source / metrics.workbench : DEFAULT_SOURCE_RATIO;
    }
    state.widths.image = clampRatio(image, DEFAULT_IMAGE_RATIO);
    state.widths.source = clampRatio(source, DEFAULT_SOURCE_RATIO);
  }

  function saveLayout() {
    hostCall("draft.save", {
      key: DRAFT_LAYOUT_KEY,
      value: { widths: state.widths, swap: state.swap }
    }).catch(function () { /* 布局偏好存不下就算了，不打扰老师 */ });
  }

  function queueLayoutSave() {
    window.clearTimeout(layoutTimer);
    layoutTimer = window.setTimeout(saveLayout, LAYOUT_DRAFT_MS);
  }

  /** 关页面前把还压在延时里的布局存回去：延时的主人就是这里，别处不许摸。 */
  function flushLayout() {
    if (!layoutTimer) return;
    window.clearTimeout(layoutTimer);
    layoutTimer = 0;
    saveLayout();
  }

  function bindSplit(node, which) {
    if (!node) return;
    var drag = null;
    node.addEventListener("pointerdown", function (event) {
      drag = { x: event.clientX, image: state.widths.image, source: state.widths.source };
      node.setAttribute("data-drag", "true");
      if (node.setPointerCapture) node.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    node.addEventListener("pointermove", function (event) {
      if (!drag) return;
      var delta = event.clientX - drag.x;
      var metrics = paneMetrics();
      // 像素位移立刻换算成比例位移：拖到哪儿都是「占画布的几分之几」
      if (which === "image") {
        state.widths.image = drag.image + (metrics.total > 0 ? delta / metrics.total : 0);
      } else {
        state.widths.source = drag.source + (metrics.workbench > 0 ? delta / metrics.workbench : 0);
      }
      applyWidths();
    });
    function stop(event) {
      if (!drag) return;
      drag = null;
      node.removeAttribute("data-drag");
      if (node.releasePointerCapture && event && event.pointerId != null) {
        try { node.releasePointerCapture(event.pointerId); } catch (error) { /* 已经松开了 */ }
      }
      queueLayoutSave();
      scheduleRender();
    }
    node.addEventListener("pointerup", stop);
    node.addEventListener("pointercancel", stop);
    node.addEventListener("keydown", function (event) {
      // 焦点在里面的互换钮上时，方向键归按钮（不许把回车/方向键顺手变成拖栏）
      if (event.target !== node) return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      var step = event.shiftKey ? 8 : 24;
      var delta = event.key === "ArrowLeft" ? -step : step;
      var metrics = paneMetrics();
      if (which === "image") {
        state.widths.image += metrics.total > 0 ? delta / metrics.total : 0;
      } else {
        state.widths.source += metrics.workbench > 0 ? delta / metrics.workbench : 0;
      }
      applyWidths();
      queueLayoutSave();
      scheduleRender();
      event.preventDefault();
    });
  }

    return {
      applyWidths: applyWidths,
      bindSplit: bindSplit,
      clampRatio: clampRatio,
      flushLayout: flushLayout,
      layoutTimer: layoutTimer,
      normalizeWidths: normalizeWidths,
      paneMetrics: paneMetrics,
      queueLayoutSave: queueLayoutSave,
      saveLayout: saveLayout,
    };
  }

  global.JzoEditorLayout = { create: create };
})(window);
