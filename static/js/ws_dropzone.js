/**
 * ws_dropzone.js —— workspace.js 的「插件拖拽装」小节抽出来的独立模块
 * （PLUGIN_SPEC §2.8.1 同款口径：底座 JS 单文件不超过 800 行）。
 *
 * 依赖一律由 create(deps) 交进来，模块不认全局、也不碰宿主 DOM。
 */
(function (global) {
  "use strict";

  function create(deps) {
    var EDITOR_PLUGIN_ID = deps.EDITOR_PLUGIN_ID;
    var addBubble = deps.addBubble;
    var fetchWriteToken = deps.fetchWriteToken;
    var loadPlugins = deps.loadPlugins;
    var wsState = deps.wsState;

  // ============ 插件拖拽装 + 拖入文件建批次：工作台全局兜底 ============
  // 拖进来的东西分两路：.zip 是插件包，走安装；其余（PDF / Word / TeX / MD / 图片）
  // 是卷子，走录入通道解析成批次。.zip 在录入通道里静默忽略——它不是题。
  var dropOverlay = document.getElementById("wsDropOverlay");
  var intakeOverlay = document.getElementById("wsIntakeOverlay");
  var intakeTitleEl = document.getElementById("wsIntakeTitle");
  var intakeHintEl = document.getElementById("wsIntakeHint");

  function installPluginZip(file, replace) {
    if (!file) return Promise.resolve();
    if (!/\.zip$/i.test(file.name || "")) {
      addBubble("sys", "只接受 .zip 插件包（标准 zip，解压即用）。", { tone: "warn" });
      return Promise.resolve();
    }
    if (file.size > 50 * 1024 * 1024) {
      addBubble("sys", "zip 包超过 50 MB 上限。", { tone: "warn" });
      return Promise.resolve();
    }
    addBubble("sys", "正在安装 " + file.name + " …");
    return fetchWriteToken()
      .then(function (token) {
        return fetch("/api/plugins/install" + (replace ? "?replace=true" : ""), {
          method: "POST",
          headers: { "Content-Type": "application/zip", "X-JZO-Token": token },
          body: file,
        });
      })
      .then(function (r) {
        return window.JzoHttp.readText(r, function (text, body) {
          var payloadLabel = "zip " + String(file.name || "未命名") + "（" + file.size + " 字节）";
          if (r.status === 409 && !replace) {
            var conflict = window.JzoHttp.fromResponse(r, text, body, {
              method: "POST", url: "/api/plugins/install", payload: payloadLabel
            });
            var question = conflict.message + " 覆盖升级会先删除旧目录，继续吗？";
            // 定调令：工作台不许有浏览器原生弹窗。确认走宿主自绘对话框，
            // 确认后仍是一次全新的安装请求（replace=true）。
            if (!window.JzoDialogs) {
              addBubble("sys", question, { tone: "warn" });
              return null;
            }
            window.JzoDialogs.confirm({
              title: "覆盖安装",
              message: question,
              confirmText: "覆盖安装",
              onAccept: function () { installPluginZip(file, true); }
            });
            return null;
          }
          if (!r.ok) {
            throw window.JzoHttp.fromResponse(r, text, body, {
              method: "POST", url: "/api/plugins/install", payload: payloadLabel
            });
          }
          var plugin = body && body.plugin ? body.plugin : {};
          addBubble("sys", "插件已安装：" + (plugin.name || plugin.id) + " v" + (plugin.version || "?"));
          // 装完立即刷新插件区；刷新失败不回滚安装结果，也不谎报安装失败。
          return loadPlugins().catch(function () { return null; });
        });
      })
      .catch(function (err) {
        addBubble("sys", "插件安装失败：" + err.message, { tone: "warn" });
      })
      .finally(function () {
        wsState.writeToken = null;
      });
  }

  function pickFirstZip(fileList) {
    for (var i = 0; i < (fileList || []).length; i += 1) {
      if (/\.zip$/i.test(fileList[i].name || "")) return fileList[i];
    }
    return null;
  }

  function hasFiles(event) {
    var types = (event.dataTransfer && event.dataTransfer.types) || [];
    return Array.prototype.indexOf.call(types, "Files") !== -1;
  }

  /** 拖的是不是插件包：全是 application/zip 才算（类型不明的先当卷子）。 */
  function draggedIsZip(event) {
    var items = (event.dataTransfer && event.dataTransfer.items) || [];
    var seen = 0;
    for (var i = 0; i < items.length; i += 1) {
      if (items[i].kind !== "file") continue;
      seen += 1;
      var type = String(items[i].type || "").toLowerCase();
      if (!type) return false;
      if (type !== "application/zip" && type !== "application/x-zip-compressed") return false;
    }
    return seen > 0;
  }

  function showDropOverlay(show, zipMode) {
    if (dropOverlay) dropOverlay.hidden = !show || !zipMode;
    if (intakeOverlay) intakeOverlay.hidden = !show || zipMode;
    if (!show || zipMode) return;
    // 落点不一样，话术就不能一样：录题工作台开着时，文件先进它的收集筐。
    var intoBasket = wsState.activeCanvasPluginId === EDITOR_PLUGIN_ID;
    if (intakeTitleEl) {
      intakeTitleEl.textContent = intoBasket
        ? "松开鼠标，收进录题工作台的收集筐"
        : "松开鼠标，自动解析并建立批次";
    }
    if (intakeHintEl) {
      intakeHintEl.textContent = intoBasket
        ? "收 PDF / Word / TeX / MD / 图片；到画布里点【开始解析】才建批次"
        : "收 PDF / Word / TeX / MD / 图片；解析完直接进批次列表";
    }
  }

  window.addEventListener("dragenter", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    wsState.dragDepth += 1;
    showDropOverlay(true, draggedIsZip(event));
  });
  window.addEventListener("dragover", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
  });
  window.addEventListener("dragleave", function (event) {
    if (!hasFiles(event)) return;
    wsState.dragDepth -= 1;
    if (wsState.dragDepth <= 0) {
      wsState.dragDepth = 0;
      showDropOverlay(false);
    }
  });
  window.addEventListener("drop", function (event) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    wsState.dragDepth = 0;
    showDropOverlay(false);
    var files = event.dataTransfer && event.dataTransfer.files;
    var file = pickFirstZip(files);
    var docs = [];
    for (var i = 0; i < (files || []).length; i += 1) {
      if (!/\.zip$/i.test(files[i].name || "")) docs.push(files[i]);
    }
    if (file) installPluginZip(file, false);
    if (docs.length) {
      // 录题工作台开着时，文件先进它的收集筐：老师点【开始解析】才建批次。
      var collected = window.JzoIntake && typeof window.JzoIntake.collectIntoEditor === "function"
        ? window.JzoIntake.collectIntoEditor(docs) : false;
      if (!collected && window.JzoIntake) {
        window.JzoIntake.ingestFiles(docs, { source: "chrome" });
      }
    } else if (!file && !docs.length) {
      addBubble("sys", "没看到可解析的文件（PDF / Word / TeX / MD / 图片都行）。", { tone: "warn" });
    }
  });

    return {
      draggedIsZip: draggedIsZip,
      dropOverlay: dropOverlay,
      hasFiles: hasFiles,
      installPluginZip: installPluginZip,
      intakeHintEl: intakeHintEl,
      intakeOverlay: intakeOverlay,
      intakeTitleEl: intakeTitleEl,
      pickFirstZip: pickFirstZip,
      showDropOverlay: showDropOverlay,
    };
  }

  global.JzoWsDropzone = { create: create };
})(window);
