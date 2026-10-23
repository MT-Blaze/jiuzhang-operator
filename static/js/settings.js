/**
 * 设置与控制：左菜单选分区，右面板干活（工作区 / 插件 / 模型配置）。
 *
 * 在线索引的拉取/安装逻辑仍由 plugins.js 负责（同一套表单 id），本文件负责：
 * ① 分区导航（含宿主指定面板）；② 工作区列表、切换与新建（新建可选教材版本）；
 * ③ 手动安装：文件选择 + 拖拽区 + 状态回显；④ 模型 Provider 的切换/保存/测连通。
 * 边界与工作台拖装一致：只收 .zip、上限 50 MB、写接口带本机令牌、409 需显式
 * 确认覆盖，失败不留半个文件。所有插件名与状态只走 textContent，不拼 HTML。
 */
(function () {
  "use strict";

  // 内嵌模式：/settings?embedded=1 是被工作台画布页签 iframe 装载的，
  // 此时必须收起站点外壳（品牌头 / 主导航 / 页脚），只留面板本体，
  // 否则「不占额外空间」的定调就被一行导航条破了。
  var EMBEDDED = /[?&]embedded=1(&|$)/.test(window.location.search);
  if (EMBEDDED) document.documentElement.setAttribute("data-embedded", "1");

  var dropZone = document.getElementById("stDropZone");
  var fileInput = document.getElementById("stZipFile");
  var pickBtn = document.getElementById("stPickZip");
  var statusBox = document.getElementById("stInstallStatus");
  var busy = false;

  function setStatus(text, tone) {
    if (!statusBox) return;
    statusBox.textContent = text || "";
    statusBox.setAttribute("data-tone", tone || "info");
    statusBox.hidden = !text;
  }

  function readToken() {
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("读取本机令牌失败（HTTP " + response.status + "）");
        return response.json();
      })
      .then(function (body) {
        var token = body && body.local_token ? String(body.local_token) : "";
        if (!token) throw new Error("本机未生成就绪令牌，请先启动服务后再试");
        return token;
      });
  }

  function readErrorDetail(response, body) {
    var detail = body && body.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail.message === "string") return detail.message;
    return "HTTP " + response.status;
  }

  function firstZip(fileList) {
    for (var i = 0; i < (fileList || []).length; i += 1) {
      if (/\.zip$/i.test(fileList[i].name || "")) return fileList[i];
    }
    return null;
  }

  function hasFiles(event) {
    var types = (event.dataTransfer && event.dataTransfer.types) || [];
    return Array.prototype.indexOf.call(types, "Files") !== -1;
  }

  function setDragging(on) {
    if (dropZone) dropZone.classList.toggle("is-dragover", Boolean(on));
  }

  function installZip(file, replace) {
    if (!file) return Promise.resolve();
    if (!/\.zip$/i.test(file.name || "")) {
      setStatus("只接受标准 .zip 插件包（解压即用）。", "warn");
      return Promise.resolve();
    }
    if (file.size > 50 * 1024 * 1024) {
      setStatus("zip 包超过 50 MB 上限。", "warn");
      return Promise.resolve();
    }

    busy = true;
    if (pickBtn) {
      pickBtn.disabled = true;
      pickBtn.setAttribute("aria-busy", "true");
    }
    setStatus("正在校验并安装 " + file.name + " …", "info");

    return readToken()
      .then(function (token) {
        return fetch("/api/plugins/install" + (replace ? "?replace=true" : ""), {
          method: "POST",
          headers: { "Content-Type": "application/zip", "X-JZO-Token": token },
          body: file,
        });
      })
      .then(function (response) {
        return response.json().catch(function () { return null; }).then(function (body) {
          if (response.status === 409 && !replace) {
            var question = readErrorDetail(response, body) + " 覆盖升级会先删除旧目录，继续吗？";
            if (window.confirm(question)) return installZip(file, true);
            setStatus("已取消覆盖，本机原有插件保持不变。", "info");
            return null;
          }
          if (!response.ok) throw new Error(readErrorDetail(response, body));
          var plugin = (body && body.plugin) || {};
          setStatus(
            "已安装 " + (plugin.name || plugin.id) + " v" + (plugin.version || "?") +
            "。工作台左栏与对话工具即刻生效，无需重启。",
            "ok"
          );
          return body;
        });
      })
      .catch(function (error) {
        setStatus("安装失败：" + (error && error.message ? error.message : error), "down");
      })
      .finally(function () {
        busy = false;
        if (pickBtn) {
          pickBtn.disabled = false;
          pickBtn.setAttribute("aria-busy", "false");
        }
      });
  }

  function openPicker() {
    if (busy || !fileInput) return;
    fileInput.click();
  }

  if (pickBtn) pickBtn.addEventListener("click", openPicker);

  if (fileInput) {
    fileInput.addEventListener("change", function () {
      var file = fileInput.files && fileInput.files[0];
      fileInput.value = "";
      if (file) installZip(file, false);
    });
  }

  if (dropZone) {
    dropZone.addEventListener("click", openPicker);
    dropZone.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openPicker();
      }
    });
    dropZone.addEventListener("dragenter", function (event) {
      if (!hasFiles(event)) return;
      event.preventDefault();
      setDragging(true);
    });
    dropZone.addEventListener("dragover", function (event) {
      if (!hasFiles(event)) return;
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
      setDragging(true);
    });
    dropZone.addEventListener("dragleave", function () {
      setDragging(false);
    });
    dropZone.addEventListener("drop", function (event) {
      event.preventDefault();
      event.stopPropagation();
      setDragging(false);
      var file = firstZip(event.dataTransfer && event.dataTransfer.files);
      if (!file) {
        setStatus("没看到 .zip 文件：插件包必须是标准 zip。", "warn");
        return;
      }
      installZip(file, false);
    });
  }

  // 拖到框外时也别让浏览器把 zip 当页面打开；只提示该往哪拖。
  window.addEventListener("dragover", function (event) {
    if (hasFiles(event)) event.preventDefault();
  });
  window.addEventListener("drop", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    setDragging(false);
    if (dropZone && dropZone.contains(event.target)) return;
    setStatus("请把 .zip 拖到虚线框内，或点【选择 zip 文件】。", "warn");
  });

  // ============ 插件管理与控制 ============
  var mgList = document.getElementById("mgList");
  var mgStatus = document.getElementById("mgStatus");
  var mgRefresh = document.getElementById("mgRefresh");
  var importFile = document.getElementById("dbImportFile");
  var importBtn = document.getElementById("dbImportBtn");
  var importName = document.getElementById("importWsName");
  var importStatus = document.getElementById("importStatus");
  var modal = document.getElementById("uninstallModal");
  var modalText = document.getElementById("uninstallText");
  var modalKeep = document.getElementById("uninstallKeep");
  var modalDanger = document.getElementById("uninstallDanger");
  var modalConfirm = document.getElementById("uninstallConfirm");
  var modalCancel = document.getElementById("uninstallCancel");
  var uninstallTarget = null;
  var uninstallPrevFocus = null;

  function mgSet(box, text, tone) {
    if (!box) return;
    box.textContent = text || "";
    box.setAttribute("data-tone", tone || "info");
    box.hidden = !text;
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function apiCall(path, method, body, options) {
    // GET 默认不带令牌；但更新续更待办那条 GET 是带令牌的路由，须显式要求。
    var needsToken = method !== "GET" || Boolean(options && options.token);
    var steps = needsToken ? readToken() : Promise.resolve();
    return steps.then(function (token) {
      var headers = { Accept: "application/json" };
      if (token) headers["X-JZO-Token"] = token;
      if (body) headers["Content-Type"] = "application/json";
      return fetch(path, { method: method, headers: headers, body: body ? JSON.stringify(body) : undefined })
        .then(function (response) {
          return response.json().catch(function () { return null; }).then(function (parsed) {
            if (!response.ok) throw new Error(readErrorDetail(response, parsed));
            return parsed || {};
          });
        });
    });
  }

  function renderInstalled(plugins) {
    if (!mgList) return;
    mgList.textContent = "";
    var list = (plugins || []).slice().sort(function (a, b) {
      return String(a.name || a.id).localeCompare(String(b.name || b.id), "zh-CN");
    });
    if (!list.length) {
      mgList.appendChild(el("li", "mg-empty", "尚未安装任何插件"));
      return;
    }
    list.forEach(function (plugin) {
      var li = el("li", "mg-card");
      li.setAttribute("data-id", plugin.id);
      if (plugin.enabled === false) li.setAttribute("data-state", "disabled");

      var head = el("div", "mg-card-head");
      head.appendChild(el("span", "mg-card-name", plugin.name || plugin.id));
      head.appendChild(el("span", "mg-card-version", "v" + (plugin.version || "?")));
      var status = el("span", "mg-card-state", plugin.enabled === false ? "已停用" : "已启用");
      status.setAttribute("data-state", plugin.enabled === false ? "off" : "on");
      head.appendChild(status);
      li.appendChild(head);
      li.appendChild(el("p", "mg-card-desc", plugin.description || ""));
      li.appendChild(el("p", "mg-card-sub", "id：" + plugin.id + " · 类型：" + (plugin.kind || "?")));

      var tools = el("div", "mg-card-tools");
      var toggle = el("button", "q-button mg-toggle");
      toggle.type = "button";
      toggle.textContent = plugin.enabled === false ? "启用" : "停用";
      toggle.addEventListener("click", function () {
        setEnabled(plugin, plugin.enabled === false);
      });
      tools.appendChild(toggle);

      if (plugin.show_in_sidebar === false) {
        tools.appendChild(el("span", "mg-tag", "不占左栏"));
      }

      var remove = el("button", "q-button q-button-danger mg-uninstall");
      remove.type = "button";
      remove.textContent = "卸载";
      remove.addEventListener("click", function () { openUninstall(plugin); });
      tools.appendChild(remove);
      li.appendChild(tools);

      mgList.appendChild(li);
    });
  }

  function loadInstalled() {
    return fetch("/api/plugins", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) { renderInstalled((data && data.plugins) || []); })
      .catch(function (error) { mgSet(mgStatus, "读取插件列表失败：" + error.message, "down"); });
  }

  function setEnabled(plugin, enabled) {
    mgSet(mgStatus, "正在" + (enabled ? "启用" : "停用") + " " + (plugin.name || plugin.id) + "…", "info");
    apiCall("/api/plugins/" + encodeURIComponent(plugin.id) + "/enabled", "POST", { enabled: enabled })
      .then(function () {
        mgSet(mgStatus, (enabled ? "已启用：" : "已停用：") + (plugin.name || plugin.id) +
          (enabled ? "，工作台左栏刷新后可见。" : "，代码与数据原地保留，随时可再启用。"), "ok");
        loadInstalled();
      })
      .catch(function (error) { mgSet(mgStatus, "操作失败：" + error.message, "down"); });
  }

  function openUninstall(plugin) {
    uninstallTarget = plugin;
    uninstallPrevFocus = document.activeElement;
    if (modalText) modalText.textContent = "确定卸载「" + (plugin.name || plugin.id) + "」？";
    if (modalKeep) modalKeep.checked = true;
    if (modalDanger) modalDanger.hidden = true;
    if (modal) {
      modal.hidden = false;
      modal.setAttribute("aria-hidden", "false");
      if (modalKeep) modalKeep.focus();
    }
  }

  function closeUninstall() {
    if (modal) {
      modal.hidden = true;
      modal.setAttribute("aria-hidden", "true");
    }
    uninstallTarget = null;
    if (uninstallPrevFocus && uninstallPrevFocus.focus) uninstallPrevFocus.focus();
    uninstallPrevFocus = null;
  }

  function confirmUninstall() {
    if (!uninstallTarget) return;
    var keep = modalKeep ? modalKeep.checked : true;
    var plugin = uninstallTarget;
    closeUninstall();
    mgSet(mgStatus, "正在卸载 " + (plugin.name || plugin.id) + "…", "info");
    apiCall("/api/plugins/" + encodeURIComponent(plugin.id) + "?keep_data=" + (keep ? "true" : "false"), "DELETE")
      .then(function (result) {
        var removed = (result && result.removed_data && result.removed_data.length) || 0;
        mgSet(mgStatus, "已卸载 " + (plugin.name || plugin.id) +
          (keep ? "（保留了本地数据）。" : "（已连同 " + removed + " 个本地数据库一并物理删除）。"), "ok");
        loadInstalled();
      })
      .catch(function (error) { mgSet(mgStatus, "卸载失败：" + error.message, "down"); });
  }

  function fileToBase64(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () {
        var text = String(reader.result || "");
        resolve(text.slice(text.indexOf(",") + 1));   // 去掉 data:;base64, 前缀
      };
      reader.onerror = function () { reject(new Error("读取文件失败")); };
      reader.readAsDataURL(file);
    });
  }

  function importDatabase() {
    if (!importFile) return;
    var name = importName ? String(importName.value || "").trim() : "";
    if (!name) { mgSet(importStatus, "请先填写新工作区名称。", "warn"); if (importName) importName.focus(); return; }
    importFile.click();
  }

  function handleImportFile(file) {
    if (!file) return;
    if (!/\.db$/i.test(file.name || "")) { mgSet(importStatus, "请选择 .db 数据库文件。", "warn"); return; }
    if (file.size > 64 * 1024 * 1024) { mgSet(importStatus, "题库文件超过 64 MB 上限。", "warn"); return; }
    mgSet(importStatus, "正在校验并挂载 " + file.name + "…", "info");
    fileToBase64(file).then(function (b64) {
      return apiCall("/api/workspaces/import", "POST", { name: importName.value.trim(), db_base64: b64 });
    }).then(function (result) {
      mgSet(importStatus, "已挂载为新工作区「" + (result.name || "") + "」（" +
        (result.question_count || 0) + " 题），并切换过去。回工作台即见。", "ok");
      if (importName) importName.value = "";
    }).catch(function (error) {
      mgSet(importStatus, "导入失败：" + (error && error.message ? error.message : error), "down");
    });
  }

  if (mgRefresh) mgRefresh.addEventListener("click", loadInstalled);
  if (modalConfirm) modalConfirm.addEventListener("click", confirmUninstall);
  if (modalCancel) modalCancel.addEventListener("click", closeUninstall);
  if (modalKeep) modalKeep.addEventListener("change", function () {
    if (modalDanger) modalDanger.hidden = modalKeep.checked;
  });
  if (modal) modal.addEventListener("keydown", function (event) {
    if (event.key === "Escape") { event.preventDefault(); closeUninstall(); }
  });
  if (importBtn) importBtn.addEventListener("click", importDatabase);
  if (importFile) importFile.addEventListener("change", function () {
    var file = importFile.files && importFile.files[0];
    importFile.value = "";
    handleImportFile(file);
  });

  // ============ 题库批量导入与导出（宿主侧 .json / .zip） ============
  var bankImportBtn = document.getElementById("bankImportBtn");
  var bankImportFile = document.getElementById("bankImportFile");
  var bankExportBtn = document.getElementById("bankExportBtn");
  var bankIoStatus = document.getElementById("bankIoStatus");

  function bankIoBusy(busy) {
    if (bankImportBtn) {
      bankImportBtn.disabled = busy;
      bankImportBtn.setAttribute("aria-busy", busy ? "true" : "false");
    }
    if (bankExportBtn) {
      bankExportBtn.disabled = busy;
      bankExportBtn.setAttribute("aria-busy", busy ? "true" : "false");
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
          return response.json().catch(function () { return null; }).then(function (parsed) {
            throw new Error(readErrorDetail(response, parsed));
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

  // ============ 双轨更新：插件热更新 + 底座自更新（PLUGIN_SPEC §1.7） ============
  // 出网铁律：下面每一个请求都只由当场的一次点击发起，没有任何定时器与轮询。
  var upCheckBtn = document.getElementById("upCheckBtn");
  var upAllBtn = document.getElementById("upAllBtn");
  var upStatus = document.getElementById("upStatus");
  var upListTitle = document.getElementById("upListTitle");
  var upList = document.getElementById("upList");
  var upHost = document.getElementById("upHost");
  var upHostText = document.getElementById("upHostText");
  var upHostBtn = document.getElementById("upHostBtn");
  var upLog = document.getElementById("upLog");
  var upProgress = document.getElementById("upProgress");
  var upIndexUrl = document.getElementById("plIndexUrl");
  var upRows = [];
  var upHostRow = null;
  var upHostArmed = false;
  var UP_LOG_MAX = 200;
  var UP_NOTICE_KEY = "jzo.updateNotice";

  function upStamp() {
    var now = new Date();
    function pad(value) { return value < 10 ? "0" + value : String(value); }
    return pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
  }

  function upLine(text, tone) {
    if (!upLog) return;
    var li = el("li", "up-log-line");
    li.setAttribute("data-tone", tone || "info");
    li.appendChild(el("span", "up-log-time", upStamp()));
    li.appendChild(el("span", "up-log-text", text));
    upLog.appendChild(li);
    while (upLog.children.length > UP_LOG_MAX) upLog.removeChild(upLog.firstChild);
    upLog.scrollTop = upLog.scrollHeight;
  }

  function upBusy(on, label) {
    if (on) {
      [upCheckBtn, upAllBtn].forEach(function (button) {
        if (!button) return;
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
      });
      upProgressSet(true, label);
      mgSet(upStatus, label || "正在处理…", "info");
      return;
    }
    [upCheckBtn, upAllBtn].forEach(function (button) {
      if (!button) return;
      button.removeAttribute("aria-busy");
    });
    if (upCheckBtn) upCheckBtn.disabled = false;
    if (upAllBtn) {
      upAllBtn.disabled = !upRows.some(function (row) { return row.state === "update_available"; });
    }
    upProgressSet(false);
  }

  // 后端没有细粒度进度事件：只诚实展示「不确定进度」，不伪造百分比。
  function upProgressSet(on, label) {
    if (!upProgress) return;
    upProgress.hidden = !on;
    upProgress.setAttribute("aria-busy", on ? "true" : "false");
    upProgress.setAttribute("aria-valuetext", on ? (label || "正在处理…") : "空闲");
  }

  // 检查/更新完成后把待办数同步给宿主：工作台左栏据此亮「有 N 项更新」文字徽标，
  // 不靠颜色单独传达状态（AGENTS §6）。只写本机，不发任何网络请求。
  function publishUpdateNotice(count) {
    var value = Number(count) || 0;
    try {
      if (value > 0) {
        localStorage.setItem(UP_NOTICE_KEY, JSON.stringify({ count: value, at: Date.now() }));
      } else {
        localStorage.removeItem(UP_NOTICE_KEY);
      }
    } catch (error) { /* 隐私模式禁用本地存储时只影响徽标，不影响更新流程 */ }
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ jzo: "updates.available", count: value }, window.location.origin);
      }
    } catch (error) { /* 宿主已关闭：忽略 */ }
  }

  function syncUpdateNotice() {
    var pending = upRows.filter(function (row) { return row.state === "update_available"; }).length;
    var host = upHostRow && upHostRow.update_available && upHostRow.available ? 1 : 0;
    publishUpdateNotice(pending + host);
  }

  var UP_STATE_LABEL = {
    up_to_date: "已是最新",
    update_available: "可更新",
    incompatible: "需先更新底座",
    not_in_index: "索引未收录",
    bad_entry: "条目有问题"
  };

  function renderUpdateRows() {
    if (!upList) return;
    upList.textContent = "";
    if (upListTitle) upListTitle.hidden = !upRows.length;
    if (!upRows.length) return;
    upRows.forEach(function (row) {
      var li = el("li", "mg-card up-card");
      li.setAttribute("data-id", row.id);
      li.setAttribute("data-state", row.state);

      var head = el("div", "mg-card-head");
      head.appendChild(el("span", "mg-card-name", row.name || row.id));
      head.appendChild(el("span", "mg-card-version",
        "v" + (row.local_version || "?") + (row.remote_version ? " → v" + row.remote_version : "")));
      var badge = el("span", "mg-card-state", UP_STATE_LABEL[row.state] || row.state);
      badge.setAttribute("data-state", row.state === "update_available" ? "on" : "off");
      head.appendChild(badge);
      li.appendChild(head);

      if (row.reason) li.appendChild(el("p", "mg-card-desc", row.reason));
      li.appendChild(el("p", "mg-card-sub", "id：" + row.id));

      var tools = el("div", "mg-card-tools");
      if (row.state === "update_available") {
        var apply = el("button", "q-button q-button-danger up-apply");
        apply.type = "button";
        apply.textContent = "更新";
        apply.addEventListener("click", function () { applyOne(row, apply); });
        tools.appendChild(apply);
      } else if (row.state === "incompatible") {
        var blocked = el("button", "q-button up-apply");
        blocked.type = "button";
        blocked.textContent = "需先更新底座";
        blocked.disabled = true;
        blocked.title = row.reason || "";
        tools.appendChild(blocked);
      }
      li.appendChild(tools);
      upList.appendChild(li);
    });
  }

  function renderHostRow() {
    if (!upHost || !upHostText || !upHostBtn) return;
    upHost.hidden = !upHostRow;
    upHostArmed = false;
    if (!upHostRow) return;
    var available = upHostRow.update_available && upHostRow.available;
    upHostText.textContent = available
      ? ("发现底座新版本 " + upHostRow.available + "（当前 " + upHostRow.current + "）" +
         (upHostRow.notes ? "：" + upHostRow.notes : ""))
      : ("底座当前 " + (upHostRow.current || "?") + "，" + (upHostRow.reason || "无需更新") + "。");
    upHostBtn.disabled = !available;
    upHostBtn.textContent = "更新并重启";
  }

  function upCheck() {
    var url = upIndexUrl && upIndexUrl.value ? upIndexUrl.value.trim() : "";
    upBusy(true, url ? "正在按索引地址检查更新…" : "正在用本机索引缓存检查更新…");
    upLine(url ? "检查更新：拉取索引 " + url : "检查更新：使用本机索引缓存（未出网）");
    apiCall("/api/plugins/update/check", "POST", url ? { url: url, allow_mirrors: true } : {})
      .then(function (body) {
        upRows = (body && body.plugins) || [];
        upHostRow = (body && body.host) || null;
        renderUpdateRows();
        renderHostRow();
        syncUpdateNotice();
        var summary = (body && body.summary) || {};
        upLine("检查完成：共 " + (summary.checked || 0) + " 个插件，可更新 " +
          (summary.update_available || 0) + " 个，需先更新底座 " + (summary.incompatible || 0) +
          " 个，已是最新 " + (summary.up_to_date || 0) + " 个。", "ok");
        if (body && body.index_source === "cache") upLine("索引来自本机缓存（未出网）。");
        upBusy(false);
        mgSet(upStatus, "检查完成。", "ok");
      })
      .catch(function (error) {
        upBusy(false);
        upLine("检查失败：" + error.message, "down");
        mgSet(upStatus, "检查更新失败：" + error.message, "down");
      });
  }

  function afterUpdated(updated) {
    loadInstalled();
    // 通知宿主工作台：刷新左栏插件状态，并让正占据画布的那个插件重新水合。
    try {
      window.parent.postMessage({ jzo: "plugins.updated", updated: updated || [] }, window.location.origin);
    } catch (error) {
      upLine("已更新，但通知工作台失败：" + error.message, "warn");
    }
  }

  function logOutcome(body) {
    ((body && body.updated) || []).forEach(function (row) {
      var kept = (row.preserved || []).length;
      upLine("已更新 " + row.id + "：" + (row.from || "?") + " → " + row.to +
        (kept ? "（保住本机文件 " + kept + " 个）" : ""), "ok");
    });
    ((body && body.failed) || []).forEach(function (row) {
      upLine("更新失败 " + row.id + "：" + row.reason, "down");
    });
    ((body && body.skipped) || []).forEach(function (row) {
      upLine("已跳过 " + row.id + "：" + (row.reason || row.state || ""), "warn");
    });
  }

  function applyOne(row, button) {
    if (button) { button.disabled = true; button.setAttribute("aria-busy", "true"); }
    upBusy(true, "正在更新 " + (row.name || row.id) + " …");
    upLine("开始更新 " + row.id + "：" + row.local_version + " → " + row.remote_version);
    apiCall("/api/plugins/update/apply", "POST", { ids: [row.id] })
      .then(function (body) {
        logOutcome(body);
        upBusy(false);
        if (button) button.removeAttribute("aria-busy");
        afterUpdated((body && body.updated) || []);
        mgSet(upStatus, "更新流程结束，详见下方日志。", "ok");
        upCheckSilently();
      })
      .catch(function (error) {
        upBusy(false);
        if (button) { button.disabled = false; button.removeAttribute("aria-busy"); }
        upLine("更新失败：" + error.message, "down");
        mgSet(upStatus, "更新失败：" + error.message, "down");
      });
  }

  function applyAll() {
    upBusy(true, "正在一键更新全部插件（单次批量，跑完即止）…");
    upLine("一键更新全部插件：本次范围内的条目逐个下载并热更。");
    apiCall("/api/plugins/update/apply", "POST", { all: true })
      .then(function (body) {
        logOutcome(body);
        upBusy(false);
        afterUpdated((body && body.updated) || []);
        mgSet(upStatus, "一键更新结束，详见下方日志。", "ok");
        upCheckSilently();
      })
      .catch(function (error) {
        upBusy(false);
        upLine("一键更新失败：" + error.message, "down");
        mgSet(upStatus, "一键更新失败：" + error.message, "down");
      });
  }

  function upCheckSilently() {
    // 更新完就地重算一次状态表：只用本机缓存，不再出网。
    apiCall("/api/plugins/update/check", "POST", {})
      .then(function (body) {
        upRows = (body && body.plugins) || [];
        upHostRow = (body && body.host) || upHostRow;
        renderUpdateRows();
        renderHostRow();
        syncUpdateNotice();
        upBusy(false);
      })
      .catch(function () { upBusy(false); });
  }

  function waitThenReload(triesLeft) {
    // 底座重启期间页面必然断线；这里的重试只为「重启完成后自动回到界面」，
    // 是用户那一次点击的收尾动作，不是后台轮询。
    if (triesLeft <= 0) {
      mgSet(upStatus, "底座重启超时，请手动刷新页面。", "down");
      upLine("等待底座重启超时，请手动刷新。", "down");
      return;
    }
    window.setTimeout(function () {
      fetch("/healthz", { cache: "no-store" })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          window.location.reload();
        })
        .catch(function () { waitThenReload(triesLeft - 1); });
    }, 2000);
  }

  function hostApply() {
    if (!upHostArmed) {
      // 第一下只下载 + 校验 + 生成一次性脚本，绝不动正在运行的底座。
      upHostBtn.disabled = true;
      upHostBtn.setAttribute("aria-busy", "true");
      upProgressSet(true, "正在下载并校验底座新版本…");
      upLine("正在下载并校验底座新版本（尚未覆盖任何文件）…");
      apiCall("/api/plugins/update/host-apply", "POST", {})
        .then(function (body) {
          upHostBtn.removeAttribute("aria-busy");
          upProgressSet(false);
          upLine("底座新版本已下载并校验：" + body.current + " → " + body.version +
            "；一次性脚本已生成。", "ok");
          if (body.launchable === false) {
            upLine("当前是开发工作树，底座拒绝自动覆盖重启；脚本在 " + body.script_path +
              "，需要时手工执行。", "warn");
            upHostBtn.disabled = true;
            upHostArmed = false;
            upHostBtn.textContent = "开发工作树不自动重启";
            return;
          }
          upHostArmed = true;
          upHostBtn.disabled = false;
          upHostBtn.textContent = "确认：覆盖并重启";
          mgSet(upStatus, "再点一次【确认：覆盖并重启】才会结束当前进程并覆盖程序文件（data/ 全程受保护）。", "warn");
        })
        .catch(function (error) {
          upHostBtn.removeAttribute("aria-busy");
          upProgressSet(false);
          upHostBtn.disabled = false;
          upLine("底座更新失败：" + error.message, "down");
          mgSet(upStatus, "底座更新失败：" + error.message, "down");
        });
      return;
    }
    upHostBtn.disabled = true;
    upHostBtn.setAttribute("aria-busy", "true");
    upLine("正在交接给一次性脚本：稍后底座会自行退出、覆盖程序文件并重启…");
    apiCall("/api/plugins/update/host-apply", "POST", { launch: true })
      .then(function (body) {
        upLine("已交接。底座将在 " + (body.restart_in_ms || 0) + " 毫秒后退出，" +
          "覆盖过程保护 data/、.venv/、.git/ 等目录，完成后自动重启。", "ok");
        mgSet(upStatus, "底座正在重启，页面稍后会自动恢复。", "warn");
        waitThenReload(30);
      })
      .catch(function (error) {
        upHostBtn.removeAttribute("aria-busy");
        upHostBtn.disabled = false;
        upLine("重启交接失败：" + error.message, "down");
        mgSet(upStatus, "重启交接失败：" + error.message, "down");
      });
  }

  function loadPending() {
    apiCall("/api/plugins/update/pending", "GET", null, { token: true })
      .then(function (body) {
        var pending = (body && body.pending) || [];
        if (pending.length) {
          upLine("本机有 " + pending.length + " 个插件待补齐（上一轮更新因底座重启中断）：" +
            pending.map(function (row) { return row.id; }).join("、"), "warn");
        }
        var last = (body && body.last_resume) || null;
        if (last && last.ran && last.had_pending) {
          (last.resumed || []).forEach(function (row) {
            upLine("启动续更完成：" + row.id + " " + (row.from || "?") + " → " + row.to, "ok");
          });
          (last.failed || []).forEach(function (row) {
            upLine("启动续更失败：" + row.id + "（" + row.reason + "）", "down");
          });
        }
      })
      .catch(function () { /* 待办读不到不影响其他面板，静默 */ });
  }

  if (upCheckBtn) upCheckBtn.addEventListener("click", upCheck);
  if (upAllBtn) upAllBtn.addEventListener("click", applyAll);
  if (upHostBtn) upHostBtn.addEventListener("click", hostApply);
  loadPending();

  // ============ 左菜单 + 右面板：分区导航 ============
  var PANEL_KEYS = ["workspace", "plugin", "provider", "system"];
  var navItems = {};
  var panelEls = {};
  PANEL_KEYS.forEach(function (key) {
    navItems[key] = document.getElementById("stNav" + key.charAt(0).toUpperCase() + key.slice(1));
    panelEls[key] = document.getElementById("stPanel" + key.charAt(0).toUpperCase() + key.slice(1));
  });
  var activePanel = "workspace";

  function selectPanel(key, focusNav) {
    if (PANEL_KEYS.indexOf(key) === -1) return;
    activePanel = key;
    PANEL_KEYS.forEach(function (name) {
      var tab = navItems[name];
      var panel = panelEls[name];
      var on = name === key;
      if (tab) {
        tab.classList.toggle("is-active", on);
        tab.setAttribute("aria-selected", on ? "true" : "false");
        tab.tabIndex = on ? 0 : -1;
        if (on && focusNav) tab.focus();
      }
      if (panel) panel.hidden = !on;
    });
  }

  PANEL_KEYS.forEach(function (name) {
    var tab = navItems[name];
    if (!tab) return;
    tab.addEventListener("click", function () { selectPanel(name, false); });
    tab.addEventListener("keydown", function (event) {
      var index = PANEL_KEYS.indexOf(name);
      var step = (event.key === "ArrowDown" || event.key === "ArrowRight") ? 1
        : (event.key === "ArrowUp" || event.key === "ArrowLeft") ? -1 : 0;
      if (event.key === "Home") step = -PANEL_KEYS.length;
      if (event.key === "End") step = PANEL_KEYS.length - index;
      if (!step) return;
      event.preventDefault();
      var next = PANEL_KEYS[(index + step + PANEL_KEYS.length) % PANEL_KEYS.length];
      selectPanel(next, true);
    });
  });

  // ============ 插件分区：左菜单下的二级菜单（页签，不做弹窗） ============
  var PLUGIN_TABS = ["manage", "update", "index", "install"];
  var pluginTabButtons = {};
  var pluginTabPanels = {};
  PLUGIN_TABS.forEach(function (key) {
    var suffix = key.charAt(0).toUpperCase() + key.slice(1);
    pluginTabButtons[key] = document.getElementById("stPluginTab" + suffix);
    pluginTabPanels[key] = document.getElementById("stPluginPanel" + suffix);
  });

  function selectPluginTab(key, focusTab) {
    if (PLUGIN_TABS.indexOf(key) === -1) return;
    PLUGIN_TABS.forEach(function (name) {
      var tab = pluginTabButtons[name];
      var panel = pluginTabPanels[name];
      var on = name === key;
      if (tab) {
        tab.classList.toggle("is-active", on);
        tab.setAttribute("aria-selected", on ? "true" : "false");
        tab.tabIndex = on ? 0 : -1;
        if (on && focusTab) tab.focus();
      }
      if (panel) panel.hidden = !on;
    });
  }

  PLUGIN_TABS.forEach(function (name) {
    var tab = pluginTabButtons[name];
    if (!tab) return;
    tab.addEventListener("click", function () { selectPluginTab(name, false); });
    tab.addEventListener("keydown", function (event) {
      var index = PLUGIN_TABS.indexOf(name);
      var step = (event.key === "ArrowRight" || event.key === "ArrowDown") ? 1
        : (event.key === "ArrowLeft" || event.key === "ArrowUp") ? -1 : 0;
      if (event.key === "Home") step = -PLUGIN_TABS.length;
      if (event.key === "End") step = PLUGIN_TABS.length - index;
      if (!step) return;
      event.preventDefault();
      var next = PLUGIN_TABS[(index + step + PLUGIN_TABS.length) % PLUGIN_TABS.length];
      selectPluginTab(next, true);
    });
  });

  // 宿主页签可以指定落在哪一区、哪一二级页签：
  // 首次用地址参数 ?panel=plugin&tab=update，后续用同源 postMessage。
  function requestPanelFromHost(key, sub) {
    if (PANEL_KEYS.indexOf(key) === -1) return;
    selectPanel(key, false);
    if (key === "plugin" && sub) selectPluginTab(String(sub), false);
  }

  var urlPanel = /[?&]panel=([^&]+)/.exec(window.location.search);
  var urlTab = /[?&]tab=([^&]+)/.exec(window.location.search);
  if (urlPanel) {
    try {
      requestPanelFromHost(decodeURIComponent(urlPanel[1]), urlTab ? decodeURIComponent(urlTab[1]) : "");
    } catch (error) { /* 非法参数回落默认区 */ }
  }
  window.addEventListener("message", function (event) {
    if (event.origin !== window.location.origin) return;
    var data = event.data;
    if (data && data.jzo === "console.panel") {
      requestPanelFromHost(String(data.panel || ""), data.tab ? String(data.tab) : "");
    }
  });

  // ============ 工作区：列出 / 切换 / 新建（含教材版本） ============
  var wsListEl = document.getElementById("stWsList");
  var wsStatus = document.getElementById("stWsStatus");
  var wsNameInput = document.getElementById("stWsName");
  var wsTextbookSelect = document.getElementById("stWsTextbook");
  var wsCreateBtn = document.getElementById("stWsCreateBtn");
  var wsTextbookRefresh = document.getElementById("stWsTextbookRefresh");
  var textbookById = {};
  var textbookItems = [];
  var activeTextbookId = "";
  var wsBusy = false;

  // 独立访问 /settings 时刷新自己；被画布页签内嵌时刷新宿主，页签与左栏一起对齐新库。
  function reloadHostPage() {
    var target = window;
    try {
      if (window.top && window.top !== window.self) target = window.top;
    } catch (error) {
      target = window;
    }
    target.location.reload();
  }

  function renderWorkspaces(data) {
    if (!wsListEl) return;
    wsListEl.textContent = "";
    var list = (data && data.workspaces) || [];
    if (!list.length) {
      wsListEl.appendChild(el("li", "st-ws-empty", "尚未登记任何工作区"));
      return;
    }
    list.forEach(function (ws) {
      var li = el("li", "st-ws-item");
      li.setAttribute("data-active", ws.is_active ? "1" : "0");
      li.appendChild(el("span", "st-ws-name", ws.name || ws.id));
      var fallbackName = ws.is_active && activeTextbookId && textbookById[activeTextbookId]
        ? "跟随默认版本（当前：" + textbookById[activeTextbookId] + "）"
        : "跟随默认版本";
      var tb = ws.textbook_id ? (textbookById[ws.textbook_id] || ws.textbook_id) : fallbackName;
      li.appendChild(el("span", "st-ws-meta",
        (ws.is_active ? "当前 · " : "") + Number(ws.question_count || 0) + " 题 · 教材：" + tb));
      var actions = el("div", "st-ws-actions");
      if (textbookItems.length || ws.textbook_id) {
        var picker = el("label", "st-ws-pick");
        picker.appendChild(el("span", "st-ws-pick-label", "教材版本"));
        var pick = el("select", "st-ws-textbook-inline");
        pick.setAttribute("aria-label", "教材版本：" + (ws.name || ws.id));
        var follow = el("option");
        follow.value = "";
        follow.textContent = "跟随默认";
        pick.appendChild(follow);
        textbookItems.forEach(function (item) {
          var option = el("option");
          option.value = item.id;
          option.textContent = item.name + (item.is_default ? "（默认）" : "");
          pick.appendChild(option);
        });
        if (ws.textbook_id && !textbookById[ws.textbook_id]) {
          var stale = el("option");
          stale.value = ws.textbook_id;
          stale.textContent = ws.textbook_id + "（当前库未登记）";
          stale.disabled = true;
          pick.appendChild(stale);
        }
        pick.value = ws.textbook_id || "";
        pick.addEventListener("change", function () {
          setWorkspaceTextbook(ws, pick.value, pick);
        });
        picker.appendChild(pick);
        actions.appendChild(picker);
      }
      if (!ws.is_active) {
        var go = el("button", "q-button", "切换");
        go.type = "button";
        go.addEventListener("click", function () { switchWorkspace(ws); });
        actions.appendChild(go);
      }
      li.appendChild(actions);
      wsListEl.appendChild(li);
    });
  }

  function loadWorkspaces() {
    return fetch("/api/workspaces", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(renderWorkspaces)
      .catch(function (error) { mgSet(wsStatus, "读取工作区失败：" + error.message, "down"); });
  }

  function switchWorkspace(ws) {
    if (wsBusy) return;
    wsBusy = true;
    if (wsCreateBtn) wsCreateBtn.disabled = true;
    mgSet(wsStatus, "正在切换到「" + (ws.name || ws.id) + "」…", "info");
    apiCall("/api/workspaces/switch", "POST", { workspace_id: ws.id })
      .then(function () { reloadHostPage(); })
      .catch(function (error) {
        wsBusy = false;
        if (wsCreateBtn) wsCreateBtn.disabled = false;
        mgSet(wsStatus, "切换失败：" + error.message, "down");
      });
  }

  // 已有工作区也能就地换教材版本：只改工作区档案里的偏好字段，不碰题库数据。
  // 改的是当前活跃工作区时刷新宿主，让大纲树、题库浏览与录题页一起按新版本重建。
  function setWorkspaceTextbook(ws, textbookId, selectEl) {
    if (wsBusy) {
      if (selectEl) selectEl.value = ws.textbook_id || "";
      return;
    }
    wsBusy = true;
    if (selectEl) selectEl.disabled = true;
    mgSet(wsStatus, "正在为「" + (ws.name || ws.id) + "」保存教材版本…", "info");
    apiCall("/api/workspaces/textbook", "POST", {
      workspace_id: ws.id,
      textbook_id: textbookId,
    })
      .then(function () {
        if (ws.is_active) {
          reloadHostPage();
          return null;
        }
        wsBusy = false;
        return loadWorkspaces();
      })
      .catch(function (error) {
        wsBusy = false;
        if (selectEl) {
          selectEl.disabled = false;
          selectEl.value = ws.textbook_id || "";
        }
        mgSet(wsStatus, "教材版本保存失败：" + error.message, "down");
      });
  }

  function loadTextbooks() {
    if (!wsTextbookSelect) return Promise.resolve();
    wsTextbookSelect.textContent = "";
    var fallback = el("option");
    fallback.value = "";
    fallback.textContent = "跟随默认版本";
    wsTextbookSelect.appendChild(fallback);
    return fetch("/api/bank/textbooks", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        var items = (data && data.items) || [];
        textbookById = {};
        textbookItems = items;
        activeTextbookId = String((data && data.active_textbook_id) || "");
        if (!items.length) {
          var none = el("option");
          none.value = "";
          none.textContent = "当前题库未登记教材版本";
          none.disabled = true;
          wsTextbookSelect.appendChild(none);
          mgSet(wsStatus, "当前题库没有 textbooks 登记表（老库未升级）；新建工作区仍可用，版本待大纲导入后再选。", "warn");
          return;
        }
        items.forEach(function (item) {
          textbookById[item.id] = item.name;
          var option = el("option");
          option.value = item.id;
          option.textContent = item.name + (item.is_default ? "（默认）" : "") +
            (item.publisher ? " · " + item.publisher : "");
          wsTextbookSelect.appendChild(option);
        });
      })
      .catch(function (error) { mgSet(wsStatus, "读取教材版本清单失败：" + error.message, "down"); });
  }

  function createWorkspace() {
    if (wsBusy || !wsNameInput) return;
    var name = String(wsNameInput.value || "").trim();
    if (!name) { mgSet(wsStatus, "请先填写工作区名称。", "warn"); wsNameInput.focus(); return; }
    var textbookId = wsTextbookSelect ? String(wsTextbookSelect.value || "") : "";
    wsBusy = true;
    if (wsCreateBtn) {
      wsCreateBtn.disabled = true;
      wsCreateBtn.setAttribute("aria-busy", "true");
    }
    mgSet(wsStatus, "正在新建工作区「" + name + "」…", "info");
    apiCall("/api/workspaces", "POST", { name: name })
      .then(function (created) {
        var newId = created && created.id ? String(created.id) : "";
        if (textbookId && newId) {
          mgSet(wsStatus, "工作区已建，正在登记教材版本…", "info");
          return apiCall("/api/workspaces/textbook", "POST", {
            workspace_id: newId,
            textbook_id: textbookId,
          });
        }
        return { workspace_id: newId, textbook_id: "" };
      })
      .then(function () { reloadHostPage(); })
      .catch(function (error) {
        wsBusy = false;
        if (wsCreateBtn) {
          wsCreateBtn.disabled = false;
          wsCreateBtn.setAttribute("aria-busy", "false");
        }
        mgSet(wsStatus, "新建失败：" + error.message, "down");
      });
  }

  if (wsCreateBtn) wsCreateBtn.addEventListener("click", createWorkspace);
  if (wsTextbookRefresh) wsTextbookRefresh.addEventListener("click", function () {
    loadTextbooks().then(loadWorkspaces);
  });
  loadTextbooks().then(loadWorkspaces);

  // ============ 模型配置：Provider 列表 / 切换 / 保存 / 测连通 ============
  var pvSelect = document.getElementById("pvSelect");
  var pvTarget = document.getElementById("pvTarget");
  var pvBaseUrl = document.getElementById("pvBaseUrl");
  var pvApiKey = document.getElementById("pvApiKey");
  var pvModel = document.getElementById("pvModel");
  var pvSwitchBtn = document.getElementById("pvSwitchBtn");
  var pvSaveBtn = document.getElementById("pvSaveBtn");
  var pvTestBtn = document.getElementById("pvTestBtn");
  var pvResult = document.getElementById("pvResult");
  var pvProfiles = [];

  function pvCurrent() {
    var name = pvSelect && pvSelect.value ? pvSelect.value : "";
    for (var i = 0; i < pvProfiles.length; i += 1) {
      if (pvProfiles[i].name === name) return pvProfiles[i];
    }
    return null;
  }

  function pvRenderTarget() {
    if (!pvTarget) return;
    var profile = pvCurrent();
    if (!profile) {
      pvTarget.textContent = "未选择 Provider";
      pvTarget.setAttribute("data-state", "off");
      return;
    }
    pvTarget.textContent = profile.label + " · " + (profile.active ? "当前使用" : "未启用") +
      " · " + (profile.configured ? "已配置密钥" : "未配置（走 Mock）") +
      (profile.host ? " · " + profile.host : "") +
      (profile.model ? " · " + profile.model : "");
    pvTarget.setAttribute("data-state", profile.configured ? "on" : "off");
    if (pvBaseUrl && !pvBaseUrl.value) {
      pvBaseUrl.placeholder = profile.host
        ? "当前接口主机：" + profile.host + "（留空则不改）"
        : "https://api.example.com/v1";
    }
    if (pvModel && !pvModel.value) pvModel.value = profile.model || "";
  }

  function pvNotifyHost() {
    // 宿主顶栏的模型胶囊是只读状态；配置变了就提醒它重新拉一次 /api/providers。
    try {
      if (window.parent && window.parent !== window.self) {
        window.parent.postMessage({ jzo: "providers.changed" }, window.location.origin);
      }
    } catch (error) { /* 独立打开时没有宿主，忽略 */ }
  }

  function pvLoad() {
    return fetch("/api/providers", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        pvProfiles = (data && data.providers) || [];
        if (pvSelect) {
          pvSelect.textContent = "";
          pvProfiles.forEach(function (p) {
            var option = el("option");
            option.value = p.name;
            option.textContent = p.label + (p.configured ? "" : "（未配置）");
            if (p.active) option.selected = true;
            pvSelect.appendChild(option);
          });
        }
        pvRenderTarget();
      })
      .catch(function (error) { mgSet(pvResult, "读取 Provider 注册表失败：" + error.message, "down"); });
  }

  function pvCollect() {
    var profile = pvCurrent();
    if (!profile) return null;
    var payload = { name: profile.name };
    var dirty = false;
    if (pvBaseUrl && pvBaseUrl.value.trim()) { payload.base_url = pvBaseUrl.value.trim(); dirty = true; }
    if (pvApiKey && pvApiKey.value.trim()) { payload.api_key = pvApiKey.value.trim(); dirty = true; }
    if (pvModel && pvModel.value.trim()) { payload.model = pvModel.value.trim(); dirty = true; }
    return dirty ? payload : false;
  }

  function pvSave() {
    var payload = pvCollect();
    if (!payload) return Promise.resolve(false);
    return apiCall("/api/providers/config", "POST", payload).then(function () {
      if (pvApiKey) pvApiKey.value = "";
      if (pvBaseUrl) pvBaseUrl.value = "";
      return pvLoad().then(function () { return true; });
    });
  }

  function pvBusy(btn, on, label) {
    if (!btn) return;
    btn.disabled = on;
    btn.setAttribute("aria-busy", on ? "true" : "false");
    if (label) btn.textContent = label;
  }

  if (pvSelect) pvSelect.addEventListener("change", pvRenderTarget);

  if (pvSwitchBtn) pvSwitchBtn.addEventListener("click", function () {
    var profile = pvCurrent();
    if (!profile) { mgSet(pvResult, "请先选择一个 Provider。", "warn"); return; }
    pvBusy(pvSwitchBtn, true);
    mgSet(pvResult, "正在切换…", "info");
    pvSave().catch(function () { return false; }).then(function () {
      return apiCall("/api/providers/active", "POST", { name: profile.name });
    }).then(function (result) {
      mgSet(pvResult, result.mock
        ? "已切到「" + result.active + "」：未配置密钥，走 Mock 回显。"
        : "已切到「" + result.active + "」：真实模型 " + result.model + "。", "ok");
      return pvLoad().then(pvNotifyHost);
    }).catch(function (error) {
      mgSet(pvResult, "切换失败：" + error.message, "down");
    }).finally(function () { pvBusy(pvSwitchBtn, false); });
  });

  if (pvSaveBtn) pvSaveBtn.addEventListener("click", function () {
    pvBusy(pvSaveBtn, true);
    pvSave().then(function (saved) {
      mgSet(pvResult, saved
        ? "配置已保存并热生效（密钥只落在本机 .env，永不回显）。"
        : "表单没有改动，无需保存。", saved ? "ok" : "info");
      if (saved) pvNotifyHost();
    }).catch(function (error) {
      mgSet(pvResult, "保存失败：" + error.message, "down");
    }).finally(function () { pvBusy(pvSaveBtn, false); });
  });

  if (pvTestBtn) pvTestBtn.addEventListener("click", function () {
    var profile = pvCurrent();
    if (!profile) { mgSet(pvResult, "请先选择一个 Provider。", "warn"); return; }
    pvBusy(pvTestBtn, true);
    mgSet(pvResult, "正在保存未提交的改动，随后向接口发一次只读 GET /models…", "info");
    pvSave().catch(function () { return false; }).then(function () {
      return apiCall("/api/providers/test", "POST", { name: profile.name });
    }).then(function (body) {
      mgSet(pvResult, (body.ok ? "连通正常 · " : "不通 · ") + (body.detail || ""),
        body.ok ? "ok" : "down");
      return pvLoad().then(pvNotifyHost);
    }).catch(function (error) {
      mgSet(pvResult, "测试失败：" + error.message, "down");
    }).finally(function () { pvBusy(pvTestBtn, false); });
  });

  pvLoad();

  // ============ 系统设置：启动行为 ============
  // 数据源是后端 /api/startup 回的 candidates——即「所有已启用插件」，
  // 前端不再自己拼一遍口径，免得两处判断漂移。
  var startupSelect = document.getElementById("startupTarget");
  var startupSaveBtn = document.getElementById("startupSaveBtn");
  var startupReloadBtn = document.getElementById("startupReloadBtn");
  var startupStatus = document.getElementById("startupStatus");
  var startupNow = document.getElementById("startupNow");

  function startupOption(value, text) {
    var option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    return option;
  }

  function renderStartup(body) {
    if (!startupSelect) return;
    var target = String((body && body.target) || "chat");
    startupSelect.textContent = "";
    startupSelect.appendChild(startupOption("chat", "默认欢迎页（自由对话）"));
    var candidates = (body && body.candidates) || [];
    candidates.forEach(function (item) {
      var label = (item.name || item.id) + "（v" + (item.version || "?") + "）";
      if (item.show_in_sidebar === false) label += " · 不占左栏";
      startupSelect.appendChild(startupOption("plugin:" + item.id, label));
    });
    var known = target === "chat" || candidates.some(function (item) {
      return "plugin:" + item.id === target;
    });
    if (!known) {
      // 配置里那个插件已被卸载/停用：如实列出原值，不假装它还在
      startupSelect.appendChild(startupOption(target, target.slice("plugin:".length) + "（已卸载或已停用）"));
    }
    startupSelect.value = target;
    var reason = String((body && body.fallback_reason) || "");
    if (startupNow) {
      if (reason) {
        startupNow.textContent = "当前配置：" + target + " —— " + reason + "。配置已原地保留，插件装回或启用后自动恢复。";
        startupNow.hidden = false;
      } else if (target === "chat") {
        startupNow.textContent = "当前生效：默认欢迎页（自由对话）。";
        startupNow.hidden = false;
      } else {
        startupNow.textContent = "当前生效：" + ((body && body.plugin_name) || target) + "。下次打开软件直接落在这里。";
        startupNow.hidden = false;
      }
    }
  }

  function loadStartup() {
    if (!startupSelect) return Promise.resolve();
    return apiCall("/api/startup", "GET")
      .then(renderStartup)
      .catch(function (error) { mgSet(startupStatus, "读取启动行为失败：" + error.message, "down"); });
  }

  if (startupSaveBtn) startupSaveBtn.addEventListener("click", function () {
    var value = startupSelect ? startupSelect.value : "chat";
    startupSaveBtn.disabled = true;
    startupSaveBtn.setAttribute("aria-busy", "true");
    mgSet(startupStatus, "正在保存启动行为…", "info");
    apiCall("/api/startup", "POST", { target: value })
      .then(function (body) {
        renderStartup(body);
        mgSet(startupStatus, "已保存：下次打开软件将进入「" +
          (body.effective === "chat" ? "默认欢迎页" : (body.plugin_name || body.effective)) + "」。", "ok");
      })
      .catch(function (error) { mgSet(startupStatus, "保存失败：" + error.message, "down"); })
      .finally(function () {
        startupSaveBtn.disabled = false;
        startupSaveBtn.removeAttribute("aria-busy");
      });
  });

  if (startupReloadBtn) startupReloadBtn.addEventListener("click", function () {
    mgSet(startupStatus, "正在重新读取…", "info");
    loadStartup().then(function () { mgSet(startupStatus, "已按磁盘上的配置刷新。", "ok"); });
  });

  loadStartup();
})();

