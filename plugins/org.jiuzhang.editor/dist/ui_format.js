/**
 * ui_format.js —— plugin.js 的「源码 / 卡片」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var FORMATS = coreState.FORMATS;
    var PLUGIN_ID = coreState.PLUGIN_ID;
    var alignRows = deps.alignRows;
    var hostCall = deps.hostCall;
    var panel = coreState.panel;
    var publishSelection = deps.publishSelection;
    var queueLayoutSave = deps.queueLayoutSave;
    var renderAll = deps.renderAll;
    var state = coreState.state;
    var colsEl = deps.dom.colsEl;
    var panelFmtBoxedEl = deps.dom.panelFmtBoxedEl;
    var panelFmtLatexEl = deps.dom.panelFmtLatexEl;
    var panelMetricsEl = deps.dom.panelMetricsEl;
    var panelSwapEl = deps.dom.panelSwapEl;
    var panelViewNoteEl = deps.dom.panelViewNoteEl;
    var renderBodyEl = deps.dom.renderBodyEl;
    var sourceBodyEl = deps.dom.sourceBodyEl;
    var sourceHintEl = deps.dom.sourceHintEl;

  // ---------- 源码 / 卡片（开关住辅助栏；画布是视图主人，宿主 ui.params 做跨帧对账） ----------
  // 互换钮被点击时会先把焦点从源码框夺走：记住最后一只有 data-field 的编辑框，换完把光标送回去
  var lastFieldNode = null;

  /** 记焦点：focusin 那边每拿到一只可编辑字段就登记一次，本模块自己留着用。 */
  function noteFieldNode(node) {
    lastFieldNode = node;
  }

  function setFormatButtons(format) {
    var value = FORMATS[format] ? format : "latex";
    panel.format = value;
    [panelFmtLatexEl, panelFmtBoxedEl].forEach(function (node) {
      if (!node) return;
      var on = node.getAttribute("data-format") === value;
      node.classList.toggle("is-on", on);
      node.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (panelViewNoteEl) {
      panelViewNoteEl.textContent = value === "boxed"
        ? "卡片：框里只有内容，环境骨架改不动。"
        : "源码：整段源码直接编辑。两者只是同一份源码的两种编辑面。";
    }
    if (panelMetricsEl) panelMetricsEl.setAttribute("data-format", value);
  }

  function setFormat(next) {
    var value = FORMATS[next] ? next : "latex";
    if (value === state.format) return;
    state.format = value;
    if (sourceHintEl) {
      sourceHintEl.textContent = value === "boxed"
        ? "卡片 · 框里只有内容，环境骨架改不动"
        : "源码 · 整段源码直接编辑";
    }
    setFormatButtons(value);
    renderAll();
    publishSelection();
  }

  /**
   * 辅助栏点格式：按钮先亮，再请宿主把参数广播给画布帧。
   * 面板拿不到画布的 DOM，真正切视图只发生在画布收到 ui.params.changed 之后。
   */
  function chooseFormatFromPanel(next) {
    if (!FORMATS[next]) return;
    setFormatButtons(next);
    hostCall("ui.params.set", {
      params: { format: next },
      snapshot: panel.uiRevisions || {},
      plugin_id: PLUGIN_ID
    }).catch(function () {
      if (panel.selection) setFormatButtons(panel.selection.format || "latex");
    });
  }

  // ---------- 源码 / 渲染左右互换（只改视觉顺序，DOM 不挪） ----------
  function setSwapButton(on) {
    panel.swap = Boolean(on);
    if (!panelSwapEl) return;
    var label = panel.swap ? "⇄ 换回" : "⇄ 互换";
    panelSwapEl.setAttribute("aria-pressed", panel.swap ? "true" : "false");
    panelSwapEl.setAttribute("aria-label", label + "（源码与渲染左右位置）");
    panelSwapEl.setAttribute("title", label + "（源码与渲染左右位置）");
    panelSwapEl.textContent = label;
  }

  function applySwap(next, persist) {
    state.swap = Boolean(next);
    if (colsEl) colsEl.setAttribute("data-swap", state.swap ? "true" : "false");
    setSwapButton(state.swap);
    if (persist) queueLayoutSave();
  }

  /** 辅助栏点互换：同样只把意图交给宿主，画布收到广播后才换位并回投选区。 */
  function toggleSwapFromPanel() {
    var next = !panel.swap;
    setSwapButton(next);
    hostCall("ui.params.set", {
      params: { swap: next ? "true" : "false" },
      snapshot: panel.uiRevisions || {},
      plugin_id: PLUGIN_ID
    }).catch(function () {
      if (panel.selection) setSwapButton(Boolean(panel.selection.swap));
    });
  }

  /** 辅助栏点【← 返回列表】：意图交给宿主，画布收到广播后才回列表。 */
  function backToListFromPanel() {
    hostCall("ui.params.set", {
      params: { view: "list" },
      snapshot: panel.uiRevisions || {},
      plugin_id: PLUGIN_ID
    }).catch(function () { /* 参数通道没通就留在三栏，绝不擅自改本帧 DOM */ });
  }

  /**
   * 互换的只有视觉位置：源码框与渲染块还是原来那两个 DOM 节点，
   * 值、选区、撤销栈与滚动进度都不会离开元素，所以只需在换序后补一次行高对齐。
   */
  function toggleSwap() {
    var focus = lastFieldNode && document.contains(lastFieldNode) ? lastFieldNode : null;
    var caret = null;
    if (focus) {
      try { caret = [focus.selectionStart, focus.selectionEnd]; } catch (error) { caret = null; }
    }
    var scrolls = [sourceBodyEl, renderBodyEl].map(function (node) {
      return node ? node.scrollTop : 0;
    });
    applySwap(!state.swap, true);
    alignRows();
    [sourceBodyEl, renderBodyEl].forEach(function (node, position) {
      if (node) node.scrollTop = scrolls[position];
    });
    // 点按钮会把焦点从源码框拿走：换完把光标送回原处，老师接着打字
    if (focus && document.activeElement !== focus) {
      try { focus.focus({ preventScroll: true }); } catch (error) { focus.focus(); }
      if (caret) {
        try { focus.setSelectionRange(caret[0], caret[1]); } catch (error) { /* input 不一定支持 */ }
      }
    }
    window.requestAnimationFrame(function () {
      alignRows();
      [sourceBodyEl, renderBodyEl].forEach(function (node, position) {
        if (node) node.scrollTop = scrolls[position];
      });
    });
  }

    return {
      applySwap: applySwap,
      backToListFromPanel: backToListFromPanel,
      chooseFormatFromPanel: chooseFormatFromPanel,
      lastFieldNode: lastFieldNode,
      noteFieldNode: noteFieldNode,
      setFormat: setFormat,
      setFormatButtons: setFormatButtons,
      setSwapButton: setSwapButton,
      toggleSwap: toggleSwap,
      toggleSwapFromPanel: toggleSwapFromPanel,
    };
  }

  global.JzoEditorFormat = { create: create };
})(window);
