/**
 * 真题题库插件运行时（org.jiuzhang.core-bank）。
 *
 * 数据不落在 iframe 里：插件经 jzo-plugin/1 协议向宿主申请 bank.* 数据，
 * 宿主再查本地 SQLite（见 app/core/bank.py）。插件拿不到数据库与文件系统。
 *
 * 右栏面板（ui.params.changed）是筛选的权威来源；本页顶部只保留搜索与刷新，
 * 避免同一条件出现两个写入者。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.core-bank";
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
    search: "",
    page: 1,
    pageSize: PAGE_SIZE,
    total: 0,
    items: [],
    selected: null,
    showSolution: false,
    loading: false
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
      (state.search ? " · 关键词「" + state.search + "」" : "");
  }

  // ---------- 安全渲染 ----------
  function renderMathToken(text) {
    var span = document.createElement("span");
    var display = text.slice(0, 2) === "$$";
    var body = display ? text.slice(2, -2) : text.slice(1, -1);
    if (window.katex && typeof window.katex.renderToString === "function") {
      try {
        span.innerHTML = window.katex.renderToString(body, {
          displayMode: display,
          throwOnError: false,
          trust: false,
          strict: "ignore"
        });
        span.className = display ? "cb-math-block" : "cb-math";
        return span;
      } catch (error) {
        /* 落到纯文本 */
      }
    }
    span.textContent = text;
    return span;
  }

  function appendInline(target, text) {
    var pattern = /(\$\$[\s\S]*?\$\$|\$[^$\n]*?\$|\*\*[^*]+\*\*)/g;
    var last = 0;
    var match;
    while ((match = pattern.exec(text)) !== null) {
      if (match.index > last) target.appendChild(document.createTextNode(text.slice(last, match.index)));
      var token = match[0];
      if (token.slice(0, 1) === "$") {
        target.appendChild(renderMathToken(token));
      } else {
        var strong = document.createElement("strong");
        strong.textContent = token.slice(2, -2);
        target.appendChild(strong);
      }
      last = pattern.lastIndex;
    }
    if (last < text.length) target.appendChild(document.createTextNode(text.slice(last)));
  }

  function appendRich(target, source, imageMap) {
    var text = String(source == null ? "" : source);
    var blocks = text.split(/\n{2,}/);
    blocks.forEach(function (block) {
      var trimmed = block.trim();
      if (!trimmed) return;
      var image = trimmed.match(/^!\[([^\]]*)\]\((\/static\/uploads\/[^)\s]+)\)$/);
      if (image) {
        var img = document.createElement("img");
        img.className = "cb-img";
        img.src = image[2];
        img.alt = image[1] || "配图";
        img.loading = "lazy";
        target.appendChild(img);
        return;
      }
      var paragraph = document.createElement("p");
      paragraph.style.margin = "0 0 8px";
      appendInline(paragraph, trimmed);
      target.appendChild(paragraph);
      if (imageMap) {
        // 段落中残留的图片语法（迁移后的正文一般已是独立段落，这里兜底）
        Array.prototype.forEach.call(paragraph.querySelectorAll("img"), function (node) {
          if (node.getAttribute("src").indexOf("/static/uploads/") !== 0) node.remove();
        });
      }
    });
  }

  // ---------- 列表 ----------
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function difficultyLabel(value) {
    return { basic: "基础", medium: "中档", hard: "压轴", novel: "新定义" }[value] || value;
  }

  function typeLabel(value) {
    return {
      single_choice: "单选", multiple_choice: "多选", fill_blank: "填空",
      solution: "解答", proof: "证明", unknown: "待定"
    }[value] || value;
  }

  function sourceLine(question) {
    var source = question.source || {};
    return [source.paper_title, source.question_no ? "原卷 " + source.question_no + " 题" : ""]
      .filter(Boolean).join(" · ");
  }

  function buildRow(question, index) {
    var row = document.createElement("article");
    row.className = "cb-row";
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.setAttribute("aria-current", String(Boolean(state.selected && state.selected.id === question.id)));
    row.setAttribute("data-id", question.id);

    row.appendChild(el("span", "cb-no", String((state.page - 1) * state.pageSize + index + 1)));
    var main = el("div");
    var stem = el("p", "cb-stem");
    appendInline(stem, question.stem.slice(0, 260));
    main.appendChild(stem);
    var meta = el("div", "cb-meta");
    var grade = el("span", "cb-chip", question.grade || "未标注");
    meta.appendChild(grade);
    var difficulty = el("span", "cb-chip", difficultyLabel(question.difficulty));
    difficulty.setAttribute("data-kind", question.difficulty);
    meta.appendChild(difficulty);
    meta.appendChild(el("span", "cb-chip", typeLabel(question.type)));
    if (question.taxonomy && question.taxonomy.chapter) {
      meta.appendChild(el("span", "cb-chip", question.taxonomy.chapter));
    }
    if (question.source && question.source.paper_title) {
      meta.appendChild(el("span", "cb-chip", sourceLine(question)));
    }
    main.appendChild(meta);
    row.appendChild(main);

    var pick = el("button", "cb-btn", basketIds[question.id] ? "已入篮" : "入篮");
    pick.type = "button";
    pick.setAttribute("aria-label", "把第 " + ((state.page - 1) * state.pageSize + index + 1) + " 题加入题篮");
    pick.addEventListener("click", function (event) {
      event.stopPropagation();
      addToBasket([question.id]);
    });
    row.appendChild(pick);

    function select() {
      state.selected = question;
      state.showSolution = false;
      renderAll();
    }
    row.addEventListener("click", select);
    row.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
    return row;
  }

  function buildPager() {
    var pages = Math.max(1, Math.ceil(state.total / state.pageSize));
    var pager = el("div", "cb-pager");
    var prev = el("button", "cb-btn", "上一页");
    prev.type = "button";
    prev.disabled = state.page <= 1;
    prev.addEventListener("click", function () {
      if (state.page > 1) { state.page -= 1; loadQuestions(); }
    });
    var next = el("button", "cb-btn", "下一页");
    next.type = "button";
    next.disabled = state.page >= pages;
    next.addEventListener("click", function () {
      if (state.page < pages) { state.page += 1; loadQuestions(); }
    });
    pager.appendChild(prev);
    pager.appendChild(el("span", null, "第 " + state.page + " / " + pages + " 页 · 共 " + state.total + " 题"));
    pager.appendChild(next);
    return pager;
  }

  function renderList(host) {
    var list = el("div", "cb-list");
    if (state.loading && !state.items.length) {
      list.appendChild(el("p", "cb-loading", "正在读取题库…"));
    } else if (!state.items.length) {
      list.appendChild(el("p", "cb-empty", "当前筛选下没有题目。试试在右侧面板把年级改成「全部」。"));
    } else {
      state.items.forEach(function (question, index) {
        list.appendChild(buildRow(question, index));
      });
      list.appendChild(buildPager());
    }
    host.appendChild(list);
  }

  // ---------- 详情 ----------
  function renderDetail(host) {
    var side = el("div", "cb-side");
    var question = state.selected;
    if (!question) {
      side.appendChild(el("p", "cb-empty", "从左侧选一道题，这里显示题干、选项与解析。"));
      host.appendChild(side);
      return;
    }

    var detail = el("div", "cb-detail");
    detail.setAttribute("data-question-id", question.id);
    detail.appendChild(el("h2", null, sourceLine(question) || "题目详情"));
    var meta = el("div", "cb-detail-meta");
    meta.textContent = [
      question.grade || "未标注",
      difficultyLabel(question.difficulty),
      typeLabel(question.type),
      question.taxonomy && question.taxonomy.chapter ? question.taxonomy.chapter : "",
      question.id
    ].filter(Boolean).join(" · ");
    detail.appendChild(meta);

    var card = el("div", "cb-question");
    appendRich(card, question.stem);
    if (question.options && question.options.length) {
      var options = el("ol", "cb-options");
      question.options.forEach(function (option) {
        var item = el("li", "cb-option");
        item.appendChild(el("span", "cb-key", option.key + "."));
        var body = el("span");
        appendRich(body, option.content);
        (option.image_ids || []).forEach(function (imageId) {
          var image = (question.images || []).filter(function (candidate) { return candidate.id === imageId; })[0];
          if (image && image.uri) {
            var img = document.createElement("img");
            img.className = "cb-img";
            img.src = image.uri;
            img.alt = image.alt || "选项配图";
            body.appendChild(img);
          }
        });
        item.appendChild(body);
        options.appendChild(item);
      });
      card.appendChild(options);
    }

    if (question.answer) {
      var answer = el("div", "cb-answer");
      answer.appendChild(el("span", "cb-answer-label", "答案："));
      if (question.answer.kind === "choice") {
        answer.appendChild(document.createTextNode((question.answer.choice_keys || []).join("、")));
      } else if (question.answer.content) {
        answer.appendChild(document.createTextNode(question.answer.content));
      }
      card.appendChild(answer);
    }

    if (state.showSolution && question.solution) {
      var solution = el("div", "cb-solution");
      solution.appendChild(el("span", "cb-answer-label", "解析："));
      appendRich(solution, question.solution);
      card.appendChild(solution);
    }

    var actions = el("div", "cb-actions");
    var toggle = el("button", "cb-btn", state.showSolution ? "收起解析" : "显示解析");
    toggle.type = "button";
    toggle.disabled = !question.solution;
    toggle.addEventListener("click", function () {
      state.showSolution = !state.showSolution;
      renderAll();
    });
    actions.appendChild(toggle);

    var add = el("button", "cb-btn cb-btn-primary", basketIds[question.id] ? "已在题篮" : "加入题篮");
    add.type = "button";
    add.addEventListener("click", function () { addToBasket([question.id]); });
    actions.appendChild(add);
    card.appendChild(actions);
    detail.appendChild(card);
    side.appendChild(detail);
    host.appendChild(side);
  }

  function renderAll() {
    if (!stageMode || !root) return;
    root.textContent = "";
    var head = el("header", "cb-head");
    head.appendChild(el("h1", "cb-title", "真题题库"));
    head.appendChild(el("p", "cb-sub", "本地 SQLite · 456 道真题 · 筛选条件以右侧面板为准"));
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
    refresh.addEventListener("click", function () { loadQuestions(); });
    toolbar.appendChild(refresh);

    var hint = el("span", "cb-sub", describeFilters());
    hint.setAttribute("data-filter-summary", "true");
    toolbar.appendChild(hint);
    root.appendChild(toolbar);

    var body = el("div", "cb-body");
    renderList(body);
    renderDetail(body);
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
      q: state.search,
      page: state.page,
      page_size: state.pageSize
    };
    hostCall("bank.list", params)
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
    return hostCall("basket.add", { ids: ids })
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
      return;
    }

    if (message.kind !== "request") return;
    if (message.method === "plugin.activate") {
      stageMode = true;
      root.hidden = false;
      var values = (message.payload && message.payload.values) || {};
      applyParams(values, "init");
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
