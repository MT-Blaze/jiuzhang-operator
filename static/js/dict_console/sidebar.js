/**
 * 辅助栏：字典小标签 + 操作区。
 * 三大分类下只铺紧凑小标签，点标签只在画布新开 / 激活该字典页签。
 * 辅助栏只渲染一次：画布开页、切页、关页都不重渲、不改高亮（常驻总控台）。
 * 操作区：【一键备份】走底座现成的备份体系（/api/settings/backup*），
 * 未开启本地备份时先征求老师同意再开启；【导入数据】交给 DcImport 走 TOML 批量导入。
 */
(function () {
  "use strict";

  var ctx = null;

  function shortTitle(category) {
    return category.title.replace(/字典$/, "");
  }

  function renderNav(container) {
    container.textContent = "";
    window.DcCatalog.CATEGORIES.forEach(function (category) {
      var group = document.createElement("div");
      group.className = "dc-chip-group";

      var title = document.createElement("h3");
      title.className = "dc-chip-group-title";
      title.textContent = shortTitle(category);

      var row = document.createElement("div");
      row.className = "dc-chip-row";
      row.setAttribute("role", "group");
      row.setAttribute("aria-label", category.title);

      category.items.forEach(function (item) {
        var chip = document.createElement("button");
        chip.type = "button";
        chip.className = "dc-chip";
        chip.textContent = item.name;
        chip.setAttribute("aria-label", "在画布新开「" + item.name + "」页签");
        chip.addEventListener("click", function () { ctx.openDict(category.key, item.table); });
        row.appendChild(chip);
      });

      group.appendChild(title);
      group.appendChild(row);
      container.appendChild(group);
    });
  }

  function busy(button, on) {
    button.disabled = on;
    button.setAttribute("aria-busy", on ? "true" : "false");
  }

  function reportBackup(result) {
    var local = result.local || {};
    var upload = result.upload || {};
    var lines = ["备份完成：" + (local.package_name || "未知包"), "落盘目录：" + (local.local_dir || "未知")];
    if (local.question_count != null) lines.push("题目数：" + local.question_count);
    if (upload.skipped) lines.push("网盘上传：未开启，已跳过");
    else if (upload.ok) lines.push("网盘上传：成功");
    else lines.push("网盘上传：失败（" + (upload.error || "未知原因") + "），本地备份已保住");
    window.DcDialog.alert({ title: "一键备份", message: lines.join("\n") });
  }

  function runBackup(button, stateEl) {
    stateEl.textContent = "正在备份…";
    return window.DcClient.writeJson("/api/settings/backup/run", null).then(function (result) {
      stateEl.textContent = "备份完成。";
      reportBackup(result);
    }).catch(function (error) {
      stateEl.textContent = "";
      window.DcDialog.alert({ title: "备份失败", message: error.message });
    }).finally(function () { busy(button, false); });
  }

  function onBackup(button, stateEl) {
    busy(button, true);
    stateEl.textContent = "正在读取备份配置…";
    window.DcClient.fetchJson("/api/settings/backup").then(function (view) {
      if (view.local_enabled) {
        runBackup(button, stateEl);
        return;
      }
      busy(button, false);
      stateEl.textContent = "";
      window.DcDialog.open({
        title: "本地备份未开启",
        message: "以默认目录开启本地备份，并立即备份一次？\n默认目录：" + (view.default_local_dir || "本机备份目录"),
        confirmText: "开启并备份",
        anchor: button,
        onConfirm: function () {
          busy(button, true);
          window.DcClient.writeJson("/api/settings/backup/config", { local_enabled: true })
            .then(function () { runBackup(button, stateEl); })
            .catch(function (error) {
              busy(button, false);
              window.DcDialog.alert({ title: "开启失败", message: error.message });
            });
        }
      });
    }).catch(function (error) {
      busy(button, false);
      stateEl.textContent = "";
      window.DcDialog.alert({ title: "读取备份配置失败", message: error.message });
    });
  }

  function init(context, elements) {
    ctx = context;
    renderNav(elements.navList);
    elements.backupBtn.addEventListener("click", function () { onBackup(elements.backupBtn, elements.opsState); });
    window.DcImport.init(elements.importBtn);
  }

  window.DcSidebar = { init: init };
})();
