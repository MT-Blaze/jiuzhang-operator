/**
 * ui_panel_glue.js —— plugin.js 的「幽灵胶囊」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var GHOST_DELAY_MS = coreState.GHOST_DELAY_MS;
    var LAMP_DELAY_MS = coreState.LAMP_DELAY_MS;
    var TAG_LIMIT = coreState.TAG_LIMIT;
    var applySelection = deps.applySelection;
    var applyMetaSync = deps.applyMetaSync;
    var el = deps.el;
    var hostCall = deps.hostCall;
    var loadBatchMeta = deps.loadBatchMeta;
    var loadMetaHistory = deps.loadMetaHistory;
    var onFormChange = deps.onFormChange;
    var panel = coreState.panel;
    var panelSay = deps.panelSay;
    var parseExamSource = deps.parseExamSource;
    var publish = deps.publish;
    var splitTags = deps.splitTags;
    var toggleTopic = deps.toggleTopic;
    var toggleKnowledge = deps.toggleKnowledge;
    var imageBodyEl = deps.dom.imageBodyEl;
    var panelMetaBodyEl = deps.dom.panelMetaBodyEl;
    var panelMetaConfirmNoteEl = deps.dom.panelMetaConfirmNoteEl;
    var panelMetaExamTypeEl = deps.dom.panelMetaExamTypeEl;
    var panelMetaGradeEl = deps.dom.panelMetaGradeEl;
    var panelMetaMockRoundEl = deps.dom.panelMetaMockRoundEl;
    var panelMetaMonthEl = deps.dom.panelMetaMonthEl;
    var panelMetaRegionEl = deps.dom.panelMetaRegionEl;
    var panelMetaSemesterEl = deps.dom.panelMetaSemesterEl;
    var panelMetaSubjectEl = deps.dom.panelMetaSubjectEl;
    var panelMetaYearEl = deps.dom.panelMetaYearEl;
    var panelSrcNameEl = deps.dom.panelSrcNameEl;
    var panelStdNameEl = deps.dom.panelStdNameEl;
    var panelGhostTagMenuEl = deps.dom.panelGhostTagMenuEl;
    var panelGhostTopicMenuEl = deps.dom.panelGhostTopicMenuEl;
    var panelGhostKnowledgeMenuEl = deps.dom.panelGhostKnowledgeMenuEl;
    var panelKnowledgeListEl = deps.dom.panelKnowledgeListEl;
    var panelMetaFoldEl = deps.dom.panelMetaFoldEl;
    var panelMetaSceneEl = deps.dom.panelMetaSceneEl;
    var panelMetaSecEl = deps.dom.panelMetaSecEl;
    var panelMetaSummaryEl = deps.dom.panelMetaSummaryEl;
    var panelMountedEl = deps.dom.panelMountedEl;
    var panelRoot = deps.dom.panelRoot;
    var panelTagListEl = deps.dom.panelTagListEl;
    var panelTagsEl = deps.dom.panelTagsEl;
    var patchIdFor = deps.patchIdFor;
    var renderBodyEl = deps.dom.renderBodyEl;
    var sourceBodyEl = deps.dom.sourceBodyEl;

  // 第三层：答案与解析两只可编辑框（独立模块：删此块+脚本行+#epAnswerSec 即可整块下架）。
  var answerEditor = window.JzoEditorAnswerEditor.create({
    coreState: coreState, dom: deps.dom, hostCall: hostCall,
    parseExamSource: parseExamSource, patchIdFor: patchIdFor,
  });

  // ---------- 幽灵胶囊（军令 #29 / #30）：标签与考向共用一套 ----------
  // 空壳、候选、高亮与已经挂上的胶囊都在 dist/ui_capsule.js 里；
  // 这里只把元素、宿主通道与要回写的地方交进去。
  var capsule = window.JzoEditorCapsule.create({
    el: el,
    hostCall: hostCall,
    tagList: panelTagListEl,
    mountedList: panelMountedEl,
    knowledgeList: panelKnowledgeListEl,
    tagMenu: panelGhostTagMenuEl,
    topicMenu: panelGhostTopicMenuEl,
    knowledgeMenu: panelGhostKnowledgeMenuEl,
    tagsValue: function () { return panelTagsEl ? panelTagsEl.value : ""; },
    entry: function () { return panel.currentEntry || {}; },
    topicStore: panel,
    scene: function () { return panelMetaSceneEl ? String(panelMetaSceneEl.value || "") : ""; },
    commitTags: function (tags) { commitTags(tags); },
    toggleTopic: function (topic) { toggleTopic(topic); },
    toggleKnowledge: function (point) { toggleKnowledge(point); },
    splitTags: splitTags,
    delay: GHOST_DELAY_MS
  });

  function renderTags() { capsule.renderTags(); }

  /** 挂载区一处重画：考向串与知识点串同属「已挂载」，分开画只会漂移。 */
  function renderMounted() { capsule.renderMounted(); capsule.renderKnowledge(); }

  function wireGhostCell(kind) { capsule.wireCell(kind); }

  function commitTags(tags) {
    if (!panelTagsEl) return;
    var list = [];
    (tags || []).forEach(function (tag) {
      var one = String(tag == null ? "" : tag).trim().slice(0, 32);
      if (one && list.indexOf(one) < 0) list.push(one);
    });
    panelTagsEl.value = list.slice(0, TAG_LIMIT).join(",");
    renderTags();
    onFormChange();
  }

  /** 从宿主代持的工作清单草稿里重建辅助栏选区——两个帧同时挂载，通知不一定赶得上。 */
  function applyDraftSelection(value) {
    // 已明确回到批次列表时，迟到的草稿不许再把上一题回灌到右栏。
    if (panel.selection || panel.view === "list") return;
    var items = value && Array.isArray(value.items) ? value.items : [];
    var active = value ? Number(value.active) || 0 : 0;
    var saved = items[active] || items[0] || null;
    if (!saved) return;
    var source = String(saved.source || "");
    var pool = { fresh: 0, stored: 0, dirty: 0, errored: 0 };
    items.forEach(function (each) {
      if (each.status === "stored") pool.stored += 1;
      else pool.fresh += 1;
      if (each.dirty) pool.dirty += 1;
      if (each.errors && each.errors.length) pool.errored += 1;
    });
    panel.source = source;
    applySelection({
      index: active, total: items.length, key: saved.key,
      question_id: saved.id || saved.saved_id || "", saved_id: saved.saved_id || "",
      pending_id: saved.pending_id || "", batch_id: saved.batch_id || "",
      mode: "review",
      status: saved.status, dirty: Boolean(saved.dirty), format: panel.format,
      swap: panel.swap, source: source, errors: saved.errors || [],
      ai_type: parseExamSource(source).type,
      confidence: typeof saved.confidence === "number" ? saved.confidence : null,
      defaults: saved.defaults || {}, pool: pool,
      images: Array.isArray(saved.images) ? saved.images : [],
      extensions: saved.extensions && typeof saved.extensions === "object" ? saved.extensions : {},
      origin: saved.origin && typeof saved.origin === "object" ? saved.origin : null
    });
  }

  /** 中转站动了：辅助栏要知道——批次卡片与公共元数据都可能变了。 */
  function onPanelPendingUpdated(payload) {
    var action = String((payload && payload.action) || "");
    if (action === "ingest") {
      loadMetaHistory();
      panelSay("新批次已建，去批次列表里审。", "info", "idle");
      return;
    }
    if (action === "meta") {
      // 底座刚把公共元数据同步过，重新读一遍这一批的账
      loadBatchMeta(panel.batchId);
      return;
    }
    if (action === "approve" || action === "delete" || action === "save_draft") {
      loadBatchMeta(panel.batchId);
    }
  }

  // ---------- 双侧呼吸灯与批次折叠（军令 #29 / #30） ----------
  // 两个 iframe 之间不直连（AGENTS §2）：画布把「鼠标停在哪一题」「画布在滚动」
  // 经宿主总线报给辅助栏，辅助栏据此亮边缘、收批次公共元数据。
  // 灯与折叠的状态和渲染都在 dist/ui_breath.js，这里只把元素、总线与延时交进去。
  var breath = window.JzoBreath.create({
    rows: [imageBodyEl, sourceBodyEl, renderBodyEl],
    panelRoot: panelRoot,
    panelMetaSecEl: panelMetaSecEl,
    panelMetaFoldEl: panelMetaFoldEl,
    panelMetaSummaryEl: panelMetaSummaryEl,
    publish: publish,
    delay: LAMP_DELAY_MS
  });

  function wireLamp() { breath.wireLamp(); }

  function onCanvasState(payload) { breath.onCanvasState(payload); }

  function signalCanvasScroll() { breath.signalCanvasScroll(); }

  function collapseMetaSection() { breath.collapseMetaSection(); }

  function expandMetaSection() { breath.expandMetaSection(); }

  /** 右下角【确定】：把当前公共字段整批存到后台，并立刻收起公共层。 */
  function confirmMetaSection() {
    var value = function (node) { return node ? String(node.value || "") : ""; };
    panel.metaConfirmed = true;
    panel.confirmedMeta = {
      source_name: value(panelSrcNameEl),
      std_name: panelStdNameEl ? String(panelStdNameEl.textContent || "").trim() : "",
      year: value(panelMetaYearEl),
      region: value(panelMetaRegionEl),
      grade: value(panelMetaGradeEl),
      body: value(panelMetaBodyEl),
      exam_type: value(panelMetaExamTypeEl),
      subject: value(panelMetaSubjectEl),
      month: value(panelMetaMonthEl),
      mock_round: value(panelMetaMockRoundEl),
      semester: value(panelMetaSemesterEl)
    };
    if (typeof applyMetaSync === "function") applyMetaSync();
    if (panelMetaConfirmNoteEl) {
      panelMetaConfirmNoteEl.textContent = "已封存并同步到后台；切题保持折叠";
    }
    collapseMetaSection();
    panelSay("批次公共元数据已确认并同步。", "ok", "idle");
  }

  /** 收起来时那一行矮标题要报点什么：标准名最有用，没有就报场景。 */
  function renderFoldSummary() {
    if (!panelMetaSummaryEl) return;
    var std = panelStdNameEl ? String(panelStdNameEl.textContent || "").trim() : "";
    var scene = panelMetaSceneEl ? String(panelMetaSceneEl.value || "").trim() : "";
    breath.renderFoldSummary(std || scene || "—");
  }

    return {
      answerEditor: answerEditor,
      applyDraftSelection: applyDraftSelection,
      breath: breath,
      capsule: capsule,
      collapseMetaSection: collapseMetaSection,
      commitTags: commitTags,
      confirmMetaSection: confirmMetaSection,
      expandMetaSection: expandMetaSection,
      onCanvasState: onCanvasState,
      onPanelPendingUpdated: onPanelPendingUpdated,
      renderFoldSummary: renderFoldSummary,
      renderMounted: renderMounted,
      renderTags: renderTags,
      signalCanvasScroll: signalCanvasScroll,
      wireGhostCell: wireGhostCell,
      wireLamp: wireLamp,
    };
  }

  global.JzoEditorPanelGlue = { create: create };
})(window);
