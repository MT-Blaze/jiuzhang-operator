/**
 * 知识点树 · 行首细灰树线与改名按钮（2026-11-12）。
 * prefix 记录每位祖先是否还要往下画竖线，当前层画 ├ / └；层级不再用 padding 缩进。
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

  function span(prefix, isLast, blank, caret) {
    var wrap = el("span", "dkl-guide");
    wrap.setAttribute("aria-hidden", "true");
    prefix.forEach(function (open) {
      wrap.appendChild(el("span", open ? "dkl-guide-seg" : "dkl-guide-seg dkl-guide-blank"));
    });
    wrap.appendChild(el("span", "dkl-guide-cur"
      + (isLast ? " dkl-guide-last" : "")
      + (blank ? " dkl-guide-blank-cur" : "")));
    if (caret) wrap.appendChild(el("span", "dkl-caret-empty"));
    return wrap;
  }

  function childPrefix(prefix, isLast) {
    return prefix.concat([!isLast]);
  }

  function opButton(text, danger, label, onClick) {
    var button = el("button", "dkl-op" + (danger ? " dkl-op-danger" : ""), text);
    button.type = "button";
    button.setAttribute("aria-label", label);
    button.addEventListener("click", function () { onClick(button); });
    return button;
  }

  function empty(prefix, text) {
    var li = el("li", "dkl-empty");
    li.appendChild(span(prefix, true, true, true));
    li.appendChild(el("span", "dkl-empty-text", text));
    return li;
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

  window.DcLinkGuide = {
    span: span, childPrefix: childPrefix, empty: empty, nameButton: nameButton,
    opButton: opButton
  };
})();
