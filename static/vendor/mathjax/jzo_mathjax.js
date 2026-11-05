/**
 * jzo_mathjax.js —— 九章算子前端的统一公式桥。
 *
 * 必须先于 tex-svg-full.js 加载：这里写的是 MathJax 的启动配置。
 * 真正渲染时再读 window.MathJax，因此桥本身不依赖脚本加载次序。
 *
 * exam-zh 的 \paren / \fillin 带可选参数，MathJax 3 的宏字典表达不了；
 * 交给 normalize() 先换成等价的 TeX，其余常用命令走 macros。
 * 任何一条命令渲染失败都不抛给界面：返回空串，调用方退回源码文本。
 */
(function (global) {
  "use strict";

  global.MathJax = {
    tex: {
      inlineMath: [["$", "$"], ["\\(", "\\)"]],
      displayMath: [["$$", "$$"], ["\\[", "\\]"]],
      processEscapes: true,
      macros: {
        paren: ["\\left(\\kern{2em}\\right)", 0],
        fillin: ["\\underline{\\hspace{2em}}", 0],
        blank: ["\\underline{\\hspace{4em}}", 0],
        eu: "\\mathrm{e}",
        upe: "\\mathrm{e}",
        iu: "\\mathrm{i}",
        upi: "\\mathrm{i}",
        uppi: "\\mathrm{\\pi}",
        paralleleq: "\\parallel",
        circlednumber: ["\\textcircled{#1}", 1],
        score: ["\\text{（#1 分）}", 1],
        zhu: "\\text{注：}"
      }
    },
    svg: { fontCache: "local" },
    options: { enableMenu: false },
    startup: { typeset: false }
  };

  // 手动调 tex2svg 不走 MathJax 的 typeset，辅助 MathML 的隐藏样式得自己补；
  // 否则公式会在 SVG 旁边再显示一遍文字（看起来像「a > b > 0a > b > 0」）。
  (function ensureAssistiveStyle() {
    if (document.getElementById("jzo-mathjax-style")) return;
    var style = document.createElement("style");
    style.id = "jzo-mathjax-style";
    style.textContent = "mjx-assistive-mml{position:absolute!important;top:0;left:0;"
      + "clip:rect(1px,1px,1px,1px);padding:1px 0 0 0!important;border:0!important;"
      + "height:1px!important;width:1px!important;overflow:hidden!important;"
      + "display:block!important}";
    (document.head || document.documentElement).appendChild(style);
  })();

  var cache = new Map();

  function normalize(source) {
    var text = String(source == null ? "" : source);
    text = text.replace(/\\paren\*?(?:\[([^\]]*)\])?/g, function (_, answer) {
      if (answer == null || answer === "") {
        return "\\left(\\kern{2em}\\right)";
      }
      return "\\left(\\kern{0.7em}" + answer + "\\kern{0.7em}\\right)";
    });
    text = text.replace(/\\fillin\*?(?:\[([^\]]*)\])?/g, function (_, hint) {
      if (hint == null || hint === "") {
        return "\\underline{\\hspace{2em}}";
      }
      return "\\underline{\\text{" + hint + "}}";
    });
    return text;
  }

  function engineReady() {
    return !!(global.MathJax && typeof global.MathJax.tex2svg === "function");
  }

  function hasError(node) {
    if (!node) return true;
    if (node.querySelector && node.querySelector("merror,[data-mjx-error]")) return true;
    // MathJax 对未定义命令的兜底是红色 mtext（不是 merror）；红字同样算失败，
    // 返回空串让调用方退回源码，绝不在界面上飘红。
    if (node.querySelector &&
        node.querySelector('mtext[mathcolor="red"], [data-mml-node="mtext"][fill="red"]')) {
      return true;
    }
    return false;
  }

  /** TeX → SVG 字符串；失败返回空串，调用方用源码降级显示。 */
  function render(tex, display) {
    var source = String(tex == null ? "" : tex).trim();
    if (!source) return "";
    var key = (display ? "D:" : "I:") + source;
    if (cache.has(key)) return cache.get(key);
    if (!engineReady()) return "";
    var html = "";
    try {
      var node = global.MathJax.tex2svg(normalize(source), { display: Boolean(display) });
      html = !hasError(node) && node.outerHTML ? node.outerHTML : "";
    } catch (error) {
      html = "";
    }
    cache.set(key, html);
    return html;
  }

  /** 给需要「引擎就绪后补一次渲染」的界面用；引擎已就绪则立即回调。 */
  function onReady(callback) {
    if (typeof callback !== "function") return;
    if (engineReady()) {
      callback();
      return;
    }
    try {
      global.MathJax.startup.promise.then(callback).catch(function () { /* 引擎坏了就走源码 */ });
    } catch (error) {
      /* 配置未完成：调用方保持源码显示即可 */
    }
  }

  global.JzoMath = {
    normalize: normalize,
    onReady: onReady,
    ready: engineReady,
    render: render
  };
})(window);
