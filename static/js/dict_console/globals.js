/**
 * 全局设置：学段 / 学科 / 教材版本三个下拉框的状态中心。
 * 【教材版本】只列 dim_textbook_versions 的纯净版本名（人教A版/统编版…），
 * 册次不在这里出现——左侧章节树按「版本 → 册次 → 章 → 节」展开。
 * 选定即写 localStorage（键 jzo.dictConsole.globals.v1），刷新后还原；
 * 后续所有字典查询经 query() 默认携带这三个参数。
 */
(function () {
  "use strict";

  var STORAGE_KEY = "jzo.dictConsole.globals.v1";
  var EVENT_NAME = "dc:globals-changed";

  var els = null;
  var stateEl = null;
  var state = { stage: "", subject_id: "", version_id: "" };
  var subjects = [];
  var grades = [];
  var versions = [];
  var ready = false;

  function load() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      var saved = JSON.parse(raw);
      if (saved && typeof saved === "object") {
        state.stage = String(saved.stage || "");
        state.subject_id = String(saved.subject_id || "");
        // 旧键 textbook_id 存的是某一册，和版本 id 不是一回事，一律丢弃。
        state.version_id = String(saved.version_id || "");
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
    return { stage: state.stage, subject_id: state.subject_id, version_id: state.version_id };
  }

  /** 字典查询默认携带的参数：只带已选项，id 一律转整数。 */
  function query() {
    var out = {};
    if (state.stage) out.stage = state.stage;
    if (state.subject_id) out.subject_id = Number(state.subject_id);
    if (state.version_id) out.version_id = Number(state.version_id);
    return out;
  }

  function stageOptions() {
    var seen = [];
    grades.forEach(function (grade) {
      if (grade.stage && seen.indexOf(grade.stage) === -1) seen.push(grade.stage);
    });
    return seen;
  }

  function filteredVersions() {
    return versions.filter(function (version) {
      if (state.subject_id && String(version.subject_id) !== state.subject_id) return false;
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

  function renderVersions() {
    var options = [{ value: "", label: "全部版本" }].concat(filteredVersions().map(function (version) {
      return { value: String(version.id), label: version.name };
    }));
    fill(els.textbook, options, state.version_id);
    state.version_id = els.textbook.value;
  }

  function label() {
    var parts = [];
    parts.push(state.stage || "全部学段");
    var subject = subjects.filter(function (item) { return String(item.id) === state.subject_id; })[0];
    parts.push(subject ? subject.name : "全部学科");
    var version = versions.filter(function (item) {
      return String(item.id) === state.version_id;
    })[0];
    parts.push(version ? version.name : "全部版本");
    return parts.join(" · ");
  }

  function renderState() {
    if (stateEl) stateEl.textContent = ready ? "当前：" + label() : "字典数据加载中…";
  }

  function onChange(key) {
    if (key === "stage") state.stage = els.stage.value;
    else if (key === "subject_id") state.subject_id = els.subject.value;
    else state.version_id = els.textbook.value;
    if (key !== "version_id") renderVersions();
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
      window.DcClient.fetchJson("/api/bank/engine/textbook-versions")
    ]).then(function (results) {
      subjects = results[0].subjects || [];
      grades = results[0].grades || [];
      versions = results[1].items || [];
      ready = true;
      renderStages();
      renderSubjects();
      renderVersions();
      [els.stage, els.subject, els.textbook].forEach(function (select) { select.disabled = false; });
      els.stage.addEventListener("change", function () { onChange("stage"); });
      els.subject.addEventListener("change", function () { onChange("subject_id"); });
      els.textbook.addEventListener("change", function () { onChange("version_id"); });
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