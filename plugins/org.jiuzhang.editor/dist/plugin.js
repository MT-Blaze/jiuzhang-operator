/**
 * 录题工作台 v3（军令 #24：批次系统与待审核池）。
 *
 * 画布实例（stage.center）有两屏：
 *   首屏是批次列表——一行一个批次，点任意一行进入审核；
 *   二屏是三栏审核界面——左原图 | 中全量 exam-zh 源码 | 右渲染，抬头写着当前批次号。
 * 辅助栏实例（sidebar.right）是审核台：元数据表单 + AI 帮改 + 审核动作。
 *
 * 题目先落在中转站（待审核池），老师审完才由【存入主库】落进主库。
 * 中转站与主库物理隔离，插件不碰数据库、不碰令牌，写库一律经宿主。
 *
 * 同一个插件的两个沙箱帧拿不到彼此的 DOM，只走底座开好的合法通道：
 *   画布 → 辅助栏：发布 stage.selection（当前题的源码、进度与元数据默认值）；
 *   辅助栏 → 画布：ui.params.set（format / swap / view），由宿主广播 ui.params.changed；
 *   两帧共享：draft.save / draft.load 交宿主代持的工作清单与元数据草稿；
 *   中转站：pending.batch_list / list / save_draft / approve / delete 五条 Host API；
 *   写库：辅助栏经宿主 bank.create / bank.update 落库，成功回音 system.question_updated。
 *
 * 插件住在不透明源沙箱里：不联网、不碰浏览器本地存储、不碰宿主 DOM，令牌永远在宿主手里。
 */
