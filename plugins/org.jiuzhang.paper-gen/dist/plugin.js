/**
 * 组卷排版插件（org.jiuzhang.paper-gen）。
 *
 * 数据来自宿主转发的 basket.list（含题目全文）；本插件不联网、不读库。
 *
 * 三个文件按 PLUGIN_SPEC §2.8.1（单文件不得过 800 行）分工：
 * - ui_rich.js：题面文本 → 安全 DOM，并拼出一题的纸面题块；
 * - core_layout.js：视口级虚拟排版引擎，五条设计约束写在该文件文件头；
 * - plugin.js（本文件）：宿主协议、题篮数据、侧栏列表与工具条。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.paper-gen";
  var REQUEST_TIMEOUT_MS = 20000;

  var root = document.getElementById("root");
  var pagesEl = document.getElementById("pgPages");
  var measureEl = document.getElementById("pgMeasure");
  var previewEl = document.getElementById("pgPreview");
  var listEl = document.getElementById("pgList");
  var emptyEl = document.getElementById("pgEmpty");
  var countEl = document.getElementById("pgCount");
  var metricsEl = document.getElementById("pgMetrics");
  var titleInput = document.getElementById("pgTitle");
  var toastEl = document.getElementById("pgToast");

  var stageMode = false;
  var requestSeq = 0;
  var pending = new Map();
  var loadToken = 0;
  var toastTimer = 0;
  var titleTimer = 0;
  var selectedId = null;

  var state = {
    items: [],
    showAnswers: false,
    density: "normal",
    title: "九章算子 · 数学练习卷",
    renderMs: 0
  };

  // ---------- 宿主通信 ----------
  function hostCall(method, payload) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "g" + requestSeq + "_" + Date.now().toString(36);
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

  function dock(text) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: "region.dock",
        payload: { text: String(text).slice(0, 200) }
      }, "*");
    } catch (error) { /* 通知丢一帧不致命 */ }
  }

  function toast(text) {
    if (!toastEl) return;
    toastEl.textContent = text;
    toastEl.setAttribute("data-show", "true");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      toastEl.setAttribute("data-show", "false");
    }, 2200);
  }

  // ---------- 富文本与题块：已拆到 ui_rich.js（PLUGIN_SPEC §2.8.1） ----------
  // plugin.js 只取排版引擎与侧栏要用的四件：建 DOM 的 el、答案文本、配图预量、题块构建。
  var rich = window.JzoPaperRich;
  var el = rich.el;
  var answerText = rich.answerText;
  var primeImages = rich.primeImages;
  var buildQuestionBlock = rich.buildQuestionBlock;

  // ---------- 排版引擎：量版式、落页、物化、重排已拆到 core_layout.js ----------
  // plugin.js 只留「协议 + 数据 + 侧栏 + 工具条」；纸面怎么排交给引擎，
  // 引擎也不认宿主协议，只吃下面这点 ctx。
  var layout = window.JzoPaperLayout.create({
    state: state,
    el: el,
    answerText: answerText,
    buildQuestionBlock: buildQuestionBlock,
    measureEl: measureEl,
    previewEl: previewEl,
    pagesEl: pagesEl,
    metricsEl: metricsEl,
    dock: dock,
    renderSide: renderSide,
    isStage: function () { return stageMode; }
  });
  var doc = layout.doc;
  var reflow = layout.reflow;
  var applyScale = layout.applyScale;
  var syncViewport = layout.syncViewport;
  var advance = layout.advance;
  var materialize = layout.materialize;
  var pruneLayouts = layout.pruneLayouts;
  var forgetRecords = layout.forgetRecords;

  // ---------- 侧栏 ----------
  function plainPreview(text) {
    return String(text || "")
      .replace(/!\[[^\]]*\]\([^)]*\)/g, "［图］")
      .replace(/\$\$?[^$]*\$\$?/g, "…")
      .replace(/\\\[[\s\S]*?\\\]|\\\([^\n]*?\\\)/g, "…")
      .replace(/\\textbf\{([^{}]*)\}/g, "$1")
      .replace(/\\textit\{([^{}]*)\}/g, "$1")
      .replace(/\\fillin/g, "＿＿")
      .replace(/\\begin\{choices\}|\\end\{choices\}|^\s*\\item\s*/gm, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function difficultyLabel(value) {
    return {
      L1: "基础", L2: "中档", L3: "难", L4: "压轴",
      basic: "基础", medium: "中档", hard: "难", novel: "压轴"
    }[value] || value;
  }

  // ---------- 三端分离：输出端只读，改题一律跳录题工作台 ----------
  function publish(event, payload) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: event, payload: payload || {}
      }, "*");
    } catch (error) {
      /* 跳转丢了不致命 */
    }
  }

  function openEditor(questionId) {
    if (!questionId) return;
    publish("system.open_editor", { question_id: questionId });
    dock("已请求打开录题工作台：" + questionId);
  }

  var refreshTimer = null;

  function scheduleRefresh() {
    // 宿主对新旧两个事件名各广播一次，去重成一次重排，别连着打两遍接口
    if (refreshTimer) window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(function () {
      refreshTimer = null;
      loadBasket();
      dock("录题端改了题目，A4 已静默重排。");
    }, 300);
  }

  function renderSide() {
    if (!listEl) return;
    listEl.textContent = "";
    countEl.textContent = String(state.items.length);
    emptyEl.hidden = state.items.length > 0;

    state.items.forEach(function (question, index) {
      var item = el("li", "pg-item");
      var row = document.createElement("button");
      row.type = "button";
      row.className = "pg-row";
      row.setAttribute("aria-current", String(question.id === selectedId));
      row.appendChild(el("span", "pg-row-no", String(index + 1).padStart(2, "0")));
      var main = el("span", "pg-row-main");
      main.appendChild(el("span", "pg-row-stem", plainPreview(question.stem).slice(0, 90)));
      var meta = el("span", "pg-row-meta");
      meta.textContent = [question.grade || "未标注", difficultyLabel(question.difficulty)].filter(Boolean).join(" · ");
      main.appendChild(meta);
      row.appendChild(main);
      row.addEventListener("click", function () { jumpTo(question.id); });
      item.appendChild(row);

      var edit = el("button", "pg-edit", "去编辑");
      edit.type = "button";
      edit.setAttribute("aria-label", "到录题工作台修改第 " + (index + 1) + " 题");
      edit.addEventListener("click", function (event) {
        event.stopPropagation();
        openEditor(question.id);
      });
      item.appendChild(edit);

      var remove = el("button", "pg-remove", "×");
      remove.type = "button";
      remove.setAttribute("aria-label", "从题篮移除第 " + (index + 1) + " 题");
      remove.addEventListener("click", function (event) {
        event.stopPropagation();
        removeQuestion(question.id);
      });
      item.appendChild(remove);
      listEl.appendChild(item);
    });
  }

  /** 点题篮行：定位到该题所在的页（页还没排到就先补页再滚）。 */
  function jumpTo(questionId) {
    selectedId = questionId;
    var guard = 0;
    while (guard < state.items.length) {
      var found = doc.pages.some(function (record) {
        return record.items.some(function (unit) { return unit.qid === questionId; });
      });
      if (found || doc.complete) break;
      advance();
      guard += 1;
    }
    var index = -1;
    doc.pages.some(function (record, i) {
      var hit = record.items.some(function (unit) { return unit.qid === questionId; });
      if (hit) index = i;
      return hit;
    });
    if (index >= 0) {
      doc.pages[index].wrap.scrollIntoView({ block: "start", behavior: "smooth" });
    }
    renderSide();
  }

  // ---------- 数据 ----------
  function loadBasket() {
    var token = ++loadToken;
    return hostCall("basket.list", { expand: true })
      .then(function (result) {
        if (token !== loadToken) return;
        var items = (result && result.items) || [];
        state.items = items.map(function (item) { return item.question; }).filter(Boolean);
        // 底座会报「取不到全文」的题数：不说出来，卷面就凭空少题
        var missing = Number((result && result.missing) || 0);
        if (missing > 0) {
          dock("题篮里有 " + missing + " 题取不到全文（插件或题库缺失），已按剩余 " +
            state.items.length + " 题排版。");
        }
        if (selectedId && !state.items.some(function (item) { return item.id === selectedId; })) {
          selectedId = null;
        }
        forgetRecords();
        pruneLayouts();
        renderSide();
        // 图未量好就排，等于给分页埋雷：先等尺寸，再上纸
        return primeImages(state.items).then(function () {
          if (token === loadToken) reflow();
        });
      })
      .catch(function (error) {
        toast("读取题篮失败：" + error.message);
        dock("组卷读取题篮失败：" + error.message);
      });
  }

  function removeQuestion(questionId) {
    hostCall("basket.remove", { question_id: questionId })
      .then(function () {
        toast("已从题篮移除");
        return loadBasket();
      })
      .catch(function (error) {
        toast("移除失败：" + error.message);
      });
  }

  function clearBasket() {
    if (!state.items.length) return;
    hostCall("basket.clear", {})
      .then(function () {
        toast("题篮已清空");
        return loadBasket();
      })
      .catch(function (error) {
        toast("清空失败：" + error.message);
      });
  }

  // ---------- 面板参数 ----------
  function applyParams(values, by) {
    if (!values || typeof values !== "object") return;
    var changed = false;
    if (typeof values.answers === "string") {
      var answers = values.answers === "显示";
       if (answers !== state.showAnswers) { state.showAnswers = answers; changed = true; }
    }
    if (typeof values.density === "string") {
      var density = values.density === "紧凑" ? "compact" : "normal";
      if (density !== state.density) { state.density = density; changed = true; }
    }
    if (changed) {
      reflow();
      dock("组卷设置：" + (state.showAnswers ? "显示答案" : "隐藏答案") + " · " +
        (state.density === "compact" ? "紧凑" : "标准") + "（" + (by === "human" ? "人工" : "同步") + "）");
    }
  }

  /** 打印/导出 PDF 前把全卷补齐：纸面可以慢，但不能缺页。 */
  function completeForPrint() {
    if (doc.complete) return;
    var started = performance.now();
    while (!doc.complete) advance();
    doc.pages.forEach(function (record) {
      if (!record.mat) materialize(record);
    });
    dock("打印前补齐 " + doc.pages.length + " 页，用时 " +
      Math.round((performance.now() - started) * 10) / 10 + " ms。");
  }

  // ---------- 工具条 ----------
  if (titleInput) {
    titleInput.addEventListener("input", function () {
      window.clearTimeout(titleTimer);
      titleTimer = window.setTimeout(function () {
        state.title = titleInput.value.trim().slice(0, 48) || "数学练习卷";
        doc.pages.forEach(function (record) { record.title.textContent = state.title; });
      }, 200);
    });
  }

  var reflowBtn = document.getElementById("pgReflow");
  if (reflowBtn) reflowBtn.addEventListener("click", function () {
    // 「重新排版」按字面只做本地重排；重新取题篮是【刷新】的活
    if (stageMode) {
      reflow();
      toast("已按当前题篮重排 " + state.items.length + " 题");
    } else {
      loadBasket();
    }
  });

  var refreshBtn = document.getElementById("pgRefresh");
  if (refreshBtn) refreshBtn.addEventListener("click", function () { loadBasket(); });

  var clearBtn = document.getElementById("pgClear");
  if (clearBtn) clearBtn.addEventListener("click", clearBasket);

  var printBtn = document.getElementById("pgPrint");
  if (printBtn) {
    printBtn.addEventListener("click", function () {
      completeForPrint();
      try {
        window.print();
      } catch (error) {
        toast("沙箱内无法直接打印，请用浏览器菜单打印");
      }
    });
  }

  if (window.ResizeObserver && previewEl) {
    new ResizeObserver(function () { applyScale(); syncViewport(0); }).observe(previewEl);
  } else {
    window.addEventListener("resize", function () { applyScale(); syncViewport(0); });
  }

  if (previewEl) {
    var scrollQueued = false;
    previewEl.addEventListener("scroll", function () {
      // 一帧只同步一次：狂拉滚动条时不让追页事件互相排队
      if (scrollQueued) return;
      scrollQueued = true;
      window.requestAnimationFrame(function () {
        scrollQueued = false;
        syncViewport();
      });
    }, { passive: true });
  }

  window.addEventListener("beforeprint", completeForPrint);

  // ---------- 能力路由字典（军令 #20） ----------
  function commandReject(source, message, code, text) {
    respond(source, message.id, false, null, code, text);
  }

  function paperSnapshot() {
    return {
      questions: state.items.length,
      pages: doc.pages.length,
      answers: state.showAnswers ? "显示" : "隐藏",
      density: state.density === "compact" ? "紧凑" : "标准",
      title: state.title
    };
  }

  function handleCommandExecute(source, message) {
    var payload = message.payload || {};
    var commandId = typeof payload.command_id === "string" ? payload.command_id : "";
    var context = payload.context && typeof payload.context === "object" ? payload.context : {};

    if (commandId === "org.jiuzhang.action.process.generate_paper") {
      var unknown = Object.keys(context).filter(function (key) {
        return ["answers", "density", "title"].indexOf(key) < 0;
      });
      if (unknown.length) {
        return commandReject(source, message, "BAD_PARAMS", "不认识的参数：" + unknown.join("、"));
      }
      if (context.answers !== undefined && ["显示", "隐藏"].indexOf(context.answers) < 0) {
        return commandReject(source, message, "BAD_PARAMS", "answers 只接受 显示/隐藏");
      }
      if (context.density !== undefined && ["标准", "紧凑"].indexOf(context.density) < 0) {
        return commandReject(source, message, "BAD_PARAMS", "density 只接受 标准/紧凑");
      }
      if (context.title !== undefined && (typeof context.title !== "string" || context.title.length > 48)) {
        return commandReject(source, message, "BAD_PARAMS", "title 必须是不超过 48 字的字符串");
      }
      applyParams({ answers: context.answers, density: context.density }, "command");
      if (typeof context.title === "string") {
        state.title = context.title.trim().slice(0, 48) || "数学练习卷";
        if (titleInput) titleInput.value = state.title;
        doc.pages.forEach(function (record) { record.title.textContent = state.title; });
      }
      reflow();
      completeForPrint();
      return respond(source, message.id, true, paperSnapshot());
    }

    if (commandId === "org.jiuzhang.action.output.export_paper") {
      if (Object.keys(context).length) {
        return commandReject(source, message, "BAD_PARAMS", "打印命令不接受参数");
      }
      completeForPrint();
      var snapshot = paperSnapshot();
      respond(source, message.id, true, {
        questions: snapshot.questions,
        pages: snapshot.pages,
        printed: true
      });
      // 先回执再调起系统打印框：打印对话框会阻塞，不能把宿主回包吊在里面。
      window.setTimeout(function () { window.print(); }, 0);
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
        applyParams((message.payload && message.payload.values) || {}, message.payload && message.payload.by);
      } else if (message.event === "basket.changed") {
        loadBasket();
      } else if (message.event === "system.question_updated" || message.event === "question.updated") {
        scheduleRefresh();
      }
      return;
    }

    if (message.kind !== "request") return;
    if (message.method === "plugin.activate") {
      stageMode = true;
      root.hidden = false;
      applyParams((message.payload && message.payload.values) || {}, "init");
      loadBasket();
      respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
      return;
    }
    if (message.method === "plugin.deactivate") {
      root.hidden = true;
      return respond(event.source, message.id, true, { ready: false });
    }
    if (message.method === "question.render") {
      var question = (message.payload && message.payload.question) || {};
      return respond(event.source, message.id, true, {
        html: '<article class="pg-question">' + escapeHtml(question.stem || "") + "</article>",
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

  if (window.parent === window && root) {
    root.hidden = false;
    pagesEl.innerHTML = "";
    var note = el("p", "pg-empty", "请从九章算子工作台左侧打开「组卷排版」；插件单独打开时拿不到题篮。");
    pagesEl.appendChild(note);
  }
})();
