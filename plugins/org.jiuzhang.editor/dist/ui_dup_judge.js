/**
 * ui_dup_judge.js —— 查重裁判台住在辅助栏的那一半（军令·查重三栏）。
 * 只看差异、唯一属性二选一、四件套决断；动作流转在 ui_dup_judge_flow.js，
 * 画布那一半在 ui_dup_compare.js，两边只经 `editor.dup_compare` 递话。 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var el = deps.el;
    var hostCall = deps.hostCall;
    var publish = deps.publish;
    var panelSay = deps.panelSay;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var openModal = deps.openModal;
    var closeModal = deps.closeModal;
    var poolPanel = deps.poolPanel;
    var dom = deps.dom;
    var root = dom.panelRoot;
    var compareEl = dom.panelPoolCompareEl;
    var secEl = dom.judgeSecEl;
    var identEl = dom.judgeIdentEl;
    var diffEl = dom.judgeDiffEl;
    var noteEl = dom.judgeNoteEl;
    var mergeEl = dom.judgeMergeEl;
    var solutionEl = dom.judgeSolutionEl;
    var separateEl = dom.judgeSeparateEl;
    var deleteEl = dom.judgeDeleteEl;
    var resolveEl = dom.judgeResolveEl;
    var exitEl = dom.judgeExitEl;
    var conflictModalEl = dom.judgeConflictModalEl;
    var conflictBodyEl = dom.judgeConflictBodyEl;
    var conflictWarnEl = dom.judgeConflictWarnEl;
    var conflictCancelEl = dom.judgeConflictCancelEl;
    var conflictOkEl = dom.judgeConflictOkEl;
    var delModalEl = dom.judgeDelModalEl;
    var delCancelEl = dom.judgeDelCancelEl;
    var delOkEl = dom.judgeDelOkEl;
    var active = false, canvasOpen = false, entry = null, resolutions = {}, flow = null, wired = false;

    function panel() { return poolPanel(); }

    function say(text, tone) {
      if (noteEl) {
        noteEl.textContent = text || "";
        noteEl.setAttribute("data-tone", tone || "info");
      }
    }

    function diff() {
      var value = entry && entry.meta_diff;
      return value && typeof value === "object" ? value : {
        multi: [], unique: [], conflicts: [], requires_resolution: []
      };
    }

    function needsResolution() {
      var list = diff().requires_resolution;
      return Array.isArray(list) ? list : [];
    }

    function lockedActions() {
      return entry && Array.isArray(entry.locked_actions) ? entry.locked_actions : [];
    }

    function unresolved() {
      return needsResolution().filter(function (field) {
        return !resolutions[field];
      });
    }

    function allResolved() {
      return unresolved().length === 0;
    }

    function chip(text, added) {
      return el("span", "ep-judge-chip" + (added ? " is-added" : ""), text);
    }

    function sourceLabel(source) {
      if (!source || typeof source !== "object") return "";
      var title = String(source.paper_title || "未命名原卷");
      var no = String(source.question_no || "");
      return no ? title + " · 第 " + no + " 题" : title;
    }

    function renderMulti(item) {
      var box = el("div", "ep-judge-item");
      var head = el("div", "ep-judge-field");
      head.appendChild(el("span", "", String(item.label || item.field || "")));
      box.appendChild(head);
      var union = Array.isArray(item.union) ? item.union : [];
      var added = Array.isArray(item.added) ? item.added : [];
      var chips = el("div", "ep-judge-chips");
      if (item.field === "source") {
        union.forEach(function (source) {
          var text = sourceLabel(source);
          var isAdded = added.some(function (one) {
            return sourceLabel(one) === text;
          });
          chips.appendChild(chip(text, isAdded));
        });
      } else {
        union.forEach(function (value) {
          chips.appendChild(chip(String(value), added.indexOf(value) >= 0));
        });
      }
      if (!union.length) chips.appendChild(el("span", "ep-judge-line", "两边都没有"));
      box.appendChild(chips);
      if (added.length) {
        box.appendChild(el("p", "ep-judge-line", "合并后自动并入：" + added.map(function (one) {
          return item.field === "source" ? sourceLabel(one) : String(one);
        }).join("、")));
      }
      return box;
    }

    function renderUnique(item) {
      var box = el("div", "ep-judge-item");
      var head = el("div", "ep-judge-field");
      head.appendChild(el("span", "", String(item.label || item.field || "")));
      if (item.conflict) head.appendChild(el("span", "ep-judge-badge", "冲突 · 必须二选一"));
      box.appendChild(head);
      var mainText = item.field === "type" ? (item.main_label || item.main) : item.main;
      var incomingText = item.field === "type" ? (item.incoming_label || item.incoming) : item.incoming;
      var line = el("p", "ep-judge-line");
      line.appendChild(document.createTextNode("主库："));
      line.appendChild(el("b", "", String(mainText || "没写")));
      line.appendChild(document.createTextNode(" ／ 新题："));
      line.appendChild(el("b", "", String(incomingText || "没写")));
      box.appendChild(line);
      if (item.conflict) {
        var picked = resolutions[item.field] || "";
        box.appendChild(el("p", "ep-judge-line", picked
          ? ("已选：" + (picked === "main" ? "保留主库" : "采用新题"))
          : "还没选；【合并】在选定之前保持锁死。"));
      }
      return box;
    }

    function paintActions() {
      var busyNow = Boolean(flow && flow.busyNow());
      var needs = needsResolution();
      var locks = lockedActions();
      var mergeLocked = locks.indexOf("merge_metadata") >= 0
        || (needs.length > 0 && !allResolved());
      var pairs = [
        [mergeEl, mergeLocked, mergeLocked ? "先解决题型/难度冲突，或两边答案不同" : ""],
        [solutionEl, locks.indexOf("add_solution") >= 0, "两边答案明确不同，不能并解析"],
        [separateEl, false, ""],
        [deleteEl, false, ""]
      ];
      pairs.forEach(function (pair) {
        var node = pair[0];
        if (!node) return;
        node.disabled = busyNow || !entry || pair[1];
        node.setAttribute("aria-disabled", node.disabled ? "true" : "false");
        node.title = pair[2] || "";
      });
      if (resolveEl) resolveEl.hidden = !needs.length;
    }

    function paint() {
      if (!entry) return;
      if (identEl) {
        var bits = [];
        if (entry.label) bits.push(String(entry.label) + " " + (Number(entry.percent) || 0) + "%");
        if (entry.item_id) bits.push("池内 " + entry.item_id);
        if (entry.main_id) bits.push("主库 " + entry.main_id);
        identEl.textContent = bits.join(" · ");
      }
      if (diffEl) {
        diffEl.textContent = "";
        var data = diff();
        (data.multi || []).forEach(function (item) { diffEl.appendChild(renderMulti(item)); });
        (data.unique || []).forEach(function (item) { diffEl.appendChild(renderUnique(item)); });
        if (!(data.multi || []).length && !(data.unique || []).length) {
          diffEl.appendChild(el("p", "ep-judge-empty", "两边元数据没有差异，可以直接裁决。"));
        }
      }
      paintActions();
    }

    function showJudge() {
      if (!root || !secEl) return;
      secEl.hidden = false;
      root.setAttribute("data-judge", "on");
    }

    function hideJudge() {
      if (!root || !secEl) return;
      secEl.hidden = true;
      root.removeAttribute("data-judge");
    }

    function push(phase) {
      if (!publish || !entry) return;
      publish("editor.dup_compare", {
        pluginId: coreState.PLUGIN_ID, from: "panel", phase: phase,
        entry: entry
      });
    }

    function enter(detail) {
      if (!detail || typeof detail !== "object") return;
      entry = detail;
      resolutions = {};
      active = true;
      panel().setCompareActive(true);
      showJudge();
      paint();
      push(canvasOpen ? "update" : "open");
      canvasOpen = true;
      if (needsResolution().length) {
        window.setTimeout(function () {
          if (active && entry && needsResolution().length) openConflict();
        }, 340);
      }
    }

    function openCompare() {
      var rows = panel().entries();
      if (!rows.length) {
        dockWarn("重题池里还没有可对比的题。", null);
        return;
      }
      active = true;
      panel().setCompareActive(true);
      var selected = panel().selected();
      if (selected) enter(selected);
      else panel().select(rows[0]);
    }

    function exit(options) {
      var opts = options || {};
      if (!active) return;
      active = false;
      canvasOpen = false;
      entry = null;
      resolutions = {};
      hideJudge();
      panel().setCompareActive(false);
      if (opts.notify !== false) {
        publish("editor.dup_compare", {
          pluginId: coreState.PLUGIN_ID, from: "panel", phase: "closed"
        });
      }
      if (!opts.quiet) panelSay("已退出查重对比，回到当前题的审核。", "info");
    }

    function onCanvasClosed() {
      if (!active) return;
      active = false;
      canvasOpen = false;
      entry = null;
      resolutions = {};
      hideJudge();
      panel().setCompareActive(false);
    }

    function onSelected(detail) {
      if (!active) return;
      if (!detail || typeof detail !== "object") return;
      enter(detail);
    }

    function onPoolState(count) {
      if (compareEl) {
        compareEl.hidden = count <= 0;
        compareEl.disabled = count <= 0;
      }
      if (active && count <= 0) exit({ quiet: true });
    }

    // ---------- 唯一属性二选一 ----------

    function openConflict() {
      var items = (diff().unique || []).filter(function (item) { return item.conflict; });
      if (!items.length) return;
      if (conflictBodyEl) {
        conflictBodyEl.textContent = "";
        items.forEach(function (item) {
          var box = el("div", "ep-judge-choice");
          box.appendChild(el("b", "", String(item.label || item.field)));
          [["main", "保留主库：" + (item.field === "type" ? (item.main_label || item.main) : item.main)],
           ["incoming", "采用新题：" + (item.field === "type" ? (item.incoming_label || item.incoming) : item.incoming)]]
            .forEach(function (pair) {
              var label = el("label", "");
              var radio = document.createElement("input");
              radio.type = "radio";
              radio.name = "epJudge-" + item.field;
              radio.value = pair[0];
              radio.setAttribute("data-field", item.field);
              radio.addEventListener("change", updateConflictOk);
              label.appendChild(radio);
              label.appendChild(document.createTextNode(String(pair[1] || "")));
              box.appendChild(label);
            });
          conflictBodyEl.appendChild(box);
        });
      }
      if (conflictWarnEl) conflictWarnEl.hidden = true;
      if (conflictOkEl) {
        conflictOkEl.disabled = true;
        conflictOkEl.setAttribute("aria-disabled", "true");
      }
      openModal(conflictModalEl);
    }

    function selectedResolutions() {
      var picked = {};
      if (!conflictBodyEl) return picked;
      Array.prototype.forEach.call(conflictBodyEl.querySelectorAll("input[type=radio]:checked"),
        function (radio) {
          picked[radio.getAttribute("data-field")] = radio.value;
        });
      return picked;
    }

    function updateConflictOk() {
      var fields = needsResolution().filter(function (field) { return field !== "answer"; });
      var picked = selectedResolutions();
      var ready = fields.every(function (field) { return Boolean(picked[field]); });
      if (conflictOkEl) {
        conflictOkEl.disabled = !ready;
        conflictOkEl.setAttribute("aria-disabled", ready ? "false" : "true");
      }
      if (conflictWarnEl) conflictWarnEl.hidden = ready;
    }

    function confirmConflict() {
      var picked = selectedResolutions();
      var missing = needsResolution().filter(function (field) { return !picked[field]; });
      if (missing.length) {
        updateConflictOk();
        return;
      }
      resolutions = picked;
      closeModal(conflictModalEl);
      paint();
      say("已选好冲突项，点【合并】写入主库。", "info");
    }

    function cancelConflict() {
      closeModal(conflictModalEl);
      say("还没选冲突项，【合并】保持锁死。", "warn");
    }

    // ---------- 四件套与自动流转：动作层在 ui_dup_judge_flow.js ----------

    flow = window.JzoEditorDupJudgeFlow.create({
      dom: dom,
      hostCall: hostCall,
      dock: deps.dock,
      dockWarn: dockWarn,
      errorDetail: errorDetail,
      openModal: openModal,
      closeModal: closeModal,
      getEntry: function () { return entry; },
      getResolutions: function () { return resolutions; },
      needsResolution: needsResolution,
      allResolved: allResolved,
      lockedActions: lockedActions,
      openConflict: openConflict,
      say: say,
      paintActions: paintActions,
      exit: exit,
      panel: panel
    });

    function wire() {
      if (wired) return;
      wired = true;
      if (compareEl) compareEl.addEventListener("click", openCompare);
      if (mergeEl) mergeEl.addEventListener("click", function () { flow.act("merge_metadata"); });
      if (solutionEl) solutionEl.addEventListener("click", function () { flow.act("add_solution"); });
      if (separateEl) separateEl.addEventListener("click", function () { flow.act("keep_separate"); });
      if (deleteEl) deleteEl.addEventListener("click", function () { flow.act("delete"); });
      if (resolveEl) resolveEl.addEventListener("click", openConflict);
      if (exitEl) exitEl.addEventListener("click", function () { exit({}); });
      if (conflictCancelEl) conflictCancelEl.addEventListener("click", cancelConflict);
      if (conflictOkEl) conflictOkEl.addEventListener("click", confirmConflict);
      if (delCancelEl) delCancelEl.addEventListener("click", function () { closeModal(delModalEl); });
      if (delOkEl) delOkEl.addEventListener("click", function () { flow.confirmDelete(); });
      panel().setSelectionListener(onSelected);
      panel().setPoolStateListener(onPoolState);
    }

    return {
      exit: exit,
      onCanvasClosed: onCanvasClosed,
      openCompare: openCompare,
      wire: wire,
    };
  }

  global.JzoEditorDupJudge = { create: create };
})(window);
