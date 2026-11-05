/**
 * core_protocol.js —— plugin.js 的「协议」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var DRAFT_LAYOUT_KEY = coreState.DRAFT_LAYOUT_KEY;
    var PLUGIN_ID = coreState.PLUGIN_ID;
    var PROTOCOL = coreState.PROTOCOL;
    var activatePanel = deps.activatePanel;
    var applyAiPatch = deps.applyAiPatch;
    var applySelection = deps.applySelection;
    var applySwap = deps.applySwap;
    var applyWidths = deps.applyWidths;
    var basketAdd = deps.basketAdd;
    var cancelSelectionPublish = deps.cancelSelectionPublish;
    var consumeReceipts = deps.consumeReceipts;
    var flushMetaDraft = deps.flushMetaDraft;
    var flushWorklist = deps.flushWorklist;
    var handleCommandExecute = deps.handleCommandExecute;
    var hostCall = deps.hostCall;
    var hostError = deps.hostError;
    var loadForEdit = deps.loadForEdit;
    var normalizeWidths = deps.normalizeWidths;
    var onCanvasState = deps.onCanvasState;
    var onPanelPendingUpdated = deps.onPanelPendingUpdated;
    var onPendingUpdated = deps.onPendingUpdated;
    var onUiParams = deps.onUiParams;
    var showDupReview = deps.showDupReview;
    var clearDupReview = deps.clearDupReview;
    var noticeDupReview = deps.noticeDupReview;
    var showCleanReview = deps.showCleanReview;
    var clearCleanReview = deps.clearCleanReview;
    var onCleanState = deps.onCleanState;
    var showPoolReview = deps.showPoolReview;
    var clearPoolReview = deps.clearPoolReview;
    var onPoolCanvasClosed = deps.onPoolCanvasClosed;
    var paintAmberBlock = deps.paintAmberBlock;
    var runApproveAll = deps.runApproveAll;
    var onCanvasApproveAll = deps.onCanvasApproveAll;
    var pending = coreState.pending;
    var publishSelection = deps.publishSelection;
    var refreshBatches = deps.refreshBatches;
    var renderAll = deps.renderAll;
    var respond = deps.respond;
    var restoreWorklist = deps.restoreWorklist;
    var saveWorklist = deps.saveWorklist;
    var seedBatch = deps.seedBatch;
    var setMode = deps.setMode;
    var startIdleWatch = deps.startIdleWatch;
    var state = coreState.state;
    var wireIntake = deps.wireIntake;
    var wireAiCopilot = deps.wireAiCopilot;
    var openAiConfig = deps.openAiConfig;
    var runAiBatch = deps.runAiBatch;
    var onAiBatchReport = deps.onAiBatchReport;
    var panelRoot = deps.dom.panelRoot;
    var root = deps.dom.root;
    var sourceHintEl = deps.dom.sourceHintEl;

  // ---------- 协议 ----------
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    if (message.kind === "response" && pending.has(message.id)) {
      var waiter = pending.get(message.id);
      pending.delete(message.id);
      if (message.ok) waiter.resolve(message.result || {});
      else waiter.reject(hostError(message.error));
      return;
    }

    if (message.kind === "notification") {
      if (message.event === "system.open_editor") {
        if (state.slot !== "stage.center") return;
        var wanted = (message.payload && message.payload.question_id) || "";
        var origin = (message.payload && message.payload.from) || "";
        if (wanted) loadForEdit(wanted, origin);
        return;
      }
      if (message.event === "editor.apply_patch") {
        // 面板自己发的回填会广播回所有帧：只有画布动手改源码，面板一律静默
        if (state.slot === "stage.center") applyAiPatch(message.payload);
        return;
      }
      if (message.event === "ui.params.changed") {
        onUiParams(message.payload);
        return;
      }
      if (message.event === "stage.selection") {
        // 宿主只把选区投给面板帧（画布自己就是来源，回灌只会形成回声）
        if (state.slot !== "stage.center") {
          applySelection((message.payload && message.payload.raw) || {});
        }
        return;
      }
      if (message.event === "editor.canvas_state") {
        // 画布的悬停与滚动：宿主只把它投给面板帧，面板据此亮边缘、收批次元数据
        if (state.slot === "stage.center") return;
        onCanvasState(message.payload || {});
        return;
      }
      if (message.event === "system.question_updated") {
        if (state.slot === "stage.center") consumeReceipts(message.payload);
        return;
      }
      if (message.event === "system.pending_updated") {
        // 中转站动了：入库与删除要把题从画布上撤下来，暂存只改内容不撤。
        if (state.slot === "stage.center") onPendingUpdated(message.payload);
        else onPanelPendingUpdated(message.payload);
        return;
      }
      if (message.event === "editor.collect_files") {
        // 宿主壳或辅助栏那边接到的文件，转进画布的收集筐：
        // 只有画布收，面板再收一遍就成了两份。
        if (state.slot !== "stage.center") return;
        var incoming = (message.payload && message.payload.files) || [];
        if (Array.isArray(incoming) && incoming.length) basketAdd(incoming);
        return;
      }
      if (message.event === "editor.dup_review") {
        // 军令 #31：查重对比浮层只在画布帧画（渲染能力只在这一帧）。
        // 辅助栏是唯一发起点：开窗给它报告，收窗只说一声——裁决动作也全在那边。
        if (state.slot !== "stage.center") return;
        // 宿主会把插件通知重包成 { text, pluginId, level, raw }：真货在 raw 里。
        var dupPayload = (message.payload && message.payload.raw) || message.payload || {};
        if (dupPayload.phase === "open" && dupPayload.report) showDupReview(dupPayload);
        else if (dupPayload.phase === "notice" && dupPayload.report) noticeDupReview(dupPayload);
        else if (dupPayload.phase === "closed") clearDupReview();
        return;
      }
      if (message.event === "editor.clean_review") {
        // 4.3：清洗预览的正文对照只画在画布帧；辅助栏只收段名/规则/字数。
        if (state.slot !== "stage.center") return;
        var cleanPayload = (message.payload && message.payload.raw) || message.payload || {};
        if (cleanPayload.open) showCleanReview(cleanPayload);
        else clearCleanReview("replaced");
        return;
      }
      if (message.event === "editor.clean_review_state") {
        // 画布回执（opened / closed / tab_not_live）只投辅助栏：它据此解降级、还焦点。
        if (state.slot === "stage.center") return;
        onCleanState((message.payload && message.payload.raw) || message.payload || {});
        return;
      }
      if (message.event === "editor.pool_review") {
        // 重题池（判据 5.1）：开窗与关窗都从辅助栏发起，画布这一屏只画渲染、一颗按钮都没有。
        // 反过来画布按 Esc 自己退了，也要喊辅助栏放开选中——两条都走同一个主题，靠 from 分头。
        var poolPayload = (message.payload && message.payload.raw) || message.payload || {};
        var poolFrom = String(poolPayload.from || "");
        if (state.slot === "stage.center") {
          if (poolFrom !== "panel") return;
          if (poolPayload.phase === "open" && poolPayload.entry) showPoolReview(poolPayload.entry);
          else if (poolPayload.phase === "closed") clearPoolReview("panel_close", false);
          return;
        }
        if (poolFrom === "canvas" && poolPayload.phase === "closed") onPoolCanvasClosed();
        return;
      }
      if (message.event === "editor.batch_review") {
        // 琥珀灯的实时描边（辅助栏算→画布那一格亮）与【全部入库】的整批扫灯，
        // 都只许画布那帧动手；画布办完把结果回投辅助栏，话在那边说。
        var reviewPayload = (message.payload && message.payload.raw) || message.payload || {};
        var reviewFrom = String(reviewPayload.from || "");
        if (state.slot === "stage.center") {
          if (reviewFrom !== "panel") return;
          if (reviewPayload.action === "amber") {
            paintAmberBlock(Number(reviewPayload.index) || 0,
              Array.isArray(reviewPayload.reasons) ? reviewPayload.reasons : []);
          } else if (reviewPayload.action === "approve_all") runApproveAll();
          else if (reviewPayload.action === "refresh_batches") refreshBatches();
          // 终极军令 任务一/三：双栏配置窗与批量识别都由辅助栏发令、画布执行。
          else if (reviewPayload.action === "ai_config") openAiConfig();
          else if (reviewPayload.action === "ai_batch") runAiBatch();
          return;
        }
        if (reviewFrom === "canvas" && reviewPayload.action === "approve_all") {
          onCanvasApproveAll(reviewPayload);
        }
        if (reviewFrom === "canvas" && reviewPayload.action === "ai_batch"
          && typeof onAiBatchReport === "function") onAiBatchReport(reviewPayload);
        return;
      }
      return;
    }

    if (message.kind !== "request") return;

    if (message.method === "plugin.activate") {
      state.slot = (message.payload && message.payload.slot) || "stage.center";
      if (state.slot !== "stage.center") {
        activatePanel();
        return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID, slot: state.slot });
      }
      root.hidden = false;
      setMode("list");
      applyWidths();
      renderAll();
      wireIntake();
      if (sourceHintEl) sourceHintEl.textContent = "源码 · 整段源码直接编辑";
      startIdleWatch();
      if (typeof wireAiCopilot === "function") wireAiCopilot();
      // 首屏就是批次列表：中转站还空着就先把这批识别结果入池，好让老师有东西可点。
      refreshBatches().then(function (cards) {
        if (cards.length) return null;
        return seedBatch().then(function () { return refreshBatches(); });
      });
      restoreWorklist().then(function () {
        renderAll();
        saveWorklist();
        publishSelection();
      });
      hostCall("draft.load", { key: DRAFT_LAYOUT_KEY }).then(function (result) {
        var value = result && result.value;
        if (value && value.widths) normalizeWidths(value.widths);
        if (value && typeof value.swap === "boolean") applySwap(value.swap, false);
        applyWidths();
        state.layoutReady = true;
      }).catch(function () { state.layoutReady = true; });
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID, slot: state.slot });
    }
    if (message.method === "plugin.deactivate") {
      if (state.slot === "stage.center") {
        root.hidden = true;
        flushWorklist();
        cancelSelectionPublish();
      } else {
        panelRoot.hidden = true;
        flushMetaDraft();
      }
      return respond(event.source, message.id, true, { ready: false });
    }
    if (message.method === "command.execute") {
      return handleCommandExecute(event.source, message);
    }
    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD",
      "未实现的方法：" + String(message.method));
  });

    return {
    };
  }

  global.JzoEditorProtocol = { create: create };
})(window);
