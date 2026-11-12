/**
 * 底座微内核之三：底栏输出区的账与渲染（从 workspace.js 拆出）。
 *
 * 只负责「给定条目与视图，把这一页画出来」：三级视图的过滤口径、空态文案、
 * 报错现场的原样铺开，都在这里；条目从哪来、双击复制怎么反馈仍归 workspace.js。
 */
(function (global) {
  "use strict";

  var DOCK_EMPTY = {
    log: "暂无业务日志。字典、题库等真实操作记录会出现在这里。",
    error: "没有报错。插件与底座的事件流一切正常。",
    terminal: "暂无系统事件。"
  };
  var DOCK_VIEWS = { log: true, error: true, terminal: true };

  function create(ctx) {
    /** 三个视图各认各的账：报错诊断收两本账里的 warn/error，运行日志只认业务账。 */
    function entryVisible(entry) {
      var dockView = ctx.view();
      if (dockView === "error") return entry.level === "error" || entry.level === "warn";
      if (dockView === "terminal") return entry.scope === "system";
      return entry.scope === "runtime";
    }

    function renderDock() {
      var logEl = ctx.el;
      if (!logEl) return;
      var dockView = ctx.view();
      logEl.setAttribute("data-view", dockView);
      logEl.textContent = "";
      var shown = ctx.entries().filter(entryVisible);
      if (!shown.length) {
        var empty = document.createElement("li");
        empty.className = "ws-dock-empty";
        empty.textContent = DOCK_EMPTY[dockView] || DOCK_EMPTY.log;
        logEl.appendChild(empty);
        return;
      }
      shown.forEach(function (entry) {
        var item = document.createElement("li");
        item.className = "ws-dock-item";
        item.setAttribute("data-level", entry.level);
        // 报错诊断复制的是完整现场；没有现场才退回那一行摘要。
        item.setAttribute("data-copy", entry.detail || entry.line);
        var time = document.createElement("span");
        time.className = "ws-dock-time";
        time.textContent = entry.time;
        item.appendChild(time);
        if (entry.topic) {
          var tag = document.createElement("span");
          tag.className = "ws-dock-topic";
          tag.textContent = entry.topic;
          item.appendChild(tag);
        }
        var body = document.createElement("span");
        body.className = "ws-dock-text";
        body.textContent = entry.text;
        item.appendChild(body);
        // 报错诊断要打完整现场：Response 全文、堆栈、请求行一律按原文铺开，
        // 不许只剩干瘪的一句「Not Found」。
        if (dockView === "error" && entry.detail && entry.detail !== entry.text) {
          var detail = document.createElement("pre");
          detail.className = "ws-dock-detail";
          detail.textContent = entry.detail;
          item.appendChild(detail);
        }
        if (dockView === "error") {
          var hint = document.createElement("span");
          hint.className = "ws-dock-copy";
          hint.setAttribute("aria-hidden", "true");
          hint.textContent = "双击复制";
          item.appendChild(hint);
        }
        logEl.appendChild(item);
      });
      var scrollEl = ctx.scrollEl && ctx.scrollEl();
      if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
    }

    return { entryVisible: entryVisible, renderDock: renderDock };
  }

  global.JzoCoreLog = { create: create, DOCK_EMPTY: DOCK_EMPTY, DOCK_VIEWS: DOCK_VIEWS };
})(window);
