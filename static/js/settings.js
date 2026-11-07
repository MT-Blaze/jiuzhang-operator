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

  // ---------- 拆出去的模块（PLUGIN_SPEC §2.8.1：单文件不超 800 行） ----------
  var stWorkspace = window.JzoStWorkspace.create({
    // 循环引用：apiCall 归更下面的 stPlugins，本块排得靠前，只能等它就位后再取。
    apiCall: function () { return stPlugins.apiCall.apply(stPlugins, arguments); },
    // 循环引用：el 归更下面的 stPlugins，本块排得靠前，只能等它就位后再取。
    el: function () { return stPlugins.el.apply(stPlugins, arguments); },
    // 循环引用：mgSet 归更下面的 stPlugins，本块排得靠前，只能等它就位后再取。
    mgSet: function () { return stPlugins.mgSet.apply(stPlugins, arguments); },
    readJson: readJson,
  });
  var loadTextbooks = stWorkspace.loadTextbooks;
  var loadWorkspaces = stWorkspace.loadWorkspaces;
  var reloadHostPage = stWorkspace.reloadHostPage;
  var runWorkspaceRequest = stWorkspace.runWorkspaceRequest;

  var stPlugins = window.JzoStPlugins.create({
    readJson: readJson,
    readToken: readToken,
    runWorkspaceRequest: runWorkspaceRequest,
  });
  var apiCall = stPlugins.apiCall;
  var el = stPlugins.el;
  var fileToBase64 = stPlugins.fileToBase64;
  var loadInstalled = stPlugins.loadInstalled;
  var mgSet = stPlugins.mgSet;
  var stBankio = window.JzoStBankio.create({
    apiCall: apiCall,
    fileToBase64: fileToBase64,
    httpFailure: httpFailure,
    loadInstalled: loadInstalled,
    mgSet: mgSet,
  });
  var stUpdate = window.JzoStUpdate.create({
    apiCall: apiCall,
    el: el,
    loadInstalled: loadInstalled,
    mgSet: mgSet,
  });
  var stBackup = window.JzoStBackup.create({
    apiCall: apiCall,
    el: el,
    mgSet: mgSet,
    reloadHostPage: reloadHostPage,
  });
  var bkSyncToggles = stBackup.bkSyncToggles;
  var loadBackup = stBackup.loadBackup;

  var stNav = window.JzoStNav.create({
    loadBackup: loadBackup,
  });
  var stProvider = window.JzoStProvider.create({
    apiCall: apiCall,
    el: el,
    mgSet: mgSet,
    readJson: readJson,
  });
  var stStartup = window.JzoStStartup.create({
    apiCall: apiCall,
    mgSet: mgSet,
  });
  var loadStartup = stStartup.loadStartup;

  // ---------- 拆出去的模块：以上每块都只经 deps 拿依赖 ----------

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

  function httpFailure(response, text, data, url, method, payload) {
    if (window.JzoHttp && typeof window.JzoHttp.fromResponse === "function") {
      return window.JzoHttp.fromResponse(response, text, data, {
        method: method, url: url, payload: payload
      });
    }
    var error = new Error("HTTP " + response.status + " " + url + "：" + String(text || "").slice(0, 300));
    error.status = response.status;
    error.body = String(text || "");
    return error;
  }

  /** 读 JSON：非 2xx 也必须把响应全文读完再抛，404 才有现场可查。 */
  function readJson(response, url, method, payload) {
    return response.text().then(function (text) {
      var data = null;
      try { data = text ? JSON.parse(text) : {}; } catch (error) { data = null; }
      if (!response.ok) throw httpFailure(response, text, data, url, method, payload);
      return data || {};
    });
  }

  function readToken() {
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (response) {
        return readJson(response, "/api/settings", "GET");
      })
      .then(function (body) {
        var token = body && body.local_token ? String(body.local_token) : "";
        if (!token) {
          throw new Error("本机未生成就绪令牌：GET /api/settings 返回里没有 local_token，请先启动服务后再试");
        }
        return token;
      });
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
        return response.text().then(function (text) {
          var body = null;
          try { body = text ? JSON.parse(text) : null; } catch (error) { body = null; }
          var payloadLabel = "zip " + String(file.name || "未命名") + "（" + file.size + " 字节）";
          if (response.status === 409 && !replace) {
            var conflict = httpFailure(response, text, body, "/api/plugins/install", "POST", payloadLabel);
            var question = conflict.message + " 覆盖升级会先删除旧目录，继续吗？";
            if (window.confirm(question)) return installZip(file, true);
            setStatus("已取消覆盖，本机原有插件保持不变。", "info");
            return null;
          }
          if (!response.ok) {
            throw httpFailure(response, text, body, "/api/plugins/install", "POST", payloadLabel);
          }
          var plugins = (body && Array.isArray(body.plugins) && body.plugins.length)
            ? body.plugins : [(body && body.plugin) || {}];
          var names = plugins.map(function (item) {
            return (item.name || item.id || "?") + " v" + (item.version || "?");
          }).join("、");
          var suite = body && body.suite;
          setStatus(
            (suite
              ? "已安装套件「" + (suite.name || suite.id) + "」，共 " + plugins.length + " 个插件：" + names
              : "已安装 " + names) +
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

  bkSyncToggles();

  loadStartup();
  // 循环引用的收口：stWorkspace 取教材列表要用 stPlugins 的 el，stPlugins 又要
  // stWorkspace 的 runWorkspaceRequest —— 首屏取数只能等两块都就位后再跑。
  loadTextbooks().then(loadWorkspaces);
})();

