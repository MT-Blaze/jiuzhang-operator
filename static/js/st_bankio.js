/**
 * st_bankio.js —— settings.js 的「题库批量导入」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var apiCall = deps.apiCall;
    var fileToBase64 = deps.fileToBase64;
    var httpFailure = deps.httpFailure;
    var loadInstalled = deps.loadInstalled;
    var mgSet = deps.mgSet;

  // ============ 题库批量导入与导出（宿主侧 .json / .zip） ============
  var bankImportBtn = document.getElementById("bankImportBtn");
  var bankImportFile = document.getElementById("bankImportFile");
  var bankExportBtn = document.getElementById("bankExportBtn");
  var bankIoStatus = document.getElementById("bankIoStatus");

  function bankIoBusy(on) {
    if (bankImportBtn) {
      bankImportBtn.disabled = on;
      bankImportBtn.setAttribute("aria-busy", on ? "true" : "false");
    }
    if (bankExportBtn) {
      bankExportBtn.disabled = on;
      bankExportBtn.setAttribute("aria-busy", on ? "true" : "false");
    }
  }

  function todayStamp() {
    var now = new Date();
    return now.getFullYear() + String(now.getMonth() + 1).padStart(2, "0")
      + String(now.getDate()).padStart(2, "0");
  }

  function handleBankImport(file) {
    if (!file) return;
    if (!/\.(json|zip)$/i.test(file.name || "")) {
      mgSet(bankIoStatus, "只接受 .json 或 .zip 题目包。", "warn");
      return;
    }
    if (file.size > 32 * 1024 * 1024) {
      mgSet(bankIoStatus, "题目包超过 32 MB 上限。", "warn");
      return;
    }
    mgSet(bankIoStatus, "正在校验并导入 " + file.name + "…", "info");
    bankIoBusy(true);
    fileToBase64(file).then(function (b64) {
      return apiCall("/api/bank/import", "POST", { filename: file.name, content_base64: b64 });
    }).then(function (result) {
      var parts = ["已导入 " + (result.imported || 0) + " 题"];
      if (result.updated) parts.push("其中 " + result.updated + " 题覆盖了同 ID 的旧题");
      if (result.skipped) parts.push(result.skipped + " 题按同 ID 跳过");
      if (result.dropped_topics) parts.push("忽略了 " + result.dropped_topics + " 个本库没有的考向节点");
      mgSet(bankIoStatus, parts.join("，") + "。回题库浏览器即可看到。", "ok");
    }).catch(function (error) {
      mgSet(bankIoStatus, "导入失败：" + (error && error.message ? error.message : error), "down");
    }).then(function () {
      bankIoBusy(false);
    });
  }

  function exportBank() {
    mgSet(bankIoStatus, "正在打包当前题库…", "info");
    bankIoBusy(true);
    fetch("/api/bank/export", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) {
          return response.text().then(function (text) {
            var parsed = null;
            try { parsed = text ? JSON.parse(text) : null; } catch (error) { parsed = null; }
            throw httpFailure(response, text, parsed, "/api/bank/export", "GET");
          });
        }
        return response.blob();
      })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var link = document.createElement("a");
        link.href = url;
        link.download = "jiuzhang-bank-" + todayStamp() + ".json";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.setTimeout(function () { URL.revokeObjectURL(url); }, 0);
        mgSet(bankIoStatus, "已导出 " + Math.max(1, Math.round(blob.size / 1024)) + " KB。", "ok");
      })
      .catch(function (error) {
        mgSet(bankIoStatus, "导出失败：" + (error && error.message ? error.message : error), "down");
      })
      .then(function () {
        bankIoBusy(false);
      });
  }

  if (bankImportBtn) bankImportBtn.addEventListener("click", function () {
    if (bankImportFile) bankImportFile.click();
  });
  if (bankImportFile) bankImportFile.addEventListener("change", function () {
    var file = bankImportFile.files && bankImportFile.files[0];
    bankImportFile.value = "";
    handleBankImport(file);
  });
  if (bankExportBtn) bankExportBtn.addEventListener("click", exportBank);

  loadInstalled();

    return {
      bankExportBtn: bankExportBtn,
      bankImportBtn: bankImportBtn,
      bankImportFile: bankImportFile,
      bankIoBusy: bankIoBusy,
      bankIoStatus: bankIoStatus,
      exportBank: exportBank,
      handleBankImport: handleBankImport,
      todayStamp: todayStamp,
    };
  }

  global.JzoStBankio = { create: create };
})(window);
