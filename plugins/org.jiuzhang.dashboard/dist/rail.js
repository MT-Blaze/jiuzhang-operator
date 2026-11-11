/**
 * 看板右栏：全局设置 + 三大主分类，与字典控制台辅助栏同构。
 *
 * 插件跑在不透明源的沙箱里，读写全局设置一律经宿主通道：
 * dict.globals_get 取当前值与真实选项，dict.globals_save 交宿主落盘并灌进字典页。
 * 分类按钮只发 dict.open（不带 table），由宿主原地铺开该分类页，二级标签画在上方。
 * 整块下架：删本文件、index.html 的引用行、plugin.js 的 DbRail.mount 调用与 plugin.css 的 db-rail 段。
 */
(function (global) {
  "use strict";

  var ALL_STAGE = "全部学段";
  var ALL_SUBJECT = "全部学科";
  var ALL_VERSION = "全部版本";

  function mount(root, deps) {
    var call = deps.call;
    var dock = deps.dock;
    var el = deps.el;

    var ui = {};
    var catButtons = [];
    var options = { stages: [], subjects: [], versions: [] };
    var knownVersions = [];
    var current = { stage: "", subject_id: "", version_id: "" };
    var draft = { stage: "", subject_id: "", version_id: "" };
    var versionSeq = 0;
    var panelOpen = false;
    var ready = false;

    function copy(source) {
      return {
        stage: source.stage || "",
        subject_id: source.subject_id || "",
        version_id: source.version_id || ""
      };
    }

    function normalize(source) {
      source = source || {};
      return {
        stage: String(source.stage || ""),
        subject_id: source.subject_id == null ? "" : String(source.subject_id),
        version_id: source.version_id == null ? "" : String(source.version_id)
      };
    }

    function subjectName(id) {
      var hit = options.subjects.filter(function (item) {
        return String(item.id) === String(id);
      })[0];
      return hit ? hit.name : "";
    }

    function versionName(id) {
      var hit = knownVersions.filter(function (item) {
        return String(item.id) === String(id);
      })[0];
      return hit ? hit.name : "";
    }

    function rememberVersions(items) {
      (items || []).forEach(function (item) {
        var seen = knownVersions.some(function (known) {
          return String(known.id) === String(item.id);
        });
        if (!seen) knownVersions.push(item);
      });
    }

    function shortLabel() {
      return [
        current.stage || "全学段",
        subjectName(current.subject_id) || "全学科",
        versionName(current.version_id) || "全版本"
      ].join(" · ");
    }

    function renderLabel() {
      if (!ui.label) return;
      ui.label.textContent = ready ? shortLabel() : "加载中…";
      if (ui.toggle) ui.toggle.title = "全局设置：" + shortLabel();
    }

    function setState(text) {
      if (ui.state) ui.state.textContent = text || "";
    }

    function fill(select, rows, kept) {
      select.textContent = "";
      rows.forEach(function (row) {
        var node = document.createElement("option");
        node.value = row.value;
        node.textContent = row.label;
        select.appendChild(node);
      });
      select.value = kept;
      if (select.value !== kept) select.value = "";
    }

    function renderStages() {
      var rows = [{ value: "", label: ALL_STAGE }].concat(options.stages.map(function (name) {
        return { value: name, label: name };
      }));
      fill(ui.stage, rows, draft.stage);
      draft.stage = ui.stage.value;
    }

    function renderSubjects() {
      var rows = [{ value: "", label: ALL_SUBJECT }].concat(options.subjects.map(function (item) {
        return { value: String(item.id), label: item.name };
      }));
      fill(ui.subject, rows, draft.subject_id);
      draft.subject_id = ui.subject.value;
    }

    function renderVersions() {
      var rows = [{ value: "", label: ALL_VERSION }].concat(options.versions.filter(function (version) {
        if (draft.subject_id && String(version.subject_id) !== draft.subject_id) return false;
        if (draft.stage && Array.isArray(version.stages) && version.stages.indexOf(draft.stage) === -1) return false;
        return true;
      }).map(function (version) {
        return { value: String(version.id), label: version.name };
      }));
      fill(ui.textbook, rows, draft.version_id);
      draft.version_id = ui.textbook.value;
    }

    /** 学段 / 学科一变就重拉版本清单；旧选中项不在新清单里时由 fill 自动落回“全部版本”。 */
    function reloadVersions() {
      var seq = ++versionSeq;
      var payload = {};
      if (draft.stage) payload.stage = draft.stage;
      if (draft.subject_id) payload.subject_id = Number(draft.subject_id);
      ui.textbook.disabled = true;
      setState("正在刷新教材版本…");
      call("dict.globals_get", payload).then(function (result) {
        if (seq !== versionSeq) return;
        options.versions = (result && result.versions) || [];
        rememberVersions(options.versions);
        renderVersions();
        ui.textbook.disabled = false;
        setState("");
      }, function (error) {
        if (seq !== versionSeq) return;
        ui.textbook.disabled = false;
        setState("教材版本刷新失败：" + error.message);
      });
    }

    function renderDraft() {
      renderStages();
      renderSubjects();
      renderVersions();
    }

    function closePanel(revert) {
      if (revert) draft = copy(current);
      panelOpen = false;
      ui.panel.hidden = true;
      ui.toggle.setAttribute("aria-expanded", "false");
    }

    function openPanel() {
      if (!ready) return;
      draft = copy(current);
      renderDraft();
      panelOpen = true;
      ui.panel.hidden = false;
      ui.toggle.setAttribute("aria-expanded", "true");
      ui.stage.focus();
      reloadVersions();
    }

    function onToggle() {
      if (panelOpen) {
        closePanel(true);
        ui.toggle.focus();
      } else {
        openPanel();
      }
    }

    function commit() {
      if (!ready) return;
      var payload = {
        stage: ui.stage.value,
        subject_id: ui.subject.value,
        version_id: ui.textbook.value
      };
      ui.confirm.disabled = true;
      setState("正在保存…");
      call("dict.globals_save", payload).then(function (result) {
        current = normalize(result && result.current ? result.current : payload);
        draft = copy(current);
        renderLabel();
        closePanel(false);
        setState("");
        dock("全局设置已生效：" + shortLabel());
      }, function (error) {
        setState("保存失败：" + error.message);
      }).then(function () {
        ui.confirm.disabled = false;
      });
    }

    function field(parent, text, id) {
      var box = el("label", "db-field");
      box.setAttribute("for", id);
      box.appendChild(el("span", "db-field-label", text));
      var select = document.createElement("select");
      select.className = "db-select";
      select.id = id;
      select.disabled = true;
      box.appendChild(select);
      parent.appendChild(box);
      return select;
    }

    function buildSkeleton() {
      root.textContent = "";
      var rail = el("div", "db-rail");

      var globals = el("section", "db-globals");
      var toggle = el("button", "db-globals-toggle");
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", "false");
      toggle.appendChild(el("span", "db-globals-icon", "⚙️"));
      var textBox = el("span", "db-globals-text");
      textBox.appendChild(el("span", "db-globals-title", "全局设置"));
      var label = el("span", "db-globals-label", "加载中…");
      textBox.appendChild(label);
      toggle.appendChild(textBox);
      toggle.appendChild(el("span", "db-globals-caret"));
      var panel = el("div", "db-globals-panel");
      panel.hidden = true;
      var stage = field(panel, "学段", "dbStage");
      var subject = field(panel, "学科", "dbSubject");
      var textbook = field(panel, "教材版本", "dbTextbook");
      var confirm = el("button", "db-globals-confirm", "确定");
      confirm.type = "button";
      confirm.disabled = true;
      panel.appendChild(confirm);
      var state = el("p", "db-dict-state");
      state.setAttribute("role", "status");
      state.setAttribute("aria-live", "polite");
      panel.appendChild(state);
      globals.appendChild(toggle);
      globals.appendChild(panel);

      var cats = el("section", "db-cats");
      cats.setAttribute("aria-label", "字典分类");
      cats.appendChild(el("p", "db-dict-state", "正在读取字典分类…"));

      rail.appendChild(globals);
      rail.appendChild(cats);
      root.appendChild(rail);

      ui = {
        toggle: toggle, label: label, panel: panel, state: state,
        stage: stage, subject: subject, textbook: textbook,
        confirm: confirm, cats: cats
      };

      toggle.addEventListener("click", onToggle);
      confirm.addEventListener("click", commit);
      stage.addEventListener("change", function () {
        draft.stage = stage.value;
        draft.version_id = textbook.value;
        reloadVersions();
      });
      subject.addEventListener("change", function () {
        draft.subject_id = subject.value;
        draft.version_id = textbook.value;
        reloadVersions();
      });
      textbook.addEventListener("change", function () {
        draft.version_id = textbook.value;
      });
      rail.addEventListener("keydown", function (event) {
        if (!panelOpen || event.key !== "Escape") return;
        event.preventDefault();
        closePanel(true);
        toggle.focus();
      });
    }

    function markCategory(key) {
      catButtons.forEach(function (entry) {
        entry.node.setAttribute("aria-pressed", entry.key === key ? "true" : "false");
      });
    }

    function openCategory(category, label) {
      call("dict.open", { category: category.key }).then(function (result) {
        var on = Boolean(result && result.active);
        markCategory(on ? category.key : "");
        dock(on
          ? "画布已原地切到「" + label + "」分类，具体字典在上方二级标签里。"
          : "已收起字典页，画布回到数据看板。");
      }, function (error) {
        dock("打开「" + label + "」分类失败：" + error.message);
      });
    }

    function renderCategories(categories) {
      catButtons = [];
      ui.cats.textContent = "";
      if (!Array.isArray(categories) || !categories.length) {
        ui.cats.appendChild(el("p", "db-dict-state", "字典目录为空，请先完成题库初始化。"));
        return;
      }
      categories.forEach(function (category) {
        var label = String(category.title || "").replace(/字典$/, "");
        var button = el("button", "db-cat-btn", label);
        button.type = "button";
        button.setAttribute("aria-pressed", "false");
        button.setAttribute("aria-label", "在画布打开「" + label + "」分类");
        if (category.desc) button.title = category.desc;
        button.addEventListener("click", function () { openCategory(category, label); });
        catButtons.push({ node: button, key: category.key });
        ui.cats.appendChild(button);
      });
    }

    function renderGlobals(result) {
      result = result || {};
      options = {
        stages: result.stages || [],
        subjects: result.subjects || [],
        versions: result.versions || []
      };
      knownVersions = [];
      rememberVersions(options.versions);
      current = normalize(result.current);
      draft = copy(current);
      ready = true;
      [ui.stage, ui.subject, ui.textbook].forEach(function (select) { select.disabled = false; });
      ui.confirm.disabled = false;
      renderDraft();
      renderLabel();
    }

    buildSkeleton();
    root.hidden = false;

    call("dict.catalog").then(function (result) {
      renderCategories(result && result.categories);
    }, function (error) {
      ui.cats.textContent = "";
      ui.cats.appendChild(el("p", "db-dict-state", "字典目录读取失败：" + error.message));
    });

    call("dict.globals_get").then(renderGlobals, function (error) {
      if (ui.label) ui.label.textContent = "读取失败";
      setState("全局设置读取失败：" + error.message);
    });
  }

  global.DbRail = { mount: mount };
})(window);
