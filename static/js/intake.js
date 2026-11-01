/**
 * 录入入口（宿主壳）：拖入的文件、粘贴的截图。
 *
 * 为什么落在宿主而不是插件里：拖拽与粘贴事件**不跨 iframe 边界**，插件沙箱里的
 * iframe 收不到工作台上的拖放；写令牌也只在宿主手里（AGENTS §2 铁律二、§5 安全）。
 * 于是插件把字节交给宿主，宿主代发——口径只有一处：
 * `POST /api/ingest/files` → 中转站里新建一批待审题。
 *
 * 分拣只看后缀（app/core/ingest.py）：文本类轻量解析、PDF 尽力抽文本层、
 * 图片走 OCR；`.zip` 静默忽略——插件安装包走的是另一条道，不进中转站也不提示。
 *
 * 屏幕截取已下线（真机实测有 Bug、体验不佳）：浏览器没有系统级截屏 API，
 * 借 getDisplayMedia 也只能看见视口、还得让用户亲手点一下才肯开屏。
 * 要截屏就用 Ctrl+V 把剪贴板里的图贴进来。
 */
(function () {
  "use strict";

  var INGEST_URL = "/api/ingest/files";
  var MAX_FILES = 20;
  var MAX_FILE_BYTES = 32 * 1024 * 1024;

  var writeQueue = Promise.resolve();

  // ---------- 通用小工具 ----------

  function dock(text, tone) {
    if (!window.JzoBus || typeof window.JzoBus.emit !== "function") return;
    window.JzoBus.emit("region.dock", {
      text: String(text || "").slice(0, 300),
      topic: tone === "warn" ? "host.warn" : "host.notice"
    });
  }

  function suffixOf(name) {
    var text = String(name || "");
    var dot = text.lastIndexOf(".");
    return dot < 0 ? "" : text.slice(dot).toLowerCase();
  }

  function isZip(name) {
    return suffixOf(name) === ".zip";
  }

  function readAsDataUrl(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(String(reader.result || "")); };
      reader.onerror = function () {
        reject(new Error("读取文件失败：" + (file && file.name ? file.name : "未命名")));
      };
      reader.readAsDataURL(file);
    });
  }

  // ---------- 写通道：一次性令牌永远在宿主侧 ----------

  function postJson(url, body) {
    return fetch("/api/settings", { cache: "no-store" })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var token = data && data.local_token;
        if (!token) throw new Error("拿不到本地写操作令牌");
        return fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-JZO-Token": token },
          body: JSON.stringify(body)
        });
      })
      .then(function (response) {
        return response.text().then(function (text) {
          var data = null;
          try { data = text ? JSON.parse(text) : {}; } catch (error) { data = null; }
          if (!response.ok) {
            var detail = data && data.detail;
            var message = typeof detail === "string" ? detail
              : (detail && detail.message) || ("宿主接口返回 HTTP " + response.status);
            throw new Error(message);
          }
          return data || {};
        });
      });
  }

  /** 写操作排队：令牌用后即焚，两个写同时打出去必有一个被拒。 */
  function serialize(task) {
    var next = writeQueue.then(task, task);
    writeQueue = next.then(function () {}, function () {});
    return next;
  }

  function announce(result) {
    var batchId = String((result && result.batch_id) || "");
    var saved = Array.isArray(result && result.saved_ids) ? result.saved_ids.length : 0;
    var warnings = Array.isArray(result && result.warnings) ? result.warnings : [];
    // parsing=true：批次已经立起来了，识别在后台跑，此刻池子里躺的是占位题。
    var parsing = Boolean(result && result.parsing);
    if (batchId) {
      window.JzoBus.emit("system.pending_updated", {
        action: "ingest",
        pending_ids: (result.saved_ids || []).map(function (id) { return String(id); }),
        batch_id: batchId,
        pluginId: ""
      });
    }
    if (saved) {
      dock(parsing
        ? "已收下 " + saved + " 份（批次 " + batchId + "），正在后台解析。"
        : "已入池 " + saved + " 道题（批次 " + batchId + "），去批次列表里审。");
    } else if (warnings.length) {
      dock("没有认出题目：" + warnings[0], "warn");
    } else {
      dock("这次没能从文件里认出题目。", "warn");
    }
    warnings.forEach(function (text) { dock(String(text), "warn"); });
  }

  /**
   * 入库一批文件条目（``{name, data_url}``）。
   * 插件转发与宿主自己拖进来的文件走同一个函数，队列与令牌口径只有一处。
   */
  function ingestEntries(entries, options) {
    var opts = options || {};
    var prepared = [];
    var oversized = 0;
    for (var i = 0; i < (entries || []).length; i += 1) {
      var entry = entries[i] || {};
      var name = String(entry.name || "").slice(0, 120);
      var dataUrl = typeof entry.data_url === "string" ? entry.data_url : "";
      if (!name || !dataUrl) continue;
      if (dataUrl.length > 48 * 1024 * 1024) { oversized += 1; continue; }
      prepared.push({ name: name, data_url: dataUrl });
      if (prepared.length >= MAX_FILES) break;
    }
    if (!prepared.length) {
      return Promise.resolve({ skipped: true, warnings: oversized ? ["文件超过 32 MB 上限。"] : [] });
    }
    return serialize(function () {
      return postJson(INGEST_URL, { files: prepared });
    }).then(function (result) {
      if (opts.silent !== true) announce(result);
      return result;
    });
  }

  /** 宿主自己拿到的 File 对象 → 入库。``.zip`` 静默忽略：不提示、不建批次。 */
  function ingestFiles(fileList, options) {
    var opts = options || {};
    var files = Array.prototype.slice.call(fileList || []);
    var docs = [];
    var ignored = 0;
    var oversized = 0;
    for (var i = 0; i < files.length; i += 1) {
      var file = files[i];
      if (!file) continue;
      if (isZip(file.name)) { ignored += 1; continue; }
      if (file.size > MAX_FILE_BYTES) { oversized += 1; continue; }
      docs.push(file);
    }
    if (!docs.length) {
      if (oversized && opts.silent !== true) dock("文件超过 32 MB 上限，没收。", "warn");
      return Promise.resolve({ skipped: true, ignored: ignored });
    }
    if (docs.length > MAX_FILES) {
      docs = docs.slice(0, MAX_FILES);
      if (opts.silent !== true) dock("一次最多收 " + MAX_FILES + " 个文件，多出来的没收。", "warn");
    }
    return Promise.all(docs.map(function (file) {
      return readAsDataUrl(file).then(function (dataUrl) {
        return { name: file.name || "未命名文件", data_url: dataUrl };
      });
    })).then(function (entries) {
      return ingestEntries(entries, opts);
    });
  }

  // ---------- 宿主自己的两个入口 ----------

  /**
   * 剪贴板里的图片：``items`` 与 ``files`` 两路都取。
   *
   * 只认 ``items`` 不够——有些环境（部分远程桌面、部分浏览器）贴图时
   * ``items`` 是空的，只有 ``files`` 里有货；反过来也有只给 ``items`` 的。
   * 两路都取、同一张只留一份，粘贴才不会时灵时不灵。
   */
  function clipboardImageFiles(event) {
    var data = event && event.clipboardData;
    if (!data) return [];
    var files = [];
    var seen = [];
    function push(file) {
      if (!file) return;
      var type = String(file.type || "").toLowerCase();
      if (type.indexOf("image/") !== 0) return;
      var name = String(file.name || "");
      var size = Number(file.size || 0);
      for (var i = 0; i < seen.length; i += 1) {
        if (seen[i].type === type && seen[i].name === name && seen[i].size === size) return;
      }
      seen.push({ type: type, name: name, size: size });
      files.push(file);
    }
    var items = data.items || [];
    for (var i = 0; i < items.length; i += 1) {
      if (items[i].kind !== "file") continue;
      var file = items[i].getAsFile();
      if (file) push(file);
    }
    var listed = data.files || [];
    for (var j = 0; j < listed.length; j += 1) push(listed[j]);
    return files;
  }

  function isTypingTarget(target) {
    if (!target || !target.tagName) return false;
    var tag = String(target.tagName).toUpperCase();
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable === true;
  }

  /**
   * 文件送进录题工作台的收集筐（军令 #27）。
   *
   * 录题画布开着的时候，拖入/粘贴的文件先落它的收集筐，
   * 老师点【开始解析】才建批次——不绕过那道确认。
   * 画布没开或已休眠就返回 false，调用方退回「直接入库」的老路，文件不许丢。
   */
  function collectIntoEditor(files) {
    var editorId = "org.jiuzhang.editor";
    var active = window.JzoWorkspace && typeof window.JzoWorkspace.activeCanvasPlugin === "function"
      ? window.JzoWorkspace.activeCanvasPlugin() : "";
    if (active !== editorId) return false;
    if (!window.JzoStage || typeof window.JzoStage.notifyCanvas !== "function") return false;
    return window.JzoStage.notifyCanvas(editorId, "editor.collect_files", { files: files });
  }

  window.addEventListener("paste", function (event) {
    if (isTypingTarget(event.target)) return;
    var files = clipboardImageFiles(event);
    if (!files.length) return;
    event.preventDefault();
    if (collectIntoEditor(files)) return;
    ingestFiles(files, { source: "paste" });
  });

  window.JzoIntake = {
    ingestFiles: ingestFiles,
    ingestEntries: ingestEntries,
    collectIntoEditor: collectIntoEditor,
    // 写队列是全局唯一的：stage.js 的写操作也走这一条，两边才不会互相烧掉对方的令牌。
    serialize: serialize
  };
})();
