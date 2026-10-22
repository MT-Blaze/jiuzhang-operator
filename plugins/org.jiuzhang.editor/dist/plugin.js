/**
 * 录题工作台（org.jiuzhang.editor）。
 *
 * 左表单、右 A4：每次输入停顿 140ms 做一次整页重绘，公式交给本地 KaTeX。
 * 保存不碰数据库，而是经宿主 bank.create 转发——宿主代取一次性令牌并
 * 固定写入底座公共题库（org.jiuzhang.core-bank），插件自报目标一律无效。
 *
 * 「一键清洗 LaTeX」是本地规则，不上传题干、不调模型：老师粘来的
 * \(...\)、\[...\]、\textbf{}、\fillin 与 choices 环境在这里归一。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.editor";
  var PAGE_W = 794;
  var PAGE_H = 1123;
  var PREVIEW_DEBOUNCE_MS = 140;
  var REQUEST_TIMEOUT_MS = 20000;
  var TYPE_LABEL = {
    single_choice: "单选",
    multiple_choice: "多选",
    fill_blank: "填空",
    solution: "解答"
  };
  var DIFF_LABEL = { basic: "基础", medium: "中档", hard: "压轴", novel: "新定义" };
  var OPTION_KEYS = "ABCDEFGH".split("");

  var root = document.getElementById("root");
  var typeEl = document.getElementById("edType");
  var diffEl = document.getElementById("edDifficulty");
  var gradeEl = document.getElementById("edGrade");
  var stemEl = document.getElementById("edStem");
  var optionsBlock = document.getElementById("edOptionsBlock");
  var optionsEl = document.getElementById("edOptions");
  var addOptionEl = document.getElementById("edAddOption");
  var answerEl = document.getElementById("edAnswer");
  var answerHintEl = document.getElementById("edAnswerHint");
  var solutionEl = document.getElementById("edSolution");
  var tagsEl = document.getElementById("edTags");
  var previewEl = document.getElementById("edPreview");
  var pageFrameEl = document.getElementById("edPageFrame");
  var pageEl = document.getElementById("edPage");
  var pageBodyEl = document.getElementById("edPageBody");
  var metricsEl = document.getElementById("edMetrics");
  var savedEl = document.getElementById("edSaved");
  var scaleEl = document.getElementById("edScale");
  var saveEl = document.getElementById("edSave");
  var cleanEl = document.getElementById("edClean");
  var resetEl = document.getElementById("edReset");
  var toastEl = document.getElementById("edToast");

  var pending = new Map();
  var requestSeq = 0;
  var previewTimer = 0;
  var toastTimer = 0;
  var mathCache = new Map();
  var scale = 1;
  var dirtySinceSave = false;

  var state = {
    options: [
      { key: "A", content: "" },
      { key: "B", content: "" },
      { key: "C", content: "" },
      { key: "D", content: "" }
    ]
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

  function toast(text, tone) {
    if (!toastEl) return;
    toastEl.textContent = text;
    toastEl.setAttribute("data-tone", tone || "info");
    toastEl.setAttribute("data-show", "true");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      toastEl.setAttribute("data-show", "false");
    }, 2600);
  }

  function respond(target, id, ok, result, code, message) {
    var packet = { protocol: PROTOCOL, id: id, kind: "response", ok: ok };
    if (ok) packet.result = result || {};
    else packet.error = { code: code || "ERROR", message: message || "失败", retryable: false };
    try { target.postMessage(packet, "*"); } catch (error) { /* 宿主已走 */ }
  }

  // ---------- 富文本 ----------
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function mathNode(tex, display) {
    var span = el("span", display ? "ed-math-block" : "ed-math");
    var key = (display ? "D:" : "I:") + tex;
    var html = mathCache.get(key);
    if (html === undefined) {
      html = "";
      if (window.katex && typeof window.katex.renderToString === "function") {
        try {
          html = window.katex.renderToString(tex, {
            displayMode: display, throwOnError: false, strict: "ignore"
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

  var INLINE_RE = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\$[^$\n]*?\$|\\\([\s\S]*?\\\)|\*\*[^*]+\*\*)/g;

  function appendRich(parent, text) {
    var source = String(text == null ? "" : text);
    var last = 0;
    var match;
    INLINE_RE.lastIndex = 0;
    while ((match = INLINE_RE.exec(source)) !== null) {
      if (match.index > last) parent.appendChild(document.createTextNode(source.slice(last, match.index)));
      var token = match[0];
      if (token.slice(0, 2) === "$$" && token.slice(-2) === "$$") {
        parent.appendChild(mathNode(token.slice(2, -2), true));
      } else if (token.slice(0, 2) === "\\[" && token.slice(-2) === "\\]") {
        parent.appendChild(mathNode(token.slice(2, -2), true));
      } else if (token.slice(0, 2) === "\\(" && token.slice(-2) === "\\)") {
        parent.appendChild(mathNode(token.slice(2, -2), false));
      } else if (token.charAt(0) === "$" && token.charAt(token.length - 1) === "$") {
        parent.appendChild(mathNode(token.slice(1, -1), false));
      } else if (token.slice(0, 2) === "**" && token.slice(-2) === "**") {
        var strong = el("strong");
        appendRich(strong, token.slice(2, -2));
        parent.appendChild(strong);
      } else {
        parent.appendChild(document.createTextNode(token));
      }
      last = match.index + token.length;
    }
    if (last < source.length) parent.appendChild(document.createTextNode(source.slice(last)));
  }

  /** 把文本按独立公式切成「文字段 / 公式段」，文字段再按空行分段。 */
  function appendBody(parent, text) {
    var source = String(text == null ? "" : text).trim();
    if (!source) return;
    var displayRe = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\])/g;
    var segments = source.split(displayRe);
    segments.forEach(function (segment, index) {
      if (!segment) return;
      if (index % 2 === 1) {
        var display = segment.slice(2, -2);
        parent.appendChild(mathNode(display, true));
        return;
      }
      segment.split(/\n{2,}/).forEach(function (paragraph) {
        var clean = paragraph.replace(/\n/g, " ").trim();
        if (!clean) return;
        var p = el("p", "ed-line");
        appendRich(p, clean);
        parent.appendChild(p);
      });
    });
  }

  // ---------- 表单 ----------
  function currentType() {
    return typeEl ? typeEl.value : "single_choice";
  }

  function isChoice() {
    var type = currentType();
    return type === "single_choice" || type === "multiple_choice";
  }

  function renderOptions() {
    if (!optionsEl) return;
    optionsEl.textContent = "";
    state.options.forEach(function (option, index) {
      var row = el("div", "ed-option");
      row.setAttribute("data-index", String(index));
      row.appendChild(el("span", "ed-option-key", option.key));
      var input = el("input");
      input.type = "text";
      input.spellcheck = false;
      input.value = option.content;
      input.setAttribute("aria-label", "选项 " + option.key + " 的内容");
      input.setAttribute("data-option-index", String(index));
      input.addEventListener("input", function () {
        state.options[index].content = input.value;
        dirtySinceSave = true;
        schedulePreview();
      });
      var remove = el("button", "ed-option-remove", "×");
      remove.type = "button";
      remove.setAttribute("aria-label", "删除选项 " + option.key);
      remove.disabled = state.options.length <= 2;
      remove.addEventListener("click", function () {
        if (state.options.length <= 2) return;
        state.options.splice(index, 1);
        relabelOptions();
        renderOptions();
        schedulePreview();
      });
      row.appendChild(input);
      row.appendChild(remove);
      optionsEl.appendChild(row);
    });
  }

  function relabelOptions() {
    state.options.forEach(function (option, index) {
      option.key = OPTION_KEYS[index] || String(index + 1);
    });
    var allowed = state.options.map(function (option) { return option.key; });
    var letters = parseAnswerLetters(answerEl.value).filter(function (key) {
      return allowed.indexOf(key) >= 0;
    });
    answerEl.value = letters.join("");
  }

  function addOption() {
    if (state.options.length >= OPTION_KEYS.length) {
      toast("最多 8 个选项", "error");
      return;
    }
    state.options.push({ key: OPTION_KEYS[state.options.length], content: "" });
    renderOptions();
    var inputs = optionsEl.querySelectorAll("input");
    if (inputs.length) inputs[inputs.length - 1].focus();
    schedulePreview();
  }

  function applyType() {
    var choice = isChoice();
    optionsBlock.hidden = !choice;
    answerHintEl.textContent = choice
      ? (currentType() === "multiple_choice" ? "多选填多个字母，如 AC" : "单选填一个字母，如 C")
      : "可填数值或 LaTeX 表达式";
    answerEl.placeholder = choice ? "C" : "$x=2$ 或 $x=3$";
    schedulePreview();
  }

  function parseAnswerLetters(value) {
    var text = String(value || "").toUpperCase().replace(/[，,、\s]/g, "");
    var letters = [];
    for (var i = 0; i < text.length; i += 1) {
      var key = text.charAt(i);
      if (OPTION_KEYS.indexOf(key) >= 0 && letters.indexOf(key) < 0) letters.push(key);
    }
    return letters.sort();
  }

  function splitTags(value) {
    var parts = String(value || "").split(/[,，;；]/);
    var seen = [];
    parts.forEach(function (part) {
      var tag = part.trim();
      if (!tag || tag.length > 32) return;
      if (seen.indexOf(tag) < 0) seen.push(tag);
    });
    return seen.slice(0, 32);
  }

  // ---------- 预览 ----------
  function renderEmpty() {
    pageBodyEl.textContent = "";
    var empty = el("div", "ed-empty");
    empty.appendChild(el("strong", null, "右侧是本页 A4 预览"));
    empty.appendChild(el("span", null, "在左边写下题干与公式，排版会实时跟上"));
    pageBodyEl.appendChild(empty);
    pageBodyEl.setAttribute("data-overflow", "false");
    metricsEl.textContent = "等待录入…";
  }

  function renderPreview() {
    var started = (window.performance && performance.now) ? performance.now() : Date.now();
    var stem = stemEl.value;
    var type = currentType();
    var solution = solutionEl.value.trim();
    var answer = answerEl.value.trim();

    if (!stem.trim() && !answer && !solution) {
      renderEmpty();
      pageEl.setAttribute("data-render-ms", "0");
      emitDraft(null);
      return;
    }

    pageBodyEl.textContent = "";
    var head = el("div", "ed-q-head");
    head.appendChild(el("span", "ed-chip", TYPE_LABEL[type] || "题目"));
    head.appendChild(el("span", "ed-chip", DIFF_LABEL[diffEl.value] || "中档"));
    head.appendChild(el("span", "ed-chip", gradeEl.value || "高中"));
    pageBodyEl.appendChild(head);

    var body = el("div", "ed-q-body");
    pageBodyEl.appendChild(body);

    if (stem.trim()) appendBody(body, stem);

    if (isChoice() && state.options.length) {
      var list = el("ol", "ed-q-options");
      state.options.forEach(function (option) {
        var item = el("li");
        item.appendChild(el("span", "ed-opt-key", option.key + "．"));
        var content = el("span");
        appendRich(content, option.content || "（未填）");
        item.appendChild(content);
        list.appendChild(item);
      });
      body.appendChild(list);
    }

    if (answer) {
      var answerBox = el("div", "ed-q-answer");
      answerBox.appendChild(el("span", "ed-label", "【答案】"));
      var answerText = el("span");
      if (isChoice()) answerText.textContent = " " + parseAnswerLetters(answer).join("");
      else appendRich(answerText, answer);
      answerBox.appendChild(answerText);
      body.appendChild(answerBox);
    }

    if (solution) {
      var solutionBox = el("div", "ed-q-solution");
      solutionBox.appendChild(el("span", "ed-label", "【解析】"));
      var solutionText = el("div");
      appendBody(solutionText, solution);
      solutionBox.appendChild(solutionText);
      body.appendChild(solutionBox);
    }

    var tags = splitTags(tagsEl.value);
    if (tags.length) {
      var tagLine = el("div", "ed-q-tags", "知识点：" + tags.join(" · "));
      pageBodyEl.appendChild(tagLine);
    }

    var elapsed = ((window.performance && performance.now) ? performance.now() : Date.now()) - started;
    var overflow = pageBodyEl.scrollHeight > pageBodyEl.clientHeight + 1;
    pageBodyEl.setAttribute("data-overflow", String(overflow));
    pageEl.setAttribute("data-render-ms", elapsed.toFixed(1));
    metricsEl.setAttribute("data-render-ms", elapsed.toFixed(1));
    metricsEl.setAttribute("data-katex", String(pageBodyEl.querySelectorAll(".katex").length));
    metricsEl.setAttribute("data-overflow", overflow ? "1" : "0");
    metricsEl.setAttribute("data-chars", String(stem.length + solution.length + answer.length));
    metricsEl.textContent = (overflow ? "超出一页安全区 · " : "单页可容 · ")
      + "重排 " + elapsed.toFixed(1) + " ms";
    emitDraft(buildQuestion(false));
  }

  function emitDraft(question) {
    if (!question) {
      try {
        window.parent.postMessage({
          protocol: PROTOCOL, kind: "notification", event: "stage.selection",
          payload: { question: null, pluginId: PLUGIN_ID }
        }, "*");
      } catch (error) { /* 忽略 */ }
      return;
    }
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: "stage.selection",
        payload: { question: question, pluginId: PLUGIN_ID }
      }, "*");
    } catch (error) { /* 忽略 */ }
  }

  function schedulePreview() {
    dirtySinceSave = true;
    if (savedEl) savedEl.hidden = true;
    window.clearTimeout(previewTimer);
    previewTimer = window.setTimeout(renderPreview, PREVIEW_DEBOUNCE_MS);
  }

  function fitPreview() {
    if (!previewEl || !pageEl) return;
    var width = Math.max(120, previewEl.clientWidth - 32);
    var height = Math.max(120, previewEl.clientHeight - 32);
    scale = Math.min(1, width / PAGE_W, height / PAGE_H);
    if (!Number.isFinite(scale) || scale <= 0) scale = 0.5;
    pageEl.style.transform = "scale(" + scale.toFixed(3) + ")";
    pageFrameEl.style.width = Math.round(PAGE_W * scale) + "px";
    pageFrameEl.style.height = Math.round(PAGE_H * scale) + "px";
    if (scaleEl) scaleEl.textContent = Math.round(scale * 100) + "%";
  }

  // ---------- LaTeX 清洗（纯本地规则） ----------
  function cleanText(raw) {
    var text = String(raw == null ? "" : raw);
    text = text.replace(/\\\[([\s\S]*?)\\\]/g, function (_, body) { return "$$" + body + "$$"; });
    text = text.replace(/\\\(([\s\S]*?)\\\)/g, function (_, body) { return "$" + body + "$"; });
    text = text.replace(/\\displaystyle\s*/g, "");
    text = text.replace(/\\fillin(?![A-Za-z])/g, "＿＿＿＿");
    text = text.replace(/\\textbf\{([^{}]*)\}/g, "$1");
    text = text.replace(/\\textit\{([^{}]*)\}/g, "$1");
    text = text.replace(/\\emph\{([^{}]*)\}/g, "$1");
    text = text.replace(/\\begin\{(?:enumerate|itemize)\}/g, "");
    text = text.replace(/\\end\{(?:enumerate|itemize)\}/g, "");
    text = text.replace(/\\item\s*/g, "· ");
    text = text.replace(/[ \t]+\n/g, "\n");
    text = text.replace(/\n{3,}/g, "\n\n");
    return text.trim();
  }

  function extractChoices(raw) {
    var text = String(raw == null ? "" : raw);
    var pattern = /\\begin\{choices\}([\s\S]*?)\\end\{choices\}/;
    var found = pattern.exec(text);
    if (!found) return null;
    var items = found[1].split(/\\item\s*/).slice(1);
    var options = [];
    items.forEach(function (item) {
      var content = cleanText(item);
      if (content) options.push(content);
    });
    if (options.length < 2) return null;
    return { options: options, stem: text.replace(pattern, "").trim() };
  }

  function cleanAll() {
    var touched = 0;
    var choices = extractChoices(stemEl.value);
    if (choices) {
      stemEl.value = cleanText(choices.stem);
      state.options = choices.options.slice(0, OPTION_KEYS.length).map(function (content, index) {
        return { key: OPTION_KEYS[index], content: content };
      });
      while (state.options.length < 2) {
        state.options.push({ key: OPTION_KEYS[state.options.length], content: "" });
      }
      if (currentType() === "fill_blank" || currentType() === "solution") {
        typeEl.value = "single_choice";
        applyType();
      }
      renderOptions();
      touched += 2;
    } else {
      var nextStem = cleanText(stemEl.value);
      if (nextStem !== stemEl.value) { stemEl.value = nextStem; touched += 1; }
    }

    state.options.forEach(function (option, index) {
      var next = cleanText(option.content);
      if (next !== option.content) {
        option.content = next;
        touched += 1;
      }
      var input = optionsEl.querySelector('input[data-option-index="' + index + '"]');
      if (input) input.value = option.content;
    });

    var nextAnswer = cleanText(answerEl.value);
    if (nextAnswer !== answerEl.value) { answerEl.value = nextAnswer; touched += 1; }
    var nextSolution = cleanText(solutionEl.value);
    if (nextSolution !== solutionEl.value) { solutionEl.value = nextSolution; touched += 1; }

    renderPreview();
    toast(touched ? "已清洗 " + touched + " 处 LaTeX 写法" : "未发现需要清洗的写法");
    dock(touched ? "LaTeX 清洗完成：" + touched + " 处" : "LaTeX 无需清洗");
  }

  // ---------- 保存 ----------
  function buildQuestion(strict) {
    var type = currentType();
    var stem = stemEl.value.trim();
    var answerRaw = answerEl.value.trim();
    var question = {
      schema_version: "1.0",
      type: type,
      stem: stem,
      difficulty: diffEl.value,
      tags: splitTags(tagsEl.value),
      extensions: { "org.jiuzhang.editor": { grade: gradeEl.value || "" } },
      meta: { status: "published", author: "九章算子·录题工作台" }
    };
    var solution = solutionEl.value.trim();
    if (solution) question.solution = solution;

    if (isChoice()) {
      var keys = state.options.map(function (option) { return option.key; });
      var options = state.options.map(function (option, index) {
        return { key: keys[index], content: option.content.trim() };
      });
      if (strict) {
        if (options.length < 2) throw new Error("选择题至少要有两个选项");
        var blank = options.filter(function (option) { return !option.content; });
        if (blank.length) throw new Error("选项 " + blank.map(function (option) { return option.key; }).join("、") + " 还没有内容");
      } else {
        options = options.filter(function (option) { return option.content; });
      }
      if (options.length) question.options = options;

      var letters = parseAnswerLetters(answerRaw);
      if (strict) {
        if (!letters.length) throw new Error("请填写答案选项，例如 C");
        if (type === "single_choice" && letters.length !== 1) throw new Error("单选题答案只能有一个字母");
        if (type === "multiple_choice" && letters.length < 2) throw new Error("多选题答案至少两个字母");
        var allowed = options.map(function (option) { return option.key; });
        var bad = letters.filter(function (key) { return allowed.indexOf(key) < 0; });
        if (bad.length) throw new Error("答案 " + bad.join("、") + " 不在现有选项中");
      }
      if (letters.length) {
        question.answer = {
          kind: "choice",
          choice_keys: letters,
          final: letters.join("")
        };
      }
    } else if (answerRaw) {
      question.answer = {
        kind: type === "fill_blank" ? "expression" : "text",
        content: answerRaw,
        final: answerRaw.replace(/\$/g, "").slice(0, 200)
      };
    }

    if (strict) {
      if (!question.stem) throw new Error("题干不能为空");
      if (!question.answer) throw new Error("请填写答案");
    }
    return question;
  }

  function setSaving(active) {
    saveEl.disabled = active;
    saveEl.setAttribute("aria-busy", String(active));
    saveEl.textContent = active ? "正在写入…" : "保存入库";
  }

  function save() {
    var question;
    try {
      question = buildQuestion(true);
    } catch (error) {
      toast(error.message, "error");
      dock("录题保存被拦下：" + error.message);
      return;
    }
    setSaving(true);
    hostCall("bank.create", { question: question }).then(function (result) {
      setSaving(false);
      var id = result && result.id;
      savedEl.hidden = false;
      savedEl.textContent = "已入库 · " + id;
      savedEl.setAttribute("data-id", id || "");
      dirtySinceSave = false;
      toast("保存成功：" + id);
      dock("新题已写入真题题库（" + id + "）");
      metricsEl.setAttribute("data-saved-id", id || "");
    }, function (error) {
      setSaving(false);
      toast("保存失败：" + error.message, "error");
      dock("录题保存失败：" + error.message);
    });
  }

  function resetForm() {
    stemEl.value = "";
    answerEl.value = "";
    solutionEl.value = "";
    tagsEl.value = "";
    typeEl.value = "single_choice";
    diffEl.value = "medium";
    gradeEl.value = "高一";
    state.options = [
      { key: "A", content: "" },
      { key: "B", content: "" },
      { key: "C", content: "" },
      { key: "D", content: "" }
    ];
    renderOptions();
    applyType();
    renderPreview();
    if (savedEl) {
      savedEl.hidden = true;
      savedEl.textContent = "";
      savedEl.setAttribute("data-id", "");
    }
    metricsEl.setAttribute("data-saved-id", "");
    toast("表单已清空");
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
        var values = (message.payload && message.payload.values) || {};
        if (typeof values.grade === "string" && values.grade) gradeEl.value = values.grade;
        if (DIFF_LABEL[values.difficulty]) diffEl.value = values.difficulty;
        schedulePreview();
      }
      return;
    }

    if (message.kind !== "request") return;
    if (message.method === "plugin.activate") {
      root.hidden = false;
      fitPreview();
      renderPreview();
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
    }
    if (message.method === "plugin.deactivate") {
      root.hidden = true;
      return respond(event.source, message.id, true, { ready: false });
    }
    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD", "未实现的方法：" + message.method);
  });

  // ---------- 启动 ----------
  function bind() {
    [stemEl, solutionEl, answerEl, tagsEl].forEach(function (node) {
      node.addEventListener("input", schedulePreview);
    });
    typeEl.addEventListener("change", applyType);
    diffEl.addEventListener("change", schedulePreview);
    gradeEl.addEventListener("change", schedulePreview);
    addOptionEl.addEventListener("click", addOption);
    saveEl.addEventListener("click", save);
    cleanEl.addEventListener("click", cleanAll);
    resetEl.addEventListener("click", resetForm);
    if (typeof ResizeObserver === "function") {
      new ResizeObserver(fitPreview).observe(previewEl);
    } else {
      window.addEventListener("resize", fitPreview);
    }
  }

  function standaloneDemo() {
    root.hidden = false;
    stemEl.value = "已知函数 $f(x)=x^{2}-5x+6$，则方程 $f(x)=0$ 的解为（　　）";
    state.options = [
      { key: "A", content: "$x=1$" },
      { key: "B", content: "$x=2$" },
      { key: "C", content: "$x=2$ 或 $x=3$" },
      { key: "D", content: "$x=1$ 或 $x=6$" }
    ];
    answerEl.value = "C";
    solutionEl.value = "由 $x^{2}-5x+6=0$ 得 $(x-2)(x-3)=0$，故 $x=2$ 或 $x=3$。";
    tagsEl.value = "一元二次方程, 因式分解";
    renderOptions();
    applyType();
    fitPreview();
    renderPreview();
  }

  renderOptions();
  applyType();
  bind();
  renderEmpty();

  if (window.parent === window) standaloneDemo();
})();
