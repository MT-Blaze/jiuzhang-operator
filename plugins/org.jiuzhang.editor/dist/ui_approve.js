/**
 * ui_approve.js —— plugin.js 的「台账」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var closeModal = deps.closeModal;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var explainHostError = deps.explainHostError;
    var hostCall = deps.hostCall;
    var openDupModal = deps.openDupModal;
    var openModal = deps.openModal;
    var panel = coreState.panel;
    var panelItem = deps.panelItem;
    var panelSay = deps.panelSay;
    var parseExamSource = deps.parseExamSource;
    var questionFromParsed = deps.questionFromParsed;
    var readForm = deps.readForm;
    var saveItem = deps.saveItem;
    var state = coreState.state;
    var syncSchoolLock = deps.syncSchoolLock;
    var validateForSave = deps.validateForSave;
    var batchNoteEl = deps.dom.batchNoteEl;
    var delModalEl = deps.dom.delModalEl;
    var dupModalEl = deps.dom.dupModalEl;
    var panelApproveEl = deps.dom.panelApproveEl;
    var poolEl = deps.dom.poolEl;

  // ---------- 台账：辅助栏底边那一行只报数，审核动作在上面那三颗钮里，这里不再带按钮。 ----------
  /** 画布侧的真身：整份工作清单都在这儿，池的账只能从这里算。 */
  function poolCounts() {
    var fresh = 0, stored = 0, dirty = 0, errored = 0;
    state.items.forEach(function (item) {
      if (item.status === "stored") stored += 1;
      else fresh += 1;
      if (item.dirty) dirty += 1;
      if (Number(item.errorCount || 0) > 0) errored += 1;
    });
    return { fresh: fresh, stored: stored, dirty: dirty, errored: errored };
  }

  /** 面板侧的账：随选区一起从画布过来，画布没开口子之前一律报零。 */
  function panelPoolCounts() {
    var pool = panel.selection && panel.selection.pool;
    if (!pool || typeof pool !== "object") return { fresh: 0, stored: 0, dirty: 0, errored: 0 };
    return {
      fresh: Number(pool.fresh) || 0, stored: Number(pool.stored) || 0,
      dirty: Number(pool.dirty) || 0, errored: Number(pool.errored) || 0
    };
  }

  function batchNote(text, phase) {
    if (!batchNoteEl) return;
    batchNoteEl.textContent = text;
    // 辅助栏窄，话术只许单行省略（契约如此）；完整文案挂 title，悬停能看全。
    batchNoteEl.title = text;
    batchNoteEl.setAttribute("data-batch", phase || "idle");
  }

  /** 台账：辅助栏底边那一行只报数，审核动作在上面那三颗钮里，这里不再带按钮。 */
  function renderPool() {
    var counts = state.slot === "stage.center" ? poolCounts() : panelPoolCounts();
    if (poolEl) {
      // 军令 #29：底段只留一行灰字「待入库：N · 已入库：M」；脏与缺件只在真发生时补上，
      // 平时这一行始终是两段，窄栏里也不会被挤成三行。
      var parts = ["待入库：" + counts.fresh, "已入库：" + counts.stored];
      if (counts.dirty) parts.push("未保存：" + counts.dirty);
      if (counts.errored) parts.push("缺件：" + counts.errored);
      poolEl.textContent = parts.join(" · ");
      poolEl.setAttribute("data-new", String(counts.fresh));
      poolEl.setAttribute("data-stored", String(counts.stored));
      poolEl.setAttribute("data-dirty", String(counts.dirty));
      poolEl.setAttribute("data-errored", String(counts.errored));
    }
  }

  // ---------- 审核三钮：存入主库 / 存为待审 / 彻底删除 ----------
  /** 当前题 → 契约里的题目文档（源码解析 + 表单元数据），顺带把该说的话说了。 */
  function documentFor(item, meta) {
    var parsed = parseExamSource(item.source);
    var doc = questionFromParsed(item, parsed, meta || {});
    return { doc: doc, parsed: parsed, problems: validateForSave(doc, parsed, meta || {}) };
  }

  function approveBusy(busy) {
    panel.approveBusy = Boolean(busy);
    if (panelApproveEl) {
      panelApproveEl.setAttribute("aria-busy", busy ? "true" : "false");
    }
    syncSchoolLock();
  }

  /**
   * 【存入主库】：中转站里的题由底座落进主库，p_ 号段换成 q_ 号段，配图搬进 uploads。
   * 主库已有同题时底座回 409，原样抛给弹窗——底座只如实报出「哪一道、差在哪儿」，
   * 覆盖与否由老师拍板，插件不替老师做主。
   */
  function onApprove(force) {
    var item = panelItem();
    if (!item) {
      panelSay("辅助栏还没收到当前题的源码，等画布发一次选区。", "warn", "idle");
      return;
    }
    if (panel.saving) return;
    var entry = readForm();
    panel.currentEntry = entry;
    panel.meta[item.key] = entry;
    if (!item.pendingId) {
      // 题库里的题直接改：走 bank.update，不经过中转站。
      panel.saving = true;
      approveBusy(true);
      panelSay("正在写入题库…", "info", "saving");
      saveItem(item, entry, "save").then(function (result) {
        panel.selection.status = "stored";
        panel.selection.dirty = false;
        panelSay("已更新题目 " + result.question_id + "。", "ok", "updated");
      }, function (error) {
        panelSay(explainHostError(error), "error", "failed");
        dockWarn("存入主库失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      }).then(function () {
        panel.saving = false;
        approveBusy(false);
      });
      return;
    }
    panel.saving = true;
    approveBusy(true);
    panelSay("正在存入主库…", "info", "saving");
    batchNote("正在存入主库…", "running");
    hostCall("pending.approve", { pending_id: item.pendingId, force: force === true })
      .then(function (result) {
        panel.saving = false;
        approveBusy(false);
        closeModal(dupModalEl);
        panel.selection.status = "stored";
        panel.selection.dirty = false;
        panelSay("已存入主库：" + (result.question_id || "") + "。", "ok", "created");
        batchNote("已存入主库（" + (result.question_id || "") + "）。", "done");
        dock("中转站里的一道题已存入主库：" + (result.question_id || ""));
      }, function (error) {
        panel.saving = false;
        approveBusy(false);
        if (error && error.duplicate) {
          batchNote("主库已有该题，等老师拍板。", "partial");
          openDupModal(item, error);
          return;
        }
        panelSay(explainHostError(error), "error", "failed");
        batchNote("存入主库失败：" + ((error && error.message) || "未知原因"), "failed");
        dockWarn("存入主库失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      });
  }

  /** 【存为待审】：把这一题写回中转池。带 pending_id 就是原地更新，池子里不会多出一道重影。 */
  function onStash() {
    var item = panelItem();
    if (!item) {
      panelSay("辅助栏还没收到当前题的源码，等画布发一次选区。", "warn", "idle");
      return;
    }
    if (panel.saving) return;
    var entry = readForm();
    panel.currentEntry = entry;
    panel.meta[item.key] = entry;
    var built = documentFor(item, entry);
    if (built.problems.length) {
      panelSay("这一题还存不进去：" + built.problems.slice(0, 3).join("；"), "warn", "invalid");
      return;
    }
    var payload = { questions: [{ pending_id: item.pendingId || "", question: built.doc }] };
    if (item.batchId) payload.batch_id = item.batchId;
    panel.saving = true;
    panelSay("正在存进中转站…", "info", "saving");
    batchNote("正在存进中转站…", "running");
    hostCall("pending.save_draft", payload).then(function (result) {
      panel.saving = false;
      var ids = (result && Array.isArray(result.saved_ids)) ? result.saved_ids : [];
      panelSay("已存为待审（池子编号 " + (item.pendingId || ids[0] || "—") + "）。", "ok", "stashed");
      batchNote("已存为待审（池子编号 " + (item.pendingId || ids[0] || "—") + "）。", "done");
      dock("一道题已存进中转站（待审核池）。");
    }, function (error) {
      panel.saving = false;
      panelSay("存为待审失败：" + ((error && error.message) || "未知原因"), "error", "failed");
      batchNote("存为待审失败。", "failed");
      dockWarn("存为待审失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
    });
  }

  /** 【彻底删除】：这一道题连同它的配图从中转站消失，主库一个字节都不碰。 */
  function onDelete() {
    var item = panelItem();
    if (!item || !item.pendingId) {
      panelSay("这一题不在待审核池里，池子删不了它——题库里的题请回题库删。", "warn", "idle");
      return;
    }
    panel.pending = item;
    openModal(delModalEl);
  }

  function onDeleteConfirm() {
    var item = panel.pending;
    closeModal(delModalEl);
    if (!item) return;
    hostCall("pending.delete", { pending_id: item.pendingId }).then(function () {
      panelSay("这一题已从中转站彻底删除。", "ok", "deleted");
      batchNote("这一题已从中转站彻底删除。", "done");
      dock("一道题已从中转站彻底删除。");
    }, function (error) {
      panelSay("删不掉：" + ((error && error.message) || "未知原因"), "error", "failed");
      batchNote("彻底删除失败。", "failed");
      dockWarn("彻底删除失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
    });
  }

    return {
      approveBusy: approveBusy,
      batchNote: batchNote,
      documentFor: documentFor,
      onApprove: onApprove,
      onDelete: onDelete,
      onDeleteConfirm: onDeleteConfirm,
      onStash: onStash,
      panelPoolCounts: panelPoolCounts,
      poolCounts: poolCounts,
      renderPool: renderPool,
    };
  }

  global.JzoEditorApprove = { create: create };
})(window);