(function () {
  "use strict";


  // ---------- 取节点（dist/ui_dom.js）----------
  var dom = window.JzoEditorDom.create();

  // ---------- 拆出去的模块（PLUGIN_SPEC §2.8.1：单文件不超 800 行） ----------
  var coreState = window.JzoEditorCoreState.create({});
  var devFixtures = window.JzoEditorFixtures.create({});
  var coreHost = window.JzoEditorHost.create({
    dom: dom,
    coreState: coreState,
  });
  var dock = coreHost.dock, dockWarn = coreHost.dockWarn, errorDetail = coreHost.errorDetail;
  var hostCall = coreHost.hostCall, hostError = coreHost.hostError, nowIso = coreHost.nowIso;
  var panelSay = coreHost.panelSay, publish = coreHost.publish, respond = coreHost.respond;
  var toast = coreHost.toast, trunc = coreHost.trunc;

  var DEV_FIXTURES = devFixtures.DEV_FIXTURES;

  var coreRich = window.JzoEditorRich.create({});
  var appendBody = coreRich.appendBody, appendRich = coreRich.appendRich;
  var clampValue = coreRich.clampValue, el = coreRich.el, safeAssetUri = coreRich.safeAssetUri;

  var coreExamSource = window.JzoEditorExamSource.create({});
  var buildExamSource = coreExamSource.buildExamSource, parseExamSource = coreExamSource.parseExamSource;

  var coreAiFields = window.JzoEditorAiFields.create({
    coreState: coreState,
  });
  var fieldAtOffset = coreAiFields.fieldAtOffset, fieldLabel = coreAiFields.fieldLabel;
  var fieldRanges = coreAiFields.fieldRanges, keyFromPatchId = coreAiFields.keyFromPatchId;
  var makeItem = coreAiFields.makeItem, patchIdFor = coreAiFields.patchIdFor, replaceField = coreAiFields.replaceField;
  var uiModal = window.JzoEditorModal.create({
    dom: dom,
    coreState: coreState,
  });
  var closeModal = uiModal.closeModal, openModal = uiModal.openModal;
  var uiModel = window.JzoEditorModel.create({ dom: dom, dock: dock, dockWarn: dockWarn, hostCall: hostCall, openModal: openModal, closeModal: closeModal });

  // 查重拦截的画布侧对比浮层（军令 #31）：只画两侧渲染，裁决动作全在辅助栏。
  var uiDup = window.JzoEditorDup.create({
    dom: dom,
    appendBody: appendBody,
    appendRich: appendRich,
    el: el,
    publish: publish,
    coreState: coreState,
  });

  // 琥珀灯（军令 #32 · 判据 5.2/43）：两帧共用的「还有未清项」判定与整批扫灯，只这一份。
  // 它排在最前，是因为画布（uiColumns 的题卡描边）与辅助栏（边缘那一圈）都要用它；
  // 反过来 readForm / parsedOf / metaFor 都还在更下面的块里，只能等就位后再取。
  var uiAmber = window.JzoEditorAmber.create({
    dom: dom,
    hostCall: hostCall,
    loadMetaDraft: function () { return coreSave.loadMetaDraft.apply(coreSave, arguments); },
    jumpTo: function () { return uiColumns.jumpTo.apply(uiColumns, arguments); },
    metaFor: function () { return coreSave.metaFor.apply(coreSave, arguments); },
    panelPoolRefresh: function () { return uiPoolPanel.refresh.apply(uiPoolPanel, arguments); },
    panelSay: panelSay,
    parseExamSource: parseExamSource,
    parsedOf: function () { return uiColumns.parsedOf.apply(uiColumns, arguments); },
    publish: publish,
    readForm: function () { return uiPanel.readForm.apply(uiPanel, arguments); },
    refreshBatches: function () { return uiBatches.refreshBatches.apply(uiBatches, arguments); },
    stashBeforeLeave: function () { return uiBatches.stashBeforeLeave.apply(uiBatches, arguments); },
    coreState: coreState,
  });

  // 重题池画布那一屏（判据 5.1）：左主库原题、右池内这条，两边都只画渲染，一颗按钮都不放。
  var uiPool = window.JzoEditorPool.create({
    dom: dom,
    publish: publish,
    renderDoc: uiDup.renderDoc,
    setMode: function () { return uiBatches.setMode.apply(uiBatches, arguments); },
    coreState: coreState,
  });

  // 重题池辅助栏那一半（判据 5.3/5.4）：档位、条目、四个动作与删除二次确认。
  var uiPoolPanel = window.JzoEditorPoolPanel.create({
    closeModal: closeModal,
    dock: dock,
    dockWarn: dockWarn,
    dom: dom,
    el: el,
    errorDetail: errorDetail,
    hostCall: hostCall,
    openModal: openModal,
    panelSay: panelSay,
    publish: publish,
    coreState: coreState,
  });

  // 查重三栏（军令·查重三栏）：画布与裁判台的装配都在 ui_dup_wiring.js。
  var uiDupBits = window.JzoEditorDupWiring.create({
    dom: dom, coreState: coreState, el: el, renderDoc: uiDup.renderDoc, buildExamSource: buildExamSource,
    uiBatches: function () { return uiBatches; }, uiColumns: function () { return uiColumns; },
    publish: publish, hostCall: hostCall, panelSay: panelSay, dock: dock, dockWarn: dockWarn,
    errorDetail: errorDetail, openModal: openModal, closeModal: closeModal,
    poolPanel: function () { return uiPoolPanel; },
  });
  var uiDupCompare = uiDupBits.compare;
  var uiDupJudge = uiDupBits.judge;

  var uiApprove = window.JzoEditorApprove.create({
    dom: dom,
    closeModal: closeModal,
    dock: dock,
    dockWarn: dockWarn,
    errorDetail: errorDetail,
    // 循环引用：explainHostError 归更下面的 uiPanel，本块排得靠前，只能等它就位后再取。
    explainHostError: function () { return uiPanel.explainHostError.apply(uiPanel, arguments); },
    hostCall: hostCall,
    openModal: openModal,
    publish: publish,
    // 循环引用：panelItem 归更下面的 uiPanel，本块排得靠前，只能等它就位后再取。
    panelItem: function () { return uiPanel.panelItem.apply(uiPanel, arguments); },
    panelSay: panelSay,
    parseExamSource: parseExamSource,
    // 循环引用：questionFromParsed 归更下面的 coreSave，本块排得靠前，只能等它就位后再取。
    questionFromParsed: function () { return coreSave.questionFromParsed.apply(coreSave, arguments); },
    // 循环引用：readForm 归更下面的 uiPanel，本块排得靠前，只能等它就位后再取。
    readForm: function () { return uiPanel.readForm.apply(uiPanel, arguments); },
    // 循环引用：saveItem 归更下面的 coreSave，本块排得靠前，只能等它就位后再取。
    saveItem: function () { return coreSave.saveItem.apply(coreSave, arguments); },
    // 循环引用：syncSchoolLock 归更下面的 uiSchoolDict，本块排得靠前，只能等它就位后再取。
    syncSchoolLock: function () { return uiSchoolDict.syncSchoolLock.apply(uiSchoolDict, arguments); },
    // 循环引用：validateForSave 归更下面的 coreSave，本块排得靠前，只能等它就位后再取。
    validateForSave: function () { return coreSave.validateForSave.apply(coreSave, arguments); },
    coreState: coreState,
  });
  var onApprove = uiApprove.onApprove;
  var onDelete = uiApprove.onDelete;
  var onDeleteConfirm = uiApprove.onDeleteConfirm;
  var onStash = uiApprove.onStash;
  var poolCounts = uiApprove.poolCounts;
  var precheckDup = uiApprove.precheck;
  var renderPool = uiApprove.renderPool;

  var coreSelection = window.JzoEditorSelection.create({
    fieldAtOffset: fieldAtOffset,
    hostCall: hostCall,
    // 循环引用：parsedOf 归更下面的 uiColumns，本块排得靠前，只能等它就位后再取。
    parsedOf: function () { return uiColumns.parsedOf.apply(uiColumns, arguments); },
    poolCounts: poolCounts,
    publish: publish,
    // 循环引用：scheduleRender 归更下面的 uiColumns，本块排得靠前，只能等它就位后再取。
    scheduleRender: function () { return uiColumns.scheduleRender.apply(uiColumns, arguments); },
    trunc: trunc,
    coreState: coreState,
  });
  var cancelSelectionPublish = coreSelection.cancelSelectionPublish;
  var defaultsOf = coreSelection.defaultsOf;
  var flushWorklist = coreSelection.flushWorklist;
  var keepExtensions = coreSelection.keepExtensions;
  var publishSelection = coreSelection.publishSelection;
  var publishSelectionSoon = coreSelection.publishSelectionSoon;
  var queueWorklistSave = coreSelection.queueWorklistSave;
  var restoreWorklist = coreSelection.restoreWorklist;
  var saveWorklist = coreSelection.saveWorklist;
  var coreReceipt = window.JzoEditorReceipt.create({
    // 循环引用：alignRows 归更下面的 uiColumns，本块排得靠前，只能等它就位后再取。
    alignRows: function () { return uiColumns.alignRows.apply(uiColumns, arguments); },
    // 循环引用：applySwap 归更下面的 uiFormat，本块排得靠前，只能等它就位后再取。
    applySwap: function () { return uiFormat.applySwap.apply(uiFormat, arguments); },
    // 循环引用：backToList 归更下面的 uiBatches，本块排得靠前，只能等它就位后再取。
    backToList: function () { return uiBatches.backToList.apply(uiBatches, arguments); },
    dock: dock,
    hostCall: hostCall,
    nowIso: nowIso,
    publishSelection: publishSelection,
    // 循环引用：renderAll 归更下面的 uiColumns，本块排得靠前，只能等它就位后再取。
    renderAll: function () { return uiColumns.renderAll.apply(uiColumns, arguments); },
    saveWorklist: saveWorklist,
    // 循环引用：setFormat 归更下面的 uiFormat，本块排得靠前，只能等它就位后再取。
    setFormat: function () { return uiFormat.setFormat.apply(uiFormat, arguments); },
    // 循环引用：setFormatButtons 归更下面的 uiFormat，本块排得靠前，只能等它就位后再取。
    setFormatButtons: function () { return uiFormat.setFormatButtons.apply(uiFormat, arguments); },
    // 循环引用：setSwapButton 归更下面的 uiFormat，本块排得靠前，只能等它就位后再取。
    setSwapButton: function () { return uiFormat.setSwapButton.apply(uiFormat, arguments); },
    // 循环引用：showSaved 归更下面的 coreSave，本块排得靠前，只能等它就位后再取。
    showSaved: function () { return coreSave.showSaved.apply(coreSave, arguments); },
    coreState: coreState,
  });
  var consumeReceipts = coreReceipt.consumeReceipts;
  var onUiParams = coreReceipt.onUiParams;
  var pushReceipt = coreReceipt.pushReceipt;

  var coreSave = window.JzoEditorSave.create({
    dom: dom,
    // 循环引用：defaultEntry 归更下面的 uiPanel，本块排得靠前，只能等它就位后再取。
    defaultEntry: function () { return uiPanel.defaultEntry.apply(uiPanel, arguments); },
    defaultsOf: defaultsOf,
    dock: dock,
    hostCall: hostCall,
    keepExtensions: keepExtensions,
    // 循环引用：markDirty 归更下面的 uiColumns，本块排得靠前，只能等它就位后再取。
    markDirty: function () { return uiColumns.markDirty.apply(uiColumns, arguments); },
    panelSay: panelSay,
    parseExamSource: parseExamSource,
    pushReceipt: pushReceipt,
    queueWorklistSave: queueWorklistSave,
    // 元数据一落草稿就重算琥珀灯（考向是「还没挂考向」这条的唯一来源）。
    repaintPanel: uiAmber.repaintPanel,
    coreState: coreState,
  });
  var flushMetaDraft = coreSave.flushMetaDraft;
  var loadMetaDraft = coreSave.loadMetaDraft;
  var metaFor = coreSave.metaFor;
  var questionFromParsed = coreSave.questionFromParsed;
  var queueMetaSave = coreSave.queueMetaSave;
  var saveViaCommand = coreSave.saveViaCommand;
  var splitTags = coreSave.splitTags;
  var validateForSave = coreSave.validateForSave;

  // 批次卡片的【删除批次】独立成一块：要下架这颗按钮，删 index.html 里那一行
  // 脚本、或给 .btn-delete-batch 加 display:none 即可，核心渲染一处不用改。
  var uiBatchDelete = window.JzoEditorBatchDelete.create({
    coreState: coreState,
    dock: dock,
    dockWarn: dockWarn,
    el: el,
    errorDetail: errorDetail,
    hostCall: hostCall,
    publishSelection: publishSelection,
    // 循环引用：publishView / refreshBatches / setMode 归更下面的 uiBatches。
    publishView: function () { return uiBatches.publishView.apply(uiBatches, arguments); },
    refreshBatches: function () { return uiBatches.refreshBatches.apply(uiBatches, arguments); },
    setMode: function () { return uiBatches.setMode.apply(uiBatches, arguments); },
  });

  var uiBatches = window.JzoEditorBatches.create({
    dom: dom,
    DEV_FIXTURES: DEV_FIXTURES,
    buildExamSource: buildExamSource,
    closeModal: closeModal,
    dock: dock,
    dockWarn: dockWarn,
    el: el,
    errorDetail: errorDetail,
    hostCall: hostCall,
    loadMetaDraft: loadMetaDraft,
    makeItem: makeItem,
    metaFor: metaFor,
    openModal: openModal,
    panelSay: panelSay,
    parseExamSource: parseExamSource,
    // 循环引用：parsedOf 归更下面的 uiColumns，本块排得靠前，只能等它就位后再取。
    parsedOf: function () { return uiColumns.parsedOf.apply(uiColumns, arguments); },
    publishSelection: publishSelection,
    publishSelectionSoon: publishSelectionSoon,
    questionFromParsed: questionFromParsed,
    // 循环引用：renderAll 归更下面的 uiColumns，本块排得靠前，只能等它就位后再取。
    renderAll: function () { return uiColumns.renderAll.apply(uiColumns, arguments); },
    // 独立的整批删除按钮模块（可整块下架）。
    renderDeleteBatchButton: uiBatchDelete.renderDeleteBatchButton,
    toast: toast,
    validateForSave: validateForSave,
    coreState: coreState,
  });
  var loadForEdit = uiBatches.loadForEdit;
  var refreshBatches = uiBatches.refreshBatches;
  var seedBatch = uiBatches.seedBatch;
  var setMode = uiBatches.setMode;
  var stashOne = uiBatches.stashOne;
  var noteActivity = uiBatches.noteActivity;
  var onPendingUpdated = uiBatches.onPendingUpdated;
  var startIdleWatch = uiBatches.startIdleWatch;
  var stashOnUnload = uiBatches.stashOnUnload;
  var uiFormat = window.JzoEditorFormat.create({
    dom: dom,
    // 循环引用：alignRows 归更下面的 uiColumns，本块排得靠前，只能等它就位后再取。
    alignRows: function () { return uiColumns.alignRows.apply(uiColumns, arguments); },
    hostCall: hostCall,
    publishSelection: publishSelection,
    // 循环引用：queueLayoutSave 归更下面的 uiLayout，本块排得靠前，只能等它就位后再取。
    queueLayoutSave: function () { return uiLayout.queueLayoutSave.apply(uiLayout, arguments); },
    // 循环引用：renderAll 归更下面的 uiColumns，本块排得靠前，只能等它就位后再取。
    renderAll: function () { return uiColumns.renderAll.apply(uiColumns, arguments); },
    coreState: coreState,
  });
  var applySwap = uiFormat.applySwap;
  var backToListFromPanel = uiFormat.backToListFromPanel;
  var chooseFormatFromPanel = uiFormat.chooseFormatFromPanel;
  var noteFieldNode = uiFormat.noteFieldNode;
  var setFormatButtons = uiFormat.setFormatButtons;
  var setSwapButton = uiFormat.setSwapButton;
  var toggleSwapFromPanel = uiFormat.toggleSwapFromPanel;

  // 渲染栏顶部只读元数据条：独立一小块，整块删掉不影响渲染正文。
  var uiMetaStrip = window.JzoEditorMetaStrip.create({
    el: el,
    typeLabels: coreState.TYPE_LABELS,
    difficultyLabels: coreState.DIFFICULTY_LABELS,
    // 循环引用：识别动作归更下面的 uiAiCopilot，本块排得靠前，只能等它就位后再取。
    onAiIdentify: function () { return uiAiCopilot.runSingle.apply(uiAiCopilot, arguments); },
  });

  var uiColumns = window.JzoEditorColumns.create({
    dom: dom,
    // 循环引用：切图台归更下面的 uiCrop，本块排得靠前，只能等它就位后再取。
    // session 不外借，只让 uiCrop 自己把画布搬回当前格子。
    reanchorCrop: function () { return uiCrop.reanchor.apply(uiCrop, arguments); },
    appendBody: appendBody,
    appendRich: appendRich,
    buildExamSource: buildExamSource,
    clampValue: clampValue,
    coreRich: coreRich,
    el: el,
    fieldLabel: fieldLabel,
    fieldRanges: fieldRanges,
    keyFromPatchId: keyFromPatchId,
    // 循环引用：openCrop 归更下面的 uiCrop，本块排得靠前，只能等它就位后再取。
    openCrop: function () { return uiCrop.openCrop.apply(uiCrop, arguments); },
    parseExamSource: parseExamSource,
    publishSelectionSoon: publishSelectionSoon,
    queueWorklistSave: queueWorklistSave,
    renderPool: renderPool,
    replaceField: replaceField,
    safeAssetUri: safeAssetUri,
    setFormatButtons: setFormatButtons,
    // 琥珀灯：题卡上的 data-amber 由这一处画，判定口径全在 uiAmber。
    amberReasons: uiAmber.amberReasons,
    metaFor: metaFor,
    metaStrip: uiMetaStrip,
    toast: toast,
    coreState: coreState,
  });
  var applyAiPatch = uiColumns.applyAiPatch;
  var itemImage = uiColumns.itemImage;
  var renderAll = uiColumns.renderAll;
  var scheduleRender = uiColumns.scheduleRender;
  var syncScroll = uiColumns.syncScroll;

  // 终极军令 任务一/三：API 配置中心 + 单题/批量识别。独立一整块，可整块下架。
  var uiAiCopilot = window.JzoEditorAiCopilot.create({
    bindSwitcher: uiModal.bindSwitcher,
    closeModal: closeModal,
    coreState: coreState,
    dock: dock,
    dockWarn: dockWarn,
    documentFor: uiApprove.documentFor,
    dom: dom,
    el: el,
    errorDetail: errorDetail,
    hostCall: hostCall,
    itemImage: itemImage,
    markDirty: uiColumns.markDirty,
    metaFor: metaFor,
    openModal: openModal,
    parsedOf: uiColumns.parsedOf,
    publish: publish,
    refreshRow: uiColumns.refreshRow,
    setSwitcher: uiModal.setSwitcher,
    toast: toast,
    writeBackSourceText: uiColumns.writeBackSourceText,
  });

  var uiIntake = window.JzoEditorIntake.create({
    dom: dom,
    dock: dock,
    dockWarn: dockWarn,
    el: el,
    errorDetail: errorDetail,
    hostCall: hostCall,
    modelGate: uiModel.ensureLayoutModel,
    panelSay: panelSay,
    publish: publish,
    refreshBatches: refreshBatches,
    // 循环引用：切图台排在更下面的 uiCrop 块，本块只能等它就位后再问它开没开。
    cropOpen: function () { return uiCrop.isOpen(); },
    coreState: coreState,
  });
  var basketAdd = uiIntake.basketAdd;
  var wireIntake = uiIntake.wireIntake;

  var uiMetaHist = window.JzoEditorMetaHist.create({
    dom: dom,
    dockWarn: dockWarn,
    errorDetail: errorDetail,
    hostCall: hostCall,
    coreState: coreState,
  });
  var loadMetaHistory = uiMetaHist.loadMetaHistory;
  var loadScenes = uiMetaHist.loadScenes;
  var renderSceneOptions = uiMetaHist.renderSceneOptions;
  var standardNameOf = uiMetaHist.standardNameOf;

  var uiSchoolDict = window.JzoEditorSchoolDict.create({
    dom: dom,
    dock: dock,
    dockWarn: dockWarn,
    el: el,
    errorDetail: errorDetail,
    hostCall: hostCall,
    panelSay: panelSay,
    // 循环引用：queueMetaSync 归更下面的 uiStdName，本块排得靠前，只能等它就位后再取。
    queueMetaSync: function () { return uiStdName.queueMetaSync.apply(uiStdName, arguments); },
    coreState: coreState,
  });
  var addSchoolRecord = uiSchoolDict.addSchoolRecord;
  var cancelSchoolConfirm = uiSchoolDict.cancelSchoolConfirm;
  var clearSchoolConflict = uiSchoolDict.clearSchoolConflict;
  var confirmSchoolCreate = uiSchoolDict.confirmSchoolCreate;
  var hideSchoolMenu = uiSchoolDict.hideSchoolMenu;
  var hideTagMenu = uiSchoolDict.hideTagMenu;
  var loadTags = uiSchoolDict.loadTags;
  var onSchoolEnter = uiSchoolDict.onSchoolEnter;
  var onTagEnter = uiSchoolDict.onTagEnter;
  var renderSchools = uiSchoolDict.renderSchools;
  var scheduleSchoolConflict = uiSchoolDict.scheduleSchoolConflict;
  var searchSchools = uiSchoolDict.searchSchools;
  var setSchoolError = uiSchoolDict.setSchoolError;
  var uiAi = window.JzoEditorAi.create({
    dom: dom,
    // 循环引用：explainHostError 归更下面的 uiPanel，本块排得靠前，只能等它就位后再取。
    explainHostError: function () { return uiPanel.explainHostError.apply(uiPanel, arguments); },
    fieldLabel: fieldLabel,
    fieldRanges: fieldRanges,
    hostCall: hostCall,
    // 循环引用：panelItem 归更下面的 uiPanel，本块排得靠前，只能等它就位后再取。
    panelItem: function () { return uiPanel.panelItem.apply(uiPanel, arguments); },
    panelSay: panelSay,
    parseExamSource: parseExamSource,
    patchIdFor: patchIdFor,
    publish: publish,
    trunc: trunc,
    coreState: coreState,
  });
  var aiClear = uiAi.aiClear;
  var aiFoldOpen = uiAi.aiFoldOpen;
  var cleanViaHost = uiAi.cleanViaHost;
  var onAiApply = uiAi.onAiApply;
  var onAiDiscard = uiAi.onAiDiscard;
  var onAiSend = uiAi.onAiSend;
  var onCleanApply = uiAi.onCleanApply;
  var onCleanDrop = uiAi.onCleanDrop;
  var onCleanState = uiAi.onCleanState;
  var renderAi = uiAi.renderAi;
  var setAiFold = uiAi.setAiFold;
  var uiPanelGlue = window.JzoEditorPanelGlue.create({
    dom: dom,
    // 循环引用：applySelection 归更下面的 uiPanel，本块排得靠前，只能等它就位后再取。
    applySelection: function () { return uiPanel.applySelection.apply(uiPanel, arguments); },
    el: el,
    hostCall: hostCall,
    // 循环引用：loadBatchMeta 归更下面的 uiStdName，本块排得靠前，只能等它就位后再取。
    loadBatchMeta: function () { return uiStdName.loadBatchMeta.apply(uiStdName, arguments); },
    loadMetaHistory: loadMetaHistory,
    // 循环引用：onFormChange 归更下面的 uiPanel，本块排得靠前，只能等它就位后再取。
    onFormChange: function () { return uiPanel.onFormChange.apply(uiPanel, arguments); },
    panelSay: panelSay,
    parseExamSource: parseExamSource,
    publish: publish,
    splitTags: splitTags,
    // 循环引用：toggleTopic 归更下面的 uiTopics，本块排得靠前，只能等它就位后再取。
    toggleTopic: function () { return uiTopics.toggleTopic.apply(uiTopics, arguments); },
    coreState: coreState,
  });
  var applyDraftSelection = uiPanelGlue.applyDraftSelection;
  var collapseMetaSection = uiPanelGlue.collapseMetaSection;
  var expandMetaSection = uiPanelGlue.expandMetaSection;
  var onCanvasState = uiPanelGlue.onCanvasState;
  var onPanelPendingUpdated = uiPanelGlue.onPanelPendingUpdated;
  var renderFoldSummary = uiPanelGlue.renderFoldSummary;
  var renderMounted = uiPanelGlue.renderMounted;
  var renderTags = uiPanelGlue.renderTags;
  var signalCanvasScroll = uiPanelGlue.signalCanvasScroll;
  var wireGhostCell = uiPanelGlue.wireGhostCell;
  var wireLamp = uiPanelGlue.wireLamp;

  var uiPanel = window.JzoEditorPanel.create({
    dom: dom,
    aiClear: aiClear,
    clearDup: uiApprove.clearDupWarning,
    panelSay: panelSay,
    precheckDup: precheckDup,
    queueMetaSave: queueMetaSave,
    // 表单一有动静就重算辅助栏那圈琥珀灯（判据 5.2：左侧题卡与右侧辅助栏边缘同时亮）。
    repaintPanel: uiAmber.repaintPanel,
    // 分值/难度一改，渲染栏题卡顶部的只读条同步换字（不重排整行、不抢输入焦点）。
    paintMetaStrip: uiColumns.refreshMetaStrip,
    renderAi: renderAi,
    // 循环引用：renderBatchMeta 归更下面的 uiStdName，本块排得靠前，只能等它就位后再取。
    renderBatchMeta: function () { return uiStdName.renderBatchMeta.apply(uiStdName, arguments); },
    renderMounted: renderMounted,
    renderPool: renderPool,
    renderTags: renderTags,
    setFormatButtons: setFormatButtons,
    setSwapButton: setSwapButton,
    splitTags: splitTags,
    standardNameOf: standardNameOf,
    // 循环引用：syncBatchContext 归更下面的 uiStdName，本块排得靠前，只能等它就位后再取。
    syncBatchContext: function () { return uiStdName.syncBatchContext.apply(uiStdName, arguments); },
    // 循环引用：syncSchoolLock 归更下面的 uiSchoolDict，本块排得靠前，只能等它就位后再取。
    syncSchoolLock: function () { return uiSchoolDict.syncSchoolLock.apply(uiSchoolDict, arguments); },
    coreState: coreState,
  });
  var applySelection = uiPanel.applySelection;
  var bindFormChanges = uiPanel.bindFormChanges;
  var explainHostError = uiPanel.explainHostError;
  var fillSelect = uiPanel.fillSelect;
  var renderPanelMetrics = uiPanel.renderPanelMetrics;

  var uiStdName = window.JzoEditorStdName.create({
    dom: dom,
    addSchoolRecord: addSchoolRecord,
    cancelSchoolConfirm: cancelSchoolConfirm,
    dockWarn: dockWarn,
    errorDetail: errorDetail,
    hostCall: hostCall,
    loadTags: loadTags,
    panelSay: panelSay,
    renderFoldSummary: renderFoldSummary,
    renderSceneOptions: renderSceneOptions,
    renderSchools: renderSchools,
    standardNameOf: standardNameOf,
    uiSchoolDict: uiSchoolDict,
    coreState: coreState,
  });
  var onMetaFieldChange = uiStdName.onMetaFieldChange;
  var onSceneChange = uiStdName.onSceneChange;
  var onStdInput = uiStdName.onStdInput;
  var queueMetaSync = uiStdName.queueMetaSync;
  var renderBatchMeta = uiStdName.renderBatchMeta;
  var renderTopLines = uiStdName.renderTopLines;
  var setStdMode = uiStdName.setStdMode;

  // 扫描卷手动切题：框选一块 → 新待审题。排在切图台之前，供它的「切分新题」动作调用。
  var uiSplit = window.JzoEditorSplit.create({
    buildExamSource: buildExamSource,
    dock: dock,
    dockWarn: dockWarn,
    errorDetail: errorDetail,
    hostCall: hostCall,
    jumpTo: uiColumns.jumpTo,
    makeItem: makeItem,
    refreshBatches: refreshBatches,
    renderAll: renderAll,
    coreState: coreState,
  });

  var uiCrop = window.JzoEditorCrop.create({
    clampValue: clampValue,
    dock: dock,
    dockWarn: dockWarn,
    el: el,
    errorDetail: errorDetail,
    hostCall: hostCall,
    itemImage: itemImage,
    metaFor: metaFor,
    renderAll: renderAll,
    scheduleRender: scheduleRender,
    splitFromCrop: uiSplit.splitFromCrop,
    stashOne: stashOne,
  });
  // 悬浮切题画板：整页原卷上增删框，Enter 一次提交；独立一整块，可整块下架。
  // 裁图/存题通道归更上面的 uiCrop 与 uiSplit，这里等它们就位后再取。
  var uiSplitBoard = window.JzoEditorSplitBoard.create({
    dom: dom, el: el, coreState: coreState, dock: dock, dockWarn: dockWarn,
    errorDetail: errorDetail, hostCall: hostCall, renderAll: renderAll,
    refreshBatches: refreshBatches, toast: toast,
    closeCrop: function () { return uiCrop.closeCrop.apply(uiCrop, arguments); },
    splitPageRegion: function () { return uiCrop.splitPageRegion.apply(uiCrop, arguments); },
    splitSpanRegion: function () { return uiCrop.splitSpanRegion.apply(uiCrop, arguments); },
    updatePageRegion: function () { return uiCrop.updatePageRegion.apply(uiCrop, arguments); },
    updateSpanRegion: function () { return uiCrop.updateSpanRegion.apply(uiCrop, arguments); },
  });
  // 终极军令 任务四：源码栏【添加配图】。独立一整块，可整块下架。
  var uiIllustration = window.JzoEditorIllustration.create({
    clampValue: clampValue, coreState: coreState, cropApi: uiCrop, dock: dock,
    dockWarn: dockWarn, dom: dom, el: el, errorDetail: errorDetail,
    fieldRanges: fieldRanges, growTextarea: uiColumns.growTextarea, hostCall: hostCall,
    itemImage: itemImage, onBoxInput: uiColumns.onBoxInput,
    onSourceInput: uiColumns.onSourceInput,
  });
  var uiLayout = window.JzoEditorLayout.create({
    dom: dom,
    hostCall: hostCall,
    scheduleRender: scheduleRender,
    coreState: coreState,
  });
  var applyWidths = uiLayout.applyWidths;
  var bindSplit = uiLayout.bindSplit;
  var flushLayout = uiLayout.flushLayout;
  var normalizeWidths = uiLayout.normalizeWidths;
  var coreCommands = window.JzoEditorCommands.create({
    hostCall: hostCall,
    loadForEdit: loadForEdit,
    respond: respond,
    saveViaCommand: saveViaCommand,
    scheduleRender: scheduleRender,
    coreState: coreState,
  });
  var handleCommandExecute = coreCommands.handleCommandExecute;
  var uiTopics = window.JzoEditorTopics.create({
    dom: dom,
    el: el,
    explainHostError: explainHostError,
    hostCall: hostCall,
    panelSay: panelSay,
    queueMetaSave: queueMetaSave,
    renderMounted: renderMounted,
    renderPanelMetrics: renderPanelMetrics,
    coreState: coreState,
  });
  var uiBoot = window.JzoEditorBoot.create({
    dom: dom,
    applySwap: applySwap,
    applyWidths: applyWidths,
    bindSplit: bindSplit,
    flushLayout: flushLayout,
    flushMetaDraft: flushMetaDraft,
    flushWorklist: flushWorklist,
    noteActivity: noteActivity,
    noteFieldNode: noteFieldNode,
    scheduleRender: scheduleRender,
    setFormatButtons: setFormatButtons,
    signalCanvasScroll: signalCanvasScroll,
    stashOnUnload: stashOnUnload,
    syncScroll: syncScroll,
    wireLamp: wireLamp,
    coreState: coreState,
  });
  var bind = uiBoot.bind;
  var wireGhost = uiBoot.wireGhost;

  var uiPanelBoot = window.JzoEditorPanelBoot.create({
    dom: dom,
    aiFoldOpen: aiFoldOpen,
    applyDraftSelection: applyDraftSelection,
    backToListFromPanel: backToListFromPanel,
    bindFormChanges: bindFormChanges,
    cancelSchoolConfirm: cancelSchoolConfirm,
    chooseFormatFromPanel: chooseFormatFromPanel,
    cleanViaHost: cleanViaHost,
    clearSchoolConflict: clearSchoolConflict,
    closeModal: closeModal,
    collapseMetaSection: collapseMetaSection,
    confirmSchoolCreate: confirmSchoolCreate,
    expandMetaSection: expandMetaSection,
    fillSelect: fillSelect,
    hideSchoolMenu: hideSchoolMenu,
    hideTagMenu: hideTagMenu,
    hostCall: hostCall,
    doDupAction: uiApprove.doDupAction,
    inspectDup: uiApprove.inspectDup,
    loadMetaDraft: loadMetaDraft,
    loadMetaHistory: loadMetaHistory,
    loadScenes: loadScenes,
    loadTags: loadTags,
    onAiApply: onAiApply,
    onAiDiscard: onAiDiscard,
    onAiSend: onAiSend,
    onCleanApply: onCleanApply,
    onCleanDrop: onCleanDrop,
    // AI 配置入口（终极军令 任务一/三）只在辅助栏这帧接活；回执走协议层。
    wireAiCopilot: uiAiCopilot.wirePanel,
    onApprove: onApprove,
    onDelete: onDelete,
    onDeleteConfirm: onDeleteConfirm,
    onMetaFieldChange: onMetaFieldChange,
    onSceneChange: onSceneChange,
    onSchoolEnter: onSchoolEnter,
    onStash: onStash,
    onStdInput: onStdInput,
    onTagEnter: onTagEnter,
    renderAi: renderAi,
    renderBatchMeta: renderBatchMeta,
    renderMounted: renderMounted,
    renderTags: renderTags,
    renderTopLines: renderTopLines,
    scheduleSchoolConflict: scheduleSchoolConflict,
    searchSchools: searchSchools,
    setAiFold: setAiFold,
    setFormatButtons: setFormatButtons,
    setSchoolError: setSchoolError,
    setStdMode: setStdMode,
    setSwapButton: setSwapButton,
    toggleSwapFromPanel: toggleSwapFromPanel,
    wireGhost: wireGhost,
    wireGhostCell: wireGhostCell,
    wireIntake: wireIntake,
    wirePoolPanel: uiPoolPanel.wire,
    wireDupJudge: uiDupJudge.wire,
    wireAmber: uiAmber.wireApproveAll,
    coreState: coreState,
  });
  var activatePanel = uiPanelBoot.activatePanel;
  var coreProtocol = window.JzoEditorProtocol.create({
    dom: dom,
    activatePanel: activatePanel,
    applyAiPatch: applyAiPatch,
    applySelection: applySelection,
    applySwap: applySwap,
    applyWidths: applyWidths,
    basketAdd: basketAdd,
    cancelSelectionPublish: cancelSelectionPublish,
    consumeReceipts: consumeReceipts,
    flushMetaDraft: flushMetaDraft,
    flushWorklist: flushWorklist,
    handleCommandExecute: handleCommandExecute,
    hostCall: hostCall,
    hostError: hostError,
    loadForEdit: loadForEdit,
    normalizeWidths: normalizeWidths,
    onCanvasState: onCanvasState,
    onPanelPendingUpdated: onPanelPendingUpdated,
    onPendingUpdated: onPendingUpdated,
    onUiParams: onUiParams,
    showDupReview: uiDup.show,
    noticeDupReview: uiDup.notice,
    clearDupReview: uiDup.clear,
    showCleanReview: uiDup.showClean,
    clearCleanReview: uiDup.clearClean,
    onCleanState: onCleanState,
    // 重题池画布与琥珀灯（判据 5.1/5.2/5.4/43）：两帧都收到 editor.pool_review / editor.batch_review，
    // 各自只认自己那一半——画布负责渲染与执行，辅助栏负责发令与说话。
    showPoolReview: uiPool.show,
    clearPoolReview: uiPool.clear,
    onPoolCanvasClosed: uiPoolPanel.onCanvasClosed,
    openDupCompare: uiDupCompare.open,
    updateDupCompare: uiDupCompare.update,
    closeDupCompare: uiDupCompare.close,
    onDupCompareClosed: uiDupJudge.onCanvasClosed,
    paintAmberBlock: uiAmber.paintBlock,
    runApproveAll: uiAmber.runApproveAll,
    onCanvasApproveAll: uiAmber.onCanvasApproveAll,
    // 批量识别回执由画布回投辅助栏：协议层两帧共用，回执只在这边说话。
    onAiBatchReport: uiAiCopilot.onBatchReport,
    publishSelection: publishSelection,
    refreshBatches: refreshBatches,
    renderAll: renderAll,
    respond: respond,
    restoreWorklist: restoreWorklist,
    saveWorklist: saveWorklist,
    seedBatch: seedBatch,
    setMode: setMode,
    startIdleWatch: startIdleWatch,
    wireIntake: wireIntake,
    // 配置弹窗与批量识别的画布半边（终极军令 任务一/三）：只在这一帧动手。
    wireAiCopilot: uiAiCopilot.wireCanvas,
    openAiConfig: uiAiCopilot.openConfig,
    runAiBatch: uiAiCopilot.runBatch,
    runAiBatchSolve: uiAiCopilot.runBatchSolve,
    coreState: coreState,
  });

  // ---------- 拆出去的模块：以上每块都只经 deps 拿依赖 ----------

  // ---------- 启动 ----------

  bind();

  // 真机探针用的调试面：只把解析/重组结果交给 Playwright 复核，不参与业务分支。
  window.__jzoEditorV2 = window.JzoEditorProbeApi.create({
    coreExamSource: coreExamSource,
    coreSave: coreSave,
    coreSelection: coreSelection,
    devFixtures: devFixtures,
    uiAmber: uiAmber,
    uiApprove: uiApprove,
    uiBatches: uiBatches,
    uiDupCompare: uiDupCompare,
    uiDupJudge: uiDupJudge,
    uiColumns: uiColumns,
    uiFormat: uiFormat,
    uiIntake: uiIntake,
    uiMetaHist: uiMetaHist,
    uiPanel: uiPanel,
    uiPool: uiPool,
    uiPoolPanel: uiPoolPanel,
    uiSchoolDict: uiSchoolDict,
    uiStdName: uiStdName,
    coreState: coreState,
  });
})();
