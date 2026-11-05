/**
 * ui_batch_delete.js —— 批次卡片上的【删除批次】（可整块下架）。
 *
 * 与批次列表渲染刻意解耦：ui_batches 只在循环里调一次
 * ``renderDeleteBatchButton(card, row)``。要下架这颗按钮，删掉 index.html 里的
 * 这一行脚本、或给 ``.btn-delete-batch`` 加 ``display:none`` 即可，
 * 核心渲染逻辑一行都不用改。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var el = deps.el;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var publishSelection = deps.publishSelection;
    var publishView = deps.publishView;
    var refreshBatches = deps.refreshBatches;
    var setMode = deps.setMode;
    var state = coreState.state;

    function renderDeleteBatchButton(card, row) {
      var batchId = String(card.batch_id || "");
      var button = el("button", "btn-delete-batch", "删除批次");
      button.type = "button";
      button.setAttribute("aria-label", "删除批次 " + batchId);
      button.addEventListener("click", function (event) {
        event.stopPropagation();
        if (!window.confirm("确认删除该批次？将同时清理所有待审题和原卷资产")) return;
        button.disabled = true;
        button.textContent = "删除中…";
        hostCall("pending.delete_batch", { batch_id: batchId }).then(function () {
          dock("批次 " + batchId + " 已彻底删除。");
          if (String(state.batchId || "") === batchId) {
            state.batchId = "";
            state.items = [];
            state.pageImages = [];
            state.scanBatch = false;
            setMode("list");
            publishView("list");
            publishSelection();
          }
          refreshBatches();
        }, function (error) {
          button.disabled = false;
          button.textContent = "删除批次";
          dockWarn("删除批次 " + batchId + " 失败：" + ((error && error.message) || "未知原因"),
            errorDetail(error));
        });
      });
      row.appendChild(button);
    }

    return { renderDeleteBatchButton: renderDeleteBatchButton };
  }

  global.JzoEditorBatchDelete = { create: create };
})(window);
