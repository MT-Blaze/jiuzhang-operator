/**
 * ui_modal.js —— plugin.js 的「弹窗」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var panel = coreState.panel;
    var delModalEl = deps.dom.delModalEl;
    var batchPurgeModalEl = deps.dom.batchPurgeModalEl;
    var poolDelModalEl = deps.dom.poolDelModalEl;

  // ---------- 弹窗：彻底删除（焦点圈住、Esc 可关、关掉还焦） ----------
  // 查重对比浮层不在这套里：它按军令 #23 一颗按钮都不放（画布里只许有题目内容），
  // 没有可圈住的焦点，开合由 ui_dup.js 自己管。
  var modalRestoreFocus = null;

  function openModalNode() {
    if (delModalEl && !delModalEl.hidden) return delModalEl;
    if (batchPurgeModalEl && !batchPurgeModalEl.hidden) return batchPurgeModalEl;
    // 重题池的【删除】同样走二次确认（军令 #32 · 判据 5.4）：不加进这一串，
    // 焦点圈不住、Esc 也关不掉，等于把红按钮的确认样式做成两套。
    if (poolDelModalEl && !poolDelModalEl.hidden) return poolDelModalEl;
    return null;
  }

  function openModal(node) {
    if (!node) return;
    modalRestoreFocus = document.activeElement;
    node.hidden = false;
    var first = node.querySelector("button");
    if (first && typeof first.focus === "function") first.focus();
  }

  function closeModal(node) {
    if (!node || node.hidden) return;
    node.hidden = true;
    if (modalRestoreFocus && typeof modalRestoreFocus.focus === "function") {
      modalRestoreFocus.focus();
    }
    modalRestoreFocus = null;
  }

  document.addEventListener("keydown", function (event) {
    var node = openModalNode();
    if (!node) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeModal(node);
      return;
    }
    if (event.key !== "Tab") return;
    var focusable = node.querySelectorAll("button");
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

    return {
      closeModal: closeModal,
      modalRestoreFocus: modalRestoreFocus,
      openModal: openModal,
      openModalNode: openModalNode,
    };
  }

  global.JzoEditorModal = { create: create };
})(window);
