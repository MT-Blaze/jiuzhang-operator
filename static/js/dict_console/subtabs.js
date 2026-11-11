/**
 * 字典控制台二级标签：分类面板内的一排横向页签（浏览器页签观感）。
 * 一个标签只显示一个子页面：子面板懒渲染，切换只改 display，绝不纵向堆叠。
 * 键盘与主标签一致：左右方向键切换、Home/End 跳首尾。
 * 整块下架：删本文件、dict_console_subtabs.css 与 panels.js 的 DcSubTabs.mount 调用。
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function mount(host, options) {
    var opts = options || {};
    var items = opts.items || [];
    var prefix = opts.idPrefix || "sub";
    var activeKey = null;

    var wrap = el("div", "dc-subtabs-wrap");
    var bar = el("div", "dc-subtabs");
    bar.setAttribute("role", "tablist");
    bar.setAttribute("aria-label", opts.label || "二级标签");
    var body = el("div", "dc-subpanels");
    wrap.appendChild(bar);
    wrap.appendChild(body);
    host.appendChild(wrap);

    var entries = items.map(function (item) {
      var button = el("button", "dc-subtab", item.label);
      button.type = "button";
      button.id = "dcSubTab-" + prefix + "-" + item.key;
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", "false");
      button.setAttribute("aria-controls", "dcSubPanel-" + prefix + "-" + item.key);
      button.tabIndex = -1;
      button.addEventListener("click", function () { activate(item.key); });
      bar.appendChild(button);

      var pane = el("section", "dc-subpanel");
      pane.id = "dcSubPanel-" + prefix + "-" + item.key;
      pane.setAttribute("role", "tabpanel");
      pane.setAttribute("aria-labelledby", button.id);
      pane.style.display = "none";
      body.appendChild(pane);
      return { item: item, button: button, pane: pane, rendered: false };
    });

    function get(key) {
      for (var i = 0; i < entries.length; i += 1) {
        if (entries[i].item.key === key) return entries[i];
      }
      return null;
    }

    function activate(key, silent) {
      var target = get(key) || entries[0];
      if (!target) return;
      activeKey = target.item.key;
      entries.forEach(function (entry) {
        var on = entry === target;
        entry.button.setAttribute("aria-selected", on ? "true" : "false");
        entry.button.tabIndex = on ? 0 : -1;
        entry.pane.style.display = on ? "block" : "none";
      });
      if (!target.rendered) {
        target.rendered = true;
        target.item.render(target.pane);
      }
      if (!silent && typeof opts.onActivate === "function") opts.onActivate(activeKey);
    }

    bar.addEventListener("keydown", function (event) {
      var keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
      if (keys.indexOf(event.key) === -1) return;
      var current = get(activeKey);
      if (!current || event.target !== current.button) return;
      event.preventDefault();
      var index = entries.indexOf(current);
      var nextIndex = index;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % entries.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + entries.length) % entries.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = entries.length - 1;
      var next = entries[nextIndex];
      activate(next.item.key);
      next.button.focus();
    });

    var initial = get(opts.initial) ? opts.initial : (entries[0] && entries[0].item.key);
    if (initial) activate(initial, true);
    if (initial && typeof opts.onActivate === "function") opts.onActivate(initial);

    return { activate: activate, active: function () { return activeKey; } };
  }

  window.DcSubTabs = { mount: mount };
})();
