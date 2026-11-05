/**
 * ui_columns.js —— plugin.js 的「三栏渲染」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var coreState = deps.coreState;
    var OPTION_KEYS = coreState.OPTION_KEYS;
    var RENDER_DEBOUNCE_MS = coreState.RENDER_DEBOUNCE_MS;
    var reanchorCrop = deps.reanchorCrop;
    var appendBody = deps.appendBody;
    var appendRich = deps.appendRich;
    var buildExamSource = deps.buildExamSource;
    var clampValue = deps.clampValue;
    var coreRich = deps.coreRich;
    var el = deps.el;
    var fieldLabel = deps.fieldLabel;
    var fieldRanges = deps.fieldRanges;
    var keyFromPatchId = deps.keyFromPatchId;
    var openCrop = deps.openCrop;
    var parseExamSource = deps.parseExamSource;
    var publishSelectionSoon = deps.publishSelectionSoon;
    var queueWorklistSave = deps.queueWorklistSave;
    var renderPool = deps.renderPool;
    var replaceField = deps.replaceField;
    var safeAssetUri = deps.safeAssetUri;
    var setFormatButtons = deps.setFormatButtons;
    var amberReasons = deps.amberReasons;
    var metaFor = deps.metaFor;
    var state = coreState.state;
    var toast = deps.toast;
    var colsEl = deps.dom.colsEl;
    var dirtyEl = deps.dom.dirtyEl;
    var formatEl = deps.dom.formatEl;
    var imageBodyEl = deps.dom.imageBodyEl;
    var imageNameEl = deps.dom.imageNameEl;
    var metricsEl = deps.dom.metricsEl;
    var progressEl = deps.dom.progressEl;
    var renderBodyEl = deps.dom.renderBodyEl;
    var root = deps.dom.root;
    var sourceBodyEl = deps.dom.sourceBodyEl;

  var renderTimer = 0;
  var scrollLock = false;
  var scrollRestore = false;

  // ---------- 三栏渲染 ----------

  /** 这一题自己的配图：真题看 images；没有就退到本批次的原卷页；假数据才用 dev 占位图。 */
  function itemImage(item) {
    var images = (item.question && Array.isArray(item.question.images)) ? item.question.images : [];
    for (var index = 0; index < images.length; index += 1) {
      var uri = safeAssetUri(images[index] && images[index].uri);
      if (uri) return { uri: uri, id: String((images[index] && images[index].id) || "") };
    }
    // 原卷页是批次层的东西：题自己没裁图时，左栏拿它给老师对照原卷。
    var page = item && item.pageImage;
    var pageUri = safeAssetUri(page && page.uri);
    if (pageUri) return { uri: pageUri, id: "", page: Number(page.page) || 1 };
    var demo = safeAssetUri(item.dev && item.dev.image_uri);
    return demo ? { uri: demo, id: "" } : null;
  }

  function renderImageCell(item, index) {
    var cell = el("div", "ed-img-cell");
    cell.setAttribute("role", "listitem");
    cell.setAttribute("data-index", String(index));
    var picture = itemImage(item);
    var frame = el("div", "ed-img-frame");
    if (picture) {
      // 原卷页是整页，先按栏宽铺满、再用 CSS 限高；裁切过的题图尺寸随原样。
      if (picture.page) frame.className += " ed-img-page";
      var img = document.createElement("img");
      img.src = picture.uri;
      img.alt = picture.page
        ? "第 " + (index + 1) + " 题 · 原卷第 " + picture.page + " 页"
        : "第 " + (index + 1) + " 题原图";
      img.addEventListener("error", function () {
        if (img.parentNode) {
          img.parentNode.replaceChild(el("p", "ed-img-missing", "原图读取失败"), img);
        }
      });
      frame.appendChild(img);
      var box = el("div", "ed-img-box");
      box.setAttribute("data-box", "stem");
      frame.appendChild(box);
    } else {
      frame.appendChild(el("p", "ed-img-missing", "本题没有配图。框选切题可以把卷子上的这一题裁下来。"));
    }
    cell.appendChild(frame);
    // 切图台入口：点开就是一只跟着鼠标的放大镜，拖拽框选，左键松开切完。
    // 文本还原页是 SVG，沙箱 CSP 既不放 blob: 也不放 data:，canvas 解不动它，
    // 干脆不给切图入口——老师要裁图可以贴一张图或直接改源码。
    var croppable = !(picture && /\.svg(?:$|\?)/i.test(String(picture.uri)));
    if (croppable) {
      var tools = el("div", "ed-img-tools");
      var pageOnly = picture && picture.page;
      var cropBtn = el("button", "ed-img-crop-btn",
        picture && !pageOnly ? "重新框选" : "框选切题");
      cropBtn.type = "button";
      cropBtn.setAttribute("data-index", String(index));
      cropBtn.setAttribute("aria-label",
        (pageOnly ? "从原卷第 " + picture.page + " 页框选切题（第 "
          : (picture ? "重新框选第 " : "框选切题（第 ")) + (index + 1) + " 题）");
      cropBtn.addEventListener("click", function () { openCrop(item, index); });
      tools.appendChild(cropBtn);
      cell.appendChild(tools);
    }
    var paper = (item.question && item.question.source && item.question.source.paper_title) || "无来源卷";
    var caption = "第 " + (index + 1) + " 题 · " + paper;
    if (picture && picture.page) caption += " · 原卷第 " + picture.page + " 页";
    if (!croppable && picture) caption += " · 文本还原页";
    var jump = el("button", "ed-img-jump", "跳到第 " + (index + 1) + " 题");
    jump.type = "button";
    jump.setAttribute("data-index", String(index));
    jump.setAttribute("aria-label", "跳到第 " + (index + 1) + " 题 · " + paper);
    jump.addEventListener("click", function () { jumpTo(index); });
    cell.appendChild(jump);
    cell.appendChild(el("p", "ed-img-caption", caption));
    return cell;
  }


  /** 源码：一整段 exam-zh 源码，可编辑——它是唯一的录入面。 */
  function renderSourceCell(item, index) {
    if (state.format === "boxed") return renderBoxedCell(item, index);
    var cell = el("div", "ed-src-cell");
    cell.setAttribute("data-index", String(index));
    cell.appendChild(el("span", "ed-src-tag", "第 " + (index + 1) + " 题 · exam-zh 全量源码"));
    var area = document.createElement("textarea");
    area.className = "ed-src-area";
    area.setAttribute("aria-label", "第 " + (index + 1) + " 题 LaTeX 源码");
    area.setAttribute("spellcheck", "false");
    area.setAttribute("data-index", String(index));
    area.setAttribute("data-field", "source");
    area.value = item.source;
    area.addEventListener("input", function () {
      onSourceInput(index, area.value);
    });
    // 选区也要上桥：AI 帮改靠光标落在哪一段来认字段，只发源码不够
    ["click", "keyup", "select"].forEach(function (type) {
      area.addEventListener(type, publishSelectionSoon);
    });
    cell.appendChild(area);
    return cell;
  }

  /** 卡片的底线：环境骨架不完整或有游离文本时，绝不自动重组——先如实说明。 */
  function boxedBlockReason(parsed) {
    if (parsed.stray) return "源码里有环境外的内容，请先在源码清掉再拆框";
    if (!parsed.env) return "缺 \\begin{question} 或 \\begin{problem}，拆不出框";
    if (!parsed.hasSolution) return "缺 \\begin{solution}，答案与解析没有归属";
    if (parsed.hasChoices && parsed.choices.length < 2) return "选项不足两项";
    return "";
  }

  function boxFieldCell(cell, index, label, envName, value, field, pos, multiline) {
    var wrap = el("div", "ed-box");
    var head = el("div", "ed-box-head");
    head.appendChild(el("span", "ed-box-env", envName));
    head.appendChild(el("span", "ed-box-field", label));
    wrap.appendChild(head);
    var node = document.createElement(multiline ? "textarea" : "input");
    node.className = multiline ? "ed-box-area ed-box-textarea" : "ed-box-area ed-box-input";
    node.setAttribute("data-index", String(index));
    node.setAttribute("data-field", field);
    if (pos != null) node.setAttribute("data-pos", String(pos));
    node.setAttribute("aria-label", label + "（" + envName + " 内容，只能改内容）");
    node.setAttribute("spellcheck", "false");
    if (!multiline) node.setAttribute("type", "text");
    node.value = value;
    node.addEventListener("input", function () {
      onBoxInput(index, field, pos, node.value);
    });
    if (field === "stem" || field === "solution") {
      ["click", "keyup", "select"].forEach(function (type) {
        node.addEventListener(type, publishSelectionSoon);
      });
    }
    wrap.appendChild(node);
    cell.appendChild(wrap);
    return node;
  }

  /** 卡片：框里只有内容，\begin{…} 骨架是写死的标签，摸不到也改不了。 */
  function renderBoxedCell(item, index) {
    var cell = el("div", "ed-boxed");
    cell.setAttribute("data-index", String(index));
    var parsed = parsedOf(item);
    cell.appendChild(el("span", "ed-src-tag", "第 " + (index + 1) + " 题 · 卡片（改完自动重组源码）"));
    var reason = boxedBlockReason(parsed);
    if (reason) {
      cell.appendChild(el("p", "ed-boxed-blocked", "卡片暂不可用：" + reason));
      var area = document.createElement("textarea");
      area.className = "ed-src-area";
      area.setAttribute("aria-label", "第 " + (index + 1) + " 题 LaTeX 源码");
      area.setAttribute("spellcheck", "false");
      area.setAttribute("data-index", String(index));
      area.setAttribute("data-field", "source");
      area.value = item.source;
      area.addEventListener("input", function () {
        onSourceInput(index, area.value);
      });
      cell.appendChild(area);
      return cell;
    }
    boxFieldCell(cell, index, "题干", "\\begin{" + parsed.env + "}", parsed.stem, "stem", null, true);
    if (parsed.hasChoices) {
      parsed.choices.forEach(function (content, position) {
        boxFieldCell(cell, index, "选项 " + (OPTION_KEYS[position] || position + 1),
          "\\item", content, "choice", position, true);
      });
    }
    boxFieldCell(cell, index, "答案", "\\begin{solution} 首行", parsed.answer, "answer", null, false);
    boxFieldCell(cell, index, "解析", "\\begin{solution} 内", parsed.analysis, "analysis", null, true);
    return cell;
  }

  /** 框里的内容 → 结构化题目；环境骨架由 buildExamSource 重新给出，不接受外部改写。 */
  function boxesToQuestion(parsed, stem, choices, answer, analysis) {
    var type = parsed.type;
    var question = {
      type: type,
      stem: typeof stem === "string" ? stem : parsed.stem,
      options: [],
      solution: typeof analysis === "string" ? analysis : parsed.analysis
    };
    var list = Array.isArray(choices) ? choices : parsed.choices;
    var text = typeof answer === "string" ? answer : parsed.answer;
    if (type === "single_choice" || type === "multiple_choice") {
      question.options = list.map(function (content, position) {
        return { key: OPTION_KEYS[position] || "A", content: String(content == null ? "" : content) };
      });
      var letters = String(text || "").toUpperCase().replace(/[^A-H]/g, "");
      var unique = [];
      for (var i = 0; i < letters.length; i += 1) {
        if (unique.indexOf(letters.charAt(i)) < 0) unique.push(letters.charAt(i));
      }
      if (type === "single_choice") unique = unique.slice(0, 1);
      question.answer = { kind: "choice", choice_keys: unique, final: unique.join("") };
    } else {
      var value = String(text || "");
      question.answer = {
        kind: type === "fill_blank" ? "expression" : "text",
        content: value,
        final: value
      };
    }
    return question;
  }

  function onSourceInput(index, value) {
    var item = state.items[index];
    if (!item || item.source === value) return;
    item.source = value;
    item.parsed = null;
    item.dirty = true;
    refreshRow(index);
  }

  function onBoxInput(index, field, pos, value) {
    var item = state.items[index];
    if (!item) return;
    var parsed = item.parsed || parseExamSource(item.source);
    item.parsed = parsed;
    var patch = parsed.patch || {
      stem: parsed.stem, choices: parsed.choices.slice(), answer: parsed.answer, analysis: parsed.analysis
    };
    if (field === "choice") {
      var list = patch.choices.slice();
      list[pos] = value;
      patch.choices = list;
    } else if (field === "stem") {
      patch.stem = value;
    } else if (field === "answer") {
      patch.answer = value;
    } else if (field === "analysis") {
      patch.analysis = value;
    } else {
      return;
    }
    parsed.patch = patch;
    var next = buildExamSource(boxesToQuestion(parsed, patch.stem, patch.choices, patch.answer, patch.analysis));
    if (next === item.source) return;
    item.source = next;
    item.parsed = null;
    item.dirty = true;
    refreshRow(index);
  }

  function parsedOf(item) {
    if (!item.parsed) item.parsed = parseExamSource(item.source);
    return item.parsed;
  }

  function renderQuestionBlock(item, index) {
    var parsed = parsedOf(item);
    var block = el("div", "ed-q-block");
    block.setAttribute("data-index", String(index));
    block.setAttribute("data-type", parsed.type);
    block.setAttribute("data-errors", String(parsed.errors.length));
    item.errorCount = parsed.errors.length;
    // 琥珀灯（军令 #32 · 判据 5.2）：这一题还有未清项就在卡片边缘点灯。
    // 判定口径只有一份，在 ui_amber.js（与底座入库前的点名同一口径），这里只照着画。
    if (amberReasons && metaFor) {
      var amber = amberReasons(parsed, metaFor(item, {}));
      if (amber.length) {
        block.setAttribute("data-amber", "on");
        block.setAttribute("data-amber-reasons", amber.join("；"));
      } else {
        block.removeAttribute("data-amber");
        block.removeAttribute("data-amber-reasons");
      }
    }

    if (parsed.errors.length) {
      block.appendChild(el("p", "ed-opt-img", "源码尚未认全：" + parsed.errors.join("；")));
    }
    var stem = el("p", "ed-q-stem");
    stem.appendChild(el("span", "ed-num", (index + 1) + "."));
    appendRich(stem, parsed.stem || item.source);
    block.appendChild(stem);

    if (parsed.hasChoices) {
      var list = el("ul", "ed-choices");
      parsed.choices.forEach(function (content, position) {
        var key = OPTION_KEYS[position] || String(position + 1);
        var li = el("li");
        var badge = el("span", "ed-choice-key", key + ".");
        if (parsed.answer && parsed.answer.toUpperCase().indexOf(key) >= 0) {
          badge.className += " is-answer";
        }
        li.appendChild(badge);
        var text = el("span", "ed-choice-text");
        appendRich(text, content);
        li.appendChild(text);
        list.appendChild(li);
      });
      block.appendChild(list);
    }
    if (parsed.answer) block.appendChild(el("p", "ed-q-answer", "答案：" + parsed.answer));
    if (parsed.analysis) {
      var analysis = el("div", "ed-q-analysis");
      appendBody(analysis, parsed.analysis);
      block.appendChild(analysis);
    }
    if (parsed.stray) block.appendChild(el("pre", "ed-raw", parsed.stray));
    return block;
  }

  // ---------- 纯图片卷：左栏整卷页图（像 PDF 阅读器一样往下滚） ----------
  /** 一页原卷 → 切图台认的那张「格子」：框选后直接切出新题，不配给任何已有题。 */
  function pageCropItem(page, index) {
    return {
      pageImage: {
        uri: safeAssetUri(page && page.uri) || "",
        page: Number(page && page.page) || index + 1
      },
      batchId: String(state.batchId || ""),
      galleryPage: true,
      question: {}
    };
  }

  function openPageCrop(page, index, cell) {
    if (!safeAssetUri(page && page.uri)) {
      toast("这一页的原卷图取不到，切不了题。", "error");
      return;
    }
    // autoSplit：松开鼠标直接生成新题，老师不必再点一次。
    openCrop(pageCropItem(page, index), index, cell, true);
  }

  function renderPageSlide(page, index) {
    var pageNo = Number(page && page.page) || index + 1;
    var cell = el("div", "ed-img-cell ed-page-cell");
    cell.setAttribute("role", "listitem");
    cell.setAttribute("data-index", String(index));
    cell.setAttribute("data-page-index", String(index));
    var frame = el("div", "ed-img-frame ed-img-page");
    var img = document.createElement("img");
    img.src = safeAssetUri(page && page.uri) || "";
    img.alt = "原卷第 " + pageNo + " 页";
    img.addEventListener("error", function () {
      if (img.parentNode) {
        img.parentNode.replaceChild(el("p", "ed-img-missing", "原卷页读取失败"), img);
      }
    });
    frame.appendChild(img);
    var box = el("div", "ed-img-box");
    box.setAttribute("data-box", "stem");
    frame.appendChild(box);
    // 切图台自己的画布/动作条会冒泡到这里：放行，别一松鼠标就重开一次。
    frame.addEventListener("click", function (event) {
      if (!event.target.closest(".ed-crop-canvas, .ed-crop-actions, .ed-crop-hint")) openPageCrop(page, index, cell);
    });
    cell.appendChild(frame);
    var tools = el("div", "ed-img-tools");
    var cropBtn = el("button", "ed-img-crop-btn", "框选切题");
    cropBtn.type = "button";
    cropBtn.setAttribute("aria-label", "原卷第 " + pageNo + " 页框选切题");
    cropBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      openPageCrop(page, index, cell);
    });
    tools.appendChild(cropBtn);
    cell.appendChild(tools);
    cell.appendChild(el("p", "ed-img-caption", "原卷第 " + pageNo + " 页 · 拖框即生成新题"));
    return cell;
  }

  function emptyColumnNote(text) {
    return el("p", "ed-column-empty", text);
  }

  function renderScanGallery() {
    var pages = Array.isArray(state.pageImages) ? state.pageImages : [];
    pages.forEach(function (page, index) {
      imageBodyEl.appendChild(renderPageSlide(page, index));
    });
    if (!pages.length) {
      imageBodyEl.appendChild(emptyColumnNote(
        "这一批没有可用的原卷页图：请重新拖入文件，或删除这个批次。"));
    }
  }

  function growTextarea(node) {
    node.style.height = "auto";
    node.style.height = Math.max(node.scrollHeight, 60) + "px";
  }

  /**
   * 行高取三栏较高者：三栏共用一条滚动，短栏余下的高度正是那层极淡底色。
   *
   * 顺序是这件事的全部：文本框必须先长到内容高度，再量行高。
   * 反过来（先量后长）的话，源码栏会在量完之后继续长高一截，
   * 三栏之间的虚线当场错位——老师点一下「源码/卡片」就看见。
   * 所以这里长—量两轮：第一轮让框就位，第二轮按最终高度重新对齐。
   *
   * 量高必须用 getBoundingClientRect 的小数高度：offsetHeight 会把 300.4px 截成 300，
   * 而框框视图里的内容高往往带小数，于是每一行的源码格都比另两栏高出一丝，
   * 虚线一行一行往下飘——这正是「点一下卡片就歪」的真相。
   */
  function alignRows() {
    var max = 0;
    for (var pass = 0; pass < 2; pass += 1) {
      Array.prototype.forEach.call(
        sourceBodyEl.querySelectorAll(".ed-src-area, .ed-box-textarea"), growTextarea);
      max = 0;
      // 纯图片卷的左栏是整卷页图，与右边的题行不对应，只对齐源码与渲染两栏。
      var bodies = state.scanBatch
        ? [sourceBodyEl, renderBodyEl]
        : [imageBodyEl, sourceBodyEl, renderBodyEl];
      for (var index = 0; index < state.items.length; index += 1) {
        var cells = bodies.map(function (body) { return body.children[index]; });
        var rowH = 0;
        cells.forEach(function (cell) {
          if (!cell) return;
          var height = cell.getBoundingClientRect().height;
          if (height > rowH) rowH = height;
        });
        cells.forEach(function (cell) {
          if (cell) cell.style.minHeight = rowH + "px";
        });
        if (index === 0) max = rowH;
      }
    }
    return max;
  }

  function markDirty() {
    state.dirty = state.items.some(function (each) { return each.dirty; });
    if (dirtyEl) {
      dirtyEl.setAttribute("data-dirty", state.dirty ? "true" : "false");
      dirtyEl.textContent = state.dirty ? "有未保存改动" : "未改动";
    }
  }

  function captureFocus() {
    var node = document.activeElement;
    if (!node || !node.getAttribute || node.getAttribute("data-field") == null) return null;
    return {
      index: node.getAttribute("data-index"),
      field: node.getAttribute("data-field"),
      pos: node.getAttribute("data-pos"),
      start: node.selectionStart,
      end: node.selectionEnd
    };
  }

  function restoreFocus(info) {
    if (!info || !sourceBodyEl) return;
    var selector = '[data-field="' + info.field + '"][data-index="' + info.index + '"]';
    if (info.pos != null) selector += '[data-pos="' + info.pos + '"]';
    var node = sourceBodyEl.querySelector(selector);
    if (!node) return;
    node.focus();
    if (info.start != null) {
      try { node.setSelectionRange(info.start, info.end); } catch (error) { /* input 不一定支持 */ }
    }
  }

  function updateStatusbar(elapsed, rowH) {
    var first = state.items[state.active] || state.items[0];
    var pageTotal = Array.isArray(state.pageImages) ? state.pageImages.length : 0;
    var progressText = state.scanBatch
      ? (state.items.length
        ? "第 " + (state.active + 1) + " / " + state.items.length + " 题 · 原卷 " + pageTotal + " 页"
        : "待框选 · 原卷 " + pageTotal + " 页")
      : "第 " + (state.active + 1) + " / " + state.items.length + " 题";
    if (progressEl) {
      progressEl.textContent = progressText;
      progressEl.setAttribute("data-active", String(state.active + 1));
      progressEl.setAttribute("data-total", String(state.items.length));
    }
    if (formatEl) {
      formatEl.setAttribute("data-format", state.format);
      formatEl.textContent = state.format === "boxed" ? "卡片" : "源码";
    }
    setFormatButtons(state.format);
    var errorTotal = 0;
    state.items.forEach(function (item) { errorTotal += Number(item.errorCount || 0); });
    if (metricsEl) {
      metricsEl.textContent = progressText + " · 渲染 " + elapsed + "ms";
      metricsEl.setAttribute("data-render-ms", String(elapsed));
      metricsEl.setAttribute("data-katex", String(coreRich.katexCount()));
      metricsEl.setAttribute("data-blocks", String(state.items.length));
      metricsEl.setAttribute("data-errors", String(errorTotal));
      metricsEl.setAttribute("data-question-id", (first && (first.savedId || first.question.id)) || "");
      metricsEl.setAttribute("data-row-h", String(rowH || 0));
      metricsEl.setAttribute("data-pane-w", String(colsEl ? colsEl.clientWidth : 0));
    }
    if (imageNameEl) imageNameEl.textContent = (first && first.dev && first.dev.image_uri) || "未载入";
    markDirty();
    markActiveRow();
    renderPool();
  }

  /**
   * 换了当前题但没重新渲染：只回灌进度与状态位。
   * render-ms 读回上一次实测值——滚一下不许冒充刚渲染过，也不许写成 0。
   */
  function syncActiveBits() {
    var elapsed = Number(metricsEl && metricsEl.getAttribute("data-render-ms"));
    var rowH = Number(metricsEl && metricsEl.getAttribute("data-row-h"));
    updateStatusbar(isNaN(elapsed) ? 0 : elapsed, isNaN(rowH) ? 0 : rowH);
  }

  function renderAll() {
    if (!root || root.hidden) return;
    if (!state.items.length && !state.scanBatch) return;
    var focus = captureFocus();
    var scrolls = [imageBodyEl, sourceBodyEl, renderBodyEl].map(function (node) {
      return node ? node.scrollTop : 0;
    });
    var started = Date.now();
    coreRich.resetKatexCount();
    imageBodyEl.textContent = "";
    sourceBodyEl.textContent = "";
    renderBodyEl.textContent = "";
    imageBodyEl.classList.toggle("is-scan-gallery", Boolean(state.scanBatch));
    if (state.scanBatch) renderScanGallery();
    state.items.forEach(function (item, index) {
      if (!state.scanBatch) imageBodyEl.appendChild(renderImageCell(item, index));
      sourceBodyEl.appendChild(renderSourceCell(item, index));
      renderBodyEl.appendChild(renderQuestionBlock(item, index));
    });
    if (state.scanBatch && !state.items.length) {
      sourceBodyEl.appendChild(emptyColumnNote(
        "在左侧原卷上拖出一个框，松开鼠标就会生成一道待审新题；题干在这里录入。"));
      renderBodyEl.appendChild(emptyColumnNote(
        "框出的新题会按录入顺序排在最上面。"));
    }
    // 切图台先归位再量行高：量的时候它得在格子里，否则量出来的行高偏小，
    // 归位后格子又长高一截，那一截会再勾一次 ResizeObserver，绕成死循环。
    reanchorCrop();
    var rowH = alignRows();
    restoreFocus(focus);
    // 清空重建会把滚动线抹回顶部：批量界面里老师的阅读位置必须原地保住
    scrollRestore = true;
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (node, position) {
      if (node) node.scrollTop = scrolls[position] || 0;
    });
    window.requestAnimationFrame(function () { scrollRestore = false; });
    updateStatusbar(Date.now() - started, rowH);
  }

  /**
   * 只重建改动那一题的渲染行：源码框继续持有焦点与光标，老师边打字边看到排版结果。
   * 整屏重排留给挂载、格式切换与拖宽——那时焦点本来就不在框里。
   */
  function refreshRow(index) {
    if (!root || root.hidden) return;
    var item = state.items[index];
    if (!item) return;
    var holder = renderBodyEl.children[index];
    if (!holder) {
      scheduleRender();
    } else {
      var started = Date.now();
      var block = renderQuestionBlock(item, index);
      renderBodyEl.replaceChild(block, holder);
      var rowH = alignRows();
      updateStatusbar(Date.now() - started, rowH);
    }
    publishSelectionSoon();
    queueWorklistSave();
  }

  function scheduleRender() {
    window.clearTimeout(renderTimer);
    renderTimer = window.setTimeout(renderAll, RENDER_DEBOUNCE_MS);
  }

  /** 把回填后的源码写回中栏：源码改 textarea 的值并把光标停在段末，卡片整格重建（框本就从源码拆出来）。 */
  function writeBackSourceText(item, index, field) {
    var area = state.format === "boxed" ? null
      : sourceBodyEl.querySelector('.ed-src-area[data-index="' + index + '"]');
    if (!area) {
      renderAll();
      return;
    }
    area.value = item.source;
    growTextarea(area);
    var range = fieldRanges(item.source)[field === "solution" ? "solution" : "stem"];
    if (range && document.activeElement === area) {
      // 光标停在改写段末尾：老师接着看结果，不必自己找位置
      area.setSelectionRange(range.end, range.end);
    }
  }

  /**
   * 辅助栏点了【采用】才有这条通知。只替换题干段/解析段的正文，
   * 目标题认不出来、段找不到、内容超长都如实拒绝——绝不用半截改写覆盖老师的源码。
   */
  function applyAiPatch(payload) {
    var raw = payload && payload.raw ? payload.raw : payload;
    var field = raw && (raw.field === "solution" || raw.field === "stem") ? raw.field : "";
    var value = String((raw && raw.value) || "");
    if (!field || !value.trim()) {
      toast("AI 回填缺字段或内容为空，源码没动", "error");
      return false;
    }
    var item = state.items[state.active];
    if (!item) {
      toast("画布当前没有题目可回填", "error");
      return false;
    }
    var wanted = keyFromPatchId(raw.id);
    if (wanted && wanted !== String(item.key).replace(/[^A-Za-z0-9_-]/g, "-")) {
      toast("AI 回填的目标不是当前题，源码没动", "error");
      return false;
    }
    var outcome = replaceField(item.source, field, value);
    if (!outcome.ok) {
      toast(outcome.message, "error");
      return false;
    }
    item.source = outcome.text;
    item.dirty = true;
    markDirty();
    writeBackSourceText(item, state.active, field);
    refreshRow(state.active);
    toast("已采用 AI 改写的" + fieldLabel(field) + "，还没保存", "ok");
    return true;
  }

  // ---------- 批量滚动：滚到哪一题，当前题就跟到哪一题 ----------
  /** 只认正在编辑的框：焦点落在第几题的源码/框里，那一题就是当前题，滚动不许来抢。 */
  function editingRowIndex() {
    var node = document.activeElement;
    if (!node || !node.getAttribute) return -1;
    if (node.tagName !== "TEXTAREA" && node.tagName !== "INPUT") return -1;
    var raw = node.getAttribute("data-index");
    if (raw == null) return -1;
    var index = Number(raw);
    return isNaN(index) || index < 0 ? -1 : index;
  }

  /** 当前题 = 视口里露出最多的那一行：只按「顶边越过滚动线」会在滚到底时漏掉最后一题。 */
  function activeFromScroll(top) {
    var body = renderBodyEl || sourceBodyEl || imageBodyEl;
    if (!body) return state.active;
    var bottom = top + Math.max(body.clientHeight || 0, 1);
    var best = state.active;
    var bestArea = -1;
    for (var position = 0; position < body.children.length; position += 1) {
      var cell = body.children[position];
      var visible = Math.min(cell.offsetTop + cell.offsetHeight, bottom) - Math.max(cell.offsetTop, top);
      if (visible > bestArea) {
        bestArea = visible;
        best = position;
      }
    }
    return clampValue(best, 0, Math.max(state.items.length - 1, 0));
  }

  /** 三栏同时高亮当前题：状态不只靠颜色（AGENTS §6），顶部进度条与左栏按钮文案一起说明。 */
  function markActiveRow() {
    // 左栏在纯图片卷里是整卷页图，与题行不是一一对应：只标源码与渲染两栏。
    var bodies = state.scanBatch
      ? [sourceBodyEl, renderBodyEl]
      : [imageBodyEl, sourceBodyEl, renderBodyEl];
    bodies.forEach(function (body) {
      if (!body) return;
      Array.prototype.forEach.call(body.children, function (cell, index) {
        if (!cell.classList) return;
        cell.classList.toggle("is-active", index === state.active);
      });
    });
    Array.prototype.forEach.call(imageBodyEl ? imageBodyEl.querySelectorAll(".ed-img-jump") : [],
      function (node) {
        var index = Number(node.getAttribute("data-index"));
        var on = index === state.active;
        node.setAttribute("aria-current", on ? "true" : "false");
      });
  }

  function jumpTo(index) {
    var target = clampValue(Number(index) || 0, 0, Math.max(state.items.length - 1, 0));
    state.active = target;
    [imageBodyEl, sourceBodyEl, renderBodyEl].forEach(function (body) {
      // 纯图片卷的左栏不跟着跳题滚：老师正在浏览的那一页不能被抢走。
      if (state.scanBatch && body === imageBodyEl) return;
      var cell = body && body.children[target];
      if (body && cell) body.scrollTop = Math.max(cell.offsetTop - 12, 0);
    });
    syncActiveBits();
    publishSelectionSoon();
    queueWorklistSave();
  }

  function followActive(from) {
    if (!state.items.length || editingRowIndex() >= 0) return;
    var next = activeFromScroll(from ? from.scrollTop : 0);
    if (next === state.active) return;
    state.active = next;
    syncActiveBits();
    publishSelectionSoon();
    queueWorklistSave();
  }

  function syncScroll(from) {
    if (scrollRestore) return;
    if (scrollLock) return;
    // 纯图片卷：左栏是独立的整卷阅读器，滚它不影响右边的源码/渲染。
    if (state.scanBatch && from === imageBodyEl) return;
    scrollLock = true;
    var bodies = state.scanBatch
      ? [sourceBodyEl, renderBodyEl]
      : [imageBodyEl, sourceBodyEl, renderBodyEl];
    bodies.forEach(function (node) {
      if (node && node !== from) node.scrollTop = from.scrollTop;
    });
    followActive(from);
    window.requestAnimationFrame(function () { scrollLock = false; });
  }

    return {
      activeFromScroll: activeFromScroll,
      alignRows: alignRows,
      applyAiPatch: applyAiPatch,
      boxFieldCell: boxFieldCell,
      boxedBlockReason: boxedBlockReason,
      boxesToQuestion: boxesToQuestion,
      captureFocus: captureFocus,
      editingRowIndex: editingRowIndex,
      followActive: followActive,
      growTextarea: growTextarea,
      itemImage: itemImage,
      jumpTo: jumpTo,
      markActiveRow: markActiveRow,
      markDirty: markDirty,
      onBoxInput: onBoxInput,
      onSourceInput: onSourceInput,
      parsedOf: parsedOf,
      refreshRow: refreshRow,
      renderAll: renderAll,
      renderBoxedCell: renderBoxedCell,
      renderImageCell: renderImageCell,
      renderQuestionBlock: renderQuestionBlock,
      renderSourceCell: renderSourceCell,
      renderTimer: renderTimer,
      restoreFocus: restoreFocus,
      scheduleRender: scheduleRender,
      scrollLock: scrollLock,
      scrollRestore: scrollRestore,
      syncActiveBits: syncActiveBits,
      syncScroll: syncScroll,
      updateStatusbar: updateStatusbar,
      writeBackSourceText: writeBackSourceText,
    };
  }

  global.JzoEditorColumns = { create: create };
})(window);
