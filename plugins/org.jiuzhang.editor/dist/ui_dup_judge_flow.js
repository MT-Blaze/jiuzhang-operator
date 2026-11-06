/**
 * ui_dup_judge_flow.js —— 裁判台的四件套与自动流转（军令·查重三栏）。
 *
 * 从 ui_dup_judge.js 拆出来的动作层：只负责发令、错误话术与「跳下一道」。
 * 差异渲染与二选一弹窗仍在主文件；两边共用一组只读 getter，状态只有一份。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var hostCall = deps.hostCall;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var openModal = deps.openModal;
    var closeModal = deps.closeModal;
    var dom = deps.dom;
    var getEntry = deps.getEntry;
    var getResolutions = deps.getResolutions;
    var needsResolution = deps.needsResolution;
    var allResolved = deps.allResolved;
    var lockedActions = deps.lockedActions;
    var openConflict = deps.openConflict;
    var say = deps.say;
    var paintActions = deps.paintActions;
    var exit = deps.exit;
    var panel = deps.panel;
    var flushSource = deps.flushSource;
    var delModalEl = dom.judgeDelModalEl;
    var delTextEl = dom.judgeDelTextEl;
    var delOkEl = dom.judgeDelOkEl;

    var busy = false;

    var LABELS = {
      merge_metadata: "合并", add_solution: "新增解析",
      keep_separate: "不重复", delete: "删除"
    };

    function labelOf(action) { return LABELS[action] || action; }

    function advance(index) {
      return panel().refresh().then(function (rows) {
        if (!rows.length) {
          say("池里已经没有待裁决的题了。", "ok");
          exit({ quiet: true });
          return;
        }
        var next = rows[Math.min(Math.max(index, 0), rows.length - 1)];
        return panel().select(next);
      });
    }

    function run(action) {
      var entry = getEntry();
      if (!entry || busy) return;
      var oldId = String(entry.pool_id || "");
      var rows = panel().entries();
      var index = rows.findIndex(function (row) { return String(row.pool_id) === oldId; });
      busy = true;
      paintActions();
      say("正在保存源码并执行「" + labelOf(action) + "」…", "info");
      // 裁决永远拿 textarea 的当下值：先强保存，存不进去就不动库。
      var ready = flushSource ? flushSource() : Promise.resolve({ ok: true });
      Promise.resolve(ready).then(function (saved) {
        if (saved && saved.ok === false) {
          busy = false;
          paintActions();
          say(saved.message || "源码没存回池，先修正再裁决。", "error");
          return;
        }
        say("正在执行「" + labelOf(action) + "」…", "info");
        return send(action, oldId, index);
      }, function (error) {
        busy = false;
        paintActions();
        say("源码没存回池：" + ((error && error.message) || "未知原因"), "error");
        dockWarn("裁决前保存源码失败", errorDetail(error));
      });
    }

    function send(action, oldId, index) {
      var payload = { pool_id: oldId, action: action };
      if (action === "merge_metadata" && needsResolution().length) {
        payload.resolutions = getResolutions();
      }
      return hostCall("pending.pool_act", payload).then(function (result) {
        busy = false;
        if (result && result.kept_in_pool) {
          var missing = (result.missing || []).join("、");
          say("还缺：" + missing + "。这一条仍留在池里。", "warn");
          panel().refresh();
          return;
        }
        say("已「" + labelOf(action) + "」，自动跳下一道。", "ok");
        if (dock) dock("重题池：" + labelOf(action) + "（" + oldId + "）");
        advance(index);
      }, function (error) {
        busy = false;
        paintActions();
        var code = String((error && (error.detailCode || error.code)) || "");
        if (code === "meta_conflict") {
          say("题型/难度还没二选一，合并被底座拒绝。", "warn");
          openConflict();
        } else if (code === "answer_mismatch") {
          say("两边答案不同，只能选「不重复」或「删除」。", "error");
        } else if (error && error.status === 404) {
          say("这一条已经不在池里了，跳到下一道。", "warn");
          advance(index);
        } else {
          say("动作没做成：" + ((error && error.message) || "未知原因"), "error");
          dockWarn("查重裁决失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
          panel().refresh();
        }
      });
    }

    function act(action) {
      var entry = getEntry();
      if (!entry || busy) return;
      if (action === "merge_metadata") {
        if (lockedActions().indexOf("merge_metadata") >= 0) {
          say("两边答案不同，合并被底座锁死。", "error");
          return;
        }
        if (needsResolution().length && !allResolved()) {
          openConflict();
          return;
        }
      }
      if (action === "delete") {
        if (delTextEl) {
          delTextEl.textContent = "删掉池里这一条（" + String(entry.item_id || "")
            + "）与它的成品图；主库原题一个字节都不碰，删完自动跳到下一道。";
        }
        openModal(delModalEl);
        return;
      }
      run(action);
    }

    function confirmDelete() {
      closeModal(delModalEl);
      run("delete");
    }

    function busyNow() { return busy; }

    return {
      act: act,
      busyNow: busyNow,
      confirmDelete: confirmDelete,
      labelOf: labelOf,
      run: run,
    };
  }

  global.JzoEditorDupJudgeFlow = { create: create };
})(window);
