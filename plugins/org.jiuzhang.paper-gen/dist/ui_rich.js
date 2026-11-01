/**
 * 组卷的富文本与题块构建（org.jiuzhang.paper-gen / ui_rich.js）。
 *
 * 从 plugin.js 拆出（PLUGIN_SPEC §2.8.1「单文件不得过 800 行」）：把题干、选项与解析
 * 里的 Markdown+LaTeX 定界符变成安全的 DOM，再拼成一题落在纸面上的题块。
 * KaTeX 渲染结果与配图天然尺寸两个缓存归本模块私有——先把尺寸量好再排，
 * 图片解码后才不会把整页顶出纸边。
 *
 * 全程只用 createElement / textContent 与 KaTeX 自己产出的 HTML，配图只认
 * /static/uploads/ 开头的地址：真题文本里带什么尖括号，都印不进纸面。
 */
(function (global) {
  "use strict";

  var mathCache = new Map();
  // 图片天然尺寸缓存：先量好再排，避免懒加载后图片撑高、把整页顶出安全区
  var imageSizeCache = new Map();

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
      return "\u0000TABLE" + (tables.length - 1) + "\u0000\n";
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

  /**
   * 构建题块：题干行 / 选项 / 答案段（.pg-ansbox）/ 间距。
   * 答案与解析整体包进 .pg-ansbox，是为了「切答案」只摘掉一个子件、
   * 其余子件落位高度分毫不差（见文件头第 2 条），从而不必整题重测。
   */
  function buildQuestionBlock(question) {
    var block = el("div", "pg-q");
    block.setAttribute("data-qid", question.id);

    var head = el("div", "pg-q-head");
    var num = el("span", "pg-q-no", "");
    head.appendChild(num);
    var source = sourceLabel(question);
    if (source) head.appendChild(el("span", "pg-q-source", source));
    block.appendChild(head);
    block.setAttribute("data-head", "1");

    richLines(question.stem).forEach(function (line, index, all) {
      if (line.tagName === "P") {
        line.className = "pg-line";
        // 结构无关的行距：题块可能被拆开落页，:last-of-type 在纸面上不再可靠
        if (index === all.length - 1) line.classList.add("pg-line-last");
      }
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

    var answer = answerText(question);
    var solution = question.solution ? solutionBody(question.solution) : "";
    if (answer || solution) {
      var box = el("div", "pg-ansbox");
      if (answer) box.appendChild(el("div", "pg-answer", "答案：" + answer));
      if (solution) {
        richLines(solution).forEach(function (line, lineIndex) {
          if (line.tagName === "P") line.className = "pg-solution";
          if (lineIndex === 0 && line.tagName === "P") {
            line.insertBefore(el("span", "pg-sol-title", "解析："), line.firstChild);
          }
          box.appendChild(line);
        });
      }
      block.appendChild(box);
    }

    block.appendChild(el("div", "pg-q-gap"));
    return block;
  }

  global.JzoPaperRich = {
    el: el,
    answerText: answerText,
    primeImages: primeImages,
    buildQuestionBlock: buildQuestionBlock
  };
})(window);
