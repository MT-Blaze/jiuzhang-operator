/**
 * 画布多标签管理器：新开 / 激活 / 关闭三态。
 * 交互核心（阶段一军令）：点辅助栏分类不覆盖当前页签——已存在同名页签就直接
 * 高亮切换，不存在才新开并激活。面板 DOM 常驻（hidden 切换），切走再切回
 * 不丢滚动位置与表单状态。默认页签【数据看板】钉住，不给关闭叉。
 * 结构：每枚页签是 div 外壳 + 主按钮（role=tab）+ 关闭按钮，两个按钮都可键盘聚焦；
 * 左右方向键在页签间移动，Home/End 跳首尾（WAI-ARIA tabs 模式）。
 */
(function () {
  "use strict";

  function DcTabs(tabBar, panelBox, options) {
    this.tabBar = tabBar;
    this.panelBox = panelBox;
    this.onChange = (options && options.onChange) || function () {};
    this.tabs = [];
    this.activeKey = null;
    this._onKeydown = this._onKeydown.bind(this);
    this.tabBar.addEventListener("keydown", this._onKeydown);
  }

  DcTabs.prototype.has = function (key) {
    return this.tabs.some(function (tab) { return tab.key === key; });
  };

  DcTabs.prototype.get = function (key) {
    for (var i = 0; i < this.tabs.length; i += 1) {
      if (this.tabs[i].key === key) return this.tabs[i];
    }
    return null;
  };

  /**
   * open(key, title, render, {pinned})：存在即激活；不存在则建页签 + 面板，
   * 首次激活时才调 render(panel, tab)（懒渲染，之后再切不重渲）。
   */
  DcTabs.prototype.open = function (key, title, render, options) {
    var tab = this.get(key);
    if (tab) {
      this.activate(key);
      return tab;
    }
    var self = this;
    var shell = document.createElement("div");
    shell.className = "dc-tab";
    shell.setAttribute("data-active", "false");

    var button = document.createElement("button");
    button.type = "button";
    button.className = "dc-tab-main";
    button.id = "dcTab-" + key;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", "false");
    button.setAttribute("aria-controls", "dcPanel-" + key);
    button.tabIndex = -1;
    button.textContent = title;
    button.addEventListener("click", function () { self.activate(key); });
    shell.appendChild(button);

    var pinned = !!(options && options.pinned);
    var closer = null;
    if (!pinned) {
      closer = document.createElement("button");
      closer.type = "button";
      closer.className = "dc-tab-close";
      closer.setAttribute("aria-label", "关闭页签 " + title);
      closer.textContent = "×";
      closer.addEventListener("click", function (event) {
        event.stopPropagation();
        self.close(key);
      });
      shell.appendChild(closer);
    }

    var panel = document.createElement("section");
    panel.className = "dc-panel";
    panel.id = "dcPanel-" + key;
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", button.id);
    panel.hidden = true;

    tab = {
      key: key, title: title, shell: shell, button: button, closer: closer,
      panel: panel, render: render, rendered: false, pinned: pinned
    };
    this.tabs.push(tab);
    this.tabBar.appendChild(shell);
    this.panelBox.appendChild(panel);
    this.activate(key);
    return tab;
  };

  DcTabs.prototype.activate = function (key) {
    var tab = this.get(key);
    if (!tab) return;
    this.activeKey = key;
    this.tabs.forEach(function (item) {
      var selected = item.key === key;
      item.shell.setAttribute("data-active", selected ? "true" : "false");
      item.button.setAttribute("aria-selected", selected ? "true" : "false");
      item.button.tabIndex = selected ? 0 : -1;
      item.panel.hidden = !selected;
    });
    if (!tab.rendered && typeof tab.render === "function") {
      tab.rendered = true;
      tab.render(tab.panel, tab);
    }
    tab.shell.scrollIntoView({ block: "nearest", inline: "nearest" });
    this.onChange(key);
  };

  DcTabs.prototype.close = function (key) {
    var tab = this.get(key);
    if (!tab || tab.pinned) return;
    var index = this.tabs.indexOf(tab);
    this.tabs.splice(index, 1);
    if (tab.shell.parentNode) tab.shell.parentNode.removeChild(tab.shell);
    if (tab.panel.parentNode) tab.panel.parentNode.removeChild(tab.panel);
    if (this.activeKey === key) {
      var next = this.tabs[index] || this.tabs[index - 1] || this.tabs[0];
      this.activeKey = null;
      if (next) {
        this.activate(next.key);
        next.button.focus();
      }
    }
    this.onChange(this.activeKey);
  };

  DcTabs.prototype._onKeydown = function (event) {
    var keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
    if (keys.indexOf(event.key) === -1) return;
    var current = this.get(this.activeKey);
    if (!current || event.target !== current.button) return;
    event.preventDefault();
    var index = this.tabs.indexOf(current);
    var nextIndex = index;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % this.tabs.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + this.tabs.length) % this.tabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = this.tabs.length - 1;
    var next = this.tabs[nextIndex];
    this.activate(next.key);
    next.button.focus();
  };

  window.DcTabs = DcTabs;
})();