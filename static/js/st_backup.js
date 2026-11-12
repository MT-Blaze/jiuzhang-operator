/**
 * st_backup.js —— settings.js 的「备份与恢复」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1：底座 JS 单文件不超 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var apiCall = deps.apiCall;
    var el = deps.el;
    var mgSet = deps.mgSet;
    var reloadHostPage = deps.reloadHostPage;

  // ============ 备份与恢复：宿主自有面板（军令 #17） ============
  var bkLocal = document.getElementById("stBackupLocal");
  var bkWebdav = document.getElementById("stBackupWebdav");
  var bkLocalDir = document.getElementById("stBackupLocalDir");
  var bkUrl = document.getElementById("stBackupUrl");
  var bkUser = document.getElementById("stBackupUser");
  var bkPass = document.getElementById("stBackupPass");
  var bkRemote = document.getElementById("stBackupRemote");
  var bkSaveBtn = document.getElementById("stBackupSaveBtn");
  var bkRunBtn = document.getElementById("stBackupRunBtn");
  var bkRefreshBtn = document.getElementById("stBackupRefreshBtn");
  var bkStatus = document.getElementById("stBackupStatus");
  var bkLast = document.getElementById("stBackupLast");
  var bkList = document.getElementById("stBackupList");
  var bkBusy = false;
  var bkBody = {};

  function bkSet(text, tone) {
    mgSet(bkStatus, text, tone);
  }

  function bkSyncToggles() {
    if (!bkLocal || !bkWebdav) return;
    if (bkWebdav.checked) {
      // 网盘依赖本地：开网盘就把本地一并勾上并锁住，避免「无本地文件可传」。
      bkLocal.checked = true;
      bkLocal.disabled = true;
    } else {
      bkLocal.disabled = false;
    }
  }

  function bkRenderList(items) {
    if (!bkList) return;
    bkList.textContent = "";
    var rows = items || [];
    if (!rows.length) {
      bkList.appendChild(el("li", "st-ws-empty", "还没有本地备份"));
      return;
    }
    rows.forEach(function (row) {
      var li = el("li", "st-ws-item");
      li.appendChild(el("span", "st-ws-name", row.package || row.stem));
      var meta = row.ok
        ? (row.generated_at || "") + " · " + Number(row.question_count || 0) + " 题 · " +
          Math.max(1, Math.round(Number(row.package_size || 0) / 1024)) + " KB"
        : "manifest 读取失败：" + (row.error || "未知原因");
      li.appendChild(el("span", "st-ws-meta", meta));
      bkList.appendChild(li);
    });
  }

  function bkRender(body) {
    if (!body) return;
    bkBody = body;
    if (bkLocal) bkLocal.checked = Boolean(body.local_enabled);
    if (bkWebdav) bkWebdav.checked = Boolean(body.webdav_enabled);
    if (bkLocalDir) bkLocalDir.value = body.local_dir || body.default_local_dir || "";
    if (bkUrl) bkUrl.value = body.url || "";
    if (bkUser) bkUser.value = body.username || "";
    if (bkRemote) bkRemote.value = body.remote_dir || "";
    if (bkPass) {
      bkPass.value = "";
      bkPass.placeholder = body.password_set
        ? "已设置（留空不改）" : "只落本机，不回显";
    }
    var last = body.last_upload || {};
    if (bkLast) {
      if (last.at) {
        bkLast.textContent = "上次网盘备份：" + last.at + " —— " +
          (last.ok ? "成功（" + (last.remote_name || "") + "）" : "失败：" + (last.error || "未知原因"));
        bkLast.hidden = false;
      } else {
        bkLast.hidden = true;
      }
    }
    bkSyncToggles();
    bkRenderList(body.local_backups || []);
  }

  function loadBackup() {
    if (!bkList) return Promise.resolve();
    return apiCall("/api/settings/backup", "GET")
      .then(bkRender)
      .catch(function (error) { bkSet("读取备份设置失败：" + error.message, "down"); });
  }

  function bkCollect() {
    var payload = {
      local_enabled: Boolean(bkLocal && bkLocal.checked),
      webdav_enabled: Boolean(bkWebdav && bkWebdav.checked),
      local_dir: bkLocalDir ? bkLocalDir.value.trim() : "",
      url: bkUrl ? bkUrl.value.trim() : "",
      username: bkUser ? bkUser.value.trim() : "",
      remote_dir: bkRemote ? bkRemote.value.trim() : "",
    };
    if (bkPass && bkPass.value) payload.password = bkPass.value;
    return payload;
  }

  function saveBackupConfig() {
    if (bkBusy) return;
    bkBusy = true;
    if (bkSaveBtn) { bkSaveBtn.disabled = true; bkSaveBtn.setAttribute("aria-busy", "true"); }
    bkSet("正在保存备份设置…", "info");
    apiCall("/api/settings/backup/config", "POST", bkCollect())
      .then(function (body) {
        bkRender(body);
        bkSet("备份设置已保存。", "ok");
      })
      .catch(function (error) { bkSet("保存失败：" + error.message, "down"); })
      .finally(function () {
        bkBusy = false;
        if (bkSaveBtn) { bkSaveBtn.disabled = false; bkSaveBtn.removeAttribute("aria-busy"); }
      });
  }

  function runBackup() {
    if (bkBusy) return;
    bkBusy = true;
    if (bkRunBtn) { bkRunBtn.disabled = true; bkRunBtn.setAttribute("aria-busy", "true"); }
    bkSet("正在生成一致性快照并压缩…", "info");
    apiCall("/api/settings/backup/run", "POST", {})
      .then(function (body) {
        var local = body.local || {};
        bkRender(body.backup || {});
        bkSet("本地备份完成：" + (local.package_name || "已生成") +
          "（" + Number(local.question_count || 0) + " 题，保留最近 3 份）。", "ok");
      })
      .catch(function (error) { bkSet("备份失败：" + error.message, "down"); })
      .finally(function () {
        bkBusy = false;
        if (bkRunBtn) { bkRunBtn.disabled = false; bkRunBtn.removeAttribute("aria-busy"); }
      });
  }

  // ---- 恢复：本地/网盘两条来源、预览勾选、校验后二次确认 ----
  var restoreLocalBtn = document.getElementById("stRestoreLocalBtn");
  var restoreRemoteBtn = document.getElementById("stRestoreRemoteBtn");
  var restoreStatus = document.getElementById("stRestoreStatus");
  var restorePicker = document.getElementById("stRestorePicker");
  var restorePickerTitle = document.getElementById("stRestorePickerTitle");
  var restoreSources = document.getElementById("stRestoreSources");
  var restorePreview = document.getElementById("stRestorePreview");
  var restoreSummary = document.getElementById("stRestoreSummary");
  var restoreGroups = document.getElementById("stRestoreGroups");
  var restoreCheckBtn = document.getElementById("stRestoreCheckBtn");
  var restoreCancelBtn = document.getElementById("stRestoreCancelBtn");
  var restoreDone = document.getElementById("stRestoreDone");
  var restoreDoneText = document.getElementById("stRestoreDoneText");
  var restoreReloadBtn = document.getElementById("stRestoreReloadBtn");
  var restoreModal = document.getElementById("restoreModal");
  var restoreModalDetail = document.getElementById("restoreModalDetail");
  var restoreModalCancel = document.getElementById("stRestoreModalCancel");
  var restoreModalConfirm = document.getElementById("stRestoreModalConfirm");
  var restoreState = { source: "", stem: "", preview: null, planId: "" };
  var restoreBusy = false;
  var restorePrevFocus = null;

  function rSet(text, tone) {
    mgSet(restoreStatus, text, tone);
  }

  function rClearPreview() {
    restoreState.preview = null;
    if (restorePreview) restorePreview.hidden = true;
    if (restoreGroups) restoreGroups.textContent = "";
    if (restoreSummary) restoreSummary.textContent = "";
    if (restoreDone) restoreDone.hidden = true;
  }

  function rCancelPlan() {
    var planId = restoreState.planId;
    restoreState.planId = "";
    if (!planId) return;
    apiCall("/api/settings/backup/restore/cancel", "POST", { plan_id: planId })
      .catch(function () { /* 临时区过期由后端兜底，取消失败不打扰老师 */ });
  }

  function rShowSources(title, rows, emptyText) {
    if (!restorePicker || !restoreSources) return;
    restorePicker.hidden = false;
    if (restorePickerTitle) restorePickerTitle.textContent = title;
    restoreSources.textContent = "";
    if (!rows.length) {
      restoreSources.appendChild(el("li", "st-ws-empty", emptyText));
      return;
    }
    rows.forEach(function (row) {
      var li = el("li", "st-ws-item");
      li.appendChild(el("span", "st-ws-name", row.package || row.stem));
      var size = Math.max(1, Math.round(Number(row.package_size || 0) / 1024));
      li.appendChild(el("span", "st-ws-meta",
        (row.generated_at || "") + " · " + Number(row.question_count || 0) + " 题 · " + size + " KB"));
      var actions = el("div", "st-ws-actions");
      var button = el("button", "q-button", "预览");
      button.type = "button";
      button.addEventListener("click", function () { rLoadPreview(row.source, row.stem); });
      actions.appendChild(button);
      li.appendChild(actions);
      restoreSources.appendChild(li);
    });
  }

  function rOpenLocal() {
    rCancelPlan();
    rClearPreview();
    var rows = (bkBody.local_backups || []).filter(function (row) { return row.ok; });
    rows.forEach(function (row) { row.source = "local"; });
    rShowSources("选择本地备份", rows, "还没有可用的本地备份，请先点【立即备份】。");
    if (rows.length) rSet("请选一份本地备份查看清单。", "info");
    else rSet("还没有可用的本地备份，请先点【立即备份】。", "warn");
  }

  function rOpenRemote() {
    if (restoreBusy) return;
    rCancelPlan();
    rClearPreview();
    rSet("正在读取网盘备份清单…", "info");
    apiCall("/api/settings/backup/remote", "GET")
      .then(function (body) {
        if (!body || !body.configured) {
          rSet("还没有配置 WebDAV 地址，请先在上方填好并保存。", "warn");
          if (restorePicker) restorePicker.hidden = true;
          return;
        }
        var rows = (body.entries || []).filter(function (row) { return row.complete; });
        rows.forEach(function (row) { row.source = "remote"; });
        rShowSources("选择网盘备份", rows, "网盘上还没有完整的备份。");
        if (rows.length) rSet("请选一份网盘备份查看清单。", "info");
        else rSet("网盘上还没有完整的备份。", "warn");
      })
      .catch(function (error) { rSet("读取网盘清单失败：" + error.message, "down"); });
  }

  function rRenderPreview(preview) {
    if (!preview) return;
    if (restorePreview) restorePreview.hidden = false;
    var sha = String(preview.package_sha256 || "");
    if (restoreSummary) {
      restoreSummary.textContent = "工作区 " + (preview.workspace_id || "") +
        " · schema " + Number(preview.schema_version || 0) +
        " · " + Number(preview.question_count || 0) + " 题" +
        " · " + Number(preview.file_count || 0) + " 个文件（图片 " + Number(preview.image_count || 0) + "）" +
        ((preview.plugins || []).length ? " · 旧包插件代码 " + preview.plugins.length + " 个（自动跳过）" : "") +
        " · " + (preview.generated_at || "") +
        " · 包哈希 " + sha.slice(0, 16) + "…";
    }
    if (!restoreGroups) return;
    restoreGroups.textContent = "";
    var metaByPath = {};
    (preview.files || []).forEach(function (item) { metaByPath[item.path] = item; });
    [
      ["bank", "题库数据（必选）"],
      ["uploads", "图片资产（必选）"],
      ["other", "其他数据文件（可选，默认勾选）"],
    ].forEach(function (group) {
      var paths = (preview.groups || {})[group[0]] || [];
      var box = el("div", "st-restore-group");
      box.appendChild(el("h5", null, group[1] + " · " + paths.length + " 个"));
      if (!paths.length) {
        box.appendChild(el("p", "st-note", "无"));
      }
      paths.forEach(function (rel) {
        var meta = metaByPath[rel] || {};
        var label = el("label", "st-restore-file");
        label.setAttribute("data-required", meta.required ? "1" : "0");
        var check = document.createElement("input");
        check.type = "checkbox";
        check.checked = true;
        check.value = rel;
        check.setAttribute("data-path", rel);
        if (meta.required) check.disabled = true;
        label.appendChild(check);
        label.appendChild(el("span", null, rel));
        if (meta.required) label.appendChild(el("span", "st-restore-tag", "必选"));
        box.appendChild(label);
      });
      restoreGroups.appendChild(box);
    });
    var legacyPluginPaths = (preview.groups || {}).plugins || [];
    if (legacyPluginPaths.length) {
      var legacyBox = el("div", "st-restore-group");
      legacyBox.appendChild(el("h5", null, "旧包插件代码（已全局化，恢复时自动跳过）· " + legacyPluginPaths.length + " 个"));
      legacyBox.appendChild(el("p", "st-note",
        "插件代码全机一份，下面这些旧包条目不会写入任何目录。"));
      legacyPluginPaths.forEach(function (rel) { legacyBox.appendChild(el("p", "st-note", rel)); });
      restoreGroups.appendChild(legacyBox);
    }
  }

  function rLoadPreview(source, stem) {
    if (!source || !stem) return;
    rCancelPlan();
    rClearPreview();
    rSet("正在读取备份清单…", "info");
    var path = source === "local"
      ? "/api/settings/backup/local/" + encodeURIComponent(stem)
      : "/api/settings/backup/remote/" + encodeURIComponent(stem);
    apiCall(path, "GET")
      .then(function (body) {
        restoreState.source = source;
        restoreState.stem = stem;
        restoreState.preview = body.preview;
        rRenderPreview(body.preview);
        rSet("清单已就绪：确认勾选后点【确认恢复】先做全量校验。", "ok");
      })
      .catch(function (error) { rSet("读取清单失败：" + error.message, "down"); });
  }

  function rCollectSelection() {
    var selected = [];
    if (!restoreGroups) return selected;
    restoreGroups.querySelectorAll('input[type="checkbox"]').forEach(function (check) {
      if (check.checked) selected.push(check.value);
    });
    return selected;
  }

  function rCheck() {
    if (restoreBusy || !restoreState.preview) return;
    var files = rCollectSelection();
    rCancelPlan();
    restoreBusy = true;
    if (restoreCheckBtn) {
      restoreCheckBtn.disabled = true;
      restoreCheckBtn.setAttribute("aria-busy", "true");
    }
    rSet("正在校验包哈希、文件哈希与逐题哈希…", "info");
    apiCall("/api/settings/backup/restore/check", "POST", {
      source: restoreState.source,
      stem: restoreState.stem,
      files: files,
    })
      .then(function (body) {
        restoreState.planId = body.plan_id;
        if (body.preview) {
          restoreState.preview = body.preview;
          rRenderPreview(body.preview);
        }
        rOpenRestoreModal(body);
      })
      .catch(function (error) { rSet("校验未通过，未写入任何数据：" + error.message, "down"); })
      .finally(function () {
        restoreBusy = false;
        if (restoreCheckBtn) {
          restoreCheckBtn.disabled = false;
          restoreCheckBtn.removeAttribute("aria-busy");
        }
      });
  }

  function rOpenRestoreModal(body) {
    if (!restoreModal) return;
    var preview = (body && body.preview) || restoreState.preview || {};
    var count = (body && body.selection ? body.selection.length : 0);
    if (restoreModalDetail) {
      restoreModalDetail.textContent = "将恢复 " + count + " 个文件" +
        "；工作区 " + (preview.workspace_id || "") + " · " + Number(preview.question_count || 0) +
        " 题 · 备份时间 " + (preview.generated_at || "") + "。";
    }
    restorePrevFocus = document.activeElement;
    restoreModal.hidden = false;
    restoreModal.setAttribute("aria-hidden", "false");
    if (restoreModalConfirm) restoreModalConfirm.focus();
  }

  function rCloseRestoreModal(focusBack) {
    if (restoreModal) {
      restoreModal.hidden = true;
      restoreModal.setAttribute("aria-hidden", "true");
    }
    if (focusBack && restorePrevFocus && restorePrevFocus.focus) restorePrevFocus.focus();
    restorePrevFocus = null;
  }

  function rConfirm() {
    var planId = restoreState.planId;
    if (!planId) return;
    restoreState.planId = "";
    rCloseRestoreModal(false);
    rSet("正在覆盖当前工作区并生成 .pre-restore.bak…", "info");
    apiCall("/api/settings/backup/restore/confirm", "POST", {
      plan_id: planId,
      confirm: "确认恢复",
    })
      .then(function (result) {
        rClearPreview();
        if (restorePicker) restorePicker.hidden = true;
        if (restoreDone) restoreDone.hidden = false;
        if (restoreDoneText) {
          var skippedPlugins = (result.plugins_skipped || []).length;
          restoreDoneText.textContent = "恢复完成：共 " + (result.restored || []).length +
            " 个文件；覆盖前副本 " + (result.pre_restore || []).length +
            " 份（.pre-restore.bak）。" +
            (skippedPlugins ? "旧包里有 " + skippedPlugins + " 个插件代码文件已跳过：插件代码全机一份，不再随工作区恢复。" : "") +
            "请重启底座以重载库连接；也可先点【刷新页面】查看。";
        }
        rSet("恢复完成。", "ok");
        loadBackup();
      })
      .catch(function (error) { rSet("恢复失败，已整批回滚：" + error.message, "down"); });
  }

  function rTrapFocus(event) {
    if (!restoreModal || event.key !== "Tab") return;
    var nodes = Array.prototype.filter.call(
      restoreModal.querySelectorAll("button, input, select, textarea, a[href]"),
      function (node) { return !node.disabled && node.offsetParent !== null; }
    );
    if (!nodes.length) return;
    var first = nodes[0];
    var last = nodes[nodes.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  if (restoreLocalBtn) restoreLocalBtn.addEventListener("click", rOpenLocal);
  if (restoreRemoteBtn) restoreRemoteBtn.addEventListener("click", rOpenRemote);
  if (restoreCheckBtn) restoreCheckBtn.addEventListener("click", rCheck);
  if (restoreCancelBtn) restoreCancelBtn.addEventListener("click", function () {
    rCancelPlan();
    rClearPreview();
    if (restorePicker) restorePicker.hidden = true;
    rSet("已取消本次恢复，未写入任何数据。", "info");
  });
  if (restoreReloadBtn) restoreReloadBtn.addEventListener("click", reloadHostPage);
  if (restoreModalCancel) restoreModalCancel.addEventListener("click", function () {
    rCancelPlan();
    rCloseRestoreModal(true);
    rSet("已取消覆盖，未写入任何数据。", "info");
  });
  if (restoreModalConfirm) restoreModalConfirm.addEventListener("click", rConfirm);
  if (restoreModal) restoreModal.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      event.preventDefault();
      rCancelPlan();
      rCloseRestoreModal(true);
      rSet("已取消覆盖，未写入任何数据。", "info");
      return;
    }
    rTrapFocus(event);
  });

  if (bkLocal) bkLocal.addEventListener("change", bkSyncToggles);
  if (bkWebdav) bkWebdav.addEventListener("change", bkSyncToggles);
  if (bkSaveBtn) bkSaveBtn.addEventListener("click", saveBackupConfig);
  if (bkRunBtn) bkRunBtn.addEventListener("click", runBackup);
  if (bkRefreshBtn) bkRefreshBtn.addEventListener("click", function () {
    bkSet("正在重新读取…", "info");
    loadBackup().then(function () { bkSet("已刷新。", "ok"); });
  });

    return {
      bkBody: bkBody,
      bkBusy: bkBusy,
      bkCollect: bkCollect,
      bkLast: bkLast,
      bkList: bkList,
      bkLocal: bkLocal,
      bkLocalDir: bkLocalDir,
      bkPass: bkPass,
      bkRefreshBtn: bkRefreshBtn,
      bkRemote: bkRemote,
      bkRender: bkRender,
      bkRenderList: bkRenderList,
      bkRunBtn: bkRunBtn,
      bkSaveBtn: bkSaveBtn,
      bkSet: bkSet,
      bkStatus: bkStatus,
      bkSyncToggles: bkSyncToggles,
      bkUrl: bkUrl,
      bkUser: bkUser,
      bkWebdav: bkWebdav,
      loadBackup: loadBackup,
      rCancelPlan: rCancelPlan,
      rCheck: rCheck,
      rClearPreview: rClearPreview,
      rCloseRestoreModal: rCloseRestoreModal,
      rCollectSelection: rCollectSelection,
      rConfirm: rConfirm,
      rLoadPreview: rLoadPreview,
      rOpenLocal: rOpenLocal,
      rOpenRemote: rOpenRemote,
      rOpenRestoreModal: rOpenRestoreModal,
      rRenderPreview: rRenderPreview,
      rSet: rSet,
      rShowSources: rShowSources,
      rTrapFocus: rTrapFocus,
      restoreBusy: restoreBusy,
      restoreCancelBtn: restoreCancelBtn,
      restoreCheckBtn: restoreCheckBtn,
      restoreDone: restoreDone,
      restoreDoneText: restoreDoneText,
      restoreGroups: restoreGroups,
      restoreLocalBtn: restoreLocalBtn,
      restoreModal: restoreModal,
      restoreModalCancel: restoreModalCancel,
      restoreModalConfirm: restoreModalConfirm,
      restoreModalDetail: restoreModalDetail,
      restorePicker: restorePicker,
      restorePickerTitle: restorePickerTitle,
      restorePrevFocus: restorePrevFocus,
      restorePreview: restorePreview,
      restoreReloadBtn: restoreReloadBtn,
      restoreRemoteBtn: restoreRemoteBtn,
      restoreSources: restoreSources,
      restoreState: restoreState,
      restoreStatus: restoreStatus,
      restoreSummary: restoreSummary,
      runBackup: runBackup,
      saveBackupConfig: saveBackupConfig,
    };
  }

  global.JzoStBackup = { create: create };
})(window);
