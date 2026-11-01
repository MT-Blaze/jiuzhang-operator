/**
 * core_selection.js —— plugin.js 的「当前题上桥」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var DEV_NS = coreState.DEV_NS;
    var DIFFICULTY_VALUES = coreState.DIFFICULTY_VALUES;
    var DRAFT_WORKLIST_KEY = coreState.DRAFT_WORKLIST_KEY;
    var SELECTION_MS = coreState.SELECTION_MS;
    var SOURCE_MAX = coreState.SOURCE_MAX;
    var TAG_LIMIT = coreState.TAG_LIMIT;
    var TYPE_VALUES = coreState.TYPE_VALUES;
    var WORKLIST_DRAFT_MS = coreState.WORKLIST_DRAFT_MS;
    var fieldAtOffset = deps.fieldAtOffset;
    var hostCall = deps.hostCall;
    var parsedOf = deps.parsedOf;
    var poolCounts = deps.poolCounts;
    var publish = deps.publish;
    var scheduleRender = deps.scheduleRender;
    var state = coreState.state;
    var trunc = deps.trunc;

  // ---------- 当前题上桥（画布 → 辅助栏：唯一的合法通道是 stage.selection） ----------
  var selectionTimer = 0;
  var worklistTimer = 0;

  /** 元数据默认值：从真题结构里摘出辅助栏表单要预填的那一小组字段。 */
  function defaultsOf(item) {
    var question = item.question || {};
    var source = question.source || {};
    var taxonomy = question.taxonomy || {};
    var extensions = question.extensions && typeof question.extensions === "object"
      ? question.extensions : {};
    var editorExt = extensions["org.jiuzhang.editor"] && typeof extensions["org.jiuzhang.editor"] === "object"
      ? extensions["org.jiuzhang.editor"] : {};
    return {
      type: TYPE_VALUES.indexOf(question.type) >= 0 ? question.type : "",
      difficulty: DIFFICULTY_VALUES.indexOf(question.difficulty) >= 0 ? question.difficulty : "L1",
      grade: trunc(question.grade, 20),
      tags: (question.tags || []).slice(0, TAG_LIMIT).join(","),
      score: trunc(editorExt.score, 8),
      paper_title: trunc(source.paper_title, 120),
      question_no: trunc(source.question_no, 20),
      exam_type: trunc(source.exam_type, 64),
      year: source.year == null ? "" : String(source.year),
      textbook: trunc(taxonomy.textbook, 64),
      chapter: trunc(taxonomy.chapter, 64),
      section: trunc(taxonomy.section, 64)
    };
  }

  /**
   * 老师当前题里的光标位置 → AI 能改哪个字段。
   * 源码按源码偏移判定（choices 与「答案：」行都判不出字段，档 1 只吃题干/解析）；
   * 卡片直接看框的语义字段，框头环境名本来就锁死，不必再算偏移。
   */
  function caretOfActive() {
    var item = state.items[state.active];
    if (!item) return null;
    var node = document.activeElement;
    if (!node || !node.getAttribute || !("selectionStart" in node)) return null;
    if (node.getAttribute("data-index") !== String(state.active)) return null;
    var boxField = node.getAttribute("data-field");
    var start = Number(node.selectionStart) || 0;
    var end = Number(node.selectionEnd) || 0;
    var picked = String(node.value || "").slice(Math.min(start, end), Math.max(start, end));
    var field = "";
    if (boxField === "source") field = fieldAtOffset(item.source, end || start);
    else if (boxField === "stem" || boxField === "solution") field = boxField;
    return {
      field: field,
      has_selection: end > start,
      text: trunc(picked, 160)
    };
  }

  function selectionPayload() {
    var item = state.items[state.active];
    // 首屏是批次列表：没有题可发，但辅助栏仍要知道有哪些批次、当前是哪一个，
    // 才能把公共元数据与标准名摆出来。
    if (state.mode === "list") return listPayload();
    if (!item) return null;
    var parsed = parsedOf(item);
    var question = item.question || {};
    return {
      index: state.active,
      total: state.items.length,
      key: item.key,
      question_id: item.savedId || question.id || "",
      saved_id: item.savedId || "",
      // 中转站的两把号：审核动作（存入主库 / 存为待办 / 彻底删除）全靠它们。
      pending_id: item.pendingId || "",
      batch_id: item.batchId || state.batchId || "",
      mode: state.mode,
      status: item.status,
      dirty: Boolean(item.dirty),
      format: state.format,
      swap: Boolean(state.swap),
      source: trunc(item.source, SOURCE_MAX),
      caret: caretOfActive(),
      errors: parsed.errors.slice(0, 8),
      ai_type: parsed.type,
      confidence: typeof item.dev.confidence === "number" ? item.dev.confidence : null,
      defaults: defaultsOf(item),
      // 待入库池的台账随选区一起走：辅助栏要自己知道「一共几题、几题脏」才敢让那颗钮亮起来。
      pool: poolCounts(),
      images: (question.images || []).slice(0, 32),
      extensions: keepExtensions(question.extensions),
      origin: question.source && typeof question.source === "object"
        ? { region: question.source.region || "", school: question.source.school || "" }
        : null
    };
  }

  /** 批次列表语境：辅助栏据此显示原文件名、标准名与公共元数据面板。 */
  function listPayload() {
    return {
      mode: "list",
      index: 0,
      total: state.items.length,
      key: "",
      question_id: "",
      saved_id: "",
      pending_id: "",
      batch_id: state.batchId || "",
      status: "pending",
      dirty: false,
      format: state.format,
      swap: Boolean(state.swap),
      source: "",
      caret: null,
      errors: [],
      ai_type: "",
      confidence: null,
      defaults: {},
      pool: poolCounts(),
      images: [],
      extensions: {},
      origin: null,
      batches: state.batches.map(function (card) {
        return {
          batch_id: String(card.batch_id || ""),
          source_name: String(card.source_name || ""),
          label: String(card.label || ""),
          pending_count: Number(card.pending_count) || 0,
          total: Number(card.total) || 0,
          meta: card.meta && typeof card.meta === "object" ? card.meta : {}
        };
      })
    };
  }

  /** 假数据提示只活在开发帧里，绝不该跟到真题库的 extensions 里。 */
  function keepExtensions(raw) {
    var out = {};
    Object.keys(raw && typeof raw === "object" ? raw : {}).forEach(function (key) {
      if (key === DEV_NS) return;
      out[key] = raw[key];
    });
    return out;
  }

  function publishSelection() {
    var payload = selectionPayload();
    if (!payload) return;
    // 选区一发布，工作清单草稿就得跟着落盘：批量保存那颗钮住在辅助栏，
    // 面板侧只能读这份草稿重建题目。草稿若还停在 600ms 前的旧版，
    // 老师刚改的那一题就会漏交，还不自知。
    saveWorklist();
    publish("stage.selection", payload);
  }

  function publishSelectionSoon() {
    window.clearTimeout(selectionTimer);
    selectionTimer = window.setTimeout(publishSelection, SELECTION_MS);
  }

  /** 画布退场：延时里还压着一次上桥，扔掉——题都走了，没必要再广播。 */
  function cancelSelectionPublish() {
    if (!selectionTimer) return;
    window.clearTimeout(selectionTimer);
    selectionTimer = 0;
  }

  function worklistValue() {
    return {
      active: state.active,
      items: state.items.map(function (item) {
        var question = item.question || {};
        return {
          key: item.key,
          id: question.id ? question.id : "",
          saved_id: item.savedId || "",
          pending_id: item.pendingId || "",
          batch_id: item.batchId || state.batchId || "",
          status: item.status,
          dirty: Boolean(item.dirty),
          source: trunc(item.source, SOURCE_MAX),
          // 辅助栏可能在画布发布选区之前就已挂载：把默认值一并存进宿主代持的草稿，
          // 面板读草稿就能自己补出这张表单，不必等一条永远不会重放的通知。
          defaults: defaultsOf(item),
          confidence: typeof item.dev.confidence === "number" ? item.dev.confidence : null,
          errors: parsedOf(item).errors.slice(0, 8),
          // 批量保存搬进辅助栏后，面板侧要靠这份台账把题目原样重建出来：
          // 少了图片、扩展与原卷字段，更新一题就会把这些悄悄抹掉。
          images: (question.images || []).slice(0, 32),
          extensions: keepExtensions(question.extensions),
          origin: question.source && typeof question.source === "object"
            ? { region: question.source.region || "", school: question.source.school || "" }
            : null
        };
      })
    };
  }

  function saveWorklist() {
    if (!state.items.length) return;
    hostCall("draft.save", { key: DRAFT_WORKLIST_KEY, value: worklistValue() })
      .catch(function () { /* 草稿存不下就算了，不打扰老师 */ });
  }

  function queueWorklistSave() {
    window.clearTimeout(worklistTimer);
    worklistTimer = window.setTimeout(saveWorklist, WORKLIST_DRAFT_MS);
  }

  /** 关页签/退场前把压在延时里的那一版工作清单落地：延时的主人归本模块，别处不许摸。 */
  function flushWorklist() {
    if (!worklistTimer) return;
    window.clearTimeout(worklistTimer);
    worklistTimer = 0;
    saveWorklist();
  }

  /** 辅助栏挂载时补的是同一份宿主代持草稿；画布重开页签也靠它对回未保存的源码。 */
  function restoreWorklist() {
    return hostCall("draft.load", { key: DRAFT_WORKLIST_KEY }).then(function (result) {
      var value = result && result.value;
      if (!value || !Array.isArray(value.items)) return;
      var touched = false;
      value.items.forEach(function (saved) {
        if (!saved || typeof saved !== "object") return;
        for (var index = 0; index < state.items.length; index += 1) {
          var item = state.items[index];
          if (item.key !== saved.key) continue;
          if (typeof saved.source === "string" && saved.source && saved.source !== item.source) {
            item.source = saved.source;
            item.parsed = null;
            touched = true;
          }
          item.dirty = Boolean(saved.dirty);
          item.status = saved.status === "stored" ? "stored" : "pending";
          item.savedId = typeof saved.saved_id === "string" ? saved.saved_id : null;
          break;
        }
      });
      var wanted = Number(value.active);
      if (wanted >= 0 && wanted < state.items.length) state.active = wanted;
      if (touched) scheduleRender();
    }).catch(function () { /* 读不到草稿就从假数据重来 */ });
  }

    return {
      cancelSelectionPublish: cancelSelectionPublish,
      caretOfActive: caretOfActive,
      defaultsOf: defaultsOf,
      flushWorklist: flushWorklist,
      keepExtensions: keepExtensions,
      listPayload: listPayload,
      publishSelection: publishSelection,
      publishSelectionSoon: publishSelectionSoon,
      queueWorklistSave: queueWorklistSave,
      restoreWorklist: restoreWorklist,
      saveWorklist: saveWorklist,
      selectionPayload: selectionPayload,
      selectionTimer: selectionTimer,
      worklistTimer: worklistTimer,
      worklistValue: worklistValue,
    };
  }

  global.JzoEditorSelection = { create: create };
})(window);
