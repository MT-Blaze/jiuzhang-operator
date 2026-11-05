/**
 * core_save.js —— plugin.js 的「落库」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var DIFFICULTY_VALUES = coreState.DIFFICULTY_VALUES;
    var DRAFT_META_KEY = coreState.DRAFT_META_KEY;
    var OPTION_KEYS = coreState.OPTION_KEYS;
    var STEM_MAX = coreState.STEM_MAX;
    var TAG_LIMIT = coreState.TAG_LIMIT;
    var TOPIC_ID_RE = coreState.TOPIC_ID_RE;
    var TOPIC_LIMIT = coreState.TOPIC_LIMIT;
    var TYPE_VALUES = coreState.TYPE_VALUES;
    var defaultEntry = deps.defaultEntry;
    var defaultsOf = deps.defaultsOf;
    var dock = deps.dock;
    var hostCall = deps.hostCall;
    var keepExtensions = deps.keepExtensions;
    var markDirty = deps.markDirty;
    var panel = coreState.panel;
    var panelSay = deps.panelSay;
    var parseExamSource = deps.parseExamSource;
    var pushReceipt = deps.pushReceipt;
    var queueWorklistSave = deps.queueWorklistSave;
    var state = coreState.state;
    var metricsEl = deps.dom.metricsEl;
    var panelMetricsEl = deps.dom.panelMetricsEl;
    var panelStatusEl = deps.dom.panelStatusEl;
    var savedEl = deps.dom.savedEl;

  // ---------- 落库（辅助栏发起；命令面走同一份实现，绝不让两处各写一套） ----------
  var metaTimer = 0;

  function splitTags(text) {
    var seen = [];
    String(text == null ? "" : text).split(/[，,、;；\n]/).forEach(function (raw) {
      var tag = raw.trim().slice(0, 32);
      if (tag && seen.indexOf(tag) < 0) seen.push(tag);
    });
    return seen.slice(0, TAG_LIMIT);
  }

  function lettersFrom(text, type) {
    var letters = String(text == null ? "" : text).toUpperCase().replace(/[^A-H]/g, "");
    var unique = [];
    for (var index = 0; index < letters.length; index += 1) {
      if (unique.indexOf(letters.charAt(index)) < 0) unique.push(letters.charAt(index));
    }
    return type === "single_choice" ? unique.slice(0, 1) : unique.slice(0, 8);
  }

  /** 元数据只认宿主代持的草稿；两帧谁先写都无所谓，读的时候都是同一份。 */
  function metaFor(item, override) {
    var stored = panel.meta[item.key] || {};
    var meta = {};
    // 草稿里没有这一题时，用题目自己的默认值打底：自动存草稿是「静默」的动作，
    // 绝不能顺手把年级、标签、来源抹掉——老师没碰过表单不等于他不要这些。
    var fallback = defaultEntry({ defaults: defaultsOf(item) });
    Object.keys(fallback).forEach(function (key) { meta[key] = fallback[key]; });
    var taxonomy = (item.question || {}).taxonomy || {};
    meta.topic_ids = Array.isArray(taxonomy.topic_ids)
      ? taxonomy.topic_ids.slice(0, TOPIC_LIMIT) : [];
    Object.keys(stored).forEach(function (key) { meta[key] = stored[key]; });
    if (override) Object.keys(override).forEach(function (key) { meta[key] = override[key]; });
    return meta;
  }

  function questionFromParsed(item, parsed, meta) {
    var question = item.question || {};
    var type = TYPE_VALUES.indexOf(meta.type) >= 0 ? meta.type : parsed.type;
    var doc = {
      schema_version: "2.0",
      type: type,
      stem: parsed.stem
    };
    var isChoice = type === "single_choice" || type === "multiple_choice";
    if (isChoice) {
      doc.options = parsed.choices.map(function (content, position) {
        return { key: OPTION_KEYS[position] || "A", content: String(content == null ? "" : content) };
      });
    }
    var letters = lettersFrom(parsed.answer, type);
    if (isChoice) {
      // 自动切题先出选项、答案留给老师补：空 choice_keys 过不了契约（至少一项），
      // 这种时候干脆不带 answer——入库前的 validateForSave 仍会拦下没答案的题。
      if (letters.length) {
        doc.answer = { kind: "choice", choice_keys: letters, final: letters.join("") };
      }
    } else {
      var value = String(parsed.answer == null ? "" : parsed.answer);
      doc.answer = { kind: type === "fill_blank" ? "expression" : "text", content: value, final: value };
    }
    if (parsed.analysis) doc.solution = parsed.analysis;
    doc.difficulty = DIFFICULTY_VALUES.indexOf(meta.difficulty) >= 0 ? meta.difficulty : "L1";
    if (meta.grade) doc.grade = String(meta.grade).trim().slice(0, 20);
    var tags = splitTags(meta.tags);
    if (tags.length) doc.tags = tags;
    var taxonomy = {};
    ["textbook", "chapter", "section"].forEach(function (field) {
      var text = String(meta[field] == null ? "" : meta[field]).trim();
      if (text) taxonomy[field] = text.slice(0, 64);
    });
    var topicIds = (meta.topic_ids || []).filter(function (id) { return TOPIC_ID_RE.test(String(id)); }).slice(0, TOPIC_LIMIT);
    if (topicIds.length) taxonomy.topic_ids = topicIds;
    if (Object.keys(taxonomy).length) doc.taxonomy = taxonomy;
    var source = {};
    if (meta.paper_title) source.paper_title = String(meta.paper_title).trim().slice(0, 120);
    if (meta.question_no) source.question_no = String(meta.question_no).trim().slice(0, 20);
    if (meta.exam_type) source.exam_type = String(meta.exam_type).trim().slice(0, 64);
    var year = Number(meta.year);
    if (year >= 1900 && year <= 2100) source.year = Math.floor(year);
    if (question.source && question.source.region) source.region = String(question.source.region).slice(0, 64);
    if (question.source && question.source.school) source.school = String(question.source.school).slice(0, 64);
    if (Object.keys(source).length) doc.source = source;
    if (Array.isArray(question.images) && question.images.length) doc.images = question.images.slice(0, 32);
    var extras = keepExtensions(question.extensions);
    // 底座新增题目的写路径只从 extensions 认年级（core-bank.grade → org.jiuzhang.editor → legacy），
    // 契约根字段 grade 在 create 通道里没人读——沿用 v1 录题插件的键双写一次，否则年级落库即丢。
    var editorExt = extras["org.jiuzhang.editor"] || {};
    if (doc.grade) editorExt.grade = doc.grade;
    // 分值同样没有契约字段：只存进插件自己的扩展里，题目正文一个字都不多。
    var scoreText = String(meta.score == null ? "" : meta.score).trim().slice(0, 8);
    if (scoreText) editorExt.score = scoreText;
    if (Object.keys(editorExt).length) extras["org.jiuzhang.editor"] = editorExt;
    if (Object.keys(extras).length) doc.extensions = extras;
    return doc;
  }

  /** 保存前的最小校验：先把源码认全，再逐条对照契约的硬边界，问题一律用老师看得懂的话说。 */
  function validateForSave(doc, parsed, meta) {
    var problems = [];
    parsed.errors.forEach(function (text) { problems.push("源码：" + text); });
    if (!doc.stem) problems.push("题干不能为空");
    if (doc.stem.length > STEM_MAX) problems.push("题干过长（上限 " + STEM_MAX + " 字）");
    if (TYPE_VALUES.indexOf(doc.type) < 0) {
      problems.push("题库只收单选、多选、填空、解答四类题型，当前判为「" + (doc.type || "未知") + "」");
    }
    var isChoice = doc.type === "single_choice" || doc.type === "multiple_choice";
    if (isChoice) {
      if (!doc.options || doc.options.length < 2) problems.push("选择题至少要两个选项");
      var keys = (doc.options || []).map(function (option) { return option.key; });
      var letters = (doc.answer && doc.answer.choice_keys) || [];
      if (!letters.length) problems.push("请填写答案字母（例：B 或 AC）");
      letters.forEach(function (letter) {
        if (keys.indexOf(letter) < 0) problems.push("答案 " + letter + " 没有对应选项");
      });
      if (doc.type === "single_choice" && letters.length !== 1) problems.push("单选题答案只能有一个字母");
      if (doc.type === "multiple_choice" && letters.length < 2) problems.push("多选题答案至少两个字母");
    } else if (!(doc.answer && doc.answer.content)) {
      problems.push("请填写答案");
    }
    var rawYear = String(meta.year == null ? "" : meta.year).trim();
    if (rawYear && !doc.source) problems.push("年份要写 1900–2100 的四位数");
    if (doc.taxonomy && doc.taxonomy.topic_ids && doc.taxonomy.topic_ids.length > TOPIC_LIMIT) {
      problems.push("考向最多挂 " + TOPIC_LIMIT + " 个");
    }
    return problems;
  }

  function saveItem(item, meta, mode) {
    var parsed = parseExamSource(item.source);
    var doc = questionFromParsed(item, parsed, meta || {});
    var problems = validateForSave(doc, parsed, meta || {});
    if (problems.length) {
      return Promise.reject({ code: "LOCAL_INVALID", message: problems.join("；"), retryable: false });
    }
    var updating = mode !== "variant" && item.savedId && item.status === "stored";
    var payload = { question: doc };
    if (updating) payload.id = item.savedId;
    // 不带 sources：契约的「没给就保持原样」保住一题多卷的其余原卷，
    // 阶段 2 的辅助栏只有一张原卷输入，不能拿它去覆盖老师挂好的整组来源。
    var method = updating ? "bank.update" : "bank.create";
    return hostCall(method, payload).then(function (result) {
      var id = (result && result.id) || (updating ? item.savedId : "");
      if (mode !== "variant") {
        item.savedId = id;
        item.status = "stored";
        item.dirty = false;
        if (state.slot === "stage.center") {
          markDirty();
          queueWorklistSave();
        }
        pushReceipt({ key: item.key, id: id, action: updating ? "update" : "create", mode: mode });
        showSaved(id, updating);
      } else {
        pushReceipt({ key: item.key, id: id, action: "create", mode: "variant" });
        dock("录题工作台另存了派生变式：" + id + "（原题未动）");
        // 变式号必须留在状态位上：话术区随后会被画布回投的选区盖掉，只靠文本没法复查
        if (panelMetricsEl) panelMetricsEl.setAttribute("data-variant-id", id || "");
        panelSay("已另存为新题 " + id + "，原题仍是 " + (item.savedId || "未入库的那一题") + "。", "ok", "saved");
      }
      return { question_id: id, created: !updating, parent_id: item.savedId || "" };
    });
  }

  /** 入库后的回显：画布只报题号，辅助栏把状态徽章、按钮与详情话术一起改到位。 */
  function showSaved(id, updating) {
    if (state.slot === "stage.center") {
      if (savedEl) {
        savedEl.hidden = false;
        savedEl.textContent = "已入库 " + id;
        savedEl.setAttribute("data-id", id || "");
      }
      if (metricsEl) metricsEl.setAttribute("data-saved-id", id || "");
      dock("录题工作台把" + (updating ? "修改后的" : "新的") + "题目写进了题库：" + id);
      return;
    }
    if (panelStatusEl) {
      panelStatusEl.textContent = "● 已入库";
      panelStatusEl.setAttribute("data-status", "stored");
    }
    if (panelMetricsEl) {
      panelMetricsEl.setAttribute("data-saved-id", id || "");
      panelMetricsEl.setAttribute("data-save-state", updating ? "updated" : "created");
    }
    panelSay((updating ? "已更新题目 " : "已入库新题 ") + id + "。", "ok", updating ? "updated" : "created");
  }

  function loadMetaDraft() {
    return hostCall("draft.load", { key: DRAFT_META_KEY }).then(function (result) {
      var value = result && result.value;
      if (value && typeof value === "object") panel.meta = value;
      return panel.meta;
    }).catch(function () { return {}; });
  }

  function saveMetaDraft() {
    hostCall("draft.save", { key: DRAFT_META_KEY, value: panel.meta })
      .catch(function () { /* 存不下就算了 */ });
  }

  function queueMetaSave() {
    window.clearTimeout(metaTimer);
    metaTimer = window.setTimeout(saveMetaDraft, 250);
    // 元数据一落草稿，琥珀灯就得重算：考向是「还没挂考向」这条未清项的唯一来源。
    // 判定与描边都在 ui_amber 那一份里，这里只喊一声。
    if (deps.repaintPanel) deps.repaintPanel();
  }

  /** 退场/关页面前把压在延时里的公共元数据落地：延时的主人归本模块，别处不许摸。 */
  function flushMetaDraft() {
    if (!metaTimer) return;
    window.clearTimeout(metaTimer);
    metaTimer = 0;
    saveMetaDraft();
  }

  /** 画布侧的命令面保存：元数据从宿主代持的草稿里读，与辅助栏用的是同一份。 */
  function saveViaCommand(mode) {
    var item = state.items[state.active];
    if (!item) return Promise.reject(new Error("画布里没有当前题目"));
    return loadMetaDraft().then(function () {
      return saveItem(item, metaFor(item, {}), mode);
    });
  }

    return {
      flushMetaDraft: flushMetaDraft,
      lettersFrom: lettersFrom,
      loadMetaDraft: loadMetaDraft,
      metaFor: metaFor,
      metaTimer: metaTimer,
      questionFromParsed: questionFromParsed,
      queueMetaSave: queueMetaSave,
      saveItem: saveItem,
      saveMetaDraft: saveMetaDraft,
      saveViaCommand: saveViaCommand,
      showSaved: showSaved,
      splitTags: splitTags,
      validateForSave: validateForSave,
    };
  }

  global.JzoEditorSave = { create: create };
})(window);
