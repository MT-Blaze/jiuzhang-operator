/**
 * 实体维度双树共用的小工具（2026-11-11）：分页拉全量、增改删对话框、排序号。
 * 两棵树各自持有 DOM 与展开状态，这里只提供无状态函数，互不共享渲染。
 * 全部文案走 textContent；写请求经 DcClient.writeJson 自带一次性令牌。
 * 整块下架：删本文件、entity_schools.js、entity_textbooks.js 与 entities.css。
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

  /** 接口单页上限 200；按 total 继续翻页，把整张字典拉回前端再合树。 */
  function fetchAll(url, params) {
    var acc = [];
    function step(offset) {
      var query = new URLSearchParams();
      Object.keys(params || {}).forEach(function (key) {
        var value = params[key];
        if (value != null && value !== "") query.set(key, String(value));
      });
      query.set("limit", String(PAGE));
      query.set("offset", String(offset));
      var glue = url.indexOf("?") === -1 ? "?" : "&";
      return window.DcClient.fetchJson(url + glue + query.toString()).then(function (data) {
        var items = data.items || [];
        acc = acc.concat(items);
        var total = data.total || 0;
        if (items.length && acc.length < total) return step(offset + PAGE);
        return { items: acc, total: total };
      });
    }
    return step(0);
  }

  function listAll(table, params) {
    return fetchAll("/api/bank/engine/dict/" + table, params);
  }

  function nextOrder(rows, getter) {
    return (rows || []).reduce(function (max, row) {
      var value = Number(getter ? getter(row) : row.sort_order);
      if (!isFinite(value)) value = 0;
      return Math.max(max, value + 1);
    }, 1);
  }

  function fail(title, error, anchor) {
    window.DcDialog.alert({
      title: title,
      message: error && error.message ? error.message : String(error),
      anchor: anchor
    });
  }

  /** 删除复用公共防呆：被引用时后端 409，DcRowOps 弹引用清单。 */
  function remove(spec) {
    var controller = {
      url: spec.url,
      reload: function () { return spec.reload(); },
      setStatus: spec.setStatus || function () {}
    };
    window.DcRowOps.deleteRow(controller, spec.row, spec.anchor);
  }

  function rename(spec) {
    window.DcDialog.open({
      title: spec.title,
      message: spec.message || "",
      confirmText: "保存",
      anchor: spec.anchor,
      fields: spec.fields,
      onConfirm: function (values) {
        window.DcClient.writeJson(spec.url, values, "PUT").then(function () {
          spec.onDone();
        }).catch(function (error) { fail("保存失败", error, spec.anchor); });
      }
    });
  }

  function add(spec) {
    window.DcDialog.open({
      title: spec.title,
      message: spec.message || "",
      confirmText: "新增",
      anchor: spec.anchor,
      fields: spec.fields,
      onConfirm: function (values) {
        var payload;
        try {
          payload = spec.build(values);
        } catch (error) {
          fail(spec.title, error, spec.anchor);
          return;
        }
        window.DcClient.writeJson(spec.url, payload, "POST").then(function () {
          spec.onDone();
        }).catch(function (error) { fail("新增失败", error, spec.anchor); });
      }
    });
  }

  /** 节点行的折叠箭头；无子节点时占位，保证同层文字对齐。 */
  function caret(expanded, label, onClick) {
    var btn = el("button", "det-caret", expanded ? "\u25BE" : "\u25B8");
    btn.type = "button";
    btn.setAttribute("aria-expanded", expanded ? "true" : "false");
    btn.setAttribute("aria-label", (expanded ? "折叠 " : "展开 ") + label);
    btn.addEventListener("click", function (event) {
      event.stopPropagation();
      onClick();
    });
    return btn;
  }

  function spacer() {
    return el("span", "det-caret det-spacer", "");
  }

  function childList(depth, open) {
    var ul = el("ul", "det-children");
    ul.style.setProperty("--det-depth", String(depth));
    ul.hidden = !open;
    return ul;
  }

  /** 一行 = 箭头 + 名称/编码/面包屑 + 计数 + ＋/改名/删；子级容器随行挂在 li 上。 */
  function makeRow(opts) {
    var expandedSet = opts.expandedSet || new Set();
    var li = el("li", "det-item");
    li._detKey = opts.key || "";
    var row = el("div", "det-row");
    row.dataset.level = String(opts.level);
    row.style.setProperty("--det-depth", String(opts.depth || 0));
    if (opts.expanded) row.classList.add("is-open");

    function toggle() {
      var box = li._detBox;
      if (!box) return;
      var open = !box.hidden;
      if (li._detKey) {
        if (open) expandedSet.delete(li._detKey);
        else expandedSet.add(li._detKey);
      }
      if (!open && li._detLazy) {
        var build = li._detLazy;
        li._detLazy = null;
        build();
      }
      box.hidden = open;
      li._detCaret.textContent = open ? "\u25B8" : "\u25BE";
      li._detCaret.setAttribute("aria-expanded", open ? "false" : "true");
      row.classList.toggle("is-open", !open);
      if (!open) {
        box.classList.remove("det-reveal");
        void box.offsetWidth;
        box.classList.add("det-reveal");
      }
    }

    if (opts.hasChildren) {
      li._detCaret = caret(opts.expanded, opts.name, toggle);
      row.appendChild(li._detCaret);
    } else {
      row.appendChild(spacer());
    }

    var label = el("button", "det-label");
    label.type = "button";
    label.appendChild(el("span", "det-name", opts.name));
    if (opts.sub) label.appendChild(el("span", "det-sub", opts.sub));
    if (opts.tag) label.appendChild(el("span", "det-tag", opts.tag));
    label.appendChild(el("span", "det-crumb", opts.crumb || ""));
    label.addEventListener("click", function () {
      if (opts.hasChildren) toggle();
      else if (typeof opts.onSelect === "function") opts.onSelect(li);
    });
    if (opts.rename) label.addEventListener("dblclick", function () { opts.rename(label); });
    row.appendChild(label);

    if (opts.badge) row.appendChild(el("span", "det-badge", opts.badge));

    var ops = el("span", "det-ops");
    if (opts.add) {
      var addBtn = el("button", "det-op", "\uFF0B" + (opts.addText || ""));
      addBtn.type = "button";
      addBtn.setAttribute("aria-label", opts.addLabel || "新增");
      addBtn.addEventListener("click", function () { opts.add(addBtn); });
      ops.appendChild(addBtn);
    }
    if (opts.rename) {
      var renameBtn = el("button", "det-op", "改名");
      renameBtn.type = "button";
      renameBtn.setAttribute("aria-label", "修改「" + opts.name + "」的名称");
      renameBtn.addEventListener("click", function () { opts.rename(renameBtn); });
      ops.appendChild(renameBtn);
    }
    if (opts.remove) {
      var delBtn = el("button", "det-op det-op-danger", "删");
      delBtn.type = "button";
      delBtn.setAttribute("aria-label", "删除「" + opts.name + "」");
      delBtn.addEventListener("click", function () { opts.remove(delBtn); });
      ops.appendChild(delBtn);
    }
    row.appendChild(ops);
    li.appendChild(row);

    if (opts.children) {
      li._detBox = opts.children;
      li.appendChild(opts.children);
    }
    if (opts.lazy) {
      if (opts.expanded) opts.lazy();
      else li._detLazy = opts.lazy;
    }
    return li;
  }

  /** 把展开集合与选中回调预先绑定，模块里直接 makeRow(opts)。 */
  function bindTree(expandedSet, onSelect) {
    return function (opts) {
      var merged = {};
      Object.keys(opts).forEach(function (key) { merged[key] = opts[key]; });
      merged.expandedSet = expandedSet;
      merged.onSelect = onSelect;
      return makeRow(merged);
    };
  }

  window.DcEntityShared = {
    el: el, fetchAll: fetchAll, listAll: listAll, nextOrder: nextOrder,
    fail: fail, remove: remove, rename: rename, add: add,
    caret: caret, spacer: spacer, childList: childList,
    makeRow: makeRow, bindTree: bindTree
  };
})();
