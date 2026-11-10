/**
 * 画布面板渲染：数据看板 + 三大分类面板。
 * 所有数字来自 /api/bank/engine/status 的真实计数，不写死、不占位。
 * 阶段二：分类里 marked editable 的基础五表升级为可编辑表格（DcTable），
 * 其余字典仍为只读总览卡，编辑能力随阶段三交付，面板上如实标注。
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

  /** 分类面板：教研属性顶部挂四栏联动；可编辑表渲染表格块，其余只读总览卡。 */
  function renderCategory(panel, tab, ctx, category) {
    panel.textContent = "";
    panel.appendChild(el("h2", "dc-panel-title", category.title));
    panel.appendChild(el("p", "dc-panel-hint", category.desc));
    var linkageMounted = false;
    if (category.key === "teaching" && window.DcLinkage) {
      window.DcLinkage.mount(panel, ctx);
      linkageMounted = true;
    }
    var editable = category.items.filter(function (item) { return item.editable; });
    var pending = category.items.filter(function (item) {
      return !item.editable && !(linkageMounted && item.linkage);
    });

    if (editable.length) {
      panel.appendChild(el("p", "dc-panel-hint",
        "双击单元格改名（blur 保存，Esc 放弃）· 新增行 · 删除自动防呆 · 搜索与全局设置联动。"));
      editable.forEach(function (item) { window.DcTable.mount(panel, item, ctx); });
    }

    if (pending.length) {
      panel.appendChild(el("h3", "dc-panel-title", "待交付字典"));
      panel.appendChild(el("p", "dc-panel-hint", "以下字典暂为只读总览。"));
      var loading = stateBox(panel, "正在读取真实行数…");
      window.DcClient.fetchJson("/api/bank/engine/status").then(function (status) {
        if (!panel.isConnected) return;
        loading.remove();
        var grid = el("div", "dc-card-grid");
        pending.forEach(function (item) { grid.appendChild(dictCard(item, status.counts || {})); });
        panel.appendChild(grid);
      }).catch(function (error) {
        if (!panel.isConnected) return;
        loading.remove();
        errorBox(panel, error, function () { renderCategory(panel, tab, ctx, category); });
      });
    }
  }

  window.DcPanels = { renderDashboard: renderDashboard, renderCategory: renderCategory };
})();