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
    var batchPurgeCancelEl = deps.dom.batchPurgeCancelEl;
    var batchPurgeEmptyEl = deps.dom.batchPurgeEmptyEl;
    var batchPurgeGroupsEl = deps.dom.batchPurgeGroupsEl;
    var batchPurgeModalEl = deps.dom.batchPurgeModalEl;
    var batchPurgeOkEl = deps.dom.batchPurgeOkEl;
    var batchPurgeSummaryEl = deps.dom.batchPurgeSummaryEl;
    var batchStatEl = deps.dom.batchStatEl;
    var batchesEl = deps.dom.batchesEl;
    var batchesEmptyEl = deps.dom.batchesEmptyEl;
    var poolCanvasEl = deps.dom.poolCanvasEl;
    var buildExamSource = deps.buildExamSource;
    var closeModal = deps.closeModal;
    var colsEl = deps.dom.colsEl;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var el = deps.el;
    var errorDetail = deps.errorDetail;
    var hostCall = deps.hostCall;
    var loadMetaDraft = deps.loadMetaDraft;
    var makeItem = deps.makeItem;
    var metaFor = deps.metaFor;
    var openModal = deps.openModal;
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

  /** 卡片第二行的短时间：「10-31 星期四 15:30」。年份对老师没意义，省下来给文件名。 */
  function shortBatchStamp(createdAt) {
    var text = String(createdAt == null ? "" : createdAt);
    var hit = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(text);
    if (!hit) return text.slice(0, 16) || "时间未知";
    var day = new Date(Number(hit[1]), Number(hit[2]) - 1, Number(hit[3]));
    return hit[2] + "-" + hit[3] + " 星期" + WEEKDAYS.charAt(day.getDay())
      + " " + hit[4] + ":" + hit[5];
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
   * 批次账目对平（军令 #32 · 第五步）：抽走的题不再算未审数，老师得看见它们去了哪。
   *
   * 四个数都来自底座，插件一个都不自己数：
   * - 未审 = 这一批在 ``pending_questions`` 里的真实行数；
   * - 池内 = 已抽进重题池的条数（``dedupe.pooled``，底座任何状态都给，G2·C1）；
   * - 已入库 = ``approved_json`` 的条数；
   * - 总数 = 录入时累加、彻底删除时回退的那个数。
   * 未审 ＋ 池内 ＋ 已入库 通常正好等于总数；池内【删除】只清池行、不动批次总数，
   * 那一条会在等式上留个缺口。缺口如实写成「已裁删」，绝不抹平成看起来对得上的样子。
   */
  function batchLedger(card, pendingCount) {
    var pending = Number(pendingCount) || 0;
    var total = card ? Number(card.total) || 0 : pending;
    var dedupe = (card && card.dedupe) || null;
    // 底座现在任何状态都给 ``pooled``（G2·C1）；万一拿不到（老底座不带这个字段），
    // 「已裁删」一律不报——把抽进池里的题折进已裁删就是在账上谎报老师删了题（判据 5.4）。
    var pooledKnown = Boolean(dedupe) && dedupe.pooled !== undefined && dedupe.pooled !== null;
    var pooled = Number(dedupe && dedupe.pooled) || 0;
    var stored = Number(card && card.approved_count) || 0;
    var gone = pooledKnown ? total - pending - pooled - stored : 0;
    if (gone < 0) gone = 0;
    return { total: total, pending: pending, pooled: pooled, stored: stored,
             gone: gone, pooledKnown: pooledKnown };
  }

  /** 账目那一串的文案：四个口径共用，卡片与二屏抬头不许各写一套。 */
  function ledgerText(ledger) {
    var parts = ["未审 " + ledger.pending];
    if (ledger.pooled) parts.push("池内 " + ledger.pooled);
    if (ledger.stored) parts.push("已入库 " + ledger.stored);
    if (ledger.gone) parts.push("已裁删 " + ledger.gone);
    return parts.join(" ＋ ") + " ＝ 总数 " + ledger.total;
  }

  /**
   * 3.1a 后台初查的显形：只在批次卡片上补一行**文字**，不加按钮、不弹窗、不加占位页。
   *
   * 三态文案（军令 #31 台账 ⑧.1/⑧.2）：
   * - `done` 且扫出冗余 → 红字两栏，条数与【剔除重复】弹窗的默认勾选集同源同尺；
   * - `pending` → 加载态（`aria-busy`），底座还没扫完；
   * - `failed` → 主库读不通，如实报「未完成」并提醒存入前仍会强校验。
   * **任何路径都不许写「没有重复」**：`done` 且冗余为 0 时这一行干脆不出，
   * 终局裁决永远在老师点【存入主库】那次强校验，卡片不作免检承诺。
   */
  function renderBatchDedupe(card, row) {
    var info = (card && card.dedupe && typeof card.dedupe === "object") ? card.dedupe : {};
    var status = String(info.status || "pending");
    var text = "";
    var loading = false;
    if (status === "done") {
      var redundant = Number(info.redundant) || 0;
      if (redundant <= 0) return;
      text = "后台初查：疑似重复 " + redundant + " 道"
        + "（批内重复 " + (Number(info.batch_redundant) || 0) + " 题"
        + " / 主库已有 " + (Number(info.bank_redundant) || 0) + " 题）"
        + "，已初查 " + (Number(info.scanned) || 0) + " 题，仍待你拍板";
    } else if (status === "failed") {
      text = "初查未完成（主库读不通），存入前仍会强校验";
    } else {
      text = "初查结果未出，存入前仍会强校验";
      loading = true;
    }
    var note = el("span", "ed-batch-dedupe", text);
    note.setAttribute("data-dedupe-status", status);
    if (loading) note.setAttribute("aria-busy", "true");
    row.appendChild(note);
  }

  /**
   * 首屏：批次列表。一张卡片先说「这是哪份卷子」（原始文件名），
   * 再给时间和批次号，右边是待审题数。审完的整行变灰沉底、点不动。
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
      var row = el("div", "ed-batch-row");
      row.setAttribute("data-batch", String(card.batch_id || ""));
      row.setAttribute("data-done", done ? "true" : "false");
      var open = el("button", "ed-batch-open");
      open.type = "button";
      var ledger = batchLedger(card, pending);
      if (done) {
        open.disabled = true;
        open.setAttribute("aria-disabled", "true");
        open.setAttribute("aria-label", "批次 " + card.batch_id + " 已审完，" + ledgerText(ledger) + "，只看不能进");
      } else {
        open.setAttribute("aria-label", "批次 " + card.batch_id + "，" + ledgerText(ledger) + "，点开审核");
        open.addEventListener("click", function () { openBatch(card.batch_id); });
      }
      // 第一行是卷子自己的名字；没有原文件名（老批次 / 手工录入）才退到批次标签。
      var title = String(card.source_name || card.label || ("批次 #" + card.batch_id));
      var main = el("span", "ed-batch-main");
      main.appendChild(el("span", "ed-batch-name", title));
      main.appendChild(el("span", "ed-batch-meta",
        shortBatchStamp(card.created_at) + " | 批次 #" + card.batch_id));
      // 抽进池、已入库、已裁删的账只在真发生时补一行；等式任何时刻都成立。
      var extra = [];
      if (ledger.pooled) extra.push("池内 " + ledger.pooled);
      if (ledger.stored) extra.push("已入库 " + ledger.stored);
      if (ledger.gone) extra.push("已裁删 " + ledger.gone);
      if (extra.length) main.appendChild(el("span", "ed-batch-extra", extra.join(" · ")));
      open.appendChild(main);
      var right = el("span", "ed-batch-right");
      right.appendChild(el("span", "ed-batch-label", "待审 "));
      right.appendChild(el("span", "ed-batch-num", String(pending)));
      right.appendChild(el("span", "ed-batch-sep", " / "));
      right.appendChild(el("span", "ed-batch-num ed-batch-total", String(total)));
      if (done && !ledger.pooled) right.appendChild(el("span", "ed-batch-check", "✅"));
      open.appendChild(right);
      row.appendChild(open);
      if (!done && pending >= 1) {
        renderBatchDedupe(card, row);
        var purge = el("button", "ed-batch-purge", "剔除重复");
        purge.type = "button";
        purge.setAttribute("aria-label", "批次 " + card.batch_id + " 一键剔除重复题");
        purge.addEventListener("click", function () { openPurge(card); });
        row.appendChild(purge);
      }
      // 行改成了 div（多一颗按钮后按钮不能再套按钮），整行的内边距与缝隙就没人接了：
      // hover 还亮着、点下去却不动，老师只当卡了。这里补一层行级点击，
      // 两颗按钮已经各自绑好动作，只收它们没吃到的那部分。
      row.addEventListener("click", function (event) {
        if (done) return;
        var hit = event.target && event.target.closest
          ? event.target.closest(".ed-batch-open, .ed-batch-purge") : null;
        if (hit) return;
        openBatch(card.batch_id);
      });
      batchListEl.appendChild(row);
    });
    if (batchesEmptyEl) batchesEmptyEl.hidden = cards.length > 0;
  }

  // ---------- 一键剔除本批次重复题（军令 #31 · 3.5） ----------
  // 清单由底座 dry-run 给出：batch 组默认勾、bank 组默认不勾，勾选粒度落在每条 drop 上。
  var purgePlan = null;
  var purgeSelected = {};
  var purgeBatchId = "";
  var purgeBusy = false;

  function purgeCheckedIds() {
    var ids = Object.keys(purgeSelected).filter(function (id) { return purgeSelected[id]; });
    ids.sort();
    return ids;
  }

  /** 底部按钮与归零红字都按「本批实读 - 当前勾选」现算，不信服务端上次的 will_empty。 */
  function updatePurgeFooter() {
    var selected = purgeCheckedIds();
    var scanned = purgePlan ? Number(purgePlan.scanned) || 0 : 0;
    if (batchPurgeOkEl) {
      batchPurgeOkEl.disabled = purgeBusy || selected.length === 0;
      batchPurgeOkEl.textContent = "执行剔除（当前勾选 " + selected.length + " 道）";
      if (purgeBusy) {
        batchPurgeOkEl.setAttribute("aria-busy", "true");
      } else {
        batchPurgeOkEl.removeAttribute("aria-busy");
      }
    }
    if (batchPurgeEmptyEl) batchPurgeEmptyEl.hidden = !purgePlan || scanned - selected.length > 0;
  }

  function purgeReasonText(reason) {
    return reason === "batch" ? "批内重复" : "与主库重复";
  }

  function purgeKeepText(group) {
    if (group.reason === "batch") {
      return "保留录入序 #" + (group.seq_keep == null ? "?" : group.seq_keep) + "：" + String(group.keep || "");
    }
    return "主库已有：" + String(group.existing_id || "");
  }

  /** 一组重复：标题栏给全选快捷勾，keep 行只报「保留」、不给任何可勾入口。 */
  function renderPurgeGroup(group, block) {
    var drops = (group && Array.isArray(group.drop)) ? group.drop : [];
    var head = el("div", "ep-purge-head");
    head.appendChild(el("span", "ep-purge-badge", purgeReasonText(group.reason)));
    var fingerprint = String(group.fingerprint || "").slice(0, 8);
    head.appendChild(el("span", "ep-purge-meta",
      (fingerprint ? "指纹 " + fingerprint + " · " : "") + "将删 " + drops.length + " 道"));
    var selectAll = el("button", "ep-btn ep-mini-btn ep-purge-all", "全选");
    selectAll.type = "button";
    head.appendChild(selectAll);
    block.appendChild(head);
    if (group.keep || group.existing_id) {
      block.appendChild(el("p", "ep-purge-keep", purgeKeepText(group)));
    }
    var list = el("div", "ep-purge-list");
    var boxes = [];
    drops.forEach(function (rawId) {
      var id = String(rawId || "");
      var label = el("label", "ep-purge-item");
      var box = document.createElement("input");
      box.type = "checkbox";
      box.setAttribute("data-purge-id", id);
      box.checked = Boolean(purgeSelected[id]);
      box.addEventListener("change", function () {
        if (box.checked) purgeSelected[id] = true;
        else delete purgeSelected[id];
        refreshSelectAll();
        updatePurgeFooter();
      });
      boxes.push(box);
      label.appendChild(box);
      label.appendChild(el("span", "ep-purge-id", id));
      list.appendChild(label);
    });
    block.appendChild(list);

    function refreshSelectAll() {
      var checked = boxes.filter(function (box) { return box.checked; }).length;
      selectAll.textContent = checked === boxes.length ? "全不选" : "全选";
    }
    selectAll.addEventListener("click", function () {
      var allChecked = boxes.length > 0 && boxes.every(function (box) { return box.checked; });
      boxes.forEach(function (box) {
        box.checked = !allChecked;
        if (allChecked) delete purgeSelected[box.getAttribute("data-purge-id")];
        else purgeSelected[box.getAttribute("data-purge-id")] = true;
      });
      refreshSelectAll();
      updatePurgeFooter();
    });
    refreshSelectAll();
  }

  function renderPurgeBody() {
    if (batchPurgeGroupsEl) batchPurgeGroupsEl.textContent = "";
    updatePurgeFooter();
    if (!batchPurgeGroupsEl || !purgePlan) return;
    var groups = Array.isArray(purgePlan.groups) ? purgePlan.groups : [];
    var scanned = Number(purgePlan.scanned) || 0;
    var mainScanned = Number(purgePlan.main_scanned) || 0;
    if (!groups.length) {
      if (batchPurgeSummaryEl) {
        batchPurgeSummaryEl.textContent = "本批没有重复题（本批实读 " + scanned + " 道，主库 " + mainScanned + " 道已扫描）。";
      }
      batchPurgeGroupsEl.appendChild(el("p", "ep-purge-empty", "没有可剔除的条目。"));
      if (batchPurgeOkEl) batchPurgeOkEl.hidden = true;
      if (batchPurgeCancelEl) batchPurgeCancelEl.textContent = "关闭";
      return;
    }
    if (batchPurgeSummaryEl) {
      batchPurgeSummaryEl.textContent = "本批实读 " + scanned + " 道，主库 " + mainScanned
        + " 道已扫描；共 " + (Number(purgePlan.redundant) || 0) + " 道重复，已默认勾选 "
        + purgeCheckedIds().length + " 道。";
    }
    groups.forEach(function (group) {
      var block = el("div", "ep-purge-group");
      renderPurgeGroup(group, block);
      batchPurgeGroupsEl.appendChild(block);
    });
  }

  function openPurge(card) {
    var id = String((card && card.batch_id) || "");
    if (!id || purgeBusy) return;
    purgePlan = null;
    purgeSelected = {};
    purgeBatchId = id;
    if (batchPurgeSummaryEl) batchPurgeSummaryEl.textContent = "正在扫描本批重复题…";
    if (batchPurgeGroupsEl) batchPurgeGroupsEl.textContent = "";
    if (batchPurgeEmptyEl) batchPurgeEmptyEl.hidden = true;
    if (batchPurgeOkEl) {
      batchPurgeOkEl.hidden = false;
      batchPurgeOkEl.disabled = true;
      batchPurgeOkEl.textContent = "执行剔除（当前勾选 0 道）";
    }
    if (batchPurgeCancelEl) batchPurgeCancelEl.textContent = "取消";
    openModal(batchPurgeModalEl);
    return hostCall("pending.batch_duplicates", { batch_id: id }).then(function (plan) {
      if (purgeBatchId !== id) return plan;
      purgePlan = plan || {};
      var defaults = Array.isArray(purgePlan.drop_ids) ? purgePlan.drop_ids : [];
      defaults.forEach(function (rawId) { purgeSelected[String(rawId)] = true; });
      renderPurgeBody();
      return plan;
    }, function (error) {
      closeModal(batchPurgeModalEl);
      dockWarn("重复清单没拉下来：" + ((error && error.message) || "未知原因"), errorDetail(error));
      return null;
    });
  }

  /** 执行剔除：勾选集升序提交，expected_drop_ids 原样回显，勾空则显式要求剔空。 */
  function submitPurge() {
    if (purgeBusy || !purgePlan) return;
    var ids = purgeCheckedIds();
    if (!ids.length) return;
    var remain = (Number(purgePlan.scanned) || 0) - ids.length;
    purgeBusy = true;
    updatePurgeFooter();
    hostCall("pending.purge_duplicates", {
      batch_id: purgeBatchId,
      drop_ids: ids,
      expected_drop_ids: ids.slice(),
      allow_empty: remain <= 0
    }).then(function (result) {
      purgeBusy = false;
      closeModal(batchPurgeModalEl);
      var deleted = (result && Array.isArray(result.deleted)) ? result.deleted : ids;
      dock("已从批次 #" + purgeBatchId + " 剔除 " + deleted.length + " 道重复题。");
      var left = Number(result && result.new_redundant) || 0;
      if (left > 0) {
        dock("还有 " + left + " 道重复未剔除（主库组默认不勾），可重扫复核。");
      }
      refreshBatches();
    }, function (error) {
      purgeBusy = false;
      var code = String((error && (error.detailCode || error.code)) || "");
      updatePurgeFooter();
      if (code === "batch_purge_selection_stale" || code === "batch_purge_keep_selected") {
        closeModal(batchPurgeModalEl);
        dock("重复清单已变，正在重新扫描。");
        openPurge({ batch_id: purgeBatchId });
        return;
      }
      if (code === "batch_purge_empty_not_confirmed") {
        // 前后端对「是否剔空」判断不一致时，留弹窗把归零红字亮出来，绝不静默重试。
        if (batchPurgeEmptyEl) batchPurgeEmptyEl.hidden = false;
        dockWarn("服务端要求先确认把本批剔空。", errorDetail(error));
        return;
      }
      dockWarn("剔除没成功：" + ((error && error.message) || "未知原因"), errorDetail(error));
    });
  }

  if (batchPurgeCancelEl) {
    batchPurgeCancelEl.addEventListener("click", function () {
      if (!purgeBusy) closeModal(batchPurgeModalEl);
    });
  }
  if (batchPurgeOkEl) {
    batchPurgeOkEl.addEventListener("click", submitPurge);
  }

  /** 二屏抬头：当前批次号与这一批还剩几道没审（池内的另算，合起来等于总数）。 */
  function renderBatchBar() {
    if (batchNoEl) batchNoEl.textContent = "批次 #" + (state.batchId || "—");
    if (batchStatEl) {
      // 与首屏卡片同一份算法：抬头这一行只是把同一本账换个地方念，不许两处各算各的。
      var ledger = batchLedger(currentBatch(), state.items.length);
      batchStatEl.textContent = ledgerText(ledger);
      batchStatEl.setAttribute("data-pending", String(ledger.pending));
      batchStatEl.setAttribute("data-pooled", String(ledger.pooled));
      batchStatEl.setAttribute("data-stored", String(ledger.stored));
      batchStatEl.setAttribute("data-total", String(ledger.total));
    }
  }

  function setMode(mode) {
    // 三屏（军令 #32 · 第五步）：list 是批次列表首屏，review 是三栏审核，
    // pool 是重题池对比——与审核画布物理分开，来回不必再跳屏。
    state.mode = mode === "review" ? "review" : (mode === "pool" ? "pool" : "list");
    if (root) root.setAttribute("data-mode", state.mode);
    if (batchesEl) batchesEl.hidden = state.mode !== "list";
    if (colsEl) colsEl.hidden = state.mode !== "review";
    if (poolCanvasEl) poolCanvasEl.hidden = state.mode !== "pool";
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
      var pages = (result && Array.isArray(result.page_images)) ? result.page_images : [];
      state.batchId = id;
      state.items = rows.map(function (row, index) {
        var doc = (row && row.question) || {};
        var item = makeItem(doc, buildExamSource(doc), index);
        item.pendingId = String((row && row.id) || "");
        item.batchId = String((row && row.batch_id) || id);
        item.assets = Array.isArray(row.assets) ? row.assets : [];
        // 原卷页属批次层：按条目的页号取那一页，没页号就退到第 1 页。
        var pageNo = Number(row && row.page_no) || 1;
        var page = pages[pageNo - 1] || pages[0] || null;
        item.pageImage = page && page.uri
          ? { uri: String(page.uri), page: Number(page.page) || pageNo }
          : null;
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
