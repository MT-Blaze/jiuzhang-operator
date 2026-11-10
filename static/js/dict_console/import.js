/**
 * 字典批量导入（阶段二）：TOML 文件 → 真实导入基础五表。
 * 点【导入数据】弹出文件选择（.toml），读取文本后先确认再 POST，
 * 导入报告（新增 / 跳过 / 错误）逐表如实告知。绝不产生 JSON 文件。
 * 整块下架：删本文件与 sidebar.js 的 DcImport.init 调用即可。
 */
(function () {
  "use strict";

  var fileInput = null;

  function ensureInput() {
    if (fileInput) return fileInput;
    fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.id = "dcImportFile";
    fileInput.accept = ".toml,text/plain";
    fileInput.hidden = true;
    document.body.appendChild(fileInput);
    return fileInput;
  }

  function reportMessage(report) {
    var lines = [];
    var inserted = report.inserted || {};
    var skipped = report.skipped || {};
    var tables = Object.keys(inserted).concat(Object.keys(skipped));
    var seen = [];
    tables.forEach(function (table) {
      if (seen.indexOf(table) !== -1) return;
      seen.push(table);
      lines.push(table + "：新增 " + (inserted[table] || 0) + " 行，跳过重复 " + (skipped[table] || 0) + " 行");
    });
    if (!seen.length) lines.push("没有可导入的表。");
    var errors = report.errors || [];
    if (errors.length) {
      lines.push("", "以下行未导入：");
      errors.slice(0, 12).forEach(function (text) { lines.push("· " + text); });
      if (errors.length > 12) lines.push("…另有 " + (errors.length - 12) + " 条");
    }
    return lines.join("\n");
  }

  function runImport(text, name, button) {
    window.DcClient.writeJson("/api/bank/engine/dict/import", { content: text }, "POST")
      .then(function (report) {
        window.DcDialog.alert({ title: "导入完成", message: reportMessage(report), anchor: button });
      })
      .catch(function (error) {
        window.DcDialog.alert({ title: "导入失败", message: error.message, anchor: button });
      });
  }

  function onFile(button) {
    var input = ensureInput();
    var file = input.files && input.files[0];
    input.value = "";
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      var text = String(reader.result || "");
      window.DcDialog.open({
        title: "导入字典数据",
        message: "文件：" + file.name + "（" + text.length + " 字符）\n"
          + "将按 TOML 表数组批量导入基础五表，重复行自动跳过。\n"
          + "格式示例：[[dict_subjects]] 下写 name / code / sort_order。确认导入？",
        confirmText: "导入",
        anchor: button,
        onConfirm: function () { runImport(text, file.name, button); }
      });
    };
    reader.onerror = function () {
      window.DcDialog.alert({ title: "读取失败", message: "无法读取文件：" + file.name, anchor: button });
    };
    reader.readAsText(file, "utf-8");
  }

  function init(button) {
    var input = ensureInput();
    button.addEventListener("click", function () { input.click(); });
    input.addEventListener("change", function () { onFile(button); });
  }

  window.DcImport = { init: init };
})();