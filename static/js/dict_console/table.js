/**
 * 字典表格（阶段二）：分类页签里每张可编辑表一个表格块。
 * 搜索框 + 分页 + 全局设置三参数（DcGlobals.query()）真正带进查询；
 * 全局设置变化或搜索输入即刷新。行内交互（编辑/新增/删除）交给 DcRowOps。
 * 整块下架：删本目录与 panels.js 的 DcTable.mount 调用即可。
 */
(function () {
  "use strict";

  var PAGE_SIZE = 50;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function buildUrl(controller) {
    var params = new URLSearchParams();
    if (controller.keyword) params.set("q", controller.keyword);
    params.set("limit", String(controller.limit));
    params.set("offset", String(controller.offset));
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
    if (!controller.readOnly) tr.appendChild(el("th", "dc-th-action", "操作"));
    controller.els.thead.textContent = "";
    controller.els.thead.appendChild(tr);
  }

  function renderRows(controller) {
    var tbody = controller.els.tbody;
    tbody.textContent = "";
    if (!controller.rows.length) {
      var empty = document.createElement("tr");
      var td = el("td", "dc-table-empty", "无匹配数据");
      td.colSpan = controller.fields.length + (controller.readOnly ? 0 : 1);
      empty.appendChild(td);
      tbody.appendChild(empty);
      return;
    }
    controller.rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.setAttribute("data-id", String(row.id));
      controller.fields.forEach(function (field) {
        var editable = field.editable && !controller.readOnly;
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
      if (!controller.readOnly) {
        var action = document.createElement("td");
        var del = el("button", "dc-btn dc-row-btn dc-row-delete", "删除");
        del.type = "button";
        del.setAttribute("aria-label", "删除 " + (row.name || row.code || row.id));
        del.addEventListener("click", function () {
          window.DcRowOps.deleteRow(controller, row, del);
        });
        action.appendChild(del);
        tr.appendChild(action);
      }
      tbody.appendChild(tr);
    });
  }

  function renderPager(controller) {
    var pages = Math.max(1, Math.ceil(controller.total / controller.limit));
    var page = Math.floor(controller.offset / controller.limit) + 1;
    controller.els.count.textContent = "共 " + controller.total + " 行";
    controller.els.pageinfo.textContent = "第 " + page + " / " + pages + " 页";
    controller.els.prev.disabled = controller.offset <= 0;
    controller.els.next.disabled = controller.offset + controller.limit >= controller.total;
  }

  function fetchRows(controller) {
    controller.setStatus("正在读取…");
    return window.DcClient.fetchJson(buildUrl(controller)).then(function (data) {
      if (!controller.section.isConnected) return;
      controller.fields = data.fields || [];
      controller.rows = data.items || [];
      controller.total = data.total || 0;
      renderHead(controller);
      renderRows(controller);
      renderPager(controller);
      controller.setStatus("");
    }).catch(function (error) {
      if (!controller.section.isConnected) return;
      controller.setStatus("加载失败：" + error.message);
    });
  }

  function mount(panel, item, ctx, options) {
    var readOnly = !!(options && options.readOnly);
    var section = el("section", "dc-table-block");
    section.setAttribute("data-table", item.table);
    section.setAttribute("aria-label", item.name + "字典表");

    var head = el("div", "dc-table-head");
    var title = el("h3", "dc-table-name", item.name);
    title.appendChild(el("span", "dc-card-table", " " + item.table));
    head.appendChild(title);
    head.appendChild(el("p", "dc-table-desc", item.desc));
    section.appendChild(head);

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
    if (readOnly) {
      tools.appendChild(el("span", "dc-table-readonly", "只读"));
    } else {
      tools.appendChild(add);
    }
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

    var pager = el("div", "dc-table-pager");
    var prev = el("button", "dc-btn dc-table-prev", "上一页");
    prev.type = "button";
    var pageinfo = el("span", "dc-table-pageinfo", "");
    var next = el("button", "dc-btn dc-table-next", "下一页");
    next.type = "button";
    pager.appendChild(prev);
    pager.appendChild(pageinfo);
    pager.appendChild(next);
    section.appendChild(pager);

    var state = el("p", "dc-table-state", "");
    state.setAttribute("role", "status");
    state.setAttribute("aria-live", "polite");
    section.appendChild(state);
    panel.appendChild(section);

    var controller = {
      table: item.table, url: "/api/bank/engine/dict/" + item.table, ctx: ctx,
      fields: [], rows: [], total: 0, limit: PAGE_SIZE, offset: 0, keyword: "",
      readOnly: readOnly,
      section: section,
      els: { search: search, add: add, count: count, thead: thead, tbody: tbody,
             prev: prev, next: next, pageinfo: pageinfo, state: state },
      setStatus: function (text) { state.textContent = text; },
      reload: function (resetOffset) {
        if (resetOffset) controller.offset = 0;
        return fetchRows(controller);
      }
    };

    var timer = null;
    search.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        controller.keyword = search.value.trim();
        controller.reload(true);
      }, 250);
    });
    add.addEventListener("click", function () { window.DcRowOps.addRow(controller); });
    prev.addEventListener("click", function () {
      controller.offset = Math.max(0, controller.offset - controller.limit);
      controller.reload(false);
    });
    next.addEventListener("click", function () {
      controller.offset += controller.limit;
      controller.reload(false);
    });

    function onGlobals() {
      if (!section.isConnected) {
        document.removeEventListener(window.DcGlobals.EVENT_NAME, onGlobals);
        return;
      }
      controller.reload(true);
    }
    document.addEventListener(window.DcGlobals.EVENT_NAME, onGlobals);

    controller.reload(true);
    return controller;
  }

  window.DcTable = { mount: mount };
})();