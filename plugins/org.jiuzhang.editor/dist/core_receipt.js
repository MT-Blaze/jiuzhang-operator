/**
 * core_receipt.js —— plugin.js 的「两帧对账」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var DRAFT_RECEIPT_KEY = coreState.DRAFT_RECEIPT_KEY;
    var PLUGIN_ID = coreState.PLUGIN_ID;
    var RECEIPT_RETRY_MAX = coreState.RECEIPT_RETRY_MAX;
    var RECEIPT_RETRY_MS = coreState.RECEIPT_RETRY_MS;
    var alignRows = deps.alignRows;
    var applySwap = deps.applySwap;
    var backToList = deps.backToList;
    var dock = deps.dock;
    var hostCall = deps.hostCall;
    var nowIso = deps.nowIso;
    var panel = coreState.panel;
    var publishSelection = deps.publishSelection;
    var renderAll = deps.renderAll;
    var saveWorklist = deps.saveWorklist;
    var setFormat = deps.setFormat;
    var setFormatButtons = deps.setFormatButtons;
    var setSwapButton = deps.setSwapButton;
    var showSaved = deps.showSaved;
    var state = coreState.state;

  // ---------- 两帧对账：辅助栏设的视图参数（面板→画布）与入库回执（面板→画布） ----------
  function onUiParams(payload) {
    var values = payload && payload.values;
    if (!payload || payload.pluginId !== PLUGIN_ID || !values) return;
    if (payload.revisions && typeof payload.revisions === "object") {
      panel.uiRevisions = JSON.parse(JSON.stringify(payload.revisions));
    }
    if (state.slot === "stage.center") {
      if (values.format && values.format !== state.format) setFormat(values.format);
      if (values.swap != null) {
        var wantSwap = values.swap === true || values.swap === "true";
        if (wantSwap !== state.swap) {
          applySwap(wantSwap, true);
          alignRows();
          publishSelection();
        }
      }
      // 辅助栏那颗【返回列表】：画布收到广播才真回列表，且不再回发一遍。
      if (values.view === "list" && state.mode === "review") backToList("已回到批次列表。", true);
      return;
    }
    if (values.format) setFormatButtons(values.format);
    if (values.swap != null) setSwapButton(values.swap === true || values.swap === "true");
  }

  /**
   * 辅助栏落库后留一张回执，画布收到 system.question_updated 时按回执认领：
   * 「新建」和「派生变式」在事件里长得一模一样，只有回执能分清是哪一题变成了哪道题。
   */
  /**
   * 回执箱是两只帧共用的一只：面板投票，画布认领。
   * 认领方不许改写箱子——它一写，就会把对面刚投进来的新票抹掉，
   * 批量提交时那一票就永远等不到，题目在画布上会一直挂着「未入库」。
   * 所以只写方（pushReceipt）先读后写，认领方只读。
   */
  function pushReceipt(receipt) {
    hostCall("draft.load", { key: DRAFT_RECEIPT_KEY }).then(function (result) {
      var value = result && result.value;
      var list = value && Array.isArray(value.items) ? value.items.slice() : [];
      list.push({
        key: receipt.key, id: receipt.id, action: receipt.action,
        mode: receipt.mode, at: nowIso()
      });
      panel.receipts = list.slice(-20);
      return hostCall("draft.save", { key: DRAFT_RECEIPT_KEY, value: { items: panel.receipts } });
    }).catch(function () { /* 回执丢了，画布顶多少刷一次状态 */ });
  }

  function consumeReceipts(payload, attempt) {
    var id = payload && payload.id ? String(payload.id) : "";
    if (!id) return;
    var tries = Number(attempt) || 0;
    hostCall("draft.load", { key: DRAFT_RECEIPT_KEY }).then(function (result) {
      var value = result && result.value;
      var list = value && Array.isArray(value.items) ? value.items : [];
      var matched = null;
      list.forEach(function (item) {
        if (!matched && item && String(item.id) === id) matched = item;
      });
      if (!matched) {
        // 宿主是先广播事件、后把应答送回辅助栏，回执落草稿比事件晚一跳；读不到就重试
        if (tries < RECEIPT_RETRY_MAX) {
          setTimeout(function () { consumeReceipts(payload, tries + 1); }, RECEIPT_RETRY_MS);
        }
        return;
      }
      panel.receipts = list.slice(-20);
      var target = null;
      state.items.forEach(function (item) {
        if (item.key === matched.key) target = item;
      });
      if (!target) target = state.items[state.active];
      if (!target || matched.mode === "variant") {
        dock("派生变式已入库：" + id + "（当前题没动）");
        return;
      }
      target.savedId = id;
      target.status = "stored";
      target.dirty = false;
      if (target.question) target.question.id = id;
      renderAll();
      saveWorklist();
      publishSelection();
      // 画布与辅助栏是两个 iframe，面板那句「已入库」画布看不见；
      // 认领回执时由画布把题号回显到读屏状态位，老师不用来回翻帧。
      showSaved(id, matched.action === "update");
    }).catch(function () { /* 读不到回执就不动，等老师再点一次保存 */ });
  }

    return {
      consumeReceipts: consumeReceipts,
      onUiParams: onUiParams,
      pushReceipt: pushReceipt,
    };
  }

  global.JzoEditorReceipt = { create: create };
})(window);
