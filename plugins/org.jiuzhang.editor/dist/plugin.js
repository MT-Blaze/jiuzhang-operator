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
  var DIFF_LABEL = {
    L1: "基础", L2: "中档", L3: "难", L4: "压轴",
    // 契约 1.0 的旧值只做兜底
    basic: "基础", medium: "中档", hard: "难", novel: "压轴"
  };
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
  var returnEl = document.getElementById("edReturn");
  var topicPickEl = document.getElementById("edTopicPick");
  var topicTreeEl = document.getElementById("edTopicTree");
  var topicChipsEl = document.getElementById("edTopicChips");
  var editingBarEl = document.getElementById("edEditing");
  var editingIdEl = document.getElementById("edEditingId");
  var deleteEl = document.getElementById("edDelete");
  var variantEl = document.getElementById("edVariant");
  var modalEl = document.getElementById("edModal");
  var modalOkEl = document.getElementById("edModalOk");
  var modalCancelEl = document.getElementById("edModalCancel");
  var modalTextEl = document.getElementById("edModalText");
  var sourceNameEl = document.getElementById("edSourceName");
  var sourceEmptyEl = document.getElementById("edSourceEmpty");
  var sourceViewEl = document.getElementById("edSourceView");
  var sourceStageEl = document.getElementById("edSourceStage");
  var sourceCanvasEl = document.getElementById("edSourceCanvas");
  var sourceStatusEl = document.getElementById("edSourceStatus");
  var cropBoxEl = document.getElementById("edCropBox");
  var cropHintEl = document.getElementById("edCropHint");
  var cropInsertEl = document.getElementById("edCropInsert");
  var cropClearEl = document.getElementById("edCropClear");
  var cropAllEl = document.getElementById("edCropAll");
  var pickImageEl = document.getElementById("edPickImage");
  var imageFileEl = document.getElementById("edImageFile");

  var pending = new Map();
  var requestSeq = 0;
  var previewTimer = 0;
  var toastTimer = 0;
  var draftTimer = 0;
  var closeTimer = 0;
  var lastDraftAt = 0;
  var modalPrevFocus = null;
  var mathCache = new Map();
  var scale = 1;
  var dirtySinceSave = false;

  var DRAFT_THROTTLE_MS = 1200;
  var AUTO_CLOSE_MS = 1000;
  var NEW_DRAFT_KEY = "__new__";

  var state = {
    options: [
      { key: "A", content: "", imageIds: [] },
      { key: "B", content: "", imageIds: [] },
      { key: "C", content: "", imageIds: [] },
      { key: "D", content: "", imageIds: [] }
    ],
    // 编辑态（三端分离：录题是唯一输入端，题库/组卷/讲义点「去编辑」跳进来）
    editingId: null,
    editingFrom: "",
    editingFlags: [],
    topicIds: [],
    topicNames: {},
    images: [],
    tree: { roots: null, children: {}, expanded: {}, loading: false, error: "" },
    // 原图框选只服务本次录入：位图与选区都是易失态，不进草稿也不进题目结构。
    source: { bitmap: null, width: 0, height: 0, name: "", crop: null },
    sourceBusy: false
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

  var INLINE_RE = /(\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}|!\[[^\]]*\]\([^)]*\)|\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\$[^$\n]*?\$|\\\([\s\S]*?\\\)|\*\*[^*]+\*\*)/g;

  /** 只认底座托管路径与 asset:// 逻辑地址；远程 URL / data: / file: 一律当普通文本。 */
  function safeAssetUri(value) {
    var uri = String(value == null ? "" : value).trim();
    if (uri.indexOf("/static/uploads/") === 0) return uri;
    if (uri.indexOf("asset://") === 0 && uri.length > 8) return uri;
    return "";
  }

  function appendImageRef(parent, uri, alt, raw) {
    var path = safeAssetUri(uri);
    if (!path) {
      parent.appendChild(document.createTextNode(raw || String(uri == null ? "" : uri)));
      return;
    }
    if (path.indexOf("asset://") === 0) {
      // asset:// 是逻辑地址，沙箱 iframe 不能直接渲染；如实标出配图归属。
      parent.appendChild(el("span", "ed-opt-img", "（配图 " + path.slice(8) + "）"));
      return;
    }
    var img = document.createElement("img");
    img.className = "ed-inline-img";
    img.setAttribute("alt", alt || "题目配图");
    img.src = path;
    img.addEventListener("error", function () {
      if (img.parentNode) img.parentNode.replaceChild(el("span", "ed-opt-img", "（配图读取失败）"), img);
    });
    parent.appendChild(img);
  }

  function appendRich(parent, text) {
    var source = String(text == null ? "" : text);
    var last = 0;
    var match;
    INLINE_RE.lastIndex = 0;
    while ((match = INLINE_RE.exec(source)) !== null) {
      if (match.index > last) parent.appendChild(document.createTextNode(source.slice(last, match.index)));
      var token = match[0];
      if (token.slice(0, 16) === "\\includegraphics") {
        var graphic = /\{([^}]*)\}$/.exec(token);
        appendImageRef(parent, graphic ? graphic[1] : "", "", token);
      } else if (token.slice(0, 2) === "![") {
        var markdown = /^!\[([^\]]*)\]\(([^)]*)\)$/.exec(token);
        appendImageRef(parent, markdown ? markdown[2] : "", markdown ? markdown[1] : "", token);
      } else if (token.slice(0, 2) === "$$" && token.slice(-2) === "$$") {
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
      row.appendChild(input);
      var imageCount = (option.imageIds || []).length;
      if (imageCount) {
        var badge = el("span", "ed-option-image", "配图 " + imageCount);
        badge.title = "该选项带 " + imageCount + " 张配图资产（保存时随题保留）";
        row.appendChild(badge);
      }
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
    empty.appendChild(el("strong", null, "中间右侧是本页 A4 预览"));
    empty.appendChild(el("span", null, "在中间左侧写下题干与公式，排版会实时跟上"));
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
        if ((option.imageIds || []).length) {
          item.appendChild(el("span", "ed-opt-img", "（配图 " + option.imageIds.length + "）"));
        }
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
    var base = {
      pluginId: PLUGIN_ID,
      editingId: state.editingId || "",
      from: state.editingFrom || ""
    };
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: "stage.selection",
        payload: Object.assign({ question: question || null }, base)
      }, "*");
    } catch (error) { /* 忽略 */ }
  }

  function schedulePreview() {
    dirtySinceSave = true;
    if (savedEl) savedEl.hidden = true;
    window.clearTimeout(previewTimer);
    previewTimer = window.setTimeout(renderPreview, PREVIEW_DEBOUNCE_MS);
    queueDraftSave();
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

  // ---------- 原图框选切图（Canvas 截取 → 宿主 asset.upload） ----------
  // 沙箱页面的 img-src 只放行底座源，data:/blob: 都会被 CSP 拦；原图用
  // createImageBitmap 直接解码到 <canvas>，既不触网也不依赖图片 URL 白名单。
  var cropDrag = null;

  function clampValue(value, min, max) {
    if (!Number.isFinite(value)) return min;
    return Math.min(max, Math.max(min, value));
  }

  function fitSource() {
    if (!state.source.bitmap || !sourceCanvasEl || !sourceViewEl) return;
    var availableWidth = Math.max(80, sourceViewEl.clientWidth - 24);
    var availableHeight = Math.max(80, sourceViewEl.clientHeight - 24);
    var ratio = Math.min(1, availableWidth / state.source.width, availableHeight / state.source.height);
    if (!Number.isFinite(ratio) || ratio <= 0) ratio = 0.25;
    sourceCanvasEl.style.width = Math.max(1, Math.round(state.source.width * ratio)) + "px";
    sourceCanvasEl.style.height = Math.max(1, Math.round(state.source.height * ratio)) + "px";
    renderCropBox();
  }

  function placeCropBox(rect, active) {
    if (!cropBoxEl) return;
    cropBoxEl.hidden = false;
    cropBoxEl.setAttribute("data-active", active ? "true" : "false");
    cropBoxEl.style.left = rect.x + "px";
    cropBoxEl.style.top = rect.y + "px";
    cropBoxEl.style.width = rect.w + "px";
    cropBoxEl.style.height = rect.h + "px";
  }

  function renderCropBox() {
    if (!state.source.crop || !sourceStageEl || !cropBoxEl) return;
    var stage = sourceStageEl.getBoundingClientRect();
    placeCropBox({
      x: state.source.crop.x * stage.width,
      y: state.source.crop.y * stage.height,
      w: state.source.crop.w * stage.width,
      h: state.source.crop.h * stage.height
    }, false);
  }

  function clearCrop(message) {
    state.source.crop = null;
    if (cropBoxEl) cropBoxEl.hidden = true;
    if (cropInsertEl) cropInsertEl.disabled = true;
    if (cropClearEl) cropClearEl.disabled = true;
    if (cropHintEl) cropHintEl.textContent = message || "尚未选择区域。";
  }

  function setSourceBusy(active) {
    state.sourceBusy = active;
    if (pickImageEl) pickImageEl.disabled = active;
    if (cropAllEl) cropAllEl.disabled = active || !state.source.bitmap;
    if (cropInsertEl) {
      cropInsertEl.disabled = active || !state.source.crop;
      cropInsertEl.setAttribute("aria-busy", String(active));
      cropInsertEl.textContent = active ? "正在上传…" : "插入选区";
    }
    if (cropClearEl) cropClearEl.disabled = active || !state.source.crop;
    if (sourceStageEl) sourceStageEl.setAttribute("aria-busy", String(active));
  }

  function stagePoint(event) {
    var rect = sourceStageEl.getBoundingClientRect();
    return {
      x: clampValue(event.clientX - rect.left, 0, rect.width),
      y: clampValue(event.clientY - rect.top, 0, rect.height)
    };
  }

  function dragRect(point) {
    var start = cropDrag.start;
    return {
      x: Math.min(start.x, point.x),
      y: Math.min(start.y, point.y),
      w: Math.abs(point.x - start.x),
      h: Math.abs(point.y - start.y)
    };
  }

  function loadSourceFile(file) {
    if (!file) return;
    if (["image/png", "image/jpeg", "image/webp"].indexOf(file.type) < 0) {
      toast("只支持 PNG / JPEG / WebP 原图", "error");
      return;
    }
    if (typeof window.createImageBitmap !== "function") {
      toast("当前浏览器不支持本地图片解码，请换新版浏览器", "error");
      return;
    }
    window.createImageBitmap(file).then(function (bitmap) {
      if (state.source.bitmap && typeof state.source.bitmap.close === "function") state.source.bitmap.close();
      state.source = {
        bitmap: bitmap,
        width: bitmap.width,
        height: bitmap.height,
        name: file.name || "原图",
        crop: null
      };
      sourceCanvasEl.width = bitmap.width;
      sourceCanvasEl.height = bitmap.height;
      sourceCanvasEl.getContext("2d").drawImage(bitmap, 0, 0);
      if (sourceEmptyEl) sourceEmptyEl.hidden = true;
      if (sourceStageEl) sourceStageEl.hidden = false;
      if (sourceNameEl) {
        sourceNameEl.textContent = state.source.name + " · " + bitmap.width + "×" + bitmap.height;
        sourceNameEl.title = sourceNameEl.textContent;
      }
      if (sourceStatusEl) {
        sourceStatusEl.textContent = "";
        sourceStatusEl.removeAttribute("data-asset-id");
        sourceStatusEl.removeAttribute("data-asset-uri");
      }
      if (metricsEl) metricsEl.removeAttribute("data-asset-id");
      clearCrop("拖拽框选要截取的区域；也可直接点【整图插入】。");
      fitSource();
      setSourceBusy(false);
      toast("原图已载入，拖拽框选后点【插入选区】");
      dock("原图已载入：" + state.source.name + "（" + bitmap.width + "×" + bitmap.height + "）");
    }, function (error) {
      toast("原图载入失败：" + ((error && error.message) || "格式不支持"), "error");
    });
  }

  /** 从原图 Canvas 取一块像素：选区按归一化坐标存，缩放窗口后仍然准确。 */
  function captureCrop(whole) {
    var sourceWidth = state.source.width;
    var sourceHeight = state.source.height;
    var crop = (whole || !state.source.crop)
      ? { x: 0, y: 0, w: 1, h: 1 }
      : state.source.crop;
    var sx = clampValue(Math.round(crop.x * sourceWidth), 0, sourceWidth - 1);
    var sy = clampValue(Math.round(crop.y * sourceHeight), 0, sourceHeight - 1);
    var sw = Math.max(1, Math.min(Math.round(crop.w * sourceWidth), sourceWidth - sx));
    var sh = Math.max(1, Math.min(Math.round(crop.h * sourceHeight), sourceHeight - sy));
    var canvas = document.createElement("canvas");
    canvas.width = sw;
    canvas.height = sh;
    canvas.getContext("2d").drawImage(sourceCanvasEl, sx, sy, sw, sh, 0, 0, sw, sh);
    return { dataUrl: canvas.toDataURL("image/png"), width: sw, height: sh };
  }

  function insertAtCursor(snippet) {
    var value = stemEl.value;
    var focused = document.activeElement === stemEl;
    if (!focused) {
      var prefix = value && !/\n$/.test(value) ? "\n\n" : "";
      var next = value + prefix + snippet;
      stemEl.value = next;
      stemEl.focus();
      stemEl.setSelectionRange(next.length, next.length);
    } else {
      var start = typeof stemEl.selectionStart === "number" ? stemEl.selectionStart : value.length;
      var end = typeof stemEl.selectionEnd === "number" ? stemEl.selectionEnd : start;
      var before = value.slice(0, start);
      var after = value.slice(end);
      var lead = before && !/\n$/.test(before) ? "\n\n" : "";
      var trail = after && !/^\n/.test(after) ? "\n" : "";
      var insert = lead + snippet + trail;
      stemEl.value = before + insert + after;
      var caret = before.length + insert.length;
      stemEl.setSelectionRange(caret, caret);
    }
    stemEl.dispatchEvent(new Event("input", { bubbles: true }));
    schedulePreview();
  }

  function insertCrop(whole) {
    if (!state.source.bitmap) {
      toast("先选择一张原图", "error");
      return;
    }
    if (!whole && !state.source.crop) {
      toast("先在原图上框选一个区域", "error");
      return;
    }
    if (state.sourceBusy) return;
    var shot;
    try {
      shot = captureCrop(whole);
    } catch (error) {
      toast("截取选区失败：" + error.message, "error");
      return;
    }
    setSourceBusy(true);
    hostCall("asset.upload", { data_url: shot.dataUrl }).then(function (result) {
      var id = String((result && result.id) || "");
      var uri = String((result && result.uri) || "");
      if (!/^img_[A-Za-z0-9_-]{1,63}$/.test(id) || !/^\/static\/uploads\/[^\s]+$/.test(uri)) {
        throw new Error("宿主返回的资产地址不合法");
      }
      state.images = state.images.filter(function (image) { return image.id !== id; });
      state.images.push({ id: id, role: "stem", uri: uri });
      insertAtCursor("\\includegraphics{" + uri + "}");
      if (sourceStatusEl) {
        sourceStatusEl.textContent = "已插入 " + id + " · " + shot.width + "×" + shot.height + " px";
        sourceStatusEl.setAttribute("data-asset-id", id);
        sourceStatusEl.setAttribute("data-asset-uri", uri);
      }
      metricsEl.setAttribute("data-asset-id", id);
      toast("配图已插入题干：" + id);
      dock("框选配图已上传并插入题干（" + id + "）");
    }, function (error) {
      toast("配图上传失败：" + error.message, "error");
      dock("框选配图上传失败：" + error.message);
    }).then(function () {
      setSourceBusy(false);
    }, function () {
      setSourceBusy(false);
    });
  }


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
    if (state.topicIds.length) question.taxonomy = { topic_ids: state.topicIds.slice(0, 8) };
    var solution = solutionEl.value.trim();
    if (solution) question.solution = solution;
    if (state.images.length) question.images = state.images.slice();

    if (isChoice()) {
      var keys = state.options.map(function (option) { return option.key; });
      var options = state.options.map(function (option, index) {
        var entry = { key: keys[index], content: option.content.trim() };
        // 选项配图必须随表单一起回写：老师只改文字，绝不能把选项上已挂的图片资产洗掉。
        if (option.imageIds && option.imageIds.length) entry.image_ids = option.imageIds.slice();
        return entry;
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
    saveEl.textContent = active ? "正在写入…" : (state.editingId ? "保存并返回" : "保存入库");
  }

  function publish(event, payload) {
    try {
      window.parent.postMessage({
        protocol: PROTOCOL, kind: "notification", event: event, payload: payload || {}
      }, "*");
    } catch (error) {
      /* 通知丢了不致命 */
    }
  }

  function setEditMode(id, from) {
    state.editingId = id || null;
    state.editingFrom = from || "";
    returnEl.hidden = !id;
    editingBarEl.hidden = !id;
    if (deleteEl) deleteEl.hidden = !id;
    if (id) editingIdEl.textContent = id;
    setSaving(false);
  }

  /** 这次保存真正解决了哪些审核标记——只清被内容证实清掉的，不做「保存即清白」。 */
  function resolvedFlags(question) {
    var flags = state.editingFlags || [];
    if (!flags.length) return [];
    var resolved = [];
    var hasAnswer = Boolean(question.answer);
    if (hasAnswer) {
      ["answer_absent", "answer_region_empty", "type_manual_review",
       "needs_conclusion", "solution_absent"].forEach(function (flag) {
        if (flags.indexOf(flag) >= 0) resolved.push(flag);
      });
    }
    if (flags.indexOf("structure_conflict") >= 0
        && (question.options || []).length >= 2) resolved.push("structure_conflict");
    var mounted = question.taxonomy && (question.taxonomy.topic_ids || [])
      .filter(function (id) { return id.indexOf("tp_kx") === 0; }).length > 0;
    if (flags.indexOf("topic_unmapped") >= 0 && mounted) resolved.push("topic_unmapped");
    return resolved;
  }

  function draftTargetKey() {
    return state.editingId || NEW_DRAFT_KEY;
  }

  /** 表单态：草稿托管与派生变式都基于它，字段与 DOM 一一对应，可整体存取。 */
  function getFormState() {
    return {
      targetKey: draftTargetKey(),
      editingId: state.editingId || "",
      from: state.editingFrom || "",
      type: currentType(),
      difficulty: diffEl.value,
      grade: gradeEl.value,
      stem: stemEl.value,
      solution: solutionEl.value,
      answerText: answerEl.value,
      tagsText: tagsEl.value,
      options: state.options.map(function (option) {
        return { key: option.key, content: option.content, imageIds: (option.imageIds || []).slice() };
      }),
      topicIds: state.topicIds.slice(),
      topicNames: Object.assign({}, state.topicNames),
      images: state.images.slice()
    };
  }

  var TYPE_VALUES = ["single_choice", "multiple_choice", "fill_blank", "solution"];

  /** keepTarget=true：只灌内容，不动编辑目标（用于载入原题 / 回填 / 草稿覆盖同一题）。 */
  function applyFormState(source, keepTarget) {
    if (!source || typeof source !== "object") return false;
    if (!keepTarget) setEditMode(source.editingId || null, source.from || "");
    if (TYPE_VALUES.indexOf(source.type) >= 0) typeEl.value = source.type;
    if (DIFF_LABEL[source.difficulty]) diffEl.value = source.difficulty;
    if (["高一", "高二", "高三"].indexOf(source.grade) >= 0) gradeEl.value = source.grade;
    stemEl.value = String(source.stem || "");
    solutionEl.value = String(source.solution || "");
    answerEl.value = String(source.answerText || "");
    tagsEl.value = String(source.tagsText || "");
    var options = Array.isArray(source.options) && source.options.length >= 2
      ? source.options
      : [
        { key: "A", content: "" }, { key: "B", content: "" },
        { key: "C", content: "" }, { key: "D", content: "" }
      ];
    state.options = options.map(function (option) {
      return { key: option.key, content: option.content || "", imageIds: (option.imageIds || []).slice() };
    });
    state.topicIds = (source.topicIds || []).slice(0, 8);
    state.topicNames = Object.assign({}, source.topicNames || {});
    state.images = (source.images || []).slice();
    renderOptions();
    applyType();
    renderTopicChips();
    renderPreview();
    return true;
  }

  /** 题库出参 → 表单态：与 getFormState 口径一致，回填与草稿走同一套字段。 */
  function documentToFormSource(document, editingId, from) {
    var answer = document.answer || null;
    return {
      editingId: editingId || "",
      from: from || "",
      type: document.type,
      difficulty: document.difficulty,
      grade: document.grade || "高一",
      stem: document.stem || "",
      solution: document.solution || "",
      answerText: answer
        ? (answer.kind === "choice" ? (answer.choice_keys || []).join(",") : (answer.content || ""))
        : "",
      tagsText: (document.tags || []).join(", "),
      options: (document.options || []).map(function (option) {
        return { key: option.key, content: option.content || "", imageIds: (option.image_ids || []).slice() };
      }),
      topicIds: ((document.taxonomy || {}).topic_ids || []).slice(),
      topicNames: {},
      images: (document.images || []).slice()
    };
  }

  function fillForm(document) {
    var source = documentToFormSource(document, state.editingId, state.editingFrom);
    // 出参的 taxonomy 带着主挂载节点的中文名，chip 先按它回显；
    // 其余挂载点没有可靠名称可取，宁可先显示 id，也不给老师贴错名字。
    if (source.topicIds.length) {
      var primaryName = document.taxonomy.topic || document.taxonomy.section
        || document.taxonomy.chapter || document.taxonomy.textbook || "";
      if (primaryName) source.topicNames[source.topicIds[0]] = primaryName;
    }
    applyFormState(source, true);
  }

  // ---------- 草稿托管（经宿主代持，插件不碰本地存储） ----------
  function persistDraft() {
    if (!dirtySinceSave) return;   // 干净态（刚保存 / 刚载入原题）不留草稿
    var key = draftTargetKey();
    hostCall("draft.save", { key: key, value: getFormState() }).then(function (res) {
      if (res && res.saved_at) lastDraftAt = res.saved_at;
    }, function () { /* 存不下不拦老师录题，静默 */ });
  }

  function queueDraftSave() {
    window.clearTimeout(draftTimer);
    draftTimer = window.setTimeout(persistDraft, DRAFT_THROTTLE_MS);
  }

  function flushDraft() {
    window.clearTimeout(draftTimer);
    persistDraft();
  }

  function clearDraft(key) {
    hostCall("draft.save", { key: key || draftTargetKey(), value: null }).then(function () {
    }, function () {});
  }

  function maybeRestoreDraft(id) {
    hostCall("draft.load", { key: id || NEW_DRAFT_KEY }).then(function (res) {
      var draft = res && res.value;
      if (!draft) return;
      if (!applyFormState(draft, true)) return;
      dirtySinceSave = true;
      if (savedEl) savedEl.hidden = true;
      toast("已恢复未保存的草稿（关页前自动留存）");
      dock("已从宿主草稿箱恢复未保存内容");
    }, function () { /* 读草稿失败按无草稿处理 */ });
  }

  function loadForEdit(id, from) {
    if (!id) {
      setEditMode(null, "");
      state.editingFlags = [];
      return;
    }
    hostCall("bank.get", { id: id }).then(function (document) {
      setEditMode(id, from);
      state.editingFlags = ((document.extensions || {})["org.jiuzhang.core-bank.migration"] || {}).flags || [];
      fillForm(document);
      savedEl.hidden = true;
      dirtySinceSave = false;
      // 载入原题后再查一次草稿箱：老师上次没保存就关了页，这里把内容找回来。
      maybeRestoreDraft(id);
      var hint = state.editingFlags.length
        ? "这道题带着 " + state.editingFlags.length + " 个待审标记：" + state.editingFlags.join("、")
        : "已载入原题，改完点「保存并返回」";
      toast(hint);
      dock("录题工作台已载入 " + id + "（" + (state.editingFlags.length ? "待审 " + state.editingFlags.join("、") : "无标记") + "）");
    }, function (error) {
      toast("读题失败：" + error.message, "error");
      dock("载入待编辑题目失败：" + error.message);
    });
  }

  /** 保存后把宿主归一过的文本回灌表单：老师看到的就是真正入库的写法。 */
  function syncCleanText(result) {
    if (!result || typeof result !== "object") return;
    if (typeof result.stem === "string") stemEl.value = result.stem;
    if (typeof result.solution === "string") solutionEl.value = result.solution;
    var answer = result.answer || null;
    if (answer) {
      answerEl.value = answer.kind === "choice"
        ? (answer.choice_keys || []).join(",")
        : String(answer.content || "");
    }
    if (Array.isArray(result.options)) {
      result.options.forEach(function (option, index) {
        if (state.options[index] && typeof option.content === "string") {
          state.options[index].content = option.content;
        }
      });
      renderOptions();
    }
    renderPreview();
  }

  function afterSaved(result, updating) {
    setSaving(false);
    var id = result && result.id;
    savedEl.hidden = false;
    savedEl.textContent = (updating ? "已保存 · " : "已入库 · ") + id;
    savedEl.setAttribute("data-id", id || "");
    dirtySinceSave = false;
    syncCleanText(result);
    // 保存成功即作废该目标的草稿：老师拿到的是已落库的内容，不该再恢复旧草稿。
    clearDraft(updating ? (id || state.editingId) : NEW_DRAFT_KEY);
    window.clearTimeout(draftTimer);
    state.editingFlags = ((result && result.extensions) || {})["org.jiuzhang.core-bank.migration"]
      ? (result.extensions["org.jiuzhang.core-bank.migration"].flags || [])
      : [];
    toast(updating ? "已保存：" + id : "保存成功：" + id);
    dock((updating ? "题目已更新（" : "新题已写入真题题库（") + id + "），各端自动回流刷新");
    metricsEl.setAttribute("data-saved-id", id || "");
    if (updating) {
      editingBarEl.textContent = "已保存 " + id + " · 各端已回流刷新";
    }
    // 极致好用：保存后 Toast 停留，1 秒后自动收起编辑页、切回来源列表；
    // 列表的后台静默刷新由宿主对 system.question_updated 的广播负责，无白屏。
    if (state.editingFrom) scheduleAutoClose(state.editingFrom);
  }

  /** 保存成功后 1 秒自动收页：交回宿主关页签并切回发起端。 */
  function scheduleAutoClose(origin) {
    window.clearTimeout(closeTimer);
    closeTimer = window.setTimeout(function () {
      publish("system.editor_close", { plugin_id: origin, id: state.editingId || "" });
    }, AUTO_CLOSE_MS);
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
    var updating = Boolean(state.editingId);
    var payload = { question: question };
    if (updating) {
      payload.question.clear_flags = resolvedFlags(question);
      if (!payload.question.clear_flags.length) delete payload.question.clear_flags;
    }
    setSaving(true);
    hostCall(updating ? "bank.update" : "bank.create",
      updating ? Object.assign({ id: state.editingId }, payload) : payload
    ).then(function (result) {
      afterSaved(result, updating);
    }, function (error) {
      setSaving(false);
      toast("保存失败：" + error.message, "error");
      dock("录题保存失败：" + error.message);
    });
  }

  /** 另存为派生变式：拿当前表单内容新建一题（底座重新签发 id），绝不覆盖原题。 */
  function saveAsVariant() {
    var question;
    try {
      question = buildQuestion(true);
    } catch (error) {
      toast(error.message, "error");
      dock("派生变式被拦下：" + error.message);
      return;
    }
    // 派生变式一定是「新题」：去掉可能残留的 id 与审核清标，交底座重新签发。
    delete question.id;
    delete question.clear_flags;
    setSaving(true);
    hostCall("bank.create", { question: question }).then(function (result) {
      setSaving(false);
      var id = result && result.id;
      var parent = state.editingId || "";
      // 切到新变式的编辑态：后续保存改的是这道新题，不再回写原题。
      state.images = (result && result.images) || state.images;
      setEditMode(id, state.editingFrom);
      clearDraft(NEW_DRAFT_KEY);
      dirtySinceSave = false;
      savedEl.hidden = false;
      savedEl.textContent = "已派生 · " + id;
      savedEl.setAttribute("data-id", id || "");
      metricsEl.setAttribute("data-saved-id", id || "");
      toast(parent ? "已生成派生变式：" + id + "（原题 " + parent + " 未改动）" : "已生成新题：" + id);
      dock("派生变式已入库（" + id + "）" + (parent ? "，源自 " + parent + " 且原题保持不变" : ""));
    }, function (error) {
      setSaving(false);
      toast("派生失败：" + error.message, "error");
      dock("另存为派生变式失败：" + error.message);
    });
  }

  // ---------- 删除本题（二次确认） ----------
  function openConfirm(text, onOk) {
    if (!modalEl) { onOk(); return; }
    modalPrevFocus = document.activeElement;
    if (modalTextEl) modalTextEl.textContent = text;
    modalEl.hidden = false;
    var overlay = modalEl.querySelector(".ed-modal") || modalEl;
    overlay.setAttribute("aria-hidden", "false");
    var ok = function () {
      closeConfirm();
      onOk();
    };
    if (modalOkEl) {
      var newOk = modalOkEl.cloneNode(true);
      modalOkEl.parentNode.replaceChild(newOk, modalOkEl);
      modalOkEl = newOk;
      modalOkEl.addEventListener("click", ok);
    }
    if (modalCancelEl) {
      modalCancelEl.onclick = closeConfirm;
    }
    if (modalOkEl) modalOkEl.focus();
  }

  function closeConfirm() {
    if (!modalEl) return;
    modalEl.hidden = true;
    var overlay = modalEl.querySelector(".ed-modal") || modalEl;
    overlay.setAttribute("aria-hidden", "true");
    if (modalPrevFocus && typeof modalPrevFocus.focus === "function") modalPrevFocus.focus();
    modalPrevFocus = null;
  }

  function requestDelete() {
    if (!state.editingId) {
      toast("当前没有正在编辑的题目，无需删除", "error");
      return;
    }
    var id = state.editingId;
    openConfirm("确定删除题目 " + id + " 吗？此操作会把它从本地真题库移除，且不可撤销。", function () {
      setSaving(true);
      hostCall("bank.delete", { id: id }).then(function () {
        setSaving(false);
        dirtySinceSave = false;
        clearDraft(id);
        window.clearTimeout(closeTimer);
        toast("已删除：" + id);
        dock("题目已删除（" + id + "），各端自动回流刷新");
        var origin = state.editingFrom;
        setEditMode(null, "");
        if (origin) publish("system.editor_close", { plugin_id: origin, id: id });
      }, function (error) {
        setSaving(false);
        toast("删除失败：" + error.message, "error");
        dock("删除题目失败：" + error.message);
      });
    });
  }

  // ---------- 考向大纲树选择器 ----------
  function fetchTopics(parentId) {
    return hostCall("bank.topics", parentId ? { parent_id: parentId } : {})
      .then(function (result) { return (result && result.items) || []; });
  }

  function toggleTopic(id) {
    var index = state.topicIds.indexOf(id);
    if (index >= 0) {
      state.topicIds.splice(index, 1);
    } else {
      if (state.topicIds.length >= 8) {
        toast("一题最多挂 8 个考向", "error");
        return;
      }
      state.topicIds.push(id);
    }
    renderTopicChips();
    renderTree();
  }

  function renderTopicChips() {
    if (!topicChipsEl) return;
    topicChipsEl.textContent = "";
    if (!state.topicIds.length) {
      topicChipsEl.textContent = "尚未挂载考向";
      return;
    }
    state.topicIds.forEach(function (id) {
      var chip = el("button", "ed-topic-chip", (state.topicNames[id] || id) + " ×");
      chip.type = "button";
      chip.setAttribute("aria-label", "取消挂载 " + (state.topicNames[id] || id));
      chip.addEventListener("click", function () { toggleTopic(id); });
      topicChipsEl.appendChild(chip);
    });
  }

  function renderTreeNode(node) {
    var item = document.createElement("li");
    var row = document.createElement("div");
    row.className = "ed-topic-rowline";
    if (node.has_children) {
      var caret = el("button", "ed-topic-caret", state.tree.expanded[node.id] ? "▾" : "▸");
      caret.type = "button";
      caret.setAttribute("aria-expanded", String(Boolean(state.tree.expanded[node.id])));
      caret.setAttribute("aria-label", (state.tree.expanded[node.id] ? "收起 " : "展开 ") + node.name);
      caret.addEventListener("click", function () {
        if (state.tree.expanded[node.id]) {
          state.tree.expanded[node.id] = false;
          renderTree();
          return;
        }
        state.tree.expanded[node.id] = true;
        if (state.tree.children[node.id]) { renderTree(); return; }
        fetchTopics(node.id).then(function (items) {
          state.tree.children[node.id] = items;
          renderTree();
        }, function () {
          state.tree.children[node.id] = [];
          renderTree();
        });
      });
      row.appendChild(caret);
    } else {
      row.appendChild(el("span", "ed-topic-caret ed-topic-leaf", "·"));
    }
    var picked = state.topicIds.indexOf(node.id) >= 0;
    if (picked) state.topicNames[node.id] = node.name;
    var name = el("button", "ed-topic-name" + (picked ? " ed-topic-on" : ""), node.name);
    name.type = "button";
    name.setAttribute("aria-pressed", String(picked));
    name.addEventListener("click", function () { toggleTopic(node.id); });
    row.appendChild(name);
    row.appendChild(el("span", "ed-topic-count", String(node.question_count || 0)));
    if (node.status === "draft") row.appendChild(el("span", "ed-topic-draft", "待补录"));
    item.appendChild(row);
    if (node.has_children && state.tree.expanded[node.id]) {
      var branch = document.createElement("ul");
      branch.className = "ed-topic-branch";
      var kids = state.tree.children[node.id];
      if (!kids) {
        branch.appendChild(el("li", "ed-topic-loading", "正在读取…"));
      } else if (!kids.length) {
        branch.appendChild(el("li", "ed-topic-loading", "这一层还没有子节点"));
      } else {
        kids.forEach(function (child) { branch.appendChild(renderTreeNode(child)); });
      }
      item.appendChild(branch);
    }
    return item;
  }

  function renderTree() {
    if (!topicTreeEl) return;
    topicTreeEl.textContent = "";
    if (state.tree.loading && !state.tree.roots) {
      topicTreeEl.appendChild(el("p", "ed-topic-loading", "正在读取大纲…"));
      return;
    }
    if (state.tree.error) {
      topicTreeEl.appendChild(el("p", "ed-topic-error", "大纲读取失败：" + state.tree.error));
      return;
    }
    var trunk = document.createElement("ul");
    trunk.className = "ed-topic-branch";
    (state.tree.roots || []).forEach(function (node) { trunk.appendChild(renderTreeNode(node)); });
    topicTreeEl.appendChild(trunk);
  }

  function openTopicTree() {
    if (!topicTreeEl) return;
    topicTreeEl.hidden = !topicTreeEl.hidden;
    if (topicTreeEl.hidden || state.tree.roots) return;
    state.tree.loading = true;
    renderTree();
    fetchTopics("").then(function (items) {
      state.tree.roots = items;
      state.tree.loading = false;
      renderTree();
    }, function (error) {
      state.tree.loading = false;
      state.tree.error = error.message;
      renderTree();
    });
  }

  function resetForm() {
    var abandoned = draftTargetKey();
    setEditMode(null, "");
    state.editingFlags = [];
    state.topicIds = [];
    state.topicNames = {};
    state.images = [];
    stemEl.value = "";
    answerEl.value = "";
    solutionEl.value = "";
    tagsEl.value = "";
    typeEl.value = "single_choice";
    diffEl.value = "L2";
    gradeEl.value = "高一";
    state.options = [
      { key: "A", content: "", imageIds: [] },
      { key: "B", content: "", imageIds: [] },
      { key: "C", content: "", imageIds: [] },
      { key: "D", content: "", imageIds: [] }
    ];
    renderOptions();
    applyType();
    renderTopicChips();
    renderPreview();
    dirtySinceSave = false;
    window.clearTimeout(draftTimer);
    clearDraft(abandoned);
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
      if (message.event === "system.open_editor") {
        // 三端分离的唯一入口：题库/组卷/讲义点「去编辑」，宿主把题号注到这里
        var wanted = (message.payload && message.payload.question_id) || "";
        var origin = (message.payload && message.payload.from) || "";
        if (wanted) loadForEdit(wanted, origin);
        return;
      }
      if (message.event === "ui.params.changed") {
        var values = (message.payload && message.payload.values) || {};
        if (typeof values.grade === "string" && values.grade) gradeEl.value = values.grade;
        if (DIFF_LABEL[values.difficulty]) diffEl.value = values.difficulty;
        schedulePreview();
        return;
      }
      if (message.event === "editor.apply_patch") {
        // 右侧 AI 副驾改写题干/解析后，老师点「回填」由宿主把候选文本推回来。
        var patch = message.payload || {};
        var patchId = typeof patch.id === "string" ? patch.id : "";
        var field = patch.field === "solution" ? "solution" : "stem";
        var text = typeof patch.value === "string" ? patch.value : "";
        if (patchId && patchId !== (state.editingId || "") ) {
          // 目标题号对不上：老师可能已经换了题，绝不回填到错的题上。
          toast("AI 改写结果与当前编辑的题目不一致，已忽略回填", "error");
          return;
        }
        if (!text) { toast("AI 没有给出可用内容", "error"); return; }
        if (field === "solution") solutionEl.value = text;
        else stemEl.value = text;
        dirtySinceSave = true;
        renderPreview();
        queueDraftSave();
        toast("AI 已回填" + (field === "solution" ? "解析" : "题干") + "，请核对后保存");
        dock("AI 副驾已回填" + (field === "solution" ? "解析" : "题干"));
        return;
      }
      return;
    }

    if (message.kind !== "request") return;
    if (message.method === "plugin.activate") {
      root.hidden = false;
      fitPreview();
      fitSource();
      renderPreview();
      // 全新打开（非跳题进入）时，先看草稿箱里有没有上次没保存的新题草稿。
      if (!state.editingId) maybeRestoreDraft(NEW_DRAFT_KEY);
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
    }
    if (message.method === "plugin.deactivate") {
      // 宿主即将摘掉本帧（休眠/关页）：趁 postMessage 还发得出去，把未保存内容交回宿主草稿箱。
      flushDraft();
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
    if (variantEl) variantEl.addEventListener("click", saveAsVariant);
    if (deleteEl) deleteEl.addEventListener("click", requestDelete);
    if (pickImageEl && imageFileEl) {
      pickImageEl.addEventListener("click", function () { imageFileEl.click(); });
      imageFileEl.addEventListener("change", function () {
        var file = imageFileEl.files && imageFileEl.files[0];
        if (file) loadSourceFile(file);
        imageFileEl.value = "";
      });
    }
    if (cropAllEl) cropAllEl.addEventListener("click", function () { insertCrop(true); });
    if (cropInsertEl) cropInsertEl.addEventListener("click", function () { insertCrop(false); });
    if (cropClearEl) cropClearEl.addEventListener("click", function () { clearCrop(); });
    if (sourceStageEl) {
      sourceStageEl.addEventListener("pointerdown", function (event) {
        if (!state.source.bitmap || state.sourceBusy) return;
        if (event.pointerType === "mouse" && event.button !== 0) return;
        event.preventDefault();
        sourceStageEl.focus();
        cropDrag = { start: stagePoint(event), pointerId: event.pointerId };
        state.source.crop = null;
        cropInsertEl.disabled = true;
        cropClearEl.disabled = true;
        placeCropBox({ x: cropDrag.start.x, y: cropDrag.start.y, w: 0, h: 0 }, true);
        cropHintEl.textContent = "拖拽出矩形…";
        try { sourceStageEl.setPointerCapture(event.pointerId); } catch (error) { /* 指针已释放 */ }
      });
      sourceStageEl.addEventListener("pointermove", function (event) {
        if (!cropDrag) return;
        event.preventDefault();
        var rect = dragRect(stagePoint(event));
        placeCropBox(rect, true);
        cropHintEl.textContent = Math.round(rect.w) + " × " + Math.round(rect.h) + " px";
      });
      sourceStageEl.addEventListener("pointerup", function (event) {
        if (!cropDrag) return;
        event.preventDefault();
        var rect = dragRect(stagePoint(event));
        try { sourceStageEl.releasePointerCapture(cropDrag.pointerId); } catch (error) { /* 已释放 */ }
        cropDrag = null;
        var stage = sourceStageEl.getBoundingClientRect();
        if (rect.w < 12 || rect.h < 12 || !stage.width || !stage.height) {
          clearCrop("框选太小，已忽略；请重新拖拽一个更大的区域。");
          return;
        }
        state.source.crop = {
          x: rect.x / stage.width,
          y: rect.y / stage.height,
          w: rect.w / stage.width,
          h: rect.h / stage.height
        };
        cropInsertEl.disabled = false;
        cropClearEl.disabled = false;
        placeCropBox(rect, false);
        var naturalWidth = Math.max(1, Math.round(state.source.width * state.source.crop.w));
        var naturalHeight = Math.max(1, Math.round(state.source.height * state.source.crop.h));
        cropHintEl.textContent = "选区 " + naturalWidth + " × " + naturalHeight + " px，点【插入选区】。";
        if (sourceStatusEl) sourceStatusEl.textContent = "";
      });
      sourceStageEl.addEventListener("pointercancel", function () {
        cropDrag = null;
        clearCrop("框选已取消。");
      });
      sourceStageEl.addEventListener("keydown", function (keyEvent) {
        if (keyEvent.key === "Escape" && (state.source.crop || cropDrag)) {
          keyEvent.preventDefault();
          cropDrag = null;
          clearCrop("框选已取消。");
        }
      });
    }
    if (modalEl) {
      modalEl.addEventListener("keydown", function (keyEvent) {
        if (keyEvent.key === "Escape") { keyEvent.preventDefault(); closeConfirm(); }
      });
    }
    window.addEventListener("beforeunload", flushDraft);
    if (topicPickEl) topicPickEl.addEventListener("click", openTopicTree);
    if (returnEl) returnEl.addEventListener("click", function () {
      if (state.editingFrom) publish("system.return_from_editor", { plugin_id: state.editingFrom });
      else toast("这次是直接从录题进来的，没有来源页可返回");
    });
    renderTopicChips();
    setSourceBusy(false);
    if (typeof ResizeObserver === "function") {
      var layoutObserver = new ResizeObserver(function () {
        fitPreview();
        fitSource();
      });
      layoutObserver.observe(previewEl);
      if (sourceViewEl) layoutObserver.observe(sourceViewEl);
    } else {
      window.addEventListener("resize", function () {
        fitPreview();
        fitSource();
      });
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
