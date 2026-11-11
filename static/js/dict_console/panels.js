/**
 * 画布面板渲染：数据看板 + 三大分类面板。
 * 所有数字来自 /api/bank/engine/status 的真实计数，不写死、不占位。
 * 分类面板内按 catalog.subs 渲染二级标签：一个标签只挂一张表 / 一棵树 / 一组联动，
 * 所有单表字典一律可增删改，统一走 DcTable，不再有只读表格。
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function stateBox(panel, message) {
    var box = el("p", "dc-panel-state", message);
    box.setAttribute("role", "status");
    panel.appendChild(box);
    return box;
  }

  function errorBox(panel, error, retry) {
    var box = el("p", "dc-panel-state dc-panel-error", "加载失败：" + error.message);
    box.setAttribute("role", "alert");
    panel.appendChild(box);
    var btn = el("button", "dc-btn", "重试");
    btn.type = "button";
    btn.addEventListener("click", retry);
    panel.appendChild(btn);
  }

  function stat(num, label) {
    var box = el("div", "dc-stat");
    box.appendChild(el("span", "dc-stat-num", String(num)));
    box.appendChild(el("span", "dc-stat-label", label));
    return box;
  }

  function categoryCount(category, counts) {
    return category.items.reduce(function (sum, item) {
      return sum + (counts[item.table] || 0);
    }, 0);
  }

  /** 数据看板：引擎真实状态 + 三大分类入口卡 + 当前全局设置。 */
  function renderDashboard(panel, tab, ctx) {
    panel.textContent = "";
    panel.appendChild(el("h2", "dc-panel-title", "数据看板"));
    var globalsLine = el("p", "dc-panel-hint", "当前全局设置：" + ctx.globals.label());
    panel.appendChild(globalsLine);
    function syncGlobals() {
      if (!panel.isConnected) {
        document.removeEventListener(window.DcGlobals.EVENT_NAME, syncGlobals);
        return;
      }
      globalsLine.textContent = "当前全局设置：" + ctx.globals.label();
    }
    document.addEventListener(window.DcGlobals.EVENT_NAME, syncGlobals);

    var loading = stateBox(panel, "正在读取引擎库状态…");
    window.DcClient.fetchJson("/api/bank/engine/status").then(function (status) {
      if (!panel.isConnected) return;
      loading.remove();
      var row = el("div", "dc-stat-row");
      row.appendChild(stat(status.table_count, "数据表"));
      row.appendChild(stat("v" + status.schema_version, "结构版本"));
      row.appendChild(stat(status.integrity === "ok" ? "正常" : status.integrity, "完整性"));
      row.appendChild(stat(status.foreign_key_violations, "外键违规"));
      panel.appendChild(row);

      panel.appendChild(el("h3", "dc-panel-title", "字典分类"));
      var grid = el("div", "dc-card-grid");
      window.DcCatalog.CATEGORIES.forEach(function (category) {
        var card = el("div", "dc-card");
        card.appendChild(el("h3", "dc-card-name", category.title));
        var count = el("p", "dc-card-count");
        count.appendChild(el("strong", "", String(categoryCount(category, status.counts || {}))));
        count.appendChild(document.createTextNode(" 行 · " + category.items.length + " 张表"));
        card.appendChild(count);
        card.appendChild(el("p", "dc-card-desc", category.desc));
        var btn = el("button", "dc-btn", "打开分类");
        btn.type = "button";
        btn.addEventListener("click", function () { ctx.openCategory(category.key); });
        card.appendChild(btn);
        grid.appendChild(card);
      });
      panel.appendChild(grid);
    }).catch(function (error) {
      if (!panel.isConnected) return;
      loading.remove();
      errorBox(panel, error, function () { renderDashboard(panel, tab, ctx); });
    });
  }

  /** 二级标签的内容：联动 / 章节树 / 单表（单表一律可增删改）。 */
  function renderSub(host, sub, ctx, category) {
    if (sub.mode === "linkage") {
      if (window.DcLinkage) window.DcLinkage.mount(host, ctx);
      return;
    }
    if (sub.mode === "chapters") {
      if (window.DcChapterTree) window.DcChapterTree.mount(host, ctx);
      return;
    }
    var item = window.DcCatalog.itemOf(category, sub.table) || {
      table: sub.table, name: sub.label, desc: category.title + " · " + sub.label
    };
    window.DcTable.mount(host, item, ctx);
  }

  /** 分类面板：分类标题下挂一排二级标签，一个标签只渲染一张表 / 一棵树 / 一组联动。 */
  function renderCategory(panel, tab, ctx, category) {
    panel.textContent = "";
    panel.appendChild(el("h2", "dc-panel-title", category.title));
    panel.appendChild(el("p", "dc-panel-hint", category.desc));
    var subs = window.DcCatalog.subsOf(category);
    window.DcSubTabs.mount(panel, {
      idPrefix: category.key,
      label: category.title + "二级标签",
      items: subs.map(function (sub) {
        return {
          key: sub.key,
          label: sub.label,
          render: function (host) { renderSub(host, sub, ctx, category); }
        };
      }),
      initial: typeof ctx.subFor === "function" ? ctx.subFor(category.key) : "",
      onActivate: function (subKey) {
        if (typeof ctx.rememberSub === "function") ctx.rememberSub(category.key, subKey);
      }
    });
  }

  window.DcPanels = { renderDashboard: renderDashboard, renderCategory: renderCategory };
})();