/**
 * ui_pool_panel.js —— 重题池住在**辅助栏**的那一半（军令 #32 · 第五步，判据 5.1/5.3/5.4）。
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）
 *
 * 画布那一屏只画渲染（ui_pool.js），这里管的是老师动手的地方：
 *
 * - 三档 严 / 标准 / 宽，默认宽；切档即时带 `?tier=` 重扫，**档位不落盘**——
 *   它只是这一会话里的读法，插件不落任何浏览器本地存储，草稿里也不给它留位子；
 * - 每条显示底座的 label ＋百分比，排序照底座的「按像的程度降序」，不自己再排一遍；
 *   点开能看「为什么像」的信号明细，措辞只说「很像」，绝不说「98% 是同一道题」；
 * - 四个动作：合并元数据 / 新增解析 / 不重复 / 删除。【覆盖】【放弃】已退役，
 *   这里不给它们留任何入口；`locked_actions` 是底座算好的锁，界面只照它灰，
 *   并写明为什么锁；【删除】走二次确认；【不重复】缺项时这条留在池里并列出缺什么；
 * - 裁决成功的条目从此退场，也不再被扫回池子（防复活归底座）。
 *
 * 空池整段留白：不写「暂无重题」这类占位文案（判据 5.3）。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var PLUGIN_ID = coreState.PLUGIN_ID;
    var el = deps.el;
    var hostCall = deps.hostCall;
    var panelSay = deps.panelSay;
    var publish = deps.publish;
    var dock = deps.dock;
    var dockWarn = deps.dockWarn;
    var errorDetail = deps.errorDetail;
    var openModal = deps.openModal;
    var closeModal = deps.closeModal;
    var dom = deps.dom;
    var actsEl = dom.panelPoolActsEl;
    var backEl = dom.panelPoolBackEl;
    var countEl = dom.panelPoolCountEl;
    var deleteEl = dom.panelPoolDeleteEl;
    var delModalEl = dom.poolDelModalEl;
    var delOkEl = dom.poolDelOkEl;
    var delCancelEl = dom.poolDelCancelEl;
    var delTextEl = dom.poolDelTextEl;
    var listEl = dom.panelPoolListEl;
    var lockEl = dom.panelPoolLockEl;
    var mergeEl = dom.panelPoolMergeEl;
    var msgEl = dom.panelPoolMsgEl;
    var sectionEl = dom.panelPoolSecEl;
    var separateEl = dom.panelPoolSeparateEl;
    var solutionEl = dom.panelPoolSolutionEl;
    var tiersEl = dom.panelPoolTiersEl;
    var entryEl = dom.panelPoolEntryEl;

    // 档位与选中都是**本会话内存态**：插件不许碰浏览器本地存储，也不进宿主草稿。
    var tier = "loose";
    var entries = [];
    var selectedId = "";
    var selectedEntry = null;
    var busy = false;
    // 军令 #32 · P0：主公口径「默认不是收起的」也包含池子段——默认展开；
    // 空池仍整段收起（判据 5.3 留白不倒：render() 里那把 !entries.length 的锁不动）。
    // 入口钮保留：只在「有货且还没展开」时才挂出来（现在没有收起路径，它是备用通路）。
    var revealed = true;
    // 展开看「为什么像」的那几条：内存态，换档不保留（重画成本低，也不必记账）。
    var opened = {};
    // 监听只挂一次的开关：辅助栏会被反复 activate。
    var wired = false;
    // 查重三栏（军令·查重三栏）：对比模式开启时画布归 ui_dup_compare 独占，
    // 这里不再把选中推去旧的两栏屏，也不在刷新时擅自收窗。
    var compareActive = false;
    var selectionListener = null;
    var poolStateListener = null;

    var ACTION_LABELS = {
      merge_metadata: "合并元数据",
      add_solution: "新增解析",
      keep_separate: "不重复",
      delete: "删除"
    };

    /** 给画布那一屏递话：开（带整条详情）与关，都从这一个口子出。 */
    function notifyCanvas(phase, entry) {
      if (!publish) return;
      publish("editor.pool_review", {
        pluginId: PLUGIN_ID, from: "panel", phase: phase,
        pool_id: entry ? String(entry.pool_id || "") : selectedId,
        entry: entry || null
      });
    }

    /** 批次卡片上的账（未审 / 池内 / 已入库 / 总数）由画布重拉，这里只喊一声。 */
    function askCanvasRefresh() {
      if (!publish) return;
      publish("editor.batch_review", { pluginId: PLUGIN_ID, from: "panel", action: "refresh_batches" });
    }

    function say(text, tone, stateName) {
      if (msgEl) {
        msgEl.textContent = text;
        msgEl.hidden = !text;
        msgEl.setAttribute("data-tone", tone || "info");
      }
      if (panelSay) panelSay(text, tone || "info", stateName || "");
    }

    /** 三档钮的选中态：只认 data-tier，样式跟面板里其它 .ep-seg-btn 一致。 */
    function paintTiers() {
      if (!tiersEl) return;
      Array.prototype.forEach.call(tiersEl.querySelectorAll("[data-tier]"), function (node) {
        var on = node.getAttribute("data-tier") === tier;
        node.classList.toggle("is-on", on);
        node.setAttribute("aria-pressed", on ? "true" : "false");
      });
    }

    function percentOf(entry) {
      return Math.max(0, Math.min(100, Number(entry && entry.percent) || 0));
    }

    /** 「为什么像」：信号明细原样来自底座，插件一个字都不改口径。 */
    function renderSignals(entry) {
      var box = el("div", "ep-pool-signals");
      var signals = Array.isArray(entry.signals) ? entry.signals : [];
      if (!signals.length) {
        box.appendChild(el("p", "ep-pool-signal", "这一条是全等指纹命中的，没有分项可看。"));
        return box;
      }
      signals.forEach(function (signal) {
        var item = signal && typeof signal === "object" ? signal : {};
        var hit = Boolean(item.hit);
        var line = el("p", "ep-pool-signal" + (hit ? " is-hit" : " is-miss"));
        line.appendChild(el("span", "ep-pool-signal-mark", hit ? "✓" : "×"));
        line.appendChild(el("span", "ep-pool-signal-label", String(item.label || item.key || "")));
        line.appendChild(el("span", "ep-pool-signal-detail", String(item.detail || "")));
        box.appendChild(line);
      });
      return box;
    }

    function rowTitle(entry) {
      var bits = [];
      if (entry.main_id) bits.push("主库 " + entry.main_id);
      bits.push("池内 " + String(entry.item_id || ""));
      if (entry.batch_id) bits.push("批次 #" + entry.batch_id);
      if (entry.source_name) bits.push(entry.source_name);
      return bits.join(" · ");
    }

    /** 一条一行：label ＋百分比在最前，点开才出信号明细。 */
    function renderRow(entry) {
      var poolId = String(entry.pool_id || "");
      var row = el("div", "ep-pool-row" + (poolId === selectedId ? " is-selected" : ""));
      row.setAttribute("role", "listitem");
      row.setAttribute("data-pool", poolId);
      if (poolId === selectedId) row.setAttribute("aria-selected", "true");
      var head = el("button", "ep-pool-trigger");
      head.type = "button";
      head.setAttribute("aria-expanded", opened[poolId] ? "true" : "false");
      head.appendChild(el("span", "ep-pool-level", String(entry.label || "像")));
      head.appendChild(el("span", "ep-pool-percent", percentOf(entry) + "%"));
      head.appendChild(el("span", "ep-pool-ident", rowTitle(entry)));
      head.addEventListener("click", function () {
        if (opened[poolId]) delete opened[poolId];
        else opened[poolId] = true;
        select(entry);
      });
      row.appendChild(head);
      if (opened[poolId]) row.appendChild(renderSignals(entry));
      return row;
    }

    /** 锁死说明：只念底座给的 locked_actions，界面不自己判答案像不像。 */
    function lockText(entry) {
      if (!entry) return "";
      var locked = Array.isArray(entry.locked_actions) ? entry.locked_actions : [];
      if (!locked.length) return "";
      var names = locked.map(function (name) { return ACTION_LABELS[name] || name; });
      var answer = entry.answer && typeof entry.answer === "object" ? entry.answer : {};
      return "已锁死：" + names.join("、") + "。两边答案不同（主库："
        + (answer.main || "没写") + " ／ 这条：" + (answer.incoming || "没写")
        + "），并进去只会拿一套答案盖掉另一套。";
    }

    function paintActions() {
      var locked = selectedEntry && Array.isArray(selectedEntry.locked_actions)
        ? selectedEntry.locked_actions : [];
      var pairs = [[mergeEl, "merge_metadata"], [solutionEl, "add_solution"],
        [separateEl, "keep_separate"], [deleteEl, "delete"]];
      pairs.forEach(function (pair) {
        var node = pair[0];
        if (!node) return;
        var off = locked.indexOf(pair[1]) >= 0;
        node.disabled = !selectedEntry || off || busy;
        node.setAttribute("aria-disabled", node.disabled ? "true" : "false");
        node.title = off ? "答案明确不同，这一项已被底座锁死" : (selectedEntry ? "" : "先在左边选中一条");
      });
      var text = lockText(selectedEntry);
      if (lockEl) {
        lockEl.textContent = text;
        lockEl.hidden = !text;
      }
      if (actsEl) actsEl.hidden = !selectedEntry;
      if (backEl) backEl.hidden = !selectedEntry;
    }

    /** 入口钮（S8 · P0-1）：老师进池子那一屏的唯一抓手，账目就是池里的条数。 */
    function paintEntry() {
      if (!entryEl) return;
      entryEl.hidden = !(entries.length && !revealed && !selectedEntry);
      entryEl.textContent = "重题池 " + entries.length + " 条";
      entryEl.setAttribute("aria-expanded", revealed ? "true" : "false");
    }

    function render() {
      if (!sectionEl) return;
      // 空池留白：整段收起，不写「暂无重题」这类占位文案（判据 5.3）。
      // 池里有货也要等老师点入口钮才展开——入口只这一颗，画布那一屏一颗按钮都没有。
      sectionEl.hidden = !selectedEntry && !(revealed && entries.length);
      paintEntry();
      if (poolStateListener) poolStateListener(entries.length, selectedEntry);
      if (!entries.length) return;
      if (countEl) {
        countEl.textContent = entries.length + " 条";
        countEl.setAttribute("data-total", String(entries.length));
      }
      if (listEl) {
        listEl.textContent = "";
        entries.forEach(function (entry) { listEl.appendChild(renderRow(entry)); });
      }
      paintActions();
    }

    /** 重取池子：档位每次现传，不落盘；排序与过滤都以底座为准。 */
    function refresh() {
      return hostCall("pending.pool_list", { tier: tier }).then(function (result) {
        var rows = (result && Array.isArray(result.items)) ? result.items : [];
        entries = rows;
        // 选中的那条可能刚被别处裁决掉：列表里没有就退场，不许留着画一张不存在的对比。
        if (selectedId && !rows.some(function (entry) { return String(entry.pool_id) === selectedId; })) {
          selectedId = "";
          selectedEntry = null;
          if (!compareActive) notifyCanvas("closed");
        }
        render();
        return rows;
      }, function (error) {
        dockWarn("重题池没读回来：" + ((error && error.message) || "未知原因"), errorDetail(error));
        return [];
      });
    }

    /** 选中一条：取详情（两侧完整文档）→ 交给画布那一屏画渲染，这里只管裁决。 */
    function select(entry) {
      var poolId = String((entry && entry.pool_id) || "");
      if (!poolId) return Promise.resolve(null);
      if (selectedId === poolId && selectedEntry) {
        render();
        return Promise.resolve(selectedEntry);
      }
      selectedId = poolId;
      selectedEntry = null;
      say("", "info", "idle");
      render();
      return hostCall("pending.pool_get", { pool_id: poolId, tier: tier }).then(function (detail) {
        if (!detail || String(detail.pool_id) !== selectedId) return null;
        selectedEntry = detail;
        render();
        // 对比模式由裁判台接管：只把详情交回去，旧两栏屏不再抢画布。
        if (compareActive && selectionListener) selectionListener(detail);
        else notifyCanvas("open", detail);
        return detail;
      }, function (error) {
        selectedId = "";
        render();
        say("这一条的详情没取回来：" + ((error && error.message) || "未知原因"), "error", "failed");
        return null;
      });
    }

    /** 四个动作的公共出口：底座说缺什么就念什么，退场就重取。 */
    function runAction(action) {
      var entry = selectedEntry;
      if (!entry || busy) return;
      var poolId = String(entry.pool_id || "");
      busy = true;
      paintActions();
      say("正在执行「" + (ACTION_LABELS[action] || action) + "」…", "info", "saving");
      hostCall("pending.pool_act", { pool_id: poolId, action: action }).then(function (result) {
        busy = false;
        var missing = (result && Array.isArray(result.missing)) ? result.missing : [];
        if (result && result.kept_in_pool) {
          // 缺项不是异常，是老师还没补完的活：留在池里，并把缺的点名。
          say("还缺：" + missing.join("、") + "。这一条仍留在池里，补完再来裁决。", "warn", "invalid");
          refresh();
          return;
        }
        var done = result && result.removed_from_pool
          ? "已「" + (ACTION_LABELS[action] || action) + "」，这一条从池里退场。"
          : "已「" + (ACTION_LABELS[action] || action) + "」。";
        say(done, "ok", "stored");
        dock("重题池：" + done + "（" + poolId + "）");
        selectedId = "";
        selectedEntry = null;
        opened = {};
        notifyCanvas("closed");
        refresh();
        askCanvasRefresh();
      }, function (error) {
        busy = false;
        var code = String((error && (error.detailCode || error.code)) || "");
        if (code === "answer_mismatch") {
          say("两边答案不同，底座拒绝了这次写入：只能选「不重复」或「删除」。", "error", "blocked");
        } else if (error && error.status === 404) {
          say("这一条已经不在池里了（别处裁过了），列表已重新取过。", "warn", "gone");
          selectedId = "";
          selectedEntry = null;
          notifyCanvas("closed");
        } else if (error && error.status === 422) {
          say("这道题还不符合入库要求：" + ((error && error.message) || "Schema 未过"), "error", "invalid");
        } else {
          say("动作没做成：" + ((error && error.message) || "未知原因"), "error", "failed");
          dockWarn("重题池动作失败：" + ((error && error.message) || "未知原因"), errorDetail(error));
        }
        refresh();
      });
    }

    /** 【删除】走二次确认（复用 #46 那颗红按钮的确认样式）。 */
    function askDelete() {
      var entry = selectedEntry;
      if (!entry) return;
      if (delTextEl) {
        delTextEl.textContent = "删掉的是池里这一条（" + String(entry.item_id || "")
          + "）与它的成品图，主库那道" + (entry.main_id ? "（" + entry.main_id + "）" : "原题")
          + "一个字节都不碰。这一条从此不再被扫回池里。";
      }
      openModal(delModalEl);
    }

    function confirmDelete() {
      closeModal(delModalEl);
      runAction("delete");
    }

    function cancelDelete() {
      closeModal(delModalEl);
    }

    /** 换档：只改内存里的 tier，立刻带 `?tier=` 重取（判据 5.3）。 */
    function chooseTier(next) {
      var value = String(next || "");
      if (["strict", "standard", "loose"].indexOf(value) < 0 || value === tier) return;
      tier = value;
      paintTiers();
      say("", "info", "idle");
      refresh();
    }

    /** 【返回审核】：收掉画布那一屏，辅助栏回到当前题的表单上。 */
    function backToReview() {
      selectedId = "";
      selectedEntry = null;
      notifyCanvas("closed");
      render();
      say("已退出重题池，回到当前题的审核。", "info", "idle");
    }

    /** 画布那边自己按了 Esc：那一屏已经收了，这边的选中要跟着放开。 */
    function onCanvasClosed() {
      if (!selectedId) return;
      selectedId = "";
      selectedEntry = null;
      render();
    }

    /** 【重题池 N 条】：展开这一段，把焦点交给第一条，老师的下一步天然是点条目。 */
    function reveal() {
      revealed = true;
      render();
      var first = listEl && listEl.querySelector ? listEl.querySelector(".ep-pool-trigger") : null;
      if (first && first.focus) first.focus();
    }

    function wire() {
      // 辅助栏会重活一遍（画布那一帧先起、这一帧后起），监听只许挂一次。
      if (wired) return;
      wired = true;
      if (entryEl) entryEl.addEventListener("click", reveal);
      if (tiersEl) {
        tiersEl.addEventListener("click", function (event) {
          var node = event.target && event.target.closest ? event.target.closest("[data-tier]") : null;
          if (node) chooseTier(node.getAttribute("data-tier"));
        });
      }
      if (mergeEl) mergeEl.addEventListener("click", function () { runAction("merge_metadata"); });
      if (solutionEl) solutionEl.addEventListener("click", function () { runAction("add_solution"); });
      if (separateEl) separateEl.addEventListener("click", function () { runAction("keep_separate"); });
      if (deleteEl) deleteEl.addEventListener("click", askDelete);
      if (delOkEl) delOkEl.addEventListener("click", confirmDelete);
      if (delCancelEl) delCancelEl.addEventListener("click", cancelDelete);
      if (backEl) backEl.addEventListener("click", backToReview);
      paintTiers();
      render();
      refresh();
    }

    function tierNow() { return tier; }

    function selected() { return selectedEntry; }

    function poolSize() { return entries.length; }

    /** 裁判台接管画布时置真：选中不再推旧两栏屏，刷新也不擅自收窗。 */
    function setCompareActive(on) { compareActive = Boolean(on); }

    function setSelectionListener(fn) { selectionListener = typeof fn === "function" ? fn : null; }

    function setPoolStateListener(fn) {
      poolStateListener = typeof fn === "function" ? fn : null;
      if (poolStateListener) poolStateListener(entries.length, selectedEntry);
    }

    return {
      ACTION_LABELS: ACTION_LABELS,
      backToReview: backToReview,
      chooseTier: chooseTier,
      confirmDelete: confirmDelete,
      onCanvasClosed: onCanvasClosed,
      refresh: refresh,
      reveal: reveal,
      runAction: runAction,
      entries: function () { return entries; },
      select: select,
      selected: selected,
      poolSize: poolSize,
      setCompareActive: setCompareActive,
      setPoolStateListener: setPoolStateListener,
      setSelectionListener: setSelectionListener,
      tierNow: tierNow,
      wire: wire,
    };
  }

  global.JzoEditorPoolPanel = { create: create };
})(window);
