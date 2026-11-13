/**
 * 实体维度双树共用的小工具（2026-11-11）：分页拉全量、新增/删除对话框、内联改名、排序号。
 * 改名一律双击节点文字出输入框（blur/Enter 保存、Esc 取消），不设“改名”按钮；
 * 单击 / 双击由 bindNodeClick 统一分流：单击延迟 200ms 再落展开，双击撤销并直接改名。
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

  /** 空值取兜底；非整数 / 负数直接拒绝，避免把脏排序写进库。 */
  function orderValue(value, fallback) {
    if (value == null || String(value).trim() === "") return fallback;
    var number = Number(value);
    if (!isFinite(number) || Math.floor(number) !== number || number < 0) {
      throw new Error("排序号必须是 0 或正整数");
    }
    return number;
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

  /** 双击节点文字 → 原地输入框：blur/Enter 保存，Esc 还原；空值视同取消，不写库。 */
  function inlineEdit(spec) {
    var host = spec.host;
    if (!host || host.querySelector("input")) return;
    var original = spec.value == null ? "" : String(spec.value);
    var input = document.createElement("input");
    input.type = "text";
    input.className = "det-inline-input";
    input.value = original;
    input.setAttribute("aria-label", spec.label || "修改名称");
    host.textContent = "";
    host.appendChild(input);
    input.focus();
    input.select();
    var done = false;
    function finish(save) {
      if (done) return;
      done = true;
      var value = input.value.trim();
      if (!save || !value || value === original) {
        host.textContent = original;
        if (spec.restoreFocus) spec.restoreFocus.focus();
        return;
      }
      var payload = {};
      payload[spec.field] = value;
      window.DcClient.writeJson(spec.url, payload, "PUT").then(function () {
        host.textContent = value;
        spec.onDone(value);
      }).catch(function (error) {
        host.textContent = original;
        fail("保存失败", error, spec.restoreFocus || host);
      });
    }
    input.addEventListener("click", function (event) { event.stopPropagation(); });
    input.addEventListener("dblclick", function (event) { event.stopPropagation(); });
    input.addEventListener("blur", function () { finish(true); });
    input.addEventListener("keydown", function (event) {
      event.stopPropagation();
      if (event.key === "Enter") { event.preventDefault(); input.blur(); }
      else if (event.key === "Escape") { event.preventDefault(); finish(false); }
    });
  }

  /**
   * 单击 / 双击分流（知识点树与实体树共用同一套手感）：
   * 单击先挂 200ms 定时器，到点才执行 toggle；双击清掉定时器并直接 edit。
   * 慢双击时第一次点击可能已经落地展开，双击回调先补一次 toggle 把它撤回来。
   */
  function bindNodeClick(button, spec) {
    var timer = null;
    var fired = false;
    function clear() {
      if (timer) {
        window.clearTimeout(timer);
        timer = null;
      }
    }
    function toggle() {
      if (typeof spec.toggle === "function") spec.toggle();
    }
    button.addEventListener("click", function (event) {
      if (event.detail > 1) { clear(); return; }
      if (!timer) fired = false;
      clear();
      timer = window.setTimeout(function () {
        timer = null;
        fired = true;
        toggle();
      }, 200);
    });
    if (typeof spec.edit === "function") {
      button.addEventListener("dblclick", function (event) {
        event.preventDefault();
        clear();
        if (fired) {
          fired = false;
          toggle();
        }
        spec.edit();
      });
    }
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

  /** 一行 = 箭头 + 名称（学校行拆全称/简称两栏）+ 计数 + +/删；子级容器挂在 li 上。 */
  function makeRow(opts) {
    var expandedSet = opts.expandedSet || new Set();
    var li = el("li", "det-item");
    li._detKey = opts.key || "";
    var row = el("div", "det-row");
    row.dataset.level = String(opts.level);
    row.style.setProperty("--det-depth", String(opts.depth || 0));
    if (opts.expanded) row.classList.add("is-open");
    var isSchool = opts.short != null;
    if (isSchool) row.classList.add("det-row-school");

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

    var nameSpan = el("span", "det-name", opts.name);
    var label = el("button", "det-label");
    label.type = "button";
    label.appendChild(nameSpan);
    var shortBtn = null;
    var shortSpan = null;
    if (isSchool) {
      shortSpan = el("span", "det-short", opts.short);
      shortBtn = el("button", "det-label det-short-cell");
      shortBtn.type = "button";
      shortBtn.appendChild(shortSpan);
    } else {
      if (opts.sub) label.appendChild(el("span", "det-sub", opts.sub));
      if (opts.tag) label.appendChild(el("span", "det-tag", opts.tag));
    }
    var crumb = el("span", "det-crumb", opts.crumb || "");
    if (!isSchool) label.appendChild(crumb);

    function activate() {
      if (opts.hasChildren) toggle();
      else if (typeof opts.onSelect === "function") opts.onSelect(li);
    }

    function wireEdit(btn, span, editSpec) {
      if (!editSpec) return null;
      btn.title = "双击修改" + (editSpec.label || "名称");
      return function start() {
        inlineEdit({
          host: span, value: editSpec.value, label: editSpec.label,
          url: editSpec.url, field: editSpec.field,
          onDone: editSpec.onDone, restoreFocus: btn
        });
      };
    }
    bindNodeClick(label, {
      toggle: activate,
      edit: wireEdit(label, nameSpan, opts.edit)
    });
    if (shortBtn) {
      bindNodeClick(shortBtn, {
        toggle: activate,
        edit: wireEdit(shortBtn, shortSpan, opts.editShort)
      });
    }

    row.appendChild(label);
    if (shortBtn) row.appendChild(shortBtn);
    if (isSchool) row.appendChild(crumb);

    if (opts.badge) row.appendChild(el("span", "det-badge", opts.badge));

    var ops = el("span", "det-ops");
    if (opts.add) {
      var addBtn = el("button", "det-op det-op-add", "+");
      addBtn.type = "button";
      addBtn.setAttribute("aria-label", opts.addLabel || "新增");
      addBtn.addEventListener("click", function () { opts.add(addBtn); });
      ops.appendChild(addBtn);
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
    el: el, fetchAll: fetchAll, listAll: listAll, nextOrder: nextOrder, orderValue: orderValue,
    fail: fail, remove: remove, inlineEdit: inlineEdit, add: add,
    bindNodeClick: bindNodeClick,
    caret: caret, spacer: spacer, childList: childList,
    makeRow: makeRow, bindTree: bindTree
  };
})();
