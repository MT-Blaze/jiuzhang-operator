/**
 * 讲义排版插件（org.jiuzhang.handout）。
 *
 * 左栏是 Markdown 原稿，右栏是 A4 纸面；输入停顿 160ms 后整篇重排。
 * 解析器只认讲义常用的那部分 Markdown（标题、列表、表格、引用、代码块），
 * 公式交给随宿主本地化的 KaTeX。全程不联网、不读题库、不碰宿主凭据。
 *
 * 排版仍是「先量后排」：所有块进测量列一次布局，按安全高度贪心落页，
 * 最后整卷读一次 scrollHeight，把被公式墨迹顶出纸边的尾块顺延。
 */
(function () {
  "use strict";

  var PROTOCOL = "jzo-plugin/1";
  var PLUGIN_ID = "org.jiuzhang.handout";
  var PAGE_W = 794;
  var PAGE_H = 1123;
  // 排版留白：与组卷插件同口径，给公式上下墨迹留余量
  var PAGE_FILL_H = 885;
  var DEBOUNCE_MS = 160;

  var root = document.getElementById("root");
  var pagesEl = document.getElementById("hpPages");
  var previewEl = document.getElementById("hpPreview");
  var measureEl = document.getElementById("hpMeasure");
  var inputEl = document.getElementById("hpInput");
  var statsEl = document.getElementById("hpStats");
  var metricsEl = document.getElementById("hpMetrics");
  var toastEl = document.getElementById("hpToast");

  var pages = [];
  var activeScale = 1;
  var reflowSeq = 0;
  var renderToken = 0;
  var debounceTimer = 0;
  var toastTimer = 0;
  var mathCache = new Map();
  // 配图先量自然尺寸再排：否则图片解码后撑高，会把整页顶出纸边
  var imageCache = new Map();

  var state = {
    markdown: "",
    size: "normal",
    renderMs: 0
  };

  var SAMPLE = [
    "# 二次函数与图象",
    "",
    "## 一、核心概念",
    "",
    "形如 $y = ax^{2} + bx + c\\ (a \\neq 0)$ 的函数叫做二次函数。它的图象是一条抛物线，对称轴为 $x = -\\dfrac{b}{2a}$，顶点坐标为 $\\left(-\\dfrac{b}{2a},\\ \\dfrac{4ac-b^{2}}{4a}\\right)$。",
    "",
    "> 记忆要点：开口方向看 $a$，对称轴看 $a$ 与 $b$ 的符号，与 $y$ 轴交点看 $c$。",
    "",
    "## 二、三种常见形式",
    "",
    "1. 一般式：$y = ax^{2} + bx + c$，适合已知三点求解析式。",
    "2. 顶点式：$y = a(x-h)^{2} + k$，顶点为 $(h, k)$，适合配方与最值问题。",
    "3. 交点式：$y = a(x-x_1)(x-x_2)$，适合已知与 $x$ 轴的两个交点。",
    "",
    "## 三、图象与性质对照",
    "",
    "| 判别式 | 与 $x$ 轴交点 | 函数值符号 |",
    "| --- | --- | --- |",
    "| $\\Delta > 0$ | 两个不同交点 | 有两段同号区间 |",
    "| $\\Delta = 0$ | 一个交点（相切） | 除顶点外恒同号 |",
    "| $\\Delta < 0$ | 无交点 | 恒正或恒负 |",
    "",
    "## 四、典型例题",
    "",
    "**例 1** 已知 $f(x) = x^{2} - 4x + 3$，求它的顶点与最小值。",
    "",
    "配方得",
    "",
    "$$f(x) = (x-2)^{2} - 1$$",
    "",
    "所以顶点为 $(2, -1)$，当 $x = 2$ 时取得最小值 $-1$。",
    "",
    "**例 2** 若方程 $x^{2} + 2x + m = 0$ 有两个不相等的实根，求 $m$ 的取值范围。",
    "",
    "由 $\\Delta = 4 - 4m > 0$，解得 $m < 1$。",
    "",
    "## 五、课堂练习",
    "",
    "- 练习 1：把 $y = 2x^{2} - 8x + 5$ 化为顶点式。",
    "- 练习 2：判断 $y = -x^{2} + 4x - 5$ 的开口方向与最值。",
    "- 练习 3：已知抛物线经过 $(0,3)$、$(1,0)$、$(3,0)$，求解析式。",
    "",
    "```text",
    "提示：先定开口，再定对称轴，最后代入已知点。",
    "```",
    "",
    "> 课后要求：完成练习 1—3，并把配方过程完整写在作业本上。"
  ].join("\n");

  // ---------- 宿主通信 ----------
  function markStale() {
    if (!root) return;
    var banner = root.querySelector(".hd-stale");
    if (!banner) {
      banner = document.createElement("p");
      banner.className = "hd-stale";
      banner.setAttribute("role", "status");
      root.insertBefore(banner, root.firstChild);
    }
    banner.textContent = "真题库里的题目刚被录题工作台改过：本讲义仍是发送过来的那一份，"
      + "请从组卷端重新发送到讲义，才看得到新内容。";
    dock("讲义内容已过期，等待重新发送。");
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
    var span = document.createElement("span");
    span.className = display ? "hp-math-block" : "hp-math";
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
    else span.textContent = display ? "$$" + tex + "$$" : "$" + tex + "$";
    return span;
  }

  function imageNode(uri, alt) {
    // 只认宿主托管的本地图片；远程 URL、data:、file: 一律不加载
    if (typeof uri !== "string" || uri.indexOf("/static/uploads/") !== 0) return null;
    var size = imageCache.get(uri);
    if (size && (!size.w || !size.h)) return null;   // 已确认坏图：不占位
    var img = document.createElement("img");
    img.className = "hp-image";
    img.src = uri;
    img.alt = alt || "配图";
    img.loading = "eager";
    img.decoding = "async";
    if (size) {
      var scale = Math.min(1, 682 / size.w, 260 / size.h);
      img.width = Math.max(1, Math.round(size.w * scale));
      img.height = Math.max(1, Math.round(size.h * scale));
    }
    return img;
  }

  /** 预载讲义里的本地配图，拿到尺寸后重建并重排。 */
  function primeImages(blocks) {
    var jobs = [];
    blocks.forEach(function (block) {
      var images = block.querySelectorAll ? block.querySelectorAll("img") : [];
      Array.prototype.forEach.call(images, function (img) {
        var uri = img.getAttribute("src");
        if (!uri || imageCache.has(uri)) return;
        imageCache.set(uri, { w: 0, h: 0 });
        jobs.push(new Promise(function (resolve) {
          var probe = new Image();
          probe.onload = function () {
            imageCache.set(uri, { w: probe.naturalWidth, h: probe.naturalHeight });
            resolve();
          };
          probe.onerror = function () { resolve(); };
          probe.src = uri;
        }));
      });
    });
    return Promise.all(jobs);
  }

  function appendInline(target, text) {
    var pattern = /(!\[[^\]]*\]\(\/static\/uploads\/[^)\s]+\)|\\\[[\s\S]*?\\\]|\\\([^\n]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]*?\$|\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`\n]+`|\\textbf\{[^{}]*\})/g;
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
        target.appendChild(mathNode(
          token.slice(0, 2) === "$$" ? token.slice(2, -2) : token.slice(1, -1),
          token.slice(0, 2) === "$$"
        ));
      } else if (token.slice(0, 2) === "**") {
        var strong = document.createElement("strong");
        appendInline(strong, token.slice(2, -2));
        target.appendChild(strong);
      } else if (token.slice(0, 8) === "\\textbf{") {
        var bold = document.createElement("strong");
        appendInline(bold, token.slice(8, -1));
        target.appendChild(bold);
      } else if (token.slice(0, 1) === "*") {
        var em = document.createElement("em");
        appendInline(em, token.slice(1, -1));
        target.appendChild(em);
      } else {
        var code = document.createElement("code");
        code.textContent = token.slice(1, -1);
        target.appendChild(code);
      }
      last = pattern.lastIndex;
    }
    if (last < text.length) target.appendChild(document.createTextNode(text.slice(last)));
  }

  /** 中文软换行直接相连，英文单词之间保留一个空格。 */
  function joinLines(lines) {
    var out = "";
    lines.forEach(function (line, index) {
      if (index === 0) { out = line; return; }
      var previous = out.slice(-1);
      var current = line.slice(0, 1);
      out += /[A-Za-z0-9]/.test(previous) && /[A-Za-z0-9]/.test(current) ? " " + line : line;
    });
    return out;
  }

  function isTableStart(lines, index) {
    var line = lines[index] || "";
    var next = lines[index + 1] || "";
    return line.indexOf("|") >= 0 && /^\s*\|?\s*:?-{3,}/.test(next);
  }

  function startsBlock(line) {
    return /^\s*(#{1,4})\s+/.test(line)
      || /^\s*```/.test(line)
      || /^\s*\$\$/.test(line)
      || /^\s*>\s?/.test(line)
      || /^\s*([-*+])\s+/.test(line)
      || /^\s*\d+[.)]\s+/.test(line)
      || /^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line);
  }

  function splitRow(line) {
    var trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
    return trimmed.split("|").map(function (cell) { return cell.trim(); });
  }

  /** Markdown 子集 → 块级 DOM 序列。只产出元素与文本节点，不拼 HTML 字符串。 */
  function parseMarkdown(source) {
    var lines = String(source || "").replace(/\r\n?/g, "\n").split("\n");
    var blocks = [];
    var i = 0;

    while (i < lines.length) {
      var line = lines[i];
      var trimmed = line.trim();
      if (!trimmed) { i += 1; continue; }

      if (/^```/.test(trimmed)) {
        var codeLines = [];
        i += 1;
        while (i < lines.length && !/^```/.test(lines[i].trim())) {
          codeLines.push(lines[i]);
          i += 1;
        }
        i += 1;
        var pre = document.createElement("pre");
        pre.appendChild(el("code", null, codeLines.join("\n")));
        blocks.push(pre);
        continue;
      }

      if (/^\$\$/.test(trimmed)) {
        var texLines = [];
        var inlineMath = trimmed.match(/^\$\$([\s\S]*?)\$\$$/);
        if (inlineMath) {
          blocks.push(mathNode(inlineMath[1].trim(), true));
          i += 1;
          continue;
        }
        var first = trimmed.slice(2);
        if (first.trim()) texLines.push(first);
        i += 1;
        while (i < lines.length && lines[i].trim().indexOf("$$") < 0) {
          texLines.push(lines[i]);
          i += 1;
        }
        if (i < lines.length) {
          var tail = lines[i].trim();
          var tailText = tail.replace(/\$\$.*$/, "");
          if (tailText.trim()) texLines.push(tailText);
          i += 1;
        }
        blocks.push(mathNode(texLines.join("\n").trim(), true));
        continue;
      }

      var heading = trimmed.match(/^(#{1,4})\s+(.*)$/);
      if (heading) {
        var level = heading[1].length;
        var title = el("h" + level);
        appendInline(title, heading[2]);
        blocks.push(title);
        i += 1;
        continue;
      }

      if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(trimmed)) {
        blocks.push(document.createElement("hr"));
        i += 1;
        continue;
      }

      if (/^>\s?/.test(trimmed)) {
        var quote = document.createElement("blockquote");
        while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
          var quoteLine = lines[i].replace(/^\s*>\s?/, "");
          if (quoteLine.trim()) {
            var quoteP = document.createElement("p");
            appendInline(quoteP, quoteLine);
            quote.appendChild(quoteP);
          }
          i += 1;
        }
        blocks.push(quote);
        continue;
      }

      if (/^\s*([-*+])\s+/.test(line)) {
        var ul = document.createElement("ul");
        while (i < lines.length && /^\s*([-*+])\s+/.test(lines[i])) {
          var li = document.createElement("li");
          appendInline(li, lines[i].replace(/^\s*([-*+])\s+/, ""));
          ul.appendChild(li);
          i += 1;
        }
        blocks.push(ul);
        continue;
      }

      if (/^\s*\d+[.)]\s+/.test(line)) {
        var ol = document.createElement("ol");
        while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) {
          var oli = document.createElement("li");
          appendInline(oli, lines[i].replace(/^\s*\d+[.)]\s+/, ""));
          ol.appendChild(oli);
          i += 1;
        }
        blocks.push(ol);
        continue;
      }

      if (isTableStart(lines, i)) {
        var table = document.createElement("table");
        var headerRow = document.createElement("tr");
        splitRow(lines[i]).forEach(function (cellText) {
          var th = document.createElement("th");
          appendInline(th, cellText);
          headerRow.appendChild(th);
        });
        table.appendChild(headerRow);
        i += 2;
        while (i < lines.length && lines[i].indexOf("|") >= 0 && lines[i].trim()) {
          var row = document.createElement("tr");
          splitRow(lines[i]).forEach(function (cellText) {
            var td = document.createElement("td");
            appendInline(td, cellText);
            row.appendChild(td);
          });
          table.appendChild(row);
          i += 1;
        }
        blocks.push(table);
        continue;
      }

      // 普通段落：吃到空行或下一个块起始为止
      var paraLines = [trimmed];
      i += 1;
      while (i < lines.length && lines[i].trim() && !startsBlock(lines[i]) && !isTableStart(lines, i)) {
        paraLines.push(lines[i].trim());
        i += 1;
      }
      var p = document.createElement("p");
      appendInline(p, joinLines(paraLines));
      blocks.push(p);
    }

    return blocks;
  }

  // ---------- 分页 ----------
  function computeScale() {
    if (!previewEl) return 1;
    var width = previewEl.clientWidth - 40;
    if (width <= 0) return 1;
    return Math.max(0.45, Math.min(1, Math.round((width / PAGE_W) * 1000) / 1000));
  }

  function applyScale() {
    activeScale = computeScale();
    document.documentElement.style.setProperty("--hp-scale", String(activeScale));
    pages.forEach(function (record) {
      record.wrap.style.width = (PAGE_W * activeScale) + "px";
      record.wrap.style.height = (PAGE_H * activeScale) + "px";
    });
  }

  function newPage() {
    var wrap = el("div", "hp-page-wrap");
    var section = el("section", "hp-page");
    section.setAttribute("data-page", String(pages.length + 1));

    var head = el("header", "hp-page-head");
    head.appendChild(el("span", "hp-page-title", "九章算子 · 讲义"));
    head.appendChild(el("span", "hp-page-info", "姓名 ________ 日期 ________"));

    var body = el("div", "hp-page-body");
    var foot = el("footer", "hp-page-foot", "第 " + (pages.length + 1) + " 页");

    section.appendChild(head);
    section.appendChild(body);
    section.appendChild(foot);
    wrap.appendChild(section);
    pagesEl.appendChild(wrap);

    var record = { wrap: wrap, page: section, body: body, foot: foot, used: 0 };
    wrap.style.width = (PAGE_W * activeScale) + "px";
    wrap.style.height = (PAGE_H * activeScale) + "px";
    pages.push(record);
    return record;
  }

  /** 所有块一次进测量列，只强制一次布局；高度取相邻块 top 差，含块间距。 */
  function measureBlocks(blocks) {
    measureEl.textContent = "";
    var fragment = document.createDocumentFragment();
    blocks.forEach(function (block) { fragment.appendChild(block); });
    measureEl.appendChild(fragment);
    measureEl.getBoundingClientRect();

    var tops = blocks.map(function (block) { return block.offsetTop; });
    var heights = blocks.map(function (block, index) {
      if (index + 1 < blocks.length) return Math.max(0, tops[index + 1] - tops[index]);
      return block.offsetHeight + 8;
    });
    measureEl.textContent = "";
    return heights;
  }

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

  /** 收尾复核：量高算不进公式墨迹，整卷读一次，把越界尾块顺延。 */
  function settlePages() {
    var rounds = 0;
    var moves = 0;
    for (var round = 0; round < 4; round += 1) {
      var overflowing = [];
      for (var i = 0; i < pages.length; i += 1) {
        var body = pages[i].body;
        if (body.scrollHeight > body.clientHeight + 1 && body.children.length > 1) {
          overflowing.push(i);
        }
      }
      if (!overflowing.length) break;
      rounds += 1;
      moves += overflowing.length;
      overflowing.forEach(function (index) {
        var record = pages[index];
        var last = record.body.lastElementChild;
        var next = pages[index + 1];
        if (!next) next = newPage();
        next.body.insertBefore(last, next.body.firstChild);
      });
    }
    pages.forEach(function (record) {
      if (record.body.scrollHeight > record.body.clientHeight + 1 && record.body.firstElementChild) {
        record.body.firstElementChild.setAttribute("data-overflow", "true");
      }
    });
    return { rounds: rounds, moves: moves };
  }

  function updateStats(pagesCount) {
    if (!statsEl) return;
    var chars = state.markdown.length;
    var text = chars + " 字 · " + pagesCount + " 页 · " + state.renderMs + " ms";
    statsEl.textContent = text;
  }

  function renderEmpty(started) {
    var note = el("div", "hp-empty", "在左侧写点什么，或点「载入示例」看一份完整讲义。");
    pagesEl.appendChild(note);
    state.renderMs = Math.round((performance.now() - started) * 10) / 10;
    updateStats(0);
    if (metricsEl) {
      metricsEl.setAttribute("data-pages", "0");
      metricsEl.setAttribute("data-blocks", "0");
      metricsEl.setAttribute("data-chars", String(state.markdown.length));
      metricsEl.setAttribute("data-render-ms", String(state.renderMs));
      metricsEl.setAttribute("data-overflow", "0");
      reflowSeq += 1;
      metricsEl.setAttribute("data-reflow", String(reflowSeq));
    }
  }

  function renderPages(started) {
    pagesEl.textContent = "";
    pages = [];
    pagesEl.setAttribute("data-size", state.size);
    measureEl.setAttribute("data-size", state.size);

    // 图片尺寸已进缓存，重建一遍让 <img> 带上写死的宽高
    var blocks = parseMarkdown(state.markdown);
    activeScale = computeScale();
    document.documentElement.style.setProperty("--hp-scale", String(activeScale));

    var heights = measureBlocks(blocks);
    var record = newPage();
    var maxHeight = 0;
    blocks.forEach(function (block, index) {
      maxHeight = Math.max(maxHeight, heights[index]);
      record = place(record, block, heights[index]);
    });
    var settled = settlePages();

    pages.forEach(function (item, index) {
      item.foot.textContent = "第 " + (index + 1) + " 页 / 共 " + pages.length + " 页";
      item.page.setAttribute("data-page", String(index + 1));
    });

    var overflow = pagesEl.querySelectorAll("[data-overflow='true']").length;
    state.renderMs = Math.round((performance.now() - started) * 10) / 10;
    updateStats(pages.length);

    if (metricsEl) {
      metricsEl.setAttribute("data-pages", String(pages.length));
      metricsEl.setAttribute("data-blocks", String(blocks.length));
      metricsEl.setAttribute("data-chars", String(state.markdown.length));
      metricsEl.setAttribute("data-render-ms", String(state.renderMs));
      metricsEl.setAttribute("data-overflow", String(overflow));
      metricsEl.setAttribute("data-max-block", String(Math.round(maxHeight)));
      metricsEl.setAttribute("data-settle", settled.rounds + "轮/" + settled.moves + "件");
      metricsEl.setAttribute("data-size", state.size);
      reflowSeq += 1;
      metricsEl.setAttribute("data-reflow", String(reflowSeq));
    }

    applyScale();
    dock("讲义已排版：" + state.markdown.length + " 字 · " + pages.length + " 页 · " + state.renderMs + " ms" +
      (overflow ? "（" + overflow + " 处超高）" : ""));
  }

  function reflow() {
    var started = performance.now();
    var token = ++renderToken;
    var probe = parseMarkdown(state.markdown);
    if (!probe.length) {
      pagesEl.textContent = "";
      pages = [];
      renderEmpty(started);
      return Promise.resolve();
    }
    // 先预载本地配图；期间用户继续打字就作废这次结果
    return primeImages(probe).then(function () {
      if (token === renderToken) renderPages(started);
    });
  }

  function scheduleReflow() {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(reflow, DEBOUNCE_MS);
  }

  function setSize(value) {
    var next = value === "large" || value === "大字" ? "large" : "normal";
    // 激活时宿主会把初始参数再通知一次；尺寸没变就不重排，省掉一整轮无谓排版
    if (next === state.size) return;
    state.size = next;
    reflow();
  }

  function loadMarkdown(text) {
    state.markdown = String(text || "");
    if (inputEl) inputEl.value = state.markdown;
    reflow();
  }

  // ---------- 交互 ----------
  if (inputEl) {
    inputEl.addEventListener("input", function () {
      state.markdown = inputEl.value;
      scheduleReflow();
    });
  }

  var sampleBtn = document.getElementById("hpSample");
  if (sampleBtn) {
    sampleBtn.addEventListener("click", function () {
      loadMarkdown(SAMPLE);
      toast("已载入示例讲义");
    });
  }

  var printBtn = document.getElementById("hpPrint");
  if (printBtn) {
    printBtn.addEventListener("click", function () {
      // 配图与分页是异步落定的，直接 print() 会把还没排完的版面打进纸里
      printBtn.disabled = true;
      printBtn.setAttribute("aria-busy", "true");
      reflow().then(function () {
        printBtn.disabled = false;
        printBtn.removeAttribute("aria-busy");
        window.print();
      }, function (error) {
        printBtn.disabled = false;
        printBtn.removeAttribute("aria-busy");
        toast("排版没走完：" + error.message + "，仍按当前版面打印。");
        window.print();
      });
    });
  }

  if (previewEl) {
    if (window.ResizeObserver) {
      new ResizeObserver(function () { applyScale(); }).observe(previewEl);
    } else {
      window.addEventListener("resize", applyScale);
    }
  }

  // ---------- 协议 ----------
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    if (message.kind === "notification") {
      if (message.event === "ui.params.changed") {
        var values = (message.payload && message.payload.values) || {};
        if (Object.prototype.hasOwnProperty.call(values, "size")) setSize(values.size);
      } else if (message.event === "system.question_updated" || message.event === "question.updated") {
        // 讲义排的是收到的那份 HTML，内容变了不能假装重排——如实提示重新发送
        markStale();
      }
      return;
    }

    if (message.kind !== "request") return;
    if (message.method === "plugin.activate") {
      root.hidden = false;
      var initial = (message.payload && message.payload.values) || {};
      state.size = initial.size === "大字" || initial.size === "large" ? "large" : "normal";
      if (!state.markdown) loadMarkdown(SAMPLE);
      else reflow();
      return respond(event.source, message.id, true, { ready: true, plugin_id: PLUGIN_ID });
    }
    if (message.method === "plugin.deactivate") {
      root.hidden = true;
      return respond(event.source, message.id, true, { ready: false });
    }
    respond(event.source, message.id, false, null, "UNSUPPORTED_METHOD", "未实现的方法：" + message.method);
  });

  if (window.parent === window && root) {
    root.hidden = false;
    loadMarkdown(SAMPLE);
  }
})();
