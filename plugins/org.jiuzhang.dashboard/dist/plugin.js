/**
 * 数据看板插件：四张数据卡片 + 近一周/近一月/近一年绿格子热力图 + 最近录入 5 题。
 *
 * 画布（stage.center）画战绩；右栏（sidebar.right）铺本插件专属的字典小标签。
 * 全部原生 DOM 渲染，无框架、无 iframe、无远程资源；数据只走宿主开放的只读通道
 * bank.dashboard_stats / bank.dashboard_heatmap 与 dict.catalog / dict.open。
 * 点小标签由宿主把字典表原地铺进当前画布，再点同一枚即收回看板——不新开页签。
 * 点击最近题目发 system.open_editor 通知，由宿主打开录题工作台并载入该题——插件之间不直连。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var REQUEST_TIMEOUT_MS = 15000;
  var REFRESH_DEBOUNCE_MS = 280;   // 宿主双名广播（system.question_updated / question.updated），去重

  var PLUGIN_ID = "org.jiuzhang.dashboard";
  var DIFFICULTY_LABELS = { L1: "基础", L2: "中档", L3: "难", L4: "压轴" };
  var TYPE_LABELS = {
    single_choice: "单选", multiple_choice: "多选",
    fill_blank: "填空", solution: "解答"
  };

  // 热力图时间档位：后端一次返回 365 天，切档只在前端按日期切片，不再往返请求。
  var HEAT_RANGES = [
    { key: "week", label: "近一周", title: "近一周", days: 7 },
    { key: "month", label: "近一月", title: "近一月", days: 30 },
    { key: "year", label: "近一年", title: "过去 365 天", days: 365 }
  ];
  var DEFAULT_HEAT_RANGE = "year";
  var WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];

  var root = document.getElementById("root");
  var seq = 0;
  var pending = new Map();
  var refreshTimer = 0;
  var activated = false;
  var activeSlot = "";
  var heatRange = DEFAULT_HEAT_RANGE;
  var heatDays = [];

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
      pending.set(id, {
        resolve: function (value) { window.clearTimeout(timer); resolve(value); },
        reject: function (error) { window.clearTimeout(timer); reject(error); }
      });
      window.parent.postMessage({
        protocol: PROTOCOL, id: id, kind: "request",
        method: method, payload: payload || {}
      }, "*");
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

  // ---------- 右栏（sidebar.right）：全局设置 + 三大主分类 ----------
  // 具体渲染在 rail.js：插件不碰浏览器存储，全局设置经宿主 dict.globals_* 通道。
  function buildDictNav() {
    root.textContent = "";
    window.DbRail.mount(root, { call: call, dock: dock, el: el });
    root.hidden = false;
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
    var head = el("div", "db-panel-head");
    var title = el("h2", "db-panel-title", heatSpec().title + "录题战绩");
    title.id = "dbHeatTitle";
    head.appendChild(title);
    var sw = el("div", "db-range-switch");
    sw.id = "dbRangeSwitch";
    sw.setAttribute("role", "group");
    sw.setAttribute("aria-label", "热力图时间范围");
    HEAT_RANGES.forEach(function (spec) {
      var button = el("button", "db-range-btn", spec.label);
      button.type = "button";
      button.setAttribute("data-range", spec.key);
      button.setAttribute("aria-pressed", String(spec.key === heatRange));
      button.addEventListener("click", function () { setHeatRange(spec.key); });
      sw.appendChild(button);
    });
    head.appendChild(sw);
    heatPanel.appendChild(head);

    var scroll = el("div", "db-heatmap-scroll");
    var grid = el("div", "db-heatmap db-heatmap--" + heatRange);
    grid.id = "dbHeatmap";
    grid.setAttribute("role", "img");
    grid.setAttribute("aria-label", heatSpec().title + "按日入库数量热力图");
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

  function num(v) {
    return typeof v === "number" ? String(v) : "—";
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
      card.querySelector(".db-card-value").textContent = num(item.value);
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
        // 跳转由宿主完成：打开录题工作台并载入该题（插件之间不直连，AGENTS 铁律二）
        notifyHost("system.open_editor", { question_id: item.id, from: "org.jiuzhang.dashboard" });
        dock("正在跳转到录题工作台，题目 " + item.id);
      });
      button.setAttribute("aria-label", "在录题工作台打开：" + (item.stem || item.id));
      li.appendChild(button);
      list.appendChild(li);
    });
  }

  function heatSpec(key) {
    var wanted = key || heatRange;
    for (var i = 0; i < HEAT_RANGES.length; i += 1) {
      if (HEAT_RANGES[i].key === wanted) return HEAT_RANGES[i];
    }
    return HEAT_RANGES[HEAT_RANGES.length - 1];
  }

  function weekdayIndex(date) {
    var day = new Date(String(date) + "T00:00:00Z");
    return (day.getUTCDay() + 6) % 7;   // 周一为一周之始
  }

  function cellNode(cell, className) {
    var node = el("span", className || "db-cell");
    node.setAttribute("data-level", String(levelOf(cell.count)));
    node.setAttribute("data-date", cell.date);
    node.title = cell.date + "：" + cell.count + " 题";
    node.setAttribute("aria-label", cell.date + "，" + cell.count + " 题");
    return node;
  }

  function blankCell(className) {
    var blank = el("span", className || "db-cell");
    blank.style.visibility = "hidden";
    return blank;
  }

  function appendYearGrid(fragment, days) {
    // 把窗口对齐到整周：最前面补空格子，让每列都是「周一到周日」
    var pad = days.length ? weekdayIndex(days[0].date) : 0;
    for (var i = 0; i < pad; i += 1) fragment.appendChild(blankCell());
    days.forEach(function (cell) { fragment.appendChild(cellNode(cell)); });
  }

  function appendMonthGrid(fragment, days) {
    // 固定 5 行 × 7 列：30 天排满前 4 行多一点，末尾补空格子保持网格齐整
    days.forEach(function (cell) { fragment.appendChild(cellNode(cell)); });
    var slots = Math.max(35, Math.ceil(days.length / 7) * 7);
    for (var i = days.length; i < slots; i += 1) fragment.appendChild(blankCell());
  }

  function appendWeekGrid(fragment, days) {
    days.forEach(function (cell) {
      var node = cellNode(cell, "db-cell db-cell--lg");
      node.appendChild(el("span", "db-cell-weekday", WEEKDAY_LABELS[weekdayIndex(cell.date)]));
      node.appendChild(el("span", "db-cell-count", String(cell.count)));
      fragment.appendChild(node);
    });
  }

  function drawHeatmap() {
    var grid = document.getElementById("dbHeatmap");
    if (!grid) return;
    var spec = heatSpec();
    var days = heatDays.length > spec.days ? heatDays.slice(heatDays.length - spec.days) : heatDays.slice();
    grid.textContent = "";
    grid.className = "db-heatmap db-heatmap--" + heatRange;
    grid.setAttribute("aria-label", spec.title + "按日入库数量热力图");
    var fragment = document.createDocumentFragment();
    if (heatRange === "week") appendWeekGrid(fragment, days);
    else if (heatRange === "month") appendMonthGrid(fragment, days);
    else appendYearGrid(fragment, days);
    grid.appendChild(fragment);
  }

  function setHeatRange(key) {
    var spec = heatSpec(key);
    if (spec.key === heatRange) return;
    heatRange = spec.key;
    var title = document.getElementById("dbHeatTitle");
    if (title) title.textContent = spec.title + "录题战绩";
    var buttons = document.querySelectorAll(".db-range-btn");
    for (var i = 0; i < buttons.length; i += 1) {
      buttons[i].setAttribute("aria-pressed",
        String(buttons[i].getAttribute("data-range") === heatRange));
    }
    drawHeatmap();
  }

  function renderHeatmap(days) {
    if (!Array.isArray(days)) return;
    heatDays = days;
    drawHeatmap();
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
        var stats = results[0] || {};
        dock("数据看板已就绪：共 " + num(stats.total_questions) + " 题，今日入库 "
          + num(stats.today_added) + " 题。");
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
        activeSlot = (msg.payload && msg.payload.slot) || "stage.center";
        if (activeSlot !== "stage.center") {
          // 右栏那一帧只画本插件自己的字典导航，不拉看板统计。
          buildDictNav();
          reply(event.source, msg.id, { ready: true, plugin_id: PLUGIN_ID, slot: activeSlot });
          return;
        }
        activated = true;
        if (!root.hidden && document.getElementById("dbCards")) {
          // 休眠后重新激活：骨架还在，只刷数据
          loadAll(false);
        } else {
          buildSkeleton();
          loadAll(true);
        }
        reply(event.source, msg.id, { ready: true, plugin_id: PLUGIN_ID, slot: activeSlot });
        return;
      }
      if (msg.method === "plugin.deactivate") {
        if (activeSlot === "stage.center") {
          activated = false;
          window.clearTimeout(refreshTimer);
        } else {
          root.hidden = true;
        }
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
