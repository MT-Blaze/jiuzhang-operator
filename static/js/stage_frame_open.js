/**
 * 宿主自有 iframe 页签：同源页面（数据字典控制台等）像控制台一样住进中央画布。
 * 不挂 sandbox：它跟宿主同源、只读本地数据，本就不是插件，假装隔离反而误导。
 * 按 key 幂等：已开的页签只激活，绝不再造第二枚；现有看板/录题页签一概不动。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var addTab = deps.addTab;
    var activate = deps.activate;
    var findTab = deps.findTab;
    var dock = deps.dock;
    var emit = deps.emit;

    function open(key, title, src) {
      var existing = findTab(key);
      if (existing) {
        activate(key);
        return existing;
      }
      var panel = document.createElement("section");
      panel.className = "ws-tab-panel";
      panel.id = "wsPanel_" + String(key).replace(/[^a-zA-Z0-9_-]/g, "_");
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-label", title);
      panel.setAttribute("data-tab", key);

      var frame = document.createElement("iframe");
      frame.className = "ws-console-frame";
      frame.setAttribute("title", title);
      frame.setAttribute("loading", "lazy");
      frame.src = src;
      panel.appendChild(frame);

      var tab = {
        key: key,
        kind: "frame",
        title: title,
        closable: true,
        panel: panel,
        state: "live",
        lastUsed: Date.now(),
        frame: frame
      };
      addTab(tab);
      activate(key);
      dock("已打开「" + title + "」。", "stage.tab.opened");
      emit("stage.tab.opened", { key: key, pluginId: null });
      return tab;
    }

    return { open: open };
  }

  global.JzoStageFrameOpen = { create: create };
})(window);
