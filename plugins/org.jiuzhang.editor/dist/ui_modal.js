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
    var dupModalEl = deps.dom.dupModalEl;
    var dupTextEl = deps.dom.dupTextEl;

  // ---------- 弹窗：查重与彻底删除共用一套开合规矩（焦点圈住、Esc 可关、关掉还焦） ----------
  var modalRestoreFocus = null;

  function openModalNode() {
    if (dupModalEl && !dupModalEl.hidden) return dupModalEl;
    if (delModalEl && !delModalEl.hidden) return delModalEl;
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

  /** 查重命中：弹窗给两颗钮——返回修改 / 强行覆盖。 */
  function openDupModal(item, error) {
    if (!dupModalEl) return;
    panel.pending = item;
    if (dupTextEl) {
      dupTextEl.textContent = "主库里已经有同一道题（"
        + ((error && error.existingId) || "已有记录")
        + "）。可以返回修改，也可以强行覆盖主库那一条。";
    }
    openModal(dupModalEl);
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
      openDupModal: openDupModal,
      openModal: openModal,
      openModalNode: openModalNode,
    };
  }

  global.JzoEditorModal = { create: create };
})(window);
