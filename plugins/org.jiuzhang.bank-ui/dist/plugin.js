/**
 * 真题题库视图插件运行时（org.jiuzhang.bank-ui）。
 *
 * 本插件只有界面，没有题库：列表/大纲/待审一律经 jzo-plugin/1 协议向宿主
 * 申请「活跃题库」的数据，宿主再交给题库引擎（app/core/bank.py）查询。
 * 插件拿不到数据库、文件系统与令牌。
 *
 * 右栏面板（ui.params.changed）是筛选的权威来源；本页顶部只保留搜索与刷新，
 * 避免同一条件出现两个写入者。
 *
 * 三个文件按 PLUGIN_SPEC §2.8.1（单文件不得过 800 行）分工：
 * - ui_browse.js：题面渲染——安全富文本、列表行、大纲树与详情；
 * - ui_review.js：待审任务工作台；
 * - plugin.js（本文件）：宿主协议、筛选参数、数据装载、视图装配与命令路由。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.bank-ui";
  var PAGE_SIZE = 12;
  var REQUEST_TIMEOUT_MS = 15000;

  var root = document.getElementById("root");
  var stageMode = false;
  var requestSeq = 0;
  var pending = new Map();
  var loadToken = 0;
  var toastTimer = null;
  var basketIds = Object.create(null);

  var state = {
    grade: "全部",
    difficulty: "全部",
    type: "全部",
    topic: "",
    topicName: "",
    search: "",
    page: 1,
    pageSize: PAGE_SIZE,
    total: 0,
    items: [],
    selected: null,
    showSolution: false,
    loading: false,
    view: "list",
    reviewFlag: "",
    reviewPage: 1,
    reviewPages: 1,
    reviewTotal: 0,
    reviewItems: [],
    reviewSummary: { total: 0, flags: [] },
    reviewLoading: false,
    reviewError: ""
  };

  // ---------- 宿主通信 ----------
  function hostCall(method, payload) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "p" + requestSeq + "_" + Date.now().toString(36);
      var timer = window.setTimeout(function () {
        pending.delete(id);
        reject(new Error("宿主响应超时（" + Math.round(REQUEST_TIMEOUT_MS / 1000) + "s）"));
      }, REQUEST_TIMEOUT_MS);
      pending.set(id, {
        resolve: function (result) { window.clearTimeout(timer); resolve(result); },
        reject: function (error) { window.clearTimeout(timer); reject(error); }
      });
      try {
        window.parent.postMessage({
          protocol: PROTOCOL,
          id: id,
          kind: "request",
          method: method,
          payload: payload || {}
        }, "*");
      } catch (error) {
        pending.delete(id);
        window.clearTimeout(timer);
        reject(error);
      }
    });
  }

  function dock(text) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL,
        kind: "notification",
        event: "region.dock",
        payload: { text: String(text).slice(0, 200) }
      }, "*");
    } catch (error) {
      /* 通知丢一帧不致命 */
    }
  }

  // 向宿主发一个授权事件（三端分离里唯一允许的跨端动作：请求打开录题工作台）
  function publish(event, payload) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL,
        kind: "notification",
        event: event,
        payload: payload || {}
      }, "*");
    } catch (error) {
      /* 跳转丢了不致命，底栏会没声音而已 */
    }
  }

  function openEditor(questionId) {
    if (!questionId) return;
    publish("system.open_editor", { question_id: questionId });
    dock("已请求打开录题工作台：" + questionId);
  }

  function applyParams(values, by) {
    if (!values || typeof values !== "object") return;
    var changed = false;
    ["grade", "difficulty", "type"].forEach(function (key) {
      if (typeof values[key] === "string" && values[key] && values[key] !== state[key]) {
        state[key] = values[key];
        changed = true;
      }
    });
    if (changed) {
      state.page = 1;
      state.showSolution = false;
      loadQuestions();
      dock("题库筛选：" + describeFilters() + "（" + (by === "human" ? "人工" : "同步") + "）");
    }
  }

  function describeFilters() {
    return "年级 " + state.grade + " · 难度 " + state.difficulty + " · 题型 " + state.type +
      (state.topic ? " · 考向「" + state.topicName + "」" : "") +
      (state.search ? " · 关键词「" + state.search + "」" : "");
  }

  /**
   * 军令 #15 任务 3 的落点：AI 只说「去哪、带什么词」，底座把检索词送到这里，
   * 插件改自己的筛选态重查一次。工具栏里的搜索框由 renderAll 从 state.search 回填，
   * 因此这里不伸手碰任何输入框。
   */
  function applyBankQuery(payload) {
    var raw = payload && typeof payload.query === "string" ? payload.query : "";
    var query = raw.trim().slice(0, 100);
    if (!query) {
      dock("宿主送来的题库检索是空的，本视图保持原样。");
      return;
    }
    // 检索词只有列表视图会消费：待审视图下必须先切回列表，
    // 否则 loadQuestions() 白打一次接口、界面还停在原面板，AI 送来的词被静默吞掉。
    if (state.view !== "list") state.view = "list";
    state.search = query;
    state.page = 1;
    state.showSolution = false;
    loadQuestions();
    dock("AI 跳转带来的关键词「" + query + "」已填入搜索框。");
  }

  // ---------- 富文本、列表、大纲树与详情：已拆到 ui_browse.js（PLUGIN_SPEC §2.8.1） ----------
  // 本文件只留「协议 + 数据 + 视图装配 + 命令路由」；题面怎么画交给浏览模块。
  var browse = window.JzoBankBrowse.create({
    state: state,
    hostCall: hostCall,
    dock: dock,
    toast: toast,
    renderAll: renderAll,
    loadQuestions: loadQuestions,
    openEditor: openEditor,
    addToBasket: addToBasket,
    inBasket: function (questionId) { return Boolean(basketIds[questionId]); }
  });
  var el = browse.el;
  var appendRich = browse.appendRich;
  var answerText = browse.answerText;
  var difficultyLabel = browse.difficultyLabel;
  var typeLabel = browse.typeLabel;
  var sourceLine = browse.sourceLine;
  var migrationFlags = browse.migrationFlags;
  var mountPager = browse.mountPager;
  var loadTree = browse.loadTree;
  var renderTree = browse.renderTree;
  var renderList = browse.renderList;
  var renderDetail = browse.renderDetail;

  // ---------- 待审工作台：已拆到 ui_review.js（PLUGIN_SPEC §2.8.1） ----------
  // 面板怎么画交给工作台；本文件只管协议、数据与视图装配。
  // 题块渲染的那几件套由 ui_browse.js 先装配，再转交工作台复用。
  var review = window.JzoBankReview.create({
    state: state,
    root: root,
    hostCall: hostCall,
    dock: dock,
    toast: toast,
    renderAll: renderAll,
    openEditor: openEditor,
    el: el,
    appendRich: appendRich,
    answerText: answerText,
    difficultyLabel: difficultyLabel,
    typeLabel: typeLabel,
    sourceLine: sourceLine,
    migrationFlags: migrationFlags,
    mountPager: mountPager
  });
  var loadReview = review.loadReview;
  var renderReviewPanel = review.renderReviewPanel;

  function renderAll() {
    if (!stageMode || !root) return;
    root.textContent = "";
    var head = el("header", "cb-head");
    head.appendChild(el("h1", "cb-title", "真题题库"));
    head.appendChild(el("p", "cb-sub", "本地 SQLite · 共 " + state.total + " 题 · 左栏点大纲取题，筛选条件以右侧面板为准"));
    var count = el("span", "cb-count", "题篮 " + Object.keys(basketIds).length);
    count.id = "cbBasketCount";
    head.appendChild(count);
    root.appendChild(head);

    var toolbar = el("div", "cb-toolbar");
    var search = document.createElement("input");
    search.className = "cb-search";
    search.type = "search";
    search.placeholder = "搜索题干关键词（回车确认）";
    search.value = state.search;
    search.setAttribute("aria-label", "搜索题干关键词");
    search.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        state.search = search.value.trim().slice(0, 100);
        state.page = 1;
        loadQuestions();
      }
    });
    toolbar.appendChild(search);

    var refresh = el("button", "cb-btn", "刷新");
    refresh.type = "button";
    refresh.disabled = state.loading;
    refresh.setAttribute("aria-busy", String(state.loading));
    // 刷新要刷「正在看的那个视图」：待审视图不消费 state.items，
    // 无脑 loadQuestions() 会让这个视图下的【刷新】点了像没反应。
    refresh.addEventListener("click", function () {
      loadTree();
      if (state.view === "review") loadReview(state.reviewPage);
      else loadQuestions();
    });
    toolbar.appendChild(refresh);

    var views = el("div", "cb-views");
    views.setAttribute("role", "tablist");
    views.setAttribute("aria-label", "题库视图");
    var listButton = el("button", "cb-btn" + (state.view === "list" ? " cb-btn-primary" : ""), "题目列表");
    listButton.type = "button";
    listButton.setAttribute("role", "tab");
    listButton.setAttribute("aria-selected", String(state.view === "list"));
    listButton.addEventListener("click", function () {
      if (state.view !== "list") {
        state.view = "list";
        loadQuestions();
      }
    });
    var reviewCount = state.reviewSummary.total;
    var reviewButton = el("button", "cb-btn" + (state.view === "review" ? " cb-btn-primary" : ""),
      "待审任务" + (reviewCount ? " " + reviewCount : ""));
    reviewButton.type = "button";
    reviewButton.setAttribute("role", "tab");
    reviewButton.setAttribute("aria-selected", String(state.view === "review"));
    reviewButton.setAttribute("data-review-tab", "true");
    reviewButton.addEventListener("click", function () { loadReview(1); });
    views.appendChild(listButton);
    views.appendChild(reviewButton);
    toolbar.appendChild(views);

    var hintLabels = { review: "人工审核：修一条清一条" };
    var hint = el("span", "cb-sub", hintLabels[state.view] || describeFilters());
    hint.setAttribute("data-filter-summary", "true");
    toolbar.appendChild(hint);
    root.appendChild(toolbar);

    var wide = state.view === "review";
    var body = el("div", wide ? "cb-body cb-body-review" : "cb-body");
    if (state.view === "review") {
      renderReviewPanel(body);
    } else {
      renderTree(body);
      renderList(body);
      renderDetail(body);
    }
    root.appendChild(body);
  }

  // ---------- 数据 ----------
  function loadQuestions() {
    if (!stageMode) return;
    var token = ++loadToken;
    state.loading = true;
    renderAll();
    var params = {
      grade: state.grade,
      difficulty: state.difficulty,
      type: state.type,
      topic: state.topic,
      q: state.search,
      page: state.page,
      page_size: state.pageSize
    };
    // 视图插件自己没有题库：永远读「当前活跃 provider」的库，不拿页签 id 猜库。
    return hostCall("bank.active_list", params)
      .then(function (result) {
        if (token !== loadToken) return;
        state.items = (result && result.items) || [];
        state.total = (result && result.total) || 0;
        if (state.selected && !state.items.some(function (item) { return item.id === state.selected.id; })) {
          state.selected = null;
        }
        if (!state.selected && state.items.length) state.selected = state.items[0];
        state.loading = false;
        renderAll();
        dock("题库已载入：" + state.total + " 题（" + describeFilters() + "）");
      })
      .catch(function (error) {
        if (token !== loadToken) return;
        state.loading = false;
        state.items = [];
        state.total = 0;
        renderAll();
        toast("读取题库失败：" + error.message);
        dock("读取题库失败：" + error.message);
      });
  }

  var refreshTimer = null;

  function scheduleRefresh() {
    // 宿主广播本题更新（新旧两个事件名各广播一次），这里去重成一次刷新，避免连打两遍接口
    if (refreshTimer) window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(function () {
      refreshTimer = null;
      if (state.view === "review") loadReview(); else loadQuestions();
    }, 260);
  }

  function loadBasket() {
    return hostCall("basket.list", {})
      .then(function (result) {
        basketIds = Object.create(null);
        ((result && result.items) || []).forEach(function (item) {
          if (item && item.question_id) basketIds[item.question_id] = true;
        });
        renderAll();
      })
      .catch(function () { /* 题篮不可用不影响题库浏览 */ });
  }

  function addToBasket(ids) {
    return hostCall("basket.active_add", { ids: ids })
      .then(function (result) {
        ids.forEach(function (id) { basketIds[id] = true; });
        var total = result && typeof result.total === "number" ? result.total : Object.keys(basketIds).length;
        toast("已加入题篮（共 " + total + " 题）");
        dock("已加入题篮：共 " + total + " 题");
        renderAll();
      })
      .catch(function (error) {
        toast("加入题篮失败：" + error.message);
      });
  }

  function toast(text) {
    var node = root && root.querySelector(".cb-toast");
    if (!node) {
      if (!root) return;
      node = el("div", "cb-toast");
      root.appendChild(node);
    }
    node.textContent = text;
    node.setAttribute("data-show", "true");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      node.setAttribute("data-show", "false");
    }, 2200);
  }

  // ---------- 能力路由字典（军令 #20） ----------
  var FILTER_SETS = {
    grade: ["全部", "高一", "高二", "高三"],
    difficulty: ["全部", "L1", "L2", "L3", "L4"],
    type: ["全部", "single_choice", "multiple_choice", "fill_blank", "solution"]
  };
  var QUESTION_ID_RE = /^q_[A-Za-z0-9_-]{1,78}$/;

  function commandReject(source, message, code, text) {
    respond(source, message.id, false, null, code, text);
  }

  function rejectUnknown(context, allowed) {
    var unknown = Object.keys(context).filter(function (key) {
      return allowed.indexOf(key) < 0;
    });
    return unknown.length ? "不认识的参数：" + unknown.join("、") : "";
  }

  function filterFromContext(context) {
    var result = { ok: true, values: {} };
    var unknown = rejectUnknown(context, ["grade", "difficulty", "type", "search"]);
    if (unknown) {
      result.ok = false;
      result.message = unknown;
      return result;
    }
    Object.keys(FILTER_SETS).forEach(function (key) {
      if (context[key] === undefined) return;
      if (typeof context[key] !== "string" || FILTER_SETS[key].indexOf(context[key]) < 0) {
        result.ok = false;
        result.message = key + " 只接受 " + FILTER_SETS[key].join("/");
        return;
      }
      result.values[key] = context[key];
    });
    if (context.search !== undefined
        && (typeof context.search !== "string" || context.search.length > 100)) {
      result.ok = false;
      result.message = "search 必须是不超过 100 字的字符串";
    }
    return result;
  }

  function handleCommandExecute(source, message) {
    var payload = message.payload || {};
    var commandId = typeof payload.command_id === "string" ? payload.command_id : "";
    var context = payload.context && typeof payload.context === "object" ? payload.context : {};

    if (commandId === "org.jiuzhang.action.view.filter_questions") {
      var parsed = filterFromContext(context);
      if (!parsed.ok) return commandReject(source, message, "BAD_PARAMS", parsed.message);
      Object.keys(parsed.values).forEach(function (key) { state[key] = parsed.values[key]; });
      if (typeof context.search === "string") state.search = context.search.trim().slice(0, 100);
      state.view = "list";
      state.page = 1;
      state.showSolution = false;
      var reload = loadQuestions();
      if (!reload || typeof reload.then !== "function") {
        return commandReject(source, message, "COMMAND_BUSY", "题库正在加载，请稍后再试");
      }
      reload.then(function () {
        respond(source, message.id, true, {
          total: state.total,
          filters: {
            grade: state.grade,
            difficulty: state.difficulty,
            type: state.type,
            search: state.search
          }
        });
      });
      return;
    }

    if (commandId === "org.jiuzhang.action.view.review_queue") {
      var reviewUnknown = rejectUnknown(context, ["flag"]);
      if (reviewUnknown) {
        return commandReject(source, message, "BAD_PARAMS", reviewUnknown);
      }
      if (context.flag !== undefined && (typeof context.flag !== "string" || context.flag.length > 40)) {
        return commandReject(source, message, "BAD_PARAMS", "flag 必须是不超过 40 字的字符串");
      }
      state.reviewFlag = typeof context.flag === "string" ? context.flag.trim() : "";
      var reviewCall = loadReview(1);
      if (!reviewCall || typeof reviewCall.then !== "function") {
        return commandReject(source, message, "COMMAND_BUSY", "待审队列正在加载，请稍后再试");
      }
      reviewCall.then(function () {
        respond(source, message.id, true, {
          total: state.reviewTotal,
          pages: state.reviewPages,
          flag: state.reviewFlag,
          flags: state.reviewSummary.flags || []
        });
      });
      return;
    }

    commandReject(source, message, "UNKNOWN_COMMAND", "未声明的方法：" + commandId);
  }

  // ---------- 协议 ----------
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    if (message.kind === "response" && pending.has(message.id)) {
      var waiter = pending.get(message.id);
      pending.delete(message.id);
      if (message.ok) waiter.resolve(message.result || {});
      else waiter.reject(new Error((message.error && message.error.message) || "宿主返回失败"));
      return;
    }

    if (message.kind === "notification") {
      if (message.event === "ui.params.changed") {
        var payload = message.payload || {};
        applyParams(payload.values, payload.by);
      }
      if (message.event === "system.question_updated" || message.event === "question.updated") {
        // 回流刷新：录题端改完题宿主广播一声，这里静默重取，不用老师按 F5
        scheduleRefresh();
      }
      if (message.event === "system.bank_query") {
        applyBankQuery(message.payload || {});
      }
      return;
    }

    if (message.kind !== "request") return;
    if (message.method === "plugin.activate") {
      stageMode = true;
      root.hidden = false;
      var values = (message.payload && message.payload.values) || {};
      applyParams(values, "init");
      loadTree();
      loadBasket().then(function () {
        if (!state.selected) loadQuestions();
      });
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
    }
    if (message.method === "plugin.deactivate") {
      root.hidden = true;
      return respond(event.source, message.id, true, { ready: false });
    }
    if (message.method === "question.render") {
      var question = (message.payload && message.payload.question) || {};
      return respond(event.source, message.id, true, {
        html: '<article class="cb-question">' + escapeHtml(question.stem || "") + "</article>",
        height: 120
      });
    }
    if (message.method === "command.execute") {
      return handleCommandExecute(event.source, message);
    }
    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD", "未实现的方法：" + message.method);
  });

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function respond(target, id, ok, result, code, message) {
    var packet = { protocol: PROTOCOL, id: id, kind: "response", ok: ok };
    if (ok) packet.result = result || {};
    else packet.error = { code: code || "ERROR", message: message || "失败", retryable: false };
    try { target.postMessage(packet, "*"); } catch (error) { /* 宿主已走 */ }
  }

  // 独立打开（无宿主）时给一条明确说明，不假装有数据
  if (window.parent === window && root) {
    root.hidden = false;
    root.appendChild(el("p", "cb-empty", "请从九章算子工作台左侧打开「真题题库」；插件单独打开时拿不到宿主题库。"));
  }
})();
