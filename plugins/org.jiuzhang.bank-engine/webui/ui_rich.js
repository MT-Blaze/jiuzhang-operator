/**
 * 题面安全渲染：MathJax 定界符与配图只走 textContent。
 *
 * 真题原文里的尖括号与反斜杠宏一律印不成 HTML；列表、详情与笔记共用这一份口径。
 */
(function (global) {
  "use strict";

  function create() {
    function renderMathToken(text) {
      var span = document.createElement("span");
      var paren = text.slice(0, 6) === "\\paren";
      var display = !paren && text.slice(0, 2) === "$$";
      var body = paren ? text : (display ? text.slice(2, -2) : text.slice(1, -1));
      var html = window.JzoMath ? window.JzoMath.render(body, display) : "";
      if (html) {
        span.innerHTML = html;
        span.className = display ? "cb-math-block" : "cb-math";
        return span;
      }
      span.textContent = text;
      return span;
    }

    function appendInline(target, text) {
      var pattern = /(\$\$[\s\S]*?\$\$|\$[^$\n]*?\$|\\paren\*?(?:\[[^\]]*\])?|\*\*[^*]+\*\*)/g;
      var last = 0;
      var match;
      while ((match = pattern.exec(text)) !== null) {
        if (match.index > last) target.appendChild(document.createTextNode(text.slice(last, match.index)));
        var token = match[0];
        if (token.slice(0, 1) === "$" || token.slice(0, 6) === "\\paren") {
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

    return { renderMathToken: renderMathToken, appendInline: appendInline, appendRich: appendRich };
  }

  global.JzoBankRich = { create: create };
})(window);
