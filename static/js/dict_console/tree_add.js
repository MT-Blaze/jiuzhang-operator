/**
 * 树形节点统一新增入口（2026-11-13）：行内不再挂「+」，新增入口只有两处——
 * 子节点列表最下方的一行低饱和「＋ 添加子节点」幽灵行，以及空状态的「＋ 添加」；
 * 点它不弹窗，直接在列表末尾长出一行输入框；Enter / 失焦保存，Esc 取消。
 * 编码字段不上界面：调用方用 timestampCode 生成 custom_* 给后端；
 * 排序由 nextOrder 取同级最大值 + 1，界面仍按 sort_order 渲染。
 * 本模块只提供无状态的界面件：幽灵行、空状态按钮、行内新增行、排序芯片与通用错误框。
 * 整块下架：删本文件、dict_console.html 引用行与各树的行内新增调用即可。
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /**
   * 列表末尾的幽灵行：整行即热区，视觉低饱和、悬停才提亮。
   * spec = {text, label, guide(), onClick(button)}
   */
  function ghostRow(spec) {
    var options = spec || {};
    var text = options.text || "添加子节点";
    var li = el("li", "dc-ghost-item");
    if (typeof options.guide === "function") li.appendChild(options.guide());
    var button = el("button", "dc-ghost-add", "\uFF0B " + text);
    button.type = "button";
    var label = options.label || text;
    button.setAttribute("aria-label", label);
    button.title = label;
    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      options.onClick(button);
    });
    li.appendChild(button);
    return li;
  }

  /** 空状态文案旁的行内按钮：文案固定「＋ 添加」，无障碍名说明加什么。 */
  function emptyAdd(spec) {
    var options = spec || {};
    var button = el("button", "node-empty-add", "\uFF0B 添加");
    button.type = "button";
    button.setAttribute("aria-label", options.label || "添加");
    button.title = options.label || "添加";
    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      options.onClick(button);
    });
    return button;
  }

  /** 同级最大 sort_order + 1；空表从 1 起，与旧弹窗口径一致。 */
  function nextOrder(rows, getter) {
    return (rows || []).reduce(function (max, row) {
      var raw = getter ? getter(row) : row && row.sort_order;
      var value = Number(raw);
      if (!isFinite(value) || value < 0) value = 0;
      return Math.max(max, value + 1);
    }, 1);
  }

  /** 前端直接签发编码：全局唯一，custom_ 前缀一眼看出是控制台手工新增。 */
  function timestampCode() {
    return "custom_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  }

  function fail(title, error, anchor) {
    window.DcDialog.alert({
      title: title,
      message: error && error.message ? error.message : String(error),
      anchor: anchor
    });
  }

  /**
   * 行内新增：host 里插一行输入框，不弹窗。
   * spec = {host, anchor, guide(), liClass, rowClass, inputClass, defaultValue,
   *         placeholder, label, url, payload(name), onSaved(created), onCancel,
   *         failTitle}
   * 同一个容器已有输入行时只聚焦，不重复长行。
   */
  function inlineAdd(spec) {
    if (!spec || !spec.host) throw new Error("缺少行内新增的挂载容器");
    var host = spec.host;
    var existing = host.querySelector(".dc-inline-row input");
    if (existing) {
      existing.focus();
      existing.select();
      return existing.parentNode;
    }
    var li = el("li", spec.liClass || "dc-inline-item");
    var row = el("div", spec.rowClass || "dc-inline-row");
    if (typeof spec.guide === "function") row.appendChild(spec.guide());
    var input = el("input", spec.inputClass || "dc-inline-input");
    input.type = "text";
    input.value = spec.defaultValue || "";
    input.placeholder = spec.placeholder || "输入名称";
    input.setAttribute("aria-label", spec.label || "新增名称");
    row.appendChild(input);
    li.appendChild(row);
    if (spec.before && spec.before.parentNode === host) host.insertBefore(li, spec.before);
    else host.appendChild(li);
    input.focus();
    input.select();

    var done = false;
    function finish(save) {
      if (done) return;
      var name = input.value.trim();
      if (!save || !name) {
        done = true;
        li.remove();
        if (spec.anchor && typeof spec.anchor.focus === "function") spec.anchor.focus();
        if (typeof spec.onCancel === "function") spec.onCancel();
        return;
      }
      var payload;
      try {
        payload = spec.payload(name);
      } catch (error) {
        fail(spec.failTitle || "还不能新增", error, input);
        return;
      }
      done = true;
      input.disabled = true;
      input.setAttribute("aria-busy", "true");
      window.DcClient.writeJson(spec.url, payload, "POST").then(function (created) {
        li.remove();
        if (typeof spec.onSaved === "function") spec.onSaved(created);
      }).catch(function (error) {
        done = false;
        input.disabled = false;
        input.setAttribute("aria-busy", "false");
        input.focus();
        input.select();
        fail(spec.failTitle || "新增失败", error, input);
      });
    }
    input.addEventListener("click", function (event) { event.stopPropagation(); });
    input.addEventListener("dblclick", function (event) { event.stopPropagation(); });
    input.addEventListener("blur", function () { finish(true); });
    input.addEventListener("keydown", function (event) {
      event.stopPropagation();
      if (event.key === "Enter") {
        event.preventDefault();
        input.blur();
      } else if (event.key === "Escape") {
        event.preventDefault();
        finish(false);
      }
    });
    return li;
  }

  /**
   * 排序芯片：平时显示「#排序号」，点一下变数字输入框；
   * Enter / 失焦调 spec.apply(value)，Esc 还原。apply 返回 Promise。
   */
  function sortChip(spec) {
    var button = el("button", spec.className || "dc-sort", "#" + spec.value);
    button.type = "button";
    var label = spec.label || "排序号";
    button.title = label + "：" + spec.value + "，点击修改";
    button.setAttribute("aria-label", label + "，当前 " + spec.value + "，点击修改");
    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      if (button.querySelector("input")) return;
      var input = document.createElement("input");
      input.type = "number";
      input.min = "0";
      input.step = "1";
      input.value = String(spec.value);
      input.className = "dc-sort-input";
      input.setAttribute("aria-label", label);
      button.textContent = "";
      button.appendChild(input);
      input.focus();
      input.select();

      var busy = false;
      function restore() {
        button.textContent = "#" + spec.value;
        button.removeAttribute("aria-busy");
      }
      function finish(save) {
        if (busy) return;
        var raw = input.value.trim();
        if (!save || raw === "") {
          restore();
          return;
        }
        var value = Number(raw);
        if (!isFinite(value) || Math.floor(value) !== value || value < 0) {
          fail("排序号无效", new Error("排序号必须是 0 或正整数"), input);
          input.focus();
          input.select();
          return;
        }
        if (value === Number(spec.value)) {
          restore();
          return;
        }
        busy = true;
        input.disabled = true;
        button.setAttribute("aria-busy", "true");
        Promise.resolve(spec.apply(value)).then(function () {
          spec.value = value;
          restore();
        }).catch(function (error) {
          busy = false;
          input.disabled = false;
          restore();
          fail(spec.failTitle || "排序保存失败", error, button);
        });
      }
      input.addEventListener("click", function (click) { click.stopPropagation(); });
      input.addEventListener("blur", function () { finish(true); });
      input.addEventListener("keydown", function (keyEvent) {
        keyEvent.stopPropagation();
        if (keyEvent.key === "Enter") {
          keyEvent.preventDefault();
          input.blur();
        } else if (keyEvent.key === "Escape") {
          keyEvent.preventDefault();
          finish(false);
          button.focus();
        }
      });
    });
    return button;
  }

  window.DcTreeAdd = {
    ghostRow: ghostRow, emptyAdd: emptyAdd, nextOrder: nextOrder,
    timestampCode: timestampCode, fail: fail, inlineAdd: inlineAdd, sortChip: sortChip
  };
})();
