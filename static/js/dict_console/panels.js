/**
 * 画布面板渲染：数据看板 + 三大分类总览。
 * 所有数字来自 /api/bank/engine/status 的真实计数，不写死、不占位。
 * 阶段一边界：分类面板只做总览导航；表格编辑与防呆随阶段二、四栏联动随阶段三交付，
 * 面板上如实标注，不做假按钮。
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

  function dictCard(item, counts) {
    var card = el("div", "dc-card");
    card.appendChild(el("h3", "dc-card-name", item.name));
    card.appendChild(el("div", "dc-card-table", item.table));
    var count = el("p", "dc-card-count");
    var num = el("strong", "", String(counts[item.table] != null ? counts[item.table] : "—"));
    count.appendChild(num);
    count.appendChild(document.createTextNode(" 行"));
    card.appendChild(count);
    card.appendChild(el("p", "dc-card-desc", item.desc));
    return card;
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

  /** 分类总览：该分类下每张字典一张卡，行数实时取自引擎状态。 */
  function renderCategory(panel, tab, ctx, category) {
    panel.textContent = "";
    panel.appendChild(el("h2", "dc-panel-title", category.title));
    panel.appendChild(el("p", "dc-panel-hint", category.desc));
    panel.appendChild(el("p", "dc-panel-hint",
      category.stage === 3
        ? "只读总览 · 四栏联动编辑随阶段三交付。"
        : "只读总览 · 表格编辑与删除防呆随阶段二交付。"));
    var loading = stateBox(panel, "正在读取真实行数…");
    window.DcClient.fetchJson("/api/bank/engine/status").then(function (status) {
      if (!panel.isConnected) return;
      loading.remove();
      var grid = el("div", "dc-card-grid");
      category.items.forEach(function (item) {
        grid.appendChild(dictCard(item, status.counts || {}));
      });
      panel.appendChild(grid);
    }).catch(function (error) {
      if (!panel.isConnected) return;
      loading.remove();
      errorBox(panel, error, function () { renderCategory(panel, tab, ctx, category); });
    });
  }

  window.DcPanels = { renderDashboard: renderDashboard, renderCategory: renderCategory };
})();