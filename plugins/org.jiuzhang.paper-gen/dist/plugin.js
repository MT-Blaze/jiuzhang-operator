/**
 * 组卷排版插件（org.jiuzhang.paper-gen）。
 *
 * 数据来自宿主转发的 basket.list（含题目全文）；本插件不联网、不读库。
 * 排版全程在前端完成：先按题块测量，再按 A4 安全区贪心分页；单题超过
 * 一整页时拆到「题干段 / 选项 / 答案 / 解析段」级别继续排，避免一题
 * 把整页顶破。渲染耗时写进 data-render-ms，供真机探针取证。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.paper-gen";
  var PAGE_W = 794;
  var PAGE_H = 1123;
  // 排版留白：给 KaTeX 分式的上下墨迹留出余量，避免末行墨迹被纸边裁掉
  var PAGE_FILL_H = 885;
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
  var pages = [];
  var page = null;
  var selectedId = null;
  var mathCache = new Map();
  // 图片天然尺寸缓存：先量好再排，避免懒加载后图片撑高、把整页顶出安全区
  var imageSizeCache = new Map();

  var state = {
    items: [],
    missing: 0,
    showAnswers: false,
    density: "normal",
    title: "九章算子 · 数学练习卷",
    renderMs: 0
  };
  var reflowSeq = 0;
  // 重排期间预览宽度不会变，缩放只算一次；每开一页都读 clientWidth 会强制整页回流。
  var activeScale = 1;
  var settleRounds = 0;
  var settleMoves = 0;

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

  // ---------- 安全富文本 ----------
  function mathNode(tex, display) {
    var span = document.createElement("span");
    span.className = display ? "pg-math-block" : "pg-math";
    var key = (display ? "D:" : "I:") + tex;
    var html = mathCache.get(key);
    if (html === undefined) {
      html = "";
      if (window.katex && typeof window.katex.renderToString === "function") {
        try {
          html = window.katex.renderToString(tex, {
            displayMode: display,
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

  function imageNode(uri, alt) {
    if (typeof uri !== "string" || uri.indexOf("/static/uploads/") !== 0) return null;
    var size = imageSizeCache.get(uri);
    if (size && (!size.w || !size.h)) return null;   // 已确认坏图：不占位
    var img = document.createElement("img");
    img.className = "pg-image";
    img.src = uri;
    img.alt = alt || "配图";
    img.loading = "eager";
    img.decoding = "async";
    if (size) {
      // 与 CSS 的 max-width:100% / max-height:180px 同口径，量出显示尺寸写进属性，
      // 浏览器在图片解码前就为它留好位置，分页测量与实际渲染严格一致。
      var scale = Math.min(1, 682 / size.w, 180 / size.h);
      img.width = Math.max(1, Math.round(size.w * scale));
      img.height = Math.max(1, Math.round(size.h * scale));
    }
    return img;
  }

  /** 预载题篮里所有配图，拿到尺寸后一次性重排；坏图记 0 尺寸并从纸面剔除。 */
  function primeImages(items) {
    var jobs = [];
    (items || []).forEach(function (question) {
      (question.images || []).forEach(function (image) {
        var uri = image && image.uri;
        if (typeof uri !== "string" || uri.indexOf("/static/uploads/") !== 0) return;
        if (imageSizeCache.has(uri)) return;
        imageSizeCache.set(uri, null);
        jobs.push(new Promise(function (resolve) {
          var probe = new Image();
          probe.onload = function () {
            imageSizeCache.set(uri, { w: probe.naturalWidth, h: probe.naturalHeight });
            resolve();
          };
          probe.onerror = function () {
            imageSizeCache.set(uri, { w: 0, h: 0 });
            resolve();
          };
          probe.src = uri;
        }));
      });
    });
    return Promise.all(jobs);
  }

  function blankNode() {
    var span = document.createElement("span");
    span.className = "pg-blank";
    span.setAttribute("aria-label", "填空");
    return span;
  }

  /**
   * 行内富文本：图片、行内/独立公式、粗体、填空线。
   * 真题原文混用 ``$...$``、``\(...\)``、``\[...\]`` 三种公式定界符，
   * 还夹着 ``\\textbf{}``、``\\fillin`` 这类文本宏；不处理就会把反斜杠
   * 原样印到纸上（第三战役目检抓到的真实缺陷）。
   */
  function appendInline(target, text) {
    var pattern = /(!\[[^\]]*\]\(\/static\/uploads\/[^)\s]+\)|\\\[[\s\S]*?\\\]|\\\([^\n]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]*?\$|\*\*[^*]+\*\*|\\textbf\{[^{}]*\}|\\textit\{[^{}]*\}|\\fillin)/g;
    var last = 0;
    var match;
    while ((match = pattern.exec(text)) !== null) {
      if (match.index > last) {
        target.appendChild(document.createTextNode(text.slice(last, match.index)));
      }
      var token = match[0];
      if (token.slice(0, 2) === "![") {
        var parts = token.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
        var img = parts ? imageNode(parts[2], parts[1]) : null;
        if (img) target.appendChild(img);
      } else if (token.slice(0, 2) === "\\[") {
        target.appendChild(mathNode(token.slice(2, -2), true));
      } else if (token.slice(0, 2) === "\\(") {
        target.appendChild(mathNode(token.slice(2, -2), false));
      } else if (token.slice(0, 1) === "$") {
        target.appendChild(mathNode(token.slice(0, 2) === "$$" ? token.slice(2, -2) : token.slice(1, -1), token.slice(0, 2) === "$$"));
      } else if (token.slice(0, 8) === "\\textbf{") {
        var strong = document.createElement("strong");
        appendInline(strong, token.slice(8, -1));
        target.appendChild(strong);
      } else if (token.slice(0, 8) === "\\textit{") {
        var em = document.createElement("em");
        appendInline(em, token.slice(8, -1));
        target.appendChild(em);
      } else if (token === "\\fillin") {
        target.appendChild(blankNode());
      } else {
        var bold = document.createElement("strong");
        bold.textContent = token.slice(2, -2);
        target.appendChild(bold);
      }
      last = pattern.lastIndex;
    }
    if (last < text.length) target.appendChild(document.createTextNode(text.slice(last)));
  }

  /** LaTeX 表格环境转真表格：真题里的对应关系表脱离数学定界符后只剩源码。 */
  function tableNode(rows) {
    var table = el("table", "pg-table");
    rows.forEach(function (cells, rowIndex) {
      var tr = document.createElement("tr");
      cells.forEach(function (cellText) {
        var cell = document.createElement(rowIndex === 0 ? "th" : "td");
        appendInline(cell, cellText);
        tr.appendChild(cell);
      });
      table.appendChild(tr);
    });
    return table;
  }

  function parseTabular(body) {
    var rows = [];
    body.split(/\\\\/).forEach(function (raw) {
      var line = raw.replace(/\\hline/g, "").trim();
      if (!line) return;
      var cells = line.split("&").map(function (cell) { return cell.trim(); });
      if (cells.length > 1) rows.push(cells);
    });
    return rows;
  }

  /** 把一段 Markdown+LaTeX 按换行拆成段落元素；空行不产生空 <p>。 */
  function richLines(source) {
    var text = String(source == null ? "" : source).replace(/\r\n?/g, "\n");
    // 先把跨行的 tabular 抽出来，换成占位符，再按行处理其余内容。
    var tables = [];
    text = text.replace(/\\begin\{tabular\}\{[^}]*\}([\s\S]*?)\\end\{tabular\}/g, function (_all, body) {
      tables.push(parseTabular(body));
      return "\n\u0000TABLE" + (tables.length - 1) + "\u0000\n";
    });

    var nodes = [];
    text.split("\n").forEach(function (line) {
      var marker = line.trim().match(/^\u0000TABLE(\d+)\u0000$/);
      if (marker) {
        var rows = tables[Number(marker[1])];
        if (rows && rows.length) nodes.push(tableNode(rows));
        return;
      }
      var content = line
        .replace(/\\begin\{choices\}/g, "")
        .replace(/\\end\{choices\}/g, "")
        .replace(/^\s*\\item\s*/, "· ")
        .trim();
      if (!content) return;
      var p = document.createElement("p");
      appendInline(p, content);
      nodes.push(p);
    });
    if (!nodes.length) {
      var blank = document.createElement("p");
      blank.textContent = "（空）";
      nodes.push(blank);
    }
    return nodes;
  }

  function appendRich(target, source) {
    richLines(source).forEach(function (node) { target.appendChild(node); });
  }

  // ---------- 题目构建 ----------
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function sourceLabel(question) {
    var source = question.source || {};
    var bits = [];
    if (source.paper_title) bits.push(source.paper_title);
    if (source.question_no) bits.push("原卷 " + source.question_no + " 题");
    return bits.join(" · ");
  }

  function optionImages(question, option) {
    var images = question.images || [];
    return (option.image_ids || []).map(function (id) {
      return images.filter(function (item) { return item.id === id; })[0];
    }).filter(Boolean);
  }

  function answerText(question) {
    var answer = question.answer;
    if (!answer) return "";
    if (answer.kind === "choice") return (answer.choice_keys || []).join("、");
    return answer.final || answer.content || "";
  }

  function buildQuestionHead(question, index) {
    var head = el("div", "pg-q-head");
    head.appendChild(el("span", "pg-q-no", String(index + 1) + "."));
    var source = sourceLabel(question);
    if (source) head.appendChild(el("span", "pg-q-source", source));
    return head;
  }

  /**
   * 真题解析常以「【答案】…【解析】…」开头，而答案已由结构化字段单独渲染。
   * 若解析里带「【解析】」标记，就从标记后开始印，避免同一页出现两份答案。
   */
  function solutionBody(source) {
    var text = String(source == null ? "" : source);
    var marker = text.search(/\\textbf\{【解析】\}|【解析】/);
    if (marker < 0) return text;
    return text.slice(marker)
      .replace(/^\\textbf\{【解析】\}/, "")
      .replace(/^【解析】/, "")
      .trim();
  }

  function buildQuestionBlock(question, index) {
    var block = el("div", "pg-q");
    block.setAttribute("data-qid", question.id);
    block.appendChild(buildQuestionHead(question, index));

    richLines(question.stem).forEach(function (line) {
      if (line.tagName === "P") line.className = "pg-line";
      block.appendChild(line);
    });

    (question.options || []).forEach(function (option) {
      var row = el("div", "pg-option");
      row.appendChild(el("span", "pg-key", option.key + "."));
      var body = el("span", "pg-opt-body");
      appendRich(body, option.content);
      optionImages(question, option).forEach(function (image) {
        var img = imageNode(image.uri, image.alt);
        if (img) body.appendChild(img);
      });
      row.appendChild(body);
      block.appendChild(row);
    });

    if (state.showAnswers) {
      var answer = answerText(question);
      if (answer) block.appendChild(el("div", "pg-answer", "答案：" + answer));
      if (question.solution) {
        var solution = solutionBody(question.solution);
        if (solution) richLines(solution).forEach(function (line, lineIndex) {
          if (line.tagName === "P") line.className = "pg-solution";
          if (lineIndex === 0 && line.tagName === "P") {
            line.insertBefore(el("span", "pg-sol-title", "解析："), line.firstChild);
          }
          block.appendChild(line);
        });
      }
    }

    block.appendChild(el("div", "pg-q-gap"));
    return block;
  }

  /**
   * 单题拆件：题内每个块级子节点本来就是排版单元，直接搬运即可。
   * 题号头与第一行绑成一个单元，避免题号孤零零落在页脚；
   * 末尾的间距块不参与分页，跟随最后一件落在同一页。
   */
  function splitBlock(entry, questionId) {
    var pieces = entry.measure.children.slice();
    var gap = null;
    if (pieces.length && pieces[pieces.length - 1].node.classList.contains("pg-q-gap")) {
      gap = pieces.pop();
    }
    if (!pieces.length) return { units: [], gap: gap ? gap.node : null };

    var head = pieces.shift();
    var firstLine = pieces.shift();
    var first = el("div", "pg-q pg-unit");
    first.setAttribute("data-qid", questionId);
    if (head) first.appendChild(head.node);
    if (firstLine) first.appendChild(firstLine.node);

    var firstHeight;
    if (pieces.length) {
      firstHeight = pieces[0].top - head.top;
    } else {
      firstHeight = entry.height - head.top;
    }
    var units = [{ node: first, height: firstHeight }];

    pieces.forEach(function (piece) {
      piece.node.setAttribute("data-qid", questionId);
      units.push({ node: piece.node, height: piece.height });
    });
    if (units.length > 1) {
      units[1].node.setAttribute("data-cont", "1");
      units[1].node.insertBefore(el("p", "pg-cont", "（接上题）"), units[1].node.firstChild);
    }
    return { units: units, gap: gap ? gap.node : null };
  }

  // ---------- 分页 ----------
  function computeScale() {
    if (!previewEl) return 1;
    var width = previewEl.clientWidth - 32;
    if (width <= 0) return 1;
    return Math.max(0.45, Math.min(1, Math.round((width / PAGE_W) * 1000) / 1000));
  }

  function applyScale() {
    var scale = computeScale();
    activeScale = scale;
    document.documentElement.style.setProperty("--pg-scale", String(scale));
    pages.forEach(function (record) {
      record.wrap.style.width = (PAGE_W * scale) + "px";
      record.wrap.style.height = (PAGE_H * scale) + "px";
    });
  }

  function newPage() {
    var wrap = el("div", "pg-page-wrap");
    var section = el("section", "pg-page");
    section.setAttribute("data-page", String(pages.length + 1));

    var head = el("header", "pg-page-head");
    var title = el("span", "pg-doc-title", state.title);
    head.appendChild(title);
    head.appendChild(el("span", "pg-doc-info", "姓名 ________ 得分 ________"));

    var body = el("div", "pg-page-body");
    var foot = el("footer", "pg-page-foot", "第 " + (pages.length + 1) + " 页");

    section.appendChild(head);
    section.appendChild(body);
    section.appendChild(foot);
    wrap.appendChild(section);
    pagesEl.appendChild(wrap);

    var record = { wrap: wrap, page: section, body: body, foot: foot, title: title, used: 0 };
    wrap.style.width = (PAGE_W * activeScale) + "px";
    wrap.style.height = (PAGE_H * activeScale) + "px";
    pages.push(record);
    return record;
  }

  /**
   * 批量测量：50 个题块一次性进测量列，只强制一次布局，再连续读取。
   * 逐题「插入-读高度-移除」会让浏览器对每个题块单独回流一次，
   * 带答案的 50 道长题能因此多花一秒以上。
   */
  function measureBlocks(entries) {
    measureEl.textContent = "";
    var fragment = document.createDocumentFragment();
    entries.forEach(function (entry) { fragment.appendChild(entry.block); });
    measureEl.appendChild(fragment);
    // 先读一次容器位置，把 50 个题块的布局一次性算完；后续读取不再触发回流。
    measureEl.getBoundingClientRect();

    entries.forEach(function (entry) {
      var block = entry.block;
      var blockTop = block.offsetTop;
      var height = block.offsetHeight;
      var children = Array.prototype.slice.call(block.children).map(function (node) {
        return { node: node, top: node.offsetTop - blockTop, height: node.offsetHeight, end: 0 };
      });
      children.forEach(function (item, index) {
        item.end = index + 1 < children.length ? children[index + 1].top : height;
        item.height = Math.max(0, item.end - item.top);
      });
      entry.measure = { height: height, children: children };
      entry.height = height;
    });

    measureEl.textContent = "";
  }

  /** 按量好的高度落页；放不下就换纸。 */
  function place(record, node, height) {
    if (record.body.children.length > 0 && record.used + height > PAGE_FILL_H) {
      record = newPage();
    }
    record.body.appendChild(node);
    record.used += height;
    node.setAttribute("data-height", String(Math.round(height)));
    if (height > PAGE_FILL_H) node.setAttribute("data-overflow", "true");
    return record;
  }

  /**
   * 收尾复核：量高能算准布局盒，但算不进 KaTeX 分式的墨迹外溢。
   * 整卷排完后统一读一次 scrollHeight，把溢出的尾件顺延到下一页；
   * 只有真正越界的页才动节点，正常页零成本。
   */
  function settlePages() {
    // 先整卷读一遍溢出（只读不写，一次布局），再统一搬件；避免读一次搬一次
    // 触发几十次整卷回流。最多补几轮，轮数交给真实布局收敛。
    settleRounds = 0;
    settleMoves = 0;
    for (var round = 0; round < 6; round += 1) {
      var overflowing = [];
      for (var i = 0; i < pages.length; i += 1) {
        var body = pages[i].body;
        if (body.scrollHeight > body.clientHeight + 1 && body.children.length > 1) {
          overflowing.push(i);
        }
      }
      if (!overflowing.length) break;
      settleRounds += 1;
      settleMoves += overflowing.length;
      overflowing.forEach(function (index) {
        var record = pages[index];
        var last = record.body.lastElementChild;
        var next = pages[index + 1];
        if (!next) next = newPage();
        next.body.insertBefore(last, next.body.firstChild);
      });
    }
    // 单件仍超页：打标交给底栏，不再无休止搬运
    pages.forEach(function (record) {
      if (record.body.scrollHeight > record.body.clientHeight + 1 && record.body.firstElementChild) {
        record.body.firstElementChild.setAttribute("data-overflow", "true");
      }
    });
  }

  function showPreviewEmpty() {
    pagesEl.textContent = "";
    pages = [];
    page = null;
    var box = el("div", "pg-preview-empty");
    box.appendChild(el("strong", null, "题篮还是空的"));
    box.appendChild(el("p", null, "去「真题题库」挑几道题入篮，本页会自动生成 A4 练习卷。"));
    pagesEl.appendChild(box);
    metricsEl.textContent = "0 题 · 0 页 · 0 ms";
    metricsEl.setAttribute("data-render-ms", "0");
    metricsEl.setAttribute("data-pages", "0");
    metricsEl.setAttribute("data-questions", "0");
    reflowSeq += 1;
    metricsEl.setAttribute("data-reflow", String(reflowSeq));
  }

  function reflow() {
    if (!stageMode || !pagesEl) return;
    var started = performance.now();

    pagesEl.textContent = "";
    pages = [];
    page = null;
    pagesEl.setAttribute("data-density", state.density);

    if (!state.items.length) {
      showPreviewEmpty();
      state.renderMs = Math.round((performance.now() - started) * 10) / 10;
      renderSide();
      return;
    }

    activeScale = computeScale();
    document.documentElement.style.setProperty("--pg-scale", String(activeScale));
    measureEl.setAttribute("data-density", state.density);

    // 第一轮：整题构建。构建只写 DOM，不读布局。
    var buildStarted = performance.now();
    var entries = state.items.map(function (question, index) {
      return { question: question, block: buildQuestionBlock(question, index) };
    });
    var buildMs = performance.now() - buildStarted;

    // 第二轮：整卷一次测量（含子件位置），避免逐题强制回流。
    var measureStart = performance.now();
    measureBlocks(entries);
    var measuredAt = performance.now();

    // 第三轮：按原题序落页，只写不读；超页题直接搬子件。
    page = newPage();
    entries.forEach(function (entry) {
      if (entry.height <= PAGE_FILL_H) {
        page = place(page, entry.block, entry.height);
        return;
      }
      if (page.body.children.length > 0) page = newPage();
      var split = splitBlock(entry, entry.question.id);
      split.units.forEach(function (unit, index) {
        var last = index === split.units.length - 1;
        var gapHeight = last && split.gap ? 14 : 0;
        page = place(page, unit.node, unit.height + gapHeight);
        if (last && split.gap) page.body.appendChild(split.gap);
      });
    });
    var placedAt = performance.now();
    settlePages();
    var settledAt = performance.now();

    pages.forEach(function (record, index) {
      record.foot.textContent = "第 " + (index + 1) + " 页 / 共 " + pages.length + " 页";
      record.page.setAttribute("data-page", String(index + 1));
    });

    var overflow = pagesEl.querySelectorAll("[data-overflow='true']").length;
    state.renderMs = Math.round((performance.now() - started) * 10) / 10;
    metricsEl.textContent = state.items.length + " 题 · " + pages.length + " 页 · " + state.renderMs + " ms" +
      (overflow ? " · " + overflow + " 处超高" : "");
    metricsEl.setAttribute("data-render-ms", String(state.renderMs));
    metricsEl.setAttribute("data-pages", String(pages.length));
    metricsEl.setAttribute("data-questions", String(state.items.length));
    metricsEl.setAttribute("data-overflow", String(overflow));
    metricsEl.setAttribute("data-density", state.density);
    reflowSeq += 1;
    metricsEl.setAttribute("data-reflow", String(reflowSeq));
    metricsEl.setAttribute("data-t-build", String(Math.round(buildMs * 10) / 10));
    metricsEl.setAttribute("data-t-measure-blocks", String(Math.round((measuredAt - measureStart) * 10) / 10));
    metricsEl.setAttribute("data-t-place", String(Math.round((placedAt - measuredAt) * 10) / 10));
    metricsEl.setAttribute("data-t-settle", String(Math.round((settledAt - placedAt) * 10) / 10));
    metricsEl.setAttribute("data-settle", settleRounds + "轮/" + settleMoves + "件");
    metricsEl.setAttribute("data-t-layout", String(Math.round((state.renderMs - buildMs) * 10) / 10));
    applyScale();
    dock("组卷完成：" + state.items.length + " 题 · " + pages.length + " 页 · " + state.renderMs + " ms" +
      (overflow ? "（" + overflow + " 处超高）" : ""));
  }

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

  function jumpTo(questionId) {
    selectedId = questionId;
    var node = pagesEl.querySelector('[data-qid="' + questionId + '"]');
    if (node) {
      var wrap = node.closest(".pg-page-wrap");
      if (wrap) wrap.scrollIntoView({ block: "start", behavior: "smooth" });
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
        state.missing = Number((result && result.missing) || 0);
        if (selectedId && !state.items.some(function (item) { return item.id === selectedId; })) {
          selectedId = null;
        }
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

  // ---------- 工具条 ----------
  if (titleInput) {
    titleInput.addEventListener("input", function () {
      window.clearTimeout(titleTimer);
      titleTimer = window.setTimeout(function () {
        state.title = titleInput.value.trim().slice(0, 48) || "数学练习卷";
        pages.forEach(function (record) { record.title.textContent = state.title; });
      }, 200);
    });
  }

  var reflowBtn = document.getElementById("pgReflow");
  if (reflowBtn) reflowBtn.addEventListener("click", function () { loadBasket(); });

  var refreshBtn = document.getElementById("pgRefresh");
  if (refreshBtn) refreshBtn.addEventListener("click", function () { loadBasket(); });

  var clearBtn = document.getElementById("pgClear");
  if (clearBtn) clearBtn.addEventListener("click", clearBasket);

  var printBtn = document.getElementById("pgPrint");
  if (printBtn) {
    printBtn.addEventListener("click", function () {
      try {
        window.print();
      } catch (error) {
        toast("沙箱内无法直接打印，请用浏览器菜单打印");
      }
    });
  }

  if (window.ResizeObserver && previewEl) {
    window.ResizeObserver && new ResizeObserver(function () { applyScale(); }).observe(previewEl);
  } else {
    window.addEventListener("resize", applyScale);
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
