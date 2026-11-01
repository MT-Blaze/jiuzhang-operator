/**
 * ui_panel_boot.js —— plugin.js 的「848」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var DIFFICULTY_VALUES = coreState.DIFFICULTY_VALUES;
    var DRAFT_WORKLIST_KEY = coreState.DRAFT_WORKLIST_KEY;
    var PANEL_DRAFT_RETRY_MS = coreState.PANEL_DRAFT_RETRY_MS;
    var TYPE_LABELS = coreState.TYPE_LABELS;
    var TYPE_VALUES = coreState.TYPE_VALUES;
    var aiFoldOpen = deps.aiFoldOpen;
    var applyDraftSelection = deps.applyDraftSelection;
    var backToListFromPanel = deps.backToListFromPanel;
    var bindFormChanges = deps.bindFormChanges;
    var cancelSchoolConfirm = deps.cancelSchoolConfirm;
    var chooseFormatFromPanel = deps.chooseFormatFromPanel;
    var cleanViaHost = deps.cleanViaHost;
    var clearSchoolConflict = deps.clearSchoolConflict;
    var closeModal = deps.closeModal;
    var collapseMetaSection = deps.collapseMetaSection;
    var confirmSchoolCreate = deps.confirmSchoolCreate;
    var expandMetaSection = deps.expandMetaSection;
    var fillSelect = deps.fillSelect;
    var hideSchoolMenu = deps.hideSchoolMenu;
    var hideTagMenu = deps.hideTagMenu;
    var hostCall = deps.hostCall;
    var loadMetaDraft = deps.loadMetaDraft;
    var loadMetaHistory = deps.loadMetaHistory;
    var loadScenes = deps.loadScenes;
    var loadTags = deps.loadTags;
    var loadTopicRoots = deps.loadTopicRoots;
    var onAiApply = deps.onAiApply;
    var onAiDiscard = deps.onAiDiscard;
    var onAiSend = deps.onAiSend;
    var onApprove = deps.onApprove;
    var onDelete = deps.onDelete;
    var onDeleteConfirm = deps.onDeleteConfirm;
    var onMetaFieldChange = deps.onMetaFieldChange;
    var onSceneChange = deps.onSceneChange;
    var onSchoolEnter = deps.onSchoolEnter;
    var onStash = deps.onStash;
    var onStdInput = deps.onStdInput;
    var onTagEnter = deps.onTagEnter;
    var panel = coreState.panel;
    var renderAi = deps.renderAi;
    var renderBatchMeta = deps.renderBatchMeta;
    var renderMounted = deps.renderMounted;
    var renderTags = deps.renderTags;
    var renderTopLines = deps.renderTopLines;
    var scheduleSchoolConflict = deps.scheduleSchoolConflict;
    var searchSchools = deps.searchSchools;
    var setAiFold = deps.setAiFold;
    var setFormatButtons = deps.setFormatButtons;
    var setSchoolError = deps.setSchoolError;
    var setStdMode = deps.setStdMode;
    var setSwapButton = deps.setSwapButton;
    var toggleSwapFromPanel = deps.toggleSwapFromPanel;
    var wireGhost = deps.wireGhost;
    var wireGhostCell = deps.wireGhostCell;
    var wireIntake = deps.wireIntake;
    var delCancelEl = deps.dom.delCancelEl;
    var delModalEl = deps.dom.delModalEl;
    var delOkEl = deps.dom.delOkEl;
    var dupBackEl = deps.dom.dupBackEl;
    var dupForceEl = deps.dom.dupForceEl;
    var dupModalEl = deps.dom.dupModalEl;
    var panelAiApplyEl = deps.dom.panelAiApplyEl;
    var panelAiAskEl = deps.dom.panelAiAskEl;
    var panelAiCleanEl = deps.dom.panelAiCleanEl;
    var panelAiDiscardEl = deps.dom.panelAiDiscardEl;
    var panelAiFoldEl = deps.dom.panelAiFoldEl;
    var panelAiSendEl = deps.dom.panelAiSendEl;
    var panelApproveEl = deps.dom.panelApproveEl;
    var panelBackListEl = deps.dom.panelBackListEl;
    var panelDeleteEl = deps.dom.panelDeleteEl;
    var panelDifficultyEl = deps.dom.panelDifficultyEl;
    var panelFmtBoxedEl = deps.dom.panelFmtBoxedEl;
    var panelFmtLatexEl = deps.dom.panelFmtLatexEl;
    var panelMetaBodyEl = deps.dom.panelMetaBodyEl;
    var panelMetaExamTypeEl = deps.dom.panelMetaExamTypeEl;
    var panelMetaFoldEl = deps.dom.panelMetaFoldEl;
    var panelMetaRegionEl = deps.dom.panelMetaRegionEl;
    var panelMetaSceneEl = deps.dom.panelMetaSceneEl;
    var panelMetaSecEl = deps.dom.panelMetaSecEl;
    var panelMetaSubjectEl = deps.dom.panelMetaSubjectEl;
    var panelMetaYearEl = deps.dom.panelMetaYearEl;
    var panelRoot = deps.dom.panelRoot;
    var panelSchoolConfirmCancelEl = deps.dom.panelSchoolConfirmCancelEl;
    var panelSchoolConfirmOkEl = deps.dom.panelSchoolConfirmOkEl;
    var panelSchoolInputEl = deps.dom.panelSchoolInputEl;
    var panelScrollEl = deps.dom.panelScrollEl;
    var panelStashEl = deps.dom.panelStashEl;
    var panelStdNameEl = deps.dom.panelStdNameEl;
    var panelSwapEl = deps.dom.panelSwapEl;
    var panelTypeEl = deps.dom.panelTypeEl;

  function activatePanel() {
    if (!panelRoot) return;
    panelRoot.hidden = false;
    fillSelect(panelTypeEl, TYPE_VALUES, TYPE_LABELS);
    fillSelect(panelDifficultyEl, DIFFICULTY_VALUES, {
      L1: "L1 基础", L2: "L2 中档", L3: "L3 难", L4: "L4 压轴"
    });
    bindFormChanges();
    renderTags();
    renderMounted();
    wireGhostCell("tag");
    wireGhostCell("topic");
    // 批次公共元数据：画布一滚动就收成一行矮标题；鼠标停在标题上才展开，
    // 移开鼠标不收起——老师正在填的字段不许被自动折叠抢走。
    if (panelMetaFoldEl) {
      panelMetaFoldEl.addEventListener("mouseenter", expandMetaSection);
      panelMetaFoldEl.addEventListener("click", function () {
        var open = panelMetaSecEl && panelMetaSecEl.getAttribute("data-fold") === "open";
        if (open) collapseMetaSection();
        else expandMetaSection();
      });
    }
    [panelFmtLatexEl, panelFmtBoxedEl].forEach(function (node) {
      if (!node) return;
      node.addEventListener("click", function () {
        chooseFormatFromPanel(node.getAttribute("data-format"));
      });
    });
    if (panelSwapEl) panelSwapEl.addEventListener("click", toggleSwapFromPanel);
    if (panelBackListEl) panelBackListEl.addEventListener("click", backToListFromPanel);
    if (panelApproveEl) panelApproveEl.addEventListener("click", function () { onApprove(false); });
    if (panelStashEl) panelStashEl.addEventListener("click", onStash);
    if (panelDeleteEl) panelDeleteEl.addEventListener("click", onDelete);
    if (dupBackEl) dupBackEl.addEventListener("click", function () { closeModal(dupModalEl); });
    if (dupForceEl) dupForceEl.addEventListener("click", function () {
      closeModal(dupModalEl);
      onApprove(true);
    });
    if (delCancelEl) delCancelEl.addEventListener("click", function () { closeModal(delModalEl); });
    if (delOkEl) delOkEl.addEventListener("click", onDeleteConfirm);
    if (panelAiAskEl) panelAiAskEl.addEventListener("input", renderAi);
    if (panelAiSendEl) panelAiSendEl.addEventListener("click", onAiSend);
    if (panelAiCleanEl) panelAiCleanEl.addEventListener("click", cleanViaHost);
    if (panelAiApplyEl) panelAiApplyEl.addEventListener("click", onAiApply);
    if (panelAiDiscardEl) panelAiDiscardEl.addEventListener("click", onAiDiscard);
    if (panelAiFoldEl) {
      panelAiFoldEl.addEventListener("click", function () { setAiFold(!aiFoldOpen()); });
    }
    // 批次公共元数据：改一次，这一批所有题立刻跟着改
    [panelMetaYearEl, panelMetaRegionEl, panelMetaBodyEl, panelMetaSubjectEl].forEach(function (node) {
      if (!node) return;
      node.addEventListener("input", onMetaFieldChange);
      node.addEventListener("change", onMetaFieldChange);
    });
    if (panelMetaSceneEl) panelMetaSceneEl.addEventListener("change", onSceneChange);
    // 学校输入框：搜字典 → 选中即加；查不到就走 AI 补全 → 老师确认 → 建档。
    if (panelSchoolInputEl) {
      panelSchoolInputEl.addEventListener("input", function () {
        var query = String(panelSchoolInputEl.value || "").trim();
        clearSchoolConflict();
        setSchoolError("");
        if (!query) { hideSchoolMenu(); return; }
        searchSchools(query);
        scheduleSchoolConflict(query);
      });
      panelSchoolInputEl.addEventListener("focus", function () {
        var query = String(panelSchoolInputEl.value || "").trim();
        if (query) searchSchools(query);
      });
      panelSchoolInputEl.addEventListener("keydown", function (event) {
        if (String(event.key || "") !== "Enter") return;
        event.preventDefault();
        onSchoolEnter();
      });
      panelSchoolInputEl.addEventListener("blur", function () {
        window.setTimeout(hideSchoolMenu, 120);
      });
    }
    if (panelSchoolConfirmOkEl) panelSchoolConfirmOkEl.addEventListener("click", confirmSchoolCreate);
    if (panelSchoolConfirmCancelEl) {
      panelSchoolConfirmCancelEl.addEventListener("click", cancelSchoolConfirm);
    }
    // 交叉标签：场景决定候选排序；打一个字就模糊查；回车把新标签记进本地库。
    if (panelMetaExamTypeEl) {
      panelMetaExamTypeEl.addEventListener("input", function () {
        loadTags(String(panelMetaExamTypeEl.value || "").trim());
        if (panel.stdManual) setStdMode(false);
        renderTopLines({ flash: true });
      });
      panelMetaExamTypeEl.addEventListener("focus", function () {
        loadTags(String(panelMetaExamTypeEl.value || "").trim());
      });
      panelMetaExamTypeEl.addEventListener("keydown", function (event) {
        if (String(event.key || "") !== "Enter") return;
        event.preventDefault();
        onTagEnter();
      });
      panelMetaExamTypeEl.addEventListener("change", onMetaFieldChange);
      panelMetaExamTypeEl.addEventListener("blur", function () {
        window.setTimeout(hideTagMenu, 120);
      });
    }
    if (panelStdNameEl) {
      panelStdNameEl.addEventListener("input", onStdInput);
      panelStdNameEl.addEventListener("change", onStdInput);
    }
    wireIntake();
    loadScenes();
    loadMetaHistory();
    renderBatchMeta();
    renderAi();
    setFormatButtons("latex");
    setSwapButton(false);
    wireGhost(panelScrollEl || panelRoot);
    wireGhost(document.getElementById("epTree"));
    loadMetaDraft().then(function () {
      return hostCall("draft.load", { key: DRAFT_WORKLIST_KEY });
    }).then(function (result) {
      applyDraftSelection(result && result.value);
      loadTopicRoots();
      if (!panel.selection) {
        // 画布可能比面板慢一步才把草稿写回来：补读一次，别让右栏晾成空壳
        window.setTimeout(function () {
          if (panel.selection) return;
          hostCall("draft.load", { key: DRAFT_WORKLIST_KEY }).then(function (retry) {
            applyDraftSelection(retry && retry.value);
          }, function () { /* 还是读不到就等画布下一次发布 */ });
        }, PANEL_DRAFT_RETRY_MS);
      }
    }).catch(function () { loadTopicRoots(); });
    panel.ready = true;
  }

    return {
      activatePanel: activatePanel,
    };
  }

  global.JzoEditorPanelBoot = { create: create };
})(window);
