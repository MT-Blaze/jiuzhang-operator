/**
 * 字典表格（阶段二）：分类页签里每张表一个表格块。
 * 搜索框 + 全局设置三参数（DcGlobals.query()）真正带进查询；
 * 字典体量很小，一次拉全量后直接铺开，不再有分页器。
 * 全局设置变化或搜索输入即刷新。行内交互（编辑/新增/删除）交给 DcRowOps。
 * 本地私有系统：所有字典一律可增删改，表格不再有只读态。
 * 整块下架：删本目录与 panels.js 的 DcTable.mount 调用即可。
 */
(function () {
  "use strict";

  var PAGE = 200;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function buildUrl(controller, offset) {
    var params = new URLSearchParams();
    if (controller.keyword) params.set("q", controller.keyword);
    params.set("limit", String(PAGE));
    params.set("offset", String(offset || 0));
    var globals = controller.ctx.globals.query();
    Object.keys(globals).forEach(function (key) { params.set(key, String(globals[key])); });
    return controller.url + "?" + params.toString();
  }

  function renderHead(controller) {
    var tr = document.createElement("tr");
    controller.fields.forEach(function (field) {
      var th = el("th", "", field.label);
      th.scope = "col";
      tr.appendChild(th);
    });
    tr.appendChild(el("th", "dc-th-action", "操作"));
    controller.els.thead.textContent = "";
    controller.els.thead.appendChild(tr);
  }

  function renderRows(controller) {
    var tbody = controller.els.tbody;
    tbody.textContent = "";
    if (!controller.rows.length) {
      var empty = document.createElement("tr");
      var td = el("td", "dc-table-empty", "无匹配数据");
      td.colSpan = controller.fields.length + 1;
      empty.appendChild(td);
      tbody.appendChild(empty);
      return;
    }
    controller.rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.setAttribute("data-id", String(row.id));
      controller.fields.forEach(function (field) {
        var editable = !!field.editable;
        var td = el("td", editable ? "dc-cell-editable" : "dc-cell-id",
          row[field.key] == null ? "" : String(row[field.key]));
        td.setAttribute("data-col", field.key);
        if (editable) {
          td.tabIndex = 0;
          td.setAttribute("aria-label", "编辑" + field.label + "（双击或按 Enter）");
          td.addEventListener("dblclick", function () {
            window.DcRowOps.editCell(controller, td, row, field);
          });
          td.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === "F2") {
              event.preventDefault();
              window.DcRowOps.editCell(controller, td, row, field);
            }
          });
        }
        tr.appendChild(td);
      });
      var action = document.createElement("td");
      var del = el("button", "dc-btn dc-row-btn dc-row-delete", "删除");
      del.type = "button";
      del.setAttribute("aria-label", "删除 " + (row.name || row.code || row.id));
      del.addEventListener("click", function () {
        window.DcRowOps.deleteRow(controller, row, del);
      });
      action.appendChild(del);
      tr.appendChild(action);
      tbody.appendChild(tr);
    });
  }

  /** 接口单页上限 200；按 total 继续翻页，把整张字典一次性拉回前端铺开。 */
  function fetchAll(controller) {
    var acc = [];
    function step(offset) {
      return window.DcClient.fetchJson(buildUrl(controller, offset)).then(function (data) {
        var items = data.items || [];
        acc = acc.concat(items);
        var total = data.total || 0;
        if (items.length && acc.length < total) return step(offset + PAGE);
        return { items: acc, total: total, fields: data.fields || [] };
      });
    }
    return step(0);
  }

  function fetchRows(controller) {
    controller.setStatus("正在读取…");
    return fetchAll(controller).then(function (data) {
      if (!controller.section.isConnected) return;
      controller.fields = data.fields.length ? data.fields : controller.fields;
      controller.rows = data.items;
      controller.total = data.total;
      renderHead(controller);
      renderRows(controller);
      controller.els.count.textContent = "共 " + controller.total + " 行";
      controller.setStatus("");
    }).catch(function (error) {
      if (!controller.section.isConnected) return;
      controller.setStatus("加载失败：" + error.message);
    });
  }

  function mount(panel, item, ctx) {
    if (item.table === "dim_regions" && window.DcRegionsTree) {
      return window.DcRegionsTree.mount(panel, item, ctx);
    }
    var section = el("section", "dc-table-block");
    section.setAttribute("data-table", item.table);
    section.setAttribute("aria-label", item.name + "字典表");

    var tools = el("div", "dc-table-tools");
    var search = document.createElement("input");
    search.type = "search";
    search.className = "dc-table-search";
    search.placeholder = "搜索名称 / 编码…";
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
      section: section,
      els: { search: search, add: add, count: count, thead: thead, tbody: tbody, state: state },
      setStatus: function (text) { state.textContent = text; },
      reload: function () { return fetchRows(controller); }
    };

    var timer = null;
    search.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        controller.keyword = search.value.trim();
        controller.reload();
      }, 250);
    });
    add.addEventListener("click", function () { window.DcRowOps.addRow(controller); });

    function onGlobals() {
      if (!section.isConnected) {
        document.removeEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
        return;
      }
      controller.reload();
    }
    document.addEventListener(window.DcGlobals.EVENT_NAME, onGlobals);

    controller.reload();
    return controller;
  }

  window.DcTable = { mount: mount };
})();