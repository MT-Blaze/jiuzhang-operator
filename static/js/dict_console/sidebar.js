/**
 * 辅助栏：字典导航 + 操作区。
 * 导航：三大分类各一枚按钮，点击交给画布新开 / 激活同名页签（不覆盖当前页签）。
 * 操作区：【一键备份】走底座现成的备份体系（/api/settings/backup*），
 * 未开启本地备份时先征求老师同意再开启；【导入数据】交给 DcImport 走 TOML 批量导入。
 */
(function () {
  "use strict";

  var ctx = null;
  var navButtons = {};

  function renderNav(listEl) {
    listEl.textContent = "";
    window.DcCatalog.CATEGORIES.forEach(function (category) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "dc-nav-item";
      btn.setAttribute("aria-current", "false");
      var name = document.createElement("span");
      name.textContent = category.title;
      var badge = document.createElement("span");
      badge.className = "dc-nav-badge";
      badge.textContent = category.items.length + " 张表";
      btn.appendChild(name);
      btn.appendChild(badge);
      btn.addEventListener("click", function () { ctx.openCategory(category.key); });
      li.appendChild(btn);
      listEl.appendChild(li);
      navButtons[category.key] = btn;
    });
  }

  /** 页签激活态回写导航：当前分类高亮，看板激活时全不亮。 */
  function syncNav(activeKey) {
    Object.keys(navButtons).forEach(function (key) {
      navButtons[key].setAttribute("aria-current", key === activeKey ? "true" : "false");
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

  window.DcSidebar = { init: init, syncNav: syncNav };
})();