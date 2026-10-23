/**
 * 试卷排版插件（org.jiuzhang.exam-paper）。
 *
 * 两种纸面，共用一套 A4 度量：
 *   practice —— 日常小练：卷头、大题标号、连续题号、选择题双列、填空横线、解答留白；
 *   card     —— 标准答题卡：封面信息、考场规则、选择题涂卡区、主观题作答框、密封线。
 *
 * 数据只经 Host API 的 basket.list 取得，本插件不联网、不读库、不碰宿主 DOM。
 * 分页在隐藏测量台里完成：先把内容放进纸面，量超页高就把刚放进去的那一题挪到新页，
 * 全部排完再把成品纸面搬进预览区，避免用户在排版过程中看到半页跳动。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.exam-paper";
  var REQUEST_TIMEOUT_MS = 20000;

  // A4 在 96dpi 下的像素基线；CSS 里纸面用 mm，这里只用于测量与缩放。
  var MM = 96 / 25.4;
  var PAGE_W = 210 * MM;
  var PAGE_H = 297 * MM;
  var CONTENT_H = PAGE_H - (16 + 14) * MM - 6;   // 上下内边距之外再留 6px 墨迹余量

  var SECTIONS = [
    { type: "choice", title: "一、选择题", hint: "每题只有一个正确答案，请将答案写在括号内。",
      cardHint: "请用 2B 铅笔将所选字母涂黑。" },
    { type: "blank", title: "二、填空题", hint: "请将答案直接填在横线上。",
      cardHint: "请在对应题号的作答框内填写答案。" },
    { type: "solution", title: "三、解答题", hint: "写出必要的文字说明、证明过程或演算步骤。",
      cardHint: "请在对应题号的作答框内写出完整过程。" },
    { type: "other", title: "四、其他题目", hint: "",
      cardHint: "请在对应题号的作答框内作答。" }
  ];

  var INLINE_RE = /(!\[[^\]]*\]\((?:asset:\/\/[^)\s]+|\/static\/[^)\s]+)\)|\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$[^$\n]+?\$|\*\*[^*\n]+\*\*)/g;

  var root = document.getElementById("epRoot");
  var deskEl = document.getElementById("epDesk");
  var zoomEl = document.getElementById("epZoom");
  var paperEl = document.getElementById("epPaper");
  var measureEl = document.getElementById("epMeasure");
  var emptyEl = document.getElementById("epEmpty");
  var metricsEl = document.getElementById("epMetrics");
  var titleInput = document.getElementById("epTitle");
  var modeButtons = Array.prototype.slice.call(document.querySelectorAll(".ep-mode"));

  var requestSeq = 0;
  var pending = new Map();
  var loadToken = 0;
  var titleTimer = 0;
  var reloadTimer = 0;
  var fitTimer = 0;
  var mathCache = new Map();

  var state = {
    mode: "practice",
    title: "九章算子 · 数学练习卷",
    items: [],
    missing: 0
  };

  // ---------- 宿主通信 ----------
  function hostCall(method, payload) {
    return new Promise(function (resolve, reject) {
      requestSeq += 1;
      var id = "e" + requestSeq + "_" + Date.now().toString(36);
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
    if (ok) {
      packet.result = result === undefined ? {} : result;
    } else {
      packet.error = { code: code || "PLUGIN_ERROR", message: message || "插件拒绝了请求" };
    }
    try {
      source.postMessage(packet, "*");
    } catch (error) {
      // 宿主帧已销毁：回复无处可去
    }
  }

  function dock(text) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: "region.dock",
        payload: { text: String(text).slice(0, 200) }
      }, "*");
    } catch (error) {
      // 通知丢一帧不致命
    }
  }

  // ---------- 安全富文本 ----------
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function mathNode(tex, display) {
    var span = el("span", display ? "ep-math-block" : "ep-math");
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
    if (html) span.innerHTML = html;
    else span.textContent = (display ? "$$" : "$") + tex + (display ? "$$" : "$");
    return span;
  }

  function allowedImage(uri) {
    var text = String(uri || "");
    return text.indexOf("/static/") === 0 || text.indexOf("asset://") === 0;
  }

  function imageNode(uri, alt) {
    if (!allowedImage(uri)) return null;
    var figure = el("div", "ep-figure");
    var img = document.createElement("img");
    img.src = uri;
    img.alt = String(alt || "题目配图");
    img.loading = "lazy";
    figure.appendChild(img);
    return figure;
  }

  function appendInline(target, text) {
    var last = 0;
    var match;
    INLINE_RE.lastIndex = 0;
    while ((match = INLINE_RE.exec(text)) !== null) {
      if (match.index > last) {
        target.appendChild(document.createTextNode(text.slice(last, match.index)));
      }
      var token = match[0];
      if (token.slice(0, 2) === "![") {
        var parts = token.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
        var figure = parts ? imageNode(parts[2], parts[1]) : null;
        if (figure) target.appendChild(figure);
        else if (parts) target.appendChild(document.createTextNode(parts[1] || ""));
      } else if (token.slice(0, 2) === "\\[") {
        target.appendChild(mathNode(token.slice(2, -2), true));
      } else if (token.slice(0, 2) === "\\(") {
        target.appendChild(mathNode(token.slice(2, -2), false));
      } else if (token.charAt(0) === "$") {
        var display = token.slice(0, 2) === "$$";
        target.appendChild(mathNode(token.slice(display ? 2 : 1, display ? -2 : -1), display));
      } else {
        var strong = document.createElement("strong");
        strong.textContent = token.slice(2, -2);
        target.appendChild(strong);
      }
      last = INLINE_RE.lastIndex;
    }
    if (last < text.length) {
      target.appendChild(document.createTextNode(text.slice(last)));
    }
  }

  /** 一段 Markdown+LaTeX 按行拆成段落；空行不产生空段落。 */
  function appendRich(target, source) {
    var text = String(source == null ? "" : source).replace(/\r\n?/g, "\n").trim();
    if (!text) {
      target.appendChild(el("p", null, "（题干为空）"));
      return;
    }
    text.split("\n").forEach(function (line) {
      var content = line.replace(/^\s*\\item\s*/, "· ").replace(/\\begin\{choices\}|\\end\{choices\}/g, "").trim();
      if (!content) return;
      var paragraph = el("p");
      appendInline(paragraph, content);
      target.appendChild(paragraph);
    });
  }

  // ---------- 题目归类与编号 ----------
  function groupOf(question) {
    var type = question && question.type;
    if (type === "single_choice" || type === "multiple_choice") return "choice";
    if (type === "fill_blank") return "blank";
    if (type === "solution" || type === "proof") return "solution";
    return "other";
  }

  /** 先按题型分大题，再按大题顺序连续编号——卷一、二、三的题号必须是连着的。 */
  function collect(items) {
    var buckets = { choice: [], blank: [], solution: [], other: [] };
    (items || []).forEach(function (raw) {
      var question = raw && raw.question ? raw.question : raw;
      if (!question || typeof question !== "object") return;
      if (!question.stem && !(question.options || []).length) return;
      buckets[groupOf(question)].push(question);
    });
    var entries = [];
    var no = 0;
    SECTIONS.forEach(function (section) {
      buckets[section.type].forEach(function (question) {
        no += 1;
        entries.push({ question: question, group: section.type, no: no });
      });
    });
    return entries;
  }

  function sectionDef(group) {
    for (var i = 0; i < SECTIONS.length; i += 1) {
      if (SECTIONS[i].type === group) return SECTIONS[i];
    }
    return SECTIONS[SECTIONS.length - 1];
  }

  function optionKey(option, index) {
    if (option && typeof option.key === "string" && option.key) return option.key;
    return "ABCDEFGH".charAt(index) || String(index + 1);
  }

  function blankCount(question) {
    var matches = String((question && question.stem) || "").match(/_{2,}|＿{2,}/g);
    return Math.min(4, Math.max(1, matches ? matches.length : 1));
  }

  function questionImages(question) {
    return Array.isArray(question && question.images) ? question.images : [];
  }

  function imageUri(image) {
    if (!image || typeof image !== "object") return "";
    return image.uri || image.path || image.url || "";
  }

  function optionImages(question, option) {
    var ids = (option && option.image_ids) || [];
    if (!ids.length) return [];
    var images = questionImages(question);
    return images.filter(function (image) {
      return image && ids.indexOf(image.id) >= 0;
    });
  }

  // ---------- 纸面骨架 ----------
  function practiceHead() {
    var head = el("header", "ep-paper-head");
    head.appendChild(el("h2", "ep-paper-title", state.title || "数学练习卷"));
    var meta = el("p", "ep-paper-meta");
    ["姓名：____________", "班级：____________", "得分：________"].forEach(function (text) {
      meta.appendChild(el("span", null, text));
    });
    head.appendChild(meta);
    return head;
  }

  function runnerHead(pageNo) {
    var head = el("header", "ep-runner");
    head.appendChild(el("span", null, state.title || "数学练习卷"));
    head.appendChild(el("span", null, "第 " + pageNo + " 页"));
    return head;
  }

  function cardCover() {
    var cover = el("header", "ep-card-cover");
    cover.appendChild(el("p", "ep-card-kicker", "九章算子 · 标准答题卡"));
    cover.appendChild(el("h2", "ep-paper-title", state.title || "数学答题卡"));
    var meta = el("div", "ep-card-meta");
    ["姓名", "班级", "考号", "座位号"].forEach(function (label) {
      var item = el("label");
      item.appendChild(document.createTextNode(label));
      item.appendChild(el("i"));
      meta.appendChild(item);
    });
    cover.appendChild(meta);
    var rules = el("ol", "ep-rules");
    [
      "答题前请在密封线内填写姓名、班级与考号。",
      "选择题必须用 2B 铅笔在涂卡区填涂，修改时用橡皮擦净。",
      "主观题用黑色签字笔在对应题号的作答框内书写，超出框外无效。",
      "考试结束后，请将试卷与答题卡一并交回。"
    ].forEach(function (text) { rules.appendChild(el("li", null, text)); });
    cover.appendChild(rules);
    return cover;
  }

  function sealNode() {
    var seal = el("div", "ep-seal");
    seal.appendChild(el("span", "ep-seal-text", "班级________ 姓名________ 考号________ 密封线内不得答题"));
    return seal;
  }

  function newSheet(kind, first, pageNo) {
    var sheet = el("article", "ep-sheet");
    sheet.setAttribute("data-kind", kind);
    if (kind === "card") sheet.appendChild(sealNode());
    var inner = el("div", "ep-sheet-inner");
    if (first) {
      inner.appendChild(kind === "card" ? cardCover() : practiceHead());
    } else {
      inner.appendChild(runnerHead(pageNo));
    }
    sheet.appendChild(inner);
    measureEl.appendChild(sheet);
    return { sheet: sheet, inner: inner };
  }

  function overflows(inner) {
    return inner.getBoundingClientRect().height > CONTENT_H;
  }

  function startSection(page, group, continued, kind) {
    var def = sectionDef(group);
    var section = el("section", "ep-section");
    section.setAttribute("data-group", group);
    var suffix = kind === "card" ? (group === "choice" ? "（涂卡区）" : "（作答区）") : "";
    section.appendChild(el("h3", "ep-section-title", def.title + suffix + (continued ? "（续）" : "")));
    var hint = kind === "card" ? def.cardHint : def.hint;
    if (!continued && hint) section.appendChild(el("p", "ep-section-hint", hint));
    page.inner.appendChild(section);
    return { el: section };
  }

  // ---------- 日常小练 ----------
  function practiceItem(entry) {
    var question = entry.question;
    var wrap = el("div", "ep-item");
    if (question.id) wrap.setAttribute("data-qid", String(question.id));

    var stem = el("div", "ep-stem");
    stem.appendChild(el("span", "ep-no", entry.no + "."));
    var body = el("div", "ep-stem-body");
    appendRich(body, question.stem || "");
    stem.appendChild(body);
    wrap.appendChild(stem);

    questionImages(question).forEach(function (image) {
      var figure = imageNode(imageUri(image), question.id ? "题目配图" : "");
      if (figure) wrap.appendChild(figure);
    });

    if (entry.group === "choice") {
      var options = Array.isArray(question.options) ? question.options : [];
      if (options.length) {
        var list = el("ul", "ep-options");
        options.forEach(function (option, index) {
          var item = el("li");
          item.appendChild(el("span", "ep-key", optionKey(option, index) + "."));
          var optBody = el("span", "ep-opt-body");
          appendInline(optBody, String(option.content || ""));
          item.appendChild(optBody);
          optionImages(question, option).forEach(function (image) {
            var figure = imageNode(imageUri(image), "选项配图");
            if (figure) item.appendChild(figure);
          });
          list.appendChild(item);
        });
        wrap.appendChild(list);
      }
    }

    if (entry.group === "blank") {
      var lines = el("div", "ep-lines");
      for (var i = 0; i < blankCount(question); i += 1) {
        lines.appendChild(el("div", "ep-line"));
      }
      wrap.appendChild(lines);
    }

    if (entry.group === "solution") {
      wrap.appendChild(el("div", "ep-work"));
    }

    return wrap;
  }

  function buildPractice(entries) {
    measureEl.textContent = "";
    var sheets = [];
    var page = newSheet("practice", true, 1);
    sheets.push(page.sheet);
    var sectionEl = null;
    var group = null;

    entries.forEach(function (entry) {
      if (entry.group !== group) {
        sectionEl = startSection(page, entry.group, false, "practice").el;
        group = entry.group;
      }
      var node = practiceItem(entry);
      sectionEl.appendChild(node);
      if (overflows(page.inner) && page.inner.querySelectorAll(".ep-item").length > 1) {
        sectionEl.removeChild(node);
        page = newSheet("practice", false, sheets.length + 1);
        sheets.push(page.sheet);
        sectionEl = startSection(page, entry.group, true, "practice").el;
        sectionEl.appendChild(node);
      }
    });

    return sheets;
  }

  // ---------- 标准答题卡 ----------
  function omrRow(entry) {
    var question = entry.question;
    var row = el("div", "ep-omr-row");
    row.appendChild(el("span", "ep-omr-no", entry.no + "."));
    var options = Array.isArray(question.options) ? question.options : [];
    if (!options.length) {
      options = ["A", "B", "C", "D"].map(function (key) { return { key: key }; });
    }
    options.forEach(function (option, index) {
      row.appendChild(el("span", "ep-bubble", optionKey(option, index)));
    });
    return row;
  }

  function answerBox(entry) {
    var box = el("div", "ep-answer-box");
    box.appendChild(el("p", "ep-answer-box-head", entry.no + "."));
    var area = el("div", "ep-answer-box-area");
    area.style.height = (entry.group === "blank" ? 24 : entry.group === "solution" ? 58 : 40) + "mm";
    box.appendChild(area);
    return box;
  }

  function buildCard(entries) {
    measureEl.textContent = "";
    var sheets = [];
    var page = newSheet("card", true, 1);
    sheets.push(page.sheet);
    var sectionEl = null;
    var group = null;

    entries.forEach(function (entry) {
      if (entry.group !== group) {
        sectionEl = startSection(page, entry.group, false, "card").el;
        group = entry.group;
      }
      var node = entry.group === "choice" ? omrRow(entry) : answerBox(entry);
      sectionEl.appendChild(node);
      var blocks = sectionEl.querySelectorAll(".ep-omr-row, .ep-answer-box").length;
      if (overflows(page.inner) && blocks > 1) {
        sectionEl.removeChild(node);
        page = newSheet("card", false, sheets.length + 1);
        sheets.push(page.sheet);
        sectionEl = startSection(page, entry.group, true, "card").el;
        sectionEl.appendChild(node);
      }
    });

    return sheets;
  }

  // ---------- 渲染与缩放 ----------
  function updateMetrics(questionCount, pageCount) {
    var parts = [questionCount + " 题", pageCount + " 页"];
    if (state.missing > 0) parts.push(state.missing + " 道失效");
    metricsEl.textContent = parts.join(" · ");
    metricsEl.setAttribute("data-mode", state.mode);
  }

  function render() {
    var entries = collect(state.items);
    paperEl.setAttribute("data-mode", state.mode);
    emptyEl.hidden = entries.length > 0;
    paperEl.textContent = "";

    if (!entries.length) {
      updateMetrics(0, 0);
      zoomEl.style.transform = "none";
      zoomEl.style.width = "auto";
      zoomEl.style.height = "auto";
      return;
    }

    var sheets = state.mode === "card" ? buildCard(entries) : buildPractice(entries);
    measureEl.textContent = "";
    sheets.forEach(function (sheet) { paperEl.appendChild(sheet); });
    updateMetrics(entries.length, sheets.length);
    fitZoom();
  }

  function fitZoom() {
    var available = Math.max(320, deskEl.clientWidth - 48);
    var scale = Math.min(1, available / PAGE_W);
    zoomEl.style.transform = "scale(" + scale.toFixed(4) + ")";
    zoomEl.style.width = Math.ceil(PAGE_W * scale) + "px";
    zoomEl.style.height = Math.ceil(paperEl.offsetHeight * scale) + "px";
  }

  function scheduleFit() {
    window.clearTimeout(fitTimer);
    fitTimer = window.setTimeout(fitZoom, 120);
  }

  // ---------- 数据 ----------
  function loadBasket() {
    var token = ++loadToken;
    return hostCall("basket.list", { expand: true }).then(function (result) {
      if (token !== loadToken) return;
      state.items = Array.isArray(result.items) ? result.items : [];
      state.missing = Number(result.missing || 0);
      render();
      if (state.missing > 0) {
        dock("有 " + state.missing + " 道题已不在题库中，本次排版已跳过。");
      }
    }, function (error) {
      if (token !== loadToken) return;
      state.items = [];
      state.missing = 0;
      render();
      dock("题篮读取失败：" + error.message);
    });
  }

  function scheduleReload() {
    window.clearTimeout(reloadTimer);
    reloadTimer = window.setTimeout(loadBasket, 90);
  }

  // ---------- 交互 ----------
  function setMode(mode) {
    if (mode !== "practice" && mode !== "card") return;
    if (mode === state.mode) return;
    state.mode = mode;
    modeButtons.forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-mode") === mode ? "true" : "false");
    });
    render();
    dock(mode === "card" ? "已切换到标准答题卡模板。" : "已切换到日常小练模板。");
  }

  modeButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setMode(button.getAttribute("data-mode"));
    });
  });

  titleInput.addEventListener("input", function () {
    window.clearTimeout(titleTimer);
    titleTimer = window.setTimeout(function () {
      var next = String(titleInput.value || "").trim().slice(0, 48);
      state.title = next || "九章算子 · 数学练习卷";
      render();
    }, 260);
  });

  document.getElementById("epRefresh").addEventListener("click", loadBasket);
  document.getElementById("epPrint").addEventListener("click", function () { window.print(); });

  window.addEventListener("beforeprint", function () {
    // 打印前同步重排一遍，保证每一页都是按当前模板量出来的
    render();
  });

  window.addEventListener("resize", scheduleFit);

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
      if (message.event === "basket.changed") {
        scheduleReload();
      } else if (message.event === "system.question_updated" || message.event === "question.updated") {
        scheduleReload();
      } else if (message.event === "stage.tab.activated") {
        if (message.payload && message.payload.pluginId === PLUGIN_ID) scheduleReload();
      }
      return;
    }

    if (message.kind !== "request") return;

    if (message.method === "plugin.activate") {
      root.hidden = false;
      respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
      loadBasket();
      scheduleFit();
      return;
    }
    if (message.method === "plugin.deactivate") {
      root.hidden = true;
      respond(event.source, message.id, true, { ready: false });
      return;
    }
    if (message.method === "question.render") {
      var question = (message.payload && message.payload.question) || {};
      var preview = el("p", "ep-card-question");
      preview.textContent = String(question.stem || "").slice(0, 200);
      respond(event.source, message.id, true, {
        html: '<article class="ep-card-question">' + escapeHtml(preview.textContent) + "</article>",
        height: 96
      });
      return;
    }
    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD", "未实现的方法：" + message.method);
  });

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
})();
