/*
 * 讲义插件 · Markdown 子集 → DOM（ui_ 前缀 = 只管「数据变成界面」，PLUGIN_SPEC §2.8.1）。
 *
 * 本文件不认识宿主：进来的是一段段源码文本，出去的是元素与文本节点，
 * 全程只 createElement / appendChild，不拼 HTML 字符串（铁律 4：界面全在沙箱里，
 * 交给宿主的每一寸都要能被净化白名单管住）。
 * MathJax 渲染缓存与配图自然尺寸缓存归本文件私有，插件别处不许再留第二份。
 */
(function (global) {
  "use strict";

  var mathCache = new Map();
  // 配图先量自然尺寸再排：否则图片解码后撑高，会把整页顶出纸边
  var imageCache = new Map();

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
      html = window.JzoMath ? window.JzoMath.render(tex, display) : "";
      if (html) mathCache.set(key, html);
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
    var pattern = /(!\[[^\]]*\]\(\/static\/uploads\/[^)\s]+\)|\\\[[\s\S]*?\\\]|\\\([^\n]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]*?\$|\\paren\*?(?:\[[^\]]*\])?|\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`\n]+`|\\textbf\{[^{}]*\})/g;
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
      } else if (token.slice(0, 6) === "\\paren") {
        target.appendChild(mathNode(token, false));
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

  global.JzoHandoutRich = {
    el: el,
    mathNode: mathNode,
    imageNode: imageNode,
    primeImages: primeImages,
    appendInline: appendInline,
    parseMarkdown: parseMarkdown
  };
})(window);
