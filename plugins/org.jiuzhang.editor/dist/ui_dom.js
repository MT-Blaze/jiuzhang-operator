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
      var metricsEl = document.getElementById("edMetrics");
      var progressEl = document.getElementById("edProgress");
      var formatEl = document.getElementById("edFormat");
      var dirtyEl = document.getElementById("edDirty");
      var toastEl = document.getElementById("edToast");
      var savedEl = document.getElementById("edSaved");
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
      var panelMetaSecEl = document.getElementById("epMetaSec");
      var panelMetaFoldEl = document.getElementById("epMetaFold");
      var panelMetaSummaryEl = document.getElementById("epMetaSummary");
      var panelGhostTagMenuEl = document.getElementById("epGhostTagMenu");
      var panelGhostTopicMenuEl = document.getElementById("epGhostTopicMenu");
      var panelApproveEl = document.getElementById("epApprove");
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
      var panelFmtLatexEl = document.getElementById("epFmtLatex");
      var panelFmtBoxedEl = document.getElementById("epFmtBoxed");
      var panelSwapEl = document.getElementById("epSwap");
      var panelBackListEl = document.getElementById("epBackList");
      var panelViewNoteEl = document.getElementById("epViewNote");
      var dupModalEl = document.getElementById("epDupModal");
      var dupTextEl = document.getElementById("epDupText");
      var dupBackEl = document.getElementById("epDupBack");
      var dupForceEl = document.getElementById("epDupForce");
      var delModalEl = document.getElementById("epDelModal");
      var delCancelEl = document.getElementById("epDelCancel");
      var delOkEl = document.getElementById("epDelOk");

      // 批次公共元数据（辅助栏顶部）：六个可填字段 + 字典学校 + 可手改的标准名。
      var panelSrcNameEl = document.getElementById("epSrcName");
      var panelStdNameEl = document.getElementById("epStdName");
      var panelStdFlashEl = document.getElementById("epStdFlash");
      var panelStdHintEl = document.getElementById("epStdHint");
      var panelMetaYearEl = document.getElementById("epMetaYear");
      var panelMetaRegionEl = document.getElementById("epMetaRegion");
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

    return {
      root: root,
      colsEl: colsEl,
      imageBodyEl: imageBodyEl,
      sourceBodyEl: sourceBodyEl,
      renderBodyEl: renderBodyEl,
      imageNameEl: imageNameEl,
      sourceHintEl: sourceHintEl,
      metricsEl: metricsEl,
      progressEl: progressEl,
      formatEl: formatEl,
      dirtyEl: dirtyEl,
      toastEl: toastEl,
      savedEl: savedEl,
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
      panelMetaSecEl: panelMetaSecEl,
      panelMetaFoldEl: panelMetaFoldEl,
      panelMetaSummaryEl: panelMetaSummaryEl,
      panelGhostTagMenuEl: panelGhostTagMenuEl,
      panelGhostTopicMenuEl: panelGhostTopicMenuEl,
      panelApproveEl: panelApproveEl,
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
      panelFmtLatexEl: panelFmtLatexEl,
      panelFmtBoxedEl: panelFmtBoxedEl,
      panelSwapEl: panelSwapEl,
      panelBackListEl: panelBackListEl,
      panelViewNoteEl: panelViewNoteEl,
      dupModalEl: dupModalEl,
      dupTextEl: dupTextEl,
      dupBackEl: dupBackEl,
      dupForceEl: dupForceEl,
      delModalEl: delModalEl,
      delCancelEl: delCancelEl,
      delOkEl: delOkEl,
      panelSrcNameEl: panelSrcNameEl,
      panelStdNameEl: panelStdNameEl,
      panelStdFlashEl: panelStdFlashEl,
      panelStdHintEl: panelStdHintEl,
      panelMetaYearEl: panelMetaYearEl,
      panelMetaRegionEl: panelMetaRegionEl,
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
    };
  }

  global.JzoEditorDom = { create: create };
})(window);
