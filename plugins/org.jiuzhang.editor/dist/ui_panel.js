/**
 * ui_panel.js —— plugin.js 的「辅助栏实例」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var TYPE_LABELS = coreState.TYPE_LABELS;
    var aiClear = deps.aiClear;
    var clearAnswerEditor = deps.clearAnswerEditor || function () {};
    var collapseMetaSection = deps.collapseMetaSection || function () {};
    var renderAnswerEditor = deps.renderAnswerEditor || function () {};
    var panel = coreState.panel;
    // 录题偏好里的「预设难度」：识别没给难度时兜底；没接偏好模块就回落 L1。
    var presetDifficulty = deps.presetDifficulty || function () { return ""; };
    var panelSay = deps.panelSay;
    var queueMetaSave = deps.queueMetaSave;
    var renderAi = deps.renderAi;
    var renderBatchMeta = deps.renderBatchMeta;
    var renderMounted = deps.renderMounted;
    var renderPool = deps.renderPool;
    var renderTags = deps.renderTags;
    // 琥珀灯：换题＝换一道未清项清单，边缘这一圈必须跟着重算（判定在 ui_amber 那一份里）。
    var repaintPanel = deps.repaintPanel;
    // 渲染栏题卡顶部的只读元数据条（缺这个依赖时只是不刷新，不影响表单）。
    var paintMetaStrip = deps.paintMetaStrip;
    var setFormatButtons = deps.setFormatButtons;
    var setSwapButton = deps.setSwapButton;
    var splitTags = deps.splitTags;
    var syncBatchContext = deps.syncBatchContext;
    var panelApproveAllEl = deps.dom.panelApproveAllEl;
    var panelApproveEl = deps.dom.panelApproveEl;
    var panelConfidenceEl = deps.dom.panelConfidenceEl;
    var panelDeleteEl = deps.dom.panelDeleteEl;
    var panelDifficultyEl = deps.dom.panelDifficultyEl;
    var panelHeadNoEl = deps.dom.panelHeadNoEl;
    var panelStashEl = deps.dom.panelStashEl;
    var panelMetricsEl = deps.dom.panelMetricsEl;
    var panelProgressEl = deps.dom.panelProgressEl;
    var panelQuestionNoEl = deps.dom.panelQuestionNoEl;
    var panelScoreEl = deps.dom.panelScoreEl;
    var panelStatusEl = deps.dom.panelStatusEl;
    var panelTagsEl = deps.dom.panelTagsEl;
    var panelTypeEl = deps.dom.panelTypeEl;
    var panelTypeNoteEl = deps.dom.panelTypeNoteEl;

  // ---------- 辅助栏实例（sidebar.right）：元数据 + 审核动作 + 格式切换 ----------
  function fillSelect(node, values, labels) {
    if (!node) return;
    node.textContent = "";
    values.forEach(function (value) {
      var option = document.createElement("option");
      option.value = value;
      option.textContent = labels[value] || value;
      node.appendChild(option);
    });
  }

  function panelItem() {
    var sel = panel.selection;
    if (!sel) return null;
    return {
      key: String(sel.key || "idx:" + Number(sel.index || 0)),
      savedId: sel.saved_id || "",
      pendingId: sel.pending_id || "",
      batchId: sel.batch_id || "",
      status: sel.status === "stored" ? "stored" : "pending",
      source: String(sel.source || panel.source || ""),
      question: {
        id: sel.question_id || "",
        images: Array.isArray(sel.images) ? sel.images : [],
        extensions: sel.extensions && typeof sel.extensions === "object" ? sel.extensions : {},
        source: sel.origin && typeof sel.origin === "object" ? sel.origin : null
      }
    };
  }

  function defaultEntry(sel) {
    var d = (sel && sel.defaults) || {};
    return {
      type: d.type || "",
      difficulty: d.difficulty || presetDifficulty() || "L1",
      grade: d.grade || "",
      textbook: d.textbook || "",
      chapter: d.chapter || "",
      section: d.section || "",
      paper_title: d.paper_title || "",
      question_no: d.question_no || "",
      exam_type: d.exam_type || "",
      year: d.year || "",
      tags: d.tags || "",
      score: d.score || "",
      topic_ids: [],
      topic_names: {},
      knowledge_point_ids: [],
      knowledge_names: {}
    };
  }

  function entryFor(sel) {
    var key = String(sel.key || "idx:" + Number(sel.index || 0));
    if (!panel.meta[key]) panel.meta[key] = defaultEntry(sel);
    return panel.meta[key];
  }

  function readForm() {
    var entry = {};
    Object.keys(panel.currentEntry || {}).forEach(function (key) { entry[key] = panel.currentEntry[key]; });
    if (panelTypeEl) entry.type = panelTypeEl.value;
    if (panelDifficultyEl) entry.difficulty = panelDifficultyEl.value;
    if (panelQuestionNoEl) entry.question_no = panelQuestionNoEl.value;
    if (panelTagsEl) entry.tags = panelTagsEl.value;
    if (panelScoreEl) entry.score = panelScoreEl.value;
    return entry;
  }

  function bindFormChanges() {
    [panelTypeEl, panelDifficultyEl, panelQuestionNoEl, panelScoreEl].forEach(function (node) {
      if (!node) return;
      node.addEventListener("input", onFormChange);
      node.addEventListener("change", onFormChange);
    });
  }

  /** 表单是元数据的编辑面：每次改动都立刻并回草稿，别让保存读到半旧的版本。 */
  function onFormChange() {
    if (!panel.selection) return;
    panel.currentEntry = readForm();
    panel.meta[panel.selection.key] = panel.currentEntry;
    panel.selection.dirty = true;
    queueMetaSave();
    renderTypeNote();
    renderPanelMetrics();
    if (paintMetaStrip) paintMetaStrip(Number(panel.selection.index) || 0);
  }

  function renderTypeNote() {
    if (!panelTypeNoteEl || !panel.selection) return;
    var aiType = panel.selection.ai_type;
    var chosen = panelTypeEl ? panelTypeEl.value : "";
    if (!aiType) {
      panelTypeNoteEl.textContent = "源码还没认全，题型先按人工选择。";
      panelTypeNoteEl.setAttribute("data-from", "manual");
      return;
    }
    if (chosen && chosen !== aiType) {
      panelTypeNoteEl.textContent = "源码判为「" + (TYPE_LABELS[aiType] || aiType) + "」，你改成了「"
        + (TYPE_LABELS[chosen] || chosen) + "」——保存以你的选择为准。";
      panelTypeNoteEl.setAttribute("data-from", "manual");
      return;
    }
    panelTypeNoteEl.textContent = "题型由源码自动判断（" + (TYPE_LABELS[aiType] || aiType) + "），可人工改。";
    panelTypeNoteEl.setAttribute("data-from", "ai");
  }

  /** 审核动作四颗钮只在有当前题时可用；回到批次列表就整排锁上。 */
  function setActionsEnabled(enabled) {
    [panelApproveEl, panelApproveAllEl, panelStashEl, panelDeleteEl].forEach(function (node) {
      if (!node) return;
      node.disabled = !enabled;
      node.setAttribute("aria-disabled", enabled ? "false" : "true");
    });
  }

  /**
   * 回到批次列表：把上一题留在表单里的私有数据全部撤下。
   * 只把 panel.selection 置空还不够——输入框、胶囊、置信度与动作钮都是上一次
   * applySelection 写进去的，不清就会挂着「第 1 题」的编辑面，老师以为还在审题。
   */
  function clearQuestionState() {
    panel.source = "";
    if (panelHeadNoEl) panelHeadNoEl.textContent = "批次概览";
    if (panelTypeEl) panelTypeEl.selectedIndex = -1;
    if (panelDifficultyEl) panelDifficultyEl.selectedIndex = -1;
    if (panelQuestionNoEl) panelQuestionNoEl.value = "";
    if (panelScoreEl) panelScoreEl.value = "";
    if (panelTagsEl) panelTagsEl.value = "";
    if (panelConfidenceEl) {
      panelConfidenceEl.textContent = "置信度 —";
      panelConfidenceEl.setAttribute("data-confidence", "");
    }
    if (panelTypeNoteEl) {
      panelTypeNoteEl.textContent = "进入批次后才会载入当前题。";
      panelTypeNoteEl.setAttribute("data-from", "manual");
    }
    if (panelMetricsEl) {
      ["data-question-id", "data-saved-id", "data-type", "data-difficulty",
       "data-dirty", "data-topics"].forEach(function (name) {
        panelMetricsEl.setAttribute(name, "");
      });
      panelMetricsEl.textContent = "尚未载入当前题。";
    }
    setActionsEnabled(false);
    renderTags();
    renderMounted();
    if (deps.aiClear) deps.aiClear("回到批次列表，等下一题。");
    if (deps.clearDup) deps.clearDup();
  }

  /** 首屏是批次列表：切换批次语境，并把上一题的单题编辑面清干净。 */
  function applyListSelection(sel) {
    panel.view = "list";
    panel.selection = null;
    panel.currentEntry = null;
    clearQuestionState();
    clearAnswerEditor();
    if (panel.metaConfirmed) collapseMetaSection();
    var cards = Array.isArray(sel.batches) ? sel.batches : [];
    var wanted = String(sel.batch_id || "");
    var current = null;
    for (var index = 0; index < cards.length; index += 1) {
      if (String(cards[index].batch_id || "") === wanted) { current = cards[index]; break; }
    }
    if (!current && cards.length) current = cards[0];
    panel.batchCard = current;
    panel.batchMeta = current && current.meta && typeof current.meta === "object"
      ? current.meta
      : {};
    panel.batchId = current ? String(current.batch_id || "") : "";
    renderBatchMeta();
    if (panelProgressEl) {
      // 首屏右上角不写「批次列表」四个字：列表就在画布上，标题是废话。
      // 节点留着给读屏与探针数批次（data-total），只是视觉上彻底退场。
      panelProgressEl.textContent = "";
      panelProgressEl.hidden = true;
      panelProgressEl.setAttribute("data-active", "0");
      panelProgressEl.setAttribute("data-total", String(cards.length));
    }
    if (panelStatusEl) {
      panelStatusEl.textContent = "● 批次列表";
      panelStatusEl.setAttribute("data-status", "list");
      panelStatusEl.setAttribute("data-dirty", "false");
    }
    renderPool();
    if (!panel.metaSyncing) {
      panelSay(cards.length
        ? "在左边点任意一行进入审核。"
        : "中转站里还没有批次：把卷子拖进来，或 Ctrl+V 粘贴截图。",
        "info", "idle");
    }
  }

  function applySelection(sel) {
    if (!sel || typeof sel !== "object") return;
    // 首屏是批次列表：这里只认批次，不动那道题还没填的表单。
    if (sel.mode === "list") {
      applyListSelection(sel);
      return;
    }
    panel.view = "review";
    var previous = panel.selection;
    var switched = !previous || previous.key !== sel.key || previous.batch_id !== sel.batch_id;
    if (previous && previous.key && previous.key !== sel.key) {
      // 换题前把老师正在填的这一半按旧题的键存回草稿，别让表单跟着题号一起漂
      panel.meta[previous.key] = Object.assign(panel.meta[previous.key] || defaultEntry(previous), readForm());
      queueMetaSave();
      // 预览中的改写属于上一道题：换题即失效，不许糊到新题上
      if (panel.ai.key && panel.ai.key !== sel.key && panel.ai.state !== "sending" && panel.ai.state !== "cleaning") {
        aiClear("换题了：上一题的改写已作废。");
      }
    }
    panel.selection = sel;
    // 公共层点过【确定】后，切题/切批次一律保持折叠；同一题内的回显不抢老师刚展开的面板。
    if (panel.metaConfirmed && switched) collapseMetaSection();
    setActionsEnabled(true);
    // 学校简称冲突会把单题入库重新锁死：回到审核面时必须按当前冲突再说一遍。
    if (deps.syncSchoolLock) deps.syncSchoolLock();
    // 军令 #31：换题就是换一条待审记录，上一题的红字不许留在这一题头上；
    // 换完顺手做一次后台查重，命中就把红字与【查看主库原题】亮起来。
    if (deps.clearDup) deps.clearDup();
    if (deps.precheckDup && sel.pending_id) deps.precheckDup({ pendingId: sel.pending_id });
    panel.source = String(sel.source || "");
    var entry = entryFor(sel);
    if (panel.currentEntry !== entry) {
      panel.currentEntry = entry;
    }
    var merged = entry;
    if (panelProgressEl) {
      panelProgressEl.hidden = false;
      panelProgressEl.textContent = "第 " + (Number(sel.index || 0) + 1) + " / " + (sel.total || 1) + " 题";
      panelProgressEl.setAttribute("data-active", String(Number(sel.index || 0) + 1));
      panelProgressEl.setAttribute("data-total", String(sel.total || 1));
    }
    if (panelStatusEl) {
      var stored = sel.status === "stored";
      panelStatusEl.textContent = stored ? "● 已入库" : "● 待审核";
      panelStatusEl.setAttribute("data-status", stored ? "stored" : "pending");
      panelStatusEl.setAttribute("data-dirty", sel.dirty ? "true" : "false");
    }
    if (panelConfidenceEl) {
      var confidence = typeof sel.confidence === "number" ? Math.round(sel.confidence * 100) : null;
      panelConfidenceEl.textContent = confidence == null ? "置信度 —（假数据占位）" : "置信度 " + confidence + "%（假数据占位）";
      panelConfidenceEl.setAttribute("data-confidence", confidence == null ? "" : String(confidence));
    }
    if (panelTypeEl) panelTypeEl.value = merged.type || sel.ai_type || "single_choice";
    if (panelDifficultyEl) panelDifficultyEl.value = merged.difficulty || presetDifficulty() || "L1";
    if (panelQuestionNoEl) panelQuestionNoEl.value = merged.question_no || "";
    if (panelTagsEl) panelTagsEl.value = merged.tags || "";
    if (panelScoreEl) panelScoreEl.value = merged.score || "";
    if (panelHeadNoEl) panelHeadNoEl.textContent = "第 " + (Number(sel.index || 0) + 1) + " 题";
    // 换批次要把公共元数据面板切过去；题级的原卷名/年份/类型跟着批次走，不再单列字段。
    syncBatchContext(sel.batch_id);
    renderTags();
    setFormatButtons(sel.format || panel.format);
    setSwapButton(Boolean(sel.swap));
    renderTypeNote();
    renderMounted();
    renderPanelMetrics();
    renderAi();
    renderAnswerEditor();
    renderPool();
    if (panelSelectionError()) {
      panelSay(panelSelectionError(), "error", "invalid");
    } else if (panel.ai.state === "ready" && panel.ai.key === sel.key) {
      // 刚把改写发给画布，那句「保存才入库」不能被选区回显盖掉——否则老师会以为已经入库了
    } else if (!panel.saving) {
      panelSay("当前第 " + (Number(sel.index || 0) + 1) + " 题" + (sel.dirty ? "有未保存改动" : "未改动") + "。",
        "info", sel.dirty ? "dirty" : "idle");
    }
    // 元数据草稿可能比画布首渲晚一步到位：选区回显时按最终表单再刷一次只读条。
    if (paintMetaStrip) paintMetaStrip(Number(sel.index) || 0, merged);
    // 换完题再算一次灯：这一圈的结论必须是**新**这道题的，不许留着上一题的未清项。
    if (repaintPanel) repaintPanel();
  }

  function panelSelectionError() {
    var sel = panel.selection;
    if (!sel || !sel.errors || !sel.errors.length) return "";
    return "源码还没认全：" + sel.errors.slice(0, 4).join("；");
  }

  function renderPanelMetrics() {
    if (!panelMetricsEl || !panel.selection) return;
    var sel = panel.selection;
    panelMetricsEl.setAttribute("data-question-id", sel.question_id || "");
    panelMetricsEl.setAttribute("data-saved-id", sel.saved_id || "");
    panelMetricsEl.setAttribute("data-type", panelTypeEl ? panelTypeEl.value : "");
    panelMetricsEl.setAttribute("data-difficulty", panelDifficultyEl ? panelDifficultyEl.value : "");
    panelMetricsEl.setAttribute("data-format", panel.format);
    panelMetricsEl.setAttribute("data-dirty", sel.dirty ? "true" : "false");
    var entry = panel.currentEntry || {};
    panelMetricsEl.setAttribute("data-topics", String((entry.topic_ids || []).length));
    panelMetricsEl.textContent = "键 " + (sel.key || "") + " · 已挂考向 " + (entry.topic_ids || []).length
      + " · 标签 " + splitTags(entry.tags).length;
  }

  function explainHostError(error) {
    var code = String((error && error.code) || "");
    var text = (error && error.message) || "未知失败";
    if (code === "FORBIDDEN") return "清单没申请这道权限（FORBIDDEN），本次未写入题库";
    if (code === "PERMISSION_DENIED") return "宿主不认这份清单的权限（PERMISSION_DENIED）：" + text;
    if (code === "RATE_LIMITED") return "请求太密（每 10 秒有上限），稍等再点一次";
    if (code === "NOT_READY") return "宿主还没就绪（NOT_READY）：" + text;
    if (code === "HOST_409") return "题库里已经有同一道题（409 撞号）：请改点【另存为新题】，或先处理旧题";
    if (code === "HOST_422") return "题目不符合题库 Schema（422）：" + text;
    if (code === "HOST_404") return "要改的那道题在题库里找不到了（404）";
    if (code.indexOf("HOST_") === 0) return "底座写库失败（" + code + "）：" + text;
    if (code === "LOCAL_INVALID") return text;
    return text;
  }

    return {
      applyListSelection: applyListSelection,
      applySelection: applySelection,
      bindFormChanges: bindFormChanges,
      defaultEntry: defaultEntry,
      entryFor: entryFor,
      explainHostError: explainHostError,
      fillSelect: fillSelect,
      onFormChange: onFormChange,
      panelItem: panelItem,
      panelSelectionError: panelSelectionError,
      readForm: readForm,
      renderPanelMetrics: renderPanelMetrics,
      renderTypeNote: renderTypeNote,
    };
  }

  global.JzoEditorPanel = { create: create };
})(window);
