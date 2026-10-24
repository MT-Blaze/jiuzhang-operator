/**
 * 题库浏览（org.jiuzhang.bank-browser）。
 *
 * 左树右表：左栏按教材目录懒展开，点节点即按该子树筛题；顶部搜索永远跨当前
 * 活跃题库查；卡片上的【加入题篮】与【去编辑】只发宿主通道——插件之间不直连，
 * 编辑跳转由宿主开录题页签并注入题号（AGENTS 铁律二）。
 *
 * 边界：题目只经 bank.active_list / bank.topics / basket.list 读取，入篮走
 * basket.active_add；插件不碰数据库、文件系统、浏览器本地存储，也不读宿主 DOM。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.bank-browser";
  var PAGE_SIZE = 12;
  var REQUEST_TIMEOUT_MS = 20000;
  var SEARCH_MAX = 100;
  var RELOAD_DEBOUNCE_MS = 500;

  var TYPE_LABELS = {
    single_choice: "单选",
    multiple_choice: "多选",
    fill_blank: "填空",
    solution: "解答",
    proof: "证明",
    unknown: "待定"
  };

  var DIFFICULTY_LABELS = {
    L1: "L1 基础",
    L2: "L2 中档",
    L3: "L3 难",
    L4: "L4 压轴"
  };

  var root = document.getElementById("bbRoot");
  var scopeEl = document.getElementById("bbScope");
  var searchInput = document.getElementById("bbSearch");
  var searchBtn = document.getElementById("bbSearchBtn");
  var clearBtn = document.getElementById("bbClear");
  var totalEl = document.getElementById("bbTotal");
  var refreshBtn = document.getElementById("bbRefresh");
  var treeEl = document.getElementById("bbTree");
  var treeEmpty = document.getElementById("bbTreeEmpty");
  var treeReset = document.getElementById("bbTreeReset");
  var crumbEl = document.getElementById("bbCrumb");
  var statusEl = document.getElementById("bbStatus");
  var listEl = document.getElementById("bbList");
  var emptyEl = document.getElementById("bbEmpty");
  var pagerEl = document.getElementById("bbPager");
  var prevBtn = document.getElementById("bbPrev");
  var nextBtn = document.getElementById("bbNext");
  var pageInfo = document.getElementById("bbPageInfo");

  var state = {
    topicId: "",
    topicLabel: "",
    q: "",
    page: 1,
    pageSize: PAGE_SIZE,
    total: 0,
    totalPages: 1,
    items: [],
    basket: {},
    pendingAdd: {}
  };

  var topicCache = {};
  var selectedNodeId = "";
  var requestSeq = 0;
  var pending = new Map();
  var loadToken = 0;
  var statusTimer = 0;
  var reloadTimer = 0;
  var booted = false;
  var mathCache = new Map();

  // ---------- 宿主通信 ----------
  function hostCall(method, payload) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "b" + requestSeq + "_" + Date.now().toString(36);
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
          protocol: PROTOCOL, id: id, kind: "request", method: method, payload: payload || {}
        }, "*");
      } catch (error) {
        pending.delete(id);
        window.clearTimeout(timer);
        reject(error);
      }
    });
  }

  function respond(source, id, ok, result, code, message) {
    var packet = { protocol: PROTOCOL, id: id, kind: "response", ok: ok };
    if (ok) packet.result = result === undefined ? {} : result;
    else packet.error = { code: code || "PLUGIN_ERROR", message: message || "插件拒绝了请求" };
    try {
      source.postMessage(packet, "*");
    } catch (error) {
      // 宿主帧已销毁
    }
  }

  function notifyHost(event, payload) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: event, payload: payload || {}
      }, "*");
    } catch (error) {
      // 通知丢一帧不致命
    }
  }

  function dock(text) {
    notifyHost("region.dock", { text: String(text).slice(0, 200) });
  }

  function setStatus(text, warn) {
    statusEl.textContent = text || "";
    statusEl.className = warn ? "bb-status is-warn" : "bb-status";
    window.clearTimeout(statusTimer);
    if (text) {
      statusTimer = window.setTimeout(function () { statusEl.textContent = ""; }, 6000);
    }
  }

  // ---------- 原生富文本 ----------
  var MATH_RE = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$[^$\n]+?\$)/g;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function mathSpan(tex, display) {
    var node = document.createElement(display ? "div" : "span");
    node.className = display ? "bb-math-block" : "bb-math";
    var key = (display ? "D:" : "I:") + tex;
    var html = mathCache.get(key);
    if (html === undefined) {
      html = "";
      if (window.katex && typeof window.katex.renderToString === "function") {
        try {
          html = window.katex.renderToString(tex, {
            displayMode: Boolean(display),
            throwOnError: false,
            trust: false,
            strict: "ignore"
          });
        } catch (error) {
          html = "";
        }
      }
      mathCache.set(key, html);
    }
    if (html) node.innerHTML = html;
    else node.textContent = (display ? "$$" : "$") + tex + (display ? "$$" : "$");
    return node;
  }

  function renderRich(target, source) {
    var text = String(source == null ? "" : source);
    var last = 0;
    var match;
    MATH_RE.lastIndex = 0;
    while ((match = MATH_RE.exec(text)) !== null) {
      if (match.index > last) target.appendChild(document.createTextNode(text.slice(last, match.index)));
      var token = match[0];
      if (token.slice(0, 2) === "$$") target.appendChild(mathSpan(token.slice(2, -2), true));
      else if (token.slice(0, 2) === "\\[") target.appendChild(mathSpan(token.slice(2, -2), true));
      else if (token.slice(0, 2) === "\\(") target.appendChild(mathSpan(token.slice(2, -2), false));
      else target.appendChild(mathSpan(token.slice(1, -1), false));
      last = match.index + token.length;
    }
    if (last < text.length) target.appendChild(document.createTextNode(text.slice(last)));
  }

  function typeLabel(value) {
    return TYPE_LABELS[value] || "待定";
  }

  function difficultyLabel(value) {
    return DIFFICULTY_LABELS[value] || String(value || "未定级");
  }

  function taxonomyLine(taxonomy) {
    var data = taxonomy && typeof taxonomy === "object" ? taxonomy : {};
    var parts = [data.textbook, data.chapter, data.section].filter(function (item) {
      return typeof item === "string" && item;
    });
    if (data.topic) parts.push(data.topic);
    return parts.join(" · ");
  }

  // ---------- 目录树 ----------
  function loadTopics(parentId) {
    var key = parentId || "";
    return hostCall("bank.topics", { parent_id: key }).then(function (result) {
      var items = result && Array.isArray(result.items) ? result.items : [];
      topicCache[key] = items;
      return items;
    });
  }

  function markSelected(id) {
    selectedNodeId = id || "";
    var buttons = treeEl.querySelectorAll(".bb-node-name");
    for (var i = 0; i < buttons.length; i += 1) {
      if (buttons[i].getAttribute("data-topic-id") === selectedNodeId) {
        buttons[i].setAttribute("aria-current", "true");
      } else {
        buttons[i].removeAttribute("aria-current");
      }
    }
  }

  function nodeElement(node) {
    var wrap = el("div", "bb-node");
    wrap.setAttribute("role", "treeitem");
    if (node.has_children) wrap.setAttribute("aria-expanded", "false");

    var row = el("div", "bb-node-row");
    var children = el("div", "bb-children");
    children.hidden = true;
    children.setAttribute("role", "group");

    if (node.has_children) {
      var twisty = el("button", "bb-twisty", "▶");
      twisty.type = "button";
      twisty.setAttribute("aria-label", "展开 " + node.name);
      twisty.setAttribute("aria-expanded", "false");
      twisty.addEventListener("click", function () {
        var open = twisty.getAttribute("aria-expanded") === "true";
        if (open) {
          twisty.setAttribute("aria-expanded", "false");
          twisty.textContent = "▶";
          wrap.setAttribute("aria-expanded", "false");
          children.hidden = true;
          return;
        }
        twisty.setAttribute("aria-expanded", "true");
        twisty.textContent = "▼";
        wrap.setAttribute("aria-expanded", "true");
        children.hidden = false;
        if (children.getAttribute("data-loaded") === "1") return;
        children.setAttribute("data-loaded", "1");
        loadTopics(node.id).then(function (items) {
          renderLevel(items, children);
          if (!items.length) {
            children.removeAttribute("data-loaded");
            var hint = el("p", "bb-hint", "此层暂无下级目录");
            children.appendChild(hint);
          }
        }, function (error) {
          children.removeAttribute("data-loaded");
          setStatus("目录加载失败：" + error.message, true);
        });
      });
      row.appendChild(twisty);
    } else {
      var spacer = el("span", "bb-twisty-spacer");
      spacer.setAttribute("aria-hidden", "true");
      row.appendChild(spacer);
    }

    var nameBtn = el("button", "bb-node-name", node.name);
    nameBtn.type = "button";
    nameBtn.setAttribute("data-topic-id", node.id);
    nameBtn.title = node.name + "（" + (node.question_count || 0) + " 题）";
    if (node.id === selectedNodeId) nameBtn.setAttribute("aria-current", "true");
    nameBtn.addEventListener("click", function () { selectTopic(node); });
    row.appendChild(nameBtn);
    row.appendChild(el("span", "bb-node-count", String(node.question_count || 0)));

    wrap.appendChild(row);
    wrap.appendChild(children);
    return wrap;
  }

  function renderLevel(items, host) {
    host.textContent = "";
    items.forEach(function (node) { host.appendChild(nodeElement(node)); });
  }

  function loadTree() {
    treeEl.textContent = "";
    treeEl.setAttribute("aria-busy", "true");
    loadTopics("").then(function (items) {
      treeEl.removeAttribute("aria-busy");
      treeEmpty.hidden = items.length > 0;
      treeEmpty.textContent = "目录为空，可直接用上方搜索。";
      if (items.length) renderLevel(items, treeEl);
    }, function (error) {
      treeEl.removeAttribute("aria-busy");
      treeEmpty.hidden = false;
      treeEmpty.textContent = "目录加载失败：" + error.message;
      setStatus("目录加载失败：" + error.message, true);
    });
  }

  function selectTopic(node) {
    state.topicId = node.id;
    state.topicLabel = node.name;
    state.q = "";
    state.page = 1;
    searchInput.value = "";
    markSelected(node.id);
    updateCrumb();
    loadPage();
  }

  function showAll() {
    state.topicId = "";
    state.topicLabel = "";
    state.q = "";
    state.page = 1;
    searchInput.value = "";
    markSelected("");
    updateCrumb();
    loadPage();
  }

  function updateCrumb() {
    if (state.q) crumbEl.textContent = "搜索「" + state.q + "」";
    else if (state.topicLabel) crumbEl.textContent = "目录 · " + state.topicLabel;
    else crumbEl.textContent = "全部题目";
    clearBtn.hidden = !(state.q || state.topicId);
  }

  // ---------- 题目列表 ----------
  function loadPage() {
    loadToken += 1;
    var token = loadToken;
    setStatus("加载中…");
    var payload = { page: state.page, page_size: state.pageSize };
    if (state.topicId) payload.topic = state.topicId;
    if (state.q) payload.q = state.q;
    hostCall("bank.active_list", payload).then(function (result) {
      if (token !== loadToken) return;
      state.items = result && Array.isArray(result.items) ? result.items : [];
      state.total = Number(result && result.total) || 0;
      state.totalPages = Math.max(1, Number(result && result.total_pages) || 1);
      if (state.page > state.totalPages) {
        state.page = state.totalPages;
        loadPage();
        return;
      }
      renderList();
      renderPager();
      totalEl.textContent = "共 " + state.total + " 题";
      setStatus(state.items.length ? "" : "这个范围内没有题目");
    }, function (error) {
      if (token !== loadToken) return;
      state.items = [];
      state.total = 0;
      state.totalPages = 1;
      renderList();
      renderPager();
      totalEl.textContent = "共 0 题";
      setStatus("加载失败：" + error.message, true);
    });
  }

  function cardFor(question) {
    var card = el("article", "bb-card");
    card.setAttribute("data-question-id", question.id);

    var head = el("div", "bb-card-head");
    head.appendChild(el("span", "bb-type", typeLabel(question.type)));
    head.appendChild(el("span", "bb-chip", difficultyLabel(question.difficulty)));
    if (question.grade) head.appendChild(el("span", "bb-chip", question.grade));

    var actions = el("div", "bb-card-actions");
    var addBtn = el("button", "bb-add", "加入题篮");
    addBtn.type = "button";
    addBtn.setAttribute("data-question-id", question.id);
    addBtn.addEventListener("click", function () { addToBasket(question, addBtn); });
    var editBtn = el("button", "bb-edit", "去编辑");
    editBtn.type = "button";
    editBtn.addEventListener("click", function () { openEditor(question); });
    actions.appendChild(addBtn);
    actions.appendChild(editBtn);
    head.appendChild(actions);
    card.appendChild(head);

    var stem = el("div", "bb-stem");
    renderRich(stem, question.stem);
    card.appendChild(stem);

    var tax = el("div", "bb-tax", taxonomyLine(question.taxonomy));
    if (!tax.textContent) tax.hidden = true;
    card.appendChild(tax);
    return card;
  }

  function renderList() {
    listEl.textContent = "";
    emptyEl.hidden = state.items.length > 0;
    state.items.forEach(function (question) {
      if (!question || typeof question.id !== "string") return;
      listEl.appendChild(cardFor(question));
    });
    syncBasketButtons();
  }

  function renderPager() {
    pageInfo.textContent = "第 " + state.page + " / " + state.totalPages + " 页";
    prevBtn.disabled = state.page <= 1;
    nextBtn.disabled = state.page >= state.totalPages;
    pagerEl.hidden = state.items.length === 0 && state.total === 0;
  }

  function syncBasketButtons() {
    var buttons = listEl.querySelectorAll(".bb-add");
    for (var i = 0; i < buttons.length; i += 1) {
      var id = buttons[i].getAttribute("data-question-id");
      if (state.pendingAdd[id]) {
        buttons[i].disabled = true;
        buttons[i].textContent = "加入中…";
      } else if (state.basket[id]) {
        buttons[i].disabled = true;
        buttons[i].classList.add("is-in");
        buttons[i].textContent = "已在题篮";
      } else {
        buttons[i].disabled = false;
        buttons[i].classList.remove("is-in");
        buttons[i].textContent = "加入题篮";
      }
    }
  }

  function refreshBasket() {
    return hostCall("basket.list", { expand: false }).then(function (result) {
      var map = {};
      var items = result && Array.isArray(result.items) ? result.items : [];
      items.forEach(function (item) {
        if (item && typeof item.question_id === "string") map[item.question_id] = true;
      });
      state.basket = map;
      syncBasketButtons();
    }, function () {
      // 题篮读失败不挡浏览，按钮保持可点，宿主会再报具体错误
    });
  }

  function loadScope() {
    return hostCall("bank.active_stats", {}).then(function (result) {
      var total = Number(result && result.total) || 0;
      scopeEl.textContent = "全库 " + total + " 题 · 左树筛选 · 全局搜索";
    }, function () {
      // 计数只是抬头，读不到也不挡浏览
    });
  }

  // ---------- 动作 ----------
  function addToBasket(question, button) {
    if (state.basket[question.id] || state.pendingAdd[question.id]) return;
    state.pendingAdd[question.id] = true;
    syncBasketButtons();
    hostCall("basket.active_add", { ids: [question.id] }).then(function (result) {
      delete state.pendingAdd[question.id];
      state.basket[question.id] = true;
      syncBasketButtons();
      var total = result && typeof result.total === "number" ? result.total : null;
      setStatus(total === null ? "已加入题篮" : "已加入题篮 · 题篮共 " + total + " 题");
      dock("已加入题篮：" + question.id);
    }, function (error) {
      delete state.pendingAdd[question.id];
      button.disabled = false;
      syncBasketButtons();
      setStatus("加入失败：" + error.message, true);
    });
  }

  function openEditor(question) {
    notifyHost("system.open_editor", { question_id: question.id });
    setStatus("正在打开录题工作台…");
  }

  function scheduleReload() {
    window.clearTimeout(reloadTimer);
    reloadTimer = window.setTimeout(function () {
      loadPage();
      refreshBasket();
    }, RELOAD_DEBOUNCE_MS);
  }

  // ---------- 交互 ----------
  // 沙箱 iframe 没有 allow-forms，表单提交会被浏览器直接拦下；搜索走按钮点击
  // 与输入框 Enter 两条显式路径，不依赖 form submit（界面语义仍用 role="search"）。
  function submitSearch() {
    var keyword = String(searchInput.value || "").trim().slice(0, SEARCH_MAX);
    if (!keyword) {
      setStatus("先输入要搜索的关键词", true);
      searchInput.focus();
      return;
    }
    state.q = keyword;
    state.topicId = "";
    state.topicLabel = "";
    state.page = 1;
    markSelected("");
    updateCrumb();
    loadPage();
  }

  /**
   * 军令 #15 任务 3 的落点：AI 说「去哪、带什么词」，底座把检索词送到这里。
   * 不另造一条内部通道——写进自己的搜索框后走老师同款路径，翻页/清目录一并归位。
   */
  function applyBankQuery(payload) {
    var raw = payload && typeof payload.query === "string" ? payload.query : "";
    var keyword = raw.trim().slice(0, SEARCH_MAX);
    if (!keyword) {
      setStatus("宿主送来的检索是空的", true);
      return;
    }
    searchInput.value = keyword;
    submitSearch();
    setStatus("AI 带来的关键词「" + keyword + "」已填入搜索框");
  }

  searchBtn.addEventListener("click", submitSearch);
  searchInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      submitSearch();
    }
  });

  clearBtn.addEventListener("click", showAll);
  treeReset.addEventListener("click", showAll);

  refreshBtn.addEventListener("click", function () {
    setStatus("已刷新");
    loadTree();
    loadScope();
    refreshBasket();
    loadPage();
  });

  prevBtn.addEventListener("click", function () {
    if (state.page <= 1) return;
    state.page -= 1;
    loadPage();
    listEl.scrollTop = 0;
  });

  nextBtn.addEventListener("click", function () {
    if (state.page >= state.totalPages) return;
    state.page += 1;
    loadPage();
    listEl.scrollTop = 0;
  });

  // ---------- 启动 ----------
  function boot() {
    updateCrumb();
    loadTree();
    loadScope();
    refreshBasket();
    loadPage();
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
      if (message.event === "basket.changed") refreshBasket();
      else if (message.event === "system.question_updated" || message.event === "question.updated") {
        scheduleReload();
      } else if (message.event === "system.bank_query") {
        applyBankQuery(message.payload || {});
      }
      return;
    }

    if (message.kind !== "request") return;

    if (message.method === "plugin.activate") {
      root.hidden = false;
      respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
      if (booted) {
        refreshBasket();
        loadPage();
      } else {
        booted = true;
        boot();
      }
      return;
    }

    if (message.method === "plugin.deactivate") {
      root.hidden = true;
      respond(event.source, message.id, true, { ready: false });
      return;
    }

    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD", "未实现的方法：" + message.method);
  });
})();
