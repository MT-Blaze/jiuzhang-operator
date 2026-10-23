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

  // 宿主页签可以指定落在哪一区：首次用地址参数 ?panel=provider，后续用同源 postMessage。
  function requestPanelFromHost(key) {
    if (PANEL_KEYS.indexOf(key) === -1) return;
    selectPanel(key, false);
  }

  var urlPanel = /[?&]panel=([^&]+)/.exec(window.location.search);
  if (urlPanel) {
    try { requestPanelFromHost(decodeURIComponent(urlPanel[1])); } catch (error) { /* 非法参数回落默认区 */ }
  }
  window.addEventListener("message", function (event) {
    if (event.origin !== window.location.origin) return;
    var data = event.data;
    if (data && data.jzo === "console.panel") requestPanelFromHost(String(data.panel || ""));
  });

  // ============ 工作区：列出 / 切换 / 新建（含教材版本） ============
  var wsListEl = document.getElementById("stWsList");
  var wsStatus = document.getElementById("stWsStatus");
  var wsNameInput = document.getElementById("stWsName");
  var wsTextbookSelect = document.getElementById("stWsTextbook");
  var wsCreateBtn = document.getElementById("stWsCreateBtn");
  var wsTextbookRefresh = document.getElementById("stWsTextbookRefresh");
  var textbookById = {};
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
      var tb = ws.textbook_id ? (textbookById[ws.textbook_id] || ws.textbook_id) : "跟随默认版本";
      li.appendChild(el("span", "st-ws-meta",
        (ws.is_active ? "当前 · " : "") + Number(ws.question_count || 0) + " 题 · 教材：" + tb));
      var actions = el("div", "st-ws-actions");
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

