/**
 * ui_batches.js —— plugin.js 的「载入真题」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var COMMAND_QUESTION_ID_RE = coreState.COMMAND_QUESTION_ID_RE;
    var DEV_FIXTURES = deps.DEV_FIXTURES;
    var PLUGIN_ID = coreState.PLUGIN_ID;
    var batchListEl = deps.dom.batchListEl;
    var batchNoEl = deps.dom.batchNoEl;
    var batchStatEl = deps.dom.batchStatEl;
    var batchesEl = deps.dom.batchesEl;
    var batchesEmptyEl = deps.dom.batchesEmptyEl;
    var buildExamSource = deps.buildExamSource;
    var colsEl = deps.dom.colsEl;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var el = deps.el;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var loadMetaDraft = deps.loadMetaDraft;
    var makeItem = deps.makeItem;
    var metaFor = deps.metaFor;
    var panel = coreState.panel;
    var panelSay = deps.panelSay;
    var parseExamSource = deps.parseExamSource;
    var parsedOf = deps.parsedOf;
    var pending = coreState.pending;
    var publishSelection = deps.publishSelection;
    var publishSelectionSoon = deps.publishSelectionSoon;
    var questionFromParsed = deps.questionFromParsed;
    var renderAll = deps.renderAll;
    var root = deps.dom.root;
    var state = coreState.state;
    var toast = deps.toast;
    var validateForSave = deps.validateForSave;

  // ---------- 载入真题（三端分离入口：题库点「去编辑」/ AI 命令） ----------
  function loadForEdit(questionId, from) {
    var id = String(questionId || "");
    if (!COMMAND_QUESTION_ID_RE.test(id)) return Promise.resolve(null);
    return hostCall("bank.get", { id: id }).then(function (document) {
      if (!document || !document.stem) return null;
      var item = makeItem(document, buildExamSource(document), 0);
      item.savedId = document.id || id;
      item.status = "stored";
      state.items = [item];
      state.active = 0;
      state.dirty = false;
      state.batchId = "";
      // 题库点「去编辑」是从批次列表外直接跳进二屏：先把三栏露出来。
      setMode("review");
      renderAll();
      publishSelectionSoon();
      dock("录题工作台已把题目 " + id + " 序列化成 exam-zh 源码"
        + (from ? "（来自 " + from + "）" : "") + "。");
      return item;
    }).catch(function (error) {
      toast("载入题目失败：" + error.message, "error");
      dock("载入题目 " + id + " 失败：" + error.message);
      return null;
    });
  }

  // ---------- 审核台（军令 #24）：首屏批次列表，二屏三栏审核 ----------
  var WEEKDAYS = "日一二三四五六";

  /** 批次录入时间 → 「2024-10-31-星期四-15:30」。写的是原卷的本地时间，不做时区换算。 */
  function batchStamp(createdAt) {
    var text = String(createdAt == null ? "" : createdAt);
    var hit = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(text);
    if (!hit) return text.slice(0, 16) || "时间未知";
    var day = new Date(Number(hit[1]), Number(hit[2]) - 1, Number(hit[3]));
    return hit[1] + "-" + hit[2] + "-" + hit[3] + "-星期" + WEEKDAYS.charAt(day.getDay())
      + "-" + hit[4] + ":" + hit[5];
  }

  function currentBatch() {
    var id = String(state.batchId || "");
    var found = null;
    state.batches.forEach(function (card) {
      if (String(card.batch_id || "") === id) found = card;
    });
    return found;
  }

  /**
   * 首屏：批次列表。一行一个批次，左边时间与编号，右边「未审：n / N」。
   * 数字用绿色；未审数为 0 的批次整行变灰、沉到最底下，并且点不动——只能看。
   */
  function renderBatchList() {
    if (!batchListEl) return;
    batchListEl.textContent = "";
    var cards = state.batches.slice();
    cards.sort(function (left, right) {
      var leftDone = Number(left.pending_count) === 0 ? 1 : 0;
      var rightDone = Number(right.pending_count) === 0 ? 1 : 0;
      if (leftDone !== rightDone) return leftDone - rightDone;
      return String(right.created_at || "").localeCompare(String(left.created_at || ""));
    });
    cards.forEach(function (card) {
      var pending = Number(card.pending_count) || 0;
      var total = Number(card.total) || 0;
      var done = pending === 0;
      var row = el("button", "ed-batch-row");
      row.type = "button";
      row.setAttribute("data-batch", String(card.batch_id || ""));
      row.setAttribute("data-done", done ? "true" : "false");
      if (done) {
        row.disabled = true;
        row.setAttribute("aria-disabled", "true");
        row.setAttribute("aria-label", "批次 " + card.batch_id + " 已审完，未审 0 / " + total + "，只看不能进");
      } else {
        row.setAttribute("aria-label", "批次 " + card.batch_id + "，未审 " + pending + " / " + total + "，点开审核");
        row.addEventListener("click", function () { openBatch(card.batch_id); });
      }
      row.appendChild(el("span", "ed-batch-left",
        batchStamp(card.created_at) + "-批次编号 #" + card.batch_id));
      var right = el("span", "ed-batch-right");
      right.appendChild(el("span", "ed-batch-label", "未审："));
      right.appendChild(el("span", "ed-batch-num", String(pending)));
      right.appendChild(el("span", "ed-batch-sep", " / "));
      right.appendChild(el("span", "ed-batch-num", String(total)));
      if (done) right.appendChild(el("span", "ed-batch-check", "✅"));
      row.appendChild(right);
      batchListEl.appendChild(row);
    });
    if (batchesEmptyEl) batchesEmptyEl.hidden = cards.length > 0;
  }

  /** 二屏抬头：当前批次号与这一批还剩几道没审。 */
  function renderBatchBar() {
    if (batchNoEl) batchNoEl.textContent = "批次 #" + (state.batchId || "—");
    if (batchStatEl) {
      var card = currentBatch();
      var pending = state.items.length;
      var total = card ? Number(card.total) || 0 : pending;
      batchStatEl.textContent = "未审 " + pending + " / " + total;
      batchStatEl.setAttribute("data-pending", String(pending));
      batchStatEl.setAttribute("data-total", String(total));
    }
  }

  function setMode(mode) {
    state.mode = mode === "review" ? "review" : "list";
    if (root) root.setAttribute("data-mode", state.mode);
    if (batchesEl) batchesEl.hidden = state.mode !== "list";
    if (colsEl) colsEl.hidden = state.mode !== "review";
  }

  /** 重新拉一遍批次卡片：未审数、总数与「审完变灰」都以底座那边的账为准。 */
  function refreshBatches() {
    return hostCall("pending.batch_list", {}).then(function (result) {
      var cards = (result && Array.isArray(result.batches)) ? result.batches : [];
      state.batches = cards;
      renderBatchList();
      renderBatchBar();
      var card = currentBatch();
      if (state.mode === "review" && card && Number(card.pending_count) === 0 && !state.items.length) {
        backToList("这一批已审完，卡片变灰沉到列表最底下。");
      }
      // 首屏要把最新的批次卡片推给辅助栏：它据此显示原文件名、标准名与公共元数据。
      if (state.mode === "list") publishSelection();
      return cards;
    }).catch(function (error) {
      dockWarn("批次列表没拉下来：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return [];
    });
  }

  /** 头一次开审核台：中转站是空的，就把识别结果整批入池，批次列表才有东西可点。 */
  function seedBatch() {
    var questions = DEV_FIXTURES.map(function (doc) {
      return { question: doc };
    });
    return hostCall("pending.save_draft", {
      questions: questions,
      origin: "editor.recognize"
    }).then(function (result) {
      dock("识别结果已入池：" + (result.batch_id || "") + "（" + questions.length + " 题）。");
      return result;
    }, function (error) {
      dockWarn("识别结果入池失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return null;
    });
  }

  /** 画布视图（review / list）也走宿主参数通道：辅助栏那颗【返回列表】才有路。 */
  function publishView(view) {
    hostCall("ui.params.set", {
      params: { view: view === "list" ? "list" : "review" },
      snapshot: panel.uiRevisions || {},
      plugin_id: PLUGIN_ID
    }).catch(function () { /* 参数通道没通，画布自己的落点不受影响 */ });
  }

  /** 点开一个批次：中转站里那一批的待审题直接铺进三栏。 */
  function openBatch(batchId) {
    var id = String(batchId || "");
    if (!id) return Promise.resolve(null);
    return hostCall("pending.list", { batch_id: id }).then(function (result) {
      var rows = (result && Array.isArray(result.items)) ? result.items : [];
      state.batchId = id;
      state.items = rows.map(function (row, index) {
        var doc = (row && row.question) || {};
        var item = makeItem(doc, buildExamSource(doc), index);
        item.pendingId = String((row && row.id) || "");
        item.batchId = String((row && row.batch_id) || id);
        item.assets = Array.isArray(row.assets) ? row.assets : [];
        item.status = "pending";
        return item;
      });
      state.active = 0;
      state.dirty = false;
      setMode("review");
      publishView("review");
      renderBatchBar();
      renderAll();
      publishSelection();
      noteActivity();
      // 识别错得再离谱也照切不误：只在底部日志留一行警告，绝不在画布上弹红窗。
      var broken = state.items.filter(function (item) { return parsedOf(item).errors.length > 0; });
      if (broken.length) {
        dockWarn("批次 " + id + " 里有 " + broken.length + " 题识别有出入，已照原样切进来。");
      }
      return state.items;
    }).catch(function (error) {
      dockWarn("批次 " + id + " 切不进来：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return null;
    });
  }

  /** 回批次列表。走之前把改过的题静默存回中转池，别让老师的改动随界面一起没了。 */
  function backToList(note, fromHost) {
    var leaving = state.mode === "review";
    setMode("list");
    if (leaving) stashBeforeLeave();
    // 辅助栏点的那一下已经走过宿主广播，画布不必把同样的意思再发一遍。
    if (!fromHost) publishView("list");
    refreshBatches();
    if (note) dock(note);
  }

  /**
   * 一道题存回中转池：带 pending_id 就是原地更新，池子里不会多出一道重影。
   * silent=true 时不打扰老师（自动保存与离开前兜底走这条）。
   */
  function stashOne(item, meta, silent) {
    var parsed = parseExamSource(item.source);
    var doc = questionFromParsed(item, parsed, meta || {});
    var problems = validateForSave(doc, parsed, meta || {});
    if (problems.length) {
      var reason = problems.slice(0, 3).join("；");
      if (!silent) panelSay("这一题还存不进去：" + reason, "warn", "invalid");
      return Promise.resolve({ ok: false, message: reason });
    }
    var payload = { questions: [{ pending_id: item.pendingId || "", question: doc }] };
    // 刚切出来的图：字节随草稿一起进池子，落 pending_assets/，主库一个字节都不碰。
    if (item.cropAsset && item.cropAsset.data_url) {
      payload.questions[0].assets = [{
        id: String(item.cropAsset.id || ""),
        data_url: String(item.cropAsset.data_url || "")
      }];
    }
    if (item.batchId) payload.batch_id = item.batchId;
    return hostCall("pending.save_draft", payload).then(function (result) {
      item.dirty = false;
      if (!item.pendingId && result && Array.isArray(result.saved_ids) && result.saved_ids[0]) {
        item.pendingId = String(result.saved_ids[0]);
        item.batchId = String(result.batch_id || item.batchId || "");
      }
      if (!silent) {
        panelSay("已存为待审（池子编号 " + (item.pendingId || "—") + "）。", "ok", "stashed");
        dock("一道题已存进中转站（待审核池）。");
      }
      return { ok: true, result: result };
    }, function (error) {
      var text = (error && error.message) || "未知原因";
      if (!silent) {
        panelSay("存为待审失败：" + text, "error", "failed");
        dockWarn("存为待审失败：" + text, errorDetail(error));
      }
      return { ok: false, message: text, detail: errorDetail(error) };
    });
  }

  /** 离开审核界面之前，把改过的题静默存回中转池。 */
  function stashBeforeLeave() {
    var targets = state.items.filter(function (item) { return item.pendingId && item.dirty; });
    if (!targets.length) return Promise.resolve(null);
    return loadMetaDraft().then(function () {
      return targets.reduce(function (chain, target) {
        return chain.then(function () {
          return stashOne(target, metaFor(target, {}), true);
        });
      }, Promise.resolve(null));
    }).catch(function () { return null; });
  }

    var IDLE_MS = coreState.IDLE_MS;
    var IDLE_TICK_MS = coreState.IDLE_TICK_MS;
  // ---------- 防呆：三分钟没人碰就静默存回中转池 ----------
  var lastActivityAt = Date.now();
  var idleTimer = 0;
  var idleBusy = false;

  function noteActivity() {
    lastActivityAt = Date.now();
  }

  /** 探针专用：把闲置时钟直接拨到「已经超时」，好验证三分钟那道闸门真的会落。 */
  function markIdleDue() {
    lastActivityAt = Date.now() - IDLE_MS - 1000;
  }

  function startIdleWatch() {
    if (idleTimer) return;
    idleTimer = window.setInterval(function () {
      if (state.slot !== "stage.center" || state.mode !== "review" || idleBusy) return;
      if (!state.items.length) return;
      if (Date.now() - lastActivityAt < IDLE_MS) return;
      autoSaveIdle();
    }, IDLE_TICK_MS);
  }

  /** 长时间无操作 → 静默存回中转池，只在底部日志留一行灰字，绝不弹窗抢老师。 */
  function autoSaveIdle() {
    var item = state.items[state.active];
    if (!item || !item.pendingId) return;
    idleBusy = true;
    loadMetaDraft().then(function () {
      return stashOne(item, metaFor(item, {}), true);
    }).then(function (outcome) {
      idleBusy = false;
      lastActivityAt = Date.now();
      if (outcome && outcome.ok) {
        dock("检测到长时间无操作，已自动存入待审核池。", "note");
      } else {
        dockWarn("自动存入待审核池没成功：" + ((outcome && outcome.message) || "未知原因"),
          (outcome && outcome.detail) || "");
      }
    }, function () {
      idleBusy = false;
    });
  }

  /** 关闭或刷新页面时的兜底：不等草稿往返，直接把当前题存回中转池。 */
  function stashOnUnload() {
    var item = state.items[state.active];
    if (!item || !item.pendingId) return;
    var meta = metaFor(item, {});
    var parsed = parseExamSource(item.source);
    var doc = questionFromParsed(item, parsed, meta);
    if (validateForSave(doc, parsed, meta).length) return;
    var payload = { questions: [{ pending_id: item.pendingId, question: doc }] };
    if (item.batchId) payload.batch_id = item.batchId;
    hostCall("pending.save_draft", payload).catch(function () { /* 页面已经在关了 */ });
  }

  /** 中转站动了：入库与删除会把题从池子里带走，画布得把那几道撤下来；暂存只是改内容，不撤。 */
  function onPendingUpdated(payload) {
    var action = String((payload && payload.action) || "");
    var ids = (payload && Array.isArray(payload.pending_ids)) ? payload.pending_ids : [];
    if ((action === "approve" || action === "delete") && ids.length) {
      var before = state.items.length;
      state.items = state.items.filter(function (item) {
        return ids.indexOf(String(item.pendingId)) < 0;
      });
      if (state.items.length !== before) {
        if (state.active >= state.items.length) state.active = Math.max(0, state.items.length - 1);
        renderBatchBar();
        renderAll();
        publishSelection();
      }
    }
    refreshBatches();
  }

    return {
      autoSaveIdle: autoSaveIdle,
      idleBusy: idleBusy,
      idleTimer: idleTimer,
      lastActivityAt: lastActivityAt,
      markIdleDue: markIdleDue,
      noteActivity: noteActivity,
      onPendingUpdated: onPendingUpdated,
      startIdleWatch: startIdleWatch,
      stashOnUnload: stashOnUnload,
      WEEKDAYS: WEEKDAYS,
      backToList: backToList,
      batchStamp: batchStamp,
      currentBatch: currentBatch,
      loadForEdit: loadForEdit,
      openBatch: openBatch,
      publishView: publishView,
      refreshBatches: refreshBatches,
      renderBatchBar: renderBatchBar,
      renderBatchList: renderBatchList,
      seedBatch: seedBatch,
      setMode: setMode,
      stashBeforeLeave: stashBeforeLeave,
      stashOne: stashOne,
    };
  }

  global.JzoEditorBatches = { create: create };
})(window);
