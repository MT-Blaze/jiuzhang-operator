/**
 * 全局设置：学段 / 学科 / 教材版本三个下拉框的状态中心。
 * 选定即写 localStorage（键 jzo.dictConsole.globals.v1），刷新后还原；
 * 后续所有字典查询经 query() 默认携带这三个参数。
 * 联动口径：学科或学段变化 → 教材版本按 subject_id + 年级所属学段重过滤，
 * 已选教材不在新清单里就自动回到「全部教材」。
 */
(function () {
  "use strict";

  var STORAGE_KEY = "jzo.dictConsole.globals.v1";
  var EVENT_NAME = "dc:globals-changed";

  var els = null;
  var stateEl = null;
  var state = { stage: "", subject_id: "", textbook_id: "" };
  var subjects = [];
  var grades = [];
  var textbooks = [];
  var ready = false;

  function load() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      var saved = JSON.parse(raw);
      if (saved && typeof saved === "object") {
        state.stage = String(saved.stage || "");
        state.subject_id = String(saved.subject_id || "");
        state.textbook_id = String(saved.textbook_id || "");
      }
    } catch (error) {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }

  function persist() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (error) { /* 隐私模式写不进去也不挡操作 */ }
  }

  function emit() {
    document.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: current() }));
  }

  function current() {
    return { stage: state.stage, subject_id: state.subject_id, textbook_id: state.textbook_id };
  }

  /** 字典查询默认携带的参数：只带已选项，id 一律转整数。 */
  function query() {
    var out = {};
    if (state.stage) out.stage = state.stage;
    if (state.subject_id) out.subject_id = Number(state.subject_id);
    if (state.textbook_id) out.textbook_id = Number(state.textbook_id);
    return out;
  }

  function gradeStage(gradeId) {
    for (var i = 0; i < grades.length; i += 1) {
      if (String(grades[i].id) === String(gradeId)) return grades[i].stage || "";
    }
    return "";
  }

  function stageOptions() {
    var seen = [];
    grades.forEach(function (grade) {
      if (grade.stage && seen.indexOf(grade.stage) === -1) seen.push(grade.stage);
    });
    return seen;
  }

  function filteredTextbooks() {
    return textbooks.filter(function (book) {
      if (state.subject_id && String(book.subject_id) !== state.subject_id) return false;
      if (state.stage && book.grade_id != null && gradeStage(book.grade_id) !== state.stage) return false;
      return true;
    });
  }

  function fill(select, options, kept) {
    select.textContent = "";
    options.forEach(function (opt) {
      var node = document.createElement("option");
      node.value = opt.value;
      node.textContent = opt.label;
      select.appendChild(node);
    });
    select.value = kept;
    if (select.value !== kept) select.value = "";
  }

  function renderSubjects() {
    var options = [{ value: "", label: "全部学科" }].concat(subjects.map(function (item) {
      return { value: String(item.id), label: item.name };
    }));
    fill(els.subject, options, state.subject_id);
    state.subject_id = els.subject.value;
  }

  function renderStages() {
    var options = [{ value: "", label: "全部学段" }].concat(stageOptions().map(function (name) {
      return { value: name, label: name };
    }));
    fill(els.stage, options, state.stage);
    state.stage = els.stage.value;
  }

  function renderTextbooks() {
    var options = [{ value: "", label: "全部教材" }].concat(filteredTextbooks().map(function (book) {
      return { value: String(book.id), label: book.name };
    }));
    fill(els.textbook, options, state.textbook_id);
    state.textbook_id = els.textbook.value;
  }

  function label() {
    var parts = [];
    parts.push(state.stage || "全部学段");
    var subject = subjects.filter(function (item) { return String(item.id) === state.subject_id; })[0];
    parts.push(subject ? subject.name : "全部学科");
    var book = textbooks.filter(function (item) { return String(item.id) === state.textbook_id; })[0];
    parts.push(book ? book.name : "全部教材");
    return parts.join(" · ");
  }

  function renderState() {
    if (stateEl) stateEl.textContent = ready ? "当前：" + label() : "字典数据加载中…";
  }

  function onChange(key) {
    state[key] = els[key === "subject_id" ? "subject" : key === "textbook_id" ? "textbook" : "stage"].value;
    if (key !== "textbook_id") renderTextbooks();
    persist();
    renderState();
    emit();
  }

  /**
   * 挂载三个下拉框并拉取真实字典。失败时下拉保持禁用并如实报错，
   * 绝不拿假选项顶替（数据字典拒绝骨架）。
   */
  function init(selectEls, statusEl) {
    els = selectEls;
    stateEl = statusEl || null;
    load();
    return Promise.all([
      window.DcClient.fetchJson("/api/bank/engine/meta"),
      window.DcClient.fetchJson("/api/bank/engine/textbooks")
    ]).then(function (results) {
      subjects = results[0].subjects || [];
      grades = results[0].grades || [];
      textbooks = results[1].items || [];
      ready = true;
      renderStages();
      renderSubjects();
      renderTextbooks();
      [els.stage, els.subject, els.textbook].forEach(function (select) { select.disabled = false; });
      els.stage.addEventListener("change", function () { onChange("stage"); });
      els.subject.addEventListener("change", function () { onChange("subject_id"); });
      els.textbook.addEventListener("change", function () { onChange("textbook_id"); });
      persist();
      renderState();
      emit();
    }).catch(function (error) {
      if (stateEl) stateEl.textContent = "全局设置加载失败：" + error.message;
      throw error;
    });
  }

  window.DcGlobals = {
    init: init, current: current, query: query, label: label,
    EVENT_NAME: EVENT_NAME, STORAGE_KEY: STORAGE_KEY
  };
})();