/**
 * 教材章节的新增 / 改名 / 删除（2026-11-11 解除只读）。
 * 走 /api/bank/engine/dict/dim_textbook_chapters 同一套字典写口；
 * 删除被题目/考向等引用时后端回 409，这里弹「已被引用，无法删除」。
 * 整块下架：删本文件、dict_console.html 的引用行与 chapters.js 的 DcChapterOps 调用。
 */
(function () {
  "use strict";

  var URL = "/api/bank/engine/dict/dim_textbook_chapters";

  function nextOrder(siblings) {
    return (siblings || []).reduce(function (max, node) {
      var order = node && node.chapter ? Number(node.chapter.sort_order) || 0 : 0;
      return Math.max(max, order + 1);
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

  function alertError(title, error, anchor) {
    window.DcDialog.alert({ title: title, message: error.message, anchor: anchor });
  }

  function failDelete(error, chapter, anchor) {
    if (error.status === 409 && error.detail && error.detail.code === "referenced") {
      window.DcDialog.alert({
        title: "已被引用，无法删除",
        message: window.DcRowOps.referenceMessage(error, chapter),
        anchor: anchor
      });
      return;
    }
    alertError("删除失败", error, anchor);
  }

  /** parent 为空 = 给册次加顶层章；否则在该章下加子节点。 */
  function add(parent, siblings, textbookId, onDone) {
    var under = parent ? "在「" + parent.name + "」下" : "给本册";
    var next = nextOrder(siblings);
    window.DcDialog.open({
      title: under + "新增章节",
      message: "名称与编码都要填；编码全局唯一，可填章节号（如 1.2）。",
      confirmText: "新增",
      fields: [
        { key: "name", label: "章节名称", required: true, placeholder: "如 函数的概念" },
        { key: "code", label: "章节编码", required: true, placeholder: "如 1.2" },
        { key: "sort_order", label: "排序号", value: String(next), placeholder: "0 起，数字越小越靠前" }
      ],
      onConfirm: function (values) {
        var payload;
        try {
          payload = {
            name: values.name, code: values.code,
            textbook_id: parent ? parent.textbook_id : textbookId,
            sort_order: orderValue(values.sort_order, next)
          };
        } catch (error) {
          alertError("还不能新增", error);
          return;
        }
        if (parent) payload.parent_id = parent.id;
        window.DcClient.writeJson(URL, payload, "POST").then(function () {
          onDone();
        }).catch(function (error) { alertError("新增失败", error); });
      }
    });
  }

  function rename(chapter, onDone) {
    window.DcDialog.open({
      title: "修改章节名称",
      message: "编码保持不变；名称在同一父节点下不能重复。",
      confirmText: "保存",
      fields: [
        { key: "name", label: "章节名称", required: true, value: chapter.name }
      ],
      onConfirm: function (values) {
        window.DcClient.writeJson(URL + "/" + chapter.id, { name: values.name }, "PUT")
          .then(function () { onDone(); })
          .catch(function (error) { alertError("保存失败", error); });
      }
    });
  }

  function remove(chapter, onDone) {
    window.DcDialog.open({
      title: "删除确认",
      message: "确认删除章节「" + chapter.name + "」？此操作不可撤销。",
      confirmText: "删除",
      onConfirm: function () {
        window.DcClient.writeJson(URL + "/" + chapter.id, null, "DELETE")
          .then(function () { onDone(); })
          .catch(function (error) { failDelete(error, chapter); });
      }
    });
  }

  window.DcChapterOps = { add: add, rename: rename, remove: remove };
})();
