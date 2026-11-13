/**
 * 树形节点统一新增入口（2026-11-13）：所有层级只露一个「+」，
 * 按钮文案不再写「新增知识点 / 新增考向」，具体加什么由所在树层决定。
 * 本模块只提供无状态的界面件与通用弹窗：+ 按钮、空状态「＋ 添加」按钮、
 * 名称 / 排序字段与整数排序校验；请求地址与载荷由各树自己拼。
 * 整块下架：删本文件、dict_console.html 引用行与两处树的 + 调用即可。
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /** 行尾统一「+」：视觉 28×28，热区由行高撑到 44px；触屏不靠 hover。 */
  function plus(spec) {
    var options = spec || {};
    var label = options.label || "新增子节点";
    var button = el("button", "node-add", "+");
    button.type = "button";
    button.setAttribute("aria-label", label);
    button.title = label;
    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      options.onClick(button);
    });
    return button;
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

  function sortField(value) {
    return {
      key: "sort_order", label: "排序号",
      value: value == null ? "" : String(value),
      placeholder: "0 起，数字越小越靠前"
    };
  }

  /** 空值取兜底；非整数 / 负数直接拒绝，避免把脏排序写进库。 */
  function sortValue(value, fallback) {
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

  /**
   * 统一新增弹窗：spec = {title, message, anchor, fields, build, url, onDone, failTitle}。
   * build 抛错时留在弹窗内提示，不把半截载荷发出去。
   */
  function open(spec) {
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
        window.DcClient.writeJson(spec.url, payload, "POST").then(function (created) {
          if (typeof spec.onDone === "function") spec.onDone(created);
        }).catch(function (error) {
          fail(spec.failTitle || "新增失败", error, spec.anchor);
        });
      }
    });
  }

  window.DcTreeAdd = {
    plus: plus, emptyAdd: emptyAdd, sortField: sortField, sortValue: sortValue,
    fail: fail, open: open
  };
})();
