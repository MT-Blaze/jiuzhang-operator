/**
 * 知识点树 · 行首细灰树线与改名按钮（2026-11-12）。
 * prefix 记录每位祖先是否还要往下画竖线，当前层画 ├ / └；层级不再用 padding 缩进。
 * 竖线由行级导线层（DcLinkGuide.lines）按整行高度画，行内内容怎么换行都不会断；
 * 行首 guide 只保留缩进占位与水平折线。
 * nameButton 复用 DcEntityShared.bindNodeClick：单击 200ms 防抖展开、双击原地改名。
 * 整块下架：删本文件与 dict_console.html 引用行即可。
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /** 行首 guide 只保留缩进占位与水平折线：折叠不再有三角标，点名称文字即可。 */
  function span(prefix, isLast, blank) {
    var wrap = el("span", "dkl-guide");
    wrap.setAttribute("aria-hidden", "true");
    prefix.forEach(function (open) {
      wrap.appendChild(el("span", open ? "dkl-guide-seg" : "dkl-guide-seg dkl-guide-blank"));
    });
    wrap.appendChild(el("span", "dkl-guide-cur"
      + (isLast ? " dkl-guide-last" : "")
      + (blank ? " dkl-guide-blank-cur" : "")));
    return wrap;
  }

  function lineEl(col, last) {
    var node = el("span", "dkl-guide-line" + (last ? " dkl-guide-line-last" : ""));
    node.setAttribute("aria-hidden", "true");
    node.style.setProperty("--col", String(col));
    return node;
  }

  /** 行级全高导线层：prefix 里每个 open 的祖先列一根，当前列再补一根（末位收半截）。 */
  function lines(prefix, last) {
    var wrap = el("span", "dkl-guide-lines");
    wrap.setAttribute("aria-hidden", "true");
    prefix.forEach(function (open, col) {
      if (open) wrap.appendChild(lineEl(col, false));
    });
    if (last !== null && last !== undefined) {
      wrap.appendChild(lineEl(prefix.length, !!last));
    }
    return wrap;
  }

  function childPrefix(prefix, isLast) {
    return prefix.concat([!isLast]);
  }

  function opButton(text, danger, label, onClick) {
    var button = el("button", "dkl-op" + (danger ? " dkl-op-danger" : ""), text);
    button.type = "button";
    button.setAttribute("aria-label", label);
    button.addEventListener("click", function (event) {
      event.stopPropagation();
      onClick(button);
    });
    return button;
  }

  /** add 非空时在文案旁补一个「＋ 添加」按钮：空状态也能直接长出下一级。 */
  function empty(prefix, text, add) {
    var li = el("li", "dkl-empty");
    var hasLine = prefix.length > 0;
    li.appendChild(lines(prefix, hasLine ? true : null));
    li.appendChild(span(prefix, true, !hasLine));
    li.appendChild(el("span", "dkl-empty-text", text));
    if (add) {
      li.appendChild(window.DcTreeAdd.emptyAdd(add));
    }
    return li;
  }

  /** 子节点列表末尾的幽灵行：低饱和整行热区，点击就地长出新输入行。 */
  function ghost(prefix, text, label, onClick, last) {
    var isLast = last !== false;
    return window.DcTreeAdd.ghostRow({
      text: text,
      label: label,
      lines: function () { return lines(prefix, isLast); },
      guide: function () { return span(prefix, isLast, false); },
      onClick: onClick
    });
  }

  function nameButton(text, label, edit, toggle) {
    var button = el("button", "dkl-name", text);
    button.type = "button";
    if (edit) {
      button.title = "双击改名";
      button.setAttribute("aria-label", label + "：双击改名");
    } else {
      button.setAttribute("aria-label", label);
    }
    window.DcEntityShared.bindNodeClick(button, {
      toggle: toggle,
      edit: edit ? function () { edit(button); } : null
    });
    return button;
  }

  /** 行尾排序号芯片：value 当前值，apply(value) 返回 Promise。 */
  function sort(value, label, apply) {
    return window.DcLinkageSort.chip(value, label, apply);
  }

  window.DcLinkGuide = {
    span: span, lines: lines, childPrefix: childPrefix, empty: empty, ghost: ghost,
    nameButton: nameButton, opButton: opButton, sort: sort
  };
})();
