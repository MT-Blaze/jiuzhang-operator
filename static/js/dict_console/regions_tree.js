/**
 * 行政区划树形折叠表格（2026-11-11）：只接管 dim_regions，其它表仍走 DcTable。
 * 默认只渲染 34 个省级；点 ▶ 展开该省地级市，再点收起。搜索时平铺命中行并标注父省。
 * 全量 367 行一次拉回本地按 parent_id 分组，展隐由 dataset.parent 控制。
 * 编辑 / 删除 / 新增复用 DcRowOps，交互口径与普通字典表一致。
 * 整块下架：删本文件、dict_console_regions.css、table.js 里的 DcRegionsTree 分支。
 */
(function () {
  "use strict";

  var PAGE = 200;
  var OPEN = "\u25BC";
  var CLOSED = "\u25B6";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /** 分页拉全量：接口单页上限 200，367 行需要 2 次。 */
  function fetchAll(controller, keyword) {
    var acc = [];
    function step(offset) {
      var params = new URLSearchParams();
      if (keyword) params.set("q", keyword);
      params.set("limit", String(PAGE));
      params.set("offset", String(offset));
      var globals = controller.ctx.globals.query();
      Object.keys(globals).forEach(function (key) { params.set(key, String(globals[key])); });
      return window.DcClient.fetchJson(controller.url + "?" + params.toString()).then(function (data) {
        var items = data.items || [];
        acc = acc.concat(items);
        var total = data.total || 0;
        if (items.length && acc.length < total) return step(offset + PAGE);
        return { items: acc, total: total, fields: data.fields || [] };
      });
    }
    return step(0);
  }

  function cell(controller, row, field) {
    var editable = !!field.editable;
    var td = el("td", editable ? "dc-cell-editable" : "dc-cell-id",
      row[field.key] == null ? "" : String(row[field.key]));
    td.setAttribute("data-col", field.key);
    if (!editable) return td;
    td.tabIndex = 0;
    td.setAttribute("aria-label", "编辑" + field.label + "（双击或按 Enter）");
    td.addEventListener("dblclick", function () {
      window.DcRowOps.editCell(controller, td, row, field);
    });
    td.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        window.DcRowOps.editCell(controller, td, row, field);
      }
    });
    return td;
  }

  /** 展开 / 折叠：只翻 dataset.parent 命中的市行，不重建整表。 */
  function setExpanded(controller, province, open) {
    if (open) controller.expanded.add(province.id);
    else controller.expanded.delete(province.id);
    var label = (province.name || ("#" + province.id));
    var btn = controller.els.tbody.querySelector(
      '.dc-tree-toggle[data-province="' + province.id + '"]');
    if (btn) {
      btn.textContent = open ? OPEN : CLOSED;
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.setAttribute("aria-label", (open ? "折叠 " : "展开 ") + label);
    }
    var rows = controller.els.tbody.querySelectorAll('tr[data-parent="' + province.id + '"]');
    Array.prototype.forEach.call(rows, function (tr) {
      tr.hidden = !open;
      if (open) {
        tr.classList.remove("dc-row-reveal");
        void tr.offsetWidth;
        tr.classList.add("dc-row-reveal");
      }
    });
  }

  function makeRow(controller, row, opts) {
    var tr = document.createElement("tr");
    tr.setAttribute("data-id", String(row.id));
    tr.dataset.level = String(row.level);
    tr.dataset.parent = row.parent_id == null ? "" : String(row.parent_id);
    tr.className = opts.flat ? "dc-row-flat" : (row.level === 1 ? "dc-row-province" : "dc-row-city");

    var lead = el("td", "dc-tree-lead");
    if (opts.flat) {
      if (opts.parentName) lead.appendChild(el("span", "dc-tree-parent", opts.parentName));
    } else if (row.level === 1) {
      if (opts.childCount) {
        var btn = el("button", "dc-tree-toggle",
          controller.expanded.has(row.id) ? OPEN : CLOSED);
        btn.type = "button";
        btn.dataset.province = String(row.id);
        btn.setAttribute("aria-expanded", controller.expanded.has(row.id) ? "true" : "false");
        btn.setAttribute("aria-label",
          (controller.expanded.has(row.id) ? "折叠 " : "展开 ") + (row.name || row.id));
        btn.addEventListener("click", function (event) {
          event.stopPropagation();
          setExpanded(controller, row, !controller.expanded.has(row.id));
        });
        lead.appendChild(btn);
      } else {
        lead.appendChild(el("span", "dc-tree-dot", "\u00B7"));
      }
    } else {
      lead.appendChild(el("span", "dc-tree-branch", "\u21B3"));
    }
    tr.appendChild(lead);

    controller.fields.forEach(function (field) { tr.appendChild(cell(controller, row, field)); });

    var action = document.createElement("td");
    var del = el("button", "dc-btn dc-row-btn dc-row-delete", "删除");
    del.type = "button";
    del.setAttribute("aria-label", "删除 " + (row.name || row.code || row.id));
    del.addEventListener("click", function () {
      window.DcRowOps.deleteRow(controller, row, del);
    });
    action.appendChild(del);
    tr.appendChild(action);

    if (!opts.flat && row.level === 2 && !controller.expanded.has(row.parent_id)) {
      tr.hidden = true;
    }
    return tr;
  }

  function updateCount(controller) {
    var provinces = controller.rows.filter(function (row) { return row.level === 1; });
    var cities = controller.rows.filter(function (row) { return row.level === 2; });
    controller.els.count.textContent = controller.keyword
      ? "共 " + controller.total + " 行"
      : "共 " + controller.total + " 行 · 省级 " + provinces.length + " / 地级市 " + cities.length;
  }

  function render(controller) {
    var tbody = controller.els.tbody;
    tbody.textContent = "";
    var flat = !!controller.keyword;
    if (!controller.rows.length) {
      var empty = document.createElement("tr");
      var td = el("td", "dc-table-empty", "无匹配数据");
      td.colSpan = controller.fields.length + 2;
      empty.appendChild(td);
      tbody.appendChild(empty);
      updateCount(controller);
      return;
    }
    if (flat) {
      controller.rows.forEach(function (row) {
        var parentName = row.level === 2 ? controller.provinceNames[row.parent_id] || "" : "";
        tbody.appendChild(makeRow(controller, row, { flat: true, parentName: parentName }));
      });
      updateCount(controller);
      return;
    }
    var groups = {};
    var provinces = [];
    controller.rows.forEach(function (row) {
      if (row.level === 1) {
        provinces.push(row);
        return;
      }
      (groups[row.parent_id] = groups[row.parent_id] || []).push(row);
    });
    provinces.forEach(function (province) {
      var kids = groups[province.id] || [];
      tbody.appendChild(makeRow(controller, province, { childCount: kids.length }));
      kids.forEach(function (city) { tbody.appendChild(makeRow(controller, city, {})); });
    });
    updateCount(controller);
  }

  function renderHead(controller) {
    var tr = document.createElement("tr");
    var lead = el("th", "dc-tree-lead", "");
    lead.scope = "col";
    tr.appendChild(lead);
    controller.fields.forEach(function (field) {
      var th = el("th", "", field.label);
      th.scope = "col";
      tr.appendChild(th);
    });
    tr.appendChild(el("th", "dc-th-action", "操作"));
    controller.els.thead.textContent = "";
    controller.els.thead.appendChild(tr);
  }

  function reload(controller) {
    controller.setStatus("正在读取…");
    var known = {};
    controller.rows.forEach(function (row) { known[row.id] = true; });
    var knownCount = Object.keys(known).length;
    var prevFlat = !!controller.lastFlat;
    var seq = (controller.seq || 0) + 1;
    controller.seq = seq;
    return fetchAll(controller, controller.keyword).then(function (data) {
      if (!controller.section.isConnected || seq !== controller.seq) return;
      controller.rows = data.items;
      controller.total = data.total;
      if (data.fields.length) controller.fields = data.fields;
      if (!controller.keyword) {
        controller.provinceNames = {};
        controller.rows.forEach(function (row) {
          if (row.level === 1) controller.provinceNames[row.id] = row.name;
        });
        // 只有树形状态下增量新增（如新增一行）才自动展开父级；
        // 首屏、全局设置二次触发、搜索清空后的整表刷新都不算增量。
        var fresh = controller.rows.filter(function (row) { return !known[row.id]; });
        if (controller.loaded && !prevFlat && knownCount && fresh.length <= 5) {
          fresh.forEach(function (row) {
            if (row.parent_id) controller.expanded.add(row.parent_id);
          });
        }
        controller.loaded = true;
      }
      controller.lastFlat = !!controller.keyword;
      renderHead(controller);
      render(controller);
      controller.setStatus("");
    }).catch(function (error) {
      if (!controller.section.isConnected || seq !== controller.seq) return;
      controller.setStatus("加载失败：" + error.message);
    });
  }

  function mount(panel, item, ctx) {
    var section = el("section", "dc-table-block dc-regions-tree");
    section.setAttribute("data-table", item.table);
    section.setAttribute("aria-label", item.name + "字典表");

    var tools = el("div", "dc-table-tools");
    var search = document.createElement("input");
    search.type = "search";
    search.className = "dc-table-search";
    search.placeholder = "搜索名称 / 编码…（例如：哈尔滨）";
    search.setAttribute("aria-label", "搜索" + item.name);
    var add = el("button", "dc-btn dc-table-add", "新增行");
    add.type = "button";
    var count = el("span", "dc-table-count", "");
    count.setAttribute("role", "status");
    tools.appendChild(search);
    tools.appendChild(add);
    tools.appendChild(count);
    section.appendChild(tools);

    var scroll = el("div", "dc-table-scroll");
    var table = el("table", "dc-table");
    var thead = document.createElement("thead");
    var tbody = document.createElement("tbody");
    table.appendChild(thead);
    table.appendChild(tbody);
    scroll.appendChild(table);
    section.appendChild(scroll);

    var state = el("p", "dc-table-state", "");
    state.setAttribute("role", "status");
    state.setAttribute("aria-live", "polite");
    section.appendChild(state);
    panel.appendChild(section);

    var controller = {
      table: item.table, url: "/api/bank/engine/dict/" + item.table, ctx: ctx,
      fields: [], rows: [], total: 0, keyword: "",
      expanded: new Set(), provinceNames: {}, loaded: false,
      section: section,
      els: { search: search, add: add, count: count, thead: thead, tbody: tbody, state: state },
      setStatus: function (text) { state.textContent = text; },
      reload: function () { return reload(controller); }
    };

    reload(controller);

    var timer = null;
    search.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        controller.keyword = search.value.trim();
        reload(controller);
      }, 250);
    });
    add.addEventListener("click", function () {
      window.DcRowOps.addRow(controller);
      var fresh = controller.els.tbody.querySelector("tr.dc-row-new");
      if (fresh && !fresh.querySelector(".dc-tree-lead")) {
        var lead = el("td", "dc-tree-lead");
        fresh.insertBefore(lead, fresh.firstChild);
      }
    });

    function onGlobals() {
      if (!section.isConnected) {
        document.removeEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
        return;
      }
      reload(controller);
    }
    document.addEventListener(window.DcGlobals.EVENT_NAME, onGlobals);

    return controller;
  }

  window.DcRegionsTree = { mount: mount };
})();
