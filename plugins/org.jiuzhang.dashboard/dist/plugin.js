/**
 * 数据看板插件：四张数据卡片 + 365 天绿格子热力图 + 最近录入 5 题。
 *
 * 全部原生 DOM 渲染，无框架、无 iframe、无远程资源；数据只走宿主开放的两条
 * 只读通道 bank.dashboard_stats / bank.dashboard_heatmap（API_REFERENCE §2.12/§2.13）。
 * 点击最近题目发 system.open_bank 通知，由宿主打开活跃题库页签——插件之间不直连。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var REQUEST_TIMEOUT_MS = 15000;
  var REFRESH_DEBOUNCE_MS = 280;   // 宿主双名广播（system.question_updated / question.updated），去重

  var DIFFICULTY_LABELS = { L1: "基础", L2: "中档", L3: "难", L4: "压轴" };
  var TYPE_LABELS = {
    single_choice: "单选", multiple_choice: "多选",
    fill_blank: "填空", solution: "解答"
  };

  var root = document.getElementById("root");
  var seq = 0;
  var pending = new Map();
  var refreshTimer = 0;
  var activated = false;

  // ---------- 宿主通道 ----------
  function call(method, payload) {
    return new Promise(function (resolve, reject) {
      seq += 1;
      // 请求 id 绝不带点号：宿主要求 ^[A-Za-z0-9_-]{1,80}$（PLUGIN_SPEC §2.8）
      var id = "p" + seq + "_" + Date.now().toString(36);
      var timer = window.setTimeout(function () {
        pending.delete(id);
        reject(new Error(method + " 超时（15s）"));
      }, REQUEST_TIMEOUT_MS);
      pending.set(id, { resolve: resolve, reject: reject });
      window.parent.postMessage({
        protocol: PROTOCOL, id: id, kind: "request",
        method: method, payload: payload || {}
      }, "*");
      // resolve/reject 时统一清 timer
      var wrapped = pending.get(id);
      wrapped.resolve = function (value) { window.clearTimeout(timer); resolve(value); };
      wrapped.reject = function (error) { window.clearTimeout(timer); reject(error); };
    });
  }

  function notifyHost(event, payload) {
    window.parent.postMessage({
      protocol: PROTOCOL, kind: "notification", event: event, payload: payload || {}
    }, "*");
  }

  function dock(text) {
    notifyHost("region.dock", { text: text });
  }

  function reply(target, id, result) {
    target.postMessage({ protocol: PROTOCOL, id: id, kind: "response", ok: true, result: result }, "*");
  }

  function fail(target, id, code, message) {
    target.postMessage({
      protocol: PROTOCOL, id: id, kind: "response", ok: false,
      error: { code: code, message: message, retryable: false }
    }, "*");
  }

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  // ---------- 渲染 ----------
  function levelOf(count) {
    if (count <= 0) return 0;
    if (count <= 2) return 1;
    if (count <= 5) return 2;
    if (count <= 9) return 3;
    return 4;
  }

  function buildSkeleton() {
    root.textContent = "";
    root.appendChild(el("h1", "db-title", "数据看板"));
    var sub = el("p", "db-sub", "录题战绩一览 · 数据来自当前活跃题库（只读）");
    root.appendChild(sub);

    var cards = el("div", "db-cards");
    cards.id = "dbCards";
    ["total", "today", "pending", "stored"].forEach(function (kind) {
      var card = el("div", "db-card");
      card.setAttribute("data-kind", kind);
      card.appendChild(el("div", "db-card-label", ""));
      card.appendChild(el("div", "db-card-value", "—"));
      cards.appendChild(card);
    });
    root.appendChild(cards);

    var heatPanel = el("section", "db-heatmap-panel");
    heatPanel.appendChild(el("h2", "db-panel-title", "过去 365 天录题战绩"));
    var scroll = el("div", "db-heatmap-scroll");
    var grid = el("div", "db-heatmap");
    grid.id = "dbHeatmap";
    grid.setAttribute("role", "img");
    grid.setAttribute("aria-label", "过去 365 天按日入库数量热力图");
    scroll.appendChild(grid);
    heatPanel.appendChild(scroll);
    var legend = el("div", "db-legend");
    legend.appendChild(el("span", "", "少"));
    [0, 1, 2, 3, 4].forEach(function (level) {
      var cell = el("span", "db-cell");
      cell.setAttribute("data-level", String(level));
      legend.appendChild(cell);
    });
    legend.appendChild(el("span", "", "多"));
    heatPanel.appendChild(legend);
    root.appendChild(heatPanel);

    var recentPanel = el("section", "db-recent-panel");
    recentPanel.appendChild(el("h2", "db-panel-title", "最近录入"));
    var list = el("ul", "db-recent-list");
    list.id = "dbRecent";
    recentPanel.appendChild(list);
    root.appendChild(recentPanel);

    root.hidden = false;
  }

  function showError(message) {
    var box = el("div", "db-error");
    box.setAttribute("role", "alert");
    box.textContent = message;
    root.insertBefore(box, root.children[1] || null);
  }

  function clearError() {
    var old = root.querySelector(".db-error");
    if (old && old.parentNode) old.parentNode.removeChild(old);
  }

  function renderStats(stats) {
    var cards = document.getElementById("dbCards");
    if (!cards) return;
    var items = [
      { kind: "total", label: "总题数", value: stats.total_questions },
      { kind: "today", label: "今日入库", value: stats.today_added },
      { kind: "pending", label: "待审核", value: stats.pending_review },
      { kind: "stored", label: "已落库", value: stats.stored_total }
    ];
    var cardsNodes = cards.querySelectorAll(".db-card");
    items.forEach(function (item, index) {
      var card = cardsNodes[index];
      if (!card) return;
      card.querySelector(".db-card-label").textContent = item.label;
      card.querySelector(".db-card-value").textContent =
        typeof item.value === "number" ? String(item.value) : "—";
    });
    renderRecent(stats.recent || []);
  }

  function renderRecent(recent) {
    var list = document.getElementById("dbRecent");
    if (!list) return;
    list.textContent = "";
    if (!recent.length) {
      var empty = el("li", "db-empty", "题库还是空的——去录题工作台录入第一题吧。");
      list.appendChild(empty);
      return;
    }
    recent.forEach(function (item) {
      var li = el("li", "db-recent-item");
      var button = el("button", "db-recent-link");
      button.type = "button";
      button.appendChild(el("span", "db-recent-stem", item.stem || item.id));
      button.appendChild(el("span", "db-tag", TYPE_LABELS[item.type] || item.type || ""));
      button.appendChild(el("span", "db-tag", DIFFICULTY_LABELS[item.difficulty] || item.difficulty || ""));
      var day = String(item.created_at || "").slice(0, 10);
      if (day) button.appendChild(el("span", "db-tag", day));
      button.addEventListener("click", function () {
        // 跳转由宿主完成：打开活跃题库页签（插件之间不直连，AGENTS 铁律二）
        notifyHost("system.open_bank", { question_id: item.id, from: "org.jiuzhang.dashboard" });
        dock("正在跳转到题库，题目 " + item.id);
      });
      button.setAttribute("aria-label", "打开题库查看：" + (item.stem || item.id));
      li.appendChild(button);
      list.appendChild(li);
    });
  }

  function renderHeatmap(days) {
    var grid = document.getElementById("dbHeatmap");
    if (!grid || !Array.isArray(days)) return;
    grid.textContent = "";
    var fragment = document.createDocumentFragment();
    // 把窗口对齐到整周：最前面补空格子，让每列都是「周一到周日」
    var pad = 0;
    if (days.length) {
      var first = new Date(days[0].date + "T00:00:00Z");
      pad = (first.getUTCDay() + 6) % 7;   // 周一为一周之始
    }
    for (var i = 0; i < pad; i += 1) {
      var blank = el("span", "db-cell");
      blank.style.visibility = "hidden";
      fragment.appendChild(blank);
    }
    days.forEach(function (cell) {
      var node = el("span", "db-cell");
      node.setAttribute("data-level", String(levelOf(cell.count)));
      node.setAttribute("data-date", cell.date);
      node.title = cell.date + "：入库 " + cell.count + " 题";
      fragment.appendChild(node);
    });
    grid.appendChild(fragment);
  }

  function loadAll(firstLoad) {
    return Promise.all([
      call("bank.dashboard_stats"),
      call("bank.dashboard_heatmap")
    ]).then(function (results) {
      clearError();
      renderStats(results[0] || {});
      renderHeatmap(results[1]);
      if (firstLoad) {
        dock("数据看板已就绪：共 " + (results[0] || {}).total_questions + " 题，今日入库 "
          + (results[0] || {}).today_added + " 题。");
      }
    }).catch(function (error) {
      clearError();
      showError("看板数据加载失败：" + error.message + "（底座其它功能不受影响）");
      if (firstLoad) dock("数据看板加载失败：" + error.message);
    });
  }

  function scheduleRefresh() {
    if (!activated) return;
    window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(function () { loadAll(false); }, REFRESH_DEBOUNCE_MS);
  }

  // ---------- 协议入口 ----------
  window.addEventListener("message", function (event) {
    var msg = event.data;
    if (!msg || msg.protocol !== PROTOCOL) return;

    if (msg.kind === "response") {
      var waiter = pending.get(msg.id);
      if (!waiter) return;
      pending.delete(msg.id);
      if (msg.ok) waiter.resolve(msg.result || {});
      else waiter.reject(new Error((msg.error && msg.error.message) || (msg.error && msg.error.code) || "宿主返回失败"));
      return;
    }

    if (msg.kind === "notification") {
      // 幂等：重复的更新事件只是再刷一次数据，结果一致
      if (msg.event === "system.question_updated" || msg.event === "question.updated") {
        scheduleRefresh();
      }
      return;
    }

    if (msg.kind !== "request") return;

    try {
      if (msg.method === "plugin.activate") {
        activated = true;
        if (!root.hidden && document.getElementById("dbCards")) {
          // 休眠后重新激活：骨架还在，只刷数据
          loadAll(false);
        } else {
          buildSkeleton();
          loadAll(true);
        }
        reply(event.source, msg.id, { ready: true, plugin_id: "org.jiuzhang.dashboard" });
        return;
      }
      if (msg.method === "plugin.deactivate") {
        activated = false;
        window.clearTimeout(refreshTimer);
        reply(event.source, msg.id, { ready: false });
        return;
      }
      if (msg.method === "question.render") {
        var question = (msg.payload && msg.payload.question) || {};
        if (typeof question.stem !== "string") {
          fail(event.source, msg.id, "INVALID_PAYLOAD", "题目缺少 stem。");
          return;
        }
        var html = '<article class="db-rendered">' + escapeHtml(question.stem) + "</article>";
        reply(event.source, msg.id, { html: html, height: 96 });
        return;
      }
      if (msg.method === "theme.changed" || msg.method === "locale.changed"
          || msg.method === "question.updated") {
        reply(event.source, msg.id, { accepted: true });
        return;
      }
      fail(event.source, msg.id, "UNSUPPORTED_METHOD", "未实现的方法：" + String(msg.method));
    } catch (error) {
      fail(event.source, msg.id, "INTERNAL_ERROR", "插件内部错误，请重试。");
    }
  });
})();
