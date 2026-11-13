/**
 * 全局设置：单按钮显示当前状态，展开后三下拉先改草稿，点【确定】才生效。
 * 选定组合写 localStorage（jzo.dictConsole.globals.v1），广播 dc:globals-changed，
 * 字典查询经 query() 默认携带这三个参数。失败时如实报错，不拿假选项顶替。
 */
(function () {
  "use strict";

  var STORAGE_KEY = "jzo.dictConsole.globals.v1";
  var EVENT_NAME = "dc:globals-changed";

  var els = null;
  var ui = null;
  var stateEl = null;
  var state = { stage: "", subject_id: "", version_id: "" };
  var draft = { stage: "", subject_id: "", version_id: "" };
  var subjects = [];
  var grades = [];
  var versions = [];
  var knownVersions = [];
  var versionSeq = 0;
  var ready = false;
  var panelOpen = false;

  function copy(source) {
    return { stage: source.stage, subject_id: source.subject_id, version_id: source.version_id };
  }

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
      if (draft.subject_id && String(version.subject_id) !== draft.subject_id) return false;
      // 版本按学段收口：高中数学绝不能再混进只服务小学/初中的人教版。
      if (draft.stage && version.stages && version.stages.indexOf(draft.stage) === -1) return false;
      return true;
    });
  }

  function subjectName(id) {
    var hit = subjects.filter(function (item) { return String(item.id) === String(id); })[0];
    return hit ? hit.name : "";
  }

  function versionName(id) {
    var hit = knownVersions.filter(function (item) { return String(item.id) === String(id); })[0];
    return hit ? hit.name : "";
  }

  function rememberVersions(items) {
    (items || []).forEach(function (item) {
      var seen = knownVersions.some(function (known) { return String(known.id) === String(item.id); });
      if (!seen) knownVersions.push(item);
    });
  }

  /** 学段 / 学科一变就按新条件重拉版本：跨学段版本（如小学的人教版）绝不留在高中清单里。 */
  function refreshVersions() {
    var seq = ++versionSeq;
    var query = [];
    if (draft.stage) query.push("stage=" + encodeURIComponent(draft.stage));
    if (draft.subject_id) query.push("subject_id=" + encodeURIComponent(draft.subject_id));
    var url = "/api/bank/engine/textbook-versions";
    if (query.length) url += "?" + query.join("&");
    els.textbook.disabled = true;
    return window.DcClient.fetchJson(url).then(function (body) {
      if (seq !== versionSeq) return;
      versions = (body && body.items) || [];
      rememberVersions(versions);
      renderVersions();
      els.textbook.disabled = false;
    }, function (error) {
      if (seq !== versionSeq) return;
      els.textbook.disabled = false;
      if (stateEl) stateEl.textContent = "教材版本刷新失败：" + error.message;
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

  function label() {
    return [
      state.stage || "全部学段",
      subjectName(state.subject_id) || "全部学科",
      versionName(state.version_id) || "全部版本"
    ].join(" · ");
  }

  function shortLabel() {
    return [
      state.stage || "全学段",
      subjectName(state.subject_id) || "全学科",
      versionName(state.version_id) || "全版本"
    ].join(" · ");
  }

  function renderToggle() {
    if (!ui || !ui.label) return;
    ui.label.textContent = ready ? shortLabel() : "加载中…";
    if (ui.toggle) ui.toggle.title = ready ? "全局设置：" + label() : "全局设置";
  }

  function renderState() {
    if (!stateEl) return;
    stateEl.textContent = ready ? "确定后立即生效，字典查询默认携带。" : "字典数据加载中…";
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

  function renderStages() {
    var options = [{ value: "", label: "全部学段" }].concat(stageOptions().map(function (name) {
      return { value: name, label: name };
    }));
    fill(els.stage, options, draft.stage);
    draft.stage = els.stage.value;
  }

  function renderSubjects() {
    var options = [{ value: "", label: "全部学科" }].concat(subjects.map(function (item) {
      return { value: String(item.id), label: item.name };
    }));
    fill(els.subject, options, draft.subject_id);
    draft.subject_id = els.subject.value;
  }

  function renderVersions() {
    var options = [{ value: "", label: "全部版本" }].concat(filteredVersions().map(function (version) {
      return { value: String(version.id), label: version.name };
    }));
    fill(els.textbook, options, draft.version_id);
    draft.version_id = els.textbook.value;
  }

  function renderDraft() {
    renderStages();
    renderSubjects();
    renderVersions();
  }

  function syncDraft(key) {
    if (key === "stage") draft.stage = els.stage.value;
    else if (key === "subject_id") draft.subject_id = els.subject.value;
    else draft.version_id = els.textbook.value;
    if (key === "stage" || key === "subject_id") {
      draft.version_id = els.textbook.value;
      renderVersions();
      refreshVersions();
    }
  }

  function setExpanded(expanded) {
    panelOpen = expanded;
    ui.panel.hidden = !expanded;
    ui.toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
  }

  function openPanel() {
    draft = copy(state);
    if (ready) {
      renderDraft();
      refreshVersions();
    }
    setExpanded(true);
    if (ready) els.stage.focus();
  }

  function closePanel(revert) {
    if (revert) draft = copy(state);
    setExpanded(false);
  }

  function commit() {
    if (!ready) return;
    state.stage = els.stage.value;
    state.subject_id = els.subject.value;
    state.version_id = els.textbook.value;
    persist();
    renderToggle();
    renderState();
    emit();
    closePanel(false);
    ui.toggle.focus();
  }

  function onToggle() {
    if (panelOpen) {
      closePanel(true);
      ui.toggle.focus();
    } else {
      openPanel();
    }
  }

  /** 新建版本后原地记住名称：否则切换标签只能退化成「全版本」。 */
  function rememberCreatedVersion(saved) {
    if (!saved.version_id || !saved.version_name) return;
    var item = {
      id: Number(saved.version_id), name: String(saved.version_name),
      code: "", sort_order: 0, publisher: null,
      subject_id: state.subject_id ? Number(state.subject_id) : null,
      stages: state.stage ? [state.stage] : []
    };
    rememberVersions([item]);
    var exists = versions.some(function (known) { return String(known.id) === String(item.id); });
    if (!exists) versions.push(item);
  }

  /** 宿主（工作台看板右栏）保存后原地灌入，不经过本页面板。 */
  function apply(saved) {
    if (!saved || typeof saved !== "object") return false;
    state.stage = String(saved.stage || "");
    state.subject_id = String(saved.subject_id || "");
    state.version_id = String(saved.version_id || "");
    rememberCreatedVersion(saved);
    draft = copy(state);
    persist();
    if (ready) {
      renderDraft();
      renderState();
    }
    renderToggle();
    emit();
    if (ui && ui.panel) closePanel(false);
    return true;
  }

  /**
   * 挂载设置面板并拉取真实字典。失败时下拉保持禁用并如实报错，
   * 绝不拿假选项顶替（数据字典拒绝骨架）。
   */
  function init(elements, statusEl, toggleEls) {
    els = elements;
    stateEl = statusEl || null;
    ui = toggleEls || {};
    load();
    draft = copy(state);
    renderToggle();
    if (ui.toggle) ui.toggle.addEventListener("click", onToggle);
    if (ui.confirm) ui.confirm.addEventListener("click", commit);
    els.stage.addEventListener("change", function () { syncDraft("stage"); });
    els.subject.addEventListener("change", function () { syncDraft("subject_id"); });
    els.textbook.addEventListener("change", function () { syncDraft("version_id"); });
    document.addEventListener("keydown", function (event) {
      if (!panelOpen || event.key !== "Escape") return;
      event.preventDefault();
      closePanel(true);
      if (ui.toggle) ui.toggle.focus();
    });

    return Promise.all([
      window.DcClient.fetchJson("/api/bank/engine/meta"),
      window.DcClient.fetchJson("/api/bank/engine/textbook-versions")
    ]).then(function (results) {
      subjects = results[0].subjects || [];
      grades = results[0].grades || [];
      versions = results[1].items || [];
      knownVersions = [];
      rememberVersions(versions);
      ready = true;
      renderDraft();
      [els.stage, els.subject, els.textbook].forEach(function (select) { select.disabled = false; });
      if (ui.confirm) ui.confirm.disabled = false;
      persist();
      renderToggle();
      renderState();
      emit();
    }).catch(function (error) {
      if (ui && ui.label) ui.label.textContent = "全局设置加载失败";
      if (stateEl) stateEl.textContent = "全局设置加载失败：" + error.message;
      throw error;
    });
  }

  window.DcGlobals = {
    init: init, apply: apply, current: current, query: query, label: label,
    EVENT_NAME: EVENT_NAME, STORAGE_KEY: STORAGE_KEY
  };
})();
