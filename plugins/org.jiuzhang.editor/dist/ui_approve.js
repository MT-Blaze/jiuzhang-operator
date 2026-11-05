/**
 * ui_approve.js —— plugin.js 的「台账」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 *
 * 军令 #31 的查重拦截分两帧落地，这里只管**辅助栏这一半**：
 *
 * - 查（`pending.duplicate`）与判（指纹 / 相似度 / 答案是否一致）都在底座，
 *   插件一个字节的判据都不自己造；
 * - 辅助栏只报「有」：底部一行红字 + 一颗【查看主库原题】。它按军令 #23
 *   绝不放渲染预览，所以两侧的渲染对比必须交给画布那帧去画；
 * - 三种裁决里「覆盖」「合并为解析二」由画布那帧发 `pending.approve`（带 action），
 *   「放弃」是纯本地动作：主库一个字节都不碰，题留在池子里等改。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var PLUGIN_ID = coreState.PLUGIN_ID;
    var closeModal = deps.closeModal;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var explainHostError = deps.explainHostError;
    var hostCall = deps.hostCall;
    var openModal = deps.openModal;
    var panel = coreState.panel;
    var panelItem = deps.panelItem;
    var panelSay = deps.panelSay;
    var parseExamSource = deps.parseExamSource;
    var publish = deps.publish;
    var questionFromParsed = deps.questionFromParsed;
    var readForm = deps.readForm;
    var saveItem = deps.saveItem;
    var state = coreState.state;
    var syncSchoolLock = deps.syncSchoolLock;
    var validateForSave = deps.validateForSave;
    var batchNoteEl = deps.dom.batchNoteEl;
    var delModalEl = deps.dom.delModalEl;
    var dupBoxEl = deps.dom.dupBoxEl;
    var dupWarnEl = deps.dom.dupWarnEl;
    var panelApproveEl = deps.dom.panelApproveEl;
    var poolEl = deps.dom.poolEl;

    // 最近一次命中的完整报告：切换题目、清红字时一起作废。
    var dupReport = null;

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

  // ---------- 查重拦截：红字与【查看主库原题】（军令 #31） ----------
  /** 红字说什么，由底座给的那份报告说了算，插件不自己编。 */
  function dupWarningText(report) {
    var blocked = Boolean(report && report.answer) && report.answer.same === false;
    if (blocked) return "主库已存在高度相似题目，且两边答案不同：只能放弃存入。";
    if (report && report.level === "high") return "主库已存在高度相似题目";
    return "主库已存在高度相似题目";
  }

  function showDupWarning(report) {
    dupReport = report || null;
    if (dupBoxEl) dupBoxEl.hidden = false;
    if (dupWarnEl) {
      var text = dupWarningText(report);
      dupWarnEl.textContent = text;
      dupWarnEl.title = text;
    }
    syncDupActions();
  }

  /** 熄红字并让画布把对比浮层一起关掉：题换了、办完了、放弃了，都走这一个口子。 */
  function clearDupWarning() {
    var had = Boolean(dupReport);
    dupReport = null;
    if (dupBoxEl) dupBoxEl.hidden = true;
    if (dupWarnEl) {
      dupWarnEl.textContent = "";
      dupWarnEl.title = "";
    }
    if (had) notifyCanvas("closed");
  }

  /** 当前题还值不值得信这一份报告：题换了就不许把旧命中贴到新题上。 */
  function stillCurrent(pendingId) {
    var item = panelItem();
    var current = item && item.pendingId ? String(item.pendingId) : "";
    return Boolean(current) && current === String(pendingId || "");
  }

  /** 后台查重：命中就把红字亮起来并把报告留着，没命中就熄掉。 */
  function precheck(item) {
    var pendingId = item && item.pendingId ? String(item.pendingId) : "";
    if (!pendingId) {
      clearDupWarning();
      return Promise.resolve(null);
    }
    return hostCall("pending.duplicate", { pending_id: pendingId }).then(function (report) {
      if (!stillCurrent(pendingId)) return null;
      if (!report || !report.hit) {
        clearDupWarning();
        return null;
      }
      showDupWarning(report);
      // 只点灯不开窗：后台查重一命中，画布那盏红灯就该亮，不用等老师点任何按钮。
      notifyCanvas("notice", report);
      return report;
    }, function () {
      // 查重失败不该挡住老师继续审题：静默熄红字，把库留给入库那一步兜。
      if (stillCurrent(pendingId)) clearDupWarning();
      return null;
    });
  }

  /** 给画布那帧递话：开窗 / 只点灯 / 收窗，三个口径都从这里出。 */
  function notifyCanvas(phase, report) {
    if (!publish) return;
    publish("editor.dup_review", {
      pluginId: PLUGIN_ID,
      from: "panel",
      phase: phase,
      report: report || null
    });
  }

  /** 【查看主库原题】：报告递去画布，由那一帧弹左右渲染对比浮层。 */
  function inspectDup() {
    if (!dupReport) return;
    notifyCanvas("open", dupReport);
  }

  /**
   * 三个裁决动作（军令 #31）：覆盖 / 放弃 / 合并为解析二。
   *
   * 按钮住在辅助栏，是因为画布里一颗按钮都不许有（军令 #23）：画布只负责把两侧
   * **渲染**摆出来给老师看，拍板的是这里。答案不同时**两颗写库钮都锁死**——
   * 覆盖等于拿错答案盖掉对答案，合并等于把两套矛盾的解法并进一道题。
   */
  function doDupAction(action) {
    var item = panelItem();
    var report = dupReport;
    if (!report || !item || !item.pendingId) return;
    if (action === "abandon") {
      // 放弃：主库一个字节都不碰，题留在池子里等老师改。
      clearDupWarning();
      panelSay("已放弃存入，这一题还留在待审池里。", "warn", "abandoned");
      batchNote("已放弃存入，题还在池子里。", "partial");
      return;
    }
    if (panel.saving) return;
    var blocked = Boolean(report.answer) && report.answer.same === false;
    if (blocked) {
      panelSay("两边答案不同：覆盖与合并都已锁死，只能放弃存入。", "error", "blocked");
      batchNote("答案不同，这一条只能放弃。", "failed");
      return;
    }
    panel.saving = true;
    approveBusy(true);
    var label = action === "merge_solution" ? "正在合并为解析二…" : "正在覆盖主库…";
    panelSay(label, "info", "saving");
    batchNote(label, "running");
    hostCall("pending.approve", { pending_id: item.pendingId, action: action })
      .then(function (result) {
        panel.saving = false;
        approveBusy(false);
        var questionId = (result && result.question_id) || report.existing_id || "";
        var done = action === "merge_solution"
          ? "已合并为主库那题的解析二：" : "已覆盖主库那一条：";
        panel.selection.status = "stored";
        panel.selection.dirty = false;
        clearDupWarning();
        panelSay(done + questionId, "ok", "stored");
        batchNote(done + questionId, "done");
        dock(done + questionId);
      }, function (error) {
        panel.saving = false;
        approveBusy(false);
        if (error && error.answer_mismatch) {
          // 后端这一关也拦下了：把两边的答案原样亮出来，两颗写库钮继续锁着。
          if (report.answer) report.answer.same = false;
          if (dupWarnEl) dupWarnEl.textContent = "两边答案不同，底座已拒绝这次写入：只能放弃存入。";
          panelSay("两边答案不同，底座已拒绝这次写入：只能放弃存入。", "error", "blocked");
          batchNote("答案不同，只能放弃。", "failed");
          return;
        }
        panelSay("写入主库失败：" + ((error && error.message) || "未知原因"), "error", "failed");
        batchNote("写入主库失败。", "failed");
        dockWarn("写入主库失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      });
  }

  /** 覆盖与合并两颗钮在答案不同时必须锁死；查重还在路上也锁住——
   *  那一刻的命中随时会被新结果替换，点下去只会被 doDupAction 静默吞掉。
   *  界面与判据同一处说了算。 */
  function syncDupActions() {
    var blocked = Boolean(dupReport && dupReport.answer) && dupReport.answer.same === false;
    var busy = Boolean(panel.saving);
    [deps.dom.dupOverwriteEl, deps.dom.dupMergeEl].forEach(function (node) {
      if (!node) return;
      node.disabled = blocked || busy;
      node.setAttribute("aria-disabled", node.disabled ? "true" : "false");
    });
    if (deps.dom.dupAbandonEl) {
      deps.dom.dupAbandonEl.disabled = false;
      deps.dom.dupAbandonEl.setAttribute("aria-disabled", "false");
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
    // 查重一开工，裁决钮跟着锁（panel.saving 由调用方先置位）。
    syncDupActions();
    syncSchoolLock();
  }

  /** 真入库：写完把红字熄掉，把池子里的账重算一遍。 */
  function approveNow(item) {
    batchNote("正在存入主库…", "running");
    return hostCall("pending.approve", { pending_id: item.pendingId }).then(function (result) {
      panel.saving = false;
      approveBusy(false);
      clearDupWarning();
      panel.selection.status = "stored";
      panel.selection.dirty = false;
      panelSay("已存入主库：" + (result.question_id || "") + "。", "ok", "created");
      batchNote("已存入主库（" + (result.question_id || "") + "）。", "done");
      dock("中转站里的一道题已存入主库：" + (result.question_id || ""));
    }, function (error) {
      panel.saving = false;
      approveBusy(false);
      if (error && error.duplicate) {
        // 后端这一关先拦下来了：补一次查重，把完整报告取回来再让老师裁决。
        batchNote("主库已存在高度相似题目，等老师拍板。", "partial");
        panelSay(error.answer_mismatch
          ? "两边答案不同，这一条只能放弃存入。" : "主库已存在高度相似题目，请看对比后再决定。",
        "warn", "duplicate");
        return precheck(item).then(function (report) {
          if (report) inspectDup();
        });
      }
      panelSay(explainHostError(error), "error", "failed");
      batchNote("存入主库失败：" + ((error && error.message) || "未知原因"), "failed");
      dockWarn("存入主库失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
    });
  }

  /**
   * 【存入主库】：先查重，命中就亮红字、开对比窗，让老师选覆盖 / 放弃 / 合并为解析二；
   * 没命中才真写库。**绝不**替老师默认选「覆盖」。
   */
  function onApprove() {
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
    panelSay("正在查重…", "info", "checking");
    batchNote("正在查重…", "running");
    precheck(item).then(function (report) {
      if (!item.pendingId) return null;
      if (report) {
        // 命中：不写库，先把两侧渲染摆出来让老师裁决。
        panel.saving = false;
        approveBusy(false);
        panelSay("主库已存在高度相似题目，请看对比后再决定。", "warn", "duplicate");
        batchNote("主库已存在高度相似题目，等老师拍板。", "partial");
        inspectDup();
        return null;
      }
      return approveNow(item);
    }).catch(function (error) {
      panel.saving = false;
      approveBusy(false);
      panelSay("存入主库失败：" + ((error && error.message) || "未知原因"), "error", "failed");
      batchNote("存入主库失败。", "failed");
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
      clearDupWarning();
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
      clearDupWarning: clearDupWarning,
      documentFor: documentFor,
      doDupAction: doDupAction,
      dupReport: function () { return dupReport; },
      inspectDup: inspectDup,
      onApprove: onApprove,
      onDelete: onDelete,
      onDeleteConfirm: onDeleteConfirm,
      onStash: onStash,
      panelPoolCounts: panelPoolCounts,
      poolCounts: poolCounts,
      precheck: precheck,
      renderPool: renderPool,
      syncDupActions: syncDupActions,
    };
  }

  global.JzoEditorApprove = { create: create };
})(window);
