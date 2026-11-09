/**
 * ui_dom.js —— 画布与辅助栏的取节点（PLUGIN_SPEC §2.8.1：单文件不超 800 行）。
 *
 * 全部 id 都来自 dist/index.html；这里只负责「一次性拿到引用」，
 * 谁要用谁从 deps.dom 里取，plugin.js 不再自己挂一百多个 DOM 变量。
 */
(function (global) {
  "use strict";

  function create() {
      var root = document.getElementById("edRoot");
      var colsEl = document.getElementById("edCols");
      var imageBodyEl = document.getElementById("edImageBody");
      var sourceBodyEl = document.getElementById("edSourceBody");
      var renderBodyEl = document.getElementById("edRenderBody");
      var imageNameEl = document.getElementById("edImageName");
      var sourceHintEl = document.getElementById("edSourceHint");
      // 终极军令 任务四：源码栏【添加配图】入口。
      var addIllustrationEl = document.getElementById("edAddIllustration");
      // 悬浮切题画板入口（整块可下架）。
      var splitBoardBtnEl = document.getElementById("edSplitBoardBtn");
      var metricsEl = document.getElementById("edMetrics");
      var progressEl = document.getElementById("edProgress");
      var formatEl = document.getElementById("edFormat");
      var dirtyEl = document.getElementById("edDirty");
      var toastEl = document.getElementById("edToast");
      var savedEl = document.getElementById("edSaved");
      // AI 配置中心与覆盖确认两颗弹窗（终极军令 任务一/三）：住在画布帧，平时 hidden。
      var aiConfigModalEl = document.getElementById("epAiConfigModal");
      var aiOverwriteModalEl = document.getElementById("epAiOverwriteModal");
      // 本地 YOLO 模型选择（按需下载）：整块独立，删掉 ui_model.js 与这段即可下架。
      var modelModalEl = document.getElementById("edModelModal");
      var modelNoteEl = document.getElementById("edModelNote");
      var modelHintEl = document.getElementById("edModelHint");
      var modelProgressEl = document.getElementById("edModelProgress");
      var modelProgressTextEl = document.getElementById("edModelProgressText");
      var modelBarEl = document.getElementById("edModelBar");
      var modelFullEl = document.getElementById("edModelFull");
      var modelQuantizedEl = document.getElementById("edModelQuantized");
      var modelCancelEl = document.getElementById("edModelCancel");
      var poolEl = document.getElementById("edPool");
      var batchNoteEl = document.getElementById("edBatchNote");
      var batchesEl = document.getElementById("edBatches");
      var batchListEl = document.getElementById("edBatchList");
      var batchesEmptyEl = document.getElementById("edBatchesEmpty");
      var batchNoEl = document.getElementById("edBatchNo");
      var batchStatEl = document.getElementById("edBatchStat");
      // 文件收集筐（军令 #27）：拖入、粘贴、点选都先落这里，【开始解析】才建批次。
      var basketEl = document.getElementById("edBasket");
      var basketFileEl = document.getElementById("edBasketFile");
      var basketEmptyEl = document.getElementById("edBasketEmpty");
      var basketListEl = document.getElementById("edBasketList");
      var basketFootEl = document.getElementById("edBasketFoot");
      var basketGoEl = document.getElementById("edBasketGo");

      var panelRoot = document.getElementById("epRoot");
      var panelScrollEl = document.getElementById("epScroll");
      var panelProgressEl = document.getElementById("epProgress");
      var panelStatusEl = document.getElementById("epStatus");
      var panelConfidenceEl = document.getElementById("epConfidence");
      var panelTypeEl = document.getElementById("epType");
      var panelTypeNoteEl = document.getElementById("epTypeNote");
      var panelDifficultyEl = document.getElementById("epDifficulty");
      var panelQuestionNoEl = document.getElementById("epQuestionNo");
      var panelScoreEl = document.getElementById("epScore");
      var panelHeadNoEl = document.getElementById("epHeadNo");
      var panelTagsEl = document.getElementById("epTags");
      var panelTagListEl = document.getElementById("epTagList");
      var panelMountedEl = document.getElementById("epMounted");
      var panelKnowledgeListEl = document.getElementById("epMountedKnowledge");
      var panelMetaSecEl = document.getElementById("epMetaSec");
      var panelMetaFoldEl = document.getElementById("epMetaFold");
      var panelMetaSummaryEl = document.getElementById("epMetaSummary");
      var panelGhostTagMenuEl = document.getElementById("epGhostTagMenu");
      var panelGhostTopicMenuEl = document.getElementById("epGhostTopicMenu");
      var panelGhostKnowledgeMenuEl = document.getElementById("epGhostKnowledgeMenu");
      var panelApproveEl = document.getElementById("epApprove");
      // AI 配置与批量识别（终极军令 任务一/三）：入口在辅助栏顶部与底部动作区。
      var panelAiConfigEl = document.getElementById("epAiConfig");
      var panelAiBatchEl = document.getElementById("epAiBatch");
      var panelAiBatchNoteEl = document.getElementById("epAiBatchNote");
      var panelStashEl = document.getElementById("epStash");
      var panelDeleteEl = document.getElementById("epDelete");
      var panelMessageEl = document.getElementById("epMessage");
      var panelMetricsEl = document.getElementById("epMetrics");
      var panelAiFieldEl = document.getElementById("epAiField");
      var panelAiAskEl = document.getElementById("epAiAsk");
      var panelAiSendEl = document.getElementById("epAiSend");
      var panelAiCleanEl = document.getElementById("epAiClean");
      var panelAiStateEl = document.getElementById("epAiState");
      var panelAiNoteEl = document.getElementById("epAiNote");
      var panelAiPreviewEl = document.getElementById("epAiPreview");
      var panelAiApplyEl = document.getElementById("epAiApply");
      var panelAiDiscardEl = document.getElementById("epAiDiscard");
      var panelAiSecEl = document.getElementById("epAiSec");
      var panelAiFoldEl = document.getElementById("epAiFold");
      var panelCleanBoxEl = document.getElementById("epCleanBox");
      var panelCleanSummaryEl = document.getElementById("epCleanSummary");
      var panelCleanApplyStemEl = document.getElementById("epCleanApplyStem");
      var panelCleanDropStemEl = document.getElementById("epCleanDropStem");
      var panelCleanApplySolutionEl = document.getElementById("epCleanApplySolution");
      var panelCleanDropSolutionEl = document.getElementById("epCleanDropSolution");
      var panelFmtLatexEl = document.getElementById("epFmtLatex");
      var panelFmtBoxedEl = document.getElementById("epFmtBoxed");
      var panelSwapEl = document.getElementById("epSwap");
      var panelBackListEl = document.getElementById("epBackList");
      var panelViewNoteEl = document.getElementById("epViewNote");
      // 查重拦截（军令 #31）：辅助栏只报「有」与「去看」，对比浮层在画布那帧。
      var dupBoxEl = document.getElementById("epDupBox");
      var dupWarnEl = document.getElementById("epDupWarn");
      var dupInspectEl = document.getElementById("epDupInspect");
      var dupOverwriteEl = document.getElementById("epDupOverwrite");
      var dupMergeEl = document.getElementById("epDupMerge");
      var dupAbandonEl = document.getElementById("epDupAbandon");
      var dupReviewEl = document.getElementById("edDupModal");
      var dupMineEl = document.getElementById("edDupMineBody");
      var dupTheirEl = document.getElementById("edDupTheirBody");
      var dupNoteEl = document.getElementById("edDupNote");
      var dupBlockEl = document.getElementById("edDupBlock");
      var cleanReviewEl = document.getElementById("edCleanModal");
      var cleanNoteEl = document.getElementById("edCleanNote");
      var cleanSectionsEl = document.getElementById("edCleanSections");
      var delModalEl = document.getElementById("epDelModal");
      var delCancelEl = document.getElementById("epDelCancel");
      var delOkEl = document.getElementById("epDelOk");
      // 重题池（军令 #32 · 第五步）：画布那一屏只画左右渲染，一颗按钮都不放；
      // 档位、四个动作、锁死说明、删除二次确认全住辅助栏。
      var poolCanvasEl = document.getElementById("edPoolCanvas");
      var poolNoteEl = document.getElementById("edPoolNote");
      var poolMainEl = document.getElementById("edPoolMainBody");
      var poolIncomingEl = document.getElementById("edPoolIncomingBody");
      var poolWarnEl = document.getElementById("edPoolWarn");
      // 查重三栏（军令·查重三栏）：原题渲染栏、源码标签与裁判台整块。
      var originalPaneEl = document.getElementById("edPaneOriginal");
      var originalBodyEl = document.getElementById("edOriginalBody");
      var originalIdentEl = document.getElementById("edOriginalIdent");
      var imagePaneEl = document.getElementById("edPaneImage");
      var splitImageEl = document.getElementById("edSplitImage");
      var cmpSourceLabelEl = document.getElementById("edCmpSourceLabel");
      var renderHeadLabelEl = document.getElementById("edRenderHeadLabel");
      var panelPoolCompareEl = document.getElementById("epPoolCompare");
      var judgeSecEl = document.getElementById("epJudgeSec");
      var judgeIdentEl = document.getElementById("epJudgeIdent");
      var judgeDiffEl = document.getElementById("epJudgeDiff");
      var judgeNoteEl = document.getElementById("epJudgeNote");
      var judgeMergeEl = document.getElementById("epJudgeMerge");
      var judgeSolutionEl = document.getElementById("epJudgeSolution");
      var judgeSeparateEl = document.getElementById("epJudgeSeparate");
      var judgeDeleteEl = document.getElementById("epJudgeDelete");
      var judgeResolveEl = document.getElementById("epJudgeResolve");
      var judgeExitEl = document.getElementById("epJudgeExit");
      var judgeConflictModalEl = document.getElementById("epJudgeConflictModal");
      var judgeConflictTextEl = document.getElementById("epJudgeConflictText");
      var judgeConflictBodyEl = document.getElementById("epJudgeConflictBody");
      var judgeConflictWarnEl = document.getElementById("epJudgeConflictWarn");
      var judgeConflictCancelEl = document.getElementById("epJudgeConflictCancel");
      var judgeConflictOkEl = document.getElementById("epJudgeConflictOk");
      var judgeDelModalEl = document.getElementById("epJudgeDelModal");
      var judgeDelTextEl = document.getElementById("epJudgeDelText");
      var judgeDelCancelEl = document.getElementById("epJudgeDelCancel");
      var judgeDelOkEl = document.getElementById("epJudgeDelOk");
      var panelPoolEntryEl = document.getElementById("epPoolEntry");
      var panelPoolSecEl = document.getElementById("epPoolSec");
      var panelPoolCountEl = document.getElementById("epPoolCount");
      var panelPoolTiersEl = document.getElementById("epPoolTiers");
      var panelPoolListEl = document.getElementById("epPoolList");
      var panelPoolMsgEl = document.getElementById("epPoolMsg");
      var panelPoolActsEl = document.getElementById("epPoolActs");
      var panelPoolMergeEl = document.getElementById("epPoolMerge");
      var panelPoolSolutionEl = document.getElementById("epPoolSolution");
      var panelPoolSeparateEl = document.getElementById("epPoolSeparate");
      var panelPoolDeleteEl = document.getElementById("epPoolDelete");
      var panelPoolLockEl = document.getElementById("epPoolLock");
      var panelPoolBackEl = document.getElementById("epPoolBack");
      var panelApproveAllEl = document.getElementById("epApproveAll");
      var poolDelModalEl = document.getElementById("epPoolDelModal");
      var poolDelTextEl = document.getElementById("epPoolDelText");
      var poolDelCancelEl = document.getElementById("epPoolDelCancel");
      var poolDelOkEl = document.getElementById("epPoolDelOk");
      var batchPurgeModalEl = document.getElementById("epBatchPurgeModal");
      var batchPurgeSummaryEl = document.getElementById("epBatchPurgeSummary");
      var batchPurgeGroupsEl = document.getElementById("epBatchPurgeGroups");
      var batchPurgeEmptyEl = document.getElementById("epBatchPurgeEmpty");
      var batchPurgeCancelEl = document.getElementById("epBatchPurgeCancel");
      var batchPurgeOkEl = document.getElementById("epBatchPurgeOk");

      // 批次公共元数据（辅助栏顶部）：七个可填字段 + 字典学校 + 可手改的标准名。
      var panelSrcNameEl = document.getElementById("epSrcName");
      var panelStdNameEl = document.getElementById("epStdName");
      var panelStdFlashEl = document.getElementById("epStdFlash");
      var panelStdHintEl = document.getElementById("epStdHint");
      var panelMetaYearEl = document.getElementById("epMetaYear");
      var panelMetaRegionEl = document.getElementById("epMetaRegion");
      var panelMetaGradeEl = document.getElementById("epMetaGrade");
      var panelMetaBodyEl = document.getElementById("epMetaBody");
      var panelMetaSceneEl = document.getElementById("epMetaScene");
      var panelMetaExamTypeEl = document.getElementById("epMetaExamType");
      var panelMetaSubjectEl = document.getElementById("epMetaSubject");
      var panelMetaSchoolsEl = document.getElementById("epMetaSchools");
      var panelSchoolListEl = document.getElementById("epSchoolList");
      var panelSchoolInputEl = document.getElementById("epSchoolInput");
      var panelSchoolMenuEl = document.getElementById("epSchoolMenu");
      var panelSchoolConfirmEl = document.getElementById("epSchoolConfirm");
      var panelSchoolConfirmTextEl = document.getElementById("epSchoolConfirmText");
      var panelSchoolFullNameEl = document.getElementById("epSchoolFullName");
      var panelSchoolConfirmOkEl = document.getElementById("epSchoolConfirmOk");
      var panelSchoolConfirmCancelEl = document.getElementById("epSchoolConfirmCancel");
      var panelSchoolErrorEl = document.getElementById("epSchoolError");
      var panelTagMenuEl = document.getElementById("epTagMenu");
      var panelRegionListEl = document.getElementById("epMetaRegionList");
      var panelBodyListEl = document.getElementById("epMetaBodyList");
      var panelSubjectListEl = document.getElementById("epMetaSubjectList");
      var panelGradeListEl = document.getElementById("epMetaGradeList");

    return {
      root: root,
      colsEl: colsEl,
      imageBodyEl: imageBodyEl,
      sourceBodyEl: sourceBodyEl,
      renderBodyEl: renderBodyEl,
      imageNameEl: imageNameEl,
      sourceHintEl: sourceHintEl,
      addIllustrationEl: addIllustrationEl,
      splitBoardBtnEl: splitBoardBtnEl,
      metricsEl: metricsEl,
      progressEl: progressEl,
      formatEl: formatEl,
      dirtyEl: dirtyEl,
      toastEl: toastEl,
      savedEl: savedEl,
      aiConfigModalEl: aiConfigModalEl,
      aiOverwriteModalEl: aiOverwriteModalEl,
      modelModalEl: modelModalEl,
      modelNoteEl: modelNoteEl,
      modelHintEl: modelHintEl,
      modelProgressEl: modelProgressEl,
      modelProgressTextEl: modelProgressTextEl,
      modelBarEl: modelBarEl,
      modelFullEl: modelFullEl,
      modelQuantizedEl: modelQuantizedEl,
      modelCancelEl: modelCancelEl,
      poolEl: poolEl,
      batchNoteEl: batchNoteEl,
      batchesEl: batchesEl,
      batchListEl: batchListEl,
      batchesEmptyEl: batchesEmptyEl,
      batchNoEl: batchNoEl,
      batchStatEl: batchStatEl,
      basketEl: basketEl,
      basketFileEl: basketFileEl,
      basketEmptyEl: basketEmptyEl,
      basketListEl: basketListEl,
      basketFootEl: basketFootEl,
      basketGoEl: basketGoEl,
      panelRoot: panelRoot,
      panelScrollEl: panelScrollEl,
      panelProgressEl: panelProgressEl,
      panelStatusEl: panelStatusEl,
      panelConfidenceEl: panelConfidenceEl,
      panelTypeEl: panelTypeEl,
      panelTypeNoteEl: panelTypeNoteEl,
      panelDifficultyEl: panelDifficultyEl,
      panelQuestionNoEl: panelQuestionNoEl,
      panelScoreEl: panelScoreEl,
      panelHeadNoEl: panelHeadNoEl,
      panelTagsEl: panelTagsEl,
      panelTagListEl: panelTagListEl,
      panelMountedEl: panelMountedEl,
      panelKnowledgeListEl: panelKnowledgeListEl,
      panelMetaSecEl: panelMetaSecEl,
      panelMetaFoldEl: panelMetaFoldEl,
      panelMetaSummaryEl: panelMetaSummaryEl,
      panelGhostTagMenuEl: panelGhostTagMenuEl,
      panelGhostTopicMenuEl: panelGhostTopicMenuEl,
      panelGhostKnowledgeMenuEl: panelGhostKnowledgeMenuEl,
      panelApproveEl: panelApproveEl,
      panelAiConfigEl: panelAiConfigEl,
      panelAiBatchEl: panelAiBatchEl,
      panelAiBatchNoteEl: panelAiBatchNoteEl,
      panelStashEl: panelStashEl,
      panelDeleteEl: panelDeleteEl,
      panelMessageEl: panelMessageEl,
      panelMetricsEl: panelMetricsEl,
      panelAiFieldEl: panelAiFieldEl,
      panelAiAskEl: panelAiAskEl,
      panelAiSendEl: panelAiSendEl,
      panelAiCleanEl: panelAiCleanEl,
      panelAiStateEl: panelAiStateEl,
      panelAiNoteEl: panelAiNoteEl,
      panelAiPreviewEl: panelAiPreviewEl,
      panelAiApplyEl: panelAiApplyEl,
      panelAiDiscardEl: panelAiDiscardEl,
      panelAiSecEl: panelAiSecEl,
      panelAiFoldEl: panelAiFoldEl,
      panelCleanBoxEl: panelCleanBoxEl,
      panelCleanSummaryEl: panelCleanSummaryEl,
      panelCleanApplyStemEl: panelCleanApplyStemEl,
      panelCleanDropStemEl: panelCleanDropStemEl,
      panelCleanApplySolutionEl: panelCleanApplySolutionEl,
      panelCleanDropSolutionEl: panelCleanDropSolutionEl,
      panelFmtLatexEl: panelFmtLatexEl,
      panelFmtBoxedEl: panelFmtBoxedEl,
      panelSwapEl: panelSwapEl,
      panelBackListEl: panelBackListEl,
      panelViewNoteEl: panelViewNoteEl,
      dupBoxEl: dupBoxEl,
      dupWarnEl: dupWarnEl,
      dupInspectEl: dupInspectEl,
      dupReviewEl: dupReviewEl,
      dupMineEl: dupMineEl,
      dupTheirEl: dupTheirEl,
      dupNoteEl: dupNoteEl,
      dupBlockEl: dupBlockEl,
      cleanReviewEl: cleanReviewEl,
      cleanNoteEl: cleanNoteEl,
      cleanSectionsEl: cleanSectionsEl,
      dupOverwriteEl: dupOverwriteEl,
      dupMergeEl: dupMergeEl,
      dupAbandonEl: dupAbandonEl,
      delModalEl: delModalEl,
      delCancelEl: delCancelEl,
      delOkEl: delOkEl,
      poolCanvasEl: poolCanvasEl,
      poolNoteEl: poolNoteEl,
      poolMainEl: poolMainEl,
      poolIncomingEl: poolIncomingEl,
      poolWarnEl: poolWarnEl,
      originalPaneEl: originalPaneEl,
      originalBodyEl: originalBodyEl,
      originalIdentEl: originalIdentEl,
      imagePaneEl: imagePaneEl,
      splitImageEl: splitImageEl,
      cmpSourceLabelEl: cmpSourceLabelEl,
      renderHeadLabelEl: renderHeadLabelEl,
      panelPoolCompareEl: panelPoolCompareEl,
      judgeSecEl: judgeSecEl,
      judgeIdentEl: judgeIdentEl,
      judgeDiffEl: judgeDiffEl,
      judgeNoteEl: judgeNoteEl,
      judgeMergeEl: judgeMergeEl,
      judgeSolutionEl: judgeSolutionEl,
      judgeSeparateEl: judgeSeparateEl,
      judgeDeleteEl: judgeDeleteEl,
      judgeResolveEl: judgeResolveEl,
      judgeExitEl: judgeExitEl,
      judgeConflictModalEl: judgeConflictModalEl,
      judgeConflictTextEl: judgeConflictTextEl,
      judgeConflictBodyEl: judgeConflictBodyEl,
      judgeConflictWarnEl: judgeConflictWarnEl,
      judgeConflictCancelEl: judgeConflictCancelEl,
      judgeConflictOkEl: judgeConflictOkEl,
      judgeDelModalEl: judgeDelModalEl,
      judgeDelTextEl: judgeDelTextEl,
      judgeDelCancelEl: judgeDelCancelEl,
      judgeDelOkEl: judgeDelOkEl,
      panelPoolEntryEl: panelPoolEntryEl,
      panelPoolSecEl: panelPoolSecEl,
      panelPoolCountEl: panelPoolCountEl,
      panelPoolTiersEl: panelPoolTiersEl,
      panelPoolListEl: panelPoolListEl,
      panelPoolMsgEl: panelPoolMsgEl,
      panelPoolActsEl: panelPoolActsEl,
      panelPoolMergeEl: panelPoolMergeEl,
      panelPoolSolutionEl: panelPoolSolutionEl,
      panelPoolSeparateEl: panelPoolSeparateEl,
      panelPoolDeleteEl: panelPoolDeleteEl,
      panelPoolLockEl: panelPoolLockEl,
      panelPoolBackEl: panelPoolBackEl,
      panelApproveAllEl: panelApproveAllEl,
      poolDelModalEl: poolDelModalEl,
      poolDelTextEl: poolDelTextEl,
      poolDelCancelEl: poolDelCancelEl,
      poolDelOkEl: poolDelOkEl,
      batchPurgeModalEl: batchPurgeModalEl,
      batchPurgeSummaryEl: batchPurgeSummaryEl,
      batchPurgeGroupsEl: batchPurgeGroupsEl,
      batchPurgeEmptyEl: batchPurgeEmptyEl,
      batchPurgeCancelEl: batchPurgeCancelEl,
      batchPurgeOkEl: batchPurgeOkEl,
      panelSrcNameEl: panelSrcNameEl,
      panelStdNameEl: panelStdNameEl,
      panelStdFlashEl: panelStdFlashEl,
      panelStdHintEl: panelStdHintEl,
      panelMetaYearEl: panelMetaYearEl,
      panelMetaRegionEl: panelMetaRegionEl,
      panelMetaGradeEl: panelMetaGradeEl,
      panelMetaBodyEl: panelMetaBodyEl,
      panelMetaSceneEl: panelMetaSceneEl,
      panelMetaExamTypeEl: panelMetaExamTypeEl,
      panelMetaSubjectEl: panelMetaSubjectEl,
      panelMetaSchoolsEl: panelMetaSchoolsEl,
      panelSchoolListEl: panelSchoolListEl,
      panelSchoolInputEl: panelSchoolInputEl,
      panelSchoolMenuEl: panelSchoolMenuEl,
      panelSchoolConfirmEl: panelSchoolConfirmEl,
      panelSchoolConfirmTextEl: panelSchoolConfirmTextEl,
      panelSchoolFullNameEl: panelSchoolFullNameEl,
      panelSchoolConfirmOkEl: panelSchoolConfirmOkEl,
      panelSchoolConfirmCancelEl: panelSchoolConfirmCancelEl,
      panelSchoolErrorEl: panelSchoolErrorEl,
      panelTagMenuEl: panelTagMenuEl,
      panelRegionListEl: panelRegionListEl,
      panelBodyListEl: panelBodyListEl,
      panelSubjectListEl: panelSubjectListEl,
      panelGradeListEl: panelGradeListEl,
    };
  }

  global.JzoEditorDom = { create: create };
})(window);
