/**
 * 设置与控制：手动安装 zip。
 *
 * 在线索引的拉取/安装逻辑仍由 plugins.js 负责（同一套表单 id），本文件只补
 * 「手动安装」：文件选择 + 拖拽区 + 状态回显。
 * 边界与工作台拖装一致：只收 .zip、上限 50 MB、写接口带本机令牌、409 需显式
 * 确认覆盖，失败不留半个文件。所有插件名只走 textContent。
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

  function apiCall(path, method, body) {
    var steps = Promise.resolve();
    if (method !== "GET") steps = readToken();
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

  loadInstalled();
})();
