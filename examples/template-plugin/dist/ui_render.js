/*
 * 模板插件 · 界面渲染（ui_ 前缀 = 只管「数据 → DOM」，PLUGIN_SPEC §2.8.1）。
 *
 * 数据驱动的标准写法：事件处理器只改 ui 上的数据，DOM 由 watch 登记的渲染函数自己重画。
 * 引擎是底座随发的公共资产 /static/common/ui_reactive.js，所有插件共用同一份，
 * 插件里不许再各存一份副本，也不许手写「改数据顺手改 DOM」的土办法（§2.8.3）。
 *
 *   ui.status = "取到 3 题";            // 只写数据
 *   ui.rows = [{ text: "…" }];          // 只写数据
 *   —— 下一个微任务里，下面两个渲染函数自己重跑，一行 DOM 不用人碰。
 */
(function (global) {
  "use strict";

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /**
   * @param ctx {{statusEl: Element, listEl: Element}} 两个容器节点，由 plugin.js 装配时传入。
   */
  function create(ctx) {
    var ui = global.JzoReactive.reactive({
      status: "等待宿主激活……",
      rows: [],          // [{key, text, html}]——列表唯一事实来源
      cardHtml: ""       // question.render 最近一次交出去的卡片（演示用）
    });

    function renderStatus() {
      if (!ctx.statusEl) return;
      ctx.statusEl.textContent = ui.status;
    }

    function renderRows() {
      if (!ctx.listEl) return;
      ctx.listEl.textContent = "";
      ui.rows.forEach(function (row) {
        var card = document.createElement("div");
        card.className = "item";
        // 只有从宿主拿到的、必须带标记的内容才走 html；其余一律 textContent，天然免疫 XSS。
        if (row.html) card.innerHTML = escapeHtml(row.text ? row.text + " " : "") + row.html;
        else card.textContent = row.text;
        ctx.listEl.appendChild(card);
      });
    }

    global.JzoReactive.watch(function () {
      renderStatus();
      renderRows();
    });

    return {
      ui: ui,
      // 宿主下发的单题卡片必须先过净化：宿主侧白名单会剥掉 <script>、内联事件与 javascript:。
      escapeHtml: escapeHtml
    };
  }

  global.JzoTemplateUi = { create: create };
})(window);
