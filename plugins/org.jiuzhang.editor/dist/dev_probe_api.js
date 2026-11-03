/**
 * dev_probe_api.js —— 真机探针用的调试面（window.__jzoEditorV2）。
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）
 *
 * 只把各模块的入口聚合成一个对象交给 Playwright 复核，不参与业务分支。
 * 交进来的是**命名空间**而不是五十条裸别名，plugin.js 因此少掉几十行接线。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreExamSource = deps.coreExamSource;
    var coreSave = deps.coreSave;
    var coreSelection = deps.coreSelection;
    var coreState = deps.coreState;
    var devFixtures = deps.devFixtures;
    var uiAmber = deps.uiAmber;
    var uiApprove = deps.uiApprove;
    var uiBatches = deps.uiBatches;
    var uiColumns = deps.uiColumns;
    var uiFormat = deps.uiFormat;
    var uiIntake = deps.uiIntake;
    var uiMetaHist = deps.uiMetaHist;
    var uiPanel = deps.uiPanel;
    var uiPool = deps.uiPool;
    var uiPoolPanel = deps.uiPoolPanel;
    var uiSchoolDict = deps.uiSchoolDict;
    var uiStdName = deps.uiStdName;
    var IDLE_MS = coreState.IDLE_MS;
    var panel = coreState.panel;
    var state = coreState.state;

    return {
  version: "3.0.0-batch",
  parseExamSource: coreExamSource.parseExamSource,
  buildExamSource: coreExamSource.buildExamSource,
  // 判据 1.6 后插件不再有本地清洗规则，清洗一律经宿主 text.clean_latex（底座一张字典）。
  amberReasons: uiAmber.amberReasons,
  amberScan: uiAmber.scan,
  poolTier: uiPoolPanel.tierNow,
  poolEntryCount: uiPoolPanel.poolSize,
  poolCanvasOpen: uiPool.isOpen,
  boxesToQuestion: uiColumns.boxesToQuestion,
  questionFromParsed: coreSave.questionFromParsed,
  validateForSave: coreSave.validateForSave,
  fixtures: devFixtures.DEV_FIXTURES,
  state: state,
  panel: panel,
  renderAll: uiColumns.renderAll,
  refreshRow: uiColumns.refreshRow,
  setFormat: uiFormat.setFormat,
  applySwap: uiFormat.applySwap,
  toggleSwap: uiFormat.toggleSwap,
  saveItem: coreSave.saveItem,
  applySelection: uiPanel.applySelection,
  selectionPayload: coreSelection.selectionPayload,
  jumpTo: uiColumns.jumpTo,
  poolCounts: uiApprove.poolCounts,
  // 审核台：批次列表、点入审核、存草稿、存回中转池
  refreshBatches: uiBatches.refreshBatches,
  renderBatchList: uiBatches.renderBatchList,
  openBatch: uiBatches.openBatch,
  backToList: uiBatches.backToList,
  backToListFromPanel: uiFormat.backToListFromPanel,
  publishView: uiBatches.publishView,
  setMode: uiBatches.setMode,
  stashOne: uiBatches.stashOne,
  onApprove: uiApprove.onApprove,
  onStash: uiApprove.onStash,
  onDelete: uiApprove.onDelete,
  autoSaveIdle: uiBatches.autoSaveIdle,
  noteActivity: uiBatches.noteActivity,
  // 批次公共元数据与接收区
  standardNameOf: uiMetaHist.standardNameOf,
  renderBatchMeta: uiStdName.renderBatchMeta,
  loadBatchMeta: uiStdName.loadBatchMeta,
  loadMetaHistory: uiMetaHist.loadMetaHistory,
  applyMetaSync: uiStdName.applyMetaSync,
  queueMetaSync: uiStdName.queueMetaSync,
  onMetaFieldChange: uiStdName.onMetaFieldChange,
  // 数据字典（军令 #28）：学校检索/建档、场景与交叉标签。
  addSchoolRecord: uiSchoolDict.addSchoolRecord,
  searchSchools: uiSchoolDict.searchSchools,
  confirmSchoolCreate: uiSchoolDict.confirmSchoolCreate,
  requestSchoolSuggest: uiSchoolDict.requestSchoolSuggest,
  loadTags: uiSchoolDict.loadTags,
  pickTag: uiSchoolDict.pickTag,
  onTagEnter: uiSchoolDict.onTagEnter,
  loadScenes: uiMetaHist.loadScenes,
  // 标准名双向联动：自动/手动模式与「已更新」闪烁。
  stdLiveName: uiStdName.stdLiveName,
  setStdMode: uiStdName.setStdMode,
  flashStd: uiStdName.flashStd,
  ingestEntries: uiIntake.ingestEntries,
  // 收集筐（军令 #27）：探针要能看筐里有什么、能把文件塞进去。
  basket: function () {
    return state.basket.map(function (entry) {
      return { id: entry.id, name: entry.name, type: entry.type, size: entry.size, url: entry.url };
    });
  },
  basketAdd: uiIntake.basketAdd,
  basketRemove: uiIntake.basketRemove,
  basketGo: uiIntake.basketGo,
  // 探针要把假时钟拨快，三分钟那道闸门才认得出「没人操作」
  idleThreshold: function () { return IDLE_MS; },
  tickIdle: function () {
    uiBatches.markIdleDue();
  }
    };
  }

  global.JzoEditorProbeApi = { create: create };
})(window);
