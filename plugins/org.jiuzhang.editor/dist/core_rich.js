/**
 * core_rich.js —— plugin.js 的「富文本」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：任何插件 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
  // ---------- 富文本（文字 + LaTeX + 底座托管配图） ----------
  var mathCache = new Map();
  var katexCount = 0;
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function clampValue(value, min, max) {
    if (max < min) return min;
    if (value < min) return min;
    if (value > max) return max;
    return value;
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
    if (html) {
      katexCount += 1;
      span.innerHTML = html;
    } else {
      span.textContent = (display ? "$$" : "$") + tex + (display ? "$$" : "$");
    }
    return span;
  }

  var INLINE_RE = /(\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}|\\fillin(?:\[[^\]]*\])?|!\[[^\]]*\]\([^)]*\)|\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\$[^$\n]*?\$|\\\([\s\S]*?\\\)|\*\*[^*]+\*\*)/g;

  /** 只认底座托管路径与 asset:// 逻辑地址；远程 URL / data: / file: 一律当普通文本。 */
  function safeAssetUri(value) {
    var uri = String(value == null ? "" : value).trim();
    if (uri.indexOf("/static/uploads/") === 0) return uri;
    // 中转站里的配图挂在 pending_assets/，审核台看的就是它。
    if (uri.indexOf("/static/pending/") === 0) return uri;
    if (uri.indexOf("/static/icons/") === 0) return uri;
    if (uri.indexOf("/static/assets/") === 0) return uri;
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

  /** 「\fillin 不带答案」是格式宪法：方括号里的内容只当老师留下的提示，绝不当答案渲染。 */
  function appendFillin(parent, token) {
    var hint = /\[([^\]]*)\]$/.exec(token);
    parent.appendChild(el("span", "ed-fillin", hint ? hint[1] : ""));
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
      } else if (token.slice(0, 7) === "\\fillin") {
        appendFillin(parent, token);
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
        parent.appendChild(mathNode(segment.slice(2, -2), true));
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

    return {
      INLINE_RE: INLINE_RE,
      appendBody: appendBody,
      appendFillin: appendFillin,
      appendImageRef: appendImageRef,
      appendRich: appendRich,
      clampValue: clampValue,
      el: el,
      // 计数是模块私有的可变标量：外面只能通过这两个口子看与清。
      katexCount: function () { return katexCount; },
      resetKatexCount: function () { katexCount = 0; },
      mathNode: mathNode,
      safeAssetUri: safeAssetUri,
    };
  }

  global.JzoEditorRich = { create: create };
})(window);
